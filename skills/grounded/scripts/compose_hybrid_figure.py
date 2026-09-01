#!/usr/bin/env python3
"""Add exact, non-distorted vector-like overlays to generated figure artwork.

The compositor deliberately never resizes its base raster. Positions are
normalized to the source canvas, font sizes scale uniformly from a 1536 px
reference width, and circular marks use one radius measured against the shorter
canvas edge. This preserves the visual quality of generated artwork while
making labels, arrows, legends, and simple geometry deterministic.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_file
from figure_typography import (
    FigureTypographyError,
    load_font_face,
    resolve_font_path,
)


ROOT = Path(__file__).resolve().parents[1]
WRITING_STYLES = ROOT / "references" / "figure-writing-style-overlays.json"
ITEM_TYPES = {"text", "line", "arrow", "circle", "rectangle", "image_region"}


class HybridFigureError(ValueError):
    """Raised when a hybrid overlay would be ambiguous or distort geometry."""


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HybridFigureError(f"{path} must contain a JSON object")
    return value


def _number(value: Any, field: str, *, minimum: float = 0.0,
            maximum: float = 1.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise HybridFigureError(f"{field} must be numeric") from exc
    if not minimum <= result <= maximum:
        raise HybridFigureError(
            f"{field} must be between {minimum:g} and {maximum:g}")
    return result


def _point(item: dict[str, Any], prefix: str = "") -> tuple[float, float]:
    return (
        _number(item.get(prefix + "x"), prefix + "x"),
        _number(item.get(prefix + "y"), prefix + "y"),
    )


def _writing_style(spec: dict[str, Any]) -> dict[str, Any]:
    overlays = _load_json(WRITING_STYLES)
    style = spec.get("review_style", "scientific")
    try:
        selected = overlays[style]
        if not isinstance(selected, dict):
            raise TypeError
        return selected
    except (KeyError, TypeError) as exc:
        raise HybridFigureError(f"unknown review_style for overlay: {style}") from exc


def _style_background(spec: dict[str, Any], style: dict[str, Any]) -> str:
    explicit = spec.get("background_color")
    if explicit is not None:
        if not isinstance(explicit, str) or not re.fullmatch(
                r"#[0-9A-Fa-f]{6}", explicit):
            raise HybridFigureError("background_color must be a six-digit hex colour")
        return explicit.upper()
    description = str((style.get("canvas") or {}).get("background") or "")
    match = re.search(r"#[0-9A-Fa-f]{6}", description)
    return match.group(0).upper() if match else "#FFFFFF"


def _wrap_lines(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for source_line in text.splitlines() or [""]:
        words = source_line.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if width <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _scaled_px(value: Any, width: int, field: str, *, minimum: float = 1.0,
               maximum: float = 300.0) -> int:
    reference = _number(value, field, minimum=minimum, maximum=maximum)
    return max(1, round(reference * width / 1536.0))


def _contains(outer: tuple[int, int, int, int],
              inner: tuple[int, int, int, int]) -> bool:
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def _fill_is_opaque(fill: Any) -> bool:
    if not isinstance(fill, str) or not fill.strip():
        return False
    value = fill.strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{8}", value):
        return value[-2:].lower() == "ff"
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", value))


def _draw_text(draw, item: dict[str, Any], canvas: tuple[int, int],
               family: str, fallback: str, font_records: list[dict[str, Any]],
               *, opaque_masks: list[tuple[int, int, int, int]]) -> dict[str, Any]:
    width, height = canvas
    text = item.get("text")
    if not isinstance(text, str) or not text:
        raise HybridFigureError("text overlay requires non-empty text")
    x, y = _point(item)
    max_width_fraction = _number(item.get("max_width", 0.3), "max_width",
                                 minimum=0.02, maximum=1.0)
    max_width = max(1, round(max_width_fraction * width))
    size = _scaled_px(item.get("size_px_at_1536", 28), width,
                      "size_px_at_1536", minimum=8, maximum=120)
    bold = item.get("weight", "regular") == "bold"
    if item.get("weight", "regular") not in {"regular", "bold"}:
        raise HybridFigureError("text weight must be regular or bold")
    requested_family = str(item.get("font_family") or family)
    explicit = item.get("font_path")
    try:
        font_path = resolve_font_path(requested_family, bold, explicit)
        font, face_index, face_style = load_font_face(font_path, size, bold)
    except FigureTypographyError as exc:
        if explicit or requested_family == fallback:
            raise HybridFigureError(f"cannot load requested font: {exc}") from exc
        try:
            font_path = resolve_font_path(fallback, bold)
            font, face_index, face_style = load_font_face(font_path, size, bold)
        except FigureTypographyError as fallback_exc:
            raise HybridFigureError(
                f"cannot load fallback font: {fallback_exc}") from fallback_exc
        requested_family = fallback
    font_records.append({
        "family": requested_family,
        "path": str(font_path),
        "face_index": face_index,
        "face_style": face_style,
        "weight": "bold" if bold else "regular",
        "size_px": size,
    })
    lines = _wrap_lines(draw, text, font, max_width)
    spacing = max(1, round(size * float(item.get("line_spacing", 0.24))))
    line_boxes = [draw.textbbox((0, 0), line or " ", font=font) for line in lines]
    line_widths = [box[2] - box[0] for box in line_boxes]
    if any(line_width > max_width for line_width in line_widths):
        raise HybridFigureError(
            f"text overlay cannot wrap within max_width without distorting: {text!r}")
    line_heights = [box[3] - box[1] for box in line_boxes]
    total_height = sum(line_heights) + spacing * max(0, len(lines) - 1)
    left = round(x * width)
    top = round(y * height)
    align = item.get("align", "left")
    if align not in {"left", "center", "right"}:
        raise HybridFigureError("text align must be left, center, or right")
    background = item.get("background")
    padding = _scaled_px(item.get("padding_px_at_1536", 0), width,
                         "padding_px_at_1536", minimum=0, maximum=80)
    if (left - padding < 0 or top - padding < 0
            or left + max_width + padding > width
            or top + total_height + padding > height):
        raise HybridFigureError(
            f"text overlay falls outside the canvas: {text!r}")
    text_bounds = (left, top, left + max_width, top + total_height)
    if background is not None and not _fill_is_opaque(background):
        raise HybridFigureError(
            f"text overlay {text!r} background must be an opaque hex colour")
    mask_present = _fill_is_opaque(background) or any(
        _contains(mask, text_bounds) for mask in opaque_masks)
    if not mask_present:
        raise HybridFigureError(
            f"text overlay {text!r} has no explicit opaque mask. Unmasked hybrid "
            "text is forbidden because the generated base may already contain text. "
            "Keep a correct generated label, or erase the complete label region with "
            "a text background or preceding opaque rectangle before replacement.")
    if background is not None:
        draw.rectangle(
            (left - padding, top - padding,
             left + max_width + padding, top + total_height + padding),
            fill=str(background),
        )
    cursor_y = top
    for line, box, line_height in zip(lines, line_boxes, line_heights):
        line_width = box[2] - box[0]
        if align == "center":
            line_x = left + (max_width - line_width) / 2
        elif align == "right":
            line_x = left + max_width - line_width
        else:
            line_x = left
        draw.text(
            (round(line_x), cursor_y), line, font=font,
            fill=str(item.get("color", "#1A1A1A")),
        )
        cursor_y += line_height + spacing
    return {
        "text": text,
        "bounds_px": list(text_bounds),
        "opaque_mask": mask_present,
    }


def _line_geometry(item: dict[str, Any], canvas: tuple[int, int]):
    width, height = canvas
    x1, y1 = _point(item, "start_")
    x2, y2 = _point(item, "end_")
    return (round(x1 * width), round(y1 * height),
            round(x2 * width), round(y2 * height))


def _draw_line(draw, item: dict[str, Any], canvas: tuple[int, int],
               *, arrow: bool) -> None:
    width, height = canvas
    x1, y1, x2, y2 = _line_geometry(item, canvas)
    stroke = _scaled_px(item.get("stroke_px_at_1536", 3), width,
                        "stroke_px_at_1536", minimum=1, maximum=40)
    color = str(item.get("color", "#1A1A1A"))
    dash = item.get("dash")
    if dash:
        if not (isinstance(dash, list) and len(dash) == 2):
            raise HybridFigureError("dash must be [on, off]")
        on = _scaled_px(dash[0], width, "dash[0]", minimum=1, maximum=100)
        off = _scaled_px(dash[1], width, "dash[1]", minimum=1, maximum=100)
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            raise HybridFigureError("line endpoints must differ")
        position = 0.0
        while position < length:
            end = min(length, position + on)
            start_fraction = position / length
            end_fraction = end / length
            draw.line((
                x1 + (x2 - x1) * start_fraction,
                y1 + (y2 - y1) * start_fraction,
                x1 + (x2 - x1) * end_fraction,
                y1 + (y2 - y1) * end_fraction,
            ), fill=color, width=stroke)
            position += on + off
    else:
        draw.line((x1, y1, x2, y2), fill=color, width=stroke)
    if arrow:
        angle = math.atan2(y2 - y1, x2 - x1)
        head = _scaled_px(item.get("head_px_at_1536", 16), width,
                          "head_px_at_1536", minimum=4, maximum=80)
        spread = math.radians(float(item.get("head_angle_degrees", 28)))
        points = [(x2, y2)]
        for direction in (angle + math.pi - spread, angle + math.pi + spread):
            points.append((x2 + head * math.cos(direction),
                           y2 + head * math.sin(direction)))
        draw.polygon(points, fill=color)


def _draw_circle(draw, item: dict[str, Any], canvas: tuple[int, int]) -> None:
    width, height = canvas
    x, y = _point(item)
    radius_fraction = _number(item.get("radius"), "radius",
                              minimum=0.002, maximum=0.5)
    radius = round(radius_fraction * min(width, height))
    center_x, center_y = round(x * width), round(y * height)
    if (center_x - radius < 0 or center_y - radius < 0
            or center_x + radius > width or center_y + radius > height):
        raise HybridFigureError("circle overlay falls outside the canvas")
    stroke = _scaled_px(item.get("stroke_px_at_1536", 3), width,
                        "stroke_px_at_1536", minimum=1, maximum=40)
    draw.ellipse(
        (center_x - radius, center_y - radius,
         center_x + radius, center_y + radius),
        fill=item.get("fill"), outline=str(item.get("color", "#1A1A1A")),
        width=stroke,
    )


def _rectangle_bounds(item: dict[str, Any],
                      canvas: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = canvas
    x, y = _point(item)
    box_width = _number(item.get("width"), "width", minimum=0.001, maximum=1.0)
    box_height = _number(item.get("height"), "height", minimum=0.001, maximum=1.0)
    left, top = round(x * width), round(y * height)
    if x + box_width > 1.0 or y + box_height > 1.0:
        raise HybridFigureError("rectangle overlay falls outside the canvas")
    return (
        left, top, left + round(box_width * width), top + round(box_height * height))


def _draw_rectangle(draw, item: dict[str, Any], canvas: tuple[int, int]) -> None:
    width, _height = canvas
    stroke = _scaled_px(item.get("stroke_px_at_1536", 3), width,
                        "stroke_px_at_1536", minimum=1, maximum=40)
    bounds = _rectangle_bounds(item, canvas)
    draw.rectangle(
        bounds,
        fill=item.get("fill"), outline=str(item.get("color", "#1A1A1A")),
        width=stroke,
    )


def _draw_image_region(image, item: dict[str, Any], canvas: tuple[int, int],
                       base_directory: Path) -> dict[str, Any]:
    """Paste one canonical raster crop with uniform scaling only."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise HybridFigureError("Pillow is required for identity layers") from exc
    asset = item.get("asset")
    identity_key = item.get("identity_key")
    if not isinstance(asset, str) or not asset.strip():
        raise HybridFigureError("image_region requires a non-empty asset")
    if not isinstance(identity_key, str) or not identity_key.strip():
        raise HybridFigureError("image_region requires a non-empty identity_key")
    asset_path = Path(asset)
    if not asset_path.is_absolute():
        asset_path = base_directory / asset_path
    asset_path = asset_path.resolve()
    if not asset_path.is_file():
        raise HybridFigureError(f"image_region asset does not exist: {asset_path}")
    source_x = _number(item.get("source_x", 0), "source_x")
    source_y = _number(item.get("source_y", 0), "source_y")
    source_width = _number(
        item.get("source_width", 1), "source_width", minimum=0.001)
    source_height = _number(
        item.get("source_height", 1), "source_height", minimum=0.001)
    if source_x + source_width > 1 or source_y + source_height > 1:
        raise HybridFigureError("image_region source crop falls outside its asset")
    destination_x, destination_y = _point(item)
    scale = _number(item.get("scale", 1), "scale", minimum=0.05, maximum=4.0)
    with Image.open(asset_path) as source:
        rgba = source.convert("RGBA")
    source_box = (
        round(source_x * rgba.width),
        round(source_y * rgba.height),
        round((source_x + source_width) * rgba.width),
        round((source_y + source_height) * rgba.height),
    )
    crop = rgba.crop(source_box)
    output_size = (
        max(1, round(crop.width * scale)),
        max(1, round(crop.height * scale)),
    )
    if output_size != crop.size:
        crop = crop.resize(output_size, Image.Resampling.LANCZOS)
    left = round(destination_x * canvas[0])
    top = round(destination_y * canvas[1])
    if left + crop.width > canvas[0] or top + crop.height > canvas[1]:
        raise HybridFigureError("image_region destination falls outside the canvas")
    image.alpha_composite(crop, (left, top))
    return {
        "identity_key": identity_key.strip(),
        "asset": str(asset_path),
        "asset_sha256": sha256_file(asset_path),
        "source_box_px": list(source_box),
        "scale": scale,
        "destination_box_px": [left, top, left + crop.width, top + crop.height],
        "anisotropic_resize": False,
    }


def _pixel_variation(image) -> float:
    from PIL import ImageStat
    return float(ImageStat.Stat(image.convert("L")).stddev[0])


def _expected_overlay_text(spec: dict[str, Any]) -> list[str]:
    exact = spec.get("exact_text")
    if not isinstance(exact, list) or not exact or any(
            not isinstance(item, str) or not item.strip() for item in exact):
        raise HybridFigureError("hybrid figure spec requires exact_text")
    rendered = [item.strip() for item in exact]
    if spec.get("render_context", "article") in {"article", "slide"}:
        omitted = {
            str(spec.get("title") or "").strip(),
            str(spec.get("subtitle") or "").strip(),
        }
        rendered = [item for item in rendered if item not in omitted]
    generated = spec.get("generated_text", [])
    if not isinstance(generated, list) or any(
            not isinstance(item, str) or not item.strip() for item in generated):
        raise HybridFigureError("generated_text must be a string list")
    unexpected = [item for item in generated if item.strip() not in rendered]
    if unexpected:
        raise HybridFigureError(
            "generated_text contains copy absent from rendered exact_text: "
            + "; ".join(unexpected))
    generated_counts = Counter(item.strip() for item in generated)
    expected_counts = Counter(rendered)
    if generated_counts - expected_counts:
        raise HybridFigureError("generated_text repeats copy beyond exact_text")
    expected_counts.subtract(generated_counts)
    return list(expected_counts.elements())


def compose(base_path: str | Path, spec: dict[str, Any], output_path: str | Path,
            report_path: str | Path | None = None) -> dict[str, Any]:
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise HybridFigureError("Pillow is required for hybrid composition") from exc
    if spec.get("render_route") != "hybrid":
        raise HybridFigureError("hybrid compositor requires render_route=hybrid")
    overlay = spec.get("overlay")
    if not isinstance(overlay, dict):
        raise HybridFigureError("hybrid figure spec requires an overlay object")
    items = overlay.get("items")
    if not isinstance(items, list) or not items:
        raise HybridFigureError("overlay.items must be a non-empty list")
    expected_overlay_text = _expected_overlay_text(spec)
    supplied_overlay_text = [
        str(item.get("text")).strip()
        for item in items
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    if Counter(supplied_overlay_text) != Counter(expected_overlay_text):
        missing = list((Counter(expected_overlay_text) - Counter(supplied_overlay_text)).elements())
        extra = list((Counter(supplied_overlay_text) - Counter(expected_overlay_text)).elements())
        detail = []
        if missing:
            detail.append("missing " + "; ".join(repr(item) for item in missing))
        if extra:
            detail.append("unexpected " + "; ".join(repr(item) for item in extra))
        raise HybridFigureError(
            "overlay text must match the deterministic exact-text manifest: "
            + ", ".join(detail))
    base_path = Path(base_path).resolve()
    output_path = Path(output_path).resolve()
    if output_path.suffix.lower() != ".png":
        raise HybridFigureError("hybrid output must use a .png filename")
    style = _writing_style(spec)
    background_color = _style_background(spec, style)
    with Image.open(base_path) as source:
        rgba = source.convert("RGBA")
        alpha_extrema = rgba.getchannel("A").getextrema()
        alpha_composited = alpha_extrema != (255, 255)
        if alpha_composited:
            image = Image.new("RGBA", rgba.size, background_color)
            image.alpha_composite(rgba)
        else:
            image = rgba
    source_size = image.size
    source_aspect = source_size[0] / source_size[1]
    target_aspect = float(spec.get("target_aspect_ratio") or source_aspect)
    tolerance = float(spec.get("aspect_ratio_tolerance", 0.03))
    relative_error = abs(source_aspect / target_aspect - 1.0)
    if relative_error > tolerance:
        raise HybridFigureError(
            f"base aspect ratio {source_aspect:.4f} differs from target "
            f"{target_aspect:.4f} by {relative_error:.1%}; refusing to stretch")
    try:
        font = style["font"]
        family, fallback = str(font["family"]), str(font["fallback"])
    except (KeyError, TypeError) as exc:
        raise HybridFigureError("writing-style overlay is missing font policy") from exc
    draw = ImageDraw.Draw(image)
    font_records: list[dict[str, Any]] = []
    identity_layers: list[dict[str, Any]] = []
    opaque_masks: list[tuple[int, int, int, int]] = []
    mask_checks: list[dict[str, Any]] = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise HybridFigureError(f"overlay item {index} must be an object")
        kind = item.get("type")
        if kind not in ITEM_TYPES:
            raise HybridFigureError(
                f"overlay item {index} type must be one of: " + ", ".join(sorted(ITEM_TYPES)))
        if kind == "text":
            mask_checks.append(_draw_text(
                draw, item, source_size, family, fallback, font_records,
                opaque_masks=opaque_masks))
        elif kind == "line":
            _draw_line(draw, item, source_size, arrow=False)
        elif kind == "arrow":
            _draw_line(draw, item, source_size, arrow=True)
        elif kind == "circle":
            _draw_circle(draw, item, source_size)
        elif kind == "image_region":
            identity_layers.append(_draw_image_region(
                image, item, source_size, base_path.parent))
        else:
            _draw_rectangle(draw, item, source_size)
            if _fill_is_opaque(item.get("fill")):
                opaque_masks.append(_rectangle_bounds(item, source_size))

    identity_counts = Counter(
        item["identity_key"] for item in identity_layers)
    singletons = sorted(
        identity for identity, count in identity_counts.items() if count < 2)
    if singletons:
        raise HybridFigureError(
            "identity image regions must repeat each identity_key at least twice: "
            + ", ".join(singletons))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".png", dir=output_path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        image.convert("RGB").save(temporary, format="PNG", optimize=True)
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    with Image.open(output_path) as final:
        output_size = final.size
        variation = _pixel_variation(final)
    if output_size != source_size:
        raise HybridFigureError(
            f"hybrid output changed dimensions {source_size} -> {output_size}")
    if variation < 2.0:
        raise HybridFigureError("hybrid output is visually blank or near-blank")
    report = {
        "schema_version": 1,
        "base": str(base_path),
        "base_sha256": sha256_file(base_path),
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
        "source_size_px": list(source_size),
        "output_size_px": list(output_size),
        "source_aspect_ratio": round(source_aspect, 6),
        "target_aspect_ratio": round(target_aspect, 6),
        "anisotropic_resize": False,
        "alpha_composited": alpha_composited,
        "background_color": background_color,
        "pixel_variation_stddev": round(variation, 3),
        "overlay_items": len(items),
        "overlay_text_items": len(expected_overlay_text),
        "mask_checks": mask_checks,
        "fonts": font_records,
        "identity_layers": identity_layers,
        "identity_keys_verified": sorted(identity_counts),
        "status": "pass",
    }
    if report_path:
        atomic_write_json(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="generated base PNG/JPEG/WebP")
    parser.add_argument("--spec", required=True, help="figure specification JSON")
    parser.add_argument("--out", required=True, help="final composed PNG")
    parser.add_argument("--report", help="write composition provenance JSON")
    args = parser.parse_args(argv)
    try:
        result = compose(args.base, _load_json(args.spec), args.out, args.report)
    except (OSError, json.JSONDecodeError, HybridFigureError) as exc:
        print(f"Hybrid composition failed: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
