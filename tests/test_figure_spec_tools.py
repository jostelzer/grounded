import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import figure_contract  # noqa: E402
import figure_spec_tools  # noqa: E402


def _complete(value, *, replacement="Filled by the author"):
    """Replace every scaffold placeholder so the skeleton can pass."""
    if isinstance(value, str):
        if value.startswith(figure_contract.PLACEHOLDER_PREFIX):
            return replacement
        return value
    if isinstance(value, dict):
        return {key: _complete(item, replacement=replacement)
                for key, item in value.items() if key != "_todo"}
    if isinstance(value, list):
        return [_complete(item, replacement=replacement) for item in value]
    return value


def completed_deterministic(panels=1):
    spec = figure_spec_tools.scaffold(
        route="deterministic", archetype="quantitative", review_style="popsci",
        panels=panels, figure_id="tool-test")
    spec = _complete(spec)
    spec["layout_plan"]["mobile_preview"]["primary_labels"] = ["No difference"]
    spec["evidence_keys"] = ["Example2024"]
    return spec


class ScaffoldTests(unittest.TestCase):
    def test_every_route_scaffold_fails_lint_only_on_placeholders(self):
        combinations = (
            ("deterministic", "quantitative"),
            ("generated", "mechanism"),
            ("generated", "cutaway"),
            ("composite", "quantitative"),
        )
        for route, archetype in combinations:
            with self.subTest(route=route, archetype=archetype):
                spec = figure_spec_tools.scaffold(
                    route=route, archetype=archetype, review_style="scientific",
                    panels=2 if archetype == "quantitative" else 1,
                    figure_id=f"scaffold-{archetype}")
                self.assertTrue(figure_contract.find_placeholders(spec))
                report = figure_spec_tools.lint(spec)
                self.assertEqual(report["status"], "fail")
                unexpected = [
                    error for error in report["errors"]
                    if not error.startswith("placeholder:")]
                self.assertEqual(unexpected, [])
                self.assertEqual(report["hints"], [])

    def test_scaffold_rejects_incoherent_route_and_archetype(self):
        with self.assertRaisesRegex(ValueError, "archetype=quantitative"):
            figure_spec_tools.scaffold(
                route="deterministic", archetype="mechanism",
                review_style="popsci", panels=1, figure_id="x")
        with self.assertRaisesRegex(ValueError, "generated route"):
            figure_spec_tools.scaffold(
                route="deterministic", archetype="cutaway",
                review_style="popsci", panels=1, figure_id="x")

    def test_completed_deterministic_scaffold_passes_lint_and_renders(self):
        spec = completed_deterministic()
        report = figure_spec_tools.lint(spec)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertTrue(any("primary label" in item for item in report["warnings"]))

    def test_two_panel_scaffold_carries_matching_panel_labels_and_jobs(self):
        spec = completed_deterministic(panels=2)
        self.assertEqual(spec["annotation_plan"]["panel_labels"], ["A", "B"])
        self.assertEqual(
            [job["label"] for job in spec["semantic_plan"]["panel_jobs"]], ["A", "B"])
        self.assertEqual(
            [panel["panel_label"] for panel in spec["data"]["panels"]], ["A", "B"])
        report = figure_spec_tools.lint(spec)
        self.assertEqual(report["status"], "pass", report["errors"])


class LintTests(unittest.TestCase):
    def test_lint_reports_every_defect_at_once_with_key_hints(self):
        spec = completed_deterministic()
        del spec["communication_goal"]["visual_question"]
        priority = spec["semantic_plan"]["information_priority"]
        priority["primary"] = priority.pop("primary_entities")
        spec["plot_design"]["legend_plan"]["placement"] = "adjacent"
        spec["semantic_plan"]["uncertainty_encodings"][0]["source"] = (
            spec["semantic_plan"]["uncertainty_encodings"][0].pop("source_of_uncertainty"))
        report = figure_spec_tools.lint(spec)
        self.assertEqual(report["status"], "fail")
        self.assertGreaterEqual(len(report["errors"]), 3)
        joined = "\n".join(report["errors"])
        self.assertIn("visual_question", joined)
        self.assertIn("primary_entities", joined)
        self.assertIn("legend", joined)
        hints = "\n".join(report["hints"])
        self.assertIn("'primary'", hints)
        self.assertIn("primary_entities", hints)
        self.assertIn("source_of_uncertainty", hints)

    def test_lint_flags_exact_text_drift_both_ways(self):
        spec = completed_deterministic()
        spec["exact_text"].remove("Study A")
        spec["exact_text"].append("Never drawn")
        report = figure_spec_tools.lint(spec, dry_run_render=False)
        joined = "\n".join(report["errors"])
        self.assertIn("'Study A'", joined)
        self.assertIn("'Never drawn'", joined)

    def test_lint_surfaces_layout_collisions_before_inspection(self):
        spec = completed_deterministic()
        for row in spec["data"]["panels"][0]["rows"]:
            row["label"] = "A very long value label that will surely collide"
        spec["exact_text"] = [
            item for item in spec["exact_text"]
            if item not in {"0.81", "0.87", "0.98"}
        ] + ["A very long value label that will surely collide"]
        report = figure_spec_tools.lint(spec)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(error.startswith("layout") for error in report["errors"]),
                        report["errors"])

    def test_lint_rejects_a_tick_label_declared_as_primary(self):
        spec = completed_deterministic()
        spec["layout_plan"]["mobile_preview"]["primary_labels"] = ["Study A"]
        report = figure_spec_tools.lint(spec)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("never primary" in error for error in report["errors"]),
                        report["errors"])


class PreviewTests(unittest.TestCase):
    def test_preview_writes_phone_view_and_measures_primary_labels(self):
        spec = completed_deterministic()
        with tempfile.TemporaryDirectory() as directory:
            result = figure_spec_tools.preview(spec, Path(directory))
            self.assertEqual(result["status"], "pass", result["errors"])
            self.assertEqual(result["preview_size"][0], 390)
            self.assertTrue(Path(result["preview"]).is_file())
            self.assertTrue(Path(result["geometry"]).is_file())
            self.assertEqual(result["geometry_qa"], "pass")
            labels = {item["text"]: item for item in result["primary_labels"]}
            self.assertIn("No difference", labels)
            self.assertGreaterEqual(labels["No difference"]["mobile_height_px"], 10.0)
            self.assertTrue(labels["No difference"]["passes"])
            self.assertGreaterEqual(
                result["smallest_supporting_label"]["effective_pt_at_journal_width"], 6.5)

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spec.json"
            code = figure_spec_tools.main([
                "scaffold", "--route", "deterministic", "--archetype", "quantitative",
                "--review-style", "bullets", "--figure-id", "cli", "--out", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(figure_spec_tools.main(["lint", "--spec", str(path)]), 1)
            spec = _complete(json.loads(path.read_text(encoding="utf-8")))
            spec["layout_plan"]["mobile_preview"]["primary_labels"] = ["No difference"]
            path.write_text(json.dumps(spec), encoding="utf-8")
            self.assertEqual(figure_spec_tools.main(["lint", "--spec", str(path)]), 0)
            self.assertEqual(figure_spec_tools.main([
                "preview", "--spec", str(path), "--out-dir", str(Path(directory) / "p")]), 0)


if __name__ == "__main__":
    unittest.main()
