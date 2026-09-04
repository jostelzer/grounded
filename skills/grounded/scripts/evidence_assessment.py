"""Structured outcome certainty and study-family accounting, separate from quote support."""
import argparse
from datetime import date
import json
from pathlib import Path

from artifact_io import atomic_write_json
import synthesis_quotes

DOMAINS = ("risk_of_bias", "inconsistency", "indirectness", "imprecision", "publication_bias")
JUDGMENTS = {"low", "some", "high", "unclear", "not_applicable"}
CERTAINTIES = {"high", "moderate", "low", "very_low"}


def assess(document, ledger, synthesis):
    errors, warnings = [], []
    if not isinstance(document, dict):
        return {"status": "fail", "errors": ["assessment must be an object"], "warnings": [], "metrics": {}}
    if not isinstance(document.get("scope"), dict) or any(
            not isinstance(document.get(name), list) or
            any(not isinstance(item, dict) for item in document[name])
            for name in ("studies", "outcomes")):
        return {"status": "fail", "errors": ["assessment needs a scope object and studies/outcomes object lists"], "warnings": [], "metrics": {}}
    if document.get("schema_version") != 1:
        errors.append("assessment schema_version must be 1")
    scope = document.get("scope", {})
    for field in ("question", "review_type", "search_date", "databases", "inclusion",
                  "exclusion", "access_limitations"):
        if not scope.get(field):
            errors.append("scope requires " + field)
    try:
        date.fromisoformat(scope.get("search_date", ""))
    except (TypeError, ValueError):
        errors.append("scope.search_date must be ISO YYYY-MM-DD")
    if scope.get("review_type") not in {"narrative", "systematic"}:
        errors.append("scope.review_type must be narrative or systematic")
    if scope.get("review_type") == "systematic" and not scope.get("protocol"):
        errors.append("systematic review requires protocol and screening-method reference")
    claims = synthesis_quotes.parse_claims(synthesis)
    claim_keys = {c["id"]: set(c["keys"]) for c in claims}
    needed = set().union(*claim_keys.values()) if claim_keys else set()
    keys = {e["key"] for e in ledger.get("entries", [])}
    studies = document.get("studies", [])
    for item in studies + document["outcomes"]:
        for name in ("source_keys", "claim_ids", "underlying_study_ids"):
            if name in item and (not isinstance(item[name], list) or
                                 any(not isinstance(value, str) for value in item[name])):
                errors.append(name + " must be a list of strings")
        if "domains" in item and (not isinstance(item["domains"], dict) or
                                   any(not isinstance(v, dict) for v in item["domains"].values())):
            errors.append("domains must map names to judgment objects")
    if errors:
        return {"status": "fail", "errors": errors, "warnings": [], "metrics": {}}
    ids, assigned = set(), {}
    for study in studies:
        sid = study.get("id")
        if not sid or sid in ids:
            errors.append("study IDs must be nonempty and unique")
        ids.add(sid)
        if study.get("kind") not in {"primary", "review"}:
            errors.append(f"{sid}: kind must be primary or review")
        if not study.get("source_keys") or not study.get("design"):
            errors.append(f"{sid}: requires source_keys and design")
        for key in study.get("source_keys", []):
            if key not in keys or key in assigned:
                errors.append(f"{sid}: unknown or multiply assigned source {key}")
            assigned[key] = sid
        if study.get("kind") == "review":
            if study.get("overlap_status") == "known" and "underlying_study_ids" not in study:
                errors.append(f"{sid}: known overlap requires underlying_study_ids (empty if none)")
            if study.get("overlap_status") not in {"known", "unknown"} or not study.get("overlap_note"):
                errors.append(f"{sid}: review requires overlap_status and overlap_note")
            if study.get("overlap_status") == "unknown":
                warnings.append(f"{sid}: overlap unknown; do not count this review as independent confirmation")
    for study in studies:
        for sid in study.get("underlying_study_ids", []):
            target = next((s for s in studies if s.get("id") == sid), None)
            if target is None or target.get("kind") != "primary":
                errors.append(f"{study.get('id')}: underlying study {sid} must identify a primary study")
    if needed - set(assigned):
        errors.append("synthesis sources missing study-family assignment: " + ", ".join(sorted(needed - set(assigned))))
    covered, outcome_ids = set(), set()
    for outcome in document.get("outcomes", []):
        oid = outcome.get("id")
        if not oid or oid in outcome_ids:
            errors.append("outcome IDs must be nonempty and unique")
        outcome_ids.add(oid)
        if outcome.get("certainty") not in CERTAINTIES or not outcome.get("rationale"):
            errors.append(f"{oid}: certainty and its rationale are required")
        if not outcome.get("outcome") or not outcome.get("claim_ids"):
            errors.append(f"{oid}: outcome and claim_ids are required")
        for domain in DOMAINS:
            entry = outcome.get("domains", {}).get(domain, {})
            if entry.get("judgment") not in JUDGMENTS or not entry.get("reason"):
                errors.append(f"{oid}: {domain} needs a judgment and reason")
        sources = set(outcome.get("source_keys", []))
        for cid in outcome.get("claim_ids", []):
            if cid not in claim_keys:
                errors.append(f"{oid}: unknown synthesis claim {cid}")
            elif not claim_keys[cid] <= sources:
                errors.append(f"{oid}: source_keys omit evidence for {cid}")
            covered.add(cid)
        if sources - keys:
            errors.append(f"{oid}: unknown source_keys")
    if set(claim_keys) - covered:
        errors.append("claims lack outcome certainty assessment: " + ", ".join(sorted(set(claim_keys) - covered)))
    return {"status": "fail" if errors else "pass", "errors": errors, "warnings": warnings,
            "metrics": {"outcomes": len(outcome_ids), "study_families": len(ids),
                        "publications": len(assigned)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--synthesis", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    result = assess(json.loads(Path(args.assessment).read_text()),
                    json.loads(Path(args.ledger).read_text()), Path(args.synthesis).read_text())
    if args.report:
        atomic_write_json(args.report, result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
