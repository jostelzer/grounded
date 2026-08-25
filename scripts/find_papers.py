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

OpenAlex courtesy settings:
  Set OPENALEX_MAILTO (or pass --mailto you@example.org) to enter OpenAlex's polite pool, which
  carries a higher and far more reliable rate limit. Requests are throttled, and 429/5xx responses
  are retried with exponential backoff honouring Retry-After. OpenAlex 429s can carry a multi-hour
  Retry-After (a spent request quota rather than a burst); when that happens OpenAlex is skipped
  for the rest of the run, clearly logged, and discovery continues on PubMed alone.

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
import datetime
import email.utils
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "1.1"
SKILL_URL = "https://github.com/jostelzer/scientific-review-skill"
# Request pacing: OpenAlex's polite pool allows 10 req/s, NCBI allows 3 req/s without an API key.
OPENALEX_MIN_INTERVAL = 0.15
PUBMED_MIN_INTERVAL = 0.34
# A Retry-After longer than this is a spent request quota, not a burst limit: waiting it out
# inside a run is pointless, so we stop asking and fall back to PubMed.
MAX_RETRY_WAIT = 120.0
# Contact address sent to each service (polite pool); filled in by main() from --mailto/env.
SERVICE_MAILTO = {}
TERTIARY_VENUES = ("statpearls", "uptodate", "merck manual", "wikipedia", "encyclopedia",
                   "cochrane clinical answers", "dynamed", "bmj best practice")
PREPRINT_HOSTS = ("biorxiv", "medrxiv", "arxiv", "ssrn", "research square", "preprints.org",
                  "psyarxiv", "osf preprints", "chemrxiv", "authorea", "scielo preprints", "europe pmc preprints")


def user_agent(mailto=None):
    """Descriptive UA; the mailto form is what OpenAlex and Crossref ask for."""
    return f"scientific-review-skill/{VERSION} (+{SKILL_URL}" + (f"; mailto:{mailto})" if mailto else ")")


class ServiceUnavailable(Exception):
    """The service could not be reached, or asked us to come back later than this run can wait."""

    def __init__(self, service, reason, retry_after=None):
        super().__init__(f"{service} unavailable: {reason}")
        self.service = service
        self.reason = reason
        self.retry_after = retry_after


_last_request = {}


def throttle(service, min_interval):
    prev = _last_request.get(service)
    if prev is not None:
        gap = min_interval - (time.monotonic() - prev)
        if gap > 0:
            time.sleep(gap)
    _last_request[service] = time.monotonic()


def parse_retry_after(headers):
    """Retry-After is either a number of seconds or an HTTP-date."""
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds())


def http_get(url, service, min_interval=0.0, retries=3, backoff=1.0, timeout=30):
    """GET with throttling and exponential backoff on 429/5xx, honouring Retry-After.

    Raises ServiceUnavailable when the service is out of reach for this run.
    """
    headers = {"User-Agent": user_agent(SERVICE_MAILTO.get(service))}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries + 1):
        throttle(service, min_interval)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            retry_after = parse_retry_after(e.headers)
            if e.code not in (429, 500, 502, 503, 504):
                raise ServiceUnavailable(service, f"HTTP {e.code} {e.reason}") from e
            if retry_after is not None and retry_after > MAX_RETRY_WAIT:
                raise ServiceUnavailable(
                    service,
                    f"HTTP {e.code} (Retry-After {fmt_duration(retry_after)}): a spent request "
                    "quota rather than a burst limit, so this run will not wait it out",
                    retry_after=retry_after,
                ) from e
            if attempt == retries:
                raise ServiceUnavailable(service, f"HTTP {e.code} after {retries + 1} attempts",
                                         retry_after=retry_after) from e
            wait = retry_after if retry_after is not None else backoff * (2 ** attempt)
            wait = min(max(wait, 0.0), MAX_RETRY_WAIT) + random.uniform(0, 0.25)
            sys.stderr.write(f"  {service}: HTTP {e.code}, retrying in {wait:.1f}s "
                             f"(attempt {attempt + 2}/{retries + 1})\n")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == retries:
                raise ServiceUnavailable(service, f"{e} after {retries + 1} attempts") from e
            wait = backoff * (2 ** attempt) + random.uniform(0, 0.25)
            sys.stderr.write(f"  {service}: {e}, retrying in {wait:.1f}s "
                             f"(attempt {attempt + 2}/{retries + 1})\n")
            time.sleep(wait)


def fmt_duration(seconds):
    if seconds >= 86400:
        return f"{seconds / 86400:.1f}d"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    if seconds >= 60:
        return f"{seconds / 60:.1f}min"
    return f"{seconds:.0f}s"


def get(url, service="pubmed", min_interval=PUBMED_MIN_INTERVAL, retries=3):
    """Fetch a URL, reporting rather than raising when the service is out of reach."""
    try:
        return http_get(url, service=service, min_interval=min_interval, retries=retries)
    except ServiceUnavailable as e:
        sys.stderr.write(f"  {e}\n")
        return None


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

class OpenAlexClient:
    """OpenAlex access with a polite-pool contact address and a one-strike availability latch.

    OpenAlex answers an exhausted request quota with 429 and a Retry-After measured in hours.
    Once that (or any other hard failure) happens, further OpenAlex calls in this run are
    pointless, so the client latches off and discovery carries on with PubMed alone.
    """

    def __init__(self, mailto=None, retries=3):
        self.mailto = mailto
        self.retries = retries
        self.unavailable = None      # reason string once OpenAlex is given up on
        self.retry_after = None
        SERVICE_MAILTO["openalex"] = mailto

    @property
    def enabled(self):
        return self.unavailable is None

    def fetch(self, url):
        if not self.enabled:
            return None
        try:
            return http_get(url, service="openalex", min_interval=OPENALEX_MIN_INTERVAL,
                            retries=self.retries)
        except ServiceUnavailable as e:
            self.unavailable = e.reason
            self.retry_after = e.retry_after
            sys.stderr.write(f"  {e}\n")
            sys.stderr.write("  skipping OpenAlex for the rest of this run — "
                             "discovery continues on PubMed alone\n")
            return None


def search_openalex(client, query, from_year, to_year, limit, types, sort):
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
    if client.mailto:
        params["mailto"] = client.mailto      # OpenAlex polite pool
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    raw = client.fetch(url)
    if not raw:
        return []
    try:
        results = json.loads(raw).get("results", [])
    except json.JSONDecodeError:
        sys.stderr.write("  openalex: unreadable response, skipping this query\n")
        return []
    out = []
    for w in results:
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
    ap.add_argument("--mailto", default=os.environ.get("OPENALEX_MAILTO", "").strip() or None,
                    help="contact address for OpenAlex's polite pool (default: $OPENALEX_MAILTO)")
    ap.add_argument("--openalex-retries", type=int, default=3,
                    help="retries per OpenAlex request before giving up on OpenAlex (default: 3)")
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

    use_openalex = "openalex" in args.sources
    client = OpenAlexClient(mailto=args.mailto, retries=args.openalex_retries)
    if use_openalex and not client.mailto:
        sys.stderr.write("Note: no --mailto / OPENALEX_MAILTO set — OpenAlex requests go to the "
                         "shared pool, which is throttled harder than the polite pool.\n")

    new_entries = []
    for q in args.query:
        hits = []
        if use_openalex and client.enabled:
            hits += search_openalex(client, q, args.from_year, args.to_year, args.limit,
                                    args.types, args.sort)
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

    if use_openalex and not client.enabled:
        print(f"\nNOTE: OpenAlex was skipped for this run — {client.unavailable}. "
              "These hits come from PubMed alone, so coverage outside biomedicine may be thin: "
              "widen the queries, or rerun later"
              + ("." if client.mailto else ", and set OPENALEX_MAILTO to use the polite pool."))

    retracted = [e for e in ledger["entries"] if e.get("is_retracted")]
    if retracted:
        print(f"\nWARNING: {len(retracted)} retracted paper(s) in ledger — do not cite except to discuss the retraction: "
              + ", ".join(e["key"] for e in retracted))
    with open(args.ledger, "w") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
    print(f"\nLedger: {len(ledger['entries'])} entries → {args.ledger}")


if __name__ == "__main__":
    main()
