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
import os
import tempfile
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_file
from quantitative_drawing import (
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
    GEOMETRY_SCHEMA_VERSION,
    RENDERER_ID,
    QuantitativeFigureError,
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
)
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
