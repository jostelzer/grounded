#!/usr/bin/env python3
"""
Quotes before prose: the synthesis carries the passage behind every key it cites.

`synthesis.md` is the claims ledger every style renders from. This module makes
its evidence traceable *before* a sentence of prose exists: each claim lists,
for every ledger key on its evidence and contrary lines, at least one

    - quote: [@Key] "verbatim passage from the stored evidence text"

and `check_synthesis` string-matches every quote against the evidence store
(`claim_evidence`), requires every number in the claim sentence to sit inside
one of its quotes, and reports the tier each key was quoted at. A claim whose
sources were never quoted cannot be drafted; a source the synthesis never
quoted cannot be cited by the review (`verify_claims.py extract --synthesis`).
"""
import re

import claim_evidence

CLAIM_RE = re.compile(r"^###\s+(C\d+)\.\s+(.+)$", re.M)
QUOTE_RE = re.compile(
    r'^- quote:\s*\[@([A-Za-z0-9_.:-]+)\]\s*[“"](.+?)[”"]\s*$', re.M)
KEY_RE = re.compile(r"@([A-Za-z0-9_.:-]+)")
FIELDS = ("strength", "evidence", "contrary", "boundary", "depends-on", "numbers")


def _field(block, field):
    match = re.search(
        rf"^- {re.escape(field)}:\s*(.*(?:\n(?!- [a-z-]+:|### |## ).*)*)", block, re.M)
    return match.group(1).strip() if match else ""


def sentence_numbers(text):
    """Numeric anchors of a claim sentence (years excluded)."""
    numbers = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*%?", text or ""):
        token = m.group(0).replace(",", "")
        if re.fullmatch(r"(?:19|20)\d\d", token.rstrip("%")):
            continue
        if token not in numbers:
            numbers.append(token)
    return numbers


def parse_claims(text):
    """Every C-entry with its sentence, cited keys, numbers, and quote lines."""
    matches = list(CLAIM_RE.finditer(text))
    claims = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        evidence = _field(block, "evidence")
        contrary = _field(block, "contrary")
        keys = []
        for key in KEY_RE.findall(evidence + "\n" + contrary):
            if key not in keys:
                keys.append(key)
        claims.append({
            "id": match.group(1),
            "sentence": match.group(2).strip(),
            "keys": keys,
            "contrary_keys": KEY_RE.findall(contrary),
            "evidence_text": " ".join(evidence.split()),
            "contrary_text": " ".join(contrary.split()),
            "boundary_text": " ".join(_field(block, "boundary").split()),
            "numbers": sentence_numbers(match.group(2)),
            "numbers_field": _field(block, "numbers"),
            "quotes": [(key, " ".join(q.split())) for key, q in QUOTE_RE.findall(block)],
        })
    return claims


HOLLOW_MIN_CLAIMS = 8
TEMPLATE_LIMIT = 3


def hollow_problems(claims):
    """Signs that the synthesis was generated rather than distilled.

    A ledger whose claims all say "none found — searched", or whose boundary,
    numbers, or evidence lines repeat verbatim across claims, has not weighed
    the literature — it has filled in a form. Both are hard failures: the fix
    is reading, not editing the lines to differ.
    """
    problems = []
    if len(claims) >= HOLLOW_MIN_CLAIMS and not any(c["contrary_keys"] for c in claims):
        problems.append(
            f"none of the {len(claims)} claims records contrary evidence — a "
            "synthesis that found no disagreement has not searched for it")
    for field, label in (("boundary_text", "boundary"), ("numbers_field", "numbers"),
                         ("evidence_text", "evidence")):
        seen = {}
        for c in claims:
            text = (c.get(field) or "").strip()
            if len(text) < 12 or text in {"—", "-", "none"}:
                continue
            key = text if field != "evidence_text" else KEY_RE.sub("", text).strip()
            seen.setdefault(key, []).append(c["id"])
        for text, ids in seen.items():
            if len(ids) >= TEMPLATE_LIMIT:
                problems.append(
                    f"templated {label} line on {len(ids)} claims ({', '.join(ids[:3])}, …): "
                    f"“{text[:60]}” — every claim states its own")
    return problems


def key_to_doi(ledger):
    return {e["key"]: claim_evidence.norm_doi(e["doi"])
            for e in ledger.get("entries", []) if e.get("doi") and e.get("key")}


def quotes_by_doi(text, ledger):
    """DOI → [(claim id, quote)] — the writer's own receipts, per source."""
    mapping = key_to_doi(ledger)
    out = {}
    for claim in parse_claims(text):
        for key, quote in claim["quotes"]:
            doi = mapping.get(key)
            if doi:
                out.setdefault(doi, []).append((claim["id"], quote))
    return out


def check_synthesis(text, store, ledger):
    """Errors, warnings, and metrics for the quotes-before-prose contract."""
    errors, warnings = [], []
    mapping = key_to_doi(ledger)
    claims = parse_claims(text)
    if not claims:
        errors.append("synthesis has no ### C1. claims")
    errors.extend(hollow_problems(claims))
    quoted_pairs = 0
    tiers = {"fulltext": 0, "abstract": 0, "none": 0}
    seen_keys = set()
    for claim in claims:
        by_key = {}
        for key, quote in claim["quotes"]:
            by_key.setdefault(key, []).append(quote)
        for key in claim["keys"]:
            if key not in mapping:
                errors.append(f"{claim['id']} cites @{key}, which is not in the ledger")
                continue
            quotes = by_key.get(key, [])
            if not quotes:
                errors.append(
                    f"{claim['id']} cites @{key} without a quote line "
                    f"(- quote: [@{key}] \"…\")")
                continue
            evidence, meta = claim_evidence.load_evidence(mapping[key], store)
            if not evidence:
                errors.append(
                    f"{claim['id']}/@{key}: no evidence text in the store — run "
                    "`verify_claims.py seed` first")
                continue
            for quote in quotes:
                if not claim_evidence.quote_in_text(quote, evidence):
                    errors.append(
                        f"{claim['id']}/@{key}: quote is not verbatim in the stored "
                        f"text: “{quote[:60]}…”")
                else:
                    quoted_pairs += 1
            if key not in seen_keys:
                seen_keys.add(key)
                tiers[(meta or {}).get("tier", "none") if (meta or {}).get("tier") in tiers else "none"] += 1
        for key in by_key:
            if key not in claim["keys"]:
                warnings.append(
                    f"{claim['id']} quotes @{key}, which its evidence/contrary lines do not cite")
        all_quotes = " … ".join(q for _k, q in claim["quotes"]).replace(",", "")
        for number in claim["numbers"]:
            if number.rstrip("%") not in all_quotes:
                errors.append(
                    f"{claim['id']}: the number {number} in the claim sentence appears "
                    "in none of its quotes")
        field_numbers = [n for n in sentence_numbers(claim["numbers_field"])
                         if n.rstrip("%") not in all_quotes]
        if field_numbers:
            warnings.append(
                f"{claim['id']}: numbers field value(s) not inside any quote "
                f"({', '.join(field_numbers[:5])}) — derived arithmetic must be "
                "labelled as such in the prose")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "claims": len(claims),
            "quoted_pairs": quoted_pairs,
            "keys_quoted": len(seen_keys),
            "keys_by_tier": tiers,
        },
    }
