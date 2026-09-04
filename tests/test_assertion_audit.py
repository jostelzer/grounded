"""Adversarial release tests: changed prose, missing evidence and incomplete coverage."""
import argparse
import contextlib
import copy
import io
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/grounded/scripts"))
import audit_contract
import claim_evidence
import claim_inventory
import claim_receipts
import export_review
import verify_claims
import evidence_assessment
import audit_search
import synthesis_quotes
import sync_review_budgets
import validate_review

DOI = "10.0000/synthetic"
REVIEW = "Pain fell by 15% in 20 adults [Trial](https://doi.org/10.0000/synthetic).\n"
QUOTE = "Pain fell by 15% in 20 adults."


def checked_fixture(directory, markdown=REVIEW):
    """Synthetic test evidence, never used to classify or judge real documents."""
    directory = Path(directory)
    review, path, store = directory / "review.md", directory / "audit.json", directory / "evidence"
    review.write_text(markdown)
    claims = claim_inventory.extract_claims(markdown, include_uncited=True)
    audit = {"schema_version": 2, "review": str(review), "claims": claims,
             "inventory_sha256": audit_contract.inventory_digest(claims)}
    evidence_texts = {}
    for claim in claims:
        if not claim["dois"]:
            claim.update(classification="nonfactual", classification_note="Synthetic fixture heading.")
        for adj in claim["adjudications"]:
            quote = claim["claim"]
            evidence_texts.setdefault(adj["doi"], []).append(quote)
            adj.update(verdict="supported", quote=quote, tier="fulltext")
    for doi, passages in evidence_texts.items():
        claim_evidence.store_text(doi, store, " ".join(passages), {"tier": "fulltext", "source": "synthetic"})
    path.write_text(json.dumps(audit))
    with contextlib.redirect_stdout(io.StringIO()):
        verify_claims.cmd_check(argparse.Namespace(audit=str(path), evidence=str(store),
                                                  summary=None, appendix=None, strict=True))
    return review, path, store, json.loads(path.read_text())


def assessment_fixture(ledger, synthesis):
    claims = evidence_assessment.synthesis_quotes.parse_claims(synthesis)
    return {"schema_version": 1,
            "scope": {"question": "Synthetic question", "review_type": "narrative", "search_date": "2026-09-04",
                      "databases": ["synthetic"], "inclusion": "Synthetic records", "exclusion": "Other records",
                      "access_limitations": "None in this fixture"},
            "studies": [{"id": e["key"], "kind": "primary", "design": "synthetic experiment",
                         "source_keys": [e["key"]]} for e in ledger["entries"]],
            "outcomes": [{"id": "O1", "outcome": "Synthetic outcome", "claim_ids": [c["id"] for c in claims],
                          "source_keys": [e["key"] for e in ledger["entries"]], "certainty": "low",
                          "rationale": "Synthetic fixture, no real evidence.",
                          "domains": {d: {"judgment": "unclear", "reason": "Synthetic fixture."}
                                      for d in evidence_assessment.DOMAINS}}]}


def synthetic_release_args(directory):
    """Offline renderer fixture: do not use this to assess real scientific claims."""
    root = Path(directory)
    markdown = (root / "review.md").read_text()
    _review, audit_path, _store, audit = checked_fixture(root, markdown)
    dois = {a["doi"] for c in audit["claims"] for a in c["adjudications"]}
    dois.update(value.rstrip(".,;") for value in re.findall(r"https?://doi\.org/([^\s<>)]+)", markdown))
    ledger = root / "synthetic-ledger.json"
    ledger.write_text(json.dumps({"entries": [
        {"key": f"K{i}", "doi": doi, "status": "verified",
         "verification": {"bibliographic_status": "verified", "retraction_status": "clear"}}
        for i, doi in enumerate(sorted(dois))]}))
    receipts = root / "review-receipts.md"
    receipts.write_text(claim_receipts.render_receipts_document(
        audit, claim_receipts.labels_from_markdown(markdown),
        title=claim_receipts.review_title(markdown), review_name="review.md"))
    args = ["--ledger", str(ledger), "--claims-audit", str(audit_path), "--claim-receipts", str(receipts)]
    for i, _asset in enumerate(re.findall(r"^!\[[^]]*\]\(([^)]+)\)", markdown, re.M)):
        spec, prompt = root / f"synthetic-figure-{i}.json", root / f"synthetic-prompt-{i}.txt"
        spec.write_text("{}")
        prompt.write_text("Synthetic renderer fixture.")
        args.extend(["--figure-spec", str(spec), "--figure-prompt", str(prompt)])
    return args


class AssertionReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.review, self.path, self.store, self.audit = checked_fixture(self.root)

    def validate(self, markdown=None, audit=None):
        audit_contract.validate_release(audit or self.audit, markdown or self.review.read_text(), self.path)

    def test_checked_review_and_stamped_review_pass(self):
        self.validate()
        # A sources block ensures receipts apparatus never enters the inventory.
        text = self.review.read_text() + "\n**Sources**\n\n**Trial (2024)** https://doi.org/10.0000/synthetic\n"
        self.validate(claim_receipts.attach_receipts(text, self.audit))

    def test_reversed_added_or_uncited_assertions_fail(self):
        for text in (REVIEW.replace("fell", "rose"), REVIEW + "Mortality also fell.\n",
                     REVIEW.replace(" [Trial](https://doi.org/10.0000/synthetic)", "")):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "assertions changed"):
                self.validate(text)

    def test_heading_and_alt_claims_are_in_inventory(self):
        text = "# Treatment cures everyone\n\n![Treatment prevents death](f.png)\n\n" + REVIEW
        claims = claim_inventory.extract_claims(text, include_uncited=True)
        self.assertEqual(len(claims), 3)
        self.assertEqual(claims[0]["classification"], "pending")
        self.assertIn("prevents death", claims[1]["claim"])

    def test_changed_evidence_or_metadata_invalidates_release(self):
        slug = claim_evidence.doi_slug(DOI)
        path = self.store / (slug + ".txt")
        path.write_text(QUOTE.replace("15%", "0%"))
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.validate()

    def test_editing_judgment_requires_recheck(self):
        changed = copy.deepcopy(self.audit)
        changed["claims"][0]["adjudications"][0]["note"] = "Revised judgment."
        with self.assertRaisesRegex(ValueError, "changed since check"):
            self.validate(audit=changed)

    def test_partial_without_coverage_is_not_releasable(self):
        changed = copy.deepcopy(self.audit)
        changed["claims"][0]["adjudications"][0].update(verdict="partial", note="Effect magnitude not supported.")
        self.assertTrue(any("unsupported element" in e for e in audit_contract.coverage_errors(changed)))

    def test_two_partial_sources_can_cover_two_complete_elements(self):
        claim = {"id": "C001", "claim": "Reading improved and attendance increased.",
                 "classification": "factual", "dois": ["a", "b"],
                 "elements": [{"id": "E1", "text": "Reading improved"},
                              {"id": "E2", "text": "and attendance increased."}],
                 "adjudications": [
                     {"doi": "a", "verdict": "partial", "covers": ["E1"], "quote": "Reading improved", "note": "Attendance not assessed."},
                     {"doi": "b", "verdict": "partial", "covers": ["E2"], "quote": "Attendance increased", "note": "Reading not assessed."}]}
        self.assertEqual(audit_contract.coverage_errors({"claims": [claim]}), [])
        claim["elements"][1]["text"] = "attendance increased."
        self.assertTrue(audit_contract.coverage_errors({"claims": [claim]}))

    def test_wrong_units_effects_signs_and_substrings_are_unmatched(self):
        for claim, quote in [("In 20 adults pain fell by 90%.", QUOTE), ("Dose 5 g.", "Dose 5 mg."),
                             ("Change -2%.", "Change 2%."), ("Change 2%.", "Change 20%."),
                             ("Risk 5%.", "Risk 5.")]:
            self.assertTrue(audit_contract.missing_quantities(claim, quote), (claim, quote))
        self.assertFalse(audit_contract.missing_quantities("Dose 5 mg for 6 weeks.", "Dose five mg for six weeks."))
        self.assertFalse(audit_contract.missing_quantities("Range 1–2%.", "Range 1-2%."))
        self.assertTrue(audit_contract.missing_quantities("Dose 5 g/day.", "Dose 5 g."))

    def test_export_input_check_rejects_stale_audit(self):
        ledger = self.root / "ledger.json"
        ledger.write_text(json.dumps({"entries": [{"key": "trial", "doi": DOI, "status": "verified",
                                                   "verification": {"bibliographic_status": "verified", "retraction_status": "clear"}}]}))
        export_review.validate_release_inputs(self.review, ledger, claims_audit=self.path)
        self.review.write_text(REVIEW.replace("fell", "rose"))
        with self.assertRaisesRegex(ValueError, "assertions changed"):
            export_review.validate_release_inputs(self.review, ledger, claims_audit=self.path)

    def test_legacy_audit_is_not_release_evidence(self):
        changed = copy.deepcopy(self.audit)
        changed.pop("schema_version")
        with self.assertRaisesRegex(ValueError, "legacy audit"):
            self.validate(audit=changed)

    def test_uncited_fact_cannot_be_classified_away_without_a_reason_or_basis(self):
        claim = {"id": "C002", "claim": "It cures everyone.", "dois": [], "adjudications": [],
                 "classification": "factual", "elements": [{"id": "E1", "text": "It cures everyone."}]}
        self.assertTrue(audit_contract.coverage_errors({"claims": [claim]}))
        claim.update(classification="interpretation", classification_note="Summary", basis=["C999"])
        self.assertTrue(any("basis" in e for e in audit_contract.coverage_errors({"claims": [claim]})))
        claim.update(classification="nonfactual", classification_note="")
        self.assertTrue(audit_contract.coverage_errors({"claims": [claim]}))

    def test_classification_command_and_element_changes_invalidate_check(self):
        original = json.loads(self.path.read_text())
        with self.assertRaises(SystemExit):
            verify_claims.cmd_classify(argparse.Namespace(audit=str(self.path), claim="C001",
                classification="nonfactual", note="Escape the audit", basis=[]))
        verify_claims.cmd_elements(argparse.Namespace(audit=str(self.path), claim="C001",
                                                     element=["Pain fell by 15%", "in 20 adults."]))
        changed = json.loads(self.path.read_text())
        self.assertNotIn("checked_sha256", changed)
        self.assertEqual(changed["claims"][0]["adjudications"][0]["verdict"], "pending")
        self.assertEqual(original["claims"][0]["adjudications"][0]["verdict"], "supported")

    def test_draft_report_keeps_uncited_findings_visible(self):
        import check_draft
        audit = {"schema_version": 2, "claims": claim_inventory.extract_claims("Treatment cures everyone.", include_uncited=True)}
        report = check_draft.render_report({"references": []}, {"entries": []}, audit)
        self.assertIn("Treatment cures everyone", report)
        self.assertIn("needs independent classification", report)


class QualificationTests(unittest.TestCase):
    def test_qualification_defaults_to_eighty_percent_agreement(self):
        root = Path(__file__).resolve().parents[1] / "skills/grounded/evals"
        candidate = json.loads((root / "judge-benchmark-input.json").read_text())
        for c in candidate["claims"]:
            c["adjudications"][0]["verdict"] = "unverifiable"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.json"
            path.write_text(json.dumps(candidate))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit, "agreement below"):
                verify_claims.cmd_score(argparse.Namespace(audit=str(path), gold=str(root / "judge-benchmark-gold.json"),
                    min_agreement=None, qualify=True, max_false_acceptance=0))

    def test_one_pair_cannot_qualify_for_whole_benchmark(self):
        root = Path(__file__).resolve().parents[1] / "skills/grounded/evals"
        gold = json.loads((root / "judge-benchmark-gold.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate.json"
            candidate.write_text(json.dumps({"claims": gold["claims"][:1]}))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                verify_claims.cmd_score(argparse.Namespace(audit=str(candidate), gold=str(root / "judge-benchmark-gold.json"),
                                                          min_agreement=80, qualify=True, max_false_acceptance=0))

    def test_full_fixture_scores_but_false_acceptance_and_fabricated_quotes_fail(self):
        root = Path(__file__).resolve().parents[1] / "skills/grounded/evals"
        gold = json.loads((root / "judge-benchmark-gold.json").read_text())
        inputs = json.loads((root / "judge-benchmark-input.json").read_text())
        candidate = copy.deepcopy(gold)
        for c, packet in zip(candidate["claims"], inputs["claims"]):
            adj = c["adjudications"][0]
            adj["quote"] = packet["passages"]
            if adj["verdict"] == "partial":
                adj["note"] = c["id"] + ": the additional clause or qualifier is not established."
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.json"
            report = Path(tmp) / "score.json"
            args = argparse.Namespace(audit=str(path), gold=str(root / "judge-benchmark-gold.json"),
                                      min_agreement=80, qualify=True, max_false_acceptance=0, report=str(report))
            path.write_text(json.dumps(candidate))
            with contextlib.redirect_stdout(io.StringIO()):
                verify_claims.cmd_score(args)
            self.assertEqual(json.loads(report.read_text())["coverage"], 1)
            candidate["claims"][1]["adjudications"][0]["verdict"] = "supported"
            path.write_text(json.dumps(candidate))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                verify_claims.cmd_score(args)
            self.assertGreater(json.loads(report.read_text())["false_acceptance_percent"], 0)
            candidate["claims"][1]["adjudications"][0]["verdict"] = "contradicted"
            candidate["claims"][0]["adjudications"][0]["quote"] = "Invented supporting text."
            path.write_text(json.dumps(candidate))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                verify_claims.cmd_score(args)

    def test_packet_preparation_never_includes_gold_labels(self):
        root = Path(__file__).resolve().parents[1] / "skills/grounded/evals"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "candidate.json"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                verify_claims.cmd_benchmark_packets(argparse.Namespace(input=str(root / "judge-benchmark-input.json"), audit=str(out)))
            self.assertNotIn("gold", stream.getvalue())
            self.assertTrue(all(a["verdict"] == "pending" for c in json.loads(out.read_text())["claims"] for a in c["adjudications"]))


class AssessmentTests(unittest.TestCase):
    def test_coverage_domains_and_duplicate_publications(self):
        ledger = {"entries": [{"key": "A"}, {"key": "B"}]}
        synthesis = "### C1. An outcome changed.\n- evidence: [@A; @B]\n"
        doc = assessment_fixture(ledger, synthesis)
        self.assertEqual(evidence_assessment.assess(doc, ledger, synthesis)["status"], "pass")
        del doc["outcomes"][0]["domains"]["imprecision"]
        doc["studies"][1]["source_keys"].append("A")
        errors = evidence_assessment.assess(doc, ledger, synthesis)["errors"]
        self.assertTrue(any("imprecision" in e for e in errors))
        self.assertTrue(any("multiply assigned" in e for e in errors))

    def test_unknown_review_overlap_is_visible_and_not_independent_evidence(self):
        ledger = {"entries": [{"key": "R"}]}
        synthesis = "### C1. An outcome changed.\n- evidence: [@R]\n"
        doc = assessment_fixture(ledger, synthesis)
        doc["studies"][0].update(kind="review", overlap_status="unknown", overlap_note="Primary study list unavailable.")
        result = evidence_assessment.assess(doc, ledger, synthesis)
        self.assertEqual(result["status"], "pass")
        self.assertIn("independent confirmation", result["warnings"][0])


class SearchAndBudgetTests(unittest.TestCase):
    def test_completed_zero_hit_contrary_search_passes_without_forcing_disagreement(self):
        from tests.test_audit_search import record
        records = [record(f"angle-{i}", f"query {i}", lane="contrary-null" if i == 0 else "primary", accepted=0)
                   for i in range(3)]
        self.assertEqual(audit_search.audit_search({"schema_version": 1, "records": records}, size="small")["status"], "pass")
        records[0]["completed"] = False
        self.assertEqual(audit_search.audit_search({"schema_version": 1, "records": records}, size="small")["status"], "fail")
        claims = [{"id": f"C{i}", "contrary_keys": [], "boundary_text": "", "numbers_field": "", "evidence_text": ""}
                  for i in range(8)]
        self.assertEqual(synthesis_quotes.hollow_problems(claims), [])

    def test_source_shortfall_is_advisory_even_for_explicit_size(self):
        from tests.test_validate_review import scientific_review
        result = validate_review.validate_review(scientific_review(), style="scientific", size="small", strict_tier=True)
        self.assertFalse(any("sources requires" in e for e in result.errors))
        self.assertTrue(any("never pad" in w for w in result.warnings))

    def test_budget_documents_and_evaluations_match_canonical_configuration(self):
        repo = Path(__file__).resolve().parents[1]
        self.assertEqual((repo / "skills/grounded/references/budgets.md").read_text(), sync_review_budgets.documentation())
        profiles = json.loads((repo / "evals/evals.json").read_text())["budget_profiles"]
        for size in ("small", "medium", "large"):
            self.assertEqual(profiles[size], json.loads(json.dumps(sync_review_budgets.profile(size))))


if __name__ == "__main__":
    unittest.main()
