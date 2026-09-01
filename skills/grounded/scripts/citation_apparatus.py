"""Helpers for DOI-linked reference apparatus that is not a cited source.

Published corrections belong on the corrected article's reference entry.  They
must remain clickable in the release, but they are not independent evidence
items and therefore must not be counted or validated as cited studies.
"""

from __future__ import annotations

import re
from urllib.parse import unquote


def normalize_doi(value: object) -> str | None:
    if not value:
        return None
    normalized = unquote(str(value)).strip().lower()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    return re.sub(r"[).,;*_]+$", "", normalized) or None


def correction_note_dois(sources: str) -> set[str]:
    """Return DOI links explicitly labelled as correction apparatus.

    ``format_references.py`` emits each reference on one line and introduces
    correction links with ``Correction:``.  Keeping this parser deliberately
    narrow prevents an ordinary uncited DOI from being mistaken for apparatus.
    """
    dois: set[str] = set()
    for match in re.finditer(r"\bCorrection:\s*([^\n]+)", sources, re.I):
        for value in re.findall(
            r"https?://(?:dx\.)?doi\.org/([^\s<>\]]+)", match.group(1), re.I
        ):
            normalized = normalize_doi(value)
            if normalized:
                dois.add(normalized)
    return dois


def ledger_correction_dois(
    ledger: dict[str, object], primary_dois: set[str] | None = None
) -> set[str]:
    """Return correction DOI records attached to selected primary articles."""
    result: set[str] = set()
    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        return result
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        primary = normalize_doi(entry.get("doi"))
        if primary_dois is not None and primary not in primary_dois:
            continue
        verification = entry.get("verification") or {}
        if not isinstance(verification, dict):
            continue
        notices = verification.get("correction_notices") or []
        if not isinstance(notices, list):
            continue
        for notice in notices:
            if not isinstance(notice, dict):
                continue
            normalized = normalize_doi(notice.get("doi"))
            if normalized:
                result.add(normalized)
    return result
