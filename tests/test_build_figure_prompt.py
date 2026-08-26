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
