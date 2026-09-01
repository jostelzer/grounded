#!/usr/bin/env python3
"""Fail-closed structural and raster QA for a Grounded review PDF.

The exporter itself has no external-process dependency.  Release QA deliberately
uses Poppler's ``pdftoppm`` as an independent renderer, then checks every page
with Pillow.  This catches failures that PDF object inspection alone cannot see.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

from artifact_io import atomic_write_json, sha256_bytes, sha256_file

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


def _normalised_visible_text(value: str) -> str:
    value = unquote(value).lower().replace("\u00ad", "")
    return re.sub(r"\s+", "", value)


def _visible_doi_occurrences(text: str, doi: str) -> int:
    """Count a DOI despite PDF line wrapping and renderer-added hyphenation."""
    text = unquote(text).lower().replace("\u00ad", "")
    doi = unquote(doi).lower().replace("\u00ad", "")
    separator = r"(?:\s*|-\s*)"
    pattern = separator.join(re.escape(character) for character in doi)
    return len(re.findall(pattern, text))


def _manifest_record_path(manifest_path: Path, record: dict[str, object]) -> Path:
    stored = record.get("path")
    if not isinstance(stored, str) or not stored:
        raise PdfQaError("release manifest contains a file without a path")
    return (manifest_path.parent / stored).resolve()


def _verify_file_record(manifest_path: Path, record: dict[str, object], label: str) -> Path:
    path = _manifest_record_path(manifest_path, record)
    if not path.is_file():
        raise PdfQaError(f"release manifest {label} does not exist: {path}")
    expected_hash = record.get("sha256")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise PdfQaError(
            f"release manifest {label} hash changed: expected {expected_hash}, "
            f"found {actual_hash}"
        )
    if record.get("bytes") != path.stat().st_size:
        raise PdfQaError(f"release manifest {label} byte count changed")
    return path


def _verify_figure_geometry(
        figure_path: Path, record: dict[str, object],
        figure_max_height_mm: float, label: str) -> None:
    """Recompute the on-page geometry from the actual pixels.

    The manifest's rendered_width_mm is what figure QA evaluated label sizes
    against; drift between it and the file's true geometry means the labels
    were judged at the wrong physical size.
    """
    try:
        from PIL import Image
        from grounded_metadata import rendered_figure_size_mm
    except ImportError as exc:
        raise PdfQaError(f"figure geometry check needs Pillow: {exc}") from exc
    with Image.open(figure_path) as image:
        pixel_width, pixel_height = image.size
    expected_width, expected_height = rendered_figure_size_mm(
        pixel_width, pixel_height, max_height_mm=figure_max_height_mm
    )
    recorded_width = float(record.get("rendered_width_mm") or 0.0)
    recorded_height = float(record.get("rendered_height_mm") or 0.0)
    if (abs(recorded_width - expected_width) > 0.5
            or abs(recorded_height - expected_height) > 0.5):
        raise PdfQaError(
            f"release manifest {label} geometry drift: recorded "
            f"{recorded_width:.1f}×{recorded_height:.1f} mm but the raster "
            f"renders at {expected_width:.1f}×{expected_height:.1f} mm"
        )


def _matrix_multiply(left, right):
    """Compose two PDF affine matrices using column-vector geometry."""
    a1, b1, c1, d1, e1, f1 = left
    a2, b2, c2, d2, e2, f2 = right
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _painted_image_placements(reader) -> list[dict[str, object]]:
    """Resolve every painted image through page/form transformation matrices."""
    from pypdf.generic import ContentStream

    identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    placements: list[dict[str, object]] = []

    def visit(stream, resources, ctm, page_number, active_forms):
        if stream is None or resources is None:
            return
        resources = resources.get_object()
        xobjects = resources.get("/XObject")
        xobjects = xobjects.get_object() if xobjects else {}
        state_stack = []
        current = ctm
        content = ContentStream(stream, reader)
        for operands, operator in content.operations:
            if operator == b"q":
                state_stack.append(current)
            elif operator == b"Q":
                if state_stack:
                    current = state_stack.pop()
            elif operator == b"cm" and len(operands) == 6:
                matrix = tuple(float(value) for value in operands)
                current = _matrix_multiply(current, matrix)
            elif operator == b"Do" and operands:
                reference = xobjects.get(operands[0])
                if reference is None:
                    continue
                obj = reference.get_object()
                subtype = obj.get("/Subtype")
                if subtype == "/Image":
                    x_length = math.hypot(current[0], current[1])
                    y_length = math.hypot(current[2], current[3])
                    dot = current[0] * current[2] + current[1] * current[3]
                    orthogonality = (
                        abs(dot) / (x_length * y_length)
                        if x_length and y_length else 1.0
                    )
                    placements.append({
                        "page": page_number,
                        "width_px": int(obj.get("/Width") or 0),
                        "height_px": int(obj.get("/Height") or 0),
                        "drawn_width_pt": x_length,
                        "drawn_height_pt": y_length,
                        "drawn_aspect_ratio": (
                            x_length / y_length if y_length else None),
                        "orthogonality_error": orthogonality,
                    })
                elif subtype == "/Form":
                    marker = (
                        getattr(reference, "idnum", None),
                        getattr(reference, "generation", 0),
                    )
                    if marker in active_forms:
                        continue
                    raw_matrix = obj.get("/Matrix") or identity
                    form_matrix = tuple(float(value) for value in raw_matrix)
                    visit(
                        obj,
                        obj.get("/Resources") or resources,
                        _matrix_multiply(current, form_matrix),
                        page_number,
                        active_forms | {marker},
                    )

    for page_number, page in enumerate(reader.pages, 1):
        visit(page.get_contents(), page.get("/Resources"), identity,
              page_number, set())
    return placements


def _verify_pdf_figure_aspects(
        reader, figure_records: list[dict[str, object]] | None,
        tolerance: float = 0.01) -> tuple[list[dict[str, object]], list[str]]:
    """Compare intrinsic figure ratios with the actual PDF image CTMs."""
    if not figure_records:
        return [], []
    expected: dict[tuple[int, int], int] = {}
    for record in figure_records:
        width = record.get("pixel_width")
        height = record.get("pixel_height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            expected[(width, height)] = expected.get((width, height), 0) + 1
    if not expected:
        return [], []

    placements = _painted_image_placements(reader)
    checks: list[dict[str, object]] = []
    failures: list[str] = []
    for dimensions, required_count in expected.items():
        width, height = dimensions
        matches = [
            placement for placement in placements
            if (placement["width_px"], placement["height_px"]) == dimensions
        ]
        if len(matches) < required_count:
            failures.append(
                f"PDF paints {len(matches)} image(s) at {width}×{height}px; "
                f"release manifest requires {required_count}")
            continue
        intrinsic = width / height
        for placement in matches:
            drawn = placement["drawn_aspect_ratio"]
            error = abs(float(drawn) / intrinsic - 1.0) if drawn else float("inf")
            shear = float(placement["orthogonality_error"])
            check = {
                **placement,
                "intrinsic_aspect_ratio": round(intrinsic, 6),
                "relative_aspect_error": round(error, 6),
                "status": "pass" if error <= tolerance and shear <= tolerance else "fail",
            }
            checks.append(check)
            if error > tolerance:
                failures.append(
                    f"page {placement['page']} stretches {width}×{height}px figure: "
                    f"intrinsic ratio {intrinsic:.4f}, painted ratio {float(drawn):.4f}, "
                    f"error {error:.1%}")
            if shear > tolerance:
                failures.append(
                    f"page {placement['page']} shears {width}×{height}px figure "
                    f"(orthogonality error {shear:.3f})")
    return checks, failures


def verify_release_manifest(
        manifest_path: str, pdf_path: str, markdown_path: str | None = None
        ) -> dict[str, object]:
    """Verify all recorded inputs and independently rebuild the exact HTML."""
    path = Path(manifest_path).resolve()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PdfQaError(f"release manifest cannot be read: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise PdfQaError("release manifest schema_version must be 1")
    inputs = manifest.get("inputs")
    artifact = manifest.get("artifact")
    render = manifest.get("render")
    if not isinstance(inputs, dict) or not isinstance(artifact, dict) or not isinstance(render, dict):
        raise PdfQaError("release manifest is missing inputs, artifact, or render")
    review_path = _verify_file_record(path, inputs.get("review") or {}, "review")
    _verify_file_record(path, inputs.get("ledger") or {}, "ledger")
    for category in (
            "figures", "figure_specs", "figure_prompts",
            "figure_inspections", "figure_provenances"):
        records = inputs.get(category, [])
        if not isinstance(records, list):
            raise PdfQaError(f"release manifest {category} must be a list")
        for index, record in enumerate(records, 1):
            if not isinstance(record, dict):
                raise PdfQaError(f"release manifest {category} record is invalid")
            verified = _verify_file_record(path, record, f"{category}[{index}]")
            if category == "figures" and "rendered_width_mm" in record:
                _verify_figure_geometry(
                    verified, record,
                    float(render.get("figure_max_height_mm") or 92.0),
                    f"{category}[{index}]",
                )
    recorded_pdf = _verify_file_record(path, artifact.get("pdf") or {}, "PDF")
    actual_pdf = Path(pdf_path).resolve()
    if actual_pdf != recorded_pdf:
        raise PdfQaError(
            f"QA PDF {actual_pdf} is not manifest PDF {recorded_pdf}"
        )
    if markdown_path is not None and Path(markdown_path).resolve() != review_path:
        raise PdfQaError("--markdown does not identify the manifest review")

    canonical_pdfs = sorted(recorded_pdf.parent.glob("*.pdf"))
    if canonical_pdfs != [recorded_pdf]:
        names = ", ".join(item.name for item in canonical_pdfs)
        raise PdfQaError(
            "release scope must contain exactly one canonical PDF; found " + names
        )

    try:
        import export_review
        markdown = review_path.read_text(encoding="utf-8")
        rebuilt = export_review.build_html(
            markdown,
            columns=int(render.get("columns")),
            style=str(render.get("style") or "scientific"),
            kicker=str(render.get("kicker")),
            colophon=render.get("colophon"),
            base_dir=str(review_path.parent),
            release=str(manifest.get("release")),
            repo=render.get("repo"),
            compiled_date=str(manifest.get("compiled_date")),
            figure_max_height_mm=float(render.get("figure_max_height_mm") or 92.0),
            ref_leading=render.get("ref_leading"),
            imprint=str(render.get("imprint") or "end"),
            edition=str(render.get("edition") or "journal"),
            pull_quote=render.get("pull_quote"),
        )
    except (OSError, TypeError, ValueError) as exc:
        raise PdfQaError(f"manifest HTML cannot be rebuilt: {exc}") from exc
    rebuilt_hash = sha256_bytes(rebuilt.encode("utf-8"))
    if rebuilt_hash != render.get("html_sha256"):
        raise PdfQaError(
            "rebuilt HTML hash does not match the release manifest"
        )
    current_dois = sorted(url.removeprefix("https://doi.org/") for url in _doi_urls(markdown))
    expected = manifest.get("expected") or {}
    if current_dois != expected.get("unique_dois"):
        raise PdfQaError("manifest DOI set does not match the current review")
    return {
        "manifest": manifest,
        "manifest_path": path,
        "review_path": review_path,
        "markdown": markdown,
        "columns": int(render.get("columns")),
        "style": str(render.get("style") or "scientific"),
        "figure_records": inputs.get("figures") or [],
    }


def record_qa_render_set(
        manifest_context: dict[str, object], render_dir: str,
        qa_result: dict[str, object]) -> None:
    path: Path = manifest_context["manifest_path"]
    manifest: dict[str, object] = manifest_context["manifest"]
    destination = Path(render_dir).resolve()
    existing = manifest.get("qa")
    relative = os.path.relpath(destination, path.parent)
    if isinstance(existing, dict) and existing.get("render_directory") != relative:
        raise PdfQaError("release manifest already names a different authoritative QA render set")
    files = [
        {
            "path": os.path.relpath(item, path.parent),
            "bytes": item.stat().st_size,
            "sha256": sha256_file(item),
        }
        for item in sorted(destination.glob("*.png"))
    ]
    manifest["qa"] = {
        "status": "pass",
        "render_directory": relative,
        "dpi": qa_result.get("dpi"),
        "rendered_pages": qa_result.get("rendered_pages"),
        "files": files,
    }
    atomic_write_json(path, manifest)


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


def inspect_structure(pdf_path: str, markdown: str | None = None,
                      expected_release: str | None = None,
                      expected_fonts: tuple[str, ...] = ("Charter", "Helvetica-Neue"),
                      figure_records: list[dict[str, object]] | None = None,
                      ) -> dict[str, object]:
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

    first_page_text = ""
    page_texts = []
    for index, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - A4_POINTS[0]) > 0.75 or abs(height - A4_POINTS[1]) > 0.75:
            failures.append(
                f"page {index} is {width:.2f} x {height:.2f} pt instead of A4"
            )
        text = page.extract_text() or ""
        page_texts.append(text)
        if index == 1:
            first_page_text = text
        # A margin-box descriptor can wrap in narrower editions. PDF text
        # extraction preserves that visual line break even though the semantic
        # label is unchanged, so compare after ordinary whitespace folding.
        masthead_text = re.sub(r"\s+", " ", text)
        if (
            "G R O U N D E D" not in masthead_text
            or "AGENTICALLY GENERATED SCIENTIFIC REVIEW" not in masthead_text
        ):
            failures.append(f"page {index} is missing the running masthead")
        if f"{index} / {len(reader.pages)}" not in text:
            failures.append(f"page {index} is missing its total-aware page number")

    # pypdf sometimes concatenates adjacent masthead runs without a space
    # ("...REVIEWGROUNDED V2.8.0"), so the label match must not require a
    # word boundary before GROUNDED. The version token itself is still
    # matched and compared exactly.
    release_match = re.search(r"GROUNDED\s+(V[^\s·]+)", first_page_text, re.I)
    embedded_release = release_match.group(1).lower() if release_match else None
    if expected_release is not None:
        expected = expected_release.upper()
        if not expected.startswith("V"):
            expected = "V" + expected
        if embedded_release is None:
            failures.append("first page is missing the GROUNDED release label")
        elif embedded_release.upper() != expected:
            failures.append(
                f"PDF embeds release {embedded_release}; expected {expected_release}"
            )

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
    for family in expected_fonts:
        if not any(font.startswith(family) for font in embedded_fonts):
            failures.append(
                f"PDF does not embed the canonical {family} family for its "
                "edition"
            )

    figure_aspect_checks, aspect_failures = _verify_pdf_figure_aspects(
        reader, figure_records)
    failures.extend(aspect_failures)

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
        reference_start_page = None
        reference_offset = None
        reference_title = (
            r"(?:References|R\s+E\s+F\s+E\s+R\s+E\s+N\s+C\s+E\s+S)"
        )
        reference_metadata = (
            r"(?:\d+\s*[·•]\s*)?VERIFIED\s+VIA\s+CROSSREF"
            r"(?:\s*[·•]\s*GROUNDED\s+.+?)?"
        )
        reference_heading = (
            rf"(?mi)^(?:{reference_metadata}\s*)?{reference_title}"
            rf"(?:\s+{reference_metadata})?\s*$"
        )
        for index, text in enumerate(page_texts, 1):
            matches = list(re.finditer(reference_heading, text))
            if matches:
                match = matches[-1]
                reference_start_page = index
                reference_offset = match.start()
        doi_pages = [
            index
            for index, text in enumerate(page_texts, 1)
            if any(
                _visible_doi_occurrences(
                    text, url.removeprefix("https://doi.org/")
                )
                for url in expected_dois
            )
        ]
        if (
            doi_pages
            and reference_start_page is not None
            and reference_start_page < doi_pages[0]
        ):
            # A standalone metadata-grid label is not the terminal heading.
            reference_start_page = None
            reference_offset = None
        if reference_start_page is None:
            failures.append("PDF is missing a visible References heading")
            reference_text = ""
            reference_only_pages = []
        else:
            start_text = page_texts[reference_start_page - 1]
            reference_text = start_text[reference_offset:] + "\n" + "\n".join(
                page_texts[reference_start_page:]
            )
            preceding_words = re.findall(r"\b\w+\b", start_text[:reference_offset])
            reference_only_pages = list(range(reference_start_page + 1, len(page_texts) + 1))
            if len(preceding_words) <= 25:
                reference_only_pages.insert(0, reference_start_page)
        missing_visible = []
        repeated_visible = []
        for url in sorted(expected_dois):
            doi = url.removeprefix("https://doi.org/")
            occurrences = _visible_doi_occurrences(reference_text, doi)
            if occurrences == 0:
                missing_visible.append(url)
            elif occurrences > 1:
                repeated_visible.append(url)
        if missing_visible:
            failures.append(
                f"{len(missing_visible)} DOI(s) are not visible in References: "
                + ", ".join(missing_visible[:3])
            )
        if repeated_visible:
            failures.append(
                f"{len(repeated_visible)} DOI(s) appear more than once in References: "
                + ", ".join(repeated_visible[:3])
            )
    else:
        reference_start_page = None
        reference_only_pages = []

    if failures:
        raise PdfQaError("; ".join(failures))
    return {
        "pages": len(reader.pages),
        "external_links": len(external_uris),
        "expected_dois": len(expected_dois),
        "internal_links": internal_links,
        "expected_figures": expected_figures,
        "font_families": sorted(embedded_fonts),
        "release": embedded_release,
        "reference_start_page": reference_start_page,
        "reference_only_pages": reference_only_pages,
        "visible_reference_dois": len(expected_dois) if markdown is not None else 0,
        "figure_aspect_checks": figure_aspect_checks,
    }


def _ink_count(image, box) -> int:
    return sum(1 for red, green, blue in image.crop(box).get_flattened_data()
               if min(red, green, blue) < 225)


def _accent_count(image, box) -> int:
    return sum(1 for red, green, blue in image.crop(box).get_flattened_data()
               if red > 190 and green < 170 and blue < 140)


def _last_ink_row(image, box) -> tuple[float, float]:
    """Return last meaningful ink row and active-row share within a box."""
    crop = image.crop(box)
    width, height = crop.size
    pixels = crop.load()
    row_threshold = max(3, int(0.004 * width))
    active_rows = []
    for y in range(height):
        ink = sum(1 for x in range(width) if min(pixels[x, y]) < 225)
        if ink >= row_threshold:
            active_rows.append(y)
    if not active_rows:
        return 0.0, 0.0
    return active_rows[-1] / height, len(active_rows) / height


def _page_layout_metrics(page) -> dict[str, float]:
    """Measure page utilization and gross two-column bottom imbalance."""
    width, height = page.size
    x0, x1 = int(0.06 * width), int(0.94 * width)
    y0, y1 = int(0.085 * height), int(0.90 * height)
    midpoint = (x0 + x1) // 2
    gutter = int(0.018 * width)
    fill, active = _last_ink_row(page, (x0, y0, x1, y1))
    left_fill, left_active = _last_ink_row(
        page, (x0, y0, midpoint - gutter, y1)
    )
    right_fill, right_active = _last_ink_row(
        page, (midpoint + gutter, y0, x1, y1)
    )
    return {
        "body_fill": round(fill, 4),
        "active_rows": round(active, 4),
        "left_fill": round(left_fill, 4),
        "right_fill": round(right_fill, 4),
        "left_active_rows": round(left_active, 4),
        "right_active_rows": round(right_active, 4),
        "column_bottom_delta": round(abs(left_fill - right_fill), 4),
    }


def _layout_failures(metrics: dict[str, float], page_number: int,
                     page_count: int, *, reference_page: bool = False,
                     columns: int | None = None) -> list[str]:
    failures = []
    if (page_number < page_count and metrics["body_fill"] < 0.88 and
            metrics["active_rows"] > 0.05):
        failures.append(
            f"page {page_number} is an under-filled non-final page "
            f"(body fill {metrics['body_fill']:.1%})"
        )
    if (metrics["column_bottom_delta"] > 0.45 and
            min(metrics["left_active_rows"], metrics["right_active_rows"]) > 0.15):
        failures.append(
            f"page {page_number} has severely unbalanced column endings "
            f"(delta {metrics['column_bottom_delta']:.1%})"
        )
    if reference_page and page_number == page_count:
        def _sparse_remedy(threshold: float) -> str:
            """Say how far from the threshold the page is and how to close it.

            The distance turns the bare percentage into an actionable target:
            either this page needs proportionally more reference material, or
            the spill should be pulled back entirely (the exporter's bounded
            auto-rebalance and --ref-leading do this without touching type
            size; --columns 1, a --figure-max-height change, or content
            rebalancing are the larger levers)."""
            actual = metrics["active_rows"]
            shortfall = threshold - actual
            if actual > 0:
                factor = threshold / actual
                growth = (
                    f"≈{factor:.1f}× the current reference material on this "
                    "page"
                )
            else:
                growth = "reference material on this page"
            return (
                f" — {shortfall:.1%} of the page short of the {threshold:.0%} "
                f"threshold; either move {growth} here, or pull the spill "
                "back onto the previous page (exporter auto-rebalance / "
                "--ref-leading, --figure-max-height, --columns 1, or content "
                "rebalancing)"
            )

        if columns == 2:
            low = min(metrics["left_active_rows"], metrics["right_active_rows"])
            high = max(metrics["left_active_rows"], metrics["right_active_rows"])
            if low < 0.03 and high < 0.65:
                failures.append(
                    f"final reference page has an empty column and only "
                    f"{high:.1%} active-row use in the other"
                    + _sparse_remedy(0.25)
                )
            if metrics["active_rows"] < 0.25:
                failures.append(
                    f"final two-column reference page is extremely sparse "
                    f"({metrics['active_rows']:.1%} active rows)"
                    + _sparse_remedy(0.25)
                )
        elif columns == 1 and metrics["active_rows"] < 0.30:
            failures.append(
                f"final one-column reference page is extremely sparse "
                f"({metrics['active_rows']:.1%} active rows)"
                + _sparse_remedy(0.30)
            )
    return failures


def _layout_warnings(metrics: dict[str, float], page_number: int,
                     page_count: int, *, reference_page: bool = False,
                     columns: int | None = None) -> list[str]:
    if not reference_page or page_number != page_count:
        return []
    threshold = 0.40 if columns == 2 else 0.45
    if metrics["active_rows"] < threshold:
        return [
            f"final reference page is sparse ({metrics['active_rows']:.1%} active rows)"
        ]
    return []


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


def render_and_inspect(pdf_path: str, output_dir: str, *, dpi: int = 120,
                       reference_start_page: int | None = None,
                       reference_only_pages: list[int] | None = None,
                       columns: int | None = None) -> dict[str, object]:
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
    layout_metrics = []
    warnings = []
    reference_page_set = (
        set(reference_only_pages) if reference_only_pages is not None else None
    )
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
        # Wide enough to hold the chip under any edition's page margins
        # (journal 13mm through primer 30mm); the gate still requires the
        # orange chip to exist in the masthead band on every page.
        chip_box = (int(0.04 * width), int(0.025 * height),
                    int(0.24 * width), int(0.085 * height))
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
        layout = _page_layout_metrics(page)
        layout_metrics.append({"page": index, **layout})
        reference_page = (
            index in reference_page_set
            if reference_page_set is not None
            else bool(reference_start_page and index >= reference_start_page)
        )
        failures.extend(_layout_failures(
            layout, index, len(page_paths), reference_page=reference_page,
            columns=columns,
        ))
        warnings.extend(_layout_warnings(
            layout, index, len(page_paths), reference_page=reference_page,
            columns=columns,
        ))
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
        "layout_metrics": layout_metrics,
        "warnings": warnings,
    }


def qa_pdf(pdf_path: str, *, markdown_path: str | None = None,
           render_dir: str | None = None, dpi: int = 120,
           expected_release: str | None = None,
           manifest_path: str | None = None,
           expected_edition: str | None = None) -> dict[str, object]:
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise PdfQaError(f"PDF does not exist: {pdf_path}")
    manifest_context = None
    columns = None
    if manifest_path:
        if render_dir is None:
            raise PdfQaError("release-manifest QA requires an explicit --render-dir")
        if Path(render_dir).resolve() == Path(manifest_path).resolve().parent:
            raise PdfQaError(
                "authoritative QA renders must use a case-local subdirectory, "
                "not the release directory itself"
            )
        manifest_context = verify_release_manifest(
            manifest_path, pdf_path, markdown_path
        )
        markdown = manifest_context["markdown"]
        markdown_path = str(manifest_context["review_path"])
        columns = manifest_context["columns"]
        if expected_release is None:
            expected_release = str(manifest_context["manifest"].get("release"))
    else:
        markdown = None
    if markdown_path and markdown is None:
        with open(markdown_path, encoding="utf-8") as stream:
            markdown = stream.read()
    expected_fonts = ("Charter", "Helvetica-Neue")
    if manifest_path:
        edition = str(
            (manifest_context["manifest"].get("render") or {}).get("edition")
            or "journal"
        )
        if expected_edition is not None and expected_edition != edition:
            raise PdfQaError(
                f"requested edition {expected_edition!r} does not match "
                f"manifest edition {edition!r}"
            )
        try:
            import export_review
            expected_fonts = tuple(export_review.EDITIONS[edition]["fonts"])
        except (ImportError, KeyError) as exc:
            raise PdfQaError(f"unknown manifest edition {edition!r}") from exc
    elif expected_edition is not None:
        try:
            import export_review
            expected_fonts = tuple(export_review.EDITIONS[expected_edition]["fonts"])
        except (ImportError, KeyError) as exc:
            raise PdfQaError(f"unknown requested edition {expected_edition!r}") from exc
    structural = inspect_structure(
        pdf_path, markdown, expected_release,
        expected_fonts=expected_fonts,
        figure_records=(
            manifest_context.get("figure_records")
            if manifest_context is not None else None
        ),
    )
    if render_dir is None:
        with tempfile.TemporaryDirectory(prefix="grounded-pdf-qa-") as temporary:
            raster = render_and_inspect(
                pdf_path, temporary, dpi=dpi,
                reference_start_page=structural["reference_start_page"],
                reference_only_pages=structural["reference_only_pages"],
                columns=columns,
            )
            raster["contact_sheets"] = []
    else:
        raster = render_and_inspect(
            pdf_path, render_dir, dpi=dpi,
            reference_start_page=structural["reference_start_page"],
            reference_only_pages=structural["reference_only_pages"],
            columns=columns,
        )
    if raster["rendered_pages"] != structural["pages"]:
        raise PdfQaError(
            f"Poppler rendered {raster['rendered_pages']} pages but PDF contains "
            f"{structural['pages']}"
        )
    result = {"pdf": pdf_path, **structural, **raster, "status": "pass"}
    if manifest_context is not None:
        record_qa_render_set(manifest_context, render_dir, result)
        result["release_manifest"] = str(Path(manifest_path).resolve())
    return result


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
    parser.add_argument(
        "--release", help="required GROUNDED release label embedded on page 1"
    )
    parser.add_argument(
        "--manifest", help="release-manifest.json; verifies exact lineage and records QA"
    )
    parser.add_argument(
        "--edition", choices=("journal", "salon", "primer", "brief"),
        help="expected PDF edition when no manifest is available; with a manifest, "
             "must match its recorded edition",
    )
    parser.add_argument("--report", help="atomically write the JSON QA report")
    args = parser.parse_args()
    try:
        result = qa_pdf(
            args.pdf, markdown_path=args.markdown,
            render_dir=args.render_dir, dpi=args.dpi,
            expected_release=args.release,
            manifest_path=args.manifest,
            expected_edition=args.edition,
        )
    except PdfQaError as exc:
        print(f"PDF QA failed: {exc}", file=sys.stderr)
        return 2
    if args.report:
        try:
            atomic_write_json(args.report, result)
        except OSError as exc:
            print(f"PDF QA report failed: {exc}", file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
