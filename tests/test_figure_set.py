"""Review-wide figure routing must not disappear between planning and export."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/grounded/scripts'))
from figure_provenance import validate_figure_set


class FigureSetTests(unittest.TestCase):
    def records(self, routes, available=True):
        specs = [{'quality_contract_version': 3, 'render_route': route} for route in routes]
        provenance = [{
            'generator_available': available,
            'generator_detection': {
                'method': 'session-tool-enumeration',
                'evidence': 'Checked direct and discoverable tools in this test session.',
            },
        } for _ in routes]
        return specs, provenance

    def test_available_generator_rejects_all_plot_review(self):
        self.assertTrue(validate_figure_set(*self.records(['deterministic'] * 3)))

    def test_composite_anchor_does_not_replace_explanatory_illustration(self):
        self.assertTrue(validate_figure_set(*self.records(['deterministic', 'composite'])))

    def test_mixed_review_passes(self):
        self.assertEqual(validate_figure_set(*self.records(['generated', 'deterministic'])), [])

    def test_observed_generator_absence_allows_plots(self):
        self.assertEqual(validate_figure_set(*self.records(['deterministic'] * 2, False)), [])

    def test_absence_requires_detection(self):
        specs, records = self.records(['deterministic'] * 2, False)
        records[0].pop('generator_detection')
        self.assertTrue(validate_figure_set(specs, records))

    def test_conflicting_capability_cannot_hide_available_generator(self):
        specs, records = self.records(['deterministic'] * 2)
        records[0]['generator_available'] = False
        self.assertTrue(validate_figure_set(specs, records))

    def test_malformed_detection_method_returns_error_without_crashing(self):
        for method in ([], {}, None, 1):
            with self.subTest(method=method):
                specs, records = self.records(['deterministic'], False)
                records[0]['generator_detection']['method'] = method
                errors = validate_figure_set(specs, records)
                self.assertTrue(any('generator_detection' in error for error in errors))

    def test_explicit_numeric_scope_exception_is_review_wide(self):
        specs, records = self.records(['deterministic'] * 2)
        reason = ('The requested report compares only published effect estimates; '
                  'the supplied evidence contains no supported mechanism or study-design question requiring illustration.')
        records[0]['quantitative_only_reason'] = reason
        self.assertTrue(validate_figure_set(specs, records))
        records[1]['quantitative_only_reason'] = reason
        self.assertEqual(validate_figure_set(specs, records), [])
        records[1]['quantitative_only_reason'] = 'Plots are easier.'
        self.assertTrue(validate_figure_set(specs, records))

    def test_single_visual_does_not_trigger_a_mix_quota(self):
        self.assertEqual(validate_figure_set(*self.records(['deterministic'])), [])

    def test_malformed_or_missing_provenance_fails(self):
        specs, records = self.records(['deterministic', 'generated'])
        self.assertTrue(validate_figure_set(specs, records[:1]))
        self.assertTrue(validate_figure_set(specs, [None, records[1]]))

    def test_legacy_contract_remains_reproducible(self):
        self.assertEqual(validate_figure_set([{'quality_contract_version': 2}], [{}]), [])


if __name__ == '__main__':
    unittest.main()
