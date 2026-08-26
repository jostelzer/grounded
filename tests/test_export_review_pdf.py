import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import export_review  # noqa: E402
import qa_review_pdf  # noqa: E402
import weasyprint_export  # noqa: E402


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

    @staticmethod
    def write_review(markdown, out, base_dir, **options):
        page = export_review.build_html(
            markdown, base_dir=base_dir, release="v-test",
            repo="example.test/grounded", compiled_date="2026-08-26",
            **options,
        )
        return weasyprint_export.write_pdf(page, out)

    def test_actual_pdf_is_deterministic_and_preserves_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            first = os.path.join(tmp, "first.pdf")
            second = os.path.join(tmp, "second.pdf")
            result_a = self.write_review(self.markdown(), first, tmp)
            result_b = self.write_review(self.markdown(), second, tmp)
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

    def test_metadata_uses_fixed_compilation_date(self):
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            self.write_review(self.markdown(), pdf, tmp)
            metadata = PdfReader(pdf).metadata
            self.assertEqual(metadata["/Author"], "Grounded")
            self.assertEqual(metadata["/Creator"], "Grounded")
            self.assertEqual(metadata["/CreationDate"], "D:20260826")
            self.assertEqual(metadata["/Producer"], "WeasyPrint 69.0")

    def test_render_failure_preserves_existing_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "review.pdf")
            with open(out, "wb") as stream:
                stream.write(b"%PDF-old")
            with self.assertRaisesRegex(ValueError, "does not exist"):
                self.write_review(self.markdown(image="missing.png"), out, tmp)
            with open(out, "rb") as stream:
                self.assertEqual(stream.read(), b"%PDF-old")

    def test_renderer_failure_preserves_existing_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "review.pdf")
            with open(out, "wb") as stream:
                stream.write(b"%PDF-old")
            with mock.patch.object(
                    weasyprint_export, "require_runtime",
                    return_value={"interface": "python"}), mock.patch.object(
                        weasyprint_export, "_render_with_python",
                        side_effect=weasyprint_export.PdfRuntimeError("render failed")):
                with self.assertRaisesRegex(
                        weasyprint_export.PdfRuntimeError, "render failed"):
                    weasyprint_export.write_pdf("<html></html>", out)
            with open(out, "rb") as stream:
                self.assertEqual(stream.read(), b"%PDF-old")

    def test_asset_path_cannot_escape_review_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            review_dir = os.path.join(tmp, "review")
            os.mkdir(review_dir)
            self.make_image(os.path.join(tmp, "outside.png"))
            with self.assertRaisesRegex(ValueError, "escapes the review directory"):
                self.write_review(
                    self.markdown(image="../outside.png"),
                    os.path.join(review_dir, "review.pdf"), review_dir,
                )

    def test_remote_figure_assets_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "remote figure assets"):
                self.write_review(
                    self.markdown(image="https://example.com/figure.png"),
                    os.path.join(tmp, "review.pdf"), tmp,
                )

    def test_invalid_compilation_date_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                export_review.build_html(
                    self.markdown(), base_dir=tmp,
                    compiled_date="26 August 2026",
                )

    def test_svg_figure_is_embedded_without_a_companion_raster(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.svg"), "w", encoding="utf-8") as stream:
                stream.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" '
                    'height="700"><rect width="1200" height="700" '
                    'fill="white"/><path d="M80 350H1120" stroke="#ff4f1f" '
                    'stroke-width="12"/></svg>'
                )
            pdf = os.path.join(tmp, "review.pdf")
            self.write_review(self.markdown(image="figure.svg"), pdf, tmp)
            self.assertTrue(os.path.isfile(pdf))

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
            self.write_review(markdown, pdf, tmp, columns=1)
            inspection = qa_review_pdf.inspect_structure(pdf, markdown)
            self.assertEqual(inspection["expected_figures"], 0)
            self.assertGreaterEqual(inspection["external_links"], 1)

    def test_auto_hyphenation_uses_ascii_hyphens(self):
        from pypdf import PdfReader

        paragraph = " ".join([
            "Messenger RNA vaccination separates the information that defines "
            "an antigen from the machinery that manufactures and delivers it. "
            "The central tension is programmability, while formulation and "
            "immune context determine what the message can accomplish."
        ] * 30)
        markdown = (
            "## Hyphenation review\n\n**Abstract** — A short summary.\n\n"
            "### Long technical prose\n\n" + paragraph + "\n\n"
            "**Sources**\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "hyphenation.pdf")
            self.write_review(markdown, pdf, tmp)
            extracted = "\n".join(
                (page.extract_text() or "") for page in PdfReader(pdf).pages)
            self.assertNotIn("\u2010", extracted)
            self.assertIn("-\n", extracted)

    def test_spanning_table_and_figure_stay_with_their_headings_in_pdf(self):
        from pypdf import PdfReader

        filler = "\n\n".join([
            "A deliberately repeated evidence paragraph fills the preceding "
            "columns so the next display block reaches a page boundary. "
            "The claim remains compact, cited, and suitable for pagination testing."
        ] * 35)
        markdown = (
            "## Pagination review\n\n**Abstract** — A short summary.\n\n"
            "### Setup\n\n" + filler + "\n\n"
            "### Evidence certainty\n\n"
            "| Outcome | Conclusion |\n"
            "|---|---|\n"
            "| Sleep | TABLE_PAYLOAD |\n\n" + filler + "\n\n"
            "The pathway is summarized in [Figure 1](#fig-mechanism).\n\n"
            "### Mechanism diagram\n\n"
            '<a id="fig-mechanism"></a>\n'
            "![A three-stage mechanism](figure.png)\n\n"
            "**Figure 1. FIGURE_PAYLOAD.** The solid steps are observed; "
            "the dashed step is inferred. "
            "[Smith 2024](https://doi.org/10.1000/example)\n\n"
            "**Sources**\n\n"
            "**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "pagination.pdf")
            self.write_review(markdown, pdf, tmp)
            pages = [page.extract_text() or "" for page in PdfReader(pdf).pages]

        def page_number(token):
            matches = [index for index, text in enumerate(pages, 1) if token in text]
            self.assertEqual(len(matches), 1, token)
            return matches[0]

        table_page = page_number("Evidence certainty")
        self.assertGreater(table_page, 1)
        self.assertEqual(table_page, page_number("TABLE_PAYLOAD"))
        figure_page = page_number("Mechanism diagram")
        self.assertGreater(figure_page, table_page)
        self.assertEqual(figure_page, page_number("FIGURE_PAYLOAD"))

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_independent_raster_qa_checks_every_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            render_dir = os.path.join(tmp, "render")
            self.write_review(self.markdown(), pdf, tmp)
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
            self.write_review(self.markdown(), pdf, tmp)
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "not empty"):
                qa_review_pdf.render_and_inspect(pdf, render_dir, dpi=120)

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_raster_qa_rejects_a_masthead_that_did_not_paint(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "unpainted-header.pdf")
            render_dir = os.path.join(tmp, "render")
            writer = PdfWriter()
            writer.add_blank_page(width=595.2756, height=841.8898)
            with open(pdf, "wb") as stream:
                writer.write(stream)
            with self.assertRaisesRegex(
                    qa_review_pdf.PdfQaError, "masthead raster|masthead chip|body raster"):
                qa_review_pdf.render_and_inspect(pdf, render_dir, dpi=120)

    def test_canonical_examples_keep_v2_pagination_and_running_masthead(self):
        from pypdf import PdfReader

        examples = (
            ("prose-small-blue-light-sleep.md", 2),
            ("prose-image-mrna-vaccines.md", 6),
            ("prose-large-mediterranean-diet.md", 11),
        )
        example_dir = os.path.join(ROOT, "examples")
        with tempfile.TemporaryDirectory() as tmp:
            for filename, expected_pages in examples:
                source = os.path.join(example_dir, filename)
                with open(source, encoding="utf-8") as stream:
                    markdown = stream.read()
                output = os.path.join(tmp, filename.replace(".md", ".pdf"))
                page = export_review.build_html(
                    markdown, base_dir=example_dir, release="v2.0.0",
                    compiled_date="2026-08-26",
                )
                weasyprint_export.write_pdf(page, output)
                reader = PdfReader(output)
                self.assertEqual(len(reader.pages), expected_pages)
                for number, pdf_page in enumerate(reader.pages, 1):
                    text = pdf_page.extract_text() or ""
                    self.assertIn("G R O U N D E D", text)
                    self.assertIn("NO FLOATING CLAIMS.", text)
                    self.assertIn(f"{number} / {expected_pages}", text)


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
