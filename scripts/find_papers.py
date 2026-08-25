#!/usr/bin/env python3
"""
Search the peer-reviewed literature (OpenAlex + PubMed) and build a source ledger.

Standard library only. Every hit is a real record from a scholarly index, with a DOI
where one exists — never a recalled citation.

Usage:
  python3 find_papers.py --query "school-based mindfulness adolescents anxiety" \
      --query "mindfulness intervention adolescent anxiety randomized" \
      --from-year 2015 --limit 25 --ledger sources.json --angle "human RCTs"

  python3 find_papers.py --query "..." --types review --limit 10      # reviews/meta-analyses only
  python3 find_papers.py --query "..." --sort cited                    # most-cited first
  python3 find_papers.py --ledger sources.json --show                  # print the ledger

What it does:
  * Queries OpenAlex (/works, relevance-ranked) and PubMed (esearch + efetch) for each query.
  * Keeps peer-reviewed journal articles only: OpenAlex type in {article, review},
    source type 'journal', not a preprint server; PubMed records are journal-indexed by design.
    Use --include-preprints to keep preprints (they are flagged 'PREPRINT').
  * Records retraction status (OpenAlex is_retracted) and flags retracted papers.
  * Merges by DOI (or PMID when no DOI) into --ledger (JSON), adding the query and angle that
    found each paper, so you can see coverage per angle.
  * Prints a compact table: key, year, citations, type, title, journal.

Ledger entry fields: key, doi, pmid, title, authors, year, journal, type, abstract,
cited_by_count, oa_url, is_retracted, is_preprint, found_by (list of {query, angle, source}),
status ('candidate' until verify_citations.py marks it 'verified').
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "scientific-review-skill/1.0 (mailto:review-skill@example.org)"
TERTIARY_VENUES = ("statpearls", "uptodate", "merck manual", "wikipedia", "encyclopedia",
                   "cochrane clinical answers", "dynamed", "bmj best practice")
PREPRINT_HOSTS = ("biorxiv", "medrxiv", "arxiv", "ssrn", "research square", "preprints.org",
                  "psyarxiv", "osf preprints", "chemrxiv", "authorea", "scielo preprints", "europe pmc preprints")


def get(url, retries=3, sleep=1.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if i == retries - 1:
                sys.stderr.write(f"  request failed: {url[:100]}... ({e})\n")
                return None
            time.sleep(sleep * (i + 1))


def norm_doi(doi):
    if not doi:
        return None
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi or None


def inverted_to_text(inv):
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    return " ".join(w for _, w in sorted(pos))


def make_key(authors, year, title):
    first = (authors[0].split(",")[0].split(" ")[-1] if authors else "anon")
    first = re.sub(r"[^A-Za-z]", "", first) or "anon"
    w = re.findall(r"[A-Za-z]{4,}", title or "")
    return f"{first}{year or 'nd'}{(w[0].lower() if w else '')}"


# ---------------------------------------------------------------- OpenAlex

def search_openalex(query, from_year, to_year, limit, types, sort):
    filt = ["is_paratext:false"]
    if types == "review":
        filt.append("type:review|article")
    else:
        filt.append("type:article|review")
    if from_year:
        filt.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filt.append(f"to_publication_date:{to_year}-12-31")
    params = {
        "search": query,
        "filter": ",".join(filt),
        "per-page": str(min(limit, 50)),
        "select": "id,doi,title,authorships,publication_year,cited_by_count,primary_location,type,"
                  "abstract_inverted_index,is_retracted,ids,best_oa_location,open_access",
    }
    if sort == "cited":
        params["sort"] = "cited_by_count:desc"
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    raw = get(url)
    if not raw:
        return []
    out = []
    for w in json.loads(raw).get("results", []):
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        src_name = (src.get("display_name") or "")
        src_type = src.get("type") or ""
        is_preprint = (src_type == "repository" and any(h in src_name.lower() for h in PREPRINT_HOSTS)) \
            or w.get("type") == "preprint"
        if types == "review" and w.get("type") != "review" and not re.search(
                r"meta-analy|systematic review|umbrella review|scoping review|review", w.get("title") or "", re.I):
            continue
        authors = []
        for a in w.get("authorships") or []:
            n = (a.get("author") or {}).get("display_name")
            if n:
                authors.append(n)
        oa = (w.get("best_oa_location") or {})
        out.append({
            "doi": norm_doi(w.get("doi")),
            "pmid": ((w.get("ids") or {}).get("pmid") or "").split("/")[-1] or None,
            "openalex": w.get("id"),
            "title": (w.get("title") or "").strip(),
            "authors": authors,
            "year": w.get("publication_year"),
            "journal": src_name,
            "source_type": src_type,
            "type": w.get("type"),
            "abstract": inverted_to_text(w.get("abstract_inverted_index")),
            "cited_by_count": w.get("cited_by_count", 0),
            "oa_url": oa.get("pdf_url") or oa.get("landing_page_url"),
            "is_retracted": bool(w.get("is_retracted")),
            "is_preprint": bool(is_preprint),
            "_source": "openalex",
        })
    return out


# ---------------------------------------------------------------- PubMed

def search_pubmed(query, from_year, to_year, limit, types):
    term = query
    if types == "review":
        term += " AND (systematic review[pt] OR meta-analysis[pt] OR review[pt])"
    if from_year or to_year:
        term += f" AND ({from_year or 1800}[dp] : {to_year or 3000}[dp])"
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": term, "retmax": str(limit), "retmode": "json", "sort": "relevance"})
    raw = get(url)
    if not raw:
        return []
    ids = json.loads(raw).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    time.sleep(0.4)  # NCBI rate limit (3 req/s without key)
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
    raw = get(url)
    if not raw:
        return []
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    for art in root.findall(".//PubmedArticle"):
        pmid = (art.findtext(".//PMID") or "").strip()
        tel = art.find(".//ArticleTitle")
        title = "".join(tel.itertext()).strip() if tel is not None else ""
        journal = art.findtext(".//Journal/Title") or ""
        year = art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4]
        try:
            year = int(year)
        except ValueError:
            year = None
        abstract = " ".join("".join(a.itertext()).strip() for a in art.findall(".//Abstract/AbstractText"))
        authors = []
        for a in art.findall(".//AuthorList/Author"):
            ln, fn = a.findtext("LastName"), a.findtext("ForeName")
            if ln:
                authors.append(f"{fn} {ln}".strip() if fn else ln)
        doi = None
        for el in art.findall("./MedlineCitation/Article/ELocationID"):
            if el.get("EIdType") == "doi" and el.text:
                doi = norm_doi(el.text)
        if not doi:
            for idn in art.findall("./PubmedData/ArticleIdList/ArticleId"):
                if idn.get("IdType") == "doi" and idn.text:
                    doi = norm_doi(idn.text)
        ptypes = [p.text or "" for p in art.findall(".//PublicationTypeList/PublicationType")]
        retracted = any("Retracted Publication" in p for p in ptypes)
        is_review = any(p in ("Review", "Systematic Review", "Meta-Analysis") for p in ptypes)
        out.append({
            "doi": doi, "pmid": pmid or None, "openalex": None, "title": title, "authors": authors,
            "year": year, "journal": journal, "source_type": "journal",
            "type": "review" if is_review else "article", "abstract": abstract,
            "cited_by_count": None, "oa_url": None, "is_retracted": retracted, "is_preprint": False,
            "pub_types": ptypes, "_source": "pubmed",
        })
    return out


# ---------------------------------------------------------------- ledger

def load_ledger(path):
    if path and os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {"created": time.strftime("%Y-%m-%d"), "entries": []}


def merge(ledger, hits, query, angle):
    by_id = {}
    for e in ledger["entries"]:
        if e.get("doi"):
            by_id["doi:" + e["doi"]] = e
        if e.get("pmid"):
            by_id["pmid:" + e["pmid"]] = e
    added, updated = 0, 0
    for h in hits:
        ident = ("doi:" + h["doi"]) if h.get("doi") else (("pmid:" + h["pmid"]) if h.get("pmid") else None)
        if ident is None:
            continue
        e = by_id.get(ident)
        if e is None and h.get("doi") and h.get("pmid"):
            e = by_id.get("pmid:" + h["pmid"])
        if e:
            # fill gaps
            for k in ("doi", "pmid", "openalex", "abstract", "oa_url", "journal", "year", "cited_by_count"):
                if not e.get(k) and h.get(k):
                    e[k] = h[k]
            if h.get("is_retracted"):
                e["is_retracted"] = True
            e["found_by"].append({"query": query, "angle": angle, "source": h["_source"]})
            updated += 1
        else:
            e = {k: v for k, v in h.items() if not k.startswith("_")}
            e["key"] = make_key(e["authors"], e["year"], e["title"])
            e["found_by"] = [{"query": query, "angle": angle, "source": h["_source"]}]
            e["status"] = "candidate"
            ledger["entries"].append(e)
            by_id[ident] = e
            if e.get("doi"):
                by_id["doi:" + e["doi"]] = e
            if e.get("pmid"):
                by_id["pmid:" + e["pmid"]] = e
            added += 1
    # make keys unique
    seen = {}
    for e in ledger["entries"]:
        k = e["key"]
        if k in seen:
            seen[k] += 1
            e["key"] = f"{k}{chr(96 + seen[k])}"
        else:
            seen[k] = 1
    return added, updated


def print_table(entries, max_rows=None):
    rows = entries if max_rows is None else entries[:max_rows]
    print(f"{'key':<26} {'year':>4} {'cites':>6} {'type':<8} {'flags':<10} title | journal")
    for e in rows:
        flags = ("RETRACTED " if e.get("is_retracted") else "") + ("PREPRINT " if e.get("is_preprint") else "")
        flags = flags.strip() or ("verified" if e.get("status") == "verified" else "")
        cites = e.get("cited_by_count")
        print(f"{e['key']:<26} {str(e.get('year') or ''):>4} {str(cites if cites is not None else '-'):>6} "
              f"{(e.get('type') or '')[:8]:<8} {flags:<10} {e['title'][:80]} | {(e.get('journal') or '')[:40]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", "-q", action="append", default=[], help="search query (repeatable)")
    ap.add_argument("--angle", default="", help="label for the angle these queries cover (stored in ledger)")
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument("--limit", type=int, default=20, help="max hits per query per source")
    ap.add_argument("--types", choices=["all", "review"], default="all", help="'review' = reviews/meta-analyses only")
    ap.add_argument("--sort", choices=["relevance", "cited"], default="relevance")
    ap.add_argument("--sources", default="openalex,pubmed")
    ap.add_argument("--include-preprints", action="store_true")
    ap.add_argument("--ledger", default="sources.json")
    ap.add_argument("--show", action="store_true", help="print the ledger and exit")
    ap.add_argument("--abstracts", action="store_true", help="also print abstracts of new hits")
    args = ap.parse_args()

    ledger = load_ledger(args.ledger)
    if args.show or not args.query:
        print_table(ledger["entries"])
        print(f"\n{len(ledger['entries'])} entries in {args.ledger}")
        return

    new_entries = []
    for q in args.query:
        hits = []
        if "openalex" in args.sources:
            hits += search_openalex(q, args.from_year, args.to_year, args.limit, args.types, args.sort)
        if "pubmed" in args.sources:
            hits += search_pubmed(q, args.from_year, args.to_year, args.limit, args.types)
        if not args.include_preprints:
            hits = [h for h in hits if not h["is_preprint"]]
        # Tertiary reference works (StatPearls et al.) are indexed in PubMed but are not studies.
        before_t = len(hits)
        hits = [h for h in hits if not any(v in (h.get("journal") or "").lower() for v in TERTIARY_VENUES)]
        if len(hits) < before_t:
            print(f"  (dropped {before_t - len(hits)} tertiary-source record(s) — StatPearls/UpToDate-type entries are not citable)")
        hits = [h for h in hits if h.get("source_type") in ("journal", "", None) or h.get("_source") == "pubmed"]
        before = {e.get("doi") or e.get("pmid") for e in ledger["entries"]}
        added, updated = merge(ledger, hits, q, args.angle)
        fresh = [e for e in ledger["entries"] if (e.get("doi") or e.get("pmid")) not in before]
        new_entries += fresh
        print(f"\n## query: {q}   ({len(hits)} hits; {added} new, {updated} already in ledger)")
        print_table(fresh)
        if args.abstracts:
            for e in fresh:
                print(f"\n[{e['key']}] {e['title']}\n  {e.get('abstract') or '(no abstract available)'}\n")

    retracted = [e for e in ledger["entries"] if e.get("is_retracted")]
    if retracted:
        print(f"\nWARNING: {len(retracted)} retracted paper(s) in ledger — do not cite except to discuss the retraction: "
              + ", ".join(e["key"] for e in retracted))
    with open(args.ledger, "w") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
    print(f"\nLedger: {len(ledger['entries'])} entries → {args.ledger}")


if __name__ == "__main__":
    main()
