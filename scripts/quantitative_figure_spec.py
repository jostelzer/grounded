#!/usr/bin/env python3
"""Normalize and validate topic-neutral quantitative figure specifications."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from artifact_io import sha256_bytes
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
