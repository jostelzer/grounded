#!/usr/bin/env python3
"""Export a finished review to journal-styled HTML, and optionally PDF.

Takes the markdown produced by format_references.py and typesets it in the
GROUNDED journal identity: repeating masthead, provenance, metadata grid,
two-column body, full-width tables and figures, numbered cited captions, and a
compact reference list. Citations and figure cross-references stay hyperlinked;
DOIs stay resolvable.

    python3 export_review.py --in review.md --out review.html
    python3 export_review.py --in review.md --out review.pdf --pdf
    python3 export_review.py --in review.md --out review.html --columns 1 --title "..."

PDF needs a renderer on PATH: Chrome/Chromium/Edge (headless), or weasyprint.
Everything else is Python standard library only.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- markdown ---
# The skill emits a narrow, fixed subset: ##/### headings, **bold**, *italic*,
# [text](url) links, - bullets, | tables |, and > blockquotes. Parse exactly that.


def inline(s):
    """Inline markdown -> HTML. Escapes first, so source text can contain < or &."""
    s = html.escape(s, quote=False)
    # links before emphasis: link text may contain punctuation but not brackets
    s = re.sub(r"\[([^\]]+)\]\((https?://(?:[^\s()]|\([^\s()]*\))+|#[A-Za-z][A-Za-z0-9_-]*)\)",
               lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # bare urls (in the sources block) become links
    s = re.sub(r'(?<!["=>])(https?://[^\s<]+)(?![^<]*</a>)',
               lambda m: f'<a href="{html.escape(m.group(1), quote=True)}">{m.group(1)}</a>', s)
    return s


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def image_data_uri(path, base_dir):
    """Embed a local image as a data URI so the export is self-contained."""
    import base64
    p = path if os.path.isabs(path) else os.path.join(base_dir, path)
    ext = os.path.splitext(p)[1].lower()
    if ext not in MIME or not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return f"data:{MIME[ext]};base64," + base64.b64encode(f.read()).decode()


def to_html(md, base_dir="."):
    """Convert the review markdown to body HTML. Returns (title, lead, body)."""
    lines = md.split("\n")
    out, i = [], 0
    title, lead = None, None
    n_figs = 0
    pending_figure_id = None
    figure_ids = []
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

        anchor = re.match(r'^<a id="(fig-[a-z][a-z0-9-]*)"></a>$', s)
        if anchor:
            if pending_figure_id is not None:
                raise ValueError("figure anchor is not followed by a figure")
            pending_figure_id = anchor.group(1)
            i += 1
            continue

        if pending_figure_id is not None and not re.match(
                r"^!\[([^\]]*)\]\(([^)\s]+)\)$", s):
            raise ValueError("figure anchor is not followed by a figure")

        # provenance header line the examples carry: "> Unedited example output..."
        if s.startswith(">"):
            note = inline(s.lstrip("> ").strip())
            out.append(f'<p class="note">{note}</p>')
            i += 1
            continue

        if s.startswith("### "):
            out.append(f"<h2>{inline(s[4:])}</h2>")
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
                caption_list = "<ul>" + "".join(
                    f"<li>{inline(item)}</li>" for item in caption_bullets) + "</ul>"
            caption = (
                f'<figcaption><b class="figno">Figure {n_figs}.</b> '
                f'<b class="figtitle">{inline(cm.group(2))}</b>'
                f'{inline(cm.group(3) or "")}{caption_list}</figcaption>')
            i = k
            uri = image_data_uri(src, base_dir)
            if uri is None:
                print(f"warning: figure not embedded (missing or unsupported): {src}", file=sys.stderr)
                uri = html.escape(src, quote=True)
            out.append(
                f'<figure id="{figure_id}"><img src="{uri}" '
                f'alt="{html.escape(alt, quote=True)}">{caption}</figure>')
            continue

        if s.startswith("## "):
            if title is None:
                title = inline(s[3:])
            else:
                out.append(f"<h2>{inline(s[3:])}</h2>")
            i += 1
            continue

        if s.startswith("# "):
            if title is None:
                title = inline(s[2:])
            else:
                out.append(f"<h2>{inline(s[2:])}</h2>")
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
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            trs = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            continue

        # bullet list
        if s.startswith("- ") or s.startswith("* "):
            items = []
            while i < len(lines) and lines[i].strip()[:2] in ("- ", "* "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
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
            lead = (m.group(1), inline(re.sub(r"^\*\*(TL;DR|Abstract)\*\*\s*[—–-]?\s*", "", text)))
            continue
        if re.match(r"^\*\*Sources\*\*\s*$", text):
            out.append('<h2 class="refhead">References</h2><div class="refs">')
            continue
        out.append(f"<p>{inline(text)}</p>")

    body = "\n".join(out)
    if pending_figure_id is not None:
        raise ValueError("figure anchor is not followed by a figure")
    for figure_id in figure_ids:
        if f'href="#{figure_id}"' not in body:
            raise ValueError(
                "every figure must be referenced from the text: %s" % figure_id)
    if '<div class="refs">' in body:
        body += "</div>"
    return title, lead, body


# -------------------------------------------------------------------- css ---
# GROUNDED — the journal identity of this skill. Swiss-modern: grotesk furniture,
# serif body, one accent, the earth-ground chip. Tagline: "No floating claims."

ACCENT = "#ff4f1f"

# The earth-ground symbol ⏚ drawn as inline SVG so it can never fall back to a
# missing-glyph box in a PDF renderer. Accent-colored: it sits in an outline chip.
GND_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><g stroke="#ff4f1f" '
           'stroke-width="2.4" stroke-linecap="round" fill="none">'
           '<path d="M12 3v8"/><path d="M4 11h16"/><path d="M7.5 15.5h9"/>'
           '<path d="M10.5 20h3"/></g></svg>')

CSS = r"""
@page {
  size: A4; margin: 12mm 13mm 16mm 13mm;
  /* Page numbers render where @page margin boxes are supported (WeasyPrint);
     Chrome ignores them harmlessly. */
  @bottom-right { content: counter(page) " / " counter(pages);
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 7pt; color: #8a8a8a; }
}
:root {
  --ink: #141414; --muted: #6b6b6b; --faint: #9a9a9a; --rule: #e4e4e4;
  --accent: #ff4f1f; --bg: #fff;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Charter", "Iowan Old Style", Georgia, "Times New Roman", serif;
  font-size: 9.5pt; line-height: 1.5;
  text-align: justify; hyphens: auto; -webkit-hyphens: auto;
}
.sans, .strip, .provenance, .kicker, h1, .metagrid, .lead, h2, thead th,
.tablabel, figcaption, .refs, footer.colophon {
  font-family: -apple-system, "Helvetica Neue", "Helvetica", Arial, sans-serif;
}
/* The whole document lives in one table so the masthead strip in <thead>
   repeats at the top of every printed page (Chrome honors this). */
table.paper { width: 100%; border-collapse: collapse; max-width: 194mm; margin: 0 auto; }
table.paper > thead > tr > th { padding: 0 0 5mm; font-weight: normal; text-align: left; }
table.paper > tbody > tr > td { padding: 0; }
.strip {
  display: flex; align-items: stretch; border-bottom: .5px solid var(--ink);
  break-inside: avoid;
}
.strip .chip {
  background: none; border: 1.5px solid var(--accent);
  display: flex; align-items: center; padding: 5px 8px; width: 32px;
}
.strip .chip svg { width: 14px; height: 14px; display: block; }
.strip .mark {
  display: flex; align-items: center; padding: 0 10px;
  font-weight: 600; font-size: 9.5pt; letter-spacing: .3em; color: var(--ink);
}
.strip .tagline {
  display: flex; align-items: center; font-size: 6.3pt; font-weight: 600;
  letter-spacing: .13em; text-transform: uppercase; color: var(--muted);
}
.strip .issue {
  display: flex; align-items: center; margin-left: auto;
  font-size: 6.3pt; font-weight: 600; letter-spacing: .13em;
  text-transform: uppercase; color: var(--muted);
}
.provenance {
  margin: 0 0 12px; font-size: 6.5pt; font-weight: 600; letter-spacing: .11em;
  text-transform: uppercase; color: var(--faint); text-align: left;
}
.provenance a { color: var(--faint); border-bottom: none; }
.provenance b { color: var(--accent); font-weight: 700; }
.kicker {
  font-size: 7.5pt; font-weight: 800; letter-spacing: .24em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 6px; text-align: left;
}
h1 {
  font-size: 24pt; line-height: 1.1; margin: 0 0 12px; font-weight: 300;
  letter-spacing: -0.015em; max-width: 30em; text-align: left; hyphens: none;
}
.metagrid {
  display: grid; grid-template-columns: repeat(4, 1fr);
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
.body.cols { column-count: 2; column-gap: 8mm; }
h2 {
  font-size: 9pt; font-weight: 600; line-height: 1.3; letter-spacing: 0;
  margin: 12px 0 4px; color: var(--ink);
  break-after: avoid; page-break-after: avoid; text-align: left; hyphens: none;
}
h2::before {
  counter-increment: sec; content: counter(sec, decimal-leading-zero);
  color: var(--accent); margin-right: 7px; font-variant-numeric: tabular-nums;
}
.body > h2:first-child, .body.cols > h2:first-child { margin-top: 0; }
h2.refhead {
  border-top: 1px solid var(--ink); padding-top: 6px; margin-top: 16px;
  column-span: all; font-size: 9pt;
}
h2.refhead::before { content: none; counter-increment: none; }
h2.refhead small { font-weight: 600; font-size: 6.3pt; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted); float: right; margin-top: 2px; }
p { margin: 0 0 6.5px; orphans: 2; widows: 2; }
ul { margin: 0 0 9px; padding-left: 1.05em; }
li { margin: 0 0 4.5px; break-inside: avoid; }
a { color: inherit; text-decoration: none; border-bottom: .5px solid rgba(255,79,31,.55); }
a:hover { border-bottom-color: var(--accent); }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: .9em; }
strong { letter-spacing: 0; }
/* Tables span the full page width (interrupting the columns, as journals do)
   and wrap their cell content — a table is never clipped or truncated. */
.tablewrap { column-span: all; break-inside: avoid; margin: 9px 0 11px; overflow: visible; }
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
.refs { font-size: 7.2pt; line-height: 1.5; color: #333; text-align: left; }
.refs p { margin: 0 0 5px; padding-left: 1.2em; text-indent: -1.2em; break-inside: avoid; }
.refs a { border-bottom: none; color: var(--muted); word-break: break-all; }
/* Figures, like tables, span the full page width and are never clipped. */
figure { column-span: all; margin: 10px 0 12px; break-inside: avoid; }
figure img { display: block; width: 100%; height: auto; }
figcaption { font-size: 7.4pt; color: var(--muted); margin-top: 5px;
  text-align: left; line-height: 1.45; }
figcaption .figno, figcaption .figtitle { color: var(--ink); }
figcaption .figno, figcaption .figtitle, .tablabel b { font-weight: 800; }
figcaption .figno::first-letter { color: var(--ink); }
figcaption ul { margin: 4px 0 0; padding-left: 1.15em; }
figcaption li { margin: 0 0 2px; break-inside: auto; }
.tomb { text-align: right; color: var(--accent); font-size: 11pt;
  margin: 4px 0 0; column-span: all; }
footer.colophon {
  margin-top: 14px; padding-top: 6px; border-top: .5px solid var(--ink);
  font-size: 6.5pt; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
  color: var(--faint); display: flex; justify-content: space-between; gap: 12px;
  text-align: left;
}
footer.colophon a { color: var(--faint); border-bottom: none; }
@media screen {
  body { padding: 10mm 0; background: #f2f2f2; }
  table.paper { background: #fff; box-shadow: 0 2px 18px rgba(0,0,0,.12); }
  table.paper > thead > tr > th { padding: 10mm 10mm 5mm; }
  table.paper > tbody > tr > td { padding: 0 10mm 12mm; }
}
@media screen and (max-width: 700px) {
  body { padding: 0; }
  table.paper > thead > tr > th { padding: 5mm 5mm 4mm; }
  table.paper > tbody > tr > td { padding: 0 5mm 8mm; }
  .body.cols { column-count: 1; }
  h1 { font-size: 16pt; }
  .metagrid { grid-template-columns: repeat(2, 1fr); }
  .metagrid > div { border-bottom: 1px solid var(--rule); }
  .tablewrap { overflow-x: auto; }
  .strip .tagline { display: none; }
}
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_text}</title>
<style>{css}</style>
</head><body>
<table class="paper">
<thead><tr><th>
  <div class="strip">
    <span class="chip">{gnd}</span>
    <span class="mark">GROUNDED</span>
    <span class="tagline">No floating claims.</span>
    <span class="issue">{issue}</span>
  </div>
</th></tr></thead>
<tbody><tr><td>
<div class="provenance">Agentically generated scientific review&nbsp;&nbsp;·&nbsp;&nbsp;<b>grounded</b> {version}&nbsp;&nbsp;·&nbsp;&nbsp;<a href="{repo_url}">{repo_label}</a></div>
<div class="kicker">{kicker}</div>
<h1>{title}</h1>
{metagrid}
{lead}
<div class="body{cols}">
{body}
<div class="tomb">&#8718;</div>
</div>
<footer class="colophon"><span>{colophon}</span><span style="white-space:nowrap">grounded {version}</span></footer>
</td></tr></tbody>
</table>
</body></html>
"""


def detect_release(script_dir):
    """Latest git tag of the skill repo, e.g. 'v1.8.0'. Empty string if unknown."""
    try:
        r = subprocess.run(["git", "-C", script_dir, "describe", "--tags", "--abbrev=0"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
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


def build_html(md, columns=2, kicker="Review", colophon=None, base_dir=".",
               release=None, repo=None):
    import datetime
    import urllib.parse

    title, lead, body = to_html(md, base_dir)
    title = title or "Scientific review"
    lead_html = ""
    if lead:
        label = "Abstract" if lead[0] == "Abstract" else "Summary"
        lead_html = f'<p class="lead"><b>{label}</b>{lead[1]}</p>'

    # inline citation URLs percent-encode parens, sources-block URLs don't;
    # normalize both forms before deduplicating
    n_refs = len({urllib.parse.unquote(d).lower().rstrip(").,;*_")
                  for d in re.findall(r"https?://doi\.org/([^\s<>]+)", md)})

    # masthead furniture: the export date, top right of every page
    today = datetime.date.today()
    issue = today.strftime("%-d %B %Y")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if release is None:
        release = detect_release(script_dir)
    if repo is None:
        repo_label, repo_url = detect_repo(script_dir)
    else:
        repo_label = re.sub(r"^https?://", "", repo)
        repo_url = repo if repo.startswith("http") else f"https://{repo}"
    release = release or "dev"
    repo_label = repo_label or "local build"
    repo_url = repo_url or "#"

    # token estimate for the whole document (~4 chars per token)
    tokens = max(1, round(len(md) / 4))
    tok = f"≈{tokens / 1000:.1f}k" if tokens >= 1000 else f"≈{tokens}"

    cells = [
        ("References", f"<i>{n_refs}</i> verified" if n_refs else "—"),
        ("Tokens", tok),
        ("Verification", "Crossref"),
        ("Compiled", today.strftime("%-d %b %Y")),
    ]
    metagrid = '<div class="metagrid">' + "".join(
        f"<div><b>{h}</b><span>{v}</span></div>" for h, v in cells) + "</div>"

    if n_refs:
        body = body.replace(
            '<h2 class="refhead">References</h2>',
            f'<h2 class="refhead">References <small>{n_refs} · verified via Crossref</small></h2>')

    if colophon is None:
        colophon = ("Agentically generated · every citation resolved and "
                    "retraction-screened via Crossref")
    plain_title = re.sub(r"<[^>]+>", "", title)
    return PAGE.format(
        title_text=plain_title, css=CSS, gnd=GND_SVG, issue=html.escape(issue),
        version=html.escape(release), repo_url=html.escape(repo_url, quote=True),
        repo_label=html.escape(repo_label), kicker=html.escape(kicker),
        title=title, metagrid=metagrid, lead=lead_html,
        cols=" cols" if columns == 2 else "", body=body,
        colophon=html.escape(colophon))


# -------------------------------------------------------------------- pdf ---

CHROME_NAMES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "microsoft-edge", "brave-browser",
]
CHROME_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def find_chrome():
    for n in CHROME_NAMES:
        p = shutil.which(n)
        if p:
            return p
    for p in CHROME_APPS:
        if os.path.exists(p):
            return p
    return None


def write_pdf(html_text, out_path):
    """Render HTML to PDF with headless Chrome or weasyprint. Returns the tool used."""
    target = os.path.abspath(out_path)
    target_dir = os.path.dirname(target)
    chrome = find_chrome()
    if chrome:
        with tempfile.TemporaryDirectory(prefix=".grounded-", dir=target_dir) as td:
            src = os.path.join(td, "review.html")
            rendered = os.path.join(td, "rendered.pdf")
            with open(src, "w") as f:
                f.write(html_text)
            cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                   "--no-pdf-header-footer", f"--print-to-pdf={rendered}",
                   "file://" + src]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and is_pdf(rendered):
                os.replace(rendered, target)
                return os.path.basename(chrome)
            # older builds reject --no-pdf-header-footer
            cmd.remove("--no-pdf-header-footer")
            if os.path.exists(rendered):
                os.unlink(rendered)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and is_pdf(rendered):
                os.replace(rendered, target)
                return os.path.basename(chrome)
            raise RuntimeError(f"chrome failed to write a PDF: {r.stderr.strip()[:300]}")
    if shutil.which("weasyprint"):
        with tempfile.TemporaryDirectory(prefix=".grounded-", dir=target_dir) as td:
            src = os.path.join(td, "review.html")
            rendered = os.path.join(td, "rendered.pdf")
            with open(src, "w") as f:
                f.write(html_text)
            r = subprocess.run(["weasyprint", src, rendered], capture_output=True, text=True, timeout=180)
            if r.returncode != 0 or not is_pdf(rendered):
                raise RuntimeError(f"weasyprint failed: {r.stderr.strip()[:300]}")
            os.replace(rendered, target)
            return "weasyprint"
    raise RuntimeError(
        "no PDF renderer found. Install Chrome/Chromium or weasyprint, or export "
        "HTML and print to PDF from the browser (Cmd/Ctrl-P).")


def is_pdf(path):
    """Return whether *path* is a non-empty PDF, not a stale output sentinel."""
    if not os.path.exists(path) or os.path.getsize(path) < 5:
        return False
    with open(path, "rb") as f:
        return f.read(5) == b"%PDF-"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True, help="finished review markdown (from format_references.py)")
    ap.add_argument("--out", required=True, help="output path (.html or .pdf)")
    ap.add_argument("--pdf", action="store_true", help="render a PDF (implied by an .pdf --out)")
    ap.add_argument("--columns", type=int, choices=[1, 2], default=2, help="body columns on paper (default 2)")
    ap.add_argument("--kicker", default="Review", help="kicker label above the title (e.g. 'Review · Immunology')")
    ap.add_argument("--colophon", help="override the footer line")
    ap.add_argument("--release", help="version shown in the provenance line (default: latest git tag)")
    ap.add_argument("--repo", help="repository link in the provenance line (default: git origin remote)")
    args = ap.parse_args()

    md = open(args.src).read()
    page = build_html(md, columns=args.columns, kicker=args.kicker, colophon=args.colophon,
                      base_dir=os.path.dirname(os.path.abspath(args.src)),
                      release=args.release, repo=args.repo)

    want_pdf = args.pdf or args.out.lower().endswith(".pdf")
    if want_pdf:
        tool = write_pdf(page, args.out)
        html_side = os.path.splitext(args.out)[0] + ".html"
        with open(html_side, "w") as f:
            f.write(page)
        print(f"Wrote {args.out} (via {tool}) and {html_side}", file=sys.stderr)
    else:
        with open(args.out, "w") as f:
            f.write(page)
        print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
