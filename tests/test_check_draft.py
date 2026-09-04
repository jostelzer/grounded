"""Draft check: citations in any form → resolved references → normalized draft → report."""

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
sys.path.insert(0, str(ROOT / "scripts"))

import check_draft  # noqa: E402
import verify_claims  # noqa: E402


DRAFT = """Brain creatine rose 8.7% after four weeks [1]. A trial found d=0.17 on digit span [2].
Vegetarians doubled their working memory (Hartwell et al., 2011), and Lee (2020) agreed.
Bare DOI: creatine and sleep loss https://doi.org/10.1007/s00213-005-0269-z helped mood.

References

1. Dechent P, Frahm J. Increase of total creatine in human brain after oral supplementation. Am J Physiol. 1999;277:R698.
2. Sandkühler JF, et al. The effects of creatine supplementation on cognitive performance. BMC Med. 2023;21:440. https://doi.org/10.1186/s12916-023-03146-5
Hartwell K, Bloom S. Creatine and working-memory doubling in vegetarian adults. J Cogn Nutr. 2011;4:112.
Lee J. Creatine, cognition and age. Nutrients. 2020;12:1.
"""

CATALOGUE = {
    "increase of total creatine": {"DOI": "10.1152/ajpregu.1999.277.3.r698",
        "title": ["Increase of total creatine in human brain after oral supplementation of creatine-monohydrate"],
        "author": [{"family": "Dechent"}], "issued": {"date-parts": [[1999]]}},
    "creatine, cognition and age": {"DOI": "10.3390/nu12000001", "title": ["Creatine, cognition and age"],
        "author": [{"family": "Lee"}], "issued": {"date-parts": [[2020]]}},
}


def fake_search(query, rows=3):
    for needle, item in CATALOGUE.items():
        if needle in query.lower():
            return [item]
    # Crossref always returns *something*; a near-miss must not resolve.
    return [{"DOI": "10.1/nearmiss", "title": ["Comment on roasted peanut consumption"],
             "author": [{"family": "Li"}], "issued": {"date-parts": [[2026]]}}]


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.normalized, self.ledger, self.resolution = check_draft.ingest(DRAFT, search=fake_search)
        self.refs = {r["handle"]: r for r in self.resolution["references"]}

    def test_every_citation_form_is_detected(self):
        self.assertEqual(self.resolution["citations"], 5)
        kinds = {c["kind"] for c in check_draft.detect_citations(check_draft.split_reference_list(DRAFT)[0])}
        self.assertEqual(kinds, {"numeric", "author-year", "narrative", "doi-url"})

    def test_numeric_references_resolve_by_search_or_embedded_doi(self):
        self.assertEqual(self.refs["num:1"]["status"], "resolved")
        self.assertEqual(self.refs["num:1"]["doi"], "10.1152/ajpregu.1999.277.3.r698")
        self.assertEqual(self.refs["num:2"]["method"], "doi-in-reference")

    def test_fabricated_reference_is_unresolved_and_named_by_the_draft(self):
        hartwell = self.refs["ay:hartwell:2011"]
        self.assertEqual(hartwell["status"], "unresolved")
        self.assertIsNone(hartwell["doi"])
        self.assertEqual(hartwell["label"], "Hartwell 2011")   # never the near-miss author
        self.assertFalse(any(h.startswith("list:hartwell") for h in self.refs))  # no duplicate record

    def test_narrative_and_bare_doi_citations_resolve(self):
        self.assertEqual(self.refs["ay:lee:2020"]["doi"], "10.3390/nu12000001")
        self.assertEqual(self.refs["doi:10.1007/s00213-005-0269-z"]["status"], "resolved")

    def test_normalized_draft_is_readable_by_the_claim_extractor(self):
        self.assertIn("[Dechent 1999](https://doi.org/10.1152/ajpregu.1999.277.3.r698)", self.normalized)
        self.assertIn("[Sandkühler et al. 2023](https://doi.org/10.1186/s12916-023-03146-5)", self.normalized)
        self.assertNotIn("(n.d.)** 1007/", self.normalized)
        self.assertEqual(self.normalized.count("https://doi.org/10.1186/s12916-023-03146-5"), 2)
        self.assertIn("(Hartwell et al., 2011)", self.normalized)   # unresolved stays as written
        self.assertIn("Lee [Lee 2020](https://doi.org/10.3390/nu12000001) agreed", self.normalized)
        self.assertIn("**Sources**", self.normalized)
        claims = verify_claims.extract_claims(self.normalized)
        dois = {d for c in claims for d in c["dois"]}
        self.assertEqual(len(dois), 4)
        self.assertEqual({e["key"] for e in self.ledger["entries"]}.__len__(), 4)


class ReportTests(unittest.TestCase):
    def test_report_scorecard_names_fabricated_retracted_and_unsupported(self):
        _n, ledger, resolution = check_draft.ingest(DRAFT, search=fake_search)
        for e in ledger["entries"]:
            e["status"] = "verified"
            e["verification"] = {"bibliographic_status": "verified", "retraction_status": "clear", "reasons": []}
        ledger["entries"][0]["status"] = "failed"
        ledger["entries"][0]["verification"] = {"bibliographic_status": "verified", "retraction_status": "flagged",
                                                "reasons": ["RETRACTED per Crossref metadata"]}
        audit = {"claims": [
            {"id": "C001", "claim": "Brain creatine rose 8.7% after four weeks.", "location": "paragraph 1, sentence 1",
             "dois": ["10.1152/ajpregu.1999.277.3.r698"], "numbers": ["8.7%"],
             "adjudications": [{"doi": "10.1152/ajpregu.1999.277.3.r698", "verdict": "supported", "quote": "8.7%", "note": "", "tier": "abstract"}]},
            {"id": "C002", "claim": "A trial found d=0.17 on digit span.", "location": "paragraph 1, sentence 2",
             "dois": ["10.1186/s12916-023-03146-5"], "numbers": ["0.17"],
             "adjudications": [{"doi": "10.1186/s12916-023-03146-5", "verdict": "not_found", "quote": "", "note": "", "tier": "fulltext"}]},
        ]}
        report = check_draft.render_report(resolution, ledger, audit, title="test")
        self.assertIn("**References:** 5 cited · 3 verified · 1 retracted/concern · 1 not found", report)
        self.assertIn("**Hartwell 2011** · NOT FOUND", report)
        self.assertIn("RETRACTED or under expression of concern", report)
        self.assertIn("**Sentences:** 2 inventoried · 2 source checks · 1 supported (0 at full text) · 0 partial · 1 unsupported · 0 contradicted", report)
        self.assertIn("## Citations to fix", report)
        self.assertIn("C002 · Sandkühler", report)


if __name__ == "__main__":
    unittest.main()
