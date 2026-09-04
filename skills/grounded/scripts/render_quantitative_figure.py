#!/usr/bin/env python3
"""Render exact quantitative fork, slope, and trajectory figures from JSON.

The renderer is deliberately topic-neutral. Scientific content, labels, axes,
colours, and annotations come from the figure specification; this module owns
only reusable plotting grammar and publication-safe geometry. Every render
emits a geometry manifest so an independent checker can recompute the mapping
from data values to final-image pixels.

Two additive behaviours sit on top of the fixed grammar:

* the primary tier — strings named in `layout_plan.mobile_preview.primary_labels`
  are drawn large enough to clear the 390 px phone gate, and their measured
  glyph heights are written to the manifest as `primary_labels_resolved`;
* opt-in auto-layout (`plot_design.render.auto_layout: true` or
  `--auto-layout`) — a deterministic search over direct-label sides and canvas
  widths that stops at the first collision-free, clipping-free layout and
  records its choices as `resolved_layout`. The spec is never rewritten.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_file
from quantitative_drawing import (
    _draw_annotation,
    _draw_contrast_label,
    _draw_dashed,
    _draw_series_label,
    _draw_text,
    _draw_vertical_text,
    _expected_pixel_text,
    _label,
    _record_text_box,
    _text_boxes_overlap,
    _validate_text_layout,
    _validate_text_manifest,
    _wrap_annotation_lines,
)
from quantitative_figure_spec import (
    AUTO_LAYOUT_MAX_ATTEMPTS,
    AUTO_LAYOUT_WIDTH_CANDIDATES,
    DEFAULT_RENDER,
    GEOMETRY_SCHEMA_VERSION,
    RENDERER_ID,
    PrimaryTier,
    QuantitativeFigureError,
    TextLayoutError,
    _canonical_hash,
    _font_set,
    _layout,
    _load_json,
    _map_x,
    _map_y,
    _normalize_panels,
    _render_config,
    _rounded,
    _style,
    find_placeholders,
)


SERIES_LABEL_SIDES = ("right", "above", "left", "below")
CONTRAST_LABEL_SIDES = ("right", "left")
INSET_STEP_PX = 40
INSET_MAX_PX = 240
INSET_FOR_ROLE = {
    "y_tick": "left", "y_axis_label": "left",
    "x_tick": "bottom", "x_axis_label": "bottom",
    "panel_title": "top", "panel_label": "top",
}


def _mark_extents(panel: dict[str, Any], box: dict[str, float],
                  x_domain, y_domain) -> list[tuple[float, float, float, float]]:
    """Pixel boxes (left, top, right, bottom) of every marker and whisker."""
    extents = []
    for series in panel["series"]:
        radius = series["marker_radius_px"] + 4
        for point in series["points"]:
            x = _map_x(point["x"], x_domain, box)
            y = _map_y(point["y"], y_domain, box)
            extents.append((x - radius, y - radius, x + radius, y + radius))
            if point["y_interval"] is not None:
                low = _map_y(point["y_interval"][0], y_domain, box)
                high = _map_y(point["y_interval"][1], y_domain, box)
                extents.append((x - 12, min(low, high) - 3, x + 12, max(low, high) + 3))
            if point["x_interval"] is not None:
                low = _map_x(point["x_interval"][0], x_domain, box)
                high = _map_x(point["x_interval"][1], x_domain, box)
                extents.append((min(low, high) - 3, y - 12, max(low, high) + 3, y + 12))
    return extents


def _place_reference_label(draw, text, font, pixel, box, extents, supersample,
                           gap_px: float = 4.0):
    """Choose where a y-reference label sits so it crosses no data mark.

    Tries the band just above the line, then just below; within a band, the
    right end, the left end, then the widest free gap between marks. Returns
    ((x, y), anchor, side_name); falls back to the conventional right end.
    """
    probe = draw.textbbox((0, 0), text, font=font, anchor="lt")
    width = (probe[2] - probe[0]) / supersample
    height = (probe[3] - probe[1]) / supersample
    inner_left, inner_right = box["left"] + 12, box["right"] - 4
    for band, offset in (("", -24), ("-below", 24)):
        if band:
            top, bottom = pixel + offset, pixel + offset + height
        else:
            bottom, top = pixel + offset, pixel + offset - height
        blockers = sorted(
            (left - gap_px, right + gap_px)
            for left, mark_top, right, mark_bottom in extents
            if top - gap_px < mark_bottom and bottom + gap_px > mark_top)
        free = []
        cursor = inner_left
        for left, right in blockers:
            if left > cursor:
                free.append((cursor, min(left, inner_right)))
            cursor = max(cursor, right)
        if cursor < inner_right:
            free.append((cursor, inner_right))
        fits = [(left, right) for left, right in free if right - left >= width]
        if not fits:
            continue
        anchor_y = bottom if not band else top
        vertical = "b" if not band else "a"
        if fits[-1][1] >= inner_right - 0.5:
            return (inner_right, anchor_y), "r" + vertical, "right" + band
        if fits[0][0] <= inner_left + 0.5:
            return (inner_left, anchor_y), "l" + vertical, "left" + band
        left, right = max(fits, key=lambda item: item[1] - item[0])
        return ((left + right) / 2, anchor_y), "m" + vertical, "gap" + band
    return (inner_right, pixel - 20), "rb", "right-unresolved"


def _render_canvas(spec: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Draw *spec* and return (supersampled canvas, manifest body)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise QuantitativeFigureError(
            "Pillow is required for deterministic quantitative rendering") from exc
    placeholders = find_placeholders(spec)
    if placeholders:
        raise QuantitativeFigureError(
            "spec still contains scaffold placeholders: " + ", ".join(placeholders[:6]))
    panels = _normalize_panels(spec)
    config = _render_config(spec, len(panels))
    layouts = _layout(config, len(panels))
    style = _style(spec, config)
    fonts, font_records = _font_set(
        style, config["width_px"], config["height_px"], config["supersample"])
    supersample = config["supersample"]
    tier = PrimaryTier(spec, fonts, config["width_px"], supersample)
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
                tier.font_for(panel["title"], "panel_title", fonts["panel_title"]),
                style["ink_color"], "la", supersample,
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
            panel["y_axis"]["label"],
            tier.font_for(panel["y_axis"]["label"], "y_axis_label", fonts["axis"]),
            style["ink_color"],
            supersample, text_layout=text_layout, panel_id=panel["id"],
            role="y_axis_label", minimum_left_px=cell["left"] + 2,
            maximum_height_px=cell["bottom"] - cell["top"] - 8)
        _draw_text(
            draw, ((box["left"] + box["right"]) / 2, box["bottom"] + 70),
            panel["x_axis"]["label"],
            tier.font_for(panel["x_axis"]["label"], "x_axis_label", fonts["axis"]),
            style["ink_color"],
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
        mark_extents = _mark_extents(panel, box, x_domain, y_domain)
        for reference in panel["reference_lines"]:
            if reference["axis"] == "x":
                pixel = _map_x(reference["value"], x_domain, box)
                coordinates = (pixel, box["top"], pixel, box["bottom"])
            else:
                pixel = _map_y(reference["value"], y_domain, box)
                coordinates = (box["left"], pixel, box["right"], pixel)
            _draw_dashed(
                draw, coordinates, style["reference_color"], 2, 8, supersample)
            label_side = None
            if reference["label"]:
                reference_font = tier.font_for(
                    reference["label"], "reference_label", fonts["note"])
                if reference["axis"] == "y":
                    # A label must not cross a data mark: pick a clear spot
                    # along the line (right end, left end, or the widest gap).
                    position, anchor, label_side = _place_reference_label(
                        draw, reference["label"], reference_font, pixel, box,
                        mark_extents, supersample)
                    _draw_text(
                        draw, position, reference["label"],
                        reference_font, style["ink_color"], anchor, supersample,
                        text_layout=text_layout, panel_id=panel["id"],
                        role="reference_label")
                else:
                    label_side = "right-of-line"
                    _draw_text(
                        draw, (pixel + 8, box["top"] + 8), reference["label"],
                        reference_font, style["ink_color"], "la", supersample,
                        text_layout=text_layout, panel_id=panel["id"],
                        role="reference_label")
                rendered_text.append(reference["label"])
            references_manifest.append({
                "id": reference["id"], "axis": reference["axis"],
                "value": reference["value"], "pixel": _rounded(pixel),
                "label_side": label_side,
            })

        events_manifest = []
        for event in panel["events"]:
            x = _map_x(event["x"], x_domain, box)
            _draw_dashed(
                draw, (x, box["top"], x, box["bottom"]),
                style["reference_color"], 2, 8, supersample)
            _draw_text(
                draw, (x + 8, box["top"] + 8), event["label"],
                tier.font_for(event["label"], "event_label", fonts["note"]),
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
        marker_radius_by_key: dict[tuple[str, str], int] = {}
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
                marker_radius_by_key[(series["id"], point["id"])] = series["marker_radius_px"]
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
                        "axis": "y",
                        "series_id": series["id"], "point_id": point["id"],
                        "low_value": point["y_interval"][0],
                        "high_value": point["y_interval"][1],
                        "x_px": _rounded(x), "low_y_px": _rounded(low_y),
                        "high_y_px": _rounded(high_y),
                    })
                if point["x_interval"] is not None:
                    low_x = _map_x(point["x_interval"][0], x_domain, box)
                    high_x = _map_x(point["x_interval"][1], x_domain, box)
                    cap = 9
                    draw.line(
                        (round(low_x * supersample), round(y * supersample),
                         round(high_x * supersample), round(y * supersample)),
                        fill=series["color"], width=3 * supersample)
                    for endpoint in (low_x, high_x):
                        draw.line(
                            (round(endpoint * supersample), round((y - cap) * supersample),
                             round(endpoint * supersample), round((y + cap) * supersample)),
                            fill=series["color"], width=3 * supersample)
                    intervals_manifest.append({
                        "axis": "x",
                        "series_id": series["id"], "point_id": point["id"],
                        "low_value": point["x_interval"][0],
                        "high_value": point["x_interval"][1],
                        "y_px": _rounded(y), "low_x_px": _rounded(low_x),
                        "high_x_px": _rounded(high_x),
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
                        tier.font_for(point["label"], "point_label", fonts["value"]),
                        series["color"], supersample,
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
                    tier.font_for(series["label"], "series_label", fonts["series"]),
                    series["color"], supersample,
                    box, cell, offset=series["marker_radius_px"] + 11,
                    text_layout=text_layout, panel_id=panel["id"],
                    allow_reflow=spec.get("quality_contract_version") == 3)
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
                contrast["label_position"],
                tier.font_for(contrast["label"], "contrast", fonts["note"]),
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

        annotations_manifest = []
        for annotation in panel["annotations"]:
            x = _map_x(annotation["x"], x_domain, box)
            y = _map_y(annotation["y"], y_domain, box)
            leader_target = None
            clearance = 0.0
            if annotation["leader_to"] is not None:
                target_key = (annotation["leader_to"]["series_id"],
                              annotation["leader_to"]["point_id"])
                leader_target = point_pixels[target_key]
                clearance = marker_radius_by_key[target_key] + 5
            bbox = _draw_annotation(
                draw, x, y, annotation["text"], annotation["align"],
                tier.font_for(annotation["text"], "annotation", fonts["note"]),
                style["ink_color"], supersample, box, text_layout, panel["id"],
                leader_target=leader_target, leader_clearance_px=clearance,
                leader_fill=style["ink_color"])
            rendered_text.append(annotation["text"])
            annotations_manifest.append({
                "id": annotation["id"], "text": annotation["text"],
                "x_value": annotation["x"], "y_value": annotation["y"],
                "x_px": _rounded(x), "y_px": _rounded(y),
                "align": annotation["align"], "leader_to": annotation["leader_to"],
                "bbox_px": bbox,
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
            "annotations": annotations_manifest,
            "interval_key": interval_key_manifest,
        })

    unrendered = tier.unrendered()
    if unrendered:
        raise QuantitativeFigureError(
            "primary label was not rendered by any plot element: "
            + ", ".join(repr(text) for text in unrendered)
            + "; primary labels must be axis titles, series or point labels, panel "
            "titles, reference, event, or contrast labels, or annotations (tick "
            "labels are never primary)")

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
    _validate_text_layout(
        text_layout, text_bounds_by_panel,
        minimum_gap_px=(
            config["width_px"] * 3.0 / 390.0
            if spec.get("quality_contract_version") == 3 else 2.0))
    _validate_text_manifest(_expected_pixel_text(spec), rendered_text)
    body = {
        "resolved_render": config,
        "style": style,
        "fonts": font_records,
        "primary_tier": {
            "declared": tier.labels,
            "cap_px": tier.cap_px,
            "required_glyph_height_px": (
                _rounded(tier.required_glyph_height_px()) if tier.plan else None),
        },
        "primary_labels_resolved": tier.resolved,
        "rendered_text": sorted(set(rendered_text)),
        "text_layout": text_layout,
        "panels": manifest_panels,
    }
    return canvas, body


def _movable_labels(spec: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Index direct labels that auto-layout may move, by rendered text."""
    index: dict[str, list[dict[str, Any]]] = {}
    panels = spec.get("data", {}).get("panels", [])
    for panel_position, panel in enumerate(panels):
        if not isinstance(panel, dict):
            continue
        for row_position, row in enumerate(panel.get("rows") or []):
            if isinstance(row, dict) and row.get("label"):
                index.setdefault(str(row["label"]), []).append({
                    "panel": panel_position, "kind": "row", "index": row_position,
                    "id": str(row.get("id")), "candidates": SERIES_LABEL_SIDES,
                    "declared": row.get("label_position", "right"),
                })
        for series_position, series in enumerate(panel.get("series") or []):
            if not isinstance(series, dict):
                continue
            if series.get("label"):
                index.setdefault(str(series["label"]), []).append({
                    "panel": panel_position, "kind": "series", "index": series_position,
                    "id": str(series.get("id")), "candidates": SERIES_LABEL_SIDES,
                    "declared": series.get("label_position", "right"),
                })
            for point_position, point in enumerate(series.get("points") or []):
                if isinstance(point, dict) and point.get("label"):
                    index.setdefault(str(point["label"]), []).append({
                        "panel": panel_position, "kind": "point",
                        "index": (series_position, point_position),
                        "id": f"{series.get('id')}/{point.get('id')}",
                        "candidates": SERIES_LABEL_SIDES,
                        "declared": point.get("label_position", "above"),
                    })
        for contrast_position, contrast in enumerate(panel.get("contrasts") or []):
            if isinstance(contrast, dict) and contrast.get("label"):
                index.setdefault(str(contrast["label"]), []).append({
                    "panel": panel_position, "kind": "contrast",
                    "index": contrast_position, "id": str(contrast.get("id")),
                    "candidates": CONTRAST_LABEL_SIDES,
                    "declared": contrast.get("label_position", "right"),
                })
    return index


def _apply_overrides(spec: dict[str, Any], width: int | None,
                     positions: dict[tuple, str],
                     insets: dict[str, int] | None = None) -> dict[str, Any]:
    variant = copy.deepcopy(spec)
    if width is not None:
        render = variant.setdefault("plot_design", {}).setdefault("render", {})
        render["width_px"] = width
        render["height_px"] = round(width / float(variant["target_aspect_ratio"]))
    if insets:
        render = variant.setdefault("plot_design", {}).setdefault("render", {})
        current = dict(render.get("plot_insets_px") or {})
        current.update(insets)
        render["plot_insets_px"] = current
    panels = variant["data"]["panels"]
    for (panel_position, kind, index), position in positions.items():
        panel = panels[panel_position]
        if kind == "row":
            panel["rows"][index]["label_position"] = position
        elif kind == "series":
            panel["series"][index]["label_position"] = position
        elif kind == "point":
            series_position, point_position = index
            panel["series"][series_position]["points"][point_position][
                "label_position"] = position
        elif kind == "contrast":
            panel["contrasts"][index]["label_position"] = position
    return variant


def _auto_layout(spec: dict[str, Any]) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Search label sides, then canvas widths, until the layout validates."""
    movable = _movable_labels(spec)
    render = spec.get("plot_design", {}).get("render") or {}
    declared_width = int(render.get("width_px", DEFAULT_RENDER["width_px"]))
    widths = [declared_width] + [
        width for width in AUTO_LAYOUT_WIDTH_CANDIDATES if width > declared_width]
    attempts = 0
    last_error: Exception | None = None
    for width in widths:
        positions: dict[tuple, str] = {}
        tried: dict[tuple, list[str]] = {}
        insets: dict[str, int] = {}
        while attempts < AUTO_LAYOUT_MAX_ATTEMPTS:
            attempts += 1
            variant = _apply_overrides(
                spec, None if width == declared_width else width, positions, insets)
            try:
                canvas, body = _render_canvas(variant)
            except TextLayoutError as exc:
                last_error = exc
                target = None

                def widen(side: str) -> bool:
                    current = insets.get(side)
                    if current is None:
                        declared_insets = (render.get("plot_insets_px") or {})
                        current = int(declared_insets.get(
                            side, DEFAULT_RENDER["plot_insets_px"][side]))
                    if current + INSET_STEP_PX > INSET_MAX_PX:
                        return False
                    insets[side] = current + INSET_STEP_PX
                    return True

                # A clipped axis title or tick label cannot move; give its
                # gutter more room instead, up to the renderer's inset ceiling.
                if exc.kind == "clip":
                    side = INSET_FOR_ROLE.get(exc.role or "")
                    if side is not None and widen(side):
                        continue
                ordered = list(exc.texts)
                if exc.kind == "collision":
                    ordered = list(reversed(ordered))
                for text in ordered:
                    for candidate in movable.get(text, []):
                        key = (candidate["panel"], candidate["kind"], candidate["index"])
                        history = tried.setdefault(key, [candidate["declared"]])
                        remaining = [
                            side for side in candidate["candidates"]
                            if side not in history]
                        if remaining:
                            target = (key, candidate, remaining[0])
                            break
                    if target:
                        break
                if target is None:
                    # Nothing movable: a tick or axis title is in the way, so
                    # widen the gutter it lives in before trying a wider canvas.
                    gutters = [
                        INSET_FOR_ROLE[role] for role in exc.roles
                        if role in INSET_FOR_ROLE]
                    if exc.kind == "collision" and gutters and widen(gutters[0]):
                        continue
                    break
                key, candidate, side = target
                positions[key] = side
                tried[key].append(side)
                continue
            resolved = {
                "auto_layout": True,
                "attempts": attempts,
                "width_px": body["resolved_render"]["width_px"],
                "height_px": body["resolved_render"]["height_px"],
                "declared_width_px": declared_width,
                "plot_insets_px": dict(insets),
                "label_positions": [
                    {
                        "panel_id": spec["data"]["panels"][key[0]].get("id"),
                        "kind": key[1], "id": _movable_id(movable, key),
                        "position": side,
                    }
                    for key, side in positions.items()
                ],
            }
            return canvas, body, resolved
    detail = str(last_error) if last_error else "no layout attempt succeeded"
    raise QuantitativeFigureError(
        f"auto-layout could not resolve the text layout after {attempts} attempts "
        f"across widths {widths}; last failure: {detail}. Shorten the blocking "
        "label, move detail to the caption, or change panel topology")


def _movable_id(movable: dict[str, list[dict[str, Any]]], key: tuple) -> str:
    for candidates in movable.values():
        for candidate in candidates:
            if (candidate["panel"], candidate["kind"], candidate["index"]) == key:
                return candidate["id"]
    return "?"


def render(
    spec: dict[str, Any], output_path: str | Path,
    geometry_path: str | Path, *, auto_layout: bool | None = None,
) -> dict[str, Any]:
    """Render *spec* and atomically write PNG plus geometry manifest.

    *auto_layout* overrides `plot_design.render.auto_layout` when given.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise QuantitativeFigureError(
            "Pillow is required for deterministic quantitative rendering") from exc
    render_block = spec.get("plot_design", {}).get("render") or {}
    if auto_layout is None:
        auto_layout = bool(render_block.get("auto_layout", False))
    if auto_layout:
        canvas, body, resolved_layout = _auto_layout(spec)
    else:
        canvas, body = _render_canvas(spec)
        resolved_layout = {"auto_layout": False}
    config = body["resolved_render"]
    supersample = config["supersample"]
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
        "resolved_layout": resolved_layout,
        **body,
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
    parser.add_argument(
        "--auto-layout", action="store_true", default=None,
        help="search direct-label sides and canvas widths until the text layout "
             "validates; choices are recorded in the geometry manifest")
    args = parser.parse_args()
    try:
        manifest = render(
            _load_json(args.spec), args.out, args.geometry,
            auto_layout=True if args.auto_layout else None)
    except (OSError, json.JSONDecodeError, QuantitativeFigureError) as exc:
        raise SystemExit(f"quantitative render failed: {exc}")
    print(json.dumps({
        "status": "pass",
        "image": manifest["image"],
        "geometry": str(Path(args.geometry).resolve()),
        "panels": len(manifest["panels"]),
        "resolved_layout": manifest["resolved_layout"],
        "primary_labels_resolved": manifest["primary_labels_resolved"],
    }, indent=2))


if __name__ == "__main__":
    main()
