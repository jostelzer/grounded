#!/usr/bin/env python3
"""
Reader questions: what a curious reader will want to know, planned before search.

A fresh agent that sees only the research request writes `reader-questions.md`
before the literature search. Research must then answer each core question
from the fact bank or synthesis, or record why it cannot:

    Reader: a parent of a four-month-old, no science training

    ### Q3. How do researchers know how long a baby actually slept?
    - type: how-we-know
    - priority: core
    - answered-by: F7, F8, C2
    - status: answered

`--stage plan` checks the list itself; `--stage draft` (before writing) also
requires every core question to be answered, partly answered with what is
missing, or unanswerable with a reason, and checks the linked IDs exist.

    python3 scripts/reader_questions.py --questions reader-questions.md \
        --stage draft --facts facts.md --synthesis synthesis.md --size medium
"""
import argparse
import re
import sys
from pathlib import Path

import fact_bank
import synthesis_quotes
from artifact_io import atomic_write_json
from review_config import QUESTION_RANGES

QUESTION_RE = re.compile(r"^###\s+(Q\d+)\.\s+(.+)$", re.M)
TYPES = {"what", "how-it-works", "how-we-know", "how-big", "meaning", "unknown",
         "background", "practical"}
REQUIRED_TYPES = ("how-it-works", "how-we-know", "how-big", "meaning", "unknown")
PRIORITIES = {"core", "useful", "optional"}
STATUS_RE = re.compile(r"^(open|answered|partial|unanswerable)\b\s*(?:[—–-]+\s*(.*))?$", re.S)


def parse_questions(text):
    reader = re.search(r"^Reader:\s*(.+)$", text, re.M)
    matches = list(QUESTION_RE.finditer(text))
    questions = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        status = synthesis_quotes._field(block, "status").strip()
        status_match = STATUS_RE.match(status) if status else None
        questions.append({
            "id": match.group(1),
            "question": match.group(2).strip(),
            "type": synthesis_quotes._field(block, "type").strip().lower(),
            "priority": synthesis_quotes._field(block, "priority").strip().lower(),
            "answered_by": fact_bank.ID_LIST_RE.findall(
                synthesis_quotes._field(block, "answered-by")),
            "status": status_match.group(1) if status_match else (status or "open"),
            "status_note": (status_match.group(2) or "").strip() if status_match else "",
        })
    return {"reader": reader.group(1).strip() if reader else "", "questions": questions}


def check_questions(text, stage="plan", facts_text=None, synthesis_text=None, size=None):
    errors, warnings = [], []
    parsed = parse_questions(text)
    questions = parsed["questions"]
    if not parsed["reader"]:
        errors.append("name the reader on a 'Reader:' line")
    if not questions:
        errors.append("no ### Q1. questions")
    seen = set()
    types = {}
    for q in questions:
        if q["id"] in seen:
            errors.append(f"{q['id']} is defined twice")
        seen.add(q["id"])
        if q["type"] not in TYPES:
            errors.append(f"{q['id']}: type must be one of {', '.join(sorted(TYPES))}")
        if q["priority"] not in PRIORITIES:
            errors.append(f"{q['id']}: priority must be core, useful or optional")
        types[q["type"]] = types.get(q["type"], 0) + 1
    for needed in REQUIRED_TYPES:
        if questions and not types.get(needed):
            errors.append(f"no '{needed}' question: a curious reader always asks one")
    if size:
        low, high = QUESTION_RANGES[size]
        if not low <= len(questions) <= high:
            warnings.append(f"{len(questions)} questions; {size} guide is {low}–{high}")
    known = set()
    if facts_text is not None:
        known |= {f["id"] for f in fact_bank.parse_facts(facts_text)}
    if synthesis_text is not None:
        known |= {c["id"] for c in synthesis_quotes.parse_claims(synthesis_text)}
    counts = {"answered": 0, "partial": 0, "unanswerable": 0, "open": 0}
    for q in questions:
        if q["status"] not in counts:
            errors.append(f"{q['id']}: status must be open, answered, partial or unanswerable")
            continue
        counts[q["status"]] += 1
        if stage == "draft":
            if q["priority"] == "core" and q["status"] == "open":
                errors.append(f"{q['id']} (core) is still open: answer it from the fact bank "
                              "or synthesis, or record why it cannot be answered")
            if q["status"] in {"answered", "partial"} and not q["answered_by"]:
                errors.append(f"{q['id']} is {q['status']} but names no F/C entries")
            if q["status"] in {"partial", "unanswerable"} and len(q["status_note"].split()) < 3:
                errors.append(f"{q['id']} is {q['status']}: say what is missing and why")
            for ref in q["answered_by"]:
                if known and ref not in known:
                    errors.append(f"{q['id']} names {ref}, which is not in the facts or synthesis")
    core = [q for q in questions if q["priority"] == "core"]
    if questions and len(core) > (len(questions) + 1) // 2 + 1:
        warnings.append(f"{len(core)} of {len(questions)} questions are core; when most "
                        "questions are core the article has no centre. Keep about half")
    answered_core = sum(q["status"] == "answered" for q in core)
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {"questions": len(questions), "core": len(core),
                    "core_answered": answered_core, "by_status": counts,
                    "by_type": dict(sorted(types.items()))},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--stage", choices=("plan", "draft"), default="plan")
    parser.add_argument("--facts")
    parser.add_argument("--synthesis")
    parser.add_argument("--size", choices=tuple(QUESTION_RANGES))
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    result = check_questions(
        Path(args.questions).read_text(), args.stage,
        Path(args.facts).read_text() if args.facts else None,
        Path(args.synthesis).read_text() if args.synthesis else None, args.size)
    if args.report:
        atomic_write_json(args.report, result)
    m = result["metrics"]
    print(f"{m['questions']} questions ({m['core']} core, {m['core_answered']} core answered); "
          + ", ".join(f"{k} {v}" for k, v in m["by_status"].items() if v))
    for item in result["warnings"]:
        print("  ~ " + item)
    for item in result["errors"]:
        print("  ! " + item)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
