#!/usr/bin/env python3
"""Validate a finished Grounded review before delivery or PDF export.

This validator covers the deterministic parts of the writing contract.  It is
deliberately not a substitute for the semantic quality gate: evidence weighing,
claim-level citation placement, narrative callbacks, and plain-language quality
still require a careful read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


WORD_BUDGETS = {
    "scientific": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "popsci": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "bullets": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
    "eli5": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
}


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    metrics: dict[str, object]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "pass" if self.ok else "fail",
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metrics": self.metrics,
        }


def _words(text: str) -> list[str]:
    text = re.sub(r"https?://[^)\s>]+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    return re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE)


def _dois(text: str) -> set[str]:
    return {
        unquote(re.sub(r"[).,;*_]+$", "", value)).lower()
        for value in re.findall(r"https?://doi\.org/([^\s<>\]]+)", text, re.I)
    }


def _sentence_count(text: str) -> int:
    pieces = re.split(r"(?<=[.!?])(?:[”’\"])?\s+(?=[A-Z0-9])", text.strip())
    return len([piece for piece in pieces if piece.strip()])


def _body_word_count(text: str) -> int:
    # Tier budgets describe the authored body, not navigation furniture.
    without_headings = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.M)
    return len(_words(without_headings))


def _section_payload(markdown: str, heading: str) -> str | None:
    match = re.search(
        rf"^###\s+{re.escape(heading)}\s*$\n+(.*?)(?=^###\s+|^\*\*Sources\*\*\s*$|\Z)",
        markdown,
        re.M | re.S | re.I,
    )
    return match.group(1).strip() if match else None


def _has_flowing_paragraph(payload: str) -> bool:
    """Return whether a section contains prose beyond figures and tables."""
    for block in re.split(r"\n\s*\n", payload):
        block = block.strip()
        if not block or re.match(r"^(?:<a\b|!\[|\*\*Figure\b|\|)", block):
            continue
        if re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)\S", block):
            continue
        plain = re.sub(r"\[[^]]+\]\([^)]+\)", " ", block)
        plain = re.sub(r"<[^>]+>|[*_`]", " ", plain)
        if re.search(r"[A-Za-z]", plain):
            return True
    return False


def _validate_figures(markdown: str, base_dir: Path | None) -> list[str]:
    errors: list[str] = []
    anchors = re.findall(r'^<a id="(fig-[a-z][a-z0-9-]*)"></a>\s*$', markdown, re.M)
    images = re.findall(r"^!\[([^]]*)\]\(([^)\s]+)\)\s*$", markdown, re.M)
    captions = re.findall(r"^\*\*Figure\s+(\d+)\.\s+.+?\*\*.*$", markdown, re.M)
    references = re.findall(r"\[Figure\s+\d+\]\(#(fig-[a-z][a-z0-9-]*)\)", markdown)

    if len(set(anchors)) != len(anchors):
        errors.append("figure anchors must be unique")
    if not (len(anchors) == len(images) == len(captions)):
        errors.append(
            "figure anchors, images, and numbered captions must have equal counts"
        )
    expected_numbers = [str(index) for index in range(1, len(captions) + 1)]
    if captions != expected_numbers:
        errors.append("figure captions must be numbered consecutively from Figure 1")
    missing_references = sorted(set(anchors) - set(references))
    if missing_references:
        errors.append("unreferenced figure anchor(s): " + ", ".join(missing_references))

    for _alt, source in images:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", source):
            errors.append(f"figure assets must be local: {source}")
        elif base_dir is not None and not (base_dir / source).is_file():
            errors.append(f"figure asset does not exist: {source}")
    return errors


def validate_review(
    markdown: str, *, style: str, size: str, base_dir: Path | None = None
) -> ValidationResult:
    """Return deterministic writing-contract errors, warnings, and metrics."""
    style = "scientific" if style == "prose" else style
    if style not in WORD_BUDGETS:
        raise ValueError(f"unsupported style: {style}")
    if size not in WORD_BUDGETS[style]:
        raise ValueError(f"unsupported size: {size}")

    errors: list[str] = []
    warnings: list[str] = []
    sources_markers = list(re.finditer(r"^\*\*Sources\*\*\s*$", markdown, re.M))
    if len(sources_markers) != 1:
        errors.append("Sources must appear exactly once")
        body, sources = markdown, ""
    else:
        marker = sources_markers[0]
        body, sources = markdown[: marker.start()], markdown[marker.end() :]
        if not sources.strip():
            errors.append("Sources must contain at least one verified reference")

    if sources.strip() and re.search(
        r"^#{1,6}\s+|^\*\*(?:Abstract|TL;DR)\*\*", sources, re.M
    ):
        errors.append("Sources must be the terminal review section")
    if re.search(r"\[@[^]]+\]", markdown):
        errors.append("unresolved citation key remains in the finished review")

    first_content = next(
        (line.strip() for line in markdown.splitlines() if line.strip()), ""
    )
    if not re.match(r"^##\s+\S", first_content):
        errors.append("the review must begin with one level-two question or headline")
    level_two = re.findall(r"^##\s+.+$", body, re.M)
    if len(level_two) != 1:
        errors.append("the review body must contain exactly one level-two title")

    body_dois = _dois(body)
    source_dois = _dois(sources)
    missing_sources = sorted(body_dois - source_dois)
    unused_sources = sorted(source_dois - body_dois)
    if missing_sources:
        errors.append(
            "body DOI(s) missing from Sources: " + ", ".join(missing_sources[:5])
        )
    if unused_sources:
        errors.append(
            "uncited DOI(s) present in Sources: " + ", ".join(unused_sources[:5])
        )

    abstract = re.search(
        r"^\*\*Abstract\*\*\s*[—–-]\s*(.+?)(?=\n\n|\Z)", body, re.M | re.S
    )
    tldr = re.search(r"^\*\*TL;DR\*\*\s*[—–-]\s*(.+?)(?=\n\n|\Z)", body, re.M | re.S)
    standfirst = re.search(r"^##\s+.+$\n+\*([^*\n].*?)\*\s*$", body, re.M)

    if style == "scientific":
        if abstract is None:
            errors.append("scientific style requires a citation-free Abstract")
        else:
            abstract_words = len(_words(abstract.group(1)))
            if not 120 <= abstract_words <= 250:
                errors.append(
                    f"scientific Abstract is {abstract_words} words; required 120–250"
                )
            if _dois(abstract.group(1)):
                errors.append("scientific Abstract must not contain citations")
        for heading in ("Introduction", "Conclusion"):
            if _section_payload(body, heading) is None:
                errors.append(f"scientific style requires a {heading} section")
        if tldr or standfirst:
            errors.append("scientific style must not use a TL;DR or italic standfirst")
    elif style == "popsci":
        if standfirst is None:
            errors.append(
                "popsci style requires an italic standfirst after the headline"
            )
        else:
            if not 1 <= _sentence_count(standfirst.group(1)) <= 3:
                errors.append("popsci standfirst must contain 1–3 sentences")
            if _dois(standfirst.group(1)):
                errors.append("popsci standfirst must not contain citations")
        if abstract or tldr:
            errors.append("popsci style must not use an Abstract or TL;DR")
        if len(re.findall(r"^###\s+.+$", body, re.M)) < 3:
            errors.append("popsci style requires at least three narrative crossheads")
    else:
        if tldr is None:
            errors.append(f"{style} style requires a citation-free TL;DR")
        elif _dois(tldr.group(1)):
            errors.append("TL;DR must not contain citations")
        if abstract or standfirst:
            errors.append(
                f"{style} style must not use an Abstract or italic standfirst"
            )
        sections = list(re.finditer(r"^###\s+.+$", body, re.M))
        if not sections:
            requirement = (
                "punchline sections"
                if style == "bullets"
                else "plain-language narrative sections"
            )
            errors.append(f"{style} style requires {requirement}")
        for index, heading in enumerate(sections):
            end = (
                sections[index + 1].start() if index + 1 < len(sections) else len(body)
            )
            payload = body[heading.end() : end]
            has_bullets = bool(re.search(r"^(?:-|\*)\s+\S", payload, re.M))
            has_list_items = bool(
                re.search(r"^(?:[-*+]\s+|\d+[.)]\s+)\S", payload, re.M)
            )
            if style == "bullets" and not has_bullets:
                errors.append(f"section {heading.group(0)!r} has no bullet body")
            elif style == "eli5":
                if has_list_items:
                    errors.append(
                        f"ELI5 section {heading.group(0)!r} must use flowing "
                        "paragraphs, not lists"
                    )
                if not _has_flowing_paragraph(payload):
                    errors.append(
                        f"ELI5 section {heading.group(0)!r} has no flowing "
                        "paragraph body"
                    )

    errors.extend(_validate_figures(markdown, base_dir))

    body_word_count = _body_word_count(body)
    minimum, maximum = WORD_BUDGETS[style][size]
    if not minimum <= body_word_count <= maximum:
        warnings.append(
            f"body is {body_word_count} words; {size} {style} guidance is "
            f"{minimum}–{maximum}"
        )
    if not body_dois:
        errors.append("finished review contains no DOI citations")

    metrics: dict[str, object] = {
        "style": style,
        "size": size,
        "body_words": body_word_count,
        "body_dois": len(body_dois),
        "source_dois": len(source_dois),
        "figures": len(re.findall(r'^<a id="fig-', markdown, re.M)),
    }
    if abstract is not None:
        metrics["abstract_words"] = len(_words(abstract.group(1)))
    if standfirst is not None:
        metrics["standfirst_sentences"] = _sentence_count(standfirst.group(1))
    return ValidationResult(tuple(errors), tuple(warnings), metrics)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", help="finished review Markdown, or - for stdin")
    parser.add_argument(
        "--style",
        choices=("scientific", "prose", "popsci", "bullets", "eli5"),
        required=True,
    )
    parser.add_argument("--size", choices=("small", "medium", "large"), required=True)
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="fail when an approximate word-budget warning is present",
    )
    parser.add_argument(
        "--pass-through",
        action="store_true",
        help="on success, write the validated review to stdout and the JSON report to stderr",
    )
    args = parser.parse_args()
    try:
        review_path = None if args.review == "-" else Path(args.review).resolve()
        markdown = (
            sys.stdin.read()
            if review_path is None
            else review_path.read_text(encoding="utf-8")
        )
        result = validate_review(
            markdown,
            style=args.style,
            size=args.size,
            base_dir=review_path.parent if review_path is not None else None,
        )
    except (OSError, ValueError) as exc:
        print(f"Review validation failed: {exc}", file=sys.stderr)
        return 2
    report = json.dumps(result.as_dict(), indent=2, sort_keys=True)
    passed = result.ok and not (args.warnings_as_errors and result.warnings)
    if args.pass_through:
        print(report, file=sys.stderr)
        if passed:
            sys.stdout.write(markdown)
    else:
        print(report)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
