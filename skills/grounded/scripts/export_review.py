#!/usr/bin/env python3
"""Export a finished review to journal-styled HTML or a deterministic PDF.

Takes the markdown produced by format_references.py and typesets it in the
GROUNDED journal identity: repeating masthead, metadata grid,
two-column body, full-width tables and figures, numbered cited captions, and a
compact reference list. Author-year DOI links in the source markdown become
DOI-linked superscript numbers attached to the supported claim, while the
reference list follows first-citation order. Figure cross-references stay
hyperlinked and DOIs stay resolvable.

    python3 export_review.py --in review.md --out review.html
    python3 export_review.py --in review.md --out review.pdf --pdf
    python3 export_review.py --in review.md --out review.html --columns 1 --title "..."

PDF renders this exact HTML/CSS with pinned WeasyPrint.  It never launches a
browser, executes document code, or accesses the network.  HTML-only export
remains Python-standard-library-only.
"""

import argparse
import base64
import datetime
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

from artifact_io import atomic_write_json, sha256_bytes, sha256_file
import claim_receipts
import audit_contract
from citation_apparatus import correction_note_dois, ledger_correction_dois
from grounded_metadata import (
    FIGURE_MAX_HEIGHT_MM, PAGE_CONTENT_WIDTH_MM, REPOSITORY_URL,
    rendered_figure_size_mm, version as grounded_version,
)

# ---------------------------------------------------------------- markdown ---
# The skill emits a narrow, fixed subset: ##/### headings, **bold**, *italic*,
# [text](url) links, - bullets, | tables |, and > blockquotes. Parse exactly that.

INLINE_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https?://(?:[^\s()]|\([^\s()]*\))+|#[A-Za-z][A-Za-z0-9_-]*)\)"
)
DOI_MARKDOWN_LINK = (
    r"\[[^\]]+\]\(https?://(?:dx\.)?doi\.org/"
    r"(?:[^\s()]|\([^\s()]*\))+\)"
)
DOI_MARKDOWN_GROUP_RE = re.compile(
    DOI_MARKDOWN_LINK + r"(?:,\s*" + DOI_MARKDOWN_LINK + r")*",
    re.IGNORECASE,
)
CITATION_MARKER_RE = re.compile(r"\ue000C(?P<number>\d+)\ue001")
CITATION_MARKER_GROUP_RE = re.compile(
    r"[ \t]*(?P<markers>\ue000C\d+\ue001"
    r"(?:,\s*\ue000C\d+\ue001)*)(?P<punct>[.,;:!?]?)"
)


class JournalCitationIndex:
    """Number DOI citations by first appearance for journal rendering only."""

    def __init__(self):
        self._number_by_doi = {}
        self._href_by_number = {}

    @staticmethod
    def normalized_doi(href):
        match = re.match(
            r"^https?://(?:dx\.)?doi\.org/(.+)$",
            html.unescape(href),
            re.IGNORECASE,
        )
        if not match:
            return None
        return urllib.parse.unquote(match.group(1)).lower()

    def number_for(self, href):
        doi = self.normalized_doi(href)
        if doi is None:
            raise ValueError(f"not a DOI resolver URL: {href}")
        if doi not in self._number_by_doi:
            number = len(self._number_by_doi) + 1
            self._number_by_doi[doi] = number
            self._href_by_number[number] = html.unescape(href)
        return self._number_by_doi[doi]

    def marker_for(self, href):
        return f"\ue000C{self.number_for(href)}\ue001"

    def render_markers(self, rendered):
        """Turn adjacent markers into one linked superscript citation cluster.

        The journal puts sentence punctuation before the raised number and
        removes the ordinary word space before it. This makes a citation read
        as support for the preceding claim instead of the opening of the next
        sentence.
        """
        def replace_group(match):
            numbers = []
            for token in CITATION_MARKER_RE.finditer(match.group("markers")):
                number = int(token.group("number"))
                if number not in numbers:
                    numbers.append(number)
            links = ",".join(
                '<a href="%s" role="doc-biblioref">%d</a>' % (
                    html.escape(self._href_by_number[number], quote=True), number
                )
                for number in numbers
            )
            label = ", ".join(str(number) for number in numbers)
            citation = (
                f'<sup class="citation" aria-label="References {label}">'
                f"{links}</sup>"
            )
            return match.group("punct") + citation

        return CITATION_MARKER_GROUP_RE.sub(replace_group, rendered)


def _reference_doi(text):
    # A correction DOI is linked apparatus on the corrected article's entry,
    # not a second cited reference. Number the primary DOI preceding the
    # formatter's explicit label while preserving the correction link below.
    primary_text = re.split(r"\bCorrection:\s*", text, maxsplit=1, flags=re.I)[0]
    urls = []
    for match in re.finditer(
            r"https?://(?:dx\.)?doi\.org/[^\s<>]+", primary_text, re.IGNORECASE):
        href = match.group(0).rstrip(".,;*_)")
        doi = JournalCitationIndex.normalized_doi(href)
        if doi and doi not in {item[0] for item in urls}:
            urls.append((doi, href))
    if len(urls) != 1:
        raise ValueError("every Sources entry must contain exactly one DOI URL")
    return urls[0][1]


def _validate_journal_citation_placement(md):
    """Reject citations that function as the first words of a sentence.

    A DOI-only table cell is allowed because it labels the row rather than
    opening a sentence. Citations after a completed sentence are valid: the
    renderer closes the preceding whitespace and attaches the superscript to
    that sentence.
    """
    body = re.split(r"(?m)^\*\*Sources\*\*\s*$", md, maxsplit=1)[0]
    for match in DOI_MARKDOWN_GROUP_RE.finditer(body):
        line_number = body.count("\n", 0, match.start()) + 1
        line_start = body.rfind("\n", 0, match.start()) + 1
        line_end = body.find("\n", match.end())
        if line_end < 0:
            line_end = len(body)
        line = body[line_start:line_end]
        relative_start = match.start() - line_start
        relative_end = match.end() - line_start
        is_table_row = line.lstrip().startswith("|")
        if is_table_row:
            cell_start = line.rfind("|", 0, relative_start) + 1
            cell_end = line.find("|", relative_end)
            if cell_end < 0:
                cell_end = len(line)
            cell_prefix = line[cell_start:relative_start]
            cell_suffix = line[relative_end:cell_end]
            if not cell_prefix.strip() and not cell_suffix.strip():
                continue

        block_start = body.rfind("\n\n", 0, match.start()) + 2
        prefix = body[block_start:match.start()]
        if not re.search(r"[^\W_]", prefix, re.UNICODE):
            raise ValueError(
                f"journal citation starts a sentence or block at line {line_number}; "
                "place it after the supported claim or quotation"
            )

        if prefix.rstrip().endswith((".", "!", "?")):
            block_end = body.find("\n\n", match.end())
            if block_end < 0:
                block_end = len(body)
            tail = body[match.end():block_end].lstrip()
            tail = tail.lstrip(",;: ")
            first_word = re.search(r"[^\W_]", tail, re.UNICODE)
            if first_word and first_word.group(0).islower():
                raise ValueError(
                    f"journal citation starts a sentence at line {line_number}; "
                    "rewrite the sentence so the citation follows its claim"
                )


def inline(s, citations=None, in_references=False):
    """Inline markdown -> HTML. Escapes first, so source text can contain < or &."""
    s = html.escape(s, quote=False)
    # links before emphasis: link text may contain punctuation but not brackets
    def replace_link(match):
        href = html.unescape(match.group(2))
        if (citations is not None and not in_references
                and JournalCitationIndex.normalized_doi(href) is not None):
            return citations.marker_for(href)
        return f'<a href="{html.escape(href, quote=True)}">{match.group(1)}</a>'

    s = INLINE_LINK_RE.sub(replace_link, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # bare urls (in the sources block) become links
    s = re.sub(r'(?<!["=>])(https?://[^\s<]+)(?![^<]*</a>)',
               lambda m: f'<a href="{html.escape(m.group(1), quote=True)}">{m.group(1)}</a>', s)
    if citations is not None and not in_references:
        s = citations.render_markers(s)
    return s


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def append_spanning_block(out, block):
    """Keep a section heading with an immediately following table or figure."""
    if out and out[-1].startswith("<h2>") and out[-1].endswith("</h2>"):
        heading = out.pop()
        section_class = ("spanning-figure-start" if block.startswith("<figure")
                         else "spanning-table-start fragmentable-table")
        out.append(
            f'<section class="{section_class}">{heading}{block}</section>')
    else:
        out.append(f'<section class="spanning-block">{block}</section>')


# Plain-text budget for the shrink-wrapped pair in arrange_page_flow,
# calibrated on the journal body (9.5pt Charter in two 88mm columns).
COMPACT_PAIR_MAX_CHARS = 6000


def arrange_page_flow(blocks, columns, use_structured_caption_flow=False,
                      compact_pair_max_chars=COMPACT_PAIR_MAX_CHARS):
    """Close column runs around displays with tall structured captions.

    WeasyPrint cannot reliably fragment ``column-span: all``: a display that
    fits below the preceding columns can be pushed to the next page, stranding
    most of the current page.  Explicit sibling runs express the same journal
    layout without asking the renderer to interrupt a fragmented multicolumn
    box.  A run still fills pages sequentially; only its final fragment is
    balanced before the following full-width block.  This alternate flow is
    deliberately reserved for figures whose multi-line bullet captions make
    the span interruption tall enough to trigger that renderer defect; compact
    prose captions retain the proven sequential journal-column route.

    ``compact_pair_max_chars`` bounds the shrink-wrapped pair below. The
    pair cannot fragment, so the bound must stay under what the run can
    still fit beside its display on one page; an edition with taller
    opening furniture and larger body type sets a lower bound.
    """
    if columns != 2 or not use_structured_caption_flow or not any(
            block.startswith('<section class="spanning-') for block in blocks):
        return "\n".join(blocks)

    flow = []
    run = []

    def flush_run(before_span=False, final=False):
        if run:
            balance_blocks = []
            for item in run:
                if item.startswith("<ul>") and item.endswith("</ul>"):
                    balance_blocks.extend(re.findall(r"<li>.*?</li>", item, re.S))
                else:
                    balance_blocks.append(item)

            def render_half(items):
                rendered = []
                list_items = []
                for item in items + [None]:
                    if item is not None and item.startswith("<li>"):
                        list_items.append(item)
                        continue
                    if list_items:
                        rendered.append("<ul>" + "".join(list_items) + "</ul>")
                        list_items = []
                    if item is not None:
                        rendered.append(item)
                return "\n".join(rendered)

            # A short terminal run must shrink-wrap so the display can use the
            # rest of the page. WeasyPrint stretches a fragmented multicol box
            # to the page bottom even when its visible columns are short.
            plain_lengths = [len(re.sub(r"<[^>]+>", "", item))
                             for item in balance_blocks]
            candidates = [index for index in range(1, len(balance_blocks))
                          if not balance_blocks[index - 1].startswith("<h2")]
            if (before_span and
                    sum(plain_lengths) <= compact_pair_max_chars and
                    len(balance_blocks) > 1 and candidates):
                total = sum(plain_lengths)
                split = min(candidates, key=lambda index: abs(
                    sum(plain_lengths[:index]) - total / 2))
                left = render_half(balance_blocks[:split])
                right = render_half(balance_blocks[split:])
                flow.append('<div class="compact-column-pair">'
                            f'<div>{left}</div><div>{right}</div></div>')
            else:
                flow.append('<div class="column-run">' + "\n".join(run) + '</div>')
            run.clear()

    for block in blocks:
        if block.startswith('<section class="spanning-'):
            flush_run(before_span=True)
            flow.append(block)
        else:
            run.append(block)
    flush_run()
    for index in range(len(flow) - 1, -1, -1):
        if flow[index].startswith('<div class="column-run">'):
            flow[index] = flow[index].replace(
                'class="column-run"', 'class="column-run final"', 1)
            break
    return "\n".join(flow)


MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def image_data_uri(path, base_dir):
    """Embed a local image as a data URI so the export is self-contained."""
    import base64
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", path):
        raise ValueError(f"remote figure assets are not allowed: {path}")
    base = os.path.realpath(base_dir)
    p = os.path.realpath(path if os.path.isabs(path) else os.path.join(base, path))
    try:
        inside = os.path.commonpath([base, p]) == base
    except ValueError:
        inside = False
    if not inside:
        raise ValueError(f"figure asset escapes the review directory: {path}")
    ext = os.path.splitext(p)[1].lower()
    if ext not in MIME:
        raise ValueError(f"unsupported figure format: {path}")
    if not os.path.isfile(p):
        raise ValueError(f"figure asset does not exist: {path}")
    with open(p, "rb") as f:
        return f"data:{MIME[ext]};base64," + base64.b64encode(f.read()).decode()


def _to_html_document(md, base_dir=".", columns=2,
                      explicit_column_runs=False,
                      compact_pair_max_chars=COMPACT_PAIR_MAX_CHARS):
    """Convert Markdown and return title, lead, body, and explicit flow mode.

    ``explicit_column_runs`` forces the sibling-run flow for editions whose
    body type leaves too little slack around a spanning display; see
    ``arrange_page_flow``. A chat Receipts stamp after Sources is stripped:
    the receipts live in their own file, the PDF prints only the tally.
    """
    md = claim_receipts.strip_receipts(md)
    _validate_journal_citation_placement(md)
    citations = JournalCitationIndex()
    lines = md.split("\n")
    out, i = [], 0
    title, lead = None, None
    n_figs = 0
    pending_figure_id = None
    figure_ids = []
    has_tall_structured_caption = False
    in_sources = False
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

        anchor = re.match(r'^<a id="(fig-[a-z][a-z0-9-]*)"></a>$', s)
        if in_sources and (anchor or s.startswith(
                ("# ", "## ", "### ", "> ", "![", "|", "- ", "* "))):
            raise ValueError("Sources must be the terminal review section")
        if anchor:
            if pending_figure_id is not None:
                raise ValueError("figure anchor is not followed by a figure")
            pending_figure_id = anchor.group(1)
            i += 1
            continue

        if pending_figure_id is not None and not re.match(
                r"^!\[([^\]]*)\]\(([^)\s]+)\)$", s):
            raise ValueError("figure anchor is not followed by a figure")

        # Render an optional leading blockquote as a provenance or editorial note.
        if s.startswith(">"):
            note = inline(s.lstrip("> ").strip(), citations=citations)
            out.append(f'<p class="note">{note}</p>')
            i += 1
            continue

        if s.startswith("### "):
            out.append(f"<h2>{inline(s[4:], citations=citations)}</h2>")
            i += 1
            continue

        # figure: ![alt](file), optionally followed by an *Caption: …* line
        fig = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)$", s)
        if fig:
            alt, src = fig.group(1), fig.group(2)
            i += 1
            n_figs += 1
            figure_id = pending_figure_id or "figure-%d" % n_figs
            pending_figure_id = None
            figure_ids.append(figure_id)
            while i < len(lines) and not lines[i].strip():
                i += 1
            caption_line = lines[i].strip() if i < len(lines) else ""
            cm = re.match(
                r"^\*\*Figure\s+(\d+)\.\s*(.+?)\*\*(\s+.+)?$", caption_line)
            if not cm:
                raise ValueError(
                    "every figure must have a numbered caption immediately after it")
            if int(cm.group(1)) != n_figs:
                raise ValueError("figure caption numbering does not match figure order")
            k = i + 1
            caption_bullets = []
            while k < len(lines) and lines[k].strip().startswith("- "):
                caption_bullets.append(lines[k].strip()[2:])
                k += 1
            caption_payload = "\n".join([caption_line] + caption_bullets)
            if not cm.group(3) and not caption_bullets:
                raise ValueError("every figure caption must explain the figure")
            if "https://doi.org/" not in caption_payload.lower():
                raise ValueError("every figure caption must contain a DOI citation")
            caption_list = ""
            if caption_bullets:
                has_tall_structured_caption = True
                caption_list = "<ul>" + "".join(
                    f"<li>{inline(item, citations=citations)}</li>"
                    for item in caption_bullets) + "</ul>"
            caption = (
                f'<figcaption><b class="figno">Figure {n_figs}.</b> '
                f'<b class="figtitle">{inline(cm.group(2), citations=citations)}</b>'
                f'{inline(cm.group(3) or "", citations=citations)}'
                f'{caption_list}</figcaption>')
            i = k
            uri = image_data_uri(src, base_dir)
            append_spanning_block(
                out,
                f'<figure id="{figure_id}"><img src="{uri}" '
                f'alt="{html.escape(alt, quote=True)}">{caption}</figure>',
            )
            continue

        if s.startswith("## "):
            if title is None:
                title = inline(s[3:], citations=citations)
            else:
                out.append(f"<h2>{inline(s[3:], citations=citations)}</h2>")
            i += 1
            continue

        if s.startswith("# "):
            if title is None:
                title = inline(s[2:], citations=citations)
            else:
                out.append(f"<h2>{inline(s[2:], citations=citations)}</h2>")
            i += 1
            continue

        # table: header row, delimiter row, body rows
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            head = split_row(s)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i].strip()))
                i += 1
            th = "".join(
                f"<th>{inline(c, citations=citations)}</th>" for c in head)
            trs = "".join(
                "<tr>" + "".join(
                    f"<td>{inline(c, citations=citations)}</td>" for c in r
                ) + "</tr>" for r in rows)
            append_spanning_block(
                out,
                f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead>'
                f'<tbody>{trs}</tbody></table></div>',
            )
            continue

        # bullet list
        if s.startswith("- ") or s.startswith("* "):
            items = []
            while i < len(lines) and lines[i].strip()[:2] in ("- ", "* "):
                items.append(
                    f"<li>{inline(lines[i].strip()[2:], citations=citations)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # paragraph (gather until blank)
        para = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^[#\-*>|!]", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        text = " ".join(para)

        # the TL;DR or Abstract becomes the journal "lead"; the Sources heading starts the refs
        m = re.match(r"^\*\*(TL;DR|Abstract)\*\*", text)
        if m:
            lead = (
                m.group(1),
                inline(
                    re.sub(r"^\*\*(TL;DR|Abstract)\*\*\s*[—–-]?\s*", "", text),
                    citations=citations,
                ),
            )
            continue
        if re.match(r"^\*\*Sources\*\*\s*$", text):
            if in_sources:
                raise ValueError("Sources must appear exactly once")
            in_sources = True
            out.append('<h2 class="refhead">References</h2>')
            out.append('<div class="refs">')
            continue
        if in_sources:
            reference_href = _reference_doi(text)
            number = citations.number_for(reference_href)
            rendered_reference = inline(
                text, citations=citations, in_references=True)
            out.append(
                f'<p data-reference-number="{number}">'
                f'<span class="refno">{number}.</span> {rendered_reference}</p>'
            )
        else:
            out.append(f"<p>{inline(text, citations=citations)}</p>")

    if pending_figure_id is not None:
        raise ValueError("figure anchor is not followed by a figure")
    reference_container = next(
        (index for index, block in enumerate(out)
         if block == '<div class="refs">'),
        None,
    )
    if reference_container is not None:
        references = out[reference_container + 1:]
        references.sort(key=lambda entry: int(re.search(
            r'data-reference-number="(\d+)"', entry).group(1)))
        if references:
            references[-1] = references[-1].replace(
                "<p ", '<p class="last-reference" ', 1)
        heading = out[reference_container - 1]
        lengths = [len(re.sub(r"<[^>]+>", "", entry))
                   for entry in references]
        if (1 < len(references) <= 13 and sum(lengths) <= 4000 and
                not has_tall_structured_caption and
                not explicit_column_runs):
            split = min(range(1, len(references)), key=lambda position: abs(
                sum(lengths[:position]) - sum(lengths) / 2))
            left = "\n".join(references[:split])
            right = "\n".join(references[split:])
            reference_section = (
                '<section class="spanning-reference-balanced">'
                f'{heading}<div class="refs balanced"><div>{left}</div>'
                f'<div>{right}</div></div></section>'
            )
            out[reference_container - 1:] = [reference_section]
        else:
            out[reference_container + 1:] = references
            if references:
                out[-1] += "</div>"
            else:
                out.append("</div>")
    else:
        out.append('<p class="tomb">&#8718;</p>')
    structured_flow = columns == 2 and (
        has_tall_structured_caption or explicit_column_runs)
    body = arrange_page_flow(
        out, columns=columns,
        use_structured_caption_flow=structured_flow,
        compact_pair_max_chars=compact_pair_max_chars)
    for figure_id in figure_ids:
        if f'href="#{figure_id}"' not in body:
            raise ValueError(
                "every figure must be referenced from the text: %s" % figure_id)
    return title, lead, body, structured_flow


def to_html(md, base_dir=".", columns=2, explicit_column_runs=False,
            compact_pair_max_chars=COMPACT_PAIR_MAX_CHARS):
    """Convert the review markdown to body HTML. Returns (title, lead, body)."""
    title, lead, body, _structured_flow = _to_html_document(
        md, base_dir=base_dir, columns=columns,
        explicit_column_runs=explicit_column_runs,
        compact_pair_max_chars=compact_pair_max_chars,
    )
    return title, lead, body


# -------------------------------------------------------------------- css ---
# GROUNDED — the journal identity of this skill. Swiss-modern: grotesk furniture,
# serif body, one accent, and the packaged electricity-ground mark.

ACCENT = "#ff4f1f"

STYLE_LABELS = {
    "scientific": "Scientific",
    "popsci": "Popsci",
    "bullets": "Bullets",
    "eli5": "ELI5",
}
BRAND_LOGO = Path(__file__).resolve().parents[1] / "assets" / "grounded-logo-512.png"


def _normalized_style(style):
    normalized = "scientific" if style == "prose" else style
    if normalized not in STYLE_LABELS:
        raise ValueError("style must be one of: " + ", ".join(STYLE_LABELS))
    return normalized


def _brand_logo_data_uri():
    """Return the packaged Grounded mark as a self-contained PNG URI."""
    try:
        encoded = base64.b64encode(BRAND_LOGO.read_bytes()).decode("ascii")
    except OSError as exc:
        raise ValueError(f"packaged Grounded logo is unavailable: {BRAND_LOGO}") from exc
    return "data:image/png;base64," + encoded


def _brand_logo_html(css_class=""):
    """Return the packaged Grounded mark as a self-contained PNG image."""
    attributes = f' class="{css_class}"' if css_class else ""
    return (
        '<img' + attributes + ' src="' + _brand_logo_data_uri() + '" '
        'alt="" aria-hidden="true">'
    )

CSS = r"""
@page {
  size: A4; margin: 25mm 13mm 12mm 13mm;
  /* The masthead rides 4mm clear of the text block: without that margin the
     hairline sits exactly on the content edge and the page reads top-heavy.
     The gap comes out of the head margin, so pagination is unchanged. */
  @top-left {
    margin-bottom: 4mm;
    content: "G R O U N D E D";
    width: 42%; vertical-align: bottom; padding: 0 0 3.4mm 42px;
    border-bottom: .5px solid #141414;
    background: url("__GROUNDED_LOGO_DATA_URI__") no-repeat left calc(100% - 1.4mm) / 32px 32px;
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 9.5pt;
    font-weight: 600; letter-spacing: .12em; color: #141414;
  }
  @top-center {
    margin-bottom: 4mm;
    content: "AGENTICALLY GENERATED SCIENTIFIC REVIEW";
    width: 38%; vertical-align: bottom; padding: 0 0 3.4mm;
    border-bottom: .5px solid #141414;
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 6.3pt;
    font-weight: 600; letter-spacing: .11em; color: #6b6b6b;
  }
  @top-right {
    margin-bottom: 4mm;
    content: element(gndrelease);
    width: 20%; vertical-align: bottom; padding: 0 0 3.4mm;
    border-bottom: .5px solid #141414;
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 6.3pt;
    font-weight: 600; letter-spacing: .13em; color: #6b6b6b;
  }
  /* Margin-box page numbers appear in print engines that support CSS Paged Media. */
  @bottom-right { content: counter(page) " / " counter(pages);
    /* Sit the folio on the colophon stamp's baseline (one footer line). */
    vertical-align: top; padding-top: 3.4mm;
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 7pt; color: #9a9a9a; }
}
:root {
  --ink: #141414; --muted: #6b6b6b; --faint: #9a9a9a; --rule: #e4e4e4;
  --accent: #ff4f1f; --bg: #fff;
}
* { box-sizing: border-box; }
html { background: #fff; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Charter", "Iowan Old Style", Georgia, "Times New Roman", serif;
  font-size: 9.5pt; line-height: 1.38;
  text-align: justify; hyphens: auto; -webkit-hyphens: auto;
  hyphenate-character: "-";
}
.sans, .strip, .kicker, h1, .metagrid, .lead, h2, thead th,
.tablabel, figcaption, .refs, footer.colophon {
  font-family: -apple-system, "Helvetica Neue", "Helvetica", Arial, sans-serif;
}
.paper { width: 100%; max-width: 194mm; margin: 0 auto; }
.running-header {
  position: absolute; width: 0; height: 0; overflow: hidden;
}
.strip {
  display: block; width: 0; height: 0; overflow: hidden;
}
.strip::after { content: none; }
.strip .chip { display: none; }
.strip .chip img { width: 32px; height: 32px; display: block; margin: 0 auto; }
.strip .mark, .strip .descriptor { display: none; }
.strip .version {
  /* A margin-box content string cannot be a link, so the release stamp is
     rendered as a running element: same typography, but a real anchor that
     paints a clickable annotation in the top-right box of every page. */
  position: running(gndrelease); display: block; text-align: right;
  font-family: "Helvetica Neue", Arial, sans-serif; font-size: 6.3pt;
  font-weight: 600; letter-spacing: .13em; text-transform: uppercase;
  color: #6b6b6b; text-decoration: none; border-bottom: 0;
}
.kicker {
  font-size: 7.5pt; font-weight: 800; letter-spacing: .24em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 6px; text-align: left;
}
h1 {
  font-size: 24pt; line-height: 1.1; margin: 0 0 12px; font-weight: 300;
  letter-spacing: -0.015em; max-width: 30em; text-align: left; hyphens: none;
}
.metagrid {
  display: grid; grid-template-columns: repeat(5, 1fr);
  border-top: .5px solid var(--ink); border-bottom: .5px solid var(--ink);
  margin: 0 0 12px; break-inside: avoid;
}
.metagrid > div { padding: 5px 8px 6px; border-right: 1px solid var(--rule); text-align: left; }
.metagrid > div:last-child { border-right: 0; }
.metagrid b {
  display: block; font-size: 5.8pt; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--faint); margin-bottom: 2px;
}
.metagrid span { font-size: 9pt; font-weight: 600; letter-spacing: -.01em; }
.metagrid span i { font-style: normal; color: var(--accent); }
.lead { font-size: 9.8pt; line-height: 1.5; font-weight: 500;
  margin: 0 0 12px; max-width: 96%; text-align: left; }
.lead b {
  display: block; font-size: 6.2pt; font-weight: 800; letter-spacing: .2em;
  text-transform: uppercase; color: var(--faint); margin-bottom: 3px;
}
.note { font-size: 7pt; color: var(--muted); margin: 8px 0 0;
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; text-align: left; }
.body { counter-reset: sec; }
/* Paged-media balancing fills earlier pages sequentially and balances the final
   fragment, preventing a terminal reference page with one nearly empty column. */
.body.cols { column-count: 2; column-gap: 8mm; column-fill: balance; }
.column-run.final { column-count: 2; column-gap: 8mm; column-fill: balance; }
.column-run { column-count: 2; column-gap: 8mm; column-fill: balance; }
.compact-column-pair {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 8mm; break-inside: avoid;
}
.spanning-figure-start, .spanning-block,
.spanning-reference-balanced { break-inside: avoid; }
.spanning-table-start { break-inside: avoid; }
.body.structured-flow > .spanning-table-start { break-inside: auto; }
.body.cols > .spanning-figure-start, .body.cols > .spanning-table-start,
.body.cols > .spanning-block { column-span: all; }
.body.cols > .spanning-reference-balanced { column-span: all; }
.body.cols > .madewith { column-span: all; }
h2 {
  font-size: 9pt; font-weight: 600; line-height: 1.3; letter-spacing: 0;
  margin: 12px 0 4px; color: var(--ink);
  break-after: avoid; page-break-after: avoid; text-align: left; hyphens: none;
}
h2::before {
  counter-increment: sec; content: counter(sec, decimal-leading-zero);
  color: var(--accent); margin-right: 7px; font-variant-numeric: tabular-nums;
}
.body > h2:first-child, .column-run > h2:first-child { margin-top: 0; }
h2.refhead {
  border-top: 1px solid var(--ink); padding-top: 6px; margin-top: 16px;
  font-size: 9pt;
}
h2.refhead::before { content: none; counter-increment: none; }
h2.refhead small.audit-summary { display: block; letter-spacing: normal; float: none; }
h2.refhead small { font-weight: 600; font-size: 6.3pt; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted); float: right; margin-top: 2px; }
.madewith {
  border-top: 1px solid var(--ink); margin: 14px 0 0; padding: 5px 0 7px;
  break-inside: avoid; text-align: left; hyphens: none;
  font-family: -apple-system, "Helvetica Neue", "Helvetica", Arial, sans-serif;
}
.madewith + h2.refhead { margin-top: 0; }
.madewith.compact { padding: 4px 0 5px; }
.madewith.compact b { margin-bottom: 0; }
.madewith.compact b a { letter-spacing: 0; text-transform: none;
  font-size: 7pt; margin-left: 6px; }
.madewith b {
  display: block; font-size: 5.8pt; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 2.5px;
}
.madewith b img.mark { width: 11px; height: 11px; margin-right: 4px;
  vertical-align: -2.5px; }
.madewith p { margin: 0; font-size: 7pt; line-height: 1.45; color: var(--muted); }
/* Marker styling is left to the edition, whose list rules the band inherits. */
.madewith ul { margin: 0; font-size: 7pt; line-height: 1.45; color: var(--muted); }
.madewith li { margin: 0 0 1px; }
.madewith a { color: var(--ink); font-weight: 600; white-space: nowrap; }
p { margin: 0 0 4.5px; orphans: 2; widows: 2; }
ul { margin: 0 0 9px; padding-left: 1.05em; }
li { margin: 0 0 4.5px; break-inside: avoid; }
a { color: inherit; text-decoration: none; border-bottom: .5px solid rgba(255,79,31,.55); }
a[href^="#fig-"] { white-space: nowrap; }
a:hover { border-bottom-color: var(--accent); }
sup.citation {
  margin-left: .08em; font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: .72em; font-weight: 700; line-height: 0; vertical-align: super;
  white-space: nowrap; font-variant-numeric: tabular-nums; text-align: left;
}
sup.citation a { color: var(--accent); border-bottom: 0; }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: .9em; }
strong { letter-spacing: 0; }
/* Tables span the full page width (interrupting the columns, as journals do)
   and wrap their cell content — a table is never clipped or truncated. */
.tablewrap { break-inside: avoid; margin: 9px 0 11px; overflow: visible; }
.body.structured-flow > .spanning-table-start > .tablewrap { break-inside: auto; }
.body.structured-flow > .fragmentable-table thead {
  display: table-header-group;
}
.body.structured-flow > .fragmentable-table tr { break-inside: avoid; }
.tablewrap table { width: 100%; border-collapse: collapse; font-size: 7.4pt; line-height: 1.4;
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; }
thead th {
  font-size: 6.4pt; text-transform: uppercase; letter-spacing: .08em;
  text-align: left; font-weight: 600;
  border-top: 1px solid var(--ink); border-bottom: .5px solid var(--ink);
  padding: 4.5px 7px 4px; hyphens: none;
}
tbody td {
  padding: 4px 7px; border-bottom: .5px solid var(--rule); vertical-align: top;
  text-align: left; overflow-wrap: break-word; hyphens: auto;
}
tbody tr:last-child td { border-bottom: 1px solid var(--ink); }
.refs { font-size: 6.9pt; line-height: 1.2; color: #333; text-align: left; }
.refs.balanced {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8mm;
}
.refs p { margin: 0 0 2.5px; padding-left: 2.25em; break-inside: avoid-page; }
.refs .refno {
  /* A float is displaced at a fragment boundary — the first entry's number
     lands in the second entry's slot and overprints it. An inline-block
     hangs the same 2em without entering float layout. */
  display: inline-block; width: 2em; margin-left: -2.25em; color: var(--accent);
  font-weight: 700; font-variant-numeric: tabular-nums;
}
.refs p.last-reference::after {
  content: "  \220E"; color: var(--accent); font-size: 1.2em; white-space: nowrap;
}
.refs.dense { font-size: 6.5pt; line-height: 1.08; }
.refs.dense p { margin-bottom: .5px; }
.refs a { border-bottom: none; color: var(--muted); word-break: break-all; }
/* Figures, like tables, span the full page width and are never clipped. */
figure { margin: 10px 0 12px; break-inside: avoid; }
figure img {
  display: block; width: 100%; max-width: 100%; height: auto; max-height: 92mm;
  object-fit: contain;
  margin: 0 auto;
}
figcaption { font-size: 7.4pt; color: var(--muted); margin-top: 5px;
  text-align: left; line-height: 1.45; }
figcaption a, figcaption .figno { white-space: nowrap; }
figcaption .figno, figcaption .figtitle { color: var(--ink); }
figcaption .figno, figcaption .figtitle, .tablabel b { font-weight: 800; }
figcaption .figno::first-letter { color: var(--ink); }
figcaption ul { margin: 4px 0 0; padding-left: 1.15em; }
figcaption li { margin: 0 0 2px; break-inside: auto; }
.tomb { text-align: right; color: var(--accent); font-size: 11pt;
  margin: 0; padding: 0; line-height: 1; }
footer.colophon {
  /* Per-page furniture is just the hairline and the folio; the verification
     colophon appears once, book-style, after the references. Fixed so it
     cannot create a spill page. */
  position: fixed; bottom: -6.2mm; left: 0; right: 0; height: 0;
  border-top: .5px solid var(--ink);
}
.endcolophon {
  margin: 4.5mm auto 0; text-align: center; color: var(--faint);
  font-size: 6.2pt; font-weight: 600; letter-spacing: .18em;
  text-transform: uppercase; line-height: 1.75; break-inside: avoid;
}
.endcolophon .rule { width: 18mm; border-top: .5px solid var(--ink); margin: 0 auto 1.6mm; }
.endcolophon a { color: var(--faint); border-bottom: none; }
@media screen {
  body { padding: 10mm 0; background: #f2f2f2; }
  .paper { background: #fff; box-shadow: 0 2px 18px rgba(0,0,0,.12);
    padding: 0 10mm 12mm; }
  .running-header { position: static; width: 100%; height: auto; overflow: visible;
    padding: 10mm 10mm 5mm;
    max-width: 194mm; margin: 0 auto; background: #fff; }
  .strip { position: relative; width: 100%; height: 34px; overflow: visible;
    border-bottom: .5px solid var(--ink); }
  .strip::after { content: none; }
  .strip .chip { background: none; display: block; position: absolute;
    top: 1px; left: 0; width: 40px; text-align: center; }
  .strip .mark { display: block; position: absolute; top: 0; left: 50px;
    line-height: 33px; font-weight: 600; font-size: 9.5pt;
    letter-spacing: .3em; color: var(--ink); }
  .strip .descriptor { display: block; position: absolute; top: 0; left: 205px;
    line-height: 33px; font-size: 6.3pt; font-weight: 600;
    letter-spacing: .11em; text-transform: uppercase; color: var(--muted);
    text-decoration: none; border-bottom: 0; }
  .strip .version { display: block; position: absolute; top: 0; right: 0;
    line-height: 33px; text-align: right; font-size: 6.3pt; font-weight: 600;
    letter-spacing: .13em; text-transform: uppercase; color: var(--muted); }
}
@media screen and (max-width: 700px) {
  body { padding: 0; }
  .running-header { padding: 5mm 5mm 4mm; }
  .paper { padding: 0 5mm 8mm; }
  .body.cols, .column-run { column-count: 1; }
  .compact-column-pair { grid-template-columns: 1fr; }
  h1 { font-size: 16pt; }
  .metagrid { grid-template-columns: repeat(2, 1fr); }
  .metagrid > div { border-bottom: 1px solid var(--rule); }
  .tablewrap { overflow-x: auto; }
  .strip .descriptor { display: none; }
}
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="Grounded">
<meta name="generator" content="Grounded">
<meta name="description" content="Agentically generated scientific review">
<meta name="dcterms.created" content="{compiled_iso}">
<title>{title_text}</title>
<style>{css}</style>
</head><body>
<header class="running-header">
  <div class="strip">
    <span class="chip">{gnd}</span>
    <span class="mark">GROUNDED</span>
    <a class="descriptor" href="{repo_url}">Agentically generated scientific review</a>
    <a class="version" href="{repo_url}">grounded {version}</a>
  </div>
</header>
<main class="paper">
<div class="kicker">{kicker}</div>
<h1>{title}</h1>
{metagrid}
{lead}
<div class="body{cols}">
{body}
</div>
{reference_body}
{imprint}<footer class="colophon"></footer>
</main>
</body></html>
"""


def detect_release(_script_dir=None):
    """Canonical packaged release from ``VERSION``, e.g. ``vX.Y.Z``."""
    try:
        return f"v{grounded_version()}"
    except (OSError, RuntimeError):
        return ""


def detect_repo(script_dir):
    """(label, url) for the origin remote, normalized to https. ('', '') if unknown."""
    try:
        r = subprocess.run(["git", "-C", script_dir, "config", "--get", "remote.origin.url"],
                           capture_output=True, text=True, timeout=10)
        raw = r.stdout.strip()
    except Exception:
        raw = ""
    if not raw:
        return "", ""
    raw = re.sub(r"\.git$", "", raw)
    m = re.match(r"^(?:git@|https?://)([^:/]+)[:/](.+)$", raw)
    if not m:
        return "", ""
    label = f"{m.group(1)}/{m.group(2)}"
    return label, f"https://{label}"


def _compiled_date(value=None):
    if value is None:
        return datetime.date.today()
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("compiled date must use YYYY-MM-DD") from exc
    if isinstance(value, datetime.date):
        return value
    raise ValueError("compiled date must be a date or YYYY-MM-DD string")


def _display_date(value, abbreviated=False):
    month = value.strftime("%b" if abbreviated else "%B")
    return f"{value.day} {month} {value.year}"


FIGURE_MAX_HEIGHT_ANCHOR = "max-height: 92mm;"
REF_LEADING_ANCHOR = ".refs { font-size: 6.9pt; line-height: 1.2;"
REF_MARGIN_ANCHOR = ".refs p { margin: 0 0 2.5px;"
DEFAULT_REF_LEADING = 1.2
MIN_REF_LEADING = 1.1
# Auto-rebalance triggers for terminal spill pages up to this many entries;
# larger spills need content-level rebalancing, which QA reports precisely.
REBALANCE_MAX_SPILL = 8


def _stylesheet(figure_max_height_mm=FIGURE_MAX_HEIGHT_MM, ref_leading=None,
                edition="journal"):
    """Canonical CSS with the figure cap, reference leading, and edition.

    The layout knobs are bounded so a rebalance can never distort the page:
    the figure cap stays within 60-120 mm and the reference leading within
    1.1-1.2 line-height at unchanged type size. The edition overlay restyles
    typography and furniture over the same semantic document; it never
    touches the evidence contract (see references/contracts.md).
    """
    if not 60 <= float(figure_max_height_mm) <= 120:
        raise ValueError("figure max height must be between 60 and 120 mm")
    if FIGURE_MAX_HEIGHT_ANCHOR not in CSS:
        raise AssertionError("figure height anchor missing from canonical CSS")
    css = CSS.replace(
        FIGURE_MAX_HEIGHT_ANCHOR,
        f"max-height: {float(figure_max_height_mm):g}mm;",
    )
    css = css.replace(
        "__GROUNDED_LOGO_DATA_URI__",
        _brand_logo_data_uri(),
    )
    if ref_leading is not None:
        ref_leading = float(ref_leading)
        if not MIN_REF_LEADING <= ref_leading <= DEFAULT_REF_LEADING:
            raise ValueError(
                f"reference leading must stay within {MIN_REF_LEADING}-"
                f"{DEFAULT_REF_LEADING}; type size never changes"
            )
        if REF_LEADING_ANCHOR not in css or REF_MARGIN_ANCHOR not in css:
            raise AssertionError("reference anchors missing from canonical CSS")
        css = css.replace(
            REF_LEADING_ANCHOR,
            f".refs {{ font-size: 6.9pt; line-height: {ref_leading:g};",
        )
        css = css.replace(REF_MARGIN_ANCHOR, ".refs p { margin: 0 0 1px;")
    if edition not in EDITIONS:
        raise ValueError(f"unknown edition: {edition}")
    overlay = EDITIONS[edition]["css"]
    if overlay:
        css = css + "\n" + overlay
    if ref_leading is not None:
        # An explicit bounded layout control must win over edition defaults.
        # Leave the edition's font size and face untouched.
        css += (f"\n.refs {{ line-height: {ref_leading:g}; }}"
                "\n.refs p { margin-bottom: 1px; }\n")
    return css


def _pdf_page_count(pdf_path):
    from pypdf import PdfReader

    return len(PdfReader(str(pdf_path)).pages)


def count_terminal_reference_spill(pdf_path, reference_count):
    """Return how many reference entries sit alone on a terminal spill page.

    A spill page is a final page that carries only the tail of the numbered
    reference list (no References heading, no body). Returns 0 when the last
    page is not a spill page. Used to trigger the bounded auto-rebalance and
    testable on any rendered review PDF.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    if len(reader.pages) < 2 or reference_count < 1:
        return 0
    last_text = reader.pages[-1].extract_text() or ""
    if re.search(r"\bReferences\b", last_text):
        return 0
    numbers = {
        int(match) for match in re.findall(r"(?m)^\s*(\d{1,3})\.\s*$", last_text)
        if 0 < int(match) <= reference_count
    }
    # The book-style imprint spilling onto its own terminal page is the same
    # degenerate layout as a bare reference tail; count it so the rebalance
    # (and its refhead fallback) can pull it back.
    has_imprint = bool(re.search(r"(?i)grounded\s+\S+.{0,4}compiled", last_text))
    if numbers and max(numbers) == reference_count:
        return len(numbers)
    if has_imprint and not numbers:
        return 1
    return 0


SALON_CSS = """
/* SALON edition - literary popsci: Didot display, Hoefler text, Optima
   furniture, generous white space; house palette, orange used sparingly. */
@page { margin: 27mm 20mm 16mm 20mm; }
body { font-family: "Hoefler Text", Baskerville, Georgia, serif;
  font-size: 9.2pt; line-height: 1.58; }
.sans, .strip, .kicker, .metagrid, .lead, thead th,
.tablabel, figcaption, .refs, footer.colophon {
  font-family: Optima, Seravek, "Gill Sans", sans-serif;
}
.strip .mark { font-family: Optima, sans-serif; font-weight: 600;
  letter-spacing: .44em; }
.strip .descriptor, .strip .version { font-family: Optima, sans-serif; }
.strip::after { top: -1.6mm; }
.body.cols { column-gap: 10mm; }
.column-run, .column-run.final { column-gap: 10mm; }
.kicker { text-align: center; letter-spacing: .46em; font-weight: 600;
  font-size: 7pt; margin: 6mm 0 5mm; }
h1 { font-family: Didot, "Bodoni 72", serif; font-weight: 400;
  font-size: 34pt; line-height: 1.1; text-align: center;
  margin: 0 auto 7mm; }
.metagrid { max-width: 150mm; margin: 0 auto 9mm;
  border-top: .5px solid var(--rule); border-bottom: .5px solid var(--rule); }
.metagrid > div { text-align: center; border-right: none; padding: 8px 8px 9px; }
.metagrid b { letter-spacing: .22em; color: var(--faint); }
.metagrid span { font-weight: 500; }
.metagrid span i { color: var(--ink); }
.body.cols > p:first-child {
  column-span: all; font-family: Didot, serif; font-size: 12.5pt;
  line-height: 1.6; text-align: center; color: #444; hyphens: none;
  max-width: 82%; margin: 0 auto 10mm;
}
h2 { font-family: Optima, sans-serif; font-weight: 600; font-size: 8.5pt;
  letter-spacing: .26em; text-transform: uppercase; text-align: center;
  border-bottom: none; margin: 7mm 0 3.5mm; }
h2::before { color: var(--accent); letter-spacing: .12em; }
sup.citation, sup.citation a { color: #9a948a; }
.dropcap { float: left; font-family: Didot, serif; font-size: 38pt;
  line-height: .88; padding: 0 5pt 0 0; margin-top: 3.5pt;
  color: var(--ink); }
.pullquote { column-span: all; font-family: Didot, serif; font-style: italic;
  font-size: 16pt; line-height: 1.45; text-align: center; color: #3d3d3d;
  hyphens: none; margin: 9mm auto; max-width: 72%; break-inside: avoid; }
.pullquote::before { content: "\u201c"; display: block;
  font-family: Didot, serif; font-style: normal; font-size: 30pt;
  line-height: .75; color: var(--accent); margin-bottom: 1.5mm; }
.pullquote .pullref { display: block; margin-top: 3.5mm;
  font-family: Optima, Seravek, "Gill Sans", sans-serif; font-style: normal;
  font-size: 6.8pt; font-weight: 600; letter-spacing: .2em;
  text-transform: uppercase; color: var(--muted); }
.pullquote .pullref a { color: var(--muted); border-bottom: none;
  text-decoration: none; }
h2.refhead::before { content: "\u2042"; display: block;
  color: var(--accent); font-family: "Hoefler Text", Baskerville, serif;
  font-size: 17pt; margin: 0 auto 4mm; letter-spacing: 0; }
h2.refhead { text-align: center; letter-spacing: .32em; font-size: 9pt;
  margin: 8mm 0 1.5mm; }
h2.refhead small { display: block; float: none; text-align: center;
  font-size: 5.8pt; letter-spacing: .2em; color: var(--faint);
  margin-top: 1.6mm; text-transform: uppercase; }
.refs { line-height: 1.35; }
.refs p { margin-bottom: 4px; }
figcaption { margin-top: 7px; line-height: 1.55; }
figcaption .figno { color: var(--accent); letter-spacing: .08em; }
.refs .refno { color: var(--accent); font-weight: 400; }
figure { margin: 14px 0 16px; }
table { margin-bottom: 14px; }
td, thead th { padding: 6px 8px; }
"""

PRIMER_CSS = """
/* PRIMER edition - the friendly explainer for ELI5: humanist sans, orange
   step badges, TL;DR as an answer card - set in the canonical two-column
   measure so a phone can zoom a single column to full screen width. */
body { font-family: Seravek, "Gill Sans", "Helvetica Neue", sans-serif;
  font-size: 9.4pt; line-height: 1.5; text-align: left; hyphens: auto; }
@page { margin: 25mm 15mm 13mm 15mm; }
.body.cols, .column-run, .column-run.final { column-gap: 9mm; }
.kicker { letter-spacing: .3em; font-weight: 600; margin: 0 0 4mm; }
h1 { font-family: Seravek, "Gill Sans", sans-serif; font-weight: 700;
  font-size: 25pt; line-height: 1.16; letter-spacing: -.005em;
  margin: 0 0 5mm; }
.metagrid { border-top: .5px solid var(--rule);
  border-bottom: .5px solid var(--rule); margin-bottom: 5mm; }
.metagrid > div { border-right: none; padding: 7px 8px 8px; }
.metagrid > div:first-child { padding-left: 0; }
.metagrid b { letter-spacing: .18em; color: var(--faint); }
.lead { background: #fff3ee; border-left: 3.5px solid var(--accent);
  padding: 4mm 5mm; font-size: 10pt; line-height: 1.52; max-width: 100%;
  font-weight: 400; margin: 0 0 6mm; }
.lead b { color: var(--accent); font-size: 6.8pt; letter-spacing: .24em;
  margin-bottom: 2mm; }
h2 { font-family: Seravek, "Gill Sans", sans-serif; font-weight: 700;
  font-size: 11pt; line-height: 1.25; margin: 6mm 0 2mm; border-bottom: none;
  letter-spacing: 0; text-transform: none; }
h2::before { content: counter(sec); display: inline-block; width: 5.6mm;
  height: 5.6mm; line-height: 5.75mm; text-align: center;
  background: var(--accent); color: #fff; border-radius: 50%;
  font-size: 8.4pt; font-weight: 600; margin-right: 2.1mm;
  letter-spacing: 0; font-variant-numeric: lining-nums;
  vertical-align: middle; margin-top: -.8mm; }
p { margin: 0 0 5px; }
li { margin: 0 0 5px; }
sup.citation, sup.citation a { color: #a9a29a; }
figcaption { font-size: 7.6pt; line-height: 1.5; }
figcaption .figno { color: var(--accent); }
.refs .refno { color: var(--accent); }
.refs { line-height: 1.4; }
.refs p { margin-bottom: 4px; }
"""

BRIEF_CSS = """
/* BRIEF edition - the condensed two-column brief for bullets: tight
   disciplined columns, punchline headings, and a drawn double-chevron
   marker (two CSS strokes - font-independent, machine-centered). */
body { font-size: 8.8pt; line-height: 1.38; }
.kicker { margin: 2mm 0 4px; }
h1 { font-size: 21pt; font-weight: 600; line-height: 1.08;
  letter-spacing: -.01em; margin: 0 0 8px; }
.metagrid { margin-bottom: 8px; }
.lead { border-top: 2px solid var(--ink); border-bottom: .5px solid var(--ink);
  padding: 2.6mm 0 3mm; font-size: 9.3pt; line-height: 1.45;
  font-weight: 500; max-width: 100%; margin: 0 0 10px; }
.lead b { color: var(--accent); letter-spacing: .2em; }
h2 { font-size: 9.5pt; font-weight: 700; margin: 10px 0 3px;
  letter-spacing: 0; text-transform: none; line-height: 1.25; }
h2::before { color: var(--accent); font-weight: 700; }
ul { margin: 0 0 6px; padding-left: 0; list-style: none; }
li { margin: 0 0 2.5px; padding-left: 5.6mm; position: relative; }
li::before, li::after { content: ""; position: absolute; top: 0.3em;
  width: 1.15mm; height: 1.15mm;
  border-top: 0.5mm solid var(--accent);
  border-right: 0.5mm solid var(--accent);
  transform: rotate(45deg); }
li::before { left: 0; }
li::after { left: 1.5mm; }
sup.citation, sup.citation a { color: #98a0a8; }
figcaption .figno { color: var(--accent); }
.refs .refno { color: var(--accent); }
"""

# Editions bind a writing style to a paper identity: an overlay on the
# canonical CSS plus the font families the rendered PDF must embed. The
# evidence contract (citations, reference order, atomic writes, QA) is
# edition-invariant; see references/contracts.md.
EDITIONS = {
    "journal": {"css": "", "fonts": ("Charter", "Helvetica-Neue")},
    "salon": {"css": SALON_CSS, "fonts": ("Didot", "Hoefler-Text", "Optima")},
    # Primer sets the largest body type of any edition, so a spanning
    # display rarely fits below its columns: it always takes the explicit
    # sibling-run flow rather than asking WeasyPrint to fragment a
    # column-span box (which silently drops the rest of the document).
    "primer": {"css": PRIMER_CSS, "fonts": ("Seravek", "Helvetica-Neue"),
               "column_runs": "explicit", "compact_pair_max_chars": 2600},
    "brief": {"css": BRIEF_CSS, "fonts": ("Charter", "Helvetica-Neue")},
}
DEFAULT_EDITION_BY_STYLE = {"popsci": "salon", "eli5": "primer",
                            "bullets": "brief"}
DROPCAP_MIN_CHARS = 200
PULL_SENTINEL = "GROUNDED-PULL-QUOTE-SENTINEL"


def resolve_edition(style, edition=None):
    style = _normalized_style(style)
    resolved = edition or DEFAULT_EDITION_BY_STYLE.get(style, "journal")
    if resolved not in EDITIONS:
        raise ValueError(f"unknown edition: {resolved}")
    return resolved


def _strip_markdown_links(text):
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)


def _pull_quote_references(paragraph, pull):
    """Citations attached to the pulled sentence, for the attribution line.

    House style places a claim's citations inside its sentence, before the
    closing punctuation, so the DOI links found between the start of the
    pulled text and the end of its sentence are the quote's own support. A
    pulled line with no citation is authorial synthesis and gets no
    attribution. Best-effort: when the pulled text cannot be located as an
    exact substring (unusual whitespace), the quote renders unattributed
    rather than misattributed.
    """
    link_re = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
    stripped_chars = []
    raw_index = []
    links = []
    position = 0
    for match in link_re.finditer(paragraph):
        for i in range(position, match.start()):
            stripped_chars.append(paragraph[i])
            raw_index.append(i)
        links.append((match.start(), match.group(1), match.group(2)))
        for ch in match.group(1):
            stripped_chars.append(ch)
            raw_index.append(match.start())
        position = match.end()
    for i in range(position, len(paragraph)):
        stripped_chars.append(paragraph[i])
        raw_index.append(i)
    stripped = "".join(stripped_chars)
    start = stripped.find(pull)
    if start < 0:
        return []
    end = start + len(pull)
    # A pull that already carries terminal punctuation is a complete
    # sentence: its own links are its support. Only an unterminated clause
    # extends to the end of the sentence it was pulled from — never into
    # the next sentence, which would misattribute.
    if not re.search(r"[.!?][\u201d\u2019\"']*$", pull):
        sentence_end = re.search(r"[.!?]", stripped[end:])
        if sentence_end:
            end += sentence_end.end()
    raw_start = raw_index[start]
    raw_end = raw_index[end - 1] + 1 if end - 1 < len(raw_index) else len(paragraph)
    return [
        (label, href) for link_start, label, href in links
        if raw_start <= link_start < raw_end and "doi.org" in href
    ]


def insert_pull_quote_sentinel(md, pull_quote):
    """Place the authored pull quote before the paragraph that contains it.

    The pull quote is presentation, but it carries words, so it must be a
    verbatim substring of the article body (links stripped) — never invented
    or paraphrased. A quote that cannot be located verbatim is a hard error.
    Returns the updated markdown and the quote's own citations (label, DOI
    URL) for the attribution line.
    """
    pull = " ".join(pull_quote.split())
    if not pull:
        raise ValueError("pull quote is empty")
    body, sep, tail = md.partition("\n**Sources**")
    paragraphs = body.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        stripped = paragraph.lstrip()
        if stripped.startswith(("#", "|", "![", "<a id=", "**Figure")):
            continue
        if pull in " ".join(_strip_markdown_links(paragraph).split()):
            if index == 0 or stripped.startswith("*"):
                raise ValueError(
                    "pull quote must come from the article body, not the "
                    "standfirst"
                )
            references = _pull_quote_references(paragraph, pull)
            paragraphs.insert(index, PULL_SENTINEL)
            return "\n\n".join(paragraphs) + sep + tail, references
    raise ValueError(
        "pull quote is not a verbatim passage of the article body: " + pull
    )


def _render_pull_quote_aside(page, pull_quote, references=()):
    pull = " ".join(pull_quote.split())
    # The oversized quotation mark above the aside carries the quotation
    # signal; wrapping the text in additional quotes doubles up whenever the
    # pulled sentence itself begins with a quoted word.
    attribution = ""
    if references:
        linked = ", ".join(
            f'<a href="{html.escape(href, quote=True)}">'
            f"{html.escape(label, quote=False)}</a>"
            for label, href in references
        )
        attribution = f'<span class="pullref">— {linked}</span>'
    aside = (
        '<aside class="pullquote">'
        + html.escape(pull, quote=False)
        + attribution
        + "</aside>"
    )
    sentinel_paragraph = f"<p>{PULL_SENTINEL}</p>"
    if sentinel_paragraph not in page:
        raise ValueError("pull quote sentinel was lost during rendering")
    return page.replace(sentinel_paragraph, aside, 1)


def inject_drop_cap(page):
    """Salon edition: set the opener's initial as a three-line drop cap.

    Specimen-verified guards: only a plain capital letter opener, and only
    when the paragraph is long enough to wrap the full cap. Anything else
    (quote openers, digits, short paragraphs) renders without a cap rather
    than improvising.
    """
    marker = '<div class="body cols">'
    start = page.find(marker)
    if start < 0:
        return page
    match = re.search(r"<p>(?!<em>)", page[start:])
    if not match:
        return page
    position = start + match.start()
    end = page.find("</p>", position)
    if end < 0:
        return page
    text = re.sub(r"<[^>]+>", "", page[position + 3:end])
    initial = text[:1]
    if not (initial.isalpha() and initial.isupper()):
        return page
    if len(text) < DROPCAP_MIN_CHARS:
        return page
    if page[position + 3] != initial:
        return page
    return (
        page[:position]
        + f'<p><span class="dropcap">{initial}</span>'
        + page[position + 4:]
    )


def count_unique_dois(md):
    # inline citation URLs percent-encode parens, sources-block URLs don't;
    # normalize both forms before deduplicating. Linked correction notices are
    # visible reference apparatus, but not independent cited sources.
    all_dois = {
        urllib.parse.unquote(d).lower().rstrip(").,;*_")
        for d in re.findall(r"https?://doi\.org/([^\s<>]+)", md)
    }
    source_split = re.split(r"^\*\*Sources\*\*\s*$", md, maxsplit=1, flags=re.M)
    sources = source_split[1] if len(source_split) == 2 else ""
    return len(all_dois - correction_note_dois(sources))


def render_pdf_rebalanced(md, out_path, *, columns=2, kicker="Review",
                          colophon=None, base_dir=".", release=None, repo=None,
                          compiled_date=None, style="scientific",
                          figure_max_height_mm=FIGURE_MAX_HEIGHT_MM,
                          ref_leading=None, edition=None, pull_quote=None,
                          claims_audit=None):
    """Render the PDF, then walk the bounded rebalance ladder.

    A terminal page carrying only the reference tail and/or the book-style
    imprint is the degenerate spill the raster QA rejects. The ladder tries,
    in order: tightened reference leading; the imprint folded into the
    References heading (zero height); both. Type size is never touched. The
    first spill-free render wins; otherwise the original stands and QA
    reports the levers.
    """
    resolved_edition = resolve_edition(style, edition)
    expected_fonts = EDITIONS[resolved_edition]["fonts"]

    def build(leading, imprint, made_with="full"):
        return build_html(
            md, columns=columns, kicker=kicker, colophon=colophon,
            base_dir=base_dir, made_with=made_with,
            imprint=imprint, release=release, repo=repo,
            compiled_date=compiled_date, style=style,
            figure_max_height_mm=figure_max_height_mm, ref_leading=leading,
            edition=resolved_edition, pull_quote=pull_quote,
            claims_audit=claims_audit,
        )

    from weasyprint_export import write_pdf
    from qa_review_pdf import PdfQaError, inspect_structure
    page = build(ref_leading, "end")
    result = write_pdf(page, out_path, expected_fonts=expected_fonts)
    effective = {"ref_leading": ref_leading, "imprint": "end",
                 "made_with": "full",
                 "rebalanced": False, "note": None, "spill": 0}
    if ref_leading is not None:
        return page, result, effective
    try:
        spill = count_terminal_reference_spill(out_path, count_unique_dois(md))
    except Exception:
        spill = 0
    effective["spill"] = spill
    if not (0 < spill <= REBALANCE_MAX_SPILL):
        return page, result, effective
    ladder = (
        (MIN_REF_LEADING, "end", "full",
         f"reference leading tightened to {MIN_REF_LEADING:g}"),
        (None, "refhead", "full",
         "imprint folded into the References heading"),
        (MIN_REF_LEADING, "refhead", "full",
         "imprint folded and reference leading tightened to "
         f"{MIN_REF_LEADING:g}"),
        (MIN_REF_LEADING, "refhead", "compact",
         "imprint folded, provenance band compacted, and reference leading "
         f"tightened to {MIN_REF_LEADING:g}"),
    )
    candidate_path = str(out_path) + ".rebalance.pdf"
    best_path = str(out_path) + ".rebalance-best.pdf"
    plain_pages = _pdf_page_count(out_path)
    best = None
    try:
        for leading, imprint, made_with, note in ladder:
            candidate_page = build(leading, imprint, made_with)
            try:
                candidate = write_pdf(candidate_page, candidate_path,
                                      expected_fonts=expected_fonts)
                # A paged-layout engine can omit overflowing content entirely.
                # Such a render also has no reference spill and fewer pages;
                # verify content before treating those properties as progress.
                try:
                    inspect_structure(
                        candidate_path, md, expected_release=release,
                        expected_fonts=expected_fonts,
                        claim_summary=(claim_receipts.summarize_audit(claims_audit)
                                       if claims_audit is not None else None),
                    )
                except PdfQaError:
                    continue
                # Acceptable = out of the degenerate band: either nothing
                # spills, or the terminal page is a full reference
                # continuation page (sparseness there stays the raster QA's
                # call).
                candidate_spill = count_terminal_reference_spill(
                    candidate_path, count_unique_dois(md))
                if 0 < candidate_spill <= REBALANCE_MAX_SPILL:
                    continue
                # The spill count cannot see a terminal page holding a short
                # reference tail that renders without standalone numbering, so
                # prefer the shortest acceptable render and keep walking while
                # a later rung can still drop a page.
                candidate_pages = _pdf_page_count(candidate_path)
                if best is None or candidate_pages < best[0]:
                    os.replace(candidate_path, best_path)
                    best = (candidate_pages, candidate_page, candidate,
                            leading, imprint, made_with, note)
                if candidate_pages < plain_pages:
                    break
            finally:
                if os.path.exists(candidate_path):
                    os.remove(candidate_path)
        if best is not None:
            _, candidate_page, candidate, leading, imprint, made_with, note = best
            os.replace(best_path, out_path)
            effective.update(ref_leading=leading, imprint=imprint,
                             made_with=made_with, rebalanced=True, note=note)
            return candidate_page, candidate, effective
    finally:
        if os.path.exists(best_path):
            os.remove(best_path)
    return page, result, effective


def build_html(md, columns=2, kicker="Review", colophon=None, base_dir=".",
               made_with="full",
               imprint="end",
               release=None, repo=None, compiled_date=None, style="scientific",
               figure_max_height_mm=FIGURE_MAX_HEIGHT_MM, ref_leading=None,
               edition=None, pull_quote=None, claims_audit=None):
    import urllib.parse

    # Chat receipts are never review prose: the PDF renders the audit itself.
    md = claim_receipts.strip_receipts(md)
    style = _normalized_style(style)
    edition = resolve_edition(style, edition)
    if pull_quote is not None and edition != "salon":
        raise ValueError("pull quotes are a salon-edition device")
    pull_references = ()
    if pull_quote is not None:
        md, pull_references = insert_pull_quote_sentinel(md, pull_quote)
    css = _stylesheet(figure_max_height_mm, ref_leading=ref_leading,
                      edition=edition)
    title, lead, body, structured_flow = _to_html_document(
        md, base_dir=base_dir, columns=columns,
        explicit_column_runs=EDITIONS[edition].get("column_runs") == "explicit",
        compact_pair_max_chars=EDITIONS[edition].get(
            "compact_pair_max_chars", COMPACT_PAIR_MAX_CHARS),
    )
    title = title or "Scientific review"
    lead_html = ""
    if lead:
        label = "Abstract" if lead[0] == "Abstract" else "Summary"
        lead_html = f'<p class="lead"><b>{label}</b>{lead[1]}</p>'

    n_refs = count_unique_dois(md)

    today = _compiled_date(compiled_date)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if release is None:
        release = detect_release(script_dir)
    if repo is None:
        _repo_label, repo_url = detect_repo(script_dir)
    else:
        repo_url = repo if repo.startswith("http") else f"https://{repo}"
    release = release or "dev"
    repo_url = repo_url or REPOSITORY_URL

    audit_summary = (
        claim_receipts.summarize_audit(claims_audit)
        if claims_audit is not None else None)
    cells = [
        ("References", f"<i>{n_refs}</i> verified" if n_refs else "—"),
        ("Style", STYLE_LABELS[style]),
        ("Made with", f'<a href="{html.escape(repo_url, quote=True)}">'
                      f"Grounded {html.escape(release)}</a>"),
        ("Verification",
         "Crossref · claims" if audit_summary else "Crossref"),
        ("Compiled", _display_date(today, abbreviated=True)),
    ]
    metagrid = '<div class="metagrid">' + "".join(
        f"<div><b>{h}</b><span>{v}</span></div>" for h, v in cells) + "</div>"

    if n_refs:
        refhead_small = f"{n_refs} · verified via Crossref"
        if imprint == "refhead":
            # Fallback imprint: fold the release stamp into the References
            # heading so the colophon costs zero page height.
            refhead_small += f" · Grounded {html.escape(release)}"
        body = body.replace(
            '<h2 class="refhead">References</h2>',
            _made_with_block(repo_url, style, made_with == "compact") +
            f'<h2 class="refhead">References <small>{refhead_small}</small></h2>')
        if n_refs >= 80:
            body = body.replace('<div class="refs">', '<div class="refs dense">')


    if colophon is None:
        # The masthead carries identity and the pages stay quiet; this
        # review's verification stamp closes the document book-style.
        sources = f"{n_refs} sources · " if n_refs else ""
        colophon = (f"{sources}every DOI resolved · "
                    "retraction-screened via Crossref")
    # The audit line is what "verified" means, sentence by sentence.
    audit_line = ""
    if audit_summary:
        audit_line = ("<br>" + html.escape(
            claim_receipts.summary_sentence(audit_summary)))
        if imprint == "refhead":
            # Rebalancing may move the imprint into References, but must never
            # discard the assertion audit tally that release QA verifies.
            body = body.replace(
                '</small></h2>',
                '</small><small class="audit-summary">'
                + html.escape(claim_receipts.summary_sentence(audit_summary))
                + '</small></h2>', 1)
    reference_body = ""
    if (n_refs and columns == 2 and not structured_flow
            and '<div class="refs">' in body):
        # Keep a flowing bibliography in its own multicolumn container.
        # A column-spanning provenance band late in a long article can make
        # WeasyPrint discard the following reference fragment altogether.
        # The compact balanced-reference layout already has its own container.
        reference_start = body.index('<aside class="madewith')
        reference_body = '<div class="body cols">' + body[reference_start:] + '</div>'
        body = body[:reference_start]
    plain_title = re.sub(r"<[^>]+>", "", title)
    page = PAGE.format(
        title_text=plain_title, compiled_iso=today.isoformat(), css=css,
        gnd=_brand_logo_html(),
        version=html.escape(release), repo_url=html.escape(repo_url, quote=True),
        kicker=html.escape(kicker),
        title=title, metagrid=metagrid, lead=lead_html,
        cols=(" structured-flow" if structured_flow else
              (" cols" if columns == 2 else "")),
        body=body,
        reference_body=reference_body,
        imprint=(
            "" if imprint == "refhead" else
            '<div class="endcolophon"><div class="rule"></div>'
            f"{html.escape(colophon)}{audit_line}<br>Grounded {html.escape(release)}"
            f" · compiled {html.escape(_display_date(today))}</div>"
        ))
    if pull_quote is not None:
        page = _render_pull_quote_aside(page, pull_quote, pull_references)
    if edition == "salon":
        page = inject_drop_cap(page)
    return page


# Voice-matched provenance copy. The band answers the two questions a reader
# of a detached PDF cannot otherwise resolve — what produced this, and how do
# I do it — so the invitation leads and the register follows the review's own.
MADE_WITH_COPY = {
    "scientific":
        "<p>You can run this protocol yourself. Grounded is a free, "
        "open-source skill for AI assistants: candidate literature is "
        "retrieved by live search, source texts are read before citation, and "
        "every DOI and retraction status is verified against Crossref. "
        "{link}</p>",
    "popsci":
        "<p>You can point this at whatever you are curious about. Grounded is "
        "a free, open-source skill for AI assistants: hand it a question, and "
        "it goes and finds the real papers, reads them, and checks every "
        "source against Crossref \u2014 which is how every claim in this "
        "story was verified before it was written. {link}</p>",
    "bullets":
        "<ul><li>Free, open-source skill for AI assistants \u2014 ask a "
        "question, get a cited review.</li>"
        "<li>Every source from a live search; every DOI and retraction status "
        "checked against Crossref.</li>"
        "<li>Yours to run: {link}</li></ul>",
    "eli5":
        "<p>You can make one of these too. Grounded is a free skill \u2014 a "
        "set of instructions you give to an AI helper so it knows how to do a "
        "job properly. This one makes it go and find real science papers, "
        "read them, and check that every single one is real before it writes "
        "anything. {link}</p>",
}


def _made_with_block(repo_url, style, compact=False):
    """End-matter provenance band closing the article before the references.

    A reader who receives the PDF alone can otherwise tell only that the
    review was agent-generated: the masthead names the release and links it,
    but not what the skill is or how to run it.  The compact form is a
    rebalance rung — it keeps both answers the band exists to give, what
    produced this and where to get it, at a single line of page height.
    """
    label = re.sub(r"^https?://", "", repo_url)
    link = (f'<a href="{html.escape(repo_url, quote=True)}">'
            f"{html.escape(label)}</a>")
    mark = _brand_logo_html("mark")
    if compact:
        return ('<aside class="madewith compact">'
                f"<b>{mark}Made with Grounded {link}</b></aside>")
    return (f'<aside class="madewith"><b>{mark}Made with Grounded</b>'
            + MADE_WITH_COPY[style].format(link=link)
            + "</aside>")


def _manifest_path_record(path, manifest_directory):
    path = Path(path).resolve()
    return {
        "path": os.path.relpath(path, manifest_directory),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_claims_audit(path):
    """Load a claim audit and refuse one that cannot ship.

    A contradicted pair means the review says something its source denies; a
    pending pair means the audit was never finished. Neither is a receipt.
    """
    try:
        audit = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"claim audit cannot be read: {exc}") from exc
    if not isinstance(audit, dict) or not isinstance(audit.get("claims"), list):
        raise ValueError("claim audit must be a JSON object with a claims list")
    summary = claim_receipts.summarize_audit(audit)
    blockers = claim_receipts.release_blockers(summary)
    if blockers:
        raise ValueError("claim audit is not releasable: " + "; ".join(blockers))
    if summary["pairs"] == 0:
        raise ValueError("claim audit contains no claim-source pairs")
    return audit


def validate_release_inputs(
        review_path, ledger_path, figure_specs=(), figure_prompts=(),
        figure_inspections=(), figure_provenances=(), claims_audit=None,
        claim_receipts_path=None):
    """Fail before rendering when release lineage inputs are incomplete."""
    review_path = Path(review_path).resolve()
    markdown = review_path.read_text(encoding="utf-8")
    if claim_receipts_path is not None and not Path(claim_receipts_path).is_file():
        raise ValueError(f"claim receipts file does not exist: {claim_receipts_path}")
    if claim_receipts_path is not None and claims_audit is None:
        raise ValueError("--claim-receipts needs the --claims-audit it was rendered from")
    if claims_audit is not None:
        audit = load_claims_audit(claims_audit)
        audit_contract.validate_release(audit, markdown, claims_audit)
        audited = {claim_receipts.norm_doi(adj.get("doi"))
                   for claim in audit["claims"]
                   for adj in claim.get("adjudications", [])}
        cited = {claim_receipts.norm_doi(doi) for doi in re.findall(
            r"https?://doi\.org/([^\s<>)]+)",
            claim_receipts.strip_receipts(markdown).split("**Sources**")[0])}
        unaudited = sorted(cited - audited)
        if unaudited:
            raise ValueError(
                "claim audit does not cover every cited source: "
                + ", ".join(unaudited[:3]))
    elif claim_receipts.receipts_block(markdown):
        raise ValueError(
            "review carries a Receipts block but no --claims-audit was given")
    figure_sources = [
        source for _alt, source in re.findall(
            r"^!\[([^]]*)\]\(([^)\s]+)\)\s*$", markdown, re.M
        )
    ]
    figures = [(review_path.parent / source).resolve() for source in figure_sources]
    missing_files = [
        str(path) for path in [
            *figures,
            *(Path(item) for item in figure_specs),
            *(Path(item) for item in figure_prompts),
            *(Path(item) for item in figure_inspections),
            *(Path(item) for item in figure_provenances),
        ]
        if not path.is_file()
    ]
    if missing_files:
        raise ValueError("release lineage input does not exist: " + ", ".join(missing_files))
    if len(figure_specs) != len(figures) or len(figure_prompts) != len(figures):
        raise ValueError(
            "release manifest requires one --figure-spec and --figure-prompt "
            "for every rendered figure"
        )
    specs = [
        json.loads(Path(item).read_text(encoding="utf-8"))
        for item in figure_specs
    ]
    if any(not isinstance(spec, dict) for spec in specs):
        raise ValueError("every figure specification must be a JSON object")
    quality_contract = any(
        spec.get("quality_contract_version") in {1, 2, 3} for spec in specs)
    if quality_contract or figure_inspections or figure_provenances:
        if (len(figure_inspections) != len(figures)
                or len(figure_provenances) != len(figures)):
            raise ValueError(
                "quality-contract release requires one --figure-inspection and "
                "--figure-provenance for every rendered figure"
            )
    if quality_contract:
        from figure_provenance import validate_figure_set
        set_errors = validate_figure_set(specs, [
            json.loads(Path(path).read_text(encoding="utf-8"))
            for path in figure_provenances])
        if set_errors:
            raise ValueError("figure-set QA failed: " + "; ".join(set_errors))
        try:
            import qa_figure
        except ImportError as exc:
            raise ValueError(f"cannot load figure QA for release: {exc}") from exc
        for index, (spec, figure, inspection_path, provenance_path) in enumerate(
                zip(specs, figures, figure_inspections, figure_provenances), 1):
            if spec.get("quality_contract_version") not in {1, 2, 3}:
                continue
            if figure.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise ValueError(
                    f"quality-contract figure {index} must be a raster so aspect "
                    "and pixel QA can be proved"
                )
            inspection = json.loads(
                Path(inspection_path).read_text(encoding="utf-8"))
            provenance = json.loads(
                Path(provenance_path).read_text(encoding="utf-8"))
            audit = qa_figure.audit_figure(
                spec, figure, inspection=inspection, provenance=provenance)
            if audit.get("status") != "pass":
                raise ValueError(
                    f"quality-contract figure {index} failed QA: "
                    + "; ".join(audit.get("errors") or ["unknown failure"])
                )
    expected_dois = sorted({
        urllib.parse.unquote(value).lower().rstrip(").,;*_")
        for value in re.findall(r"https?://doi\.org/([^\s<>\]]+)", markdown, re.I)
    })
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    ledger_by_doi = {
        re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(entry.get("doi") or "").lower()): entry
        for entry in ledger.get("entries", []) if isinstance(entry, dict) and entry.get("doi")
    }
    source_split = re.split(r"^\*\*Sources\*\*\s*$", markdown, maxsplit=1, flags=re.M)
    sources = source_split[1] if len(source_split) == 2 else ""
    correction_dois = correction_note_dois(sources)
    cited_dois = sorted(set(expected_dois) - correction_dois)
    cited_primary_dois = set(cited_dois) & set(ledger_by_doi)
    recorded_corrections = ledger_correction_dois(ledger, cited_primary_dois)
    unrecorded_corrections = sorted(correction_dois - recorded_corrections)
    missing_correction_notes = sorted(recorded_corrections - correction_dois)
    if unrecorded_corrections:
        raise ValueError(
            "release correction DOI(s) are not recorded on a cited ledger entry: "
            + ", ".join(unrecorded_corrections[:5])
        )
    if missing_correction_notes:
        raise ValueError(
            "release review omits recorded correction notice DOI(s): "
            + ", ".join(missing_correction_notes[:5])
        )
    missing_ledger = [doi for doi in cited_dois if doi not in ledger_by_doi]
    if missing_ledger:
        raise ValueError(
            "release review DOI(s) are absent from the ledger: "
            + ", ".join(missing_ledger[:5])
        )
    ineligible = []
    for doi in cited_dois:
        entry = ledger_by_doi[doi]
        verification = entry.get("verification") or {}
        if (
            entry.get("status") != "verified"
            or verification.get("bibliographic_status") != "verified"
            or verification.get("retraction_status") != "clear"
        ):
            ineligible.append(str(entry.get("key") or doi))
    if ineligible:
        raise ValueError(
            "release review cites ledger entries that are not fully verified: "
            + ", ".join(ineligible[:5])
        )
    cited_ledger_by_doi = {doi: ledger_by_doi[doi] for doi in cited_dois}
    return markdown, figures, expected_dois, cited_ledger_by_doi


def _figure_manifest_record(path, manifest_directory, figure_max_height_mm):
    """Path record plus the geometry the journal page renders this raster at.

    Recording the true rendered width closes the gap where a height-capped
    figure silently displays narrower than the width its label sizes were
    QA'd against.
    """
    record = _manifest_path_record(path, manifest_directory)
    try:
        from PIL import Image
    except ImportError:
        return record
    with Image.open(path) as image:
        pixel_width, pixel_height = image.size
    rendered_width, rendered_height = rendered_figure_size_mm(
        pixel_width, pixel_height, max_height_mm=figure_max_height_mm
    )
    record.update({
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "rendered_width_mm": round(rendered_width, 2),
        "rendered_height_mm": round(rendered_height, 2),
    })
    return record


def write_release_manifest(
        manifest_path, *, review_path, ledger_path, pdf_path, html_document,
        release, columns, kicker, colophon, repo, compiled_date,
        figure_specs=(), figure_prompts=(), figure_inspections=(),
        figure_provenances=(), style="scientific",
        figure_max_height_mm=FIGURE_MAX_HEIGHT_MM, ref_leading=None,
        imprint="end", edition="journal", pull_quote=None, claims_audit=None,
        made_with="full",
        claim_receipts_path=None):
    """Bind every release input to the exact HTML and canonical PDF."""
    manifest_path = Path(manifest_path).resolve()
    manifest_directory = manifest_path.parent
    review_path = Path(review_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    markdown, figures, expected_dois, ledger_by_doi = validate_release_inputs(
        review_path, ledger_path, figure_specs, figure_prompts,
        figure_inspections, figure_provenances, claims_audit, claim_receipts_path
    )
    inputs = {
        "review": _manifest_path_record(review_path, manifest_directory),
        "ledger": _manifest_path_record(ledger_path, manifest_directory),
        "figures": [
            _figure_manifest_record(path, manifest_directory, figure_max_height_mm)
            for path in figures
        ],
        "figure_specs": [
            _manifest_path_record(path, manifest_directory) for path in figure_specs
        ],
        "figure_prompts": [
            _manifest_path_record(path, manifest_directory) for path in figure_prompts
        ],
        "figure_inspections": [
            _manifest_path_record(path, manifest_directory)
            for path in figure_inspections
        ],
        "figure_provenances": [
            _manifest_path_record(path, manifest_directory)
            for path in figure_provenances
        ],
    }
    claim_summary = None
    if claims_audit is not None:
        inputs["claims_audit"] = _manifest_path_record(
            claims_audit, manifest_directory)
        claim_summary = claim_receipts.summarize_audit(
            load_claims_audit(claims_audit))
    if claim_receipts_path is not None:
        inputs["claim_receipts"] = _manifest_path_record(
            claim_receipts_path, manifest_directory)
    html_bytes = html_document.encode("utf-8")
    manifest = {
        "schema_version": 1,
        "release": release,
        "compiled_date": compiled_date,
        "render": {
            "columns": columns,
            "figure_max_height_mm": float(figure_max_height_mm),
            "page_content_width_mm": PAGE_CONTENT_WIDTH_MM,
            "ref_leading": (
                float(ref_leading) if ref_leading is not None else None
            ),
            "edition": edition,
            "pull_quote": pull_quote,
            "imprint": imprint,
            "made_with": made_with,
            "style": _normalized_style(style),
            "kicker": kicker,
            "colophon": colophon,
            "repo": repo,
            "html_bytes": len(html_bytes),
            "html_sha256": sha256_bytes(html_bytes),
        },
        "inputs": inputs,
        "artifact": {
            "pdf": _manifest_path_record(pdf_path, manifest_directory),
        },
        "expected": {
            "unique_dois": expected_dois,
            "reference_entries": len([
                doi for doi in expected_dois if doi in ledger_by_doi
            ]),
            "correction_notices": len([
                doi for doi in expected_dois if doi not in ledger_by_doi
            ]),
            "figures": len(figures),
            "cited_ledger_keys": [
                str(ledger_by_doi[doi].get("key") or doi)
                for doi in expected_dois if doi in ledger_by_doi
            ],
            "claim_pairs": claim_summary["pairs"] if claim_summary else 0,
            "claim_summary": claim_summary,
        },
    }
    atomic_write_json(manifest_path, manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", help="finished review markdown (from format_references.py)")
    ap.add_argument("--out", help="output path (.html or .pdf)")
    ap.add_argument("--pdf", action="store_true", help="render a PDF (implied by an .pdf --out)")
    ap.add_argument("--columns", type=int, choices=[1, 2], default=2, help="body columns on paper (default 2)")
    ap.add_argument(
        "--style", choices=("scientific", "prose", "popsci", "bullets", "eli5"),
        default="scientific",
        help="writing style printed in the PDF metadata grid (default scientific)",
    )
    ap.add_argument("--kicker", default="Review", help="kicker label above the title (e.g. 'Review · Immunology')")
    ap.add_argument("--colophon", help="override the footer line")
    ap.add_argument(
        "--release",
        help="version shown at the right edge of the masthead "
             "(default: packaged VERSION)",
    )
    ap.add_argument("--repo", help="repository linked from the masthead descriptor (default: git origin remote)")
    ap.add_argument("--compiled-date", help="fixed YYYY-MM-DD compilation date (default: today)")
    ap.add_argument("--html-sidecar", action="store_true",
                    help="also write HTML beside a PDF (off by default)")
    ap.add_argument(
        "--release-manifest",
        help="write immutable release lineage JSON (PDF only; requires --ledger)",
    )
    ap.add_argument("--ledger", help="verified sources.json for release lineage")
    ap.add_argument("--figure-spec", action="append", default=[],
                    help="figure specification JSON (repeat once per figure)")
    ap.add_argument("--figure-prompt", action="append", default=[],
                    help="saved generation prompt (repeat once per figure)")
    ap.add_argument("--figure-inspection", action="append", default=[],
                    help="visual inspection JSON (repeat once per figure)")
    ap.add_argument("--figure-provenance", action="append", default=[],
                    help="generation provenance JSON (repeat once per figure)")
    ap.add_argument("--claims-audit",
                    help="checked claims_audit.json from verify_claims.py; "
                         "renders the terminal Claim receipts section and the "
                         "colophon audit line, and is hashed into the release "
                         "manifest (a contradicted or pending pair is a hard error)")
    ap.add_argument("--claim-receipts",
                    help="the receipts markdown written by verify_claims.py receipts; "
                         "delivered beside the PDF and hashed into the release manifest")
    ap.add_argument(
        "--ref-leading", type=float, default=None, metavar="LH",
        help="reference-list line-height, bounded "
             f"{MIN_REF_LEADING}-{DEFAULT_REF_LEADING} (type size never "
             "changes); leave unset to let the exporter tighten it once, "
             "within the same bounds, only to pull a small terminal reference "
             "spill back onto the previous page",
    )
    ap.add_argument(
        "--figure-max-height", type=float, default=FIGURE_MAX_HEIGHT_MM,
        metavar="MM",
        help="figure height cap on paper in mm, bounded 60-120 "
             f"(default {FIGURE_MAX_HEIGHT_MM:g}); recorded in the release "
             "manifest so QA evaluates the true rendered geometry",
    )
    ap.add_argument(
        "--edition", choices=tuple(EDITIONS), default=None,
        help="paper identity: 'journal' (canonical, default for scientific/"
             "bullets/eli5) or 'salon' (literary edition, default for "
             "popsci); the evidence contract is identical in every edition",
    )
    ap.add_argument(
        "--pull-quote", metavar="TEXT",
        help="salon edition only: one verbatim sentence from the article "
             "body, set as the column-spanning pull quote before the "
             "paragraph that contains it; a quote that is not verbatim body "
             "text is a hard error",
    )
    ap.add_argument("--check-pdf-runtime", action="store_true",
                    help="validate the canonical WeasyPrint runtime and exit")
    args = ap.parse_args()

    if args.check_pdf_runtime:
        from weasyprint_export import require_runtime
        print(json.dumps(require_runtime(), sort_keys=True))
        return
    if not args.src or not args.out:
        ap.error("--in and --out are required unless --check-pdf-runtime is used")

    with open(args.src, encoding="utf-8") as stream:
        md = stream.read()
    base_dir = os.path.dirname(os.path.abspath(args.src))
    claims_audit = None
    if args.claims_audit:
        try:
            claims_audit = load_claims_audit(args.claims_audit)
        except ValueError as exc:
            ap.error(str(exc))
    elif claim_receipts.receipts_block(md):
        ap.error("review carries a Receipts block; pass the matching --claims-audit")

    want_pdf = args.pdf or args.out.lower().endswith(".pdf")
    if want_pdf:
        if not args.ledger or not args.claims_audit or not args.claim_receipts:
            ap.error("PDF delivery requires --ledger, --claims-audit and --claim-receipts; finish the assertion audit first")
        try:
            validate_release_inputs(
                args.src, args.ledger, args.figure_spec, args.figure_prompt,
                args.figure_inspection, args.figure_provenance,
                args.claims_audit, args.claim_receipts,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            ap.error(str(exc))
        from weasyprint_export import write_pdf
        release = args.release or detect_release(os.path.dirname(os.path.abspath(__file__))) or "dev"
        compiled_date = args.compiled_date or datetime.date.today().isoformat()
        if args.repo is None:
            _repo_label, detected_repo = detect_repo(
                os.path.dirname(os.path.abspath(__file__))
            )
            effective_repo = detected_repo or None
        else:
            effective_repo = args.repo
        try:
            page, result, effective = render_pdf_rebalanced(
                md, args.out, columns=args.columns, kicker=args.kicker,
                colophon=args.colophon, base_dir=base_dir,
                release=release, repo=effective_repo,
                compiled_date=compiled_date,
                style=args.style, figure_max_height_mm=args.figure_max_height,
                ref_leading=args.ref_leading, edition=args.edition,
                pull_quote=args.pull_quote, claims_audit=claims_audit,
            )
        except ValueError as exc:
            ap.error(str(exc))
        effective_ref_leading = effective["ref_leading"]
        effective_imprint = effective["imprint"]
        if effective["rebalanced"]:
            spill = effective["spill"]
            print(
                f"Rebalanced: {spill} spilled terminal entr"
                f"{'y' if spill == 1 else 'ies'} pulled back — "
                + effective["note"],
                file=sys.stderr,
            )
        if args.html_sidecar:
            html_side = os.path.splitext(args.out)[0] + ".html"
            with open(html_side, "w", encoding="utf-8") as stream:
                stream.write(page)
            suffix = f" and {html_side}"
        else:
            suffix = ""
        if args.release_manifest:
            write_release_manifest(
                args.release_manifest,
                review_path=args.src,
                ledger_path=args.ledger,
                pdf_path=args.out,
                html_document=page,
                release=release,
                columns=args.columns,
                kicker=args.kicker,
                colophon=args.colophon,
                repo=effective_repo,
                compiled_date=compiled_date,
                figure_specs=args.figure_spec,
                figure_prompts=args.figure_prompt,
                figure_inspections=args.figure_inspection,
                figure_provenances=args.figure_provenance,
                style=args.style,
                figure_max_height_mm=args.figure_max_height,
                ref_leading=effective_ref_leading,
                imprint=effective_imprint,
                made_with=effective["made_with"],
                edition=resolve_edition(args.style, args.edition),
                pull_quote=args.pull_quote,
                claims_audit=args.claims_audit,
                claim_receipts_path=args.claim_receipts,
            )
            suffix += f" and {args.release_manifest}"
        print(
            f"Wrote {args.out} (via {result['renderer']}, sha256 {result['sha256']}){suffix}",
            file=sys.stderr,
        )
    else:
        try:
            page = build_html(
                md, columns=args.columns, kicker=args.kicker,
                colophon=args.colophon, base_dir=base_dir,
                release=args.release, repo=args.repo,
                compiled_date=args.compiled_date, style=args.style,
                figure_max_height_mm=args.figure_max_height,
                edition=args.edition, pull_quote=args.pull_quote,
                claims_audit=claims_audit,
            )
        except ValueError as exc:
            ap.error(str(exc))
        with open(args.out, "w", encoding="utf-8") as stream:
            stream.write(page)
        print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
