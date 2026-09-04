"""The phone gate is measured from the renderer's geometry, not attested."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import figure_provenance  # noqa: E402
import qa_figure  # noqa: E402
import qa_quantitative_geometry  # noqa: E402
import render_quantitative_figure  # noqa: E402
from artifact_io import sha256_file  # noqa: E402
from test_render_quantitative_figure import (  # noqa: E402
    DeterministicQuantitativeFigureTests as Fixture,
)


PRIMARY = ["Drug −6.2%", "Control +4.1%", "Δ −10.3"]


def v3_spec():
    spec = Fixture.make_phone_readable(Fixture.spec())
    spec["quality_contract_version"] = 3
    # A short vertical title: Tesseract reads long rotated text as tall boxes,
    # which is a pre-existing false positive of the dominance cap whenever no
    # geometry manifest is available to rule it out.
    panel = spec["data"]["panels"][0]
    panel["y_axis"]["label"] = "Change (%)"
    spec["exact_text"] = [
        "Change (%)" if item == "Change from shared start (%)" else item
        for item in spec["exact_text"]]
    spec["communication_goal"].update({
        "visual_question": "How far apart were the groups at follow-up?",
        "panel_thesis": "The single panel shows the shared start, endpoints, and contrast.",
    })
    spec["layout_plan"] = {
        "content_density": "moderate",
        "wide_canvas_required": False,
        "aspect_ratio_rationale": "The compact landscape frame fits the plotted relationship.",
        "balance_strategy": "The external y label and direct labels balance the data region.",
        "final_display": "Single-column article figure at final report width.",
        "mobile_preview": {
            "width_px": 390,
            "minimum_primary_label_height_px": 10,
            "all_labels_required_without_zoom": False,
            "primary_labels": list(PRIMARY),
            "first_glance_path": ["Find shared start", "Follow both paths", "Read contrast"],
            "supporting_detail_strategy": "Axis ticks remain publication-sized and may require zoom.",
            "explain_back_without_zoom": "The groups began together and ended apart.",
        },
    }
    spec["plot_design"].update({
        "typography": {
            "family": "Helvetica Neue", "fallback": "Arial",
            "upright_natural_width": True,
        },
        "axis_semantics": [{
            "panel_id": "main",
            "x_label": "Follow-up time",
            "x_meaning": "The x-axis shows elapsed follow-up time.",
            "y_label": "Change (%)",
            "y_meaning": "The y-axis shows mean percentage change from the shared start.",
        }],
        "caption_axis_summary": (
            "The x-axis shows follow-up time; the y-axis shows mean percentage change."),
        "numeric_annotation_attachment": (
            "Endpoint values sit beside their markers and the contrast sits on its bracket."),
        "uncertainty_display": {
            "present": True,
            "encoding": "Whiskers and the bracket label show 95% confidence intervals.",
            "attachment": "Each interval touches the estimate or contrast it qualifies.",
        },
        "axis_label_placement": {
            "x_orientation": "horizontal",
            "x_location": "below-data-region",
            "y_orientation": "vertical",
            "y_location": "outside-data-region",
        },
        "legend_plan": {
            "needed": False,
            "reason": "Conventional whiskers are self-evident and explained in the caption.",
            "placement": "none",
        },
    })
    spec["semantic_plan"] = {
        "entities": [
            {"id": "shared-start", "depiction": "the common baseline marker",
             "role": "reference state", "evidence_basis": "reported study baseline"},
            {"id": "endpoints", "depiction": "two direct-labelled endpoint markers",
             "role": "reported group outcomes", "evidence_basis": "reported means"},
            {"id": "contrast", "depiction": "one bracket joining the endpoints",
             "role": "reported between-group difference", "evidence_basis": "reported contrast"},
        ],
        "connectors": [], "panel_jobs": [],
        "grouping_rationale": "One panel keeps the contrast attached to its endpoints.",
        "anatomy_subjects": [], "anatomical_context": [],
        "salience_targets": ["shared-start", "endpoints", "contrast"],
        "information_priority": {
            "primary_entities": ["endpoints", "contrast"],
            "supporting_entities": ["shared-start"],
            "excluded_nonessential": ["decorative icons"],
            "dominance_rationale": "The endpoints and contrast answer the question.",
            "deletion_test": "Remove anything that does not change the endpoint comparison.",
        },
        "uncertainty_encodings": [{
            "target": "contrast",
            "source_of_uncertainty": "sampling uncertainty in the reported contrast",
            "visual_encoding": "a 95% confidence interval attached to the bracket",
            "reader_interpretation": "the interval qualifies the between-group estimate",
        }],
        "cross_view_identity": [],
        "representation_plan": {
            "kind": "literal",
            "evidence_native_anchor": "the plotted endpoints and their attached contrast",
            "cognitive_translation_steps": 0,
            "literal_rejected_reason": None,
            "added_explanatory_value": "The plot directly encodes the reported values.",
            "arranged_elements": False,
            "arrangement_evidence_job": None,
        },
        "quantitative_decision": {
            "verified_numbers_available": True,
            "numbers_carry_primary_message": True,
            "reason": "The exact endpoints and contrast carry the message.",
        },
    }
    return spec


def inspection_for(spec, *, attested_primary_height):
    goal = spec["communication_goal"]
    integrity = {
        key: True for key in (
            "title_matches_visual_question", "panels_form_one_explanation",
            "declared_entities_specific", "all_objects_declared",
            "all_connectors_semantic", "related_content_grouped",
            "panels_add_distinct_information", "primary_entities_visually_dominant",
            "nonessential_elements_absent", "aspect_ratio_suits_content",
            "composition_optically_balanced", "callout_backings_legible",
            "font_system_consistent", "absolute_white_canvas",
            "visual_language_consistent", "stock_asset_assemblage_absent",
            "representation_serves_evidence",
            "visual_explanation_survives_without_labels",
            "text_subordinate_to_visuals", "poster_layout_absent",
            "object_inventory_absent", "anatomy_checked_at_original_size",
            "anatomical_context_sufficient", "uncertainty_encodings_explanatory",
        )
    }
    integrity.update({
        "avoidable_cognitive_translation_added": False,
        "arranged_object_lineup_present": False,
        "arrangement_encodes_evidence": False,
        "cross_view_identity_preserved": [],
        "salience_targets_visible": ["shared-start", "endpoints", "contrast"],
    })
    for key in (
        "anatomy_errors", "unexplained_objects", "ambiguous_connectors",
        "salience_failures", "redundant_sections", "typography_issues",
        "entity_specificity_issues", "visual_clutter", "anatomical_context_losses",
        "identity_drift", "uncertainty_ambiguities", "quantitative_annotation_issues",
        "layout_balance_issues", "callout_backing_issues", "font_consistency_issues",
        "composite_integration_issues", "paper_integrity_issues",
        "representation_issues", "visual_language_issues", "stock_asset_issues",
        "typography_dominance_issues", "visual_explanation_issues",
    ):
        integrity[key] = []
    return {
        "ocr_text": " ".join(qa_figure.expected_pixel_text(spec)),
        "minimum_label_height_px": 24,
        "relationships": [], "detected_effects": [], "text_collisions": [],
        "duplicate_text": [], "unlisted_text": [], "geometry_distortions": [],
        "visual_quality": {key: "pass" for key in qa_figure.V3_VISUAL_QUALITY_DIMENSIONS},
        "typography_scale": {
            "p90_label_height_px": 24,
            "text_box_area_fraction": 0.12,
            "display_headline_absent": True,
            "labels_subordinate_to_visuals": True,
        },
        "communication": {
            "observed_takeaway": goal["reader_takeaway"],
            "observed_explain_back": goal["plain_language_explain_back"],
            "explain_back_matches": True, "intuitive_without_caption": True,
            "familiar_starting_point_visible": True,
            "requires_caption_to_understand": False, "unexplained_jargon": [],
            "intended_takeaway_conveyed": True, "information_flow_clear": True,
            "must_show_visible": goal["must_show"],
            "observed_information_flow": goal["information_flow"],
            "misleading_or_ambiguous": [], "revision_needed": False,
        },
        "mobile_preview": {
            "width_px": 390,
            "minimum_primary_label_height_px": attested_primary_height,
            "readable_primary_labels": list(PRIMARY),
            "observed_first_glance_path": [
                "Find shared start", "Follow both paths", "Read contrast"],
            "observed_explain_back": "The groups began together and ended apart.",
            "explain_back_matches": True,
            "primary_labels_require_zoom": False,
            "supporting_labels_inflated_for_phone": False,
        },
        "annotation": {"panel_labels": [], "callouts": []},
        "integrity": integrity,
        "quantitative": {key: True for key in (
            "axis_semantics_visible", "numeric_annotations_attached_to_referents",
            "uncertainty_attached_to_estimate", "uncertainty_graphically_visible",
            "data_marks_visually_primary", "annotations_clear_of_marks",
            "y_axis_label_vertical", "redundant_legend_absent",
            "full_composition_balanced",
        )},
    }


def provenance_for(spec, image, *, geometry_name=None, detection=None):
    goal = spec["communication_goal"]
    attempt = {"kind": "render", "asset": str(image), "tool": "render_quantitative_figure.py"}
    if geometry_name:
        attempt["geometry"] = geometry_name
    record = {
        "schema_version": 2, "generator_available": False,
        "selected_route": "deterministic", "selected_asset": str(image),
        "selected_sha256": sha256_file(image),
        "attempts": [attempt],
        "comparison": {"candidates_compared": 1,
                       "selection_rationale": "The verified render was inspected."},
        "post_generation_reviews": [{
            "asset": str(image), "intended_takeaway": goal["reader_takeaway"],
            "observed_takeaway": goal["reader_takeaway"],
            "observed_explain_back": goal["plain_language_explain_back"],
            "intended_meaning_conveyed": True, "information_flow_clear": True,
            "intuitive_without_caption": True, "unexplained_jargon": [],
            "issues": [], "decision": "accept",
        }],
    }
    if detection is not None:
        record["generator_detection"] = detection
    return record


class MeasuredPhoneGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.spec = v3_spec()
        self.image = root / "figure.png"
        self.geometry_path = root / "figure.geometry.json"
        self.manifest = render_quantitative_figure.render(
            self.spec, self.image, self.geometry_path)

    def test_renderer_resolves_primary_labels_above_the_floor(self):
        resolved = {item["text"]: item for item in self.manifest["primary_labels_resolved"]}
        self.assertEqual(set(resolved), set(PRIMARY))
        for record in resolved.values():
            self.assertGreaterEqual(record["mobile_height_px"], 10.0)
        base_sizes = {item["role"]: item["size_px"] for item in self.manifest["fonts"]}
        self.assertLessEqual(max(base_sizes.values()), 40)
        ticks = [
            item for item in self.manifest["text_layout"]
            if item["role"] in {"x_tick", "y_tick"}]
        tallest_tick = max(box["bbox_px"]["bottom"] - box["bbox_px"]["top"] for box in ticks)
        self.assertLess(tallest_tick * 390 / self.manifest["image"]["width_px"], 10.0)

    def test_geometry_measurement_passes_an_honest_inspection(self):
        rendered = min(item["glyph_height_px"]
                       for item in self.manifest["primary_labels_resolved"])
        inspection = inspection_for(self.spec, attested_primary_height=rendered)
        report = qa_figure.audit_figure(
            self.spec, self.image, inspection=inspection,
            provenance=provenance_for(
                self.spec, self.image,
                detection={"method": "session-tool-enumeration",
                           "evidence": "no raster generator among exposed tools"}),
            geometry=self.manifest)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["metrics"]["mobile_primary_label_source"], "measured")
        self.assertGreaterEqual(report["metrics"]["measured_mobile_primary_label_px"], 10.0)
        self.assertTrue(report["metrics"]["geometry_manifest_used"])
        self.assertFalse(any("generator_detection" in item for item in report["warnings"]))

    def test_overstated_attestation_fails_against_the_geometry(self):
        inspection = inspection_for(self.spec, attested_primary_height=80)
        report = qa_figure.audit_figure(
            self.spec, self.image, inspection=inspection,
            provenance=provenance_for(self.spec, self.image), geometry=self.manifest)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("overstates" in error for error in report["errors"]),
                        report["errors"])

    def test_geometry_for_a_different_image_is_rejected(self):
        stale = copy.deepcopy(self.manifest)
        stale["image"]["sha256"] = "0" * 64
        inspection = inspection_for(self.spec, attested_primary_height=40)
        report = qa_figure.audit_figure(
            self.spec, self.image, inspection=inspection,
            provenance=provenance_for(self.spec, self.image), geometry=stale)
        self.assertTrue(any("does not describe the audited image" in error
                            for error in report["errors"]), report["errors"])

    def test_missing_geometry_keeps_attestation_but_warns(self):
        inspection = inspection_for(self.spec, attested_primary_height=40)
        report = qa_figure.audit_figure(
            self.spec, self.image, inspection=inspection,
            provenance=provenance_for(self.spec, self.image))
        # Without a manifest the attested height stands: no phone-gate error,
        # even though the raster cannot support 40 px.
        self.assertFalse(any("primary label" in error for error in report["errors"]),
                         report["errors"])
        self.assertFalse(report["metrics"]["geometry_manifest_used"])
        self.assertEqual(report["metrics"]["mobile_primary_label_source"], "attested")
        self.assertTrue(any("attested primary label height" in item
                            for item in report["warnings"]), report["warnings"])
        self.assertTrue(any("generator_detection" in item
                            for item in report["warnings"]), report["warnings"])

    def test_geometry_is_discovered_from_the_provenance_render_attempt(self):
        inspection = inspection_for(self.spec, attested_primary_height=80)
        report = qa_figure.audit_figure(
            self.spec, self.image, inspection=inspection,
            provenance=provenance_for(
                self.spec, self.image, geometry_name=self.geometry_path.name))
        self.assertTrue(report["metrics"]["geometry_manifest_used"])
        self.assertTrue(any("overstates" in error for error in report["errors"]))

    def test_geometry_qa_rejects_a_forged_primary_label_record(self):
        forged = copy.deepcopy(self.manifest)
        forged["primary_labels_resolved"][0]["glyph_height_px"] = 400.0
        report = qa_quantitative_geometry.audit_geometry(self.spec, self.image, forged)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("exceeds its recorded text box" in error
                            for error in report["errors"]), report["errors"])
        shrunk = copy.deepcopy(self.manifest)
        shrunk["primary_labels_resolved"][0]["glyph_height_px"] = 12.0
        report = qa_quantitative_geometry.audit_geometry(self.spec, self.image, shrunk)
        self.assertTrue(any("required at least" in error for error in report["errors"]),
                        report["errors"])

    def test_placeholder_specs_are_rejected_by_figure_qa(self):
        spec = copy.deepcopy(self.spec)
        spec["communication_goal"]["evidence_boundary"] = "<<FILL: boundary>>"
        with self.assertRaisesRegex(ValueError, "placeholder"):
            qa_figure.audit_figure(
                spec, self.image,
                inspection=inspection_for(self.spec, attested_primary_height=40),
                provenance=provenance_for(self.spec, self.image))


class ProvenanceDetectionTests(unittest.TestCase):
    def test_detection_record_shape_is_checked(self):
        self.assertEqual(figure_provenance.provenance_warnings(
            {"generator_available": True}), [])
        self.assertTrue(figure_provenance.provenance_warnings(
            {"generator_available": False}))
        self.assertTrue(any("method" in item for item in figure_provenance.provenance_warnings(
            {"generator_available": False,
             "generator_detection": {"method": "guess", "evidence": "x"}})))
        self.assertEqual(figure_provenance.provenance_warnings(
            {"generator_available": False,
             "generator_detection": {"method": "session-tool-enumeration",
                                     "evidence": "no raster generator exposed"}}), [])


if __name__ == "__main__":
    unittest.main()
