#!/usr/bin/env python3
"""Shared font discovery and loading for deterministic Grounded artwork."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FigureTypographyError(ValueError):
    """Raised when a requested publication font cannot be loaded safely."""


def _fontconfig_path(family: str, bold: bool) -> Path | None:
    executable = shutil.which("fc-match")
    if not executable:
        return None
    query = family + (":style=Bold" if bold else ":style=Regular")
    completed = subprocess.run(
        [executable, "-f", "%{file}", query], check=False,
        capture_output=True, text=True, timeout=15,
    )
    path = Path(completed.stdout.strip()) if completed.returncode == 0 else None
    return path if path and path.is_file() else None


def font_candidates(family: str, bold: bool) -> list[Path]:
    """Return platform and bundled candidates in preference order."""
    suffix = " Bold" if bold else ""
    filenames = {
        "Arial": f"Arial{suffix}.ttf",
        "Helvetica Neue": "HelveticaNeue.ttc",
        "Helvetica": "Helvetica.ttc",
        "Optima": "Optima.ttc",
        "Seravek": "Seravek.ttc",
    }
    candidates: list[Path] = []
    if family in filenames:
        candidates.extend([
            Path("/System/Library/Fonts") / filenames[family],
            Path("/System/Library/Fonts/Supplemental") / filenames[family],
            Path("/Library/Fonts/Microsoft") / filenames[family],
        ])
    matched = _fontconfig_path(family, bold)
    if matched:
        candidates.append(matched)
    candidates.append(
        ROOT / "assets" / "fonts" /
        ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))
    return candidates


def resolve_font_path(
    family: str, bold: bool, explicit: str | None = None,
) -> Path:
    """Resolve an upright regular or bold font without synthetic styling."""
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FigureTypographyError(f"font file does not exist: {path}")
        return path
    for candidate in font_candidates(family, bold):
        if candidate.is_file():
            return candidate.resolve()
    raise FigureTypographyError(f"no usable font found for {family}")


def load_font_face(path: Path, size: int, bold: bool):
    """Load an upright face from a TTF/OTF or multi-face TTC collection."""
    try:
        from PIL import ImageFont
    except ImportError as exc:
        raise FigureTypographyError(
            "Pillow is required for deterministic figure typography") from exc
    candidates = []
    for index in range(64):
        try:
            face = ImageFont.truetype(str(path), size=size, index=index)
        except OSError:
            break
        _family, style = face.getname()
        normalized = style.lower()
        if bold and "bold" in normalized and "italic" not in normalized:
            return face, index, style
        if not bold and normalized == "regular":
            return face, index, style
        candidates.append((face, index, style))
        if path.suffix.lower() not in {".ttc", ".otc"}:
            break
    if bold:
        for face, index, style in candidates:
            if "medium" in style.lower() and "italic" not in style.lower():
                return face, index, style
    else:
        for face, index, style in candidates:
            normalized = style.lower()
            if "italic" not in normalized and "condensed" not in normalized:
                return face, index, style
    raise FigureTypographyError(
        f"font {path} has no {'bold' if bold else 'regular'} upright face")
