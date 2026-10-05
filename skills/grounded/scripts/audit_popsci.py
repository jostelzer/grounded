#!/usr/bin/env python3
"""
Check that a popsci review went through its working steps.

Run before figures and again before release. It checks the records described in
`references/popsci-pipeline.md`: reader questions answered, quote-anchored story
notes, a draft with a readability profile, and a cold read with its repair
decisions. Missing or failing records are errors. Readability flags that remain
are warnings: questions for the writer, not gates. So is a revision that left
the article heavier than the first draft (`review_draft.v1.md`).

    python3 scripts/audit_popsci.py --case . --size medium --review review_draft.md \
        --report popsci-audit.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import fact_bank
import reader_questions
import readability_profile
from artifact_io import atomic_write_json
from review_config import POPSCI_TARGET_WORDS, WORD_BUDGETS, source_range


FIRST_DRAFT = "review_draft.v1.md"


def revision_weight(before, after, target):
    """Ways the cold-read revision made the article heavier than its first draft."""
    heavier = []
    if after["prose_words"] > before["prose_words"] * 1.03 and before["prose_words"] >= 0.9 * target:
        heavier.append(f"{after['prose_words'] - before['prose_words']} words longer")
    if after["sources_cited"] > before["sources_cited"] + 1:
        heavier.append(f"{after['sources_cited'] - before['sources_cited']} more sources cited")
    if after["limitation_sentences"] > before["limitation_sentences"]:
        heavier.append(f"{after['limitation_sentences'] - before['limitation_sentences']} more "
                       "sentences that limit or hedge")
    return heavier


def audit(case, size, review_name="review_draft.md", ledger_name="sources.json",
          evidence_name="evidence"):
    case = Path(case)
    errors, warnings, records = [], [], {}

    def need(name):
        path = case / name
        if not path.is_file():
            errors.append(f"missing {name}")
            records[name] = "missing"
            return None
        records[name] = "present"
        return path.read_text(encoding="utf-8")

    synthesis = need("synthesis.md")
    facts = need("facts.md")
    questions = need("reader-questions.md")
    if facts is not None:
        ledger_path, evidence = case / ledger_name, case / evidence_name
        if ledger_path.is_file() and evidence.is_dir():
            result = fact_bank.check_facts(facts, evidence, json.loads(ledger_path.read_text()),
                                           synthesis, size)
            records["facts.md"] = result["status"]
            errors += ["story notes: " + e for e in result["errors"]]
            warnings += ["story notes: " + w for w in result["warnings"]]
        else:
            errors.append(f"cannot check facts.md without {ledger_name} and {evidence_name}/")
    if questions is not None:
        result = reader_questions.check_questions(questions, "draft", facts, synthesis, size)
        records["reader-questions.md"] = result["status"]
        errors += ["reader questions: " + e for e in result["errors"]]
        warnings += ["reader questions: " + w for w in result["warnings"]]

    cold = need("cold-read.md")
    if cold is not None:
        readers = len(re.findall(r"^##\s+Reader\b", cold, re.M))
        if readers < 2:
            errors.append("cold-read.md needs two '## Reader' reports")
        if not re.search(r"^##\s+Repairs\b", cold, re.M):
            errors.append("cold-read.md needs a '## Repairs' section, even if it is empty")
        if "not independent" in cold.lower():
            warnings.append("the cold read was not independent; say so when delivering")

    review = need(review_name)
    if review is not None:
        result = readability_profile.profile(review)
        records["readability"] = result["status"]
        measures = result["measures"]
        warnings += ["readability: " + flag for flag in result["flags"]]
        if result["passages"].get("self_reference"):
            errors.append("the article talks about itself or the request: "
                          + result["passages"]["self_reference"][0]["text"])
        if measures:
            _low, high = WORD_BUDGETS["popsci"][size]
            target = POPSCI_TARGET_WORDS[size]
            if measures["prose_words"] < 0.8 * target:
                warnings.append(f"{measures['prose_words']} prose words against a target of about "
                                f"{target}: check which reader questions are still only partly "
                                "answered and what would make the piece more rewarding")
            if measures["prose_words"] > high:
                warnings.append(f"{measures['prose_words']} prose words; the {size} ceiling is "
                                f"{high}. Cut what belongs in the synthesis")
            first = case / FIRST_DRAFT
            if not first.is_file():
                warnings.append(f"no {FIRST_DRAFT}: keep the draft the cold readers saw, so the "
                                "revision can be compared with it")
            else:
                before = readability_profile.profile(first.read_text(encoding="utf-8"))["measures"]
                heavier = revision_weight(before, measures, target) if before else []
                records["revision"] = "heavier" if heavier else "no heavier"
                if heavier:
                    warnings.append("the revision made the article heavier than the first draft ("
                                    + "; ".join(heavier) + "): a revision cuts, merges and "
                                    "rewrites, and pays for anything it adds")
            cited_low, cited_high = source_range("popsci", size)
            if measures["sources_cited"] > cited_high:
                warnings.append(f"{measures['sources_cited']} sources cited; a {size} feature "
                                f"usually cites {cited_low}–{cited_high}. Check that each one "
                                "moves the explanation forward")
    return {"status": "pass" if not errors else "fail", "errors": errors,
            "warnings": warnings, "records": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", default=".")
    parser.add_argument("--size", choices=("small", "medium", "large"), required=True)
    parser.add_argument("--review", default="review_draft.md")
    parser.add_argument("--ledger", default="sources.json")
    parser.add_argument("--evidence", default="evidence")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    result = audit(args.case, args.size, args.review, args.ledger, args.evidence)
    if args.report:
        atomic_write_json(args.report, result)
    for item in result["warnings"]:
        print("  ~ " + item)
    for item in result["errors"]:
        print("  ! " + item)
    print(f"popsci working steps: {result['status']}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
