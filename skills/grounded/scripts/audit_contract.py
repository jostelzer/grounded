"""Release invariants for assertion coverage, evidence identity, and checked audits.

These checks attest consistency, not scientific truth. An independent judge
still decides whether quotations entail each asserted element.
"""
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import claim_evidence
from claim_inventory import extract_claims, spell_to_digits


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def inventory_digest(claims):
    return digest([{k: c[k] for k in ("id", "claim", "location", "dois")}
                   for c in claims])


def checked_digest(audit):
    return digest({k: v for k, v in audit.items()
                   if k not in {"checked_sha256", "review"}})


def quantities(text):
    """Exact signed values plus attached units; no substring or percent stripping."""
    text = spell_to_digits(text).replace("−", "-").replace(",", "")
    # A hyphen between positive bounds is a range, not a minus sign.
    text = re.sub(r"(?<=\d)[-–—](?=\d)", " to ", text)
    aliases = {"milligrams": "mg", "milligram": "mg", "micrograms": "µg",
               "microgram": "µg", "grams": "g", "gram": "g", "percent": "%"}
    text = re.sub(r"\b(" + "|".join(aliases) + r")\b", lambda m: aliases[m.group()], text)
    text = re.sub(r"\b(?:Figure|Fig\.)\s+\d+\b", "", text, flags=re.I)
    pattern = r"(?<![\w.])([+-]?\d+(?:\.\d+)?)(?:\s*(%|mg|kg|µg|μg|g|ml|mL|mmol|mm|cm|hours?|days?|weeks?|months?|years?)\b|(%))?"
    result = set()
    for match in re.finditer(pattern, text):
        value, unit, percent = match.groups()
        unit = (unit or percent or "").lower().replace("μ", "µ")
        denominator = re.match(r"(?:/(?:kg|day|d|hour|h|week))+\b", text[match.end():])
        if denominator and unit:
            unit += denominator.group().replace("/d", "/day") if denominator.group() == "/d" else denominator.group()
        if unit.endswith("s"):
            unit = unit[:-1]
        # A bare publication year is not an empirical quantity.
        following = text[match.end():].lstrip().lower()
        if not unit and re.fullmatch(r"(?:19|20)\d\d", value) and re.match(r"(?:study|trial|review|paper)\b", following):
            continue
        result.add((Decimal(value), unit))
    return result


def missing_quantities(claim, quote):
    return quantities(claim) - quantities(quote)


def elements_problem(claim):
    elements = claim.get("elements", [])
    if not elements or any(not isinstance(e, dict) or not e.get("text") for e in elements):
        return "missing assertion elements"
    if [e.get("id") for e in elements] != [f"E{i}" for i in range(1, len(elements) + 1)]:
        return "element IDs must be consecutive E1, E2, …"
    normalize = lambda text: " ".join(text.split())
    if normalize(" ".join(e["text"] for e in elements)) != normalize(claim["claim"]):
        return "elements must partition the complete assertion verbatim"
    return None


def coverage_errors(audit):
    errors = []
    claims = audit.get("claims", [])
    by_id = {c["id"]: c for c in claims}
    if len(by_id) != len(claims):
        errors.append("duplicate assertion IDs")
    for c in claims:
        prefix = c["id"] + ": "
        classification = c.get("classification", "pending")
        if classification not in {"factual", "interpretation", "nonfactual"}:
            errors.append(prefix + "assertion still needs independent classification")
            continue
        if classification != "factual":
            if not c.get("classification_note", "").strip():
                errors.append(prefix + "classification needs a reason")
            if c.get("dois"):
                errors.append(prefix + "cited assertions must be assessed as factual")
            if classification == "interpretation":
                basis = c.get("basis", [])
                if not basis or any(k not in by_id or by_id[k].get("classification") != "factual"
                                    for k in basis):
                    errors.append(prefix + "interpretation needs factual assertion IDs as its basis")
            continue
        problem = elements_problem(c)
        if problem:
            errors.append(prefix + problem)
            continue
        elements = {e["id"]: e["text"] for e in c["elements"]}
        covered = set()
        if set(c.get("dois", [])) != {a.get("doi") for a in c.get("adjudications", [])}:
            errors.append(prefix + "citation/adjudication mismatch")
        for adj in c.get("adjudications", []):
            verdict = adj.get("verdict")
            covers = set(adj.get("covers", []))
            if verdict == "supported" and not covers:
                covers = set(elements)
            if verdict not in {"supported", "partial"}:
                errors.append(prefix + f"source verdict {verdict} is not releasable")
                continue
            if covers - set(elements):
                errors.append(prefix + "unknown covered element")
            if verdict == "partial" and (not adj.get("note") or covers == set(elements)):
                errors.append(prefix + "partial must name its gap and cannot cover the entire assertion")
            quotes = adj.get("quote", [])
            quotes = [quotes] if isinstance(quotes, str) else quotes
            for key in covers & set(elements):
                if missing_quantities(elements[key], " … ".join(quotes)):
                    errors.append(prefix + f"{key} has unmatched values or units in its supporting quotes")
                else:
                    covered.add(key)
        missing = set(elements) - covered
        if missing:
            errors.append(prefix + "unsupported element(s): " + ", ".join(sorted(missing)))
    return errors


def bind_evidence(audit, directory, audit_path):
    """Record hashes only after quote checks. Resolve relative to the audit file."""
    import os
    audit["evidence_directory"] = os.path.relpath(Path(directory).resolve(),
                                                 Path(audit_path).resolve().parent)
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            text, meta = claim_evidence.load_evidence(adj["doi"], directory)
            adj["evidence_sha256"] = digest({"text": text, "metadata": meta})


def validate_release(audit, markdown, audit_path, key_to_doi=None):
    if audit.get("schema_version") != 2:
        raise ValueError("legacy audit: re-extract and independently check the complete assertion inventory")
    current = extract_claims(markdown, key_to_doi, include_uncited=True)
    if inventory_digest(current) != audit.get("inventory_sha256") or \
            inventory_digest(audit["claims"]) != audit.get("inventory_sha256"):
        raise ValueError("review assertions changed: re-extract and re-adjudicate before release")
    errors = coverage_errors(audit)
    if errors:
        raise ValueError("assertion coverage failed: " + "; ".join(errors))
    if audit.get("checked_sha256") != checked_digest(audit):
        raise ValueError("audit is unchecked or changed since check; rerun check")
    directory = Path(audit_path).resolve().parent / audit["evidence_directory"]
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            text, meta = claim_evidence.load_evidence(adj["doi"], directory)
            if not text or digest({"text": text, "metadata": meta}) != adj.get("evidence_sha256"):
                raise ValueError("evidence changed or missing for " + adj["doi"])
