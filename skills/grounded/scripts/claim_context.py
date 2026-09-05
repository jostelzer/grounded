"""Recorded semantic review, separate from quote matching and evidence certainty.

Validators establish coverage and freshness of a judgment, not its correctness.
The independent reviewer supplies meaning, inspected context, and conclusions.
"""
import hashlib
import json
import re
from pathlib import Path

import claim_evidence

VERSION = 1
DIMENSIONS = {"population", "design", "exposure", "comparison", "outcome",
              "timeframe", "quantity", "uncertainty", "scope"}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def record_pair(record, text):
    """Bind reviewer-selected line ranges to the exact source inspected."""
    if not isinstance(record, dict):
        raise ValueError("context review must be a JSON object")
    record = dict(record)
    record["source_sha256"] = fingerprint(text)
    errors = pair_errors(record, text)
    if errors:
        raise ValueError("; ".join(errors))
    return record


def pair_errors(record, text=None, verdict=None):
    if not isinstance(record, dict):
        return ["missing independent context review"]
    errors = []
    meaning = record.get("meaning")
    if not isinstance(meaning, dict) or not meaning or set(meaning) - DIMENSIONS or any(
            not nonempty(v) for v in meaning.values()):
        errors.append("meaning needs applicable, nonempty scientific dimensions")
    if record.get("interpretation") not in {"preserved", "mismatch", "unresolved"}:
        errors.append("interpretation must be preserved, mismatch, or unresolved")
    if verdict in {"supported", "partial"} and record.get("interpretation") != "preserved":
        errors.append("covered elements require preserved interpretation")
    for key in ("rationale", "limitations"):
        if not nonempty(record.get(key)):
            errors.append(key + " needs a source-specific explanation")
    context = record.get("context")
    if not isinstance(context, list) or not context:
        errors.append("context needs inspected source line ranges and reasons")
    else:
        lines = text.splitlines() if text is not None else None
        for span in context:
            if not isinstance(span, dict):
                errors.append("invalid context range")
                continue
            start, end = span.get("start_line"), span.get("end_line")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end or (
                    lines is not None and end > len(lines)):
                errors.append("context range is outside stored source")
            if not nonempty(span.get("reason")):
                errors.append("context range needs its relevance explained")
    if not nonempty(record.get("source_sha256")):
        errors.append("context review is not bound to inspected source")
    elif text is not None and record["source_sha256"] != fingerprint(text):
        errors.append("source changed since context inspection; inspect again")
    return errors


def argument_digest(audit):
    # Check adds evidence hashes/tier metadata after judging. Those are bound
    # separately; semantic edits, classifications and source assignments are not.
    claims = json.loads(json.dumps(audit["claims"]))
    for claim in claims:
        for adj in claim.get("adjudications", []):
            adj.pop("evidence_sha256", None)
            adj.pop("tier", None)
    return fingerprint({"claims": claims, "assessment": audit.get("evidence_assessment")})


def document_digest(markdown):
    import claim_receipts
    text = claim_receipts.strip_source_annotations(claim_receipts.strip_receipts(markdown))
    return fingerprint(text.strip())


def figure_paths(markdown, review_path):
    """The same local Markdown assets used by the written-review renderer."""
    result = set()
    for path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown):
        path = path.strip().strip("<>")
        if re.match(r"[a-z]+://", path):
            raise ValueError("figure context review requires a local inspected asset")
        result.add(str((Path(review_path).resolve().parent / path).resolve()))
    return result


def record_document(record, audit, markdown, review_path, audit_path):
    import audit_contract
    if not isinstance(record, dict) or not isinstance(record.get("figures"), list):
        raise ValueError("whole-review record must be an object with a figures list")
    record = json.loads(json.dumps(record))
    record["argument_sha256"] = argument_digest(audit)
    record["document_sha256"] = document_digest(markdown)
    for fig in record.get("figures", []):
        if not isinstance(fig, dict) or not nonempty(fig.get("path")):
            raise ValueError("each inspected figure needs a path")
        path = (Path(review_path).resolve().parent / fig["path"]).resolve()
        fig.update(audit_contract.artifact_reference(path, audit_path))
    errors = document_errors(record, audit, audit_path, markdown, review_path, require_preserved=False)
    if errors:
        raise ValueError("; ".join(errors))
    return record


def document_errors(record, audit, audit_path=None, markdown=None, review_path=None, require_preserved=True):
    if not isinstance(record, dict):
        return ["missing final whole-review interpretation check"]
    errors = []
    for key in ("takeaway", "rationale", "limitations"):
        if not nonempty(record.get(key)):
            errors.append("whole-review " + key + " is required")
    if record.get("interpretation") not in {"preserved", "mismatch", "unresolved"}:
        errors.append("invalid whole-review interpretation")
    elif require_preserved and record.get("interpretation") != "preserved":
        errors.append("whole-review interpretation is unresolved or misleading")
    if record.get("argument_sha256") != argument_digest(audit):
        errors.append("assertion judgments changed since whole-review inspection")
    if markdown is not None and record.get("document_sha256") != document_digest(markdown):
        errors.append("document changed since whole-review inspection")
    by_id = {c["id"]: c for c in audit["claims"]}
    def check_basis(ids):
        return isinstance(ids, list) and bool(ids) and all(
            i in by_id and by_id[i].get("classification") in {"factual", "interpretation"} for i in ids)
    no_scientific_claims = not any(c.get("classification") in {"factual", "interpretation"}
                                  for c in audit["claims"])
    if not check_basis(record.get("basis")) and not (no_scientific_claims and record.get("basis") == []):
        errors.append("whole-review takeaway needs checked scientific basis IDs")
    figures = record.get("figures")
    if not isinstance(figures, list):
        return errors + ["whole-review figures must list inspected assets (empty for text only)"]
    actual = set()
    for fig in figures:
        if not isinstance(fig, dict) or not nonempty(fig.get("path")):
            errors.append("invalid inspected figure")
            continue
        if not nonempty(fig.get("observed_meaning")) or not check_basis(fig.get("basis")):
            errors.append("figure needs observed scientific meaning and basis IDs")
        if audit_path is not None:
            path = (Path(audit_path).resolve().parent / fig["path"]).resolve()
            if str(path) in actual:
                errors.append("duplicate inspected figure")
            actual.add(str(path))
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != fig.get("sha256"):
                errors.append("figure changed or missing since semantic inspection: " + fig["path"])
    if markdown is not None and review_path is not None and actual != figure_paths(markdown, review_path):
        errors.append("whole-review inspection must cover exactly the rendered figure assets")
    return errors


def audit_errors(audit, directory=None, audit_path=None, markdown=None, review_path=None):
    if "context_contract_version" not in audit:
        return []  # Historical audits remain readable, without new assurances.
    if audit["context_contract_version"] != VERSION:
        return ["unsupported context contract version"]
    errors = []
    for claim in audit["claims"]:
        for adj in claim.get("adjudications", []):
            if adj.get("verdict") not in {"supported", "partial", "contradicted"}:
                continue
            text = None
            if directory is not None:
                text, _ = claim_evidence.load_evidence(adj["doi"], directory)
                if text is None:
                    errors.append(claim["id"] + ": context source unavailable")
            errors.extend(claim["id"] + ": " + e for e in pair_errors(
                adj.get("context_review"), text, adj.get("verdict")))
    errors.extend(document_errors(audit.get("document_review"), audit, audit_path, markdown, review_path))
    return errors
