#!/usr/bin/env python3
"""
Resolve [@key] citations in a draft and build the reference list from bibliographically verified ledger entries.

Write the review with citation keys from the ledger, e.g.:
    ... no superiority over teaching-as-usual at one year [@Kuyken2022effectiveness].
    ... earlier meta-analyses were more optimistic [@Dunning2018research; @Caldwell2019school].

Figures use stable IDs in their captions and stable reference tokens in the
body. Numbering and links are resolved in order of appearance:

    ... the pathway is summarized in {{figure:mechanism}}.

    ![Specific visual description](mechanism.png)
    **Figure {#mechanism}. A transient signal builds memory.** Caption text [@Paper2024].

Then run:
    python3 format_references.py --ledger sources.json --draft review_draft.md --out review.md --style vancouver
    python3 format_references.py --ledger sources.json --draft review_draft.md --out review.md --style apa

Styles: bracket (linked author-year; default), vancouver (numbered, order of
first appearance), apa (author-year), nature (numbered, superscript).

Rules enforced:
  * A key that is not in the ledger, or whose status is not 'verified', is a hard error. Run
    verify_citations.py first. Nothing unverified can reach the reference list.
  * Reference entries are built from the Crossref 'canonical' metadata saved by verify_citations.py,
    never from the model's memory.
  * Every entry ends with its DOI link so a reader can check it.
  * The verifier has already checked Crossref's publisher and Retraction Watch update metadata;
    no service-status notes or per-reference warning symbols are added to the review. The one
    factual annotation allowed: when the verifier recorded a published correction
    (corrigendum/erratum), the reference entry ends with a linked "Correction: <doi>." note.
  * Every Markdown image has a unique stable figure ID, a cited caption, and a
    body cross-reference; numbering and anchors are generated deterministically.
  * In default chat output, citation links follow the supported words and
    precede sentence-ending punctuation.

Outputs the finished markdown and prints a citation count summary (refs used, refs in ledger unused).
"""
import argparse
import html
import json
import re
import sys
from urllib.parse import quote


FIGURE_ID = r"[a-z][a-z0-9-]*"
FIGURE_IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)$")
FIGURE_CAPTION_RE = re.compile(
    r"^\*\*Figure\s+\{#(?P<id>" + FIGURE_ID +
    r")\}\.\s*(?P<title>.+?)\*\*(?P<body>\s+.+)?$")
FIGURE_TOKEN_RE = re.compile(r"\{\{figure:(?P<id>" + FIGURE_ID + r")\}\}")
CITATION_KEY = r"\[@[^\]\n]+\]"
CHAT_CITATION_AFTER_PUNCTUATION_RE = re.compile(
    r"(?P<punct>[.!?])(?P<closer>[”’\"']?)(?P<space>[ \t]+)"
    r"(?P<cites>" + CITATION_KEY +
    r"(?:(?:,[ \t]*|[ \t]+)" + CITATION_KEY + r")*)"
)


def normalize_chat_citation_punctuation(text):
    """Put sentence-ending punctuation after default chat citation keys.

    Drafts occasionally arrive as ``claim. [@source]``. The default linked
    author-year form reads as part of the sentence, so its correct Markdown is
    ``claim [@source].`` The journal renderer deliberately reverses that visual
    order later for its numeric superscripts.
    """
    return CHAT_CITATION_AFTER_PUNCTUATION_RE.sub(
        lambda match: (
            match.group("closer") + match.group("space")
            + match.group("cites") + match.group("punct")
        ),
        text,
    )


def resolve_figures(text):
    """Validate figure blocks and resolve stable IDs to numbered links.

    Draft syntax deliberately keeps numbering out of the author's hands. Every
    Markdown image must be followed by a caption with a stable ID and at least
    one ledger citation. Every declared figure must be referenced from the body.
    The returned Markdown contains a hidden HTML anchor, a visible numbered
    caption, and clickable ``Figure N`` body links.
    """
    lines = text.split("\n")
    out = []
    figures = []
    by_id = {}
    errors = []
    i = 0

    while i < len(lines):
        image = FIGURE_IMAGE_RE.match(lines[i].strip())
        if not image:
            out.append(lines[i])
            i += 1
            continue

        image_line = lines[i]
        j = i + 1
        blanks = []
        while j < len(lines) and not lines[j].strip():
            blanks.append(lines[j])
            j += 1
        caption_line = lines[j].strip() if j < len(lines) else ""
        caption = FIGURE_CAPTION_RE.match(caption_line)
        if not caption:
            errors.append(
                "every figure must be followed by a caption like "
                "'**Figure {#stable-id}. Declarative title.** Caption [@source].'")
            out.append(image_line)
            out.extend(blanks)
            i = j
            continue

        figure_id = caption.group("id")
        if figure_id in by_id:
            errors.append("duplicate figure id: %s" % figure_id)
        number = len(figures) + 1
        record = {"id": figure_id, "number": number,
                  "title": caption.group("title").strip()}
        figures.append(record)
        by_id.setdefault(figure_id, record)

        k = j + 1
        caption_bullets = []
        while k < len(lines) and lines[k].strip().startswith("- "):
            caption_bullets.append(lines[k])
            k += 1
        caption_payload = "\n".join([caption_line] + caption_bullets)
        if not caption.group("body") and not caption_bullets:
            errors.append("figure caption has no explanatory body: %s" % figure_id)
        if not re.search(r"\[(@[^\]]+)\]", caption_payload):
            errors.append("figure caption has no ledger citation: %s" % figure_id)

        out.append('<a id="fig-%s"></a>' % figure_id)
        out.append(image_line)
        out.extend(blanks)
        out.append("**Figure %d. %s**%s" % (
            number, caption.group("title").strip(), caption.group("body") or ""))
        out.extend(caption_bullets)
        i = k

    raw_tokens = re.findall(r"\{\{figure:([^}]+)\}\}", text)
    for token in raw_tokens:
        if not re.fullmatch(FIGURE_ID, token):
            errors.append("invalid figure reference id: %s" % token)
        elif token not in by_id:
            errors.append("unknown figure reference: %s" % token)
    used = set(token for token in raw_tokens if token in by_id)
    for record in figures:
        if record["id"] not in used:
            errors.append("figure is never referenced from the text: %s" % record["id"])

    resolved = "\n".join(out)

    def replace_token(match):
        record = by_id.get(match.group("id"))
        if record is None:
            return match.group(0)
        return "[Figure %d](#fig-%s)" % (record["number"], record["id"])

    return FIGURE_TOKEN_RE.sub(replace_token, resolved), errors, figures


def clean(t):
    """Unescape HTML entities and strip markup from Crossref strings."""
    return re.sub(r"<[^>]+>", "", html.unescape(t or "")).strip()


def doi_href(doi):
    """Return a Markdown/HTML-safe resolver URL for an arbitrary DOI.

    DOI suffixes may legally contain characters such as parentheses, angle
    brackets, or question marks. They must remain part of the path rather than
    being interpreted as Markdown/HTML syntax or URL query delimiters.
    """
    return "https://doi.org/" + quote(doi, safe="/:;,-._~")


def is_verified(entry):
    verification = entry.get("verification") or {}
    return (
        entry.get("status") == "verified"
        and bool(entry.get("canonical"))
        and verification.get("bibliographic_status") == "verified"
        and verification.get("retraction_status") == "clear"
    )


def correction_note(entry):
    """Factual note appended to a reference entry when a published correction exists.

    Non-blocking by design: the verifier records corrigenda/errata in
    ``verification.correction_notices`` without failing the citation, and the
    reader gets a plain pointer to the correction notice.
    """
    notices = (entry.get("verification") or {}).get("correction_notices") or []
    dois = sorted({n.get("doi") for n in notices if n.get("doi")})
    if not notices:
        return ""
    if dois:
        links = ", ".join(f"[{d}]({doi_href(d)})" for d in dois)
        return f" Correction: {links}."
    return " A published correction exists."


def fix_case(name):
    """Crossref sometimes stores ALL-CAPS surnames; title-case them (keeps mixed-case names untouched)."""
    name = clean(name)
    if len(name) > 1 and name.isupper():
        return " ".join(w.title() if not w.startswith(("d'", "D'")) else w[:2] + w[2:].title() for w in name.split(" "))
    return name


def clean_title(t):
    """Strip markup and make sure the title ends with exactly one terminal mark."""
    t = clean(t)
    t = re.sub(r"\s+", " ", t)
    return t if t.endswith(("?", "!", ".")) else t + "."


def initials(given):
    parts = re.split(r"[\s\-.]+", given or "")
    return "".join(p[0].upper() for p in parts if p)


def initials_dotted(given):
    parts = re.split(r"[\s\-.]+", given or "")
    return " ".join(p[0].upper() + "." for p in parts if p)


def fmt_vancouver(n, c, doi):
    au = c.get("authors_structured") or []
    names = [f"{fix_case(a['family'])} {initials(a['given'])}".strip() for a in au]
    authors = ", ".join(names)
    title = clean_title(c.get("title", ""))
    journal = clean(c.get("journal") or c.get("journal_short") or "")
    year = c.get("year") or "n.d."
    vol = c.get("volume") or ""
    iss = f"({c['issue']})" if c.get("issue") else ""
    pages = c.get("pages") or c.get("article_number") or ""
    loc = f"{year};{vol}{iss}" + (f":{pages}" if pages else "")
    return f"{n}. {authors}. {title} {journal}. {loc}. {doi_href(doi)}"


def fmt_apa(c, doi, suffix=""):
    au = c.get("authors_structured") or []
    def one(a):
        return f"{fix_case(a['family'])}, {initials_dotted(a['given'])}".rstrip(", ").strip()
    if len(au) == 0:
        authors = ""
    elif len(au) == 1:
        authors = one(au[0])
    elif len(au) <= 20:
        authors = ", ".join(one(a) for a in au[:-1]) + ", & " + one(au[-1])
    else:
        authors = ", ".join(one(a) for a in au[:19]) + ", ... " + one(au[-1])
    title = clean_title(c.get("title", ""))
    journal = clean(c.get("journal") or "")
    year = f"{c.get('year') or 'n.d.'}{suffix}"
    vol = c.get("volume") or ""
    iss = f"({c['issue']})" if c.get("issue") else ""
    pages = c.get("pages") or c.get("article_number") or ""
    pages = pages.replace("-", "–") if pages else ""
    loc = f"*{journal}*" + (f", *{vol}*{iss}" if vol else "") + (f", {pages}" if pages else "")
    return f"{authors} ({year}). {title} {loc}. {doi_href(doi)}"


def fmt_nature(n, c, doi):
    au = c.get("authors_structured") or []
    names = [f"{fix_case(a['family'])}, {initials_dotted(a['given'])}".rstrip(", ") for a in au]
    title = clean_title(c.get("title", ""))
    journal = clean(c.get("journal") or c.get("journal_short") or "")
    vol = c.get("volume") or ""
    pages = c.get("pages") or c.get("article_number") or ""
    return f"{n}. {', '.join(names)} {title} *{journal}* **{vol}**, {pages} ({c.get('year') or 'n.d.'}). {doi_href(doi)}"


def bracket_intext(c, suffix=""):
    """Author 2026 / Author & Author 2026 / Author et al. 2026 — rendered in text as a DOI link"""
    au = c.get("authors_structured") or []
    year = f"{c.get('year') or 'n.d.'}{suffix}"
    if not au:
        return f"Anon. {year}"
    if len(au) == 1:
        return f"{fix_case(au[0]['family'])} {year}"
    if len(au) == 2:
        return f"{fix_case(au[0]['family'])} & {fix_case(au[1]['family'])} {year}"
    return f"{fix_case(au[0]['family'])} et al. {year}"


def fmt_bracket(c, doi, suffix=""):
    """One line: **All Authors (2026)** Title. *Journal*. doi link.

    The reference list names every author — "et al." lives only in the in-text tags.
    """
    au = c.get("authors_structured") or []
    names = ", ".join(f"{fix_case(a['family'])} {initials(a['given'])}".strip()
                      for a in au) or "Anon."
    year = f"{c.get('year') or 'n.d.'}{suffix}"
    title = clean_title(c.get("title", ""))
    journal = clean(c.get("journal") or c.get("journal_short") or "")
    return f"**{names} ({year})** {title} *{journal}*. {doi_href(doi)}"


def apa_intext(c, suffix=""):
    au = c.get("authors_structured") or []
    year = f"{c.get('year') or 'n.d.'}{suffix}"
    if not au:
        return f"Anon., {year}"
    if len(au) == 1:
        return f"{fix_case(au[0]['family'])}, {year}"
    if len(au) == 2:
        return f"{fix_case(au[0]['family'])} & {fix_case(au[1]['family'])}, {year}"
    return f"{fix_case(au[0]['family'])} et al., {year}"


def year_suffixes(keys, by_key, style):
    """Assign a/b/c suffixes to cited entries that would render identically in text."""
    label = bracket_intext if style == "bracket" else apa_intext
    groups = {}
    for k in keys:
        c = by_key[k]["canonical"]
        groups.setdefault(label(c), []).append(k)
    out = {}
    for same in groups.values():
        if len(same) > 1:
            same.sort(key=lambda k: clean_title(by_key[k]["canonical"].get("title", "")).lower())
            for i, k in enumerate(same):
                out[k] = chr(97 + i)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out", help="write here; omit to print to stdout (the default — the review is a chat message, not a file)")
    ap.add_argument("--style", choices=["bracket", "vancouver", "apa", "nature"], default="bracket")
    ap.add_argument("--heading", default="**Sources**")
    args = ap.parse_args()

    ledger = json.load(open(args.ledger))
    by_key = {e["key"]: e for e in ledger["entries"]}
    text = open(args.draft).read()
    if args.style == "bracket":
        text = normalize_chat_citation_punctuation(text)

    text, figure_errors, _figures = resolve_figures(text)

    order = []          # keys in order of first appearance
    errors = list(figure_errors)
    # pass 1: collect cited keys so APA suffixes can be assigned before substitution
    cited_keys = []
    for grp in re.findall(r"\[(@[^\]]+)\]", text):
        for k in grp.split(";"):
            k = k.strip().lstrip("@")
            if k and k not in cited_keys:
                cited_keys.append(k)
    verified_cited = [k for k in cited_keys if k in by_key and is_verified(by_key[k])]
    suffix = year_suffixes(verified_cited, by_key, args.style) if args.style in ("apa", "bracket") else {}

    def resolve_group(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";") if k.strip()]
        nums = []
        intext = []
        for k in keys:
            e = by_key.get(k)
            if e is None:
                errors.append(f"unknown citation key: {k}")
                continue
            if not is_verified(e):
                verification = e.get("verification") or {}
                errors.append(
                    f"citation not verified: {k} "
                    f"(status={e.get('status')}, bibliographic={verification.get('bibliographic_status')}, "
                    f"retraction={verification.get('retraction_status')}) — run verify_citations.py"
                )
                continue
            if k not in order:
                order.append(k)
            nums.append(order.index(k) + 1)
            if args.style == "bracket":
                doi_url = doi_href(e["doi"])
                intext.append(f"[{bracket_intext(e['canonical'], suffix.get(k, ''))}]({doi_url})")
            else:
                intext.append(apa_intext(e["canonical"], suffix.get(k, "")))
        if args.style == "bracket":
            return ", ".join(intext)
        if args.style == "apa":
            return "(" + "; ".join(intext) + ")"
        if args.style == "nature":
            return "^" + ",".join(str(n) for n in nums) + "^"
        # vancouver: compress runs like 1,2,3 -> 1–3
        nums = sorted(set(nums))
        runs, start, prev = [], None, None
        for n in nums:
            if start is None:
                start = prev = n
            elif n == prev + 1:
                prev = n
            else:
                runs.append((start, prev)); start = prev = n
        if start is not None:
            runs.append((start, prev))
        return "[" + ",".join(f"{a}–{b}" if b > a + 1 else (f"{a},{b}" if b == a + 1 else f"{a}") for a, b in runs) + "]"

    body = re.sub(r"\[(@[^\]]+)\]", resolve_group, text)

    if errors:
        print("ERRORS — output not written:")
        for e in sorted(set(errors)):
            print("  -", e)
        sys.exit(1)

    refs = []
    if args.style == "bracket":
        entries = sorted(order, key=lambda k: ((by_key[k]["canonical"].get("authors_structured") or [{"family": ""}])[0]["family"].lower(), by_key[k]["canonical"].get("year") or 0))
        for k in entries:
            refs.append(fmt_bracket(by_key[k]["canonical"], by_key[k]["doi"], suffix.get(k, "")) + correction_note(by_key[k]))
    elif args.style == "apa":
        entries = sorted(order, key=lambda k: ((by_key[k]["canonical"].get("authors_structured") or [{"family": ""}])[0]["family"].lower(), by_key[k]["canonical"].get("year") or 0))
        for k in entries:
            refs.append(fmt_apa(by_key[k]["canonical"], by_key[k]["doi"], suffix.get(k, "")) + correction_note(by_key[k]))
    else:
        for i, k in enumerate(order, 1):
            c, doi = by_key[k]["canonical"], by_key[k]["doi"]
            base = fmt_vancouver(i, c, doi) if args.style == "vancouver" else fmt_nature(i, c, doi)
            refs.append(base + correction_note(by_key[k]))

    out = body.rstrip() + "\n\n" + args.heading + "\n\n" + "\n\n".join(refs) + "\n"

    unused = [e["key"] for e in ledger["entries"] if is_verified(e) and e["key"] not in order]
    if args.out:
        open(args.out, "w").write(out)
        print(f"Wrote {args.out}: {len(order)} references cited ({args.style}).", file=sys.stderr)
    else:
        # Default: print the finished review so it can be pasted straight into the reply.
        print(out)
        print(f"\n[{len(order)} references cited, {args.style} style]", file=sys.stderr)
    if unused:
        print(f"{len(unused)} verified ledger entries not cited: {', '.join(unused[:15])}{' …' if len(unused) > 15 else ''}", file=sys.stderr)


if __name__ == "__main__":
    main()
