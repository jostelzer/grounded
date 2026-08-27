#!/usr/bin/env python3
"""
Claim-level verification: check that every cited sentence says what its source says.

Bibliographic verification (verify_citations.py) proves a source exists; this tool
audits whether the sentence in front of each citation is supported by that source's
own text. It is deliberately split between deterministic machinery (this script)
and judgment (the agent):

  extract   parse the review into (claim sentence, cited DOI) pairs
  fetch     acquire evidence per DOI via claim_evidence.py — abstract tier for
            every source, full text for sources carrying numeric claims
  packets   print one adjudication packet per pending pair: the claim, the
            evidence tier, and candidate passages selected around the claim's
            numbers and rare terms. The agent reads packets and writes a verdict
            and a VERBATIM quote into the audit JSON.
  check     enforce the quote-or-abstain contract mechanically: a verdict of
            supported/partial/contradicted is kept only if its quote appears
            verbatim (after normalization) in the stored evidence, and a numeric
            claim marked supported must have at least one of its numbers inside
            the quote. Violations are downgraded, never silently accepted.
            Renders the audit appendix and prints coverage statistics.

Verdicts: supported | partial | not_found | contradicted | unverifiable.
The judge can be wrong, but it cannot invent evidence: quotes that do not occur
in the source are rejected here, in code.

Usage:
  python3 verify_claims.py extract --review review.md --audit claims_audit.json
  python3 verify_claims.py fetch   --audit claims_audit.json --evidence evidence/
  python3 verify_claims.py packets --audit claims_audit.json --evidence evidence/
  python3 verify_claims.py check   --audit claims_audit.json --evidence evidence/ \
                                   --appendix claims_appendix.md
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import claim_evidence
from artifact_io import atomic_write_json, atomic_write_text

VERDICTS = {"supported", "partial", "not_found", "contradicted", "unverifiable"}
FINAL_NEEDING_QUOTE = {"supported", "partial", "contradicted"}

_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
          "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_SPELLED = {w: i for i, w in enumerate(_UNITS)}
_SPELLED.update(_TENS)
for _t, _tv in _TENS.items():
    for _u in range(1, 10):
        _SPELLED[f"{_t}-{_UNITS[_u]}"] = _tv + _u


def spell_to_digits(text):
    """Rewrite spelled-out numbers (\"twenty-two\") as digits so a quote like
    \"Twenty-two subjects\" satisfies the numeric anchor \"22\"."""
    pattern = re.compile(
        r"\b(" + "|".join(sorted(_SPELLED, key=len, reverse=True)) + r")\b", re.I)
    return pattern.sub(lambda m: str(_SPELLED[m.group(1).lower()]), text or "")


def quotes_of(adj):
    """An adjudication's quote may be one string or a list of strings."""
    quote = adj.get("quote", "")
    if isinstance(quote, str):
        return [quote] if quote else []
    return [q for q in quote if q]

DOI_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https?://(?:dx\.)?doi\.org/(?:[^\s()]|\([^\s()]*\)|%28|%29)+)\)",
    re.IGNORECASE,
)
# Words a sentence splitter must not break after.
_ABBREV = ("et al", "e.g", "i.e", "vs", "cf", "ca", "approx", "Fig", "fig",
           "No", "no", "Dr", "St", "resp")


def _protect(text):
    for a in _ABBREV:
        text = text.replace(a + ".", a + "\u2024")
    text = re.sub(r"(\d)\.(\d)", "\\1\u2024\\2", text)
    return text


def _unprotect(text):
    return text.replace("\u2024", ".")


def split_sentences(paragraph):
    protected = _protect(paragraph)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(\[])", protected)
    return [_unprotect(p).strip() for p in parts if p.strip()]


def claim_numbers(text):
    """Numeric anchors of a claim: numbers that are not years or citation labels."""
    cleaned = DOI_LINK_RE.sub(" ", text)
    numbers = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*%?", cleaned):
        token = m.group(0).replace(",", "")
        bare = token.rstrip("%")
        if re.fullmatch(r"(?:19|20)\d\d", bare):
            continue
        if token not in numbers:
            numbers.append(token)
    return numbers


def _strip_citations(sentence):
    text = DOI_LINK_RE.sub("", sentence)
    text = re.sub(r"\[@[^\]]+\]", "", text)
    text = re.sub(r"\(\s*(?:[,;]\s*)*\)", "", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _pairs_from_text(text_block, location, key_to_doi):
    dois = [claim_evidence.norm_doi(m.group(2)) for m in DOI_LINK_RE.finditer(text_block)]
    for m in re.finditer(r"\[@([^\]\s;]+)(?:;\s*@[^\]]+)*\]", text_block):
        for key in re.findall(r"@([^\s;\]]+)", m.group(0)):
            doi = key_to_doi.get(key)
            if doi:
                dois.append(claim_evidence.norm_doi(doi))
    seen, ordered = set(), []
    for d in dois:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    if not ordered:
        return None
    return {
        "claim": _strip_citations(text_block),
        "location": location,
        "dois": ordered,
        "numbers": claim_numbers(text_block),
    }


def extract_claims(markdown, key_to_doi=None):
    key_to_doi = key_to_doi or {}
    body = re.split(r"(?mi)^(?:\*\*Sources\*\*|#{1,4}\s*Sources)\s*$", markdown)[0]
    claims = []
    para_no = 0
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block or block.startswith("#") or block.startswith("!["):
            continue
        if block.lstrip().startswith("|"):
            rows = [r for r in block.splitlines() if r.strip().startswith("|")]
            for i, row in enumerate(rows):
                if re.fullmatch(r"[|\s:\-]+", row):
                    continue
                pair = _pairs_from_text(row, f"table row {i}", key_to_doi)
                if pair:
                    claims.append(pair)
            continue
        para_no += 1
        for j, sentence in enumerate(split_sentences(block), 1):
            pair = _pairs_from_text(sentence, f"paragraph {para_no}, sentence {j}", key_to_doi)
            if pair:
                claims.append(pair)
    for i, c in enumerate(claims, 1):
        c["id"] = f"C{i:03d}"
        c["adjudications"] = [
            {"doi": d, "verdict": "pending", "quote": "", "note": ""} for d in c["dois"]
        ]
    return claims


# ------------------------------------------------------------------ passages --

_STOP = set("""the a an and or of in on for with without to from by as is are was were
be been being that this those these it its their there than then into over under about
during between among after before which while whereas although though because""".split())


def candidate_passages(claim, numbers, evidence_text, max_windows=6, radius=320):
    """Deterministic passage selection: windows around the claim's numbers and
    rare words, ranked by how many distinct claim tokens they contain."""
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

    def score(span):
        window = lower[span[0]:span[1]]
        return sum(1 for t in claim_tokens if t in window)

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
    if args.ledger:
        ledger = json.loads(Path(args.ledger).read_text())
        key_to_doi = {e["key"]: e.get("doi") for e in ledger["entries"] if e.get("doi")}
    claims = extract_claims(markdown, key_to_doi)
    audit = {
        "review": str(args.review),
        "created": time.strftime("%Y-%m-%d"),
        "claims": claims,
    }
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
    tiers = {}
    for doi in dois:
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
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            if args.pending_only and adj["verdict"] != "pending":
                continue
            if args.claim and c["id"] != args.claim:
                continue
            text, meta = claim_evidence.load_evidence(adj["doi"], args.evidence)
            print(f"### {c['id']} :: {adj['doi']} "
                  f"[tier: {(meta or {}).get('tier', 'MISSING')}] ({c['location']})")
            print(f"CLAIM: {c['claim']}")
            if c["numbers"]:
                print(f"NUMERIC ANCHORS: {', '.join(c['numbers'])}")
            for i, passage in enumerate(candidate_passages(
                    c["claim"], c["numbers"], text or ""), 1):
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
                elif verdict == "supported" and c["numbers"]:
                    quote_flat = spell_to_digits(" … ".join(quotes)).replace(",", "")
                    if not any(n.rstrip("%") in quote_flat for n in c["numbers"]):
                        downgrades.append(
                            f"{c['id']}/{adj['doi']}: numeric claim but no claim number "
                            f"in quote — downgraded supported -> partial")
                        verdict = adj["verdict"] = "partial"
                        adj["note"] = (adj.get("note", "") + " [numeric anchor missing]").strip()
            if verdict == "contradicted":
                hard_fail = True
            counts[verdict] = counts.get(verdict, 0) + 1
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
    if hard_fail:
        print("HARD FAIL: at least one claim is contradicted by its source.")
        sys.exit(1)
    if pending and args.strict:
        print(f"{pending} pairs still pending — strict mode fails.")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract")
    p.add_argument("--review", required=True)
    p.add_argument("--ledger")
    p.add_argument("--audit", required=True)
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("fetch")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--fulltext-all", action="store_true")
    p.add_argument("--sleep", type=float, default=0.3)
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("packets")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--pending-only", action="store_true")
    p.add_argument("--claim")
    p.set_defaults(fn=cmd_packets)

    p = sub.add_parser("check")
    p.add_argument("--audit", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--appendix")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(fn=cmd_check)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
