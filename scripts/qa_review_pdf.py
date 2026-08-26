#!/usr/bin/env python3
"""Fail-closed structural and raster QA for a Grounded review PDF.

The exporter itself has no external-process dependency.  Release QA deliberately
uses Poppler's ``pdftoppm`` as an independent renderer, then checks every page
with Pillow.  This catches failures that PDF object inspection alone cannot see.
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


A4_POINTS = (595.2756, 841.8898)


class PdfQaError(RuntimeError):
    """Raised when a PDF does not satisfy the Grounded release contract."""


def _load_runtime():
    try:
        from weasyprint_export import require_runtime
        from PIL import Image, ImageDraw, ImageOps
        from pypdf import PdfReader
        require_runtime()
    except (ImportError, RuntimeError) as exc:
        raise PdfQaError(
            "Grounded PDF QA requires the pinned packages in requirements-pdf.txt"
        ) from exc
    return Image, ImageDraw, ImageOps, PdfReader


def _annotations(reader):
    for page_number, page in enumerate(reader.pages, 1):
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            if annotation.get("/Subtype") == "/Link":
                yield page_number, annotation


def _forbidden_document_actions(reader) -> list[str]:
    root = reader.trailer["/Root"]
    failures = []
    if root.get("/OpenAction") is not None:
        failures.append("document has an OpenAction")
    if root.get("/AA") is not None:
        failures.append("document has additional actions")
    names = root.get("/Names")
    if names is not None and names.get_object().get("/JavaScript") is not None:
        failures.append("document contains JavaScript")
    for index, page in enumerate(reader.pages, 1):
        if page.get("/AA") is not None:
            failures.append(f"page {index} has additional actions")
    return failures


def _doi_urls(markdown: str) -> set[str]:
    dois = {
        unquote(re.sub(r"[).,;*_]+$", "", match)).lower()
        for match in re.findall(r"https?://doi\.org/([^\s<>\]]+)", markdown, re.I)
    }
    return {"https://doi.org/" + doi for doi in dois}


def _embedded_font_families(reader) -> set[str]:
    families = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        fonts = resources.get_object().get("/Font")
        if not fonts:
            continue
        for reference in fonts.get_object().values():
            base_font = str(reference.get_object().get("/BaseFont", ""))
            families.add(base_font.split("+", 1)[-1])
    return families


def inspect_structure(pdf_path: str, markdown: str | None = None) -> dict[str, object]:
    """Inspect PDF objects, metadata, page geometry, links, and running furniture."""
    _Image, _ImageDraw, _ImageOps, PdfReader = _load_runtime()
    try:
        reader = PdfReader(pdf_path, strict=True)
    except Exception as exc:
        raise PdfQaError(f"PDF cannot be parsed strictly: {exc}") from exc
    if reader.is_encrypted:
        raise PdfQaError("PDF is encrypted")
    if not reader.pages:
        raise PdfQaError("PDF contains no pages")

    failures = _forbidden_document_actions(reader)
    external_uris: set[str] = set()
    internal_links = 0
    for page_number, annotation in _annotations(reader):
        action = annotation.get("/A")
        destination = annotation.get("/Dest")
        if destination is not None:
            internal_links += 1
        if action is not None:
            action = action.get_object()
            kind = action.get("/S")
            if kind != "/URI":
                failures.append(f"page {page_number} has unsupported link action {kind}")
            elif action.get("/URI"):
                external_uris.add(unquote(str(action["/URI"])).lower())

    for index, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - A4_POINTS[0]) > 0.75 or abs(height - A4_POINTS[1]) > 0.75:
            failures.append(
                f"page {index} is {width:.2f} x {height:.2f} pt instead of A4"
            )
        text = page.extract_text() or ""
        if "G R O U N D E D" not in text or "NO FLOATING CLAIMS." not in text:
            failures.append(f"page {index} is missing the running masthead")
        if f"{index} / {len(reader.pages)}" not in text:
            failures.append(f"page {index} is missing its total-aware page number")

    metadata = reader.metadata or {}
    if metadata.get("/Author") != "Grounded":
        failures.append("PDF author metadata is not Grounded")
    if metadata.get("/Creator") != "Grounded":
        failures.append("PDF creator metadata is not Grounded")
    if metadata.get("/Subject") != "Agentically generated scientific review":
        failures.append("PDF subject metadata is incomplete")
    if metadata.get("/Producer") != "WeasyPrint 69.0":
        failures.append("PDF producer is not the canonical WeasyPrint 69.0 renderer")
    embedded_fonts = _embedded_font_families(reader)
    for family in ("Charter", "Helvetica-Neue"):
        if not any(font.startswith(family) for font in embedded_fonts):
            failures.append(f"PDF does not embed the canonical {family} family")

    expected_dois: set[str] = set()
    expected_figures = 0
    if markdown is not None:
        expected_dois = _doi_urls(markdown)
        expected_figures = len(set(re.findall(
            r'<a id="(fig-[a-z][a-z0-9-]*)"></a>', markdown
        )))
        missing_dois = sorted(expected_dois - external_uris)
        if missing_dois:
            failures.append(
                f"{len(missing_dois)} DOI link(s) are absent from the PDF: "
                + ", ".join(missing_dois[:3])
            )
        if internal_links < expected_figures:
            failures.append(
                f"PDF has {internal_links} internal figure links; expected at least "
                f"{expected_figures}"
            )

    if failures:
        raise PdfQaError("; ".join(failures))
    return {
        "pages": len(reader.pages),
        "external_links": len(external_uris),
        "expected_dois": len(expected_dois),
        "internal_links": internal_links,
        "expected_figures": expected_figures,
        "font_families": sorted(embedded_fonts),
    }


def _ink_count(image, box) -> int:
    return sum(1 for red, green, blue in image.crop(box).get_flattened_data()
               if min(red, green, blue) < 225)


def _accent_count(image, box) -> int:
    return sum(1 for red, green, blue in image.crop(box).get_flattened_data()
               if red > 190 and green < 170 and blue < 140)


def _contact_sheets(page_paths: list[Path], output_dir: Path, Image, ImageDraw,
                    ImageOps) -> list[str]:
    results = []
    for start in range(0, len(page_paths), 6):
        group = page_paths[start:start + 6]
        cells = []
        for page_number, path in enumerate(group, start + 1):
            with Image.open(path) as source:
                page = source.convert("RGB")
            page.thumbnail((620, 877))
            page = ImageOps.expand(page, border=3, fill="black")
            cell = Image.new("RGB", (page.width, page.height + 30), "white")
            cell.paste(page, (0, 30))
            ImageDraw.Draw(cell).text((9, 8), f"PAGE {page_number}", fill="black")
            cells.append(cell)
        columns = min(3, len(cells))
        rows = (len(cells) + columns - 1) // columns
        cell_width = max(cell.width for cell in cells)
        cell_height = max(cell.height for cell in cells)
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#dddddd")
        for index, cell in enumerate(cells):
            sheet.paste(cell, ((index % columns) * cell_width,
                               (index // columns) * cell_height))
        first = start + 1
        last = start + len(group)
        path = output_dir / f"contact-{first:02d}-{last:02d}.png"
        sheet.save(path)
        results.append(str(path))
    return results


def render_and_inspect(pdf_path: str, output_dir: str, *, dpi: int = 120) -> dict[str, object]:
    """Rasterize every page independently and enforce visual invariants."""
    Image, ImageDraw, ImageOps, _PdfReader = _load_runtime()
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise PdfQaError("Poppler pdftoppm is required for independent raster QA")
    if dpi < 72 or dpi > 240:
        raise PdfQaError("QA raster DPI must be between 72 and 240")

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise PdfQaError(f"QA output directory is not empty: {destination}")
    prefix = destination / "page"
    try:
        completed = subprocess.run(
            [renderer, "-png", "-r", str(dpi), pdf_path, str(prefix)],
            check=False, capture_output=True, text=True, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PdfQaError(f"Poppler rasterization failed: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise PdfQaError(f"Poppler rasterization failed: {detail}")
    page_paths = sorted(
        destination.glob("page-*.png"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    if not page_paths:
        raise PdfQaError("Poppler produced no page images")

    failures = []
    dimensions = set()
    accent_counts = []
    scale = (dpi / 75.0) ** 2
    for index, path in enumerate(page_paths, 1):
        with Image.open(path) as source:
            page = source.convert("RGB")
        width, height = page.size
        dimensions.add(page.size)
        if width < 500 or height < 700:
            failures.append(f"page {index} raster is unexpectedly small")
            continue
        header_box = (int(0.04 * width), int(0.025 * height),
                      int(0.96 * width), int(0.085 * height))
        chip_box = (int(0.04 * width), int(0.025 * height),
                    int(0.17 * width), int(0.085 * height))
        page_number_box = (int(0.78 * width), int(0.95 * height),
                           int(0.96 * width), int(0.99 * height))
        body_box = (int(0.04 * width), int(0.085 * height),
                    int(0.96 * width), int(0.93 * height))
        edge_width = max(1, int(0.015 * width))
        edge_ink = _ink_count(page, (0, 0, edge_width, height))
        edge_ink += _ink_count(page, (width - edge_width, 0, width, height))
        header_ink = _ink_count(page, header_box)
        page_number_ink = _ink_count(page, page_number_box)
        body_ink = _ink_count(page, body_box)
        accent = _accent_count(page, chip_box)
        accent_counts.append(accent)
        if header_ink < 600 * scale:
            failures.append(f"page {index} masthead raster is missing or incomplete")
        if accent < 40 * scale:
            failures.append(f"page {index} orange masthead chip is missing")
        if page_number_ink < 8 * scale:
            failures.append(f"page {index} page-number raster is missing")
        if body_ink < 1500 * scale:
            failures.append(f"page {index} body raster is nearly empty")
        if edge_ink > 4 * scale:
            failures.append(f"page {index} has ink at the outer clipping edge")
    if len(dimensions) != 1:
        failures.append("rasterized pages have inconsistent dimensions")
    accent_spread_limit = max(12, 0.08 * max(accent_counts)) if accent_counts else 0
    if accent_counts and max(accent_counts) - min(accent_counts) > accent_spread_limit:
        failures.append("running masthead chip is inconsistent across pages")
    if failures:
        raise PdfQaError("; ".join(failures))

    contacts = _contact_sheets(page_paths, destination, Image, ImageDraw, ImageOps)
    return {
        "dpi": dpi,
        "rendered_pages": len(page_paths),
        "page_size_pixels": list(next(iter(dimensions))),
        "contact_sheets": contacts,
    }


def qa_pdf(pdf_path: str, *, markdown_path: str | None = None,
           render_dir: str | None = None, dpi: int = 120) -> dict[str, object]:
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise PdfQaError(f"PDF does not exist: {pdf_path}")
    markdown = None
    if markdown_path:
        with open(markdown_path, encoding="utf-8") as stream:
            markdown = stream.read()
    structural = inspect_structure(pdf_path, markdown)
    if render_dir is None:
        with tempfile.TemporaryDirectory(prefix="grounded-pdf-qa-") as temporary:
            raster = render_and_inspect(pdf_path, temporary, dpi=dpi)
            raster["contact_sheets"] = []
    else:
        raster = render_and_inspect(pdf_path, render_dir, dpi=dpi)
    if raster["rendered_pages"] != structural["pages"]:
        raise PdfQaError(
            f"Poppler rendered {raster['rendered_pages']} pages but PDF contains "
            f"{structural['pages']}"
        )
    return {"pdf": pdf_path, **structural, **raster, "status": "pass"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Grounded PDF to inspect")
    parser.add_argument("--markdown", help="source review; checks DOI and figure links")
    parser.add_argument(
        "--render-dir", help="new or empty directory for page PNGs and contact sheets"
    )
    parser.add_argument(
        "--dpi", type=int, default=120,
        help="independent raster DPI (72–240; default 120)",
    )
    args = parser.parse_args()
    try:
        result = qa_pdf(
            args.pdf, markdown_path=args.markdown,
            render_dir=args.render_dir, dpi=args.dpi,
        )
    except PdfQaError as exc:
        print(f"PDF QA failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
