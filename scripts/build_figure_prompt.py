#!/usr/bin/env python3
"""Build a modular ImageGen prompt for a verified scientific figure."""

import argparse
import copy
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILES = os.path.join(ROOT, "references", "figure-style-presets.json")
DEFAULT_ARCHETYPES = os.path.join(ROOT, "references", "figure-archetypes.json")
DEFAULT_WRITING_STYLES = os.path.join(
    ROOT, "references", "figure-writing-style-overlays.json")
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


def load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def deep_merge(base, override):
    """Return a recursively merged copy without mutating either input."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def expand_dotted_keys(value):
    """Expand ``{"canvas.aspect": "2:1"}`` into a nested override.

    Early figure specs used both dotted and nested override syntax. Supporting
    both prevents a requested aspect from being silently ignored.
    """
    if not isinstance(value, dict):
        raise ValueError("style_overrides must be an object")
    expanded = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError("style_overrides keys must be non-empty strings")
        target = expanded
        parts = key.split(".")
        for part in parts[:-1]:
            current = target.setdefault(part, {})
            if not isinstance(current, dict):
                raise ValueError("conflicting dotted style override: %s" % key)
            target = current
        target[parts[-1]] = copy.deepcopy(item)
    return expanded


def merge_writing_style(profile, overlay):
    """Apply a writing-style art-direction overlay without dropping base bans."""
    result = deep_merge(profile, overlay)
    for field in ("visual_language", "avoid", "art_direction", "selection_standard"):
        inherited = profile.get(field, [])
        added = overlay.get(field, [])
        if inherited or added:
            result[field] = list(inherited) + [
                item for item in added if item not in inherited
            ]
    base_rules = profile.get("font", {}).get("rules", [])
    style_rules = overlay.get("font", {}).get("rules", [])
    if base_rules or style_rules:
        if overlay.get("font", {}).get("family") != profile.get("font", {}).get("family"):
            result.setdefault("font", {})["rules"] = list(style_rules)
        else:
            result.setdefault("font", {})["rules"] = list(base_rules) + [
                item for item in style_rules if item not in base_rules
            ]
    return result


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
        elif background is None:
            background = "quiet-canvas"
        normalized_callouts.append({
            "text": text,
            "target": target,
            "leader_line": leader_line,
            "background": background,
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


def bullet_section(title, items):
    if not items:
        return ""
    return "%s\n%s" % (title, "\n".join("- %s" % item for item in items))


def format_palette(palette):
    return ", ".join("%s %s" % (key.replace("_", " "), value)
                     for key, value in palette.items())


def build_prompt(spec, profiles, archetypes, profile_name=None,
                 archetype_name=None, writing_styles=None,
                 review_style=None, render_route=None):
    for field in REQUIRED_FIELDS:
        if field not in spec:
            raise ValueError("missing required field: %s" % field)

    purpose = require_string(spec, "purpose")
    title = require_string(spec, "title")
    story = require_string_list(spec, "story")
    exact_text = require_string_list(spec, "exact_text")

    selected_profile = profile_name or spec.get("profile", "nature-reviews")
    selected_archetype = archetype_name or spec.get("archetype", "mechanism")
    if selected_profile not in profiles:
        raise ValueError("unknown profile: %s" % selected_profile)
    if selected_archetype not in archetypes:
        raise ValueError("unknown archetype: %s" % selected_archetype)

    writing_styles = writing_styles or load_json(DEFAULT_WRITING_STYLES)
    selected_review_style = review_style or spec.get("review_style", "scientific")
    if selected_review_style == "prose":
        selected_review_style = "scientific"
    if selected_review_style not in REVIEW_STYLES:
        raise ValueError("review_style must be one of: %s" % ", ".join(REVIEW_STYLES))
    if selected_review_style not in writing_styles:
        raise ValueError("missing writing-style overlay: %s" % selected_review_style)

    overrides = expand_dotted_keys(spec.get("style_overrides", {}))
    profile = merge_writing_style(
        profiles[selected_profile], writing_styles[selected_review_style])
    profile = deep_merge(profile, overrides)
    archetype = archetypes[selected_archetype]

    subtitle = spec.get("subtitle")
    if subtitle is not None and (not isinstance(subtitle, str) or not subtitle.strip()):
        raise ValueError("subtitle must be a non-empty string when supplied")

    framing = profile.get("framing", {})
    render_context = spec.get(
        "render_context", framing.get("default_context", "article"))
    if render_context not in RENDER_CONTEXTS:
        raise ValueError(
            "render_context must be one of: %s" % ", ".join(RENDER_CONTEXTS))

    rendered_text = list(exact_text)
    if render_context in ("article", "slide"):
        frame_text = {title}
        if subtitle:
            frame_text.add(subtitle.strip())
        rendered_text = [item for item in rendered_text if item not in frame_text]
    if not rendered_text:
        raise ValueError("exact_text must include at least one in-figure string")

    selected_route = render_route or inferred_render_route(
        spec, selected_archetype)
    if selected_route not in RENDER_ROUTES:
        raise ValueError("render_route must be one of: %s" % ", ".join(RENDER_ROUTES))

    generated_text = optional_string_list(spec, "generated_text")
    if any(item not in rendered_text for item in generated_text):
        raise ValueError("generated_text must be a subset of rendered exact_text")
    if selected_route == "generated":
        if generated_text and generated_text != rendered_text:
            raise ValueError(
                "generated figures must render every exact_text string directly")
        generated_text = list(rendered_text)
    if selected_route == "deterministic" and generated_text:
        raise ValueError("deterministic figures cannot declare generated_text")
    if selected_route == "composite" and generated_text:
        raise ValueError(
            "composite figures keep every exact text item on the deterministic layer")
    overlay_text = [item for item in rendered_text if item not in generated_text]

    contract_version = spec.get("quality_contract_version")
    if contract_version not in {None, 1, 2, 3}:
        raise ValueError("quality_contract_version must be 1, 2, or 3 when supplied")
    target_aspect = spec.get("target_aspect_ratio")
    if target_aspect is not None:
        try:
            target_aspect = float(target_aspect)
        except (TypeError, ValueError) as exc:
            raise ValueError("target_aspect_ratio must be numeric") from exc
        if not 1.0 <= target_aspect <= 4.0:
            raise ValueError("target_aspect_ratio must be between 1.0 and 4.0")
    visual_anchor = spec.get("visual_anchor")
    if visual_anchor is not None and (
        not isinstance(visual_anchor, str) or not visual_anchor.strip()
    ):
        raise ValueError("visual_anchor must be a non-empty string when supplied")
    if contract_version in {1, 2, 3}:
        if "review_style" not in spec or "render_route" not in spec:
            raise ValueError(
                "quality contract requires explicit review_style and render_route")
        if target_aspect is None:
            raise ValueError(
                "quality contract requires numeric target_aspect_ratio")
        if (selected_archetype != "quantitative" or selected_route == "composite") \
                and not visual_anchor:
            raise ValueError(
                "quality contract requires visual_anchor for generated visual content")
        if selected_route == "hybrid" and not isinstance(spec.get("overlay"), dict):
            raise ValueError("quality contract v1 hybrid figures require overlay")

    communication_goal = None
    selected_concept = None
    concept_evaluations = None
    concept_rationale = None
    plot_design = None
    annotation_plan = None
    semantic_plan = None
    layout_plan = None
    composite_plan = None
    if contract_version in {2, 3}:
        communication_goal = validate_communication_goal(spec)
        annotation_plan = validate_annotation_plan(spec, rendered_text)
        if selected_archetype == "quantitative":
            if selected_route not in {"deterministic", "composite"}:
                raise ValueError(
                    "communication-first quantitative figures must use deterministic or composite plotting")
            plot_design = validate_plot_design(spec)
            if selected_route == "composite":
                selected_concept, concept_evaluations, concept_rationale = (
                    validate_concept_plan(spec))
                composite_plan = validate_composite_plan(spec)
        else:
            if selected_route != "generated":
                raise ValueError(
                    "communication-first non-quantitative figures must use image generation")
            selected_concept, concept_evaluations, concept_rationale = (
                validate_concept_plan(spec))
        if contract_version == 3:
            semantic_plan = validate_semantic_plan(spec, annotation_plan)
            layout_plan = validate_layout_plan(spec)

    observed = optional_string_list(spec, "observed")
    inferred = optional_string_list(spec, "inferred")
    layout_notes = optional_string_list(spec, "layout_notes")
    constraints = optional_string_list(spec, "constraints")
    custom_avoid = optional_string_list(spec, "avoid")
    geometry_invariants = optional_string_list(spec, "geometry_invariants")
    custom_art_direction = optional_string_list(spec, "art_direction")
    data = spec.get("data")
    if data is not None and not isinstance(data, (dict, list)):
        raise ValueError("data must be an object or list")
    if contract_version in {2, 3}:
        if selected_archetype == "quantitative":
            if data is None or data == [] or data == {}:
                raise ValueError(
                    "communication-first quantitative plots require verified structured data")
        elif data is not None:
            raise ValueError(
                "known numbers that carry the figure belong in a quantitative deterministic plot")
        else:
            generated_word_counts = [len(item.split()) for item in rendered_text]
            if len(rendered_text) > V2_GENERATED_MAX_STRINGS:
                raise ValueError(
                    "communication-first generated illustrations allow at most %d essential labels"
                    % V2_GENERATED_MAX_STRINGS)
            if (generated_word_counts
                    and max(generated_word_counts) > V2_GENERATED_MAX_WORDS_PER_STRING):
                raise ValueError(
                    "communication-first generated labels allow at most %d words each"
                    % V2_GENERATED_MAX_WORDS_PER_STRING)
            if sum(generated_word_counts) > V2_GENERATED_MAX_WORDS:
                raise ValueError(
                    "communication-first generated illustrations allow at most %d words in pixels"
                    % V2_GENERATED_MAX_WORDS)

    font = profile["font"]
    canvas = copy.deepcopy(profile["canvas"])
    if render_context == "slide":
        if target_aspect is not None and abs(target_aspect - (16 / 9)) > 0.01:
            raise ValueError("slide target_aspect_ratio must be 16/9")
        canvas["aspect"] = "16:9 landscape (required; no other slide ratio)"
        canvas["margin"] = (
            "Full-bleed canvas; keep the top 19% and bottom 8% visually quiet "
            "because the canonical title/citation chrome overlays those zones"
        )
    if target_aspect is not None and render_context != "slide":
        canvas["aspect"] = (
            "%.4g:1 landscape; preserve this ratio exactly with no anisotropic scaling"
            % target_aspect)

    route_asset = {
        "generated": (
            "Complete publication-grade scientific figure rendered end to end, "
            "including every required label and all final typography directly in pixels."),
        "hybrid": (
            "Last-resort repair route: premium generated scientific illustration "
            "retained after direct-text generation and targeted correction failed. "
            "The remaining exact typographic/data layer is added deterministically."),
        "deterministic": (
            "Deterministic publication-grade scientific figure production brief. "
            "Do not use an image generator for exact plot or data geometry."),
        "composite": (
            "Composite publication-grade quantitative figure: generated text-free "
            "orientation art integrated with deterministic axes, values, uncertainty, "
            "and typography. Generated pixels never encode magnitude."),
    }[selected_route]
    sections = [
        "USE CASE\nscientific-educational",
        "ASSET\n%s" % route_asset,
        "AUTHORING ROUTE\n%s" % selected_route,
        "REVIEW-STYLE IDENTITY\n%s\n%s" % (
            profile["name"], profile["intent"]),
        "PURPOSE\n%s" % purpose,
    ]
    if communication_goal:
        sections.extend([
            "COMMUNICATION GOAL — THE RELEASE GATE\n"
            "After one look, the reader should understand: %s\n"
            "Begin from this recognizable visual idea: %s\n"
            "A non-specialist should be able to explain it back as: %s\n"
            "Evidence boundary: %s" % (
                communication_goal["reader_takeaway"],
                communication_goal["familiar_starting_point"],
                communication_goal["plain_language_explain_back"],
                communication_goal["evidence_boundary"]),
            bullet_section("MUST BE VISUALLY APPARENT", communication_goal["must_show"]),
            bullet_section("INTENDED INFORMATION FLOW", communication_goal["information_flow"]),
        ])
    if layout_plan:
        sections.append(
            "CONTENT-FIT LAYOUT — HARD GATE\n"
            "Content density: %s. Wide canvas required by topology: %s. "
            "Aspect-ratio rationale: %s\n"
            "Balance strategy: %s\nFinal display: %s\n"
            "Choose the canvas from the information topology, not a universal wide "
            "template. Reject dead gutters, lopsided visual weight, and padding added "
            "merely to fill page width."
            % (layout_plan["content_density"],
               "yes" if layout_plan["wide_canvas_required"] else "no",
               layout_plan["aspect_ratio_rationale"],
               layout_plan["balance_strategy"], layout_plan["final_display"]))
    if semantic_plan:
        sections.extend([
            "ONE VISUAL THESIS — HARD GATE\n"
            "Reader-facing question: %s\n"
            "Why every section belongs in this one figure: %s\n"
            "Do not combine independent questions merely because they share a broad topic. "
            "Every panel must be necessary to answer this question, and the caption title "
            "must name the actual subject or finding rather than comment on figure construction."
            % (communication_goal["visual_question"], communication_goal["panel_thesis"]),
            "SEMANTIC OBJECT MANIFEST — NOTHING DECORATIVE\n" + "\n".join(
                "- %s: depict %s; role: %s; evidence basis: %s" % (
                    item["id"], item["depiction"], item["role"],
                    item["evidence_basis"])
                for item in semantic_plan["entities"]),
            "VISUAL CONTENT BUDGET — HARD GATE\n"
            "Primary entities: %s.\nSupporting entities: %s.\n"
            "Explicitly omit as non-essential: %s.\n"
            "Dominance rationale: %s\nDeletion test: %s\n"
            "The primary entities must receive the dominant area, contrast, and first eye fixation. "
            "Supporting entities may clarify them but must not compete. Do not render props, scenery, "
            "background furniture, or repeated motifs that fail the deletion test."
            % (
                ", ".join(semantic_plan["information_priority"]["primary_entities"]),
                ", ".join(semantic_plan["information_priority"]["supporting_entities"])
                or "none",
                "; ".join(semantic_plan["information_priority"]["excluded_nonessential"])
                or "nothing beyond the declared semantic manifest",
                semantic_plan["information_priority"]["dominance_rationale"],
                semantic_plan["information_priority"]["deletion_test"],
            ),
            "LOGICAL GROUPING\n%s\n"
            "Related outcomes or repeated views of the same result belong in one visual "
            "unit. A separate panel is permitted only when it performs a distinct explanatory job."
            % semantic_plan["grouping_rationale"],
            "QUANTITATIVE ROUTING DECISION\n%s" %
            semantic_plan["quantitative_decision"]["reason"],
        ])
        if semantic_plan["panel_jobs"]:
            sections.append(bullet_section(
                "DISTINCT PANEL JOBS",
                ["%s — %s" % (item["label"], item["job"])
                 for item in semantic_plan["panel_jobs"]]))
        if semantic_plan["connectors"]:
            sections.append(bullet_section(
                "DECLARED CONNECTORS — USE NO OTHERS",
                ["%s → %s; meaning: %s; label: %s" % (
                    item["from"], item["to"], item["meaning"], item["label"])
                 for item in semantic_plan["connectors"]]))
        else:
            sections.append(
                "CONNECTORS — HARD GATE\nNo arrows or connector lines are declared. "
                "Do not invent decorative arrows, brackets, trajectories, or flow marks.")
        if semantic_plan["anatomy_subjects"]:
            sections.append(
                "ANATOMICAL INTEGRITY — HARD GATE\n"
                "Inspect every depicted person or animal before returning the image. Each "
                "subject must have the correct number and arrangement of limbs, hands, digits, "
                "facial features, and joints. Reject any extra, missing, duplicated, fused, or "
                "impossible body part. Subjects: %s."
                % "; ".join(semantic_plan["anatomy_subjects"]))
            sections.append(
                "ANATOMICAL CONTEXT — ORIENT BEFORE SIMPLIFYING\n" + "\n".join(
                    "- %s: keep orientation landmarks %s; focal region: %s; why this context is needed: %s"
                    % (item["subject"], ", ".join(item["orientation_landmarks"]),
                       item["focal_region"], item["context_rationale"])
                    for item in semantic_plan["anatomical_context"]
                ) + "\nSimplification must never remove the landmarks a reader needs to locate "
                "the focal region or understand where an instrument, symptom, or mechanism applies.")
        if semantic_plan["salience_targets"]:
            sections.append(
                "SALIENCE AT FINAL SIZE — HARD GATE\nThese must-show entities must remain "
                "plainly visible through adequate contrast, size, separation, and colour: %s. "
                "Do not encode an important difference with near-white, tiny, or overlapping marks."
                % ", ".join(semantic_plan["salience_targets"]))
        if semantic_plan["uncertainty_encodings"]:
            sections.append(
                "UNCERTAINTY MUST EXPLAIN SOMETHING\n" + "\n".join(
                    "- %s: source: %s; encoding: %s; reader should understand: %s"
                    % (item["target"], item["source_of_uncertainty"],
                       item["visual_encoding"], item["reader_interpretation"])
                    for item in semantic_plan["uncertainty_encodings"]
                ) + "\nNever use a generic question mark, dashed halo, outcome icon, or the word "
                "uncertain without tying it to the exact claim or quantity and showing what "
                "the uncertainty changes in the interpretation.")
        if semantic_plan["cross_view_identity"]:
            sections.append(
                "CROSS-VIEW IDENTITY — HARD REGISTRATION GATE\n" + "\n".join(
                    "- %s across %s: preserve %s; reason: %s"
                    % (item["entity"], ", ".join(item["views"]),
                       ", ".join(item["invariant_features"]), item["reason"])
                    for item in semantic_plan["cross_view_identity"]
                ) + "\nWhen one specimen, object, or population is shown under several filters, "
                "thresholds, or states, preserve its identity and registered positions. Change "
                "only the declared transformation so downstream differences remain traceable.")
    if selected_concept:
        selected_scores = next(
            item for item in concept_evaluations
            if item["id"] == selected_concept["id"])
        sections.extend([
            "SELECTED CONCEPT — RENDER ONLY THIS CONCEPT\n"
            "Concept: %s\nDetailed image description: %s\n"
            "Selection rationale: %s\n"
            "Scores: clarity %d/5; simplicity %d/5; completeness %d/5; "
            "elegance %d/5; intuitiveness %d/5.\n"
            "The other two concepts were planning alternatives. Do not blend, quote, or "
            "import motifs from them." % (
                selected_concept["id"], selected_concept["description"],
                concept_rationale,
                selected_scores["clarity"], selected_scores["simplicity"],
                selected_scores["completeness"], selected_scores["elegance"],
                selected_scores["intuitiveness"]),
            bullet_section(
                "SELECTED CONCEPT INFORMATION FLOW",
                selected_concept["information_flow"]),
        ])
    if composite_plan:
        sections.append(
            "COMPOSITE INTEGRATION — GENERATED ORIENTATION, DETERMINISTIC EVIDENCE\n"
            + "\n".join(
                "- %s: purpose: %s; placement: %s; text-free; does not encode magnitude"
                % (item["id"], item["purpose"], item["placement"])
                for item in composite_plan["generated_assets"])
            + "\nDeterministic evidence layer: %s\nIntegration strategy: %s\n"
              "Balance rationale: %s\nPreserve every generated asset's intrinsic "
              "aspect ratio. The deterministic layer owns all panel letters, labels, "
              "axes, values, intervals, and legends."
            % (composite_plan["deterministic_evidence_layer"],
               composite_plan["integration_strategy"],
               composite_plan["balance_rationale"]))
    if plot_design:
        sections.extend([
            "DETERMINISTIC PLOT DESIGN\n"
            "Chart type: %s\nEncoding: %s\nStyle rationale: %s" % (
                plot_design["chart_type"], plot_design["encoding"],
                plot_design["style_rationale"]),
            bullet_section("PLOT READER PATH", plot_design["reader_path"]),
            "PLOT FINISH — HARD REQUIREMENT\n"
            "Use bespoke publication-quality styling from the selected profile: direct "
            "labels where they reduce eye travel, restrained colour, intentional spacing, "
            "crisp natural-width type, and a quiet evidence-first hierarchy. Do not emit "
            "library-default axes, legends, colours, gridlines, or margins.",
        ])
        if plot_design.get("axis_semantics"):
            sections.append(
                "QUANTITATIVE SEMANTICS — HARD GATE\n" + "\n".join(
                    "- %s: x-axis %r means %s; y-axis %r means %s"
                    % (item["panel_id"], item["x_label"], item["x_meaning"],
                       item["y_label"], item["y_meaning"])
                    for item in plot_design["axis_semantics"]
                ) + "\nCaption axis summary: %s\nNumeric annotation attachment: %s\n"
                "Uncertainty encoding: %s\nUncertainty attachment: %s\n"
                "Axis placement: horizontal x-axis below the data region; vertical y-axis "
                "outside the data region. Legend needed: %s; reason: %s; placement: %s.\n"
                "Every axis must name its construct and unit or category. Every interval, "
                "difference, denominator, and endpoint label must sit on, beside, or connect "
                "directly to its graphical referent; never float like a caption inside the plot."
                % (plot_design["caption_axis_summary"],
                   plot_design["numeric_annotation_attachment"],
                   plot_design["uncertainty_display"]["encoding"],
                   plot_design["uncertainty_display"]["attachment"],
                   plot_design["legend_plan"]["needed"],
                   plot_design["legend_plan"]["reason"],
                   plot_design["legend_plan"]["placement"]))
    if annotation_plan:
        panel_text = (
            ", ".join(annotation_plan["panel_labels"])
            if annotation_plan["panel_labels"] else "single continuous composition")
        sections.append(
            "PANELS AND EXPLANATORY CALLOUTS — ALL REVIEW STYLES\n"
            "Panel structure: %s. %s\n"
            "When distinct sections exist, render their identifiers as sequential uppercase "
            "panel labels A, B, C, D. Place explanatory text beside the structure it explains; "
            "when a target is not self-evident, connect the text to the exact target with a "
            "thin clean leader line that visibly begins at the label and whose endpoint visibly lands "
            "on the named referent, not "
            "nearby empty space. When a callout names multiple structures, branch the leader "
            "or use a quiet bracket that reaches every named member. Never use a vague floating "
            "label or a decorative connector. Any callout over illustrated, photographic, "
            "textured, or otherwise busy pixels must sit on an opaque white backing plate "
            "with restrained padding; callouts on quiet white canvas remain unboxed. Use the "
            "same declared house sans-serif family for panels, labels, axes, values, and legends." % (
                panel_text, annotation_plan["rationale"]))
        if annotation_plan["callouts"]:
            sections.append(
                "CALLOUT TARGETS\n" + "\n".join(
                    "- %s → %s (%s)" % (
                        item["text"], item["target"],
                        ("leader line required" if item["leader_line"]
                         else "direct adjacency; no leader line needed")
                        + "; backing: " + item["background"])
                    for item in annotation_plan["callouts"]))
    if communication_goal:
        sections.append(
            "INTUITION AND EXPLAIN-BACK TEST — ALL REVIEW STYLES\n"
            "Make the unfamiliar idea grow visibly from the declared familiar starting "
            "point. Use the most literal domain-native representation that works; use a "
            "metaphor only when it makes the mechanism more accurate and easier to explain, "
            "never as decoration. Reveal one conceptual step at a time along the intended eye "
            "path. Put each necessary term beside the thing it names and remove every object, "
            "arrow, label, or effect that does not help the reader reach the takeaway. The "
            "artwork must pass the explain-back sentence without depending on the article "
            "caption. If a non-specialist would need unexplained jargon or would describe a "
            "different mechanism, the concept is not ready to render.")
    if selected_route == "generated":
        sections.append(
            "FIRST-PASS DIRECT-TEXT CONTRACT — EXECUTE IN THIS IMAGEGEN CALL\n"
            "Render the entire finished figure now, including all required typography "
            "as an integrated part of the artwork. Do not return a textless base, blank "
            "label zones, placeholders, pseudo-text, or a layout intended for later "
            "typesetting. Render each quoted string in the single exact-text manifest "
            "below exactly once and verbatim; "
            "preserve spelling, capitalization, punctuation, symbols, and numbers. Fit "
            "copy with natural line wrapping and placement, never squeezed or stretched "
            "letterforms. Do not repeat the manifest copy elsewhere in the artwork. "
            "The manifest contains only essential short labels; explanatory prose, citations, "
            "and qualifications belong in the external caption. Do not invent extra copy.")
    if visual_anchor:
        sections.append(
            "DOMINANT VISUAL ANCHOR\n%s" % visual_anchor.strip())
    if render_context == "article":
        sections.append(
            "CAPTION CONTEXT — DO NOT RENDER INSIDE THE ARTWORK\n"
            "Title: %s%s" % (
                title,
                "\nSubtitle: %s" % subtitle.strip() if subtitle else ""))
    elif render_context == "slide":
        sections.append(
            "SLIDE CHROME CONTEXT — DO NOT RENDER INSIDE THE ARTWORK\n"
            "Claim title: %s%s\n"
            "The canonical deck renderer adds this claim, DOI citations, evidence "
            "chip, masthead, and slide counter as real text." % (
                title,
                "\nScope: %s" % subtitle.strip() if subtitle else ""))
    else:
        sections.append("TITLE — RENDER COMPACTLY\n%s" % title)
        if subtitle:
            sections.append("SUBTITLE — RENDER ONLY ONCE\n%s" % subtitle.strip())

    sections.extend([
        "BASE SCIENTIFIC STYLE PROFILE\n%s\n%s" % (
            profiles[selected_profile]["name"],
            profiles[selected_profile]["intent"],
        ),
        "FRAMING\nContext: %s\n%s" % (
            render_context,
            framing.get(
                render_context,
                "Keep the scientific content visually primary.")),
        "TYPOGRAPHY — HARD REQUIREMENT\n"
        "- Render every character in %s throughout; %s is the only acceptable visual fallback.\n"
        "- Text colour: %s. Minimum readable text at 1,536 px width: %s px; body %s px; local headings %s px; compact standalone title %s px; panel letters %s px.\n%s" % (
            font["family"], font["fallback"], font["text_color"],
            font["minimum_px_at_1536_width"], font["body_px_at_1536_width"],
            font["section_px_at_1536_width"], font["title_px_at_1536_width"],
            font["panel_label_px_at_1536_width"],
            "\n".join("- %s" % item for item in font["rules"])),
        "CANVAS\n- Background: %s\n- Aspect: %s\n- Margin: %s\n- Density: %s" % (
            canvas["background"], canvas["aspect"], canvas["margin"],
            canvas["density"]),
        "PALETTE\n%s" % format_palette(profile["palette"]),
        bullet_section("VISUAL LANGUAGE", profile["visual_language"]),
        bullet_section("EDITORIAL ART DIRECTION", profile.get("art_direction", [])),
        bullet_section("CANDIDATE SELECTION STANDARD", profile.get("selection_standard", [])),
        "ARCHETYPE\n%s — %s" % (selected_archetype, archetype["goal"]),
        bullet_section("COMPOSITION", archetype["composition"]),
        bullet_section("EVIDENCE-BACKED STORY", story),
    ])

    if observed:
        sections.append(bullet_section("DIRECTLY OBSERVED", observed))
    if inferred:
        sections.append(bullet_section(
            "INFERRED, MODEL-SUPPORTED, MIXED, OR UNCERTAIN", inferred))
    if data is not None:
        sections.append("EXACT DATA — DO NOT ALTER\n%s" % json.dumps(
            data, ensure_ascii=False, indent=2, sort_keys=True))
    if layout_notes:
        sections.append(bullet_section("TOPIC-SPECIFIC LAYOUT", layout_notes))
    if constraints:
        sections.append(bullet_section("SCIENTIFIC CONSTRAINTS", constraints))
    if custom_art_direction:
        sections.append(bullet_section(
            "TOPIC-SPECIFIC ART DIRECTION", custom_art_direction))

    geometry_contract = [
        "Preserve the declared canvas aspect ratio exactly from source through final export.",
        "Never resize, condense, expand, shear, or stretch the artwork or typography along one axis.",
        "Every intended circle remains a true circle and every intended square remains square.",
        "Fit copy by wrapping, editing, or moving it—not by distorting glyph proportions.",
    ] + geometry_invariants
    sections.append(bullet_section("GEOMETRY — HARD INVARIANTS", geometry_contract))

    slide_contract = ""
    if render_context == "slide":
        slide_contract = (
            " Keep the top and bottom chrome zones free of essential labels, values, "
            "arrows, and focal structures. Do not render the claim title, citations, "
            "evidence chip, masthead, or slide number in the pixels."
        )
    if selected_route == "generated":
        sections.append(
            "EXACT IN-FIGURE TEXT MANIFEST — RENDER EVERY STRING VERBATIM IN %s\n%s" % (
                font["family"].upper(),
                "\n".join("- %s" % json.dumps(item, ensure_ascii=False)
                          for item in generated_text)))
    elif selected_route == "hybrid":
        if generated_text:
            sections.append(
                "TEXT THE IMAGE MODEL MAY RENDER VERBATIM IN %s\n%s" % (
                    font["family"].upper(),
                    "\n".join("- %s" % json.dumps(item, ensure_ascii=False)
                              for item in generated_text)))
        sections.append(
            "RESERVED DETERMINISTIC OVERLAY COPY — DO NOT RENDER THESE WORDS\n%s\n"
            "Leave optically quiet, compositionally intentional space for this copy. "
            "Render no placeholder glyphs, pseudo-text, letters, numbers, or watermark "
            "in those zones." % "\n".join(
                "- %s" % json.dumps(item, ensure_ascii=False)
                for item in overlay_text))
    elif selected_route in {"deterministic", "composite"}:
        sections.append(
            "EXACT DETERMINISTIC TEXT MANIFEST\n%s" % "\n".join(
                "- %s" % json.dumps(item, ensure_ascii=False)
                for item in rendered_text))
    else:
        raise ValueError("unsupported render route")

    all_avoid = list(profile["avoid"]) + custom_avoid
    sections.extend([
        bullet_section("AVOID", all_avoid),
        bullet_section("ARCHETYPE QA", archetype["qa"]),
        "FINAL CONTRACT\n"
        + ({
            "generated": (
                "Generate the genuinely polished, fully typeset final figure in this call. "
                "Before returning it, visually verify every quoted manifest string character "
                "by character. Do not leave blank text placeholders, pseudo-text, or add "
                "unlisted copy. Preserve every number, unit, interval, denominator, qualifier, "
                "relationship, font proportion, and geometric invariant. Optimize for the "
                "declared reader takeaway and intended eye path, not for decorative density. "
                "After generation the agent will independently state what the image actually "
                "communicates; unclear meaning or flow requires another iteration."),
            "hybrid": (
                "Generate the polished illustration layer now. Preserve every scientific "
                "relationship and geometry invariant, leave the declared overlay zones quiet, "
                "and render no pseudo-text. The deterministic compositor adds the exact copy."),
            "deterministic": (
                "Render this figure deterministically with mathematically faithful geometry, "
                "natural-width typography, and no anisotropic scaling."),
            "composite": (
                "Generate only the declared text-free orientation assets, then integrate "
                "them into the deterministic plotting canvas. Keep every axis, value, "
                "interval, panel letter, and label on the deterministic layer; preserve "
                "asset aspect ratios and verify the complete optical balance."),
        }[selected_route])
        + " No watermark, logo, masthead, or imitation journal branding."
        + slide_contract
    ])
    return "\n\n".join(section for section in sections if section)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a modular prompt for a Grounded review figure")
    parser.add_argument("--spec", help="JSON evidence and copy specification")
    parser.add_argument("--profile", help="Override the style profile")
    parser.add_argument("--archetype", help="Override the figure archetype")
    parser.add_argument("--review-style", choices=REVIEW_STYLES,
                        help="Override the review writing style")
    parser.add_argument("--render-route", choices=RENDER_ROUTES,
                        help="Override generated, hybrid, deterministic, or composite routing")
    parser.add_argument("--profiles", default=DEFAULT_PROFILES,
                        help="Style profile JSON file")
    parser.add_argument("--writing-styles", default=DEFAULT_WRITING_STYLES,
                        help="Writing-style overlay JSON file")
    parser.add_argument("--archetypes", default=DEFAULT_ARCHETYPES,
                        help="Archetype JSON file")
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--list-archetypes", action="store_true")
    parser.add_argument("--out", help="Write prompt to a file instead of stdout")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    profiles = load_json(args.profiles)
    archetypes = load_json(args.archetypes)
    writing_styles = load_json(args.writing_styles)

    if args.list_profiles:
        for name in sorted(profiles):
            print("%s\t%s" % (name, profiles[name]["name"]))
        return 0
    if args.list_archetypes:
        for name in sorted(archetypes):
            print("%s\t%s" % (name, archetypes[name]["goal"]))
        return 0
    if not args.spec:
        raise ValueError("--spec is required unless listing profiles or archetypes")

    prompt = build_prompt(
        load_json(args.spec), profiles, archetypes,
        args.profile, args.archetype, writing_styles,
        args.review_style, args.render_route)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as stream:
            stream.write(prompt)
            stream.write("\n")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        sys.exit(2)
