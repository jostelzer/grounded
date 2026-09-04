import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

    def test_caption_number_is_structural_but_empirical_numbers_remain(self):
        claims = verify_claims.extract_claims(
            '<a id="fig-main"></a>\n\n![alt](main.png)\n\n'
            '**Figure 2. Main result.** The interval was 95% '
            '[Study](https://doi.org/10.1/study).')
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["numbers"], ["95%"])

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


class _AuditHelpers:
    DOI = "10.1186/s12916-023-03146-5"
    EVIDENCE = ("The creatine effect on digit span bordered significance for BDS "
                "(p = 0.067, η²P = 0.028) — "
                "Cohen’s d was 0.17 for BDS. All participants gave written consent.")

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
            summary=str(Path(tmp) / "claims_summary.json"),
            strict=False)
        verify_claims.cmd_check(args)
        return json.loads(audit_path.read_text()), Path(tmp)

    def test_check_writes_the_summary_the_colophon_prints(self):
        _, tmp = self.run_check(self.audit_with(
            "supported", "Cohen's d was 0.17 for BDS"))
        summary = json.loads((tmp / "claims_summary.json").read_text())
        self.assertEqual(summary["pairs"], 1)
        self.assertEqual(summary["supported_fulltext"], 1)
        self.assertEqual(summary["contradicted"], 0)

class QuoteEnforcementTests(_AuditHelpers, unittest.TestCase):
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
            "supported", "The creatine effect on digit span bordered significance"))
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


class JudgmentGateTests(_AuditHelpers, unittest.TestCase):
    def multi(self, n, verdict, note, quote="Cohen's d was 0.17 for BDS"):
        doc = self.audit_with(verdict, quote)
        base = doc["claims"][0]
        doc["claims"] = []
        for i in range(n):
            c = json.loads(json.dumps(base))
            c["id"] = f"C{i + 1:03d}"
            c["adjudications"][0]["note"] = note
            doc["claims"].append(c)
        return doc

    def test_partial_without_a_note_is_a_hard_fail(self):
        with self.assertRaises(SystemExit):
            self.run_check(self.multi(1, "partial", ""))

    def test_templated_note_across_pairs_is_a_hard_fail(self):
        with self.assertRaises(SystemExit):
            self.run_check(self.multi(3, "supported", "Adjudicated against the stored text."))
        audit, _ = self.run_check(self.multi(2, "supported", "Adjudicated against the stored text."))
        self.assertEqual(audit["claims"][1]["adjudications"][0]["verdict"], "supported")

    def test_unrelated_quote_is_downgraded_to_unverifiable(self):
        audit, _ = self.run_check(self.audit_with(
            "supported", "digit span bordered significance for BDS", numbers=()))
        self.assertEqual(audit["claims"][0]["adjudications"][0]["verdict"], "supported")
        # A real passage from the paper that has nothing to do with the sentence.
        doc = self.audit_with("supported", "All participants gave written consent", numbers=())
        audit, _ = self.run_check(doc)
        adj = audit["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "unverifiable")
        self.assertIn("unrelated", adj["note"])

    def test_bridge_rescues_a_paraphrase_but_must_connect_both_sides(self):
        doc = self.audit_with("supported", "All participants gave written consent", numbers=())
        doc["claims"][0]["claim"] = "Everyone in the trial agreed to take part."
        doc["claims"][0]["adjudications"][0]["bridge"] = "consent = agreed to take part"
        audit, _ = self.run_check(doc)
        self.assertEqual(audit["claims"][0]["adjudications"][0]["verdict"], "supported")
        doc["claims"][0]["adjudications"][0]["bridge"] = "the source is on topic"
        audit, _ = self.run_check(doc)
        adj = audit["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "unverifiable")
        self.assertIn("bridge does not connect", adj["note"])

    def test_templated_bridge_is_a_hard_fail(self):
        doc = self.multi(3, "supported", "", quote="digit span bordered significance for BDS")
        for c in doc["claims"]:
            c["adjudications"][0]["bridge"] = "BDS = digit span"
        with self.assertRaises(SystemExit):
            self.run_check(doc)

    def test_specific_partial_notes_pass(self):
        doc = self.multi(3, "partial", "")
        for i, c in enumerate(doc["claims"]):
            c["adjudications"][0]["note"] = f"abstract lacks element {i}"
        audit, _ = self.run_check(doc)
        self.assertEqual(audit["claims"][2]["adjudications"][0]["verdict"], "partial")

    def test_adjudicate_records_one_pair_and_enforces_quote_and_note(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "audit.json"
        path.write_text(json.dumps(self.audit_with("pending", "")))
        base = dict(audit=str(path), claim="C001", doi=self.DOI, note=None)
        with self.assertRaises(SystemExit):
            verify_claims.cmd_adjudicate(argparse.Namespace(
                **base, verdict="supported", quote=[]))
        with self.assertRaises(SystemExit):
            verify_claims.cmd_adjudicate(argparse.Namespace(
                **base, verdict="partial", quote=["Cohen's d was 0.17 for BDS"]))
        verify_claims.cmd_adjudicate(argparse.Namespace(
            **base, verdict="supported", quote=["Cohen's d was 0.17 for BDS"]))
        adj = json.loads(path.read_text())["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "supported")
        self.assertEqual(adj["quote"], "Cohen's d was 0.17 for BDS")


class ExtractionShapeTests(unittest.TestCase):
    def test_caption_is_one_claim_and_citation_commas_are_cleaned(self):
        md = ("## Q\n\nCurrent reviews describe appetite returning, weight regain, "
              "and markers deteriorating [A 2024](https://doi.org/10.1/a), "
              "[B 2025](https://doi.org/10.1/b).\n\n"
              '<a id="fig-x"></a>\n![alt](x.png)\n\n'
              "**Figure 1. The signal fades.** Panel A follows weight. Whiskers are "
              "95% intervals [A 2024](https://doi.org/10.1/a), [B 2025](https://doi.org/10.1/b).\n\n"
              "**Sources**\n\n**A (2024)** T. *J*. https://doi.org/10.1/a\n")
        claims = verify_claims.extract_claims(md)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0]["claim"],
                         "Current reviews describe appetite returning, weight regain, and markers deteriorating.")
        self.assertEqual(claims[1]["location"], "figure 1 caption")
        self.assertEqual(claims[1]["dois"], ["10.1/a", "10.1/b"])
        self.assertTrue(claims[1]["claim"].startswith("**Figure 1. The signal fades.**"))


class LocalSeedTests(unittest.TestCase):
    def test_store_is_seeded_from_read_fulltexts_and_ledger_abstracts(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "fulltexts").mkdir()
        body = "word " * 800
        (tmp / "fulltexts" / "Smith2024.txt").write_text(body)
        ledger = {"entries": [
            {"key": "Smith2024", "doi": "10.1/full", "abstract": "short"},
            {"key": "Lee2023", "doi": "10.1/abs", "abstract": "abstract " * 40},
            {"key": "None2022", "doi": "10.1/none", "abstract": "tiny"},
        ]}
        (tmp / "sources.json").write_text(json.dumps(ledger))
        manifest = {"records": [{"doi": "10.1/full", "status": "valid_fulltext",
                                 "path": "Smith2024.txt"}]}
        (tmp / "fulltext-manifest.json").write_text(json.dumps(manifest))
        seeded = claim_evidence.seed_local_evidence(
            ["10.1/full", "10.1/abs", "10.1/none"], tmp / "evidence",
            ledger_path=tmp / "sources.json", fulltext_dir=tmp / "fulltexts",
            manifest_path=tmp / "fulltext-manifest.json")
        self.assertEqual(seeded, {"10.1/full": "fulltext", "10.1/abs": "abstract"})
        text, meta = claim_evidence.load_evidence("10.1/full", tmp / "evidence")
        self.assertEqual(meta["tier"], "fulltext")
        self.assertEqual(meta["source"], "local-fulltext")
        self.assertTrue(claim_evidence.quote_in_text("word word", text))
        # Re-seeding never downgrades what the store already holds.
        again = claim_evidence.seed_local_evidence(
            ["10.1/full"], tmp / "evidence", ledger_path=tmp / "sources.json")
        self.assertEqual(again, {})


class SynthesisQuoteTests(unittest.TestCase):
    SYNTHESIS = """# Synthesis — Q

## Verdict
V.

## Throughline
T.

## Claims

### C1. Brain creatine rose by 8.7% after four weeks of supplementation.
- strength: moderate — one small imaging study.
- evidence: six adults, 20 g/day for 4 weeks, +8.7% total creatine [@Dechent1999]
- quote: [@Dechent1999] "yielded a statistically significant increase (8.7% corresponding to 0.6 mM"
- contrary: none found — searched
- boundary: healthy adults.
- depends-on: —
- numbers: 8.7% (range 3.5–13.3%).

### C2. Later reviews call the increase modest.
- strength: limited
- evidence: narrative reviews [@Roschel2021]
- contrary: none found — searched
- boundary: —
- depends-on: C1
- numbers: —

## Patterns
- P1. x (C1)

## Open
- y
"""
    EVIDENCE = ("Oral consumption of creatine yielded a statistically significant increase "
                "(8.7% corresponding to 0.6 mM, P < 0.001) of the mean concentration.")

    def setUp(self):
        import synthesis_quotes
        self.sq = synthesis_quotes
        self.tmp = Path(tempfile.mkdtemp())
        self.store = self.tmp / "evidence"
        self.ledger = {"entries": [
            {"key": "Dechent1999", "doi": "10.1/dechent", "status": "verified"},
            {"key": "Roschel2021", "doi": "10.1/roschel", "status": "verified"},
        ]}
        claim_evidence.store_text("10.1/dechent", self.store, self.EVIDENCE,
                                  {"tier": "fulltext", "source": "test"})

    def test_parse_reads_keys_numbers_and_quote_lines(self):
        claims = self.sq.parse_claims(self.SYNTHESIS)
        self.assertEqual([c["id"] for c in claims], ["C1", "C2"])
        self.assertEqual(claims[0]["keys"], ["Dechent1999"])
        self.assertEqual(claims[0]["numbers"], ["8.7%"])
        self.assertEqual(claims[0]["quotes"][0][0], "Dechent1999")

    def test_check_requires_a_verbatim_quote_per_cited_key(self):
        result = self.sq.check_synthesis(self.SYNTHESIS, self.store, self.ledger)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("C2 cites @Roschel2021 without a quote" in e for e in result["errors"]))
        fixed = self.SYNTHESIS.replace("- evidence: narrative reviews [@Roschel2021]",
                                       "- evidence: narrative reviews [@Roschel2021]\n"
                                       '- quote: [@Roschel2021] "modest increases"')
        result = self.sq.check_synthesis(fixed, self.store, self.ledger)
        self.assertTrue(any("no evidence text in the store" in e for e in result["errors"]))
        claim_evidence.store_text("10.1/roschel", self.store, "reviews report modest increases in brain creatine",
                                  {"tier": "abstract", "source": "test"})
        result = self.sq.check_synthesis(fixed, self.store, self.ledger)
        self.assertEqual(result["errors"], [], result["errors"])
        self.assertEqual(result["metrics"]["keys_by_tier"], {"fulltext": 1, "abstract": 1, "none": 0})
        self.assertTrue(any("3.5" in w for w in result["warnings"]))  # numbers-field arithmetic warns

    def test_check_rejects_a_sentence_number_missing_from_its_quotes(self):
        wrong = self.SYNTHESIS.replace("(8.7% corresponding to 0.6 mM", "of the mean concentration")
        result = self.sq.check_synthesis(wrong, self.store, self.ledger)
        self.assertTrue(any("the number 8.7% in the claim sentence" in e for e in result["errors"]))

    def test_extract_with_synthesis_refuses_an_unquoted_source_and_carries_quotes(self):
        review = ("## Q\n\nBrain creatine rose 8.7% [Dechent 1999](https://doi.org/10.1/dechent). "
                  "Reviews agree [Roschel 2021](https://doi.org/10.1/roschel).\n\n**Sources**\n\n"
                  "**Dechent P (1999)** T. *J*. https://doi.org/10.1/dechent\n")
        (self.tmp / "review.md").write_text(review)
        (self.tmp / "sources.json").write_text(json.dumps(self.ledger))
        (self.tmp / "synthesis.md").write_text(self.SYNTHESIS)
        args = argparse.Namespace(review=str(self.tmp / "review.md"), ledger=str(self.tmp / "sources.json"),
                                  synthesis=str(self.tmp / "synthesis.md"), audit=str(self.tmp / "audit.json"))
        with self.assertRaises(SystemExit):
            verify_claims.cmd_extract(args)
        (self.tmp / "synthesis.md").write_text(self.SYNTHESIS.replace(
            "- evidence: narrative reviews [@Roschel2021]",
            '- evidence: narrative reviews [@Roschel2021]\n- quote: [@Roschel2021] "modest increases"'))
        from tests.test_assertion_audit import assessment_fixture
        (self.tmp / "evidence-assessment.json").write_text(json.dumps(
            assessment_fixture(self.ledger, self.SYNTHESIS)))
        verify_claims.cmd_extract(args)
        audit = json.loads((self.tmp / "audit.json").read_text())
        self.assertEqual(audit["claims"][1]["adjudications"][0]["synthesis_quotes"],
                         ["yielded a statistically significant increase (8.7% corresponding to 0.6 mM"])

    def test_blind_packets_hide_source_and_place_and_packet_ids_adjudicate(self):
        audit = {"review": "r.md", "claims": [{
            "id": "C001", "claim": "Brain creatine rose 8.7%.", "location": "paragraph 1, sentence 1",
            "dois": ["10.1/dechent"], "numbers": ["8.7%"],
            "adjudications": [{"doi": "10.1/dechent", "verdict": "pending", "quote": "", "note": "",
                               "synthesis_quotes": ["yielded a statistically significant increase"]}]}]}
        (self.tmp / "audit.json").write_text(json.dumps(audit))
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verify_claims.cmd_packets(argparse.Namespace(
                audit=str(self.tmp / "audit.json"), evidence=str(self.store),
                pending_only=False, claim=None, blind=True))
        text = out.getvalue()
        self.assertIn("### packet C001#1 [tier: fulltext]", text)
        self.assertNotIn("10.1/dechent", text)
        self.assertNotIn("paragraph 1", text)
        self.assertIn("S1. yielded a statistically significant increase", text)
        verify_claims.cmd_adjudicate(argparse.Namespace(
            audit=str(self.tmp / "audit.json"), packet="C001#1", claim=None, doi=None,
            verdict="supported", quote=["8.7% corresponding to 0.6 mM"], note=None, bridge=None))
        adj = json.loads((self.tmp / "audit.json").read_text())["claims"][0]["adjudications"][0]
        self.assertEqual(adj["verdict"], "supported")

    def test_seed_command_reports_unquotable_sources(self):
        (self.tmp / "sources.json").write_text(json.dumps(self.ledger))
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            verify_claims.cmd_seed(argparse.Namespace(
                ledger=str(self.tmp / "sources.json"), evidence=str(self.store),
                fulltext_dir=None, fulltext_manifest=None))
        self.assertIn("1 without any stored text", out.getvalue())
        self.assertIn("10.1/roschel", out.getvalue())


class DecorativeCitationTests(unittest.TestCase):
    """Real decorative citations from the v0.4.2 reruns, kept as a regression set."""

    def test_recorded_decorative_pairs_never_pass_as_supported(self):
        fixture = json.loads(Path(ROOT, "evals", "decorative-citations.json").read_text())
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                self.assertFalse(
                    verify_claims.quote_relates_to_claim(case["quote"], case["claim"]),
                    case["why"])
        for case in fixture["legitimate_paraphrases"]:
            with self.subTest(case=case["id"]):
                self.assertFalse(verify_claims.quote_relates_to_claim(case["quote"], case["claim"]))
                self.assertTrue(verify_claims.bridge_connects(case["bridge"], case["quote"], case["claim"]))


class ScoreTests(unittest.TestCase):
    def doc(self, verdicts):
        return {"review": "r.md", "claims": [{
            "id": cid, "claim": "x", "location": "p", "dois": [doi],
            "numbers": [],
            "adjudications": [{"doi": doi, "verdict": v, "quote": "", "note": ""}],
        } for (cid, doi), v in verdicts.items()]}

    def run_score(self, cand, gold, min_agreement=None):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "cand.json").write_text(json.dumps(self.doc(cand)))
        (tmp / "gold.json").write_text(json.dumps(self.doc(gold)))
        args = argparse.Namespace(audit=str(tmp / "cand.json"),
                                  gold=str(tmp / "gold.json"),
                                  min_agreement=min_agreement)
        verify_claims.cmd_score(args)

    def test_perfect_agreement_passes_threshold(self):
        pairs = {("C001", "10.1/a"): "supported", ("C002", "10.1/b"): "partial"}
        self.run_score(pairs, pairs, min_agreement=100)

    def test_disagreement_fails_threshold(self):
        gold = {("C001", "10.1/a"): "supported", ("C002", "10.1/b"): "partial"}
        cand = {("C001", "10.1/a"): "supported", ("C002", "10.1/b"): "supported"}
        with self.assertRaises(SystemExit):
            self.run_score(cand, gold, min_agreement=90)

    def test_no_overlap_errors(self):
        with self.assertRaises(SystemExit):
            self.run_score({("C009", "10.9/z"): "supported"},
                           {("C001", "10.1/a"): "supported"})


class SpelledNumberTests(unittest.TestCase):
    def test_spelled_numbers_normalize(self):
        self.assertEqual(verify_claims.spell_to_digits("Twenty-two subjects and forty-two more"),
                         "22 subjects and 42 more")
        self.assertEqual(verify_claims.spell_to_digits("Fifteen healthy adults"), "15 healthy adults")


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

    def test_binary_bodies_are_rejected_not_stored(self):
        self.assertEqual(claim_evidence.blocked_page("PK\x03\x04garbage" * 200), "binary_body")
        self.assertEqual(claim_evidence.blocked_page("%PDF-1.7 stream" * 200), "binary_body")
        self.assertIsNone(claim_evidence.blocked_page("<html><p>Real article text.</p></html>"))

    def test_numeric_windows_rank_first(self):
        filler = " ".join(["creatine cognition memory trial adults"] * 40)
        text = filler + " The effect bordered on significance (p = 0.067) for digit span. " + filler
        passages = verify_claims.candidate_passages(
            "creatine improved digit span (p=0.067) in adults", ["0.067"], text)
        self.assertIn("0.067", passages[0])

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
