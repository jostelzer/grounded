import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import export_review  # noqa: E402


class WritePdfTests(unittest.TestCase):
    def test_chrome_success_atomically_replaces_existing_pdf(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "review.pdf")
            with open(out, "wb") as f:
                f.write(b"%PDF-old")

            def render(cmd, **_kwargs):
                target = next(arg.split("=", 1)[1] for arg in cmd
                              if arg.startswith("--print-to-pdf="))
                with open(target, "wb") as f:
                    f.write(b"%PDF-fresh")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            with mock.patch.object(export_review, "find_chrome", return_value="/fake/chrome"), \
                    mock.patch.object(export_review.subprocess, "run", side_effect=render):
                tool = export_review.write_pdf("<p>new</p>", out)

            self.assertEqual(tool, "chrome")
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-fresh")

    def test_stale_existing_pdf_is_not_mistaken_for_failed_render(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "review.pdf")
            with open(out, "wb") as f:
                f.write(b"%PDF-old")
            failed = subprocess.CompletedProcess([], 1, "", "renderer failed")

            with mock.patch.object(export_review, "find_chrome", return_value="/fake/chrome"), \
                    mock.patch.object(export_review.subprocess, "run", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "renderer failed"):
                    export_review.write_pdf("<p>new</p>", out)

            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-old")


class FigureExportTests(unittest.TestCase):
    def markdown(self, caption=None, reference=True):
        if caption is None:
            caption = (
                "**Figure 1. A transient signal builds memory.** "
                "The solid steps are observed; the dashed step is inferred. "
                "[Smith 2024](https://doi.org/10.1000/example)"
            )
        body_reference = (
            "The pathway is summarized in [Figure 1](#fig-mechanism).\n\n"
            if reference else "The pathway is summarized below.\n\n")
        return (
            "## Test review\n\n**TL;DR** — Test.\n\n" + body_reference +
            '<a id="fig-mechanism"></a>\n'
            "![A three-stage mechanism](figure.png)\n\n" + caption +
            "\n\n**Sources**\n\n"
            "**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )

    def test_numbered_cited_caption_and_cross_reference_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            _title, _lead, body = export_review.to_html(
                self.markdown(), base_dir=tmp)
        self.assertIn('<a href="#fig-mechanism">Figure 1</a>', body)
        self.assertIn('<figure id="fig-mechanism">', body)
        self.assertIn('<b class="figno">Figure 1.</b>', body)
        self.assertIn('<b class="figtitle">A transient signal builds memory.</b>', body)
        self.assertEqual(body.count("Figure 1."), 1)

    def test_missing_caption_is_rejected_by_exporter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            with self.assertRaisesRegex(ValueError, "must have a numbered caption"):
                export_review.to_html(
                    self.markdown(caption="Not a caption."), base_dir=tmp)

    def test_uncited_caption_is_rejected_by_exporter(self):
        caption = "**Figure 1. A title.** Explanation without a source."
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            with self.assertRaisesRegex(ValueError, "must contain a DOI citation"):
                export_review.to_html(self.markdown(caption=caption), base_dir=tmp)

    def test_unreferenced_figure_is_rejected_by_exporter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            with self.assertRaisesRegex(ValueError, "referenced from the text"):
                export_review.to_html(
                    self.markdown(reference=False), base_dir=tmp)

    def test_structured_bullet_caption_renders_inside_figcaption(self):
        caption = (
            "**Figure 1. A plain-language mechanism.**\n"
            "- **Shows:** Three steps.\n"
            "- **Evidence boundary:** The dashed step is uncertain.\n"
            "- **Sources:** [Smith 2024](https://doi.org/10.1000/example)"
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            _title, _lead, body = export_review.to_html(
                self.markdown(caption=caption), base_dir=tmp)
        self.assertIn('<figcaption><b class="figno">Figure 1.</b>', body)
        self.assertIn("<ul><li><strong>Shows:</strong> Three steps.</li>", body)
        self.assertIn("<strong>Sources:</strong>", body)


if __name__ == "__main__":
    unittest.main()
