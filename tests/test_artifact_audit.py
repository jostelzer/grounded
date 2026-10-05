"""Document artifact evidence must remain independently judged and byte-bound."""
import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/grounded/scripts'))
import audit_contract
import claim_inventory
import claim_receipts
import verify_claims


class ArtifactAuditTests(unittest.TestCase):
    def test_grouped_counts_and_week_units_preserve_values(self):
        for count in ('39 740', '39\u00a0740', '39\u202f740'):
            self.assertFalse(audit_contract.missing_quantities('39,740 adults', count + ' adults'))
        for duration in ('4 wk', '4-wk', '4 wks', 'four-week'):
            self.assertFalse(audit_contract.missing_quantities('4 weeks', duration))
        self.assertFalse(audit_contract.missing_quantities('one month', '1-month follow-up'))
        self.assertTrue(audit_contract.missing_quantities('39,740 adults', '39 741 adults'))
        self.assertTrue(audit_contract.missing_quantities('4 weeks', '4 days'))
        self.assertTrue(audit_contract.missing_quantities('4 weeks', '−4 wk'))
        self.assertNotEqual(audit_contract.quantities('1 2'), audit_contract.quantities('12'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'audit.json'
        self.artifact = self.root / 'manifest.json'
        self.artifact.write_text('{"database": "PubMed"}')
        self.markdown = 'This review searched PubMed.'
        claims = claim_inventory.extract_claims(self.markdown, include_uncited=True)
        self.audit = {'schema_version': 2, 'claims': claims, 'review': 'review.md',
                      'inventory_sha256': audit_contract.inventory_digest(claims)}
        self.path.write_text(json.dumps(self.audit))

    def classify(self, artifacts=None):
        verify_claims.cmd_classify(argparse.Namespace(
            audit=str(self.path), claim='C001', classification='artifact',
            note='The inspected database field records PubMed.', basis=None,
            artifact=[str(self.artifact)] if artifacts is None else artifacts))

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_claims.cmd_check(argparse.Namespace(audit=str(self.path), evidence=str(self.root),
                                                      strict=True, summary=None, appendix=None))
        return json.loads(self.path.read_text())

    def test_inspected_artifact_releases_and_receipts_disclose_hash(self):
        self.classify()
        audit = self.check()
        audit_contract.validate_release(audit, self.markdown, self.path)
        reference = audit['claims'][0]['artifacts'][0]
        self.assertEqual(reference['path'], 'manifest.json')
        receipts = claim_receipts.render_receipts_document(audit)
        self.assertIn(reference['sha256'], receipts)
        self.assertIn('manifest.json', receipts)

    def test_changed_file_invalidates_check_and_release(self):
        self.classify()
        audit = self.check()
        self.artifact.write_text('{"database": "Other"}')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            audit_contract.validate_release(audit, self.markdown, self.path)
        with self.assertRaises(SystemExit):
            self.check()
        self.assertNotIn('checked_sha256', json.loads(self.path.read_text()))

    def test_missing_file_invalidates_check_and_release(self):
        self.classify()
        audit = self.check()
        self.artifact.rename(self.root / 'moved.json')
        with self.assertRaisesRegex(ValueError, 'artifact missing'):
            audit_contract.validate_release(audit, self.markdown, self.path)
        with self.assertRaises(SystemExit):
            self.check()

    def test_missing_evidence_is_rejected_before_recording(self):
        for artifacts in ([], [str(self.root / 'missing.json')]):
            with self.subTest(artifacts=artifacts), self.assertRaises(SystemExit):
                self.classify(artifacts)
        self.assertEqual(json.loads(self.path.read_text()), self.audit)

    def test_cited_assertions_cannot_be_reclassified_even_by_manual_edit(self):
        self.audit['claims'][0]['dois'] = ['10.0000/example']
        self.path.write_text(json.dumps(self.audit))
        with self.assertRaisesRegex(SystemExit, 'cited assertions'):
            self.classify()
        self.audit['claims'][0].update(classification='artifact', classification_note='Inspected.',
                                       artifacts=[audit_contract.artifact_reference(self.artifact, self.path)])
        self.assertTrue(any('cited assertions' in e for e in audit_contract.coverage_errors(self.audit)))

    def test_caption_and_bullets_keep_sentence_local_sources(self):
        citation = '[Trial](https://doi.org/10.0000/example)'
        text = f'**Figure 1. A curve.** Pain fell {citation}. The line is blue.\n\n- Pain fell {citation}.\n- The panel is square. Another line is red.'
        claims = claim_inventory.extract_claims(text, include_uncited=True)
        self.assertEqual(len(claims), 6, claims)
        self.assertEqual([bool(c['dois']) for c in claims], [False, True, False, True, False, False])
        self.assertTrue(any('Another line is red.' in c['claim'] for c in claims))
        legacy = claim_inventory.extract_claims(text)
        self.assertEqual(legacy[0]['location'], 'figure 1 caption')
        self.assertIn('line is blue', legacy[0]['claim'])
        trailing = claim_inventory.extract_claims(
            f'**Figure 1. A curve.** Pain fell. {citation}', include_uncited=True)
        self.assertEqual(len(trailing), 2)
        self.assertEqual(trailing[1]['claim'], 'Pain fell.')
        self.assertEqual(trailing[1]['dois'], ['10.0000/example'])

    def test_marked_rounding_direction_words_and_detached_units_are_supported(self):
        supported = [
            ("about 16 minutes shorter to 16 minutes longer", "−16.1 to 15.8 minutes"),
            ("The extra sleep was 35 minutes", "35 more minutes of sleep"),
            ("about 4 points", "4.26 mm Hg (95% CI 3.62 to 4.89)"),
            ("nearly five years", "mean follow-up 4.74 years"),
            ("about 21,000 people", "20,995 persons"),
            ("about four and a half times the rate", "hazard ratio 4.53"),
            ("0.67 hours less school-time use", "−0.67 h"),
            ("about 250 mothers", "246 women"),
        ]
        for claim, quote in supported:
            self.assertFalse(audit_contract.missing_quantities(claim, quote), (claim, quote))

    def test_unmarked_rounding_wrong_units_and_bare_sign_changes_stay_unmatched(self):
        unmatched = [
            ("16 minutes shorter", "−16.1 minutes"),          # rounding not marked
            ("250 mothers", "246 women"),
            ("about 100 trials", "133 trials"),               # not a rounding of 133
            ("about 15 hours", "15 min"),                     # conflicting units
            ("Risk about 5%", "Risk 5.2"),                    # percent against a plain number
            ("0.67 hours", "−0.67 h"),                        # sign with no direction word
            ("about 4 points", "14.26 mm Hg"),
        ]
        for claim, quote in unmatched:
            self.assertTrue(audit_contract.missing_quantities(claim, quote), (claim, quote))

    def test_exact_conversions_frequencies_and_number_words_are_supported(self):
        supported = [
            ("The session lasted two hours", "a 120-min session"),
            ("followed to age 3 years", "through 36 months of age"),
            ("lasted 1.5 hours", "90 minutes"),
            ("two weeks later", "14 days after"),
            ("9.80 hours means nine hours and forty-eight minutes", "9.80 h"),
            ("About 38 in every 100 babies", "37.6% of infants"),
            ("About six in every hundred mothers", "6.2% of mothers"),
            ("about 4 in 10 babies", "37.6% of infants"),
            ("The difference was essentially zero", "difference −0.18 min"),
            ("gained 1.4 hours a day", "1.4 h/day"),
            ("One hundred six infants took part", "106 infants"),
            ("106 infants took part", "One hundred six infants were enrolled"),
            ("246 mothers", "Two hundred and forty-six women"),
        ]
        for claim, quote in supported:
            self.assertFalse(audit_contract.missing_quantities(claim, quote), (claim, quote))

    def test_conversions_and_frequencies_do_not_excuse_wrong_values(self):
        unmatched = [
            ("lasted 2 hours", "90 minutes"),                 # a different duration
            ("three weeks later", "14 days after"),
            ("38 in every 100 babies", "37.6% of infants"),   # rounding not marked
            ("about 4 in 10 babies", "33.0% of infants"),     # too far for "about 4 in 10"
            ("about 4 in 10 babies", "40 infants"),           # a count is not a share
            ("gained 1.4 hours", "1.4 h/day"),                # the rate is not named
            ("5 mg", "5 g"),
            ("hundreds of studies and 3 trials", "2 trials"),
        ]
        for claim, quote in unmatched:
            self.assertTrue(audit_contract.missing_quantities(claim, quote), (claim, quote))

    def test_time_unit_aliases_preserve_sign_and_unit_distinctions(self):
        for unit in ('h', 'hr', 'hrs', 'hour', 'hours'):
            self.assertFalse(audit_contract.missing_quantities('−0.67 hours', f'−0.67 {unit}'))
        for unit in ('min', 'mins', 'minute', 'minutes'):
            self.assertFalse(audit_contract.missing_quantities('15 minutes', f'15 {unit}'))
        self.assertTrue(audit_contract.missing_quantities('0.67 hours', '−0.67 h'))
        self.assertTrue(audit_contract.missing_quantities('15 hours', '15 min'))


if __name__ == '__main__':
    unittest.main()
