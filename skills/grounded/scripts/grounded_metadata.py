"""Shared package identity for network clients and release tooling."""

from pathlib import Path


NAME = "grounded"
REPOSITORY_URL = "https://github.com/jostelzer/grounded"

# Canonical journal-PDF layout geometry, shared by the exporter (which
# enforces it in CSS) and figure QA (which must evaluate label legibility at
# the width a figure will actually render at). A4 210mm minus 13mm margins on
# each side; figures are height-capped and scale down proportionally, so a
# figure taller than PAGE_CONTENT_WIDTH_MM / FIGURE_MAX_HEIGHT_MM (~2:1)
# renders narrower than the full content width.
PAGE_CONTENT_WIDTH_MM = 184.0
FIGURE_MAX_HEIGHT_MM = 92.0


def rendered_figure_size_mm(
    pixel_width: int, pixel_height: int,
    max_height_mm: float = FIGURE_MAX_HEIGHT_MM,
    content_width_mm: float = PAGE_CONTENT_WIDTH_MM,
) -> tuple[float, float]:
    """Return (width_mm, height_mm) a figure raster renders at on the page.

    Mirrors the exporter's CSS: `width: 100%; height: auto; max-height: <cap>;
    object-fit: contain` — full content width unless the height cap forces a
    proportional scale-down.
    """
    if pixel_width <= 0 or pixel_height <= 0:
        raise ValueError("figure pixel dimensions must be positive")
    aspect = pixel_width / pixel_height
    height = min(content_width_mm / aspect, max_height_mm)
    return (height * aspect, height)


def version() -> str:
    value = (
        (Path(__file__).resolve().parents[1] / "VERSION")
        .read_text(encoding="utf-8")
        .strip()
    )
    if not value or any(character.isspace() for character in value):
        raise RuntimeError("VERSION must contain one non-empty version token")
    return value.removeprefix("v")


def user_agent(*, mailto: str | None = None, qualifier: str | None = None) -> str:
    product = f"{NAME}/{version()}"
    if qualifier:
        product += f" {qualifier}"
    contact = f"; mailto:{mailto.strip()}" if mailto and mailto.strip() else ""
    return f"{product} (+{REPOSITORY_URL}{contact})"
