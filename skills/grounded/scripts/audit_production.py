#!/usr/bin/env python3
"""Run Grounded's staged, fail-fast journal-review production gate.

The manifest is deliberately small: it points at the live evidence, review,
figure, and release artifacts while recording only the manual decisions that
cannot be inferred from those files.  Existing Grounded validators are called
directly, so a stale pass report cannot release changed inputs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json, sha256_file
import audit_search
from grounded_metadata import FIGURE_MAX_HEIGHT_MM, rendered_figure_size_mm
import qa_figure
from figure_provenance import validate_figure_set
import qa_review_pdf
import validate_review


STAGES = ("evidence", "semantic", "figures", "release")
from review_config import CLAIM_RANGES, TIER_REQUIREMENTS
FIGURE_TARGETS = {size: spec["figure_target"] for size, spec in TIER_REQUIREMENTS.items()}
FIGURE_CAPS = {size: spec["figure_cap"] for size, spec in TIER_REQUIREMENTS.items()}
FULLTEXT_MINIMUMS = {size: spec["fulltexts"][0] for size, spec in TIER_REQUIREMENTS.items()}
FIGURE_KINDS = {
    "synthesis", "mechanism", "study-design", "quantitative",
    "comparison", "uncertainty", "cutaway",
}
SEMANTIC_CHECKS = (
    "claim_traceability",
    "selected_style_structure",
    "selected_style_voice",
    "citation_locality",
    "first_use_term_links",
    "number_density",
    "table_fit",
    "visual_job_distinctness",
)
RELEASE_CHECKS = (
    "all_pages_inspected",
    "figure_text_checked_at_final_size",
    "references_and_links_inspected",
    "independent_audit_completed",
)
ITERATION_FAILURE_CLASSES = {
    "evidence", "writing", "figure-meaning", "figure-copy", "layout",
    "runtime", "external",
}


def _words(value: object) -> int:
    return len(re.findall(r"\b[\w'-]+\b", str(value or "")))


def _block(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    value = manifest.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"production manifest requires an object named {name}")
    return value


def _path(base_dir: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty path")
    result = (base_dir / value).resolve()
    if not result.is_file():
        raise ValueError(f"{field} does not exist: {result}")
    return result


def _json_file(base_dir: Path, value: object, field: str) -> tuple[Path, dict[str, Any]]:
    path = _path(base_dir, value, field)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must contain a JSON object")
    return path, payload


def _override(base_dir: Path, value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return _json_file(
        base_dir, value, "evidence.thin_literature_override"
    )[1]


def _clear_issues(block: dict[str, Any], label: str, errors: list[str]) -> None:
    issues = block.get("unresolved_issues")
    if not isinstance(issues, list):
        errors.append(f"{label}.unresolved_issues must be a list")
    elif issues:
        errors.append(
            f"{label} has unresolved issue(s): "
            + "; ".join(str(item) for item in issues[:5])
        )


def _manual_checks(
    block: dict[str, Any], required: tuple[str, ...], label: str,
    errors: list[str],
) -> None:
    checks = block.get("manual_checks")
    if not isinstance(checks, dict):
        errors.append(f"{label}.manual_checks must be an object")
        return
    missing = [name for name in required if checks.get(name) is not True]
    if missing:
        errors.append(
            f"{label} manual check(s) not passed: " + ", ".join(missing)
        )


def _account_warnings(
    block: dict[str, Any], observed: list[str], label: str,
    errors: list[str], warnings: list[str],
) -> None:
    accepted = block.get("accepted_warnings", [])
    if not isinstance(accepted, list):
        errors.append(f"{label}.accepted_warnings must be a list")
        return
    reasons: dict[str, str] = {}
    for index, record in enumerate(accepted, 1):
        if not isinstance(record, dict):
            errors.append(
                f"{label}.accepted_warnings[{index}] must be an object")
            continue
        message = str(record.get("message") or "").strip()
        reason = str(record.get("reason") or "").strip()
        if not message:
            errors.append(
                f"{label}.accepted_warnings[{index}] requires message")
        elif message in reasons:
            errors.append(f"{label} accepts the same warning more than once: {message}")
        elif _words(reason) < 5:
            errors.append(
                f"{label} warning acceptance requires a substantive reason: {message}")
        else:
            reasons[message] = reason
    unknown = sorted(set(reasons) - set(observed))
    if unknown:
        errors.append(
            f"{label} accepts warning(s) not produced by the live gate: "
            + "; ".join(unknown[:5])
        )
    for message in observed:
        reason = reasons.get(message)
        if reason is None:
            errors.append(f"{label} has an unreviewed warning: {message}")
        else:
            warnings.append(f"{label}: {message}; accepted because {reason}")


def _iteration_budget(
    count: object, *, limit: int, exception: object, label: str,
    errors: list[str], warnings: list[str],
) -> int:
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        errors.append(f"{label} must be a positive integer")
        return 0
    if count <= limit:
        if exception is not None:
            errors.append(f"{label} has an iteration exception but did not exceed its budget")
        return count
    if not isinstance(exception, dict):
        errors.append(
            f"{label} is {count}; normal budget is {limit}, so a diagnosed "
            "iteration_exception is required")
        return count
    failure_class = exception.get("failure_class")
    reason = str(exception.get("reason") or "").strip()
    next_action = str(exception.get("next_action") or "").strip()
    if failure_class not in ITERATION_FAILURE_CLASSES:
        errors.append(
            f"{label} iteration_exception.failure_class must be one of "
            + ", ".join(sorted(ITERATION_FAILURE_CLASSES)))
    if _words(reason) < 8:
        errors.append(f"{label} iteration_exception requires a diagnostic reason")
    if _words(next_action) < 5:
        errors.append(f"{label} iteration_exception requires a bounded next_action")
    if (failure_class in ITERATION_FAILURE_CLASSES
            and _words(reason) >= 8 and _words(next_action) >= 5):
        warnings.append(
            f"{label} exceeded the normal budget ({count}>{limit}); "
            f"diagnosed as {failure_class}: {reason}")
    return count


def audit_synthesis(
    text: str, *, size: str, ledger_keys: set[str],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    headings = ("## Verdict", "## Throughline", "## Claims", "## Patterns", "## Open")
    positions = [text.find(heading) for heading in headings]
    missing = [heading for heading, position in zip(headings, positions) if position < 0]
    if missing:
        errors.append("synthesis is missing exact heading(s): " + ", ".join(missing))
    elif positions != sorted(positions):
        errors.append("synthesis headings are out of contract order")

    matches = list(re.finditer(r"^###\s+(C\d+)\.\s+(.+)$", text, re.M))
    claim_ids = [match.group(1) for match in matches]
    expected_ids = [f"C{index}" for index in range(1, len(matches) + 1)]
    if claim_ids != expected_ids:
        errors.append("synthesis claim IDs must be consecutive from C1")
    required_fields = (
        "strength", "evidence", "contrary", "boundary", "depends-on", "numbers",
    )
    cited_keys: set[str] = set()
    dependencies: dict[str, list[str]] = {}
    try:
        import synthesis_quotes
        errors.extend(synthesis_quotes.hollow_problems(synthesis_quotes.parse_claims(text)))
    except ImportError:
        warnings.append("synthesis_quotes unavailable; hollow-synthesis checks skipped")
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end]
        values: dict[str, str] = {}
        for field in required_fields:
            field_match = re.search(
                rf"^- {re.escape(field)}:\s*(.*(?:\n(?!- [a-z-]+:|### |## ).*)*)",
                block, re.M,
            )
            if field_match is None or not field_match.group(1).strip():
                errors.append(f"synthesis {match.group(1)} is missing - {field}:")
            else:
                values[field] = field_match.group(1).strip()
        evidence = values.get("evidence", "")
        contrary = values.get("contrary", "")
        if evidence and not re.search(r"\[@[^\]]+\]", evidence):
            errors.append(f"synthesis {match.group(1)} evidence has no ledger key")
        if contrary and not (
            re.search(r"\[@[^\]]+\]", contrary)
            or re.search(r"\bnone found\s*[—-]\s*searched\b", contrary, re.I)
        ):
            errors.append(
                f"synthesis {match.group(1)} contrary field needs keys or "
                "'none found — searched'")
        cited_keys.update(re.findall(r"@([A-Za-z0-9_.:-]+)", evidence + "\n" + contrary))
        dependencies[match.group(1)] = re.findall(
            r"\bC\d+\b", values.get("depends-on", ""))

    known = set(claim_ids)
    for claim_id, refs in dependencies.items():
        current = int(claim_id[1:]) if claim_id[1:].isdigit() else 0
        for dependency in refs:
            if dependency not in known:
                errors.append(f"synthesis {claim_id} depends on unknown {dependency}")
            elif int(dependency[1:]) >= current:
                errors.append(
                    f"synthesis {claim_id} must follow, not precede, dependency {dependency}")
    missing_ledger = sorted(cited_keys - ledger_keys)
    if missing_ledger:
        errors.append(
            "synthesis cites key(s) absent from the ledger: "
            + ", ".join(missing_ledger[:12]))
    minimum, maximum = CLAIM_RANGES[size]
    if not minimum <= len(matches) <= maximum:
        warnings.append(
            f"{size} synthesis guidance is {minimum}–{maximum} claims; found {len(matches)}")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "claims": len(matches),
            "cited_ledger_keys": len(cited_keys),
        },
    }


def audit_visual_jobs(
    jobs: object, *, size: str, claim_count: int | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(jobs, list) or not jobs:
        return {
            "status": "fail",
            "errors": ["semantic.visual_jobs must be a non-empty list"],
            "warnings": [],
            "metrics": {"visual_jobs": 0},
        }
    ids: list[str] = []
    questions: list[str] = []
    synthesis_positions: list[int] = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"semantic.visual_jobs[{index + 1}] must be an object")
            continue
        job_id = str(job.get("id") or "").strip()
        kind = job.get("kind")
        question = re.sub(r"\s+", " ", str(job.get("question") or "").strip())
        evidence_keys = job.get("evidence_keys")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", job_id):
            errors.append(f"visual job {index + 1} has an invalid stable id")
        if kind not in FIGURE_KINDS:
            errors.append(f"visual job {job_id or index + 1} has invalid kind {kind!r}")
        if _words(question) < 4:
            errors.append(f"visual job {job_id or index + 1} needs one specific question")
        if not isinstance(evidence_keys, list) or not evidence_keys or not all(
            isinstance(key, str) and re.fullmatch(r"[CP]\d+", key)
            for key in evidence_keys
        ):
            errors.append(
                f"visual job {job_id or index + 1} needs synthesis C/P evidence_keys")
        elif claim_count is not None:
            unknown_claims = [
                key for key in evidence_keys
                if key.startswith("C") and int(key[1:]) > claim_count
            ]
            if unknown_claims:
                errors.append(
                    f"visual job {job_id or index + 1} cites unknown synthesis "
                    "claim(s): " + ", ".join(unknown_claims))
        if kind == "synthesis":
            synthesis_positions.append(index)
        ids.append(job_id)
        questions.append(question.casefold())
    if len(set(ids)) != len(ids):
        errors.append("visual job IDs must be unique")
    if len(set(questions)) != len(questions):
        errors.append("visual jobs must ask distinct reader-facing questions")
    if synthesis_positions != [0]:
        errors.append("exactly the first visual job must be the whole-answer synthesis")
    if len(jobs) > FIGURE_CAPS[size]:
        errors.append(
            f"{size} production permits at most {FIGURE_CAPS[size]} visual jobs; "
            f"found {len(jobs)}")
    if len(jobs) < FIGURE_TARGETS[size]:
        warnings.append(
            f"{size} journal-PDF target is {FIGURE_TARGETS[size]} distinct visual jobs; "
            f"planned {len(jobs)}")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": {"visual_jobs": len(jobs)},
    }


def _audit_evidence(
    manifest: dict[str, Any], base_dir: Path, state: dict[str, Any],
    errors: list[str], warnings: list[str],
) -> dict[str, Any]:
    block = _block(manifest, "evidence")
    size = state["size"]
    if block.get("frozen") is not True:
        errors.append("evidence.frozen must be true before drafting")
    _clear_issues(block, "evidence", errors)
    _ledger_path, ledger = _json_file(base_dir, block.get("ledger"), "evidence.ledger")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        errors.append("evidence ledger entries must be a list")
        entries = []
    ledger_keys = {
        str(entry.get("key")) for entry in entries
        if isinstance(entry, dict) and entry.get("key")
    }
    _search_path, search_manifest = _json_file(
        base_dir, block.get("search_manifest"), "evidence.search_manifest")
    thin_override = _override(base_dir, block.get("thin_literature_override"))
    search_result = audit_search.audit_search(
        search_manifest, size=size, thin_literature_override=thin_override)
    errors.extend(f"search: {item}" for item in search_result["errors"])
    observed_warnings = [f"search: {item}" for item in search_result["warnings"]]

    _fulltext_path, fulltext = _json_file(
        base_dir, block.get("fulltext_manifest"), "evidence.fulltext_manifest")
    if fulltext.get("schema_version") != 1:
        errors.append("full-text manifest schema_version must be 1")
    summary = fulltext.get("summary")
    counted = (
        summary.get("counted_with_complete_notes", 0)
        if isinstance(summary, dict) else 0)
    minimum = FULLTEXT_MINIMUMS[size]
    if not isinstance(counted, int) or isinstance(counted, bool):
        errors.append("full-text manifest counted total must be an integer")
        counted = 0
    if counted < minimum:
        allowed = (
            set(thin_override.get("allowed_shortfalls", []))
            if isinstance(thin_override, dict)
            and isinstance(thin_override.get("allowed_shortfalls", []), list)
            else set())
        reason = str((thin_override or {}).get("reason") or "")
        evidence = (thin_override or {}).get("saturation_evidence")
        if ("fulltexts" in allowed and _words(reason) >= 5
                and isinstance(evidence, list) and evidence):
            warnings.append(
                f"full-text shortfall {counted}/{minimum} accepted by the "
                f"thin-literature override: {reason}")
        else:
            errors.append(
                f"{size} production requires {minimum}+ counted full texts; found {counted}")

    synthesis_path = _path(base_dir, block.get("synthesis"), "evidence.synthesis")
    synthesis_result = audit_synthesis(
        synthesis_path.read_text(encoding="utf-8"),
        size=size,
        ledger_keys=ledger_keys,
    )
    errors.extend(synthesis_result["errors"])
    observed_warnings.extend(synthesis_result["warnings"])
    import evidence_assessment
    _assessment_path, assessment = _json_file(
        base_dir, block.get("assessment"), "evidence.assessment")
    assessed = evidence_assessment.assess(assessment, ledger, synthesis_path.read_text(encoding="utf-8"))
    errors.extend(assessed["errors"])
    observed_warnings.extend(assessed["warnings"])
    _account_warnings(
        block, observed_warnings, "evidence", errors, warnings)
    state.update({
        "ledger": ledger,
        "fulltext": fulltext,
        "thin_override": thin_override,
        "synthesis_claims": synthesis_result["metrics"]["claims"],
    })
    return {
        "search": search_result["metrics"],
        "counted_fulltexts": counted,
        **synthesis_result["metrics"],
    }


def _live_review_validation(
    manifest: dict[str, Any], base_dir: Path, state: dict[str, Any], *,
    image_mode: bool,
) -> tuple[Path, dict[str, Any]]:
    semantic = _block(manifest, "semantic")
    review_path = _path(base_dir, semantic.get("review"), "semantic.review")
    result = validate_review.validate_review(
        review_path.read_text(encoding="utf-8"),
        style=state["style"],
        size=state["size"],
        base_dir=review_path.parent,
        strict_tier=True,
        image_mode=image_mode,
        ledger=state["ledger"],
        fulltext_manifest=state["fulltext"],
        thin_literature_override=state["thin_override"],
    )
    return review_path, result.as_dict()


def _audit_semantic(
    manifest: dict[str, Any], base_dir: Path, state: dict[str, Any],
    errors: list[str], warnings: list[str],
) -> dict[str, Any]:
    block = _block(manifest, "semantic")
    _clear_issues(block, "semantic", errors)
    _manual_checks(block, SEMANTIC_CHECKS, "semantic", errors)
    review_path, result = _live_review_validation(
        manifest, base_dir, state, image_mode=False)
    errors.extend(f"review: {item}" for item in result["errors"])
    visual_result = audit_visual_jobs(
        block.get("visual_jobs"), size=state["size"],
        claim_count=state["synthesis_claims"],
    )
    errors.extend(visual_result["errors"])
    observed = [f"review: {item}" for item in result["warnings"]]
    observed.extend(visual_result["warnings"])
    _account_warnings(block, observed, "semantic", errors, warnings)
    state.update({
        "review_path": review_path,
        "visual_jobs": block.get("visual_jobs") if isinstance(
            block.get("visual_jobs"), list) else [],
    })
    return {**result["metrics"], **visual_result["metrics"]}


def _audit_figures(
    manifest: dict[str, Any], base_dir: Path, state: dict[str, Any],
    errors: list[str], warnings: list[str],
) -> dict[str, Any]:
    block = _block(manifest, "figures")
    _clear_issues(block, "figures", errors)
    _iteration_budget(
        block.get("full_set_cycles"), limit=1,
        exception=block.get("iteration_exception"),
        label="figures.full_set_cycles", errors=errors, warnings=warnings)
    items = block.get("items")
    if not isinstance(items, list):
        errors.append("figures.items must be a list")
        items = []
    planned_ids = [str(job.get("id")) for job in state["visual_jobs"]]
    item_ids = [
        str(item.get("job_id")) for item in items if isinstance(item, dict)]
    if item_ids != planned_ids:
        errors.append("figure item job_ids must match visual-job order exactly")

    figure_results: list[dict[str, Any]] = []
    figure_specs = []
    figure_provenances = []
    observed: list[str] = []
    total_authored_attempts = 0
    max_height = state["figure_max_height_mm"]
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append(f"figures.items[{index}] must be an object")
            continue
        label = f"figure {item.get('job_id') or index}"
        _spec_path, spec = _json_file(
            base_dir, item.get("spec"), f"{label}.spec")
        if spec.get("quality_contract_version") != 3:
            errors.append(f"{label} must use quality_contract_version 3")
        image_path = _path(base_dir, item.get("image"), f"{label}.image")
        _inspection_path, inspection = _json_file(
            base_dir, item.get("inspection"), f"{label}.inspection")
        _provenance_path, provenance = _json_file(
            base_dir, item.get("provenance"), f"{label}.provenance")
        figure_specs.append(spec)
        figure_provenances.append(provenance)
        try:
            from PIL import Image
            with Image.open(image_path) as image:
                width, height = image.size
        except (ImportError, OSError) as exc:
            raise ValueError(f"{label} dimensions cannot be read: {exc}") from exc
        rendered_width, _ = rendered_figure_size_mm(
            width, height, max_height_mm=max_height)
        result = qa_figure.audit_figure(
            spec, image_path, inspection=inspection, provenance=provenance,
            pdf_width_mm=rendered_width,
        )
        errors.extend(f"{label}: {message}" for message in result["errors"])
        observed.extend(f"{label}: {message}" for message in result["warnings"])
        attempts = provenance.get("attempts")
        authored_attempts = sum(
            1 for attempt in attempts
            if isinstance(attempt, dict)
            and attempt.get("kind") in {"generate", "edit", "render", "compose"}
        ) if isinstance(attempts, list) else 0
        total_authored_attempts += authored_attempts
        if authored_attempts:
            _iteration_budget(
                authored_attempts, limit=3,
                exception=item.get("iteration_exception"),
                label=f"{label} authored attempts",
                errors=errors, warnings=warnings)
        result["job_id"] = item.get("job_id")
        figure_results.append(result)
    errors.extend(validate_figure_set(figure_specs, figure_provenances))
    _account_warnings(block, observed, "figures", errors, warnings)
    state["figure_results"] = figure_results
    return {
        "figures": len(figure_results),
        "authored_attempts": total_authored_attempts,
        "figure_qa": figure_results,
    }


def release_figure_errors(
    figure_results: list[dict[str, Any]], records: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if len(figure_results) != len(records):
        return [
            "release figure count does not match the live figure-QA set: "
            f"{len(records)} vs {len(figure_results)}"]
    for result, record in zip(figure_results, records):
        metrics = result.get("metrics") if isinstance(result, dict) else None
        metrics = metrics if isinstance(metrics, dict) else {}
        digest = str(metrics.get("image_sha256") or "")
        if not isinstance(record, dict) or record.get("sha256") != digest:
            errors.append(
                f"release figure order/hash does not match live-QA figure "
                f"{result.get('job_id')!r}")
            continue
        evaluated = float(metrics.get("evaluated_rendered_width_mm") or 0.0)
        released = float(record.get("rendered_width_mm") or 0.0)
        if abs(evaluated - released) > 0.5:
            errors.append(
                f"release figure {result.get('job_id')!r} was QA'd at "
                f"{evaluated:.1f} mm but renders at {released:.1f} mm")
    return errors


def _audit_recorded_render_set(
    manifest_path: Path, release_manifest: dict[str, Any], errors: list[str],
) -> int:
    qa = release_manifest.get("qa")
    if not isinstance(qa, dict) or qa.get("status") != "pass":
        errors.append("release manifest has no passing authoritative PDF QA render set")
        return 0
    files = qa.get("files")
    if not isinstance(files, list) or not files:
        errors.append("release manifest PDF QA render set is empty")
        return 0
    for index, record in enumerate(files, 1):
        if not isinstance(record, dict):
            errors.append(f"release QA file record {index} is invalid")
            continue
        try:
            path = _path(manifest_path.parent, record.get("path"), f"release.qa.files[{index}]")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if record.get("bytes") != path.stat().st_size:
            errors.append(f"release QA file byte count changed: {path.name}")
        if record.get("sha256") != sha256_file(path):
            errors.append(f"release QA file hash changed: {path.name}")
    pages = qa.get("rendered_pages")
    if not isinstance(pages, int) or isinstance(pages, bool) or pages < 1:
        errors.append("release QA rendered_pages must be a positive integer")
        return 0
    if len(files) < pages:
        errors.append("release QA render set contains fewer files than rendered pages")
    return pages


def _audit_release(
    manifest: dict[str, Any], base_dir: Path, state: dict[str, Any],
    errors: list[str], warnings: list[str],
) -> dict[str, Any]:
    block = _block(manifest, "release")
    _clear_issues(block, "release", errors)
    _manual_checks(block, RELEASE_CHECKS, "release", errors)
    builds = _iteration_budget(
        block.get("full_document_builds"), limit=2,
        exception=block.get("iteration_exception"),
        label="release.full_document_builds", errors=errors, warnings=warnings)
    review_path, validation = _live_review_validation(
        manifest, base_dir, state, image_mode=True)
    errors.extend(f"final review: {item}" for item in validation["errors"])
    observed = [f"final review: {item}" for item in validation["warnings"]]
    _account_warnings(block, observed, "release", errors, warnings)

    release_manifest_path = _path(
        base_dir, block.get("manifest"), "release.manifest")
    pdf_path = _path(base_dir, block.get("pdf"), "release.pdf")
    try:
        context = qa_review_pdf.verify_release_manifest(
            str(release_manifest_path), str(pdf_path), str(review_path))
    except qa_review_pdf.PdfQaError as exc:
        errors.append(f"release manifest: {exc}")
        return {
            **validation["metrics"], "full_document_builds": builds,
            "rendered_pages": 0,
        }
    release_manifest = context["manifest"]
    claims_audit_name = block.get("claims_audit")
    if claims_audit_name:
        recorded = (release_manifest.get("inputs") or {}).get("claims_audit")
        if not isinstance(recorded, dict):
            errors.append(
                "release.claims_audit is declared but the release manifest "
                "records no claim audit; export with --claims-audit")
        else:
            try:
                declared = _path(base_dir, claims_audit_name, "release.claims_audit")
                recorded_path = (release_manifest_path.parent
                                 / str(recorded.get("path"))).resolve()
                if declared.resolve() != recorded_path:
                    errors.append(
                        "release.claims_audit is not the audit the release "
                        "manifest records")
            except ValueError as exc:
                errors.append(str(exc))
    rendered_pages = _audit_recorded_render_set(
        release_manifest_path, release_manifest, errors)
    render = release_manifest.get("render")
    render = render if isinstance(render, dict) else {}
    if str(render.get("style") or "") != state["style"]:
        errors.append("release manifest style does not match production style")
    recorded_height = float(render.get("figure_max_height_mm") or 0.0)
    if abs(recorded_height - state["figure_max_height_mm"]) > 0.01:
        errors.append(
            "release figure_max_height_mm changed after figure QA: "
            f"{state['figure_max_height_mm']:.1f} to {recorded_height:.1f}")
    figure_records = context.get("figure_records")
    if not isinstance(figure_records, list):
        errors.append("release manifest figure records must be a list")
        figure_records = []
    errors.extend(release_figure_errors(state["figure_results"], figure_records))
    return {
        **validation["metrics"],
        "full_document_builds": builds,
        "rendered_pages": rendered_pages,
        "claim_summary": context.get("claim_summary"),
    }


USAGE_COUNTERS = ("input_tokens", "output_tokens", "cache_read_input_tokens")


def _usage_summary(manifest: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """Token accounting per stage, recorded when the host reports it.

    Each stage block may carry ``usage``: ``{"model": str, "input_tokens": int,
    "output_tokens": int, "cache_read_input_tokens": int}`` (counters
    optional, non-negative). Usage is never a gate — it is the cost
    visibility every other cleanup is measured against — so a missing block
    is recorded as unrecorded, not as a failure; a malformed one is an error.
    """
    stages: dict[str, Any] = {}
    totals = {name: 0 for name in USAGE_COUNTERS}
    for stage in STAGES:
        block = manifest.get(stage)
        usage = block.get("usage") if isinstance(block, dict) else None
        if usage is None:
            continue
        if not isinstance(usage, dict):
            errors.append(f"{stage}.usage must be an object")
            continue
        record: dict[str, Any] = {}
        model = usage.get("model")
        if model is not None:
            if not isinstance(model, str) or not model.strip():
                errors.append(f"{stage}.usage.model must be a non-empty string")
            else:
                record["model"] = model.strip()
        for name in USAGE_COUNTERS:
            value = usage.get(name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"{stage}.usage.{name} must be a non-negative integer")
                continue
            record[name] = value
            totals[name] += value
        stages[stage] = record
    return {
        "recorded": bool(stages),
        "stages": stages,
        **{f"total_{name}": totals[name] for name in USAGE_COUNTERS},
    }


def audit_production(
    manifest: dict[str, Any], *, base_dir: Path, target_stage: str,
) -> dict[str, Any]:
    if manifest.get("schema_version") != 1:
        raise ValueError("production manifest schema_version must be 1")
    if target_stage not in STAGES:
        raise ValueError(f"unsupported production stage: {target_stage}")
    size = manifest.get("size")
    if size not in CLAIM_RANGES:
        raise ValueError("production size must be small, medium, or large")
    style = "scientific" if manifest.get("style") == "prose" else manifest.get("style")
    if style not in {"scientific", "popsci", "bullets", "eli5"}:
        raise ValueError("production style is invalid")
    if manifest.get("output_format") != "journal-pdf":
        raise ValueError("staged production currently supports output_format journal-pdf")
    case_id = str(manifest.get("case_id") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", case_id):
        raise ValueError("production case_id must be a stable lowercase slug")
    render = manifest.get("render", {})
    if not isinstance(render, dict):
        raise ValueError("production render must be an object")
    max_height = render.get("figure_max_height_mm", FIGURE_MAX_HEIGHT_MM)
    try:
        max_height = float(max_height)
    except (TypeError, ValueError) as exc:
        raise ValueError("render.figure_max_height_mm must be numeric") from exc
    if not 60.0 <= max_height <= 120.0:
        raise ValueError("render.figure_max_height_mm must be between 60 and 120")

    state: dict[str, Any] = {
        "size": size,
        "style": style,
        "figure_max_height_mm": max_height,
    }
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "case_id": case_id,
        "size": size,
        "style": style,
        "output_format": "journal-pdf",
        "target_stage": target_stage,
        "completed_stages": [],
        "stages": {},
    }
    auditors = {
        "evidence": _audit_evidence,
        "semantic": _audit_semantic,
        "figures": _audit_figures,
        "release": _audit_release,
    }
    for stage in STAGES[:STAGES.index(target_stage) + 1]:
        before = len(errors)
        metrics["stages"][stage] = auditors[stage](
            manifest, base_dir, state, errors, warnings)
        if len(errors) != before:
            break
        metrics["completed_stages"].append(stage)
    metrics["usage"] = _usage_summary(manifest, errors)
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="production.json")
    parser.add_argument("--stage", choices=STAGES, default="release")
    parser.add_argument("--report", help="atomically write the production audit report")
    args = parser.parse_args(argv)
    try:
        manifest_path = Path(args.manifest).resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("production manifest must contain a JSON object")
        result = audit_production(
            manifest, base_dir=manifest_path.parent, target_stage=args.stage)
        if args.report:
            atomic_write_json(args.report, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Production audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
