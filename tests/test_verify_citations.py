import importlib.util
import os
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    path = os.path.join(ROOT, "scripts", name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VC = load("verify_citations")
FR = load("format_references")


def work(**overrides):
    record = {
        "DOI": "10.1000/original",
        "type": "journal-article",
        "title": ["A perfectly ordinary paper"],
        "container-title": ["Journal of Tests"],
        "author": [{"family": "Smith", "given": "Ada", "sequence": "first"}],
        "issued": {"date-parts": [[2020]]},
        "volume": "1",
        "page": "1-10",
    }
    record.update(overrides)
    return record


def update(utype, label=None, doi="10.1000/notice"):
    entry = {"DOI": doi, "type": utype, "source": "publisher"}
    if label is not None:
        entry["label"] = label
    return entry


class ClassifyUpdateTests(unittest.TestCase):
    def test_severities(self):
        cases = {
            ("retraction", ""): "retraction",
            ("partial_retraction", ""): "retraction",
            ("withdrawal", ""): "retraction",
            ("removal", ""): "retraction",
            ("", "retraction"): "retraction",
            ("expression_of_concern", ""): "concern",
            ("", "expression of concern"): "concern",
            ("corrigendum", ""): "correction",
            ("erratum", ""): "correction",
            ("correction", ""): "correction",
            ("", "corrigendum"): "correction",
            ("new_version", ""): None,
            ("new_edition", ""): None,
            ("", ""): None,
        }
        for (utype, label), expected in cases.items():
            with self.subTest(utype=utype, label=label):
                self.assertEqual(VC.classify_update(utype, label), expected)


class UpdateSignalTests(unittest.TestCase):
    def test_retraction_in_updated_by(self):
        signals = VC.crossref_update_signals(work(**{"updated-by": [update("retraction")]}))
        self.assertEqual([s["severity"] for s in signals], ["retraction"])
        self.assertEqual(signals[0]["relation"], "updated-by")

    def test_expression_of_concern_is_detected(self):
        signals = VC.crossref_update_signals(
            work(**{"updated-by": [update("expression_of_concern", "Expression of concern")]}))
        self.assertEqual([s["severity"] for s in signals], ["concern"])

    def test_corrigendum_is_detected_but_distinct(self):
        # Real-world shape: 10.3389/fnut.2024.1424972 carries a publisher corrigendum.
        signals = VC.crossref_update_signals(
            work(**{"updated-by": [update("corrigendum", "Corrigendum", "10.3389/fnut.2025.1570800")]}))
        self.assertEqual([s["severity"] for s in signals], ["correction"])

    def test_unrelated_update_types_are_ignored(self):
        signals = VC.crossref_update_signals(work(**{"updated-by": [update("new_version")]}))
        self.assertEqual(signals, [])

    def test_title_fallback_carries_retraction_severity(self):
        signals = VC.crossref_update_signals(work(title=["Retraction: A perfectly ordinary paper"]))
        self.assertEqual([s["severity"] for s in signals], ["retraction"])

    def test_paper_about_retractions_is_not_flagged(self):
        signals = VC.crossref_update_signals(
            work(title=["Retractions in oncology journals: a bibliometric study"]))
        self.assertEqual(signals, [])


class VerifyOneTests(unittest.TestCase):
    def verify(self, record):
        entry = {"key": "Smith2020", "doi": "10.1000/original",
                 "title": "A perfectly ordinary paper", "year": 2020}
        with mock.patch.object(VC, "crossref", return_value=(record, None)):
            return VC.verify_one(entry)

    def test_clean_record_is_clear(self):
        status, reasons, _canonical, details = self.verify(work())
        self.assertEqual(status, "verified")
        self.assertEqual(details["retraction_status"], "clear")
        self.assertEqual(details["correction_notices"], [])
        self.assertEqual(reasons, [])

    def test_retraction_blocks(self):
        status, reasons, _c, details = self.verify(work(**{"updated-by": [update("retraction")]}))
        self.assertEqual(status, "failed")
        self.assertEqual(details["retraction_status"], "flagged")
        self.assertTrue(any("RETRACTED" in r for r in reasons))

    def test_withdrawal_blocks(self):
        status, _r, _c, details = self.verify(work(**{"updated-by": [update("withdrawal")]}))
        self.assertEqual(status, "failed")
        self.assertEqual(details["retraction_status"], "flagged")

    def test_expression_of_concern_blocks_with_accurate_wording(self):
        status, reasons, _c, details = self.verify(
            work(**{"updated-by": [update("expression_of_concern", "Expression of concern")]}))
        self.assertEqual(status, "failed")
        self.assertEqual(details["retraction_status"], "flagged")
        self.assertTrue(any("EXPRESSION OF CONCERN" in r for r in reasons))
        self.assertFalse(any("RETRACTED" in r for r in reasons))

    def test_corrigendum_warns_but_does_not_block(self):
        status, reasons, _c, details = self.verify(
            work(**{"updated-by": [update("corrigendum", "Corrigendum", "10.3389/fnut.2025.1570800")]}))
        self.assertEqual(status, "verified")
        self.assertEqual(details["retraction_status"], "clear")
        self.assertEqual(len(details["correction_notices"]), 1)
        self.assertTrue(any("published correction" in r for r in reasons))
        self.assertTrue(any("10.3389/fnut.2025.1570800" in r for r in reasons))


class CorrectionNoteTests(unittest.TestCase):
    def test_no_notices_no_note(self):
        self.assertEqual(FR.correction_note({"verification": {"correction_notices": []}}), "")
        self.assertEqual(FR.correction_note({}), "")

    def test_note_links_the_correction_doi(self):
        entry = {"verification": {"correction_notices": [
            {"severity": "correction", "doi": "10.3389/fnut.2025.1570800"}]}}
        note = FR.correction_note(entry)
        self.assertEqual(
            note,
            " Correction: [10.3389/fnut.2025.1570800]"
            "(https://doi.org/10.3389/fnut.2025.1570800).")

    def test_note_without_doi_is_still_factual(self):
        entry = {"verification": {"correction_notices": [{"severity": "correction", "doi": ""}]}}
        self.assertEqual(FR.correction_note(entry), " A published correction exists.")

    def test_flagged_entry_is_still_not_verified(self):
        entry = {
            "status": "verified", "canonical": {"title": "x"},
            "verification": {"bibliographic_status": "verified", "retraction_status": "flagged"},
        }
        self.assertFalse(FR.is_verified(entry))


if __name__ == "__main__":
    unittest.main()
