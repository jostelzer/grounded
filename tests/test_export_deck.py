import os
import sys
import tempfile
import unittest


ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import export_deck  # noqa: E402
import weasyprint_export  # noqa: E402


def verified_entry(key="Smith2024"):
    return {
        "key": key,
        "doi": "10.1000/example",
        "status": "verified",
        "verification": {
            "bibliographic_status": "verified",
            "retraction_status": "clear",
        },
        "canonical": {
            "title": "A verified result",
            "year": 2024,
            "journal": "Journal of Tests",
            "authors_structured": [{"family": "Smith", "given": "Alex"}],
        },
    }


class DeckExportTests(unittest.TestCase):
    @staticmethod
    def storyboard():
        roles = ("question", "evidence", "limitations", "conclusion")
        return {
            "title": "What does the evidence show?",
            "subtitle": "A compact verified review",
            "style": "scientific",
            "size": "small",
            "reference_keys": ["Smith2024"],
            "slides": [
                {
                    "id": f"slide-{index}",
                    "role": role,
                    "title": f"Claim {index} is supported.",
                    "image": "slide.png",
                    "alt": f"Diagram supporting claim {index}.",
                    "citations": ["Smith2024"],
                    "evidence": "strong" if index == 2 else "mixed",
                }
                for index, role in enumerate(roles, 1)
            ],
        }

    @staticmethod
    def ledger():
        return {"entries": [verified_entry()]}

    @staticmethod
    def make_image(path):
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB", (1600, 900), "white")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((100, 220, 1500, 680), outline="#ff4f1f", width=16)
        canvas.save(path)

    def test_storyboard_contract_builds_title_content_and_reference_slides(self):
        document = export_deck.validate_storyboard(self.storyboard(), self.ledger())
        self.assertEqual(document.total_slides, 6)
        self.assertEqual(len(document.slides), 4)
        self.assertEqual(len(document.reference_pages), 1)

    def test_unverified_reference_is_a_hard_failure(self):
        ledger = self.ledger()
        ledger["entries"][0]["verification"]["retraction_status"] = "retracted"
        with self.assertRaisesRegex(
            export_deck.DeckValidationError, "reference is not verified"
        ):
            export_deck.validate_storyboard(self.storyboard(), ledger)

    def test_style_arc_is_enforced(self):
        storyboard = self.storyboard()
        storyboard["slides"][0]["role"] = "evidence"
        with self.assertRaisesRegex(
            export_deck.DeckValidationError, "must begin with role question"
        ):
            export_deck.validate_storyboard(storyboard, self.ledger())

    def test_slide_images_must_be_local_readable_and_16_by_9(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "slide.png"))
            document = export_deck.validate_storyboard(self.storyboard(), self.ledger())
            embedded = export_deck.embed_slide_images(document, tmp)
            self.assertEqual(set(embedded), {f"slide-{index}" for index in range(1, 5)})

            from PIL import Image

            Image.new("RGB", (800, 800), "white").save(os.path.join(tmp, "slide.png"))
            with self.assertRaisesRegex(
                export_deck.DeckValidationError, "must be 16:9"
            ):
                export_deck.embed_slide_images(document, tmp)

    def test_html_keeps_claims_and_doi_citations_as_real_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "slide.png"))
            page = export_deck.build_html(
                self.storyboard(),
                self.ledger(),
                base_dir=tmp,
                release="v-test",
                repo="example.test/grounded",
                compiled_date="2026-08-27",
            )
            self.assertIn("Claim 1 is supported.", page)
            self.assertIn("https://doi.org/10.1000/example", page)
            self.assertIn("data:image/png;base64,", page)
            self.assertIn("grounded v-test</span>", page)

    def test_actual_pdf_is_deterministic_16_by_9_and_preserves_links(self):
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "slide.png"))
            page = export_deck.build_html(
                self.storyboard(),
                self.ledger(),
                base_dir=tmp,
                release="v-test",
                repo="example.test/grounded",
                compiled_date="2026-08-27",
            )
            first = os.path.join(tmp, "first.pdf")
            second = os.path.join(tmp, "second.pdf")
            result_a = weasyprint_export.write_pdf(page, first)
            result_b = weasyprint_export.write_pdf(page, second)
            with open(first, "rb") as stream:
                first_bytes = stream.read()
            with open(second, "rb") as stream:
                second_bytes = stream.read()
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(result_a["sha256"], result_b["sha256"])

            reader = PdfReader(first, strict=True)
            self.assertEqual(len(reader.pages), 6)
            for pdf_page in reader.pages:
                self.assertAlmostEqual(float(pdf_page.mediabox.width), 960, places=1)
                self.assertAlmostEqual(float(pdf_page.mediabox.height), 540, places=1)
            annotations = [
                annotation.get_object()
                for pdf_page in reader.pages
                for annotation in (pdf_page.get("/Annots") or [])
            ]
            uris = [
                str(annotation["/A"]["/URI"])
                for annotation in annotations
                if annotation.get("/A") and annotation["/A"].get("/URI")
            ]
            self.assertIn("https://doi.org/10.1000/example", uris)


if __name__ == "__main__":
    unittest.main()
