import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
SCRIPT = os.path.join(ROOT, "scripts", "build_figure_prompt.py")
SPEC = importlib.util.spec_from_file_location("build_figure_prompt", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FigurePromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = MODULE.load_json(MODULE.DEFAULT_PROFILES)
        cls.archetypes = MODULE.load_json(MODULE.DEFAULT_ARCHETYPES)
        cls.writing_styles = MODULE.load_json(MODULE.DEFAULT_WRITING_STYLES)

    def minimal_spec(self):
        return {
            "purpose": "Explain a verified mechanism.",
            "title": "A clean mechanism",
            "story": ["A leads to B."],
            "exact_text": ["A clean mechanism", "A", "B"],
        }

    def test_every_writing_style_declares_an_exact_white_canvas(self):
        self.assertEqual(
            set(self.writing_styles), {"scientific", "popsci", "bullets", "eli5"})
        for name, style in self.writing_styles.items():
            with self.subTest(style=name):
                self.assertEqual(style["canvas"]["background"], "#FFFFFF")

    def test_every_profile_has_a_phone_safe_generated_type_margin(self):
        for name, profile in self.profiles.items():
            with self.subTest(profile=name):
                font = profile["font"]
                self.assertGreaterEqual(font["minimum_px_at_1536_width"], 96)
                self.assertGreaterEqual(font["body_px_at_1536_width"], 104)
                self.assertGreaterEqual(font["panel_label_px_at_1536_width"], 116)

    def v2_generated_spec(self):
        spec = self.minimal_spec()
        spec.update({
            "quality_contract_version": 2,
            "review_style": "scientific",
            "render_route": "generated",
            "target_aspect_ratio": 2.0,
            "visual_anchor": "One domain-specific structure linking A to B",
            "communication_goal": {
                "reader_takeaway": "A visibly leads to B, within a limited evidence boundary.",
                "must_show": ["A", "the transition", "B"],
                "information_flow": ["Notice A", "Follow the transition", "Arrive at B"],
                "evidence_boundary": "The direction is supported; its magnitude is not shown.",
                "familiar_starting_point": "A visible path joining a starting point to an outcome.",
                "plain_language_explain_back": "A travels along one path and produces B.",
            },
            "concepts": [
                {
                    "id": "pathway",
                    "description": "A single continuous domain-native pathway with A at left and B at right.",
                    "information_flow": ["A", "transition", "B"],
                    "strengths": ["Immediate eye path", "Few visual elements"],
                    "risks": ["Could imply an exact rate if overdecorated"],
                },
                {
                    "id": "paired",
                    "description": "Two aligned states separated by a restrained transition marker.",
                    "information_flow": ["Compare states", "Read the connector"],
                    "strengths": ["Simple comparison"],
                    "risks": ["Less explicit process"],
                },
                {
                    "id": "cutaway",
                    "description": "A domain-native cutaway revealing the transition inside one structure.",
                    "information_flow": ["See the whole", "Inspect the transition"],
                    "strengths": ["Elegant integration"],
                    "risks": ["Higher visual complexity"],
                },
            ],
            "concept_selection": {
                "selected_id": "pathway",
                "selection_rationale": "It gives the clearest complete explanation with the least visual machinery.",
                "evaluations": [
                    {"id": "pathway", "clarity": 5, "simplicity": 5,
                     "completeness": 4, "elegance": 5, "intuitiveness": 5,
                     "assessment": "Best overall."},
                    {"id": "paired", "clarity": 4, "simplicity": 5,
                     "completeness": 3, "elegance": 4, "intuitiveness": 4,
                     "assessment": "Too static."},
                    {"id": "cutaway", "clarity": 3, "simplicity": 2,
                     "completeness": 5, "elegance": 5, "intuitiveness": 3,
                     "assessment": "Too complex."},
                ],
            },
            "annotation_plan": {
                "panel_labels": ["A", "B"],
                "callouts": [],
                "rationale": "Two distinct sections need stable references; direct labels are adjacent.",
            },
        })
        return spec

    def v3_generated_spec(self):
        spec = self.v2_generated_spec()
        spec["quality_contract_version"] = 3
        spec["layout_plan"] = {
            "content_density": "moderate",
            "wide_canvas_required": False,
            "aspect_ratio_rationale": (
                "Two linked stages use a compact horizontal composition without dead gutters."
            ),
            "balance_strategy": (
                "Equal visual weight around the transition keeps the optical centre stable."
            ),
            "final_display": "Journal article figure at its true proportional PDF size.",
            "mobile_preview": {
                "width_px": 390,
                "minimum_label_height_px": 12,
                "primary_labels": ["A", "B"],
                "first_glance_path": ["Notice A", "Follow the transition", "Arrive at B"],
                "explain_back_without_zoom": "A visibly leads to B.",
            },
        }
        spec["communication_goal"].update({
            "visual_question": "How does the signal reach the response?",
            "panel_thesis": (
                "A establishes the specific signal and B shows the response it produces."
            ),
        })
        spec["semantic_plan"] = {
            "entities": [
                {
                    "id": "signal",
                    "depiction": "one specific domain-native signal structure",
                    "role": "the starting entity",
                    "evidence_basis": "directly supported starting state",
                },
                {
                    "id": "response",
                    "depiction": "one specific domain-native response structure",
                    "role": "the resulting entity",
                    "evidence_basis": "directly supported response state",
                },
            ],
            "connectors": [{
                "from": "signal", "to": "response", "meaning": "causal",
                "label": "activates",
            }],
            "panel_jobs": [
                {"label": "A", "job": "establish the signal",
                 "adds_distinct_information": True},
                {"label": "B", "job": "show the resulting response",
                 "adds_distinct_information": True},
            ],
            "grouping_rationale": (
                "The two stages answer one question; no outcome is split into a duplicate panel."
            ),
            "anatomy_subjects": [],
            "anatomical_context": [],
            "salience_targets": ["signal", "response"],
            "information_priority": {
                "primary_entities": ["signal", "response"],
                "supporting_entities": [],
                "excluded_nonessential": ["decorative background props"],
                "dominance_rationale": "The signal and response carry the complete explanation.",
                "deletion_test": "Remove anything that does not change the signal-to-response explanation.",
            },
            "uncertainty_encodings": [],
            "cross_view_identity": [],
            "representation_plan": {
                "kind": "literal",
                "evidence_native_anchor": "the specific signal and response structures",
                "cognitive_translation_steps": 0,
                "literal_rejected_reason": None,
                "added_explanatory_value": "The literal pathway is the shortest explanation.",
                "arranged_elements": False,
                "arrangement_evidence_job": None,
            },
            "quantitative_decision": {
                "verified_numbers_available": False,
                "numbers_carry_primary_message": False,
                "reason": "The supported message is a qualitative relationship.",
            },
        }
        return spec

    def v3_cutaway_spec(self, review_style="popsci"):
        spec = self.v3_generated_spec()
        spec.update({
            "archetype": "cutaway",
            "review_style": review_style,
            "target_aspect_ratio": 1.35,
            "title": "A hidden structure explains the visible whole",
            "visual_anchor": "one recognizable whole object opened by one coherent section",
            "exact_text": [
                "A hidden structure explains the visible whole",
                "Layer carries signal",
                "Core makes response",
            ],
        })
        spec["communication_goal"].update({
            "visual_question": "How do the hidden parts make the visible whole work?",
            "panel_thesis": "One continuous section connects the recognizable exterior to its working interior.",
            "reader_takeaway": "The outer form works because two hidden parts occupy specific nested positions.",
            "must_show": ["recognizable exterior", "outer layer", "inner core"],
            "information_flow": ["recognize the whole", "follow the cut inward", "read each part's job"],
            "familiar_starting_point": "the intact outer silhouette",
            "plain_language_explain_back": "The outside contains a layer that carries a signal to a working core.",
        })
        spec["concepts"][0].update({
            "id": "sectional-plate",
            "description": "One recognizable whole object with a single clean section revealing two nested working parts.",
            "information_flow": ["recognize the whole", "enter the section", "read two jobs"],
        })
        spec["concept_selection"]["selected_id"] = "sectional-plate"
        spec["concept_selection"]["evaluations"][0]["id"] = "sectional-plate"
        spec["concept_selection"]["selection_rationale"] = (
            "The single section removes the hidden-structure imagination step with the fewest elements."
        )
        spec["annotation_plan"] = {
            "panel_labels": [],
            "callouts": [
                {
                    "text": "Layer carries signal",
                    "target": "signal",
                    "leader_line": True,
                    "background": "quiet-canvas",
                    "placement_priority": "quiet-canvas-first",
                    "explanatory_role": "Names the outer hidden layer and explains its transfer job.",
                },
                {
                    "text": "Core makes response",
                    "target": "response",
                    "leader_line": True,
                    "background": "quiet-canvas",
                    "placement_priority": "quiet-canvas-first",
                    "explanatory_role": "Names the inner core and explains the response it produces.",
                },
            ],
            "rationale": "One continuous cutaway needs no panel letter; two leaders explain the hidden parts.",
        }
        spec["layout_plan"]["content_density"] = "moderate"
        spec["layout_plan"]["mobile_preview"].update({
            "primary_labels": ["Layer carries signal", "Core makes response"],
            "first_glance_path": ["recognize the whole", "follow the cut inward", "read each part's job"],
            "explain_back_without_zoom": "The outer layer carries a signal to the working core.",
        })
        spec["semantic_plan"]["panel_jobs"] = []
        spec["semantic_plan"]["connectors"] = []
        spec["semantic_plan"]["grouping_rationale"] = (
            "The intact exterior and exposed interior are two views of one physical explanation."
        )
        spec["semantic_plan"]["cutaway_plan"] = {
            "exterior_silhouette": "the complete familiar outline remains visible around the opening",
            "cut_plane": "one oblique section with a shared scale and perspective",
            "interior_entities": ["signal", "response"],
            "spatial_relationships": [
                "the signal layer surrounds the response core",
                "the cut surface preserves continuity with the intact exterior",
            ],
            "annotation_strategy": "two short labels in surrounding white space lead directly to the two exposed structures",
            "suitability": {
                "hidden_interior_removes_mental_step": True,
                "faithful_interior_supported": True,
                "distinct_evidence_job": True,
                "phone_readable": True,
                "reason": "The hidden nesting is the explanation and cannot be inferred from an exterior view alone.",
            },
        }
        return spec

    def test_v3_prompt_encodes_one_thesis_semantic_arrows_and_salience(self):
        spec = self.v3_generated_spec()
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes, writing_styles=self.writing_styles)
        self.assertIn("ONE VISUAL THESIS — HARD GATE", prompt)
        self.assertIn("Do not combine independent questions", prompt)
        self.assertIn("DECLARED CONNECTORS — USE NO OTHERS", prompt)
        self.assertIn("signal → response; meaning: causal", prompt)
        self.assertIn("SALIENCE AT FINAL SIZE — HARD GATE", prompt)
        self.assertIn("VISUAL CONTENT BUDGET — HARD GATE", prompt)
        self.assertIn("decorative background props", prompt)
        self.assertIn("A — establish the signal", prompt)
        self.assertIn("PHONE PREVIEW — HARD GATE", prompt)
        self.assertIn("REPRESENTATION ECONOMY — HARD GATE", prompt)

    def test_cutaway_archetype_builds_a_style_specific_integrity_prompt(self):
        prompt = MODULE.build_prompt(
            self.v3_cutaway_spec(), self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("CUTAWAY INTEGRITY — HARD GATE", prompt)
        self.assertIn("one coherent cut plane", prompt)
        self.assertIn("premium museum-editorial sectional plate", prompt)
        self.assertIn("explanatory job:", prompt)
        self.assertIn("Layer carries signal → signal", prompt)
        self.assertIn("Reserve the full outer 6–8%", prompt)
        self.assertIn("glyph-line height of at least 48 px", prompt)

    def test_cutaway_suitability_fails_closed(self):
        spec = self.v3_cutaway_spec()
        spec["semantic_plan"]["cutaway_plan"]["suitability"][
            "distinct_evidence_job"] = False
        with self.assertRaisesRegex(ValueError, "distinct_evidence_job=true"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_cutaway_requires_one_explanatory_callout_per_interior_entity(self):
        spec = self.v3_cutaway_spec()
        spec["annotation_plan"]["callouts"].pop()
        spec["exact_text"].remove("Core makes response")
        spec["layout_plan"]["mobile_preview"]["primary_labels"].remove(
            "Core makes response")
        with self.assertRaisesRegex(ValueError, "cover every interior entity"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_rejects_nonwhite_canvas_override(self):
        spec = self.v3_generated_spec()
        spec["style_overrides"] = {"canvas": {"background": "#FBFAF6"}}
        with self.assertRaisesRegex(ValueError, "exact #FFFFFF canvas"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_requires_phone_preview_label_floor(self):
        spec = self.v3_generated_spec()
        spec["layout_plan"]["mobile_preview"]["minimum_label_height_px"] = 8
        with self.assertRaisesRegex(ValueError, "at least 12"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_rejects_an_unclassified_or_competing_entity(self):
        spec = self.v3_generated_spec()
        spec["semantic_plan"]["information_priority"]["primary_entities"] = ["signal"]
        with self.assertRaisesRegex(ValueError, "classify every entity"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_rejects_missing_visual_question(self):
        spec = self.v3_generated_spec()
        spec["communication_goal"].pop("visual_question")
        with self.assertRaisesRegex(ValueError, "visual_question"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_rejects_an_undefined_or_decorative_connector(self):
        spec = self.v3_generated_spec()
        spec["semantic_plan"]["connectors"][0]["meaning"] = "decorative"
        with self.assertRaisesRegex(ValueError, "connector meaning"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_rejects_panel_jobs_that_duplicate_or_miss_panels(self):
        spec = self.v3_generated_spec()
        spec["semantic_plan"]["panel_jobs"] = spec["semantic_plan"]["panel_jobs"][:1]
        with self.assertRaisesRegex(ValueError, "panel_jobs labels"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_routes_primary_verified_numbers_deterministically(self):
        spec = self.v3_generated_spec()
        decision = spec["semantic_plan"]["quantitative_decision"]
        decision["verified_numbers_available"] = True
        decision["numbers_carry_primary_message"] = True
        with self.assertRaisesRegex(ValueError, "require deterministic"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_human_subjects_trigger_explicit_anatomy_rejection(self):
        spec = self.v3_generated_spec()
        spec["semantic_plan"]["anatomy_subjects"] = ["one adult person"]
        spec["semantic_plan"]["anatomical_context"] = [{
            "subject": "one adult person",
            "orientation_landmarks": ["head", "torso"],
            "focal_region": "the depicted response region",
            "context_rationale": "The landmarks locate the response on the body.",
        }]
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("ANATOMICAL INTEGRITY — HARD GATE", prompt)
        self.assertIn("extra, missing, duplicated, fused, or impossible body part", prompt)
        self.assertIn("ANATOMICAL CONTEXT — ORIENT BEFORE SIMPLIFYING", prompt)

    def test_v3_human_subject_without_orientation_context_is_rejected(self):
        spec = self.v3_generated_spec()
        spec["semantic_plan"]["anatomy_subjects"] = ["one adult person"]
        with self.assertRaisesRegex(ValueError, "cover every anatomy subject"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_default_prompt_defines_arial_and_rejects_serif(self):
        prompt = MODULE.build_prompt(
            self.minimal_spec(), self.profiles, self.archetypes
        )
        self.assertIn("Render every character in Arial throughout", prompt)
        self.assertIn("serif typography", prompt)
        self.assertIn("#1A1A1A", prompt)
        self.assertIn("Context: article", prompt)
        self.assertIn("figure-native", prompt)
        self.assertIn("Nature Reviews-inspired conceptual synthesis", prompt)
        self.assertNotIn("neuroscience or biomedical composition", prompt)

    def test_article_context_keeps_caption_title_out_of_render_manifest(self):
        prompt = MODULE.build_prompt(
            self.minimal_spec(), self.profiles, self.archetypes
        )
        self.assertIn("CAPTION CONTEXT — DO NOT RENDER", prompt)
        manifest = prompt.split("EXACT IN-FIGURE TEXT MANIFEST", 1)[1].split(
            "AVOID", 1
        )[0]
        self.assertNotIn("A clean mechanism", manifest)
        self.assertIn('"A"', manifest)
        self.assertIn('"B"', manifest)

    def test_standalone_context_renders_a_compact_title(self):
        spec = self.minimal_spec()
        spec["render_context"] = "standalone"
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Context: standalone", prompt)
        self.assertIn("TITLE — RENDER COMPACTLY\nA clean mechanism", prompt)
        manifest = prompt.split("EXACT IN-FIGURE TEXT MANIFEST", 1)[1].split(
            "AVOID", 1
        )[0]
        self.assertIn('"A clean mechanism"', manifest)

    def test_slide_context_reserves_chrome_and_omits_the_claim_from_pixels(self):
        spec = self.minimal_spec()
        spec["render_context"] = "slide"
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Context: slide", prompt)
        self.assertIn("16:9 landscape", prompt)
        self.assertIn("top 19% and bottom 8% visually quiet", prompt)
        self.assertIn("SLIDE CHROME CONTEXT", prompt)
        manifest = prompt.split("EXACT IN-FIGURE TEXT MANIFEST", 1)[1].split(
            "AVOID", 1
        )[0]
        self.assertNotIn('"A clean mechanism"', manifest)
        self.assertIn('"A"', manifest)
        self.assertIn('"B"', manifest)

    def test_exact_text_is_json_quoted_verbatim(self):
        spec = self.minimal_spec()
        spec["exact_text"].append("95% CI 6.1–15.4")
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn(json.dumps("95% CI 6.1–15.4", ensure_ascii=False), prompt)

    def test_profile_and_archetype_are_independent_overrides(self):
        spec = self.minimal_spec()
        spec["profile"] = "nature-reviews"
        spec["archetype"] = "comparison"
        prompt = MODULE.build_prompt(
            spec,
            self.profiles,
            self.archetypes,
            profile_name="nature-data",
            archetype_name="timeline",
        )
        self.assertIn("Nature-inspired quantitative figure", prompt)
        self.assertIn("timeline —", prompt)
        self.assertNotIn("Nature Reviews-inspired conceptual synthesis", prompt)

    def test_nature_reviews_profile_is_domain_general(self):
        visual_language = " ".join(
            self.profiles["nature-reviews"]["visual_language"]
        )
        self.assertIn("domain-specific structures", visual_language)
        self.assertIn("study operations, or evidence marks", visual_language)
        self.assertNotIn("Let biological structures", visual_language)
        self.assertNotIn("clean cutaway anatomy", visual_language)

    def test_style_override_does_not_mutate_profile_catalog(self):
        original = copy.deepcopy(self.profiles)
        spec = self.minimal_spec()
        spec["style_overrides"] = {"canvas": {"aspect": "square"}}
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Aspect: square", prompt)
        self.assertEqual(self.profiles, original)

    def test_dotted_style_override_is_applied(self):
        spec = self.minimal_spec()
        spec["style_overrides"] = {"canvas.aspect": "2:1 editorial landscape"}
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Aspect: 2:1 editorial landscape", prompt)

    def test_popsci_uses_distinct_premium_art_direction(self):
        spec = self.minimal_spec()
        spec["review_style"] = "popsci"
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Premium editorial science illustration", prompt)
        self.assertIn("Render every character in Helvetica Neue throughout", prompt)
        self.assertIn("serious long-form magazine", prompt)
        self.assertIn("corporate infographic", prompt)
        self.assertIn("Never resize, condense, expand, shear, or stretch", prompt)

    def test_hybrid_route_reserves_exact_copy_for_overlay(self):
        spec = self.minimal_spec()
        spec["render_route"] = "hybrid"
        spec["generated_text"] = ["A"]
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("AUTHORING ROUTE\nhybrid", prompt)
        generated = prompt.split("TEXT THE IMAGE MODEL MAY RENDER", 1)[1].split(
            "RESERVED DETERMINISTIC OVERLAY COPY", 1)[0]
        reserved = prompt.split("RESERVED DETERMINISTIC OVERLAY COPY", 1)[1].split(
            "AVOID", 1)[0]
        self.assertIn('"A"', generated)
        self.assertNotIn('"B"', generated)
        self.assertIn('"B"', reserved)
        self.assertIn("no placeholder glyphs, pseudo-text", prompt)

    def test_generated_route_requires_imagegen_to_render_all_text_now(self):
        prompt = MODULE.build_prompt(
            self.minimal_spec(), self.profiles, self.archetypes)
        self.assertIn("FIRST-PASS DIRECT-TEXT CONTRACT", prompt)
        self.assertIn("EXECUTE IN THIS IMAGEGEN CALL", prompt)
        self.assertIn("Do not return a textless base", prompt)
        self.assertIn("fully typeset final figure in this call", prompt)
        self.assertEqual(prompt.count('- "A"'), 1)
        self.assertEqual(prompt.count('- "B"'), 1)

    def test_generated_route_rejects_a_partial_text_manifest(self):
        spec = self.minimal_spec()
        spec["render_route"] = "generated"
        spec["generated_text"] = ["A"]
        with self.assertRaisesRegex(ValueError, "every exact_text string directly"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_text_bearing_comparison_defaults_to_direct_generation(self):
        spec = self.minimal_spec()
        spec["archetype"] = "comparison"
        spec["exact_text"].extend([f"Outcome {index}" for index in range(12)])
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("AUTHORING ROUTE\ngenerated", prompt)
        self.assertIn("FIRST-PASS DIRECT-TEXT CONTRACT", prompt)

    def test_quantitative_archetype_routes_deterministically(self):
        spec = self.minimal_spec()
        spec["archetype"] = "quantitative"
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("AUTHORING ROUTE\ndeterministic", prompt)

    def test_quality_contract_requires_explicit_route_style_and_aspect(self):
        spec = self.minimal_spec()
        spec["quality_contract_version"] = 1
        with self.assertRaisesRegex(ValueError, "explicit review_style and render_route"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

        spec["review_style"] = "eli5"
        spec["render_route"] = "generated"
        with self.assertRaisesRegex(ValueError, "target_aspect_ratio"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_complete_quality_contract_emits_rich_style_and_geometry_sections(self):
        spec = self.minimal_spec()
        spec.update({
            "quality_contract_version": 1,
            "review_style": "eli5",
            "render_route": "generated",
            "target_aspect_ratio": 2.0,
            "visual_anchor": "A cell membrane shown as a selective kitchen sieve",
        })
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("Warm explanatory illustration", prompt)
        self.assertIn("DOMINANT VISUAL ANCHOR", prompt)
        self.assertIn("EDITORIAL ART DIRECTION", prompt)
        self.assertIn("CANDIDATE SELECTION STANDARD", prompt)
        self.assertIn("GEOMETRY — HARD INVARIANTS", prompt)
        self.assertIn("2:1 landscape", prompt)

    def test_v2_selects_one_of_three_concepts_before_prompting(self):
        spec = self.v2_generated_spec()
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("COMMUNICATION GOAL — THE RELEASE GATE", prompt)
        self.assertIn("SELECTED CONCEPT — RENDER ONLY THIS CONCEPT", prompt)
        self.assertIn(spec["concepts"][0]["description"], prompt)
        self.assertNotIn(spec["concepts"][1]["description"], prompt)
        self.assertNotIn(spec["concepts"][2]["description"], prompt)
        self.assertIn(
            "clarity 5/5; simplicity 5/5; completeness 4/5; elegance 5/5; "
            "intuitiveness 5/5", prompt)
        self.assertIn("INTUITION AND EXPLAIN-BACK TEST — ALL REVIEW STYLES", prompt)
        self.assertIn("A travels along one path and produces B.", prompt)
        self.assertIn("endpoint visibly lands on the named referent", prompt)
        self.assertIn("visibly begins at the label", prompt)
        self.assertIn("reaches every named member", prompt)

    def test_v2_rejects_a_lower_scoring_selected_concept(self):
        spec = self.v2_generated_spec()
        spec["concept_selection"]["selected_id"] = "paired"
        with self.assertRaisesRegex(ValueError, "highest combined"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_v2_requires_a_plain_language_explain_back_target(self):
        spec = self.v2_generated_spec()
        del spec["communication_goal"]["plain_language_explain_back"]
        with self.assertRaisesRegex(ValueError, "plain_language_explain_back"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_v2_rejects_a_winner_that_is_not_intuitive(self):
        spec = self.v2_generated_spec()
        spec["concept_selection"]["evaluations"][0]["intuitiveness"] = 3
        with self.assertRaisesRegex(ValueError, "at least 4"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_v2_generated_illustration_rejects_known_numeric_data(self):
        spec = self.v2_generated_spec()
        spec["data"] = {"estimate": 2.4, "unit": "points"}
        with self.assertRaisesRegex(ValueError, "known numbers.*belong"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_v2_rejects_lowercase_panel_labels(self):
        spec = self.v2_generated_spec()
        spec["annotation_plan"]["panel_labels"] = ["a", "b"]
        with self.assertRaisesRegex(ValueError, "uppercase prefix"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_v2_quantitative_route_requires_real_data_and_polished_plot_design(self):
        spec = self.minimal_spec()
        spec.update({
            "quality_contract_version": 2,
            "review_style": "popsci",
            "render_route": "deterministic",
            "archetype": "quantitative",
            "target_aspect_ratio": 2.0,
            "communication_goal": {
                "reader_takeaway": "The estimate is above the null but uncertain.",
                "must_show": ["estimate", "interval", "null"],
                "information_flow": ["Find the estimate", "Read the interval", "Compare with null"],
                "evidence_boundary": "One verified estimate only.",
                "familiar_starting_point": "A dot and its uncertainty line compared with a null line.",
                "plain_language_explain_back": "The estimate is above the null, but the interval shows uncertainty.",
            },
            "annotation_plan": {
                "panel_labels": [], "callouts": [],
                "rationale": "A single plot needs neither panels nor anatomical callouts.",
            },
            "plot_design": {
                "chart_type": "dot-and-whisker plot",
                "encoding": "Position is the estimate; the line is the verified interval.",
                "reader_path": ["Estimate", "Interval", "Null line"],
                "style_rationale": "Direct labels and restrained colour minimize eye travel.",
            },
            "data": {"estimate": 1.4, "interval": [1.1, 1.8], "null": 1.0},
        })
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn("DETERMINISTIC PLOT DESIGN", prompt)
        self.assertIn("Do not emit library-default axes", prompt)

    def test_v3_quantitative_route_binds_axes_intervals_and_caption_semantics(self):
        spec = self.v3_generated_spec()
        spec.update({
            "archetype": "quantitative",
            "render_route": "deterministic",
            "exact_text": ["A clean mechanism", "Outcome", "Effect (points)"],
            "annotation_plan": {
                "panel_labels": [], "callouts": [],
                "rationale": "One quantitative panel needs no panel letter.",
            },
            "data": {"panels": [{
                "id": "main",
                "x_axis": {"label": "Outcome"},
                "y_axis": {"label": "Effect (points)"},
                "series": [{"points": [{"y_interval": [1.0, 2.0]}]}],
                "contrasts": [],
            }]},
            "plot_design": {
                "chart_type": "direct-labelled dot and interval",
                "encoding": "Position is the estimate and the whisker is its interval.",
                "reader_path": ["Read outcome", "Find estimate", "Read interval"],
                "style_rationale": "Direct attachment minimizes eye travel.",
                "typography": {
                    "family": "Arial", "fallback": "Helvetica",
                    "upright_natural_width": True,
                },
                "axis_semantics": [{
                    "panel_id": "main",
                    "x_label": "Outcome",
                    "x_meaning": "The x-axis names the measured outcome category.",
                    "y_label": "Effect (points)",
                    "y_meaning": "The y-axis shows the adjusted effect in score points.",
                }],
                "caption_axis_summary": (
                    "The x-axis names the outcome; the y-axis shows adjusted score points."
                ),
                "numeric_annotation_attachment": (
                    "Each value is placed beside its estimate mark."
                ),
                "uncertainty_display": {
                    "present": True,
                    "encoding": "Vertical whiskers show 95% confidence intervals.",
                    "attachment": "Each whisker passes through its estimate dot.",
                },
                "axis_label_placement": {
                    "x_orientation": "horizontal",
                    "x_location": "below-data-region",
                    "y_orientation": "vertical",
                    "y_location": "outside-data-region",
                },
                "legend_plan": {
                    "needed": False,
                    "reason": "The conventional point-and-whisker is explained in the caption.",
                    "placement": "none",
                },
            },
        })
        spec["semantic_plan"]["panel_jobs"] = []
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [
            "Outcome", "Effect (points)"]
        decision = spec["semantic_plan"]["quantitative_decision"]
        decision.update({
            "verified_numbers_available": True,
            "numbers_carry_primary_message": True,
            "reason": "The exact estimate and interval carry the message.",
        })
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("QUANTITATIVE SEMANTICS — HARD GATE", prompt)
        self.assertIn("x-axis 'Outcome'", prompt)
        self.assertIn("Every interval", prompt)
        spec["plot_design"].pop("axis_semantics")
        with self.assertRaisesRegex(ValueError, "axis_semantics"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_requires_content_fit_layout_plan(self):
        spec = self.v3_generated_spec()
        spec.pop("layout_plan")
        with self.assertRaisesRegex(ValueError, "layout_plan"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_generated_phone_labels_must_stay_short(self):
        spec = self.v3_generated_spec()
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [
            "A", "Everyday exposure causes illness remains unproven"]
        with self.assertRaisesRegex(ValueError, "at most four words"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_generated_phone_labels_reject_compound_policy_prose(self):
        spec = self.v3_generated_spec()
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [
            "A", "During class: stored"]
        with self.assertRaisesRegex(ValueError, "one idea without colon"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_generated_prompt_rejects_stock_asset_collage_and_mini_captions(self):
        prompt = MODULE.build_prompt(
            self.v3_generated_spec(), self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("VISUAL-LANGUAGE COHERENCE — HARD GATE", prompt)
        self.assertIn("Render one authored plate", prompt)
        self.assertIn("glossy stock symbols", prompt)
        self.assertIn("MOBILE LABEL SIMPLICITY — HARD GATE", prompt)
        self.assertIn("Move nuance to the external caption", prompt)
        self.assertIn("existing exact-white canvas", prompt)

    def test_v3_sparse_wide_canvas_requires_real_horizontal_topology(self):
        spec = self.v3_generated_spec()
        spec["layout_plan"]["content_density"] = "sparse"
        spec["layout_plan"]["wide_canvas_required"] = False
        with self.assertRaisesRegex(ValueError, "sparse figure wider than 1.75:1"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_callout_over_busy_pixels_requires_declared_backing(self):
        spec = self.v3_generated_spec()
        spec["exact_text"].append("Local note")
        spec["annotation_plan"]["callouts"] = [{
            "text": "Local note",
            "target": "the focal structure",
            "leader_line": True,
            "placement_priority": "quiet-canvas-first",
        }]
        with self.assertRaisesRegex(ValueError, "background"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)
        spec["annotation_plan"]["callouts"][0]["background"] = "opaque-white"
        with self.assertRaisesRegex(ValueError, "quiet_canvas_rejected_reason"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)
        spec["annotation_plan"]["callouts"][0]["quiet_canvas_rejected_reason"] = (
            "Moving the label would detach it from the small target.")
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("backing: opaque-white", prompt)
        self.assertIn("placement: quiet-canvas-first", prompt)

    def test_v3_arranged_elements_require_a_declared_evidence_job(self):
        spec = self.v3_generated_spec()
        representation = spec["semantic_plan"]["representation_plan"]
        representation["arranged_elements"] = True
        representation["arrangement_evidence_job"] = None
        with self.assertRaisesRegex(ValueError, "arrangement_evidence_job"):
            MODULE.build_prompt(
                spec, self.profiles, self.archetypes,
                writing_styles=self.writing_styles)

    def test_v3_justified_metaphor_assistance_is_explicit_in_the_prompt(self):
        spec = self.v3_generated_spec()
        representation = spec["semantic_plan"]["representation_plan"]
        representation.update({
            "kind": "metaphor-assisted",
            "cognitive_translation_steps": 1,
            "literal_rejected_reason": (
                "The literal microscopic structure is not recognizable at report scale."),
            "added_explanatory_value": (
                "One familiar outline orients the literal evidence-native structure."),
        })
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("metaphor-assisted", prompt)
        self.assertIn("not recognizable at report scale", prompt)

    def test_v3_composite_keeps_generated_art_text_free_and_data_deterministic(self):
        spec = self.v3_generated_spec()
        spec.update({
            "archetype": "quantitative",
            "render_route": "composite",
            "visual_anchor": "Two text-free orientation objects above one compact comparison",
            "exact_text": ["Category", "Outcome (units)"],
            "annotation_plan": {
                "panel_labels": [], "callouts": [],
                "rationale": "One compact comparison needs no panel letter.",
            },
            "data": {"panels": [{
                "id": "main",
                "x_axis": {"label": "Category"},
                "y_axis": {"label": "Outcome (units)"},
                "series": [{"points": [{"y_interval": [1.0, 2.0]}]}],
                "contrasts": [],
            }]},
            "plot_design": {
                "chart_type": "paired point estimates",
                "encoding": "Position shows the verified means; whiskers show uncertainty.",
                "reader_path": ["Recognize anchors", "Compare means", "Read uncertainty"],
                "style_rationale": "Compact centred evidence with subordinate orientation art.",
                "typography": {"family": "Arial", "fallback": "Helvetica",
                               "upright_natural_width": True},
                "axis_semantics": [{
                    "panel_id": "main", "x_label": "Category",
                    "x_meaning": "The x-axis names the comparison categories.",
                    "y_label": "Outcome (units)",
                    "y_meaning": "The y-axis shows the measured outcome in units.",
                }],
                "caption_axis_summary": "Categories are on x; measured units are on y.",
                "numeric_annotation_attachment": "Values sit beside their marks.",
                "uncertainty_display": {
                    "present": True, "encoding": "Whiskers show intervals.",
                    "attachment": "Each whisker passes through its mean.",
                },
                "axis_label_placement": {
                    "x_orientation": "horizontal", "x_location": "below-data-region",
                    "y_orientation": "vertical", "y_location": "outside-data-region",
                },
                "legend_plan": {
                    "needed": False,
                    "reason": "The interval glyph is conventional and caption-defined.",
                    "placement": "none",
                },
            },
            "composite_plan": {
                "generated_assets": [{
                    "id": "anchor-pair",
                    "purpose": "Orient the reader to the two compared categories.",
                    "placement": "Above the corresponding deterministic marks.",
                    "text_free": True,
                    "encodes_magnitude": False,
                }],
                "deterministic_evidence_layer": (
                    "All axes, means, intervals, values, and typography."
                ),
                "integration_strategy": (
                    "Place the proportional text-free cutouts in reserved non-data space."
                ),
                "balance_rationale": "The anchors and plot share one compact vertical stack.",
                "intrinsic_aspect_preserved": True,
            },
        })
        spec["semantic_plan"]["panel_jobs"] = []
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = [
            "Category", "Outcome (units)"]
        spec["semantic_plan"]["quantitative_decision"].update({
            "verified_numbers_available": True,
            "numbers_carry_primary_message": True,
            "reason": "The exact means and intervals carry the message.",
        })
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("COMPOSITE INTEGRATION", prompt)
        self.assertIn("text-free", prompt)
        self.assertIn("EXACT DETERMINISTIC TEXT MANIFEST", prompt)

    def test_v3_identity_hybrid_keeps_canonical_art_text_free(self):
        spec = self.v3_generated_spec()
        spec["render_route"] = "hybrid"
        spec["generated_text"] = []
        spec["overlay"] = {
            "font_family": "Arial",
            "font_fallback": "Helvetica",
            "text_color": "#161616",
            "labels": [
                {"text": item, "x": 0.1, "y": 0.1 + index * 0.1,
                 "anchor": "left", "size_px": 96}
                for index, item in enumerate(spec["exact_text"])
                if item != spec["title"]
            ],
        }
        spec["semantic_plan"]["cross_view_identity"] = [{
            "entity": "signal",
            "views": ["source", "filtered"],
            "invariant_features": ["position", "shape", "membership"],
            "reason": "Only the declared filter may change visibility.",
        }]
        prompt = MODULE.build_prompt(
            spec, self.profiles, self.archetypes,
            writing_styles=self.writing_styles)
        self.assertIn("AUTHORING ROUTE\nhybrid", prompt)
        self.assertIn("identity-preserving geometry layer", prompt)
        self.assertIn("RESERVED DETERMINISTIC OVERLAY COPY", prompt)
        self.assertNotIn("TEXT THE IMAGE MODEL MAY RENDER", prompt)

    def test_structured_data_is_preserved(self):
        spec = self.minimal_spec()
        spec["data"] = {
            "estimate": 21.0,
            "interval": [13.9, 29.8],
            "unit": "percentage points",
        }
        prompt = MODULE.build_prompt(spec, self.profiles, self.archetypes)
        self.assertIn('"estimate": 21.0', prompt)
        self.assertIn('"interval": [', prompt)
        self.assertIn('"unit": "percentage points"', prompt)

    def test_invalid_spec_fails_before_prompting(self):
        with self.assertRaisesRegex(ValueError, "exact_text"):
            MODULE.build_prompt(
                {"purpose": "x", "title": "y", "story": ["z"]},
                self.profiles,
                self.archetypes,
            )

    def test_invalid_render_context_fails(self):
        spec = self.minimal_spec()
        spec["render_context"] = "poster"
        with self.assertRaisesRegex(ValueError, "render_context"):
            MODULE.build_prompt(spec, self.profiles, self.archetypes)

    def test_domain_native_archetypes_are_available(self):
        self.assertIn("anatomical-mechanism", self.archetypes)
        self.assertIn("cutaway", self.archetypes)
        self.assertIn("study-overview", self.archetypes)

    def test_main_writes_prompt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "spec.json")
            out_path = os.path.join(tmp, "prompt.txt")
            with open(spec_path, "w", encoding="utf-8") as stream:
                json.dump(self.minimal_spec(), stream)
            code = MODULE.main(["--spec", spec_path, "--out", out_path])
            self.assertEqual(code, 0)
            with open(out_path, "r", encoding="utf-8") as stream:
                self.assertIn("A clean mechanism", stream.read())


if __name__ == "__main__":
    unittest.main()
