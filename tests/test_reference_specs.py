"""Every `json figure-spec` block in the references must actually pass.

This keeps the documented specification shape from drifting away from the
validators: a reference example that stops passing fails the suite.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import figure_spec_tools  # noqa: E402
import qa_quantitative_geometry  # noqa: E402
import render_quantitative_figure  # noqa: E402


FENCE = re.compile(r"```json figure-spec\n(.*?)```", re.S)


def documented_specs():
    found = []
    for path in sorted((ROOT / "references").glob("*.md")):
        for match in FENCE.finditer(path.read_text(encoding="utf-8")):
            found.append((path.name, json.loads(match.group(1))))
    return found


class ReferenceSpecTests(unittest.TestCase):
    def test_reference_examples_exist(self):
        names = [name for name, _spec in documented_specs()]
        self.assertIn("quantitative-figure-guide.md", names)

    def test_every_documented_spec_lints_clean(self):
        for name, spec in documented_specs():
            with self.subTest(reference=name, figure=spec.get("figure_id")):
                report = figure_spec_tools.lint(spec)
                self.assertEqual(report["status"], "pass", report["errors"])
                self.assertEqual(report["hints"], [])

    def test_documented_deterministic_specs_render_and_pass_geometry_qa(self):
        for name, spec in documented_specs():
            if spec.get("render_route") != "deterministic":
                continue
            with self.subTest(reference=name, figure=spec.get("figure_id")):
                with tempfile.TemporaryDirectory() as directory:
                    image = Path(directory) / "figure.png"
                    geometry = Path(directory) / "figure.geometry.json"
                    manifest = render_quantitative_figure.render(spec, image, geometry)
                    report = qa_quantitative_geometry.audit_geometry(spec, image, manifest)
                    self.assertEqual(report["status"], "pass", report["errors"])
                    declared = spec["layout_plan"]["mobile_preview"]["primary_labels"]
                    resolved = {
                        item["text"]: item["mobile_height_px"]
                        for item in manifest["primary_labels_resolved"]}
                    for label in declared:
                        self.assertGreaterEqual(resolved[label], 10.0, label)


if __name__ == "__main__":
    unittest.main()
