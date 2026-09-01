#!/usr/bin/env python3
"""Normalize a figure's border-connected paper to opaque exact white.

Only near-white pixels connected to the canvas edge are changed.  The tool
therefore removes generator paper tints without recolouring isolated subject
highlights.  It fails when the required five-percent white safety band remains
occupied, because that is a composition problem that should be regenerated or
re-laid out rather than erased.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from collections import deque
from pathlib import Path


class CanvasNormalizationError(ValueError):
    """Raised when a raster cannot be normalized without changing content."""


def _is_near_white(pixel: tuple[int, int, int], threshold: int,
                   maximum_chroma: int) -> bool:
    return min(pixel) >= threshold and max(pixel) - min(pixel) <= maximum_chroma


def normalize_canvas(
    source_path: str | Path,
    output_path: str | Path,
    *,
    threshold: int = 244,
    maximum_chroma: int = 14,
    safety_band_fraction: float = 0.05,
) -> dict[str, int | float | str]:
    """Flatten *source_path* and whiten only edge-connected near-white paper."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise CanvasNormalizationError("Pillow is required") from exc
    if not 0 <= threshold <= 255:
        raise CanvasNormalizationError("threshold must be between 0 and 255")
    if not 0 <= maximum_chroma <= 255:
        raise CanvasNormalizationError("maximum_chroma must be between 0 and 255")
    if not 0 < safety_band_fraction <= 0.25:
        raise CanvasNormalizationError(
            "safety_band_fraction must be greater than 0 and at most 0.25")

    source = Path(source_path).resolve()
    output = Path(output_path).resolve()
    if output.suffix.lower() != ".png":
        raise CanvasNormalizationError("normalized output must be a PNG")
    with Image.open(source) as opened:
        rgba = opened.convert("RGBA")
        flattened = Image.new("RGBA", rgba.size, "white")
        flattened.alpha_composite(rgba)
        image = flattened.convert("RGB")

    width, height = image.size
    pixels = image.load()
    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()
    for x in range(width):
        queue.append((x, 0))
        if height > 1:
            queue.append((x, height - 1))
    for y in range(1, max(1, height - 1)):
        queue.append((0, y))
        if width > 1:
            queue.append((width - 1, y))

    changed = 0
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if not _is_near_white(pixels[x, y], threshold, maximum_chroma):
            continue
        if pixels[x, y] != (255, 255, 255):
            pixels[x, y] = (255, 255, 255)
            changed += 1
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))

    band = max(1, round(min(width, height) * safety_band_fraction))
    occupied = 0
    total = 0
    for y in range(height):
        for x in range(width):
            if x < band or x >= width - band or y < band or y >= height - band:
                total += 1
                occupied += pixels[x, y] != (255, 255, 255)
    if occupied:
        raise CanvasNormalizationError(
            f"{occupied} of {total} safety-band pixels remain non-white; "
            "move the composition inward or regenerate it")

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".png", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        image.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "input": str(source),
        "output": str(output),
        "width_px": width,
        "height_px": height,
        "pixels_whitened": changed,
        "safety_band_fraction": safety_band_fraction,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--threshold", type=int, default=244)
    parser.add_argument("--maximum-chroma", type=int, default=14)
    parser.add_argument("--safety-band-fraction", type=float, default=0.05)
    args = parser.parse_args()
    report = normalize_canvas(
        args.source, args.output, threshold=args.threshold,
        maximum_chroma=args.maximum_chroma,
        safety_band_fraction=args.safety_band_fraction)
    print(
        f"normalized {report['pixels_whitened']} paper pixels; "
        f"wrote {report['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
