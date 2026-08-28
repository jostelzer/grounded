"""Golden-run pipeline test recorded from the infant-colic review.

Runs formatter -> validator -> figure QA -> exporter -> PDF QA entirely
offline against tests/fixtures/colic (verification results are frozen in the
fixture ledger; no network calls happen here). This is the tripwire that
keeps hardening work from destroying known-good behavior: see
references/contracts.md.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "colic")
sys.path.insert(0, SCRIPTS)

import qa_figure  # noqa: E402


def run_script(name, *args, stdin_text=None, cwd=None):
    return subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, name), *args],
        input=stdin_text, capture_output=True, text=True, cwd=cwd,
    )


def has_pdf_runtime():
    try:
        import weasyprint_export
        weasyprint_export.require_runtime()
        return True
    except Exception:
        return False


class GoldenColicPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="grounded-golden-")
        for name in os.listdir(FIXTURE):
            shutil.copy(os.path.join(FIXTURE, name), self.tmp)
        self.ledger = os.path.join(self.tmp, "sources.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def format_draft(self):
        completed = run_script(
            "format_references.py",
            "--ledger", self.ledger,
            "--draft", os.path.join(self.tmp, "review_draft.md"),
            "--style", "bracket",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def test_formatter_resolves_all_citations(self):
        markdown = self.format_draft()
        self.assertIn("**Sources**", markdown)
        self.assertNotIn("[@", markdown)
        self.assertEqual(markdown.count("https://doi.org/10.1136/bmj.g2107") >= 2, True)

    def test_validator_passes_strict_popsci_small_with_figure(self):
        markdown = self.format_draft()
        report_path = os.path.join(self.tmp, "validation.json")
        completed = run_script(
            "validate_review.py", "-",
            "--style", "popsci", "--size", "small",
            "--ledger", self.ledger,
            "--fulltext-manifest", os.path.join(self.tmp, "fulltext-manifest.json"),
            "--strict-tier", "--image-mode",
            "--report", report_path,
            stdin_text=markdown, cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.load(open(report_path, encoding="utf-8"))
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertEqual(report["metrics"]["figures"], 1)
        self.assertEqual(report["metrics"]["source_dois"], 20)

    def test_figure_qa_passes_with_recorded_inspection(self):
        spec = json.load(open(os.path.join(self.tmp, "colic-treatments.figure.json")))
        inspection = json.load(
            open(os.path.join(self.tmp, "colic-treatments-inspection.json"))
        )
        result = qa_figure.audit_figure(
            spec, os.path.join(self.tmp, "colic-treatments.png"),
            inspection=inspection,
        )
        self.assertEqual(result["status"], "pass", result["errors"])

    @unittest.skipUnless(has_pdf_runtime(), "pinned WeasyPrint runtime missing")
    def test_export_produces_release_pdf(self, extra_args=(),
                                         expected_edition="salon"):
        out = os.path.join(self.tmp, "review.pdf")
        completed = run_script(
            "export_review.py",
            "--in", os.path.join(self.tmp, "review.md"),
            "--out", out, "--pdf",
            "--style", "popsci",
            "--kicker", "Review · Paediatrics",
            "--ledger", self.ledger,
            "--release-manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--figure-spec", os.path.join(self.tmp, "colic-treatments.figure.json"),
            "--figure-prompt", os.path.join(self.tmp, "colic-treatments.prompt.txt"),
            "--release", "v-test", "--repo", "example.test/grounded",
            "--compiled-date", "2026-08-27",
            *extra_args,
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(os.path.exists(out))
        manifest = json.load(
            open(os.path.join(self.tmp, "release-manifest.json"), encoding="utf-8")
        )
        self.assertEqual(manifest["render"]["edition"], expected_edition)

    @unittest.skipUnless(
        has_pdf_runtime() and shutil.which("pdftoppm"),
        "WeasyPrint runtime or Poppler missing",
    )
    def test_journal_edition_export_still_passes(self):
        self.test_export_produces_release_pdf(
            extra_args=("--edition", "journal"),
            expected_edition="journal",
        )

    @unittest.skipUnless(
        has_pdf_runtime() and shutil.which("pdftoppm"),
        "WeasyPrint runtime or Poppler missing",
    )
    def test_salon_pull_quote_export_passes_qa(self):
        self.test_export_produces_release_pdf(
            extra_args=(
                "--pull-quote",
                "benefit in breastfed infants, none in formula-fed",
            ),
        )
        completed = run_script(
            "qa_review_pdf.py",
            os.path.join(self.tmp, "review.pdf"),
            "--manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--render-dir", os.path.join(self.tmp, "qa-render-pull"),
            "--report", os.path.join(self.tmp, "pdf-qa-pull.json"),
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    @unittest.skipUnless(
        has_pdf_runtime() and shutil.which("pdftoppm"),
        "WeasyPrint runtime or Poppler missing",
    )
    def test_pdf_qa_passes_end_to_end(self):
        self.test_export_produces_release_pdf()
        completed = run_script(
            "qa_review_pdf.py",
            os.path.join(self.tmp, "review.pdf"),
            "--manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--render-dir", os.path.join(self.tmp, "qa-render"),
            "--report", os.path.join(self.tmp, "pdf-qa.json"),
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.load(open(os.path.join(self.tmp, "pdf-qa.json"), encoding="utf-8"))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["visible_reference_dois"], 20)


class GoldenEli5PipelineTests(unittest.TestCase):
    """The ELI5 golden run shares the colic evidence base (ledger, figure,
    full-text manifest) with a validated ELI5 rendition of the same claims,
    rendered in the primer edition."""

    ELI5_FIXTURE = os.path.join(ROOT, "tests", "fixtures", "colic-eli5")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="grounded-golden-eli5-")
        for source in (FIXTURE, self.ELI5_FIXTURE):
            for name in os.listdir(source):
                shutil.copy(os.path.join(source, name), self.tmp)
        self.ledger = os.path.join(self.tmp, "sources.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validator_passes_strict_eli5_small(self):
        report_path = os.path.join(self.tmp, "validation.json")
        completed = run_script(
            "validate_review.py", os.path.join(self.tmp, "review.md"),
            "--style", "eli5", "--size", "small",
            "--ledger", self.ledger,
            "--fulltext-manifest", os.path.join(self.tmp, "fulltext-manifest.json"),
            "--strict-tier", "--image-mode",
            "--report", report_path,
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.load(open(report_path, encoding="utf-8"))
        self.assertEqual(report["status"], "pass", report["errors"])

    @unittest.skipUnless(
        has_pdf_runtime() and shutil.which("pdftoppm"),
        "WeasyPrint runtime or Poppler missing",
    )
    def test_eli5_primer_export_passes_qa(self):
        out = os.path.join(self.tmp, "review.pdf")
        completed = run_script(
            "export_review.py",
            "--in", os.path.join(self.tmp, "review.md"),
            "--out", out, "--pdf",
            "--style", "eli5",
            "--kicker", "Explainer · Paediatrics",
            "--ledger", self.ledger,
            "--release-manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--figure-spec", os.path.join(self.tmp, "colic-treatments.figure.json"),
            "--figure-prompt", os.path.join(self.tmp, "colic-treatments.prompt.txt"),
            "--release", "v-test", "--repo", "example.test/grounded",
            "--compiled-date", "2026-08-28",
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        manifest = json.load(
            open(os.path.join(self.tmp, "release-manifest.json"), encoding="utf-8")
        )
        self.assertEqual(manifest["render"]["edition"], "primer")
        completed = run_script(
            "qa_review_pdf.py", out,
            "--manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--render-dir", os.path.join(self.tmp, "qa-render"),
            "--report", os.path.join(self.tmp, "pdf-qa.json"),
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.load(open(os.path.join(self.tmp, "pdf-qa.json"), encoding="utf-8"))
        self.assertEqual(report["status"], "pass")


class GoldenBulletsPipelineTests(unittest.TestCase):
    """The bullets golden run shares the colic evidence base with a
    validated bullets rendition of the same claims, rendered in the brief
    edition (drawn double-chevron markers)."""

    BULLETS_FIXTURE = os.path.join(ROOT, "tests", "fixtures", "colic-bullets")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="grounded-golden-bullets-")
        for source in (FIXTURE, self.BULLETS_FIXTURE):
            for name in os.listdir(source):
                shutil.copy(os.path.join(source, name), self.tmp)
        self.ledger = os.path.join(self.tmp, "sources.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_validator_passes_strict_bullets_small(self):
        report_path = os.path.join(self.tmp, "validation.json")
        completed = run_script(
            "validate_review.py", os.path.join(self.tmp, "review.md"),
            "--style", "bullets", "--size", "small",
            "--ledger", self.ledger,
            "--fulltext-manifest", os.path.join(self.tmp, "fulltext-manifest.json"),
            "--strict-tier", "--image-mode",
            "--report", report_path,
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.load(open(report_path, encoding="utf-8"))
        self.assertEqual(report["status"], "pass", report["errors"])

    @unittest.skipUnless(
        has_pdf_runtime() and shutil.which("pdftoppm"),
        "WeasyPrint runtime or Poppler missing",
    )
    def test_bullets_brief_export_passes_qa(self):
        out = os.path.join(self.tmp, "review.pdf")
        completed = run_script(
            "export_review.py",
            "--in", os.path.join(self.tmp, "review.md"),
            "--out", out, "--pdf",
            "--style", "bullets",
            "--kicker", "Brief · Paediatrics",
            "--ledger", self.ledger,
            "--release-manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--figure-spec", os.path.join(self.tmp, "colic-treatments.figure.json"),
            "--figure-prompt", os.path.join(self.tmp, "colic-treatments.prompt.txt"),
            "--release", "v-test", "--repo", "example.test/grounded",
            "--compiled-date", "2026-08-28",
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        manifest = json.load(
            open(os.path.join(self.tmp, "release-manifest.json"), encoding="utf-8")
        )
        self.assertEqual(manifest["render"]["edition"], "brief")
        completed = run_script(
            "qa_review_pdf.py", out,
            "--manifest", os.path.join(self.tmp, "release-manifest.json"),
            "--render-dir", os.path.join(self.tmp, "qa-render"),
            "--report", os.path.join(self.tmp, "pdf-qa.json"),
            cwd=self.tmp,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.load(open(os.path.join(self.tmp, "pdf-qa.json"), encoding="utf-8"))
        self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main()
