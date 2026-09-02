"""Claim receipts: the audit as the reader sees it (chat block, colophon
numbers, exporter appendix) and the gates that keep it honest."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "skills" / "grounded"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claim_receipts  # noqa: E402
import validate_review  # noqa: E402


DOI_A = "10.1000/alpha"
DOI_B = "10.1000/beta"

REVIEW = (
    "## Does it work?\n\n"
    "**TL;DR** — Mostly.\n\n"
    "### The trial\n\n"
    "The trial found a 12% reduction [Smith et al. 2024](https://doi.org/10.1000/alpha). "
    "Mechanism work agrees [Lee & Park 2023](https://doi.org/10.1000/beta), "
    "[Smith et al. 2024](https://doi.org/10.1000/alpha).\n\n"
    "**Sources**\n\n"
    "**Lee J, Park S (2023)** Mechanism. *Cells*. https://doi.org/10.1000/beta\n\n"
    "**Smith A, Jones B, Khan C (2024)** The trial. *BMJ*. https://doi.org/10.1000/alpha\n"
)


def audit(verdict_b="supported"):
    return {
        "review": "review.md", "created": "2026-09-01",
        "claims": [
            {"id": "C001", "claim": "The trial found a 12% reduction.",
             "location": "paragraph 1, sentence 1", "dois": [DOI_A],
             "numbers": ["12%"],
             "adjudications": [{"doi": DOI_A, "verdict": "supported",
                                "quote": "a 12% reduction", "note": "",
                                "tier": "fulltext"}]},
            {"id": "C002", "claim": "Mechanism work agrees.",
             "location": "paragraph 1, sentence 2", "dois": [DOI_B, DOI_A],
             "numbers": [],
             "adjudications": [
                 {"doi": DOI_B, "verdict": verdict_b, "quote": "agrees",
                  "note": "", "tier": "abstract"},
                 {"doi": DOI_A, "verdict": "partial", "quote": "agrees",
                  "note": "full text gives the direction, not the mechanism",
                  "tier": "fulltext"}]},
        ],
    }


class SummaryTests(unittest.TestCase):
    def test_counts_pairs_tiers_and_sources(self):
        summary = claim_receipts.summarize_audit(audit())
        self.assertEqual(summary["claims"], 2)
        self.assertEqual(summary["pairs"], 3)
        self.assertEqual(summary["supported_fulltext"], 1)
        self.assertEqual(summary["supported_abstract"], 1)
        self.assertEqual(summary["partial"], 1)
        self.assertEqual(summary["contradicted"], 0)
        self.assertEqual(summary["sources"], 2)
        self.assertEqual(summary["sources_fulltext"], 1)
        self.assertEqual(summary["sources_abstract"], 1)

    def test_summary_sentence_reads_like_the_colophon(self):
        sentence = claim_receipts.summary_sentence(
            claim_receipts.summarize_audit(audit()))
        self.assertEqual(
            sentence,
            "2 cited sentences · 3 source checks · 1 supported at full text · "
            "1 at abstract · 1 partial · 0 contradicted")

    def test_only_supported_and_partial_pairs_can_ship(self):
        self.assertEqual(claim_receipts.release_blockers(
            claim_receipts.summarize_audit(audit())), [])
        blocked = audit(verdict_b="contradicted")
        blocked["claims"][0]["adjudications"][0]["verdict"] = "pending"
        blocked["claims"][1]["adjudications"][1]["verdict"] = "not_found"
        problems = claim_receipts.release_blockers(
            claim_receipts.summarize_audit(blocked))
        self.assertEqual(len(problems), 3)
        self.assertIn("contradicted", problems[0])
        self.assertIn("pending", problems[1])
        self.assertIn("not_found", problems[2])
        decorative = audit()
        decorative["claims"][1]["adjudications"][1]["verdict"] = "unverifiable"
        self.assertTrue(any("unverifiable" in e for e in claim_receipts.receipt_errors(
            claim_receipts.attach_receipts(REVIEW, decorative))))


class LabelTests(unittest.TestCase):
    def test_labels_come_from_the_review_links_first(self):
        labels = claim_receipts.labels_from_markdown(REVIEW)
        self.assertEqual(labels[DOI_A], "Smith et al. 2024")
        self.assertEqual(labels[DOI_B], "Lee & Park 2023")

    def test_sources_entry_is_the_fallback_label(self):
        sources_only = "**Sources**\n\n**Van Laren J, Delate T (2026)** T. *J*. https://doi.org/10.1/x\n"
        self.assertEqual(claim_receipts.labels_from_markdown(sources_only)["10.1/x"],
                         "Van Laren & Delate 2026")


class AttachTests(unittest.TestCase):
    def test_attach_annotates_sources_and_stamps_the_tally(self):
        out = claim_receipts.attach_receipts(REVIEW, audit(), receipts_name="r-receipts.md")
        self.assertIn("https://doi.org/10.1000/alpha · 2 claims · full text", out)
        self.assertIn("https://doi.org/10.1000/beta · 1 claim · abstract", out)
        block = claim_receipts.receipts_block(out)
        self.assertEqual(block.strip().splitlines(), [
            "**Receipts**", "",
            "*2 cited sentences · 3 source checks · 1 supported at full text · "
            "1 at abstract · 1 partial · 0 contradicted — every pair's verbatim "
            "quote is in `r-receipts.md`.*"])
        self.assertEqual(claim_receipts.count_receipt_lines(out), 3)
        self.assertEqual(claim_receipts.receipt_errors(out), [])

    def test_receipts_document_lists_every_sentence_with_its_quotes(self):
        doc = claim_receipts.render_receipts_document(
            audit(), claim_receipts.labels_from_markdown(REVIEW),
            title="Does it work?", review_name="review.md")
        self.assertTrue(doc.startswith("# Claim receipts — Does it work?"))
        self.assertIn("## C001 · ¶1 s1\n\n> The trial found a 12% reduction.\n\n"
                      "- **Smith et al. 2024** · full text · supported — “a 12% reduction”", doc)
        self.assertIn("- **Smith et al. 2024** · full text · partial — “agrees” "
                      "(full text gives the direction, not the mechanism)", doc)

    def test_attach_is_idempotent_and_strip_restores_the_review(self):
        once = claim_receipts.attach_receipts(REVIEW, audit())
        twice = claim_receipts.attach_receipts(once, audit())
        self.assertEqual(once, twice)
        stripped = claim_receipts.strip_receipts(once)
        self.assertNotIn("**Receipts**", stripped)
        self.assertIn("· 2 claims · full text", stripped)
        self.assertEqual(claim_receipts.strip_source_annotations(stripped), REVIEW)

    def test_receipt_errors_catch_pending_contradicted_and_malformed(self):
        broken = claim_receipts.attach_receipts(REVIEW, audit(verdict_b="contradicted"))
        errors = claim_receipts.receipt_errors(broken)
        self.assertTrue(any("contradicted" in e for e in errors))
        malformed = REVIEW + "\n**Receipts**\n\nnot a receipt\n"
        self.assertTrue(any("tally" in e for e in claim_receipts.receipt_errors(malformed)))

    def test_receipt_prints_the_bridge(self):
        bridged = audit()
        bridged["claims"][1]["adjudications"][0]["bridge"] = "agrees = concurs"
        doc = claim_receipts.render_receipts_document(bridged)
        self.assertIn("supported — “agrees” (bridge: agrees = concurs)", doc)

    def test_snippet_strips_markdown_and_table_pipes(self):
        self.assertEqual(
            claim_receipts.snippet("The [Rome IV](https://x) rule **dropped** it."),
            "The Rome IV rule dropped it.")
        self.assertEqual(
            claim_receipts.snippet("| *L. reuteri* | NNT 2.6 | Moderate |"),
            "L. reuteri · NNT 2.6 · Moderate")


class ValidatorTests(unittest.TestCase):
    def test_validator_ignores_receipts_as_prose_and_reports_them(self):
        attached = claim_receipts.attach_receipts(REVIEW, audit())
        result = validate_review.validate_review(attached, style="bullets", size="small")
        self.assertNotIn("Sources must be the terminal review section", result.errors)
        self.assertEqual(result.metrics["claim_receipts"], 3)
        bare = validate_review.validate_review(REVIEW, style="bullets", size="small")
        self.assertEqual(result.metrics["body_words"], bare.metrics["body_words"])

    def test_validator_rejects_unfinished_receipts(self):
        attached = claim_receipts.attach_receipts(REVIEW, audit(verdict_b="contradicted"))
        result = validate_review.validate_review(attached, style="bullets", size="small")
        self.assertTrue(any("contradicted" in e for e in result.errors))


class CliTests(unittest.TestCase):
    def test_receipts_command_refuses_a_pending_audit_and_attaches_a_finished_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = Path(tmp) / "review.md"
            review.write_text(REVIEW, encoding="utf-8")
            pending = audit()
            pending["claims"][0]["adjudications"][0]["verdict"] = "pending"
            audit_path = Path(tmp) / "claims_audit.json"
            audit_path.write_text(json.dumps(pending))
            run = subprocess.run(
                [sys.executable, str(SCRIPTS / "verify_claims.py"), "receipts",
                 "--audit", str(audit_path), "--review", str(review)],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stdout)
            self.assertEqual(review.read_text(encoding="utf-8"), REVIEW)
            audit_path.write_text(json.dumps(audit()))
            run = subprocess.run(
                [sys.executable, str(SCRIPTS / "verify_claims.py"), "receipts",
                 "--audit", str(audit_path), "--review", str(review)],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            stamped = review.read_text(encoding="utf-8")
            self.assertIn("**Receipts**", stamped)
            self.assertIn("`review-receipts.md`", stamped)
            receipts = (Path(tmp) / "review-receipts.md").read_text(encoding="utf-8")
            self.assertIn("## C002 · ¶1 s2", receipts)


if __name__ == "__main__":
    unittest.main()
