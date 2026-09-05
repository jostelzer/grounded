"""Adversarial integrity checks using synthetic, non-evidentiary fixtures."""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/grounded/scripts"))
import audit_contract
import claim_context
import claim_evidence
import claim_receipts
import fetch_fulltext
import verify_claims

SCRIPT = Path(verify_claims.__file__)
DOI = "10.0000/context-fixture"
SOURCE = "## Methods\nWe compared two synthetic materials under dry conditions.\n## Results\nMaterial A lasted 8 hours.\nOnly dry conditions were tested.\n"


def pair_record():
    return {"meaning": {"comparison": "Two synthetic materials in dry conditions",
                         "outcome": "Material A endurance of 8 hours",
                         "scope": "No claim about wet conditions"},
            "context": [{"start_line": 1, "end_line": 5,
                         "reason": "Methods define conditions; result and note limit the outcome."}],
            "interpretation": "preserved",
            "rationale": "The endurance statement preserves the tested condition and material.",
            "limitations": "Synthetic fixture; no evidence about real materials."}


class ContextOperatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.review = self.root / "review.md"
        self.path = self.root / "audit.json"
        self.store = self.root / "evidence"
        self.review.write_text(f"Material A lasted 8 hours in dry conditions [source](https://doi.org/{DOI}).\n")
        claim_evidence.store_text(DOI, self.store, SOURCE, {"tier": "fulltext", "source": "synthetic"})
        self.run_cli("extract", "--review", str(self.review), "--audit", str(self.path))

    def run_cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def judge(self):
        record = self.root / "pair.json"
        record.write_text(json.dumps(pair_record()))
        self.run_cli("adjudicate", "--audit", str(self.path), "--packet", "C001#1",
                     "--verdict", "supported", "--quote", "Material A lasted 8 hours.",
                     "--context-review", str(record), "--evidence", str(self.store))

    def whole(self, figures=None, interpretation="preserved"):
        record = self.root / "whole.json"
        record.write_text(json.dumps({"takeaway": "The material's endurance was measured in dry conditions.",
            "basis": ["C001"], "interpretation": interpretation,
            "rationale": "The complete text makes no wet-condition extrapolation.",
            "limitations": "This is only a synthetic software fixture.", "figures": figures or []}))
        return self.run_cli("review-context", "--audit", str(self.path), "--record", str(record))

    def check(self, ok=True):
        return self.run_cli("check", "--audit", str(self.path), "--evidence", str(self.store), "--strict", ok=ok)

    def test_new_audit_cannot_release_on_quote_alone(self):
        audit = json.loads(self.path.read_text())
        self.assertEqual(audit["context_contract_version"], 1)
        self.run_cli("adjudicate", "--audit", str(self.path), "--packet", "C001#1",
                     "--verdict", "supported", "--quote", "Material A lasted 8 hours.", ok=False)
        self.judge()
        self.assertIn("whole-review", self.check(ok=False).stdout)
        self.whole()
        self.check()
        audit = json.loads(self.path.read_text())
        audit_contract.validate_release(audit, self.review.read_text(), self.path)
        receipts = claim_receipts.render_receipts_document(audit)
        self.assertIn("Inspected source lines 1–5", receipts)
        self.assertIn("Interpretation: preserved", receipts)

    def test_source_change_requires_fresh_inspection_even_if_quote_survives(self):
        self.judge()
        self.whole()
        file = self.store / (claim_evidence.doi_slug(DOI) + ".txt")
        file.write_text(SOURCE + "Correction: the test excluded one early failure.\n")
        self.assertIn("source changed since context inspection", self.check(ok=False).stdout.lower())

    def test_semantic_judgment_change_invalidates_whole_review(self):
        self.judge()
        self.whole()
        audit = json.loads(self.path.read_text())
        audit["claims"][0]["adjudications"][0]["note"] = "Changed interpretation."
        self.path.write_text(json.dumps(audit))
        self.assertIn("changed since whole-review", self.check(ok=False).stdout)

    def test_misleading_whole_review_is_recordable_but_not_releasable(self):
        self.judge()
        self.whole(interpretation="mismatch")
        self.assertIn("unresolved or misleading", self.check(ok=False).stdout)
        self.assertEqual(json.loads(self.path.read_text())["document_review"]["interpretation"], "mismatch")
        receipts = claim_receipts.render_receipts_document(json.loads(self.path.read_text()))
        self.assertIn("**mismatch**", receipts)
        self.assertIn("Scientific basis: C001", receipts)

    def test_figure_bytes_and_semantic_basis_are_required(self):
        figure = self.root / "figure.png"
        figure.write_bytes(b"synthetic asset identity; no visual judgment asserted")
        markdown = self.review.read_text() + "\n![](figure.png)\n"
        # Direct document recorder isolates figure validation from alt extraction.
        self.judge()
        audit = json.loads(self.path.read_text())
        record = {"takeaway": "Tested dry-condition endurance only", "basis": ["C001"],
                  "interpretation": "preserved", "rationale": "Scoped synthetic test",
                  "limitations": "Synthetic", "figures": []}
        with self.assertRaisesRegex(ValueError, "exactly the rendered"):
            claim_context.record_document(record, audit, markdown, self.review, self.path)
        record["figures"] = [{"path": "figure.png", "basis": ["C001"], "observed_meaning": "Synthetic dry-condition comparison"}]
        bound = claim_context.record_document(record, audit, markdown, self.review, self.path)
        figure.write_bytes(b"different")
        self.assertTrue(any("figure changed" in e for e in claim_context.document_errors(
            bound, audit, self.path, markdown, self.review)))

    def test_packets_expose_full_source_and_retain_table_rows(self):
        table = SOURCE + "\n## Table\nCondition | Endurance\nDry | 8 hours\nNote: wet conditions excluded\n"
        claim_evidence.store_text(DOI, self.store, table, {"tier": "fulltext", "source": "synthetic"})
        output = self.run_cli("packets", "--audit", str(self.path), "--evidence", str(self.store), "--blind").stdout
        self.assertIn("CONTEXT SOURCE:", output)
        self.assertIn("Condition | Endurance\n", output)
        self.assertIn("Note: wet conditions excluded", output)


class ContextValidationTests(unittest.TestCase):
    def test_invalid_context_ranges_and_mismatches_fail(self):
        for start, end in [(0, 1), (3, 2), (1, 90), (True, 2)]:
            record = pair_record()
            record["context"][0].update(start_line=start, end_line=end)
            with self.assertRaises(ValueError):
                claim_context.record_pair(record, SOURCE)
        record = claim_context.record_pair(pair_record(), SOURCE)
        record["interpretation"] = "unresolved"
        self.assertIn("covered elements require preserved interpretation", claim_context.pair_errors(record, SOURCE, "supported"))

    def test_qualitative_scope_is_valid_without_intervention_fields(self):
        record = pair_record()
        record["meaning"] = {"scope": "Participants described a shared experience in this setting."}
        self.assertEqual(claim_context.pair_errors(claim_context.record_pair(record, SOURCE), SOURCE), [])

    def test_nonassertive_draft_needs_no_invented_scientific_basis(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audit = {"claims": [{"id": "C001", "classification": "nonfactual"}]}
            record = {"takeaway": "A question, with no asserted answer.", "basis": [],
                      "interpretation": "preserved", "rationale": "No empirical assertions to infer from.",
                      "limitations": "The question is not answered by this draft.", "figures": []}
            result = claim_context.record_document(record, audit, "Is it durable?", root / "r.md", root / "a.json")
            self.assertFalse(claim_context.document_errors(result, audit))
            record["basis"] = ["C001"]
            with self.assertRaisesRegex(ValueError, "scientific basis"):
                claim_context.record_document(record, audit, "Is it durable?", root / "r.md", root / "a.json")

    def test_jats_keeps_table_headers_spans_notes_and_links_once(self):
        xml = '''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><abstract><p>Summary.</p></abstract></front>
        <body><sec><title>Results</title><p>See table.</p><table-wrap><label>Table 1</label>
        <caption><p>Endurance under the tested condition</p></caption><table><thead><tr><th>Material</th><th colspan="2">Hours</th></tr></thead>
        <tbody><tr><td>A</td><td>8</td><td>7–9</td></tr></tbody></table>
        <table-wrap-foot><fn><p>Dry conditions only.</p></fn></table-wrap-foot></table-wrap>
        <supplementary-material xlink:href="supp.pdf"><caption>Protocol supplement</caption></supplementary-material></sec></body></article>'''
        text, headings = fetch_fulltext.article_text(xml)
        self.assertIn("Material | Hours [colspan=2]", text)
        self.assertIn("A | 8 | 7–9", text)
        self.assertEqual(text.count("Dry conditions only."), 1)
        self.assertEqual(text.count("Endurance under the tested condition"), 1)
        self.assertIn("Source asset: supp.pdf", text)
        self.assertIn("Results", headings)

    def test_false_rejection_is_reported_separately_from_false_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def doc(verdict):
                return {"claims": [{"id": "C001", "claim": "Scoped synthetic result", "adjudications": [{"doi": DOI, "verdict": verdict}]}]}
            (root / "gold.json").write_text(json.dumps(doc("supported")))
            (root / "candidate.json").write_text(json.dumps(doc("unverifiable")))
            with contextlib.redirect_stdout(io.StringIO()):
                verify_claims.cmd_score(argparse.Namespace(audit=root / "candidate.json", gold=root / "gold.json",
                    min_agreement=None, qualify=False, report=root / "report.json"))
            report = json.loads((root / "report.json").read_text())
            self.assertEqual(report["false_rejection_percent"], 100)
            self.assertEqual(report["false_acceptances"], 0)
            self.assertEqual(report["positive_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
