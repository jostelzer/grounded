import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import qa_figure  # noqa: E402


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
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "figure.png"
            Image.new("RGB", (1536, 1024), "white").save(image)
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
        from PIL import Image

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        Image.new("RGB", (width, height), "white").save(tmp.name)
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
