#!/usr/bin/env python3
"""
Compare what a draft's paragraphs do with published popular-science features.

`references/popsci-feature-corpus.json` labels every body paragraph of
published features with one function: scene, orientation, method, finding,
explanation, context, complication, voice, practical or payoff. A labelling
agent applies the same scheme to a draft and saves

    {"article": "review.md", "paragraphs": [
       {"label": "scene", "has_number": false, "has_quote": false, "approx_words": 80}, ...]}

This script places the draft inside the corpus range for each measure (share of
each function, where the first method and finding appear, the longest run of
complication paragraphs, how many paragraphs carry numbers, paragraph length)
and flags measures outside the corpus's 10th–90th percentile. These are
diagnostics for an editor, not quotas: a flagged measure is a question to
answer from the draft, not a number to hit.

    python3 scripts/paragraph_profile.py --corpus references/popsci-feature-corpus.json \
        --labels paragraph-labels.json --report paragraph-profile.json
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "grounded" / "scripts"))
from artifact_io import atomic_write_json

LABELS = ("scene", "orientation", "method", "finding", "explanation", "context",
          "complication", "voice", "practical", "payoff")
# Journalists' interview quotes have no counterpart in a literature-based
# feature, so the voice share is reported but never flagged.
UNFLAGGED = {"share_voice"}


def measures(paragraphs):
    n = len(paragraphs)
    if not n:
        return {}
    labels = [p.get("label") for p in paragraphs]
    out = {f"share_{label}": round(labels.count(label) / n, 3) for label in LABELS}

    def first(label):
        return round(labels.index(label) / n, 3) if label in labels else 1.0

    out["first_method_position"] = first("method")
    out["first_finding_position"] = first("finding")
    run = best = 0
    for label in labels:
        run = run + 1 if label == "complication" else 0
        best = max(best, run)
    out["longest_complication_run"] = best
    out["numeric_paragraph_share"] = round(
        sum(bool(p.get("has_number")) for p in paragraphs) / n, 3)
    words = [int(p.get("approx_words") or 0) for p in paragraphs]
    out["mean_paragraph_words"] = round(statistics.mean(words), 1)
    out["paragraphs"] = n
    return out


def _percentile(values, q):
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return round(values[low] + (values[high] - values[low]) * (position - low), 3)


def corpus_ranges(corpus):
    per_article = [measures(a["paragraphs"]) for a in corpus["articles"] if a.get("paragraphs")]
    ranges = {}
    for key in per_article[0]:
        values = [m[key] for m in per_article]
        ranges[key] = {"p10": _percentile(values, 0.1), "p25": _percentile(values, 0.25),
                       "median": _percentile(values, 0.5), "p75": _percentile(values, 0.75),
                       "p90": _percentile(values, 0.9)}
    return ranges, len(per_article)


def profile(corpus, labels):
    ranges, count = corpus_ranges(corpus)
    draft = measures(labels["paragraphs"])
    flags = []
    for key, value in draft.items():
        r = ranges.get(key)
        if not r or key in UNFLAGGED or key == "paragraphs":
            continue
        if value < r["p10"] or value > r["p90"]:
            side = "below" if value < r["p10"] else "above"
            flags.append(f"{key} = {value} is {side} the corpus 10th–90th percentile "
                         f"({r['p10']}–{r['p90']}; median {r['median']})")
    return {"corpus_articles": count, "draft": draft, "corpus": ranges, "flags": flags}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--labels", help="the draft's paragraph labels")
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    corpus = json.loads(Path(args.corpus).read_text())
    if not args.labels:
        ranges, count = corpus_ranges(corpus)
        print(f"{count} corpus articles")
        for key, r in ranges.items():
            print(f"  {key}: median {r['median']} (10th–90th {r['p10']}–{r['p90']})")
        return 0
    labels = json.loads(Path(args.labels).read_text())
    unknown = sorted({p.get("label") for p in labels.get("paragraphs", [])} - set(LABELS))
    if unknown:
        print("  ! unknown paragraph label(s): " + ", ".join(map(str, unknown)))
        return 1
    result = profile(corpus, labels)
    if args.report:
        atomic_write_json(args.report, result)
    print(f"{result['draft'].get('paragraphs', 0)} paragraphs against "
          f"{result['corpus_articles']} published features")
    for flag in result["flags"]:
        print("  ~ " + flag)
    if not result["flags"]:
        print("  within the corpus range on every measure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
