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

    def test_time_unit_aliases_preserve_sign_and_unit_distinctions(self):
        for unit in ('h', 'hr', 'hrs', 'hour', 'hours'):
            self.assertFalse(audit_contract.missing_quantities('−0.67 hours', f'−0.67 {unit}'))
        for unit in ('min', 'mins', 'minute', 'minutes'):
            self.assertFalse(audit_contract.missing_quantities('15 minutes', f'15 {unit}'))
        self.assertTrue(audit_contract.missing_quantities('0.67 hours', '−0.67 h'))
        self.assertTrue(audit_contract.missing_quantities('15 hours', '15 min'))


if __name__ == '__main__':
    unittest.main()
