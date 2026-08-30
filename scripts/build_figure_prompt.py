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

from figure_contract import (
    ABSOLUTE_WHITE,
    CALLOUT_BACKGROUNDS,
    CLEAN_SANS_FAMILIES,
    CONCEPT_SCORE_DIMENSIONS,
    CONNECTOR_MEANINGS,
    CONTENT_DENSITIES,
    RENDER_CONTEXTS,
    RENDER_ROUTES,
    REQUIRED_FIELDS,
    REVIEW_STYLES,
    V2_GENERATED_MAX_STRINGS,
    V2_GENERATED_MAX_WORDS,
    V2_GENERATED_MAX_WORDS_PER_STRING,
    inferred_render_route,
    optional_string_list,
    require_string,
    require_string_list,
    validate_annotation_plan,
    validate_communication_goal,
    validate_composite_plan,
    validate_concept_plan,
    validate_layout_plan,
    validate_plot_design,
    validate_semantic_plan,
)


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
            raise ValueError("quality-contract hybrid figures require overlay")

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
            identity_hybrid = (
                contract_version == 3
                and selected_route == "hybrid"
                and isinstance(spec.get("semantic_plan"), dict)
                and bool(spec["semantic_plan"].get("cross_view_identity"))
            )
            if selected_route != "generated" and not identity_hybrid:
                raise ValueError(
                    "communication-first non-quantitative figures must use image generation; "
                    "v3 hybrid requires declared cross-view identity preservation")
            selected_concept, concept_evaluations, concept_rationale = (
                validate_concept_plan(spec))
        if contract_version == 3:
            semantic_plan = validate_semantic_plan(spec, annotation_plan)
            layout_plan = validate_layout_plan(spec)
            missing_mobile_labels = [
                item for item in layout_plan["mobile_preview"]["primary_labels"]
                if item not in rendered_text
            ]
            if missing_mobile_labels:
                raise ValueError(
                    "layout_plan.mobile_preview.primary_labels must appear in "
                    "rendered exact_text: %s" % ", ".join(missing_mobile_labels))

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
    if contract_version == 3 and str(canvas.get("background", "")).upper() != ABSOLUTE_WHITE:
        raise ValueError(
            "quality contract v3 requires an exact #FFFFFF canvas in every writing style")
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
            "retained after whole-image generation and targeted correction failed a "
            "hard typography or repeated-identity invariant. The exact typographic "
            "and identity-preserving geometry layer is added deterministically."),
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
        mobile = layout_plan["mobile_preview"]
        sections.append(
            "CONTENT-FIT LAYOUT — HARD GATE\n"
            "Content density: %s. Wide canvas required by topology: %s. "
            "Aspect-ratio rationale: %s\n"
            "Balance strategy: %s\nFinal display: %s\n"
            "Choose the canvas from the information topology, not a universal wide "
            "template. Reject dead gutters, lopsided visual weight, and padding added "
            "merely to fill page width.\n"
            "PHONE PREVIEW — HARD GATE\n"
            "Inspect a separate proportional %d px-wide preview. The smallest label "
            "must remain at least %.1f px high without zoom. Primary first-glance "
            "labels: %s. First-glance path: %s. Explain-back at phone size: %s."
            % (layout_plan["content_density"],
               "yes" if layout_plan["wide_canvas_required"] else "no",
               layout_plan["aspect_ratio_rationale"],
               layout_plan["balance_strategy"], layout_plan["final_display"],
               mobile["width_px"], mobile["minimum_label_height_px"],
               ", ".join(mobile["primary_labels"]),
               " → ".join(mobile["first_glance_path"]),
               mobile["explain_back_without_zoom"]))
        if selected_route == "generated":
            sections.append(
                "MOBILE LABEL SIMPLICITY — HARD GATE\n"
                "Each primary label names exactly one visible state, change, "
                "comparison, or conclusion in a short phrase. Do not typeset "
                "miniature policy prose, stacked qualifications, noun piles, or "
                "multi-clause copy. Move nuance to the external caption. Place "
                "labels on existing exact-white canvas whenever possible; an opaque "
                "white backing over artwork is fallback-only.")
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
            "REPRESENTATION ECONOMY — HARD GATE\n"
            "Selected kind: %s. Evidence-native anchor: %s. Cognitive translation "
            "steps: %d. Added explanatory value: %s. Arranged elements: %s.%s%s\n"
            "Prefer literal scientific structures. A metaphor, tactile motif, product-"
            "still-life lineup, or arranged asset set is acceptable only when it shortens "
            "the path from pixels to evidence. Reject any composition that first makes "
            "the reader decode a visual device and then translate it back into the "
            "scientific relationship."
            % (
                semantic_plan["representation_plan"]["kind"],
                semantic_plan["representation_plan"]["evidence_native_anchor"],
                semantic_plan["representation_plan"]["cognitive_translation_steps"],
                semantic_plan["representation_plan"]["added_explanatory_value"],
                ("yes" if semantic_plan["representation_plan"]["arranged_elements"]
                 else "no"),
                ((" Literal alternative rejected because: "
                  + semantic_plan["representation_plan"]["literal_rejected_reason"])
                 if semantic_plan["representation_plan"]["literal_rejected_reason"]
                 else ""),
                ((" Arrangement evidence job: "
                  + semantic_plan["representation_plan"]["arrangement_evidence_job"])
                 if semantic_plan["representation_plan"]["arrangement_evidence_job"]
                 else ""),
            ),
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
            "textured, or otherwise busy pixels must first be moved to quiet white canvas "
            "when that preserves the spatial relationship. An opaque white backing plate "
            "with restrained padding is fallback-only; callouts on quiet white canvas remain "
            "unboxed. Use the "
            "same declared house sans-serif family for panels, labels, axes, values, and legends." % (
                panel_text, annotation_plan["rationale"]))
        if annotation_plan["callouts"]:
            sections.append(
                "CALLOUT TARGETS\n" + "\n".join(
                    "- %s → %s (%s)" % (
                        item["text"], item["target"],
                        ("leader line required" if item["leader_line"]
                         else "direct adjacency; no leader line needed")
                        + "; placement: " + item["placement_priority"]
                        + "; backing: " + item["background"]
                        + (("; quiet-canvas rejection: "
                            + item["quiet_canvas_rejected_reason"])
                           if item["quiet_canvas_rejected_reason"] else ""))
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
        "VISUAL-LANGUAGE COHERENCE — HARD GATE\n"
        "Render one authored plate, not an assembly of recognizable assets. Every "
        "primary and supporting element must share the same abstraction, "
        "dimensionality, line treatment, perspective, lighting, and material finish. "
        "Reject glossy stock symbols, emoji-like objects, app pictograms, sticker "
        "cutouts, and mismatched illustration styles. A circle, badge, card, or frame "
        "is allowed only when it encodes a declared scientific boundary, group, "
        "sample, or comparison—never merely to decorate an isolated object.",
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
