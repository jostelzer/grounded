#!/usr/bin/env python3
"""
Get the full text of an open-access paper as plain text, for close reading of key sources.

Tries, in order:
  1. Europe PMC full-text XML (covers PubMed Central open-access articles) — best quality.
  2. The open-access URL recorded by OpenAlex in the ledger (PDF or landing page) — printed for
     you to open with a web-fetch tool, since PDF parsing needs non-standard libraries.

Usage:
  python3 fetch_fulltext.py --ledger sources.json --key Kuyken2022effectiveness --out Kuyken2022.txt
  python3 fetch_fulltext.py --doi 10.1136/ebmental-2021-300396 --out paper.txt
  python3 fetch_fulltext.py --ledger sources.json --key X --sections   # print section headings only

Prints the word count and the section headings found, so you can decide whether to read all of it.
If no full text is available, says so and prints the abstract from the ledger instead.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "scientific-review-skill/1.0 (mailto:review-skill@example.org)"


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"  fetch failed: {url[:90]} ({e})\n")
        return None


def europepmc_pmcid(doi):
    q = urllib.parse.quote(f'DOI:"{doi}"')
    raw = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=lite")
    if not raw:
        return None
    for r in json.loads(raw).get("resultList", {}).get("result", []):
        if r.get("pmcid") and r.get("isOpenAccess") == "Y":
            return r["pmcid"]
    for r in json.loads(raw).get("resultList", {}).get("result", []):
        if r.get("pmcid"):
            return r["pmcid"]
    return None


def europepmc_fulltext(pmcid):
    raw = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
    if not raw or "<article" not in raw:
        return None, []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None, []
    body = root.find(".//body")
    if body is None:
        return None, []
    chunks, headings = [], []
    for el in body.iter():
        if el.tag == "title":
            t = "".join(el.itertext()).strip()
            if t:
                headings.append(t)
                chunks.append(f"\n## {t}\n")
        elif el.tag == "p":
            t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
            if t:
                chunks.append(t + "\n")
    abstract = root.find(".//abstract")
    abs_text = re.sub(r"\s+", " ", "".join(abstract.itertext())).strip() if abstract is not None else ""
    text = ("## Abstract\n" + abs_text + "\n" if abs_text else "") + "".join(chunks)
    return text, headings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger")
    ap.add_argument("--key")
    ap.add_argument("--doi")
    ap.add_argument("--out")
    ap.add_argument("--sections", action="store_true", help="print section headings only")
    args = ap.parse_args()

    entry = None
    doi = args.doi
    if args.ledger and args.key:
        ledger = json.load(open(args.ledger))
        entry = next((e for e in ledger["entries"] if e["key"] == args.key), None)
        if entry is None:
            sys.exit(f"key {args.key} not in ledger")
        doi = entry.get("doi")
    if not doi:
        sys.exit("need --doi or --ledger/--key with a DOI")
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip().lower())

    pmcid = europepmc_pmcid(doi)
    text, headings = (None, [])
    if pmcid:
        text, headings = europepmc_fulltext(pmcid)
    if text:
        words = len(text.split())
        print(f"Full text via Europe PMC ({pmcid}): {words} words, {len(headings)} sections")
        for h in headings[:40]:
            print("  -", h)
        if args.sections:
            return
        if args.out:
            open(args.out, "w").write(f"# {entry['title'] if entry else doi}\nDOI: {doi}\nSource: Europe PMC {pmcid}\n\n" + text)
            print(f"Saved to {args.out}")
        else:
            print(text)
        return

    print("No open-access full text available via Europe PMC.")
    oa = entry.get("oa_url") if entry else None
    if oa:
        print(f"OpenAlex open-access location (open it with a web-fetch tool): {oa}")
    else:
        print(f"Try the publisher page: https://doi.org/{doi}  (may be paywalled)")
    if entry and entry.get("abstract"):
        print("\nAbstract from ledger:\n" + entry["abstract"])


if __name__ == "__main__":
    main()
