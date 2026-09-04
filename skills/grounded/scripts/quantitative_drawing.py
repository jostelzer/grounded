#!/usr/bin/env python3
"""Drawing and text-layout primitives for deterministic quantitative figures."""

from __future__ import annotations

from itertools import combinations

import math
from typing import Any

from quantitative_figure_spec import QuantitativeFigureError, TextLayoutError, _rounded


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
    maximum_height_px: float | None = None,
):
    """Draw an upright sans-serif axis title rotated 90 degrees counter-clockwise."""
    from PIL import Image, ImageDraw

    probe = ImageDraw.Draw(canvas)
    rendered_text = text
    if maximum_height_px is not None:
        maximum_width = maximum_height_px * supersample - 8 * supersample
        words = text.split()
        candidates = []
        for line_count in range(1, min(3, len(words)) + 1):
            for breaks in combinations(range(1, len(words)), line_count - 1):
                indices = (0,) + breaks + (len(words),)
                lines = [" ".join(words[indices[i]:indices[i + 1]])
                         for i in range(line_count)]
                widths = [
                    probe.textbbox((0, 0), line, font=font, anchor="lt")[2]
                    for line in lines
                ]
                if max(widths) <= maximum_width:
                    candidates.append((line_count, max(widths), max(widths) - min(widths), lines))
            if candidates:
                break
        if candidates:
            _count, _maximum, _imbalance, lines = min(
                candidates, key=lambda item: (item[0], item[1], item[2]))
            rendered_text = "\n".join(lines)
    bbox = probe.multiline_textbbox(
        (0, 0), rendered_text, font=font, spacing=4 * supersample,
        align="center")
    padding = 4 * supersample
    width = round(bbox[2] - bbox[0])
    height = round(bbox[3] - bbox[1])
    patch = Image.new(
        "RGBA", (width + 2 * padding, height + 2 * padding), (0, 0, 0, 0))
    patch_draw = ImageDraw.Draw(patch)
    patch_draw.multiline_text(
        (padding - bbox[0], padding - bbox[1]), rendered_text,
        font=font, fill=fill, spacing=4 * supersample,
        align="center")
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
        raise TextLayoutError(
            f"label has no readable word-boundary fit inside its panel: {text!r}",
            texts=[text], kind="clip")
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
        raise TextLayoutError(
            f"contrast label has no horizontal space inside its panel: {text!r}",
            texts=[text], kind="clip")
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
    text_layout: list[dict[str, Any]], panel_id: str, *,
    allow_reflow: bool = False,
) -> None:
    """Direct-label a series, wrapping only when an edge forces a side flip."""
    if position not in {"above", "below"}:
        anchor = "lm" if position == "right" else "rm"
        label_x = x + offset if position == "right" else x - offset
        box = draw.textbbox(
            (round(label_x * supersample), round(y * supersample)),
            text, font=font, anchor=anchor)
        outside = (
            box[0] < panel_bounds["left"] * supersample
            or box[2] > panel_bounds["right"] * supersample)
        if outside and allow_reflow:
            fallback_position = (
                "above" if y >= (plot_bounds["top"] + plot_bounds["bottom"]) / 2
                else "below")
            _draw_series_label(
                draw, x, y, text, fallback_position, font, fill, supersample,
                plot_bounds, panel_bounds, offset, text_layout, panel_id,
                allow_reflow=allow_reflow)
            return
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


def _draw_annotation(
    draw, x, y, text, align, font, fill, supersample,
    plot_bounds: dict[str, float], text_layout: list[dict[str, Any]],
    panel_id: str, *, leader_target: tuple[float, float] | None = None,
    leader_clearance_px: float = 0.0, leader_fill=None,
) -> dict[str, float]:
    """Draw free explanatory copy anchored at a data coordinate.

    The anchor is the top edge of the text block: its left, centre, or right
    end depending on *align*. An optional thin leader runs from the nearest
    edge of the text block to the target mark, stopping short of it.
    """
    max_width = max(150, (plot_bounds["right"] - plot_bounds["left"]) * 0.45)
    lines = _wrap_annotation_lines(draw, text, font, max_width, supersample)
    line_spacing = 4 * supersample
    line_boxes = [
        draw.textbbox((0, 0), line, font=font, anchor="lt") for line in lines
    ]
    line_height = max(box[3] - box[1] for box in line_boxes)
    content_width = max(box[2] - box[0] for box in line_boxes)
    content_height = len(lines) * line_height + (len(lines) - 1) * line_spacing
    anchor_x = x * supersample
    top = y * supersample
    if align == "left":
        left = anchor_x
    elif align == "center":
        left = anchor_x - content_width / 2
    else:
        left = anchor_x - content_width
    right = left + content_width
    for index, (line, box) in enumerate(zip(lines, line_boxes)):
        width = box[2] - box[0]
        if align == "left":
            line_x = left
        elif align == "center":
            line_x = left + (content_width - width) / 2
        else:
            line_x = right - width
        line_y = top + index * (line_height + line_spacing)
        draw.text((round(line_x), round(line_y)), line, font=font, fill=fill, anchor="lt")
    bbox = (left, top, right, top + content_height)
    _record_text_box(text_layout, panel_id, "annotation", text, bbox, supersample)
    if leader_target is not None:
        target_x, target_y = leader_target[0] * supersample, leader_target[1] * supersample
        pad = 6 * supersample
        start_x = min(max(target_x, left - pad), right + pad)
        start_y = min(max(target_y, top - pad), bottom_edge(bbox) + pad)
        # Pull the start onto the padded boundary nearest the target.
        if left - pad < start_x < right + pad and top - pad < start_y < bottom_edge(bbox) + pad:
            distances = {
                "left": abs(target_x - (left - pad)),
                "right": abs(target_x - (right + pad)),
                "top": abs(target_y - (top - pad)),
                "bottom": abs(target_y - (bottom_edge(bbox) + pad)),
            }
            side = min(distances, key=distances.get)
            if side == "left":
                start_x = left - pad
            elif side == "right":
                start_x = right + pad
            elif side == "top":
                start_y = top - pad
            else:
                start_y = bottom_edge(bbox) + pad
        length = math.hypot(target_x - start_x, target_y - start_y)
        clearance = leader_clearance_px * supersample
        if length > clearance + 2 * supersample:
            unit_x = (target_x - start_x) / length
            unit_y = (target_y - start_y) / length
            end_x = target_x - unit_x * clearance
            end_y = target_y - unit_y * clearance
            draw.line(
                (round(start_x), round(start_y), round(end_x), round(end_y)),
                fill=leader_fill or fill, width=2 * supersample)
    return {
        "left": _rounded(bbox[0] / supersample), "top": _rounded(bbox[1] / supersample),
        "right": _rounded(bbox[2] / supersample), "bottom": _rounded(bbox[3] / supersample),
    }


def bottom_edge(bbox) -> float:
    return bbox[3]


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
    *, minimum_gap_px: float = 2.0,
) -> None:
    """Fail closed when deterministic copy clips or crowds inside a panel."""
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
            raise TextLayoutError(
                f"{record['role']} text does not fit inside panel {panel_id}: "
                f"{record['text']!r}", texts=[record["text"]], kind="clip",
                role=record["role"])
        by_panel.setdefault(panel_id, []).append(record)
    for panel_id, records in by_panel.items():
        for index, first in enumerate(records):
            for second in records[index + 1:]:
                if _text_boxes_overlap(
                    first["bbox_px"], second["bbox_px"], gap_px=minimum_gap_px
                ):
                    raise TextLayoutError(
                        f"text collision or sub-3px mobile clearance in panel {panel_id}: "
                        f"{first['text']!r} overlaps {second['text']!r}",
                        texts=[first["text"], second["text"]], kind="collision",
                        roles=[first["role"], second["role"]])


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
