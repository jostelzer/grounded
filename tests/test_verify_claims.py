import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import claim_evidence  # noqa: E402
import verify_claims  # noqa: E402


REVIEW = """## Does it work?

Large trials found no broad benefit, with a small effect of d=0.17 on digit span
[Sandkühler et al. 2023](https://doi.org/10.1186/s12916-023-03146-5). Brain creatine
rose by 8.7% after supplementation [Dechent et al. 1999](https://doi.org/10.1152/ajpregu.1999.277.3.r698),
[Lyoo et al. 2003](https://doi.org/10.1016/S0925-4927(03)00046-5). Watanabe found less
fatigue [Watanabe et al. 2002](https://doi.org/10.1016/s0168-0102%2802%2900007-x).

| Study | Result |
|---|---|
| Rae 2003 | Better reasoning [Rae et al. 2003](https://doi.org/10.1098/rspb.2003.2492) |

Uncited context sentence with a number 42 that has no citation link at all.

**Sources**

**Sandkühler JF (2023)** The effects. *BMC Medicine*. https://doi.org/10.1186/s12916-023-03146-5
"""


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.claims = verify_claims.extract_claims(REVIEW)

    def test_pairs_and_sources_exclusion(self):
        dois = {d for c in self.claims for d in c["dois"]}
        self.assertEqual(dois, {
            "10.1186/s12916-023-03146-5",
            "10.1152/ajpregu.1999.277.3.r698",
            "10.1016/s0925-4927(03)00046-5",
            "10.1016/s0168-0102(02)00007-x",
            "10.1098/rspb.2003.2492",
        })
        # the Sources block and the uncited sentence contribute no claims
        self.assertEqual(len(self.claims), 4)

    def test_multi_citation_sentence_keeps_both_dois(self):
        brain = next(c for c in self.claims if "8.7%" in c["claim"])
        self.assertEqual(len(brain["dois"]), 2)
        self.assertIn("8.7%", brain["numbers"])

    def test_claim_text_has_no_citation_links(self):
        for c in self.claims:
            self.assertNotIn("doi.org", c["claim"])
            self.assertNotIn("[", c["claim"].replace("[@", ""))

    def test_numbers_exclude_years(self):
        digit = next(c for c in self.claims if "d=0.17" in c["claim"])
        self.assertIn("0.17", digit["numbers"])
        self.assertNotIn("2023", digit["numbers"])

    def test_table_row_is_a_claim(self):
        row = next(c for c in self.claims if c["location"].startswith("table row"))
        self.assertEqual(row["dois"], ["10.1098/rspb.2003.2492"])

    def test_ledger_keys_resolve_to_dois(self):
        claims = verify_claims.extract_claims(
            "A cited draft sentence [@Rae2003].",
            key_to_doi={"Rae2003": "10.1098/rspb.2003.2492"})
        self.assertEqual(claims[0]["dois"], ["10.1098/rspb.2003.2492"])


class SentenceSplitTests(unittest.TestCase):
    def test_et_al_and_decimals_do_not_split(self):
        parts = verify_claims.split_sentences(
            "Rae et al. found d=0.17 in adults. A second trial was null.")
        self.assertEqual(len(parts), 2)
        self.assertIn("et al. found d=0.17", parts[0])


class QuoteEnforcementTests(unittest.TestCase):
    DOI = "10.1186/s12916-023-03146-5"
    EVIDENCE = ("The creatine effect bordered significance for BDS "
                "(p = 0.067, η²P = 0.028) — "
                "Cohen’s d was 0.17 for BDS.")

    def audit_with(self, verdict, quote, numbers=("0.17",)):
        return {
            "review": "r.md", "created": "2026-08-27",
            "claims": [{
                "id": "C001", "claim": "Digit span improved with d=0.17.",
                "location": "paragraph 1, sentence 1", "dois": [self.DOI],
                "numbers": list(numbers),
                "adjudications": [{"doi": self.DOI, "verdict": verdict,
                                   "quote": quote, "note": ""}],
            }],
        }

    def run_check(self, audit, appendix=False):
        tmp = tempfile.mkdtemp()
        store = Path(tmp) / "evidence"
        store.mkdir()
        slug = claim_evidence.doi_slug(self.DOI)
        (store / f"{slug}.txt").write_text(self.EVIDENCE)
        (store / f"{slug}.meta.json").write_text(json.dumps(
            {"doi": self.DOI, "tier": "fulltext", "source": "test"}))
        audit_path = Path(tmp) / "audit.json"
        audit_path.write_text(json.dumps(audit))
        args = argparse.Namespace(
            audit=str(audit_path), evidence=str(store),
            appendix=str(Path(tmp) / "appendix.md") if appendix else None,
            strict=False)
        verify_claims.cmd_check(args)
        return json.loads(audit_path.read_text()), Path(tmp)

    def test_verbatim_quote_with_unicode_variants_is_kept(self):
        # straight quotes/dashes in the judge's quote vs curly/thin-space evidence
        audit, _ = self.run_check(self.audit_with(
            "supported", "Cohen's d was 0.17 for BDS"))
        self.assertEqual(audit["claims"][0]["adjudications"][0]["verdict"], "supported")

    def test_fabricated_quote_is_downgraded(self):
        audit, _ = self.run_check(self.audit_with(
            "supported", "creatine strongly improved all outcomes"))
        adj = audit["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "unverifiable")
        self.assertIn("quote rejected", adj["note"])

    def test_numeric_claim_without_number_in_quote_becomes_partial(self):
        audit, _ = self.run_check(self.audit_with(
            "supported", "The creatine effect bordered significance for BDS"))
        adj = audit["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "partial")
        self.assertIn("numeric anchor missing", adj["note"])

    def test_contradicted_is_a_hard_fail(self):
        with self.assertRaises(SystemExit):
            self.run_check(self.audit_with(
                "contradicted", "Cohen's d was 0.17 for BDS"))

    def test_appendix_renders(self):
        _, tmp = self.run_check(self.audit_with(
            "supported", "Cohen's d was 0.17 for BDS"), appendix=True)
        rendered = (tmp / "appendix.md").read_text()
        self.assertIn("C001", rendered)
        self.assertIn("supported", rendered)


class PassageSelectionTests(unittest.TestCase):
    def test_windows_anchor_on_numbers(self):
        text = ("Filler. " * 200) + "The increase was 8.7% overall. " + ("More filler. " * 200)
        windows = verify_claims.candidate_passages(
            "Brain creatine rose by 8.7% after supplementation", ["8.7%"], text)
        self.assertTrue(any("8.7%" in w for w in windows))


class EvidenceHelperTests(unittest.TestCase):
    def test_doi_slug_and_norm(self):
        self.assertEqual(
            claim_evidence.norm_doi("https://doi.org/10.1016/S0168-0102%2802%2900007-X"),
            "10.1016/s0168-0102(02)00007-x")
        self.assertEqual(
            claim_evidence.doi_slug("10.1016/S0168-0102(02)00007-X"),
            "10-1016-s0168-0102-02-00007-x")

    def test_blocked_page_detection(self):
        self.assertEqual(claim_evidence.blocked_page(
            "<html>Just a moment... Enable JavaScript and cookies to continue"),
            "challenge_page")
        self.assertIsNone(claim_evidence.blocked_page("A perfectly ordinary article body."))

    def test_deinvert(self):
        self.assertEqual(
            claim_evidence.deinvert({"world": [1], "hello": [0]}), "hello world")


if __name__ == "__main__":
    unittest.main()
