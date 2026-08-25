#!/usr/bin/env python3
"""
Verify that every source you intend to cite is real and bibliographically correct, then screen it for retraction signals.

Checks each DOI against Crossref, whose REST metadata includes publisher updates and
Retraction Watch records. Bibliographic verification and retraction screening are
recorded separately. A citation passes only if:
  1. the DOI resolves in Crossref,
  2. the Crossref record is a journal article (or a flagged-acceptable type),
  3. the title in your ledger matches the registered title (fuzzy, to catch wrong-DOI errors),
  4. the year matches within 1 (online-first vs issue date),
  5. Crossref's ``updated-by`` and ``update-to`` metadata contains no retraction signal.

Usage:
  python3 verify_citations.py --ledger sources.json                 # verify all entries
  python3 verify_citations.py --ledger sources.json --keys Kuyken2022effectiveness Dunning2018research
  python3 verify_citations.py --doi 10.1136/bmj.n71 --doi 10.1111/camh.12572   # ad hoc DOIs
  python3 verify_citations.py --ledger sources.json --cited review.md    # verify only keys cited in review.md as [@key]

Marks ledger entries status = 'verified' | 'failed' (with a reason) and fills canonical
metadata (authors, title, journal, volume, issue, pages, year) from Crossref for reference
formatting. Exit code 1 if any checked citation failed — treat that as a hard stop.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "scientific-review-skill/1.1"
OK_TYPES = {"journal-article"}
WARN_TYPES = {"book-chapter", "proceedings-article", "book", "monograph", "reference-entry", "report"}


def get(url, accept=None, retries=3):
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, ""
            if i == retries - 1:
                return e.code, ""
        except (urllib.error.URLError, TimeoutError):
            if i == retries - 1:
                return 0, ""
        time.sleep(1.0 * (i + 1))


def norm_doi(doi):
    doi = (doi or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)


def norm_title(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def title_similarity(a, b):
    a, b = set(norm_title(a).split()), set(norm_title(b).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def crossref(doi):
    status, body = get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if status != 200:
        return None, f"Crossref HTTP {status}"
    try:
        m = json.loads(body)["message"]
    except (ValueError, KeyError):
        return None, "Crossref: unparseable response"
    return m, None


def crossref_retraction_signals(m):
    """Return normalized retraction signals from a Crossref work record.

    Crossref exposes a retracted original through ``updated-by`` and exposes a
    retraction notice through ``update-to``. Records can originate with either the
    publisher or Crossref's integrated Retraction Watch data, so both directions and
    all sources must be inspected.
    """
    signals = []
    for field in ("updated-by", "update-to"):
        for update in m.get(field) or []:
            relation_type = str(update.get("type") or "").strip().lower()
            label = str(update.get("label") or "").strip().lower()
            if not (relation_type.startswith("retract") or label.startswith("retract")):
                continue
            signals.append({
                "relation": field,
                "doi": norm_doi(update.get("DOI")),
                "type": update.get("type"),
                "label": update.get("label"),
                "source": str(update.get("source") or "crossref"),
            })

    # Defensive fallback for old or incomplete deposits that are clearly notices but
    # lack an update relation. Keep this deliberately narrow so papers *about*
    # retractions are not falsely rejected.
    title = (m.get("title") or [""])[0]
    if not signals and re.match(
        r"^\s*(?:retraction|retracted)(?:\s*[:\-—]|\s+(?:notice|statement|to|of)\b)",
        re.sub(r"<[^>]+>", "", title),
        re.I,
    ):
        signals.append({
            "relation": "title",
            "doi": norm_doi(m.get("DOI")),
            "type": "retraction-notice",
            "label": "Clear retraction-notice title",
            "source": "crossref",
        })
    return signals


def cr_year(m):
    for k in ("published-print", "published-online", "issued", "created"):
        parts = (m.get(k) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return parts[0][0]
    return None


def cr_authors(m):
    out = []
    for a in m.get("author") or []:
        fam, giv = a.get("family"), a.get("given")
        if fam:
            out.append({"family": fam, "given": giv or ""})
        elif a.get("name"):
            out.append({"family": a["name"], "given": ""})
    return out


def verify_one(entry):
    doi = norm_doi(entry.get("doi"))
    bibliographic_issues = []
    warnings = []
    retraction_issues = []
    if not doi:
        details = {"bibliographic_status": "failed", "retraction_status": "not_checked", "retraction_sources": {"crossref": "not_checked"}}
        return "failed", ["no DOI — cannot verify; find the DOI or drop the citation"], {}, details
    m, err = crossref(doi)
    if err:
        details = {"bibliographic_status": "failed", "retraction_status": "not_checked", "retraction_sources": {"crossref": "not_checked"}}
        if err == "Crossref HTTP 404":
            reason = err + " — DOI does not resolve; it may be mistyped or unregistered"
        else:
            reason = err + " — verification could not be completed"
        return "failed", [reason], {}, details
    ctype = m.get("type")
    cr_title = (m.get("title") or [""])[0]
    sim = title_similarity(entry.get("title", ""), cr_title)
    if entry.get("title") and sim < 0.5:
        bibliographic_issues.append(f"title mismatch (similarity {sim:.2f}): ledger='{entry.get('title','')[:70]}' vs Crossref='{cr_title[:70]}'")
    y = cr_year(m)
    if entry.get("year") and y and abs(int(entry["year"]) - int(y)) > 1:
        bibliographic_issues.append(f"year mismatch: ledger {entry['year']} vs Crossref {y}")
    if ctype not in OK_TYPES:
        if ctype in WARN_TYPES:
            warnings.append(f"WARN: type is '{ctype}', not a journal article — cite only if appropriate for the claim")
        elif ctype == "posted-content":
            warnings.append("preprint / posted content — not peer reviewed; cite only if explicitly labelled as a preprint")
        else:
            bibliographic_issues.append(f"type '{ctype}' is not a journal article")
    retraction_signals = crossref_retraction_signals(m)
    if retraction_signals:
        origins = sorted({signal["source"] for signal in retraction_signals})
        relations = sorted({signal["relation"] for signal in retraction_signals})
        retraction_issues.append(
            "RETRACTED or retraction notice in Crossref metadata "
            f"(relation: {', '.join(relations)}; source: {', '.join(origins)}) — do not cite as evidence"
        )
    retraction_status = "flagged" if retraction_signals else "clear"
    canonical = {
        "title": cr_title, "authors_structured": cr_authors(m), "journal": (m.get("container-title") or [""])[0],
        "journal_short": (m.get("short-container-title") or [""])[0], "volume": m.get("volume"),
        "issue": m.get("issue"), "pages": m.get("page"), "year": y, "type": ctype,
        "article_number": m.get("article-number"), "publisher": m.get("publisher"), "url": "https://doi.org/" + doi,
    }
    reasons = bibliographic_issues + warnings + retraction_issues
    hard_fail = bool(bibliographic_issues or retraction_issues)
    details = {
        "bibliographic_status": "failed" if bibliographic_issues else "verified",
        "retraction_status": retraction_status,
        "retraction_sources": {"crossref": retraction_status},
        "retraction_signals": retraction_signals,
    }
    return ("failed" if hard_fail else "verified"), reasons, canonical, details


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger")
    ap.add_argument("--keys", nargs="*")
    ap.add_argument("--doi", action="append", default=[])
    ap.add_argument("--cited", help="markdown file; verify only keys that appear as [@key] or [key] citations in it")
    ap.add_argument("--allow-preprints", action="store_true")
    args = ap.parse_args()

    entries = []
    ledger = None
    if args.ledger:
        with open(args.ledger) as fh:
            ledger = json.load(fh)
        entries = ledger["entries"]
        if args.keys:
            entries = [e for e in entries if e["key"] in set(args.keys)]
        if args.cited:
            text = open(args.cited).read()
            cited = set(re.findall(r"\[@([A-Za-z0-9_\-]+)", text)) | set(re.findall(r"@([A-Za-z][A-Za-z0-9_\-]+)", text))
            entries = [e for e in entries if e["key"] in cited]
            missing = cited - {e["key"] for e in ledger["entries"]}
            if missing:
                print(f"ERROR: cited keys not in ledger (unknown sources): {sorted(missing)}")
    for d in args.doi:
        entries.append({"key": d, "doi": d, "title": "", "year": None})

    if not entries:
        print("nothing to verify")
        return

    failed = 0
    for e in entries:
        status, reasons, canonical, details = verify_one(e)
        if status == "verified" and not args.allow_preprints and any("preprint" in r for r in reasons):
            status = "failed"
            details["bibliographic_status"] = "failed"
        e["status"] = status
        e["verification"] = {"checked": time.strftime("%Y-%m-%d"), **details, "reasons": reasons}
        if canonical:
            e["canonical"] = canonical
        mark = "OK " if status == "verified" else "FAIL"
        print(f"[{mark}] {e['key']:<28} {e.get('doi') or '(no doi)'}")
        for r in reasons:
            print(f"       - {r}")
        if status == "failed":
            failed += 1
        time.sleep(0.2)

    if ledger is not None:
        with open(args.ledger, "w") as fh:
            json.dump(ledger, fh, indent=2, ensure_ascii=False)
    n = len(entries)
    print(f"\n{n - failed}/{n} passed Crossref bibliographic and retraction checks.")
    if failed:
        print(f"{failed} FAILED — fix or remove before citing.")
    elif not failed:
        print("Crossref retraction screening complete (publisher and Retraction Watch update metadata).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
