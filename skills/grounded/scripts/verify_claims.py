#!/usr/bin/env python3
"""
Claim-level verification: check that every cited sentence says what its source says.

Bibliographic verification (verify_citations.py) proves a source exists; this tool
audits whether the sentence in front of each citation is supported by that source's
own text. It is deliberately split between deterministic machinery (this script)
and judgment (the agent):

  seed      fill the evidence store from the review's own reading — the
            authenticated full texts in fulltexts/ and the ledger abstracts —
            for every verified ledger DOI, before any network call
  synthesis-check
            quotes before prose: every key a synthesis claim cites carries a
            verbatim quote line that string-matches the stored text, and every
            number in the claim sentence sits inside one of its quotes
  extract   parse the review into (claim sentence, cited DOI) pairs; with
            --synthesis, refuse a cited source the synthesis never quoted and
            carry the synthesis quotes into each packet
  fetch     acquire evidence per DOI via claim_evidence.py — abstract tier for
            every source, full text for sources carrying numeric claims
  packets   print one adjudication packet per pending pair: the claim, the
            evidence tier, and candidate passages selected around the claim's
            numbers and rare terms. The agent reads packets and writes a verdict
            and a VERBATIM quote into the audit JSON.
  check     enforce the quote-or-abstain contract mechanically: a verdict of
            supported/partial/contradicted is kept only if its quote appears
            verbatim (after normalization) in the stored evidence, and a numeric
            claim marked supported must have all assigned quantities and units
            inside its supporting quotations. Violations are downgraded, never silently accepted.
            Renders the audit appendix, writes the summary the colophon
            prints, and prints coverage statistics.
  receipts  write the reader-facing receipts as a separate Markdown file
            (one entry per cited sentence: source, evidence tier, verdict,
            verbatim quote) and stamp the review: every Sources entry gains
            "· N claims · full text|abstract" and a two-line **Receipts** block
            after Sources carries the tally and the file name. The PDF prints
            only the tally in its colophon.

Verdicts: supported | partial | not_found | contradicted | unverifiable.
The judge can be wrong, but it cannot invent evidence: quotes that do not occur
in the source are rejected here, in code.

Usage:
  python3 verify_claims.py extract  --review review.md --audit claims_audit.json
  python3 verify_claims.py fetch    --audit claims_audit.json --evidence evidence/
  python3 verify_claims.py packets  --audit claims_audit.json --evidence evidence/
  python3 verify_claims.py check    --audit claims_audit.json --evidence evidence/ \
                                    --summary claims_summary.json --appendix claims_appendix.md
  python3 verify_claims.py receipts --audit claims_audit.json --review review.md
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import claim_evidence
import claim_receipts
import synthesis_quotes
from artifact_io import atomic_write_json, atomic_write_text

PACKET_FALLBACK_CHARS = 2500
VERDICTS = {"supported", "partial", "not_found", "contradicted", "unverifiable"}
FINAL_NEEDING_QUOTE = {"supported", "partial", "contradicted"}

from claim_inventory import (
    DOI_LINK_RE, claim_numbers, extract_claims, quotes_of, spell_to_digits,
    split_sentences,
)
import audit_contract
import evidence_assessment


# ------------------------------------------------------------------ passages --

_STOP = set("""the a an and or of in on for with without to from by as is are was were
be been being that this those these it its their there than then into over under about
during between among after before which while whereas although though because""".split())


def candidate_passages(claim, numbers, evidence_text, max_windows=8, radius=320):
    """Deterministic passage selection: windows around the claim's numbers and
    rare words, ranked by numeric anchors first, then by how many distinct
    claim tokens they contain — a window carrying the sentence's own number
    is never crowded out by wordier ones."""
    if not evidence_text:
        return []
    anchors = list(numbers)
    for w in re.findall(r"[A-Za-z][A-Za-z-]{5,}", claim):
        lw = w.lower()
        if lw not in _STOP and lw not in anchors:
            anchors.append(lw)
    lower = evidence_text.lower()
    spans = []
    for anchor in anchors:
        for m in re.finditer(re.escape(anchor.lower()), lower):
            spans.append((max(0, m.start() - radius), min(len(lower), m.end() + radius)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    claim_tokens = {t for t in re.findall(r"[a-z0-9.%]+", claim.lower()) if t not in _STOP}

    number_tokens = [n.replace(",", "").lower() for n in numbers]

    def score(span):
        window = lower[span[0]:span[1]].replace(",", "")
        anchors = sum(1 for n in number_tokens if n and n in window)
        return 100 * anchors + sum(1 for t in claim_tokens if t in window)

    merged.sort(key=score, reverse=True)
    out = []
    for s, e in merged[:max_windows]:
        snippet = re.sub(r"\s+", " ", evidence_text[s:e]).strip()
        out.append(("…" if s > 0 else "") + snippet + ("…" if e < len(evidence_text) else ""))
    return out


# ------------------------------------------------------------------ commands --

def cmd_extract(args):
    markdown = Path(args.review).read_text()
    key_to_doi = {}
    ledger = None
    if args.ledger:
        ledger = json.loads(Path(args.ledger).read_text())
        key_to_doi = {e["key"]: e.get("doi") for e in ledger["entries"] if e.get("doi")}
    claims = extract_claims(markdown, key_to_doi, include_uncited=True)
    if getattr(args, "synthesis", None):
        if ledger is None:
            sys.exit("--synthesis needs --ledger to map keys to DOIs")
        quoted = synthesis_quotes.quotes_by_doi(
            Path(args.synthesis).read_text(), ledger)
        unquoted = []
        for c in claims:
            for adj in c["adjudications"]:
                found = quoted.get(claim_evidence.norm_doi(adj["doi"]), [])
                adj["synthesis_quotes"] = [q for _cid, q in found]
                if not found and adj["doi"] not in unquoted:
                    unquoted.append(adj["doi"])
        if unquoted:
            for doi in unquoted:
                print(f"  ! cited source has no quote in the synthesis: {doi}")
            print("HARD FAIL: the review cites what the synthesis never quoted — "
                  "add the quote to synthesis.md (and re-run synthesis-check) or "
                  "drop the citation.")
            sys.exit(1)
        assessment_path = Path(getattr(args, "assessment", None) or
                               Path(args.synthesis).with_name("evidence-assessment.json"))
        assessment = json.loads(assessment_path.read_text())
        assessed = evidence_assessment.assess(assessment, ledger, Path(args.synthesis).read_text())
        if assessed["errors"]:
            sys.exit("; ".join(assessed["errors"]))
    audit = {
        "schema_version": 2,
        "review": str(args.review),
        "inventory_sha256": audit_contract.inventory_digest(claims),
        "created": time.strftime("%Y-%m-%d"),
        "claims": claims,
    }
    if getattr(args, "synthesis", None):
        audit["evidence_assessment"] = assessment
    atomic_write_json(args.audit, audit)
    n_pairs = sum(len(c["dois"]) for c in claims)
    dois = {d for c in claims for d in c["dois"]}
    print(f"{len(claims)} claims, {n_pairs} claim-citation pairs, "
          f"{len(dois)} unique DOIs -> {args.audit}")


def _numeric_dois(audit):
    return {d for c in audit["claims"] if c["numbers"] for d in c["dois"]}


def cmd_fetch(args):
    audit = json.loads(Path(args.audit).read_text())
    dois = []
    for c in audit["claims"]:
        for d in c["dois"]:
            if d not in dois:
                dois.append(d)
    numeric = _numeric_dois(audit) if not args.fulltext_all else set(dois)
    if args.ledger or args.fulltext_dir:
        seeded = claim_evidence.seed_local_evidence(
            dois, args.evidence, ledger_path=args.ledger,
            fulltext_dir=args.fulltext_dir, manifest_path=args.fulltext_manifest)
        counts = {}
        for tier in seeded.values():
            counts[tier] = counts.get(tier, 0) + 1
        print("seeded from the review's own reading: "
              + (", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nothing"))
    tiers = {}
    for doi in dois:
        if args.offline:
            _text, meta = claim_evidence.load_evidence(doi, args.evidence)
            meta = meta or {"tier": "none", "source": "offline: not in store"}
        else:
            meta = claim_evidence.acquire(doi, args.evidence,
                                          want_fulltext=(doi in numeric or args.fulltext_all))
        tiers[meta.get("tier", "none")] = tiers.get(meta.get("tier", "none"), 0) + 1
        print(f"[{meta.get('tier', 'none'):>8}] {doi}  ({meta.get('source', '-')}"
              f"{', ' + str(meta.get('words', 0)) + 'w' if meta.get('words') else ''})")
        time.sleep(args.sleep)
    print("coverage: " + ", ".join(f"{k}={v}" for k, v in sorted(tiers.items())))


def cmd_packets(args):
    audit = json.loads(Path(args.audit).read_text())
    shown = 0
    blind = getattr(args, "blind", False)
    for c in audit["claims"]:
        if args.claim and c["id"] != args.claim:
            continue
        if not c["adjudications"]:
            print(f"{c['id']} (classification required): {c['claim']}")
            print("  Classify factual, interpretation with factual basis IDs, or nonfactual with reason.")
        for element in c.get("elements", []):
            print(f"  {c['id']}/{element['id']}: {element['text']}")
        for index, adj in enumerate(c["adjudications"], 1):
            if args.pending_only and adj["verdict"] != "pending":
                continue
            if args.claim and c["id"] != args.claim:
                continue
            text, meta = claim_evidence.load_evidence(adj["doi"], args.evidence)
            if blind:
                # The judge sees the sentence and the passages, nothing else:
                # no source identity, no place in the review, no author context.
                print(f"### packet {c['id']}#{index} "
                      f"[tier: {(meta or {}).get('tier', 'MISSING')}]")
            else:
                print(f"### {c['id']} :: {adj['doi']} "
                      f"[tier: {(meta or {}).get('tier', 'MISSING')}] ({c['location']})")
            print(f"CLAIM: {claim_receipts.plain_text(c['claim'])}")
            if c["numbers"]:
                print(f"NUMERIC ANCHORS: {', '.join(c['numbers'])}")
            for i, quote in enumerate(adj.get("synthesis_quotes") or [], 1):
                print(f"  S{i}. {quote}")
            passages = candidate_passages(c["claim"], c["numbers"], text or "")
            if text and not passages:
                # No anchor matched: show the opening of the stored text rather
                # than nothing, so the judge can still read and abstain honestly.
                head = re.sub(r"\s+", " ", text[:PACKET_FALLBACK_CHARS]).strip()
                passages = [head + ("…" if len(text) > PACKET_FALLBACK_CHARS else "")]
                print("  (no passage anchored on the claim's terms; opening of the "
                      f"stored text shown, {len(text.split())} words in store)")
            for i, passage in enumerate(passages, 1):
                print(f"  P{i}. {passage}")
            if not text:
                print("  (no evidence text in store — verdict must be unverifiable)")
            print()
            shown += 1
    print(f"{shown} packets.")


def cmd_check(args):
    audit = json.loads(Path(args.audit).read_text())
    counts = {}
    downgrades = []
    hard_fail = False
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            verdict = adj.get("verdict", "pending")
            if verdict not in VERDICTS | {"pending"}:
                downgrades.append(f"{c['id']}/{adj['doi']}: unknown verdict '{verdict}'")
                verdict = adj["verdict"] = "pending"
            text, meta = claim_evidence.load_evidence(adj["doi"], args.evidence)
            adj["tier"] = (meta or {}).get("tier", "none")
            if verdict in FINAL_NEEDING_QUOTE:
                quotes = quotes_of(adj)
                bad = [q for q in quotes if not claim_evidence.quote_in_text(q, text or "")]
                if not quotes or bad:
                    downgrades.append(
                        f"{c['id']}/{adj['doi']}: quote not found verbatim in evidence "
                        f"— downgraded {verdict} -> unverifiable"
                        + (f" (rejected: “{bad[0][:60]}…”)" if bad else ""))
                    verdict = adj["verdict"] = "unverifiable"
                    adj["note"] = (adj.get("note", "") + " [quote rejected by check]").strip()
                elif not quote_relates_to_claim(" ".join(quotes), c["claim"]):
                    bridge = " ".join((adj.get("bridge") or "").split())
                    if not bridge:
                        downgrades.append(
                            f"{c['id']}/{adj['doi']}: quote shares no content term or "
                            f"number with the claim — downgraded {verdict} -> unverifiable "
                            "(pick a quote that shares a term, or state the paraphrase "
                            "with --bridge)")
                        verdict = adj["verdict"] = "unverifiable"
                        adj["note"] = (adj.get("note", "") + " [quote unrelated to claim]").strip()
                    elif not bridge_connects(bridge, " ".join(quotes), c["claim"]):
                        downgrades.append(
                            f"{c['id']}/{adj['doi']}: bridge “{bridge[:50]}” names no term "
                            f"from both the quote and the claim — downgraded {verdict} -> unverifiable")
                        verdict = adj["verdict"] = "unverifiable"
                        adj["note"] = (adj.get("note", "") + " [bridge does not connect]").strip()
                elif verdict == "supported" and c["numbers"]:
                    quote_flat = spell_to_digits(" … ".join(quotes)).replace(",", "")
                    covered_text = " ".join(e["text"] for e in c.get("elements", [])
                                            if e["id"] in adj.get("covers", [])) or c["claim"]
                    if audit_contract.missing_quantities(covered_text, " … ".join(quotes)):
                        downgrades.append(
                            f"{c['id']}/{adj['doi']}: numeric claim has unmatched quantities "
                            f"in quote — downgraded supported -> partial")
                        verdict = adj["verdict"] = "partial"
                        adj["note"] = (adj.get("note", "") + " [numeric anchor missing]").strip()
            if verdict == "contradicted":
                hard_fail = True
            counts[verdict] = counts.get(verdict, 0) + 1
    atomic_write_json(args.audit, audit)
    judgment_errors = judgment_problems(audit)
    if audit.get("schema_version") == 2:
        judgment_errors.extend(audit_contract.coverage_errors(audit))
        audit.pop("checked_sha256", None)
        if not judgment_errors and not hard_fail:
            audit_contract.bind_evidence(audit, args.evidence, args.audit)
            audit["checked_sha256"] = audit_contract.checked_digest(audit)
        atomic_write_json(args.audit, audit)

    total = sum(counts.values())
    tier_counts = {}
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            if adj.get("verdict") in ("supported", "partial"):
                tier_counts[adj.get("tier", "none")] = tier_counts.get(adj.get("tier", "none"), 0) + 1
    print(f"{total} claim-citation pairs: "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if tier_counts:
        print("evidence tier of supported/partial verdicts: "
              + ", ".join(f"{k}={v}" for k, v in sorted(tier_counts.items())))
    for d in downgrades:
        print("  ! " + d)

    if getattr(args, "summary", None):
        summary = claim_receipts.summarize_audit(audit)
        atomic_write_json(args.summary, summary)
        print(f"summary -> {args.summary}: {claim_receipts.summary_sentence(summary)}")

    if args.appendix:
        lines = ["# Claim verification appendix", "",
                 f"Review: {audit['review']}  ·  checked {time.strftime('%Y-%m-%d')}", ""]
        for c in audit["claims"]:
            for adj in c["adjudications"]:
                lines.append(f"**{c['id']}** ({c['location']}; evidence: {adj.get('tier')}) "
                             f"— **{adj.get('verdict')}**")
                lines.append(f"> {c['claim']}")
                if quotes_of(adj):
                    for q in quotes_of(adj):
                        lines.append(f"- source `{adj['doi']}`: “{q}”")
                else:
                    lines.append(f"- source `{adj['doi']}`"
                                 + (f": {adj['note']}" if adj.get("note") else ""))
                lines.append("")
        atomic_write_text(args.appendix, "\n".join(lines))
        print(f"appendix -> {args.appendix}")

    pending = counts.get("pending", 0)
    if judgment_errors:
        for item in judgment_errors:
            print("  ! " + item)
        print("HARD FAIL: verdicts were not adjudicated pair by pair — "
              "read each packet and use `adjudicate`.")
        sys.exit(1)
    if hard_fail:
        print("HARD FAIL: at least one claim is contradicted by its source.")
        sys.exit(1)
    if pending and args.strict:
        print(f"{pending} pairs still pending — strict mode fails.")
        sys.exit(1)


TEMPLATED_NOTE_LIMIT = 3
_RELEVANCE_STOP = _STOP | set("""study studies found reported results result effect effects
evidence review reviews trial trials patients participants people data analysis
significant significantly however although whether within across between
they them their theirs there these those this that than then thus such some
same also only ever even more most much many less least very just still well
what when where which while whom whose will would could should might must
have having been being were does done each every other others another both
either neither into onto over under upon with without through during before
after since until again further here rather quite often usually sometimes
already because therefore whereas among along around about above below
against toward towards including included include based using used uses
show shows shown showed suggest suggests suggested indicate indicates
indicated associated association associations compared comparison
observed observation observational measured measure measures measurement
authors author paper article research researchers current recent""".split())


def _content_terms(text):
    """Crude stems of the content words a quote must share with its claim."""
    text = DOI_LINK_RE.sub(" ", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    terms = set()
    for token in re.findall(r"[A-Za-z][A-Za-z-]{2,}", text):
        low = token.lower()
        if len(token) < 4 and not token.isupper():
            continue  # short words are noise; short all-caps abbreviations (BDS, LDL) are not
        if low not in _RELEVANCE_STOP:
            terms.add(low[:5])
    for number in re.findall(r"\d+(?:[.,]\d+)*%?", text):
        bare = number.replace(",", "").rstrip("%")
        if not re.fullmatch(r"(?:19|20)\d\d", bare):
            terms.add("#" + bare)
    return terms


def bridge_connects(bridge, quote, claim):
    """A bridge states the paraphrase in the judge's words ("appetite =
    hunger"); it must name at least one content term from the quote and one
    from the claim, so it is about this pair and not a formula."""
    terms = _content_terms(spell_to_digits(bridge))
    return bool(terms & _content_terms(spell_to_digits(quote))) and \
        bool(terms & _content_terms(claim))


def quote_relates_to_claim(quote, claim):
    """A supporting quote shares at least one content term or number with the
    claim. This is the checker's floor for "unrelated": it cannot judge
    meaning, but a passage about informed consent cannot support a sentence
    about weight regain, and that much is decidable."""
    return bool(_content_terms(spell_to_digits(quote)) & _content_terms(claim))


def judgment_problems(audit):
    """Signs that verdicts were generated rather than judged.

    A `partial` must say what the quote does not cover, and a note that is
    copied onto several pairs is a template, not a judgment. Both are hard
    failures: the fix is to read the packets, not to edit the note.
    """
    problems = []
    notes = {}
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            note = " ".join((adj.get("note") or "").split())
            verdict = adj.get("verdict")
            if verdict == "partial" and not note:
                problems.append(
                    f"{c['id']}/{adj['doi']}: partial verdict without a note "
                    "naming the element the quote does not cover")
            if note:
                notes.setdefault(note, []).append(f"{c['id']}/{adj['doi']}")
            bridge = " ".join((adj.get("bridge") or "").split())
            if bridge:
                notes.setdefault("bridge: " + bridge, []).append(f"{c['id']}/{adj['doi']}")
    for note, pairs in notes.items():
        if len(pairs) >= TEMPLATED_NOTE_LIMIT:
            problems.append(
                f"templated note on {len(pairs)} pairs ({pairs[0]}, {pairs[1]}, …): "
                f"“{note[:70]}” — notes must be specific to the pair")
    return problems


def cmd_adjudicate(args):
    """Record one judgment: one claim, one source, one verdict, its quote."""
    audit = json.loads(Path(args.audit).read_text())
    if args.verdict not in VERDICTS:
        sys.exit(f"verdict must be one of {sorted(VERDICTS)}")
    quotes = [q for q in (args.quote or []) if q.strip()]
    if args.verdict in FINAL_NEEDING_QUOTE and not quotes:
        sys.exit(f"a {args.verdict} verdict needs at least one --quote copied "
                 "verbatim from the packet")
    if args.verdict == "partial" and not (args.note or "").strip():
        sys.exit("a partial verdict needs a --note naming what the quote does not cover")
    packet = getattr(args, "packet", None)
    if packet:
        match = re.fullmatch(r"(C\d+)#(\d+)", packet)
        if not match:
            sys.exit("--packet looks like C007#2")
        claim_id, position = match.group(1), int(match.group(2))
        for c in audit["claims"]:
            if c["id"] == claim_id and 1 <= position <= len(c["adjudications"]):
                args.claim = claim_id
                args.doi = c["adjudications"][position - 1]["doi"]
                break
        else:
            sys.exit(f"no packet {packet} in the audit")
    if not (args.claim and args.doi):
        sys.exit("give --packet C007#2, or --claim and --doi")
    target = claim_evidence.norm_doi(args.doi)
    for c in audit["claims"]:
        if c["id"] != args.claim:
            continue
        for adj in c["adjudications"]:
            if claim_evidence.norm_doi(adj["doi"]) == target:
                adj["verdict"] = args.verdict
                adj["quote"] = quotes if len(quotes) > 1 else (quotes[0] if quotes else "")
                adj["note"] = (args.note or "").strip()
                covers = getattr(args, "covers", None)
                if covers is not None:
                    adj["covers"] = covers
                else:
                    adj.pop("covers", None)
                bridge = (getattr(args, "bridge", None) or "").strip()
                if bridge:
                    adj["bridge"] = bridge
                else:
                    adj.pop("bridge", None)
                atomic_write_json(args.audit, audit)
                pending = sum(1 for cc in audit["claims"] for a in cc["adjudications"]
                              if a.get("verdict", "pending") == "pending")
                print(f"{c['id']}/{target}: {args.verdict} — {pending} pair(s) still pending")
                return
        sys.exit(f"{args.claim} does not cite {target}")
    sys.exit(f"no claim {args.claim} in the audit")


def cmd_receipts(args):
    """Write the receipts file and stamp the review with the tally.

    Refuses an unfinished audit: only supported and partial pairs are
    receipts — run `check` first and repair the review."""
    audit = json.loads(Path(args.audit).read_text())
    summary = claim_receipts.summarize_audit(audit)
    blockers = claim_receipts.release_blockers(summary)
    if blockers:
        for item in blockers:
            print("  ! " + item)
        print("receipts not written — finish the audit and repair the review first.")
        sys.exit(1)
    review = Path(args.review)
    markdown = review.read_text(encoding="utf-8")
    audit_contract.validate_release(audit, markdown, args.audit)
    out = Path(args.out) if args.out else review.with_name(review.stem + "-receipts.md")
    document = claim_receipts.render_receipts_document(
        audit, claim_receipts.labels_from_markdown(markdown),
        title=claim_receipts.review_title(markdown), review_name=review.name)
    atomic_write_text(out, document)
    stamped = claim_receipts.attach_receipts(markdown, audit, receipts_name=out.name)
    atomic_write_text(review, stamped)
    print(f"receipts -> {out} ({summary['pairs']} pairs); "
          f"{review.name} stamped: {claim_receipts.summary_sentence(summary)}")


def cmd_classify(args):
    audit = json.loads(Path(args.audit).read_text())
    claim = next((c for c in audit["claims"] if c["id"] == args.claim), None)
    if claim is None:
        sys.exit("unknown assertion " + args.claim)
    if claim["dois"] and args.classification != "factual":
        sys.exit("cited assertions must be assessed as factual")
    if not args.note.strip():
        sys.exit("classification requires an independent reason")
    claim.update(classification=args.classification, classification_note=args.note,
                 basis=args.basis or [])
    audit.pop("checked_sha256", None)
    atomic_write_json(args.audit, audit)


def cmd_elements(args):
    audit = json.loads(Path(args.audit).read_text())
    claim = next((c for c in audit["claims"] if c["id"] == args.claim), None)
    if claim is None:
        sys.exit("unknown assertion " + args.claim)
    claim["elements"] = [{"id": f"E{i}", "text": text}
                         for i, text in enumerate(args.element, 1)]
    problem = audit_contract.elements_problem(claim)
    if problem:
        sys.exit(problem)
    for adj in claim["adjudications"]:
        adj.update(verdict="pending", quote="", note="")
        adj.pop("covers", None)
    audit.pop("checked_sha256", None)
    atomic_write_json(args.audit, audit)


def cmd_seed(args):
    """Seed the store for every verified ledger DOI from the review's own reading."""
    ledger = json.loads(Path(args.ledger).read_text())
    dois = [claim_evidence.norm_doi(e["doi"]) for e in ledger.get("entries", [])
            if e.get("doi") and e.get("status", "verified") == "verified"]
    seeded = claim_evidence.seed_local_evidence(
        dois, args.evidence, ledger_path=args.ledger,
        fulltext_dir=args.fulltext_dir, manifest_path=args.fulltext_manifest)
    counts = {}
    for tier in seeded.values():
        counts[tier] = counts.get(tier, 0) + 1
    missing = [d for d in dois if claim_evidence.load_evidence(d, args.evidence)[1] is None]
    print(f"{len(dois)} verified DOIs; seeded "
          + (", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nothing")
          + f"; {len(missing)} without any stored text"
          + (" (fetch them, or they cannot be quoted)" if missing else ""))
    for d in missing[:10]:
        print("  - " + d)


def cmd_synthesis_check(args):
    text = Path(args.synthesis).read_text(encoding="utf-8")
    ledger = json.loads(Path(args.ledger).read_text())
    result = synthesis_quotes.check_synthesis(text, args.evidence, ledger)
    assessment_path = Path(getattr(args, "assessment", None) or
                           Path(args.synthesis).with_name("evidence-assessment.json"))
    assessed = evidence_assessment.assess(json.loads(assessment_path.read_text()), ledger, text)
    result["errors"].extend(assessed["errors"])
    result["warnings"].extend(assessed["warnings"])
    result["status"] = "fail" if result["errors"] else "pass"
    if args.report:
        atomic_write_json(args.report, result)
    m = result["metrics"]
    print(f"{m['claims']} claims, {m['quoted_pairs']} verbatim quotes over "
          f"{m['keys_quoted']} keys (full text {m['keys_by_tier']['fulltext']}, "
          f"abstract {m['keys_by_tier']['abstract']})")
    for item in result["warnings"]:
        print("  ~ " + item)
    for item in result["errors"]:
        print("  ! " + item)
    if result["errors"]:
        print("HARD FAIL: the synthesis is not quote-anchored — no drafting until it is.")
        sys.exit(1)


def cmd_score(args):
    """Score a candidate audit against a gold-labeled audit (same review).

    Pairs are matched on (claim id, doi). Reports verdict agreement, the
    confusion between gold and candidate verdicts, and coverage of the gold
    set. Use this to measure a judge before trusting it at scale."""
    candidate = json.loads(Path(args.audit).read_text())
    gold = json.loads(Path(args.gold).read_text())

    def pairs(doc):
        return {(c["id"], a["doi"]): a.get("verdict", "pending")
                for c in doc["claims"] for a in c["adjudications"]}

    gold_pairs = pairs(gold)
    cand_pairs = pairs(candidate)
    matched = sorted(set(gold_pairs) & set(cand_pairs))
    if not matched:
        print("no overlapping (claim id, doi) pairs between audit and gold")
        sys.exit(1)
    agree = sum(1 for k in matched if gold_pairs[k] == cand_pairs[k])
    confusion = {}
    for k in matched:
        if gold_pairs[k] != cand_pairs[k]:
            key = f"gold={gold_pairs[k]} candidate={cand_pairs[k]}"
            confusion.setdefault(key, []).append(k)
    print(f"pairs matched: {len(matched)}/{len(gold_pairs)} of gold "
          f"({len(cand_pairs)} in candidate)")
    print(f"verdict agreement: {agree}/{len(matched)} "
          f"({100.0 * agree / len(matched):.1f}%)")
    for key, ks in sorted(confusion.items()):
        print(f"  {key}: {len(ks)}  e.g. {ks[0][0]}/{ks[0][1]}")
    missing = sorted(set(gold_pairs) - set(cand_pairs))
    if missing:
        print(f"gold pairs absent from candidate: {len(missing)} "
              f"(first: {missing[0][0]}/{missing[0][1]})")
    extra = sorted(set(cand_pairs) - set(gold_pairs))
    negatives = [k for k in gold_pairs if gold_pairs[k] != "supported"]
    false_accepts = [k for k in negatives if cand_pairs.get(k) == "supported"]
    false_acceptance = 100.0 * len(false_accepts) / len(negatives) if negatives else 0.0
    report = {
        "coverage": len(matched) / len(gold_pairs),
        "agreement": 100.0 * agree / len(matched),
        "false_acceptance_percent": false_acceptance,
        "missing_pairs": missing, "extra_pairs": extra,
        "gold_sha256": audit_contract.digest(gold),
        "candidate_sha256": audit_contract.digest(candidate),
        "confusion": {key: len(value) for key, value in confusion.items()},
    }
    print(f"false acceptance: {len(false_accepts)}/{len(negatives)} ({false_acceptance:.1f}%)")
    failures = []
    gold_claims = {c["id"]: c["claim"] for c in gold["claims"] if "claim" in c}
    if any(c.get("claim") != gold_claims[c["id"]] for c in candidate["claims"] if c["id"] in gold_claims):
        failures.append("candidate assertion text differs from the benchmark")
    if missing or extra or len(cand_pairs) != sum(len(c["adjudications"]) for c in candidate["claims"]):
        failures.append("qualification requires every gold pair exactly once and no extra pairs")
    if getattr(args, "qualify", False) and not VERDICTS <= set(gold_pairs.values()):
        failures.append("qualification benchmark must exercise all five verdicts")
    if getattr(args, "qualify", False):
        input_path = Path(getattr(args, "benchmark_input", None) or
                          Path(args.gold).with_name("judge-benchmark-input.json"))
        inputs = json.loads(input_path.read_text())
        report["input_sha256"] = audit_contract.digest(inputs)
        passages = {c["id"]: " … ".join(c["passages"]) for c in inputs["claims"]}
        for c in candidate["claims"]:
            for adj in c["adjudications"]:
                if adj.get("verdict") in FINAL_NEEDING_QUOTE:
                    quotes = quotes_of(adj)
                    if not quotes or any(not claim_evidence.quote_in_text(q, passages.get(c["id"], "")) for q in quotes):
                        failures.append(c["id"] + ": qualification quotation is absent from the supplied passage")
        failures.extend(judgment_problems(candidate))
    if false_acceptance > getattr(args, "max_false_acceptance", 0):
        failures.append("false acceptance exceeds configured maximum")
    minimum_agreement = args.min_agreement
    if minimum_agreement is None and getattr(args, "qualify", False):
        minimum_agreement = 80
    report["minimum_agreement"] = minimum_agreement
    if minimum_agreement is not None:
        rate = 100.0 * agree / len(matched)
        if rate < minimum_agreement:
            print(f"FAIL: agreement {rate:.1f}% below required {minimum_agreement}%")
            failures.append("agreement below threshold")
    report["status"] = "fail" if failures else "pass"
    report["errors"] = failures
    if getattr(args, "report", None):
        atomic_write_json(args.report, report)
    if failures:
        sys.exit("; ".join(failures))


def cmd_benchmark_packets(args):
    document = json.loads(Path(args.input).read_text())
    # Only the unlabelled fixture is read. Never load the gold answers here.
    candidate = {"claims": []}
    for c in document["claims"]:
        candidate["claims"].append({"id": c["id"], "claim": c["claim"], "dois": c["dois"],
                                     "adjudications": [{"doi": d, "verdict": "pending", "quote": "", "note": ""}
                                                        for d in c["dois"]]})
        print(f"{c['id']}#1: {c['claim']}")
        for passage in c["passages"]:
            print("  Passage: " + passage)
        if not c["passages"]:
            print("  No source text available.")
    atomic_write_json(args.audit, candidate)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("benchmark-packets")
    p.add_argument("--input", required=True, help="unlabelled judge-benchmark-input.json only")
    p.add_argument("--audit", required=True)
    p.set_defaults(fn=cmd_benchmark_packets)

    p = sub.add_parser("seed")
    p.add_argument("--ledger", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--fulltext-dir")
    p.add_argument("--fulltext-manifest")
    p.set_defaults(fn=cmd_seed)

    p = sub.add_parser("synthesis-check")
    p.add_argument("--synthesis", required=True)
    p.add_argument("--assessment", help="defaults to evidence-assessment.json beside synthesis")
    p.add_argument("--ledger", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--report")
    p.set_defaults(fn=cmd_synthesis_check)

    p = sub.add_parser("extract")
    p.add_argument("--review", required=True)
    p.add_argument("--ledger")
    p.add_argument("--synthesis", help="synthesis.md; every cited source must carry a quote there")
    p.add_argument("--assessment", help="outcome certainty and study families, required for reviews")
    p.add_argument("--audit", required=True)
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("fetch")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--fulltext-all", action="store_true")
    p.add_argument("--sleep", type=float, default=0.3)
    p.add_argument("--ledger", help="sources.json; seeds abstracts and maps keys to DOIs")
    p.add_argument("--fulltext-dir", help="the review's fulltexts/ directory; seeds full text already read")
    p.add_argument("--fulltext-manifest", help="fulltext-manifest.json; only valid_fulltext records are trusted")
    p.add_argument("--offline", action="store_true",
                   help="use only the seeded store; never call the network")
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("adjudicate")
    p.add_argument("--audit", required=True)
    p.add_argument("--packet", help="blind packet id, e.g. C007#2")
    p.add_argument("--claim", help="claim id, e.g. C007")
    p.add_argument("--doi")
    p.add_argument("--verdict", required=True, choices=sorted(VERDICTS))
    p.add_argument("--quote", action="append", help="verbatim passage; repeat for several")
    p.add_argument("--note", help="required for partial: the element the quote does not cover")
    p.add_argument("--bridge", help="when the quote paraphrases the claim with no shared "
                                    "word: the equivalence, e.g. 'appetite = hunger'")
    p.add_argument("--covers", action="append", help="fully supported element ID; repeat, e.g. E1")
    p.set_defaults(fn=cmd_adjudicate)

    p = sub.add_parser("classify")
    p.add_argument("--audit", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--classification", choices=("factual", "interpretation", "nonfactual"), required=True)
    p.add_argument("--note", required=True)
    p.add_argument("--basis", action="append", help="factual assertion ID underpinning an interpretation")
    p.set_defaults(fn=cmd_classify)

    p = sub.add_parser("elements")
    p.add_argument("--audit", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--element", action="append", required=True,
                   help="verbatim consecutive clause; repeat to partition the whole assertion")
    p.set_defaults(fn=cmd_elements)

    p = sub.add_parser("packets")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--pending-only", action="store_true")
    p.add_argument("--claim")
    p.add_argument("--blind", action="store_true",
                   help="packets for an independent judge: sentence and passages only")
    p.set_defaults(fn=cmd_packets)

    p = sub.add_parser("check")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--appendix")
    p.add_argument("--summary", help="write the verdict/tier counts the colophon prints")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("receipts")
    p.add_argument("--audit", required=True)
    p.add_argument("--review", required=True, help="finished review markdown (stamped in place)")
    p.add_argument("--out", help="receipts markdown path (default <review>-receipts.md)")
    p.set_defaults(fn=cmd_receipts)

    p = sub.add_parser("score")
    p.add_argument("--audit", required=True, help="candidate audit to evaluate")
    p.add_argument("--gold", required=True, help="gold-labeled audit, e.g. evals/claim-benchmark-creatine.json")
    p.add_argument("--min-agreement", type=float, help="fail below this agreement percentage")
    p.add_argument("--max-false-acceptance", type=float, default=0)
    p.add_argument("--qualify", action="store_true", help="require all five verdict classes in gold")
    p.add_argument("--benchmark-input", help="unlabelled fixture; defaults beside gold")
    p.add_argument("--report", help="write coverage, confusion, false acceptance and fixture hashes")
    p.set_defaults(fn=cmd_score)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
