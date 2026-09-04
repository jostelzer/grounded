import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import qa_quantitative_geometry  # noqa: E402
import qa_figure  # noqa: E402
import render_quantitative_figure  # noqa: E402
from artifact_io import sha256_file  # noqa: E402


class DeterministicQuantitativeFigureTests(unittest.TestCase):
    @staticmethod
    def spec():
        return {
            "quality_contract_version": 2,
            "profile": "nature-data",
            "archetype": "quantitative",
            "render_route": "deterministic",
            "render_context": "article",
            "review_style": "scientific",
            "target_aspect_ratio": 2.0,
            "purpose": "Show two exact trajectories from one shared starting point.",
            "title": "The paths diverged after assignment",
            "story": [
                "Both groups begin at the same reference value.",
                "The intervention falls while the comparator rises.",
                "The endpoint contrast has a reported confidence interval.",
            ],
            "communication_goal": {
                "reader_takeaway": "The groups moved in opposite directions after assignment.",
                "must_show": ["shared start", "two endpoints", "endpoint uncertainty"],
                "information_flow": ["Start together", "Follow both paths", "Read the gap"],
                "evidence_boundary": "These are group estimates, not personal trajectories.",
                "familiar_starting_point": "Two paths leaving one shared starting point.",
                "plain_language_explain_back": "The groups started together and ended far apart.",
            },
            "annotation_plan": {
                "panel_labels": [],
                "callouts": [],
                "rationale": "One continuous quantitative panel needs no panel letter.",
            },
            "plot_design": {
                "chart_type": "direct-labelled fork trajectory",
                "encoding": "Position is exact change; whiskers are reported intervals.",
                "reader_path": ["Shared origin", "Direct-labelled endpoints", "Contrast bracket"],
                "style_rationale": "Open axes and restrained colour keep the values primary.",
                "render": {
                    "width_px": 1200,
                    "height_px": 600,
                    "outer_margin_px": 50,
                    "panel_gap_px": 50,
                    "columns": 1,
                    "supersample": 2,
                    "plot_insets_px": {
                        "left": 140, "right": 170, "top": 80, "bottom": 90,
                    },
                },
            },
            "data": {
                "panels": [{
                    "id": "main",
                    "x_axis": {
                        "label": "Follow-up time",
                        "domain": [0, 10],
                        "ticks": [
                            {"value": 0, "label": "Start"},
                            {"value": 10, "label": "End"},
                        ],
                    },
                    "y_axis": {
                        "label": "Change from shared start (%)",
                        "domain": [-10, 10],
                        "ticks": [
                            {"value": -10, "label": "−10"},
                            {"value": 0, "label": "0"},
                            {"value": 10, "label": "+10"},
                        ],
                    },
                    "reference_lines": [{
                        "id": "zero", "axis": "y", "value": 0,
                        "label": "Shared start",
                    }],
                    "events": [{
                        "id": "assignment", "x": 0, "label": "Assignment",
                    }],
                    "series": [
                        {
                            "id": "intervention",
                            "label": "Intervention",
                            "label_position": "right",
                            "label_point_id": "end",
                            "color": "#315A70",
                            "points": [
                                {"id": "start", "x": 0, "y": 0},
                                {
                                    "id": "end", "x": 10, "y": -6.2,
                                    "y_interval": [-7.0, -5.4],
                                    "label": "−6.2%", "label_position": "below",
                                },
                            ],
                        },
                        {
                            "id": "comparator",
                            "label": "Comparator",
                            "label_position": "right",
                            "label_point_id": "end",
                            "color": "#C77A5A",
                            "points": [
                                {"id": "start", "x": 0, "y": 0},
                                {
                                    "id": "end", "x": 10, "y": 4.1,
                                    "y_interval": [3.4, 4.8],
                                    "label": "+4.1%", "label_position": "above",
                                },
                            ],
                        },
                    ],
                    "contrasts": [{
                        "id": "endpoint-gap",
                        "from": {"series_id": "intervention", "point_id": "end"},
                        "to": {"series_id": "comparator", "point_id": "end"},
                        "x": 10,
                        "x_offset_px": -65,
                        "estimate": -10.3,
                        "interval": [-11.7, -8.9],
                        "label": "−10.3 points (95% CI −11.7 to −8.9)",
                        "label_position": "left",
                    }],
                }],
            },
            "exact_text": [
                "The paths diverged after assignment",
                "Follow-up time",
                "Change from shared start (%)",
                "Start", "End", "−10", "0", "+10",
                "Shared start", "Assignment",
                "Intervention", "−6.2%", "Comparator", "+4.1%",
                "−10.3 points (95% CI −11.7 to −8.9)",
            ],
        }

    @staticmethod
    def make_phone_readable(spec):
        """Remove redundant plot copy while retaining the exact comparison."""
        panel = spec["data"]["panels"][0]
        panel["reference_lines"] = []
        panel["events"] = []
        panel["series"][0]["label"] = "Drug −6.2%"
        panel["series"][1]["label"] = "Control +4.1%"
        for series in panel["series"]:
            series["points"][1]["label"] = None
        panel["contrasts"][0].update({
            "x": 5,
            "x_offset_px": -20,
            "label": "Δ −10.3",
        })
        removed = {
            "Shared start", "Assignment", "Intervention", "Comparator",
            "−6.2%", "+4.1%", "−10.3 points (95% CI −11.7 to −8.9)",
        }
        spec["exact_text"] = [
            item for item in spec["exact_text"] if item not in removed
        ]
        spec["exact_text"].extend([
            "Drug −6.2%", "Control +4.1%", "Δ −10.3",
        ])
        return spec

    def render_case(self, spec=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        image = root / "figure.png"
        geometry = root / "figure.geometry.json"
        selected_spec = spec or self.spec()
        manifest = render_quantitative_figure.render(
            selected_spec, image, geometry)
        return selected_spec, image, geometry, manifest

    def test_renderer_emits_exact_geometry_and_raster(self):
        spec, image, geometry, manifest = self.render_case()
        self.assertTrue(image.is_file())
        self.assertTrue(geometry.is_file())
        self.assertEqual(manifest["image"]["width_px"], 1200)
        self.assertEqual(manifest["image"]["height_px"], 600)
        points = {
            (point["series_id"], point["point_id"]): point
            for point in manifest["panels"][0]["points"]
        }
        self.assertEqual(points[("intervention", "end")]["y_value"], -6.2)
        self.assertNotEqual(
            points[("intervention", "end")]["y_px"],
            points[("comparator", "end")]["y_px"],
        )
        report = qa_quantitative_geometry.audit_geometry(spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["metrics"]["points_verified"], 4)
        self.assertEqual(report["metrics"]["intervals_verified"], 2)
        self.assertGreater(report["metrics"]["raster_marks_probed"], 8)

    def test_renderer_emits_and_audits_horizontal_intervals(self):
        spec = copy.deepcopy(self.spec())
        endpoint = spec["data"]["panels"][0]["series"][0]["points"][1]
        endpoint.pop("y_interval")
        endpoint["x_interval"] = [8.5, 10]
        _spec, image, _geometry, manifest = self.render_case(spec)
        horizontal = [
            item for item in manifest["panels"][0]["intervals"]
            if item.get("axis") == "x"
        ]
        self.assertEqual(len(horizontal), 1)
        self.assertEqual(horizontal[0]["low_value"], 8.5)
        self.assertEqual(horizontal[0]["high_value"], 10)
        self.assertIn("low_x_px", horizontal[0])
        self.assertIn("high_x_px", horizontal[0])
        report = qa_quantitative_geometry.audit_geometry(spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["metrics"]["intervals_verified"], 2)

    def test_point_cannot_declare_horizontal_and_vertical_intervals(self):
        spec = copy.deepcopy(self.spec())
        spec["data"]["panels"][0]["series"][0]["points"][1]["x_interval"] = [8.5, 10]
        with self.assertRaisesRegex(ValueError, "both x_interval and y_interval"):
            self.render_case(spec)

    def test_v3_renderer_uses_explicit_clean_sans_typography(self):
        spec = self.make_phone_readable(self.spec())
        spec["quality_contract_version"] = 3
        spec["layout_plan"] = {
            "content_density": "moderate",
            "wide_canvas_required": False,
            "aspect_ratio_rationale": "The trajectories and endpoint labels need a balanced landscape frame.",
            "balance_strategy": "External labels and marks balance around the plot centre.",
            "final_display": "Single-column article figure at final report width.",
            "mobile_preview": {
                "width_px": 390,
                "minimum_primary_label_height_px": 10,
                "all_labels_required_without_zoom": False,
                "primary_labels": ["Follow-up time", "Change from shared start (%)"],
                "first_glance_path": ["Find shared start", "Follow both paths", "Read contrast"],
                "supporting_detail_strategy": "Axis ticks remain publication-sized and may require zoom.",
                "explain_back_without_zoom": "The groups began together and ended apart.",
            },
        }
        spec["plot_design"]["typography"] = {
            "family": "Helvetica Neue",
            "fallback": "Arial",
            "upright_natural_width": True,
        }
        _spec, _image, _geometry, manifest = self.render_case(spec)
        self.assertTrue(manifest["fonts"])
        self.assertEqual(
            {record["requested_family"] for record in manifest["fonts"]},
            {"Helvetica Neue"})
        report = qa_quantitative_geometry.audit_geometry(
            spec, _image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract is unavailable")
    def test_real_v3_render_does_not_inflate_every_label_for_phone(self):
        spec = self.make_phone_readable(self.spec())
        spec["quality_contract_version"] = 3
        spec["layout_plan"] = {
            "content_density": "sparse",
            "wide_canvas_required": True,
            "aspect_ratio_rationale": "One comparison needs a compact landscape frame.",
            "balance_strategy": "Labels and marks balance around the plot centre.",
            "final_display": "Single-column article figure at final report width.",
            "mobile_preview": {
                "width_px": 390,
                "minimum_primary_label_height_px": 10,
                "all_labels_required_without_zoom": False,
                "primary_labels": [
                    "Follow-up time", "Change from shared start (%)"],
                "first_glance_path": [
                    "Find the shared start", "Follow the paths", "Read the gap"],
                "supporting_detail_strategy": "Axis ticks remain publication-sized and may require zoom.",
                "explain_back_without_zoom": (
                    "The groups began together and ended apart."),
            },
        }
        spec["plot_design"]["typography"] = {
            "family": "Helvetica Neue",
            "fallback": "Arial",
            "upright_natural_width": True,
        }
        _spec, image, _geometry, manifest = self.render_case(spec)
        _ocr, measured_height = qa_figure._tesseract(image)
        self.assertIsNotNone(measured_height)
        delivered_height = measured_height * 390 / manifest["image"]["width_px"]
        self.assertLess(delivered_height, 10.0)
        self.assertLessEqual(
            max(record["size_px"] for record in manifest["fonts"]), 36)
        # Only the declared primary labels clear the phone floor.
        resolved = {item["text"]: item for item in manifest["primary_labels_resolved"]}
        self.assertEqual(
            set(resolved), {"Follow-up time", "Change from shared start (%)"})
        for item in resolved.values():
            self.assertGreaterEqual(item["mobile_height_px"], 10.0)

    def test_v3_renderer_rejects_display_or_flared_plot_type(self):
        spec = self.spec()
        spec["quality_contract_version"] = 3
        spec["layout_plan"] = {
            "content_density": "moderate",
            "wide_canvas_required": False,
            "aspect_ratio_rationale": "The trajectories need a compact landscape frame.",
            "balance_strategy": "Marks and labels balance around the plot centre.",
            "final_display": "Single-column article figure at final report width.",
        }
        spec["plot_design"]["typography"] = {
            "family": "Optima",
            "fallback": "Helvetica Neue",
            "upright_natural_width": True,
        }
        with self.assertRaisesRegex(
            render_quantitative_figure.QuantitativeFigureError,
            "clean sans-serif"):
            self.render_case(spec)

    def test_panel_title_cannot_become_an_in_plot_caption_or_glossary(self):
        spec = self.spec()
        spec["data"]["panels"][0]["title"] = (
            "CRP = C-reactive protein and the interpretation of every result")
        spec["exact_text"].append(spec["data"]["panels"][0]["title"])
        with self.assertRaisesRegex(
            render_quantitative_figure.QuantitativeFigureError,
            "move interpretation and definitions to the external caption"):
            self.render_case(spec)

    def test_compact_figure_scales_type_for_the_true_pdf_width(self):
        spec = self.spec()
        spec["target_aspect_ratio"] = 1.6
        spec["plot_design"]["render"].update({
            "width_px": 1600,
            "height_px": 1000,
        })
        spec["plot_design"]["render"]["plot_insets_px"]["right"] = 220
        _spec, _image, _geometry, manifest = self.render_case(spec)
        tick = next(item for item in manifest["fonts"] if item["role"] == "tick")
        self.assertGreaterEqual(tick["size_px"], 35)
        self.assertLess(tick["target_pdf_width_mm"], 184.0)
        y_label = next(
            item for item in manifest["text_layout"]
            if item["role"] == "y_axis_label")
        cell_left = manifest["panels"][0]["cell_box_px"]["left"]
        self.assertGreaterEqual(y_label["bbox_px"]["left"], cell_left + 2)

    def test_text_layout_is_inside_the_canvas_and_collision_free(self):
        _spec, _image, _geometry, manifest = self.render_case()
        width = manifest["image"]["width_px"]
        height = manifest["image"]["height_px"]
        records = manifest["text_layout"]
        self.assertGreater(len(records), 10)
        for record in records:
            box = record["bbox_px"]
            self.assertGreaterEqual(box["left"], 0)
            self.assertGreaterEqual(box["top"], 0)
            self.assertLessEqual(box["right"], width)
            self.assertLessEqual(box["bottom"], height)
        for index, first in enumerate(records):
            for second in records[index + 1:]:
                if first["panel_id"] != second["panel_id"]:
                    continue
                self.assertFalse(
                    render_quantitative_figure._text_boxes_overlap(
                        first["bbox_px"], second["bbox_px"]),
                    f"{first['text']!r} overlaps {second['text']!r}",
                )

    def test_renderer_supports_a_multi_point_trajectory(self):
        spec = self.spec()
        points = spec["data"]["panels"][0]["series"][0]["points"]
        points.insert(1, {"id": "middle", "x": 5, "y": -2.7})
        selected_spec, image, _geometry, manifest = self.render_case(spec)
        report = qa_quantitative_geometry.audit_geometry(
            selected_spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["metrics"]["points_verified"], 5)
        trajectory = [
            point for point in manifest["panels"][0]["points"]
            if point["series_id"] == "intervention"
        ]
        self.assertEqual([point["point_id"] for point in trajectory], [
            "start", "middle", "end",
        ])

    def test_interval_key_is_attached_to_an_example_whisker_inside_plot(self):
        spec = self.spec()
        label = "Point = estimate; whisker = 95% CI"
        spec["data"]["panels"][0]["interval_key"] = {
            "label": label,
            "position": "top-right",
            "x_offset_px": -80,
            "y_offset_px": 18,
        }
        spec["exact_text"].append(label)
        _spec, _image, _geometry, manifest = self.render_case(spec)
        key = manifest["panels"][0]["interval_key"]
        self.assertEqual(key["label"], label)
        self.assertEqual(key["position"], "top-right")
        self.assertTrue(any(
            item["role"] == "interval_key" and item["text"] == label
            for item in manifest["text_layout"]))

    def test_geometry_manifest_records_conventional_axis_orientation(self):
        _spec, _image, _geometry, manifest = self.render_case()
        panel = manifest["panels"][0]
        self.assertEqual(panel["x_axis"]["label_orientation"], "horizontal")
        self.assertEqual(panel["x_axis"]["label_location"], "below-data-region")
        self.assertEqual(panel["y_axis"]["label_orientation"], "vertical")
        self.assertEqual(panel["y_axis"]["label_location"], "outside-data-region")

    def test_v3_qa_rejects_axes_or_intervals_not_attached_to_their_meaning(self):
        spec = self.make_phone_readable(self.spec())
        spec["quality_contract_version"] = 3
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
                "primary_labels": ["Follow-up time", "Change from shared start (%)"],
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
                "y_label": "Change from shared start (%)",
                "y_meaning": "The y-axis shows mean percentage change from the shared start.",
            }],
            "caption_axis_summary": (
                "The x-axis shows follow-up time; the y-axis shows mean percentage change."
            ),
            "numeric_annotation_attachment": (
                "Endpoint values sit beside their markers and the contrast sits on its bracket."
            ),
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
        selected_spec, image, _geometry, _manifest = self.render_case(spec)
        goal = selected_spec["communication_goal"]
        integrity = {
            "title_matches_visual_question": True,
            "panels_form_one_explanation": True,
            "declared_entities_specific": True,
            "all_objects_declared": True,
            "all_connectors_semantic": True,
            "related_content_grouped": True,
            "panels_add_distinct_information": True,
            "primary_entities_visually_dominant": True,
            "nonessential_elements_absent": True,
            "aspect_ratio_suits_content": True,
            "composition_optically_balanced": True,
            "callout_backings_legible": True,
            "font_system_consistent": True,
            "absolute_white_canvas": True,
            "visual_language_consistent": True,
            "stock_asset_assemblage_absent": True,
            "representation_serves_evidence": True,
            "visual_explanation_survives_without_labels": True,
            "text_subordinate_to_visuals": True,
            "poster_layout_absent": True,
            "object_inventory_absent": True,
            "avoidable_cognitive_translation_added": False,
            "arranged_object_lineup_present": False,
            "arrangement_encodes_evidence": False,
            "anatomy_checked_at_original_size": True,
            "anatomical_context_sufficient": True,
            "uncertainty_encodings_explanatory": True,
            "cross_view_identity_preserved": [],
            "salience_targets_visible": ["shared-start", "endpoints", "contrast"],
            "anatomy_errors": [], "unexplained_objects": [],
            "ambiguous_connectors": [], "salience_failures": [],
            "redundant_sections": [], "typography_issues": [],
            "entity_specificity_issues": [], "visual_clutter": [],
            "anatomical_context_losses": [], "identity_drift": [],
            "uncertainty_ambiguities": [], "quantitative_annotation_issues": [],
            "layout_balance_issues": [], "callout_backing_issues": [],
            "font_consistency_issues": [], "composite_integration_issues": [],
            "paper_integrity_issues": [], "representation_issues": [],
            "visual_language_issues": [], "stock_asset_issues": [],
            "typography_dominance_issues": [], "visual_explanation_issues": [],
        }
        inspection = {
            "ocr_text": " ".join(qa_figure.expected_pixel_text(selected_spec)),
            "minimum_label_height_px": 32,
            "relationships": [], "detected_effects": [], "text_collisions": [],
            "duplicate_text": [], "unlisted_text": [], "geometry_distortions": [],
            "visual_quality": {key: "pass" for key in qa_figure.V3_VISUAL_QUALITY_DIMENSIONS},
            "typography_scale": {
                "p90_label_height_px": 32,
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
                "minimum_primary_label_height_px": 34,
                "readable_primary_labels": [
                    "Follow-up time", "Change from shared start (%)"],
                "observed_first_glance_path": [
                    "Find shared start", "Follow both paths", "Read contrast"],
                "observed_explain_back": "The groups began together and ended apart.",
                "explain_back_matches": True,
                "primary_labels_require_zoom": False,
                "supporting_labels_inflated_for_phone": False,
            },
            "annotation": {"panel_labels": [], "callouts": []},
            "integrity": integrity,
            "quantitative": {
                "axis_semantics_visible": False,
                "numeric_annotations_attached_to_referents": True,
                "uncertainty_attached_to_estimate": False,
                "uncertainty_graphically_visible": False,
                "data_marks_visually_primary": True,
                "annotations_clear_of_marks": True,
                "y_axis_label_vertical": True,
                "redundant_legend_absent": True,
                "full_composition_balanced": True,
            },
        }
        asset = str(image)
        provenance = {
            "schema_version": 2, "generator_available": False,
            "selected_route": "deterministic", "selected_asset": asset,
            "selected_sha256": sha256_file(image),
            "attempts": [{"kind": "render", "asset": asset,
                           "tool": "render_quantitative_figure.py"}],
            "comparison": {"candidates_compared": 1,
                           "selection_rationale": "The verified render was inspected."},
            "post_generation_reviews": [{
                "asset": asset, "intended_takeaway": goal["reader_takeaway"],
                "observed_takeaway": goal["reader_takeaway"],
                "observed_explain_back": goal["plain_language_explain_back"],
                "intended_meaning_conveyed": True, "information_flow_clear": True,
                "intuitive_without_caption": True, "unexplained_jargon": [],
                "issues": [], "decision": "accept",
            }],
        }
        report = qa_figure.audit_figure(
            selected_spec, image, inspection=inspection, provenance=provenance)
        self.assertTrue(any("plotted dimension" in error for error in report["errors"]))
        self.assertTrue(any("reported interval" in error for error in report["errors"]))

    def test_renderer_supports_sequential_ab_panels(self):
        spec = self.spec()
        first = spec["data"]["panels"][0]
        contrast_text = first["contrasts"][0]["label"]
        first["contrasts"] = []
        spec["exact_text"].remove(contrast_text)
        first["panel_label"] = "A"
        second = copy.deepcopy(first)
        second["id"] = "second"
        second["panel_label"] = "B"
        spec["data"]["panels"].append(second)
        spec["plot_design"]["render"]["columns"] = 2
        spec["plot_design"]["render"]["width_px"] = 1600
        spec["plot_design"]["render"]["height_px"] = 800
        spec["plot_design"]["render"]["plot_insets_px"]["right"] = 220
        spec["exact_text"].extend(["A", "B"])
        selected_spec, image, _geometry, manifest = self.render_case(spec)
        report = qa_quantitative_geometry.audit_geometry(
            selected_spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(
            [panel["panel_label"] for panel in manifest["panels"]], ["A", "B"])

    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract is unavailable")
    def test_real_render_clears_the_full_v2_figure_qa_type_gate(self):
        spec, image, _geometry, _manifest = self.render_case()
        _machine_text, measured_height = qa_figure._tesseract(image)
        self.assertIsNotNone(measured_height)
        expected_copy = qa_figure.expected_pixel_text(spec)
        goal = spec["communication_goal"]
        inspection = {
            "ocr_text": " ".join(expected_copy),
            "minimum_label_height_px": measured_height,
            "relationships": [],
            "detected_effects": [],
            "text_collisions": [],
            "duplicate_text": [],
            "unlisted_text": [],
            "geometry_distortions": [],
            "visual_quality": {
                "composition": "pass",
                "hierarchy": "pass",
                "domain_specificity": "pass",
                "style_fit": "pass",
                "polish": "pass",
                "explanatory_value": "pass",
                "information_flow": "pass",
                "intuitiveness": "pass",
            },
            "communication": {
                "observed_takeaway": goal["reader_takeaway"],
                "observed_explain_back": goal["plain_language_explain_back"],
                "explain_back_matches": True,
                "intuitive_without_caption": True,
                "familiar_starting_point_visible": True,
                "requires_caption_to_understand": False,
                "unexplained_jargon": [],
                "intended_takeaway_conveyed": True,
                "information_flow_clear": True,
                "must_show_visible": goal["must_show"],
                "observed_information_flow": goal["information_flow"],
                "misleading_or_ambiguous": [],
                "revision_needed": False,
            },
            "annotation": {"panel_labels": [], "callouts": []},
        }
        asset = str(image)
        provenance = {
            "schema_version": 2,
            "generator_available": False,
            "selected_route": "deterministic",
            "selected_asset": asset,
            "selected_sha256": sha256_file(image),
            "attempts": [{
                "kind": "render",
                "asset": asset,
                "tool": "render_quantitative_figure.py",
            }],
            "post_generation_reviews": [{
                "asset": asset,
                "intended_takeaway": goal["reader_takeaway"],
                "observed_takeaway": goal["reader_takeaway"],
                "observed_explain_back": goal["plain_language_explain_back"],
                "intended_meaning_conveyed": True,
                "information_flow_clear": True,
                "intuitive_without_caption": True,
                "unexplained_jargon": [],
                "issues": [],
                "decision": "accept",
            }],
        }
        report = qa_figure.audit_figure(
            spec, image, inspection=inspection, provenance=provenance)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertGreaterEqual(
            report["metrics"]["minimum_effective_label_pt"], 7.0)

    def test_geometry_qa_detects_manifest_coordinate_tampering(self):
        spec, image, _geometry, manifest = self.render_case()
        tampered = copy.deepcopy(manifest)
        tampered["panels"][0]["points"][1]["y_px"] += 24
        report = qa_quantitative_geometry.audit_geometry(spec, image, tampered)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("intervention/end y_px" in error for error in report["errors"]))

    def test_geometry_qa_detects_reported_text_collision(self):
        spec, image, _geometry, manifest = self.render_case()
        tampered = copy.deepcopy(manifest)
        first = tampered["text_layout"][0]
        second = next(
            record for record in tampered["text_layout"][1:]
            if record["panel_id"] == first["panel_id"])
        second["bbox_px"] = copy.deepcopy(first["bbox_px"])
        report = qa_quantitative_geometry.audit_geometry(spec, image, tampered)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("text collision" in error for error in report["errors"]))

    def test_v3_geometry_treats_sub_three_pixel_mobile_text_gap_as_collision(self):
        geometry = {
            "text_layout": [
                {"panel_id": "main", "text": "A", "bbox_px": {
                    "left": 20, "top": 20, "right": 60, "bottom": 60}},
                {"panel_id": "main", "text": "Axis", "bbox_px": {
                    "left": 20, "top": 66, "right": 100, "bottom": 106}},
            ],
            "rendered_text": ["A", "Axis"],
        }
        errors = []
        count = qa_quantitative_geometry._audit_text_layout(
            geometry,
            {"main": {"left": 0, "right": 1200, "top": 0, "bottom": 600}},
            (1200, 600), errors, quality_contract_version=3)
        self.assertEqual(count, 2)
        self.assertTrue(any("sub-3px mobile clearance" in error for error in errors))

    def test_geometry_qa_probes_the_real_raster_not_only_the_manifest(self):
        from PIL import Image, ImageDraw

        spec, image_path, _geometry, manifest = self.render_case()
        endpoint = next(
            point for point in manifest["panels"][0]["points"]
            if point["series_id"] == "intervention" and point["point_id"] == "end"
        )
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        draw = ImageDraw.Draw(image)
        x, y = round(endpoint["x_px"]), round(endpoint["y_px"])
        draw.rectangle((x - 40, y - 40, x + 40, y + 40), fill="#FFFFFF")
        image.save(image_path)
        tamper_consistent_hash = copy.deepcopy(manifest)
        tamper_consistent_hash["image"]["sha256"] = sha256_file(image_path)
        report = qa_quantitative_geometry.audit_geometry(
            spec, image_path, tamper_consistent_hash)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(
            "missing the coloured mark for intervention/end" in error
            for error in report["errors"]
        ))

    def test_renderer_rejects_contrast_not_implied_by_endpoints(self):
        spec = self.spec()
        spec["data"]["panels"][0]["contrasts"][0]["estimate"] = -9.0
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                    render_quantitative_figure.QuantitativeFigureError,
                    "from.y minus to.y"):
                render_quantitative_figure.render(
                    spec, Path(directory) / "figure.png",
                    Path(directory) / "figure.geometry.json")

    def test_renderer_rejects_text_not_declared_in_exact_manifest(self):
        spec = self.spec()
        spec["exact_text"].remove("Assignment")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                    render_quantitative_figure.QuantitativeFigureError,
                    "absent from exact_text"):
                render_quantitative_figure.render(
                    spec, Path(directory) / "figure.png",
                    Path(directory) / "figure.geometry.json")

    def test_renderer_rejects_colliding_direct_labels(self):
        spec = self.spec()
        for series in spec["data"]["panels"][0]["series"]:
            series["label_point_id"] = "start"
            series["label_position"] = "right"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                    render_quantitative_figure.QuantitativeFigureError,
                    "text collision"):
                render_quantitative_figure.render(
                    spec, Path(directory) / "figure.png",
                    Path(directory) / "figure.geometry.json")

    def test_renderer_rejects_a_direct_label_outside_its_panel(self):
        spec = self.spec()
        series = spec["data"]["panels"][0]["series"][1]
        old_label = series["label"]
        series["label"] = (
            "A deliberately overlong direct label that cannot fit in the panel gutter")
        spec["exact_text"][spec["exact_text"].index(old_label)] = series["label"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                    render_quantitative_figure.QuantitativeFigureError,
                    "does not fit inside panel"):
                render_quantitative_figure.render(
                    spec, Path(directory) / "figure.png",
                    Path(directory) / "figure.geometry.json")

    def test_geometry_qa_rejects_manifest_from_a_changed_spec(self):
        spec, image, _geometry, manifest = self.render_case()
        changed = copy.deepcopy(spec)
        changed["data"]["panels"][0]["series"][0]["points"][1]["y"] = -5.8
        changed["data"]["panels"][0]["contrasts"][0]["estimate"] = -9.9
        report = qa_quantitative_geometry.audit_geometry(changed, image, manifest)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("exact figure spec" in error for error in report["errors"]))

    def v3_layout(self, spec, primary):
        spec["quality_contract_version"] = 3
        spec["layout_plan"] = {
            "content_density": "moderate",
            "wide_canvas_required": False,
            "aspect_ratio_rationale": "A compact landscape fits the comparison.",
            "balance_strategy": "Marks and labels balance around the plot centre.",
            "final_display": "Single-column article figure at final report width.",
            "mobile_preview": {
                "width_px": 390,
                "minimum_primary_label_height_px": 10,
                "all_labels_required_without_zoom": False,
                "primary_labels": list(primary),
                "first_glance_path": ["Start", "Paths", "Gap"],
                "supporting_detail_strategy": "Ticks stay publication-sized.",
                "explain_back_without_zoom": "The groups began together and ended apart.",
            },
        }
        spec["plot_design"]["typography"] = {
            "family": "Helvetica Neue", "fallback": "Arial",
            "upright_natural_width": True,
        }
        return spec

    def test_primary_label_never_drawn_fails_closed(self):
        spec = self.v3_layout(self.make_phone_readable(self.spec()), ["Nowhere"])
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError,
                "primary label was not rendered"):
            self.render_case(spec)

    def test_tick_labels_are_never_primary(self):
        spec = self.v3_layout(self.make_phone_readable(self.spec()), ["Start"])
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError,
                "tick labels are never primary"):
            self.render_case(spec)

    def test_scaffold_placeholders_cannot_render(self):
        spec = self.spec()
        spec["purpose"] = "<<FILL: purpose>>"
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError, "placeholder"):
            self.render_case(spec)

    @staticmethod
    def dot_plot_spec(*, use_sugar):
        spec = DeterministicQuantitativeFigureTests.spec()
        spec["target_aspect_ratio"] = 1.6
        spec["plot_design"]["render"].update({"width_px": 1600, "height_px": 1000})
        names = ["Trial one", "Trial two", "Cohort"]
        values = [(0.86, [0.72, 1.02]), (0.91, [0.78, 1.06]), (0.97, [0.80, 1.17])]
        colours = ["#3B7C85", "#3B6F9C", "#C86F55"]
        panel = {
            "id": "main",
            "y_axis": {
                "label": "Risk ratio", "domain": [0.55, 1.3],
                "ticks": [{"value": 0.6, "label": "0.6"}, {"value": 1.0, "label": "1.0"},
                          {"value": 1.2, "label": "1.2"}],
            },
            "reference_lines": [
                {"id": "no-difference", "axis": "y", "value": 1.0, "label": "No difference"}],
            "events": [], "contrasts": [],
        }
        if use_sugar:
            panel["x_axis"] = {"label": "Evidence source", "categories": names}
            panel["rows"] = [
                {"id": f"row-{index}", "value": value, "interval": interval,
                 "label": f"{value:.2f}", "label_position": "right", "color": colour}
                for index, ((value, interval), colour) in enumerate(
                    zip(values, colours), start=1)]
        else:
            panel["x_axis"] = {
                "label": "Evidence source", "domain": [0.5, 3.5],
                "ticks": [{"value": index, "label": name}
                          for index, name in enumerate(names, start=1)]}
            panel["series"] = [
                {"id": f"row-{index}", "label": None, "color": colour,
                 "points": [{"id": "estimate", "x": index, "y": value,
                             "y_interval": interval, "label": f"{value:.2f}",
                             "label_position": "right"}]}
                for index, ((value, interval), colour) in enumerate(
                    zip(values, colours), start=1)]
        spec["data"]["panels"] = [panel]
        spec["exact_text"] = [
            spec["title"], "Evidence source", "Risk ratio", *names,
            "0.6", "1.0", "1.2", "No difference", "0.86", "0.91", "0.97"]
        return spec

    def test_categories_and_rows_expand_to_the_explicit_form(self):
        sugar = self.dot_plot_spec(use_sugar=True)
        explicit = self.dot_plot_spec(use_sugar=False)
        _s, sugar_image, _g, sugar_manifest = self.render_case(sugar)
        _e, explicit_image, _g2, explicit_manifest = self.render_case(explicit)
        self.assertEqual(sugar_manifest["panels"][0]["points"],
                         explicit_manifest["panels"][0]["points"])
        self.assertEqual(sugar_manifest["panels"][0]["x_axis"]["ticks"],
                         explicit_manifest["panels"][0]["x_axis"]["ticks"])
        self.assertEqual(sugar_manifest["image"]["sha256"],
                         explicit_manifest["image"]["sha256"])
        report = qa_quantitative_geometry.audit_geometry(sugar, sugar_image, sugar_manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    def test_rows_require_a_categorical_axis_of_matching_length(self):
        spec = self.dot_plot_spec(use_sugar=True)
        spec["data"]["panels"][0]["x_axis"]["categories"].append("Extra")
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError, "one row per category"):
            self.render_case(spec)

    def test_horizontal_forest_rows_use_x_intervals(self):
        spec = self.dot_plot_spec(use_sugar=True)
        panel = spec["data"]["panels"][0]
        panel["y_axis"], panel["x_axis"] = (
            {"label": "Evidence source", "categories": panel["x_axis"]["categories"]},
            {"label": "Risk ratio", "domain": [0.55, 1.3],
             "ticks": panel["y_axis"]["ticks"]})
        panel["reference_lines"][0]["axis"] = "x"
        for row in panel["rows"]:
            row["label_position"] = "above"
        # Category names on the y-axis need a wider left gutter than the
        # v2 fixture declares; the renderer fails closed without it.
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError,
                "y_tick text does not fit"):
            self.render_case(copy.deepcopy(spec))
        spec["plot_design"]["render"]["plot_insets_px"]["left"] = 220
        _s, image, _g, manifest = self.render_case(spec)
        intervals = manifest["panels"][0]["intervals"]
        self.assertEqual({item["axis"] for item in intervals}, {"x"})
        report = qa_quantitative_geometry.audit_geometry(spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    def test_auto_layout_widens_a_gutter_for_clipped_category_ticks(self):
        spec = self.dot_plot_spec(use_sugar=True)
        panel = spec["data"]["panels"][0]
        panel["y_axis"], panel["x_axis"] = (
            {"label": "Evidence source", "categories": panel["x_axis"]["categories"]},
            {"label": "Risk ratio", "domain": [0.55, 1.3],
             "ticks": panel["y_axis"]["ticks"]})
        panel["reference_lines"][0]["axis"] = "x"
        for row in panel["rows"]:
            row["label_position"] = "above"
        spec["plot_design"]["render"]["auto_layout"] = True
        selected_spec, image, _g, manifest = self.render_case(spec)
        resolved = manifest["resolved_layout"]
        self.assertTrue(resolved["auto_layout"])
        self.assertGreater(resolved["plot_insets_px"].get("left", 0), 140)
        self.assertEqual(resolved["label_positions"], [])
        report = qa_quantitative_geometry.audit_geometry(selected_spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    def test_annotation_with_leader_renders_and_audits(self):
        spec = self.v3_layout(self.dot_plot_spec(use_sugar=True), ["All intervals cross 1.0"])
        panel = spec["data"]["panels"][0]
        panel["annotations"] = [{
            "id": "takeaway", "text": "All intervals cross 1.0", "x": 0.6, "y": 1.29,
            "align": "left", "leader_to": {"series_id": "row-1", "point_id": "estimate"},
        }]
        spec["exact_text"].append("All intervals cross 1.0")
        _s, image, _g, manifest = self.render_case(spec)
        annotations = manifest["panels"][0]["annotations"]
        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0]["leader_to"], {"series_id": "row-1", "point_id": "estimate"})
        self.assertTrue(any(item["role"] == "annotation" for item in manifest["text_layout"]))
        resolved = {item["text"]: item for item in manifest["primary_labels_resolved"]}
        self.assertGreaterEqual(resolved["All intervals cross 1.0"]["mobile_height_px"], 10.0)
        report = qa_quantitative_geometry.audit_geometry(spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    def test_reference_label_moves_off_a_whisker(self):
        spec = self.dot_plot_spec(use_sugar=True)
        _s, _image, _g, manifest = self.render_case(spec)
        reference = manifest["panels"][0]["reference_lines"][0]
        # The right-hand whisker reaches above the line, so the label moves.
        self.assertNotEqual(reference["label_side"], "right")
        label_box = next(
            item["bbox_px"] for item in manifest["text_layout"]
            if item["role"] == "reference_label")
        for point in manifest["panels"][0]["points"]:
            self.assertFalse(
                label_box["left"] - 4 < point["x_px"] < label_box["right"] + 4
                and label_box["top"] - 4 < point["y_px"] < label_box["bottom"] + 4)
        clear = self.dot_plot_spec(use_sugar=True)
        for row in clear["data"]["panels"][0]["rows"]:
            row["interval"] = [row["value"] - 0.05, row["value"] + 0.02]
        _s, _image, _g, clear_manifest = self.render_case(clear)
        self.assertEqual(
            clear_manifest["panels"][0]["reference_lines"][0]["label_side"], "right")

    def test_annotation_leader_must_reference_an_existing_point(self):
        spec = self.dot_plot_spec(use_sugar=True)
        spec["data"]["panels"][0]["annotations"] = [{
            "id": "takeaway", "text": "Note", "x": 1, "y": 1.2,
            "align": "left", "leader_to": {"series_id": "missing", "point_id": "estimate"},
        }]
        spec["exact_text"].append("Note")
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError, "existing point"):
            self.render_case(spec)

    def test_auto_layout_resolves_colliding_direct_labels(self):
        spec = self.spec()
        for series in spec["data"]["panels"][0]["series"]:
            series["label_point_id"] = "start"
            series["label_position"] = "right"
        spec["plot_design"]["render"]["auto_layout"] = True
        selected_spec, image, _g, manifest = self.render_case(spec)
        resolved = manifest["resolved_layout"]
        self.assertTrue(resolved["auto_layout"])
        self.assertGreater(resolved["attempts"], 1)
        moved = {(item["kind"], item["id"]): item["position"]
                 for item in resolved["label_positions"]}
        self.assertTrue(moved)
        self.assertTrue(all(position != "right" for position in moved.values()))
        report = qa_quantitative_geometry.audit_geometry(selected_spec, image, manifest)
        self.assertEqual(report["status"], "pass", report["errors"])

    def test_auto_layout_off_still_fails_closed(self):
        spec = self.spec()
        for series in spec["data"]["panels"][0]["series"]:
            series["label_point_id"] = "start"
            series["label_position"] = "right"
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError, "text collision"):
            self.render_case(spec)

    def test_geometry_qa_accepts_a_resolved_width_only_when_the_spec_opted_in(self):
        spec = self.spec()
        spec["plot_design"]["render"]["auto_layout"] = True
        geometry = {"resolved_layout": {"auto_layout": True, "width_px": 1536,
                                        "height_px": 768}}
        errors = []
        adjusted = qa_quantitative_geometry._apply_resolved_layout(spec, geometry, errors)
        self.assertEqual(errors, [])
        self.assertEqual(adjusted["plot_design"]["render"]["width_px"], 1536)
        spec["plot_design"]["render"]["auto_layout"] = False
        errors = []
        unchanged = qa_quantitative_geometry._apply_resolved_layout(spec, geometry, errors)
        self.assertEqual(unchanged["plot_design"]["render"]["width_px"], 1200)
        self.assertTrue(any("did not opt in" in error for error in errors))

    def test_empty_label_is_rejected_but_null_is_allowed(self):
        spec = self.spec()
        spec["data"]["panels"][0]["series"][0]["label"] = None
        spec["exact_text"].remove("Intervention")
        self.render_case(spec)
        spec["data"]["panels"][0]["series"][0]["label"] = ""
        with self.assertRaisesRegex(
                render_quantitative_figure.QuantitativeFigureError, "non-empty string"):
            self.render_case(spec)


if __name__ == "__main__":
    unittest.main()
