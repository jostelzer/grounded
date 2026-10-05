"""Release invariants for assertion coverage, evidence identity, and checked audits.

These checks attest consistency, not scientific truth. An independent judge
still decides whether quotations entail each asserted element.
"""
import hashlib
import json
import os
import re
from decimal import Decimal
from pathlib import Path

import claim_evidence
import claim_context
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


_UNIT_ALIASES = {"milligrams": "mg", "milligram": "mg", "micrograms": "µg",
                 "microgram": "µg", "grams": "g", "gram": "g", "percent": "%",
                 "h": "hour", "hr": "hour", "hrs": "hour", "hours": "hour",
                 "min": "minute", "mins": "minute", "minutes": "minute",
                 "wk": "week", "wks": "week"}
_QUANTITY_RE = re.compile(
    r"(?<![\w.])([+-]?\d+(?:\.\d+)?)(?:\s*(%|mg|kg|µg|μg|g|ml|mL|mmol|mm|cm|minutes?|hours?|"
    r"days?|weeks?|months?|years?)\b|(%))?")
# A rounded figure is honest only when the sentence says it is rounded.
_ROUND_CUE_RE = re.compile(
    r"(?:\babout|\baround|\broughly|\bapproximately|\bapprox\.?|\bsome|\bcirca|\bessentially|"
    r"\bvirtually|\bpractically|\beffectively|~|≈)\s*$", re.I)
_BOUND_CUE_RE = re.compile(
    r"\b(?:nearly|almost|close to|just over|just under|more than|well over|over|under|"
    r"fewer than|less than|at least|at most|up to)\s*$", re.I)
# Prose may carry a minus sign in a word: "16 minutes shorter" for −16.
_DIRECTION_RE = re.compile(
    r"\b(?:lower|less|fewer|shorter|smaller|earlier|below|behind|slower|worse|fell|falls?|"
    r"fallen|drop(?:ped|s)?|declin\w+|decreas\w+|reduc\w+|loss|lost|los(?:e|es|ing)|cut|"
    r"minus|down)\b", re.I)


# "38 in every 100" is 38%; the denominator is not a measurement of its own.
_FREQUENCY_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s+(?:in|out of)\s+(?:every\s+|each\s+)?"
    r"(1000|100|10|thousand|hundred|ten)\b(?!\s*(?:%|mg|kg|µg|g|ml|mL|mmol|mm|cm)\b)", re.I)
_FREQUENCY_BASE = {"10": 10, "ten": 10, "100": 100, "hundred": 100,
                   "1000": 1000, "thousand": 1000}
# Units that are exact multiples of one another: prose may say "two hours" for 120 minutes.
_EXACT_FAMILIES = ({"minute": Decimal(1), "hour": Decimal(60)},
                   {"day": Decimal(1), "week": Decimal(7)},
                   {"month": Decimal(1), "year": Decimal(12)})
_RATE_WORDS = {"day": r"\b(?:daily|(?:a|per|each|every)\s+day)\b",
               "hour": r"\b(?:hourly|(?:an|per|each|every)\s+hour)\b",
               "week": r"\b(?:weekly|(?:a|per|each|every)\s+week)\b"}


def _normalise_quantities(text):
    text = spell_to_digits(text).replace("−", "-").replace(",", "")
    # "four and a half times" is 4.5, not 4.
    for words, fraction in (("a half", "5"), ("a quarter", "25"), ("3 quarters", "75")):
        text = re.sub(rf"(?<![\w.])(\d+) and {words}\b", rf"\1.{fraction}", text)
    # Scientific typography uses spaces (including narrow/no-break spaces)
    # to group thousands. Preserve the number rather than treating each
    # three-digit group as a separate measurement.
    text = re.sub(r"(?<![\w.])\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?!\d)",
                  lambda m: re.sub(r"[ \u00a0\u202f]", "", m[0]), text)
    # Adjectival durations express the same units as ordinary durations.
    text = re.sub(r"(?<=\d)[-‑](?=(?:wk|wks|weeks?|months?|days?|years?|"
                  r"h|hr|hrs|hours?|min|mins|minutes?)\b)", " ", text)
    # A hyphen between positive bounds is a range, not a minus sign.
    text = re.sub(r"(?<=\d)[-–—](?=\d)", " to ", text)
    text = re.sub(r"\b(" + "|".join(_UNIT_ALIASES) + r")\b",
                  lambda m: _UNIT_ALIASES[m.group()], text)
    # "9 hours and 48 minutes" is one duration.
    text = re.sub(r"(?<![\w.])(\d+) hour (?:and )?(\d{1,2}) minute\b",
                  lambda m: f"{int(m[1]) * 60 + int(m[2])} minute", text)
    return re.sub(r"\b(?:Figure|Fig\.)\s+\d+\b", "", text, flags=re.I)


def _scan_quantities(text):
    """Yield (value, unit, raw number, start, end, scale) over the normalised text.

    `scale` is how many units of the value one step of the stated number is
    worth: 1 for ordinary quantities, 10 for "4 in 10" read as 40%.
    """
    text = _normalise_quantities(text)
    found = []
    frequency_spans = []
    for match in _FREQUENCY_RE.finditer(text):
        scale = Decimal(100) / _FREQUENCY_BASE[match[2].lower()]
        found.append((Decimal(match[1]) * scale, "%", match[1], match.start(), match.end(), scale))
        frequency_spans.append(match.span())
    for match in _QUANTITY_RE.finditer(text):
        if any(start <= match.start() < end for start, end in frequency_spans):
            continue
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
        found.append((Decimal(value), unit, value, match.start(), match.end(), Decimal(1)))
    return text, sorted(found, key=lambda item: item[3])


def quantities(text):
    """Exact signed values plus attached units; no substring or percent stripping."""
    return {(value, unit) for value, unit, *_rest in _scan_quantities(text)[1]}


def _rounding_tolerance(raw):
    """Half the size of the last stated digit, capped so "about 100" is not 50–150."""
    digits = raw.lstrip("+-")
    if "." in digits:
        return Decimal(1).scaleb(-len(digits.split(".")[1])) / 2
    zeros = len(digits) - len(digits.rstrip("0"))
    step = Decimal(1).scaleb(zeros)
    return max(Decimal("0.5"), min(step / 2, abs(Decimal(digits)) * Decimal("0.05")))


def _units_compatible(claim_unit, quote_unit, sentence=""):
    """Same unit, or one side leaves the unit to its context (a table header, a lay
    word such as "points"). A percentage never matches a plain number. A rate
    ("hour/day") matches its numerator when the sentence names the denominator
    in words ("1.4 hours a day")."""
    if claim_unit == quote_unit:
        return True
    numerator, _, denominator = quote_unit.partition("/")
    if denominator in _RATE_WORDS and numerator == claim_unit:
        return bool(re.search(_RATE_WORDS[denominator], sentence, re.I))
    return "" in (claim_unit, quote_unit) and "%" not in (claim_unit, quote_unit)


def _in_claim_unit(quote_value, quote_unit, claim_unit):
    """The quote's value in the claim's unit when the two convert exactly
    (minutes and hours, days and weeks, months and years); otherwise None."""
    for family in _EXACT_FAMILIES:
        if quote_unit in family and claim_unit in family and quote_unit != claim_unit:
            return quote_value * family[quote_unit] / family[claim_unit]
    return None


def missing_quantities(claim, quote):
    """Claim quantities the quote does not support.

    A quantity is supported by the same value and a compatible unit. Prose may
    also round, if it says so ("about 16 minutes" for 15.8), may carry a minus
    sign in a direction word ("16 minutes shorter" for −16.1), may convert
    between units that are exact multiples ("two hours" for 120 minutes) and
    may state a percentage as a frequency ("about 38 in every 100" for 37.6%).
    Wrong values, conflicting units, unmarked rounding and unexplained sign
    changes stay unmatched.
    """
    quote_quantities = quantities(quote)
    text, found = _scan_quantities(claim)
    missing = set()
    for value, unit, raw, start, end, scale in found:
        if (value, unit) in quote_quantities:
            continue
        before = text[max(0, start - 24):start]
        # "about 16 minutes shorter to 16 minutes longer": the cue covers both ends.
        joined = re.search(r"[-+]?\d[\d.]*%?(?:\s+[^\W\d]+){0,3}\s+(?:to|and|or)\s*$",
                           text[max(0, start - 60):start])
        if joined:
            before = text[max(0, start - 60):start][:joined.start()][-24:]
        if _ROUND_CUE_RE.search(before):
            tolerance = _rounding_tolerance(raw) * scale
        elif _BOUND_CUE_RE.search(before):
            tolerance = 2 * _rounding_tolerance(raw) * scale
        else:
            tolerance = Decimal(0)
        if scale > 1:
            # "about 4 in 10" is coarse; it still may not stray far from the percentage.
            tolerance = min(tolerance, Decimal("2.5"))
        sentence_start = max(text.rfind(".", 0, start), text.rfind(";", 0, start)) + 1
        sentence_end = min((i for i in (text.find(". ", end), text.find(";", end)) if i != -1),
                           default=len(text))
        sentence = text[sentence_start:sentence_end]
        direction = bool(_DIRECTION_RE.search(sentence))
        for quote_value, quote_unit in quote_quantities:
            converted = _in_claim_unit(quote_value, quote_unit, unit)
            if converted is not None:
                quote_value = converted
            elif not _units_compatible(unit, quote_unit, sentence):
                continue
            candidates = [quote_value]
            if quote_value < 0 <= value and direction:
                candidates.append(-quote_value)
            if any(abs(candidate - value) <= tolerance for candidate in candidates):
                break
        else:
            missing.add((value, unit))
    return missing


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


def artifact_reference(path, audit_path):
    """Snapshot the actual inspected file, relative to the audit's location."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"artifact is not a file: {path}")
    return {"path": os.path.relpath(path, Path(audit_path).resolve().parent),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def artifact_errors(audit, audit_path):
    errors = []
    for claim in audit.get("claims", []):
        for reference in claim.get("artifacts", []):
            if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
                errors.append(claim["id"] + ": invalid artifact reference")
                continue
            path = reference["path"]
            if Path(path).is_absolute() or not path:
                errors.append(claim["id"] + ": artifact path must be relative to audit")
                continue
            try:
                current = artifact_reference(Path(audit_path).resolve().parent / path, audit_path)
                if current["sha256"] != reference.get("sha256"):
                    errors.append(claim["id"] + ": artifact changed: " + path)
            except (OSError, ValueError):
                errors.append(claim["id"] + ": artifact missing or unreadable: " + path)
    return errors


def coverage_errors(audit):
    errors = []
    claims = audit.get("claims", [])
    by_id = {c["id"]: c for c in claims}
    if len(by_id) != len(claims):
        errors.append("duplicate assertion IDs")
    for c in claims:
        prefix = c["id"] + ": "
        classification = c.get("classification", "pending")
        if classification not in {"factual", "interpretation", "nonfactual", "artifact"}:
            errors.append(prefix + "assertion still needs independent classification")
            continue
        if classification != "factual":
            if not c.get("classification_note", "").strip():
                errors.append(prefix + "classification needs a reason")
            if c.get("dois"):
                errors.append(prefix + "cited assertions must be assessed as factual")
            if c.get("adjudications"):
                errors.append(prefix + "non-factual classifications cannot retain source adjudications")
            if classification == "artifact" and not c.get("artifacts"):
                errors.append(prefix + "artifact classification needs inspected file evidence")
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
    errors.extend(artifact_errors(audit, audit_path))
    if errors:
        raise ValueError("assertion coverage failed: " + "; ".join(errors))
    if audit.get("checked_sha256") != checked_digest(audit):
        raise ValueError("audit is unchecked or changed since check; rerun check")
    directory = Path(audit_path).resolve().parent / audit["evidence_directory"]
    context_errors = claim_context.audit_errors(audit, directory, audit_path, markdown, audit["review"])
    if context_errors:
        raise ValueError("interpretation review failed: " + "; ".join(context_errors))
    for c in audit["claims"]:
        for adj in c["adjudications"]:
            text, meta = claim_evidence.load_evidence(adj["doi"], directory)
            if not text or digest({"text": text, "metadata": meta}) != adj.get("evidence_sha256"):
                raise ValueError("evidence changed or missing for " + adj["doi"])
