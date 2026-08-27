#!/usr/bin/env python3
"""Search scholarly indexes and build an auditable source ledger.

The script searches OpenAlex and PubMed with pagination, applies an explicit
publication-eligibility policy, automatically records database runs in
``search_log.md``, and can traverse backward and forward citations via OpenAlex.

Usage:
  python3 find_papers.py --query "school-based mindfulness adolescents anxiety" \
      --query "mindfulness intervention adolescent anxiety randomized" \
      --from-year 2015 --limit 25 --ledger sources.json --angle "human RCTs"

  python3 find_papers.py --openalex-query "school mindfulness adolescent anxiety" \
      --pubmed-query 'mindfulness[tiab] AND adolescent*[tiab] AND anxiety[tiab]'

  python3 find_papers.py --ledger sources.json --chase Kuyken2022effectiveness \
      --chase-direction both --chase-limit 50

  python3 find_papers.py --query "..." --types review --limit 100
  python3 find_papers.py --ledger sources.json --show

OpenAlex courtesy settings:
  Set OPENALEX_MAILTO (or pass --mailto you@example.org) to enter OpenAlex's polite pool, which
  carries a higher and far more reliable rate limit. Requests are throttled, and 429/5xx responses
  are retried with exponential backoff honouring Retry-After. OpenAlex 429s can carry a multi-hour
  Retry-After (a spent request quota rather than a burst); when that happens OpenAlex is skipped
  for the rest of the run, clearly logged, and discovery continues on PubMed alone.

``--query`` is sent to every enabled database. ``--openalex-query`` and
``--pubmed-query`` are database-specific, so PubMed field syntax never leaks
into OpenAlex. The strict publication policy removes obvious non-evidence
records, but does not pretend that an index or Crossref proves peer review:
accepted entries explicitly carry ``peer_review_status=not_independently_verified``.
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
from collections import Counter
from dataclasses import dataclass, field

from artifact_io import atomic_write_json
from grounded_metadata import user_agent as grounded_user_agent

# Request pacing: OpenAlex's polite pool allows 10 req/s, NCBI allows 3 req/s without an API key.
OPENALEX_MIN_INTERVAL = 0.15
PUBMED_MIN_INTERVAL = 0.34
OPENCITATIONS_MIN_INTERVAL = 0.35
# A Retry-After longer than this is a spent request quota, not a burst limit: waiting it out
# inside a run is pointless, so we stop asking and fall back to PubMed.
MAX_RETRY_WAIT = 120.0
OPENALEX_MAX_PAGE_SIZE = 100
PUBMED_MAX_RESULTS = 10_000
# Contact address sent to each service (polite pool); filled in by main() from --mailto/env.
SERVICE_MAILTO = {}
TERTIARY_VENUES = ("statpearls", "uptodate", "merck manual", "wikipedia", "encyclopedia",
                   "cochrane clinical answers", "dynamed", "bmj best practice")
PREPRINT_HOSTS = ("biorxiv", "medrxiv", "arxiv", "ssrn", "research square", "preprints.org",
                  "psyarxiv", "osf preprints", "chemrxiv", "authorea",
                  "scielo preprints", "europe pmc preprints")
PUBMED_EXCLUDED_TYPES = frozenset({
    "Autobiography", "Biography", "Comment", "Directory", "Editorial",
    "Expression of Concern", "Interview", "Letter", "News", "Newspaper Article",
    "Personal Narrative", "Portrait", "Preprint", "Published Erratum",
    "Retraction of Publication",
})
PUBMED_EVIDENCE_TYPES = frozenset({
    "Adaptive Clinical Trial", "Case Reports", "Clinical Study", "Clinical Trial",
    "Clinical Trial, Phase I", "Clinical Trial, Phase II", "Clinical Trial, Phase III",
    "Clinical Trial, Phase IV", "Comparative Study", "Consensus Development Conference",
    "Controlled Clinical Trial", "Evaluation Study", "Guideline", "Journal Article",
    "Meta-Analysis", "Multicenter Study", "Observational Study", "Practice Guideline",
    "Pragmatic Clinical Trial", "Randomized Controlled Trial", "Review",
    "Systematic Review", "Twin Study", "Validation Study",
})
OPENALEX_WORK_FIELDS = (
    "id,doi,title,authorships,publication_year,publication_date,cited_by_count,"
    "primary_location,type,abstract_inverted_index,is_retracted,ids,best_oa_location,open_access"
)
PUBMED_SORT_VALUES = {
    "relevance": "relevance",
    "pub-date": "pub_date",
    "first-author": "Author",
    "journal": "JournalName",
}


@dataclass
class SearchResult:
    database: str
    query: str
    api_query: str
    filters: str
    sort: str
    hits: list = field(default_factory=list)
    total_matches: int = None
    pages: int = 0
    status: str = "ok"
    exclusions: Counter = field(default_factory=Counter)
    citation_direction: str = None

    @property
    def retrieved(self):
        return len(self.hits) + sum(self.exclusions.values())


def user_agent(mailto=None):
    """Descriptive UA; the mailto form is what OpenAlex and Crossref ask for."""
    return grounded_user_agent(mailto=mailto)


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


def http_get(url, service, min_interval=0.0, retries=3, backoff=1.0, timeout=30,
             extra_headers=None):
    """GET with throttling and exponential backoff on 429/5xx, honouring Retry-After.

    Raises ServiceUnavailable when the service is out of reach for this run.
    """
    headers = {"User-Agent": user_agent(SERVICE_MAILTO.get(service))}
    headers.update(extra_headers or {})
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


def short_openalex_id(value):
    if not value:
        return None
    match = re.search(r"(?:^|/)(W\d+)$", str(value), re.I)
    return match.group(1).upper() if match else None


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


def ordered_unique(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


# ---------------------------------------------------------------- OpenAlex

class OpenAlexClient:
    """OpenAlex access with a polite-pool contact address and a one-strike availability latch.

    OpenAlex answers an exhausted request quota with 429 and a Retry-After measured in hours.
    Once that (or any other hard failure) happens, further OpenAlex calls in this run are
    pointless, so the client latches off and discovery carries on with PubMed alone.
    """

    def __init__(self, mailto=None, retries=3, api_key=None):
        self.mailto = mailto
        self.retries = retries
        self.api_key = api_key
        self.unavailable = None      # reason string once OpenAlex is given up on
        self.retry_after = None
        SERVICE_MAILTO["openalex"] = mailto

    @property
    def enabled(self):
        return self.unavailable is None

    def add_identity(self, params):
        params = dict(params)
        if self.mailto:
            params["mailto"] = self.mailto
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def fetch(self, url, latch=True):
        if not self.enabled:
            return None
        try:
            return http_get(url, service="openalex", min_interval=OPENALEX_MIN_INTERVAL,
                            retries=self.retries)
        except ServiceUnavailable as e:
            sys.stderr.write(f"  {e}\n")
            seed_miss = (
                e.reason.startswith("HTTP 400") or e.reason.startswith("HTTP 404")
            )
            if latch or not seed_miss:
                self.unavailable = e.reason
                self.retry_after = e.retry_after
                sys.stderr.write("  skipping OpenAlex for the rest of this run — "
                                 "discovery continues on PubMed alone\n")
            return None


def parse_openalex_work(work):
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    source_name = source.get("display_name") or ""
    source_type = source.get("type") or ""
    work_type = work.get("type") or ""
    is_preprint = (
        work_type == "preprint"
        or (source_type == "repository" and any(
            host in source_name.lower() for host in PREPRINT_HOSTS
        ))
    )
    authors = []
    for authorship in work.get("authorships") or []:
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
    oa_location = work.get("best_oa_location") or {}
    return {
        "doi": norm_doi(work.get("doi")),
        "pmid": ((work.get("ids") or {}).get("pmid") or "").split("/")[-1] or None,
        "openalex": work.get("id"),
        "title": (work.get("title") or "").strip(),
        "authors": authors,
        "year": work.get("publication_year"),
        "journal": source_name,
        "source_type": source_type,
        "type": work_type,
        "abstract": inverted_to_text(work.get("abstract_inverted_index")),
        "cited_by_count": work.get("cited_by_count", 0),
        "oa_url": oa_location.get("pdf_url") or oa_location.get("landing_page_url"),
        "is_retracted": bool(work.get("is_retracted")),
        "is_preprint": bool(is_preprint),
        "peer_review_status": "not_independently_verified",
        "_source": "openalex",
    }


def fetch_openalex_pages(client, base_params, limit, page_size):
    """Fetch up to ``limit`` works with OpenAlex cursor pagination."""
    works = []
    total_matches = None
    pages = 0
    cursor = "*"
    seen_cursors = set()
    status = "ok"
    while len(works) < limit and cursor and cursor not in seen_cursors:
        seen_cursors.add(cursor)
        params = dict(base_params)
        params["per_page"] = str(min(
            page_size, OPENALEX_MAX_PAGE_SIZE, limit - len(works)
        ))
        params["cursor"] = cursor
        params = client.add_identity(params)
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        raw = client.fetch(url)
        if not raw:
            status = client.unavailable or "no response"
            break
        pages += 1
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            status = "unreadable JSON response"
            break
        meta = payload.get("meta") or {}
        if total_matches is None:
            try:
                total_matches = int(meta.get("count"))
            except (TypeError, ValueError):
                total_matches = None
        batch = payload.get("results") or []
        works.extend(batch[:limit - len(works)])
        next_cursor = meta.get("next_cursor")
        if not batch or not next_cursor:
            break
        cursor = next_cursor
    return works, total_matches, pages, status


def openalex_type_filter(types, include_preprints):
    if types == "review":
        values = ["review", "article"]
    else:
        values = ["article", "review"]
        if include_preprints:
            values.append("preprint")
    return "|".join(values)


def search_openalex(
        client, query, from_year, to_year, limit, types, sort, page_size=100,
        include_preprints=False):
    filters = [
        "is_paratext:false",
        f"type:{openalex_type_filter(types, include_preprints)}",
    ]
    if from_year:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year:
        filters.append(f"to_publication_date:{to_year}-12-31")
    params = {
        "search": query,
        "filter": ",".join(filters),
        "select": OPENALEX_WORK_FIELDS,
    }
    if sort == "cited":
        params["sort"] = "-cited_by_count"
    raw_works, total, pages, status = fetch_openalex_pages(
        client, params, limit=limit, page_size=page_size,
    )
    result = SearchResult(
        database="openalex", query=query, api_query=query,
        filters=params["filter"], sort=sort, total_matches=total,
        pages=pages, status=status,
    )
    for work in raw_works:
        if types == "review" and work.get("type") != "review" and not re.search(
                r"meta-analy|systematic review|umbrella review|scoping review|review",
                work.get("title") or "", re.I):
            result.exclusions["not a review"] += 1
            continue
        result.hits.append(parse_openalex_work(work))
    return result


# ---------------------------------------------------------------- PubMed

def pubmed_term(query, from_year, to_year, types):
    term = query
    if types == "review":
        term += " AND (systematic review[pt] OR meta-analysis[pt] OR review[pt])"
    if from_year or to_year:
        term += f" AND ({from_year or 1800}[dp] : {to_year or 3000}[dp])"
    return term


def parse_pubmed_articles(raw_xml):
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return None
    output = []
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//PMID") or "").strip()
        title_element = article.find(".//ArticleTitle")
        title = "".join(title_element.itertext()).strip() if title_element is not None else ""
        journal = article.findtext(".//Journal/Title") or ""
        year = article.findtext(".//PubDate/Year") or (
            article.findtext(".//PubDate/MedlineDate") or ""
        )[:4]
        try:
            year = int(year)
        except ValueError:
            year = None
        abstract = " ".join(
            "".join(element.itertext()).strip()
            for element in article.findall(".//Abstract/AbstractText")
        )
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            last_name = author.findtext("LastName")
            first_name = author.findtext("ForeName")
            if last_name:
                authors.append(
                    f"{first_name} {last_name}".strip() if first_name else last_name
                )
        doi = None
        for element in article.findall("./MedlineCitation/Article/ELocationID"):
            if element.get("EIdType") == "doi" and element.text:
                doi = norm_doi(element.text)
        if not doi:
            for identifier in article.findall("./PubmedData/ArticleIdList/ArticleId"):
                if identifier.get("IdType") == "doi" and identifier.text:
                    doi = norm_doi(identifier.text)
        publication_types = [
            element.text or ""
            for element in article.findall(".//PublicationTypeList/PublicationType")
        ]
        is_retracted = "Retracted Publication" in publication_types
        is_review = bool(
            {"Review", "Systematic Review", "Meta-Analysis"} & set(publication_types)
        )
        output.append({
            "doi": doi,
            "pmid": pmid or None,
            "openalex": None,
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal,
            "source_type": "journal",
            "type": "review" if is_review else "article",
            "abstract": abstract,
            "cited_by_count": None,
            "oa_url": None,
            "is_retracted": is_retracted,
            "is_preprint": False,
            "pub_types": publication_types,
            "peer_review_status": "not_independently_verified",
            "_source": "pubmed",
        })
    return output


def search_pubmed(
        query, from_year, to_year, limit, types, page_size=100,
        sort="relevance"):
    term = pubmed_term(query, from_year, to_year, types)
    api_sort = PUBMED_SORT_VALUES[sort]
    result = SearchResult(
        database="pubmed", query=query, api_query=term,
        filters="publication-date" if from_year or to_year else "none",
        sort=api_sort,
    )
    retstart = 0
    effective_limit = min(limit, PUBMED_MAX_RESULTS)
    while retstart < effective_limit:
        retmax = min(page_size, effective_limit - retstart)
        params = {
            "db": "pubmed", "term": term, "retstart": str(retstart),
            "retmax": str(retmax), "retmode": "json", "sort": api_sort,
        }
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" +
            urllib.parse.urlencode(params)
        )
        raw = get(url)
        if not raw:
            result.status = "PubMed ESearch unavailable"
            break
        try:
            search_payload = json.loads(raw).get("esearchresult", {})
        except json.JSONDecodeError:
            result.status = "unreadable PubMed ESearch response"
            break
        if result.total_matches is None:
            try:
                result.total_matches = int(search_payload.get("count", 0))
            except (TypeError, ValueError):
                result.total_matches = None
        ids = search_payload.get("idlist") or []
        if not ids:
            break
        fetch_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" +
            urllib.parse.urlencode({
                "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
            })
        )
        raw_xml = get(fetch_url)
        if not raw_xml:
            result.status = "PubMed EFetch unavailable"
            break
        articles = parse_pubmed_articles(raw_xml)
        if articles is None:
            result.status = "unreadable PubMed EFetch response"
            break
        result.hits.extend(articles)
        result.pages += 1
        retstart += len(ids)
        if len(ids) < retmax or (
                result.total_matches is not None and retstart >= result.total_matches):
            break
    if limit > PUBMED_MAX_RESULTS and result.status == "ok":
        result.status = f"capped at PubMed ESearch limit ({PUBMED_MAX_RESULTS})"
    return result


# ------------------------------------------------------ publication eligibility

def candidate_eligibility(
        hit, include_preprints=False, include_conference_papers=False,
        policy="strict"):
    """Return ``(eligible, reason)`` under a transparent index-based policy."""
    journal = (hit.get("journal") or "").lower()
    if any(venue in journal for venue in TERTIARY_VENUES):
        return False, "tertiary source"
    if hit.get("is_preprint"):
        if include_preprints:
            hit["publication_eligibility"] = "preprint; not peer reviewed"
            return True, "preprint explicitly included"
        return False, "preprint"

    if hit.get("_source") == "openalex":
        work_type = hit.get("type")
        source_type = hit.get("source_type")
        if source_type == "conference" or work_type == "proceedings-article":
            if not include_conference_papers:
                return False, "conference paper not enabled"
            hit["publication_eligibility"] = "conference-paper candidate"
            return True, "eligible conference candidate"
        if work_type not in ("article", "review"):
            return False, f"OpenAlex type {work_type or 'missing'}"
        if policy == "strict" and source_type != "journal":
            return False, f"OpenAlex source type {source_type or 'missing'}"
        if policy == "broad" and source_type not in ("journal", "", None):
            return False, f"OpenAlex source type {source_type}"
        hit["publication_eligibility"] = "journal-indexed candidate"
        return True, "eligible journal candidate"

    if hit.get("_source") == "opencitations":
        work_type = (hit.get("type") or "").lower().replace("_", " ").replace("-", " ")
        if work_type not in {"journal article", "review", "article"}:
            return False, f"OpenCitations type {work_type or 'missing'}"
        if policy == "strict" and not hit.get("journal"):
            return False, "OpenCitations venue missing"
        hit["publication_eligibility"] = "OpenCitations journal-metadata candidate"
        return True, "eligible OpenCitations candidate"

    publication_types = set(hit.get("pub_types") or [])
    excluded = publication_types & PUBMED_EXCLUDED_TYPES
    if excluded:
        return False, "PubMed non-evidence type: " + ", ".join(sorted(excluded))
    if policy == "strict" and not publication_types & PUBMED_EVIDENCE_TYPES:
        return False, "no eligible PubMed publication type"
    hit["publication_eligibility"] = "PubMed journal-indexed candidate"
    return True, "eligible PubMed candidate"


def filter_candidates(
        hits, include_preprints=False, include_conference_papers=False,
        policy="strict"):
    accepted = []
    exclusions = Counter()
    for hit in hits:
        eligible, reason = candidate_eligibility(
            hit,
            include_preprints=include_preprints,
            include_conference_papers=include_conference_papers,
            policy=policy,
        )
        if eligible:
            accepted.append(hit)
        else:
            exclusions[reason] += 1
    return accepted, exclusions


# ------------------------------------------------------------- citation chasing


def _pid_doi(value):
    match = re.search(r"(?:^|\s)doi:([^\s]+)", value or "", re.I)
    return norm_doi(match.group(1)) if match else None


def _opencitations_authors(value):
    authors = []
    for author in (value or "").split(";"):
        author = re.sub(r"\s*\[[^]]*\]\s*$", "", author).strip()
        if author:
            authors.append(author)
    return authors


def parse_opencitations_metadata(record):
    doi = _pid_doi(record.get("id"))
    year_match = re.match(r"(\d{4})", record.get("pub_date") or "")
    venue = re.sub(r"\s*\[[^]]*\]\s*$", "", record.get("venue") or "").strip()
    return {
        "doi": doi,
        "pmid": None,
        "openalex": None,
        "title": (record.get("title") or "").strip(),
        "authors": _opencitations_authors(record.get("author")),
        "year": int(year_match.group(1)) if year_match else None,
        "journal": venue,
        "source_type": "journal" if venue else None,
        "type": (record.get("type") or "").strip().lower(),
        "abstract": "",
        "cited_by_count": None,
        "oa_url": None,
        "is_retracted": False,
        "is_preprint": "preprint" in (record.get("type") or "").lower(),
        "peer_review_status": "not_independently_verified",
        "_source": "opencitations",
    }


class OpenCitationsClient:
    """Second citation-graph provider using the official Index and Meta APIs."""

    def __init__(self, token=None, retries=3):
        self.token = token
        self.retries = retries
        self.unavailable = None

    @property
    def enabled(self):
        return self.unavailable is None

    def fetch(self, url):
        if not self.enabled:
            return None
        headers = {"authorization": self.token} if self.token else {}
        try:
            return http_get(
                url, service="opencitations",
                min_interval=OPENCITATIONS_MIN_INTERVAL,
                retries=self.retries, extra_headers=headers,
            )
        except ServiceUnavailable as exc:
            self.unavailable = exc.reason
            sys.stderr.write(f"  {exc}\n")
            return None

    def graph_dois(self, doi, direction):
        operation = "references" if direction == "backward" else "citations"
        identifier = urllib.parse.quote("doi:" + doi, safe=":/")
        url = f"https://api.opencitations.net/index/v2/{operation}/{identifier}"
        raw = self.fetch(url)
        if raw is None:
            return None, url
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError:
            self.unavailable = "unreadable Index JSON response"
            return None, url
        if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], list):
            rows = rows[0]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            self.unavailable = "unexpected Index JSON shape"
            return None, url
        field = "cited" if direction == "backward" else "citing"
        dois = ordered_unique([
            _pid_doi(row.get(field)) for row in rows if _pid_doi(row.get(field))
        ])
        return dois, url

    def metadata(self, dois):
        output = []
        for start in range(0, len(dois), 40):
            chunk = dois[start:start + 40]
            identifiers = "__".join("doi:" + doi for doi in chunk)
            encoded = urllib.parse.quote(identifiers, safe=":/_")
            url = f"https://api.opencitations.net/meta/v1/metadata/{encoded}"
            raw = self.fetch(url)
            if raw is None:
                return None
            try:
                rows = json.loads(raw)
            except json.JSONDecodeError:
                self.unavailable = "unreadable Meta JSON response"
                return None
            if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], list):
                rows = rows[0]
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                self.unavailable = "unexpected Meta JSON shape"
                return None
            output.extend(rows)
        return output


def opencitations_citations(client, entry, seed_label, direction, limit, chase_sort):
    doi = norm_doi(entry.get("doi"))
    if not doi:
        return SearchResult(
            database="opencitations", query=seed_label, api_query=seed_label,
            filters="citation seed", sort=chase_sort,
            status="OpenCitations fallback requires a DOI",
            citation_direction=direction,
        )
    dois, api_url = client.graph_dois(doi, direction)
    if dois is None:
        return SearchResult(
            database="opencitations", query=seed_label, api_query=api_url,
            filters=f"{direction} citation graph", sort=chase_sort,
            status=client.unavailable or "OpenCitations Index unavailable",
            citation_direction=direction,
        )
    records = client.metadata(dois[:max(limit * 3, limit)])
    if records is None:
        return SearchResult(
            database="opencitations", query=seed_label, api_query=api_url,
            filters=f"{direction} citation graph; {len(dois)} DOI(s)",
            sort=chase_sort, total_matches=len(dois), pages=1,
            status=client.unavailable or "OpenCitations Meta unavailable",
            citation_direction=direction,
        )
    hits = rank_chase_hits(
        [parse_opencitations_metadata(record) for record in records], chase_sort
    )[:limit]
    for hit in hits:
        hit["_citation_direction"] = direction
        hit["_citation_seed"] = seed_label
    return SearchResult(
        database="opencitations", query=seed_label, api_query=api_url,
        filters=f"{direction} citation graph; metadata resolved {len(records)}/{len(dois)}",
        sort=chase_sort, hits=hits, total_matches=len(dois), pages=1,
        status="ok", citation_direction=direction,
    )

def ledger_seed(ledger, token):
    normalized_doi = norm_doi(token)
    lowered = token.lower()
    for entry in ledger["entries"]:
        if entry.get("key", "").lower() == lowered:
            return entry
        if entry.get("doi") and entry["doi"] == normalized_doi:
            return entry
        if entry.get("pmid") and str(entry["pmid"]) == token:
            return entry
        if (short_openalex_id(entry.get("openalex")) and
                short_openalex_id(entry.get("openalex")) == short_openalex_id(token)):
            return entry
    if short_openalex_id(token):
        return {"key": short_openalex_id(token), "openalex": short_openalex_id(token)}
    if normalized_doi and normalized_doi.startswith("10."):
        return {"key": normalized_doi, "doi": normalized_doi}
    if token.isdigit():
        return {"key": token, "pmid": token}
    return None


def openalex_seed_identifier(entry):
    if short_openalex_id(entry.get("openalex")):
        return short_openalex_id(entry["openalex"])
    if entry.get("doi"):
        return "doi:" + entry["doi"]
    if entry.get("pmid"):
        return "pmid:" + str(entry["pmid"])
    return None


def fetch_openalex_seed(client, entry):
    identifier = openalex_seed_identifier(entry)
    if not identifier:
        return None
    encoded_identifier = urllib.parse.quote(identifier, safe=":/")
    params = client.add_identity({
        "select": OPENALEX_WORK_FIELDS + ",referenced_works",
    })
    url = (
        "https://api.openalex.org/works/" + encoded_identifier + "?" +
        urllib.parse.urlencode(params)
    )
    raw = client.fetch(url, latch=False)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def rank_chase_hits(hits, chase_sort):
    if chase_sort == "recent":
        return sorted(
            hits,
            key=lambda hit: (
                hit.get("year") or 0, hit.get("cited_by_count") or 0,
            ),
            reverse=True,
        )
    return sorted(
        hits,
        key=lambda hit: (
            hit.get("cited_by_count") or 0, hit.get("year") or 0,
        ),
        reverse=True,
    )


def backward_citations(
        client, seed_work, seed_label, limit, pool, page_size, chase_sort):
    referenced_ids = ordered_unique([
        short_openalex_id(value)
        for value in seed_work.get("referenced_works") or []
        if short_openalex_id(value)
    ])
    scanned_ids = referenced_ids[:pool]
    raw_works = []
    pages = 0
    status = "ok"
    for start in range(0, len(scanned_ids), 100):
        chunk = scanned_ids[start:start + 100]
        params = {
            "filter": "openalex:" + "|".join(chunk),
            "select": OPENALEX_WORK_FIELDS,
        }
        works, _, chunk_pages, chunk_status = fetch_openalex_pages(
            client, params, limit=len(chunk), page_size=min(page_size, 100),
        )
        raw_works.extend(works)
        pages += chunk_pages
        if chunk_status != "ok":
            status = chunk_status
            break
    hits = rank_chase_hits(
        [parse_openalex_work(work) for work in raw_works], chase_sort
    )[:limit]
    for hit in hits:
        hit["_citation_direction"] = "backward"
        hit["_citation_seed"] = seed_label
    return SearchResult(
        database="openalex", query=seed_label,
        api_query=f"referenced_works({seed_label})",
        filters=f"openalex IDs from seed; scanned {len(scanned_ids)}/{len(referenced_ids)}",
        sort=chase_sort, hits=hits, total_matches=len(referenced_ids),
        pages=pages, status=status, citation_direction="backward",
    )


def forward_citations(
        client, seed_work, seed_label, limit, page_size, chase_sort):
    seed_id = short_openalex_id(seed_work.get("id"))
    if not seed_id:
        return SearchResult(
            database="openalex", query=seed_label,
            api_query=f"cites({seed_label})", filters="cites:unresolved",
            sort=chase_sort, status="seed has no OpenAlex ID",
        )
    params = {
        "filter": f"cites:{seed_id}",
        "select": OPENALEX_WORK_FIELDS,
        "sort": (
            "-publication_date" if chase_sort == "recent"
            else "-cited_by_count"
        ),
    }
    raw_works, total, pages, status = fetch_openalex_pages(
        client, params, limit=limit, page_size=page_size,
    )
    hits = [parse_openalex_work(work) for work in raw_works]
    for hit in hits:
        hit["_citation_direction"] = "forward"
        hit["_citation_seed"] = seed_label
    return SearchResult(
        database="openalex", query=seed_label,
        api_query=f"cites:{seed_id}", filters=f"cites:{seed_id}",
        sort=chase_sort, hits=hits, total_matches=total,
        pages=pages, status=status, citation_direction="forward",
    )


def chase_citations(
        client, ledger, tokens, direction, limit, pool, page_size, chase_sort,
        fallback_client=None, use_openalex=True):
    results = []
    for token in tokens:
        entry = ledger_seed(ledger, token)
        if not entry:
            results.append(SearchResult(
                database="openalex", query=token, api_query=token,
                filters="citation seed", sort=chase_sort,
                status=(
                    "seed not found in ledger and is not a DOI, PMID, or OpenAlex ID"
                ),
            ))
            continue
        seed_label = entry.get("key") or token
        requested_directions = [
            item for item in ("backward", "forward")
            if direction in (item, "both")
        ]
        provider_results = []
        if use_openalex:
            seed_work = fetch_openalex_seed(client, entry)
            if not seed_work:
                for requested in requested_directions:
                    provider_results.append(SearchResult(
                        database="openalex", query=seed_label, api_query=token,
                        filters="citation seed", sort=chase_sort,
                        status="could not resolve citation seed in OpenAlex",
                        citation_direction=requested,
                    ))
            else:
                if "backward" in requested_directions:
                    provider_results.append(backward_citations(
                        client, seed_work, seed_label, limit, pool, page_size, chase_sort,
                    ))
                if "forward" in requested_directions:
                    provider_results.append(forward_citations(
                        client, seed_work, seed_label, limit, page_size, chase_sort,
                    ))
            results.extend(provider_results)
        completed_directions = {
            result.citation_direction for result in provider_results
            if result.status == "ok" and (result.pages > 0 or result.total_matches == 0)
        }
        if fallback_client is not None:
            for requested in requested_directions:
                if requested not in completed_directions:
                    results.append(opencitations_citations(
                        fallback_client, entry, seed_label, requested, limit, chase_sort,
                    ))
    return results


# ---------------------------------------------------------------- ledger + log

def load_ledger(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"created": time.strftime("%Y-%m-%d"), "entries": []}


def provenance_for(hit, query, angle, method):
    provenance = {
        "query": query,
        "angle": angle,
        "source": hit["_source"],
        "method": method,
    }
    if hit.get("_citation_direction"):
        provenance["direction"] = hit["_citation_direction"]
    if hit.get("_citation_seed"):
        provenance["seed"] = hit["_citation_seed"]
    return provenance


def merge(ledger, hits, query, angle, method="keyword"):
    by_id = {}
    for e in ledger["entries"]:
        if e.get("doi"):
            by_id["doi:" + e["doi"]] = e
        if e.get("pmid"):
            by_id["pmid:" + str(e["pmid"])] = e
        if short_openalex_id(e.get("openalex")):
            by_id["openalex:" + short_openalex_id(e["openalex"])] = e
    added, updated = 0, 0
    for h in hits:
        identifiers = []
        if h.get("doi"):
            identifiers.append("doi:" + h["doi"])
        if h.get("pmid"):
            identifiers.append("pmid:" + str(h["pmid"]))
        if short_openalex_id(h.get("openalex")):
            identifiers.append("openalex:" + short_openalex_id(h["openalex"]))
        if not identifiers:
            continue
        e = next((by_id[ident] for ident in identifiers if ident in by_id), None)
        provenance = provenance_for(h, query, angle, method)
        if e:
            # fill gaps
            for k in (
                    "doi", "pmid", "openalex", "abstract", "oa_url", "journal",
                    "year", "cited_by_count", "pub_types",
                    "publication_eligibility", "peer_review_status", "source_type"):
                if not e.get(k) and h.get(k):
                    e[k] = h[k]
            if h.get("is_retracted"):
                e["is_retracted"] = True
            if provenance not in e.setdefault("found_by", []):
                e["found_by"].append(provenance)
            for ident in identifiers:
                by_id[ident] = e
            updated += 1
        else:
            e = {k: v for k, v in h.items() if not k.startswith("_")}
            e["key"] = make_key(e["authors"], e["year"], e["title"])
            e["found_by"] = [provenance]
            e["status"] = "candidate"
            ledger["entries"].append(e)
            for ident in identifiers:
                by_id[ident] = e
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
    print(
        f"{'key':<26} {'year':>4} {'cites':>6} {'type':<8} "
        f"{'flags':<10} title | journal"
    )
    for e in rows:
        flags = (
            ("RETRACTED " if e.get("is_retracted") else "") +
            ("PREPRINT " if e.get("is_preprint") else "")
        )
        flags = flags.strip() or ("verified" if e.get("status") == "verified" else "")
        cites = e.get("cited_by_count")
        print(
            f"{e['key']:<26} {str(e.get('year') or ''):>4} "
            f"{str(cites if cites is not None else '-'):>6} "
            f"{(e.get('type') or '')[:8]:<8} {flags:<10} {e['title'][:80]} | "
            f"{(e.get('journal') or '')[:40]}"
        )


def markdown_cell(value):
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def append_search_log(
        path, result, angle, method, accepted, added, updated, exclusions):
    if not path:
        return
    needs_header = not os.path.exists(path) or os.path.getsize(path) == 0
    combined_exclusions = result.exclusions + exclusions
    exclusion_text = "; ".join(
        f"{reason}={count}" for reason, count in sorted(combined_exclusions.items())
    ) or "none"
    timestamp = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ).isoformat()
    row = [
        timestamp, result.database, method, angle, result.query, result.api_query,
        result.filters, result.sort, result.total_matches, result.retrieved,
        len(accepted), added, updated, result.pages, exclusion_text, result.status,
    ]
    with open(path, "a", encoding="utf-8") as handle:
        if needs_header:
            handle.write(
                "# Search log\n\n"
                "Generated automatically by `find_papers.py`. Total matches is the "
                "database-reported count; retrieved is the number inspected locally.\n\n"
                "| UTC timestamp | database | method | angle | requested query/seed | "
                "API query | filters | sort | total matches | retrieved | accepted | "
                "new | updated | pages | exclusions | status |\n"
                "|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|\n"
            )
        handle.write(
            "| " + " | ".join(markdown_cell(value) for value in row) + " |\n"
        )


def stable_angle_id(value):
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    if value and value[0].isdigit():
        value = "angle-" + value
    return value or "unassigned"


def append_search_manifest(
        path, result, angle, angle_id, lane, method, accepted, added, updated,
        exclusions):
    if not path:
        return
    target = os.path.abspath(path)
    if os.path.exists(target):
        with open(target, encoding="utf-8") as stream:
            manifest = json.load(stream)
        if manifest.get("schema_version") != 1 or not isinstance(
                manifest.get("records"), list):
            raise ValueError(f"unsupported search manifest: {target}")
    else:
        manifest = {"schema_version": 1, "records": []}
    combined_exclusions = result.exclusions + exclusions
    timestamp = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ).isoformat()
    direction = result.citation_direction
    record = {
        "timestamp": timestamp,
        "database": result.database,
        "provider": result.database,
        "method": method,
        "citation_direction": direction,
        "angle": angle,
        "angle_id": angle_id,
        "lane": "citation-chase" if direction else lane,
        "requested_query_or_seed": result.query,
        "api_query": result.api_query,
        "filters": result.filters,
        "sort": result.sort,
        "total_matches": result.total_matches,
        "retrieved": result.retrieved,
        "accepted": len(accepted),
        "new": added,
        "updated": updated,
        "pages": result.pages,
        "exclusions": dict(sorted(combined_exclusions.items())),
        "status": result.status,
        "completed": result.status == "ok" and (
            result.pages > 0 or result.total_matches == 0
        ),
    }
    manifest["records"].append(record)
    manifest["updated_at"] = timestamp
    atomic_write_json(target, manifest)


def parse_sources(value):
    sources = ordered_unique([
        source.strip().lower() for source in value.split(",") if source.strip()
    ])
    unknown = set(sources) - {"openalex", "pubmed"}
    if unknown:
        raise ValueError("unknown source(s): " + ", ".join(sorted(unknown)))
    if not sources:
        raise ValueError("at least one source is required")
    return sources


def parse_citation_providers(value):
    providers = ordered_unique([
        provider.strip().lower() for provider in value.split(",") if provider.strip()
    ])
    unknown = set(providers) - {"openalex", "opencitations"}
    if unknown:
        raise ValueError(
            "unknown citation provider(s): " + ", ".join(sorted(unknown))
        )
    if not providers:
        raise ValueError("at least one citation provider is required")
    return providers


def build_query_plan(shared_queries, openalex_queries, pubmed_queries, sources):
    plan = []
    seen = set()
    for query in shared_queries:
        for source in sources:
            pair = (source, query)
            if pair not in seen:
                seen.add(pair)
                plan.append(pair)
    for source, queries in (
            ("openalex", openalex_queries), ("pubmed", pubmed_queries)):
        if source not in sources:
            continue
        for query in queries:
            pair = (source, query)
            if pair not in seen:
                seen.add(pair)
                plan.append(pair)
    return plan


def process_result(result, ledger, args, method):
    accepted, exclusions = filter_candidates(
        result.hits,
        include_preprints=args.include_preprints,
        include_conference_papers=args.include_conference_papers,
        policy=args.publication_policy,
    )
    before_length = len(ledger["entries"])
    added, updated = merge(
        ledger, accepted, result.query, args.angle, method=method,
    )
    fresh = ledger["entries"][before_length:]
    append_search_log(
        args.search_log, result, args.angle, method, accepted,
        added, updated, exclusions,
    )
    append_search_manifest(
        args.search_manifest, result, args.angle, args.angle_id, args.lane,
        method, accepted, added, updated, exclusions,
    )
    total = result.total_matches if result.total_matches is not None else "?"
    print(
        f"\n## {result.database} {method}: {result.query} "
        f"({total} total; {result.retrieved} retrieved across {result.pages} "
        f"page(s); {len(accepted)} accepted; {added} new, {updated} already in ledger)"
    )
    if result.status != "ok":
        print(f"  status: {result.status}")
    if exclusions or result.exclusions:
        combined = result.exclusions + exclusions
        print("  excluded: " + ", ".join(
            f"{reason}={count}" for reason, count in sorted(combined.items())
        ))
    print_table(fresh)
    if args.abstracts:
        for entry in fresh:
            print(
                f"\n[{entry['key']}] {entry['title']}\n  "
                f"{entry.get('abstract') or '(no abstract available)'}\n"
            )


def build_parser():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--query", "-q", action="append", default=[],
        help="query sent to every enabled database (repeatable)",
    )
    ap.add_argument(
        "--openalex-query", action="append", default=[],
        help="OpenAlex-only query (repeatable)",
    )
    ap.add_argument(
        "--pubmed-query", action="append", default=[],
        help="PubMed-only query; PubMed field syntax is allowed (repeatable)",
    )
    ap.add_argument(
        "--angle", default="",
        help="evidence angle stored in the ledger and search log",
    )
    ap.add_argument(
        "--angle-id",
        help="stable machine ID for the evidence angle (default: slug of --angle)",
    )
    ap.add_argument(
        "--lane",
        choices=["reviews", "primary", "foundational", "recent", "contrary-null", "general"],
        default="general",
        help="search-funnel lane recorded in search-manifest.json",
    )
    ap.add_argument("--from-year", type=int)
    ap.add_argument("--to-year", type=int)
    ap.add_argument(
        "--limit", type=int, default=100,
        help="total records retrieved per query per database (default: 100)",
    )
    ap.add_argument(
        "--page-size", type=int, default=50,
        help="records requested per API page (default: 50)",
    )
    ap.add_argument(
        "--types", choices=["all", "review"], default="all",
        help="review = reviews/meta-analyses only",
    )
    ap.add_argument(
        "--sort", choices=["relevance", "cited"], default="relevance",
        help="OpenAlex sort",
    )
    ap.add_argument(
        "--pubmed-sort",
        choices=["relevance", "pub-date", "first-author", "journal"],
        default="relevance",
    )
    ap.add_argument("--sources", default="openalex,pubmed")
    ap.add_argument(
        "--mailto", default=os.environ.get("OPENALEX_MAILTO", "").strip() or None,
        help="contact address for OpenAlex courtesy metadata",
    )
    ap.add_argument(
        "--openalex-api-key",
        default=os.environ.get("OPENALEX_API_KEY", "").strip() or None,
        help="optional OpenAlex API key (default: OPENALEX_API_KEY)",
    )
    ap.add_argument("--openalex-retries", type=int, default=3)
    ap.add_argument(
        "--citation-providers", default="openalex,opencitations",
        help="ordered citation-graph providers (default: openalex,opencitations)",
    )
    ap.add_argument(
        "--opencitations-token",
        default=os.environ.get("OPENCITATIONS_TOKEN", "").strip() or None,
        help="optional OpenCitations access token",
    )
    ap.add_argument("--opencitations-retries", type=int, default=3)
    ap.add_argument("--include-preprints", action="store_true")
    ap.add_argument(
        "--include-conference-papers", action="store_true",
        help="include OpenAlex article records hosted by conference sources",
    )
    ap.add_argument(
        "--publication-policy", choices=["strict", "broad"], default="strict",
        help="strict requires explicit eligible publication types (default: strict)",
    )
    ap.add_argument("--ledger", default="sources.json")
    ap.add_argument(
        "--search-log",
        help="automatic markdown log (default: search_log.md beside ledger)",
    )
    ap.add_argument("--no-search-log", action="store_true")
    ap.add_argument(
        "--search-manifest",
        help="structured log (default: search-manifest.json beside ledger)",
    )
    ap.add_argument("--no-search-manifest", action="store_true")
    ap.add_argument(
        "--chase", action="append", default=[], metavar="KEY_OR_ID",
        help="ledger key, DOI, PMID, or OpenAlex ID to citation-chase",
    )
    ap.add_argument(
        "--chase-direction", choices=["backward", "forward", "both"],
        default="both",
    )
    ap.add_argument(
        "--chase-limit", type=int, default=50,
        help="records retrieved per seed and direction",
    )
    ap.add_argument(
        "--chase-pool", type=int, default=500,
        help="maximum backward references inspected per seed",
    )
    ap.add_argument("--chase-sort", choices=["cited", "recent"], default="cited")
    ap.add_argument("--show", action="store_true", help="print the ledger and exit")
    ap.add_argument(
        "--abstracts", action="store_true",
        help="print abstracts of newly added entries",
    )
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if (args.limit <= 0 or args.page_size <= 0 or args.chase_limit <= 0 or
            args.chase_pool <= 0):
        ap.error(
            "--limit, --page-size, --chase-limit, and --chase-pool must be positive"
        )
    if args.from_year and args.to_year and args.from_year > args.to_year:
        ap.error("--from-year cannot be later than --to-year")
    try:
        sources = parse_sources(args.sources)
        citation_providers = parse_citation_providers(args.citation_providers)
    except ValueError as exc:
        ap.error(str(exc))

    ledger = load_ledger(args.ledger)
    if args.show:
        print_table(ledger["entries"])
        print(f"\n{len(ledger['entries'])} entries in {args.ledger}")
        return 0

    has_search = bool(args.query or args.openalex_query or args.pubmed_query)
    if not has_search and not args.chase:
        print_table(ledger["entries"])
        print(f"\n{len(ledger['entries'])} entries in {args.ledger}")
        return 0
    if args.openalex_query and "openalex" not in sources:
        ap.error("--openalex-query requires openalex in --sources")
    if args.pubmed_query and "pubmed" not in sources:
        ap.error("--pubmed-query requires pubmed in --sources")
    if args.no_search_log:
        args.search_log = None
    elif not args.search_log:
        ledger_directory = os.path.dirname(os.path.abspath(args.ledger))
        args.search_log = os.path.join(ledger_directory, "search_log.md")
    if args.no_search_manifest:
        args.search_manifest = None
    elif not args.search_manifest:
        ledger_directory = os.path.dirname(os.path.abspath(args.ledger))
        args.search_manifest = os.path.join(ledger_directory, "search-manifest.json")
    args.angle_id = args.angle_id or stable_angle_id(args.angle)
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.angle_id):
        ap.error("--angle-id must match [a-z][a-z0-9-]*")

    client = OpenAlexClient(
        mailto=args.mailto, retries=args.openalex_retries,
        api_key=args.openalex_api_key,
    )
    opencitations_client = (
        OpenCitationsClient(
            token=args.opencitations_token, retries=args.opencitations_retries
        )
        if "opencitations" in citation_providers else None
    )
    uses_openalex = (
        ("openalex" in sources and bool(args.query or args.openalex_query))
        or ("openalex" in citation_providers and bool(args.chase))
    )
    if uses_openalex and not client.mailto and not client.api_key:
        sys.stderr.write(
            "Note: no --openalex-api-key / OPENALEX_API_KEY or --mailto / "
            "OPENALEX_MAILTO set; anonymous OpenAlex limits may be stricter.\n"
        )

    plan = build_query_plan(
        args.query, args.openalex_query, args.pubmed_query, sources,
    )
    for database, query in plan:
        if database == "openalex":
            if not client.enabled:
                result = SearchResult(
                    database="openalex", query=query, api_query=query,
                    filters="not run", sort=args.sort,
                    status=client.unavailable or "OpenAlex disabled",
                )
            else:
                result = search_openalex(
                    client, query, args.from_year, args.to_year, args.limit,
                    args.types, args.sort, page_size=args.page_size,
                    include_preprints=args.include_preprints,
                )
        else:
            result = search_pubmed(
                query, args.from_year, args.to_year, args.limit, args.types,
                page_size=args.page_size, sort=args.pubmed_sort,
            )
        process_result(result, ledger, args, method="keyword")

    if args.chase:
        results = chase_citations(
            client, ledger, args.chase, args.chase_direction,
            args.chase_limit, args.chase_pool, args.page_size, args.chase_sort,
            fallback_client=opencitations_client,
            use_openalex="openalex" in citation_providers,
        )
        for result in results:
            method = "citation"
            if result.citation_direction:
                method = result.citation_direction + "-citation"
            process_result(result, ledger, args, method=method)

    if uses_openalex and not client.enabled:
        print(
            f"\nNOTE: OpenAlex became unavailable — {client.unavailable}. "
            "Completed PubMed searches remain in the ledger and log."
        )

    retracted = [e for e in ledger["entries"] if e.get("is_retracted")]
    if retracted:
        print(
            f"\nWARNING: {len(retracted)} retracted paper(s) in ledger — do not cite "
            "except to discuss the retraction: " +
            ", ".join(e["key"] for e in retracted)
        )
    atomic_write_json(args.ledger, ledger)
    print(f"\nLedger: {len(ledger['entries'])} entries → {args.ledger}")
    if args.search_log:
        print(f"Search log → {args.search_log}")
    if args.search_manifest:
        print(f"Search manifest → {args.search_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
