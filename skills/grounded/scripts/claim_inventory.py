"""Deterministic assertion inventory; semantic classification belongs to the judge."""
import re
import claim_evidence

_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
          "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_SPELLED = {w: i for i, w in enumerate(_UNITS)}
_SPELLED.update(_TENS)
for _t, _tv in _TENS.items():
    for _u in range(1, 10):
        _SPELLED[f"{_t}-{_UNITS[_u]}"] = _tv + _u


def spell_to_digits(text):
    """Rewrite spelled-out numbers (\"twenty-two\") as digits so a quote like
    \"Twenty-two subjects\" satisfies the numeric anchor \"22\"."""
    pattern = re.compile(
        r"\b(" + "|".join(sorted(_SPELLED, key=len, reverse=True)) + r")\b", re.I)
    return pattern.sub(lambda m: str(_SPELLED[m.group(1).lower()]), text or "")


def quotes_of(adj):
    """An adjudication's quote may be one string or a list of strings."""
    quote = adj.get("quote", "")
    if isinstance(quote, str):
        return [quote] if quote else []
    return [q for q in quote if q]

DOI_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((https?://(?:dx\.)?doi\.org/(?:[^\s()]|\([^\s()]*\)|%28|%29)+)\)",
    re.IGNORECASE,
)
# Words a sentence splitter must not break after.
_ABBREV = ("et al", "e.g", "i.e", "vs", "cf", "ca", "approx", "Fig", "fig",
           "No", "no", "Dr", "St", "resp")


def _protect(text):
    for a in _ABBREV:
        text = text.replace(a + ".", a + "\u2024")
    text = re.sub(r"(\d)\.(\d)", "\\1\u2024\\2", text)
    return text


def _unprotect(text):
    return text.replace("\u2024", ".")


def split_sentences(paragraph):
    protected = _protect(paragraph)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(\[])", protected)
    return [_unprotect(p).strip() for p in parts if p.strip()]


def split_assertions(block):
    """Split prose, keeping Markdown links intact and citations sentence-local."""
    links = []
    def protect_link(match):
        links.append(match.group())
        return f"\uFFF0{len(links) - 1}\uFFF1"
    protected = re.sub(r"!?\[[^\]]*\]\([^\n]*?\)", protect_link, block)
    protected = _protect(protected)
    protected = re.sub(r"(Figure\s+\d+)\.", lambda m: m[1] + "\u2024", protected)
    parts = re.split(
        r"(?:(?<=[.!?])|(?<=[.!?]\*\*)|(?<=[.!?]\*)|(?<=[.!?]__)|(?<=[.!?]_))"
        r"\s+(?=[\*_\"“(\[]*[A-Z0-9])", protected)
    # Restore links before parsing citations.
    return [_unprotect(re.sub(r"\uFFF0(\d+)\uFFF1", lambda m: links[int(m[1])], p)).strip()
            for p in parts if p.strip()]


def claim_numbers(text):
    """Numeric anchors of a claim: numbers that are not years or citation labels."""
    cleaned = DOI_LINK_RE.sub(" ", text)
    # A numbered caption's leading ``Figure N.`` is document structure, not a
    # scientific quantity the cited paper must contain.  Strip only that
    # anchored prefix; empirical numbers elsewhere in the caption still bind.
    cleaned = re.sub(r"^\s*\*\*Figure\s+\d+\.", "", cleaned, flags=re.IGNORECASE)
    numbers = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*%?", cleaned):
        token = m.group(0).replace(",", "")
        bare = token.rstrip("%")
        if re.fullmatch(r"(?:19|20)\d\d", bare):
            continue
        if token not in numbers:
            numbers.append(token)
    return numbers


def _strip_citations(sentence):
    text = DOI_LINK_RE.sub("", sentence)
    text = re.sub(r"\[@[^\]]+\]", "", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\(\s*(?:[,;]\s*)*\)", "", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    # Removing "claim, [A], [B]." leaves ",," and ",." behind.
    text = re.sub(r"(?:\s*,)+(\s*[.;:!?])", r"\1", text)
    text = re.sub(r"(?:\s*,){2,}", ",", text)
    return re.sub(r"\s+", " ", text).strip()


def _pairs_from_text(text_block, location, key_to_doi, include_uncited=False):
    dois = [claim_evidence.norm_doi(m.group(2)) for m in DOI_LINK_RE.finditer(text_block)]
    for m in re.finditer(r"\[@([^\]\s;]+)(?:;\s*@[^\]]+)*\]", text_block):
        for key in re.findall(r"@([^\s;\]]+)", m.group(0)):
            doi = key_to_doi.get(key)
            if doi:
                dois.append(claim_evidence.norm_doi(doi))
    seen, ordered = set(), []
    for d in dois:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    if not ordered and not include_uncited:
        return None
    return {
        "claim": _strip_citations(text_block),
        "location": location,
        "dois": ordered,
        "numbers": claim_numbers(text_block),
    }


def extract_claims(markdown, key_to_doi=None, *, include_uncited=False):
    key_to_doi = key_to_doi or {}
    markdown = re.split(r"(?m)^\*\*Receipts\*\*\s*$", markdown)[0]
    body = re.split(r"(?mi)^(?:\*\*Sources\*\*|#{1,4}\s*Sources)\s*$", markdown)[0]
    claims = []
    para_no = 0
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        block = re.sub(r'<a\s[^>]*>\s*</a>', '', block).strip()
        if not block:
            continue
        if block.startswith("!["):
            if not include_uncited:
                continue
            block = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", block)
        if block.startswith("#"):
            if not include_uncited and not DOI_LINK_RE.search(block):
                continue
            block = re.sub(r"^#{1,6}\s+", "", block)
            pair = _pairs_from_text(block, "heading", key_to_doi, include_uncited)
            if pair:
                claims.append(pair)
            continue
        caption = re.match(r"^\*\*Figure\s+(\d+)\.", block)
        if caption:
            if include_uncited:
                for j, sentence in enumerate(split_assertions(" ".join(block.split())), 1):
                    pair = _pairs_from_text(sentence, f"figure {caption.group(1)} caption, sentence {j}", key_to_doi, True)
                    if pair:
                        claims.append(pair)
                continue
            # A caption is one cited statement about the figure; its sources
            # back the caption as a whole, not each descriptive sentence.
            pair = _pairs_from_text(
                " ".join(block.split()), f"figure {caption.group(1)} caption", key_to_doi, include_uncited)
            if pair:
                claims.append(pair)
            continue
        if block.lstrip().startswith("|"):
            rows = [r for r in block.splitlines() if r.strip().startswith("|")]
            for i, row in enumerate(rows):
                if re.fullmatch(r"[|\s:\-]+", row):
                    continue
                pair = _pairs_from_text(row, f"table row {i}", key_to_doi, include_uncited)
                if pair:
                    claims.append(pair)
            continue
        para_no += 1
        if include_uncited:
            items = re.split(r"(?m)^\s*(?:[-+*]|\d+[.)])\s+", block)
            for item_no, item in enumerate((x for x in items if x.strip()), 1):
                for j, sentence in enumerate(split_assertions(item), 1):
                    location = (f"paragraph {para_no}, item {item_no}, sentence {j}" if len(items) > 1
                                else f"paragraph {para_no}, sentence {j}")
                    pair = _pairs_from_text(sentence, location, key_to_doi, True)
                    if pair:
                        claims.append(pair)
            continue
        for j, sentence in enumerate(split_sentences(block), 1):
            pair = _pairs_from_text(sentence, f"paragraph {para_no}, sentence {j}", key_to_doi, include_uncited)
            if pair:
                claims.append(pair)
    for i, c in enumerate(claims, 1):
        c["id"] = f"C{i:03d}"
        if include_uncited:
            c["classification"] = "factual" if c["dois"] else "pending"
            c["elements"] = [{"id": "E1", "text": c["claim"]}]
        c["adjudications"] = [
            {"doi": d, "verdict": "pending", "quote": "", "note": ""} for d in c["dois"]
        ]
    return claims
