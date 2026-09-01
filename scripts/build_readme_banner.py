#!/usr/bin/env python3
"""Compose the README hero banner from real example PDF pages.

Repo tooling, not part of the shipped skill: this is deliberately absent from
the ``build_release_skill.py`` allowlist.

The committed banner is the ``fan`` preset at its default width; ``band`` is a
tighter page-tops alternative. Regenerate whenever ``examples/*.pdf`` change::

    python3 scripts/build_readme_banner.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"

# Back-to-front: each fan is drawn outside-in so the hero page lands on top.
# (pdf stem, page number, rotation degrees, x offset, y offset, scale)
PRESETS = {
    # Whole pages, wide fan: reads as "a stack of finished journal articles".
    "fan": {
        "page_height": 900,
        "crop": 1.0,
        "layout": (
            ("seed-oils", 1, -7.5, -1180, 70, 0.86),
            ("school-smartphone-bans", 1, 7.5, 1180, 70, 0.86),
            ("microplastics-health-eli5", 1, -4.0, -640, 18, 0.93),
            ("ozempic-after-stopping", 2, 4.0, 640, 18, 0.93),
            ("ozempic-after-stopping", 1, 0.0, 0, 0, 1.0),
        ),
    },
    # Page tops only: mastheads, titles and metadata rows stay legible at the
    # ~900px README column width.
    "band": {
        "page_height": 1180,
        "crop": 0.52,
        "layout": (
            ("seed-oils", 1, -3.0, -1300, 34, 0.92),
            ("school-smartphone-bans", 1, 3.0, 1300, 34, 0.92),
            ("microplastics-health-eli5", 1, -1.5, -660, 10, 0.96),
            ("ozempic-after-stopping", 2, 1.5, 660, 10, 0.96),
            ("ozempic-after-stopping", 1, 0.0, 0, 0, 1.0),
        ),
    },
}

BORDER = (214, 214, 214, 255)
SHADOW_BLUR = 22
SHADOW_OFFSET = (0, 14)
SHADOW_ALPHA = 90
MARGIN = 90


def render_page(pdf: Path, page: int, dpi: int, workdir: Path) -> Image.Image:
    prefix = workdir / f"{pdf.stem}-{page}"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page),
         str(pdf), str(prefix)],
        check=True,
    )
    matches = sorted(workdir.glob(f"{pdf.stem}-{page}-*.png"))
    if not matches:
        raise SystemExit(f"pdftoppm produced no page for {pdf.name} p{page}")
    return Image.open(matches[0]).convert("RGB")


def framed(page: Image.Image, height: int, crop: float) -> Image.Image:
    if crop < 1.0:
        page = page.crop((0, 0, page.width, round(page.height * crop)))
    width = round(page.width * height / page.height)
    page = page.resize((width, height), Image.LANCZOS).convert("RGBA")
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 0, page.width - 1, page.height - 1), outline=BORDER, width=2)
    return page


def with_shadow(card: Image.Image, angle: float) -> tuple[Image.Image, Image.Image]:
    """Return (rotated card, rotated shadow) sharing one coordinate frame."""
    pad = SHADOW_BLUR * 3
    frame = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    frame.paste(card, (pad, pad))

    silhouette = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    silhouette.paste(
        Image.new("RGBA", card.size, (15, 18, 24, SHADOW_ALPHA)),
        (pad + SHADOW_OFFSET[0], pad + SHADOW_OFFSET[1]),
    )
    silhouette = silhouette.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))

    rotate = dict(resample=Image.BICUBIC, expand=True)
    return frame.rotate(angle, **rotate), silhouette.rotate(angle, **rotate)


def build(preset: str, dpi: int, max_width: int, out: Path) -> None:
    spec = PRESETS[preset]
    page_height, crop = spec["page_height"], spec["crop"]
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        cards = []
        for stem, page, angle, dx, dy, scale in spec["layout"]:
            pdf = EXAMPLES / f"{stem}.pdf"
            if not pdf.exists():
                raise SystemExit(f"missing example PDF: {pdf}")
            card = framed(render_page(pdf, page, dpi, workdir),
                          round(page_height * crop * scale), crop)
            cards.append((with_shadow(card, angle), dx, dy))

    # Size the canvas to whatever the fan actually occupies.
    boxes = []
    for (rotated, _shadow), dx, dy in cards:
        boxes.append((dx - rotated.width // 2, dy - rotated.height // 2,
                      dx + rotated.width // 2, dy + rotated.height // 2))
    left = min(b[0] for b in boxes) - MARGIN
    top = min(b[1] for b in boxes) - MARGIN
    right = max(b[2] for b in boxes) + MARGIN
    bottom = max(b[3] for b in boxes) + MARGIN

    canvas = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    for (rotated, shadow), dx, dy in cards:
        origin = (dx - rotated.width // 2 - left, dy - rotated.height // 2 - top)
        canvas.alpha_composite(shadow, origin)
        canvas.alpha_composite(rotated, origin)

    if max_width and canvas.width > max_width:
        canvas = canvas.resize(
            (max_width, round(canvas.height * max_width / canvas.width)), Image.LANCZOS)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, optimize=True)
    print(f"wrote {out} ({canvas.width}x{canvas.height})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(PRESETS), default="fan")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--max-width", type=int, default=1800,
                        help="downscale the finished banner to this width (0 keeps full size)")
    parser.add_argument("--out", type=Path, default=REPO / "assets" / "grounded-banner.png")
    args = parser.parse_args(argv)
    build(args.preset, args.dpi, args.max_width, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
