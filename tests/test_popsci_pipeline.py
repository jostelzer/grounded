import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
EVALS = Path(__file__).resolve().parents[1] / "evals" / "popsci-writing"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(EVALS))

import audit_popsci  # noqa: E402
import audit_search  # noqa: E402
import claim_evidence  # noqa: E402
import fact_bank  # noqa: E402
import paragraph_profile  # noqa: E402
import readability_profile  # noqa: E402
import reader_questions  # noqa: E402
import score_comprehension  # noqa: E402
import validate_review  # noqa: E402

DOI_A, DOI_B = "10.1000/trial", "10.1000/review"
LEDGER = {"entries": [
    {"key": "Trial2013", "doi": DOI_A, "authors": ["Robyn Stremler", "Ellen Hodnett"],
     "year": 2013, "title": "A sleep education trial"},
    {"key": "Review2020", "doi": DOI_B, "authors": ["Ana Dias", "Ben Field", "Cy Rocha"],
     "year": 2020, "title": "Infant sleep across the first year"},
]}
TEXT_A = ("We randomised 246 first-time mothers to sleep education or usual care. "
          "Infants wore ankle actigraphs at 6 and 12 weeks. The between-group "
          "difference in longest sleep period was -0.18 minutes.")
TEXT_B = ("Sleep is regulated by a circadian process and by homeostatic sleep "
          "pressure that builds during waking. The longest sleep period increased "
          "over the first six months.")
SYNTHESIS = """# Synthesis — Can young babies sleep longer stretches?

## Verdict
Sleep lessons did not lengthen the longest stretch; age did.

## Throughline
Follow one trial, then widen to development.

## Claims

### C1. Sleep education did not lengthen infants' longest night sleep in one trial.
- strength: limited — one trial
- evidence: randomised trial, 246 mothers [@Trial2013]
- quote: [@Trial2013] "We randomised 246 first-time mothers to sleep education or usual care."
- contrary: none found — searched
- boundary: first-time mothers, first 12 weeks
- depends-on: —
- numbers: 246 mothers; difference -0.18 minutes

### C2. The longest sleep period grows over the first six months.
- strength: moderate — systematic review
- evidence: systematic review [@Review2020]
- quote: [@Review2020] "The longest sleep period increased over the first six months."
- contrary: none found — searched
- boundary: healthy term infants
- depends-on: —
- numbers: —
"""
FACTS = """# Fact bank — Can young babies sleep longer stretches?

### F1. The trial enrolled 246 first-time mothers.
- kind: method
- quote: [@Trial2013] "We randomised 246 first-time mothers to sleep education or usual care."
- answers: Q2
- supports: C1

### F2. Babies wore ankle actigraphs, small movement monitors.
- kind: method
- quote: [@Trial2013] "Infants wore ankle actigraphs at 6 and 12 weeks."
- answers: Q2

### F3. Sleep pressure "builds during waking".
- kind: definition
- quote: [@Review2020] "homeostatic sleep pressure that builds during waking"
- answers: Q1
"""
QUESTIONS = """# Reader questions

Reader: a parent of a young baby with no science training

### Q1. Why do babies wake so often?
- type: how-it-works
- priority: core
- answered-by: F3, C2
- status: answered

### Q2. How did researchers measure sleep?
- type: how-we-know
- priority: core
- answered-by: F1, F2
- status: answered

### Q3. How much longer could the stretches get?
- type: how-big
- priority: core
- answered-by: C2
- status: partial — the review gives no single number for longest-stretch growth

### Q4. Should I expect my baby to sleep through?
- type: meaning
- priority: useful
- answered-by: C2
- status: answered

### Q5. What is still unknown?
- type: unknown
- priority: useful
- status: unanswerable — no study tested the scenario the reader describes
"""


def make_store(tmp):
    store = Path(tmp) / "evidence"
    claim_evidence.store_text(DOI_A, store, TEXT_A, {"tier": "fulltext"})
    claim_evidence.store_text(DOI_B, store, TEXT_B, {"tier": "abstract"})
    return store


class FactBankTests(unittest.TestCase):
    def test_quote_anchored_bank_passes_and_reports_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = fact_bank.check_facts(FACTS, make_store(tmp), LEDGER, SYNTHESIS)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["metrics"]["kinds"], {"definition": 1, "method": 2})

    def test_invented_number_quote_and_unknown_claim_fail(self):
        bad = FACTS.replace("enrolled 246", "enrolled 300").replace(
            '"builds during waking"', '"builds all day"').replace("supports: C1", "supports: C9")
        with tempfile.TemporaryDirectory() as tmp:
            result = fact_bank.check_facts(bad, make_store(tmp), LEDGER, SYNTHESIS)
        joined = " ".join(result["errors"])
        self.assertIn("number 300", joined)
        self.assertIn("quoted words", joined)
        self.assertIn("C9", joined)

    def test_non_verbatim_quote_and_unknown_kind_fail(self):
        bad = FACTS.replace("Infants wore ankle actigraphs", "Infants wore wrist actigraphs").replace(
            "kind: definition", "kind: opinion")
        with tempfile.TemporaryDirectory() as tmp:
            result = fact_bank.check_facts(bad, make_store(tmp), LEDGER)
        joined = " ".join(result["errors"])
        self.assertIn("not verbatim", joined)
        self.assertIn("kind must be", joined)

    def test_numbers_inside_names_are_not_quantities(self):
        self.assertEqual(fact_bank.quantities("Omega-3 and omega-6 fats in 246 mothers"), ["246"])
        self.assertEqual(fact_bank.quantities("Stage 2 hypertension begins at 140, type 2 diabetes aside"),
                         ["140"])

    def test_fact_quotes_merge_by_doi(self):
        quotes = fact_bank.quotes_by_doi(FACTS, LEDGER)
        self.assertEqual([fid for fid, _q in quotes[DOI_A]], ["F1", "F2"])


class ReaderQuestionTests(unittest.TestCase):
    def test_answered_questions_pass_draft_stage(self):
        result = reader_questions.check_questions(QUESTIONS, "draft", FACTS, SYNTHESIS)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["metrics"]["core_answered"], 2)

    def test_open_core_question_and_missing_types_fail(self):
        text = QUESTIONS.replace("- answered-by: F1, F2\n- status: answered",
                                 "- status: open").replace("type: unknown", "type: what")
        result = reader_questions.check_questions(text, "draft", FACTS, SYNTHESIS)
        joined = " ".join(result["errors"])
        self.assertIn("Q2 (core) is still open", joined)
        self.assertIn("'unknown'", joined)
        self.assertEqual(reader_questions.check_questions(
            text.replace("type: what", "type: unknown"), "plan")["status"], "pass")

    def test_unexplained_partial_and_dangling_reference_fail(self):
        text = QUESTIONS.replace(
            "partial — the review gives no single number for longest-stretch growth",
            "partial").replace("answered-by: F3, C2", "answered-by: F9")
        joined = " ".join(reader_questions.check_questions(text, "draft", FACTS, SYNTHESIS)["errors"])
        self.assertIn("say what is missing", joined)
        self.assertIn("F9", joined)


TOUR = """## A headline

*A standfirst that invites the reader in.*

### The first part

The 2020 analysis pooled 133 trials with 12,197 adults, and sodium fell by 130 millimoles, about 7.6 grams, while pressure fell 4.3 mmHg (95% confidence interval 3.6 to 4.9) [@Trial2013]. This review describes more below [@Trial2013], [@Review2020].

Sleep pressure builds while you are awake and drains away while you sleep [@Review2020]. The finding does not establish why any one baby wakes [@Review2020].

**Scope and methods.** A narrative review searched on 4 October 2026 in PubMed and OpenAlex; Crossref verified records.

**Sources**

**Trial (2013)** T. *J*. https://doi.org/10.1000/trial
"""


class ReadabilityTests(unittest.TestCase):
    def test_a_limitation_repeated_as_a_refrain_is_flagged(self):
        filler = "Researchers assigned 246 families by lot and followed their babies for twelve weeks [@Trial2013]. " * 3
        refrain = [
            "The study measured totals, leaving the gain in the longest block unanswered [@Trial2013].",
            "The total-night result still leaves the longest block unresolved [@Trial2019].",
            "The trial did not measure the longest uninterrupted stretch [@Trial2018].",
            "These results leave the lasting effects of the lessons unresolved [@Trial2013].",
        ]
        text = "# Title\n\n*Standfirst.*\n\n" + "\n\n".join(filler + closer for closer in refrain)
        result = readability_profile.profile(text)
        self.assertEqual(len(result["passages"]["caveat_closers"]), 4)
        self.assertTrue(any("end on a caveat" in flag for flag in result["flags"]))

    def test_profile_counts_load_and_points_at_passages(self):
        result = readability_profile.profile(TOUR)
        measures, passages = result["measures"], result["passages"]
        self.assertEqual(measures["paragraphs"], 2)  # standfirst and scope note are apparatus
        self.assertEqual(measures["sources_cited"], 2)
        self.assertEqual(passages["number_heavy_sentences"][0]["numbers"], 8)
        self.assertIn("confidence interval", passages["statistics_in_prose"])
        self.assertIn("millimoles", passages["lab_units"])
        self.assertEqual(len(passages["self_reference"]), 1)
        self.assertEqual(len(passages["caveat_closers"]), 1)
        self.assertTrue(any("talk about the article" in f for f in result["flags"]))
        long_tour = TOUR.replace("### The first part\n\n", "### The first part\n\n" + (
            "The pooled analysis of 40 trials found a fall of 4.3 points in 2,000 adults [@Trial2013]. " * 30))
        self.assertTrue(any("numbers_per_100_words" in f
                            for f in readability_profile.profile(long_tour)["flags"]))

    def test_plain_prose_is_clear_and_names_are_not_numbers(self):
        plain = ("## T\n\n*S.*\n\n### Part\n\nOmega-3 fats come mostly from fish [@Trial2013]. "
                 "People who ate more of them in 2019 had about a third fewer attacks [@Trial2013].\n")
        result = readability_profile.profile(plain)
        self.assertEqual(result["flags"], [])
        self.assertEqual(result["measures"]["numbers_per_100_words"], 0.0)

    def test_reader_copy_has_no_citations_or_sources(self):
        copy = readability_profile.reader_copy(TOUR)
        self.assertNotIn("[@", copy)
        self.assertNotIn("**Sources**", copy)
        self.assertIn("fell 4.3 mmHg (95% confidence interval 3.6 to 4.9).", copy)

    def test_rendered_doi_citations_are_stripped_too(self):
        rendered = TOUR.replace("[@Trial2013]", "[Stremler et al. 2013](https://doi.org/10.1000/trial)")
        self.assertEqual(readability_profile.profile(rendered)["measures"]["prose_words"],
                         readability_profile.profile(TOUR)["measures"]["prose_words"])


class QuizTests(unittest.TestCase):
    QUIZ = {"schema_version": 1, "items": [
        {"id": f"K{i}", "kind": kind, "prompt": "?", "options": {"A": "a", "B": "b", "C": "c"},
         "answer": "B", "basis": ["F1"], **({"certainty_order": ["A", "B", "C"]}
                                            if kind == "certainty" else {})}
        for i, kind in enumerate(["method", "method", "certainty", "certainty", "magnitude",
                                  "fact", "misconception", "mechanism"], 1)]}

    def test_quiz_validation(self):
        self.assertEqual(score_comprehension.validate_quiz(self.QUIZ), [])
        broken = json.loads(json.dumps(self.QUIZ))
        broken["items"][2]["certainty_order"] = ["A"]
        broken["items"][0]["answer"] = "Z"
        errors = " ".join(score_comprehension.validate_quiz(broken))
        self.assertIn("certainty_order", errors)
        self.assertIn("answer is not", errors)

    def test_scoring_tracks_accuracy_coverage_and_calibration(self):
        answers = {"reader": "parent", "article": "X", "answers": {
            "K1": "B", "K2": "N", "K3": "A", "K4": "C", "K5": "B", "K6": "B", "K7": "C", "K8": "B"}}
        result = score_comprehension.score(self.QUIZ, [answers])
        reader = result["readers"][0]
        self.assertEqual(reader["correct"], 4)
        self.assertEqual(reader["not_said"], 1)
        self.assertEqual(reader["overconfident"], 1)
        self.assertEqual(reader["underconfident"], 1)
        self.assertEqual(reader["misconception_chosen"], 1)
        self.assertEqual(result["articles"]["X"]["accuracy"], 0.5)


class ProfileTests(unittest.TestCase):
    def test_draft_outside_corpus_range_is_flagged(self):
        def article(labels):
            return {"paragraphs": [{"label": l, "has_number": l == "finding",
                                    "has_quote": False, "approx_words": 90} for l in labels]}
        corpus = {"articles": [article(["scene", "orientation", "method", "finding",
                                        "explanation", "complication", "finding", "payoff"])
                               for _ in range(5)]}
        draft = article(["orientation", "finding", "complication", "complication",
                         "complication", "finding", "complication", "payoff"])
        result = paragraph_profile.profile(corpus, draft)
        flagged = " ".join(result["flags"])
        self.assertIn("first_method_position", flagged)
        self.assertIn("longest_complication_run", flagged)
        self.assertEqual(result["corpus_articles"], 5)

    def test_shipped_corpus_has_labelled_articles(self):
        corpus = json.loads((EVALS / "popsci-feature-corpus.json").read_text())
        self.assertGreaterEqual(len(corpus["articles"]), 15)
        labels = {p["label"] for a in corpus["articles"] for p in a["paragraphs"]}
        self.assertLessEqual(labels, set(paragraph_profile.LABELS))


class SearchAndAuditTests(unittest.TestCase):
    def test_popsci_search_requires_background_lane(self):
        records = [
            {"completed": True, "method": "keyword", "angle_id": f"a{i}", "lane": lane,
             "requested_query_or_seed": f"q{i}{j}", "accepted": 1}
            for i, lane in enumerate(["primary", "contrary-null", "reviews"]) for j in range(2)]
        manifest = {"schema_version": 1, "records": records}
        plain = audit_search.audit_search(manifest, size="small")
        popsci = audit_search.audit_search(manifest, size="small", style="popsci")
        self.assertFalse(any("background" in e for e in plain["errors"]))
        self.assertTrue(any("background lane" in e for e in popsci["errors"]))

    def test_working_steps_audit_lists_missing_records_and_passes_complete_case(self):
        article = ("## Why babies wake\n\n*A standfirst.*\n\n### The trial\n\n"
                   "The trial enrolled 246 first-time mothers [@Trial2013]. "
                   "Sleep pressure builds during waking [@Review2020].\n")
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            make_store(tmp)
            (case / "sources.json").write_text(json.dumps(LEDGER))
            (case / "synthesis.md").write_text(SYNTHESIS)
            (case / "facts.md").write_text(FACTS)
            (case / "reader-questions.md").write_text(QUESTIONS)
            missing = audit_popsci.audit(case, "small")
            self.assertEqual(missing["status"], "fail")
            self.assertIn("missing cold-read.md", missing["errors"])
            self.assertIn("missing review_draft.md", missing["errors"])
            (case / "review_draft.md").write_text(article)
            (case / "cold-read.md").write_text("## Reader 1\n\nfine\n\n## Reader 2\n\nfine\n")
            needs_repairs = audit_popsci.audit(case, "small")
            self.assertTrue(any("Repairs" in e for e in needs_repairs["errors"]))
            (case / "cold-read.md").write_text(
                "## Reader 1\n\nfine\n\n## Reader 2\n\nfine\n\n## Repairs\n\n- none\n")
            result = audit_popsci.audit(case, "small")
            self.assertEqual(result["status"], "pass", result["errors"])
            self.assertTrue(any("review_draft.v1.md" in w for w in result["warnings"]))
            (case / "review_draft.v1.md").write_text(article)
            same = audit_popsci.audit(case, "small")
            self.assertEqual(same["records"]["revision"], "no heavier")
            (case / "review_draft.md").write_text(
                article + "\nThe study did not measure the longest stretch [@Trial2013]. "
                "That leaves the main question unanswered [@Trial2013].\n")
            heavier = audit_popsci.audit(case, "small")
            self.assertEqual(heavier["status"], "pass")
            self.assertTrue(any("heavier than the first draft" in w and "limit or hedge" in w
                                for w in heavier["warnings"]), heavier["warnings"])
            (case / "review_draft.md").write_text(article)
            (case / "review_draft.md").write_text(
                article.replace("Sleep pressure", "As this review shows, sleep pressure"))
            self.assertTrue(any("talks about itself" in e
                                for e in audit_popsci.audit(case, "small")["errors"]))


if __name__ == "__main__":
    unittest.main()
