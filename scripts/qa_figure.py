#!/usr/bin/env python3
"""Compare a rendered Grounded figure with its evidence/copy specification."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import unicodedata
from pathlib import Path

from artifact_io import sha256_file
from grounded_metadata import rendered_figure_size_mm
from typing import Any


VISUAL_QUALITY_DIMENSIONS = (
    "composition",
    "hierarchy",
    "domain_specificity",
    "style_fit",
    "polish",
)


def _normal(value: str) -> str:
    """Normalize text for spec-vs-OCR comparison.

    Both the expected copy and the OCR output pass through this same fold, so
    the mapping never alters what a figure must say — only the comparison
    space. The confusable folds exist because OCR cannot distinguish glyphs
    that are pixel-identical in Arial: capital I and lowercase l ("CI" reads
    as "Cl"), and the minus sign family.
    """
    value = unicodedata.normalize("NFKC", value).lower()
    value = value.replace("–", "-").replace("—", "-").replace("−", "-")
    value = re.sub(r"[​‌‍﻿]", "", value)
    value = value.replace("l", "i").replace("|", "i")
    return re.sub(r"[^a-z0-9%+./=-]+", " ", value).strip()


def expected_pixel_text(spec: dict[str, Any]) -> list[str]:
    exact = spec.get("exact_text")
    if not isinstance(exact, list) or not exact or not all(
        isinstance(item, str) and item.strip() for item in exact
    ):
        raise ValueError("figure spec exact_text must be a non-empty string list")
    rendered = [item.strip() for item in exact]
    if spec.get("render_context", "article") in {"article", "slide"}:
        omitted = {str(spec.get("title") or "").strip(), str(spec.get("subtitle") or "").strip()}
        rendered = [item for item in rendered if item not in omitted]
    return rendered


def _tesseract(image_path: Path) -> tuple[str, float | None]:
    executable = shutil.which("tesseract")
    if not executable:
        raise ValueError("Tesseract is required for figure OCR")
    completed = subprocess.run(
        [executable, str(image_path), "stdout", "tsv"],
        check=False, capture_output=True, text=True, timeout=120,
    )
    if completed.returncode:
        raise ValueError("Tesseract OCR failed: " + (completed.stderr.strip() or "unknown error"))
    lines = completed.stdout.splitlines()
    if not lines:
        return "", None
    header = lines[0].split("\t")
    index = {name: position for position, name in enumerate(header)}
    words = []
    heights = []
    for line in lines[1:]:
        fields = line.split("\t")
        try:
            text = fields[index["text"]].strip()
            confidence = float(fields[index["conf"]])
            height = int(fields[index["height"]])
        except (IndexError, KeyError, ValueError):
            continue
        if text and confidence >= 40:
            words.append(text)
            if len(re.sub(r"\W", "", text)) >= 2:
                heights.append(height)
    label_height = None
    if heights:
        ordered = sorted(heights)
        label_height = float(ordered[max(0, round(0.10 * (len(ordered) - 1)))])
    # The TSV pass drops words below its confidence floor, which can lose
    # short tokens ("=", "95%") from lines the plain pass reads correctly.
    # Text presence is checked against both passes; label heights only ever
    # come from the TSV geometry.
    plain = subprocess.run(
        [executable, str(image_path), "stdout"],
        check=False, capture_output=True, text=True, timeout=120,
    )
    plain_text = plain.stdout if plain.returncode == 0 else ""
    combined = " ".join(part for part in (" ".join(words), plain_text) if part)
    return combined, label_height


def _relationship_tuple(value: dict[str, Any]) -> tuple[str, str, str]:
    try:
        return (
            _normal(str(value["from"])),
            _normal(str(value["relation"])),
            _normal(str(value["to"])),
        )
    except KeyError as exc:
        raise ValueError("relationships require from, relation, and to") from exc


def _required_number(value: Any, field: str, *, minimum: float,
                     maximum: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(
            f"{field} must be between {minimum:g} and {maximum:g}")
    return result


def _validate_provenance(
    spec: dict[str, Any], image_path: Path,
    provenance: dict[str, Any] | None,
) -> list[str]:
    """Return fail-closed provenance errors for quality-contract figures."""
    errors: list[str] = []
    contract_version = spec.get("quality_contract_version")
    if provenance is None:
        if contract_version == 1:
            errors.append("quality contract v1 requires generation provenance")
        return errors
    if not isinstance(provenance, dict):
        raise ValueError("figure provenance must be an object")
    if provenance.get("schema_version") != 1:
        errors.append("generation provenance schema_version must be 1")

    generator_available = provenance.get("generator_available")
    if not isinstance(generator_available, bool):
        errors.append("generation provenance requires boolean generator_available")
        generator_available = False
    if generator_available:
        generator = provenance.get("generator")
        if not isinstance(generator, dict) or not str(generator.get("tool") or "").strip():
            errors.append("available generator provenance requires generator.tool")

    route = spec.get("render_route")
    selected_route = provenance.get("selected_route")
    if contract_version == 1 and route not in {"generated", "hybrid", "deterministic"}:
        errors.append("quality contract v1 requires an explicit valid render_route")
    if selected_route != route:
        errors.append(
            f"provenance selected_route {selected_route!r} does not match spec {route!r}")

    selected_asset = provenance.get("selected_asset")
    if not isinstance(selected_asset, str) or Path(selected_asset).name != image_path.name:
        errors.append("provenance selected_asset does not identify the audited image")
    expected_hash = provenance.get("selected_sha256")
    actual_hash = sha256_file(image_path)
    if expected_hash != actual_hash:
        errors.append("provenance selected_sha256 does not match the audited image")

    attempts = provenance.get("attempts")
    if not isinstance(attempts, list):
        errors.append("generation provenance attempts must be a list")
        attempts = []
    elif any(not isinstance(item, dict) for item in attempts):
        errors.append("every generation provenance attempt must be an object")
        attempts = [item for item in attempts if isinstance(item, dict)]
    generate_attempts = [item for item in attempts if item.get("kind") == "generate"]
    edit_attempts = [item for item in attempts if item.get("kind") == "edit"]
    compose_attempts = [item for item in attempts if item.get("kind") == "compose"]

    comparison = provenance.get("comparison")
    compared = 0
    if isinstance(comparison, dict):
        value = comparison.get("candidates_compared")
        if isinstance(value, int) and not isinstance(value, bool):
            compared = value
        else:
            errors.append("comparison.candidates_compared must be an integer")
        if not str(comparison.get("selection_rationale") or "").strip():
            errors.append("comparison requires a non-empty selection_rationale")
    elif comparison is not None:
        errors.append("generation provenance comparison must be an object")

    if route in {"generated", "hybrid"}:
        if not generator_available:
            errors.append(f"{route} route requires an available image generator")
        if not generate_attempts:
            errors.append(f"{route} route requires a generated candidate")
        if len(generate_attempts) > 1 and compared < 2:
            errors.append(
                f"{route} route with multiple candidates requires comparison of at least two")
        if len(generate_attempts) == 1 and comparison is not None and compared < 1:
            errors.append("single-candidate provenance requires candidates_compared=1")
        if compared > len(generate_attempts):
            errors.append(
                "comparison.candidates_compared exceeds recorded generated candidates")

    if route == "hybrid":
        if provenance.get("direct_text_attempted") is not True:
            errors.append("hybrid fallback requires direct_text_attempted=true")
        if not any(item.get("text_mode") == "direct" for item in generate_attempts):
            errors.append("hybrid fallback requires a direct-text generate attempt")
        if not str(provenance.get("fallback_reason") or "").strip():
            errors.append("hybrid fallback requires a concrete fallback_reason")
        if len(generate_attempts) < 2 and not edit_attempts:
            errors.append(
                "hybrid fallback requires a targeted edit or a second generated candidate")
        hybrid = provenance.get("hybrid")
        if not isinstance(hybrid, dict):
            errors.append("hybrid route requires hybrid composition provenance")
        else:
            if not str(hybrid.get("compositor") or "").strip():
                errors.append("hybrid provenance requires a compositor")
            if not str(hybrid.get("base_asset") or "").strip():
                errors.append("hybrid provenance requires a base_asset")
            if hybrid.get("anisotropic_resize") is not False:
                errors.append("hybrid composition must prove anisotropic_resize=false")
        if not compose_attempts:
            errors.append("hybrid route requires a compose attempt")

    if route == "deterministic" and spec.get("archetype") != "quantitative":
        if generator_available:
            if len(generate_attempts) < 2:
                errors.append(
                    "non-quantitative deterministic fallback requires two generated candidates")
            if not edit_attempts:
                errors.append(
                    "non-quantitative deterministic fallback requires a targeted edit")
        if provenance.get("hybrid_considered") is not True:
            errors.append(
                "non-quantitative deterministic fallback requires hybrid_considered=true")
        if not str(provenance.get("fallback_reason") or "").strip():
            errors.append(
                "non-quantitative deterministic fallback requires a concrete fallback_reason")
    return errors


def audit_figure(
    spec: dict[str, Any], image_path: str | Path, *,
    inspection: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    pdf_width_mm: float | None = None,
) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for figure QA") from exc
    path = Path(image_path)
    with Image.open(path) as image:
        width, height = image.size
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            flattened = Image.new("RGBA", rgba.size, "white")
            flattened.alpha_composite(rgba)
            grey = flattened.convert("L")
        else:
            grey = image.convert("L")
        from PIL import ImageStat
        pixel_stddev = float(ImageStat.Stat(grey).stddev[0])
        pixel_extrema = list(grey.getextrema())
    if width < 800 or height < 400:
        raise ValueError("figure raster is too small for publication QA")
    if pdf_width_mm is None:
        # Default to the width this raster will actually render at in the
        # journal PDF: full content width unless the exporter's figure
        # height cap forces a proportional scale-down. An explicit
        # --pdf-width-mm still overrides for non-journal deliveries.
        pdf_width_mm, _rendered_height = rendered_figure_size_mm(width, height)
    if not 50 <= pdf_width_mm <= 190:
        raise ValueError("pdf_width_mm must be between 50 and 190")

    contract_version = spec.get("quality_contract_version")
    if contract_version not in {None, 1}:
        raise ValueError("quality_contract_version must be 1 when supplied")
    errors: list[str] = []
    if pixel_stddev < 2.0:
        errors.append(
            f"figure is blank or near-blank (pixel standard deviation {pixel_stddev:.2f})")

    target_aspect = spec.get("target_aspect_ratio")
    actual_aspect = width / height
    aspect_error = None
    if target_aspect is None:
        if contract_version == 1:
            errors.append("quality contract v1 requires target_aspect_ratio")
    else:
        target_aspect = _required_number(
            target_aspect, "target_aspect_ratio", minimum=1.0, maximum=4.0)
        tolerance = _required_number(
            spec.get("aspect_ratio_tolerance", 0.03),
            "aspect_ratio_tolerance", minimum=0.0, maximum=0.1)
        aspect_error = abs(actual_aspect / target_aspect - 1.0)
        if aspect_error > tolerance:
            errors.append(
                f"raster aspect {actual_aspect:.4f} differs from target "
                f"{target_aspect:.4f} by {aspect_error:.1%}; stretching is forbidden")

    inspection = inspection or {}
    if not isinstance(inspection, dict):
        raise ValueError("figure inspection must be an object")
    warnings: list[str] = []
    ocr_text = inspection.get("ocr_text")
    measured_height = inspection.get("minimum_label_height_px")
    if not isinstance(ocr_text, str):
        ocr_text, tesseract_height = _tesseract(path)
        if measured_height is None:
            measured_height = tesseract_height
    elif shutil.which("tesseract"):
        machine_text, _machine_height = _tesseract(path)
        machine_normal = _normal(machine_text)
        overridden = [
            text for text in expected_pixel_text(spec)
            if _normal(text) not in machine_normal
        ]
        if len(overridden) >= 3:
            message = (
                "manual OCR transcript asserts "
                f"{len(overridden)} expected item(s) tesseract could not read: "
                + "; ".join(overridden[:5]))
            if contract_version == 1:
                errors.append(message)
            else:
                warnings.append(message + " — confirm each by visual inspection")
    else:
        warnings.append(
            "manual OCR transcript used without a tesseract cross-check"
        )
    if measured_height is not None:
        try:
            measured_height = float(measured_height)
        except (TypeError, ValueError) as exc:
            raise ValueError("minimum_label_height_px must be numeric") from exc

    expected_text = expected_pixel_text(spec)
    normal_ocr = _normal(ocr_text)
    missing_text = [text for text in expected_text if _normal(text) not in normal_ocr]
    errors.extend(f"missing expected text: {text}" for text in missing_text)

    abbreviations = spec.get("abbreviations", {})
    if not isinstance(abbreviations, dict):
        raise ValueError("figure spec abbreviations must be an object")
    missing_expansions = []
    for short, expansion in abbreviations.items():
        definition = f"{short} = {expansion}"
        if _normal(definition) not in normal_ocr:
            missing_expansions.append(definition)
            errors.append(f"unexpanded local abbreviation: {definition}")

    expected_relationships = spec.get("relationships", [])
    observed_relationships = inspection.get("relationships", [])
    if not isinstance(expected_relationships, list) or not isinstance(observed_relationships, list):
        raise ValueError("relationships must be lists")
    expected_set = {_relationship_tuple(item) for item in expected_relationships}
    observed_set = {_relationship_tuple(item) for item in observed_relationships}
    for source, relation, target in sorted(expected_set - observed_set):
        if (target, relation, source) in observed_set:
            errors.append(
                f"reversed relationship: {source} --{relation}--> {target}"
            )
        else:
            errors.append(
                f"missing relationship: {source} --{relation}--> {target}"
            )

    detected_effects = inspection.get("detected_effects", [])
    if not isinstance(detected_effects, list):
        raise ValueError("detected_effects must be a list")
    avoid_text = " ".join(str(item) for item in spec.get("avoid", []))
    prohibited = {
        effect for effect in ("gradient", "drop shadow", "shadow", "glow", "3d")
        if effect in avoid_text.lower()
    }
    for effect in sorted(prohibited & {_normal(str(item)) for item in detected_effects}):
        errors.append(f"prohibited visual effect detected: {effect}")

    collisions = inspection.get("text_collisions", [])
    if not isinstance(collisions, list):
        raise ValueError("text_collisions must be a list")
    for collision in collisions:
        errors.append(f"text collision: {collision}")

    duplicate_text = inspection.get("duplicate_text")
    unlisted_text = inspection.get("unlisted_text")
    if contract_version == 1:
        if duplicate_text is None:
            errors.append("quality contract v1 inspection requires duplicate_text")
            duplicate_text = []
        if unlisted_text is None:
            errors.append("quality contract v1 inspection requires unlisted_text")
            unlisted_text = []
    if duplicate_text is None:
        duplicate_text = []
    if unlisted_text is None:
        unlisted_text = []
    if not isinstance(duplicate_text, list):
        raise ValueError("duplicate_text must be a list")
    if not isinstance(unlisted_text, list):
        raise ValueError("unlisted_text must be a list")
    for text in duplicate_text:
        errors.append(f"duplicated rendered text: {text}")
    for text in unlisted_text:
        errors.append(f"unlisted rendered text: {text}")

    geometry_distortions = inspection.get("geometry_distortions")
    if geometry_distortions is None:
        if contract_version == 1:
            errors.append("quality contract v1 inspection requires geometry_distortions")
        geometry_distortions = []
    if not isinstance(geometry_distortions, list):
        raise ValueError("geometry_distortions must be a list")
    for distortion in geometry_distortions:
        errors.append(f"geometry distortion: {distortion}")

    visual_quality = inspection.get("visual_quality")
    if contract_version == 1:
        if not isinstance(visual_quality, dict):
            errors.append("quality contract v1 inspection requires visual_quality")
            visual_quality = {}
        for dimension in VISUAL_QUALITY_DIMENSIONS:
            verdict = visual_quality.get(dimension)
            if verdict != "pass":
                errors.append(
                    f"visual quality {dimension} must pass; found {verdict!r}")
    elif visual_quality is not None and not isinstance(visual_quality, dict):
        raise ValueError("visual_quality must be an object")

    errors.extend(_validate_provenance(spec, path, provenance))

    effective_points = None
    if measured_height is None:
        errors.append("minimum label height could not be measured")
    else:
        effective_points = measured_height * (pdf_width_mm / width) * (72.0 / 25.4)
        if effective_points < 6.5:
            errors.append(
                f"smallest effective label is {effective_points:.2f} pt at a "
                f"{pdf_width_mm:.1f} mm rendered width; required at least 6.5 pt"
            )
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "width_px": width,
            "height_px": height,
            "actual_aspect_ratio": round(actual_aspect, 6),
            "target_aspect_ratio": (
                round(float(target_aspect), 6) if target_aspect is not None else None
            ),
            "aspect_ratio_relative_error": (
                round(aspect_error, 6) if aspect_error is not None else None
            ),
            "pixel_standard_deviation": round(pixel_stddev, 3),
            "pixel_extrema": pixel_extrema,
            "ocr_characters": len(ocr_text),
            "expected_text_items": len(expected_text),
            "missing_text_items": len(missing_text),
            "relationships_expected": len(expected_set),
            "relationships_observed": len(observed_set),
            "minimum_label_height_px": measured_height,
            "minimum_effective_label_pt": (
                round(effective_points, 2) if effective_points is not None else None
            ),
            "missing_abbreviation_expansions": missing_expansions,
            "geometry_distortions": len(geometry_distortions),
            "duplicate_text_items": len(duplicate_text),
            "unlisted_text_items": len(unlisted_text),
            "visual_quality": visual_quality,
            "render_route": spec.get("render_route"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--inspection",
        help="optional structured topology/effects/OCR inspection JSON",
    )
    parser.add_argument(
        "--provenance",
        help="generation/composition provenance JSON; required by quality contract v1",
    )
    parser.add_argument(
        "--pdf-width-mm", type=float, default=None,
        help="rendered width to evaluate label sizes at; defaults to the "
             "width the journal PDF will actually display this raster at "
             "(content width, reduced when the figure height cap applies)",
    )
    args = parser.parse_args(argv)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        inspection = (
            json.loads(Path(args.inspection).read_text(encoding="utf-8"))
            if args.inspection else None
        )
        provenance = (
            json.loads(Path(args.provenance).read_text(encoding="utf-8"))
            if args.provenance else None
        )
        result = audit_figure(
            spec, args.image, inspection=inspection, provenance=provenance,
            pdf_width_mm=args.pdf_width_mm,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Figure QA failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
