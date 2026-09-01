#!/usr/bin/env python3
"""Fail-closed structural and raster QA for a Grounded slide-deck PDF.

Structural QA checks the canonical 16:9 geometry, page kinds, content images,
per-slide DOI annotations, evidence chips, counters, metadata, fonts, and safe
document actions.  Independent Poppler rasterization then checks every landscape
page for painted chrome, visible content, clipping, and overflow symptoms.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

import export_deck
import qa_review_pdf
from format_references import doi_href


DECK_POINTS = export_deck.DECK_POINTS


class DeckPdfQaError(RuntimeError):
    """Raised when a deck PDF does not satisfy the Grounded contract."""


def _load_runtime():
    try:
        return qa_review_pdf._load_runtime()
    except qa_review_pdf.PdfQaError as exc:
        raise DeckPdfQaError(str(exc)) from exc


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _page_image_count(page, reader) -> int:
    """Count raster XObjects actually painted by this page's content stream."""
    from pypdf.generic import ContentStream

    seen_forms: set[tuple[int, int] | int] = set()

    def visit(stream, resources) -> int:
        if stream is None or resources is None:
            return 0
        resources = resources.get_object()
        xobjects = resources.get("/XObject")
        if not xobjects:
            return 0
        xobjects = xobjects.get_object()
        count = 0
        content = ContentStream(stream, reader)
        for operands, operator in content.operations:
            if operator != b"Do" or not operands:
                continue
            reference = xobjects.get(operands[0])
            if reference is None:
                continue
            obj = reference.get_object()
            subtype = obj.get("/Subtype")
            if subtype == "/Image":
                count += 1
            elif subtype == "/Form":
                indirect = getattr(reference, "idnum", None)
                generation = getattr(reference, "generation", 0)
                marker = (indirect, generation) if indirect is not None else id(obj)
                if marker not in seen_forms:
                    seen_forms.add(marker)
                    count += visit(obj, obj.get("/Resources") or resources)
        return count

    return visit(page.get_contents(), page.get("/Resources"))


def _page_link_contract(reader) -> tuple[list[set[str]], list[str]]:
    uris = [set() for _page in reader.pages]
    failures = []
    for page_number, annotation in qa_review_pdf._annotations(reader):
        action = annotation.get("/A")
        destination = annotation.get("/Dest")
        if destination is not None:
            failures.append(f"page {page_number} contains an unexpected internal link")
        if action is None:
            continue
        action = action.get_object()
        kind = action.get("/S")
        if kind != "/URI":
            failures.append(f"page {page_number} has unsupported link action {kind}")
        elif action.get("/URI"):
            uris[page_number - 1].add(unquote(str(action["/URI"])).lower())
    return uris, failures


def _expected_doi(entry: dict) -> str:
    return unquote(doi_href(entry["doi"])).lower()


def _release_from_text(text: str) -> str | None:
    match = re.search(r"\bGROUNDED\s*(V[^\s\u00b7]+)", text, re.I)
    return match.group(1).lower() if match else None


def _page_text_failures(page_number: int, page_count: int, text: str) -> list[str]:
    normalized = _normalized_text(text)
    upper = normalized.upper()
    failures = []
    if "GROUNDED" not in upper and "G R O U N D E D" not in upper:
        failures.append(f"page {page_number} is missing the GROUNDED identity")
    if "AGENTICALLY GENERATED SCIENTIFIC REVIEW" not in upper:
        failures.append(f"page {page_number} is missing the linked review descriptor")
    if not re.search(rf"\b{page_number}\s*/\s*{page_count}\b", normalized):
        failures.append(f"page {page_number} is missing its total-aware slide counter")
    return failures


def inspect_structure(
    pdf_path: str, storyboard: dict, ledger: dict, expected_release: str | None = None
) -> dict[str, object]:
    """Inspect PDF objects against the validated storyboard and ledger."""
    document = export_deck.validate_storyboard(storyboard, ledger)
    _Image, _ImageDraw, _ImageOps, PdfReader = _load_runtime()
    try:
        reader = PdfReader(pdf_path, strict=True)
    except Exception as exc:
        raise DeckPdfQaError(f"PDF cannot be parsed strictly: {exc}") from exc
    if reader.is_encrypted:
        raise DeckPdfQaError("PDF is encrypted")
    if len(reader.pages) != document.total_slides:
        raise DeckPdfQaError(
            f"PDF contains {len(reader.pages)} pages; storyboard requires "
            f"{document.total_slides}"
        )

    failures = list(qa_review_pdf._forbidden_document_actions(reader))
    page_uris, link_failures = _page_link_contract(reader)
    failures.extend(link_failures)
    image_counts = []
    page_text = []
    for page_number, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - DECK_POINTS[0]) > 0.75 or abs(height - DECK_POINTS[1]) > 0.75:
            failures.append(
                f"page {page_number} is {width:.2f} x {height:.2f} pt instead of "
                "canonical 16:9"
            )
        text = page.extract_text() or ""
        page_text.append(text)
        failures.extend(_page_text_failures(page_number, document.total_slides, text))
        image_counts.append(_page_image_count(page, reader))

    if image_counts[0] != 1:
        failures.append("title slide must contain exactly one packaged logo image")

    by_key = export_deck._ledger_index(ledger)
    for offset, slide in enumerate(document.slides, 1):
        page_index = offset
        page_number = page_index + 1
        normalized = _normalized_text(page_text[page_index])
        if _normalized_text(slide.title) not in normalized:
            failures.append(
                f"content slide {page_number} is missing its real-text claim title"
            )
        if slide.evidence.upper() not in normalized.upper():
            failures.append(
                f"content slide {page_number} is missing evidence chip {slide.evidence}"
            )
        if image_counts[page_index] < 2:
            failures.append(
                f"content slide {page_number} is missing its logo or raster body image"
            )
        expected = {_expected_doi(by_key[key]) for key in slide.citations}
        missing = sorted(expected - page_uris[page_index])
        if missing:
            failures.append(
                f"content slide {page_number} is missing {len(missing)} DOI link(s): "
                + ", ".join(missing)
            )

    first_reference = 1 + len(document.slides)
    for offset, entries in enumerate(document.reference_pages):
        page_index = first_reference + offset
        page_number = page_index + 1
        if image_counts[page_index] != 1:
            failures.append(
                f"reference slide {page_number} must contain exactly one packaged logo image"
            )
        if "REFERENCES" not in page_text[page_index].upper():
            failures.append(f"reference slide {page_number} is missing its heading")
        expected = {_expected_doi(entry) for entry in entries}
        missing = sorted(expected - page_uris[page_index])
        if missing:
            failures.append(
                f"reference slide {page_number} is missing {len(missing)} DOI link(s)"
            )

    all_expected = {_expected_doi(entry) for entry in document.references}
    all_uris = set().union(*page_uris)
    missing = sorted(all_expected - all_uris)
    if missing:
        failures.append(
            f"{len(missing)} verified reference DOI link(s) are absent from the deck"
        )

    metadata = reader.metadata or {}
    if metadata.get("/Author") != "Grounded":
        failures.append("PDF author metadata is not Grounded")
    if metadata.get("/Creator") != "Grounded":
        failures.append("PDF creator metadata is not Grounded")
    if metadata.get("/Subject") != "Agentically generated scientific review deck":
        failures.append("PDF subject metadata is not the Grounded deck identity")
    if metadata.get("/Producer") != "WeasyPrint 69.0":
        failures.append("PDF producer is not the canonical WeasyPrint 69.0 renderer")
    embedded_fonts = qa_review_pdf._embedded_font_families(reader)
    for family in ("Charter", "Helvetica-Neue"):
        if not any(font.startswith(family) for font in embedded_fonts):
            failures.append(f"PDF does not embed the canonical {family} family")

    release = _release_from_text(_normalized_text(page_text[0]))
    if expected_release is not None:
        expected = expected_release.upper()
        if not expected.startswith("V"):
            expected = "V" + expected
        if release is None:
            failures.append("title slide is missing the GROUNDED release label")
        elif release.upper() != expected:
            failures.append(
                f"PDF embeds release {release}; expected {expected_release}"
            )

    if failures:
        raise DeckPdfQaError("; ".join(failures))
    return {
        "pages": len(reader.pages),
        "content_slides": len(document.slides),
        "reference_slides": len(document.reference_pages),
        "expected_dois": len(all_expected),
        "external_links": sum(len(page) for page in page_uris),
        "image_counts": image_counts,
        "font_families": sorted(embedded_fonts),
        "release": release,
    }


def _white_share(image, box) -> float:
    pixels = image.crop(box).get_flattened_data()
    total = 0
    white = 0
    for red, green, blue in pixels:
        total += 1
        if min(red, green, blue) > 245:
            white += 1
    return white / total if total else 0.0


def _raster_page_failures(
    page, page_number: int, page_count: int, page_kind: str, *, dpi: int
) -> list[str]:
    """Check one landscape raster for chrome, content, and clipping symptoms."""
    width, height = page.size
    scale = (dpi / 75.0) ** 2
    failures = []
    if width <= height or abs(width / height - 16 / 9) > 0.015:
        failures.append(f"page {page_number} raster is not 16:9 landscape")
        return failures

    top = (0, 0, width, int(0.19 * height))
    strip = (int(0.02 * width), 0, int(0.98 * width), int(0.068 * height))
    chip = (int(0.02 * width), 0, int(0.065 * width), int(0.07 * height))
    top_counter = (int(0.90 * width), 0, int(0.98 * width), int(0.075 * height))
    footer = (0, int(0.928 * height), width, height)
    # Stop above the intentional full-width rule at the chrome/body boundary;
    # only accidental text or furniture at the physical edge should count.
    side_chrome = (0, 0, int(0.012 * width), int(0.18 * height))
    side_chrome_right = (int(0.988 * width), 0, width, int(0.18 * height))

    if page_kind in {"content", "references"}:
        if qa_review_pdf._ink_count(page, strip) < 450 * scale:
            failures.append(f"page {page_number} masthead raster is missing")
        if qa_review_pdf._accent_count(page, chip) < 28 * scale:
            failures.append(f"page {page_number} orange ground chip is missing")
        if qa_review_pdf._ink_count(page, top_counter) < 6 * scale:
            failures.append(f"page {page_number} slide-counter raster is missing")
        if qa_review_pdf._ink_count(page, side_chrome) > 4 * scale:
            failures.append(f"page {page_number} chrome clips at the left edge")
        if qa_review_pdf._ink_count(page, side_chrome_right) > 4 * scale:
            failures.append(f"page {page_number} chrome clips at the right edge")

    if page_kind == "content":
        claim = (
            int(0.025 * width),
            int(0.065 * height),
            int(0.975 * width),
            int(0.19 * height),
        )
        visual = (0, int(0.19 * height), width, int(0.928 * height))
        citations = (int(0.02 * width), int(0.928 * height), int(0.87 * width), height)
        evidence = (int(0.87 * width), int(0.928 * height), width, height)
        if _white_share(page, top) < 0.72:
            failures.append(f"content slide {page_number} top chrome is not intact")
        if _white_share(page, footer) < 0.72:
            failures.append(f"content slide {page_number} footer chrome is not intact")
        if qa_review_pdf._ink_count(page, claim) < 180 * scale:
            failures.append(f"content slide {page_number} claim title is not painted")
        if qa_review_pdf._ink_count(page, visual) < 1200 * scale:
            failures.append(f"content slide {page_number} body image is nearly empty")
        if qa_review_pdf._ink_count(page, citations) < 45 * scale:
            failures.append(f"content slide {page_number} citation line is not painted")
        if qa_review_pdf._ink_count(page, evidence) < 18 * scale:
            failures.append(f"content slide {page_number} evidence chip is not painted")
    elif page_kind == "references":
        body = (
            int(0.03 * width),
            int(0.14 * height),
            int(0.97 * width),
            int(0.92 * height),
        )
        if qa_review_pdf._ink_count(page, body) < 700 * scale:
            failures.append(f"reference slide {page_number} text body is nearly empty")
    else:
        hero = (
            int(0.03 * width),
            int(0.04 * height),
            int(0.97 * width),
            int(0.92 * height),
        )
        bottom_counter = (int(0.88 * width), int(0.91 * height), width, height)
        if qa_review_pdf._ink_count(page, hero) < 650 * scale:
            failures.append("title slide hero is missing or incomplete")
        if qa_review_pdf._accent_count(page, hero) < 35 * scale:
            failures.append("title slide ground chip is missing")
        if qa_review_pdf._ink_count(page, bottom_counter) < 6 * scale:
            failures.append("title slide counter is not painted")
    return failures


def _landscape_contact_sheets(
    page_paths: list[Path], output_dir: Path, Image, ImageDraw, ImageOps
) -> list[str]:
    results = []
    for start in range(0, len(page_paths), 4):
        group = page_paths[start : start + 4]
        cells = []
        for page_number, path in enumerate(group, start + 1):
            with Image.open(path) as source:
                page = source.convert("RGB")
            page.thumbnail((860, 484))
            page = ImageOps.expand(page, border=3, fill="black")
            cell = Image.new("RGB", (page.width, page.height + 30), "white")
            cell.paste(page, (0, 30))
            ImageDraw.Draw(cell).text((9, 8), f"SLIDE {page_number}", fill="black")
            cells.append(cell)
        columns = min(2, len(cells))
        rows = (len(cells) + columns - 1) // columns
        cell_width = max(cell.width for cell in cells)
        cell_height = max(cell.height for cell in cells)
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#dddddd")
        for index, cell in enumerate(cells):
            sheet.paste(
                cell,
                (
                    (index % columns) * cell_width,
                    (index // columns) * cell_height,
                ),
            )
        first = start + 1
        last = start + len(group)
        path = output_dir / f"contact-{first:02d}-{last:02d}.png"
        sheet.save(path)
        results.append(str(path))
    return results


def render_and_inspect(
    pdf_path: str,
    output_dir: str,
    *,
    content_slides: int,
    reference_slides: int,
    dpi: int = 120,
) -> dict[str, object]:
    """Rasterize every slide with Poppler and enforce landscape visual invariants."""
    Image, ImageDraw, ImageOps, _PdfReader = _load_runtime()
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise DeckPdfQaError("Poppler pdftoppm is required for independent deck QA")
    if dpi < 72 or dpi > 240:
        raise DeckPdfQaError("QA raster DPI must be between 72 and 240")

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise DeckPdfQaError(f"QA output directory is not empty: {destination}")
    prefix = destination / "slide"
    try:
        completed = subprocess.run(
            [renderer, "-png", "-r", str(dpi), pdf_path, str(prefix)],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeckPdfQaError(f"Poppler rasterization failed: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise DeckPdfQaError(f"Poppler rasterization failed: {detail}")
    page_paths = sorted(
        destination.glob("slide-*.png"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    expected_pages = 1 + content_slides + reference_slides
    if len(page_paths) != expected_pages:
        raise DeckPdfQaError(
            f"Poppler rendered {len(page_paths)} pages; expected {expected_pages}"
        )

    failures = []
    dimensions = set()
    for page_number, path in enumerate(page_paths, 1):
        with Image.open(path) as source:
            page = source.convert("RGB")
        dimensions.add(page.size)
        if page_number == 1:
            kind = "title"
        elif page_number <= 1 + content_slides:
            kind = "content"
        else:
            kind = "references"
        failures.extend(
            _raster_page_failures(page, page_number, expected_pages, kind, dpi=dpi)
        )
    if len(dimensions) != 1:
        failures.append("rasterized deck pages have inconsistent dimensions")
    if failures:
        raise DeckPdfQaError("; ".join(failures))

    contacts = _landscape_contact_sheets(
        page_paths, destination, Image, ImageDraw, ImageOps
    )
    return {
        "dpi": dpi,
        "rendered_pages": len(page_paths),
        "page_size_pixels": list(next(iter(dimensions))),
        "contact_sheets": contacts,
    }


def qa_pdf(
    pdf_path: str,
    *,
    storyboard_path: str,
    ledger_path: str,
    render_dir: str | None = None,
    dpi: int = 120,
    expected_release: str | None = None,
) -> dict[str, object]:
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise DeckPdfQaError(f"PDF does not exist: {pdf_path}")
    storyboard = export_deck.load_json(storyboard_path)
    ledger = export_deck.load_json(ledger_path)
    structural = inspect_structure(
        pdf_path, storyboard, ledger, expected_release=expected_release
    )
    if render_dir is None:
        with tempfile.TemporaryDirectory(prefix="grounded-deck-qa-") as temporary:
            raster = render_and_inspect(
                pdf_path,
                temporary,
                content_slides=structural["content_slides"],
                reference_slides=structural["reference_slides"],
                dpi=dpi,
            )
            raster["contact_sheets"] = []
    else:
        raster = render_and_inspect(
            pdf_path,
            render_dir,
            content_slides=structural["content_slides"],
            reference_slides=structural["reference_slides"],
            dpi=dpi,
        )
    return {"pdf": pdf_path, **structural, **raster, "status": "pass"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Grounded deck PDF to inspect")
    parser.add_argument("--storyboard", required=True, help="source storyboard JSON")
    parser.add_argument("--ledger", required=True, help="verified sources.json ledger")
    parser.add_argument(
        "--render-dir", help="new or empty directory for slide PNGs and contact sheets"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=120,
        help="independent raster DPI (72--240; default 120)",
    )
    parser.add_argument(
        "--release", help="required GROUNDED release label embedded on slide 1"
    )
    args = parser.parse_args(argv)
    result = qa_pdf(
        args.pdf,
        storyboard_path=args.storyboard,
        ledger_path=args.ledger,
        render_dir=args.render_dir,
        dpi=args.dpi,
        expected_release=args.release,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, DeckPdfQaError) as exc:
        print(f"Deck PDF QA failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
