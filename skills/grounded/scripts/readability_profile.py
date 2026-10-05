#!/usr/bin/env python3
"""
Measure how hard a popular-science draft is to read, and point at the passages.

Accurate drafts fail readers in a few repeatable ways: too many numbers per
paragraph, statistics in running prose, a roll-call of studies, very long
sentences and paragraphs, and reflex caveats. This script counts those things
in the prose body (headline, standfirst, crossheads, tables, figures, captions
and the scope note are left out), compares them with what published features
do, and lists the worst passages so a writer can fix them. It reads no sources
and judges no facts: a flag is a question for the writer, not a verdict.

    python3 scripts/readability_profile.py --review review_draft.md \
        --report readability.json --reader-copy reader-copy.md

`--reader-copy` also writes the article without citations, for cold readers.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from artifact_io import atomic_write_json, atomic_write_text
from review_config import READABILITY_GUIDE

CITATION_RE = re.compile(
    r"\s*(?:\[@[^\]\n]+\]|\[[^\]\n]+\]\(https?://(?:dx\.)?doi\.org/[^)\s]+\))"
    r"(?:\s*[,;]\s*(?:\[@[^\]\n]+\]|\[[^\]\n]+\]\(https?://(?:dx\.)?doi\.org/[^)\s]+\)))*")
ONE_CITATION_RE = re.compile(
    r"\[@([^\]\n]+)\]|\[[^\]\n]+\]\((https?://(?:dx\.)?doi\.org/[^)\s]+)\)")
LINK_RE = re.compile(r"\[([^\]\n]+)\]\((?:https?://|#)[^)\s]*\)")
FIGURE_TOKEN_RE = re.compile(r"\{\{figure:[^}]+\}\}")
YEAR_RE = re.compile(r"\b(?:1[5-9]|20)\d\d\b")
from fact_bank import NAME_NUMBER_RE
NUMBER_RE = re.compile(r"(?<![\w.])[−-]?\d+(?:[.,]\d+)*%?")
STAT_TERMS = (
    r"confidence intervals?", r"\bCI\b", r"hazard ratios?", r"odds ratios?", r"relative risks?",
    r"risk ratios?", r"rate ratios?", r"standard deviations?", r"\bSD\b", r"\bp[- ]values?",
    r"\bp\s*[<=>]", r"standardi[sz]ed (?:mean )?differences?", r"effect sizes?", r"heterogeneity",
    r"\bI²", r"percentiles?", r"person-years", r"meta-regression", r"statistically significant",
    r"interquartile", r"\bIQR\b", r"credible intervals?",
)
STAT_RE = re.compile("|".join(STAT_TERMS), re.I)
LAB_UNIT_RE = re.compile(
    r"\b(?:mmol|millimoles?|micromoles?|µmol|micrograms?|nanograms?|µg|μg|ng|"
    r"nanometres?|nanometers?|micrometres?|micrometers?|µm|μm|mg/dL|mmol/L|kJ|pg|IU)\b")
HEDGE_RE = re.compile(
    r"\b(?:do(?:es)? not (?:establish|prove|show|demonstrate|mean|settle|supply|test)|"
    r"did not (?:establish|prove|show|settle|test|investigate)|is not an established|"
    r"neither [^.]{0,80}? (?:establish(?:es)?|show(?:s)?|investigated|tested)|cannot (?:say|show|tell|establish|diagnose|prove|"
    r"be (?:ruled out|excluded|shown))|can ?not be (?:shown|established)|"
    r"remains? (?:unclear|unknown|uncertain|unproven|untested)|it is (?:unclear|not known)|"
    r"not (?:been|yet) (?:shown|tested|established)|has not been (?:shown|tested|established)|"
    r"(?:leav(?:es?|ing)|left)\b[^.;]{0,90}?\b(?:unanswered|unresolved|untested|unsettled|unknown|open)|"
    r"remains? (?:the |an? )?(?:unanswered|unresolved|open)|did not (?:measure|report))\b",
    re.I)
NEGATION_RE = re.compile(
    r"\brather than\b|\binstead of\b|, not (?:a|an|the|just|simply|merely|only|as|by|for|in|to|"
    r"from|on)\b|\bnot (?:just|simply|merely|only) \w+[^.]{0,60}\bbut\b|"
    r"\b(?:is|are|was|were) not (?:a|an|the)\b", re.I)
SELF_REFERENCE_RE = re.compile(
    r"\b(?:this (?:review|article|piece|feature)|the (?:studies|trials|sources) (?:described|"
    r"reviewed|cited|covered) here|described here|reviewed here|as asked|the (?:user|request)|"
    r"the (?:pattern|scenario|night) in the question|by our (?:arithmetic|subtraction|sums?|"
    r"calculation)|our (?:arithmetic|subtraction|own sums?)|the article's own|"
    r"the (?:evidence|sources|studies|literature) (?:used|gathered|assembled|reviewed|cited) "
    r"here|this evidence set|the evidence set)\b", re.I)
ROLL_CALL_RE = re.compile(
    r"\b\d[\d,]*\s+(?:randomi[sz]ed\s+|controlled\s+|clinical\s+|observational\s+|earlier\s+|"
    r"small\s+|long-term\s+)*(?:trials?|studies|cohorts?|papers|experiments|reviews|"
    r"meta-analyses)\b", re.I)
SCOPE_NOTE_RE = re.compile(
    r"^\*\*(?:Scope|About this|How this (?:review|article)|Methods?\b)", re.I)
APPARATUS_HEADING_RE = re.compile(
    r"^#+\s*(?:Scope|About this|How this (?:review|article)|Methods?\b|Sources|References)", re.I)
APPARATUS_WORDS_RE = re.compile(
    r"\b(?:PubMed|OpenAlex|Crossref|narrative review|systematic review|searched on|"
    r"full texts?|abstracts? only)\b", re.I)


def _syllables(word):
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def strip_citations(text):
    text = CITATION_RE.sub("", text)
    text = FIGURE_TOKEN_RE.sub("the figure", text)
    return LINK_RE.sub(r"\1", text)


def reader_copy(markdown):
    """The article as a reader meets it: no citation keys, no Sources block."""
    body = re.split(r"(?mi)^(?:\*\*Sources\*\*|#{1,4}\s*Sources|\*\*Receipts\*\*)\s*$", markdown)[0]
    body = CITATION_RE.sub("", body)
    body = re.sub(r"(?m)^<a id=\"[^\"]*\"></a>\s*\n", "", body)
    return re.sub(r" +([.,;:])", r"\1", body).rstrip() + "\n"


def prose_blocks(markdown):
    """Body paragraphs with their distinct citations, apparatus left out."""
    body = re.split(r"(?mi)^(?:\*\*Sources\*\*|#{1,4}\s*Sources|\*\*Receipts\*\*)\s*$", markdown)[0]
    blocks = []
    seen_heading = in_apparatus = False
    for raw in re.split(r"\n\s*\n", body):
        text = raw.strip()
        if not text:
            continue
        if text.startswith("#"):
            seen_heading = True
            in_apparatus = bool(APPARATUS_HEADING_RE.match(text))
            continue
        if in_apparatus or len(set(m.lower() for m in APPARATUS_WORDS_RE.findall(text))) >= 3:
            continue  # the scope and methods note describes the review, not the subject
        if (text.startswith(("|", "!", "<a ", "```", ">")) or re.match(r"^\*\*Figure\b", text)
                or re.fullmatch(r"\[[^\]]*\]", text, re.S) or SCOPE_NOTE_RE.match(text)
                or re.match(r"^\*\*(?:Table|Abstract|TL;DR)\b", text)):
            continue
        if seen_heading and not blocks and re.fullmatch(r"\*[^*].*\*", text, re.S):
            continue  # standfirst
        if re.match(r"^(?:[-*+]|\d+[.)])\s", text):
            continue
        keys = []
        for key_group, doi in ONE_CITATION_RE.findall(text):
            for key in (re.split(r"\s*;\s*", key_group) if key_group else [doi]):
                key = key.strip().lstrip("@").lower()
                if key and key not in keys:
                    keys.append(key)
        clean = " ".join(strip_citations(text).split())
        clean = re.sub(r" +([.,;:])", r"\1", clean)
        if len(clean.split()) >= 4:
            blocks.append({"text": clean, "sources": keys})
    return blocks


def sentences(paragraph):
    parts = re.split(r"(?<=[.!?])[\"”’)]*\s+(?=[\"“‘(]?[A-Z0-9])", paragraph)
    return [p.strip() for p in parts if len(p.split()) >= 2]


def numbers(text):
    text = YEAR_RE.sub(" ", NAME_NUMBER_RE.sub(" ", text))
    return NUMBER_RE.findall(text)


def _short(text, limit=110):
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def profile(markdown, guide=None):
    guide = guide or READABILITY_GUIDE
    blocks = prose_blocks(markdown)
    if not blocks:
        return {"status": "empty", "measures": {}, "flags": ["no prose paragraphs found"],
                "passages": {}}
    words = sum(len(b["text"].split()) for b in blocks)
    all_sentences = [(i, s) for i, b in enumerate(blocks, 1) for s in sentences(b["text"])]
    sentence_lengths = [len(s.split()) for _i, s in all_sentences]
    syllables = sum(_syllables(w) for b in blocks for w in b["text"].split())
    n_sent = max(len(all_sentences), 1)
    para_numbers = [len(numbers(b["text"])) for b in blocks]
    total_numbers = sum(para_numbers)
    sources = []
    for b in blocks:
        for key in b["sources"]:
            if key not in sources:
                sources.append(key)
    stat_hits = [m.group(0) for b in blocks for m in STAT_RE.finditer(b["text"])]
    hedge_hits = sum(len(HEDGE_RE.findall(b["text"])) for b in blocks)
    per_k = 1000 / max(words, 1)
    measures = {
        "prose_words": words,
        "paragraphs": len(blocks),
        "mean_paragraph_words": round(words / len(blocks), 1),
        "short_paragraph_share": round(
            sum(len(b["text"].split()) < 35 for b in blocks) / len(blocks), 2),
        "mean_sentence_words": round(sum(sentence_lengths) / n_sent, 1),
        "reading_grade": round(0.39 * words / n_sent + 11.8 * syllables / max(words, 1) - 15.59, 1),
        "numbers_per_100_words": round(total_numbers * 100 / max(words, 1), 2),
        "numeric_paragraph_share": round(sum(n > 0 for n in para_numbers) / len(blocks), 2),
        "statistics_terms_per_1000_words": round(len(stat_hits) * per_k, 1),
        "sources_cited": len(sources),
        "sources_per_1000_words": round(len(sources) * per_k, 1),
        "study_roll_calls_per_1000_words": round(
            sum(len(ROLL_CALL_RE.findall(b["text"])) for b in blocks) * per_k, 1),
        "hedges_per_1000_words": round(hedge_hits * per_k, 1),
        "negations_per_1000_words": round(
            sum(len(NEGATION_RE.findall(b["text"])) for b in blocks) * per_k, 1),
        # Sentences that limit, hedge or define by negation: compared before and
        # after the cold-read revision, which must not add to them.
        "limitation_sentences": sum(
            bool(HEDGE_RE.search(s) or NEGATION_RE.search(s)) for _i, s in all_sentences),
        "questions": sum(s.rstrip("\"”’)").endswith("?") for _i, s in all_sentences),
    }

    passages = {
        "long_sentences": [
            {"paragraph": i, "words": len(s.split()), "text": _short(s)}
            for i, s in sorted(all_sentences, key=lambda x: -len(x[1].split()))
            if len(s.split()) > guide["long_sentence_words"]][:8],
        "number_heavy_sentences": [
            {"paragraph": i, "numbers": len(numbers(s)), "text": _short(s)}
            for i, s in sorted(all_sentences, key=lambda x: -len(numbers(x[1])))
            if len(numbers(s)) > guide["numbers_per_sentence"]][:8],
        "number_heavy_paragraphs": [
            {"paragraph": i, "numbers": n, "text": _short(blocks[i - 1]["text"], 80)}
            for i, n in sorted(enumerate(para_numbers, 1), key=lambda x: -x[1])
            if n > guide["numbers_per_paragraph"]][:6],
        "long_paragraphs": [
            {"paragraph": i, "words": len(b["text"].split()), "text": _short(b["text"], 80)}
            for i, b in enumerate(blocks, 1)
            if len(b["text"].split()) > guide["long_paragraph_words"]][:6],
        "source_heavy_paragraphs": [
            {"paragraph": i, "sources": len(b["sources"]), "text": _short(b["text"], 80)}
            for i, b in enumerate(blocks, 1)
            if len(b["sources"]) > guide["sources_per_paragraph"]][:6],
        "statistics_in_prose": sorted({h.lower() for h in stat_hits}),
        "lab_units": sorted({m.group(0) for b in blocks for m in LAB_UNIT_RE.finditer(b["text"])}),
        "self_reference": [
            {"paragraph": i, "text": _short(s)} for i, s in all_sentences
            if SELF_REFERENCE_RE.search(s)][:6],
        "negation_sentences": [
            {"paragraph": i, "text": _short(s)} for i, s in all_sentences
            if NEGATION_RE.search(s)][:8],
        "caveat_closers": [
            {"paragraph": i, "text": _short(sentences(b["text"])[-1])}
            for i, b in enumerate(blocks, 1)
            if sentences(b["text"]) and HEDGE_RE.search(sentences(b["text"])[-1])][:8],
    }

    flags = []

    def flag(key, message):
        # Rates mean little on a fragment; passage flags below still apply.
        if words >= 300 and measures[key] > guide[key]:
            flags.append(f"{key} = {measures[key]} (guide: at most {guide[key]}). {message}")

    flag("numbers_per_100_words", "Keep the numbers the reader must feel; say the rest in "
         "words or move it to a table or caption.")
    flag("numeric_paragraph_share", "Published features carry a number in about a quarter of "
         "their paragraphs: add paragraphs that explain, and thin the ones that only report.")
    flag("statistics_terms_per_1000_words", "Give the plain meaning in the prose; keep "
         "intervals and ratios in a table or caption.")
    flag("sources_per_1000_words", "This reads as a tour of the literature: tell a few anchor "
         "studies fully and let the rest support them in a clause, or leave them out.")
    flag("study_roll_calls_per_1000_words", "Counts of trials and studies are apparatus: "
         "keep one where the size is the point.")
    flag("mean_sentence_words", "Split sentences that carry more than one idea.")
    flag("mean_paragraph_words", "Break paragraphs where the point changes.")
    flag("short_paragraph_share", "Too many paragraphs of a sentence or two: the piece reads "
         "like notes. Merge fragments into paragraphs that develop a point.")
    flag("reading_grade", "Use shorter sentences and more familiar words.")
    flag("hedges_per_1000_words", "State each limitation once, where it changes the meaning.")
    flag("negations_per_1000_words", "Too many sentences say what something is not "
         "('rather than', 'not X but Y'): say what it is.")
    for key, message in (
            ("long_sentences", "sentence(s) too long to read in one breath"),
            ("number_heavy_sentences", "sentence(s) carry more numbers than a reader can hold"),
            ("number_heavy_paragraphs", "paragraph(s) are crowded with numbers"),
            ("long_paragraphs", "paragraph(s) are very long"),
            ("source_heavy_paragraphs", "paragraph(s) cite so many sources they read as a list"),
            ("self_reference", "sentence(s) talk about the article or the request"),
            ("caveat_closers", "paragraph(s) end on a caveat")):
        limit = guide.get(f"max_{key}", 0)
        if len(passages[key]) > limit:
            flags.append(f"{len(passages[key])} {message} (see passages.{key})")
    if passages["lab_units"]:
        flags.append("laboratory units in prose (" + ", ".join(passages["lab_units"])
                     + "): convert to everyday scale or explain once")
    return {"status": "flags" if flags else "clear", "measures": measures, "flags": flags,
            "passages": passages}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", required=True)
    parser.add_argument("--report")
    parser.add_argument("--reader-copy")
    args = parser.parse_args(argv)
    markdown = Path(args.review).read_text(encoding="utf-8")
    result = profile(markdown)
    if args.report:
        atomic_write_json(args.report, result)
    if args.reader_copy:
        atomic_write_text(args.reader_copy, reader_copy(markdown))
    m = result["measures"]
    if m:
        print(f"{m['prose_words']} prose words in {m['paragraphs']} paragraphs; "
              f"{m['mean_sentence_words']} words per sentence; reading grade {m['reading_grade']}; "
              f"{m['numbers_per_100_words']} numbers per 100 words; "
              f"{m['sources_cited']} sources ({m['sources_per_1000_words']} per 1,000 words)")
    for item in result["flags"]:
        print("  ~ " + item)
    for key, items in result["passages"].items():
        if not items or key in {"statistics_in_prose", "lab_units"}:
            continue
        print(f"  {key}:")
        for entry in items[:5]:
            detail = ", ".join(f"{k} {v}" for k, v in entry.items() if k not in {"text", "paragraph"})
            print(f"    ¶{entry['paragraph']}" + (f" ({detail})" if detail else "")
                  + f": {entry['text']}")
    if result["passages"].get("statistics_in_prose"):
        print("  statistics_in_prose: " + ", ".join(result["passages"]["statistics_in_prose"]))
    if not result["flags"]:
        print("  no readability flags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
