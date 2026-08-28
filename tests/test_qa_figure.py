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
            "render_route": "hybrid",
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
            "selected_route": "hybrid",
            "selected_asset": Path(path).name,
            "selected_sha256": sha256_file(path),
            "attempts": [
                {"kind": "generate", "asset": "one.png"},
                {"kind": "generate", "asset": "two.png"},
                {"kind": "compose", "asset": Path(path).name},
            ],
            "comparison": {
                "candidates_compared": 2,
                "selection_rationale": "The second candidate has the strongest focal structure.",
            },
            "hybrid": {
                "compositor": "compose_hybrid_figure.py",
                "base_asset": "two.png",
                "anisotropic_resize": False,
            },
            "fallback_reason": None,
            "hybrid_considered": True,
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

    def test_single_generated_candidate_is_release_blocking(self):
        def mutate(provenance):
            provenance["attempts"] = provenance["attempts"][1:]
            provenance["comparison"]["candidates_compared"] = 1

        result = self.audit(mutate_provenance=mutate)
        self.assertTrue(any("two generated candidates" in error for error in result["errors"]))
        self.assertTrue(any("comparison of at least two" in error for error in result["errors"]))


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
