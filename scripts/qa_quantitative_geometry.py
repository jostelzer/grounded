#!/usr/bin/env python3
"""Independently verify quantitative data-to-pixel geometry.

This checker intentionally does not import the renderer. It re-derives canvas
layout and every coordinate from the source spec, compares those values with
the geometry manifest, and probes the raster for the expected coloured data
marks. A self-consistent but incorrect renderer report therefore cannot pass.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_bytes, sha256_file


EXPECTED_RENDERER = "grounded.quantitative-trajectory.v1"
EXPECTED_SCHEMA_VERSION = 1
# Deliberately duplicated rather than imported from the renderer: QA must catch
# accidental changes to default layout arithmetic.
DEFAULT_WIDTH = 1800
DEFAULT_MARGIN = 72
DEFAULT_GAP = 72
DEFAULT_COLUMNS = 2
DEFAULT_SUPERSAMPLE = 2
DEFAULT_INSETS = {"left": 140, "right": 74, "top": 92, "bottom": 104}
COORDINATE_TOLERANCE_PX = 0.02
VALUE_TOLERANCE = 1e-9


class QuantitativeGeometryQaError(ValueError):
    """Raised when a spec or manifest cannot be interpreted safely."""


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QuantitativeGeometryQaError(f"{path} must contain a JSON object")
    return value


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QuantitativeGeometryQaError(f"{field} must be an object")
    return value


def _items(value: Any, field: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        raise QuantitativeGeometryQaError(
            f"{field} must be {'a non-empty list' if nonempty else 'a list'}")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuantitativeGeometryQaError(f"{field} must be a non-empty string")
    return value.strip()


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise QuantitativeGeometryQaError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise QuantitativeGeometryQaError(f"{field} must be finite")
    return result


def _integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise QuantitativeGeometryQaError(f"{field} must be an integer")
    return value


def _domain(axis: dict[str, Any], field: str) -> tuple[float, float]:
    raw = _items(axis.get("domain"), f"{field}.domain", nonempty=True)
    if len(raw) != 2:
        raise QuantitativeGeometryQaError(f"{field}.domain must contain two values")
    lower = _number(raw[0], f"{field}.domain[0]")
    upper = _number(raw[1], f"{field}.domain[1]")
    if lower >= upper:
        raise QuantitativeGeometryQaError(f"{field}.domain must increase")
    return lower, upper


def _resolved_config(spec: dict[str, Any], panel_count: int) -> dict[str, Any]:
    target_ratio = _number(spec.get("target_aspect_ratio"), "target_aspect_ratio")
    if not 1.0 <= target_ratio <= 4.0:
        raise QuantitativeGeometryQaError(
            "target_aspect_ratio must be between 1 and 4")
    design = _object(spec.get("plot_design"), "plot_design")
    render = design.get("render", {})
    render = _object(render, "plot_design.render")
    width = _integer(render.get("width_px", DEFAULT_WIDTH), "render.width_px")
    if not 1000 <= width <= 4096:
        raise QuantitativeGeometryQaError("render.width_px is outside the supported range")
    height = _integer(
        render.get("height_px", round(width / target_ratio)), "render.height_px")
    if not 500 <= height <= 4096:
        raise QuantitativeGeometryQaError(
            "render.height_px is outside the supported range")
    if abs(width / height / target_ratio - 1.0) > 0.005:
        raise QuantitativeGeometryQaError(
            "render dimensions do not preserve target_aspect_ratio")
    margin = _integer(
        render.get("outer_margin_px", DEFAULT_MARGIN), "render.outer_margin_px")
    if not 30 <= margin <= 240:
        raise QuantitativeGeometryQaError(
            "render.outer_margin_px is outside the supported range")
    gap = _integer(render.get("panel_gap_px", DEFAULT_GAP), "render.panel_gap_px")
    if not 20 <= gap <= 240:
        raise QuantitativeGeometryQaError(
            "render.panel_gap_px is outside the supported range")
    columns = _integer(
        render.get("columns", min(panel_count, DEFAULT_COLUMNS)), "render.columns")
    if not 1 <= columns <= min(4, panel_count):
        raise QuantitativeGeometryQaError("render.columns is incompatible with panel count")
    supersample = _integer(
        render.get("supersample", DEFAULT_SUPERSAMPLE), "render.supersample")
    if not 1 <= supersample <= 4:
        raise QuantitativeGeometryQaError(
            "render.supersample is outside the supported range")
    raw_insets = _object(
        render.get("plot_insets_px", DEFAULT_INSETS), "render.plot_insets_px")
    insets = {
        side: _integer(raw_insets.get(side, DEFAULT_INSETS[side]), f"insets.{side}")
        for side in ("left", "right", "top", "bottom")
    }
    if any(not 30 <= value <= 240 for value in insets.values()):
        raise QuantitativeGeometryQaError(
            "render.plot_insets_px values are outside the supported range")
    return {
        "width_px": width,
        "height_px": height,
        "outer_margin_px": margin,
        "panel_gap_px": gap,
        "columns": columns,
        "rows": math.ceil(panel_count / columns),
        "supersample": supersample,
        "plot_insets_px": insets,
    }


def _layout(config: dict[str, Any], panel_count: int) -> list[dict[str, float]]:
    width, height = config["width_px"], config["height_px"]
    margin, gap = config["outer_margin_px"], config["panel_gap_px"]
    columns, rows = config["columns"], config["rows"]
    insets = config["plot_insets_px"]
    cell_width = (width - 2 * margin - (columns - 1) * gap) / columns
    cell_height = (height - 2 * margin - (rows - 1) * gap) / rows
    result = []
    for index in range(panel_count):
        row, column = divmod(index, columns)
        cell_left = margin + column * (cell_width + gap)
        cell_top = margin + row * (cell_height + gap)
        plot = {
            "cell_left": cell_left,
            "cell_right": cell_left + cell_width,
            "cell_top": cell_top,
            "cell_bottom": cell_top + cell_height,
            "left": cell_left + insets["left"],
            "right": cell_left + cell_width - insets["right"],
            "top": cell_top + insets["top"],
            "bottom": cell_top + cell_height - insets["bottom"],
        }
        if plot["right"] - plot["left"] < 260 or plot["bottom"] - plot["top"] < 210:
            raise QuantitativeGeometryQaError(
                "render configuration leaves a plot area too small for publication labels")
        result.append(plot)
    return result


def _x_pixel(value: float, domain: tuple[float, float], box: dict[str, float]) -> float:
    fraction = (value - domain[0]) / (domain[1] - domain[0])
    return box["left"] + fraction * (box["right"] - box["left"])


def _y_pixel(value: float, domain: tuple[float, float], box: dict[str, float]) -> float:
    fraction = (value - domain[0]) / (domain[1] - domain[0])
    return box["bottom"] - fraction * (box["bottom"] - box["top"])


def _close(actual: Any, expected: float, field: str, errors: list[str],
           tolerance: float = COORDINATE_TOLERANCE_PX) -> None:
    try:
        observed = float(actual)
    except (TypeError, ValueError):
        errors.append(f"{field} must be numeric")
        return
    if not math.isfinite(observed) or abs(observed - expected) > tolerance:
        errors.append(
            f"{field}={observed:g} does not match expected {expected:.6f}")


def _same_value(actual: Any, expected: float, field: str, errors: list[str]) -> None:
    _close(actual, expected, field, errors, tolerance=VALUE_TOLERANCE)


def _unique_by(records: Any, keys: tuple[str, ...], field: str,
               errors: list[str]) -> dict[tuple[Any, ...], dict[str, Any]]:
    if not isinstance(records, list):
        errors.append(f"{field} must be a list")
        return {}
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"{field}[{index}] must be an object")
            continue
        key = tuple(record.get(name) for name in keys)
        if any(part is None for part in key):
            errors.append(f"{field}[{index}] is missing identity fields")
            continue
        if key in indexed:
            errors.append(f"{field} has duplicate identity {key}")
            continue
        indexed[key] = record
    return indexed


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    value = hex_colour.lstrip("#")
    if len(value) != 6:
        raise QuantitativeGeometryQaError(f"invalid series colour: {hex_colour}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _colour_distance(first, second) -> float:
    return math.sqrt(sum((int(a) - int(b)) ** 2 for a, b in zip(first, second)))


def _has_colour_near(image, x: float, y: float, colour: str,
                     radius: int, tolerance: float = 72.0) -> bool:
    target = _rgb(colour)
    center_x, center_y = round(x), round(y)
    left = max(0, center_x - radius)
    right = min(image.width - 1, center_x + radius)
    top = max(0, center_y - radius)
    bottom = min(image.height - 1, center_y + radius)
    for pixel_y in range(top, bottom + 1):
        for pixel_x in range(left, right + 1):
            if _colour_distance(image.getpixel((pixel_x, pixel_y))[:3], target) <= tolerance:
                return True
    return False


def _panel_manifest_map(manifest: dict[str, Any], errors: list[str]):
    return _unique_by(manifest.get("panels"), ("id",), "geometry.panels", errors)


def _text_boxes_overlap(first: dict[str, float], second: dict[str, float]) -> bool:
    half_gap = 1.0
    return (
        min(first["right"] + half_gap, second["right"] + half_gap)
        - max(first["left"] - half_gap, second["left"] - half_gap) > 0
        and min(first["bottom"] + half_gap, second["bottom"] + half_gap)
        - max(first["top"] - half_gap, second["top"] - half_gap) > 0
    )


def _audit_text_layout(
    geometry: dict[str, Any], panel_bounds: dict[str, dict[str, float]],
    canvas: tuple[int, int], errors: list[str],
) -> int:
    records = geometry.get("text_layout")
    if not isinstance(records, list) or not records:
        errors.append("geometry text_layout must be a non-empty list")
        return 0
    normalized: list[tuple[str, str, dict[str, float]]] = []
    for index, record in enumerate(records):
        field = f"geometry.text_layout[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{field} must be an object")
            continue
        panel_id = record.get("panel_id")
        text = record.get("text")
        raw_box = record.get("bbox_px")
        if panel_id not in panel_bounds:
            errors.append(f"{field}.panel_id does not identify a spec panel")
            continue
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{field}.text must be a non-empty string")
            continue
        if not isinstance(raw_box, dict):
            errors.append(f"{field}.bbox_px must be an object")
            continue
        try:
            box = {
                side: float(raw_box[side])
                for side in ("left", "top", "right", "bottom")
            }
        except (KeyError, TypeError, ValueError):
            errors.append(f"{field}.bbox_px must contain four numeric edges")
            continue
        if not all(math.isfinite(value) for value in box.values()):
            errors.append(f"{field}.bbox_px edges must be finite")
            continue
        if box["left"] >= box["right"] or box["top"] >= box["bottom"]:
            errors.append(f"{field}.bbox_px must have positive area")
            continue
        bounds = panel_bounds[panel_id]
        if (
            box["left"] < bounds["left"] - 0.5
            or box["right"] > bounds["right"] + 0.5
            or box["top"] < -0.5
            or box["bottom"] > canvas[1] + 0.5
        ):
            errors.append(f"{field} is not contained by its panel and canvas")
        normalized.append((panel_id, text, box))
    for index, (panel_id, text, box) in enumerate(normalized):
        for other_panel, other_text, other_box in normalized[index + 1:]:
            if panel_id == other_panel and _text_boxes_overlap(box, other_box):
                errors.append(
                    f"geometry text collision in panel {panel_id}: "
                    f"{text!r} overlaps {other_text!r}")
    rendered_text = geometry.get("rendered_text")
    if isinstance(rendered_text, list):
        layout_text = {text for _panel, text, _box in normalized}
        if layout_text != set(rendered_text):
            errors.append("geometry text_layout does not cover rendered_text exactly")
    return len(normalized)


def audit_geometry(
    spec: dict[str, Any], image_path: str | Path,
    geometry: dict[str, Any],
) -> dict[str, Any]:
    """Return a fail-closed geometry report for one deterministic raster."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise QuantitativeGeometryQaError(
            "Pillow is required for quantitative geometry QA") from exc
    if not isinstance(spec, dict) or not isinstance(geometry, dict):
        raise QuantitativeGeometryQaError("spec and geometry must be objects")
    if spec.get("quality_contract_version") not in {2, 3}:
        raise QuantitativeGeometryQaError(
            "spec must use quality_contract_version=2 or 3")
    if spec.get("archetype") != "quantitative" or spec.get("render_route") not in {
            "deterministic", "composite"}:
        raise QuantitativeGeometryQaError(
            "geometry QA requires a deterministic or composite quantitative spec")
    panels = _items(_object(spec.get("data"), "data").get("panels"),
                    "data.panels", nonempty=True)
    config = _resolved_config(spec, len(panels))
    layouts = _layout(config, len(panels))
    panel_text_bounds = {
        _string(_object(panel, "panel").get("id"), "panel.id"): {
            "left": layout["cell_left"], "right": layout["cell_right"],
        }
        for panel, layout in zip(panels, layouts)
    }
    errors: list[str] = []
    if geometry.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        errors.append(
            f"geometry schema_version must be {EXPECTED_SCHEMA_VERSION}")
    if geometry.get("renderer") != EXPECTED_RENDERER:
        errors.append(f"geometry renderer must be {EXPECTED_RENDERER}")
    if geometry.get("spec_sha256") != _canonical_hash(spec):
        errors.append("geometry manifest does not match the exact figure spec")
    image_path = Path(image_path).resolve()
    image_record = geometry.get("image")
    if not isinstance(image_record, dict):
        errors.append("geometry image record must be an object")
        image_record = {}
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")
    except OSError as exc:
        raise QuantitativeGeometryQaError(f"cannot open figure raster: {exc}") from exc
    if image.size != (config["width_px"], config["height_px"]):
        errors.append(
            f"image dimensions {image.size} do not match expected "
            f"{(config['width_px'], config['height_px'])}")
    if image_record.get("width_px") != image.width or image_record.get("height_px") != image.height:
        errors.append("geometry image dimensions do not match the raster")
    if image_record.get("sha256") != sha256_file(image_path):
        errors.append("geometry image hash does not match the raster")
    resolved = geometry.get("resolved_render")
    if not isinstance(resolved, dict):
        errors.append("geometry resolved_render must be an object")
    else:
        for field in (
            "width_px", "height_px", "outer_margin_px", "panel_gap_px",
            "columns", "rows", "supersample",
        ):
            if resolved.get(field) != config[field]:
                errors.append(f"geometry resolved_render.{field} does not match the spec")
        if resolved.get("plot_insets_px") != config["plot_insets_px"]:
            errors.append("geometry resolved_render.plot_insets_px does not match the spec")
    panel_records = _panel_manifest_map(geometry, errors)
    expected_panel_ids = set()
    points_verified = intervals_verified = marks_probed = 0
    for panel_index, (raw_panel, box) in enumerate(zip(panels, layouts)):
        panel_field = f"data.panels[{panel_index}]"
        panel = _object(raw_panel, panel_field)
        panel_id = _string(panel.get("id"), f"{panel_field}.id")
        expected_panel_ids.add((panel_id,))
        record = panel_records.get((panel_id,))
        if record is None:
            errors.append(f"geometry is missing panel {panel_id}")
            continue
        plot_box = record.get("plot_box_px")
        if not isinstance(plot_box, dict):
            errors.append(f"panel {panel_id} plot_box_px must be an object")
            plot_box = {}
        for side in ("left", "right", "top", "bottom"):
            _close(plot_box.get(side), box[side],
                   f"panel {panel_id} plot_box_px.{side}", errors)
        x_axis = _object(panel.get("x_axis"), f"{panel_field}.x_axis")
        y_axis = _object(panel.get("y_axis"), f"{panel_field}.y_axis")
        x_domain = _domain(x_axis, f"{panel_field}.x_axis")
        y_domain = _domain(y_axis, f"{panel_field}.y_axis")
        axis_record = record.get("x_axis")
        if not isinstance(axis_record, dict):
            errors.append(f"panel {panel_id} x_axis must be an object")
            axis_record = {}
        if axis_record.get("domain") != list(x_domain):
            errors.append(f"panel {panel_id} x-axis domain does not match the spec")
        expected_x_range = [box["left"], box["right"]]
        raw_x_range = axis_record.get("pixel_range")
        if not isinstance(raw_x_range, list) or len(raw_x_range) != 2:
            errors.append(f"panel {panel_id} x-axis pixel_range is invalid")
        else:
            for index, expected in enumerate(expected_x_range):
                _close(raw_x_range[index], expected,
                       f"panel {panel_id} x-axis pixel_range[{index}]", errors)
        axis_record_y = record.get("y_axis")
        if not isinstance(axis_record_y, dict):
            errors.append(f"panel {panel_id} y_axis must be an object")
            axis_record_y = {}
        if axis_record_y.get("domain") != list(y_domain):
            errors.append(f"panel {panel_id} y-axis domain does not match the spec")
        expected_y_range = [box["bottom"], box["top"]]
        raw_y_range = axis_record_y.get("pixel_range")
        if not isinstance(raw_y_range, list) or len(raw_y_range) != 2:
            errors.append(f"panel {panel_id} y-axis pixel_range is invalid")
        else:
            for index, expected in enumerate(expected_y_range):
                _close(raw_y_range[index], expected,
                       f"panel {panel_id} y-axis pixel_range[{index}]", errors)

        for axis_name, raw_axis, domain, manifest_axis, pixel_function, pixel_field in (
            ("x", x_axis, x_domain, axis_record, _x_pixel, "x_px"),
            ("y", y_axis, y_domain, axis_record_y, _y_pixel, "y_px"),
        ):
            tick_records = _unique_by(
                manifest_axis.get("ticks"), ("value",),
                f"panel {panel_id} {axis_name}-axis ticks", errors)
            expected_tick_keys = set()
            for tick_index, raw_tick in enumerate(_items(
                    raw_axis.get("ticks"), f"{panel_field}.{axis_name}_axis.ticks",
                    nonempty=True)):
                tick = _object(raw_tick, f"{panel_field}.{axis_name}_axis.ticks[{tick_index}]")
                value = _number(tick.get("value"), "tick.value")
                expected_tick_keys.add((value,))
                tick_record = tick_records.get((value,))
                if tick_record is None:
                    errors.append(f"panel {panel_id} is missing {axis_name}-tick {value:g}")
                    continue
                expected_pixel = pixel_function(value, domain, box)
                _close(tick_record.get(pixel_field), expected_pixel,
                       f"panel {panel_id} {axis_name}-tick {value:g} {pixel_field}", errors)
            for unexpected in set(tick_records) - expected_tick_keys:
                errors.append(f"panel {panel_id} has unexpected {axis_name}-tick {unexpected[0]}")

        point_records = _unique_by(
            record.get("points"), ("series_id", "point_id"),
            f"panel {panel_id} points", errors)
        interval_records = _unique_by(
            record.get("intervals"), ("series_id", "point_id"),
            f"panel {panel_id} intervals", errors)
        expected_points = set()
        expected_intervals = set()
        expected_point_values: dict[tuple[str, str], tuple[float, float]] = {}
        for series_index, raw_series in enumerate(_items(
                panel.get("series"), f"{panel_field}.series", nonempty=True)):
            series = _object(raw_series, f"{panel_field}.series[{series_index}]")
            series_id = _string(series.get("id"), "series.id")
            colour = _string(series.get("color"), "series.color").upper()
            line_width = int(series.get("line_width_px", 7))
            marker_radius = int(series.get("marker_radius_px", 9))
            points = _items(series.get("points"), "series.points", nonempty=True)
            expected_path = []
            for point_index, raw_point in enumerate(points):
                point = _object(raw_point, f"series.points[{point_index}]")
                point_id = _string(point.get("id"), "point.id")
                key = (series_id, point_id)
                expected_points.add(key)
                x_value = _number(point.get("x"), "point.x")
                y_value = _number(point.get("y"), "point.y")
                expected_point_values[key] = (x_value, y_value)
                x_px = _x_pixel(x_value, x_domain, box)
                y_px = _y_pixel(y_value, y_domain, box)
                expected_path.append((x_px, y_px))
                point_record = point_records.get(key)
                if point_record is None:
                    errors.append(f"panel {panel_id} is missing point {series_id}/{point_id}")
                    continue
                _same_value(point_record.get("x_value"), x_value,
                            f"point {series_id}/{point_id} x_value", errors)
                _same_value(point_record.get("y_value"), y_value,
                            f"point {series_id}/{point_id} y_value", errors)
                _close(point_record.get("x_px"), x_px,
                       f"point {series_id}/{point_id} x_px", errors)
                _close(point_record.get("y_px"), y_px,
                       f"point {series_id}/{point_id} y_px", errors)
                if str(point_record.get("color") or "").upper() != colour:
                    errors.append(f"point {series_id}/{point_id} colour does not match the spec")
                if not _has_colour_near(
                        image, x_px, y_px, colour,
                        radius=marker_radius + line_width + 4):
                    errors.append(
                        f"raster is missing the coloured mark for {series_id}/{point_id}")
                else:
                    marks_probed += 1
                points_verified += 1
                interval = point.get("y_interval")
                if interval is not None:
                    interval = _items(interval, "point.y_interval", nonempty=True)
                    low, high = _number(interval[0], "interval.low"), _number(
                        interval[1], "interval.high")
                    expected_intervals.add(key)
                    interval_record = interval_records.get(key)
                    if interval_record is None:
                        errors.append(
                            f"panel {panel_id} is missing interval {series_id}/{point_id}")
                    else:
                        low_y, high_y = (
                            _y_pixel(low, y_domain, box),
                            _y_pixel(high, y_domain, box),
                        )
                        _same_value(interval_record.get("low_value"), low,
                                    f"interval {series_id}/{point_id} low_value", errors)
                        _same_value(interval_record.get("high_value"), high,
                                    f"interval {series_id}/{point_id} high_value", errors)
                        _close(interval_record.get("x_px"), x_px,
                               f"interval {series_id}/{point_id} x_px", errors)
                        _close(interval_record.get("low_y_px"), low_y,
                               f"interval {series_id}/{point_id} low_y_px", errors)
                        _close(interval_record.get("high_y_px"), high_y,
                               f"interval {series_id}/{point_id} high_y_px", errors)
                        for label, endpoint in (("low", low_y), ("high", high_y)):
                            if not _has_colour_near(image, x_px, endpoint, colour, radius=12):
                                errors.append(
                                    f"raster is missing {label} interval cap for "
                                    f"{series_id}/{point_id}")
                            else:
                                marks_probed += 1
                        intervals_verified += 1
            for first, second in zip(expected_path, expected_path[1:]):
                for fraction in (0.25, 0.5, 0.75):
                    sample_x = first[0] + fraction * (second[0] - first[0])
                    sample_y = first[1] + fraction * (second[1] - first[1])
                    if not _has_colour_near(
                            image, sample_x, sample_y, colour,
                            radius=max(5, line_width + 2)):
                        errors.append(
                            f"raster path for series {series_id} misses its expected geometry")
                        break
                    marks_probed += 1
        for unexpected in set(point_records) - expected_points:
            errors.append(
                f"panel {panel_id} has unexpected point {unexpected[0]}/{unexpected[1]}")
        for unexpected in set(interval_records) - expected_intervals:
            errors.append(
                f"panel {panel_id} has unexpected interval {unexpected[0]}/{unexpected[1]}")

        reference_records = _unique_by(
            record.get("reference_lines"), ("id",),
            f"panel {panel_id} reference_lines", errors)
        expected_reference_ids = set()
        for index, raw_reference in enumerate(panel.get("reference_lines", [])):
            reference = _object(raw_reference, f"reference_lines[{index}]")
            identity = _string(reference.get("id"), "reference.id")
            expected_reference_ids.add((identity,))
            axis = reference.get("axis")
            value = _number(reference.get("value"), "reference.value")
            expected_pixel = (
                _x_pixel(value, x_domain, box) if axis == "x"
                else _y_pixel(value, y_domain, box))
            reference_record = reference_records.get((identity,))
            if reference_record is None:
                errors.append(f"panel {panel_id} is missing reference line {identity}")
            else:
                if reference_record.get("axis") != axis:
                    errors.append(f"reference line {identity} axis does not match the spec")
                _same_value(reference_record.get("value"), value,
                            f"reference line {identity} value", errors)
                _close(reference_record.get("pixel"), expected_pixel,
                       f"reference line {identity} pixel", errors)
        for unexpected in set(reference_records) - expected_reference_ids:
            errors.append(f"panel {panel_id} has unexpected reference line {unexpected[0]}")

        event_records = _unique_by(
            record.get("events"), ("id",), f"panel {panel_id} events", errors)
        expected_event_ids = set()
        for index, raw_event in enumerate(panel.get("events", [])):
            event = _object(raw_event, f"events[{index}]")
            identity = _string(event.get("id"), "event.id")
            expected_event_ids.add((identity,))
            x_value = _number(event.get("x"), "event.x")
            event_record = event_records.get((identity,))
            if event_record is None:
                errors.append(f"panel {panel_id} is missing event {identity}")
            else:
                _same_value(event_record.get("x_value"), x_value,
                            f"event {identity} x_value", errors)
                _close(event_record.get("x_px"), _x_pixel(x_value, x_domain, box),
                       f"event {identity} x_px", errors)
        for unexpected in set(event_records) - expected_event_ids:
            errors.append(f"panel {panel_id} has unexpected event {unexpected[0]}")

        contrast_records = _unique_by(
            record.get("contrasts"), ("id",), f"panel {panel_id} contrasts", errors)
        expected_contrast_ids = set()
        for index, raw_contrast in enumerate(panel.get("contrasts", [])):
            contrast = _object(raw_contrast, f"contrasts[{index}]")
            identity = _string(contrast.get("id"), "contrast.id")
            expected_contrast_ids.add((identity,))
            from_ref = _object(contrast.get("from"), "contrast.from")
            to_ref = _object(contrast.get("to"), "contrast.to")
            from_key = (_string(from_ref.get("series_id"), "from.series_id"),
                        _string(from_ref.get("point_id"), "from.point_id"))
            to_key = (_string(to_ref.get("series_id"), "to.series_id"),
                      _string(to_ref.get("point_id"), "to.point_id"))
            if from_key not in expected_point_values or to_key not in expected_point_values:
                errors.append(f"contrast {identity} references an unknown point")
                continue
            x_value = _number(contrast.get("x"), "contrast.x")
            offset = int(contrast.get("x_offset_px", 0))
            bracket_x = _x_pixel(x_value, x_domain, box) + offset
            from_y = _y_pixel(expected_point_values[from_key][1], y_domain, box)
            to_y = _y_pixel(expected_point_values[to_key][1], y_domain, box)
            expected_estimate = expected_point_values[from_key][1] - expected_point_values[to_key][1]
            supplied_estimate = _number(contrast.get("estimate"), "contrast.estimate")
            decimal_places = _integer(
                contrast.get("decimal_places", 1), "contrast.decimal_places")
            if not 0 <= decimal_places <= 8:
                raise QuantitativeGeometryQaError(
                    "contrast.decimal_places must be between 0 and 8")
            rounding_tolerance = 0.5 * (10 ** (-decimal_places)) + 1e-9
            if abs(supplied_estimate - expected_estimate) > rounding_tolerance:
                errors.append(f"contrast {identity} estimate is inconsistent with its points")
            contrast_record = contrast_records.get((identity,))
            if contrast_record is None:
                errors.append(f"panel {panel_id} is missing contrast {identity}")
            else:
                _same_value(contrast_record.get("x_value"), x_value,
                            f"contrast {identity} x_value", errors)
                _close(contrast_record.get("bracket_x_px"), bracket_x,
                       f"contrast {identity} bracket_x_px", errors)
                _close(contrast_record.get("from_y_px"), from_y,
                       f"contrast {identity} from_y_px", errors)
                _close(contrast_record.get("to_y_px"), to_y,
                       f"contrast {identity} to_y_px", errors)
                _same_value(contrast_record.get("estimate"), supplied_estimate,
                            f"contrast {identity} estimate", errors)
                if contrast_record.get("interval") != contrast.get("interval"):
                    errors.append(f"contrast {identity} interval does not match the spec")
        for unexpected in set(contrast_records) - expected_contrast_ids:
            errors.append(f"panel {panel_id} has unexpected contrast {unexpected[0]}")
    for unexpected in set(panel_records) - expected_panel_ids:
        errors.append(f"geometry has unexpected panel {unexpected[0]}")
    text_boxes_verified = _audit_text_layout(
        geometry, panel_text_bounds, image.size, errors)
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "metrics": {
            "panel_count": len(panels),
            "points_verified": points_verified,
            "intervals_verified": intervals_verified,
            "raster_marks_probed": marks_probed,
            "text_boxes_verified": text_boxes_verified,
            "coordinate_tolerance_px": COORDINATE_TOLERANCE_PX,
        },
        "image": str(image_path),
        "geometry_renderer": geometry.get("renderer"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify deterministic quantitative data-to-pixel geometry")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--geometry", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    try:
        report = audit_geometry(
            _load_json(args.spec), args.image, _load_json(args.geometry))
    except (OSError, json.JSONDecodeError, QuantitativeGeometryQaError) as exc:
        raise SystemExit(f"quantitative geometry QA failed: {exc}")
    if args.report:
        atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
