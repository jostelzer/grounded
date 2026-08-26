import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import export_review  # noqa: E402
import qa_review_pdf  # noqa: E402
import reportlab_export  # noqa: E402


class PdfExportTests(unittest.TestCase):
    @staticmethod
    def markdown(image="figure.png"):
        return (
            "## Test review\n\n**TL;DR** — Test.\n\n"
            "The pathway is summarized in [Figure 1](#fig-mechanism).\n\n"
            '<a id="fig-mechanism"></a>\n'
            f"![A three-stage mechanism]({image})\n\n"
            "**Figure 1. A transient signal builds memory.** "
            "The solid steps are observed; the dashed step is inferred. "
            "[Smith 2024](https://doi.org/10.1000/example)\n\n"
            "**Sources**\n\n"
            "**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )

    @staticmethod
    def make_image(path):
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB", (1200, 700), "white")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((80, 120, 1120, 580), outline="#ff4f1f", width=12)
        draw.line((160, 350, 1040, 350), fill="#141414", width=8)
        canvas.save(path)

    def test_actual_pdf_is_deterministic_and_preserves_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            first = os.path.join(tmp, "first.pdf")
            second = os.path.join(tmp, "second.pdf")
            kwargs = dict(
                base_dir=tmp, release="v-test", repo_label="example/grounded",
                compiled_date="2026-08-26",
            )
            result_a = reportlab_export.write_pdf(self.markdown(), first, **kwargs)
            result_b = reportlab_export.write_pdf(self.markdown(), second, **kwargs)
            with open(first, "rb") as stream:
                first_bytes = stream.read()
            with open(second, "rb") as stream:
                second_bytes = stream.read()

            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(result_a["sha256"], result_b["sha256"])
            self.assertTrue(first_bytes.startswith(b"%PDF-"))
            inspection = qa_review_pdf.inspect_structure(first, self.markdown())
            self.assertEqual(inspection["expected_dois"], 1)
            self.assertGreaterEqual(inspection["internal_links"], 1)
            self.assertEqual(inspection["expected_figures"], 1)

    def test_render_failure_preserves_existing_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "review.pdf")
            with open(out, "wb") as stream:
                stream.write(b"%PDF-old")
            with self.assertRaisesRegex(
                    reportlab_export.PdfInputError, "does not exist"):
                reportlab_export.write_pdf(
                    self.markdown(image="missing.png"), out,
                    base_dir=tmp, compiled_date="2026-08-26",
                )
            with open(out, "rb") as stream:
                self.assertEqual(stream.read(), b"%PDF-old")

    def test_asset_path_cannot_escape_review_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            review_dir = os.path.join(tmp, "review")
            os.mkdir(review_dir)
            self.make_image(os.path.join(tmp, "outside.png"))
            with self.assertRaisesRegex(
                    reportlab_export.PdfInputError, "escapes the review directory"):
                reportlab_export.write_pdf(
                    self.markdown(image="../outside.png"),
                    os.path.join(review_dir, "review.pdf"),
                    base_dir=review_dir, compiled_date="2026-08-26",
                )

    def test_remote_figure_assets_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                    reportlab_export.PdfInputError, "remote figure assets"):
                reportlab_export.write_pdf(
                    self.markdown(image="https://example.com/figure.png"),
                    os.path.join(tmp, "review.pdf"), base_dir=tmp,
                    compiled_date="2026-08-26",
                )

    def test_invalid_compilation_date_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                    reportlab_export.PdfInputError, "YYYY-MM-DD"):
                reportlab_export.write_pdf(
                    self.markdown(), os.path.join(tmp, "review.pdf"),
                    base_dir=tmp, compiled_date="26 August 2026",
                )

    def test_svg_requires_committed_pdf_companion(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.svg"), "w", encoding="utf-8") as stream:
                stream.write('<svg xmlns="http://www.w3.org/2000/svg"/>')
            with self.assertRaisesRegex(
                    reportlab_export.PdfInputError, "companion PNG"):
                reportlab_export.write_pdf(
                    self.markdown(image="figure.svg"),
                    os.path.join(tmp, "review.pdf"), base_dir=tmp,
                    compiled_date="2026-08-26",
                )

    def test_cli_does_not_write_html_sidecar_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            markdown = os.path.join(tmp, "review.md")
            pdf = os.path.join(tmp, "review.pdf")
            with open(markdown, "w", encoding="utf-8") as stream:
                stream.write(self.markdown())
            completed = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "export_review.py"),
                 "--in", markdown, "--out", pdf, "--pdf",
                 "--release", "v-test", "--compiled-date", "2026-08-26"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(os.path.isfile(pdf))
            self.assertFalse(os.path.exists(os.path.join(tmp, "review.html")))

    def test_single_column_review_without_figures(self):
        markdown = (
            "## Plain review\n\n**Abstract** — A short summary.\n\n"
            "### One supported conclusion\n\n"
            "The body remains readable and cites "
            "[Smith 2024](https://doi.org/10.1000/example).\n\n"
            "**Sources**\n\n**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "review.pdf")
            reportlab_export.write_pdf(
                markdown, pdf, base_dir=tmp, columns=1,
                compiled_date="2026-08-26",
            )
            inspection = qa_review_pdf.inspect_structure(pdf, markdown)
            self.assertEqual(inspection["expected_figures"], 0)
            self.assertGreaterEqual(inspection["external_links"], 1)

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_independent_raster_qa_checks_every_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            render_dir = os.path.join(tmp, "render")
            reportlab_export.write_pdf(
                self.markdown(), pdf, base_dir=tmp, compiled_date="2026-08-26",
            )
            structural = qa_review_pdf.inspect_structure(pdf, self.markdown())
            raster = qa_review_pdf.render_and_inspect(pdf, render_dir, dpi=120)
            self.assertEqual(raster["rendered_pages"], structural["pages"])
            self.assertTrue(raster["contact_sheets"])

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_raster_qa_refuses_a_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            render_dir = os.path.join(tmp, "render")
            os.mkdir(render_dir)
            with open(os.path.join(render_dir, "keep.txt"), "w", encoding="utf-8") as stream:
                stream.write("do not overwrite")
            reportlab_export.write_pdf(
                self.markdown(), pdf, base_dir=tmp, compiled_date="2026-08-26",
            )
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "not empty"):
                qa_review_pdf.render_and_inspect(pdf, render_dir, dpi=120)

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_raster_qa_rejects_a_masthead_that_did_not_paint(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen.canvas import Canvas

        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "unpainted-header.pdf")
            render_dir = os.path.join(tmp, "render")
            canvas = Canvas(pdf, pagesize=A4, invariant=1)
            canvas.setAuthor("Grounded")
            canvas.setCreator("Grounded")
            canvas.setSubject("Agentically generated scientific review")
            canvas.setFillColorRGB(1, 1, 1)
            canvas.drawString(40, 800, "G R O U N D E D   NO FLOATING CLAIMS.")
            canvas.drawString(520, 20, "1 / 1")
            canvas.setFillColorRGB(0, 0, 0)
            for row in range(50):
                canvas.drawString(50, 740 - row * 12, "Visible review body content " * 4)
            canvas.showPage()
            canvas.save()
            with self.assertRaisesRegex(
                    qa_review_pdf.PdfQaError, "masthead raster|masthead chip"):
                qa_review_pdf.render_and_inspect(pdf, render_dir, dpi=120)


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
