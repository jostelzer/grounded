#!/usr/bin/env python3
"""Validate a structured Grounded search funnel against the requested tier."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


from review_config import SEARCH_REQUIREMENTS as REQUIREMENTS
LARGE_LANES = {"reviews", "primary", "foundational", "recent", "contrary-null"}


def _bounds(actual: int, bounds: tuple[int, int | None]) -> bool:
    minimum, maximum = bounds
    return actual >= minimum and (maximum is None or actual <= maximum)


def _expected(bounds: tuple[int, int | None]) -> str:
    minimum, maximum = bounds
    return f"{minimum}+" if maximum is None else f"{minimum}–{maximum}"


def _override(value: dict[str, Any] | None) -> tuple[set[str], str | None]:
    if value is None:
        return set(), None
    reason = value.get("reason")
    evidence = value.get("saturation_evidence")
    allowed = value.get("allowed_search_shortfalls", [])
    if not isinstance(reason, str) or len(reason.split()) < 5:
        raise ValueError("thin-literature override requires a substantive reason")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("thin-literature override requires saturation_evidence")
    if not isinstance(allowed, list):
        raise ValueError("allowed_search_shortfalls must be a list")
    names = set(allowed)
    if not names <= {"angles", "queries", "citation_chases", "lanes"}:
        raise ValueError("unknown allowed_search_shortfalls value")
    return names, reason


def audit_search(
    manifest: dict[str, Any], *, size: str,
    thin_literature_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if size not in REQUIREMENTS:
        raise ValueError(f"unsupported size: {size}")
    if manifest.get("schema_version") != 1:
        raise ValueError("search manifest schema_version must be 1")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("search manifest records must be a list")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("every search manifest record must be an object")

    overridden, reason = _override(thin_literature_override)
    errors: list[str] = []
    warnings: list[str] = []

    def issue(category: str, message: str, *, shortfall: bool = True) -> None:
        if category in overridden and shortfall:
            warnings.append(f"{message}; accepted by thin-literature override: {reason}")
        else:
            errors.append(message)

    completed = [record for record in records if record.get("completed") is True]
    superseded_count = sum(
        1 for record in completed if record.get("superseded") is True
    )
    keyword = [
        record for record in completed
        if not record.get("citation_direction")
        and record.get("method") == "keyword"
        and record.get("superseded") is not True
    ]
    by_angle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    labels: dict[str, set[str]] = defaultdict(set)
    for record in keyword:
        angle_id = str(record.get("angle_id") or "")
        if angle_id and angle_id != "unassigned":
            by_angle[angle_id].append(record)
            labels[angle_id].add(str(record.get("angle") or ""))
    ambiguous = sorted(angle for angle, values in labels.items() if len(values) > 1)
    if ambiguous:
        errors.append("angle ID(s) map to multiple labels: " + ", ".join(ambiguous))

    requirement = REQUIREMENTS[size]
    angle_minimum, angle_maximum = requirement["angles"]
    if len(by_angle) < angle_minimum:
        issue(
            "angles",
            f"{size} search requires {_expected(requirement['angles'])} completed angles; "
            f"found {len(by_angle)}",
        )
    elif angle_maximum is not None and len(by_angle) > angle_maximum:
        # Over-searching is over-diligence, not an evidence-quality problem:
        # minima stay hard errors, maxima advise.
        warnings.append(
            f"{size} search suggests at most {angle_maximum} angles; "
            f"found {len(by_angle)}"
        )
    query_counts: dict[str, int] = {}
    for angle_id, angle_records in sorted(by_angle.items()):
        accepted_by_query: dict[str, int] = {}
        for record in angle_records:
            query = str(record.get("requested_query_or_seed") or "").strip().lower()
            if not query:
                continue
            accepted_by_query[query] = (
                accepted_by_query.get(query, 0) + int(record.get("accepted") or 0)
            )
        queries = set(accepted_by_query)
        # A completed query that accepted nothing was real effort (it counts
        # toward the minimum) but adds no redundancy (it never counts toward
        # the maximum).
        productive = {q for q, count in accepted_by_query.items() if count > 0}
        query_counts[angle_id] = len(queries)
        query_minimum, query_maximum = requirement["queries"]
        if len(queries) < query_minimum:
            issue(
                "queries",
                f"angle {angle_id} requires {_expected(requirement['queries'])} "
                f"distinct completed queries; found {len(queries)}",
            )
        elif query_maximum is not None and len(productive) > query_maximum:
            warnings.append(
                f"angle {angle_id} suggests at most {query_maximum} distinct "
                f"productive queries; found {len(productive)}"
            )

    lanes = {str(record.get("lane")) for record in keyword}
    required_lanes = LARGE_LANES if size == "large" else {"contrary-null"}
    missing_lanes = sorted(required_lanes - lanes)
    if missing_lanes:
        # Contrary searches must complete even when they return no disagreement.
        if "contrary-null" in missing_lanes:
            errors.append("search requires a completed contrary-null lane")
        remaining = [lane for lane in missing_lanes if lane != "contrary-null"]
        if remaining:
            issue("lanes", "search is missing lane(s): " + ", ".join(remaining))

    chase_by_seed: dict[str, set[str]] = defaultdict(set)
    for record in completed:
        direction = record.get("citation_direction")
        seed = str(record.get("requested_query_or_seed") or "").strip()
        if direction in {"backward", "forward"} and seed:
            chase_by_seed[seed].add(str(direction))
    both = sorted(
        seed for seed, directions in chase_by_seed.items()
        if directions == {"backward", "forward"}
    )
    if not _bounds(len(both), requirement["central"]):
        issue(
            "citation_chases",
            f"{size} search requires {_expected(requirement['central'])} central papers "
            f"with completed backward and forward audits; found {len(both)}",
            shortfall=len(both) < requirement["central"][0],
        )

    failed = [record for record in records if record.get("completed") is not True]
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "size": size,
            "attempted_records": len(records),
            "completed_records": len(completed),
            "superseded_records": superseded_count,
            "failed_or_incomplete_records": len(failed),
            "completed_angles": len(by_angle),
            "completed_queries_by_angle": query_counts,
            "completed_lanes": sorted(lanes),
            "both_direction_central_papers": len(both),
            "central_papers": both,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="search-manifest.json")
    parser.add_argument("--size", choices=tuple(REQUIREMENTS), required=True)
    parser.add_argument("--thin-literature-override")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        override = (
            json.loads(Path(args.thin_literature_override).read_text(encoding="utf-8"))
            if args.thin_literature_override else None
        )
        result = audit_search(
            manifest, size=args.size, thin_literature_override=override
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Search audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
