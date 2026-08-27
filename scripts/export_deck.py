#!/usr/bin/env python3
"""Export a verified Grounded storyboard as a canonical 16:9 PDF deck.

The research pipeline ends before this script begins.  It accepts a storyboard,
the already verified source ledger, and locally generated slide images; validates
their assertion--evidence contract; builds one self-contained HTML document; and
renders that exact document with Grounded's pinned WeasyPrint path.

    python3 export_deck.py --storyboard storyboard.json --ledger sources.json \
        --out review-deck.pdf
    python3 export_deck.py --check-pdf-runtime

Content images are embedded as data URIs.  No browser, network request, reveal.js,
or presentation application is involved.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from export_review import (
    _brand_logo_html,
    _compiled_date,
    _display_date,
    detect_release,
    detect_repo,
    image_data_uri,
    inline,
)
from format_references import (
    bracket_intext,
    doi_href,
    fmt_bracket,
    is_verified,
    year_suffixes,
)


SIZE_CONTRACTS = {
    "small": {"content": (4, 6), "total": (6, 8), "reference_min": 1},
    "medium": {"content": (8, 12), "total": (10, 15), "reference_min": 1},
    "large": {"content": (14, 20), "total": (18, 25), "reference_min": 3},
}
STYLE_ARCS = {
    "scientific": {
        "roles": {"question", "evidence", "limitations", "conclusion"},
        "first": "question",
        "last": "conclusion",
        "required": {"evidence", "limitations"},
        "kicker": "Journal club",
    },
    "popsci": {
        "roles": {"hook", "story", "contrary-evidence", "kicker"},
        "first": "hook",
        "last": "kicker",
        "required": {"story", "contrary-evidence"},
        "kicker": "Evidence story",
    },
    "bullets": {
        "roles": {"tldr", "point"},
        "first": "tldr",
        "last": None,
        "required": {"point"},
        "kicker": "TL;DR",
    },
    "eli5": {
        "roles": {"idea"},
        "first": "idea",
        "last": "idea",
        "required": set(),
        "kicker": "Simple ideas",
    },
}
EVIDENCE_LEVELS = {"strong", "mixed", "limited"}
SLIDE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
REFERENCE_CAPACITY = 38
DECK_POINTS = (960.0, 540.0)
TOP_LEVEL_FIELDS = {
    "title",
    "subtitle",
    "style",
    "size",
    "kicker",
    "reference_keys",
    "slides",
}
SLIDE_FIELDS = {"id", "role", "title", "image", "alt", "citations", "evidence"}


class DeckValidationError(ValueError):
    """Raised when a storyboard cannot satisfy the deck contract."""


@dataclass(frozen=True)
class ContentSlide:
    slide_id: str
    role: str
    title: str
    image: str
    alt: str
    citations: tuple[str, ...]
    evidence: str


@dataclass(frozen=True)
class DeckDocument:
    title: str
    subtitle: str | None
    style: str
    size: str
    kicker: str
    slides: tuple[ContentSlide, ...]
    reference_keys: tuple[str, ...]
    references: tuple[dict, ...]
    reference_pages: tuple[tuple[dict, ...], ...]
    suffixes: dict[str, str]
    total_slides: int


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise DeckValidationError(f"{path} must contain a JSON object")
    return value


def _string(mapping: dict, field: str, *, optional: bool = False) -> str | None:
    value = mapping.get(field)
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DeckValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(
    mapping: dict, field: str, *, minimum: int = 1, maximum: int | None = None
) -> tuple[str, ...]:
    value = mapping.get(field)
    if not isinstance(value, list) or len(value) < minimum:
        raise DeckValidationError(
            f"{field} must contain at least {minimum} string"
            + ("" if minimum == 1 else "s")
        )
    if maximum is not None and len(value) > maximum:
        raise DeckValidationError(f"{field} may contain at most {maximum} strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise DeckValidationError(f"{field} must contain only non-empty strings")
    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise DeckValidationError(f"{field} contains duplicate values")
    return normalized


def _ledger_index(ledger: dict) -> dict[str, dict]:
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise DeckValidationError("ledger entries must be a list")
    by_key: dict[str, dict] = {}
    for position, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise DeckValidationError(f"ledger entry {position} must be an object")
        key = entry.get("key")
        if not isinstance(key, str) or not key.strip():
            raise DeckValidationError(f"ledger entry {position} has no key")
        if key in by_key:
            raise DeckValidationError(f"ledger contains duplicate key: {key}")
        by_key[key] = entry
    return by_key


def _check_reference_keys(keys: tuple[str, ...], by_key: dict[str, dict]) -> None:
    for key in keys:
        entry = by_key.get(key)
        if entry is None:
            raise DeckValidationError(f"unknown reference key: {key}")
        if not is_verified(entry):
            verification = entry.get("verification") or {}
            raise DeckValidationError(
                f"reference is not verified: {key} "
                f"(status={entry.get('status')}, "
                f"bibliographic={verification.get('bibliographic_status')}, "
                f"retraction={verification.get('retraction_status')})"
            )
        if not isinstance(entry.get("doi"), str) or not entry["doi"].strip():
            raise DeckValidationError(f"verified reference has no DOI: {key}")


def _check_arc(style: str, slides: tuple[ContentSlide, ...]) -> None:
    arc = STYLE_ARCS[style]
    roles = [slide.role for slide in slides]
    unknown = sorted(set(roles) - arc["roles"])
    if unknown:
        raise DeckValidationError(
            f"{style} storyboard has unsupported role(s): {', '.join(unknown)}"
        )
    if roles[0] != arc["first"]:
        raise DeckValidationError(
            f"{style} storyboard must begin with role {arc['first']}"
        )
    if arc["last"] is not None and roles[-1] != arc["last"]:
        raise DeckValidationError(
            f"{style} storyboard must end with role {arc['last']}"
        )
    missing = sorted(arc["required"] - set(roles))
    if missing:
        raise DeckValidationError(
            f"{style} storyboard is missing role(s): {', '.join(missing)}"
        )
    if style == "popsci" and roles.count("contrary-evidence") != 1:
        raise DeckValidationError(
            "popsci storyboard must contain exactly one contrary-evidence turn slide"
        )
    if style == "bullets" and any(role != "point" for role in roles[1:]):
        raise DeckValidationError(
            "bullets storyboard must use one tldr slide followed only by point slides"
        )


def _reference_page_count(size: str, reference_count: int, content_count: int) -> int:
    contract = SIZE_CONTRACTS[size]
    total_min, total_max = contract["total"]
    minimum = max(
        contract["reference_min"],
        total_min - 1 - content_count,
        math.ceil(reference_count / REFERENCE_CAPACITY),
    )
    maximum = total_max - 1 - content_count
    if minimum > maximum:
        raise DeckValidationError(
            f"{reference_count} references and {content_count} content slides cannot "
            f"fit the {size} total-slide cap of {total_max}"
        )
    return minimum


def _partition(items: tuple[dict, ...], parts: int) -> tuple[tuple[dict, ...], ...]:
    if parts < 1 or len(items) < parts:
        raise DeckValidationError(
            "the verified reference list cannot populate every required reference slide"
        )
    quotient, remainder = divmod(len(items), parts)
    chunks = []
    start = 0
    for index in range(parts):
        length = quotient + (1 if index < remainder else 0)
        chunks.append(items[start : start + length])
        start += length
    return tuple(chunks)


def validate_storyboard(storyboard: dict, ledger: dict) -> DeckDocument:
    """Validate JSON data and return the normalized, render-ready deck model."""
    if not isinstance(storyboard, dict):
        raise DeckValidationError("storyboard must be a JSON object")
    unexpected = sorted(set(storyboard) - TOP_LEVEL_FIELDS)
    if unexpected:
        raise DeckValidationError(
            "storyboard has unsupported field(s): " + ", ".join(unexpected)
        )

    title = _string(storyboard, "title")
    subtitle = _string(storyboard, "subtitle", optional=True)
    style = _string(storyboard, "style")
    size = _string(storyboard, "size")
    style = "scientific" if style == "prose" else style
    size = "large" if size == "big" else size
    if style not in STYLE_ARCS:
        raise DeckValidationError("style must be one of: " + ", ".join(STYLE_ARCS))
    if size not in SIZE_CONTRACTS:
        raise DeckValidationError("size must be one of: " + ", ".join(SIZE_CONTRACTS))
    kicker = _string(storyboard, "kicker", optional=True) or STYLE_ARCS[style]["kicker"]

    by_key = _ledger_index(ledger)
    reference_keys = _string_list(storyboard, "reference_keys")
    _check_reference_keys(reference_keys, by_key)
    reference_set = set(reference_keys)

    raw_slides = storyboard.get("slides")
    if not isinstance(raw_slides, list):
        raise DeckValidationError("slides must be a list")
    content_min, content_max = SIZE_CONTRACTS[size]["content"]
    if not content_min <= len(raw_slides) <= content_max:
        raise DeckValidationError(
            f"{size} deck requires {content_min}--{content_max} content slides; "
            f"received {len(raw_slides)}"
        )

    normalized: list[ContentSlide] = []
    seen_ids: set[str] = set()
    for position, raw in enumerate(raw_slides, 1):
        if not isinstance(raw, dict):
            raise DeckValidationError(f"slide {position} must be an object")
        unexpected = sorted(set(raw) - SLIDE_FIELDS)
        if unexpected:
            raise DeckValidationError(
                f"slide {position} has unsupported field(s): {', '.join(unexpected)}"
            )
        slide_id = _string(raw, "id")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", slide_id):
            raise DeckValidationError(
                f"slide {position} id must use lowercase letters, digits, and hyphens"
            )
        if slide_id in seen_ids:
            raise DeckValidationError(f"duplicate slide id: {slide_id}")
        seen_ids.add(slide_id)

        role = _string(raw, "role")
        claim = _string(raw, "title")
        if claim.rstrip("\"\u201d'").endswith((".", "?", "!")) is False:
            raise DeckValidationError(
                f"slide {slide_id} title must be a full sentence ending in punctuation"
            )
        image_path = _string(raw, "image")
        if os.path.splitext(image_path)[1].lower() not in SLIDE_IMAGE_EXTENSIONS:
            raise DeckValidationError(
                f"slide {slide_id} image must be PNG, JPEG, or WebP"
            )
        alt = _string(raw, "alt")
        citations = _string_list(raw, "citations", minimum=1, maximum=5)
        for key in citations:
            if key not in reference_set:
                raise DeckValidationError(
                    f"slide {slide_id} citation {key} is absent from reference_keys"
                )
        evidence = _string(raw, "evidence")
        if evidence not in EVIDENCE_LEVELS:
            raise DeckValidationError(
                f"slide {slide_id} evidence must be strong, mixed, or limited"
            )
        normalized.append(
            ContentSlide(
                slide_id=slide_id,
                role=role,
                title=claim,
                image=image_path,
                alt=alt,
                citations=citations,
                evidence=evidence,
            )
        )

    slides = tuple(normalized)
    _check_arc(style, slides)

    suffixes = year_suffixes(list(reference_keys), by_key, "bracket")
    references = tuple(
        sorted(
            (by_key[key] for key in reference_keys),
            key=lambda entry: (
                (
                    (entry["canonical"].get("authors_structured") or [{"family": ""}])[
                        0
                    ].get("family")
                    or ""
                ).lower(),
                entry["canonical"].get("year") or 0,
                (entry["canonical"].get("title") or "").lower(),
            ),
        )
    )
    page_count = _reference_page_count(size, len(references), len(slides))
    reference_pages = _partition(references, page_count)
    total_slides = 1 + len(slides) + len(reference_pages)
    total_min, total_max = SIZE_CONTRACTS[size]["total"]
    if not total_min <= total_slides <= total_max:
        raise DeckValidationError(
            f"{size} deck total must be {total_min}--{total_max}; got {total_slides}"
        )
    if total_slides > 25:
        raise DeckValidationError("deck exceeds the hard maximum of 25 slides")

    return DeckDocument(
        title=title,
        subtitle=subtitle,
        style=style,
        size=size,
        kicker=kicker,
        slides=slides,
        reference_keys=reference_keys,
        references=references,
        reference_pages=reference_pages,
        suffixes=suffixes,
        total_slides=total_slides,
    )


def embed_slide_images(document: DeckDocument, base_dir: str) -> dict[str, str]:
    """Return validated 16:9 raster assets as data URIs, keyed by slide ID."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise DeckValidationError(
            "deck image validation requires the pinned Pillow runtime"
        ) from exc

    embedded: dict[str, str] = {}
    for slide in document.slides:
        uri = image_data_uri(slide.image, base_dir)
        try:
            payload = base64.b64decode(uri.split(",", 1)[1], validate=True)
            with Image.open(io.BytesIO(payload)) as image:
                width, height = image.size
                image_format = (image.format or "").upper()
                image.verify()
        except (ValueError, OSError, UnidentifiedImageError) as exc:
            raise DeckValidationError(
                f"slide {slide.slide_id} image is not a readable raster"
            ) from exc
        if image_format not in {"PNG", "JPEG", "WEBP"}:
            raise DeckValidationError(
                f"slide {slide.slide_id} image format is not PNG, JPEG, or WebP"
            )
        if width <= 0 or height <= 0 or abs(width / height - 16 / 9) > 0.005:
            raise DeckValidationError(
                f"slide {slide.slide_id} image is {width} x {height}; deck images "
                "must be 16:9"
            )
        embedded[slide.slide_id] = uri
    return embedded


def _identity_strip(
    kicker: str, counter: str, repo_url: str, release: str
) -> str:
    return (
        '<div class="strip">'
        f'<span class="chip">{_brand_logo_html()}</span>'
        '<span class="mark">GROUNDED</span>'
        f'<a class="descriptor" href="{html.escape(repo_url, quote=True)}">'
        'Agentically generated scientific review</a>'
        f'<span class="kicker">{html.escape(kicker)}</span>'
        f'<span class="version">{html.escape(counter)}&nbsp;&nbsp;·&nbsp;&nbsp;'
        f'grounded {html.escape(release)}</span>'
        "</div>"
    )


def _citation_line(
    slide: ContentSlide, by_key: dict[str, dict], suffixes: dict[str, str]
) -> str:
    links = []
    for key in slide.citations:
        entry = by_key[key]
        label = bracket_intext(entry["canonical"], suffixes.get(key, ""))
        links.append(
            f'<a href="{html.escape(doi_href(entry["doi"]), quote=True)}">'
            f"{html.escape(label)}</a>"
        )
    return '<span class="citation-separator"> · </span>'.join(links)


def _balanced_reference_columns(
    entries: tuple[dict, ...], suffixes: dict[str, str], start_number: int
) -> str:
    rendered = []
    for entry in entries:
        rendered.append(
            inline(
                fmt_bracket(
                    entry["canonical"], entry["doi"], suffixes.get(entry["key"], "")
                )
            )
        )
    lengths = [len(re.sub(r"<[^>]+>", "", item)) for item in rendered]
    split = (
        min(
            range(1, len(rendered)),
            key=lambda index: abs(sum(lengths[:index]) - sum(lengths) / 2),
        )
        if len(rendered) > 1
        else 1
    )
    columns = (rendered[:split], rendered[split:])
    html_columns = []
    entry_number = start_number
    for column in columns:
        paragraphs = []
        for item in column:
            paragraphs.append(
                f'<p><span class="ref-number">{entry_number}.</span>{item}</p>'
            )
            entry_number += 1
        html_columns.append(
            '<div class="reference-column">' + "".join(paragraphs) + "</div>"
        )
    return "".join(html_columns)


CSS = r"""
@page { size: 13.333333in 7.5in; margin: 0; }
:root {
  --ink: #141414; --muted: #686868; --faint: #999; --rule: #dedede;
  --accent: #ff4f1f; --paper: #fff;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; }
body { color: var(--ink); }
.slide {
  position: relative; width: 13.333333in; height: 7.5in; overflow: hidden;
  break-after: page; page-break-after: always; background: var(--paper);
}
.slide:last-child { break-after: auto; page-break-after: auto; }
.sans, .strip, .content-footer, .title-meta, .title-kicker,
.reference-heading, .reference-footer {
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
}
.strip {
  height: .46in; margin: 0 .34in; display: flex; align-items: stretch;
  border-bottom: .75pt solid var(--ink); background: #fff;
}
.strip .chip {
  width: .42in; display: flex; align-items: center; justify-content: center;
}
.strip .chip img { width: .32in; height: .32in; display: block; }
.strip .mark {
  display: flex; align-items: center; padding-left: .13in;
  font-size: 9.5pt; font-weight: 650; letter-spacing: .29em;
}
.strip .descriptor {
  display: flex; align-items: center; padding-left: .16in;
  color: var(--muted); font-size: 6.2pt; font-weight: 650;
  letter-spacing: .10em; text-transform: uppercase; text-decoration: none;
}
.strip .kicker {
  display: flex; align-items: center; margin-left: auto; color: var(--accent);
  font-size: 6.4pt; font-weight: 750; letter-spacing: .14em;
  text-transform: uppercase;
}
.strip .version {
  display: flex; align-items: center; min-width: 1.56in; justify-content: flex-end;
  color: var(--muted); font-size: 6.2pt; font-weight: 650;
  letter-spacing: .08em; text-transform: uppercase;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.content-slide .slide-image {
  position: absolute; inset: 0; width: 100%; height: 100%; display: block;
  object-fit: cover;
}
.content-top {
  position: absolute; z-index: 2; left: 0; right: 0; top: 0; height: 1.42in;
  background: rgba(255,255,255,.985); border-bottom: .75pt solid var(--rule);
}
.claim {
  margin: 0; height: .96in; padding: .14in .52in .10in;
  display: flex; align-items: center; color: var(--ink);
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 17pt; line-height: 1.13; font-weight: 430; letter-spacing: -.012em;
  text-align: left; hyphens: none;
}
.content-footer {
  position: absolute; z-index: 2; left: 0; right: 0; bottom: 0; height: .52in;
  padding: 0 .34in; display: flex; align-items: center; gap: .22in;
  background: rgba(255,255,255,.985); border-top: .75pt solid var(--ink);
}
.citations {
  min-width: 0; flex: 1; overflow: hidden; white-space: nowrap;
  font-size: 7.2pt; font-weight: 560; color: #383838; letter-spacing: .005em;
}
.citations a { color: inherit; text-decoration: none; border-bottom: .6pt solid rgba(255,79,31,.7); }
.citation-separator { color: var(--faint); padding: 0 .025in; }
.evidence-chip {
  flex: none; min-width: .82in; padding: .055in .12in .05in;
  border: .8pt solid currentColor; border-radius: .14in; text-align: center;
  font-size: 6.4pt; font-weight: 750; letter-spacing: .12em;
  text-transform: uppercase;
}
.evidence-strong { color: #28734e; background: #edf6f1; }
.evidence-mixed { color: #9a5b14; background: #fff5e8; }
.evidence-limited { color: #6f667d; background: #f3f0f7; }
.title-slide { padding: .55in .65in .48in; }
.title-rule { width: 100%; height: 1pt; background: var(--ink); margin-top: .22in; }
.title-hero { display: grid; grid-template-columns: .78in 1fr; column-gap: .25in; align-items: center; }
.title-chip {
  width: .76in; height: .76in; display: flex; align-items: center; justify-content: center;
}
.title-chip img { width: .62in; height: .62in; display: block; }
.title-mark {
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 25pt; font-weight: 620; letter-spacing: .31em;
}
.title-descriptor {
  grid-column: 2; margin-top: -.17in; color: var(--muted);
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 7.5pt; font-weight: 680; letter-spacing: .12em; text-transform: uppercase;
  text-decoration: none;
}
.title-kicker {
  margin: .72in 0 .12in; color: var(--accent); font-size: 8pt; font-weight: 780;
  letter-spacing: .2em; text-transform: uppercase;
}
.deck-title {
  margin: 0; max-width: 11.3in; font-family: "Charter", "Iowan Old Style", Georgia, serif;
  font-size: 35pt; line-height: 1.05; font-weight: 400; letter-spacing: -.02em;
}
.deck-subtitle {
  margin: .22in 0 0; max-width: 10.5in;
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: var(--muted); font-size: 13pt; line-height: 1.3; font-weight: 430;
}
.title-meta {
  position: absolute; left: .65in; right: .65in; bottom: .49in;
  padding-top: .12in; border-top: .75pt solid var(--ink);
  display: flex; align-items: baseline; gap: .11in; color: var(--faint);
  font-size: 6.6pt; font-weight: 650; letter-spacing: .09em; text-transform: uppercase;
}
.title-meta b { color: var(--accent); }
.title-meta a { color: inherit; text-decoration: none; border-bottom: .5pt solid var(--rule); }
.title-meta .title-counter { margin-left: auto; color: var(--muted); font-size: 7.2pt; }
.title-meta .title-version { color: var(--muted); font-size: 7.2pt; white-space: nowrap; }
.reference-slide { padding-top: 0; }
.reference-heading {
  height: .72in; margin: 0 .47in; display: flex; align-items: center;
  border-bottom: .75pt solid var(--rule);
}
.reference-heading h2 { margin: 0; font-size: 18pt; font-weight: 430; letter-spacing: -.01em; }
.reference-heading h2 { white-space: nowrap; }
.reference-heading span {
  margin-left: auto; color: var(--faint); font-size: 6.3pt; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
}
.reference-grid {
  height: 5.76in; margin: .14in .47in 0; display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: .38in;
  font-family: "Charter", "Iowan Old Style", Georgia, serif;
  font-size: 5.65pt; line-height: 1.18; color: #282828;
}
.reference-grid.reference-sparse { font-size: 7.1pt; line-height: 1.24; }
.reference-grid.reference-normal { font-size: 6.25pt; line-height: 1.2; }
.reference-column { min-width: 0; }
.reference-column p {
  position: relative; margin: 0 0 .055in; padding-left: .24in;
  break-inside: avoid; overflow-wrap: anywhere;
}
.reference-column .ref-number {
  position: absolute; left: 0; color: var(--accent);
  font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: 5.3pt; font-weight: 700;
}
.reference-column strong { font-weight: 700; }
.reference-column em { font-style: italic; }
.reference-column a { color: var(--muted); text-decoration: none; border-bottom: .4pt solid var(--rule); }
.reference-footer {
  position: absolute; left: .47in; right: .47in; bottom: .22in;
  padding-top: .07in; border-top: .75pt solid var(--ink);
  display: flex; color: var(--faint); font-size: 6pt; font-weight: 650;
  letter-spacing: .09em; text-transform: uppercase;
}
.reference-footer span:last-child { margin-left: auto; }
@media screen {
  body { background: #ddd; padding: 16px 0; }
  .slide { margin: 0 auto 16px; box-shadow: 0 2px 18px rgba(0,0,0,.18); }
}
"""


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="Grounded">
<meta name="generator" content="Grounded">
<meta name="description" content="Agentically generated scientific review deck">
<meta name="dcterms.created" content="{compiled_iso}">
<title>{title}</title>
<style>{css}</style>
</head><body>{slides}</body></html>
"""


def build_html(
    storyboard: dict,
    ledger: dict,
    *,
    base_dir: str = ".",
    release: str | None = None,
    repo: str | None = None,
    compiled_date=None,
) -> str:
    """Validate inputs and assemble the canonical, self-contained deck HTML."""
    document = validate_storyboard(storyboard, ledger)
    by_key = _ledger_index(ledger)
    images = embed_slide_images(document, base_dir)
    today = _compiled_date(compiled_date)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if release is None:
        release = detect_release(script_dir)
    if repo is None:
        _repo_label, repo_url = detect_repo(script_dir)
    else:
        repo_url = repo if repo.startswith("http") else f"https://{repo}"
    release = release or "dev"
    repo_url = repo_url or "#"

    title_subtitle = (
        f'<p class="deck-subtitle">{html.escape(document.subtitle)}</p>'
        if document.subtitle
        else ""
    )
    descriptor_link = (
        f'<a href="{html.escape(repo_url, quote=True)}">'
        "Agentically generated scientific review</a>"
        if repo_url != "#"
        else "Agentically generated scientific review"
    )
    title_slide = (
        '<section class="slide title-slide" data-slide-kind="title">'
        '<div class="title-hero">'
        f'<span class="title-chip">{_brand_logo_html()}</span>'
        '<span class="title-mark">GROUNDED</span>'
        f'<a class="title-descriptor" href="{html.escape(repo_url, quote=True)}">'
        'Agentically generated scientific review</a>'
        '</div><div class="title-rule"></div>'
        f'<div class="title-kicker">{html.escape(document.kicker)}</div>'
        f'<h1 class="deck-title">{html.escape(document.title)}</h1>'
        f"{title_subtitle}"
        '<div class="title-meta">'
        f"{descriptor_link}&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"{len(document.reference_keys)} verified references&nbsp;&nbsp;·&nbsp;&nbsp;"
        f"{html.escape(_display_date(today, abbreviated=True))}"
        f'<span class="title-counter">1 / {document.total_slides}</span>'
        f'<span class="title-version">grounded {html.escape(release)}</span>'
        "</div></section>"
    )

    slide_html = [title_slide]
    for index, slide in enumerate(document.slides, 2):
        role = slide.role.replace("-", " ")
        kicker = f"{document.kicker} · {role}"
        citations = _citation_line(slide, by_key, document.suffixes)
        slide_html.append(
            f'<section class="slide content-slide" data-slide-kind="content" '
            f'data-slide-id="{html.escape(slide.slide_id, quote=True)}">'
            f'<img class="slide-image" src="{images[slide.slide_id]}" '
            f'alt="{html.escape(slide.alt, quote=True)}">'
            '<header class="content-top">'
            f'{_identity_strip(kicker, f"{index} / {document.total_slides}", repo_url, release)}'
            f'<h2 class="claim">{html.escape(slide.title)}</h2>'
            "</header>"
            '<footer class="content-footer">'
            f'<div class="citations">{citations}</div>'
            f'<span class="evidence-chip evidence-{slide.evidence}">{slide.evidence}</span>'
            "</footer></section>"
        )

    first_reference_page = 2 + len(document.slides)
    reference_offset = 0
    for page_index, entries in enumerate(document.reference_pages, 1):
        absolute_page = first_reference_page + page_index - 1
        first = reference_offset + 1
        last = reference_offset + len(entries)
        reference_offset = last
        columns = _balanced_reference_columns(
            entries, document.suffixes, start_number=first
        )
        density = (
            "reference-sparse"
            if len(entries) <= 20
            else ("reference-normal" if len(entries) <= 30 else "reference-dense")
        )
        slide_html.append(
            '<section class="slide reference-slide" data-slide-kind="references">'
            f'{_identity_strip("References", f"{absolute_page} / {document.total_slides}", repo_url, release)}'
            '<div class="reference-heading">'
            f"<h2>References {page_index} / {len(document.reference_pages)}</h2>"
            f"<span>Verified sources {first}--{last}</span></div>"
            f'<div class="reference-grid {density}">{columns}</div>'
            '<footer class="reference-footer">'
            "<span>Bibliography and integrity status verified via Crossref</span>"
            f"<span>{len(document.reference_keys)} sources · {document.size} deck</span>"
            "</footer></section>"
        )

    return PAGE.format(
        title=html.escape(document.title),
        compiled_iso=today.isoformat(),
        css=CSS,
        slides="".join(slide_html),
    )


def _atomic_write_text(path: str, content: str) -> None:
    target = Path(path).resolve()
    if not target.parent.is_dir():
        raise DeckValidationError(f"output directory does not exist: {target.parent}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--storyboard", help="deck storyboard JSON")
    parser.add_argument("--ledger", help="verified sources.json ledger")
    parser.add_argument("--out", help="output .pdf or .html path")
    parser.add_argument(
        "--release",
        help="version shown at the right edge of each slide "
             "(default: packaged VERSION)",
    )
    parser.add_argument("--repo", help="repository linked from the slide identity")
    parser.add_argument("--compiled-date", help="fixed YYYY-MM-DD compilation date")
    parser.add_argument(
        "--html-sidecar",
        action="store_true",
        help="also write the canonical HTML beside a PDF",
    )
    parser.add_argument(
        "--check-pdf-runtime",
        action="store_true",
        help="validate the canonical WeasyPrint runtime and exit",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.check_pdf_runtime:
        from weasyprint_export import require_runtime

        print(json.dumps(require_runtime(), sort_keys=True))
        return 0
    if not args.storyboard or not args.ledger or not args.out:
        raise DeckValidationError(
            "--storyboard, --ledger, and --out are required unless checking runtime"
        )

    storyboard = load_json(args.storyboard)
    ledger = load_json(args.ledger)
    base_dir = os.path.dirname(os.path.abspath(args.storyboard))
    release = args.release
    if release is None:
        release = detect_release(os.path.dirname(os.path.abspath(__file__))) or "dev"
    page = build_html(
        storyboard,
        ledger,
        base_dir=base_dir,
        release=release,
        repo=args.repo,
        compiled_date=args.compiled_date,
    )

    extension = os.path.splitext(args.out)[1].lower()
    if extension == ".pdf":
        from weasyprint_export import write_pdf

        result = write_pdf(page, args.out)
        suffix = ""
        if args.html_sidecar:
            sidecar = os.path.splitext(args.out)[0] + ".html"
            _atomic_write_text(sidecar, page)
            suffix = f" and {sidecar}"
        print(
            f"Wrote {args.out} (via {result['renderer']}, sha256 "
            f"{result['sha256']}){suffix}",
            file=sys.stderr,
        )
    elif extension == ".html":
        if args.html_sidecar:
            raise DeckValidationError("--html-sidecar is only valid for PDF output")
        _atomic_write_text(args.out, page)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        raise DeckValidationError("deck output must end in .pdf or .html")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Deck export failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
