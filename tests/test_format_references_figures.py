import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "format_references.py")
SPEC = importlib.util.spec_from_file_location("format_references", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def figure_block(figure_id="mechanism", citation="[@Paper2024]"):
    return (
        "The pathway is summarized in {{figure:%s}}.\n\n"
        "![A three-stage mechanism](mechanism.png)\n\n"
        "**Figure {#%s}. A transient signal builds memory.** "
        "Observed delivery is solid; one signalling step is inferred. %s"
    ) % (figure_id, figure_id, citation)


class FigureResolutionTests(unittest.TestCase):
    def test_numbers_anchors_and_body_links_follow_figure_order(self):
        text = (
            figure_block("mechanism") + "\n\n" +
            "The outcome comparison appears in {{figure:outcomes}}.\n\n"
            "![Two aligned outcomes](outcomes.png)\n"
            "**Figure {#outcomes}. Outcomes separate cleanly.** "
            "The denominators remain distinct. [@Paper2024]"
        )
        resolved, errors, figures = MODULE.resolve_figures(text)
        self.assertEqual(errors, [])
        self.assertEqual([f["number"] for f in figures], [1, 2])
        self.assertIn("[Figure 1](#fig-mechanism)", resolved)
        self.assertIn("[Figure 2](#fig-outcomes)", resolved)
        self.assertIn('<a id="fig-mechanism"></a>\n![', resolved)
        self.assertIn("**Figure 2. Outcomes separate cleanly.**", resolved)
        self.assertNotIn("{{figure:", resolved)
        self.assertNotIn("{#", resolved)

    def test_missing_caption_is_rejected(self):
        text = "![Description](figure.png)"
        _resolved, errors, _figures = MODULE.resolve_figures(text)
        self.assertTrue(any("every figure must" in error for error in errors))

    def test_uncited_caption_is_rejected(self):
        text = figure_block(citation="No source here.")
        _resolved, errors, _figures = MODULE.resolve_figures(text)
        self.assertIn("figure caption has no ledger citation: mechanism", errors)

    def test_structured_bullet_caption_is_supported(self):
        text = (
            "The pathway is summarized in {{figure:mechanism}}.\n\n"
            "![A three-stage mechanism](mechanism.png)\n"
            "**Figure {#mechanism}. A transient signal builds memory.**\n"
            "- **Shows:** Delivery, translation and immune memory.\n"
            "- **Evidence boundary:** One signalling step is inferred.\n"
            "- **Sources:** [@Paper2024]"
        )
        resolved, errors, _figures = MODULE.resolve_figures(text)
        self.assertEqual(errors, [])
        self.assertIn("**Figure 1. A transient signal builds memory.**\n- **Shows:**", resolved)
        self.assertIn("- **Sources:** [@Paper2024]", resolved)

    def test_duplicate_unknown_and_unreferenced_ids_are_rejected(self):
        text = (
            "Unknown {{figure:missing}}.\n\n"
            "![First](one.png)\n"
            "**Figure {#same}. First title.** Evidence. [@Paper2024]\n\n"
            "![Second](two.png)\n"
            "**Figure {#same}. Second title.** Evidence. [@Paper2024]"
        )
        _resolved, errors, _figures = MODULE.resolve_figures(text)
        self.assertIn("duplicate figure id: same", errors)
        self.assertIn("unknown figure reference: missing", errors)
        self.assertIn("figure is never referenced from the text: same", errors)

    def test_caption_citation_is_verified_and_enters_sources(self):
        ledger = {
            "entries": [{
                "key": "Paper2024",
                "doi": "10.1000/example",
                "status": "verified",
                "verification": {
                    "bibliographic_status": "verified",
                    "retraction_status": "clear"
                },
                "canonical": {
                    "title": "A verified figure source",
                    "journal": "Journal of Tests",
                    "year": 2024,
                    "authors_structured": [{"family": "Smith", "given": "Ada"}]
                }
            }]
        }
        draft = "## Test\n\n**TL;DR** — Test.\n\n" + figure_block()
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = os.path.join(tmp, "sources.json")
            draft_path = os.path.join(tmp, "draft.md")
            out_path = os.path.join(tmp, "review.md")
            with open(ledger_path, "w", encoding="utf-8") as stream:
                json.dump(ledger, stream)
            with open(draft_path, "w", encoding="utf-8") as stream:
                stream.write(draft)
            result = subprocess.run(
                [sys.executable, SCRIPT, "--ledger", ledger_path,
                 "--draft", draft_path, "--out", out_path,
                 "--style", "bracket"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with open(out_path, encoding="utf-8") as stream:
                rendered = stream.read()
        self.assertIn("[Figure 1](#fig-mechanism)", rendered)
        self.assertIn("**Figure 1. A transient signal builds memory.**", rendered)
        self.assertIn("[Smith 2024](https://doi.org/10.1000/example)", rendered)
        self.assertIn("**Smith A (2024)** A verified figure source.", rendered)


if __name__ == "__main__":
    unittest.main()
