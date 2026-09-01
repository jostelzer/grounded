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

from artifact_io import atomic_write_json
import figure_contract
from figure_provenance import validate_provenance
from grounded_metadata import rendered_figure_size_mm
from typing import Any


VISUAL_QUALITY_DIMENSIONS = (
    "composition",
    "hierarchy",
    "domain_specificity",
    "style_fit",
    "polish",
)
V2_VISUAL_QUALITY_DIMENSIONS = VISUAL_QUALITY_DIMENSIONS + (
    "explanatory_value",
    "information_flow",
    "intuitiveness",
)
V3_VISUAL_QUALITY_DIMENSIONS = V2_VISUAL_QUALITY_DIMENSIONS + (
    "concept_coherence",
    "anatomical_integrity",
    "connector_semantics",
    "logical_grouping",
    "salience",
    "nonredundancy",
    "typography",
)
MAX_ARTICLE_P90_TEXT_HEIGHT_SHORT_EDGE_FRACTION = 0.055
MAX_STANDALONE_P90_TEXT_HEIGHT_SHORT_EDGE_FRACTION = 0.07
MAX_ARTICLE_TEXT_BOX_AREA_FRACTION = 0.20
MAX_STANDALONE_TEXT_BOX_AREA_FRACTION = 0.24


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


def _tesseract_metrics(
    image_path: Path,
) -> tuple[str, float | None, float | None, float | None]:
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
        return "", None, None, None
    header = lines[0].split("\t")
    index = {name: position for position, name in enumerate(header)}
    words = []
    heights = []
    text_box_area = 0
    for line in lines[1:]:
        fields = line.split("\t")
        try:
            text = fields[index["text"]].strip()
            confidence = float(fields[index["conf"]])
            height = int(fields[index["height"]])
            width = int(fields[index["width"]])
        except (IndexError, KeyError, ValueError):
            continue
        if text and confidence >= 40:
            words.append(text)
            if len(re.sub(r"\W", "", text)) >= 2:
                heights.append(height)
                text_box_area += width * height
    label_height = None
    p90_height = None
    if heights:
        ordered = sorted(heights)
        label_height = float(ordered[max(0, round(0.10 * (len(ordered) - 1)))])
        p90_height = float(ordered[min(
            len(ordered) - 1, round(0.90 * (len(ordered) - 1)))])
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
    try:
        from PIL import Image
        with Image.open(image_path) as image:
            canvas_area = image.width * image.height
    except (ImportError, OSError):
        canvas_area = 0
    text_area_fraction = text_box_area / canvas_area if canvas_area else None
    return combined, label_height, p90_height, text_area_fraction


def _tesseract(image_path: Path) -> tuple[str, float | None]:
    """Backward-compatible text/minimum-height helper used by renderer tests."""
    text, label_height, _p90_height, _area_fraction = _tesseract_metrics(image_path)
    return text, label_height


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


def _outer_frame_exact_white_share(image) -> float:
    """Measure exact #FFFFFF paper on the clear five-percent safety band."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    band = max(1, round(min(width, height) * 0.05))
    pixels = rgb.load()
    total = 0
    white = 0
    for y in range(height):
        for x in range(width):
            if x < band or x >= width - band or y < band or y >= height - band:
                total += 1
                if pixels[x, y] == (255, 255, 255):
                    white += 1
    return white / total if total else 0.0


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
        alpha_minimum = 255
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            alpha_minimum = rgba.getchannel("A").getextrema()[0]
            flattened = Image.new("RGBA", rgba.size, "white")
            flattened.alpha_composite(rgba)
            rgb = flattened.convert("RGB")
        else:
            rgb = image.convert("RGB")
        grey = rgb.convert("L")
        outer_frame_white_share = _outer_frame_exact_white_share(rgb)
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
    if contract_version not in {None, 1, 2, 3}:
        raise ValueError("quality_contract_version must be 1, 2, or 3 when supplied")
    errors: list[str] = []
    communication_goal = None
    annotation_plan = None
    semantic_plan = None
    layout_plan = None
    composite_plan = None
    if contract_version in {2, 3}:
        communication_goal = figure_contract.validate_communication_goal(spec)
        annotation_plan = figure_contract.validate_annotation_plan(
            spec, expected_pixel_text(spec))
        if spec.get("archetype") == "quantitative":
            figure_contract.validate_plot_design(spec)
            if spec.get("render_route") not in {"deterministic", "composite"}:
                errors.append(
                    "communication-first quantitative figures require deterministic or composite plotting")
            if spec.get("render_route") == "composite":
                figure_contract.validate_concept_plan(spec)
                composite_plan = figure_contract.validate_composite_plan(spec)
            if spec.get("data") is None or spec.get("data") in ([], {}):
                errors.append(
                    "communication-first quantitative plots require verified structured data")
        else:
            figure_contract.validate_concept_plan(spec)
            raw_semantic = spec.get("semantic_plan")
            identity_hybrid = (
                contract_version == 3
                and spec.get("render_route") == "hybrid"
                and isinstance(raw_semantic, dict)
                and bool(raw_semantic.get("cross_view_identity"))
            )
            if spec.get("render_route") != "generated" and not identity_hybrid:
                errors.append(
                    "communication-first non-quantitative figures require image generation; "
                    "v3 permits hybrid only for declared cross-view identity preservation")
            if spec.get("data") is not None:
                errors.append(
                    "known numbers that carry the figure belong in a quantitative deterministic plot")
            rendered_text = expected_pixel_text(spec)
            word_counts = [len(item.split()) for item in rendered_text]
            if len(rendered_text) > figure_contract.V2_GENERATED_MAX_STRINGS:
                errors.append(
                    "communication-first generated illustrations have too many labels")
            if (word_counts and max(word_counts)
                    > figure_contract.V2_GENERATED_MAX_WORDS_PER_STRING):
                errors.append(
                    "communication-first generated illustration has an overlong label")
            if sum(word_counts) > figure_contract.V2_GENERATED_MAX_WORDS:
                errors.append(
                    "communication-first generated illustration has too much in-pixel copy")
        if contract_version == 3:
            semantic_plan = figure_contract.validate_semantic_plan(
                spec, annotation_plan)
            layout_plan = figure_contract.validate_layout_plan(spec)
            figure_contract.validate_v3_rendered_copy(
                spec, expected_pixel_text(spec))
            missing_mobile_labels = [
                item for item in layout_plan["mobile_preview"]["primary_labels"]
                if item not in expected_pixel_text(spec)
            ]
            if missing_mobile_labels:
                errors.append(
                    "mobile primary labels are absent from rendered exact_text: %s"
                    % ", ".join(missing_mobile_labels))
            if alpha_minimum < 255:
                errors.append(
                    "quality contract v3 requires an opaque canvas; transparent pixels are forbidden")
            if outer_frame_white_share != 1.0:
                errors.append(
                    "outer figure canvas is not exact #FFFFFF "
                    f"({outer_frame_white_share:.3%} exact-white safety-band pixels; "
                    "required 100%)")
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
    machine_text = None
    machine_minimum_height = None
    machine_p90_height = None
    machine_text_area_fraction = None
    if shutil.which("tesseract"):
        (machine_text, machine_minimum_height, machine_p90_height,
         machine_text_area_fraction) = _tesseract_metrics(path)
    if not isinstance(ocr_text, str):
        if machine_text is None:
            raise ValueError("Tesseract is required when ocr_text is not supplied")
        ocr_text = machine_text
        if measured_height is None:
            measured_height = machine_minimum_height
    elif machine_text is not None:
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
        if contract_version == 3:
            continue
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
    if contract_version in {1, 2, 3}:
        if duplicate_text is None:
            errors.append(
                f"quality contract v{contract_version} inspection requires duplicate_text")
            duplicate_text = []
        if unlisted_text is None:
            errors.append(
                f"quality contract v{contract_version} inspection requires unlisted_text")
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
        if contract_version in {1, 2, 3}:
            errors.append(
                f"quality contract v{contract_version} inspection requires geometry_distortions")
        geometry_distortions = []
    if not isinstance(geometry_distortions, list):
        raise ValueError("geometry_distortions must be a list")
    for distortion in geometry_distortions:
        errors.append(f"geometry distortion: {distortion}")

    visual_quality = inspection.get("visual_quality")
    if contract_version in {1, 2, 3}:
        if not isinstance(visual_quality, dict):
            errors.append(
                f"quality contract v{contract_version} inspection requires visual_quality")
            visual_quality = {}
        dimensions = (
            V3_VISUAL_QUALITY_DIMENSIONS if contract_version == 3
            else V2_VISUAL_QUALITY_DIMENSIONS if contract_version == 2
            else VISUAL_QUALITY_DIMENSIONS)
        for dimension in dimensions:
            verdict = visual_quality.get(dimension)
            if verdict != "pass":
                errors.append(
                    f"visual quality {dimension} must pass; found {verdict!r}")
    elif visual_quality is not None and not isinstance(visual_quality, dict):
        raise ValueError("visual_quality must be an object")

    typography_scale = inspection.get("typography_scale")
    effective_p90_text_height = None
    effective_text_area_fraction = None
    mobile_primary_label_height = None
    if contract_version == 3:
        if not isinstance(typography_scale, dict):
            errors.append(
                "quality contract v3 inspection requires typography_scale")
            typography_scale = {}
        try:
            reported_p90 = _required_number(
                typography_scale.get("p90_label_height_px"),
                "typography_scale.p90_label_height_px",
                minimum=0.0, maximum=float(height),
            )
        except ValueError as exc:
            errors.append(str(exc))
            reported_p90 = 0.0
        try:
            reported_area = _required_number(
                typography_scale.get("text_box_area_fraction"),
                "typography_scale.text_box_area_fraction",
                minimum=0.0, maximum=1.0,
            )
        except ValueError as exc:
            errors.append(str(exc))
            reported_area = 0.0
        if typography_scale.get("display_headline_absent") is not True:
            errors.append(
                "typography scale inspection must confirm display_headline_absent")
        if typography_scale.get("labels_subordinate_to_visuals") is not True:
            errors.append(
                "typography scale inspection must confirm labels_subordinate_to_visuals")
        effective_p90_text_height = max(
            reported_p90, machine_p90_height or 0.0)
        effective_text_area_fraction = max(
            reported_area, machine_text_area_fraction or 0.0)
        standalone = spec.get("render_context", "article") == "standalone"
        height_fraction_limit = (
            MAX_STANDALONE_P90_TEXT_HEIGHT_SHORT_EDGE_FRACTION
            if standalone else MAX_ARTICLE_P90_TEXT_HEIGHT_SHORT_EDGE_FRACTION)
        area_fraction_limit = (
            MAX_STANDALONE_TEXT_BOX_AREA_FRACTION
            if standalone else MAX_ARTICLE_TEXT_BOX_AREA_FRACTION)
        height_fraction = effective_p90_text_height / min(width, height)
        if height_fraction > height_fraction_limit:
            errors.append(
                "typography dominates the artwork: the robust upper label height is "
                f"{effective_p90_text_height:.1f} px ({height_fraction:.1%} of the "
                f"short canvas edge; maximum {height_fraction_limit:.1%})")
        if effective_text_area_fraction > area_fraction_limit:
            errors.append(
                "typography occupies too much of the artwork: OCR text boxes cover "
                f"{effective_text_area_fraction:.1%} of the canvas; maximum "
                f"{area_fraction_limit:.1%}")

    communication = inspection.get("communication")
    if contract_version in {2, 3}:
        if not isinstance(communication, dict):
            errors.append(
                f"quality contract v{contract_version} inspection requires communication")
            communication = {}
        if not str(communication.get("observed_takeaway") or "").strip():
            errors.append("communication inspection requires observed_takeaway")
        if not str(communication.get("observed_explain_back") or "").strip():
            errors.append("communication inspection requires observed_explain_back")
        if communication.get("explain_back_matches") is not True:
            errors.append("communication inspection must confirm explain_back_matches")
        if communication.get("intuitive_without_caption") is not True:
            errors.append("communication inspection must confirm intuitive_without_caption")
        if communication.get("familiar_starting_point_visible") is not True:
            errors.append(
                "communication inspection must confirm familiar_starting_point_visible")
        if communication.get("requires_caption_to_understand") is not False:
            errors.append(
                "communication inspection must set requires_caption_to_understand=false")
        unexplained_jargon = communication.get("unexplained_jargon")
        if not isinstance(unexplained_jargon, list):
            errors.append("communication inspection requires unexplained_jargon list")
            unexplained_jargon = []
        for term in unexplained_jargon:
            errors.append(f"unexplained figure jargon: {term}")
        if communication.get("intended_takeaway_conveyed") is not True:
            errors.append("communication inspection must confirm intended_takeaway_conveyed")
        if communication.get("information_flow_clear") is not True:
            errors.append("communication inspection must confirm information_flow_clear")
        visible = communication.get("must_show_visible")
        if not isinstance(visible, list):
            errors.append("communication inspection requires must_show_visible list")
            visible = []
        for item in communication_goal["must_show"]:
            if item not in visible:
                errors.append(
                    f"communication inspection did not confirm must-show item: {item}")
        observed_flow = communication.get("observed_information_flow")
        if not isinstance(observed_flow, list) or not observed_flow:
            errors.append(
                "communication inspection requires a non-empty observed_information_flow")
        ambiguous = communication.get("misleading_or_ambiguous")
        if not isinstance(ambiguous, list):
            errors.append("communication inspection requires misleading_or_ambiguous list")
            ambiguous = []
        for item in ambiguous:
            errors.append(f"misleading or ambiguous communication: {item}")
        if communication.get("revision_needed") is not False:
            errors.append(
                "selected figure communication inspection must set revision_needed=false")
        if contract_version == 3:
            mobile_observed = inspection.get("mobile_preview")
            if not isinstance(mobile_observed, dict):
                errors.append(
                    "quality contract v3 inspection requires mobile_preview")
                mobile_observed = {}
            mobile_planned = layout_plan["mobile_preview"]
            if mobile_observed.get("width_px") != mobile_planned["width_px"]:
                errors.append(
                    "mobile inspection must use the planned 390 px preview width")
            readable = mobile_observed.get("readable_primary_labels")
            if not isinstance(readable, list):
                errors.append(
                    "mobile inspection requires readable_primary_labels list")
                readable = []
            for label in mobile_planned["primary_labels"]:
                if label not in readable:
                    errors.append(
                        f"mobile inspection did not confirm readable primary label: {label}")
            try:
                native_primary_height = _required_number(
                    mobile_observed.get("minimum_primary_label_height_px"),
                    "mobile_preview.minimum_primary_label_height_px",
                    minimum=0.0, maximum=float(height),
                )
                mobile_primary_label_height = (
                    native_primary_height * mobile_planned["width_px"] / width)
                if (mobile_primary_label_height
                        < mobile_planned["minimum_primary_label_height_px"]):
                    errors.append(
                        "smallest mobile primary label is "
                        f"{mobile_primary_label_height:.2f} px at a "
                        f"{mobile_planned['width_px']} px preview; required at least "
                        f"{mobile_planned['minimum_primary_label_height_px']:.1f} px")
            except ValueError as exc:
                errors.append(str(exc))
            mobile_flow = mobile_observed.get("observed_first_glance_path")
            if not isinstance(mobile_flow, list) or not mobile_flow:
                errors.append(
                    "mobile inspection requires a non-empty observed_first_glance_path")
            if not str(mobile_observed.get("observed_explain_back") or "").strip():
                errors.append(
                    "mobile inspection requires an independent observed_explain_back")
            if mobile_observed.get("explain_back_matches") is not True:
                errors.append(
                    "mobile inspection must confirm explain_back_matches")
            if mobile_observed.get("primary_labels_require_zoom") is not False:
                errors.append(
                    "mobile inspection failed: primary labels must be readable without zoom")
            if mobile_observed.get("supporting_labels_inflated_for_phone") is not False:
                errors.append(
                    "mobile inspection failed: supporting labels must remain at compact "
                    "publication scale rather than being inflated for the phone preview")

        annotation = inspection.get("annotation")
        if not isinstance(annotation, dict):
            errors.append(
                f"quality contract v{contract_version} inspection requires annotation")
            annotation = {}
        observed_panels = annotation.get("panel_labels")
        if observed_panels != annotation_plan["panel_labels"]:
            errors.append(
                "observed panel labels do not match the planned uppercase A–D sequence")
        observed_callouts = annotation.get("callouts")
        if not isinstance(observed_callouts, list):
            errors.append("annotation inspection requires callouts list")
            observed_callouts = []
        observed_by_text = {
            item.get("text"): item for item in observed_callouts
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        }
        for planned in annotation_plan["callouts"]:
            observed = observed_by_text.get(planned["text"])
            if observed is None:
                errors.append(
                    f"planned explanatory callout was not observed: {planned['text']}")
                continue
            if observed.get("target") != planned["target"]:
                errors.append(
                    f"callout points to the wrong target: {planned['text']}")
            if observed.get("background") != planned["background"]:
                errors.append(
                    f"callout backing does not match the plan: {planned['text']}")
            if observed.get("quiet_canvas_considered") is not True:
                errors.append(
                    f"callout placement did not consider quiet canvas first: {planned['text']}")
            if (
                planned["background"] == "opaque-white"
                and observed.get("opaque_backing_present") is not True
            ):
                errors.append(
                    f"busy-region callout lacks opaque white backing: {planned['text']}")
            if (
                planned["background"] == "opaque-white"
                and observed.get("backing_necessary") is not True
            ):
                errors.append(
                    f"opaque callout backing was not justified as necessary: {planned['text']}")
            if (
                planned["background"] == "quiet-canvas"
                and observed.get("text_on_quiet_canvas") is not True
            ):
                errors.append(
                    f"unboxed callout is not on quiet canvas: {planned['text']}")
            if planned["leader_line"] and observed.get("leader_line_present") is not True:
                errors.append(
                    f"required leader line is missing: {planned['text']}")
            if (
                planned["leader_line"]
                and observed.get("leader_origin_attached_to_label") is not True
            ):
                errors.append(
                    "leader line is visually detached from its label: "
                    f"{planned['text']}"
                )
            if (
                planned["leader_line"]
                and observed.get("leader_endpoint_hits_target") is not True
            ):
                errors.append(
                    "leader line does not terminate on every declared target: "
                    f"{planned['text']}"
                )

    integrity = inspection.get("integrity")
    if contract_version == 3:
        if not isinstance(integrity, dict):
            errors.append("quality contract v3 inspection requires integrity")
            integrity = {}
        required_true = {
            "title_matches_visual_question":
                "title must name the actual reader-facing subject or finding",
            "panels_form_one_explanation":
                "all panels must answer one visual question",
            "declared_entities_specific":
                "depicted entities must be specific enough to identify their role",
            "all_objects_declared":
                "every meaningful visual object must have a declared semantic role",
            "all_connectors_semantic":
                "every connector must have a declared source, target, and meaning",
            "related_content_grouped":
                "logically related content must share one visual unit",
            "panels_add_distinct_information":
                "every separate panel must add distinct information",
            "primary_entities_visually_dominant":
                "the primary message entities must dominate area, contrast, and first fixation",
            "nonessential_elements_absent":
                "props, scenery, and repeated motifs that fail the deletion test must be absent",
            "aspect_ratio_suits_content":
                "the canvas ratio must fit the information density and topology",
            "composition_optically_balanced":
                "the complete composition must be optically centred and balanced",
            "callout_backings_legible":
                "callout text must use quiet canvas or opaque white backing over busy pixels",
            "font_system_consistent":
                "all typographic roles must use one consistent house sans-serif system",
            "absolute_white_canvas":
                "the visible paper must be exact #FFFFFF with no page tint or texture",
            "visual_language_consistent":
                "all elements must share one abstraction, dimensionality, line treatment, lighting, and material finish",
            "stock_asset_assemblage_absent":
                "the figure must not read as a collage of glossy stock symbols, emoji-like objects, app pictograms, or decorative badges",
            "representation_serves_evidence":
                "the chosen representation must shorten the path from pixels to evidence",
            "visual_explanation_survives_without_labels":
                "the domain-native visual structure must still communicate the subject and relationship when labels are mentally hidden",
            "text_subordinate_to_visuals":
                "labels must remain subordinate to evidence-bearing visuals in area and salience",
            "poster_layout_absent":
                "the figure must not use a headline-plus-icons or presentation-poster composition",
            "object_inventory_absent":
                "the figure must not substitute an isolated object inventory for a visual explanation",
        }
        for field, message in required_true.items():
            if integrity.get(field) is not True:
                errors.append(f"integrity inspection failed: {message}")
        if integrity.get("avoidable_cognitive_translation_added") is not False:
            errors.append(
                "integrity inspection failed: the representation adds an avoidable "
                "cognitive translation step")
        arranged_present = integrity.get("arranged_object_lineup_present")
        if not isinstance(arranged_present, bool):
            errors.append(
                "integrity inspection requires arranged_object_lineup_present boolean")
        elif arranged_present:
            if not semantic_plan["representation_plan"]["arranged_elements"]:
                errors.append(
                    "an unplanned arranged-object lineup appeared in the rendered figure")
            if integrity.get("arrangement_encodes_evidence") is not True:
                errors.append(
                    "arranged-object composition does not perform a declared evidence job")

        issue_lists = {
            "anatomy_errors": "anatomical integrity error",
            "unexplained_objects": "unexplained visual object",
            "ambiguous_connectors": "ambiguous connector",
            "salience_failures": "must-show salience failure",
            "redundant_sections": "redundant visual section",
            "typography_issues": "typography issue",
            "entity_specificity_issues": "entity-specificity issue",
            "visual_clutter": "nonessential visual clutter",
            "anatomical_context_losses": "insufficient anatomical context",
            "identity_drift": "cross-view identity drift",
            "uncertainty_ambiguities": "ambiguous uncertainty encoding",
            "quantitative_annotation_issues": "detached quantitative annotation",
            "layout_balance_issues": "content-fit or optical-balance issue",
            "callout_backing_issues": "callout backing issue",
            "font_consistency_issues": "font-system inconsistency",
            "composite_integration_issues": "composite integration issue",
            "paper_integrity_issues": "paper-integrity issue",
            "visual_language_issues": "visual-language coherence issue",
            "stock_asset_issues": "stock-asset assemblage issue",
            "representation_issues": "representation-economy issue",
            "typography_dominance_issues": "typography-dominance issue",
            "visual_explanation_issues": "visual-explanation issue",
        }
        if semantic_plan["cutaway_plan"]:
            issue_lists["cutaway_integrity_issues"] = "cutaway-integrity issue"
        for field, label in issue_lists.items():
            values = integrity.get(field)
            if not isinstance(values, list):
                errors.append(f"integrity inspection requires {field} list")
                values = []
            for value in values:
                errors.append(f"{label}: {value}")

        if semantic_plan["anatomy_subjects"]:
            if integrity.get("anatomy_checked_at_original_size") is not True:
                errors.append(
                    "every depicted person or animal must be checked at original size "
                    "for extra, missing, fused, duplicated, or impossible body parts")
            if integrity.get("anatomical_context_sufficient") is not True:
                errors.append(
                    "anatomical context must retain enough orientation landmarks to locate "
                    "the focal region and understand any instrument or mechanism")
        if semantic_plan["cutaway_plan"]:
            cutaway_required_true = {
                "cutaway_exterior_recognizable":
                    "the cutaway exterior must remain recognizable without labels",
                "cut_plane_coherent":
                    "the cutaway must use one coherent plane, perspective, and scale",
                "interior_spatial_relationships_truthful":
                    "the exposed interior relationships must match the declared spatial plan",
                "cutaway_annotations_complete":
                    "every essential interior entity must have one precise explanatory callout",
            }
            for field, message in cutaway_required_true.items():
                if integrity.get(field) is not True:
                    errors.append(f"integrity inspection failed: {message}")
        if semantic_plan["uncertainty_encodings"]:
            if integrity.get("uncertainty_encodings_explanatory") is not True:
                errors.append(
                    "uncertainty encoding must identify the exact uncertain claim or quantity "
                    "and explain how it changes interpretation")
        observed_identity = integrity.get("cross_view_identity_preserved")
        if not isinstance(observed_identity, list):
            errors.append(
                "integrity inspection requires cross_view_identity_preserved list")
            observed_identity = []
        observed_identity = {
            item.get("entity") for item in observed_identity
            if isinstance(item, dict) and item.get("preserved") is True
        }
        for item in semantic_plan["cross_view_identity"]:
            if item["entity"] not in observed_identity:
                errors.append(
                    "cross-view identity was not confirmed for entity: %s"
                    % item["entity"])
        salience_visible = integrity.get("salience_targets_visible")
        if not isinstance(salience_visible, list):
            errors.append("integrity inspection requires salience_targets_visible list")
            salience_visible = []
        for entity_id in semantic_plan["salience_targets"]:
            if entity_id not in salience_visible:
                errors.append(
                    f"integrity inspection did not confirm salience target: {entity_id}")

        if spec.get("render_route") in {"deterministic", "composite"}:
            quantitative = inspection.get("quantitative")
            if not isinstance(quantitative, dict):
                errors.append(
                    "quality contract v3 deterministic figures require quantitative inspection")
                quantitative = {}
            quantitative_checks = {
                "axis_semantics_visible":
                    "each plotted dimension must visibly name its construct and unit or category",
                "numeric_annotations_attached_to_referents":
                    "every numeric annotation must visibly attach to its estimate, endpoint, or contrast",
                "uncertainty_attached_to_estimate":
                    "every reported interval must be visually attached to the estimate it qualifies",
                "uncertainty_graphically_visible":
                    "a stated interval must appear as an attached whisker, band, bracket, or equivalent extent rather than text alone",
                "data_marks_visually_primary":
                    "data marks must remain visually primary instead of being overwhelmed by annotations",
                "annotations_clear_of_marks":
                    "direct labels must keep a clear gap from data marks, trajectories, axes, and one another",
                "y_axis_label_vertical":
                    "the y-axis label must be vertical and outside the data region",
                "redundant_legend_absent":
                    "conventional point-and-interval marks must not have a redundant legend",
                "full_composition_balanced":
                    "the full plot, including external labels and annotations, must be balanced",
            }
            for field, message in quantitative_checks.items():
                if quantitative.get(field) is not True:
                    errors.append("quantitative inspection failed: " + message)

        if spec.get("render_route") == "composite":
            if integrity.get("composite_components_integrated") is not True:
                errors.append(
                    "integrity inspection failed: composite components must form one balanced explanation")
            composite = inspection.get("composite")
            if not isinstance(composite, dict):
                errors.append(
                    "quality contract v3 composite figures require composite inspection")
                composite = {}
            composite_checks = {
                "generated_assets_text_free":
                    "generated composite assets must contain no text",
                "generated_assets_orientation_only":
                    "generated composite assets must not encode magnitude",
                "quantitative_layer_deterministic":
                    "all values, axes, intervals, and typography must be deterministic",
                "intrinsic_aspect_ratios_preserved":
                    "generated assets must preserve their intrinsic aspect ratios",
            }
            for field, message in composite_checks.items():
                if composite.get(field) is not True:
                    errors.append("composite inspection failed: " + message)

    errors.extend(validate_provenance(spec, path, provenance))

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
            "outer_frame_exact_white_share": round(outer_frame_white_share, 6),
            "alpha_minimum": alpha_minimum,
            "ocr_characters": len(ocr_text),
            "expected_text_items": len(expected_text),
            "missing_text_items": len(missing_text),
            "relationships_expected": len(expected_set),
            "relationships_observed": len(observed_set),
            "minimum_label_height_px": measured_height,
            "minimum_effective_label_pt": (
                round(effective_points, 2) if effective_points is not None else None
            ),
            "minimum_mobile_primary_label_px": (
                round(mobile_primary_label_height, 2)
                if mobile_primary_label_height is not None else None
            ),
            "robust_upper_label_height_px": effective_p90_text_height,
            "ocr_text_box_area_fraction": effective_text_area_fraction,
            "missing_abbreviation_expansions": missing_expansions,
            "geometry_distortions": len(geometry_distortions),
            "duplicate_text_items": len(duplicate_text),
            "unlisted_text_items": len(unlisted_text),
            "visual_quality": visual_quality,
            "typography_scale": typography_scale,
            "communication": communication,
            "mobile_preview": inspection.get("mobile_preview"),
            "annotation": inspection.get("annotation"),
            "integrity": integrity,
            "quantitative": inspection.get("quantitative"),
            "composite": inspection.get("composite"),
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
    parser.add_argument(
        "--report",
        help="optional path for an atomically written JSON QA report",
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
    if args.report:
        atomic_write_json(args.report, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
