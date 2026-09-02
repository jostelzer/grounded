#!/usr/bin/env python3
"""
Check a draft you already have: do its references exist, and do they say that?

The front door for text Grounded did not write — an LLM answer, a manuscript
section, a press release, a student essay. No size, style, or format question:
the draft is the review, and the deliverable is a chat-ready report.

  ingest   parse the draft's citations in whatever form they arrive — DOI links,
           bare DOIs, numeric markers [3] with a reference list, author–year
           (Smith et al., 2020) with a reference list — resolve every reference
           to a DOI (Crossref bibliographic search when the draft gives none),
           and write a ledger (sources.json), a resolution record
           (resolution.json), and a normalized draft whose in-text citations are
           Grounded DOI links so the claim audit can read it.
  report   render the check: a scorecard, one line per reference (verified,
           retracted, not found, mismatched, unresolved), one line per cited
           sentence with its verdict and verbatim quote, and the list of
           citations that must be fixed.

Between the two, the ordinary chain runs on the normalized draft:
  verify_citations.py --ledger sources.json
  verify_claims.py extract / fetch / packets --blind / adjudicate / check

A reference no index can find is reported as exactly that; a real paper whose
text does not back the sentence is reported as a decorative citation. Nothing
is softened: this is a check, not a release, so every verdict is shown.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import claim_receipts
from artifact_io import atomic_write_json, atomic_write_text
from grounded_metadata import user_agent

UA = user_agent()
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>)\]]+", re.I)
DOI_URL_RE = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s\"'<>)\]]+)", re.I)
MD_DOI_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://(?:dx\.)?doi\.org/[^)\s]+)\)", re.I)
NUMERIC_RE = re.compile(r"\[(\d{1,3}(?:\s*[,–-]\s*\d{1,3})*)\]")
LETTERS = r"A-Za-zÀ-ÖØ-öø-ÿ"
SURNAME = rf"[A-ZÀ-ÖØ-Þ][{LETTERS}'’\-]+(?: [A-ZÀ-ÖØ-Þ][{LETTERS}'’\-]+)?"
AUTHOR_YEAR_PAREN_RE = re.compile(
    r"\(((?:" + SURNAME + r"(?: et al\.?| (?:&|and) " + SURNAME + r")?,? \d{4}[a-z]?)"
    r"(?:;\s*" + SURNAME + r"(?: et al\.?| (?:&|and) " + SURNAME + r")?,? \d{4}[a-z]?)*)\)")
AUTHOR_YEAR_NARRATIVE_RE = re.compile(
    r"\b(" + SURNAME + r"(?: et al\.?| (?:&|and) " + SURNAME + r")?) \((\d{4}[a-z]?)\)")
REF_HEADING_RE = re.compile(
    r"(?im)^(?:#{1,6}\s*|\*\*)?(references|sources|bibliography|works cited|literature cited)\s*:?(?:\*\*)?\s*$")
RESOLVED_MIN = 0.72
AMBIGUOUS_MIN = 0.45


# --------------------------------------------------------------- parsing --

def norm_doi(doi):
    return urllib.parse.unquote((doi or "").strip().lower()).rstrip(".,;)")


def split_reference_list(text):
    """(body, [reference strings]) — the list after a References-style heading."""
    match = REF_HEADING_RE.search(text)
    if not match:
        return text, []
    body, tail = text[:match.start()], text[match.end():]
    entries, current = [], []
    for line in tail.splitlines():
        stripped = line.strip()
        starts_new = bool(re.match(
            rf"^(?:\[\d+\]|\d+[.)]|\(\d+\)|\*\*[A-ZÀ-ÖØ-Þ]|[A-ZÀ-ÖØ-Þ][{LETTERS}'’\-]+,? [A-ZÀ-ÖØ-Þ])", stripped))
        if not stripped:
            if current:
                entries.append(" ".join(current)); current = []
            continue
        if starts_new and current:
            entries.append(" ".join(current)); current = []
        current.append(stripped)
    if current:
        entries.append(" ".join(current))
    return body, [e for e in entries if len(e) > 12]


def reference_number(entry):
    match = re.match(r"^(?:\[(\d+)\]|(\d+)[.)]|\((\d+)\))", entry)
    return int(next(g for g in match.groups() if g)) if match else None


def strip_marker(entry):
    # A list marker is "[3]", "3." or "(3)" followed by a space — never the
    # "10." that opens a bare DOI.
    return re.sub(r"^(?:\[\d+\]|\d+[.)]|\(\d+\))\s+", "", entry).strip()


def entry_year(entry):
    match = re.search(r"\b((?:19|20)\d\d)[a-z]?\b", entry)
    return match.group(1) if match else None


def entry_surname(entry):
    match = re.match(rf"^\**\s*([A-ZÀ-ÖØ-Þ][{LETTERS}'’\-]+)", strip_marker(entry))
    return match.group(1) if match else None


def expand_numeric(marker):
    numbers = []
    for part in re.split(r"\s*,\s*", marker):
        rng = re.match(r"(\d+)\s*[–-]\s*(\d+)$", part)
        if rng:
            numbers.extend(range(int(rng.group(1)), int(rng.group(2)) + 1))
        elif part.strip().isdigit():
            numbers.append(int(part))
    return numbers


def parse_author_year(token):
    token = token.strip().rstrip(",")
    match = re.match(r"^(.*?),?\s(\d{4}[a-z]?)$", token)
    if not match:
        return None, None
    names, year = match.group(1), match.group(2)
    surname = re.match(r"^(" + SURNAME + r")", names)
    return (surname.group(1).split()[0] if surname else names.split()[0]), year


def detect_citations(body):
    """Every in-text citation occurrence with its kind and lookup handle."""
    found = []
    for m in MD_DOI_LINK_RE.finditer(body):
        found.append({"span": m.span(), "kind": "doi-link", "doi": norm_doi(DOI_URL_RE.search(m.group(2)).group(1)), "label": m.group(1)})
    covered = [f["span"] for f in found]

    def free(span):
        return not any(a <= span[0] < b for a, b in covered)
    for m in DOI_URL_RE.finditer(body):
        if free(m.span()):
            found.append({"span": m.span(), "kind": "doi-url", "doi": norm_doi(m.group(1))}); covered.append(m.span())
    for m in DOI_RE.finditer(body):
        if free(m.span()):
            found.append({"span": m.span(), "kind": "doi-bare", "doi": norm_doi(m.group(0))}); covered.append(m.span())
    for m in NUMERIC_RE.finditer(body):
        if free(m.span()):
            found.append({"span": m.span(), "kind": "numeric", "numbers": expand_numeric(m.group(1))}); covered.append(m.span())
    for m in AUTHOR_YEAR_PAREN_RE.finditer(body):
        if free(m.span()):
            pairs = [parse_author_year(t) for t in m.group(1).split(";")]
            found.append({"span": m.span(), "kind": "author-year", "pairs": [p for p in pairs if p[0]]}); covered.append(m.span())
    for m in AUTHOR_YEAR_NARRATIVE_RE.finditer(body):
        if free(m.span()):
            surname = m.group(1).split()[0]
            found.append({"span": m.span(), "kind": "narrative", "pairs": [(surname, m.group(2))], "prefix": m.group(1)}); covered.append(m.span())
    return sorted(found, key=lambda f: f["span"][0])


# ------------------------------------------------------------ resolution --

def crossref_search(query, rows=3):
    """Top Crossref candidates for a free-text reference string."""
    url = ("https://api.crossref.org/works?query.bibliographic="
           + urllib.parse.quote(query[:300]) + f"&rows={rows}&select=DOI,title,author,issued,container-title")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))["message"].get("items", [])
        except Exception:  # noqa: BLE001 — retried, then reported as unresolved
            time.sleep(1.5 * (attempt + 1))
    return []


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def candidate_similarity(reference, item):
    """How much of the candidate's title the reference string contains, with
    a year and first-author check folded in."""
    title = (item.get("title") or [""])[0]
    title_tokens = _tokens(title)
    if not title_tokens:
        return 0.0
    ref_tokens = _tokens(reference)
    score = len(title_tokens & ref_tokens) / len(title_tokens)
    year = str((item.get("issued") or {}).get("date-parts", [[None]])[0][0] or "")
    if year and year in reference:
        score += 0.08
    family = ((item.get("author") or [{}])[0].get("family") or "").lower()
    if family and family in reference.lower():
        score += 0.08
    return min(score, 1.0)


def resolve_reference(reference, search=crossref_search):
    """{doi, status, similarity, candidate title} for one reference string."""
    direct = DOI_RE.search(reference)
    if direct:
        return {"doi": norm_doi(direct.group(0)), "status": "resolved", "method": "doi-in-reference",
                "similarity": 1.0, "candidate_title": None}
    items = search(strip_marker(reference))
    best, best_score = None, 0.0
    for item in items:
        score = candidate_similarity(reference, item)
        if score > best_score:
            best, best_score = item, score
    if best is None:
        return {"doi": None, "status": "unresolved", "method": "crossref-search", "similarity": 0.0, "candidate_title": None}
    status = "resolved" if best_score >= RESOLVED_MIN else ("ambiguous" if best_score >= AMBIGUOUS_MIN else "unresolved")
    return {"doi": norm_doi(best.get("DOI")) if status != "unresolved" else None, "status": status,
            "method": "crossref-search", "similarity": round(best_score, 3),
            "candidate_title": (best.get("title") or [""])[0],
            "candidate_year": str((best.get("issued") or {}).get("date-parts", [[None]])[0][0] or ""),
            "candidate_family": ((best.get("author") or [{}])[0].get("family") or "")}


def make_key(surname, year, doi):
    base = re.sub(r"[^A-Za-z]", "", surname or "Anon") or "Anon"
    tail = re.sub(r"[^a-z0-9]", "", (doi or "")[-6:])
    return f"{base}{year or ''}{tail}"


def make_label(surname, year, n_authors=None):
    if not surname:
        return f"Source {year or ''}".strip()
    if n_authors and n_authors > 2:
        return f"{surname} et al. {year}".strip()
    return f"{surname} {year}".strip()


def ingest(text, search=crossref_search):
    """Resolve every citation; return (normalized draft, ledger, resolution)."""
    body, ref_list = split_reference_list(text)
    citations = detect_citations(body)
    references = {}          # handle -> record
    consumed = set()         # reference-list entries already attached to a citation

    def add(handle, reference, res, surname=None, year=None):
        if handle in references:
            return references[handle]
        rec = {"handle": handle, "reference": reference, **res}
        from_reference = (entry_surname(reference or ""), entry_year(reference or ""))
        if res.get("status") == "resolved":
            rec["surname"] = surname or res.get("candidate_family") or from_reference[0]
            rec["year"] = year or res.get("candidate_year") or from_reference[1]
        else:
            # An unresolved reference is named by what the draft wrote, never
            # by whatever Crossref's nearest miss happened to be.
            rec["surname"] = surname or from_reference[0]
            rec["year"] = year or from_reference[1]
        if reference is not None:
            consumed.add(reference)
        rec["key"] = make_key(rec["surname"], rec["year"], rec.get("doi"))
        rec["label"] = make_label(rec["surname"], rec["year"], 3 if reference and (" et al" in reference or reference.count(",") > 3) else None)
        references[handle] = rec
        return rec

    by_number = {reference_number(e): e for e in ref_list if reference_number(e)}
    for cite in citations:
        if cite["kind"] in ("doi-link", "doi-url", "doi-bare"):
            entry = next((e for e in ref_list if cite["doi"] in e.lower()), None)
            surname = None; year = None
            if cite.get("label"):
                parsed = parse_author_year(cite["label"].replace(" et al.", "").replace(" et al", ""))
                surname, year = parsed if parsed[0] else (None, None)
            rec = add("doi:" + cite["doi"], entry or cite["doi"],
                      {"doi": cite["doi"], "status": "resolved", "method": "doi-in-text", "similarity": 1.0, "candidate_title": None},
                      surname, year)
            if cite.get("label"):
                rec["label"] = cite["label"]
            cite["handles"] = [rec["handle"]]
        elif cite["kind"] == "numeric":
            cite["handles"] = []
            for n in cite["numbers"]:
                entry = by_number.get(n)
                if entry is None:
                    rec = add(f"num:{n}", None, {"doi": None, "status": "unlisted", "method": "numeric", "similarity": 0.0, "candidate_title": None})
                else:
                    rec = add(f"num:{n}", entry, resolve_reference(entry, search))
                cite["handles"].append(rec["handle"])
        else:
            cite["handles"] = []
            for surname, year in cite["pairs"]:
                entry = next((e for e in ref_list if surname.lower() in e.lower()[:120] and year and year[:4] in e), None)
                handle = f"ay:{surname.lower()}:{year}"
                if entry is None:
                    rec = add(handle, f"{surname} {year}",
                              {"doi": None, "status": "unlisted", "method": "author-year",
                               "similarity": 0.0, "candidate_title": None}, surname, year)
                else:
                    rec = add(handle, entry, resolve_reference(entry, search), surname, year)
                cite["handles"].append(rec["handle"])
    # references listed but never cited still get resolved (they may be the fabricated ones)
    for entry in ref_list:
        if entry in consumed:
            continue
        n = reference_number(entry)
        handle = f"num:{n}" if n else "list:" + re.sub(r"\W+", "", strip_marker(entry))[:40].lower()
        if handle not in references:
            add(handle, entry, resolve_reference(entry, search))["cited"] = False
    for rec in references.values():
        rec.setdefault("cited", True)

    # normalized draft: each citation becomes Grounded DOI links; unresolved stay as they were
    out, cursor = [], 0
    for cite in citations:
        a, b = cite["span"]
        out.append(body[cursor:a])
        links = []
        for h in cite["handles"]:
            rec = references[h]
            if rec.get("doi"):
                links.append(f"[{rec['label']}](https://doi.org/{rec['doi']})")
        if links:
            prefix = cite.get("prefix", "") + " " if cite["kind"] == "narrative" else ""
            out.append(prefix + ", ".join(links))
        else:
            out.append(body[a:b])
        cursor = b
    out.append(body[cursor:])
    normalized = "".join(out).rstrip() + "\n"
    resolved = [r for r in references.values() if r.get("doi")]
    if resolved:
        def source_line(r):
            text = strip_marker(r["reference"] or "")
            text = DOI_URL_RE.sub("", text).strip()
            if not text or text.lower() == r["doi"]:
                text = ""
            return (f"**{r['surname'] or 'Anon'} ({r['year'] or 'n.d.'})** "
                    f"{(text[:200] + ' ') if text else ''}https://doi.org/{r['doi']}")
        normalized += "\n**Sources**\n\n" + "\n\n".join(source_line(r) for r in resolved) + "\n"
    ledger = {"entries": [{"key": r["key"], "doi": r["doi"], "title": r.get("candidate_title") or "",
                           "year": int(r["year"][:4]) if r.get("year") and r["year"][:4].isdigit() else None,
                           "status": "candidate", "found_by": ["draft-check"], "reference": r.get("reference")}
                          for r in resolved]}
    resolution = {"checked": time.strftime("%Y-%m-%d"), "citations": len(citations),
                  "references": sorted(references.values(), key=lambda r: r["handle"])}
    return normalized, ledger, resolution


# ---------------------------------------------------------------- report --

REFERENCE_STATUS = {
    "unresolved": "NOT FOUND — no paper matching this reference exists in Crossref; treat as fabricated or mis-cited until a DOI is produced",
    "ambiguous": "AMBIGUOUS — the closest Crossref match is uncertain; confirm the DOI before relying on it",
    "unlisted": "UNLISTED — cited in the text but absent from the reference list",
}


def render_report(resolution, ledger, audit, title="draft"):
    by_doi = {claim_receipts.norm_doi(e["doi"]): e for e in ledger.get("entries", []) if e.get("doi")}
    refs = resolution["references"]
    verified = retracted = failed = 0
    lines = [f"# Draft check — {title}", ""]
    ref_lines = []

    def display_label(r):
        # After verification the ledger carries Crossref's own author record;
        # prefer it to the draft's spelling, and to a bare "Source" for a naked DOI.
        entry = by_doi.get(claim_receipts.norm_doi(r.get("doi")), {}) if r.get("doi") else {}
        canonical = entry.get("canonical") or {}
        if canonical.get("authors_structured"):
            try:
                import format_references
                return format_references.bracket_intext(canonical)
            except Exception:  # noqa: BLE001 — fall back to the draft's label
                pass
        return r.get("label") or r.get("handle")
    for r in refs:
        r["label"] = display_label(r)
        label = r["label"]
        if r["status"] in REFERENCE_STATUS:
            closest = (r.get("candidate_title") or "")[:90]
            ref_lines.append(f"- **{label}** · {REFERENCE_STATUS[r['status']]}"
                             + (f" (closest Crossref match: “{closest}…”, similarity {r['similarity']})" if closest else ""))
            failed += 1
            continue
        entry = by_doi.get(claim_receipts.norm_doi(r["doi"]), {})
        ver = entry.get("verification") or {}
        if entry.get("status") == "verified":
            verified += 1
            ref_lines.append(f"- **{label}** · verified · https://doi.org/{r['doi']}" + (" · not cited in the text" if r.get("cited") is False else ""))
        elif ver.get("retraction_status") == "flagged":
            retracted += 1
            ref_lines.append(f"- **{label}** · RETRACTED or under expression of concern · https://doi.org/{r['doi']} — {'; '.join(ver.get('reasons', []))[:160]}")
        elif ver:
            failed += 1
            ref_lines.append(f"- **{label}** · FAILED verification · https://doi.org/{r['doi']} — {'; '.join(ver.get('reasons', []))[:160]}")
        else:
            failed += 1
            ref_lines.append(f"- **{label}** · not verified (run verify_citations.py) · https://doi.org/{r['doi']}")
    summary = claim_receipts.summarize_audit(audit) if audit else None
    score = [f"**References:** {len(refs)} cited · {verified} verified · {retracted} retracted/concern · {failed} not found, unlisted, or failed"]
    if summary:
        unsupported = summary["not_found"] + summary["unverifiable"]
        score.append(f"**Sentences:** {summary['claims']} cited · {summary['pairs']} source checks · "
                     f"{summary['supported']} supported ({summary['supported_fulltext']} at full text) · "
                     f"{summary['partial']} partial · {unsupported} unsupported · {summary['contradicted']} contradicted")
    lines += score + ["", "## References", ""] + ref_lines + [""]
    if audit:
        labels = {}
        for r in refs:
            if r.get("doi"):
                labels[claim_receipts.norm_doi(r["doi"])] = r.get("label") or r["doi"]
        lines += ["## Receipts", "", f"*{claim_receipts.summary_sentence(summary)}.*", ""]
        lines += [claim_receipts.receipt_line(e) for e in claim_receipts.receipt_entries(audit, labels)]
        fixes = [e for e in claim_receipts.receipt_entries(audit, labels)
                 if e["verdict"] in ("not_found", "unverifiable", "contradicted")]
        lines += ["", "## Citations to fix", ""]
        if fixes:
            for e in fixes:
                lines.append(f"- {e['id']} · {e['label']} · {e['verdict'].replace('_', ' ')} — “{e['snippet']}”")
        else:
            lines.append("- none: every cited sentence is backed by its source's own text at the tier shown.")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- cli --

def cmd_ingest(args):
    text = Path(args.draft).read_text(encoding="utf-8")
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    normalized, ledger, resolution = ingest(text, search=(lambda q, rows=3: []) if args.offline else crossref_search)
    atomic_write_text(out_dir / "draft-normalized.md", normalized)
    atomic_write_json(out_dir / "sources.json", ledger)
    atomic_write_json(out_dir / "resolution.json", resolution)
    counts = {}
    for r in resolution["references"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"{resolution['citations']} in-text citations, {len(resolution['references'])} references: "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + f" -> {out_dir}")


def cmd_report(args):
    resolution = json.loads(Path(args.resolution).read_text())
    ledger = json.loads(Path(args.ledger).read_text())
    audit = json.loads(Path(args.audit).read_text()) if args.audit else None
    report = render_report(resolution, ledger, audit, title=args.title)
    if args.out:
        atomic_write_text(args.out, report)
    print(report)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--draft", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--offline", action="store_true", help="never call Crossref; references without a DOI stay unresolved")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("report")
    p.add_argument("--resolution", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--audit")
    p.add_argument("--title", default="draft")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_report)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
