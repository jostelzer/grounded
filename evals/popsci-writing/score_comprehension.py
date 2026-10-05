#!/usr/bin/env python3
"""
Comprehension and calibration quiz: does the article leave readers right, and
right about how sure anyone is?

A quiz setter that sees the synthesis, fact bank and reader questions, but not
the article, writes `quiz.json`: multiple-choice items on what a reader should
take away, including how sure the evidence is and common misreadings. Cold
readers who see only the article answer each item, or `N` when the article does
not say. This script scores accuracy, coverage and calibration per reader and
per article:

    {"schema_version": 1, "items": [
      {"id": "K1", "kind": "method", "prompt": "...",
       "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
       "answer": "B", "basis": ["F7"]},
      {"id": "K2", "kind": "certainty", "prompt": "How sure ...?",
       "options": {"A": "Well established", "B": "Probable", "C": "Uncertain",
                   "D": "No evidence either way"},
       "answer": "C", "certainty_order": ["A", "B", "C", "D"], "basis": ["C3"]}]}

    answers file: {"reader": "skeptical engineer", "article": "review.md",
                   "answers": {"K1": "B", "K2": "N"}}

    python3 scripts/score_comprehension.py --quiz quiz.json answers-*.json \
        --report comprehension.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "grounded" / "scripts"))
from artifact_io import atomic_write_json

KINDS = {"fact", "method", "mechanism", "magnitude", "certainty", "misconception",
         "unknown", "meaning"}
NOT_SAID = "N"


def validate_quiz(quiz):
    errors = []
    items = quiz.get("items")
    if quiz.get("schema_version") != 1:
        errors.append("quiz schema_version must be 1")
    if not isinstance(items, list) or len(items) < 8:
        return errors + ["a quiz needs at least 8 items"]
    seen = set()
    kinds = set()
    for item in items:
        iid = item.get("id")
        if not iid or iid in seen:
            errors.append(f"item id {iid!r} missing or repeated")
        seen.add(iid)
        kinds.add(item.get("kind"))
        options = item.get("options") or {}
        if item.get("kind") not in KINDS:
            errors.append(f"{iid}: kind must be one of {', '.join(sorted(KINDS))}")
        if not 3 <= len(options) <= 5 or NOT_SAID in options:
            errors.append(f"{iid}: give 3–5 options, none labelled {NOT_SAID}")
        if item.get("answer") not in options:
            errors.append(f"{iid}: answer is not one of its options")
        if not item.get("basis"):
            errors.append(f"{iid}: name the F/C entries that establish the answer")
        if item.get("kind") == "certainty":
            order = item.get("certainty_order") or []
            if sorted(order) != sorted(options):
                errors.append(f"{iid}: certainty_order must rank every option, strongest first")
    for needed in ("method", "certainty"):
        if needed not in kinds:
            errors.append(f"the quiz needs at least one {needed} item")
    return errors


def score(quiz, answer_sets):
    items = {item["id"]: item for item in quiz["items"]}
    readers = []
    for answers in answer_sets:
        given = answers.get("answers", {})
        tally = {"correct": 0, "wrong": 0, "not_said": 0, "missing": 0,
                 "overconfident": 0, "underconfident": 0, "misconception_chosen": 0}
        by_kind = {}
        wrong_items = []
        for iid, item in items.items():
            choice = str(given.get(iid, "")).strip().upper()
            kind_tally = by_kind.setdefault(item["kind"], [0, 0])
            kind_tally[1] += 1
            if not choice:
                tally["missing"] += 1
            elif choice == NOT_SAID:
                tally["not_said"] += 1
                wrong_items.append(iid)
            elif choice == item["answer"]:
                tally["correct"] += 1
                kind_tally[0] += 1
            else:
                tally["wrong"] += 1
                wrong_items.append(iid)
                if item["kind"] == "certainty" and choice in item.get("certainty_order", []):
                    order = item["certainty_order"]
                    if order.index(choice) < order.index(item["answer"]):
                        tally["overconfident"] += 1
                    else:
                        tally["underconfident"] += 1
                if item["kind"] == "misconception":
                    tally["misconception_chosen"] += 1
        total = len(items)
        readers.append({
            "reader": answers.get("reader", "?"),
            "article": answers.get("article", "?"),
            "accuracy": round(tally["correct"] / total, 3),
            "not_said_rate": round(tally["not_said"] / total, 3),
            **tally,
            "by_kind": {k: f"{c}/{n}" for k, (c, n) in sorted(by_kind.items())},
            "missed_items": wrong_items,
        })
    articles = {}
    for r in readers:
        a = articles.setdefault(r["article"], {"readers": 0, "accuracy": 0.0,
                                               "not_said_rate": 0.0, "overconfident": 0,
                                               "underconfident": 0, "misconception_chosen": 0})
        a["readers"] += 1
        a["accuracy"] += r["accuracy"]
        a["not_said_rate"] += r["not_said_rate"]
        for key in ("overconfident", "underconfident", "misconception_chosen"):
            a[key] += r[key]
    for a in articles.values():
        a["accuracy"] = round(a["accuracy"] / a["readers"], 3)
        a["not_said_rate"] = round(a["not_said_rate"] / a["readers"], 3)
    return {"items": len(items), "readers": readers, "articles": articles}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiz", required=True)
    parser.add_argument("answers", nargs="*", help="reader answer files")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    quiz = json.loads(Path(args.quiz).read_text())
    errors = validate_quiz(quiz)
    if errors:
        for item in errors:
            print("  ! " + item)
        print("HARD FAIL: the quiz is not usable.")
        return 1
    if not args.answers:
        print(f"quiz valid: {len(quiz['items'])} items")
        return 0
    result = score(quiz, [json.loads(Path(p).read_text()) for p in args.answers])
    if args.report:
        atomic_write_json(args.report, result)
    for name, a in result["articles"].items():
        print(f"{name}: accuracy {a['accuracy']:.0%} over {a['readers']} reader(s); "
              f"not covered {a['not_said_rate']:.0%}; overconfident {a['overconfident']}, "
              f"underconfident {a['underconfident']}, misreadings chosen "
              f"{a['misconception_chosen']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
