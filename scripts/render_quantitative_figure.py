#!/usr/bin/env python3
"""Render exact quantitative fork, slope, and trajectory figures from JSON.

The renderer is deliberately topic-neutral. Scientific content, labels, axes,
colours, and annotations come from the figure specification; this module owns
only reusable plotting grammar and publication-safe geometry. Every render
emits a geometry manifest so an independent checker can recompute the mapping
from data values to final-image pixels.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_bytes, sha256_file
from figure_typography import (
    FigureTypographyError,
    load_font_face,
    resolve_font_path,
)
from grounded_metadata import PAGE_CONTENT_WIDTH_MM, rendered_figure_size_mm


ROOT = Path(__file__).resolve().parents[1]
WRITING_STYLES = ROOT / "references" / "figure-writing-style-overlays.json"
RENDERER_ID = "grounded.quantitative-trajectory.v1"
GEOMETRY_SCHEMA_VERSION = 1
HEX_COLOUR = re.compile(r"#[0-9A-Fa-f]{6}")
LABEL_POSITIONS = {"above", "below", "left", "right"}
CLEAN_SANS_FAMILIES = {"Arial", "Helvetica", "Helvetica Neue", "Inter", "Seravek"}
DEFAULT_RENDER = {
    "width_px": 1800,
    "outer_margin_px": 72,
    "panel_gap_px": 72,
    "columns": 2,
    "supersample": 2,
    "plot_insets_px": {"left": 140, "right": 74, "top": 92, "bottom": 104},
}


class QuantitativeFigureError(ValueError):
    """Raised when deterministic quantitative artwork would be ambiguous."""


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QuantitativeFigureError(f"{path} must contain a JSON object")
    return value


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QuantitativeFigureError(f"{field} must be an object")
    return value


def _list(value: Any, field: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "a non-empty list" if nonempty else "a list"
        raise QuantitativeFigureError(f"{field} must be {qualifier}")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuantitativeFigureError(f"{field} must be a non-empty string")
    return value.strip()


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise QuantitativeFigureError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise QuantitativeFigureError(f"{field} must be finite")
    return result


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise QuantitativeFigureError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise QuantitativeFigureError(
            f"{field} must be between {minimum} and {maximum}")
    return value


def _colour(value: Any, field: str) -> str:
    if not isinstance(value, str) or not HEX_COLOUR.fullmatch(value):
        raise QuantitativeFigureError(f"{field} must be a six-digit hex colour")
    return value.upper()


def _domain(axis: dict[str, Any], field: str) -> tuple[float, float]:
    raw = _list(axis.get("domain"), f"{field}.domain", nonempty=True)
    if len(raw) != 2:
        raise QuantitativeFigureError(f"{field}.domain must contain [minimum, maximum]")
    lower = _number(raw[0], f"{field}.domain[0]")
    upper = _number(raw[1], f"{field}.domain[1]")
    if not lower < upper:
        raise QuantitativeFigureError(f"{field}.domain minimum must be below maximum")
    return lower, upper


def _inside(value: float, domain: tuple[float, float], field: str) -> float:
    if not domain[0] <= value <= domain[1]:
        raise QuantitativeFigureError(
            f"{field}={value:g} lies outside [{domain[0]:g}, {domain[1]:g}]")
    return value


def _ticks(axis: dict[str, Any], domain: tuple[float, float], field: str):
    ticks = _list(axis.get("ticks"), f"{field}.ticks", nonempty=True)
    normalized = []
    seen: set[float] = set()
    for index, raw in enumerate(ticks):
        tick = _object(raw, f"{field}.ticks[{index}]")
        value = _inside(
            _number(tick.get("value"), f"{field}.ticks[{index}].value"),
            domain, f"{field}.ticks[{index}].value")
        if value in seen:
            raise QuantitativeFigureError(f"{field}.ticks values must be unique")
        seen.add(value)
        normalized.append({
            "value": value,
            "label": _string(tick.get("label"), f"{field}.ticks[{index}].label"),
        })
    return normalized


def _map_x(value: float, domain: tuple[float, float], box: dict[str, float]) -> float:
    return box["left"] + ((value - domain[0]) / (domain[1] - domain[0])) * (
        box["right"] - box["left"])


def _map_y(value: float, domain: tuple[float, float], box: dict[str, float]) -> float:
    return box["bottom"] - ((value - domain[0]) / (domain[1] - domain[0])) * (
        box["bottom"] - box["top"])


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _render_config(spec: dict[str, Any], panel_count: int) -> dict[str, Any]:
    plot_design = _object(spec.get("plot_design"), "plot_design")
    supplied = plot_design.get("render", {})
    if supplied is None:
        supplied = {}
    supplied = _object(supplied, "plot_design.render")
    target_ratio = _number(spec.get("target_aspect_ratio"), "target_aspect_ratio")
    if not 1.0 <= target_ratio <= 4.0:
        raise QuantitativeFigureError("target_aspect_ratio must be between 1 and 4")
    width = _integer(
        supplied.get("width_px", DEFAULT_RENDER["width_px"]),
        "plot_design.render.width_px", 1000, 4096)
    expected_height = round(width / target_ratio)
    height = _integer(
        supplied.get("height_px", expected_height),
        "plot_design.render.height_px", 500, 4096)
    if abs(width / height / target_ratio - 1.0) > 0.005:
        raise QuantitativeFigureError(
            "plot_design.render dimensions must preserve target_aspect_ratio")
    margin = _integer(
        supplied.get("outer_margin_px", DEFAULT_RENDER["outer_margin_px"]),
        "plot_design.render.outer_margin_px", 30, 240)
    gap = _integer(
        supplied.get("panel_gap_px", DEFAULT_RENDER["panel_gap_px"]),
        "plot_design.render.panel_gap_px", 20, 240)
    default_columns = min(panel_count, DEFAULT_RENDER["columns"])
    columns = _integer(
        supplied.get("columns", default_columns),
        "plot_design.render.columns", 1, min(4, panel_count))
    supersample = _integer(
        supplied.get("supersample", DEFAULT_RENDER["supersample"]),
        "plot_design.render.supersample", 1, 4)
    raw_insets = supplied.get("plot_insets_px", DEFAULT_RENDER["plot_insets_px"])
    raw_insets = _object(raw_insets, "plot_design.render.plot_insets_px")
    insets = {
        side: _integer(
            raw_insets.get(side, DEFAULT_RENDER["plot_insets_px"][side]),
            f"plot_design.render.plot_insets_px.{side}", 30, 240)
        for side in ("left", "right", "top", "bottom")
    }
    background_override = supplied.get("background_color")
    ink_override = supplied.get("ink_color")
    reference_override = supplied.get("reference_color")
    return {
        "width_px": width,
        "height_px": height,
        "outer_margin_px": margin,
        "panel_gap_px": gap,
        "columns": columns,
        "rows": math.ceil(panel_count / columns),
        "supersample": supersample,
        "plot_insets_px": insets,
        "background_color": (
            _colour(background_override, "plot_design.render.background_color")
            if background_override is not None else None),
        "ink_color": (
            _colour(ink_override, "plot_design.render.ink_color")
            if ink_override is not None else None),
        "reference_color": (
            _colour(reference_override, "plot_design.render.reference_color")
            if reference_override is not None else "#B7B7B1"),
    }


def _layout(config: dict[str, Any], panel_count: int) -> list[dict[str, Any]]:
    width = config["width_px"]
    height = config["height_px"]
    margin = config["outer_margin_px"]
    gap = config["panel_gap_px"]
    columns = config["columns"]
    rows = config["rows"]
    insets = config["plot_insets_px"]
    cell_width = (width - 2 * margin - (columns - 1) * gap) / columns
    cell_height = (height - 2 * margin - (rows - 1) * gap) / rows
    layouts = []
    for index in range(panel_count):
        row, column = divmod(index, columns)
        left = margin + column * (cell_width + gap)
        top = margin + row * (cell_height + gap)
        cell = {
            "left": left,
            "top": top,
            "right": left + cell_width,
            "bottom": top + cell_height,
        }
        plot = {
            "left": cell["left"] + insets["left"],
            "top": cell["top"] + insets["top"],
            "right": cell["right"] - insets["right"],
            "bottom": cell["bottom"] - insets["bottom"],
        }
        if plot["right"] - plot["left"] < 260 or plot["bottom"] - plot["top"] < 210:
            raise QuantitativeFigureError(
                "plot_design.render leaves a plot area too small for publication labels")
        layouts.append({
            "cell_box_px": {key: _rounded(value) for key, value in cell.items()},
            "plot_box_px": {key: _rounded(value) for key, value in plot.items()},
        })
    return layouts


def _style(spec: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    overlays = _load_json(WRITING_STYLES)
    review_style = spec.get("review_style", "scientific")
    if review_style not in overlays:
        raise QuantitativeFigureError(f"unknown review_style: {review_style}")
    overlay = _object(overlays[review_style], f"writing style {review_style}")
    font = _object(overlay.get("font"), f"writing style {review_style}.font")
    family = _string(font.get("family"), "font.family")
    fallback = _string(font.get("fallback"), "font.fallback")
    if spec.get("quality_contract_version") == 3:
        typography = _object(
            _object(spec.get("plot_design"), "plot_design").get("typography"),
            "plot_design.typography")
        family = _string(typography.get("family"), "plot_design.typography.family")
        fallback = _string(
            typography.get("fallback"), "plot_design.typography.fallback")
        if family not in CLEAN_SANS_FAMILIES or fallback not in CLEAN_SANS_FAMILIES:
            raise QuantitativeFigureError(
                "quality contract v3 requires clean sans-serif plot typography")
        if typography.get("upright_natural_width") is not True:
            raise QuantitativeFigureError(
                "plot_design.typography must set upright_natural_width=true")
    ink = config["ink_color"] or _colour(
        font.get("text_color", "#1A1A1A"), "font.text_color")
    background = config["background_color"]
    if background is None:
        description = str((_object(
            overlay.get("canvas", {}), "writing style canvas").get("background") or ""))
        match = HEX_COLOUR.search(description)
        background = match.group(0).upper() if match else "#FFFFFF"
    return {
        "review_style": review_style,
        "font_family": family,
        "font_fallback": fallback,
        "ink_color": ink,
        "background_color": background,
        "reference_color": config["reference_color"],
    }


def _font_set(style: dict[str, Any], width: int, height: int, supersample: int):
    # Keep physical type size stable across raster widths. The smallest role is
    # 30 px at 1,536 px. Its measured glyph box retains margin above the
    # journal's 6.5 pt final-width floor instead of merely sizing the font face
    # to the threshold or relying on a permissive manual transcript.
    rendered_width_mm, _rendered_height_mm = rendered_figure_size_mm(width, height)
    # A compact/tall raster is narrowed by the journal's figure-height cap.
    # Compensate before drawing so the smallest actual glyph—not merely the
    # nominal font face—retains the 6.5 pt publication floor. The 0.92 factor
    # preserves the established wide-figure sizes while adding the measured
    # safety margin needed once the rendered width falls below full content.
    height_cap_scale = max(
        1.0, 0.92 * PAGE_CONTENT_WIDTH_MM / rendered_width_mm)
    scale = (width / 1536) * height_cap_scale
    sizes = {
        "panel_label": max(25, round(36 * scale)),
        "panel_title": max(24, round(34 * scale)),
        "axis": max(21, round(31 * scale)),
        "tick": max(20, round(30 * scale)),
        "series": max(21, round(31 * scale)),
        "value": max(23, round(34 * scale)),
        "note": max(20, round(30 * scale)),
    }
    try:
        regular_path = resolve_font_path(style["font_family"], False)
        bold_path = resolve_font_path(style["font_family"], True)
        fonts = {}
        records = []
        for name, size in sizes.items():
            bold = name in {"panel_label", "panel_title", "value"}
            path = bold_path if bold else regular_path
            face, face_index, face_style = load_font_face(
                path, size * supersample, bold)
            fonts[name] = face
            records.append({
                "role": name,
                "requested_family": style["font_family"],
                "loaded_family": face.getname()[0],
                "path": str(path),
                "face_index": face_index,
                "face_style": face_style,
                "size_px": size,
                "target_pdf_width_mm": round(rendered_width_mm, 3),
            })
        return fonts, records
    except FigureTypographyError as exc:
        raise QuantitativeFigureError(str(exc)) from exc


def _panel_label(raw: Any, field: str) -> str | None:
    if raw is None:
        return None
    label = _string(raw, field)
    if label not in {"A", "B", "C", "D"}:
        raise QuantitativeFigureError(f"{field} must be one of A, B, C, D")
    return label


def _normalize_panels(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if spec.get("quality_contract_version") not in {2, 3}:
        raise QuantitativeFigureError("renderer requires quality_contract_version=2 or 3")
    if spec.get("archetype") != "quantitative":
        raise QuantitativeFigureError("renderer requires archetype=quantitative")
    if spec.get("render_route") not in {"deterministic", "composite"}:
        raise QuantitativeFigureError(
            "renderer requires render_route=deterministic or composite")
    render_context = spec.get("render_context", "article")
    if render_context not in {"article", "slide"}:
        raise QuantitativeFigureError(
            "quantitative renderer supports article and slide contexts; "
            "standalone title framing is not implemented")
    if render_context == "slide" and abs(
            float(spec.get("target_aspect_ratio", 0)) - (16 / 9)) > 0.01:
        raise QuantitativeFigureError("slide quantitative figures must use 16:9")
    data = _object(spec.get("data"), "data")
    raw_panels = _list(data.get("panels"), "data.panels", nonempty=True)
    if len(raw_panels) > 4:
        raise QuantitativeFigureError("data.panels supports at most four panels")
    panels = []
    panel_ids: set[str] = set()
    labels: list[str] = []
    for panel_index, raw_panel in enumerate(raw_panels):
        field = f"data.panels[{panel_index}]"
        panel = _object(raw_panel, field)
        panel_id = _string(panel.get("id"), f"{field}.id")
        if panel_id in panel_ids:
            raise QuantitativeFigureError("data.panels ids must be unique")
        panel_ids.add(panel_id)
        panel_label = _panel_label(panel.get("panel_label"), f"{field}.panel_label")
        if panel_label:
            labels.append(panel_label)
        title = panel.get("title")
        if title is not None:
            title = _string(title, f"{field}.title")
        x_axis = _object(panel.get("x_axis"), f"{field}.x_axis")
        y_axis = _object(panel.get("y_axis"), f"{field}.y_axis")
        x_domain = _domain(x_axis, f"{field}.x_axis")
        y_domain = _domain(y_axis, f"{field}.y_axis")
        normalized = {
            "id": panel_id,
            "panel_label": panel_label,
            "title": title,
            "x_axis": {
                "label_orientation": "horizontal",
                "label_location": "below-data-region",
                "label": _string(x_axis.get("label"), f"{field}.x_axis.label"),
                "domain": x_domain,
                "ticks": _ticks(x_axis, x_domain, f"{field}.x_axis"),
            },
            "y_axis": {
                "label_orientation": "vertical",
                "label_location": "outside-data-region",
                "label": _string(y_axis.get("label"), f"{field}.y_axis.label"),
                "domain": y_domain,
                "ticks": _ticks(y_axis, y_domain, f"{field}.y_axis"),
            },
            "series": [],
            "reference_lines": [],
            "events": [],
            "contrasts": [],
            "interval_key": None,
        }
        raw_interval_key = panel.get("interval_key")
        if raw_interval_key is not None:
            key_field = f"{field}.interval_key"
            interval_key = _object(raw_interval_key, key_field)
            position = interval_key.get("position", "top-right")
            if position not in {"top-left", "top-right"}:
                raise QuantitativeFigureError(
                    f"{key_field}.position must be top-left or top-right")
            normalized["interval_key"] = {
                "label": _string(interval_key.get("label"), f"{key_field}.label"),
                "position": position,
                "x_offset_px": _integer(
                    interval_key.get("x_offset_px", 0),
                    f"{key_field}.x_offset_px", -160, 160),
                "y_offset_px": _integer(
                    interval_key.get("y_offset_px", 0),
                    f"{key_field}.y_offset_px", -80, 160),
            }
        series_ids: set[str] = set()
        point_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        raw_series = _list(panel.get("series"), f"{field}.series", nonempty=True)
        for series_index, raw_item in enumerate(raw_series):
            series_field = f"{field}.series[{series_index}]"
            item = _object(raw_item, series_field)
            series_id = _string(item.get("id"), f"{series_field}.id")
            if series_id in series_ids:
                raise QuantitativeFigureError(f"{field}.series ids must be unique")
            series_ids.add(series_id)
            colour = _colour(item.get("color"), f"{series_field}.color")
            label = item.get("label")
            if label is not None:
                label = _string(label, f"{series_field}.label")
            label_position = item.get("label_position", "right")
            if label_position not in LABEL_POSITIONS:
                raise QuantitativeFigureError(
                    f"{series_field}.label_position must be one of "
                    + ", ".join(sorted(LABEL_POSITIONS)))
            line_width = _integer(
                item.get("line_width_px", 7), f"{series_field}.line_width_px", 2, 18)
            marker_radius = _integer(
                item.get("marker_radius_px", 9),
                f"{series_field}.marker_radius_px", 4, 18)
            raw_points = _list(item.get("points"), f"{series_field}.points", nonempty=True)
            points = []
            point_ids: set[str] = set()
            for point_index, raw_point in enumerate(raw_points):
                point_field = f"{series_field}.points[{point_index}]"
                point = _object(raw_point, point_field)
                point_id = _string(point.get("id"), f"{point_field}.id")
                if point_id in point_ids:
                    raise QuantitativeFigureError(
                        f"{series_field}.points ids must be unique")
                point_ids.add(point_id)
                x_value = _inside(
                    _number(point.get("x"), f"{point_field}.x"),
                    x_domain, f"{point_field}.x")
                y_value = _inside(
                    _number(point.get("y"), f"{point_field}.y"),
                    y_domain, f"{point_field}.y")
                point_label = point.get("label")
                if point_label is not None:
                    point_label = _string(point_label, f"{point_field}.label")
                point_label_position = point.get("label_position", "above")
                if point_label_position not in LABEL_POSITIONS:
                    raise QuantitativeFigureError(
                        f"{point_field}.label_position must be one of "
                        + ", ".join(sorted(LABEL_POSITIONS)))
                interval = point.get("y_interval")
                normalized_interval = None
                if interval is not None:
                    interval = _list(interval, f"{point_field}.y_interval", nonempty=True)
                    if len(interval) != 2:
                        raise QuantitativeFigureError(
                            f"{point_field}.y_interval must contain [low, high]")
                    low = _inside(_number(interval[0], f"{point_field}.y_interval[0]"),
                                  y_domain, f"{point_field}.y_interval[0]")
                    high = _inside(_number(interval[1], f"{point_field}.y_interval[1]"),
                                   y_domain, f"{point_field}.y_interval[1]")
                    if not low <= y_value <= high:
                        raise QuantitativeFigureError(
                            f"{point_field}.y_interval must contain the point estimate")
                    normalized_interval = [low, high]
                normalized_point = {
                    "id": point_id,
                    "x": x_value,
                    "y": y_value,
                    "label": point_label,
                    "label_position": point_label_position,
                    "y_interval": normalized_interval,
                }
                points.append(normalized_point)
                point_lookup[(series_id, point_id)] = normalized_point
            if any(points[index]["x"] > points[index + 1]["x"]
                   for index in range(len(points) - 1)):
                raise QuantitativeFigureError(
                    f"{series_field}.points must be ordered by nondecreasing x")
            label_point_id = item.get("label_point_id", points[-1]["id"])
            if label is not None and label_point_id not in point_ids:
                raise QuantitativeFigureError(
                    f"{series_field}.label_point_id must identify a series point")
            normalized["series"].append({
                "id": series_id,
                "label": label,
                "label_position": label_position,
                "label_point_id": label_point_id,
                "color": colour,
                "line_width_px": line_width,
                "marker_radius_px": marker_radius,
                "points": points,
            })

        reference_ids: set[str] = set()
        for ref_index, raw_ref in enumerate(panel.get("reference_lines", [])):
            ref_field = f"{field}.reference_lines[{ref_index}]"
            ref = _object(raw_ref, ref_field)
            axis = ref.get("axis")
            if axis not in {"x", "y"}:
                raise QuantitativeFigureError(f"{ref_field}.axis must be x or y")
            domain = x_domain if axis == "x" else y_domain
            ref_id = _string(ref.get("id"), f"{ref_field}.id")
            if ref_id in reference_ids:
                raise QuantitativeFigureError(
                    f"{field}.reference_lines ids must be unique")
            reference_ids.add(ref_id)
            normalized["reference_lines"].append({
                "id": ref_id,
                "axis": axis,
                "value": _inside(_number(ref.get("value"), f"{ref_field}.value"),
                                  domain, f"{ref_field}.value"),
                "label": (_string(ref.get("label"), f"{ref_field}.label")
                          if ref.get("label") is not None else None),
            })
        event_ids: set[str] = set()
        for event_index, raw_event in enumerate(panel.get("events", [])):
            event_field = f"{field}.events[{event_index}]"
            event = _object(raw_event, event_field)
            event_id = _string(event.get("id"), f"{event_field}.id")
            if event_id in event_ids:
                raise QuantitativeFigureError(f"{field}.events ids must be unique")
            event_ids.add(event_id)
            normalized["events"].append({
                "id": event_id,
                "x": _inside(_number(event.get("x"), f"{event_field}.x"),
                             x_domain, f"{event_field}.x"),
                "label": _string(event.get("label"), f"{event_field}.label"),
            })
        contrast_ids: set[str] = set()
        for contrast_index, raw_contrast in enumerate(panel.get("contrasts", [])):
            contrast_field = f"{field}.contrasts[{contrast_index}]"
            contrast = _object(raw_contrast, contrast_field)
            contrast_id = _string(contrast.get("id"), f"{contrast_field}.id")
            if contrast_id in contrast_ids:
                raise QuantitativeFigureError(f"{field}.contrasts ids must be unique")
            contrast_ids.add(contrast_id)
            from_ref = _object(contrast.get("from"), f"{contrast_field}.from")
            to_ref = _object(contrast.get("to"), f"{contrast_field}.to")
            from_key = (
                _string(from_ref.get("series_id"), f"{contrast_field}.from.series_id"),
                _string(from_ref.get("point_id"), f"{contrast_field}.from.point_id"),
            )
            to_key = (
                _string(to_ref.get("series_id"), f"{contrast_field}.to.series_id"),
                _string(to_ref.get("point_id"), f"{contrast_field}.to.point_id"),
            )
            if from_key not in point_lookup or to_key not in point_lookup:
                raise QuantitativeFigureError(
                    f"{contrast_field} must reference two existing points")
            estimate = _number(contrast.get("estimate"), f"{contrast_field}.estimate")
            observed_difference = point_lookup[from_key]["y"] - point_lookup[to_key]["y"]
            decimal_places = _integer(
                contrast.get("decimal_places", 1),
                f"{contrast_field}.decimal_places", 0, 8)
            tolerance = 0.5 * (10 ** (-decimal_places)) + 1e-9
            if abs(estimate - observed_difference) > tolerance:
                raise QuantitativeFigureError(
                    f"{contrast_field}.estimate must equal from.y minus to.y")
            interval = _list(
                contrast.get("interval"), f"{contrast_field}.interval", nonempty=True)
            if len(interval) != 2:
                raise QuantitativeFigureError(
                    f"{contrast_field}.interval must contain [low, high]")
            low = _number(interval[0], f"{contrast_field}.interval[0]")
            high = _number(interval[1], f"{contrast_field}.interval[1]")
            if not low <= estimate <= high:
                raise QuantitativeFigureError(
                    f"{contrast_field}.interval must contain the estimate")
            position = contrast.get("label_position", "right")
            if position not in {"left", "right"}:
                raise QuantitativeFigureError(
                    f"{contrast_field}.label_position must be left or right")
            offset = _integer(
                contrast.get("x_offset_px", 0), f"{contrast_field}.x_offset_px", -160, 160)
            normalized["contrasts"].append({
                "id": contrast_id,
                "from": {"series_id": from_key[0], "point_id": from_key[1]},
                "to": {"series_id": to_key[0], "point_id": to_key[1]},
                "x": _inside(_number(contrast.get("x"), f"{contrast_field}.x"),
                             x_domain, f"{contrast_field}.x"),
                "x_offset_px": offset,
                "estimate": estimate,
                "interval": [low, high],
                "decimal_places": decimal_places,
                "label": _string(contrast.get("label"), f"{contrast_field}.label"),
                "label_position": position,
            })
        panels.append(normalized)
    if len(panels) > 1:
        expected = list("ABCD"[:len(panels)])
        if labels != expected:
            raise QuantitativeFigureError(
                "multi-panel deterministic figures require sequential panel_label A, B, C, D")
    return panels


def _draw_dashed(draw, coordinates, fill, width, dash, supersample):
    x1, y1, x2, y2 = coordinates
    length = math.hypot(x2 - x1, y2 - y1)
    if not length:
        return
    unit_x, unit_y = (x2 - x1) / length, (y2 - y1) / length
    position = 0.0
    while position < length:
        end = min(length, position + dash)
        draw.line(
            (round((x1 + unit_x * position) * supersample),
             round((y1 + unit_y * position) * supersample),
             round((x1 + unit_x * end) * supersample),
             round((y1 + unit_y * end) * supersample)),
            fill=fill, width=max(1, width * supersample),
        )
        position += dash * 1.8


def _record_text_box(
    text_layout: list[dict[str, Any]] | None, panel_id: str | None,
    role: str | None, text: str, box, supersample: int,
) -> None:
    if text_layout is None:
        return
    text_layout.append({
        "panel_id": panel_id,
        "role": role or "text",
        "text": text,
        "bbox_px": {
            "left": _rounded(box[0] / supersample),
            "top": _rounded(box[1] / supersample),
            "right": _rounded(box[2] / supersample),
            "bottom": _rounded(box[3] / supersample),
        },
    })


def _draw_text(
    draw, position, text, font, fill, anchor, supersample, *,
    text_layout: list[dict[str, Any]] | None = None,
    panel_id: str | None = None, role: str | None = None,
):
    scaled_position = (
        round(position[0] * supersample), round(position[1] * supersample))
    draw.text(
        scaled_position, text, font=font, fill=fill, anchor=anchor)
    _record_text_box(
        text_layout, panel_id, role, text,
        draw.textbbox(scaled_position, text, font=font, anchor=anchor), supersample)


def _draw_vertical_text(
    canvas, position, text, font, fill, supersample, *,
    text_layout: list[dict[str, Any]] | None = None,
    panel_id: str | None = None, role: str | None = None,
    minimum_left_px: float | None = None,
):
    """Draw an upright sans-serif axis title rotated 90 degrees counter-clockwise."""
    from PIL import Image, ImageDraw

    probe = ImageDraw.Draw(canvas)
    bbox = probe.textbbox((0, 0), text, font=font, anchor="lt")
    padding = 4 * supersample
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    patch = Image.new(
        "RGBA", (width + 2 * padding, height + 2 * padding), (0, 0, 0, 0))
    patch_draw = ImageDraw.Draw(patch)
    patch_draw.text(
        (padding - bbox[0], padding - bbox[1]), text,
        font=font, fill=fill, anchor="lt")
    rotated = patch.rotate(90, expand=True)
    center_x = round(position[0] * supersample)
    center_y = round(position[1] * supersample)
    left = center_x - rotated.width // 2
    if minimum_left_px is not None:
        left = max(left, round(minimum_left_px * supersample))
    top = center_y - rotated.height // 2
    canvas.paste(rotated, (left, top), rotated)
    _record_text_box(
        text_layout, panel_id, role, text,
        (left, top, left + rotated.width, top + rotated.height), supersample)


def _label(
    draw, x, y, text, position, font, fill, supersample, offset=15,
    horizontal_bounds: dict[str, float] | None = None,
    vertical_bounds: dict[str, float] | None = None,
    text_layout: list[dict[str, Any]] | None = None,
    panel_id: str | None = None, role: str | None = None,
):
    if position == "above":
        coordinates, anchor = (x, y - offset), "mb"
    elif position == "below":
        coordinates, anchor = (x, y + offset), "ma"
    elif position == "left":
        coordinates, anchor = (x - offset, y), "rm"
    else:
        coordinates, anchor = (x + offset, y), "lm"
    if horizontal_bounds is not None and position in {"above", "below"}:
        scaled = (
            round(coordinates[0] * supersample),
            round(coordinates[1] * supersample),
        )
        box = draw.textbbox(scaled, text, font=font, anchor=anchor)
        if box[2] > horizontal_bounds["right"] * supersample:
            anchor = "rb" if position == "above" else "ra"
        elif box[0] < horizontal_bounds["left"] * supersample:
            anchor = "lb" if position == "above" else "la"
    if vertical_bounds is not None and position in {"above", "below"}:
        scaled = (
            round(coordinates[0] * supersample),
            round(coordinates[1] * supersample),
        )
        box = draw.textbbox(scaled, text, font=font, anchor=anchor)
        flip_offset = offset + (getattr(font, "size", 0) / supersample) * 0.75
        if position == "above" and box[1] < vertical_bounds["top"] * supersample:
            coordinates = (x, y + flip_offset)
            anchor = anchor[0] + "a"
        elif position == "below" and box[3] > vertical_bounds["bottom"] * supersample:
            coordinates = (x, y - flip_offset)
            anchor = anchor[0] + "b"
    _draw_text(
        draw, coordinates, text, font, fill, anchor, supersample,
        text_layout=text_layout, panel_id=panel_id, role=role)


def _wrap_annotation_lines(draw, text, font, max_width_px, supersample):
    """Wrap explanatory copy at word boundaries without changing its manifest text."""
    maximum = max_width_px * supersample
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        width = draw.textbbox((0, 0), candidate, font=font, anchor="lt")[2]
        if current and width > maximum:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if not lines or any(
        draw.textbbox((0, 0), line, font=font, anchor="lt")[2] > maximum
        for line in lines
    ):
        raise QuantitativeFigureError(
            "label has no readable word-boundary fit inside its panel")
    return lines


def _draw_contrast_label(
    draw, x, y, text, position, font, fill, background, supersample,
    horizontal_bounds: dict[str, float], max_width_px: float, offset=16,
    text_layout: list[dict[str, Any]] | None = None,
    panel_id: str | None = None,
):
    """Draw a paper-backed contrast label, wrapping it within one panel."""
    if position == "left":
        edge = x - offset
        available = edge - horizontal_bounds["left"]
    else:
        edge = x + offset
        available = horizontal_bounds["right"] - edge
    padding = 5
    if available <= 2 * padding:
        raise QuantitativeFigureError(
            "contrast label has no horizontal space inside its panel")
    usable_width = min(available - 2 * padding, max_width_px)
    lines = _wrap_annotation_lines(
        draw, text, font, usable_width, supersample)
    scaled_padding = padding * supersample
    line_spacing = 5 * supersample
    line_boxes = [
        draw.textbbox((0, 0), line, font=font, anchor="lt") for line in lines
    ]
    line_height = max(box[3] - box[1] for box in line_boxes)
    content_width = max(box[2] - box[0] for box in line_boxes)
    content_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
    center_y = round(y * supersample)
    top = center_y - content_height / 2
    if position == "left":
        right = round(edge * supersample)
        left = right - content_width
        alignment = "right"
    else:
        left = round(edge * supersample)
        right = left + content_width
        alignment = "left"
    for index, (line, box) in enumerate(zip(lines, line_boxes)):
        width = box[2] - box[0]
        line_x = right - width if alignment == "right" else left
        line_y = top + index * (line_height + line_spacing)
        draw.text(
            (round(line_x), round(line_y)), line, font=font, fill=fill, anchor="lt",
            stroke_width=max(1, round(scaled_padding * 0.4)), stroke_fill=background)
    _record_text_box(
        text_layout, panel_id, "contrast", text,
        (left, top, right, top + content_height), supersample)


def _draw_series_label(
    draw, x, y, text, position, font, fill, supersample,
    plot_bounds: dict[str, float], panel_bounds: dict[str, float], offset: float,
    text_layout: list[dict[str, Any]], panel_id: str,
) -> None:
    """Direct-label a series, wrapping only when an edge forces a side flip."""
    if position not in {"above", "below"}:
        _label(
            draw, x, y, text, position, font, fill, supersample,
            offset=offset, horizontal_bounds=plot_bounds,
            vertical_bounds=plot_bounds, text_layout=text_layout,
            panel_id=panel_id, role="series_label")
        return
    preferred_anchor = "mb" if position == "above" else "ma"
    preferred_coordinates = (x, y - offset) if position == "above" else (x, y + offset)
    scaled = (
        round(preferred_coordinates[0] * supersample),
        round(preferred_coordinates[1] * supersample),
    )
    preferred_box = draw.textbbox(
        scaled, text, font=font, anchor=preferred_anchor)
    if preferred_box[2] > plot_bounds["right"] * supersample:
        preferred_anchor = "rb" if position == "above" else "ra"
    elif preferred_box[0] < plot_bounds["left"] * supersample:
        preferred_anchor = "lb" if position == "above" else "la"
    preferred_box = draw.textbbox(
        scaled, text, font=font, anchor=preferred_anchor)
    horizontal_shift = 0.0
    if preferred_box[0] < panel_bounds["left"] * supersample:
        horizontal_shift = (
            panel_bounds["left"] * supersample - preferred_box[0]) / supersample
    elif preferred_box[2] > panel_bounds["right"] * supersample:
        horizontal_shift = (
            panel_bounds["right"] * supersample - preferred_box[2]) / supersample
    if horizontal_shift:
        preferred_coordinates = (
            preferred_coordinates[0] + horizontal_shift,
            preferred_coordinates[1],
        )
        scaled = (
            round(preferred_coordinates[0] * supersample),
            round(preferred_coordinates[1] * supersample),
        )
        preferred_box = draw.textbbox(
            scaled, text, font=font, anchor=preferred_anchor)
    forced_flip = (
        position == "above"
        and preferred_box[1] < plot_bounds["top"] * supersample
    ) or (
        position == "below"
        and preferred_box[3] > plot_bounds["bottom"] * supersample
    )
    if not forced_flip:
        _draw_text(
            draw, preferred_coordinates, text, font, fill, preferred_anchor,
            supersample, text_layout=text_layout, panel_id=panel_id,
            role="series_label")
        return

    midpoint = (plot_bounds["left"] + plot_bounds["right"]) / 2
    gutter_left = plot_bounds["right"] + 20
    gutter_width = panel_bounds["right"] - gutter_left - 4
    if x >= midpoint and gutter_width >= 140:
        lines = _wrap_annotation_lines(
            draw, text, font, gutter_width, supersample)
        line_spacing = 4 * supersample
        line_boxes = [
            draw.textbbox((0, 0), line, font=font, anchor="lt") for line in lines
        ]
        line_height = max(box[3] - box[1] for box in line_boxes)
        content_width = max(box[2] - box[0] for box in line_boxes)
        content_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
        proposed_top = (
            (y + offset) * supersample if position == "above"
            else (y - offset) * supersample - content_height
        )
        top = min(
            max(proposed_top, (plot_bounds["top"] + 8) * supersample),
            (plot_bounds["bottom"] - 8) * supersample - content_height,
        )
        left = gutter_left * supersample
        right = left + content_width
        leader_end = (
            (gutter_left - 5) * supersample,
            top + min(line_height, content_height) / 2,
        )
        draw.line(
            (round(x * supersample), round(y * supersample),
             round(leader_end[0]), round(leader_end[1])),
            fill=fill, width=2 * supersample)
        for index, line in enumerate(lines):
            line_y = top + index * (line_height + line_spacing)
            draw.text(
                (round(left), round(line_y)), line,
                font=font, fill=fill, anchor="lt")
        _record_text_box(
            text_layout, panel_id, "series_label", text,
            (left, top, right, top + content_height), supersample)
        return

    max_width = max(150, (plot_bounds["right"] - plot_bounds["left"]) * 0.62)
    lines = _wrap_annotation_lines(
        draw, text, font, max_width, supersample)
    line_spacing = 4 * supersample
    line_boxes = [
        draw.textbbox((0, 0), line, font=font, anchor="lt") for line in lines
    ]
    line_height = max(box[3] - box[1] for box in line_boxes)
    content_width = max(box[2] - box[0] for box in line_boxes)
    content_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
    if x >= midpoint:
        right = min(x, plot_bounds["right"]) * supersample
        left = right - content_width
        alignment = "right"
    else:
        left = max(x, plot_bounds["left"]) * supersample
        right = left + content_width
        alignment = "left"
    flip_offset = offset + (getattr(font, "size", 0) / supersample) * 0.75
    if position == "above":
        top = (y + flip_offset) * supersample
    else:
        top = (y - flip_offset) * supersample - content_height
    for index, (line, box) in enumerate(zip(lines, line_boxes)):
        width = box[2] - box[0]
        line_x = right - width if alignment == "right" else left
        line_y = top + index * (line_height + line_spacing)
        draw.text(
            (round(line_x), round(line_y)), line, font=font, fill=fill, anchor="lt")
    _record_text_box(
        text_layout, panel_id, "series_label", text,
        (left, top, right, top + content_height), supersample)


def _text_boxes_overlap(
    first: dict[str, float], second: dict[str, float], gap_px: float = 2.0,
) -> bool:
    half_gap = gap_px / 2
    return (
        min(first["right"] + half_gap, second["right"] + half_gap)
        - max(first["left"] - half_gap, second["left"] - half_gap) > 0
        and min(first["bottom"] + half_gap, second["bottom"] + half_gap)
        - max(first["top"] - half_gap, second["top"] - half_gap) > 0
    )


def _validate_text_layout(
    text_layout: list[dict[str, Any]], bounds_by_panel: dict[str, dict[str, float]],
) -> None:
    """Fail closed when deterministic copy clips or collides inside a panel."""
    by_panel: dict[str, list[dict[str, Any]]] = {}
    for record in text_layout:
        panel_id = record["panel_id"]
        if panel_id not in bounds_by_panel:
            raise QuantitativeFigureError(
                f"text layout references unknown panel {panel_id}")
        bounds = bounds_by_panel[panel_id]
        box = record["bbox_px"]
        if (
            box["left"] < bounds["left"] - 0.5
            or box["right"] > bounds["right"] + 0.5
            or box["top"] < bounds["top"] - 0.5
            or box["bottom"] > bounds["bottom"] + 0.5
        ):
            raise QuantitativeFigureError(
                f"{record['role']} text does not fit inside panel {panel_id}: "
                f"{record['text']!r}")
        by_panel.setdefault(panel_id, []).append(record)
    for panel_id, records in by_panel.items():
        for index, first in enumerate(records):
            for second in records[index + 1:]:
                if _text_boxes_overlap(first["bbox_px"], second["bbox_px"]):
                    raise QuantitativeFigureError(
                        f"text collision in panel {panel_id}: "
                        f"{first['text']!r} overlaps {second['text']!r}")


def _expected_pixel_text(spec: dict[str, Any]) -> list[str]:
    exact = spec.get("exact_text")
    if not isinstance(exact, list) or not exact or any(
        not isinstance(item, str) or not item.strip() for item in exact
    ):
        raise QuantitativeFigureError("exact_text must be a non-empty string list")
    expected = [item.strip() for item in exact]
    if spec.get("render_context", "article") in {"article", "slide"}:
        omitted = {
            str(spec.get("title") or "").strip(),
            str(spec.get("subtitle") or "").strip(),
        }
        expected = [item for item in expected if item not in omitted]
    return expected


def _validate_text_manifest(expected: list[str], rendered: list[str]) -> None:
    missing = sorted(set(expected) - set(rendered))
    extra = sorted(set(rendered) - set(expected))
    if missing or extra:
        detail = []
        if missing:
            detail.append("missing from plot: " + "; ".join(repr(item) for item in missing))
        if extra:
            detail.append("absent from exact_text: " + "; ".join(repr(item) for item in extra))
        raise QuantitativeFigureError(
            "deterministic rendered text must match exact_text: " + ", ".join(detail))


def render(
    spec: dict[str, Any], output_path: str | Path,
    geometry_path: str | Path,
) -> dict[str, Any]:
    """Render *spec* and atomically write PNG plus geometry manifest."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise QuantitativeFigureError(
            "Pillow is required for deterministic quantitative rendering") from exc
    panels = _normalize_panels(spec)
    config = _render_config(spec, len(panels))
    layouts = _layout(config, len(panels))
    style = _style(spec, config)
    fonts, font_records = _font_set(
        style, config["width_px"], config["height_px"], config["supersample"])
    supersample = config["supersample"]
    canvas = Image.new(
        "RGB",
        (config["width_px"] * supersample, config["height_px"] * supersample),
        style["background_color"],
    )
    draw = ImageDraw.Draw(canvas)
    rendered_text: list[str] = []
    text_layout: list[dict[str, Any]] = []
    manifest_panels = []
    for panel, layout in zip(panels, layouts):
        cell = layout["cell_box_px"]
        box = layout["plot_box_px"]
        x_domain = panel["x_axis"]["domain"]
        y_domain = panel["y_axis"]["domain"]
        header_x = cell["left"]
        header_y = cell["top"] + 3
        if panel["panel_label"]:
            _draw_text(
                draw, (header_x, header_y), panel["panel_label"],
                fonts["panel_label"], style["ink_color"], "la", supersample,
                text_layout=text_layout, panel_id=panel["id"], role="panel_label")
            rendered_text.append(panel["panel_label"])
            header_x += 42
        if panel["title"]:
            _draw_text(
                draw, (header_x, header_y), panel["title"],
                fonts["panel_title"], style["ink_color"], "la", supersample,
                text_layout=text_layout, panel_id=panel["id"], role="panel_title")
            rendered_text.append(panel["title"])

        axis_width = 2 * supersample
        draw.line(
            (round(box["left"] * supersample), round(box["top"] * supersample),
             round(box["left"] * supersample), round(box["bottom"] * supersample)),
            fill=style["ink_color"], width=axis_width)
        draw.line(
            (round(box["left"] * supersample), round(box["bottom"] * supersample),
             round(box["right"] * supersample), round(box["bottom"] * supersample)),
            fill=style["ink_color"], width=axis_width)
        _draw_vertical_text(
            canvas,
            (cell["left"] + 22, (box["top"] + box["bottom"]) / 2),
            panel["y_axis"]["label"], fonts["axis"], style["ink_color"],
            supersample, text_layout=text_layout, panel_id=panel["id"],
            role="y_axis_label", minimum_left_px=cell["left"] + 2)
        _draw_text(
            draw, ((box["left"] + box["right"]) / 2, box["bottom"] + 70),
            panel["x_axis"]["label"], fonts["axis"], style["ink_color"],
            "ma", supersample, text_layout=text_layout,
            panel_id=panel["id"], role="x_axis_label")
        rendered_text.extend([panel["y_axis"]["label"], panel["x_axis"]["label"]])
        x_ticks_manifest = []
        for tick in panel["x_axis"]["ticks"]:
            x = _map_x(tick["value"], x_domain, box)
            draw.line(
                (round(x * supersample), round(box["bottom"] * supersample),
                 round(x * supersample), round((box["bottom"] + 9) * supersample)),
                fill=style["ink_color"], width=axis_width)
            _draw_text(
                draw, (x, box["bottom"] + 20), tick["label"], fonts["tick"],
                style["ink_color"], "ma", supersample, text_layout=text_layout,
                panel_id=panel["id"], role="x_tick")
            rendered_text.append(tick["label"])
            x_ticks_manifest.append({
                "value": tick["value"], "label": tick["label"], "x_px": _rounded(x),
            })
        y_ticks_manifest = []
        for tick in panel["y_axis"]["ticks"]:
            y = _map_y(tick["value"], y_domain, box)
            draw.line(
                (round((box["left"] - 9) * supersample), round(y * supersample),
                 round(box["left"] * supersample), round(y * supersample)),
                fill=style["ink_color"], width=axis_width)
            _draw_text(
                draw, (box["left"] - 16, y), tick["label"], fonts["tick"],
                style["ink_color"], "rm", supersample, text_layout=text_layout,
                panel_id=panel["id"], role="y_tick")
            rendered_text.append(tick["label"])
            y_ticks_manifest.append({
                "value": tick["value"], "label": tick["label"], "y_px": _rounded(y),
            })

        interval_key_manifest = None
        if panel["interval_key"]:
            key = panel["interval_key"]
            y = box["top"] + 34 + key["y_offset_px"]
            if key["position"] == "top-left":
                x = box["left"] + 28 + key["x_offset_px"]
                label_x, label_anchor = x + 24, "lm"
            else:
                x = box["right"] - 28 + key["x_offset_px"]
                label_x, label_anchor = x - 24, "rm"
            half, cap = 18, 8
            key_colour = style["ink_color"]
            draw.line(
                (round(x * supersample), round((y - half) * supersample),
                 round(x * supersample), round((y + half) * supersample)),
                fill=key_colour, width=3 * supersample)
            for endpoint in (y - half, y + half):
                draw.line(
                    (round((x - cap) * supersample), round(endpoint * supersample),
                     round((x + cap) * supersample), round(endpoint * supersample)),
                    fill=key_colour, width=3 * supersample)
            radius = 5 * supersample
            center_x, center_y = round(x * supersample), round(y * supersample)
            draw.ellipse(
                (center_x - radius, center_y - radius,
                 center_x + radius, center_y + radius),
                fill=key_colour, outline=style["background_color"],
                width=max(1, supersample))
            _draw_text(
                draw, (label_x, y), key["label"], fonts["note"],
                key_colour, label_anchor, supersample,
                text_layout=text_layout, panel_id=panel["id"],
                role="interval_key")
            rendered_text.append(key["label"])
            interval_key_manifest = {
                "label": key["label"], "position": key["position"],
                "x_px": _rounded(x), "y_px": _rounded(y),
            }

        references_manifest = []
        for reference in panel["reference_lines"]:
            if reference["axis"] == "x":
                pixel = _map_x(reference["value"], x_domain, box)
                coordinates = (pixel, box["top"], pixel, box["bottom"])
            else:
                pixel = _map_y(reference["value"], y_domain, box)
                coordinates = (box["left"], pixel, box["right"], pixel)
            _draw_dashed(
                draw, coordinates, style["reference_color"], 2, 8, supersample)
            if reference["label"]:
                if reference["axis"] == "y":
                    _draw_text(
                        draw, (box["right"] - 4, pixel - 20), reference["label"],
                        fonts["note"], style["ink_color"], "rb", supersample,
                        text_layout=text_layout, panel_id=panel["id"],
                        role="reference_label")
                else:
                    _draw_text(
                        draw, (pixel + 8, box["top"] + 8), reference["label"],
                        fonts["note"], style["ink_color"], "la", supersample,
                        text_layout=text_layout, panel_id=panel["id"],
                        role="reference_label")
                rendered_text.append(reference["label"])
            references_manifest.append({
                "id": reference["id"], "axis": reference["axis"],
                "value": reference["value"], "pixel": _rounded(pixel),
            })

        events_manifest = []
        for event in panel["events"]:
            x = _map_x(event["x"], x_domain, box)
            _draw_dashed(
                draw, (x, box["top"], x, box["bottom"]),
                style["reference_color"], 2, 8, supersample)
            _draw_text(
                draw, (x + 8, box["top"] + 8), event["label"], fonts["note"],
                style["ink_color"], "la", supersample, text_layout=text_layout,
                panel_id=panel["id"], role="event_label")
            rendered_text.append(event["label"])
            events_manifest.append({
                "id": event["id"], "x_value": event["x"], "x_px": _rounded(x),
            })

        points_manifest = []
        intervals_manifest = []
        series_manifest = []
        point_pixels: dict[tuple[str, str], tuple[float, float]] = {}
        for series in panel["series"]:
            coordinates = [
                (_map_x(point["x"], x_domain, box),
                 _map_y(point["y"], y_domain, box))
                for point in series["points"]
            ]
            if len(coordinates) > 1:
                draw.line(
                    tuple(
                        round(component * supersample)
                        for coordinate in coordinates for component in coordinate
                    ),
                    fill=series["color"],
                    width=series["line_width_px"] * supersample,
                    joint="curve",
                )
            for point, (x, y) in zip(series["points"], coordinates):
                point_pixels[(series["id"], point["id"])] = (x, y)
                if point["y_interval"] is not None:
                    low_y = _map_y(point["y_interval"][0], y_domain, box)
                    high_y = _map_y(point["y_interval"][1], y_domain, box)
                    cap = 9
                    draw.line(
                        (round(x * supersample), round(low_y * supersample),
                         round(x * supersample), round(high_y * supersample)),
                        fill=series["color"], width=3 * supersample)
                    for endpoint in (low_y, high_y):
                        draw.line(
                            (round((x - cap) * supersample), round(endpoint * supersample),
                             round((x + cap) * supersample), round(endpoint * supersample)),
                            fill=series["color"], width=3 * supersample)
                    intervals_manifest.append({
                        "series_id": series["id"], "point_id": point["id"],
                        "low_value": point["y_interval"][0],
                        "high_value": point["y_interval"][1],
                        "x_px": _rounded(x), "low_y_px": _rounded(low_y),
                        "high_y_px": _rounded(high_y),
                    })
                radius = series["marker_radius_px"] * supersample
                center_x, center_y = round(x * supersample), round(y * supersample)
                draw.ellipse(
                    (center_x - radius, center_y - radius,
                     center_x + radius, center_y + radius),
                    fill=series["color"], outline=style["background_color"],
                    width=2 * supersample)
                if point["label"]:
                    _label(
                        draw, x, y, point["label"], point["label_position"],
                        fonts["value"], series["color"], supersample,
                        offset=series["marker_radius_px"] + 11,
                        horizontal_bounds=cell, vertical_bounds=box,
                        text_layout=text_layout, panel_id=panel["id"],
                        role="point_label")
                    rendered_text.append(point["label"])
                points_manifest.append({
                    "series_id": series["id"], "point_id": point["id"],
                    "x_value": point["x"], "y_value": point["y"],
                    "x_px": _rounded(x), "y_px": _rounded(y),
                    "color": series["color"],
                })
            if series["label"]:
                label_point = next(
                    point for point in series["points"]
                    if point["id"] == series["label_point_id"])
                x, y = point_pixels[(series["id"], label_point["id"])]
                _draw_series_label(
                    draw, x, y, series["label"], series["label_position"],
                    fonts["series"], series["color"], supersample,
                    box, cell, offset=series["marker_radius_px"] + 11,
                    text_layout=text_layout, panel_id=panel["id"])
                rendered_text.append(series["label"])
            series_manifest.append({
                "id": series["id"], "color": series["color"],
                "line_width_px": series["line_width_px"],
                "marker_radius_px": series["marker_radius_px"],
                "point_ids": [point["id"] for point in series["points"]],
            })

        contrasts_manifest = []
        for contrast in panel["contrasts"]:
            from_key = (contrast["from"]["series_id"], contrast["from"]["point_id"])
            to_key = (contrast["to"]["series_id"], contrast["to"]["point_id"])
            _from_x, from_y = point_pixels[from_key]
            _to_x, to_y = point_pixels[to_key]
            bracket_x = _map_x(contrast["x"], x_domain, box) + contrast["x_offset_px"]
            bracket_colour = style["ink_color"]
            cap = 10
            draw.line(
                (round(bracket_x * supersample), round(from_y * supersample),
                 round(bracket_x * supersample), round(to_y * supersample)),
                fill=bracket_colour, width=2 * supersample)
            for endpoint_y in (from_y, to_y):
                draw.line(
                    (round((bracket_x - cap) * supersample), round(endpoint_y * supersample),
                     round((bracket_x + cap) * supersample), round(endpoint_y * supersample)),
                    fill=bracket_colour, width=2 * supersample)
            middle_y = (from_y + to_y) / 2
            _draw_contrast_label(
                draw, bracket_x, middle_y, contrast["label"],
                contrast["label_position"], fonts["note"],
                style["ink_color"], style["background_color"], supersample,
                cell, max_width_px=max(160, (box["right"] - box["left"]) * 0.58),
                offset=16, text_layout=text_layout, panel_id=panel["id"])
            rendered_text.append(contrast["label"])
            contrasts_manifest.append({
                "id": contrast["id"], "from": contrast["from"], "to": contrast["to"],
                "x_value": contrast["x"], "x_offset_px": contrast["x_offset_px"],
                "bracket_x_px": _rounded(bracket_x),
                "from_y_px": _rounded(from_y), "to_y_px": _rounded(to_y),
                "estimate": contrast["estimate"], "interval": contrast["interval"],
            })

        manifest_panels.append({
            "id": panel["id"], "panel_label": panel["panel_label"],
            **layout,
            "x_axis": {
                "label_orientation": panel["x_axis"]["label_orientation"],
                "label_location": panel["x_axis"]["label_location"],
                "domain": list(x_domain),
                "pixel_range": [_rounded(box["left"]), _rounded(box["right"])],
                "ticks": x_ticks_manifest,
            },
            "y_axis": {
                "label_orientation": panel["y_axis"]["label_orientation"],
                "label_location": panel["y_axis"]["label_location"],
                "domain": list(y_domain),
                "pixel_range": [_rounded(box["bottom"]), _rounded(box["top"])],
                "ticks": y_ticks_manifest,
            },
            "series": series_manifest,
            "points": points_manifest,
            "intervals": intervals_manifest,
            "reference_lines": references_manifest,
            "events": events_manifest,
            "contrasts": contrasts_manifest,
            "interval_key": interval_key_manifest,
        })

    text_bounds_by_panel = {}
    for index, (panel, layout) in enumerate(zip(panels, layouts)):
        row = index // config["columns"]
        cell = layout["cell_box_px"]
        text_bounds_by_panel[panel["id"]] = {
            "left": cell["left"],
            "right": cell["right"],
            "top": (0 if row == 0 else cell["top"] - config["panel_gap_px"] / 2),
            "bottom": (
                config["height_px"] if row == config["rows"] - 1
                else cell["bottom"] + config["panel_gap_px"] / 2),
        }
    _validate_text_layout(text_layout, text_bounds_by_panel)
    _validate_text_manifest(_expected_pixel_text(spec), rendered_text)
    if supersample > 1:
        canvas = canvas.resize(
            (config["width_px"], config["height_px"]), Image.Resampling.LANCZOS)
    output = Path(output_path).resolve()
    geometry = Path(geometry_path).resolve()
    if output == geometry:
        raise QuantitativeFigureError("PNG and geometry manifest must use distinct paths")
    if output.suffix.lower() != ".png":
        raise QuantitativeFigureError("deterministic quantitative output must be PNG")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".png", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        canvas.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    manifest = {
        "schema_version": GEOMETRY_SCHEMA_VERSION,
        "renderer": RENDERER_ID,
        "spec_sha256": _canonical_hash(spec),
        "image": {
            "path": str(output), "sha256": sha256_file(output),
            "width_px": config["width_px"], "height_px": config["height_px"],
        },
        "resolved_render": config,
        "style": style,
        "fonts": font_records,
        "rendered_text": sorted(set(rendered_text)),
        "text_layout": text_layout,
        "panels": manifest_panels,
    }
    atomic_write_json(geometry, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a spec-driven deterministic quantitative figure")
    parser.add_argument(
        "--spec", required=True,
        help="quality-contract-v2-or-v3 quantitative figure JSON")
    parser.add_argument("--out", required=True, help="output PNG")
    parser.add_argument("--geometry", required=True, help="output geometry manifest JSON")
    args = parser.parse_args()
    try:
        manifest = render(_load_json(args.spec), args.out, args.geometry)
    except (OSError, json.JSONDecodeError, QuantitativeFigureError) as exc:
        raise SystemExit(f"quantitative render failed: {exc}")
    print(json.dumps({
        "status": "pass",
        "image": manifest["image"],
        "geometry": str(Path(args.geometry).resolve()),
        "panels": len(manifest["panels"]),
    }, indent=2))


if __name__ == "__main__":
    main()
