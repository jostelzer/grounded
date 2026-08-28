import copy
import importlib.util
import json
import os
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    def test_default_prompt_defines_arial_and_rejects_serif(self):
        prompt = MODULE.build_prompt(
            self.minimal_spec(), self.profiles, self.archetypes
        )
        self.assertIn("Render every character in Arial throughout", prompt)
        self.assertIn("serif typography", prompt)
        self.assertIn("#1A1A1A", prompt)
        self.assertIn("Context: article", prompt)
        self.assertIn("figure-native", prompt)

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
        self.assertIn("Render every character in Optima throughout", prompt)
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
