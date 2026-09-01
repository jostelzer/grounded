import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import export_deck  # noqa: E402
import qa_deck_pdf  # noqa: E402
import weasyprint_export  # noqa: E402


class DeckFixture:
    @staticmethod
    def ledger(count=10):
        return {
            "entries": [
                {
                    "key": f"Paper{number}",
                    "doi": f"10.1000/deck{number}",
                    "status": "verified",
                    "verification": {
                        "bibliographic_status": "verified",
                        "retraction_status": "clear",
                    },
                    "canonical": {
                        "title": f"Verified deck source {number}",
                        "journal": "Journal of Deck Tests",
                        "year": 2020 + number,
                        "authors_structured": [
                            {"family": f"Author{number}", "given": "Ada"}
                        ],
                    },
                }
                for number in range(1, count + 1)
            ]
        }

    @staticmethod
    def storyboard():
        roles = ("question", "evidence", "limitations", "conclusion")
        return {
            "title": "A verified test deck",
            "subtitle": "The written review remains the primary deliverable.",
            "style": "scientific",
            "size": "small",
            "reference_keys": [f"Paper{number}" for number in range(1, 11)],
            "slides": [
                {
                    "id": f"slide-{number}",
                    "role": role,
                    "title": f"Verified claim {number} is supported by the evidence.",
                    "image": f"slide-{number}.png",
                    "alt": f"A visual explanation of verified claim {number}.",
                    "citations": [f"Paper{number}", f"Paper{number + 4}"],
                    "evidence": ("mixed" if role == "limitations" else "strong"),
                }
                for number, role in enumerate(roles, 1)
            ],
        }

    @staticmethod
    def make_images(directory, storyboard, size=(1600, 900)):
        from PIL import Image, ImageDraw

        for number, slide in enumerate(storyboard["slides"], 1):
            canvas = Image.new("RGB", size, "white")
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                (80, 210, size[0] - 80, size[1] - 120), outline="#ff4f1f", width=14
            )
            draw.line((150, 480, size[0] - 150, 480), fill="#141414", width=10)
            draw.ellipse(
                (180 + number * 25, 330, 420 + number * 25, 570),
                fill="#b8d5e6",
                outline="#141414",
                width=5,
            )
            canvas.save(os.path.join(directory, slide["image"]))


class StoryboardValidationTests(unittest.TestCase):
    def setUp(self):
        self.storyboard = DeckFixture.storyboard()
        self.ledger = DeckFixture.ledger()

    def test_small_storyboard_normalizes_to_six_total_slides(self):
        document = export_deck.validate_storyboard(self.storyboard, self.ledger)
        self.assertEqual(len(document.slides), 4)
        self.assertEqual(len(document.reference_pages), 1)
        self.assertEqual(document.total_slides, 6)
        self.assertEqual(document.kicker, "Journal club")

    def test_content_slide_without_citations_is_a_hard_failure(self):
        self.storyboard["slides"][1]["citations"] = []
        with self.assertRaisesRegex(
            export_deck.DeckValidationError, "at least 1 string"
        ):
            export_deck.validate_storyboard(self.storyboard, self.ledger)

    def test_unverified_reference_is_a_hard_failure(self):
        self.ledger["entries"][0]["verification"]["retraction_status"] = "unknown"
        with self.assertRaisesRegex(export_deck.DeckValidationError, "not verified"):
            export_deck.validate_storyboard(self.storyboard, self.ledger)

    def test_claim_title_must_be_a_full_sentence(self):
        self.storyboard["slides"][0]["title"] = "A fragment without punctuation"
        with self.assertRaisesRegex(export_deck.DeckValidationError, "full sentence"):
            export_deck.validate_storyboard(self.storyboard, self.ledger)

    def test_scientific_arc_requires_limitations(self):
        self.storyboard["slides"][2]["role"] = "evidence"
        with self.assertRaisesRegex(export_deck.DeckValidationError, "limitations"):
            export_deck.validate_storyboard(self.storyboard, self.ledger)

    def test_each_style_uses_its_declared_storyboard_grammar(self):
        role_sets = {
            "popsci": ("hook", "story", "contrary-evidence", "kicker"),
            "bullets": ("tldr", "point", "point", "point"),
            "eli5": ("idea", "idea", "idea", "idea"),
        }
        for style, roles in role_sets.items():
            with self.subTest(style=style):
                storyboard = DeckFixture.storyboard()
                storyboard["style"] = style
                for slide, role in zip(storyboard["slides"], roles):
                    slide["role"] = role
                document = export_deck.validate_storyboard(storyboard, self.ledger)
                self.assertEqual(document.style, style)

    def test_size_caps_are_enforced(self):
        self.storyboard["slides"] = self.storyboard["slides"][:3]
        with self.assertRaisesRegex(
            export_deck.DeckValidationError, "4--6 content slides"
        ):
            export_deck.validate_storyboard(self.storyboard, self.ledger)

    def test_prose_and_big_aliases_normalize_before_rendering(self):
        storyboard = DeckFixture.storyboard()
        storyboard["style"] = "prose"
        document = export_deck.validate_storyboard(storyboard, self.ledger)
        self.assertEqual(document.style, "scientific")

        storyboard["style"] = "scientific"
        storyboard["size"] = "big"
        base = storyboard["slides"]
        storyboard["slides"] = [
            {
                **base[1],
                "id": f"evidence-{number}",
                "title": f"Evidence claim {number} is supported.",
            }
            for number in range(12)
        ]
        storyboard["slides"] = [base[0], *storyboard["slides"], base[2], base[3]]
        document = export_deck.validate_storyboard(storyboard, self.ledger)
        self.assertEqual(document.size, "large")


class DeckHtmlTests(unittest.TestCase):
    def test_html_is_self_contained_and_uses_real_text_chrome(self):
        storyboard = DeckFixture.storyboard()
        ledger = DeckFixture.ledger()
        with tempfile.TemporaryDirectory() as tmp:
            DeckFixture.make_images(tmp, storyboard)
            first = export_deck.build_html(
                storyboard,
                ledger,
                base_dir=tmp,
                release="v-test",
                repo="example.test/grounded",
                compiled_date="2026-08-26",
            )
            second = export_deck.build_html(
                storyboard,
                ledger,
                base_dir=tmp,
                release="v-test",
                repo="example.test/grounded",
                compiled_date="2026-08-26",
            )
        self.assertEqual(first, second)
        self.assertEqual(first.count('data-slide-kind="content"'), 4)
        self.assertEqual(first.count("data:image/png;base64,"), 10)
        self.assertNotIn('src="slide-1.png"', first)
        self.assertIn("Verified claim 1 is supported by the evidence.", first)
        self.assertIn("https://doi.org/10.1000/deck1", first)
        self.assertIn("evidence-strong", first)
        self.assertIn("1 / 6", first)
        self.assertIn("6 / 6", first)
        self.assertIn("References 1 / 1", first)
        self.assertIn("Agentically generated scientific review</a>", first)
        self.assertIn("grounded v-test</span>", first)
        self.assertNotIn("No floating claims", first)

    def test_non_16_by_9_image_is_rejected(self):
        storyboard = DeckFixture.storyboard()
        ledger = DeckFixture.ledger()
        with tempfile.TemporaryDirectory() as tmp:
            DeckFixture.make_images(tmp, storyboard)
            from PIL import Image

            Image.new("RGB", (1200, 800), "white").save(
                os.path.join(tmp, "slide-1.png")
            )
            with self.assertRaisesRegex(
                export_deck.DeckValidationError, "must be 16:9"
            ):
                export_deck.build_html(storyboard, ledger, base_dir=tmp)

    def test_remote_slide_asset_is_rejected(self):
        storyboard = DeckFixture.storyboard()
        storyboard["slides"][0]["image"] = "https://example.test/slide.png"
        with tempfile.TemporaryDirectory() as tmp:
            DeckFixture.make_images(tmp, DeckFixture.storyboard())
            with self.assertRaisesRegex(ValueError, "remote figure assets"):
                export_deck.build_html(storyboard, DeckFixture.ledger(), base_dir=tmp)


class DeckPdfTests(unittest.TestCase):
    @staticmethod
    def build_pdf(tmp):
        storyboard = DeckFixture.storyboard()
        ledger = DeckFixture.ledger()
        DeckFixture.make_images(tmp, storyboard)
        page = export_deck.build_html(
            storyboard,
            ledger,
            base_dir=tmp,
            release="v-test",
            repo="example.test/grounded",
            compiled_date="2026-08-26",
        )
        first = os.path.join(tmp, "first.pdf")
        second = os.path.join(tmp, "second.pdf")
        result_a = weasyprint_export.write_pdf(page, first)
        result_b = weasyprint_export.write_pdf(page, second)
        return storyboard, ledger, first, second, result_a, result_b

    def test_pdf_build_is_deterministic_and_passes_structural_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            storyboard, ledger, first, second, result_a, result_b = self.build_pdf(tmp)
            with open(first, "rb") as stream:
                first_bytes = stream.read()
            with open(second, "rb") as stream:
                second_bytes = stream.read()
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(result_a["sha256"], result_b["sha256"])
            inspection = qa_deck_pdf.inspect_structure(
                first, storyboard, ledger, expected_release="v-test"
            )
        self.assertEqual(inspection["pages"], 6)
        self.assertEqual(inspection["content_slides"], 4)
        self.assertEqual(inspection["reference_slides"], 1)
        self.assertEqual(inspection["image_counts"][0], 1)
        self.assertTrue(all(count >= 2 for count in inspection["image_counts"][1:5]))
        self.assertEqual(inspection["image_counts"][5], 1)

    def test_structural_qa_rejects_missing_per_slide_doi_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            storyboard, ledger, first, _second, _a, _b = self.build_pdf(tmp)
            empty_links = [set() for _ in range(6)]
            with mock.patch.object(
                qa_deck_pdf, "_page_link_contract", return_value=(empty_links, [])
            ):
                with self.assertRaisesRegex(
                    qa_deck_pdf.DeckPdfQaError, "content slide 2 is missing"
                ):
                    qa_deck_pdf.inspect_structure(first, storyboard, ledger)

    def test_raster_gate_rejects_blank_content_slide(self):
        from PIL import Image

        blank = Image.new("RGB", (1600, 900), "white")
        failures = qa_deck_pdf._raster_page_failures(blank, 2, 6, "content", dpi=120)
        self.assertTrue(any("masthead" in failure for failure in failures))
        self.assertTrue(any("body image" in failure for failure in failures))

    @unittest.skipUnless(shutil.which("pdftoppm"), "Poppler is not installed")
    def test_independent_landscape_raster_qa_checks_every_slide(self):
        with tempfile.TemporaryDirectory() as tmp:
            _storyboard, _ledger, first, _second, _a, _b = self.build_pdf(tmp)
            raster = qa_deck_pdf.render_and_inspect(
                first,
                os.path.join(tmp, "raster"),
                content_slides=4,
                reference_slides=1,
                dpi=120,
            )
        self.assertEqual(raster["rendered_pages"], 6)
        self.assertEqual(raster["page_size_pixels"], [1600, 900])
        self.assertTrue(raster["contact_sheets"])


if __name__ == "__main__":
    unittest.main()
