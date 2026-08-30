#!/usr/bin/env python3
"""Validate Grounded figure-generation provenance records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from artifact_io import sha256_file

def validate_provenance(
    spec: dict[str, Any], image_path: Path,
    provenance: dict[str, Any] | None,
) -> list[str]:
    """Return fail-closed provenance errors for quality-contract figures."""
    errors: list[str] = []
    contract_version = spec.get("quality_contract_version")
    if provenance is None:
        if contract_version in {1, 2, 3}:
            errors.append(
                f"quality contract v{contract_version} requires generation provenance")
        return errors
    if not isinstance(provenance, dict):
        raise ValueError("figure provenance must be an object")
    expected_schema = 2 if contract_version in {2, 3} else 1
    if provenance.get("schema_version") != expected_schema:
        errors.append(
            f"generation provenance schema_version must be {expected_schema}")

    generator_available = provenance.get("generator_available")
    if not isinstance(generator_available, bool):
        errors.append("generation provenance requires boolean generator_available")
        generator_available = False
    if generator_available:
        generator = provenance.get("generator")
        if not isinstance(generator, dict) or not str(generator.get("tool") or "").strip():
            errors.append("available generator provenance requires generator.tool")

    route = spec.get("render_route")
    selected_route = provenance.get("selected_route")
    if contract_version in {1, 2, 3} and route not in {
        "generated", "hybrid", "deterministic", "composite"
    }:
        errors.append("quality contract requires an explicit valid render_route")
    if selected_route != route:
        errors.append(
            f"provenance selected_route {selected_route!r} does not match spec {route!r}")

    selected_asset = provenance.get("selected_asset")
    if not isinstance(selected_asset, str) or Path(selected_asset).name != image_path.name:
        errors.append("provenance selected_asset does not identify the audited image")
    expected_hash = provenance.get("selected_sha256")
    actual_hash = sha256_file(image_path)
    if expected_hash != actual_hash:
        errors.append("provenance selected_sha256 does not match the audited image")

    attempts = provenance.get("attempts")
    if not isinstance(attempts, list):
        errors.append("generation provenance attempts must be a list")
        attempts = []
    elif any(not isinstance(item, dict) for item in attempts):
        errors.append("every generation provenance attempt must be an object")
        attempts = [item for item in attempts if isinstance(item, dict)]
    generate_attempts = [item for item in attempts if item.get("kind") == "generate"]
    edit_attempts = [item for item in attempts if item.get("kind") == "edit"]
    compose_attempts = [item for item in attempts if item.get("kind") == "compose"]

    comparison = provenance.get("comparison")
    compared = 0
    if isinstance(comparison, dict):
        value = comparison.get("candidates_compared")
        if isinstance(value, int) and not isinstance(value, bool):
            compared = value
        else:
            errors.append("comparison.candidates_compared must be an integer")
        if not str(comparison.get("selection_rationale") or "").strip():
            errors.append("comparison requires a non-empty selection_rationale")
    elif comparison is not None:
        errors.append("generation provenance comparison must be an object")

    if route in {"generated", "hybrid", "composite"}:
        if not generator_available:
            errors.append(f"{route} route requires an available image generator")
        if not generate_attempts:
            errors.append(f"{route} route requires a generated candidate")
        if len(generate_attempts) > 1 and compared < 2:
            errors.append(
                f"{route} route with multiple candidates requires comparison of at least two")
        if len(generate_attempts) == 1 and comparison is not None and compared < 1:
            errors.append("single-candidate provenance requires candidates_compared=1")
        if compared > len(generate_attempts):
            errors.append(
                "comparison.candidates_compared exceeds recorded generated candidates")

    if route == "hybrid":
        if not str(provenance.get("fallback_reason") or "").strip():
            errors.append("hybrid fallback requires a concrete fallback_reason")
        hybrid = provenance.get("hybrid")
        fallback_mode = None
        if not isinstance(hybrid, dict):
            errors.append("hybrid route requires hybrid composition provenance")
        else:
            fallback_mode = hybrid.get("fallback_mode")
            if fallback_mode is None and contract_version in {1, 2}:
                fallback_mode = "typography-repair"
            if fallback_mode not in {
                    "typography-repair", "identity-preserving-composition"}:
                errors.append(
                    "hybrid provenance requires fallback_mode typography-repair "
                    "or identity-preserving-composition")
            if not str(hybrid.get("compositor") or "").strip():
                errors.append("hybrid provenance requires a compositor")
            if not str(hybrid.get("base_asset") or "").strip():
                errors.append("hybrid provenance requires a base_asset")
            if hybrid.get("anisotropic_resize") is not False:
                errors.append("hybrid composition must prove anisotropic_resize=false")
        if fallback_mode == "typography-repair":
            if provenance.get("direct_text_attempted") is not True:
                errors.append("hybrid fallback requires direct_text_attempted=true")
            if not any(item.get("text_mode") == "direct" for item in generate_attempts):
                errors.append("hybrid fallback requires a direct-text generate attempt")
            if len(generate_attempts) < 2 and not edit_attempts:
                errors.append(
                    "hybrid fallback requires a targeted edit or a second generated candidate")
        elif fallback_mode == "identity-preserving-composition":
            cross_view = (
                spec.get("semantic_plan", {}).get("cross_view_identity", [])
                if isinstance(spec.get("semantic_plan"), dict) else [])
            if contract_version != 3 or not cross_view:
                errors.append(
                    "identity-preserving hybrid requires v3 declared cross_view_identity")
            if not any(item.get("text_mode") == "none" for item in generate_attempts):
                errors.append(
                    "identity-preserving hybrid requires a text-free generated canonical asset")
            if len(generate_attempts) < 2 and not edit_attempts:
                errors.append(
                    "identity-preserving hybrid requires evidence that whole-image generation "
                    "or targeted editing failed the identity invariant")
            if isinstance(hybrid, dict):
                if hybrid.get("generated_asset_text_free") is not True:
                    errors.append(
                        "identity-preserving hybrid must prove generated_asset_text_free=true")
                if hybrid.get("identity_geometry_deterministic") is not True:
                    errors.append(
                        "identity-preserving hybrid must prove identity_geometry_deterministic=true")
        if not compose_attempts:
            errors.append("hybrid route requires a compose attempt")

    if route == "composite":
        if not generator_available:
            errors.append("composite route requires an available image generator")
        if not generate_attempts:
            errors.append("composite route requires a generated orientation asset")
        if not compose_attempts:
            errors.append("composite route requires a compose attempt")
        composite = provenance.get("composite")
        if not isinstance(composite, dict):
            errors.append("composite route requires composite provenance")
        else:
            if not str(composite.get("compositor") or "").strip():
                errors.append("composite provenance requires a compositor")
            if composite.get("generated_assets_text_free") is not True:
                errors.append("composite provenance must prove generated assets are text-free")
            if composite.get("quantitative_layer_deterministic") is not True:
                errors.append(
                    "composite provenance must prove the quantitative layer is deterministic")
            if composite.get("intrinsic_aspect_preserved") is not True:
                errors.append(
                    "composite provenance must prove generated asset aspect ratios are preserved")

    if route == "deterministic" and spec.get("archetype") != "quantitative":
        if generator_available:
            if len(generate_attempts) < 2:
                errors.append(
                    "non-quantitative deterministic fallback requires two generated candidates")
            if not edit_attempts:
                errors.append(
                    "non-quantitative deterministic fallback requires a targeted edit")
        if provenance.get("hybrid_considered") is not True:
            errors.append(
                "non-quantitative deterministic fallback requires hybrid_considered=true")
        if not str(provenance.get("fallback_reason") or "").strip():
            errors.append(
                "non-quantitative deterministic fallback requires a concrete fallback_reason")

    if contract_version in {2, 3}:
        archetype = spec.get("archetype")
        if archetype == "quantitative":
            if route not in {"deterministic", "composite"}:
                errors.append(
                    "communication-first quantitative figures require deterministic or composite plotting")
            if route == "deterministic" and not any(
                    item.get("kind") == "render" for item in attempts):
                errors.append(
                    "communication-first deterministic plots require a render attempt")
            if route == "composite" and not compose_attempts:
                errors.append(
                    "communication-first composite plots require a compose attempt")
        elif route == "hybrid":
            fallback_mode = (
                provenance.get("hybrid", {}).get("fallback_mode")
                if isinstance(provenance.get("hybrid"), dict) else None)
            if not (
                contract_version == 3
                and fallback_mode == "identity-preserving-composition"
            ):
                errors.append(
                    "communication-first non-quantitative hybrid is permitted only "
                    "for a v3 identity-preserving composition fallback")
        elif route != "generated":
            errors.append(
                "communication-first non-quantitative figures require image generation")

        reviews = provenance.get("post_generation_reviews")
        if not isinstance(reviews, list) or not reviews:
            errors.append(
                "communication-first contracts require post_generation_reviews for every candidate")
            reviews = []
        elif any(not isinstance(item, dict) for item in reviews):
            errors.append("every post-generation review must be an object")
            reviews = [item for item in reviews if isinstance(item, dict)]

        authored_attempts = [
            item for item in attempts
            if item.get("kind") in {"generate", "edit", "render", "compose"}
            and str(item.get("asset") or "").strip()
        ]
        attempt_assets = [str(item["asset"]) for item in authored_attempts]
        reviewed_assets = [str(item.get("asset") or "") for item in reviews]
        for asset in attempt_assets:
            if asset not in reviewed_assets:
                errors.append(
                    f"candidate lacks a post-generation communication review: {asset}")
        goal = spec.get("communication_goal")
        intended_takeaway = (
            str(goal.get("reader_takeaway") or "").strip()
            if isinstance(goal, dict) else "")
        for review in reviews:
            asset = str(review.get("asset") or "").strip()
            if not asset:
                errors.append("post-generation review requires asset")
                continue
            if asset not in attempt_assets:
                errors.append(
                    f"post-generation review names an unrecorded candidate: {asset}")
            if str(review.get("intended_takeaway") or "").strip() != intended_takeaway:
                errors.append(
                    f"post-generation review for {asset} must restate the declared reader takeaway")
            if not str(review.get("observed_takeaway") or "").strip():
                errors.append(
                    f"post-generation review for {asset} requires observed_takeaway")
            if not str(review.get("observed_explain_back") or "").strip():
                errors.append(
                    f"post-generation review for {asset} requires observed_explain_back")
            intuitive = review.get("intuitive_without_caption") is True
            unexplained_jargon = review.get("unexplained_jargon")
            if not isinstance(unexplained_jargon, list):
                errors.append(
                    f"post-generation review unexplained_jargon must be a list for {asset}")
                unexplained_jargon = []
            meaning_pass = review.get("intended_meaning_conveyed") is True
            flow_pass = review.get("information_flow_clear") is True
            issues = review.get("issues")
            if not isinstance(issues, list):
                errors.append(f"post-generation review issues must be a list for {asset}")
                issues = []
            decision = review.get("decision")
            if meaning_pass and flow_pass and intuitive and not unexplained_jargon:
                if issues:
                    errors.append(
                        f"accepted post-generation review must have no unresolved issues: {asset}")
                if decision != "accept":
                    errors.append(
                        f"passing post-generation review must use decision=accept: {asset}")
            else:
                if not issues:
                    errors.append(
                        f"failed post-generation review must name concrete issues: {asset}")
                if decision not in {"revise", "regenerate"}:
                    errors.append(
                        f"failed post-generation review must decide revise or regenerate: {asset}")
                try:
                    position = attempt_assets.index(asset)
                except ValueError:
                    position = len(attempt_assets)
                if position >= len(attempt_assets) - 1:
                    errors.append(
                        f"failed communication review was not followed by another attempt: {asset}")

        selected_reviews = [
            item for item in reviews if item.get("asset") == selected_asset]
        if len(selected_reviews) != 1:
            errors.append(
                "selected asset requires exactly one post-generation communication review")
        else:
            selected_review = selected_reviews[0]
            if (selected_review.get("intended_meaning_conveyed") is not True
                    or selected_review.get("information_flow_clear") is not True
                    or selected_review.get("intuitive_without_caption") is not True
                    or selected_review.get("unexplained_jargon") != []
                    or selected_review.get("decision") != "accept"):
                errors.append(
                    "selected asset failed the post-generation meaning, information-flow, "
                    "or intuition gate")
    return errors
