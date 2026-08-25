#!/usr/bin/env python3
"""Export a finished review to journal-styled HTML, and optionally PDF.

Takes the markdown produced by format_references.py and typesets it the way a
journal does: a title block, a lead paragraph, two-column body on paper sizes,
proper small-caps section heads, hairline-ruled tables, and a reference list in
smaller type. Citations stay hyperlinked; DOIs stay resolvable.

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
    s = re.sub(r"\[([^\]]+)\]\((https?://(?:[^\s()]|\([^\s()]*\))+)\)",
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


def to_html(md):
    """Convert the review markdown to body HTML. Returns (title, lead, body)."""
    lines = md.split("\n")
    out, i = [], 0
    title, lead = None, None
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

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
        while i < len(lines) and lines[i].strip() and not re.match(r"^[#\-*>|]", lines[i].strip()):
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
    if '<div class="refs">' in body:
        body += "</div>"
    return title, lead, body


# -------------------------------------------------------------------- css ---

CSS = r"""
@page { size: A4; margin: 20mm 16mm 18mm 16mm; }
:root {
  --ink: #1a1a1a; --muted: #5c5c5c; --rule: #d4d4d4;
  --accent: #7a2018; --bg: #fff; --panel: #faf9f7;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Source Serif 4", "Charter", "Iowan Old Style", Georgia, "Times New Roman", serif;
  font-size: 9.5pt; line-height: 1.45;
  font-variant-numeric: oldstyle-figures proportional-nums;
  text-align: justify; hyphens: auto; -webkit-hyphens: auto;
}
.sheet { max-width: 190mm; margin: 0 auto; padding: 14mm 12mm 18mm; }
header.masthead {
  border-top: 3px solid var(--ink); border-bottom: 1px solid var(--rule);
  padding: 6px 0 10px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
}
.masthead .kicker {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 7.5pt; letter-spacing: .16em; text-transform: uppercase;
  color: var(--muted); font-weight: 600;
}
h1 {
  font-size: 19pt; line-height: 1.18; margin: 2px 0 10px; font-weight: 600;
  letter-spacing: -0.01em; max-width: 34em; text-align: left; hyphens: none;
}
.lead {
  font-size: 10pt; line-height: 1.45; margin: 0 0 4px;
  padding: 10px 14px; background: var(--panel);
  border-left: 3px solid var(--accent);
}
.lead b { font-variant: small-caps; letter-spacing: .04em; }
.note {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 7.5pt; color: var(--muted); margin: 10px 0 0;
}
.rule { border: 0; border-top: 1px solid var(--rule); margin: 14px 0 4px; }
.body { margin-top: 14px; }
.body.cols { column-count: 2; column-gap: 9mm; column-rule: 1px solid #ebebeb; }
h2 {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 8.75pt; font-weight: 700; line-height: 1.35;
  letter-spacing: .01em; margin: 14px 0 5px; color: var(--accent);
  break-after: avoid; page-break-after: avoid; text-align: left; hyphens: none;
}
h2:first-child { margin-top: 0; }
h2.refhead {
  color: var(--ink); border-top: 1px solid var(--rule); padding-top: 8px;
  margin-top: 18px; font-variant: small-caps; letter-spacing: .06em; font-size: 10pt;
}
p { margin: 0 0 7px; orphans: 2; widows: 2; }
ul { margin: 0 0 9px; padding-left: 1.05em; }
li { margin: 0 0 4.5px; break-inside: avoid; }
a { color: inherit; text-decoration: none; border-bottom: .5px solid rgba(122,32,24,.45); }
a:hover { border-bottom-color: var(--accent); }
code { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: .9em; }
/* Tables span the full page width (interrupting the columns, as journals do)
   and wrap their cell content — a table is never clipped or truncated. */
.tablewrap { column-span: all; break-inside: avoid; margin: 10px 0 12px; overflow: visible; }
table { width: 100%; border-collapse: collapse; font-size: 7.8pt; line-height: 1.35; }
thead th {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 7pt; text-transform: uppercase; letter-spacing: .06em;
  text-align: left; font-weight: 700;
  border-top: 1.5px solid var(--ink); border-bottom: .75px solid var(--ink);
  padding: 5px 7px 4px; hyphens: none;
}
tbody td {
  padding: 4px 7px; border-bottom: .5px solid #e8e8e8; vertical-align: top;
  text-align: left; overflow-wrap: break-word; hyphens: auto;
}
tbody tr:last-child td { border-bottom: 1.5px solid var(--ink); }
.refs { font-size: 8pt; line-height: 1.4; color: #333; text-align: left; }
.refs p { margin: 0 0 5px; padding-left: 1.1em; text-indent: -1.1em; }
.refs a { border-bottom: none; color: var(--muted); word-break: break-all; }
figure { margin: 10px 0; break-inside: avoid; }
figure img { width: 100%; height: auto; }
figcaption { font-size: 8pt; color: var(--muted); margin-top: 5px; }
footer.colophon {
  margin-top: 16px; padding-top: 7px; border-top: 1px solid var(--rule);
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 7.5pt; color: var(--muted);
}
@media screen and (max-width: 700px) {
  .sheet { padding: 6mm; }
  .body.cols { column-count: 1; }
  h1 { font-size: 16pt; }
  .tablewrap { overflow-x: auto; }
}
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_text}</title>
<style>{css}</style>
</head><body>
<div class="sheet">
<header class="masthead">
  <div class="kicker">{kicker}</div>
  <div class="kicker">{right}</div>
</header>
<h1>{title}</h1>
{lead}
<hr class="rule">
<div class="body{cols}">
{body}
</div>
<footer class="colophon">{colophon}</footer>
</div>
</body></html>
"""


def build_html(md, columns=2, kicker="Scientific review", colophon=None):
    title, lead, body = to_html(md)
    title = title or "Scientific review"
    lead_html = ""
    if lead:
        label = "Abstract" if lead[0] == "Abstract" else "Summary"
        lead_html = f'<p class="lead"><b>{label}</b> — {lead[1]}</p>'
    import urllib.parse
    # inline citation URLs percent-encode parens, sources-block URLs don't;
    # normalize both forms before deduplicating
    n_refs = len({urllib.parse.unquote(d).lower().rstrip(").,;")
                  for d in re.findall(r"https?://doi\.org/([^\s<>]+)", md)})
    right = f"{n_refs} verified references" if n_refs else ""
    if colophon is None:
        colophon = ("Every citation in this review was resolved and verified through Crossref, "
                    "including retraction screening. Generated with the scientific-review skill.")
    plain_title = re.sub(r"<[^>]+>", "", title)
    return PAGE.format(
        title_text=plain_title, css=CSS, kicker=html.escape(kicker), right=right,
        title=title, lead=lead_html, cols=" cols" if columns == 2 else "",
        body=body, colophon=html.escape(colophon))


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
    chrome = find_chrome()
    if chrome:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "review.html")
            with open(src, "w") as f:
                f.write(html_text)
            cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                   "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(out_path)}",
                   "file://" + src]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return os.path.basename(chrome)
            # older builds reject --no-pdf-header-footer
            cmd.remove("--no-pdf-header-footer")
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return os.path.basename(chrome)
            raise RuntimeError(f"chrome failed to write a PDF: {r.stderr.strip()[:300]}")
    if shutil.which("weasyprint"):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "review.html")
            with open(src, "w") as f:
                f.write(html_text)
            r = subprocess.run(["weasyprint", src, out_path], capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                raise RuntimeError(f"weasyprint failed: {r.stderr.strip()[:300]}")
            return "weasyprint"
    raise RuntimeError(
        "no PDF renderer found. Install Chrome/Chromium or weasyprint, or export "
        "HTML and print to PDF from the browser (Cmd/Ctrl-P).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True, help="finished review markdown (from format_references.py)")
    ap.add_argument("--out", required=True, help="output path (.html or .pdf)")
    ap.add_argument("--pdf", action="store_true", help="render a PDF (implied by an .pdf --out)")
    ap.add_argument("--columns", type=int, choices=[1, 2], default=2, help="body columns on paper (default 2)")
    ap.add_argument("--kicker", default="Scientific review", help="masthead label")
    ap.add_argument("--colophon", help="override the footer line")
    args = ap.parse_args()

    md = open(args.src).read()
    page = build_html(md, columns=args.columns, kicker=args.kicker, colophon=args.colophon)

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
