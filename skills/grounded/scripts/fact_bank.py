#!/usr/bin/env python3
"""
Popsci story notes: small verified facts a writer may use freely.

`synthesis.md` holds the calibrated claims that answer the question. A feature
also needs the material around them: how each anchor study was run, what a term
means, how a mechanism works, everyday scale, the authors' own written words.
`facts.md` records that material, one checkable fact per entry:

    ### F7. Most babies wore a movement monitor on the ankle.
    - kind: method
    - quote: [@Stremler2013effect] "verbatim passage from the stored text"
    - answers: Q4
    - supports: C3

Every key carries a verbatim quote from the evidence store, every number in the
fact sentence sits inside a quote, and any words the sentence puts in quotation
marks must appear in a quote. Findings about effects, associations or
certainty stay in the synthesis, where strength and contrary evidence live.

    python3 scripts/fact_bank.py check --facts facts.md --ledger sources.json \
        --evidence evidence/ --synthesis synthesis.md --size medium
"""
import argparse
import json
import re
import sys
from pathlib import Path

import claim_evidence
import synthesis_quotes
from artifact_io import atomic_write_json
from review_config import FACT_RANGES

FACT_RE = re.compile(r"^###\s+(F\d+)\.\s+(.+)$", re.M)
KINDS = {
    "method", "definition", "mechanism", "scale", "background", "context",
    "detail", "voice", "practice",
}
QUOTED_RE = re.compile(r"[“\"]([^”\"]{4,})[”\"]")
ID_LIST_RE = re.compile(r"\b([QCF]\d+)\b")
# Digits inside names (omega-3, COVID-19, PM2.5, H2O) are not quantities.
NAME_NUMBER_RE = re.compile(
    r"\b[A-Za-z]+[-‐]?\d+(?:\.\d+)?\b|"
    r"\b(?:stage|phase|type|grade|class|step|figure|table|panel|level|tier|group|category|"
    r"version|chapter|part|question)\s+\d+\b", re.I)


def quantities(sentence):
    return synthesis_quotes.sentence_numbers(NAME_NUMBER_RE.sub(" ", sentence))


def parse_facts(text):
    """Every F-entry with its sentence, kind, keys, quotes and links."""
    matches = list(FACT_RE.finditer(text))
    facts = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        quotes = [(key, " ".join(q.split()))
                  for key, q in synthesis_quotes.QUOTE_RE.findall(block)]
        keys = []
        for key in synthesis_quotes.KEY_RE.findall(
                synthesis_quotes._field(block, "source")) + [k for k, _q in quotes]:
            if key not in keys:
                keys.append(key)
        facts.append({
            "id": match.group(1),
            "sentence": match.group(2).strip(),
            "kind": synthesis_quotes._field(block, "kind").strip().lower(),
            "keys": keys,
            "quotes": quotes,
            "answers": ID_LIST_RE.findall(synthesis_quotes._field(block, "answers")),
            "supports": ID_LIST_RE.findall(synthesis_quotes._field(block, "supports")),
        })
    return facts


def quotes_by_doi(text, ledger):
    """DOI → [(fact id, quote)], merged with synthesis quotes by the extractor."""
    mapping = synthesis_quotes.key_to_doi(ledger)
    out = {}
    for fact in parse_facts(text):
        for key, quote in fact["quotes"]:
            doi = mapping.get(key)
            if doi:
                out.setdefault(doi, []).append((fact["id"], quote))
    return out


def check_facts(text, store, ledger, synthesis_text=None, size=None):
    """Errors, warnings and metrics for the fact bank."""
    errors, warnings = [], []
    mapping = synthesis_quotes.key_to_doi(ledger)
    facts = parse_facts(text)
    if not facts:
        errors.append("fact bank has no ### F1. entries")
    claim_ids = None
    if synthesis_text is not None:
        claim_ids = {c["id"] for c in synthesis_quotes.parse_claims(synthesis_text)}
    seen_ids, seen_sentences = set(), {}
    kinds = {}
    store_cache = {}
    for fact in facts:
        fid = fact["id"]
        if fid in seen_ids:
            errors.append(f"{fid} is defined twice")
        seen_ids.add(fid)
        normalized = " ".join(fact["sentence"].lower().split())
        if normalized in seen_sentences:
            errors.append(f"{fid} repeats {seen_sentences[normalized]} word for word")
        seen_sentences.setdefault(normalized, fid)
        if fact["kind"] not in KINDS:
            errors.append(f"{fid}: kind must be one of {', '.join(sorted(KINDS))}")
        kinds[fact["kind"]] = kinds.get(fact["kind"], 0) + 1
        if not fact["keys"]:
            errors.append(f"{fid} has no source key")
        quoted_keys = {k for k, _q in fact["quotes"]}
        for key in fact["keys"]:
            if key not in mapping:
                errors.append(f"{fid} cites @{key}, which is not in the ledger")
                continue
            if key not in quoted_keys:
                errors.append(f"{fid} cites @{key} without a quote line")
        for key, quote in fact["quotes"]:
            doi = mapping.get(key)
            if not doi:
                continue
            if doi not in store_cache:
                store_cache[doi] = claim_evidence.load_evidence(doi, store)[0]
            evidence = store_cache[doi]
            if not evidence:
                errors.append(f"{fid}/@{key}: no evidence text in the store — run "
                              "`verify_claims.py seed` first")
            elif not claim_evidence.quote_in_text(quote, evidence):
                errors.append(f"{fid}/@{key}: quote is not verbatim in the stored "
                              f"text: “{quote[:60]}…”")
        all_quotes = " … ".join(q for _k, q in fact["quotes"])
        for number in quantities(fact["sentence"]):
            if number.rstrip("%") not in all_quotes.replace(",", ""):
                errors.append(f"{fid}: the number {number} appears in none of its quotes")
        for phrase in QUOTED_RE.findall(fact["sentence"]):
            if not claim_evidence.quote_in_text(phrase, all_quotes):
                errors.append(f"{fid}: quoted words “{phrase[:40]}” are not in its quotes")
        if fact["kind"] == "voice" and not QUOTED_RE.search(fact["sentence"]):
            warnings.append(f"{fid}: a voice fact should carry the authors' words in "
                            "quotation marks")
        if claim_ids is not None:
            for cid in [i for i in fact["supports"] if i.startswith("C")]:
                if cid not in claim_ids:
                    errors.append(f"{fid} supports {cid}, which is not in the synthesis")
    if size:
        low, high = FACT_RANGES[size]
        if len(facts) < low:
            warnings.append(f"{len(facts)} facts; a {size} feature usually needs "
                            f"{low}–{high} to explain methods, terms and scale")
        elif len(facts) > high:
            warnings.append(f"{len(facts)} facts exceed the {size} guide of {low}–{high}; "
                            "keep what the reader's questions need")
    for needed in ("method", "definition"):
        if facts and not kinds.get(needed):
            warnings.append(f"no {needed} facts: a lay reader usually needs some")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {"facts": len(facts), "kinds": dict(sorted(kinds.items())),
                    "keys": len({k for f in facts for k in f["keys"]})},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--facts", required=True)
    check.add_argument("--ledger", required=True)
    check.add_argument("--evidence", required=True)
    check.add_argument("--synthesis")
    check.add_argument("--size", choices=tuple(FACT_RANGES))
    check.add_argument("--report")
    args = parser.parse_args(argv)
    ledger = json.loads(Path(args.ledger).read_text())
    synthesis = Path(args.synthesis).read_text() if args.synthesis else None
    result = check_facts(Path(args.facts).read_text(), args.evidence, ledger,
                         synthesis, args.size)
    if args.report:
        atomic_write_json(args.report, result)
    m = result["metrics"]
    print(f"{m['facts']} facts over {m['keys']} sources; kinds: "
          + ", ".join(f"{k} {v}" for k, v in m["kinds"].items()))
    for item in result["warnings"]:
        print("  ~ " + item)
    for item in result["errors"]:
        print("  ! " + item)
    if result["errors"]:
        print("HARD FAIL: the fact bank is not quote-anchored.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
