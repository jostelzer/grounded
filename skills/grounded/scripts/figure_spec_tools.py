#!/usr/bin/env python3
"""Scaffold, lint, and preview Grounded figure specifications.

Three additive helpers for the figure contract:

* ``scaffold`` writes a schema-complete v3 skeleton for a route and archetype,
  with ``<<FILL: …>>`` placeholders that every gate rejects until replaced;
* ``lint`` runs every validator independently and reports all failures at
  once, with "did you mean" hints for misnamed keys;
* ``preview`` renders a deterministic spec (or takes a generated image), writes
  the proportional 390 px phone preview, and prints the measured primary label
  heights and the effective smallest label at the journal width.

The validators themselves are unchanged and stay fail-fast; this module only
wraps them so a spec can be repaired in one pass instead of one key per run.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json
import figure_contract
from grounded_metadata import rendered_figure_size_mm


ROOT = Path(__file__).resolve().parents[1]
ARCHETYPES = ROOT / "references" / "figure-archetypes.json"
WRITING_STYLES = ROOT / "references" / "figure-writing-style-overlays.json"
PLACEHOLDER_PREFIX = figure_contract.PLACEHOLDER_PREFIX
MOBILE_PREVIEW_WIDTH_PX = 390


def _fill(hint: str) -> str:
    return f"{PLACEHOLDER_PREFIX}: {hint}>>"


def _fill_label(hint: str) -> str:
    """Placeholder for rendered copy: short, no compound punctuation."""
    return f"{PLACEHOLDER_PREFIX} {hint}>>"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


# --------------------------------------------------------------------------
# Known key sets, used only for "did you mean" hints. Extra keys are tolerated
# by every validator; the hints exist because a misnamed key otherwise shows
# up as a bare "X must be a non-empty string" for the key the author meant.
# --------------------------------------------------------------------------

KNOWN_KEYS: dict[str, set[str]] = {
    "$": {
        "quality_contract_version", "figure_id", "profile", "archetype",
        "review_style", "render_route", "render_context", "target_aspect_ratio",
        "aspect_ratio_tolerance", "purpose", "title", "subtitle", "story",
        "observed", "inferred", "evidence_keys", "exact_text", "visual_anchor",
        "communication_goal", "layout_plan", "annotation_plan", "semantic_plan",
        "concepts", "concept_selection", "composite_plan", "plot_design", "data",
        "abbreviations", "relationships", "layout_notes", "constraints", "avoid",
        "geometry_invariants", "style_overrides",
    },
    "communication_goal": {
        "visual_question", "panel_thesis", "reader_takeaway", "must_show",
        "information_flow", "evidence_boundary", "familiar_starting_point",
        "plain_language_explain_back",
    },
    "layout_plan": {
        "content_density", "wide_canvas_required", "aspect_ratio_rationale",
        "balance_strategy", "final_display", "mobile_preview",
    },
    "layout_plan.mobile_preview": {
        "width_px", "minimum_primary_label_height_px",
        "all_labels_required_without_zoom", "primary_labels", "first_glance_path",
        "supporting_detail_strategy", "explain_back_without_zoom",
    },
    "annotation_plan": {"panel_labels", "callouts", "rationale"},
    "annotation_plan.callouts[]": {
        "text", "target", "leader_line", "background", "placement_priority",
        "quiet_canvas_rejected_reason", "explanatory_role",
    },
    "semantic_plan": {
        "entities", "connectors", "panel_jobs", "grouping_rationale",
        "anatomy_subjects", "anatomical_context", "salience_targets",
        "information_priority", "uncertainty_encodings", "cross_view_identity",
        "representation_plan", "cutaway_plan", "quantitative_decision",
    },
    "semantic_plan.entities[]": {"id", "depiction", "role", "evidence_basis"},
    "semantic_plan.connectors[]": {"from", "to", "meaning", "label"},
    "semantic_plan.panel_jobs[]": {"label", "job", "adds_distinct_information"},
    "semantic_plan.anatomical_context[]": {
        "subject", "orientation_landmarks", "focal_region", "context_rationale"},
    "semantic_plan.information_priority": {
        "primary_entities", "supporting_entities", "excluded_nonessential",
        "dominance_rationale", "deletion_test",
    },
    "semantic_plan.uncertainty_encodings[]": {
        "target", "source_of_uncertainty", "visual_encoding", "reader_interpretation"},
    "semantic_plan.cross_view_identity[]": {
        "entity", "views", "invariant_features", "reason"},
    "semantic_plan.representation_plan": {
        "kind", "evidence_native_anchor", "cognitive_translation_steps",
        "literal_rejected_reason", "added_explanatory_value", "arranged_elements",
        "arrangement_evidence_job",
    },
    "semantic_plan.quantitative_decision": {
        "verified_numbers_available", "numbers_carry_primary_message", "reason"},
    "semantic_plan.cutaway_plan": {
        "exterior_silhouette", "cut_plane", "interior_entities",
        "spatial_relationships", "annotation_strategy", "suitability",
    },
    "semantic_plan.cutaway_plan.suitability": {
        "hidden_interior_removes_mental_step", "faithful_interior_supported",
        "distinct_evidence_job", "phone_readable", "reason",
    },
    "concepts[]": {"id", "description", "information_flow", "strengths", "risks"},
    "concept_selection": {"selected_id", "selection_rationale", "evaluations"},
    "concept_selection.evaluations[]": {
        "id", "clarity", "simplicity", "completeness", "elegance", "intuitiveness",
        "assessment",
    },
    "composite_plan": {
        "generated_assets", "deterministic_evidence_layer", "integration_strategy",
        "balance_rationale", "intrinsic_aspect_preserved",
    },
    "composite_plan.generated_assets[]": {
        "id", "purpose", "placement", "text_free", "encodes_magnitude"},
    "plot_design": {
        "chart_type", "encoding", "reader_path", "style_rationale", "typography",
        "render", "axis_semantics", "caption_axis_summary",
        "numeric_annotation_attachment", "uncertainty_display",
        "axis_label_placement", "legend_plan",
    },
    "plot_design.typography": {"family", "fallback", "upright_natural_width"},
    "plot_design.render": {
        "width_px", "height_px", "outer_margin_px", "panel_gap_px", "columns",
        "supersample", "plot_insets_px", "background_color", "ink_color",
        "reference_color", "auto_layout",
    },
    "plot_design.render.plot_insets_px": {"left", "right", "top", "bottom"},
    "plot_design.axis_semantics[]": {
        "panel_id", "x_label", "x_meaning", "y_label", "y_meaning"},
    "plot_design.uncertainty_display": {"present", "encoding", "attachment"},
    "plot_design.axis_label_placement": {
        "x_orientation", "x_location", "y_orientation", "y_location"},
    "plot_design.legend_plan": {"needed", "reason", "placement"},
    "data": {"panels"},
    "data.panels[]": {
        "id", "panel_label", "title", "x_axis", "y_axis", "series", "rows",
        "reference_lines", "events", "contrasts", "annotations", "interval_key",
    },
    "data.panels[].x_axis": {"label", "domain", "ticks", "categories"},
    "data.panels[].y_axis": {"label", "domain", "ticks", "categories"},
    "data.panels[].x_axis.ticks[]": {"value", "label"},
    "data.panels[].y_axis.ticks[]": {"value", "label"},
    "data.panels[].series[]": {
        "id", "label", "label_position", "label_point_id", "color",
        "line_width_px", "marker_radius_px", "points",
    },
    "data.panels[].series[].points[]": {
        "id", "x", "y", "label", "label_position", "y_interval", "x_interval"},
    "data.panels[].rows[]": {
        "id", "value", "interval", "label", "label_position", "color",
        "series_label", "series_label_position", "line_width_px", "marker_radius_px",
    },
    "data.panels[].reference_lines[]": {"id", "axis", "value", "label", "style"},
    "data.panels[].events[]": {"id", "x", "label"},
    "data.panels[].contrasts[]": {
        "id", "from", "to", "x", "x_offset_px", "estimate", "interval",
        "decimal_places", "label", "label_position",
    },
    "data.panels[].contrasts[].from": {"series_id", "point_id"},
    "data.panels[].contrasts[].to": {"series_id", "point_id"},
    "data.panels[].annotations[]": {"id", "text", "x", "y", "align", "leader_to"},
    "data.panels[].annotations[].leader_to": {"series_id", "point_id"},
    "data.panels[].interval_key": {"label", "position", "x_offset_px", "y_offset_px"},
}


def _key_hints(value: Any, path: str = "$") -> list[str]:
    """Return "unknown key … did you mean …" hints for misnamed keys."""
    hints: list[str] = []
    if isinstance(value, dict):
        known = KNOWN_KEYS.get(path)
        if known is not None:
            for key in value:
                if key in known or str(key).startswith("_"):
                    continue
                name = str(key)
                close = difflib.get_close_matches(name, sorted(known), n=1, cutoff=0.6)
                if not close:
                    # A truncated key ("source", "primary") is the common slip;
                    # prefer the known key it begins.
                    prefixed = sorted(
                        (item for item in known
                         if item.startswith(name) or name.startswith(item)),
                        key=len)
                    close = prefixed[:1] or difflib.get_close_matches(
                        name, sorted(known), n=1, cutoff=0.45)
                suggestion = f"; did you mean {close[0]!r}?" if close else ""
                hints.append(f"unknown key {key!r} at {path}{suggestion}")
        for key, item in value.items():
            child = f"{path}.{key}" if path != "$" else str(key)
            hints.extend(_key_hints(item, child))
    elif isinstance(value, list):
        for item in value:
            hints.extend(_key_hints(item, f"{path}[]"))
    return hints


# --------------------------------------------------------------------------
# Scaffold
# --------------------------------------------------------------------------

def _typography_for(review_style: str) -> dict[str, Any]:
    overlays = _load_json(WRITING_STYLES)
    font = overlays.get(review_style, {}).get("font", {})
    family = font.get("family", "Arial")
    fallback = font.get("fallback", "Helvetica")
    if family not in figure_contract.CLEAN_SANS_FAMILIES:
        family, fallback = "Helvetica Neue", "Arial"
    if fallback not in figure_contract.CLEAN_SANS_FAMILIES:
        fallback = "Arial"
    return {"family": family, "fallback": fallback, "upright_natural_width": True}


def _example_panel(index: int, panel_count: int) -> dict[str, Any]:
    letter = "ABCD"[index]
    # Short enough to sit three abreast in a half-width (two-column) panel.
    names = ["Study A", "Study B", "Study C"]
    values = [(0.81, [0.70, 0.95]), (0.87, [0.72, 1.06]), (0.98, [0.79, 1.17])]
    colours = ["#3B7C85", "#3B6F9C", "#C86F55"]
    panel: dict[str, Any] = {
        "id": f"panel-{letter.lower()}",
        "title": None,
        "x_axis": {"label": "Evidence source", "categories": names},
        "y_axis": {
            "label": "Risk ratio",
            "domain": [0.55, 1.25],
            "ticks": [
                {"value": 0.6, "label": "0.6"}, {"value": 0.8, "label": "0.8"},
                {"value": 1.0, "label": "1.0"}, {"value": 1.2, "label": "1.2"},
            ],
        },
        "rows": [
            {"id": f"row-{position}", "value": value, "interval": interval,
             "label": f"{value:.2f}", "label_position": "right", "color": colour}
            for position, ((value, interval), colour) in enumerate(
                zip(values, colours), start=1)
        ],
        "reference_lines": [
            {"id": "no-difference", "axis": "y", "value": 1.0, "label": "No difference"}
        ],
        "events": [],
        "contrasts": [],
        "annotations": [],
    }
    if panel_count > 1:
        panel["panel_label"] = letter
    return panel


def _plot_text(spec: dict[str, Any]) -> list[str]:
    """Every string the deterministic renderer will draw, in draw order."""
    strings: list[str] = []
    for panel in spec.get("data", {}).get("panels", []):
        if panel.get("panel_label"):
            strings.append(panel["panel_label"])
        if panel.get("title"):
            strings.append(panel["title"])
        for axis_name in ("y_axis", "x_axis"):
            axis = panel.get(axis_name, {})
            if axis.get("label"):
                strings.append(axis["label"])
        for axis_name in ("x_axis", "y_axis"):
            axis = panel.get(axis_name, {})
            for category in axis.get("categories") or []:
                strings.append(category)
            for tick in axis.get("ticks") or []:
                if tick.get("label"):
                    strings.append(tick["label"])
        key = panel.get("interval_key")
        if key and key.get("label"):
            strings.append(key["label"])
        for reference in panel.get("reference_lines") or []:
            if reference.get("label"):
                strings.append(reference["label"])
        for event in panel.get("events") or []:
            if event.get("label"):
                strings.append(event["label"])
        for row in panel.get("rows") or []:
            if row.get("label"):
                strings.append(row["label"])
            if row.get("series_label"):
                strings.append(row["series_label"])
        for series in panel.get("series") or []:
            for point in series.get("points") or []:
                if point.get("label"):
                    strings.append(point["label"])
            if series.get("label"):
                strings.append(series["label"])
        for contrast in panel.get("contrasts") or []:
            if contrast.get("label"):
                strings.append(contrast["label"])
        for annotation in panel.get("annotations") or []:
            if annotation.get("text"):
                strings.append(annotation["text"])
    ordered: list[str] = []
    for item in strings:
        if item not in ordered:
            ordered.append(item)
    return ordered


def scaffold(*, route: str, archetype: str, review_style: str, panels: int,
             figure_id: str, profile: str | None = None) -> dict[str, Any]:
    """Return a schema-complete v3 skeleton with placeholders."""
    if route not in {"generated", "deterministic", "composite"}:
        raise ValueError("route must be generated, deterministic, or composite")
    if review_style not in figure_contract.REVIEW_STYLES:
        raise ValueError("review_style must be one of: "
                         + ", ".join(figure_contract.REVIEW_STYLES))
    archetypes = _load_json(ARCHETYPES)
    if archetype not in archetypes:
        raise ValueError("archetype must be one of: " + ", ".join(sorted(archetypes)))
    quantitative = route in {"deterministic", "composite"}
    if archetype == "cutaway" and route != "generated":
        raise ValueError("cutaway figures require the generated route")
    if quantitative and archetype != "quantitative":
        raise ValueError("deterministic and composite routes require archetype=quantitative")
    if not quantitative and archetype == "quantitative":
        raise ValueError("the quantitative archetype requires the deterministic or composite route")
    if not 1 <= panels <= 4:
        raise ValueError("panels must be between 1 and 4")

    panel_labels = list("ABCD"[:panels]) if panels > 1 else []
    entity_ids = [f"entity-{'abcd'[index]}" for index in range(panels)]
    spec: dict[str, Any] = {
        "quality_contract_version": 3,
        "figure_id": figure_id,
        "profile": profile or ("nature-data" if quantitative else "nature-reviews"),
        "archetype": archetype,
        "review_style": review_style,
        "render_route": route,
        "render_context": "article",
        "target_aspect_ratio": 1.6 if quantitative else 1.5,
        "aspect_ratio_tolerance": 0.02,
        "purpose": _fill("the one reader-facing question this figure answers"),
        "title": _fill("caption title naming the actual finding"),
        "story": [_fill("ordered, evidence-backed visual statement")],
        "observed": [_fill("what the sources directly report")],
        "inferred": [],
        "evidence_keys": [_fill("ledger key")],
        "exact_text": [],
        "communication_goal": {
            "visual_question": _fill("single reader-facing question"),
            "panel_thesis": _fill("why every section belongs in one explanation"),
            "reader_takeaway": _fill("one-look takeaway sentence"),
            "must_show": [_fill("indispensable visual fact")],
            "information_flow": [_fill("first eye-path step"), _fill("second step")],
            "evidence_boundary": _fill("what the figure deliberately does not claim"),
            "familiar_starting_point": _fill("recognizable visual idea to start from"),
            "plain_language_explain_back": _fill(
                "sentence a non-specialist can say without the caption"),
        },
        "layout_plan": {
            "content_density": "moderate",
            "wide_canvas_required": False,
            "aspect_ratio_rationale": _fill("why this topology earns the ratio"),
            "balance_strategy": _fill("how optical weight is centred"),
            "final_display": "Journal PDF at no more than 92 mm high",
            "mobile_preview": {
                "width_px": MOBILE_PREVIEW_WIDTH_PX,
                "minimum_primary_label_height_px": 10,
                "all_labels_required_without_zoom": False,
                "primary_labels": [],
                "first_glance_path": [_fill("step one"), _fill("step two")],
                "supporting_detail_strategy": _fill(
                    "how zoom or the caption carries compact supporting labels"),
                "explain_back_without_zoom": _fill("what stays clear on a phone"),
            },
        },
        "annotation_plan": {
            "panel_labels": panel_labels,
            "callouts": [],
            "rationale": _fill("why panels/callouts are or are not needed"),
        },
        "semantic_plan": {
            "entities": [
                {
                    "id": entity_id,
                    "depiction": _fill("specific depiction of this object"),
                    "role": _fill("explanatory role"),
                    "evidence_basis": _fill("ledger keys or synthesis claim ids"),
                }
                for entity_id in entity_ids
            ],
            "connectors": [],
            "panel_jobs": [
                {"label": label, "job": _fill("distinct explanatory job"),
                 "adds_distinct_information": True}
                for label in panel_labels
            ],
            "grouping_rationale": _fill("why related content shares a unit"),
            "anatomy_subjects": [],
            "anatomical_context": [],
            "salience_targets": list(entity_ids),
            "information_priority": {
                "primary_entities": list(entity_ids),
                "supporting_entities": [],
                "excluded_nonessential": ["icons", "decorative backgrounds", "legends"],
                "dominance_rationale": _fill("why primary entities dominate"),
                "deletion_test": _fill("what remains after removing non-primary elements"),
            },
            "uncertainty_encodings": [],
            "cross_view_identity": [],
            "representation_plan": {
                "kind": "literal",
                "evidence_native_anchor": _fill("literal scientific structure"),
                "cognitive_translation_steps": 0,
                "literal_rejected_reason": None,
                "added_explanatory_value": _fill(
                    "why this is the shortest route from pixels to evidence"),
                "arranged_elements": False,
                "arrangement_evidence_job": None,
            },
            "quantitative_decision": {
                "verified_numbers_available": quantitative,
                "numbers_carry_primary_message": quantitative,
                "reason": _fill("route rationale"),
            },
        },
        "abbreviations": {},
        "avoid": ["3D", "gradient", "dashboard cards", "decorative icons"],
        "geometry_invariants": [],
    }
    if quantitative:
        spec["semantic_plan"]["uncertainty_encodings"] = [
            {
                "target": entity_id,
                "source_of_uncertainty": _fill("e.g. reported sampling uncertainty"),
                "visual_encoding": _fill("e.g. whiskers attached to each estimate"),
                "reader_interpretation": _fill("what the reader should infer"),
            }
            for entity_id in entity_ids
        ]
        data_panels = [_example_panel(index, panels) for index in range(panels)]
        for panel, entity_id in zip(data_panels, entity_ids):
            panel["id"] = entity_id
        width = 1536
        spec["plot_design"] = {
            "chart_type": _fill("e.g. direct-labelled dot plot with intervals"),
            "encoding": _fill("what position, whiskers, and colour encode"),
            "reader_path": [_fill("first thing read"), _fill("then")],
            "style_rationale": _fill("why open axes and direct labels"),
            "typography": _typography_for(review_style),
            "render": {
                "width_px": width,
                "height_px": round(width / 1.6),
                "outer_margin_px": 64,
                "panel_gap_px": 64,
                "columns": min(2, panels),
                "supersample": 2,
                "background_color": "#FFFFFF",
                "auto_layout": False,
            },
            "axis_semantics": [
                {
                    "panel_id": panel["id"],
                    "x_label": panel["x_axis"]["label"],
                    "x_meaning": _fill("what the x dimension means"),
                    "y_label": panel["y_axis"]["label"],
                    "y_meaning": _fill("what the y dimension means, with units"),
                }
                for panel in data_panels
            ],
            "caption_axis_summary": _fill("repeat what x and y encode, for the caption"),
            "numeric_annotation_attachment": _fill(
                "how every printed value attaches to its mark"),
            "uncertainty_display": {
                "present": True,
                "encoding": _fill("e.g. whiskers show reported 95% CIs"),
                "attachment": _fill("e.g. every whisker intersects its estimate"),
            },
            "axis_label_placement": {
                "x_orientation": "horizontal",
                "x_location": "below-data-region",
                "y_orientation": "vertical",
                "y_location": "outside-data-region",
            },
            "legend_plan": {
                "needed": False,
                "reason": _fill("why direct labels make a legend unnecessary"),
                "placement": "none",
            },
        }
        spec["data"] = {
            "_todo": _fill("replace the example numbers with verified values"),
            "panels": data_panels,
        }
        spec["exact_text"] = list(panel_labels) + [
            item for item in _plot_text(spec) if item not in panel_labels]
        # The reference-line label is a drawn takeaway string, so it is a valid
        # primary label out of the box; replace it with the real takeaway.
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = ["No difference"]
        spec["geometry_invariants"] = [
            "Whiskers intersect their estimates", "No anisotropic transform"]
    else:
        spec["visual_anchor"] = _fill("concrete domain-native focal structure")
        # Generated primary labels are capped at four words and 28 characters,
        # so the placeholder must already respect that.
        spec["exact_text"] = list(panel_labels) + [_fill_label("label")]
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [_fill_label("label")]
        spec["concepts"] = [
            {
                "id": f"concept-{name}",
                "description": _fill(f"complete visual description ({name})"),
                "information_flow": [_fill(f"eye-path step ({name})")],
                "strengths": [_fill("strength")],
                "risks": [_fill("risk")],
            }
            for name in ("one", "two", "three")
        ]
        spec["concept_selection"] = {
            "selected_id": "concept-one",
            "selection_rationale": _fill("why the winner communicates best"),
            "evaluations": [
                {"id": "concept-one", "clarity": 5, "simplicity": 5, "completeness": 5,
                 "elegance": 5, "intuitiveness": 5, "assessment": _fill("assessment")},
                {"id": "concept-two", "clarity": 4, "simplicity": 4, "completeness": 4,
                 "elegance": 4, "intuitiveness": 4, "assessment": _fill("assessment")},
                {"id": "concept-three", "clarity": 4, "simplicity": 4, "completeness": 4,
                 "elegance": 4, "intuitiveness": 4, "assessment": _fill("assessment")},
            ],
        }
    if route == "composite":
        spec["concepts"] = [
            {
                "id": f"concept-{name}",
                "description": _fill(f"orientation-anchor concept ({name})"),
                "information_flow": [_fill(f"eye-path step ({name})")],
                "strengths": [_fill("strength")],
                "risks": [_fill("risk")],
            }
            for name in ("one", "two", "three")
        ]
        spec["concept_selection"] = {
            "selected_id": "concept-one",
            "selection_rationale": _fill("why the winner communicates best"),
            "evaluations": [
                {"id": "concept-one", "clarity": 5, "simplicity": 5, "completeness": 5,
                 "elegance": 5, "intuitiveness": 5, "assessment": _fill("assessment")},
                {"id": "concept-two", "clarity": 4, "simplicity": 4, "completeness": 4,
                 "elegance": 4, "intuitiveness": 4, "assessment": _fill("assessment")},
                {"id": "concept-three", "clarity": 4, "simplicity": 4, "completeness": 4,
                 "elegance": 4, "intuitiveness": 4, "assessment": _fill("assessment")},
            ],
        }
        spec["composite_plan"] = {
            "generated_assets": [{
                "id": "anchor-1",
                "purpose": _fill("orientation-only role of the generated asset"),
                "placement": _fill("where it sits relative to the plot"),
                "text_free": True,
                "encodes_magnitude": False,
            }],
            "deterministic_evidence_layer": _fill("what the plotted layer owns"),
            "integration_strategy": _fill("how the asset and plot form one composition"),
            "balance_rationale": _fill("why neither layer dominates wrongly"),
            "intrinsic_aspect_preserved": True,
        }
    if archetype == "cutaway":
        spec["semantic_plan"]["entities"].append({
            "id": "interior-1",
            "depiction": _fill("specific interior structure exposed by the cut"),
            "role": _fill("what it explains"),
            "evidence_basis": _fill("ledger keys"),
        })
        spec["semantic_plan"]["information_priority"]["primary_entities"].append("interior-1")
        spec["semantic_plan"]["salience_targets"].append("interior-1")
        spec["semantic_plan"]["cutaway_plan"] = {
            "exterior_silhouette": _fill("recognizable whole-object orientation anchor"),
            "cut_plane": _fill("one coherent section and viewpoint"),
            "interior_entities": ["interior-1"],
            "spatial_relationships": [_fill("truthful nesting or adjacency rule")],
            "annotation_strategy": _fill("how short labels and leaders explain the interior"),
            "suitability": {
                "hidden_interior_removes_mental_step": True,
                "faithful_interior_supported": True,
                "distinct_evidence_job": True,
                "phone_readable": True,
                "reason": _fill("why this cutaway earns a figure slot"),
            },
        }
        spec["exact_text"].append(_fill_label("callout"))
        spec["annotation_plan"]["callouts"] = [{
            "text": _fill_label("callout"),
            "target": "interior-1",
            "leader_line": True,
            "background": "quiet-canvas",
            "placement_priority": "quiet-canvas-first",
            "quiet_canvas_rejected_reason": None,
            "explanatory_role": _fill("full semantic job of this callout"),
        }]
    return spec


# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------

def _catch(errors: list[str], label: str, function, *args):
    """Run one validator, recording its first error instead of raising."""
    try:
        return function(*args)
    except (ValueError, TypeError, KeyError) as exc:
        errors.append(f"{label}: {exc}")
        return None


def lint(spec: dict[str, Any], *, dry_run_render: bool = True) -> dict[str, Any]:
    """Return every validation failure at once plus key hints."""
    errors: list[str] = []
    warnings: list[str] = []
    hints = _key_hints(spec)

    placeholders = figure_contract.find_placeholders(spec)
    for path in placeholders:
        errors.append(f"placeholder: {path} still carries a <<FILL …>> placeholder")

    for field in figure_contract.REQUIRED_FIELDS:
        if field not in spec:
            errors.append(f"required: missing top-level field {field!r}")
    _catch(errors, "purpose", figure_contract.require_string, spec, "purpose")
    _catch(errors, "title", figure_contract.require_string, spec, "title")
    _catch(errors, "story", figure_contract.require_string_list, spec, "story")
    _catch(errors, "exact_text", figure_contract.require_string_list, spec, "exact_text")

    version = spec.get("quality_contract_version")
    if version != 3:
        warnings.append(
            f"quality_contract_version is {version!r}; new figures use 3 and the "
            "v3-only gates below are skipped")
    route = spec.get("render_route")
    if route not in figure_contract.RENDER_ROUTES:
        errors.append("render_route: must be generated, deterministic, or composite")
    if spec.get("review_style") not in figure_contract.REVIEW_STYLES:
        errors.append("review_style: must be scientific, popsci, bullets, or eli5")
    if spec.get("render_context", "article") not in figure_contract.RENDER_CONTEXTS:
        errors.append("render_context: must be article, standalone, or slide")
    archetypes = _load_json(ARCHETYPES)
    if spec.get("archetype") not in archetypes:
        errors.append("archetype: must be one of " + ", ".join(sorted(archetypes)))
    quantitative = spec.get("archetype") == "quantitative"
    if quantitative and route not in {"deterministic", "composite"}:
        errors.append("route: the quantitative archetype requires deterministic or composite")
    if not quantitative and route in {"deterministic", "composite"}:
        errors.append("route: deterministic and composite require archetype=quantitative")

    rendered_text: list[str] = []
    try:
        rendered_text = _expected_text(spec)
    except ValueError as exc:
        errors.append(f"exact_text: {exc}")

    _catch(errors, "communication_goal", figure_contract.validate_communication_goal, spec)
    annotation_plan = _catch(
        errors, "annotation_plan", figure_contract.validate_annotation_plan,
        spec, rendered_text)
    if version == 3:
        _catch(errors, "layout_plan", figure_contract.validate_layout_plan, spec)
        _catch(errors, "rendered copy", figure_contract.validate_v3_rendered_copy,
               spec, rendered_text)
        if annotation_plan is not None:
            _catch(errors, "semantic_plan", figure_contract.validate_semantic_plan,
                   spec, annotation_plan)
        else:
            warnings.append(
                "semantic_plan was not checked because annotation_plan failed")
        mobile = (spec.get("layout_plan") or {}).get("mobile_preview") or {}
        for label in mobile.get("primary_labels") or []:
            if isinstance(label, str) and label not in rendered_text:
                errors.append(
                    f"mobile primary label is absent from exact_text: {label!r}")

    if quantitative:
        _catch(errors, "plot_design", figure_contract.validate_plot_design, spec)
        if spec.get("data") in (None, {}, []):
            errors.append("data: quantitative figures require structured data.panels")
        else:
            import quantitative_figure_spec as qfs
            panels = _catch(errors, "data", qfs._normalize_panels, spec)
            if panels is not None:
                config = _catch(errors, "plot_design.render", qfs._render_config,
                                spec, len(panels))
                if config is not None:
                    _catch(errors, "plot_design.render", qfs._layout, config, len(panels))
                    _catch(errors, "typography", qfs._style, spec, config)
            plot_text = _plot_text(spec)
            declared = [item.strip() for item in spec.get("exact_text", [])
                        if isinstance(item, str)]
            omitted = {str(spec.get("title") or "").strip(),
                       str(spec.get("subtitle") or "").strip()}
            missing = [item for item in plot_text if item not in declared]
            extra = [item for item in declared
                     if item not in plot_text and item not in omitted]
            if missing:
                errors.append(
                    "exact_text: strings the plot will draw are missing: "
                    + "; ".join(repr(item) for item in missing))
            if extra:
                errors.append(
                    "exact_text: strings no plot element draws: "
                    + "; ".join(repr(item) for item in extra))
            if dry_run_render and not errors and not placeholders:
                import render_quantitative_figure as renderer
                try:
                    canvas, body = renderer._render_canvas(spec)
                    for record in body.get("primary_labels_resolved", []):
                        warnings.append(
                            f"primary label {record['text']!r} drawn at "
                            f"{record['size_px']} px → {record['mobile_height_px']:.1f} px "
                            "at 390 px")
                except qfs.TextLayoutError as exc:
                    errors.append(
                        f"layout ({exc.kind}): {exc}; try "
                        "plot_design.render.auto_layout=true or shorter copy")
                except qfs.QuantitativeFigureError as exc:
                    errors.append(f"render: {exc}")
        if route == "composite":
            _catch(errors, "concepts", figure_contract.validate_concept_plan, spec)
            _catch(errors, "composite_plan", figure_contract.validate_composite_plan, spec)
    else:
        if route == "generated" or route == "hybrid":
            _catch(errors, "concepts", figure_contract.validate_concept_plan, spec)
        if not str(spec.get("visual_anchor") or "").strip():
            errors.append("visual_anchor: non-quantitative figures name a focal structure")
        if spec.get("data") is not None:
            errors.append(
                "data: known numbers that carry the figure belong in a deterministic plot")
        counts = [len(item.split()) for item in rendered_text]
        if len(rendered_text) > figure_contract.V2_GENERATED_MAX_STRINGS:
            errors.append(
                f"exact_text: generated copy is limited to "
                f"{figure_contract.V2_GENERATED_MAX_STRINGS} strings")
        if counts and max(counts) > figure_contract.V2_GENERATED_MAX_WORDS_PER_STRING:
            errors.append(
                f"exact_text: a generated string exceeds "
                f"{figure_contract.V2_GENERATED_MAX_WORDS_PER_STRING} words")
        if sum(counts) > figure_contract.V2_GENERATED_MAX_WORDS:
            errors.append(
                f"exact_text: generated copy exceeds "
                f"{figure_contract.V2_GENERATED_MAX_WORDS} words in total")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "hints": hints,
        "metrics": {
            "error_count": len(errors),
            "placeholder_count": len(placeholders),
            "hint_count": len(hints),
        },
    }


def _expected_text(spec: dict[str, Any]) -> list[str]:
    exact = spec.get("exact_text")
    if not isinstance(exact, list) or not exact or any(
            not isinstance(item, str) or not item.strip() for item in exact):
        raise ValueError("exact_text must be a non-empty string list")
    rendered = [item.strip() for item in exact]
    if spec.get("render_context", "article") in {"article", "slide"}:
        omitted = {str(spec.get("title") or "").strip(),
                   str(spec.get("subtitle") or "").strip()}
        rendered = [item for item in rendered if item not in omitted]
    return rendered


# --------------------------------------------------------------------------
# Preview
# --------------------------------------------------------------------------

def _phone_preview(image_path: Path, out_path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(image_path) as source:
        rgb = source.convert("RGB")
        height = max(1, round(rgb.height * MOBILE_PREVIEW_WIDTH_PX / rgb.width))
        preview = rgb.resize((MOBILE_PREVIEW_WIDTH_PX, height), Image.Resampling.LANCZOS)
        preview.save(out_path, format="PNG", optimize=True)
        return preview.size


def preview(spec: dict[str, Any], out_dir: Path, *, image: Path | None = None,
            auto_layout: bool | None = None) -> dict[str, Any]:
    """Render or take an image, write the 390 px view, and measure the gate."""
    out_dir.mkdir(parents=True, exist_ok=True)
    figure_id = str(spec.get("figure_id") or "figure")
    mobile = (spec.get("layout_plan") or {}).get("mobile_preview") or {}
    primary_labels = [item for item in mobile.get("primary_labels") or []
                      if isinstance(item, str)]
    minimum = float(mobile.get("minimum_primary_label_height_px", 10.0))
    result: dict[str, Any] = {
        "figure_id": figure_id, "primary_labels": [], "warnings": [], "errors": [],
    }
    geometry = None
    if spec.get("render_route") in {"deterministic", "composite"} and image is None:
        import render_quantitative_figure as renderer
        import qa_quantitative_geometry as geometry_qa
        image = out_dir / f"{figure_id}.png"
        geometry_path = out_dir / f"{figure_id}.geometry.json"
        geometry = renderer.render(spec, image, geometry_path, auto_layout=auto_layout)
        result["image"] = str(image)
        result["geometry"] = str(geometry_path)
        result["resolved_layout"] = geometry.get("resolved_layout")
        report = geometry_qa.audit_geometry(spec, image, geometry)
        result["geometry_qa"] = report["status"]
        result["errors"].extend(report["errors"])
        width = geometry["image"]["width_px"]
        for record in geometry.get("primary_labels_resolved", []):
            result["primary_labels"].append({
                "text": record["text"], "role": record["role"],
                "size_px": record["size_px"],
                "mobile_height_px": round(record["glyph_height_px"]
                                          * MOBILE_PREVIEW_WIDTH_PX / width, 2),
                "passes": record["glyph_height_px"] * MOBILE_PREVIEW_WIDTH_PX / width
                >= minimum,
            })
        tick_heights = [
            record["bbox_px"]["bottom"] - record["bbox_px"]["top"]
            for record in geometry.get("text_layout", [])
            if record.get("role") in {"x_tick", "y_tick"}
        ]
        if tick_heights:
            pdf_width_mm, _ = rendered_figure_size_mm(
                geometry["image"]["width_px"], geometry["image"]["height_px"])
            smallest = min(tick_heights)
            result["smallest_supporting_label"] = {
                "native_px": round(smallest, 1),
                "effective_pt_at_journal_width": round(
                    smallest * (pdf_width_mm / width) * (72.0 / 25.4), 2),
                "journal_width_mm": round(pdf_width_mm, 1),
            }
    elif image is None:
        raise ValueError("preview of a generated figure needs --image")
    else:
        result["image"] = str(image)
        if shutil.which("tesseract"):
            import qa_figure
            from PIL import Image

            with Image.open(image) as source:
                width = source.width
            _text, _minimum, _p90, _area, words = qa_figure._tesseract_metrics(image)
            for label in primary_labels:
                height = qa_figure._ocr_label_height(label, words)
                result["primary_labels"].append({
                    "text": label,
                    "ocr_height_px": height,
                    "mobile_height_px": (
                        round(height * MOBILE_PREVIEW_WIDTH_PX / width, 2)
                        if height is not None else None),
                    "passes": (
                        height * MOBILE_PREVIEW_WIDTH_PX / width >= minimum
                        if height is not None else None),
                })
        else:
            result["warnings"].append(
                "tesseract is unavailable; primary label heights were not measured")
    preview_path = out_dir / f"{figure_id}.preview-{MOBILE_PREVIEW_WIDTH_PX}.png"
    result["preview"] = str(preview_path)
    result["preview_size"] = _phone_preview(Path(image), preview_path)
    missing = [label for label in primary_labels
               if label not in {item["text"] for item in result["primary_labels"]}]
    if missing and geometry is not None:
        result["errors"].append(
            "primary labels were not resolved by the renderer: "
            + ", ".join(repr(item) for item in missing))
    failing = [item["text"] for item in result["primary_labels"] if item.get("passes") is False]
    if failing:
        result["errors"].append(
            "primary labels below the 10 px phone floor: "
            + ", ".join(repr(item) for item in failing))
    result["status"] = "pass" if not result["errors"] else "fail"
    return result


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = commands.add_parser(
        "scaffold", help="write a schema-complete v3 skeleton with placeholders")
    scaffold_parser.add_argument(
        "--route", required=True, choices=["generated", "deterministic", "composite"])
    scaffold_parser.add_argument("--archetype", required=True)
    scaffold_parser.add_argument(
        "--review-style", required=True, choices=list(figure_contract.REVIEW_STYLES))
    scaffold_parser.add_argument("--panels", type=int, default=1)
    scaffold_parser.add_argument("--figure-id", required=True)
    scaffold_parser.add_argument("--profile")
    scaffold_parser.add_argument("--out", help="output JSON path (default: stdout)")

    lint_parser = commands.add_parser(
        "lint", help="report every validation failure at once")
    lint_parser.add_argument("--spec", required=True)
    lint_parser.add_argument("--report", help="optional JSON report path")
    lint_parser.add_argument(
        "--no-render", action="store_true",
        help="skip the deterministic dry-run render (layout collisions are not checked)")

    preview_parser = commands.add_parser(
        "preview", help="render, write the 390 px view, and measure the phone gate")
    preview_parser.add_argument("--spec", required=True)
    preview_parser.add_argument("--out-dir", required=True)
    preview_parser.add_argument("--image", help="generated figure raster to preview")
    preview_parser.add_argument(
        "--auto-layout", action="store_true", default=None,
        help="render with auto-layout regardless of the spec's setting")
    preview_parser.add_argument("--report", help="optional JSON report path")

    args = parser.parse_args(argv)
    try:
        if args.command == "scaffold":
            spec = scaffold(
                route=args.route, archetype=args.archetype,
                review_style=args.review_style, panels=args.panels,
                figure_id=args.figure_id, profile=args.profile)
            payload = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
            if args.out:
                Path(args.out).write_text(payload, encoding="utf-8")
                print(json.dumps({"status": "written", "path": args.out,
                                  "placeholders": len(figure_contract.find_placeholders(spec))}))
            else:
                sys.stdout.write(payload)
            return 0
        if args.command == "lint":
            result = lint(_load_json(args.spec), dry_run_render=not args.no_render)
            if args.report:
                atomic_write_json(args.report, result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == "pass" else 1
        result = preview(
            _load_json(args.spec), Path(args.out_dir),
            image=Path(args.image) if args.image else None,
            auto_layout=True if args.auto_layout else None)
        if args.report:
            atomic_write_json(args.report, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "pass" else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"figure_spec_tools {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
