import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import qa_figure  # noqa: E402
from artifact_io import sha256_file  # noqa: E402


class FigureQaTests(unittest.TestCase):
    @staticmethod
    def spec():
        return {
            "title": "Caption title",
            "render_context": "article",
            "exact_text": [
                "Caption title", "Exposure", "Response", "CI = confidence interval"
            ],
            "abbreviations": {"CI": "confidence interval"},
            "relationships": [{
                "from": "Exposure", "relation": "increases", "to": "Response"
            }],
            "avoid": ["gradient", "drop shadow"],
        }

    @staticmethod
    def inspection():
        return {
            "ocr_text": "Exposure Response CI = confidence interval",
            "minimum_label_height_px": 28,
            "relationships": [{
                "from": "Exposure", "relation": "increases", "to": "Response"
            }],
            "detected_effects": [],
            "text_collisions": [],
        }

    def run_audit(self, inspection=None, spec=None):
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            canvas = Image.new("RGB", (1536, 1024), "white")
            draw = ImageDraw.Draw(canvas)
            draw.ellipse((120, 180, 620, 680), fill="#D3E5EF", outline="#1A1A1A", width=8)
            draw.rectangle((900, 260, 1360, 620), fill="#D7E6DD", outline="#1A1A1A", width=8)
            draw.line((620, 430, 900, 430), fill="#D28A67", width=18)
            canvas.save(image)
            return qa_figure.audit_figure(
                spec or self.spec(), image,
                inspection=inspection or self.inspection(),
            )

    def test_conformant_figure_passes(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_missing_expected_text_is_detected(self):
        inspection = self.inspection()
        inspection["ocr_text"] = "Exposure CI = confidence interval"
        result = self.run_audit(inspection)
        self.assertTrue(any("missing expected text: Response" in error for error in result["errors"]))

    def test_unexpanded_abbreviation_is_detected(self):
        inspection = self.inspection()
        inspection["ocr_text"] = "Exposure Response CI"
        result = self.run_audit(inspection)
        self.assertTrue(any("unexpanded" in error for error in result["errors"]))

    def test_prohibited_gradient_and_small_labels_are_separate_failures(self):
        inspection = self.inspection()
        inspection["detected_effects"] = ["gradient"]
        inspection["minimum_label_height_px"] = 8
        result = self.run_audit(inspection)
        self.assertTrue(any("gradient" in error for error in result["errors"]))
        self.assertTrue(any("effective label" in error for error in result["errors"]))

    def test_reversed_arrow_is_detected(self):
        inspection = self.inspection()
        inspection["relationships"] = [{
            "from": "Response", "relation": "increases", "to": "Exposure"
        }]
        result = self.run_audit(inspection)
        self.assertTrue(any("reversed relationship" in error for error in result["errors"]))

    def test_blank_pixels_fail_even_when_manual_transcript_claims_content(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "blank.png"
            Image.new("RGB", (1536, 1024), "white").save(image)
            result = qa_figure.audit_figure(
                self.spec(), image, inspection=self.inspection())
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("blank or near-blank" in error for error in result["errors"]))

    def test_transparent_noise_cannot_fake_nonblank_content(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "transparent.png"
            # Hidden RGB variation is fully transparent and therefore invisible
            # on the white PDF page.
            canvas = Image.new("RGBA", (1536, 1024), (0, 0, 0, 0))
            for x in range(0, 1536, 32):
                canvas.putpixel((x, 100), (x % 255, 20, 200, 0))
            canvas.save(image)
            result = qa_figure.audit_figure(
                self.spec(), image, inspection=self.inspection())
        self.assertTrue(any("blank or near-blank" in error for error in result["errors"]))


class QualityContractTests(unittest.TestCase):
    @staticmethod
    def spec():
        return {
            "quality_contract_version": 1,
            "review_style": "popsci",
            "render_route": "generated",
            "archetype": "mechanism",
            "target_aspect_ratio": 2.0,
            "render_context": "article",
            "title": "Caption only",
            "exact_text": ["Caption only", "Signal", "Response"],
            "relationships": [{
                "from": "Signal", "relation": "increases", "to": "Response"
            }],
            "avoid": [],
        }

    @staticmethod
    def inspection():
        return {
            "ocr_text": "Signal Response",
            "minimum_label_height_px": 32,
            "relationships": [{
                "from": "Signal", "relation": "increases", "to": "Response"
            }],
            "detected_effects": [],
            "text_collisions": [],
            "geometry_distortions": [],
            "duplicate_text": [],
            "unlisted_text": [],
            "visual_quality": {
                "composition": "pass",
                "hierarchy": "pass",
                "domain_specificity": "pass",
                "style_fit": "pass",
                "polish": "pass",
            },
        }

    @staticmethod
    def make_image(path, size=(1600, 800)):
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB", size, "#FBFAF6")
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((100, 120, 620, 640), fill="#7399A9")
        draw.polygon([(760, 400), (1120, 130), (1500, 400), (1120, 670)], fill="#C77A5A")
        canvas.save(path)

    @staticmethod
    def provenance(path):
        return {
            "schema_version": 1,
            "generator_available": True,
            "generator": {"tool": "built-in-imagegen", "supports_edit": True},
            "selected_route": "generated",
            "selected_asset": Path(path).name,
            "selected_sha256": sha256_file(path),
            "attempts": [
                {
                    "kind": "generate",
                    "asset": Path(path).name,
                    "text_mode": "direct",
                    "outcome": "selected",
                    "reason": "first candidate passed all quality gates",
                },
            ],
            "comparison": {
                "candidates_compared": 1,
                "selection_rationale": "The first candidate passed all quality gates.",
            },
            "fallback_reason": None,
            "hybrid_considered": False,
        }

    def audit(self, *, size=(1600, 800), spec=None, inspection=None,
              mutate_provenance=None):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            self.make_image(image, size)
            provenance = self.provenance(image)
            if mutate_provenance:
                mutate_provenance(provenance)
            return qa_figure.audit_figure(
                spec or self.spec(), image,
                inspection=inspection or self.inspection(),
                provenance=provenance,
            )

    def test_complete_contract_passes(self):
        result = self.audit()
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["metrics"]["aspect_ratio_relative_error"], 0.0)

    def test_stretched_raster_is_release_blocking(self):
        result = self.audit(size=(1600, 900))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("stretching is forbidden" in error for error in result["errors"]))

    def test_cheap_visual_verdict_is_release_blocking(self):
        inspection = self.inspection()
        inspection["visual_quality"]["polish"] = "cheap"
        result = self.audit(inspection=inspection)
        self.assertTrue(any("visual quality polish must pass" in error for error in result["errors"]))

    def test_duplicate_and_unlisted_text_are_release_blocking(self):
        inspection = self.inspection()
        inspection["duplicate_text"] = ["Signal"]
        inspection["unlisted_text"] = ["mystery label"]
        result = self.audit(inspection=inspection)
        self.assertTrue(any(
            "duplicated rendered text: Signal" in error for error in result["errors"]))
        self.assertTrue(any(
            "unlisted rendered text: mystery label" in error
            for error in result["errors"]))

    def test_single_passing_generated_candidate_is_releasable(self):
        result = self.audit()
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_multiple_candidates_require_a_real_comparison(self):
        def mutate(provenance):
            provenance["attempts"].append({
                "kind": "generate", "asset": "alternate.png",
                "text_mode": "direct", "outcome": "rejected",
            })
            provenance["comparison"]["candidates_compared"] = 1

        result = self.audit(mutate_provenance=mutate)
        self.assertTrue(any(
            "multiple candidates requires comparison of at least two" in error
            for error in result["errors"]))

    def test_comparison_cannot_claim_unrecorded_candidates(self):
        def mutate(provenance):
            provenance["comparison"]["candidates_compared"] = 2

        result = self.audit(mutate_provenance=mutate)
        self.assertTrue(any(
            "exceeds recorded generated candidates" in error
            for error in result["errors"]))

    def test_hybrid_is_a_documented_last_resort(self):
        spec = self.spec()
        spec["render_route"] = "hybrid"

        def mutate(provenance):
            provenance["selected_route"] = "hybrid"
            provenance["attempts"].extend([
                {
                    "kind": "edit", "asset": "direct-text-edit.png",
                    "outcome": "rejected", "reason": "several labels still wrong",
                },
                {"kind": "compose", "asset": "figure.png", "outcome": "selected"},
            ])
            provenance["direct_text_attempted"] = True
            provenance["fallback_reason"] = (
                "Direct-text generation and one targeted edit left three exact labels wrong.")
            provenance["hybrid_considered"] = True
            provenance["hybrid"] = {
                "compositor": "compose_hybrid_figure.py",
                "base_asset": "direct-text-edit.png",
                "anisotropic_resize": False,
            }

        result = self.audit(spec=spec, mutate_provenance=mutate)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_hybrid_without_direct_text_attempt_fails(self):
        spec = self.spec()
        spec["render_route"] = "hybrid"

        def mutate(provenance):
            provenance["selected_route"] = "hybrid"
            provenance["attempts"].append(
                {"kind": "compose", "asset": "figure.png"})
            provenance["hybrid"] = {
                "compositor": "compose_hybrid_figure.py",
                "base_asset": "candidate.png",
                "anisotropic_resize": False,
            }

        result = self.audit(spec=spec, mutate_provenance=mutate)
        self.assertTrue(any(
            "direct_text_attempted=true" in error for error in result["errors"]))
        self.assertTrue(any(
            "concrete fallback_reason" in error for error in result["errors"]))


class CommunicationFirstContractTests(unittest.TestCase):
    @staticmethod
    def spec():
        return {
            "quality_contract_version": 2,
            "review_style": "scientific",
            "render_route": "generated",
            "archetype": "mechanism",
            "target_aspect_ratio": 2.0,
            "visual_anchor": "A domain-specific structure linking signal to response",
            "render_context": "article",
            "title": "Caption only",
            "exact_text": ["Caption only", "A", "Signal"],
            "relationships": [],
            "avoid": [],
            "communication_goal": {
                "reader_takeaway": "The signal reaches the response through one visible pathway.",
                "must_show": ["signal", "pathway", "response"],
                "information_flow": ["Find signal", "Follow pathway", "Reach response"],
                "evidence_boundary": "Direction only; no magnitude is implied.",
                "familiar_starting_point": "A visible path from a signal to a response.",
                "plain_language_explain_back": "The signal follows one pathway to reach the response.",
            },
            "concepts": [
                {"id": "path", "description": "One continuous domain-native pathway.",
                 "information_flow": ["signal", "path", "response"],
                 "strengths": ["Clear"], "risks": ["Could oversimplify"]},
                {"id": "pair", "description": "Two aligned states with a connector.",
                 "information_flow": ["compare", "connect"],
                 "strengths": ["Simple"], "risks": ["Static"]},
                {"id": "cutaway", "description": "A cutaway showing the pathway internally.",
                 "information_flow": ["whole", "inside"],
                 "strengths": ["Complete"], "risks": ["Dense"]},
            ],
            "concept_selection": {
                "selected_id": "path",
                "selection_rationale": "The clearest complete and elegant option.",
                "evaluations": [
                    {"id": "path", "clarity": 5, "simplicity": 5,
                     "completeness": 4, "elegance": 5, "intuitiveness": 5,
                     "assessment": "Best."},
                    {"id": "pair", "clarity": 4, "simplicity": 5,
                     "completeness": 3, "elegance": 4, "intuitiveness": 4,
                     "assessment": "Too static."},
                    {"id": "cutaway", "clarity": 3, "simplicity": 2,
                     "completeness": 5, "elegance": 5, "intuitiveness": 3,
                     "assessment": "Too dense."},
                ],
            },
            "annotation_plan": {
                "panel_labels": ["A"],
                "callouts": [],
                "rationale": "One named section supports precise discussion; the local label is adjacent.",
            },
        }

    @staticmethod
    def inspection():
        return {
            "ocr_text": "A Signal",
            "minimum_label_height_px": 32,
            "relationships": [],
            "detected_effects": [],
            "text_collisions": [],
            "geometry_distortions": [],
            "duplicate_text": [],
            "unlisted_text": [],
            "visual_quality": {
                "composition": "pass", "hierarchy": "pass",
                "domain_specificity": "pass", "style_fit": "pass",
                "polish": "pass", "explanatory_value": "pass",
                "information_flow": "pass", "intuitiveness": "pass",
            },
            "communication": {
                "observed_takeaway": "A signal visibly reaches a response through a pathway.",
                "observed_explain_back": "The signal follows one pathway to reach the response.",
                "explain_back_matches": True,
                "intuitive_without_caption": True,
                "familiar_starting_point_visible": True,
                "requires_caption_to_understand": False,
                "unexplained_jargon": [],
                "intended_takeaway_conveyed": True,
                "information_flow_clear": True,
                "must_show_visible": ["signal", "pathway", "response"],
                "observed_information_flow": ["signal", "pathway", "response"],
                "misleading_or_ambiguous": [],
                "revision_needed": False,
            },
            "annotation": {"panel_labels": ["A"], "callouts": []},
        }

    @staticmethod
    def make_image(path):
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB", (1600, 800), "white")
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((120, 150, 620, 650), fill="#7399A9")
        draw.line((620, 400, 1000, 400), fill="#1A1A1A", width=14)
        draw.rectangle((1000, 200, 1480, 600), fill="#C77A5A")
        canvas.save(path)

    def provenance(self, image, *, first_pass=True, spec=None):
        spec = spec or self.spec()
        selected = Path(image).name
        attempts = [{
            "kind": "generate", "asset": selected,
            "text_mode": "direct", "outcome": "selected",
            "reason": "Meaning and information flow passed on first inspection.",
        }]
        reviews = [{
            "asset": selected,
            "intended_takeaway": spec["communication_goal"]["reader_takeaway"],
            "observed_takeaway": "A signal visibly reaches a response through a pathway.",
            "observed_explain_back": "The signal follows one pathway to reach the response.",
            "intuitive_without_caption": True,
            "unexplained_jargon": [],
            "intended_meaning_conveyed": True,
            "information_flow_clear": True,
            "issues": [],
            "decision": "accept",
        }]
        if not first_pass:
            attempts.insert(0, {
                "kind": "generate", "asset": "candidate-1.png",
                "text_mode": "direct", "outcome": "rejected",
                "reason": "The pathway direction was unclear.",
            })
            reviews.insert(0, {
                "asset": "candidate-1.png",
                "intended_takeaway": spec["communication_goal"]["reader_takeaway"],
                "observed_takeaway": "Two structures are present but their relation is unclear.",
                "observed_explain_back": "Two structures appear, but their relation is unclear.",
                "intuitive_without_caption": False,
                "unexplained_jargon": [],
                "intended_meaning_conveyed": False,
                "information_flow_clear": False,
                "issues": ["No clear path from signal to response"],
                "decision": "regenerate",
            })
        return {
            "schema_version": 2,
            "generator_available": True,
            "generator": {"tool": "built-in-imagegen", "supports_edit": True},
            "selected_route": "generated",
            "selected_asset": selected,
            "selected_sha256": sha256_file(image),
            "attempts": attempts,
            "comparison": {
                "candidates_compared": len([
                    item for item in attempts if item["kind"] == "generate"]),
                "selection_rationale": "The selected candidate communicates the intent most clearly.",
            },
            "post_generation_reviews": reviews,
            "fallback_reason": None,
            "hybrid_considered": False,
        }

    def audit(self, *, spec=None, inspection=None, provenance_mutator=None,
              first_pass=True):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            self.make_image(image)
            spec = spec or self.spec()
            provenance = self.provenance(
                image, first_pass=first_pass, spec=spec)
            if provenance_mutator:
                provenance_mutator(provenance)
            return qa_figure.audit_figure(
                spec, image,
                inspection=inspection or self.inspection(),
                provenance=provenance,
            )

    def v3_spec(self):
        spec = copy.deepcopy(self.spec())
        spec["quality_contract_version"] = 3
        spec["communication_goal"].update({
            "visual_question": "How does the signal reach the response?",
            "panel_thesis": "The one section shows the complete signal-to-response path.",
        })
        spec["layout_plan"] = {
            "content_density": "sparse",
            "wide_canvas_required": True,
            "aspect_ratio_rationale": (
                "A compact canvas fits one relationship without empty side gutters."
            ),
            "balance_strategy": (
                "The two primary entities share the optical centre and visual weight."
            ),
            "final_display": "Single-column article figure at final report width.",
            "mobile_preview": {
                "width_px": 390,
                "minimum_label_height_px": 12,
                "primary_labels": ["A", "Signal"],
                "first_glance_path": ["Find signal", "Follow pathway", "Reach response"],
                "explain_back_without_zoom": "The signal follows one pathway.",
            },
        }
        spec["semantic_plan"] = {
            "entities": [
                {"id": "signal", "depiction": "one specific signal structure",
                 "role": "starting entity", "evidence_basis": "supported input"},
                {"id": "response", "depiction": "one specific response structure",
                 "role": "resulting entity", "evidence_basis": "supported output"},
            ],
            "connectors": [{
                "from": "signal", "to": "response", "meaning": "causal",
                "label": "activates",
            }],
            "panel_jobs": [{
                "label": "A", "job": "show the complete relationship",
                "adds_distinct_information": True,
            }],
            "grouping_rationale": "One relationship belongs in one visual unit.",
            "anatomy_subjects": ["one adult person"],
            "anatomical_context": [{
                "subject": "one adult person",
                "orientation_landmarks": ["head", "torso"],
                "focal_region": "the response region",
                "context_rationale": "The landmarks locate the response on the body.",
            }],
            "salience_targets": ["signal", "response"],
            "information_priority": {
                "primary_entities": ["signal", "response"],
                "supporting_entities": [],
                "excluded_nonessential": ["decorative background props"],
                "dominance_rationale": "The two entities carry the explanation.",
                "deletion_test": "Remove anything that does not change the explain-back sentence.",
            },
            "uncertainty_encodings": [],
            "cross_view_identity": [],
            "representation_plan": {
                "kind": "literal",
                "evidence_native_anchor": "the signal and response structures",
                "cognitive_translation_steps": 0,
                "literal_rejected_reason": None,
                "added_explanatory_value": "The literal path needs no decoding step.",
                "arranged_elements": False,
                "arrangement_evidence_job": None,
            },
            "quantitative_decision": {
                "verified_numbers_available": False,
                "numbers_carry_primary_message": False,
                "reason": "The message is qualitative.",
            },
        }
        return spec

    def v3_inspection(self):
        inspection = copy.deepcopy(self.inspection())
        inspection["minimum_label_height_px"] = 52
        inspection["mobile_preview"] = {
            "width_px": 390,
            "readable_primary_labels": ["A", "Signal"],
            "observed_first_glance_path": ["Find signal", "Follow pathway", "Reach response"],
            "observed_explain_back": "The signal follows one pathway to the response.",
            "explain_back_matches": True,
            "requires_zoom": False,
        }
        inspection["visual_quality"].update({
            "concept_coherence": "pass",
            "anatomical_integrity": "pass",
            "connector_semantics": "pass",
            "logical_grouping": "pass",
            "salience": "pass",
            "nonredundancy": "pass",
            "typography": "pass",
        })
        inspection["integrity"] = {
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
            "avoidable_cognitive_translation_added": False,
            "arranged_object_lineup_present": False,
            "arrangement_encodes_evidence": False,
            "anatomy_checked_at_original_size": True,
            "anatomical_context_sufficient": True,
            "uncertainty_encodings_explanatory": True,
            "cross_view_identity_preserved": [],
            "salience_targets_visible": ["signal", "response"],
            "anatomy_errors": [],
            "unexplained_objects": [],
            "ambiguous_connectors": [],
            "salience_failures": [],
            "redundant_sections": [],
            "typography_issues": [],
            "entity_specificity_issues": [],
            "visual_clutter": [],
            "anatomical_context_losses": [],
            "identity_drift": [],
            "uncertainty_ambiguities": [],
            "quantitative_annotation_issues": [],
            "layout_balance_issues": [],
            "callout_backing_issues": [],
            "font_consistency_issues": [],
            "composite_integration_issues": [],
            "paper_integrity_issues": [],
            "visual_language_issues": [],
            "stock_asset_issues": [],
            "representation_issues": [],
        }
        return inspection

    def test_v3_complete_integrity_contract_passes(self):
        result = self.audit(spec=self.v3_spec(), inspection=self.v3_inspection())
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_extra_or_impossible_body_parts_are_release_blocking(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["anatomy_errors"] = ["extra limb"]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any(
            "anatomical integrity error: extra limb" in error
            for error in result["errors"]))

    def test_v3_ambiguous_connectors_and_unexplained_objects_fail(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["ambiguous_connectors"] = ["arrow has no meaning"]
        inspection["integrity"]["unexplained_objects"] = ["unidentified symbol"]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("ambiguous connector" in error for error in result["errors"]))
        self.assertTrue(any("unexplained visual object" in error for error in result["errors"]))

    def test_v3_generic_entities_fail_even_when_the_layout_is_clean(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["declared_entities_specific"] = False
        inspection["integrity"]["entity_specificity_issues"] = [
            "generic marker label does not identify what changed"
        ]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("specific enough" in error for error in result["errors"]))
        self.assertTrue(any("entity-specificity issue" in error for error in result["errors"]))

    def test_v3_unrelated_or_redundant_panels_fail(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["panels_form_one_explanation"] = False
        inspection["integrity"]["redundant_sections"] = ["last section repeats the prior result"]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("one visual question" in error for error in result["errors"]))
        self.assertTrue(any("redundant visual section" in error for error in result["errors"]))

    def test_v3_meta_title_that_does_not_answer_the_visual_question_fails(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["title_matches_visual_question"] = False
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any(
            "title must name the actual reader-facing subject or finding" in error
            for error in result["errors"]))

    def test_v3_low_salience_and_ugly_typography_fail(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["salience_targets_visible"] = ["signal"]
        inspection["integrity"]["salience_failures"] = ["response disappears into background"]
        inspection["integrity"]["typography_issues"] = ["crowded inconsistent type hierarchy"]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("salience target: response" in error for error in result["errors"]))
        self.assertTrue(any("typography issue" in error for error in result["errors"]))

    def test_v3_clutter_and_lost_anatomical_context_fail(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["nonessential_elements_absent"] = False
        inspection["integrity"]["anatomical_context_sufficient"] = False
        inspection["integrity"]["visual_clutter"] = ["background prop competes with the focal entities"]
        inspection["integrity"]["anatomical_context_losses"] = ["focal region cannot be located"]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("deletion test" in error for error in result["errors"]))
        self.assertTrue(any("orientation landmarks" in error for error in result["errors"]))

    def test_v3_content_fit_and_optical_balance_are_release_blocking(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["aspect_ratio_suits_content"] = False
        inspection["integrity"]["composition_optically_balanced"] = False
        inspection["integrity"]["layout_balance_issues"] = [
            "the sparse message sits in a broad canvas with an empty side gutter"
        ]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("canvas ratio" in error for error in result["errors"]))
        self.assertTrue(any("optically centred" in error for error in result["errors"]))
        self.assertTrue(any("content-fit or optical-balance issue" in error
                            for error in result["errors"]))

    def test_v3_offwhite_canvas_and_phone_scale_are_release_blocking(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            canvas = Image.new("RGB", (1600, 800), "#FBFAF6")
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((200, 200, 1400, 600), fill="#315A70")
            canvas.save(image)
            spec = self.v3_spec()
            inspection = self.v3_inspection()
            inspection["minimum_label_height_px"] = 32
            result = qa_figure.audit_figure(
                spec, image, inspection=inspection,
                provenance=self.provenance(image, spec=spec))
        self.assertTrue(any("not exact #FFFFFF" in error for error in result["errors"]))
        self.assertTrue(any("smallest mobile label" in error for error in result["errors"]))

    def test_v3_every_writing_style_accepts_only_exact_white_paper(self):
        for style in ("scientific", "popsci", "bullets", "eli5"):
            with self.subTest(style=style):
                spec = self.v3_spec()
                spec["review_style"] = style
                result = self.audit(spec=spec, inspection=self.v3_inspection())
                self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_transparency_is_release_blocking_even_if_it_flattens_white(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            canvas = Image.new("RGBA", (1600, 800), (255, 255, 255, 255))
            canvas.putpixel((0, 0), (255, 255, 255, 254))
            draw = ImageDraw.Draw(canvas)
            draw.ellipse((200, 200, 700, 600), fill="#7399A9")
            canvas.save(image)
            spec = self.v3_spec()
            result = qa_figure.audit_figure(
                spec, image, inspection=self.v3_inspection(),
                provenance=self.provenance(image, spec=spec))
        self.assertTrue(any("opaque canvas" in error for error in result["errors"]))

    def test_v3_one_nonwhite_safety_band_pixel_is_release_blocking(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            canvas = Image.new("RGB", (1600, 800), "white")
            canvas.putpixel((0, 0), (254, 254, 254))
            draw = ImageDraw.Draw(canvas)
            draw.ellipse((200, 200, 700, 600), fill="#7399A9")
            canvas.save(image)
            spec = self.v3_spec()
            result = qa_figure.audit_figure(
                spec, image, inspection=self.v3_inspection(),
                provenance=self.provenance(image, spec=spec))
        self.assertTrue(any("not exact #FFFFFF" in error for error in result["errors"]))

    @staticmethod
    def add_callout(spec, *, background="quiet-canvas"):
        spec["exact_text"].append("Local note")
        callout = {
            "text": "Local note",
            "target": "response",
            "leader_line": True,
            "placement_priority": "quiet-canvas-first",
            "background": background,
        }
        if background == "opaque-white":
            callout["quiet_canvas_rejected_reason"] = (
                "Every quiet placement would detach the note from its small target.")
        spec["annotation_plan"]["callouts"] = [callout]
        return spec

    @staticmethod
    def add_observed_callout(inspection, *, background="quiet-canvas"):
        inspection["ocr_text"] += " Local note"
        inspection["annotation"]["callouts"] = [{
            "text": "Local note",
            "target": "response",
            "background": background,
            "quiet_canvas_considered": True,
            "text_on_quiet_canvas": background == "quiet-canvas",
            "opaque_backing_present": background == "opaque-white",
            "backing_necessary": background == "opaque-white",
            "leader_line_present": True,
            "leader_origin_attached_to_label": True,
            "leader_endpoint_hits_target": True,
        }]
        return inspection

    def test_v3_valid_quiet_canvas_callout_passes(self):
        spec = self.add_callout(self.v3_spec())
        inspection = self.add_observed_callout(self.v3_inspection())
        result = self.audit(spec=spec, inspection=inspection)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_callout_must_actually_consider_quiet_canvas(self):
        spec = self.add_callout(self.v3_spec())
        inspection = self.add_observed_callout(self.v3_inspection())
        inspection["annotation"]["callouts"][0]["quiet_canvas_considered"] = False
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any("quiet canvas first" in error for error in result["errors"]))

    def test_v3_opaque_callout_backing_must_be_necessary(self):
        spec = self.add_callout(self.v3_spec(), background="opaque-white")
        inspection = self.add_observed_callout(
            self.v3_inspection(), background="opaque-white")
        inspection["annotation"]["callouts"][0]["backing_necessary"] = False
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any("not justified as necessary" in error
                            for error in result["errors"]))

    def test_v3_unplanned_arranged_object_lineup_fails(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["arranged_object_lineup_present"] = True
        inspection["integrity"]["arrangement_encodes_evidence"] = True
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("unplanned arranged-object lineup" in error
                            for error in result["errors"]))

    def test_v3_arrangement_that_does_not_encode_evidence_fails(self):
        spec = self.v3_spec()
        representation = spec["semantic_plan"]["representation_plan"]
        representation["arranged_elements"] = True
        representation["arrangement_evidence_job"] = (
            "Position shows the supported order of the two states.")
        inspection = self.v3_inspection()
        inspection["integrity"]["arranged_object_lineup_present"] = True
        inspection["integrity"]["arrangement_encodes_evidence"] = False
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any("does not perform a declared evidence job" in error
                            for error in result["errors"]))

    def test_v3_avoidable_representation_translation_fails(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["avoidable_cognitive_translation_added"] = True
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("avoidable cognitive translation" in error
                            for error in result["errors"]))

    def test_v3_mixed_stock_symbol_language_is_release_blocking(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["visual_language_consistent"] = False
        inspection["integrity"]["stock_asset_assemblage_absent"] = False
        inspection["integrity"]["visual_language_issues"] = [
            "primary objects mix glossy three-dimensional symbols with flat line art"
        ]
        inspection["integrity"]["stock_asset_issues"] = [
            "isolated app-style pictograms read as an asset collage"
        ]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("abstraction, dimensionality" in error
                            for error in result["errors"]))
        self.assertTrue(any("glossy stock symbols" in error
                            for error in result["errors"]))
        self.assertTrue(any("visual-language coherence issue" in error
                            for error in result["errors"]))
        self.assertTrue(any("stock-asset assemblage issue" in error
                            for error in result["errors"]))

    def test_v3_justified_metaphor_assistance_can_pass(self):
        spec = self.v3_spec()
        representation = spec["semantic_plan"]["representation_plan"]
        representation.update({
            "kind": "metaphor-assisted",
            "cognitive_translation_steps": 1,
            "literal_rejected_reason": (
                "The literal microscopic structure is not recognizable at report scale."),
            "added_explanatory_value": (
                "One familiar outline orients the literal evidence-native structure."),
        })
        result = self.audit(spec=spec, inspection=self.v3_inspection())
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_callout_backing_and_font_consistency_are_release_blocking(self):
        inspection = self.v3_inspection()
        inspection["integrity"]["callout_backings_legible"] = False
        inspection["integrity"]["font_system_consistent"] = False
        inspection["integrity"]["callout_backing_issues"] = [
            "label crosses a textured visual region without an opaque backing"
        ]
        inspection["integrity"]["font_consistency_issues"] = [
            "two unrelated type families appear in one figure"
        ]
        result = self.audit(spec=self.v3_spec(), inspection=inspection)
        self.assertTrue(any("opaque white backing" in error for error in result["errors"]))
        self.assertTrue(any("house sans-serif" in error for error in result["errors"]))

    def composite_v3_case(self):
        spec = self.v3_spec()
        spec.update({
            "render_route": "composite",
            "archetype": "quantitative",
            "exact_text": ["Caption only", "Category", "Outcome (unit)", "Group", "1.0"],
            "annotation_plan": {
                "panel_labels": [], "callouts": [],
                "rationale": "One integrated panel answers one comparison question.",
            },
            "plot_design": {
                "chart_type": "direct-labelled point and interval",
                "encoding": "Position is the estimate; the whisker is its interval.",
                "reader_path": ["Recognize the orientation asset", "Read the estimate"],
                "style_rationale": "The evidence remains visually primary.",
                "typography": {
                    "family": "Helvetica Neue", "fallback": "Arial",
                    "upright_natural_width": True,
                },
                "axis_semantics": [{
                    "panel_id": "main", "x_label": "Category",
                    "x_meaning": "The x-axis identifies the compared group.",
                    "y_label": "Outcome (unit)",
                    "y_meaning": "The y-axis reports the measured outcome in its unit.",
                }],
                "caption_axis_summary": (
                    "The x-axis identifies the group; the y-axis reports the outcome."
                ),
                "numeric_annotation_attachment": "The value label touches its point.",
                "uncertainty_display": {
                    "present": True, "encoding": "A whisker shows the interval.",
                    "attachment": "The whisker passes through its estimate.",
                },
                "axis_label_placement": {
                    "x_orientation": "horizontal", "x_location": "below-data-region",
                    "y_orientation": "vertical", "y_location": "outside-data-region",
                },
                "legend_plan": {
                    "needed": False,
                    "reason": "The direct-labelled conventional mark needs no key.",
                    "placement": "none",
                },
            },
            "data": {"panels": [{
                "id": "main",
                "x_axis": {"label": "Category", "domain": [0, 2],
                           "ticks": [{"value": 1, "label": "Group"}]},
                "y_axis": {"label": "Outcome (unit)", "domain": [0, 2],
                           "ticks": [{"value": 0, "label": "0"},
                                     {"value": 2, "label": "2"}]},
                "series": [{"id": "group", "label": "Group", "points": [{
                    "id": "estimate", "x": 1, "y": 1.0,
                    "y_interval": [0.8, 1.2], "label": "1.0",
                }]}],
            }]},
            "composite_plan": {
                "generated_assets": [{
                    "id": "orientation", "purpose": "Identify the real-world context",
                    "placement": "Adjacent to the data region", "text_free": True,
                    "encodes_magnitude": False,
                }],
                "deterministic_evidence_layer": (
                    "All axes, values, intervals, labels, and typography are rendered from data."
                ),
                "integration_strategy": (
                    "The orientation asset introduces the adjacent quantitative comparison."
                ),
                "balance_rationale": (
                    "The asset and plot share visual weight around one optical centre."
                ),
                "intrinsic_aspect_preserved": True,
            },
        })
        spec["layout_plan"]["content_density"] = "moderate"
        spec["layout_plan"]["wide_canvas_required"] = False
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [
            "Category", "Outcome (unit)"]
        spec["semantic_plan"]["quantitative_decision"] = {
            "verified_numbers_available": True,
            "numbers_carry_primary_message": True,
            "reason": "The estimate and interval carry the comparison.",
        }
        spec["semantic_plan"]["panel_jobs"] = []
        inspection = self.v3_inspection()
        inspection["ocr_text"] = "Category Outcome unit Group 1.0"
        inspection["annotation"] = {"panel_labels": [], "callouts": []}
        inspection["mobile_preview"].update({
            "readable_primary_labels": ["Category", "Outcome (unit)"],
            "observed_first_glance_path": ["Recognize context", "Read estimate"],
            "observed_explain_back": "The context and estimate form one comparison.",
        })
        inspection["integrity"]["composite_components_integrated"] = True
        inspection["quantitative"] = {
            "axis_semantics_visible": True,
            "numeric_annotations_attached_to_referents": True,
            "uncertainty_attached_to_estimate": True,
            "uncertainty_graphically_visible": True,
            "data_marks_visually_primary": True,
            "annotations_clear_of_marks": True,
            "y_axis_label_vertical": True,
            "redundant_legend_absent": True,
            "full_composition_balanced": True,
        }
        inspection["composite"] = {
            "generated_assets_text_free": True,
            "generated_assets_orientation_only": True,
            "quantitative_layer_deterministic": True,
            "intrinsic_aspect_ratios_preserved": True,
        }
        return spec, inspection

    def test_v3_composite_separates_orientation_art_from_evidence(self):
        spec, inspection = self.composite_v3_case()

        def mutate(provenance):
            selected = provenance["selected_asset"]
            provenance.update({
                "selected_route": "composite",
                "attempts": [
                    {"kind": "generate", "asset": "orientation.png",
                     "text_mode": "none", "outcome": "accepted-for-composition"},
                    {"kind": "compose", "asset": selected,
                     "tool": "deterministic-compositor", "outcome": "selected"},
                ],
                "comparison": {"candidates_compared": 1,
                               "selection_rationale": "The orientation asset is clear."},
                "composite": {
                    "compositor": "deterministic-compositor",
                    "generated_assets_text_free": True,
                    "quantitative_layer_deterministic": True,
                    "intrinsic_aspect_preserved": True,
                },
            })
            goal = spec["communication_goal"]["reader_takeaway"]
            provenance["post_generation_reviews"] = [
                {
                    "asset": "orientation.png", "intended_takeaway": goal,
                    "observed_takeaway": "The context is recognizable but has no evidence.",
                    "observed_explain_back": "This identifies the real-world context.",
                    "intuitive_without_caption": True, "unexplained_jargon": [],
                    "intended_meaning_conveyed": False, "information_flow_clear": True,
                    "issues": ["The deterministic evidence layer is not yet composed."],
                    "decision": "revise",
                },
                {
                    "asset": selected, "intended_takeaway": goal,
                    "observed_takeaway": goal,
                    "observed_explain_back": spec["communication_goal"]["plain_language_explain_back"],
                    "intuitive_without_caption": True, "unexplained_jargon": [],
                    "intended_meaning_conveyed": True, "information_flow_clear": True,
                    "issues": [], "decision": "accept",
                },
            ]

        result = self.audit(
            spec=spec, inspection=inspection, provenance_mutator=mutate)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_composite_rejects_generated_magnitude_or_missing_integration(self):
        spec, _inspection = self.composite_v3_case()
        spec["composite_plan"]["generated_assets"][0]["encodes_magnitude"] = True
        with self.assertRaisesRegex(ValueError, "encodes_magnitude=false"):
            self.audit(spec=spec, inspection=self.v3_inspection())

    def test_v3_quantitative_text_only_interval_and_dominant_labels_fail(self):
        spec, inspection = self.composite_v3_case()
        inspection["quantitative"]["uncertainty_graphically_visible"] = False
        inspection["quantitative"]["data_marks_visually_primary"] = False
        inspection["quantitative"]["annotations_clear_of_marks"] = False

        def mutate(provenance):
            selected = provenance["selected_asset"]
            provenance.update({
                "selected_route": "composite",
                "attempts": [
                    {"kind": "generate", "asset": "orientation.png",
                     "text_mode": "none", "outcome": "accepted-for-composition"},
                    {"kind": "compose", "asset": selected,
                     "tool": "deterministic-compositor", "outcome": "selected"},
                ],
                "comparison": {"candidates_compared": 1,
                               "selection_rationale": "One candidate was audited."},
                "composite": {
                    "compositor": "deterministic-compositor",
                    "generated_assets_text_free": True,
                    "quantitative_layer_deterministic": True,
                    "intrinsic_aspect_preserved": True,
                },
            })

        result = self.audit(
            spec=spec, inspection=inspection, provenance_mutator=mutate)
        self.assertTrue(any("attached whisker" in error for error in result["errors"]))
        self.assertTrue(any("overwhelmed by annotations" in error
                            for error in result["errors"]))
        self.assertTrue(any("clear gap from data marks" in error
                            for error in result["errors"]))

    def test_v3_cross_view_identity_drift_fails(self):
        spec = self.v3_spec()
        spec["semantic_plan"]["cross_view_identity"] = [{
            "entity": "signal",
            "views": ["before filter", "after filter"],
            "invariant_features": ["registered position", "shape"],
            "reason": "Only the declared filter may change visibility.",
        }]
        inspection = self.v3_inspection()
        inspection["integrity"]["identity_drift"] = ["signal moved between views"]
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any("cross-view identity was not confirmed" in error
                            for error in result["errors"]))

    def test_v3_identity_preserving_hybrid_is_a_narrow_audited_fallback(self):
        spec = self.v3_spec()
        spec["render_route"] = "hybrid"
        spec["semantic_plan"]["cross_view_identity"] = [{
            "entity": "signal",
            "views": ["source view", "filtered view"],
            "invariant_features": ["registered position", "membership", "shape"],
            "reason": "Only the declared filter may change visibility.",
        }]
        inspection = self.v3_inspection()
        inspection["integrity"]["cross_view_identity_preserved"] = [{
            "entity": "signal", "preserved": True,
        }]

        def mutate(provenance):
            goal = spec["communication_goal"]["reader_takeaway"]
            provenance["selected_route"] = "hybrid"
            provenance["attempts"] = [
                {"kind": "generate", "asset": "canonical.png",
                 "text_mode": "none", "outcome": "accepted-for-composition"},
                {"kind": "edit", "asset": "identity-edit.png",
                 "outcome": "rejected", "reason": "Repeated-view membership drifted."},
                {"kind": "compose", "asset": "figure.png", "outcome": "selected"},
            ]
            provenance["comparison"] = {
                "candidates_compared": 1,
                "selection_rationale": "One canonical art layer was selected for exact duplication.",
            }
            provenance["fallback_reason"] = (
                "Whole-image generation and one targeted edit changed repeated-view identity.")
            provenance["hybrid"] = {
                "fallback_mode": "identity-preserving-composition",
                "compositor": "deterministic identity compositor",
                "base_asset": "canonical.png",
                "generated_asset_text_free": True,
                "identity_geometry_deterministic": True,
                "anisotropic_resize": False,
            }
            provenance["post_generation_reviews"] = [
                {
                    "asset": "canonical.png", "intended_takeaway": goal,
                    "observed_takeaway": "The canonical source structure is clear.",
                    "observed_explain_back": "This is the source structure.",
                    "intuitive_without_caption": True, "unexplained_jargon": [],
                    "intended_meaning_conveyed": False, "information_flow_clear": True,
                    "issues": ["Repeated views are not yet composed."],
                    "decision": "revise",
                },
                {
                    "asset": "identity-edit.png", "intended_takeaway": goal,
                    "observed_takeaway": "The filter is visible but identity changed.",
                    "observed_explain_back": "The second view may not show the same specimen.",
                    "intuitive_without_caption": False, "unexplained_jargon": [],
                    "intended_meaning_conveyed": False, "information_flow_clear": False,
                    "issues": ["Membership and positions drifted."],
                    "decision": "regenerate",
                },
                {
                    "asset": "figure.png", "intended_takeaway": goal,
                    "observed_takeaway": goal,
                    "observed_explain_back": spec["communication_goal"]["plain_language_explain_back"],
                    "intuitive_without_caption": True, "unexplained_jargon": [],
                    "intended_meaning_conveyed": True, "information_flow_clear": True,
                    "issues": [], "decision": "accept",
                },
            ]

        result = self.audit(
            spec=spec, inspection=inspection, provenance_mutator=mutate)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v3_identity_hybrid_without_declared_cross_view_invariant_fails(self):
        spec = self.v3_spec()
        spec["render_route"] = "hybrid"

        def mutate(provenance):
            provenance["selected_route"] = "hybrid"
            provenance["attempts"].append(
                {"kind": "compose", "asset": "figure.png", "outcome": "selected"})
            provenance["fallback_reason"] = "Generated identities drifted."
            provenance["hybrid"] = {
                "fallback_mode": "identity-preserving-composition",
                "compositor": "deterministic compositor",
                "base_asset": "figure.png",
                "generated_asset_text_free": True,
                "identity_geometry_deterministic": True,
                "anisotropic_resize": False,
            }

        result = self.audit(spec=spec, provenance_mutator=mutate)
        self.assertTrue(any("declared cross_view_identity" in error
                            for error in result["errors"]))

    def test_v2_first_candidate_can_pass_after_meaning_check(self):
        result = self.audit()
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v2_failed_meaning_check_can_pass_only_after_another_attempt(self):
        result = self.audit(first_pass=False)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_v2_selected_candidate_with_unclear_flow_fails(self):
        inspection = self.inspection()
        inspection["communication"]["information_flow_clear"] = False
        result = self.audit(inspection=inspection)
        self.assertTrue(any(
            "information_flow_clear" in error for error in result["errors"]))

    def test_v2_unresolved_candidate_review_requires_another_attempt(self):
        def mutate(provenance):
            review = provenance["post_generation_reviews"][0]
            review.update({
                "intended_meaning_conveyed": False,
                "information_flow_clear": False,
                "issues": ["The direction is ambiguous"],
                "decision": "regenerate",
            })

        result = self.audit(provenance_mutator=mutate)
        self.assertTrue(any(
            "was not followed by another attempt" in error
            for error in result["errors"]))

    def test_v2_missing_explanatory_value_fails(self):
        inspection = self.inspection()
        inspection["visual_quality"].pop("explanatory_value")
        result = self.audit(inspection=inspection)
        self.assertTrue(any(
            "explanatory_value must pass" in error for error in result["errors"]))

    def test_v2_missing_intuitiveness_fails(self):
        inspection = self.inspection()
        inspection["visual_quality"].pop("intuitiveness")
        result = self.audit(inspection=inspection)
        self.assertTrue(any(
            "intuitiveness must pass" in error for error in result["errors"]))

    def test_v2_caption_dependency_and_unexplained_jargon_fail(self):
        inspection = self.inspection()
        inspection["communication"]["requires_caption_to_understand"] = True
        inspection["communication"]["intuitive_without_caption"] = False
        inspection["communication"]["unexplained_jargon"] = ["latent mediator"]
        result = self.audit(inspection=inspection)
        self.assertTrue(any(
            "requires_caption_to_understand=false" in error
            for error in result["errors"]))
        self.assertTrue(any(
            "unexplained figure jargon: latent mediator" in error
            for error in result["errors"]))

    def test_v2_required_callout_leader_line_is_checked(self):
        spec = self.spec()
        spec["exact_text"].append("Target note")
        spec["annotation_plan"]["callouts"] = [{
            "text": "Target note",
            "target": "response structure",
            "leader_line": True,
        }]
        inspection = self.inspection()
        inspection["ocr_text"] += " Target note"
        inspection["annotation"]["callouts"] = [{
            "text": "Target note",
            "target": "response structure",
            "leader_line_present": False,
            "leader_origin_attached_to_label": False,
            "leader_endpoint_hits_target": False,
        }]
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any(
            "required leader line is missing" in error
            for error in result["errors"]))

    def test_v2_leader_line_must_hit_every_declared_target(self):
        spec = self.spec()
        spec["exact_text"].append("Two-result note")
        spec["annotation_plan"]["callouts"] = [{
            "text": "Two-result note",
            "target": "both result structures",
            "leader_line": True,
        }]
        inspection = self.inspection()
        inspection["ocr_text"] += " Two-result note"
        inspection["annotation"]["callouts"] = [{
            "text": "Two-result note",
            "target": "both result structures",
            "leader_line_present": True,
            "leader_origin_attached_to_label": True,
            "leader_endpoint_hits_target": False,
        }]
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any(
            "does not terminate on every declared target" in error
            for error in result["errors"]))

    def test_v2_leader_line_must_visibly_belong_to_its_label(self):
        spec = self.spec()
        spec["exact_text"].append("Outcome note")
        spec["annotation_plan"]["callouts"] = [{
            "text": "Outcome note",
            "target": "the outcome pair",
            "leader_line": True,
        }]
        inspection = self.inspection()
        inspection["ocr_text"] += " Outcome note"
        inspection["annotation"]["callouts"] = [{
            "text": "Outcome note",
            "target": "the outcome pair",
            "leader_line_present": True,
            "leader_origin_attached_to_label": False,
            "leader_endpoint_hits_target": True,
        }]
        result = self.audit(spec=spec, inspection=inspection)
        self.assertTrue(any(
            "visually detached from its label" in error
            for error in result["errors"]))


class RenderedWidthTests(unittest.TestCase):
    """Label legibility must be judged at the width the journal page will
    actually render the raster at: the exporter's height cap scales tall
    figures down, so their labels print smaller than a naive full-width
    assumption."""

    @staticmethod
    def spec():
        return {"exact_text": ["axis"], "render_context": "article"}

    @staticmethod
    def inspection(height_px=22.0):
        return {
            "ocr_text": "axis",
            "minimum_label_height_px": height_px,
            "relationships": [],
            "detected_effects": [],
            "text_collisions": [],
        }

    def make_image(self, width, height):
        from PIL import Image, ImageDraw

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        canvas = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(
            (round(width * 0.1), round(height * 0.2),
             round(width * 0.9), round(height * 0.8)),
            fill="#D3E5EF", outline="#1A1A1A", width=max(2, width // 200),
        )
        canvas.save(tmp.name)
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name

    def test_wide_figure_is_judged_at_full_content_width(self):
        image = self.make_image(1536, 662)
        result = qa_figure.audit_figure(
            self.spec(), image, inspection=self.inspection()
        )
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertGreaterEqual(result["metrics"]["minimum_effective_label_pt"], 6.5)

    def test_tall_figure_fails_and_names_the_rendered_width(self):
        image = self.make_image(1000, 1500)
        result = qa_figure.audit_figure(
            self.spec(), image, inspection=self.inspection()
        )
        self.assertEqual(result["status"], "fail")
        message = " ".join(result["errors"])
        self.assertIn("mm rendered width", message)

    def test_explicit_width_override_still_wins(self):
        image = self.make_image(1000, 1500)
        result = qa_figure.audit_figure(
            self.spec(), image, inspection=self.inspection(height_px=40.0),
            pdf_width_mm=170.0,
        )
        self.assertEqual(result["status"], "pass", result["errors"])


class ConfusableFoldingTests(unittest.TestCase):
    """OCR cannot tell Arial capital-I from lowercase-l; the comparison fold
    must treat them as equal without altering what the figure says."""

    def test_ci_matches_cl_ocr(self):
        self.assertEqual(qa_figure._normal("95% CI"), qa_figure._normal("95% Cl"))

    def test_unicode_minus_matches_hyphen(self):
        self.assertEqual(qa_figure._normal("\u221225.4"), qa_figure._normal("-25.4"))

    def test_distinct_words_stay_distinct(self):
        self.assertNotEqual(
            qa_figure._normal("placebo"), qa_figure._normal("probiotic")
        )
        self.assertNotEqual(qa_figure._normal("-25.4"), qa_figure._normal("-47.3"))


if __name__ == "__main__":
    unittest.main()
