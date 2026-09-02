#!/usr/bin/env python3
"""
Evidence store for claim-level verification: fetch and cache the text behind a DOI.

Acquisition is a tiered waterfall, each result cached with provenance so a source
is fetched at most once per store:

  full text (best first)
    1. Europe PMC fullTextXML (JATS; version of record)         — highest quality
    2. An open-access location listed by OpenAlex (HTML only)   — publisher or
       repository copy; the OA version label is recorded because an accepted
       manuscript is not the version of record. PDF-only locations are recorded
       as a hint for manual escalation, never parsed here.
  abstract floor (union; something is nearly always available)
    3. OpenAlex abstract_inverted_index
    4. Crossref abstract
    5. Europe PMC core abstractText

Never fetches from pirate archives. Landing pages that answer with an anti-bot
challenge or paywall-denial language are rejected (fail closed), not stored.

Store layout: <store>/<doi-slug>.txt (the text) + <store>/<doi-slug>.meta.json
(tier, source, version, url, sha256, word count, retrieval date, notes).
"""
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import fetch_fulltext
from artifact_io import atomic_write_json, atomic_write_text, sha256_bytes
from audit_fulltexts import CHALLENGE_PATTERNS, DENIAL_PATTERNS, _VisibleHtml
from grounded_metadata import user_agent

UA = user_agent()
MIN_FULLTEXT_WORDS = 700


def norm_doi(doi):
    doi = (doi or "").strip().lower()
    doi = urllib.parse.unquote(doi)
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)


def doi_slug(doi):
    return re.sub(r"[^a-z0-9]+", "-", norm_doi(doi)).strip("-")


def _get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — any failure just moves the waterfall on
        return None


BINARY_SIGNATURES = ("PK\x03\x04", "%PDF-", "\x1f\x8b")


def binary_body(text):
    """A response that is a zip/docx, PDF, or gzip stream decoded as text.

    Such bodies pass the word-count floor with garbage and were once stored
    as full text; they are rejected here so the store never holds bytes a
    judge cannot read."""
    head = (text or "")[:8]
    return any(head.startswith(sig) for sig in BINARY_SIGNATURES) or \
        "[Content_Types].xml" in (text or "")[:4000]


def blocked_page(text):
    if binary_body(text):
        return "binary_body"
    lower = (text or "").lower()
    if any(re.search(p, lower, re.I) for p in CHALLENGE_PATTERNS):
        return "challenge_page"
    if any(re.search(p, lower, re.I) for p in DENIAL_PATTERNS):
        return "access_denied"
    return None


def deinvert(inverted):
    positions = {}
    for word, idxs in (inverted or {}).items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def html_to_text(html_body):
    parser = _VisibleHtml()
    try:
        parser.feed(html_body)
    except Exception:  # noqa: BLE001 — malformed HTML falls through to nothing
        return ""
    return re.sub(r"\n{3,}", "\n\n", "\n".join(parser.parts)).strip()


def openalex_work(doi):
    raw = _get("https://api.openalex.org/works/https://doi.org/"
               + urllib.parse.quote(norm_doi(doi), safe="/"))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _oa_locations(work):
    locations = []
    best = work.get("best_oa_location")
    if best:
        locations.append(best)
    for loc in work.get("locations") or []:
        if loc and loc.get("is_oa") and loc not in locations:
            locations.append(loc)
    return locations


def fetch_fulltext_tier(doi, work=None):
    """Return (text, meta) for the best available full text, or (None, notes)."""
    notes = []
    pmcid = fetch_fulltext.europepmc_pmcid(norm_doi(doi))
    if pmcid:
        text, headings = fetch_fulltext.europepmc_fulltext(pmcid)
        if text and len(text.split()) >= MIN_FULLTEXT_WORDS:
            return text, {
                "tier": "fulltext", "source": "europepmc", "version": "publishedVersion",
                "url": f"https://europepmc.org/articles/{pmcid}",
                "sections": len(headings),
            }
        notes.append(f"europepmc {pmcid}: no usable body")

    work = work or openalex_work(doi)
    pdf_hint = None
    for loc in _oa_locations(work or {}):
        url = loc.get("landing_page_url")
        if loc.get("pdf_url") and not pdf_hint:
            pdf_hint = loc["pdf_url"]
        if not url:
            continue
        body = _get(url)
        if not body:
            notes.append(f"unreachable: {url[:80]}")
            continue
        blocked = blocked_page(body)
        if blocked:
            notes.append(f"{blocked}: {url[:80]}")
            continue
        text = html_to_text(body)
        if len(text.split()) >= MIN_FULLTEXT_WORDS:
            return text, {
                "tier": "fulltext", "source": "oa_location",
                "version": loc.get("version") or "unknown", "url": url,
                "pdf_url_hint": pdf_hint,
            }
        notes.append(f"too little text ({len(text.split())} words): {url[:80]}")
    if pdf_hint:
        notes.append(f"pdf_only_hint: {pdf_hint}")
    return None, notes


def fetch_abstract_tier(doi, work=None):
    """Union abstract fetcher. Returns (text, meta) or (None, notes)."""
    notes = []
    work = work or openalex_work(doi)
    if work and work.get("abstract_inverted_index"):
        text = deinvert(work["abstract_inverted_index"])
        if text:
            return text, {"tier": "abstract", "source": "openalex",
                          "url": work.get("id", "")}
    notes.append("openalex: no abstract")

    raw = _get("https://api.crossref.org/works/"
               + urllib.parse.quote(norm_doi(doi), safe=""))
    if raw:
        try:
            abstract = json.loads(raw)["message"].get("abstract") or ""
        except (ValueError, KeyError):
            abstract = ""
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", abstract)).strip()
        if text:
            return text, {"tier": "abstract", "source": "crossref",
                          "url": "https://doi.org/" + norm_doi(doi)}
    notes.append("crossref: no abstract")

    raw = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
               + urllib.parse.quote(f'DOI:"{norm_doi(doi)}"')
               + "&resultType=core&format=json")
    if raw:
        try:
            results = json.loads(raw)["resultList"]["result"]
        except (ValueError, KeyError):
            results = []
        for r in results:
            text = re.sub(r"\s+", " ",
                          re.sub(r"<[^>]+>", " ", r.get("abstractText") or "")).strip()
            if text:
                return text, {"tier": "abstract", "source": "europepmc",
                              "url": f"https://europepmc.org/abstract/MED/{r.get('id', '')}"}
    notes.append("europepmc: no abstract")
    return None, notes


def acquire(doi, store, want_fulltext=False, refresh=False):
    """Fetch (or reuse) evidence for one DOI. Returns the meta dict.

    Cached abstract-tier evidence is upgraded in place when full text is asked
    for later; anything else cached is reused as-is.
    """
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    slug = doi_slug(doi)
    text_path = store / f"{slug}.txt"
    meta_path = store / f"{slug}.meta.json"

    cached = None
    if meta_path.exists() and not refresh:
        cached = json.loads(meta_path.read_text())
        upgradable = want_fulltext and cached.get("tier") != "fulltext" \
            and not cached.get("fulltext_exhausted")
        if not upgradable:
            return cached

    notes = []
    work = openalex_work(doi)
    text, info = (None, None)
    if want_fulltext:
        text, result = fetch_fulltext_tier(doi, work=work)
        if text is None:
            notes.extend(result)
        else:
            info = result
    if text is None and cached is not None:
        # The upgrade found no full text: keep what the store already holds
        # rather than replacing a real abstract with an empty record.
        cached["fulltext_exhausted"] = True
        cached.setdefault("notes", []).extend(notes)
        atomic_write_json(meta_path, cached)
        return cached
    if text is None:
        text, result = fetch_abstract_tier(doi, work=work)
        if text is None:
            notes.extend(result)
        else:
            info = result
            if want_fulltext:
                info["fulltext_exhausted"] = True

    meta = {
        "doi": norm_doi(doi), "slug": slug,
        "retrieved": time.strftime("%Y-%m-%d"),
        "words": len(text.split()) if text else 0,
        "notes": notes,
        **({"tier": "none"} if text is None else info),
    }
    if text is not None:
        meta["sha256"] = sha256_bytes(text.encode("utf-8"))
        atomic_write_text(text_path, text)
    atomic_write_json(meta_path, meta)
    return meta


def store_text(doi, store, text, info):
    """Write one evidence record (text + meta) into the store."""
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    slug = doi_slug(doi)
    meta = {
        "doi": norm_doi(doi), "slug": slug,
        "retrieved": time.strftime("%Y-%m-%d"),
        "words": len(text.split()), "notes": [],
        "sha256": sha256_bytes(text.encode("utf-8")),
        **info,
    }
    atomic_write_text(store / f"{slug}.txt", text)
    atomic_write_json(store / f"{slug}.meta.json", meta)
    return meta


def seed_local_evidence(dois, store, ledger_path=None, fulltext_dir=None,
                        manifest_path=None):
    """Seed the store from what the review already read, before any network.

    Full texts retained in ``fulltexts/`` (authenticated by
    ``fulltext-manifest.json`` when given) enter at the fulltext tier; the
    ledger's stored abstracts enter at the abstract tier. Returns
    {doi: tier} for every DOI seeded or upgraded.
    """
    store = Path(store)
    by_doi = {}
    if ledger_path:
        ledger = json.loads(Path(ledger_path).read_text())
        for entry in ledger.get("entries", []):
            if entry.get("doi"):
                by_doi[norm_doi(entry["doi"])] = entry
    valid_paths = {}
    if manifest_path:
        manifest = json.loads(Path(manifest_path).read_text())
        for record in manifest.get("records", []):
            if record.get("status") == "valid_fulltext" and record.get("doi"):
                valid_paths[norm_doi(record["doi"])] = record.get("path")
    seeded = {}
    for doi in dois:
        doi = norm_doi(doi)
        _text, existing = load_evidence(doi, store)
        current = (existing or {}).get("tier", "none")
        entry = by_doi.get(doi)
        if fulltext_dir and current != "fulltext":
            candidates = []
            if doi in valid_paths and valid_paths[doi]:
                candidates.append(Path(fulltext_dir) / valid_paths[doi])
            if entry and entry.get("key") and not manifest_path:
                candidates.append(Path(fulltext_dir) / f"{entry['key']}.txt")
            for path in candidates:
                if path.is_file():
                    text = path.read_text(encoding="utf-8", errors="replace")
                    if len(text.split()) >= MIN_FULLTEXT_WORDS:
                        store_text(doi, store, text, {
                            "tier": "fulltext", "source": "local-fulltext",
                            "version": "as-read", "url": str(path)})
                        seeded[doi] = "fulltext"
                        break
            if doi in seeded:
                continue
        if current == "none" and entry:
            abstract = re.sub(r"\s+", " ", str(entry.get("abstract") or "")).strip()
            if len(abstract.split()) >= 30:
                store_text(doi, store, abstract, {
                    "tier": "abstract", "source": "ledger",
                    "url": "https://doi.org/" + doi})
                seeded[doi] = "abstract"
    return seeded


def load_evidence(doi, store):
    """Return (text, meta) for a DOI already in the store, else (None, None)."""
    store = Path(store)
    slug = doi_slug(doi)
    meta_path = store / f"{slug}.meta.json"
    text_path = store / f"{slug}.txt"
    if not meta_path.exists():
        return None, None
    meta = json.loads(meta_path.read_text())
    text = text_path.read_text() if text_path.exists() else None
    return text, meta


def normalize_for_match(text):
    """Normalization under which a judge's quote must appear verbatim."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[‐-―−]", "-", text)
    text = re.sub(r"[^a-z0-9%=<>.,;:()\[\]/'\"+-]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def quote_in_text(quote, text):
    return bool(quote) and normalize_for_match(quote) in normalize_for_match(text)
