#!/usr/bin/env python3
"""Validate a finished Grounded review before delivery or PDF export.

This validator covers the deterministic parts of the writing contract.  It is
deliberately not a substitute for the semantic quality gate: evidence weighing,
whether a cited source supports its claim, narrative callbacks, and
plain-language quality still require a careful read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from artifact_io import atomic_write_json

WORD_BUDGETS = {
    "scientific": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "popsci": {"small": (600, 1000), "medium": (1500, 2500), "large": (3500, 6000)},
    "bullets": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
    "eli5": {"small": (350, 700), "medium": (900, 1600), "large": (2000, 4000)},
}

TIER_REQUIREMENTS = {
    "small": {"sections": (3, 5), "sources": (10, 20), "tables": (0, 1),
              "fulltexts": (2, None), "figure_cap": 1},
    "medium": {"sections": (6, 9), "sources": (30, 60), "tables": (1, 2),
               "fulltexts": (8, None), "figure_cap": 3},
    "large": {"sections": (10, 15), "sources": (70, 150), "tables": (2, 4),
              "fulltexts": (25, None), "figure_cap": 5},
}

MOJIBAKE = re.compile(r"(?:\ufffd|Ã.|Â(?=\s|[^\w])|â(?:€|€™|€œ|€\x9d|€“|€”))")
SCAFFOLD_LABEL = re.compile(
    r"^\s*(?:Kicker|Lede|Nut graf|Standfirst|Scaffold|Working title)\s*:", re.I | re.M
)
TECHNICAL_TERMS = (
    "SMD", "CI", "OR", "I²", "GRADE", "HAM-D", "PHQ-9", "mRNA",
    "hazard ratio", "odds ratio", "confidence interval",
)
DOI_MARKDOWN_LINK = (
    r"\[[^\]\n]+\]\(https?://(?:dx\.)?doi\.org/"
    r"(?:[^\s()]|\([^\s()]*\))+\)"
)
DOI_MARKDOWN_GROUP_RE = re.compile(
    DOI_MARKDOWN_LINK + r"(?:,\s*" + DOI_MARKDOWN_LINK + r")*",
    re.IGNORECASE,
)


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


def _chat_citation_placement_errors(body: str) -> list[str]:
    """Enforce claim-first author-year links with punctuation after the link."""
    errors: list[str] = []
    for match in DOI_MARKDOWN_GROUP_RE.finditer(body):
        line_number = body.count("\n", 0, match.start()) + 1
        line_start = body.rfind("\n", 0, match.start()) + 1
        line_end = body.find("\n", match.end())
        if line_end < 0:
            line_end = len(body)
        line = body[line_start:line_end]
        relative_start = match.start() - line_start
        relative_end = match.end() - line_start

        if line.lstrip().startswith("|"):
            cell_start = line.rfind("|", 0, relative_start) + 1
            cell_end = line.find("|", relative_end)
            if cell_end < 0:
                cell_end = len(line)
            prefix = line[cell_start:relative_start]
            suffix = line[relative_end:cell_end]
            if not prefix.strip() and not suffix.strip():
                continue
        else:
            block_start = body.rfind("\n\n", 0, match.start()) + 2
            prefix = body[block_start:match.start()]

        if not re.search(r"[^\W_]", prefix, re.UNICODE):
            errors.append(
                f"chat citation starts a sentence or block at line {line_number}; "
                "place it after the supported claim or quotation"
            )
        elif re.search(r"[.!?][”’\"']?\s*$", prefix):
            errors.append(
                f"chat citation follows sentence-ending punctuation at line "
                f"{line_number}; put the citation before that punctuation"
            )
    return errors


def _sentence_count(text: str) -> int:
    pieces = re.split(r"(?<=[.!?])(?:[”’\"])?\s+(?=[A-Z0-9])", text.strip())
    return len([piece for piece in pieces if piece.strip()])


def _body_word_count(text: str) -> int:
    # Tier budgets describe the authored body, not navigation furniture.
    without_headings = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.M)
    return len(_words(without_headings))


_TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$"
)


def _word_breakdown(text: str) -> dict[str, int]:
    """Split the body word count into prose, tables, captions, and alt text.

    The tier budget binds the prose alone: tables, figure captions, and alt
    text are mandatory apparatus with their own compact caps, so adding a
    required figure never forces prose cuts to stay inside the tier range.
    """
    without_headings = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.M)
    alt_words = sum(
        len(_words(match))
        for match in re.findall(r"!\[([^\]]*)\]\([^)]+\)", without_headings)
    )
    no_images = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", without_headings)
    table_words = 0
    prose_lines: list[str] = []
    for line in no_images.splitlines():
        if line.lstrip().startswith("|"):
            if not _TABLE_SEPARATOR_RE.match(line):
                table_words += len(_words(line))
        else:
            prose_lines.append(line)
    caption_words = 0
    remaining: list[str] = []
    for paragraph in re.split(r"\n\s*\n", "\n".join(prose_lines)):
        if re.match(r"\s*\*\*Figure[\s{]", paragraph):
            caption_words += len(_words(paragraph))
        else:
            remaining.append(paragraph)
    prose_words = len(_words("\n\n".join(remaining)))
    return {
        "prose": prose_words,
        "tables": table_words,
        "captions": caption_words,
        "alt_text": alt_words,
        "total": prose_words + table_words + caption_words + alt_words,
    }


def _table_count(text: str) -> int:
    return len(re.findall(
        r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$",
        text,
        re.M,
    ))


def _normalise_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = unquote(value).strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return re.sub(r"[).,;*_]+$", "", value) or None


def _nontrivial_abstract(entry: dict[str, object]) -> bool:
    return len(_words(str(entry.get("abstract") or ""))) >= 50


def _fulltext_records(manifest: dict[str, object] | None) -> list[dict[str, object]]:
    if not manifest:
        return []
    records = manifest.get("records", [])
    return [record for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def _reading_and_verification_errors(
    source_dois: set[str],
    ledger: dict[str, object],
    fulltext_manifest: dict[str, object] | None,
) -> tuple[list[str], dict[str, object]]:
    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        return ["ledger entries must be a list"], {}
    by_doi = {
        _normalise_doi(str(entry.get("doi") or "")): entry
        for entry in entries if isinstance(entry, dict) and entry.get("doi")
    }
    valid_fulltext_keys = {
        str(record.get("ledger_key"))
        for record in _fulltext_records(fulltext_manifest)
        if record.get("status") == "valid_fulltext"
    }
    missing_ledger: list[str] = []
    missing_bibliographic: list[str] = []
    missing_retraction: list[str] = []
    ineligible_publication: list[str] = []
    missing_reading: list[str] = []
    for doi in sorted(source_dois):
        entry = by_doi.get(doi)
        if entry is None:
            missing_ledger.append(doi)
            continue
        key = str(entry.get("key") or doi)
        verification = entry.get("verification") or {}
        canonical = entry.get("canonical") or {}
        if (
            entry.get("status") != "verified"
            or not isinstance(verification, dict)
            or verification.get("bibliographic_status") != "verified"
        ):
            missing_bibliographic.append(key)
        if (
            not isinstance(verification, dict)
            or verification.get("retraction_status") != "clear"
        ):
            missing_retraction.append(key)
        publication_type = canonical.get("type") if isinstance(canonical, dict) else None
        if entry.get("is_preprint") or publication_type not in {
            "journal-article", "journal-issue", "proceedings-article"
        }:
            ineligible_publication.append(key)
        if not (_nontrivial_abstract(entry) or key in valid_fulltext_keys):
            missing_reading.append(key)
    errors = []
    for label, values in (
        ("cited DOI(s) absent from ledger", missing_ledger),
        ("citation(s) missing bibliographic verification", missing_bibliographic),
        ("citation(s) missing a clear retraction check", missing_retraction),
        ("citation(s) without eligible publication metadata", ineligible_publication),
        ("citation(s) missing abstract-or-full-text reading evidence", missing_reading),
    ):
        if values:
            errors.append(f"{label}: " + ", ".join(values[:12]))
    return errors, {
        "ledger_citations": len(source_dois) - len(missing_ledger),
        "reading_eligible": len(source_dois) - len(missing_ledger) - len(missing_reading),
        "missing_reading_keys": missing_reading,
    }


def _thin_override(value: dict[str, object] | None) -> tuple[set[str], str | None]:
    if value is None:
        return set(), None
    reason = value.get("reason")
    evidence = value.get("saturation_evidence")
    shortfalls = value.get("allowed_shortfalls")
    if not isinstance(reason, str) or len(reason.split()) < 5:
        raise ValueError("thin-literature override requires a substantive reason")
    if not isinstance(evidence, list) or not evidence or not all(
        isinstance(item, str) and item.strip() for item in evidence
    ):
        raise ValueError("thin-literature override requires saturation_evidence")
    if not isinstance(shortfalls, list) or not shortfalls:
        raise ValueError("thin-literature override requires allowed_shortfalls")
    allowed = set(shortfalls)
    if not allowed <= {"sources", "fulltexts"}:
        raise ValueError("thin-literature override may cover only sources/fulltexts")
    return allowed, reason


def _tier_error(
    name: str,
    actual: int,
    bounds: tuple[int, int | None],
) -> str | None:
    minimum, maximum = bounds
    if actual < minimum or (maximum is not None and actual > maximum):
        expected = f"{minimum}+" if maximum is None else f"{minimum}–{maximum}"
        return f"strict tier requires {expected} {name}; found {actual}"
    return None


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

    for anchor in anchors:
        anchor_position = markdown.find(f'<a id="{anchor}"></a>')
        reference_position = markdown.find(f"](#{anchor})")
        if reference_position > anchor_position >= 0:
            errors.append(
                f"figure {anchor} must be introduced in the body before its artwork"
            )
        next_anchor = markdown.find('<a id="fig-', anchor_position + 1)
        next_heading = markdown.find("\n### ", anchor_position + 1)
        sources_boundary = markdown.find("\n**Sources**", anchor_position + 1)
        boundaries = [
            value for value in (next_anchor, next_heading, sources_boundary)
            if value >= 0
        ]
        block_end = min(boundaries) if boundaries else len(markdown)
        if not _dois(markdown[anchor_position:block_end]):
            errors.append(f"figure {anchor} caption contains no DOI citation")

    for _alt, source in images:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", source):
            errors.append(f"figure assets must be local: {source}")
        elif base_dir is not None and not (base_dir / source).is_file():
            errors.append(f"figure asset does not exist: {source}")
    return errors


def validate_review(
    markdown: str, *, style: str, size: str, base_dir: Path | None = None,
    strict_tier: bool = False, image_mode: bool = False,
    ledger: dict[str, object] | None = None,
    fulltext_manifest: dict[str, object] | None = None,
    thin_literature_override: dict[str, object] | None = None,
    legacy_word_count: bool = False,
) -> ValidationResult:
    """Return deterministic writing-contract errors, warnings, and metrics."""
    style = "scientific" if style == "prose" else style
    if style not in WORD_BUDGETS:
        raise ValueError(f"unsupported style: {style}")
    if size not in WORD_BUDGETS[style]:
        raise ValueError(f"unsupported size: {size}")

    errors: list[str] = []
    warnings: list[str] = []
    if MOJIBAKE.search(markdown):
        errors.append("review contains mojibake or a Unicode replacement character")
    sources_markers = list(re.finditer(r"^\*\*Sources\*\*\s*$", markdown, re.M))
    if len(sources_markers) != 1:
        errors.append("Sources must appear exactly once")
        body, sources = markdown, ""
    else:
        marker = sources_markers[0]
        body, sources = markdown[: marker.start()], markdown[marker.end() :]
        if not sources.strip():
            errors.append("Sources must contain at least one verified reference")
    scaffold = SCAFFOLD_LABEL.search(body)
    if scaffold:
        errors.append(f"exposed drafting scaffold label: {scaffold.group(0).strip()}")

    if sources.strip() and re.search(
        r"^#{1,6}\s+|^\*\*(?:Abstract|TL;DR)\*\*", sources, re.M
    ):
        errors.append("Sources must be the terminal review section")
    if re.search(r"\[@[^]]+\]", markdown):
        errors.append("unresolved citation key remains in the finished review")
    errors.extend(_chat_citation_placement_errors(body))

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

    figure_count = len(re.findall(r'^<a id="fig-', markdown, re.M))
    body_word_count = _body_word_count(body)
    breakdown = _word_breakdown(body)
    minimum, maximum = WORD_BUDGETS[style][size]
    tier_bound_count = body_word_count if legacy_word_count else breakdown["prose"]
    tier_bound_label = "body" if legacy_word_count else "prose body"
    if not minimum <= tier_bound_count <= maximum:
        overage = (
            f"trim {tier_bound_count - maximum} words"
            if tier_bound_count > maximum
            else f"add {minimum - tier_bound_count} words"
        )
        message = (
            f"{tier_bound_label} is {tier_bound_count} words; {size} {style} "
            f"guidance is {minimum}–{maximum} — {overage}"
        )
        (errors if strict_tier else warnings).append(message)
    if not legacy_word_count:
        apparatus_caps = (
            ("captions", breakdown["captions"], 80 * max(1, figure_count)),
            ("alt_text", breakdown["alt_text"], 40 * max(1, figure_count)),
            ("tables", breakdown["tables"], 120),
        )
        for name, actual, cap in apparatus_caps:
            if actual > cap:
                message = (
                    f"{name} carry {actual} words; keep them within {cap} — "
                    f"trim {actual - cap} words"
                )
                (errors if strict_tier else warnings).append(message)
    if not body_dois:
        errors.append("finished review contains no DOI citations")

    section_count = len(re.findall(r"^###\s+.+$", body, re.M))
    table_count = _table_count(body)
    fulltext_count = sum(
        record.get("status") == "valid_fulltext" and bool(record.get("counted"))
        for record in _fulltext_records(fulltext_manifest)
    )
    overridden, override_reason = _thin_override(thin_literature_override)
    if strict_tier:
        requirements = TIER_REQUIREMENTS[size]
        checks = (
            ("sections", section_count, requirements["sections"]),
            ("sources", len(source_dois), requirements["sources"]),
            ("tables", table_count, requirements["tables"]),
            ("fulltexts", fulltext_count, requirements["fulltexts"]),
        )
        for name, actual, bounds in checks:
            issue = _tier_error(name, actual, bounds)
            if issue and name in overridden and actual < bounds[0]:
                warnings.append(f"{issue}; accepted by thin-literature override: {override_reason}")
            elif issue:
                errors.append(issue)
        if figure_count > requirements["figure_cap"]:
            errors.append(
                f"strict tier permits at most {requirements['figure_cap']} figures; "
                f"found {figure_count}"
            )
        if image_mode and figure_count < 1:
            errors.append("strict image mode requires at least one figure")

    evidence_metrics: dict[str, object] = {}
    if ledger is not None:
        evidence_errors, evidence_metrics = _reading_and_verification_errors(
            source_dois, ledger, fulltext_manifest
        )
        errors.extend(evidence_errors)

    if style != "eli5":
        def _covered_by_adjacent_expansion(term: str) -> bool:
            """An abbreviation whose expansion was already linked at first
            use ("95% [confidence interval](...)" then "95% CI") is covered;
            warning on the later shorthand is noise."""
            if not term.isupper() or not 2 <= len(term) <= 6:
                return False
            first = re.search(rf"\b{re.escape(term)}\b", body)
            if not first:
                return False
            preceding = body[:first.start()]
            for link_text in re.findall(
                    r"\[([^\]]+)\]\((?!https?://doi\.org/)", preceding):
                initials = "".join(
                    word[0] for word in re.findall(r"[A-Za-z]+", link_text)
                ).upper()
                if term in (initials, link_text.strip().upper()):
                    return True
            return False

        missing_links = [
            term for term in TECHNICAL_TERMS
            if re.search(rf"\b{re.escape(term)}\b", body)
            and not re.search(
                rf"\[[^]]*\b{re.escape(term)}\b[^]]*\]\((?!https?://doi\.org/)",
                body,
                re.I,
            )
            and not _covered_by_adjacent_expansion(term)
        ]
        if missing_links:
            warnings.append(
                "technical term(s) may need a first-use explanatory link: "
                + ", ".join(missing_links)
            )

    metrics: dict[str, object] = {
        "style": style,
        "size": size,
        "body_words": body_word_count,
        "word_breakdown": breakdown,
        "body_dois": len(body_dois),
        "source_dois": len(source_dois),
        "figures": figure_count,
        "sections": section_count,
        "tables": table_count,
        "valid_fulltexts": fulltext_count,
        "strict_tier": strict_tier,
        **evidence_metrics,
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
        "--strict-tier", action="store_true",
        help="make all requested tier ranges release-blocking",
    )
    parser.add_argument(
        "--image-mode", action="store_true",
        help="with --strict-tier, require at least one figure",
    )
    parser.add_argument("--ledger", help="sources.json; gates every cited record")
    parser.add_argument(
        "--fulltext-manifest",
        help="fulltext-manifest.json; supplies authentic full-text reading evidence",
    )
    parser.add_argument(
        "--thin-literature-override",
        help="structured JSON allowing only evidenced source/full-text shortfalls",
    )
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
    parser.add_argument(
        "--report", help="atomically write the JSON validation report"
    )
    parser.add_argument(
        "--legacy-word-count",
        action="store_true",
        help="bind the tier word range to the whole body (prose + tables + "
             "captions + alt text) as before v2.9, instead of prose alone "
             "with separate apparatus caps",
    )
    args = parser.parse_args()
    try:
        review_path = None if args.review == "-" else Path(args.review).resolve()
        markdown = (
            sys.stdin.read()
            if review_path is None
            else review_path.read_text(encoding="utf-8")
        )
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger else None
        )
        fulltext_manifest = (
            json.loads(Path(args.fulltext_manifest).read_text(encoding="utf-8"))
            if args.fulltext_manifest else None
        )
        thin_override = (
            json.loads(Path(args.thin_literature_override).read_text(encoding="utf-8"))
            if args.thin_literature_override else None
        )
        result = validate_review(
            markdown,
            style=args.style,
            size=args.size,
            base_dir=review_path.parent if review_path is not None else None,
            strict_tier=args.strict_tier,
            image_mode=args.image_mode,
            ledger=ledger,
            fulltext_manifest=fulltext_manifest,
            thin_literature_override=thin_override,
            legacy_word_count=args.legacy_word_count,
        )
    except (OSError, ValueError) as exc:
        print(f"Review validation failed: {exc}", file=sys.stderr)
        return 2
    report = json.dumps(result.as_dict(), indent=2, sort_keys=True)
    if args.report:
        try:
            atomic_write_json(args.report, result.as_dict())
        except OSError as exc:
            print(f"Review validation report failed: {exc}", file=sys.stderr)
            return 2
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
