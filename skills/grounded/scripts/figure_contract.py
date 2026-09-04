#!/usr/bin/env python3
"""Shared, topic-neutral validation for Grounded figure specifications.

This module contains no prompt assembly, raster inspection, or filesystem writes.
Both authoring and QA import the same semantic contract from here.
"""

from __future__ import annotations

import re


REQUIRED_FIELDS = ("purpose", "title", "story", "exact_text")
RENDER_CONTEXTS = ("article", "standalone", "slide")
REVIEW_STYLES = ("scientific", "popsci", "bullets", "eli5")
RENDER_ROUTES = ("generated", "hybrid", "deterministic", "composite")
CONCEPT_SCORE_DIMENSIONS = (
    "clarity", "simplicity", "completeness", "elegance", "intuitiveness")
V2_GENERATED_MAX_STRINGS = 8
V2_GENERATED_MAX_WORDS = 32
V2_GENERATED_MAX_WORDS_PER_STRING = 8
CLEAN_SANS_FAMILIES = {
    "Arial", "Helvetica", "Helvetica Neue", "Inter", "Seravek",
}
CONNECTOR_MEANINGS = {
    "causal", "temporal", "transfer", "comparison", "association", "navigation",
}
CALLOUT_BACKGROUNDS = {"opaque-white", "quiet-canvas"}
CONTENT_DENSITIES = {"sparse", "moderate", "dense"}
REPRESENTATION_KINDS = {"literal", "metaphor-assisted"}
CUTAWAY_MAX_INTERIOR_ENTITIES = 6
ABSOLUTE_WHITE = "#FFFFFF"
MOBILE_PREVIEW_WIDTH_PX = 390
MINIMUM_MOBILE_PRIMARY_LABEL_HEIGHT_PX = 10.0
MAXIMUM_MOBILE_PRIMARY_LABELS = 3
GENERATED_MOBILE_PRIMARY_MAX_WORDS = 4
GENERATED_MOBILE_PRIMARY_MAX_CHARACTERS = 28
GENERATED_MOBILE_PRIMARY_COMPOUND_PUNCTUATION = ":;()/"
GLOSSARY_DEFINITION = re.compile(r"^[A-Z][A-Z0-9-]{1,9}\s*=\s*\S")
PLACEHOLDER_PREFIX = "<<FILL"


def find_placeholders(value, path=""):
    """Return JSON paths of scaffold placeholders (`<<FILL ...>>`) in a spec."""
    found = []
    if isinstance(value, str):
        if value.strip().startswith(PLACEHOLDER_PREFIX):
            found.append(path or "$")
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(find_placeholders(item, "%s.%s" % (path, key) if path else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_placeholders(item, "%s[%d]" % (path, index)))
    return found


def validate_no_placeholders(spec):
    """Reject a spec that still carries scaffold placeholders."""
    placeholders = find_placeholders(spec)
    if placeholders:
        raise ValueError(
            "spec still contains scaffold placeholders: "
            + ", ".join(placeholders[:8]))


def inferred_render_route(spec, archetype_name):
    explicit = spec.get("render_route")
    if explicit:
        return explicit
    if archetype_name == "quantitative":
        return "deterministic"
    return "generated"


def require_string(spec, field):
    value = spec.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % field)
    return value.strip()


def require_string_list(spec, field):
    value = spec.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError("%s must be a non-empty list" % field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def optional_string_list(spec, field):
    value = spec.get(field, [])
    if not isinstance(value, list):
        raise ValueError("%s must be a list" % field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def _required_object(value, field):
    if not isinstance(value, dict):
        raise ValueError("%s must be an object" % field)
    return value


def _required_nested_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % field)
    return value.strip()


def _required_nested_string_list(value, field):
    if not isinstance(value, list) or not value:
        raise ValueError("%s must be a non-empty list" % field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def _nested_string_list(value, field, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise ValueError("%s must be a %slist" % (field, qualifier))
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def validate_communication_goal(spec):
    goal = _required_object(spec.get("communication_goal"), "communication_goal")
    normalized = {
        "reader_takeaway": _required_nested_string(
            goal.get("reader_takeaway"), "communication_goal.reader_takeaway"),
        "must_show": _required_nested_string_list(
            goal.get("must_show"), "communication_goal.must_show"),
        "information_flow": _required_nested_string_list(
            goal.get("information_flow"), "communication_goal.information_flow"),
        "evidence_boundary": _required_nested_string(
            goal.get("evidence_boundary"), "communication_goal.evidence_boundary"),
        "familiar_starting_point": _required_nested_string(
            goal.get("familiar_starting_point"),
            "communication_goal.familiar_starting_point"),
        "plain_language_explain_back": _required_nested_string(
            goal.get("plain_language_explain_back"),
            "communication_goal.plain_language_explain_back"),
    }
    if spec.get("quality_contract_version") == 3:
        normalized.update({
            "visual_question": _required_nested_string(
                goal.get("visual_question"),
                "communication_goal.visual_question"),
            "panel_thesis": _required_nested_string(
                goal.get("panel_thesis"),
                "communication_goal.panel_thesis"),
        })
    return normalized


def validate_v3_rendered_copy(spec, rendered_text):
    """Reject poster-like or caption-like copy before pixels are produced."""
    if spec.get("quality_contract_version") != 3:
        return
    for text in rendered_text:
        if GLOSSARY_DEFINITION.match(text):
            raise ValueError(
                "quality contract v3 keeps abbreviation definitions in the caption, "
                "not as glossary copy inside the artwork")
        alphabetic_words = re.findall(r"[A-Za-z]+", text)
        long_words = [word for word in alphabetic_words if len(word) > 1]
        if len(long_words) >= 2 and all(word.isupper() for word in long_words):
            raise ValueError(
                "quality contract v3 uses sentence case for multiword labels; "
                "all-caps display copy is poster-like")


def validate_layout_plan(spec):
    """Validate the topic-neutral canvas-fit and optical-balance plan."""
    plan = _required_object(spec.get("layout_plan"), "layout_plan")
    density = _required_nested_string(
        plan.get("content_density"), "layout_plan.content_density")
    if density not in CONTENT_DENSITIES:
        raise ValueError(
            "layout_plan.content_density must be one of: %s"
            % ", ".join(sorted(CONTENT_DENSITIES)))
    wide_required = plan.get("wide_canvas_required")
    if not isinstance(wide_required, bool):
        raise ValueError("layout_plan.wide_canvas_required must be boolean")
    raw_target_ratio = spec.get("target_aspect_ratio")
    if isinstance(raw_target_ratio, bool):
        raise ValueError("target_aspect_ratio must be numeric")
    try:
        target_ratio = float(raw_target_ratio)
    except (TypeError, ValueError) as exc:
        raise ValueError("target_aspect_ratio must be numeric") from exc
    if density == "sparse" and target_ratio > 1.75 and not wide_required:
        raise ValueError(
            "a sparse figure wider than 1.75:1 must prove horizontal topology "
            "with layout_plan.wide_canvas_required=true")
    mobile = _required_object(
        plan.get("mobile_preview"), "layout_plan.mobile_preview")
    preview_width = mobile.get("width_px")
    if preview_width != MOBILE_PREVIEW_WIDTH_PX:
        raise ValueError(
            "layout_plan.mobile_preview.width_px must be %d"
            % MOBILE_PREVIEW_WIDTH_PX)
    raw_minimum = mobile.get("minimum_primary_label_height_px")
    if isinstance(raw_minimum, bool):
        raise ValueError(
            "layout_plan.mobile_preview.minimum_primary_label_height_px must be numeric")
    try:
        mobile_minimum = float(raw_minimum)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "layout_plan.mobile_preview.minimum_primary_label_height_px must be numeric") from exc
    if mobile_minimum < MINIMUM_MOBILE_PRIMARY_LABEL_HEIGHT_PX:
        raise ValueError(
            "layout_plan.mobile_preview.minimum_primary_label_height_px must be at least %.1f"
            % MINIMUM_MOBILE_PRIMARY_LABEL_HEIGHT_PX)
    if mobile.get("all_labels_required_without_zoom") is not False:
        raise ValueError(
            "layout_plan.mobile_preview.all_labels_required_without_zoom must be false; "
            "only primary wayfinding labels drive the phone gate")
    primary_labels = _nested_string_list(
        mobile.get("primary_labels"),
        "layout_plan.mobile_preview.primary_labels", nonempty=True)
    if len(primary_labels) > MAXIMUM_MOBILE_PRIMARY_LABELS:
        raise ValueError(
            "layout_plan.mobile_preview.primary_labels may contain at most three labels")
    if spec.get("render_route") == "generated":
        for label in primary_labels:
            if (
                len(label.split()) > GENERATED_MOBILE_PRIMARY_MAX_WORDS
                or len(label) > GENERATED_MOBILE_PRIMARY_MAX_CHARACTERS
            ):
                raise ValueError(
                    "generated mobile primary labels must use at most four words "
                    "and 28 characters; shorten the label and move detail to the caption")
            if any(mark in label for mark in
                   GENERATED_MOBILE_PRIMARY_COMPOUND_PUNCTUATION):
                raise ValueError(
                    "generated mobile primary labels must express one idea without "
                    "colon, semicolon, parentheses, or slash; move qualification to "
                    "the caption")
    first_glance_path = _nested_string_list(
        mobile.get("first_glance_path"),
        "layout_plan.mobile_preview.first_glance_path", nonempty=True)
    if len(first_glance_path) > 5:
        raise ValueError(
            "layout_plan.mobile_preview.first_glance_path may contain at most five steps")
    return {
        "content_density": density,
        "wide_canvas_required": wide_required,
        "aspect_ratio_rationale": _required_nested_string(
            plan.get("aspect_ratio_rationale"),
            "layout_plan.aspect_ratio_rationale"),
        "balance_strategy": _required_nested_string(
            plan.get("balance_strategy"), "layout_plan.balance_strategy"),
        "final_display": _required_nested_string(
            plan.get("final_display"), "layout_plan.final_display"),
        "mobile_preview": {
            "width_px": preview_width,
            "minimum_primary_label_height_px": mobile_minimum,
            "all_labels_required_without_zoom": False,
            "primary_labels": primary_labels,
            "first_glance_path": first_glance_path,
            "supporting_detail_strategy": _required_nested_string(
                mobile.get("supporting_detail_strategy"),
                "layout_plan.mobile_preview.supporting_detail_strategy"),
            "explain_back_without_zoom": _required_nested_string(
                mobile.get("explain_back_without_zoom"),
                "layout_plan.mobile_preview.explain_back_without_zoom"),
        },
    }


def validate_composite_plan(spec):
    """Validate generated orientation assets inside a quantitative composition."""
    plan = _required_object(spec.get("composite_plan"), "composite_plan")
    assets = plan.get("generated_assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("composite_plan.generated_assets must be a non-empty list")
    normalized_assets = []
    asset_ids = set()
    for index, asset in enumerate(assets):
        field = "composite_plan.generated_assets[%d]" % index
        asset = _required_object(asset, field)
        asset_id = _required_nested_string(asset.get("id"), field + ".id")
        if asset_id in asset_ids:
            raise ValueError("composite generated asset ids must be unique")
        asset_ids.add(asset_id)
        if asset.get("text_free") is not True:
            raise ValueError("composite generated assets must set text_free=true")
        if asset.get("encodes_magnitude") is not False:
            raise ValueError(
                "composite generated assets must set encodes_magnitude=false")
        normalized_assets.append({
            "id": asset_id,
            "purpose": _required_nested_string(
                asset.get("purpose"), field + ".purpose"),
            "placement": _required_nested_string(
                asset.get("placement"), field + ".placement"),
            "text_free": True,
            "encodes_magnitude": False,
        })
    if plan.get("intrinsic_aspect_preserved") is not True:
        raise ValueError(
            "composite_plan must set intrinsic_aspect_preserved=true")
    return {
        "generated_assets": normalized_assets,
        "deterministic_evidence_layer": _required_nested_string(
            plan.get("deterministic_evidence_layer"),
            "composite_plan.deterministic_evidence_layer"),
        "integration_strategy": _required_nested_string(
            plan.get("integration_strategy"),
            "composite_plan.integration_strategy"),
        "balance_rationale": _required_nested_string(
            plan.get("balance_rationale"),
            "composite_plan.balance_rationale"),
        "intrinsic_aspect_preserved": True,
    }


def validate_semantic_plan(spec, annotation_plan):
    """Validate the v3 topic-neutral meaning and integrity plan."""
    plan = _required_object(spec.get("semantic_plan"), "semantic_plan")
    entities = plan.get("entities")
    if not isinstance(entities, list) or not entities:
        raise ValueError("semantic_plan.entities must be a non-empty list")
    normalized_entities = []
    entity_ids = []
    for index, entity in enumerate(entities):
        entity = _required_object(entity, "semantic_plan.entities[%d]" % index)
        entity_id = _required_nested_string(
            entity.get("id"), "semantic_plan.entities[%d].id" % index)
        if entity_id in entity_ids:
            raise ValueError("semantic_plan entity ids must be unique")
        entity_ids.append(entity_id)
        normalized_entities.append({
            "id": entity_id,
            "depiction": _required_nested_string(
                entity.get("depiction"),
                "semantic_plan.entities[%d].depiction" % index),
            "role": _required_nested_string(
                entity.get("role"),
                "semantic_plan.entities[%d].role" % index),
            "evidence_basis": _required_nested_string(
                entity.get("evidence_basis"),
                "semantic_plan.entities[%d].evidence_basis" % index),
        })

    connectors = plan.get("connectors")
    if not isinstance(connectors, list):
        raise ValueError("semantic_plan.connectors must be a list")
    normalized_connectors = []
    for index, connector in enumerate(connectors):
        connector = _required_object(
            connector, "semantic_plan.connectors[%d]" % index)
        source = _required_nested_string(
            connector.get("from"), "semantic_plan.connectors[%d].from" % index)
        target = _required_nested_string(
            connector.get("to"), "semantic_plan.connectors[%d].to" % index)
        if source not in entity_ids or target not in entity_ids:
            raise ValueError(
                "semantic_plan connector endpoints must identify declared entities")
        meaning = _required_nested_string(
            connector.get("meaning"),
            "semantic_plan.connectors[%d].meaning" % index)
        if meaning not in CONNECTOR_MEANINGS:
            raise ValueError(
                "semantic_plan connector meaning must be one of: %s"
                % ", ".join(sorted(CONNECTOR_MEANINGS)))
        normalized_connectors.append({
            "from": source,
            "to": target,
            "meaning": meaning,
            "label": _required_nested_string(
                connector.get("label"),
                "semantic_plan.connectors[%d].label" % index),
        })

    panel_jobs = plan.get("panel_jobs")
    if not isinstance(panel_jobs, list):
        raise ValueError("semantic_plan.panel_jobs must be a list")
    normalized_panel_jobs = []
    for index, job in enumerate(panel_jobs):
        job = _required_object(job, "semantic_plan.panel_jobs[%d]" % index)
        label = _required_nested_string(
            job.get("label"), "semantic_plan.panel_jobs[%d].label" % index)
        if job.get("adds_distinct_information") is not True:
            raise ValueError(
                "every semantic_plan panel job must add distinct information")
        normalized_panel_jobs.append({
            "label": label,
            "job": _required_nested_string(
                job.get("job"), "semantic_plan.panel_jobs[%d].job" % index),
            "adds_distinct_information": True,
        })
    if [item["label"] for item in normalized_panel_jobs] != annotation_plan["panel_labels"]:
        raise ValueError(
            "semantic_plan.panel_jobs labels must exactly match annotation_plan.panel_labels")

    anatomy_subjects = plan.get("anatomy_subjects")
    salience_targets = plan.get("salience_targets")
    if not isinstance(anatomy_subjects, list) or any(
        not isinstance(item, str) or not item.strip() for item in anatomy_subjects
    ):
        raise ValueError("semantic_plan.anatomy_subjects must be a string list")
    if not isinstance(salience_targets, list) or any(
        not isinstance(item, str) or item not in entity_ids for item in salience_targets
    ):
        raise ValueError(
            "semantic_plan.salience_targets must identify declared entity ids")

    priority = _required_object(
        plan.get("information_priority"), "semantic_plan.information_priority")
    primary_entities = _nested_string_list(
        priority.get("primary_entities"),
        "semantic_plan.information_priority.primary_entities", nonempty=True)
    supporting_entities = _nested_string_list(
        priority.get("supporting_entities"),
        "semantic_plan.information_priority.supporting_entities")
    if len(set(primary_entities + supporting_entities)) != len(
            primary_entities + supporting_entities):
        raise ValueError(
            "semantic_plan information-priority entity ids must be unique")
    if set(primary_entities + supporting_entities) != set(entity_ids):
        raise ValueError(
            "semantic_plan information priority must classify every entity exactly once")
    normalized_priority = {
        "primary_entities": primary_entities,
        "supporting_entities": supporting_entities,
        "excluded_nonessential": _nested_string_list(
            priority.get("excluded_nonessential"),
            "semantic_plan.information_priority.excluded_nonessential"),
        "dominance_rationale": _required_nested_string(
            priority.get("dominance_rationale"),
            "semantic_plan.information_priority.dominance_rationale"),
        "deletion_test": _required_nested_string(
            priority.get("deletion_test"),
            "semantic_plan.information_priority.deletion_test"),
    }

    uncertainties = plan.get("uncertainty_encodings")
    if not isinstance(uncertainties, list):
        raise ValueError("semantic_plan.uncertainty_encodings must be a list")
    normalized_uncertainties = []
    for index, item in enumerate(uncertainties):
        field = "semantic_plan.uncertainty_encodings[%d]" % index
        item = _required_object(item, field)
        target = _required_nested_string(item.get("target"), field + ".target")
        if target not in entity_ids:
            raise ValueError(
                "semantic_plan uncertainty targets must identify declared entities")
        normalized_uncertainties.append({
            "target": target,
            "source_of_uncertainty": _required_nested_string(
                item.get("source_of_uncertainty"), field + ".source_of_uncertainty"),
            "visual_encoding": _required_nested_string(
                item.get("visual_encoding"), field + ".visual_encoding"),
            "reader_interpretation": _required_nested_string(
                item.get("reader_interpretation"), field + ".reader_interpretation"),
        })

    cross_view = plan.get("cross_view_identity")
    if not isinstance(cross_view, list):
        raise ValueError("semantic_plan.cross_view_identity must be a list")
    normalized_cross_view = []
    for index, item in enumerate(cross_view):
        field = "semantic_plan.cross_view_identity[%d]" % index
        item = _required_object(item, field)
        entity = _required_nested_string(item.get("entity"), field + ".entity")
        if entity not in entity_ids:
            raise ValueError(
                "semantic_plan cross-view identity must identify a declared entity")
        normalized_cross_view.append({
            "entity": entity,
            "views": _nested_string_list(
                item.get("views"), field + ".views", nonempty=True),
            "invariant_features": _nested_string_list(
                item.get("invariant_features"), field + ".invariant_features",
                nonempty=True),
            "reason": _required_nested_string(item.get("reason"), field + ".reason"),
        })

    anatomical_context = plan.get("anatomical_context")
    if not isinstance(anatomical_context, list):
        raise ValueError("semantic_plan.anatomical_context must be a list")
    normalized_anatomical_context = []
    seen_subjects = set()
    for index, item in enumerate(anatomical_context):
        field = "semantic_plan.anatomical_context[%d]" % index
        item = _required_object(item, field)
        subject = _required_nested_string(item.get("subject"), field + ".subject")
        if subject not in anatomy_subjects or subject in seen_subjects:
            raise ValueError(
                "semantic_plan anatomical context must identify each anatomy subject once")
        seen_subjects.add(subject)
        normalized_anatomical_context.append({
            "subject": subject,
            "orientation_landmarks": _nested_string_list(
                item.get("orientation_landmarks"), field + ".orientation_landmarks",
                nonempty=True),
            "focal_region": _required_nested_string(
                item.get("focal_region"), field + ".focal_region"),
            "context_rationale": _required_nested_string(
                item.get("context_rationale"), field + ".context_rationale"),
        })
    if seen_subjects != set(anatomy_subjects):
        raise ValueError(
            "semantic_plan anatomical context must cover every anatomy subject")

    quantitative = _required_object(
        plan.get("quantitative_decision"), "semantic_plan.quantitative_decision")
    numbers_available = quantitative.get("verified_numbers_available")
    numbers_primary = quantitative.get("numbers_carry_primary_message")
    if not isinstance(numbers_available, bool) or not isinstance(numbers_primary, bool):
        raise ValueError(
            "semantic_plan.quantitative_decision requires two boolean availability fields")
    if numbers_primary and not numbers_available:
        raise ValueError("primary quantitative content requires verified numbers")
    if numbers_primary and spec.get("render_route") not in {
            "deterministic", "composite"}:
        raise ValueError(
            "verified numbers carrying the primary message require deterministic or composite rendering")
    if spec.get("render_route") in {"deterministic", "composite"} and not numbers_primary:
        raise ValueError(
            "deterministic and composite rendering require numbers_carry_primary_message=true")
    normalized_quantitative = {
        "verified_numbers_available": numbers_available,
        "numbers_carry_primary_message": numbers_primary,
        "reason": _required_nested_string(
            quantitative.get("reason"),
            "semantic_plan.quantitative_decision.reason"),
    }

    representation = _required_object(
        plan.get("representation_plan"), "semantic_plan.representation_plan")
    representation_kind = _required_nested_string(
        representation.get("kind"), "semantic_plan.representation_plan.kind")
    if representation_kind not in REPRESENTATION_KINDS:
        raise ValueError(
            "semantic_plan.representation_plan.kind must be one of: %s"
            % ", ".join(sorted(REPRESENTATION_KINDS)))
    translation_steps = representation.get("cognitive_translation_steps")
    if not isinstance(translation_steps, int) or isinstance(translation_steps, bool):
        raise ValueError(
            "semantic_plan.representation_plan.cognitive_translation_steps must be an integer")
    if not 0 <= translation_steps <= 1:
        raise ValueError(
            "semantic_plan.representation_plan permits at most one cognitive translation step")
    literal_rejected_reason = representation.get("literal_rejected_reason")
    if representation_kind == "literal":
        if translation_steps != 0:
            raise ValueError(
                "literal representation must use zero cognitive translation steps")
        if literal_rejected_reason not in (None, ""):
            raise ValueError(
                "literal_rejected_reason is only valid for metaphor-assisted representation")
        literal_rejected_reason = None
    else:
        literal_rejected_reason = _required_nested_string(
            literal_rejected_reason,
            "semantic_plan.representation_plan.literal_rejected_reason")
    arranged_elements = representation.get("arranged_elements")
    if not isinstance(arranged_elements, bool):
        raise ValueError(
            "semantic_plan.representation_plan.arranged_elements must be boolean")
    arrangement_evidence_job = representation.get("arrangement_evidence_job")
    if arranged_elements:
        arrangement_evidence_job = _required_nested_string(
            arrangement_evidence_job,
            "semantic_plan.representation_plan.arrangement_evidence_job")
    elif arrangement_evidence_job not in (None, ""):
        raise ValueError(
            "arrangement_evidence_job is only valid when arranged_elements=true")
    else:
        arrangement_evidence_job = None
    normalized_representation = {
        "kind": representation_kind,
        "evidence_native_anchor": _required_nested_string(
            representation.get("evidence_native_anchor"),
            "semantic_plan.representation_plan.evidence_native_anchor"),
        "cognitive_translation_steps": translation_steps,
        "literal_rejected_reason": literal_rejected_reason,
        "added_explanatory_value": _required_nested_string(
            representation.get("added_explanatory_value"),
            "semantic_plan.representation_plan.added_explanatory_value"),
        "arranged_elements": arranged_elements,
        "arrangement_evidence_job": arrangement_evidence_job,
    }

    cutaway_plan = None
    if spec.get("archetype") == "cutaway":
        if spec.get("render_route") != "generated":
            raise ValueError("cutaway figures require the generated route")
        cutaway = _required_object(
            plan.get("cutaway_plan"), "semantic_plan.cutaway_plan")
        suitability = _required_object(
            cutaway.get("suitability"),
            "semantic_plan.cutaway_plan.suitability")
        suitability_fields = (
            "hidden_interior_removes_mental_step",
            "faithful_interior_supported",
            "distinct_evidence_job",
            "phone_readable",
        )
        for field in suitability_fields:
            if suitability.get(field) is not True:
                raise ValueError(
                    "cutaway suitability requires %s=true" % field)

        interior_entities = _nested_string_list(
            cutaway.get("interior_entities"),
            "semantic_plan.cutaway_plan.interior_entities", nonempty=True)
        if len(interior_entities) > CUTAWAY_MAX_INTERIOR_ENTITIES:
            raise ValueError(
                "cutaway figures may expose at most %d essential interior entities"
                % CUTAWAY_MAX_INTERIOR_ENTITIES)
        if len(set(interior_entities)) != len(interior_entities):
            raise ValueError("cutaway interior entity ids must be unique")
        if any(entity_id not in entity_ids for entity_id in interior_entities):
            raise ValueError(
                "cutaway interior_entities must identify declared semantic entities")

        callouts_by_target = {}
        for index, callout in enumerate(annotation_plan["callouts"]):
            target = callout["target"]
            if target in callouts_by_target:
                raise ValueError(
                    "cutaway callouts must identify each interior entity exactly once")
            callouts_by_target[target] = callout
            if not callout.get("explanatory_role"):
                raise ValueError(
                    "cutaway callouts require a non-empty explanatory_role")
            words = callout["text"].split()
            if (len(words) > GENERATED_MOBILE_PRIMARY_MAX_WORDS
                    or len(callout["text"]) > GENERATED_MOBILE_PRIMARY_MAX_CHARACTERS):
                raise ValueError(
                    "cutaway callouts must be phone-first labels of at most %d words "
                    "and %d characters"
                    % (GENERATED_MOBILE_PRIMARY_MAX_WORDS,
                       GENERATED_MOBILE_PRIMARY_MAX_CHARACTERS))
        if set(callouts_by_target) != set(interior_entities):
            raise ValueError(
                "cutaway callouts must cover every interior entity exactly once")

        cutaway_plan = {
            "exterior_silhouette": _required_nested_string(
                cutaway.get("exterior_silhouette"),
                "semantic_plan.cutaway_plan.exterior_silhouette"),
            "cut_plane": _required_nested_string(
                cutaway.get("cut_plane"),
                "semantic_plan.cutaway_plan.cut_plane"),
            "interior_entities": interior_entities,
            "spatial_relationships": _nested_string_list(
                cutaway.get("spatial_relationships"),
                "semantic_plan.cutaway_plan.spatial_relationships", nonempty=True),
            "annotation_strategy": _required_nested_string(
                cutaway.get("annotation_strategy"),
                "semantic_plan.cutaway_plan.annotation_strategy"),
            "suitability": {
                **{field: True for field in suitability_fields},
                "reason": _required_nested_string(
                    suitability.get("reason"),
                    "semantic_plan.cutaway_plan.suitability.reason"),
            },
        }
    elif plan.get("cutaway_plan") not in (None, {}):
        raise ValueError(
            "semantic_plan.cutaway_plan is only valid for the cutaway archetype")

    if spec.get("render_route") in {"deterministic", "composite"}:
        plot_design = _required_object(spec.get("plot_design"), "plot_design")
        typography = _required_object(
            plot_design.get("typography"), "plot_design.typography")
        family = _required_nested_string(
            typography.get("family"), "plot_design.typography.family")
        fallback = _required_nested_string(
            typography.get("fallback"), "plot_design.typography.fallback")
        if family not in CLEAN_SANS_FAMILIES or fallback not in CLEAN_SANS_FAMILIES:
            raise ValueError(
                "quality contract v3 quantitative figures require clean sans-serif typography")
        if typography.get("upright_natural_width") is not True:
            raise ValueError(
                "plot_design.typography must confirm upright_natural_width=true")

    return {
        "entities": normalized_entities,
        "connectors": normalized_connectors,
        "panel_jobs": normalized_panel_jobs,
        "grouping_rationale": _required_nested_string(
            plan.get("grouping_rationale"), "semantic_plan.grouping_rationale"),
        "anatomy_subjects": [item.strip() for item in anatomy_subjects],
        "anatomical_context": normalized_anatomical_context,
        "salience_targets": salience_targets,
        "information_priority": normalized_priority,
        "uncertainty_encodings": normalized_uncertainties,
        "cross_view_identity": normalized_cross_view,
        "quantitative_decision": normalized_quantitative,
        "representation_plan": normalized_representation,
        "cutaway_plan": cutaway_plan,
    }


def validate_concept_plan(spec):
    concepts = spec.get("concepts")
    if not isinstance(concepts, list) or len(concepts) != 3:
        raise ValueError("communication-first generated figures require exactly three concepts")
    normalized = []
    ids = []
    for index, concept in enumerate(concepts, 1):
        concept = _required_object(concept, "concepts[%d]" % (index - 1))
        concept_id = _required_nested_string(
            concept.get("id"), "concepts[%d].id" % (index - 1))
        if concept_id in ids:
            raise ValueError("concept ids must be unique")
        ids.append(concept_id)
        normalized.append({
            "id": concept_id,
            "description": _required_nested_string(
                concept.get("description"),
                "concepts[%d].description" % (index - 1)),
            "information_flow": _required_nested_string_list(
                concept.get("information_flow"),
                "concepts[%d].information_flow" % (index - 1)),
            "strengths": _required_nested_string_list(
                concept.get("strengths"),
                "concepts[%d].strengths" % (index - 1)),
            "risks": _required_nested_string_list(
                concept.get("risks"),
                "concepts[%d].risks" % (index - 1)),
        })
    descriptions = [item["description"].casefold() for item in normalized]
    flows = [tuple(step.casefold() for step in item["information_flow"])
             for item in normalized]
    if len(set(descriptions)) != 3 or len(set(flows)) != 3:
        raise ValueError(
            "the three concepts must have genuinely different descriptions and information flows")

    selection = _required_object(spec.get("concept_selection"), "concept_selection")
    selected_id = _required_nested_string(
        selection.get("selected_id"), "concept_selection.selected_id")
    if selected_id not in ids:
        raise ValueError("concept_selection.selected_id must identify one of the three concepts")
    rationale = _required_nested_string(
        selection.get("selection_rationale"),
        "concept_selection.selection_rationale")
    evaluations = selection.get("evaluations")
    if not isinstance(evaluations, list) or len(evaluations) != 3:
        raise ValueError("concept_selection.evaluations must score all three concepts")
    scores = {}
    normalized_evaluations = []
    for index, evaluation in enumerate(evaluations):
        evaluation = _required_object(
            evaluation, "concept_selection.evaluations[%d]" % index)
        concept_id = _required_nested_string(
            evaluation.get("id"),
            "concept_selection.evaluations[%d].id" % index)
        if concept_id not in ids or concept_id in scores:
            raise ValueError("concept evaluations must identify each concept exactly once")
        dimension_scores = {}
        for dimension in CONCEPT_SCORE_DIMENSIONS:
            value = evaluation.get(dimension)
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
                raise ValueError(
                    "concept evaluation %s must be an integer from 1 to 5" % dimension)
            dimension_scores[dimension] = value
        assessment = _required_nested_string(
            evaluation.get("assessment"),
            "concept_selection.evaluations[%d].assessment" % index)
        scores[concept_id] = sum(dimension_scores.values())
        normalized_evaluations.append({
            "id": concept_id,
            **dimension_scores,
            "assessment": assessment,
        })
    if scores[selected_id] != max(scores.values()):
        raise ValueError(
            "selected concept must have the highest combined clarity, simplicity, "
            "completeness, elegance, and intuitiveness score")
    selected_scores = next(
        item for item in normalized_evaluations if item["id"] == selected_id)
    if any(selected_scores[dimension] < 4 for dimension in CONCEPT_SCORE_DIMENSIONS):
        raise ValueError("selected concept must score at least 4 in every selection dimension")
    selected = next(item for item in normalized if item["id"] == selected_id)
    return selected, normalized_evaluations, rationale


def validate_plot_design(spec):
    design = _required_object(spec.get("plot_design"), "plot_design")
    normalized = {
        "chart_type": _required_nested_string(
            design.get("chart_type"), "plot_design.chart_type"),
        "encoding": _required_nested_string(
            design.get("encoding"), "plot_design.encoding"),
        "reader_path": _required_nested_string_list(
            design.get("reader_path"), "plot_design.reader_path"),
        "style_rationale": _required_nested_string(
            design.get("style_rationale"), "plot_design.style_rationale"),
    }
    if spec.get("quality_contract_version") == 3:
        data = _required_object(spec.get("data"), "data")
        panels = data.get("panels")
        if not isinstance(panels, list) or not panels:
            raise ValueError(
                "quality contract v3 quantitative figures require data.panels")
        semantics = design.get("axis_semantics")
        if not isinstance(semantics, list) or len(semantics) != len(panels):
            raise ValueError(
                "plot_design.axis_semantics must describe every quantitative panel")
        normalized_semantics = []
        panel_ids = []
        for index, (item, panel) in enumerate(zip(semantics, panels)):
            field = "plot_design.axis_semantics[%d]" % index
            item = _required_object(item, field)
            panel = _required_object(panel, "data.panels[%d]" % index)
            panel_id = _required_nested_string(item.get("panel_id"), field + ".panel_id")
            if panel_id != panel.get("id") or panel_id in panel_ids:
                raise ValueError(
                    "plot_design.axis_semantics panel ids must match data.panels in order")
            panel_ids.append(panel_id)
            x_axis = _required_object(panel.get("x_axis"), "data panel x_axis")
            y_axis = _required_object(panel.get("y_axis"), "data panel y_axis")
            x_label = _required_nested_string(item.get("x_label"), field + ".x_label")
            y_label = _required_nested_string(item.get("y_label"), field + ".y_label")
            if x_label != x_axis.get("label") or y_label != y_axis.get("label"):
                raise ValueError(
                    "plot_design axis labels must exactly match the rendered data axes")
            normalized_semantics.append({
                "panel_id": panel_id,
                "x_label": x_label,
                "x_meaning": _required_nested_string(
                    item.get("x_meaning"), field + ".x_meaning"),
                "y_label": y_label,
                "y_meaning": _required_nested_string(
                    item.get("y_meaning"), field + ".y_meaning"),
            })
        uncertainty = _required_object(
            design.get("uncertainty_display"), "plot_design.uncertainty_display")
        present = uncertainty.get("present")
        if not isinstance(present, bool):
            raise ValueError("plot_design.uncertainty_display.present must be boolean")
        data_has_uncertainty = any(
            point.get("y_interval") is not None
            for panel in panels
            for series in panel.get("series", [])
            for point in series.get("points", [])
        ) or any(panel.get("contrasts") for panel in panels)
        if data_has_uncertainty and not present:
            raise ValueError(
                "reported intervals require plot_design.uncertainty_display.present=true")
        axis_placement = _required_object(
            design.get("axis_label_placement"),
            "plot_design.axis_label_placement")
        required_axis_placement = {
            "x_orientation": "horizontal",
            "x_location": "below-data-region",
            "y_orientation": "vertical",
            "y_location": "outside-data-region",
        }
        for field, expected in required_axis_placement.items():
            if axis_placement.get(field) != expected:
                raise ValueError(
                    "plot_design.axis_label_placement.%s must be %r"
                    % (field, expected))
        legend_plan = _required_object(
            design.get("legend_plan"), "plot_design.legend_plan")
        legend_needed = legend_plan.get("needed")
        if not isinstance(legend_needed, bool):
            raise ValueError("plot_design.legend_plan.needed must be boolean")
        legend_placement = _required_nested_string(
            legend_plan.get("placement"), "plot_design.legend_plan.placement")
        if legend_needed:
            if legend_placement != "adjacent-to-marks":
                raise ValueError(
                    "a needed plot legend must use placement='adjacent-to-marks'")
        elif legend_placement != "none":
            raise ValueError("an omitted plot legend must use placement='none'")
        interval_keys_present = any(panel.get("interval_key") for panel in panels)
        if interval_keys_present and not legend_needed:
            raise ValueError(
                "conventional interval keys must be omitted when legend_plan.needed=false")
        normalized.update({
            "axis_semantics": normalized_semantics,
            "caption_axis_summary": _required_nested_string(
                design.get("caption_axis_summary"),
                "plot_design.caption_axis_summary"),
            "numeric_annotation_attachment": _required_nested_string(
                design.get("numeric_annotation_attachment"),
                "plot_design.numeric_annotation_attachment"),
            "uncertainty_display": {
                "present": present,
                "encoding": _required_nested_string(
                    uncertainty.get("encoding"),
                    "plot_design.uncertainty_display.encoding"),
                "attachment": _required_nested_string(
                    uncertainty.get("attachment"),
                    "plot_design.uncertainty_display.attachment"),
            },
            "axis_label_placement": required_axis_placement,
            "legend_plan": {
                "needed": legend_needed,
                "reason": _required_nested_string(
                    legend_plan.get("reason"),
                    "plot_design.legend_plan.reason"),
                "placement": legend_placement,
            },
        })
    return normalized


def validate_annotation_plan(spec, rendered_text):
    plan = _required_object(spec.get("annotation_plan"), "annotation_plan")
    panel_labels = plan.get("panel_labels")
    if not isinstance(panel_labels, list) or any(
        not isinstance(item, str) for item in panel_labels
    ):
        raise ValueError("annotation_plan.panel_labels must be a list of strings")
    expected_labels = list("ABCD"[:len(panel_labels)])
    if panel_labels != expected_labels:
        raise ValueError(
            "annotation_plan.panel_labels must be the sequential uppercase prefix A, B, C, D")
    callouts = plan.get("callouts")
    if not isinstance(callouts, list):
        raise ValueError("annotation_plan.callouts must be a list")
    normalized_callouts = []
    for index, callout in enumerate(callouts):
        callout = _required_object(
            callout, "annotation_plan.callouts[%d]" % index)
        text = _required_nested_string(
            callout.get("text"), "annotation_plan.callouts[%d].text" % index)
        target = _required_nested_string(
            callout.get("target"), "annotation_plan.callouts[%d].target" % index)
        leader_line = callout.get("leader_line")
        if not isinstance(leader_line, bool):
            raise ValueError(
                "annotation_plan.callouts[%d].leader_line must be boolean" % index)
        background = callout.get("background")
        if spec.get("quality_contract_version") == 3:
            background = _required_nested_string(
                background,
                "annotation_plan.callouts[%d].background" % index)
            if background not in CALLOUT_BACKGROUNDS:
                raise ValueError(
                    "annotation callout background must be one of: %s"
                    % ", ".join(sorted(CALLOUT_BACKGROUNDS)))
            placement_priority = _required_nested_string(
                callout.get("placement_priority"),
                "annotation_plan.callouts[%d].placement_priority" % index)
            if placement_priority != "quiet-canvas-first":
                raise ValueError(
                    "v3 annotation callouts must set placement_priority="
                    "quiet-canvas-first")
            quiet_canvas_rejected_reason = callout.get(
                "quiet_canvas_rejected_reason")
            if background == "opaque-white":
                quiet_canvas_rejected_reason = _required_nested_string(
                    quiet_canvas_rejected_reason,
                    "annotation_plan.callouts[%d].quiet_canvas_rejected_reason"
                    % index)
            elif quiet_canvas_rejected_reason not in (None, ""):
                raise ValueError(
                    "quiet_canvas_rejected_reason is only valid for an opaque-white "
                    "fallback")
        elif background is None:
            background = "quiet-canvas"
            placement_priority = "quiet-canvas-first"
            quiet_canvas_rejected_reason = None
        else:
            placement_priority = "quiet-canvas-first"
            quiet_canvas_rejected_reason = None
        explanatory_role = callout.get("explanatory_role")
        if explanatory_role is not None:
            explanatory_role = _required_nested_string(
                explanatory_role,
                "annotation_plan.callouts[%d].explanatory_role" % index)
        normalized_callouts.append({
            "text": text,
            "target": target,
            "leader_line": leader_line,
            "background": background,
            "placement_priority": placement_priority,
            "quiet_canvas_rejected_reason": quiet_canvas_rejected_reason,
            "explanatory_role": explanatory_role,
        })
    rationale = _required_nested_string(
        plan.get("rationale"), "annotation_plan.rationale")
    required_copy = panel_labels + [item["text"] for item in normalized_callouts]
    missing = [item for item in required_copy if item not in rendered_text]
    if missing:
        raise ValueError(
            "panel labels and callout text must appear in exact_text: %s"
            % ", ".join(missing))
    return {
        "panel_labels": panel_labels,
        "callouts": normalized_callouts,
        "rationale": rationale,
    }
