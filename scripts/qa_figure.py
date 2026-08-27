#!/usr/bin/env python3
"""Compare a rendered Grounded figure with its evidence/copy specification."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any


def _normal(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    value = value.replace("–", "-").replace("—", "-")
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
    return " ".join(words), label_height


def _relationship_tuple(value: dict[str, Any]) -> tuple[str, str, str]:
    try:
        return (
            _normal(str(value["from"])),
            _normal(str(value["relation"])),
            _normal(str(value["to"])),
        )
    except KeyError as exc:
        raise ValueError("relationships require from, relation, and to") from exc


def audit_figure(
    spec: dict[str, Any], image_path: str | Path, *,
    inspection: dict[str, Any] | None = None,
    pdf_width_mm: float = 170.0,
) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for figure QA") from exc
    path = Path(image_path)
    with Image.open(path) as image:
        width, height = image.size
    if width < 800 or height < 400:
        raise ValueError("figure raster is too small for publication QA")
    if not 50 <= pdf_width_mm <= 190:
        raise ValueError("pdf_width_mm must be between 50 and 190")

    inspection = inspection or {}
    ocr_text = inspection.get("ocr_text")
    measured_height = inspection.get("minimum_label_height_px")
    if not isinstance(ocr_text, str):
        ocr_text, tesseract_height = _tesseract(path)
        if measured_height is None:
            measured_height = tesseract_height
    if measured_height is not None:
        try:
            measured_height = float(measured_height)
        except (TypeError, ValueError) as exc:
            raise ValueError("minimum_label_height_px must be numeric") from exc

    expected_text = expected_pixel_text(spec)
    normal_ocr = _normal(ocr_text)
    missing_text = [text for text in expected_text if _normal(text) not in normal_ocr]
    errors = [f"missing expected text: {text}" for text in missing_text]

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

    effective_points = None
    if measured_height is None:
        errors.append("minimum label height could not be measured")
    else:
        effective_points = measured_height * (pdf_width_mm / width) * (72.0 / 25.4)
        if effective_points < 6.5:
            errors.append(
                f"smallest effective label is {effective_points:.2f} pt; required at least 6.5 pt"
            )
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "metrics": {
            "width_px": width,
            "height_px": height,
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
    parser.add_argument("--pdf-width-mm", type=float, default=170.0)
    args = parser.parse_args(argv)
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        inspection = (
            json.loads(Path(args.inspection).read_text(encoding="utf-8"))
            if args.inspection else None
        )
        result = audit_figure(
            spec, args.image, inspection=inspection,
            pdf_width_mm=args.pdf_width_mm,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Figure QA failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
