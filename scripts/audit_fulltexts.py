#!/usr/bin/env python3
"""Classify retained papers and build a fail-closed full-text manifest.

The audit separates article authenticity from reading evidence. A file can be a
genuine article while still not count toward a tier because its notes entry is
missing the design, result, limitation, or synthesis use. Duplicate content is
never counted twice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from artifact_io import atomic_write_json, sha256_bytes


SUPPORTED_SUFFIXES = {".txt", ".md", ".html", ".htm", ".xml", ".pdf"}
CHALLENGE_PATTERNS = (
    r"just a moment(?:\.\.\.)?",
    r"checking (?:if )?the site connection is secure",
    r"enable javascript and cookies to continue",
    r"cf-chl-|cloudflare ray id|attention required! \| cloudflare",
    r"verify (?:that )?you are human|captcha",
)
DENIAL_PATTERNS = (
    r"\baccess denied\b|\bpermission denied\b",
    r"you (?:do not|don't) have permission to access",
    r"request (?:was )?blocked|unauthorized request|forbidden",
    r"institutional login|sign in to access|purchase this article",
)
COMMON_SECTIONS = (
    "abstract", "introduction", "background", "methods", "methodology",
    "materials and methods", "results", "findings", "discussion", "conclusion",
    "limitations", "references",
)
NOTE_SIGNALS = {
    "design": re.compile(
        r"\b(?:trial|cohort|survey|experiment|meta-analysis|systematic review|"
        r"narrative review|model|analysis|dataset|participants?|patients?|sample|"
        r"randomi[sz]|methods?|design)\b", re.I
    ),
    "result": re.compile(
        r"\b(?:found|showed|reported|result|associated|increased|decreased|higher|"
        r"lower|improved|worsened|difference|effect|no (?:clear |significant )?"
        r"(?:benefit|effect|difference))\b", re.I
    ),
    "limitation": re.compile(
        r"\b(?:limit|cannot|could not|confound|underpower|small sample|observational|"
        r"heterogen|uncertain|bias|not (?:a |an )?(?:test|outcome)|generalisa|"
        r"generaliza|preclude)\w*\b", re.I
    ),
    "synthesis_use": re.compile(
        r"\b(?:support|counter|boundary|mechanis|lead|inference|evidence|warn|"
        r"context|demonstrat|inform|relevant|used|useful|weight)\w*\b", re.I
    ),
}


class _VisibleHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.headings: list[str] = []
        self._hidden = 0
        self._heading: str | None = None
        self._heading_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and not self._hidden:
            self._heading = tag
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._heading == tag:
            heading = re.sub(r"\s+", " ", " ".join(self._heading_parts)).strip()
            if heading:
                self.headings.append(heading)
            self._heading = None
            self._heading_parts = []
        if tag in {"script", "style", "noscript", "svg"} and self._hidden:
            self._hidden -= 1
        if tag in {"p", "div", "section", "article", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden:
            return
        self.parts.append(data)
        if self._heading is not None:
            self._heading_parts.append(data)


def norm_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = unquote(value).strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return re.sub(r"[\s).,;*_]+$", "", value) or None


def _words(text: str) -> list[str]:
    return re.findall(r"\b[\w’'-]+\b", text, re.UNICODE)


def _headings_from_text(text: str) -> list[str]:
    headings = [
        match.strip() for match in re.findall(r"^#{1,4}\s+(.+?)\s*$", text, re.M)
    ]
    for name in COMMON_SECTIONS:
        if re.search(rf"^\s*{re.escape(name)}\s*$", text, re.I | re.M):
            headings.append(name.title())
    return list(dict.fromkeys(headings))[:80]


def extract_document(path: Path) -> tuple[str, list[str], str, str]:
    """Return visible text, headings, media type, and extraction method."""
    payload = path.read_bytes()
    suffix = path.suffix.lower()
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if suffix == ".pdf" or payload.startswith(b"%PDF-"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(path, strict=True)
            pages = [(page.extract_text() or "") for page in reader.pages]
        except Exception as exc:
            raise ValueError(f"PDF extraction failed: {exc}") from exc
        text = "\n\n".join(pages)
        return text, _headings_from_text(text), "application/pdf", "pypdf"
    decoded = payload.decode("utf-8", errors="replace")
    if suffix in {".html", ".htm"} or re.search(r"<html\b|<!doctype\s+html", decoded[:1000], re.I):
        parser = _VisibleHtml()
        parser.feed(decoded)
        text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        return text, parser.headings, "text/html", "html-visible-text"
    if suffix == ".xml" or re.search(r"<article[\s>]", decoded[:2000], re.I):
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(decoded)
            text = "\n".join(
                re.sub(r"\s+", " ", "".join(node.itertext())).strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] in {"title", "p"}
            )
            headings = [
                re.sub(r"\s+", " ", "".join(node.itertext())).strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "title"
            ]
            return text, headings[:80], "application/xml", "xml-text"
        except Exception:
            pass
    return decoded, _headings_from_text(decoded), media_type, "utf-8-text"


def _title_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    stop = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "the", "to", "with"}
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in stop
    }


def title_match(title: str | None, text: str) -> bool:
    expected = _title_tokens(title)
    if not expected:
        return False
    observed = _title_tokens(text[:8000])
    return len(expected & observed) / len(expected) >= 0.55


def _notes_entries(notes: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    current_key: str | None = None
    current: list[str] = []
    for line in notes.splitlines():
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s+`([^`]+)`\s*[—–-]\s*(.*)$", line)
        if match:
            if current_key:
                entries[current_key] = "\n".join(current).strip()
            current_key = match.group(1).strip()
            current = [line.strip()]
        elif current_key and (line.startswith("  ") or (line.strip() and not line.startswith("#") and not re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line))):
            current.append(line.strip())
        elif current_key:
            entries[current_key] = "\n".join(current).strip()
            current_key, current = None, []
    if current_key:
        entries[current_key] = "\n".join(current).strip()
    return entries


def _note_audit(note: str | None) -> dict[str, Any]:
    signals = {
        name: bool(pattern.search(note or "")) for name, pattern in NOTE_SIGNALS.items()
    }
    return {
        "entry": note,
        "found": note is not None,
        "signals": signals,
        "complete": note is not None and all(signals.values()),
    }


def _ledger_by_key(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("key")): entry
        for entry in ledger.get("entries", [])
        if entry.get("key")
    }


def classify(
    path: Path,
    entry: dict[str, Any] | None,
    note: str | None,
    *,
    min_words: int,
) -> dict[str, Any]:
    payload = path.read_bytes()
    digest = sha256_bytes(payload)
    retrieved = dt.datetime.fromtimestamp(
        path.stat().st_mtime, tz=dt.timezone.utc
    ).replace(microsecond=0).isoformat()
    record: dict[str, Any] = {
        "path": path.name,
        "ledger_key": entry.get("key") if entry else path.stem,
        "doi": norm_doi(entry.get("doi")) if entry else None,
        "source_url": (entry or {}).get("oa_url") or (
            f"https://doi.org/{norm_doi(entry.get('doi'))}" if entry and norm_doi(entry.get("doi")) else None
        ),
        "retrieved_at": retrieved,
        "bytes": len(payload),
        "sha256": digest,
    }
    try:
        text, headings, media_type, method = extract_document(path)
    except ValueError as exc:
        record.update({
            "status": "unreadable", "reason": str(exc), "media_type": None,
            "extraction_method": None, "word_count": 0, "section_headings": [],
            "title_match": False, "doi_match": False, "notes": _note_audit(note),
            "counted": False,
        })
        return record
    compact = re.sub(r"\s+", " ", text).strip()
    lower = compact.lower()
    word_count = len(_words(compact))
    expected_doi = norm_doi((entry or {}).get("doi"))
    observed_dois = {
        norm_doi(value) for value in re.findall(
            r"(?:https?://(?:dx\.)?doi\.org/|\bdoi\s*:\s*)(10\.\d{4,9}/[^\s<>]+)",
            compact, re.I,
        )
    }
    source_match = re.search(r"(?mi)^Source:\s*(https?://\S+)", text[:4000])
    if source_match:
        record["source_url"] = source_match.group(1).rstrip(").,;")
    doi_matches = bool(expected_doi and expected_doi in observed_dois)
    title_matches = title_match((entry or {}).get("title"), compact)
    note_audit = _note_audit(note)
    challenge = any(re.search(pattern, lower, re.I) for pattern in CHALLENGE_PATTERNS)
    denial = any(re.search(pattern, lower, re.I) for pattern in DENIAL_PATTERNS)
    section_names = {heading.strip().lower() for heading in headings}
    has_article_sections = bool(section_names & {"methods", "methodology", "results", "findings", "discussion"})
    abstract_like = (
        "abstract" in section_names
        or bool(re.search(r"\babstract\b", compact[:1500], re.I))
    )
    if challenge:
        status, reason = "challenge_page", "anti-bot challenge language detected"
    elif denial:
        status, reason = "access_denied", "access-denial or paywall language detected"
    elif word_count < 80:
        status, reason = "metadata_shell", f"only {word_count} extracted words"
    elif word_count < min_words and abstract_like and not has_article_sections:
        status, reason = "abstract_only", f"abstract-like record has {word_count} words"
    elif word_count < min_words:
        status, reason = "metadata_shell", f"only {word_count} extracted words"
    elif entry is None:
        status, reason = "metadata_shell", "filename does not map to a ledger key"
    elif not (doi_matches if observed_dois else title_matches):
        status, reason = "metadata_shell", "article title or DOI could not be matched"
    else:
        status, reason = "valid_fulltext", "article-length text with matched identity"
    counted = status == "valid_fulltext" and note_audit["complete"]
    record.update({
        "status": status,
        "reason": reason,
        "media_type": media_type,
        "extraction_method": method,
        "word_count": word_count,
        "section_headings": headings,
        "title_match": title_matches,
        "doi_match": doi_matches,
        "notes": note_audit,
        "counted": counted,
    })
    return record


def build_manifest(
    ledger: dict[str, Any],
    fulltext_dir: Path,
    *,
    notes: str = "",
    min_words: int = 1000,
) -> dict[str, Any]:
    if min_words < 100:
        raise ValueError("min_words must be at least 100")
    by_key = _ledger_by_key(ledger)
    note_entries = _notes_entries(notes)
    records = []
    for path in sorted(fulltext_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        entry = by_key.get(path.stem)
        record = classify(
            path, entry, note_entries.get(path.stem), min_words=min_words
        )
        records.append(record)
    by_hash: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_hash.setdefault(record["sha256"], []).append(record)
    for siblings in by_hash.values():
        originals = [item for item in siblings if item["status"] == "valid_fulltext"]
        if not originals:
            continue
        original = originals[0]
        for record in siblings:
            if record is original:
                continue
            record["status"] = "duplicate"
            record["reason"] = f"content duplicates {original['path']}"
            record["duplicate_of"] = original["path"]
            record["counted"] = False
    counts: dict[str, int] = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "fulltext_directory": str(fulltext_dir.resolve()),
        "minimum_words": min_words,
        "summary": {
            "files": len(records),
            "status_counts": dict(sorted(counts.items())),
            "valid_distinct": sum(record["status"] == "valid_fulltext" for record in records),
            "counted_with_complete_notes": sum(bool(record["counted"]) for record in records),
        },
        "records": records,
    }


def update_reading_evidence(ledger: dict[str, Any], manifest: dict[str, Any]) -> None:
    fulltext_by_key = {
        record["ledger_key"]: record for record in manifest.get("records", [])
        if record.get("ledger_key") and record.get("status") == "valid_fulltext"
    }
    for entry in ledger.get("entries", []):
        abstract_words = len(_words(entry.get("abstract") or ""))
        fulltext = fulltext_by_key.get(entry.get("key"))
        eligible = abstract_words >= 50 or bool(fulltext)
        entry["reading_evidence"] = {
            "status": "eligible" if eligible else "missing",
            "abstract_word_count": abstract_words,
            "fulltext_sha256": fulltext.get("sha256") if fulltext else None,
            "fulltext_status": fulltext.get("status") if fulltext else None,
            "notes_complete": bool(fulltext and fulltext.get("notes", {}).get("complete")),
        }


def permits_fulltext_shortfall(override: dict[str, Any] | None) -> bool:
    if override is None:
        return False
    reason = override.get("reason")
    evidence = override.get("saturation_evidence")
    allowed = override.get("allowed_shortfalls", [])
    if not isinstance(reason, str) or len(reason.split()) < 5:
        raise ValueError("thin-literature override requires a substantive reason")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("thin-literature override requires saturation_evidence")
    if not isinstance(allowed, list):
        raise ValueError("allowed_shortfalls must be a list")
    if not set(allowed) <= {"sources", "fulltexts"}:
        raise ValueError("allowed_shortfalls may contain only sources/fulltexts")
    return "fulltexts" in allowed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, help="Grounded sources.json")
    parser.add_argument("--fulltext-dir", required=True)
    parser.add_argument("--notes", help="notes.md with per-key evidence entries")
    parser.add_argument("--out", required=True, help="fulltext-manifest.json")
    parser.add_argument("--min-words", type=int, default=1000)
    parser.add_argument("--minimum", type=int, default=0,
                        help="required count of distinct valid texts with complete notes")
    parser.add_argument("--update-ledger", action="store_true",
                        help="atomically add reading_evidence fields to the ledger")
    parser.add_argument(
        "--thin-literature-override",
        help="structured JSON that may document a genuine full-text shortfall",
    )
    args = parser.parse_args(argv)
    try:
        ledger_path = Path(args.ledger)
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else ""
        manifest = build_manifest(
            ledger, Path(args.fulltext_dir), notes=notes, min_words=args.min_words
        )
        override = (
            json.loads(Path(args.thin_literature_override).read_text(encoding="utf-8"))
            if args.thin_literature_override else None
        )
        shortfall_permitted = permits_fulltext_shortfall(override)
        if shortfall_permitted:
            manifest["thin_literature_override"] = override
        atomic_write_json(args.out, manifest)
        if args.update_ledger:
            update_reading_evidence(ledger, manifest)
            atomic_write_json(ledger_path, ledger)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Full-text audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2, sort_keys=True))
    counted = manifest["summary"]["counted_with_complete_notes"]
    if counted < args.minimum and not shortfall_permitted:
        print(
            f"Full-text audit failed: {counted} counted; required {args.minimum}",
            file=sys.stderr,
        )
        return 2
    if counted < args.minimum:
        print(
            "Full-text shortfall accepted by documented thin-literature override: "
            f"{counted}/{args.minimum}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
