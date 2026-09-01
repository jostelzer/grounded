import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_production  # noqa: E402
import validate_review  # noqa: E402


class ProductionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return name

    def synthesis(self, claims=5):
        blocks = []
        for index in range(1, claims + 1):
            blocks.append(
                f"### C{index}. Claim {index} is supported by the evidence.\n"
                "- strength: moderate — one direct study\n"
                "- evidence: trial, n=100, bounded result [@K1]\n"
                "- contrary: none found — searched\n"
                "- boundary: the studied population and duration\n"
                "- depends-on: —\n"
                "- numbers: n=100\n"
            )
        return (
            "# Synthesis — test question\n\n"
            "## Verdict\n\nThe evidence supports a bounded answer.\n\n"
            "## Throughline\n\nDirect evidence narrows the broad claim.\n\n"
            "## Claims\n\n" + "\n".join(blocks) +
            "\n## Patterns\n\n- P1. Directness changes confidence (C1, C2).\n\n"
            "## Open\n\n- A larger trial would settle the remaining uncertainty.\n"
        )

    def base_manifest(self):
        search = {
            "schema_version": 1,
            "records": [
                {
                    "angle": f"angle {index}",
                    "angle_id": f"angle-{index}",
                    "requested_query_or_seed": f"query {index}",
                    "lane": "primary",
                    "method": "keyword",
                    "citation_direction": None,
                    "completed": True,
                    "accepted": 1,
                }
                for index in range(3)
            ],
        }
        self.write_json("search-manifest.json", search)
        self.write_json("sources.json", {"entries": [{"key": "K1"}]})
        self.write_json(
            "fulltext-manifest.json",
            {
                "schema_version": 1,
                "summary": {"counted_with_complete_notes": 2},
                "records": [],
            },
        )
        (self.root / "synthesis.md").write_text(
            self.synthesis(), encoding="utf-8")
        (self.root / "review.md").write_text("review", encoding="utf-8")
        return {
            "schema_version": 1,
            "case_id": "case-one",
            "size": "small",
            "style": "popsci",
            "output_format": "journal-pdf",
            "render": {"figure_max_height_mm": 92},
            "evidence": {
                "ledger": "sources.json",
                "search_manifest": "search-manifest.json",
                "fulltext_manifest": "fulltext-manifest.json",
                "synthesis": "synthesis.md",
                "frozen": True,
                "unresolved_issues": [],
                "accepted_warnings": [],
            },
        }

    @staticmethod
    def semantic_block():
        return {
            "review": "review.md",
            "manual_checks": {
                name: True for name in audit_production.SEMANTIC_CHECKS
            },
            "visual_jobs": [
                {
                    "id": "whole-answer",
                    "kind": "synthesis",
                    "question": "What is the whole evidence-based answer?",
                    "evidence_keys": ["C1", "P1"],
                },
                {
                    "id": "key-comparison",
                    "kind": "comparison",
                    "question": "Where does the decisive comparison change?",
                    "evidence_keys": ["C2"],
                },
            ],
            "unresolved_issues": [],
            "accepted_warnings": [],
        }

    def test_evidence_gate_passes_live_search_and_synthesis_inputs(self):
        result = audit_production.audit_production(
            self.base_manifest(), base_dir=self.root, target_stage="evidence")
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["metrics"]["completed_stages"], ["evidence"])
        self.assertEqual(result["metrics"]["stages"]["evidence"]["claims"], 5)

    def test_semantic_gate_runs_validator_and_requires_whole_answer_first(self):
        manifest = self.base_manifest()
        manifest["semantic"] = self.semantic_block()
        validation = validate_review.ValidationResult(
            (), (), {"style": "popsci", "size": "small"})
        with mock.patch.object(
            audit_production.validate_review, "validate_review",
            return_value=validation,
        ) as validator:
            result = audit_production.audit_production(
                manifest, base_dir=self.root, target_stage="semantic")
        self.assertEqual(result["status"], "pass", result["errors"])
        validator.assert_called_once()

        manifest["semantic"]["visual_jobs"].reverse()
        with mock.patch.object(
            audit_production.validate_review, "validate_review",
            return_value=validation,
        ):
            result = audit_production.audit_production(
                manifest, base_dir=self.root, target_stage="semantic")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("whole-answer synthesis" in error
                            for error in result["errors"]))

    def test_live_warnings_must_be_reviewed_exactly_once(self):
        manifest = self.base_manifest()
        manifest["semantic"] = self.semantic_block()
        validation = validate_review.ValidationResult(
            (), ("term link may be missing",),
            {"style": "popsci", "size": "small"},
        )
        with mock.patch.object(
            audit_production.validate_review, "validate_review",
            return_value=validation,
        ):
            result = audit_production.audit_production(
                manifest, base_dir=self.root, target_stage="semantic")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("unreviewed warning" in error
                            for error in result["errors"]))

        manifest["semantic"]["accepted_warnings"] = [{
            "message": "review: term link may be missing",
            "reason": "The first occurrence is already expanded and linked.",
        }]
        with mock.patch.object(
            audit_production.validate_review, "validate_review",
            return_value=validation,
        ):
            result = audit_production.audit_production(
                manifest, base_dir=self.root, target_stage="semantic")
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_iteration_overrun_requires_a_diagnosis(self):
        errors, warnings = [], []
        audit_production._iteration_budget(
            4, limit=3, exception=None, label="figure attempts",
            errors=errors, warnings=warnings)
        self.assertTrue(any("iteration_exception" in error for error in errors))

        errors, warnings = [], []
        audit_production._iteration_budget(
            4,
            limit=3,
            exception={
                "failure_class": "figure-copy",
                "reason": "The selected candidate retained one incorrect required label twice.",
                "next_action": "Repair only that label and rerun QA.",
            },
            label="figure attempts",
            errors=errors,
            warnings=warnings,
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_release_width_must_equal_the_live_figure_qa_width(self):
        figures = [{
            "job_id": "whole-answer",
            "metrics": {
                "image_sha256": "abc",
                "evaluated_rendered_width_mm": 82.0,
            },
        }]
        records = [{"sha256": "abc", "rendered_width_mm": 74.0}]
        errors = audit_production.release_figure_errors(figures, records)
        self.assertTrue(any("82.0 mm" in error and "74.0 mm" in error
                            for error in errors))
        records[0]["rendered_width_mm"] = 82.0
        self.assertEqual(
            audit_production.release_figure_errors(figures, records), [])


if __name__ == "__main__":
    unittest.main()
