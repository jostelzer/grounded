#!/usr/bin/env python3
"""
Claim receipts: the reader-facing rendering of a claim audit.

`verify_claims.py` produces `claims_audit.json` — one verdict and verbatim
quote per (cited sentence, source) pair. This module turns that audit into what
the reader actually sees:

  * a summary (`summarize_audit`) — the numbers the colophon prints;
  * a standalone receipts Markdown file, one entry per cited sentence
    (`render_receipts_document`);
  * the stamp on the review itself — a per-source annotation on each Sources
    entry and a two-line `**Receipts**` block carrying the tally and the file
    name (`attach_receipts`);
  * helpers the validator and exporter use to strip that block again
    (`strip_receipts`) so it never counts as review prose.

Pure text processing, no network, no ledger required: labels come from the
review's own author–year links, so the receipt names a source exactly as the
text does.
"""
import re
import urllib.parse
import audit_contract

RECEIPTS_HEADING = "**Receipts**"
RECEIPTS_BLOCK_RE = re.compile(r"(?ms)^\*\*Receipts\*\*\s*$.*\Z")
SOURCES_HEADING_RE = re.compile(r"(?m)^\*\*Sources\*\*\s*$")
DOI_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https?://(?:dx\.)?doi\.org/(?:[^\s()]|\([^\s()]*\)|%28|%29)+)\)",
    re.IGNORECASE,
)
DOI_URL_RE = re.compile(r"https?://(?:dx\.)?doi\.org/([^\s<>]+)", re.IGNORECASE)
SOURCE_ENTRY_RE = re.compile(r"^\*\*(?P<names>.+?)\s\((?P<year>\d{4}[a-z]?|n\.d\.)\)\*\*")
ANNOTATION_RE = re.compile(
    r"\s·\s\d+\s(?:claim|claims)\s·\s(?:full text|abstract|no text)\s*$")
RECEIPT_LINE_RE = re.compile(r"^- (?P<id>C\d{3,}) · ")

TIER_LABELS = {"fulltext": "full text", "abstract": "abstract", "none": "no text"}
TIER_RANK = {"fulltext": 2, "abstract": 1, "none": 0}
VERDICT_ORDER = ("supported", "partial", "not_found", "unverifiable",
                 "contradicted", "pending")
SNIPPET_CHARS = 90


def norm_doi(doi):
    doi = urllib.parse.unquote((doi or "").strip().lower())
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi).rstrip(".,;*_)")


def tier_label(tier):
    return TIER_LABELS.get(tier or "none", "no text")


# ------------------------------------------------------------------ summary --

def summarize_audit(audit):
    """Count the audit the way the colophon reports it."""
    claims = audit.get("claims", [])
    counts = {verdict: 0 for verdict in VERDICT_ORDER}
    supported_fulltext = supported_abstract = 0
    source_tier = {}
    pairs = 0
    for claim in claims:
        for adj in claim.get("adjudications", []):
            pairs += 1
            verdict = adj.get("verdict") or "pending"
            counts[verdict] = counts.get(verdict, 0) + 1
            tier = adj.get("tier") or "none"
            if verdict == "supported":
                if tier == "fulltext":
                    supported_fulltext += 1
                else:
                    supported_abstract += 1
            doi = norm_doi(adj.get("doi"))
            if TIER_RANK.get(tier, 0) >= TIER_RANK.get(source_tier.get(doi, "none"), 0):
                source_tier[doi] = tier
    by_tier = {"fulltext": 0, "abstract": 0, "none": 0}
    for tier in source_tier.values():
        by_tier[tier if tier in by_tier else "none"] += 1
    return {
        "coverage_errors": audit_contract.coverage_errors(audit) if audit.get("schema_version") == 2 else [],
        "claims": sum(bool(c.get("dois", c.get("adjudications"))) for c in claims),
        "assertions": len(claims),
        "pairs": pairs,
        "supported": counts["supported"],
        "supported_fulltext": supported_fulltext,
        "supported_abstract": supported_abstract,
        "partial": counts["partial"],
        "not_found": counts["not_found"],
        "unverifiable": counts["unverifiable"],
        "contradicted": counts["contradicted"],
        "pending": counts["pending"],
        "sources": len(source_tier),
        "sources_fulltext": by_tier["fulltext"],
        "sources_abstract": by_tier["abstract"],
        "sources_no_text": by_tier["none"],
    }


def summary_sentence(summary):
    """The one line the colophon and the Receipts heading both print."""
    claims = summary["claims"]
    parts = [
        f"{claims} cited sentence{'s' if claims != 1 else ''}",
        f"{summary['pairs']} source check{'s' if summary['pairs'] != 1 else ''}",
        f"{summary['supported_fulltext']} supported at full text",
        f"{summary['supported_abstract']} at abstract",
        f"{summary['partial']} partial",
    ]
    for key, label in (("not_found", "not found"),
                       ("unverifiable", "unverifiable"),
                       ("pending", "pending")):
        if summary[key]:
            parts.append(f"{summary[key]} {label}")
    parts.append(f"{summary['contradicted']} contradicted")
    return " · ".join(parts)


def release_blockers(summary):
    """Why an audit cannot ship.

    Schema-v2 receipts require complete element coverage. Partial source
    support is allowed only when other evidence covers the remaining elements. A contradicted pair is
    a false sentence; a pending pair is unfinished work; a not_found or
    unverifiable pair is a decorative citation — a real paper attached to a
    sentence its text does not back — and the promise is that none ships.
    The repair is in the review: drop or move the citation, or rewrite the
    sentence to what the source says, then re-audit.
    """
    problems = []
    problems.extend(summary.get("coverage_errors", []))
    if summary["contradicted"]:
        problems.append(f"{summary['contradicted']} claim(s) contradicted by their source")
    if summary["pending"]:
        problems.append(f"{summary['pending']} claim-source pair(s) still pending adjudication")
    if summary["not_found"]:
        problems.append(
            f"{summary['not_found']} citation(s) whose source text does not address "
            "the sentence (not_found) — remove, relocate, or rewrite")
    if summary["unverifiable"]:
        problems.append(
            f"{summary['unverifiable']} citation(s) with no usable evidence or a "
            "rejected quote (unverifiable) — obtain the text or remove the citation")
    return problems


# ------------------------------------------------------------------- labels --

def _label_from_entry(line):
    match = SOURCE_ENTRY_RE.match(line.strip())
    if not match:
        return None
    names = [name.strip() for name in match.group("names").split(",") if name.strip()]
    year = match.group("year")

    def family(name):
        tokens = name.split()
        if len(tokens) >= 2 and re.fullmatch(r"[A-ZÀ-Ý][A-ZÀ-Ýa-zà-ÿ.-]*", tokens[-1]):
            return " ".join(tokens[:-1])
        return name

    if not names:
        return f"Anon. {year}"
    if len(names) == 1:
        return f"{family(names[0])} {year}"
    if len(names) == 2:
        return f"{family(names[0])} & {family(names[1])} {year}"
    return f"{family(names[0])} et al. {year}"


def labels_from_markdown(markdown):
    """DOI → the author–year label the review itself uses for that source.

    Body links come first so the receipt says exactly what the text says; a
    Sources entry is the fallback for a DOI cited only where the link text
    is not a label.
    """
    labels = {}
    body, sources = _split_sources(markdown)
    for match in DOI_LINK_RE.finditer(body):
        doi = norm_doi(match.group(2))
        labels.setdefault(doi, match.group(1).strip())
    for line in sources.splitlines():
        url = DOI_URL_RE.search(line)
        if not url:
            continue
        doi = norm_doi(url.group(1))
        label = _label_from_entry(line)
        if label and doi not in labels:
            labels[doi] = label
    return labels


# ----------------------------------------------------------------- receipts --

def compact_location(location):
    match = re.match(r"paragraph (\d+), sentence (\d+)", location or "")
    if match:
        return f"¶{match.group(1)} s{match.group(2)}"
    match = re.match(r"table row (\d+)", location or "")
    if match:
        return f"table r{match.group(1)}"
    match = re.match(r"figure (\d+) caption", location or "")
    if match:
        return f"fig {match.group(1)}"
    return location or "—"


def plain_text(text):
    """Strip the review's Markdown from a claim so the receipt reads as prose:
    term links become their text, emphasis marks go, table cells join."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\{\{figure:[^}]+\}\}", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)", "", text)
    if text.lstrip().startswith("|"):
        cells = [cell.strip() for cell in text.strip().strip("|").split("|")]
        text = " · ".join(cell for cell in cells if cell)
    return " ".join(text.split())


def snippet(text, limit=SNIPPET_CHARS):
    text = plain_text(text)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def quotes_of(adj):
    quote = adj.get("quote", "")
    if isinstance(quote, str):
        return [quote] if quote else []
    return [q for q in quote if q]


def verdict_phrase(adj):
    verdict = adj.get("verdict") or "pending"
    quotes = quotes_of(adj)
    note = " ".join((adj.get("note") or "").split())
    if verdict in ("supported", "partial", "contradicted") and quotes:
        text = f"{verdict} — " + " … ".join(f"“{q}”" for q in quotes)
        bridge = " ".join((adj.get("bridge") or "").split())
        if bridge:
            text += f" (bridge: {bridge})"
        if verdict == "partial" and note:
            text += f" ({note})"
        return text
    if verdict == "not_found":
        return f"not found in {tier_label(adj.get('tier'))}"
    if note:
        return f"{verdict} ({note})"
    return verdict


def receipt_entries(audit, labels=None):
    """One structured receipt per (claim, source) pair, in review order."""
    labels = labels or {}
    entries = []
    for claim in audit.get("claims", []):
        for adj in claim.get("adjudications", []):
            doi = norm_doi(adj.get("doi"))
            entries.append({
                "id": claim.get("id"),
                "location": compact_location(claim.get("location")),
                "snippet": snippet(claim.get("claim")),
                "doi": doi,
                "label": labels.get(doi) or doi,
                "tier": adj.get("tier") or "none",
                "verdict": adj.get("verdict") or "pending",
                "phrase": verdict_phrase(adj),
            })
    return entries


def receipt_line(entry):
    return (f"- {entry['id']} · {entry['location']} · “{entry['snippet']}” · "
            f"{entry['label']} · {tier_label(entry['tier'])} · {entry['phrase']}")


def render_receipts_markdown(audit, labels=None):
    """The flat one-line-per-pair form (used for draft checks in chat)."""
    summary = summarize_audit(audit)
    lines = [RECEIPTS_HEADING, "", f"*{summary_sentence(summary)}.*", ""]
    lines.extend(receipt_line(entry) for entry in receipt_entries(audit, labels))
    return "\n".join(lines) + "\n"


def review_title(markdown):
    match = re.search(r"^##\s+(.+)$", markdown, re.M)
    return match.group(1).strip() if match else "review"


def render_receipts_document(audit, labels=None, title="review", review_name="review.md"):
    """The receipts file: every cited sentence, then its sources and quotes."""
    summary = summarize_audit(audit)
    lines = [
        f"# Claim receipts — {title}", "",
        f"*{summary_sentence(summary)}.*", "",
        f"Every cited sentence of `{review_name}`, paired with the passage in its "
        "source that the checker matched verbatim. *Full text* means the passage "
        "came from the version-of-record text; *abstract* means only the abstract "
        "was available. A *bridge* states the paraphrase when the sentence and "
        "the passage share no word.", "",
    ]
    current = None
    for entry in receipt_entries(audit, labels):
        if entry["id"] != current:
            current = entry["id"]
            claim = next(c for c in audit["claims"] if c.get("id") == current)
            lines += [f"## {current} · {entry['location']}", "",
                      f"> {plain_text(claim.get('claim'))}", ""]
        lines.append(f"- **{entry['label']}** · {tier_label(entry['tier'])} · {entry['phrase']}")
        lines.append("")
    uncited = [c for c in audit["claims"] if not c.get("dois")]
    if uncited:
        lines += ["## Uncited inventory and interpretations", ""]
        for c in uncited:
            lines.append(f"- {c['id']} · {c.get('classification', 'pending')} · {plain_text(c['claim'])} — "
                         + c.get("classification_note", "")
                         + (" (basis: " + ", ".join(c["basis"]) + ")" if c.get("basis") else ""))
    assessment = audit.get("evidence_assessment")
    if assessment:
        lines += ["", "## Outcome certainty (separate from source support)", ""]
        for outcome in assessment["outcomes"]:
            lines.append(f"- {outcome['outcome']}: {outcome['certainty']} — {outcome['rationale']}")
    return "\n".join(lines)


def pointer_block(summary, receipts_name):
    return (f"{RECEIPTS_HEADING}\n\n*{summary_sentence(summary)} — every pair's "
            f"verbatim quote is in `{receipts_name}`.*\n")


def source_counts(audit):
    """DOI → (number of cited sentences, best evidence tier)."""
    counts = {}
    for claim in audit.get("claims", []):
        for adj in claim.get("adjudications", []):
            doi = norm_doi(adj.get("doi"))
            n, tier = counts.get(doi, (0, "none"))
            adj_tier = adj.get("tier") or "none"
            if TIER_RANK.get(adj_tier, 0) > TIER_RANK.get(tier, 0):
                tier = adj_tier
            counts[doi] = (n + 1, tier)
    return counts


def _split_sources(markdown):
    parts = SOURCES_HEADING_RE.split(markdown, maxsplit=1)
    if len(parts) != 2:
        return markdown, ""
    return parts[0], parts[1]


def strip_receipts(markdown):
    """Remove the Receipts block (the per-source annotations stay: they are
    part of each Sources entry and carry no DOI of their own)."""
    return RECEIPTS_BLOCK_RE.sub("", markdown).rstrip("\n") + "\n"


def strip_source_annotations(markdown):
    return "\n".join(ANNOTATION_RE.sub("", line) for line in markdown.split("\n"))


def annotate_sources(markdown, audit):
    counts = source_counts(audit)
    lines = markdown.split("\n")
    marker = next((i for i, line in enumerate(lines)
                   if SOURCES_HEADING_RE.match(line)), None)
    if marker is None:
        raise ValueError("review has no Sources block to annotate")
    for i in range(marker + 1, len(lines)):
        line = ANNOTATION_RE.sub("", lines[i])
        if RECEIPTS_HEADING in line:
            break
        url = DOI_URL_RE.search(line)
        if not url or not line.startswith("**"):
            lines[i] = line
            continue
        n, tier = counts.get(norm_doi(url.group(1)), (0, "none"))
        if n:
            line = f"{line.rstrip()} · {n} claim{'s' if n != 1 else ''} · {tier_label(tier)}"
        lines[i] = line
    return "\n".join(lines)


def attach_receipts(markdown, audit, receipts_name="review-receipts.md"):
    """Annotate Sources and append the two-line Receipts stamp; idempotent."""
    base = strip_receipts(markdown)
    base = annotate_sources(base, audit)
    return base.rstrip("\n") + "\n\n" + pointer_block(summarize_audit(audit), receipts_name)


def receipts_block(markdown):
    match = RECEIPTS_BLOCK_RE.search(markdown)
    return match.group(0) if match else ""


def count_receipt_lines(markdown):
    """Source checks recorded by the Receipts stamp (0 when unstamped)."""
    match = re.search(r"(\d+) source checks?", receipts_block(markdown))
    return int(match.group(1)) if match else 0


def receipt_errors(markdown):
    """Shape errors in the Receipts stamp: it must carry a clean tally."""
    block = receipts_block(markdown)
    if not block:
        return []
    errors = []
    if not re.search(r"\d+ source checks?", block):
        errors.append("Receipts block carries no audit tally")
    for label in ("pending", "contradicted", "not found", "unverifiable"):
        match = re.search(rf"(\d+) {label}", block)
        if match and int(match.group(1)) > 0:
            errors.append(
                f"Receipts tally records {match.group(1)} {label} pair(s); only "
                "supported and partial citations may ship")
    for line in block.splitlines():
        if RECEIPT_LINE_RE.match(line):
            errors.append("per-pair receipt lines belong in the receipts file, not the review")
            break
    return errors
