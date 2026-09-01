import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import audit_fulltexts  # noqa: E402


class FulltextAuditTests(unittest.TestCase):
    @staticmethod
    def ledger():
        return {
            "entries": [
                {
                    "key": "Smith2024signal",
                    "doi": "10.1000/signal",
                    "title": "A durable signal in human cells",
                    "abstract": " ".join(["abstract"] * 70),
                },
                {
                    "key": "Jones2023pathway",
                    "doi": "10.1000/pathway",
                    "title": "A second cellular pathway",
                    "abstract": "",
                },
            ]
        }

    @staticmethod
    def article(title, doi):
        filler = " ".join(["measured biological response"] * 420)
        return (
            f"# {title}\nDOI: {doi}\n\n## Abstract\nSummary.\n\n"
            f"## Methods\nRandomized cohort design. {filler}\n\n"
            "## Results\nThe measured response increased.\n\n"
            "## Discussion\nThe observational subset limits causal inference.\n"
        )

    @staticmethod
    def notes():
        return (
            "# Retained full-text audit\n\n"
            "- `Smith2024signal` — Randomized cohort design with 100 participants. "
            "The response increased. The small sample limits inference. This is "
            "supporting evidence for the mechanism.\n"
            "- `Jones2023pathway` — Cohort analysis of 80 patients. Results showed "
            "a lower response. Observational confounding is a limitation. Used as "
            "contrary evidence.\n"
        )

    def test_authenticity_categories_and_distinct_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            valid = self.article(
                "A durable signal in human cells", "10.1000/signal"
            )
            (folder / "Smith2024signal.txt").write_text(valid, encoding="utf-8")
            (folder / "Jones2023pathway.txt").write_text(valid, encoding="utf-8")
            (folder / "challenge.html").write_text(
                "<html><title>Just a moment...</title><body>Enable JavaScript "
                "and cookies to continue. cf-chl-token</body></html>",
                encoding="utf-8",
            )
            (folder / "denied.html").write_text(
                "<html><body><h1>Access denied</h1>You do not have permission "
                "to access this resource.</body></html>", encoding="utf-8"
            )
            (folder / "shell.html").write_text(
                "<html><body>Article title. Authors. View PDF.</body></html>",
                encoding="utf-8",
            )
            (folder / "abstract.html").write_text(
                "<html><body><h2>Abstract</h2>" + ("summary " * 250) +
                "</body></html>", encoding="utf-8"
            )
            manifest = audit_fulltexts.build_manifest(
                self.ledger(), folder, notes=self.notes(), min_words=1000
            )
            statuses = {record["path"]: record["status"] for record in manifest["records"]}
            self.assertEqual(statuses["Smith2024signal.txt"], "valid_fulltext")
            self.assertEqual(statuses["Jones2023pathway.txt"], "duplicate")
            self.assertEqual(statuses["challenge.html"], "challenge_page")
            self.assertEqual(statuses["denied.html"], "access_denied")
            self.assertEqual(statuses["shell.html"], "metadata_shell")
            self.assertEqual(statuses["abstract.html"], "abstract_only")
            self.assertEqual(manifest["summary"]["valid_distinct"], 1)
            self.assertEqual(manifest["summary"]["counted_with_complete_notes"], 1)

    def test_missing_notes_do_not_count_an_authentic_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Smith2024signal.txt").write_text(
                self.article("A durable signal in human cells", "10.1000/signal"),
                encoding="utf-8",
            )
            manifest = audit_fulltexts.build_manifest(
                self.ledger(), folder, min_words=1000
            )
            record = manifest["records"][0]
            self.assertEqual(record["status"], "valid_fulltext")
            self.assertFalse(record["counted"])

    def test_reading_evidence_keeps_verification_separate(self):
        ledger = self.ledger()
        manifest = {
            "records": [{
                "ledger_key": "Jones2023pathway",
                "status": "valid_fulltext",
                "sha256": "a" * 64,
                "notes": {"complete": True},
            }]
        }
        audit_fulltexts.update_reading_evidence(ledger, manifest)
        smith, jones = ledger["entries"]
        self.assertEqual(smith["reading_evidence"]["status"], "eligible")
        self.assertEqual(jones["reading_evidence"]["status"], "eligible")
        self.assertEqual(jones["reading_evidence"]["fulltext_sha256"], "a" * 64)
        self.assertNotIn("status", smith)

    def test_only_a_structured_override_can_permit_a_fulltext_shortfall(self):
        override = {
            "reason": "The complete field contains fewer eligible full texts.",
            "saturation_evidence": ["all index records were screened"],
            "allowed_shortfalls": ["sources", "fulltexts"],
        }
        self.assertTrue(audit_fulltexts.permits_fulltext_shortfall(override))
        with self.assertRaisesRegex(ValueError, "substantive reason"):
            audit_fulltexts.permits_fulltext_shortfall({
                "reason": "thin",
                "saturation_evidence": ["claim"],
                "allowed_shortfalls": ["fulltexts"],
            })


if __name__ == "__main__":
    unittest.main()
