#!/usr/bin/env python3
"""Deterministic, browser-free PDF renderer for Grounded reviews.

The public entry point is :func:`write_pdf`.  It consumes the finished Markdown
that ``format_references.py`` emits and composes the PDF directly with ReportLab.
No HTML engine, browser, network access, shell command, or system font is used.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import html
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Iterable


ACCENT_HEX = "#ff4f1f"
INK_HEX = "#141414"
MUTED_HEX = "#666666"
FAINT_HEX = "#929292"
RULE_HEX = "#dddddd"

REQUIRED_REPORTLAB = "4.4.9"
REQUIRED_PILLOW = "12.3.0"
REQUIRED_PYPDF = "6.10.0"
SUPPORTED_RASTER = {".png", ".jpg", ".jpeg", ".webp"}


class PdfRuntimeError(RuntimeError):
    """Raised when the canonical PDF runtime is absent or incompatible."""


class PdfInputError(ValueError):
    """Raised when an input review cannot be rendered safely."""


def _display_date(value: _datetime.date, *, abbreviated: bool = False) -> str:
    """Format dates consistently on platforms without the ``%-d`` directive."""
    month = value.strftime("%b" if abbreviated else "%B")
    return f"{value.day} {month} {value.year}"


def require_runtime() -> dict[str, str]:
    """Load and validate the sole supported PDF runtime."""
    try:
        import reportlab
        import PIL
        import pypdf
    except ImportError as exc:
        raise PdfRuntimeError(
            "Grounded PDF export requires the pinned packages in "
            "requirements-pdf.txt. Install them into the active Python "
            "environment; the exporter never falls back to a browser."
        ) from exc
    versions = {
        "reportlab": reportlab.Version,
        "pillow": PIL.__version__,
        "pypdf": pypdf.__version__,
    }
    required = {
        "reportlab": REQUIRED_REPORTLAB,
        "pillow": REQUIRED_PILLOW,
        "pypdf": REQUIRED_PYPDF,
    }
    mismatches = [
        f"{name} {versions[name]} (required {required[name]})"
        for name in required if versions[name] != required[name]
    ]
    if mismatches:
        raise PdfRuntimeError(
            "Grounded PDF export/QA requires the exact deterministic runtime: "
            + ", ".join(mismatches)
        )
    return versions


@dataclass
class Block:
    kind: str
    text: str = ""
    items: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    figure_id: str = ""
    figure_number: int = 0
    image: str = ""
    alt: str = ""
    caption_title: str = ""
    caption_tail: str = ""
    caption_items: list[str] = field(default_factory=list)


@dataclass
class ReviewDocument:
    title: str
    lead_label: str | None
    lead_text: str | None
    blocks: list[Block]


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_review(markdown: str) -> ReviewDocument:
    """Parse the deliberately narrow Markdown dialect emitted by Grounded."""
    lines = markdown.splitlines()
    blocks: list[Block] = []
    title = "Scientific review"
    lead_label = None
    lead_text = None
    pending_figure_id = None
    seen_title = False
    figure_ids: list[str] = []
    i = 0

    while i < len(lines):
        raw = lines[i]
        text = raw.strip()
        if not text:
            i += 1
            continue

        anchor = re.fullmatch(r'<a id="(fig-[a-z][a-z0-9-]*)"></a>', text)
        if anchor:
            if pending_figure_id is not None:
                raise PdfInputError("figure anchor is not followed by a figure")
            pending_figure_id = anchor.group(1)
            i += 1
            continue

        if text.startswith("## ") or text.startswith("# "):
            heading = text[3:] if text.startswith("## ") else text[2:]
            if not seen_title:
                title = heading
                seen_title = True
            else:
                blocks.append(Block("heading", text=heading))
            i += 1
            continue

        if text.startswith("### "):
            blocks.append(Block("heading", text=text[4:]))
            i += 1
            continue

        if text == "**Sources**":
            blocks.append(Block("sources"))
            i += 1
            continue

        lead = re.match(r"^\*\*(TL;DR|Abstract)\*\*\s*[—–-]?\s*(.*)$", text)
        if lead and lead_text is None:
            lead_label = lead.group(1)
            lead_text = lead.group(2)
            i += 1
            continue

        if text.startswith(">"):
            blocks.append(Block("note", text=text.lstrip("> ").strip()))
            i += 1
            continue

        figure = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", text)
        if figure:
            figure_id = pending_figure_id or f"figure-{len(figure_ids) + 1}"
            pending_figure_id = None
            figure_ids.append(figure_id)
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            caption_line = lines[i].strip() if i < len(lines) else ""
            match = re.match(r"^\*\*Figure\s+(\d+)\.\s*(.+?)\*\*(\s+.+)?$", caption_line)
            if not match:
                raise PdfInputError(
                    "every figure must have a numbered caption immediately after it"
                )
            expected_number = len(figure_ids)
            if int(match.group(1)) != expected_number:
                raise PdfInputError("figure caption numbering does not match figure order")
            i += 1
            caption_items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                caption_items.append(lines[i].strip()[2:])
                i += 1
            caption_payload = "\n".join([caption_line, *caption_items])
            if not match.group(3) and not caption_items:
                raise PdfInputError("every figure caption must explain the figure")
            if "https://doi.org/" not in caption_payload.lower():
                raise PdfInputError("every figure caption must contain a DOI citation")
            blocks.append(Block(
                "figure",
                figure_id=figure_id,
                figure_number=expected_number,
                image=figure.group(2),
                alt=figure.group(1),
                caption_title=match.group(2),
                caption_tail=(match.group(3) or "").strip(),
                caption_items=caption_items,
            ))
            continue

        if pending_figure_id is not None:
            raise PdfInputError("figure anchor is not followed by a figure")

        if (text.startswith("|") and i + 1 < len(lines)
                and re.fullmatch(r"\|[\s:|-]+\|", lines[i + 1].strip())):
            headers = _split_row(text)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append(Block("table", headers=headers, rows=rows))
            continue

        if text.startswith("- ") or text.startswith("* "):
            items = []
            while i < len(lines):
                item = lines[i].strip()
                if not (item.startswith("- ") or item.startswith("* ")):
                    break
                items.append(item[2:])
                i += 1
            blocks.append(Block("bullets", items=items))
            continue

        paragraph = [text]
        i += 1
        while i < len(lines) and lines[i].strip():
            paragraph.append(lines[i].strip())
            i += 1
        blocks.append(Block("paragraph", text=" ".join(paragraph)))

    if pending_figure_id is not None:
        raise PdfInputError("figure anchor is not followed by a figure")
    for figure_id in figure_ids:
        if f"](#{figure_id})" not in markdown:
            raise PdfInputError(
                f"every figure must be referenced from the text: {figure_id}"
            )
    return ReviewDocument(title, lead_label, lead_text, blocks)


def _rich_text(value: str) -> str:
    """Convert Grounded inline Markdown to safe ReportLab paragraph markup."""
    value = html.escape(value, quote=False)

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = html.escape(match.group(2), quote=True)
        return f'<link href="{href}" color="{INK_HEX}"><u>{label}</u></link>'

    value = re.sub(
        r"\[([^\]]+)\]\((https?://(?:[^\s()]|\([^\s()]*\))+|#[A-Za-z][A-Za-z0-9_-]*)\)",
        link,
        value,
    )
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<i>\1</i>", value)
    value = re.sub(r"`([^`]+)`", r'<font name="GroundedMono">\1</font>', value)

    def bare_url(match: re.Match[str]) -> str:
        url = match.group(1)
        href = html.escape(url, quote=True)
        return f'<link href="{href}" color="{MUTED_HEX}">{url}</link>'

    value = re.sub(r'(?<!["=>])(https?://[^\s<]+)(?![^<]*</link>)', bare_url, value)
    return value


def _safe_asset_path(source: str, base_dir: str) -> str:
    if re.match(r"^[a-z]+://", source, re.I):
        raise PdfInputError(f"remote figure assets are forbidden in PDF export: {source}")
    base = os.path.realpath(base_dir)
    path = os.path.realpath(source if os.path.isabs(source) else os.path.join(base, source))
    try:
        inside = os.path.commonpath([base, path]) == base
    except ValueError:
        inside = False
    if not inside:
        raise PdfInputError(f"figure asset escapes the review directory: {source}")
    if not os.path.isfile(path):
        raise PdfInputError(f"figure asset does not exist: {source}")
    extension = os.path.splitext(path)[1].lower()
    if extension == ".svg":
        companion = os.path.splitext(path)[0] + "-pdf.png"
        if not os.path.isfile(companion):
            raise PdfInputError(
                f"SVG figure needs a deterministic PDF companion PNG: {companion}"
            )
        path = companion
        extension = ".png"
    if extension not in SUPPORTED_RASTER:
        raise PdfInputError(f"unsupported PDF figure format: {source}")
    return path


def _register_fonts(repo_dir: str) -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fonts = {
        "GroundedSans": "DejaVuSans.ttf",
        "GroundedSans-Bold": "DejaVuSans-Bold.ttf",
        "GroundedSans-Italic": "DejaVuSans-Oblique.ttf",
        "GroundedSerif": "DejaVuSerif.ttf",
        "GroundedSerif-Bold": "DejaVuSerif-Bold.ttf",
        "GroundedSerif-Italic": "DejaVuSerif-Italic.ttf",
        "GroundedMono": "DejaVuSansMono.ttf",
    }
    font_dir = os.path.join(repo_dir, "assets", "fonts")
    missing = [name for name in fonts.values()
               if not os.path.isfile(os.path.join(font_dir, name))]
    if missing:
        raise PdfRuntimeError(
            "Grounded's bundled PDF fonts are incomplete: " + ", ".join(missing)
        )
    for family, filename in fonts.items():
        if family not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(family, os.path.join(font_dir, filename)))
    pdfmetrics.registerFontFamily(
        "GroundedSans", normal="GroundedSans", bold="GroundedSans-Bold",
        italic="GroundedSans-Italic", boldItalic="GroundedSans-Bold",
    )
    pdfmetrics.registerFontFamily(
        "GroundedSerif", normal="GroundedSerif", bold="GroundedSerif-Bold",
        italic="GroundedSerif-Italic", boldItalic="GroundedSerif-Bold",
    )


def _styles():
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor

    ink = HexColor(INK_HEX)
    muted = HexColor(MUTED_HEX)
    faint = HexColor(FAINT_HEX)
    return {
        "provenance": ParagraphStyle(
            "provenance", fontName="GroundedSans-Bold", fontSize=5.8,
            leading=7.2, textColor=faint, spaceAfter=8, alignment=TA_LEFT,
        ),
        "kicker": ParagraphStyle(
            "kicker", fontName="GroundedSans-Bold", fontSize=7.2,
            leading=8.5, textColor=HexColor(ACCENT_HEX), spaceAfter=5,
            alignment=TA_LEFT,
        ),
        "title": ParagraphStyle(
            "title", fontName="GroundedSans", fontSize=23, leading=25,
            textColor=ink, spaceAfter=10, alignment=TA_LEFT,
        ),
        "lead": ParagraphStyle(
            "lead", fontName="GroundedSans", fontSize=9.2, leading=12.4,
            textColor=ink, spaceAfter=10, alignment=TA_LEFT,
        ),
        "lead_label": ParagraphStyle(
            "lead_label", fontName="GroundedSans-Bold", fontSize=5.8,
            leading=7, textColor=faint, spaceAfter=2, alignment=TA_LEFT,
        ),
        "heading": ParagraphStyle(
            "heading", fontName="GroundedSans-Bold", fontSize=8.7,
            leading=11, textColor=ink, spaceBefore=7, spaceAfter=3,
            keepWithNext=True, alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "body", fontName="GroundedSerif", fontSize=8.6, leading=12.1,
            textColor=ink, spaceAfter=5.3, alignment=TA_JUSTIFY,
            allowWidows=0, allowOrphans=0,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="GroundedSerif", fontSize=8.6, leading=12.1,
            textColor=ink, alignment=TA_LEFT,
        ),
        "note": ParagraphStyle(
            "note", fontName="GroundedSans", fontSize=6.5, leading=8.2,
            textColor=muted, spaceAfter=5, alignment=TA_LEFT,
        ),
        "caption": ParagraphStyle(
            "caption", fontName="GroundedSans", fontSize=6.7, leading=8.6,
            textColor=muted, spaceBefore=4, spaceAfter=0, alignment=TA_LEFT,
        ),
        "ref": ParagraphStyle(
            "ref", fontName="GroundedSans", fontSize=6.25, leading=8.15,
            textColor=HexColor("#333333"), spaceAfter=4.2, alignment=TA_LEFT,
            allowWidows=0, allowOrphans=0,
        ),
        "ref_heading": ParagraphStyle(
            "ref_heading", fontName="GroundedSans-Bold", fontSize=8.5,
            leading=10, textColor=ink, alignment=TA_LEFT,
        ),
        "table_head": ParagraphStyle(
            "table_head", fontName="GroundedSans-Bold", fontSize=6.1,
            leading=7.5, textColor=ink, alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", fontName="GroundedSans", fontSize=6.5,
            leading=8.2, textColor=ink, alignment=TA_LEFT,
        ),
        "meta": ParagraphStyle(
            "meta", fontName="GroundedSans", fontSize=7.8, leading=9,
            textColor=ink, alignment=TA_LEFT,
        ),
        "meta_label": ParagraphStyle(
            "meta_label", fontName="GroundedSans-Bold", fontSize=5.1,
            leading=6.2, textColor=faint, alignment=TA_LEFT,
        ),
        "right_small": ParagraphStyle(
            "right_small", fontName="GroundedSans-Bold", fontSize=5.5,
            leading=7, textColor=faint, alignment=TA_RIGHT,
        ),
    }


class _FigureFlowable:
    """Factory namespace kept out of module import when ReportLab is absent."""

    @staticmethod
    def create(block: Block, base_dir: str, styles, page_width: float,
               page_height: float):
        from PIL import Image as PillowImage
        from reportlab.platypus import Flowable, Paragraph

        path = _safe_asset_path(block.image, base_dir)
        with PillowImage.open(path) as image:
            pixels = image.width * image.height
            if pixels > 80_000_000:
                raise PdfInputError(
                    f"figure exceeds the 80-megapixel safety limit: {block.image}"
                )
            pixel_width, pixel_height = image.width, image.height

        caption_bits = [
            f'<b>Figure {block.figure_number}. {_rich_text(block.caption_title)}</b>'
        ]
        if block.caption_tail:
            caption_bits.append(" " + _rich_text(block.caption_tail))
        if block.caption_items:
            caption_bits.extend("<br/>• " + _rich_text(item)
                                for item in block.caption_items)
        caption = Paragraph("".join(caption_bits), styles["caption"])

        class Figure(Flowable):
            def __init__(self):
                super().__init__()
                self.path = path
                self.ratio = pixel_height / float(pixel_width)
                self.draw_width = 0
                self.draw_height = 0
                self.caption_height = 0

            def wrap(self, available_width, available_height):
                _, caption_height = caption.wrap(available_width, available_height)
                desired_width = min(available_width, page_width)
                desired_height = desired_width * self.ratio
                maximum_height = min(page_height * 0.68,
                                     available_height - caption_height - 6)
                if maximum_height < 150 and desired_height + caption_height > available_height:
                    return available_width, available_height + 1
                self.draw_height = min(desired_height, maximum_height)
                self.draw_width = self.draw_height / self.ratio
                self.caption_height = caption_height
                self.width = available_width
                self.height = self.draw_height + caption_height + 6
                return self.width, self.height

            def draw(self):
                x = (self.width - self.draw_width) / 2
                y = self.caption_height + 6
                self.canv.bookmarkPage(block.figure_id)
                self.canv.drawImage(
                    self.path, x, y, width=self.draw_width, height=self.draw_height,
                    preserveAspectRatio=True, anchor="c", mask="auto",
                )
                caption.drawOn(self.canv, 0, 0)

        return Figure()


def _metadata_table(reference_count: int, token_count: int, compiled_date,
                    styles, width: float):
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph, Table, TableStyle

    token_text = f"≈{token_count / 1000:.1f}k" if token_count >= 1000 else f"≈{token_count}"
    values = [
        ("REFERENCES", f'<font color="{ACCENT_HEX}"><b>{reference_count}</b></font> verified'),
        ("TOKENS", token_text),
        ("VERIFICATION", "Crossref"),
        ("COMPILED", _display_date(compiled_date, abbreviated=True)),
    ]
    data = [[
        [Paragraph(label, styles["meta_label"]), Paragraph(value, styles["meta"])]
        for label, value in values
    ]]
    table = Table(data, colWidths=[width / 4] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, HexColor(INK_HEX)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, HexColor(INK_HEX)),
        ("LINEBEFORE", (1, 0), (-1, 0), 0.35, HexColor(RULE_HEX)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _review_table(block: Block, styles, width: float):
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph, Table, TableStyle

    count = len(block.headers)
    if not count or any(len(row) != count for row in block.rows):
        raise PdfInputError("table rows do not match the header width")
    data = [[Paragraph(_rich_text(cell), styles["table_head"])
             for cell in block.headers]]
    data.extend([
        [Paragraph(_rich_text(cell), styles["table_cell"]) for cell in row]
        for row in block.rows
    ])
    table = Table(data, colWidths=[width / count] * count, repeatRows=1,
                  splitByRow=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.7, HexColor(INK_HEX)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.45, HexColor(INK_HEX)),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, HexColor(RULE_HEX)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.7, HexColor(INK_HEX)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _regular_flowables(blocks: Iterable[Block], styles, section_start: int = 0):
    from reportlab.platypus import ListFlowable, ListItem, Paragraph

    flowables = []
    section = section_start
    for block in blocks:
        if block.kind == "heading":
            section += 1
            heading = (
                f'<font color="{ACCENT_HEX}">{section:02d}</font>&nbsp;&nbsp;'
                f'{_rich_text(block.text)}'
            )
            flowables.append(Paragraph(heading, styles["heading"]))
        elif block.kind == "paragraph":
            flowables.append(Paragraph(_rich_text(block.text), styles["body"]))
        elif block.kind == "note":
            flowables.append(Paragraph(_rich_text(block.text), styles["note"]))
        elif block.kind == "bullets":
            items = [ListItem(Paragraph(_rich_text(item), styles["bullet"]),
                              leftIndent=7)
                     for item in block.items]
            flowables.append(ListFlowable(
                items, bulletType="bullet", start="circle", bulletFontName="GroundedSans",
                bulletFontSize=5, leftIndent=11, bulletOffsetY=1.4, spaceAfter=5,
            ))
        else:
            raise PdfInputError(f"unexpected regular block: {block.kind}")
    return flowables, section


def _build_story(document: ReviewDocument, markdown: str, base_dir: str,
                 columns: int, kicker: str, release: str, repo_label: str,
                 compiled_date, frame_width: float, frame_height: float,
                 colophon: str | None):
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        BalancedColumns, HRFlowable, Paragraph, Spacer,
    )

    styles = _styles()
    reference_count = len({
        re.sub(r"[).,;*_]+$", "", value.lower())
        for value in re.findall(r"https?://doi\.org/([^\s<>]+)", markdown)
    })
    token_count = max(1, round(len(markdown) / 4))
    provenance = (
        "AGENTICALLY GENERATED SCIENTIFIC REVIEW&nbsp;&nbsp;·&nbsp;&nbsp;"
        f'<font color="{ACCENT_HEX}">GROUNDED</font> {html.escape(release)}'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;{html.escape(repo_label)}'
    )
    story = [
        Paragraph(provenance, styles["provenance"]),
        Paragraph(html.escape(kicker.upper()), styles["kicker"]),
        Paragraph(_rich_text(document.title), styles["title"]),
        _metadata_table(reference_count, token_count, compiled_date, styles, frame_width),
        Spacer(1, 9),
    ]
    if document.lead_text:
        label = "ABSTRACT" if document.lead_label == "Abstract" else "SUMMARY"
        story.extend([
            Paragraph(label, styles["lead_label"]),
            Paragraph(_rich_text(document.lead_text), styles["lead"]),
        ])

    section = 0
    regular: list[Block] = []
    references: list[Block] = []
    in_references = False

    def flush_regular():
        nonlocal regular, section
        if not regular:
            return
        flows, section = _regular_flowables(regular, styles, section)
        if columns == 2:
            story.append(BalancedColumns(
                flows, nCols=2, needed=48, innerPadding=14,
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                spaceAfter=5, name=f"body-{len(story)}",
            ))
        else:
            story.extend(flows)
        regular = []

    for block in document.blocks:
        if block.kind == "sources":
            flush_regular()
            in_references = True
            continue
        if in_references:
            if block.kind != "paragraph":
                raise PdfInputError("references must be plain paragraphs")
            references.append(block)
            continue
        if block.kind in {"heading", "paragraph", "note", "bullets"}:
            regular.append(block)
            continue
        flush_regular()
        if block.kind == "table":
            story.extend([Spacer(1, 3), _review_table(block, styles, frame_width), Spacer(1, 6)])
        elif block.kind == "figure":
            story.extend([
                Spacer(1, 4),
                _FigureFlowable.create(
                    block, base_dir, styles, frame_width, frame_height,
                ),
                Spacer(1, 7),
            ])
        else:
            raise PdfInputError(f"unknown review block: {block.kind}")
    flush_regular()

    if references:
        reference_label = (
            f'<b>References</b><font color="{FAINT_HEX}">'
            f'&nbsp;&nbsp;&nbsp;{reference_count} · VERIFIED VIA CROSSREF</font>'
        )
        story.extend([
            Spacer(1, 6),
            HRFlowable(width="100%", thickness=0.7, color=HexColor(INK_HEX),
                       spaceBefore=0, spaceAfter=5),
            Paragraph(reference_label, styles["ref_heading"]),
            Spacer(1, 4),
        ])
        ref_flows = [Paragraph(_rich_text(block.text), styles["ref"])
                     for block in references]
        if columns == 2:
            story.append(BalancedColumns(
                ref_flows, nCols=2, needed=36, innerPadding=14,
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                name="references",
            ))
        else:
            story.extend(ref_flows)

    story.extend([
        Spacer(1, 5),
        Paragraph(
            _rich_text(colophon) if colophon else (
                "AGENTICALLY GENERATED · EVERY CITATION RESOLVED AND "
                "RETRACTION-SCREENED VIA CROSSREF"
            ),
            styles["right_small"],
        ),
    ])
    return story


def _canvas_class(title: str, release: str, compiled_date):
    from reportlab.pdfgen import canvas as canvas_module

    class NumberedCanvas(canvas_module.Canvas):
        def __init__(self, *args, **kwargs):
            # BaseDocTemplate passes ``invariant=None`` by default.  Overwrite it
            # explicitly so PDF IDs, timestamps, and object ordering are stable.
            kwargs["invariant"] = 1
            kwargs["pageCompression"] = 1
            super().__init__(*args, **kwargs)
            self._saved_page_states = []
            self.setTitle(title)
            self.setAuthor("Grounded")
            self.setSubject("Agentically generated scientific review")

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_page_number(page_count)
                canvas_module.Canvas.showPage(self)
            canvas_module.Canvas.save(self)

        def _draw_page_number(self, page_count):
            from reportlab.lib.colors import HexColor
            from reportlab.lib.units import mm
            from reportlab.lib.pagesizes import A4

            width, _ = A4
            self.saveState()
            self.setFont("GroundedSans", 6.2)
            self.setFillColor(HexColor(FAINT_HEX))
            self.drawRightString(width - 13 * mm, 8.5 * mm,
                                 f"{self._pageNumber} / {page_count}")
            self.setFont("GroundedSans-Bold", 5.7)
            self.drawString(13 * mm, 8.5 * mm, f"GROUNDED {release.upper()}")
            self.restoreState()

    return NumberedCanvas


def _draw_running_header(canvas, _doc, compiled_date):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    width, height = A4
    left = 13 * mm
    right = width - 13 * mm
    top = height - 10.5 * mm
    bottom = top - 8.5 * mm
    canvas.saveState()
    canvas.setStrokeColor(HexColor(INK_HEX))
    canvas.setLineWidth(0.55)
    canvas.line(left, top, right, top)
    canvas.line(left, bottom, right, bottom)
    canvas.setStrokeColor(HexColor(ACCENT_HEX))
    canvas.setLineWidth(1.1)
    canvas.rect(left, bottom, 9 * mm, 8.5 * mm, stroke=1, fill=0)
    canvas.setStrokeColor(HexColor(ACCENT_HEX))
    canvas.setLineWidth(0.8)
    chip_x = left + 4.5 * mm
    chip_y = bottom + 4.5 * mm
    canvas.line(chip_x, chip_y + 1.8 * mm, chip_x, chip_y - 0.4 * mm)
    canvas.line(chip_x - 1.7 * mm, chip_y - 0.4 * mm,
                chip_x + 1.7 * mm, chip_y - 0.4 * mm)
    canvas.line(chip_x - 1.15 * mm, chip_y - 1.2 * mm,
                chip_x + 1.15 * mm, chip_y - 1.2 * mm)
    canvas.line(chip_x - 0.55 * mm, chip_y - 2.0 * mm,
                chip_x + 0.55 * mm, chip_y - 2.0 * mm)
    canvas.setFillColor(HexColor(INK_HEX))
    canvas.setFont("GroundedSans-Bold", 8.8)
    canvas.drawString(left + 12 * mm, bottom + 2.5 * mm, "G R O U N D E D")
    canvas.setFillColor(HexColor(MUTED_HEX))
    canvas.setFont("GroundedSans-Bold", 5.4)
    canvas.drawString(left + 47 * mm, bottom + 2.8 * mm, "NO FLOATING CLAIMS.")
    canvas.drawRightString(
        right, bottom + 2.8 * mm, _display_date(compiled_date).upper(),
    )
    canvas.restoreState()


def write_pdf(markdown: str, out_path: str, *, base_dir: str = ".",
              columns: int = 2, kicker: str = "Review", release: str = "dev",
              repo_label: str = "local build", compiled_date=None,
              colophon: str | None = None) -> dict[str, object]:
    """Write one deterministic PDF atomically and return build metadata."""
    runtime = require_runtime()
    if columns not in (1, 2):
        raise PdfInputError("columns must be 1 or 2")
    compiled_date = compiled_date or _datetime.date.today()
    if isinstance(compiled_date, str):
        try:
            compiled_date = _datetime.date.fromisoformat(compiled_date)
        except ValueError as exc:
            raise PdfInputError("compiled date must use YYYY-MM-DD") from exc
    if not isinstance(compiled_date, _datetime.date):
        raise PdfInputError("compiled date must be a date or YYYY-MM-DD string")

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _register_fonts(repo_dir)
    document = parse_review(markdown)
    target = os.path.abspath(out_path)
    target_dir = os.path.dirname(target)
    if not os.path.isdir(target_dir):
        raise PdfInputError(f"output directory does not exist: {target_dir}")

    page_width, page_height = A4
    left = 13 * mm
    bottom = 15 * mm
    frame_width = page_width - 26 * mm
    frame_height = page_height - 39 * mm
    frame = Frame(
        left, bottom, frame_width, frame_height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="grounded-page",
    )
    story = _build_story(
        document, markdown, os.path.abspath(base_dir), columns, kicker,
        release, repo_label, compiled_date, frame_width, frame_height, colophon,
    )

    with tempfile.TemporaryDirectory(prefix=".grounded-pdf-", dir=target_dir) as tmp:
        rendered = os.path.join(tmp, "rendered.pdf")
        pdf = BaseDocTemplate(
            rendered, pagesize=A4, leftMargin=left, rightMargin=left,
            topMargin=24 * mm, bottomMargin=bottom,
            title=document.title, author="Grounded", creator="Grounded",
            subject="Agentically generated scientific review",
        )
        pdf.addPageTemplates([
            PageTemplate(
                id="grounded", frames=[frame],
                onPage=lambda canvas, doc: _draw_running_header(
                    canvas, doc, compiled_date,
                ),
            )
        ])
        pdf.build(
            story,
            canvasmaker=_canvas_class(document.title, release, compiled_date),
        )
        if not os.path.isfile(rendered) or os.path.getsize(rendered) < 5:
            raise PdfRuntimeError("ReportLab did not produce a PDF")
        with open(rendered, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise PdfRuntimeError("ReportLab output is not a PDF")
        with open(rendered, "rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        os.replace(rendered, target)
    return {"renderer": "reportlab", "runtime": runtime, "sha256": digest}
