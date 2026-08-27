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


if __name__ == "__main__":
    unittest.main()
