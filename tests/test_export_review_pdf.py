import os
import json
import re
import shutil
import subprocess
from tests.test_assertion_audit import synthetic_release_args
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "skills", "grounded")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import export_review  # noqa: E402
import grounded_metadata  # noqa: E402
import qa_review_pdf  # noqa: E402
import weasyprint_export  # noqa: E402
from artifact_io import sha256_file  # noqa: E402


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
            self.assertEqual(inspection["release"], "v-test")
            checked = qa_review_pdf.inspect_structure(
                first, self.markdown(), expected_release="v-test"
            )
            self.assertEqual(checked["release"], "v-test")
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "expected v-other"):
                qa_review_pdf.inspect_structure(
                    first, self.markdown(), expected_release="v-other"
                )
            self.assertGreaterEqual(inspection["internal_links"], 1)
            self.assertEqual(inspection["expected_figures"], 1)
            ratio_checked = qa_review_pdf.inspect_structure(
                first, self.markdown(),
                figure_records=[{"pixel_width": 1200, "pixel_height": 700}],
            )
            self.assertTrue(ratio_checked["figure_aspect_checks"])
            self.assertTrue(all(
                item["status"] == "pass"
                for item in ratio_checked["figure_aspect_checks"]
            ))

    def test_pdf_matrix_gate_rejects_anisotropic_figure_placement(self):
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )
            distorted = page.replace(
                "height: auto; max-height: 92mm;\n  object-fit: contain;",
                "height: 60mm; max-height: 60mm;\n  object-fit: fill;",
                1,
            )
            self.assertNotEqual(distorted, page)
            pdf = os.path.join(tmp, "distorted.pdf")
            weasyprint_export.write_pdf(distorted, pdf)
            _checks, failures = qa_review_pdf._verify_pdf_figure_aspects(
                PdfReader(pdf, strict=True),
                [{"pixel_width": 1200, "pixel_height": 700}],
            )
            self.assertTrue(failures)
            self.assertIn("stretches 1200×700px figure", " ".join(failures))

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

    def test_packaged_logo_and_writing_style_are_visible_furniture(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
                style="eli5",
            )

        self.assertIn('<img src="data:image/png;base64,', page)
        self.assertIn("<b>Style</b><span>ELI5</span>", page)
        self.assertIn(
            '<a class="descriptor" href="https://example.test/grounded">'
            "Agentically generated scientific review</a>",
            page,
        )
        self.assertIn(
            '<a class="version" href="https://example.test/grounded">'
            'grounded v-test</a>', page)
        self.assertIn(
            '<b>Made with</b><span><a href="https://example.test/grounded">'
            'Grounded v-test</a></span>',
            page,
        )
        self.assertNotIn('<b>Tokens</b>', page)
        self.assertIn('<aside class="madewith"><b><img class="mark" '
                      'src="data:image/png;base64,', page)
        self.assertIn('Made with Grounded</b>', page)
        self.assertIn(
            '<a href="https://example.test/grounded">'
            'example.test/grounded</a></p></aside>'
            '<h2 class="refhead">References', page)
        self.assertNotIn('<div class="provenance">', page)
        self.assertNotIn("No floating claims", page)
        self.assertNotIn("<svg viewBox=", page)

    def test_default_release_uses_packaged_version(self):
        unrelated_parent_tag = mock.Mock(returncode=0, stdout="v1.0\n")
        with mock.patch.object(
                export_review.subprocess, "run",
                return_value=unrelated_parent_tag):
            page = export_review.build_html(
                "## Review\n\n**Abstract** — Summary.\n\n**Sources**\n",
                release=None,
                repo="example.test/grounded",
                compiled_date="2026-08-26",
            )
        expected = f"v{grounded_metadata.version()}"
        self.assertIn(f'>grounded {expected}</a>', page)
        self.assertNotIn('>grounded v1.0</a>', page)

    def test_prose_style_alias_prints_as_scientific(self):
        page = export_review.build_html(
            "## Review\n\n**Abstract** — Summary.\n\n**Sources**\n",
            release="v-test", repo="example.test/grounded",
            compiled_date="2026-08-26", style="prose",
        )
        self.assertIn("<b>Style</b><span>Scientific</span>", page)

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
                 *synthetic_release_args(tmp),
                 "--release", "v-test", "--compiled-date", "2026-08-26"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(os.path.isfile(pdf))
            self.assertFalse(os.path.exists(os.path.join(tmp, "review.html")))

    def test_release_manifest_invalidates_if_markdown_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            review = os.path.join(tmp, "review.md")
            ledger = os.path.join(tmp, "sources.json")
            spec = os.path.join(tmp, "figure.json")
            prompt = os.path.join(tmp, "figure.prompt.txt")
            pdf = os.path.join(tmp, "review.pdf")
            manifest = os.path.join(tmp, "release-manifest.json")
            with open(review, "w", encoding="utf-8") as stream:
                stream.write(self.markdown())
            with open(ledger, "w", encoding="utf-8") as stream:
                json.dump({"entries": [{
                    "key": "Smith2024", "doi": "10.1000/example",
                    "status": "verified",
                    "verification": {
                        "bibliographic_status": "verified",
                        "retraction_status": "clear",
                    },
                }]}, stream)
            with open(spec, "w", encoding="utf-8") as stream:
                stream.write("{}\n")
            with open(prompt, "w", encoding="utf-8") as stream:
                stream.write("saved prompt\n")
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )
            weasyprint_export.write_pdf(page, pdf)
            export_review.write_release_manifest(
                manifest, review_path=review, ledger_path=ledger, pdf_path=pdf,
                html_document=page, release="v-test", columns=2,
                kicker="Review", colophon=None, repo="example.test/grounded",
                compiled_date="2026-08-26", figure_specs=[spec],
                figure_prompts=[prompt],
            )
            context = qa_review_pdf.verify_release_manifest(manifest, pdf, review)
            self.assertEqual(context["columns"], 2)
            with open(review, "a", encoding="utf-8") as stream:
                stream.write("\nChanged after rendering.\n")
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "review hash changed"):
                qa_review_pdf.verify_release_manifest(manifest, pdf, review)

    @staticmethod
    def claims_audit(verdict="supported"):
        return {
            "review": "review.md", "created": "2026-08-26",
            "claims": [{
                "id": "C001",
                "claim": "The solid steps are observed; the dashed step is inferred.",
                "location": "paragraph 2, sentence 2",
                "dois": ["10.1000/example"], "numbers": [],
                "adjudications": [{
                    "doi": "10.1000/example", "verdict": verdict,
                    "quote": "the dashed step is inferred", "note": "",
                    "tier": "fulltext"}],
            }],
        }

    def test_claim_audit_prints_only_the_tally_in_the_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
                claims_audit=self.claims_audit(),
            )
        self.assertIn("<b>Verification</b><span>Crossref · claims</span>", page)
        self.assertIn(
            "retraction-screened via Crossref<br>1 cited sentence · 1 source check · "
            "1 supported at full text · 0 at abstract · 0 partial · 0 contradicted", page)
        # The per-pair receipts live in their own file, never in the PDF.
        self.assertNotIn("Claim receipts", page.split("</style>")[1])
        self.assertNotIn("the dashed step is inferred”", page)

    def test_chat_receipts_block_is_never_rendered_as_prose(self):
        import claim_receipts
        attached = claim_receipts.attach_receipts(self.markdown(), self.claims_audit())
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            page = export_review.build_html(
                attached, base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
                claims_audit=self.claims_audit(),
            )
            self.assertNotIn("**Receipts**", page)
            self.assertNotIn("verbatim quote is in", page)
            # The Sources annotation survives as reference apparatus.
            self.assertIn("· 1 claim · full text", page)
            with self.assertRaisesRegex(ValueError, "Receipts block"):
                export_review.validate_release_inputs(
                    self._write(tmp, "review.md", attached),
                    self._write(tmp, "sources.json", json.dumps(self.ledger())),
                )

    @staticmethod
    def _write(tmp, name, text):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        return path

    @staticmethod
    def ledger():
        return {"entries": [{
            "key": "Smith2024", "doi": "10.1000/example", "status": "verified",
            "verification": {"bibliographic_status": "verified",
                             "retraction_status": "clear"},
        }]}

    def test_release_refuses_a_contradicted_or_pending_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = self._write(tmp, "review.md", self.markdown())
            ledger = self._write(tmp, "sources.json", json.dumps(self.ledger()))
            for verdict, message in (("contradicted", "contradicted"),
                                     ("pending", "pending")):
                audit = self._write(tmp, "claims_audit.json",
                                    json.dumps(self.claims_audit(verdict)))
                with self.assertRaisesRegex(ValueError, message):
                    export_review.validate_release_inputs(
                        review, ledger, claims_audit=audit)

    def test_release_manifest_binds_the_audit_and_qa_rejects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            from tests.test_assertion_audit import checked_fixture
            self.make_image(os.path.join(tmp, "figure.png"))
            review = self._write(tmp, "review.md", self.markdown())
            ledger = self._write(tmp, "sources.json", json.dumps(self.ledger()))
            spec = self._write(tmp, "figure.json", "{}\n")
            prompt = self._write(tmp, "figure.prompt.txt", "saved prompt\n")
            audit = self._write(tmp, "claims_audit.json",
                                json.dumps(self.claims_audit()))
            review, audit, _store, checked_audit = checked_fixture(tmp, self.markdown())
            receipts = self._write(tmp, "review-receipts.md", "# Claim receipts\n")
            pdf = os.path.join(tmp, "review.pdf")
            manifest = os.path.join(tmp, "release-manifest.json")
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
                claims_audit=checked_audit,
            )
            weasyprint_export.write_pdf(page, pdf)
            export_review.write_release_manifest(
                manifest, review_path=review, ledger_path=ledger, pdf_path=pdf,
                html_document=page, release="v-test", columns=2,
                kicker="Review", colophon=None, repo="example.test/grounded",
                compiled_date="2026-08-26", figure_specs=[spec],
                figure_prompts=[prompt], claims_audit=audit,
                claim_receipts_path=receipts,
            )
            recorded = json.load(open(manifest, encoding="utf-8"))
            self.assertEqual(recorded["inputs"]["claim_receipts"]["path"], "review-receipts.md")
            self.assertEqual(recorded["expected"]["claim_pairs"], 1)
            self.assertEqual(recorded["expected"]["claim_summary"]["supported_fulltext"], 1)
            self.assertEqual(recorded["inputs"]["claims_audit"]["path"], "audit.json")
            context = qa_review_pdf.verify_release_manifest(manifest, pdf, review)
            self.assertEqual(context["claim_summary"]["pairs"], 1)
            qa_review_pdf.inspect_structure(
                pdf, self.markdown(), claim_summary=context["claim_summary"])
            # A PDF rendered without the audit tally cannot pass an audited manifest.
            bare = os.path.join(tmp, "bare", "review.pdf")
            os.mkdir(os.path.dirname(bare))
            weasyprint_export.write_pdf(export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26"), bare)
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "claim-audit line"):
                qa_review_pdf.inspect_structure(
                    bare, self.markdown(), claim_summary=context["claim_summary"])
            # Editing the receipts file after release breaks lineage.
            with open(receipts, "a", encoding="utf-8") as stream:
                stream.write("edited\n")
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "claim_receipts hash changed"):
                qa_review_pdf.verify_release_manifest(manifest, pdf, review)
            with open(receipts, "w", encoding="utf-8") as stream:
                stream.write("# Claim receipts\n")
            # Editing the audit after release breaks lineage.
            with open(audit, "w", encoding="utf-8") as stream:
                json.dump(self.claims_audit("partial"), stream)
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "claims_audit hash changed"):
                qa_review_pdf.verify_release_manifest(manifest, pdf, review)

    def test_quality_contract_manifest_hashes_inspection_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            figure = os.path.join(tmp, "figure.png")
            self.make_image(figure)
            review = os.path.join(tmp, "review.md")
            ledger = os.path.join(tmp, "sources.json")
            spec = os.path.join(tmp, "figure.json")
            prompt = os.path.join(tmp, "figure.prompt.txt")
            inspection = os.path.join(tmp, "figure.inspection.json")
            provenance = os.path.join(tmp, "figure.provenance.json")
            pdf = os.path.join(tmp, "review.pdf")
            manifest = os.path.join(tmp, "release-manifest.json")
            with open(review, "w", encoding="utf-8") as stream:
                stream.write(self.markdown())
            with open(ledger, "w", encoding="utf-8") as stream:
                json.dump({"entries": [{
                    "key": "Smith2024", "doi": "10.1000/example",
                    "status": "verified",
                    "verification": {
                        "bibliographic_status": "verified",
                        "retraction_status": "clear",
                    },
                }]}, stream)
            target_ratio = 1200 / 700
            with open(spec, "w", encoding="utf-8") as stream:
                json.dump({
                    "quality_contract_version": 1,
                    "review_style": "scientific",
                    "render_route": "deterministic",
                    "archetype": "quantitative",
                    "target_aspect_ratio": target_ratio,
                    "title": "Caption only",
                    "render_context": "article",
                    "exact_text": ["Caption only"],
                    "relationships": [],
                    "avoid": [],
                }, stream)
            with open(prompt, "w", encoding="utf-8") as stream:
                stream.write("saved deterministic production brief\n")
            with open(inspection, "w", encoding="utf-8") as stream:
                json.dump({
                    "ocr_text": "",
                    "minimum_label_height_px": 32,
                    "relationships": [],
                    "detected_effects": [],
                    "text_collisions": [],
                    "geometry_distortions": [],
                    "duplicate_text": [],
                    "unlisted_text": [],
                    "visual_quality": {
                        "composition": "pass", "hierarchy": "pass",
                        "domain_specificity": "pass", "style_fit": "pass",
                        "polish": "pass",
                    },
                }, stream)
            with open(provenance, "w", encoding="utf-8") as stream:
                json.dump({
                    "schema_version": 1,
                    "generator_available": True,
                    "generator": {"tool": "built-in-imagegen"},
                    "selected_route": "deterministic",
                    "selected_asset": "figure.png",
                    "selected_sha256": sha256_file(figure),
                    "attempts": [{"kind": "render", "asset": "figure.png"}],
                    "comparison": {
                        "candidates_compared": 1,
                        "selection_rationale": "The exact plot geometry is the evidence.",
                    },
                    "hybrid_considered": False,
                    "fallback_reason": None,
                }, stream)
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )
            weasyprint_export.write_pdf(page, pdf)
            export_review.write_release_manifest(
                manifest, review_path=review, ledger_path=ledger, pdf_path=pdf,
                html_document=page, release="v-test", columns=2,
                kicker="Review", colophon=None, repo="example.test/grounded",
                compiled_date="2026-08-26", figure_specs=[spec],
                figure_prompts=[prompt], figure_inspections=[inspection],
                figure_provenances=[provenance],
            )
            content = json.loads(Path(manifest).read_text(encoding="utf-8"))
            self.assertEqual(len(content["inputs"]["figure_inspections"]), 1)
            self.assertEqual(len(content["inputs"]["figure_provenances"]), 1)
            qa_review_pdf.verify_release_manifest(manifest, pdf, review)
            with open(inspection, "a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(
                    qa_review_pdf.PdfQaError, "figure_inspections.*hash changed"):
                qa_review_pdf.verify_release_manifest(manifest, pdf, review)

    def test_v3_release_requires_inspection_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            figure = os.path.join(tmp, "figure.png")
            self.make_image(figure)
            review = os.path.join(tmp, "review.md")
            ledger = os.path.join(tmp, "sources.json")
            spec = os.path.join(tmp, "figure.json")
            prompt = os.path.join(tmp, "figure.prompt.txt")
            Path(review).write_text(self.markdown(), encoding="utf-8")
            Path(ledger).write_text(json.dumps({"entries": [{
                "key": "Smith2024",
                "doi": "10.1000/example",
                "status": "verified",
                "verification": {
                    "bibliographic_status": "verified",
                    "retraction_status": "clear",
                },
            }]}), encoding="utf-8")
            Path(spec).write_text(
                json.dumps({"quality_contract_version": 3}), encoding="utf-8"
            )
            Path(prompt).write_text("saved prompt\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "quality-contract release requires one --figure-inspection",
            ):
                export_review.validate_release_inputs(
                    review, ledger, [spec], [prompt]
                )

    def test_release_accepts_recorded_correction_as_reference_apparatus(self):
        with tempfile.TemporaryDirectory() as tmp:
            correction = "10.1000/correction"
            review = Path(tmp) / "review.md"
            ledger = Path(tmp) / "sources.json"
            review.write_text(
                "## Question?\n\nA finding "
                "[Smith 2024](https://doi.org/10.1000/example).\n\n"
                "**Sources**\n\n**Smith 2024** A source. "
                "https://doi.org/10.1000/example Correction: "
                f"[{correction}](https://doi.org/{correction}).\n",
                encoding="utf-8",
            )
            entry = {
                "key": "Smith2024",
                "doi": "10.1000/example",
                "status": "verified",
                "verification": {
                    "bibliographic_status": "verified",
                    "retraction_status": "clear",
                    "correction_notices": [{"doi": correction}],
                },
            }
            ledger.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
            _markdown, _figures, expected, by_doi = (
                export_review.validate_release_inputs(review, ledger)
            )
            self.assertEqual(expected, ["10.1000/correction", "10.1000/example"])
            self.assertEqual(set(by_doi), {"10.1000/example"})
            _title, _lead, rendered = export_review.to_html(
                review.read_text(encoding="utf-8")
            )
            self.assertIn(f'https://doi.org/{correction}', rendered)
            self.assertEqual(rendered.count('data-reference-number="1"'), 1)
            self.assertEqual(export_review.count_unique_dois(
                review.read_text(encoding="utf-8")
            ), 1)

            entry["verification"]["correction_notices"] = []
            ledger.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not recorded"):
                export_review.validate_release_inputs(review, ledger)

    def test_visible_references_heading_is_release_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )
            without_heading = re.sub(
                r'<h2 class="refhead">.*?</h2>', "", page, count=1,
                flags=re.S,
            )
            weasyprint_export.write_pdf(without_heading, pdf)
            with self.assertRaisesRegex(qa_review_pdf.PdfQaError, "visible References"):
                qa_review_pdf.inspect_structure(pdf, self.markdown())

    def test_folded_reference_imprint_is_visible_when_pdf_extracts_metadata_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "review.pdf")
            page = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v4.0.0",
                repo="example.test/grounded", compiled_date="2026-08-26",
                imprint="refhead",
            )
            weasyprint_export.write_pdf(page, pdf)
            inspection = qa_review_pdf.inspect_structure(
                pdf, self.markdown(), expected_release="v4.0.0"
            )
            self.assertEqual(inspection["visible_reference_dois"], 1)
            self.assertIsNotNone(inspection["reference_start_page"])

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

    def test_journal_citations_are_linked_superscripts_in_first_use_order(self):
        markdown = (
            "## Citation review\n\n**Abstract** — A short summary.\n\n"
            "The first claim cites beta "
            "[Beta 2024](https://doi.org/10.1000/beta). "
            "The next claim is complete. "
            "[Alpha 2023](https://doi.org/10.1000/alpha) "
            "Beta remains relevant "
            "[Beta 2024](https://doi.org/10.1000/beta).\n\n"
            "**Sources**\n\n"
            "**Alpha A (2023)** Alpha source. *Journal*. "
            "https://doi.org/10.1000/alpha\n\n"
            "**Beta B (2024)** Beta source. *Journal*. "
            "https://doi.org/10.1000/beta\n"
        )

        _title, _lead, body = export_review.to_html(markdown)

        beta = (
            '<sup class="citation" aria-label="References 1">'
            '<a href="https://doi.org/10.1000/beta" '
            'role="doc-biblioref">1</a></sup>'
        )
        alpha = (
            '<sup class="citation" aria-label="References 2">'
            '<a href="https://doi.org/10.1000/alpha" '
            'role="doc-biblioref">2</a></sup>'
        )
        self.assertIn("first claim cites beta." + beta, body)
        self.assertIn("next claim is complete." + alpha + " Beta", body)
        self.assertEqual(body.count(beta), 2)
        self.assertLess(
            body.index('data-reference-number="1"'),
            body.index('data-reference-number="2"'),
        )
        self.assertLess(body.index("Beta source"), body.index("Alpha source"))

    def test_journal_rejects_citations_that_open_a_sentence(self):
        bodies = (
            "[Smith 2024](https://doi.org/10.1000/example) reported a result.",
            "Earlier evidence differed. "
            "[Smith 2024](https://doi.org/10.1000/example) reported a result.",
        )
        for body in bodies:
            with self.subTest(body=body):
                markdown = (
                    "## Invalid citation review\n\n**Abstract** — Summary.\n\n"
                    + body
                    + "\n\n**Sources**\n\n"
                    "**Smith S (2024)** Source. *Journal*. "
                    "https://doi.org/10.1000/example\n"
                )
                with self.assertRaisesRegex(
                        ValueError, "journal citation starts a sentence"):
                    export_review.to_html(markdown)

    def test_journal_allows_a_citation_only_table_cell(self):
        markdown = (
            "## Table citation review\n\n**Abstract** — Summary.\n\n"
            "| Finding | Source |\n|---|---|\n"
            "| A supported result | "
            "[Smith 2024](https://doi.org/10.1000/example) |\n\n"
            "**Sources**\n\n"
            "**Smith S (2024)** Source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        _title, _lead, body = export_review.to_html(markdown)
        self.assertIn('<td><sup class="citation"', body)

    def test_sources_must_be_the_terminal_review_section(self):
        markdown = (
            "## Invalid review\n\n**Abstract** — A short summary.\n\n"
            "**Sources**\n\n**Smith 2024** A source. *Journal*. "
            "https://doi.org/10.1000/example\n\n"
            "### This section is misplaced\n\nMore discussion.\n"
        )
        with self.assertRaisesRegex(ValueError, "terminal review section"):
            export_review.to_html(markdown)

    def test_balanced_short_references_have_a_rendered_text_cap(self):
        short_entries = "\n\n".join(
            f"**Author {number} (2024)** A concise source. *Journal*. "
            f"https://doi.org/10.1000/example{number}"
            for number in range(2)
        )
        short = (
            "## Review\n\n**Abstract** — A short summary.\n\n"
            f"**Sources**\n\n{short_entries}\n"
        )
        _, _, short_body = export_review.to_html(short)
        self.assertIn('class="spanning-reference-balanced"', short_body)

        long_entries = "\n\n".join(
            f"**Author {number} (2024)** " + ("Extended source text. " * 120) +
            f"*Journal*. https://doi.org/10.1000/long{number}"
            for number in range(2)
        )
        long = (
            "## Review\n\n**Abstract** — A short summary.\n\n"
            f"**Sources**\n\n{long_entries}\n"
        )
        _, _, long_body = export_review.to_html(long)
        self.assertNotIn('class="spanning-reference-balanced"', long_body)

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

    def test_short_columns_do_not_strand_space_before_a_full_width_figure(self):
        from pypdf import PdfReader

        items = "\n".join(
            f"- Evidence item {number} explains a distinct observed mechanism "
            "with enough detail to exercise balanced column layout."
            for number in range(1, 7))
        markdown = (
            "## Compact display review\n\n**Abstract** — A short summary.\n\n"
            "### Evidence before the display\n\n" + items + "\n\n"
            "The pathway is summarized in [Figure 1](#fig-mechanism).\n\n"
            '<a id="fig-mechanism"></a>\n'
            "![A three-stage mechanism](figure.png)\n\n"
            "**Figure 1. SAME_PAGE_FIGURE.** The observed stages are shown. "
            "[Smith 2024](https://doi.org/10.1000/example)\n\n"
            "**Sources**\n\n**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            pdf = os.path.join(tmp, "same-page.pdf")
            self.write_review(markdown, pdf, tmp)
            pages = [page.extract_text() or "" for page in PdfReader(pdf).pages]

        self.assertIn("Evidence item 1", pages[0])
        self.assertIn("Evidence item 6", pages[0])
        self.assertIn("SAME_PAGE_FIGURE", pages[0])

    def test_explicit_column_runs_never_nest_in_an_outer_multicolumn_body(self):
        markdown = self.markdown().replace(
            "**Figure 1. A transient signal builds memory.** "
            "The solid steps are observed; the dashed step is inferred. "
            "[Smith 2024](https://doi.org/10.1000/example)",
            "**Figure 1. A transient signal builds memory.**\n"
            "- **Shows:** The solid steps are observed; the dashed step is inferred. "
            "[Smith 2024](https://doi.org/10.1000/example)",
        )
        with tempfile.TemporaryDirectory() as tmp:
            self.make_image(os.path.join(tmp, "figure.png"))
            page = export_review.build_html(
                markdown, base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )

        self.assertIn('<div class="column-run final">', page)
        self.assertIn('<div class="body structured-flow">', page)
        self.assertNotIn('<div class="body cols">', page)

    def test_eli5_showcase_exports_as_flowing_prose_not_bullets(self):
        example_dir = os.path.join(REPO, "tests", "fixtures", "showcase")
        source = os.path.join(example_dir, "eli5-why-clouds-are-white.md")
        with open(source, encoding="utf-8") as stream:
            markdown = stream.read()

        page = export_review.build_html(
            markdown,
            base_dir=example_dir,
            release="v-test",
            repo="example.test/grounded",
            compiled_date="2026-08-26",
        )

        self.assertNotRegex(markdown, r"(?m)^[-*]\s+")
        self.assertNotIn("<ul>", page)
        self.assertRegex(
            page,
            r"<p>An ordinary warm cloud is (?:made of|a crowd of) tiny clear water drops\.",
        )
        self.assertIn("<div class=\"body cols\">", page)

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
    def test_running_masthead_paints_on_a_real_continuation_page(self):
        from pypdf import PdfReader

        example_dir = os.path.join(REPO, "tests", "fixtures", "showcase")
        with tempfile.TemporaryDirectory() as tmp:
            for filename in (
                    "prose-small-blue-light-sleep.md",
                    "eli5-why-clouds-are-white.md"):
                with self.subTest(filename=filename):
                    source = os.path.join(example_dir, filename)
                    with open(source, encoding="utf-8") as stream:
                        markdown = stream.read()
                    pdf = os.path.join(tmp, filename.replace(".md", ".pdf"))
                    render_dir = os.path.join(tmp, filename.replace(".md", ""))
                    # Render through the ladder, exactly as the CLI runs it.
                    export_review.render_pdf_rebalanced(
                        markdown, pdf, base_dir=example_dir,
                        release="v-test", compiled_date="2026-08-26")
                    self.assertEqual(len(PdfReader(pdf).pages), 2)
                    raster = qa_review_pdf.render_and_inspect(
                        pdf, render_dir, dpi=120)
                    # The raster QA independently checks masthead and orange-chip
                    # ink on page 2, not merely extractable header text.
                    self.assertEqual(raster["rendered_pages"], 2)

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
            ("prose-large-mediterranean-diet.md", 10),
        )
        example_dir = os.path.join(REPO, "tests", "fixtures", "showcase")
        with tempfile.TemporaryDirectory() as tmp:
            for filename, expected_pages in examples:
                source = os.path.join(example_dir, filename)
                with open(source, encoding="utf-8") as stream:
                    markdown = stream.read()
                output = os.path.join(tmp, filename.replace(".md", ".pdf"))
                # The canonical render path includes the spill-rebalance
                # ladder (leading, imprint fold), exactly as the CLI runs it.
                export_review.render_pdf_rebalanced(
                    markdown, output, base_dir=example_dir, release="v2.0.0",
                    compiled_date="2026-08-26",
                )
                reader = PdfReader(output)
                self.assertEqual(len(reader.pages), expected_pages)
                inspection = qa_review_pdf.inspect_structure(output, markdown)
                self.assertEqual(
                    inspection["expected_dois"],
                    len(qa_review_pdf._doi_urls(markdown)),
                )
                self.assertEqual(
                    inspection["expected_figures"],
                    markdown.count('<a id="fig-'),
                )
                for number, pdf_page in enumerate(reader.pages, 1):
                    text = pdf_page.extract_text() or ""
                    self.assertIn("G R O U N D E D", text)
                    self.assertIn("AGENTICALLY GENERATED SCIENTIFIC REVIEW", text)
                    self.assertIn(f"{number} / {expected_pages}", text)

    def test_structured_table_uses_space_below_figure_three_safely(self):
        from pypdf import PdfReader

        example_dir = os.path.join(REPO, "tests", "fixtures", "showcase")
        source = os.path.join(example_dir, "large-mediterranean-diet.md")
        with open(source, encoding="utf-8") as stream:
            markdown = stream.read()
        with tempfile.TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "mediterranean.pdf")
            self.write_review(markdown, output, example_dir)
            pages = [page.extract_text() or "" for page in PdfReader(output).pages]

        self.assertEqual(len(pages), 10)
        self.assertIn("Figure 3.", pages[5])
        self.assertIn("The evidence supports a hierarchy of claims", pages[5])
        self.assertIn("OUTCOME", pages[5])
        # The continued table repeats its semantic header instead of stranding
        # a heading or splitting a row at the page boundary.
        self.assertIn("OUTCOME", pages[6])


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

    def test_page_flow_mode_is_propagated_explicitly(self):
        structured_caption = (
            "**Figure 1. A plain-language mechanism.**\n"
            "- **Shows:** Three steps.\n"
            "- **Evidence boundary:** The dashed step is uncertain.\n"
            "- **Sources:** [Smith 2024](https://doi.org/10.1000/example)"
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "figure.png"), "wb") as stream:
                stream.write(b"png")
            structured = export_review.build_html(
                self.markdown(caption=structured_caption), base_dir=tmp,
                release="v-test", repo="example.test/grounded",
                compiled_date="2026-08-26",
            )
            plain = export_review.build_html(
                self.markdown(), base_dir=tmp, release="v-test",
                repo="example.test/grounded", compiled_date="2026-08-26",
            )
        self.assertIn('<div class="body structured-flow">', structured)
        self.assertNotIn('<div class="body cols">', structured)
        self.assertIn('<div class="body cols">', plain)
        self.assertNotIn('<div class="body structured-flow">', plain)

    def test_raster_layout_gate_catches_sparse_pages_and_column_imbalance(self):
        from PIL import Image, ImageDraw

        sparse = Image.new("RGB", (1000, 1400), "white")
        draw = ImageDraw.Draw(sparse)
        for y in range(150, 950, 12):
            draw.line((70, y, 930, y), fill="black", width=2)
        sparse_metrics = qa_review_pdf._page_layout_metrics(sparse)
        sparse_failures = qa_review_pdf._layout_failures(sparse_metrics, 2, 4)
        self.assertTrue(any("under-filled" in failure for failure in sparse_failures))

        unbalanced = Image.new("RGB", (1000, 1400), "white")
        draw = ImageDraw.Draw(unbalanced)
        for y in range(150, 1280, 5):
            draw.line((70, y, 465, y), fill="black", width=3)
        for y in range(150, 620, 5):
            draw.line((535, y, 930, y), fill="black", width=3)
        unbalanced_metrics = qa_review_pdf._page_layout_metrics(unbalanced)
        unbalanced_failures = qa_review_pdf._layout_failures(
            unbalanced_metrics, 4, 4
        )
        self.assertTrue(
            any("unbalanced column" in failure for failure in unbalanced_failures)
        )

        balanced = Image.new("RGB", (1000, 1400), "white")
        draw = ImageDraw.Draw(balanced)
        for y in range(150, 900, 10):
            draw.line((70, y, 465, y), fill="black", width=2)
            draw.line((535, y, 930, y), fill="black", width=2)
        self.assertEqual(
            qa_review_pdf._layout_failures(
                qa_review_pdf._page_layout_metrics(balanced), 4, 4
            ),
            [],
        )

        empty_column = Image.new("RGB", (1000, 1400), "white")
        draw = ImageDraw.Draw(empty_column)
        for y in range(150, 700, 8):
            draw.line((70, y, 465, y), fill="black", width=2)
        final_failures = qa_review_pdf._layout_failures(
            qa_review_pdf._page_layout_metrics(empty_column), 4, 4,
            reference_page=True, columns=2,
        )
        self.assertTrue(any("empty column" in failure for failure in final_failures))

    def test_release_input_errors_surface_as_messages_not_crashes(self):
        """Regression: a branch-local `import json` in main() once shadowed the
        module import, so every release-lineage validation error crashed with
        UnboundLocalError instead of printing its message."""
        with tempfile.TemporaryDirectory() as tmp:
            review = os.path.join(tmp, "review.md")
            with open(review, "w", encoding="utf-8") as stream:
                stream.write(PdfExportTests.markdown())
            PdfExportTests.make_image(os.path.join(tmp, "figure.png"))
            ledger = os.path.join(tmp, "sources.json")
            with open(ledger, "w", encoding="utf-8") as stream:
                json.dump({"entries": []}, stream)
            completed = subprocess.run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS, "export_review.py"),
                    "--in", review,
                    "--out", os.path.join(tmp, "review.pdf"),
                    "--pdf",
                    "--ledger", ledger,
                    "--release-manifest", os.path.join(tmp, "release.json"),
                ],
                capture_output=True, text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertNotIn("UnboundLocalError", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertIn("figure-spec", completed.stderr)

    def test_bounded_leading_knob_and_its_envelope(self):
        page_default = export_review._stylesheet(92)
        page_tight = export_review._stylesheet(92, ref_leading=1.1)
        self.assertIn("line-height: 1.2;", page_default)
        self.assertIn("line-height: 1.1;", page_tight)
        with self.assertRaises(ValueError):
            export_review._stylesheet(92, ref_leading=1.0)
        with self.assertRaises(ValueError):
            export_review._stylesheet(92, ref_leading=1.5)

    def test_terminal_spill_is_detected_and_auto_rebalanced(self):
        """End to end: a review whose reference tail spills onto a final
        page alone is re-rendered once with tightened (bounded) reference
        leading, pulling the spill back; type size is untouched."""
        fixture = os.path.join(REPO, "tests", "fixtures", "spill-probe.md")
        with open(fixture, encoding="utf-8") as stream:
            markdown = stream.read()
        # Keep this synthetic probe at the bounded spill threshold even when
        # masthead metadata changes without consuming additional row height.
        markdown = markdown.replace(
            "\n**Sources**\n",
            "\nAdditional calibration text keeps this synthetic layout probe "
            "near a page boundary without changing production content.\n\n"
            "**Sources**\n",
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            plain = os.path.join(tmp, "plain.pdf")
            page = export_review.build_html(
                markdown, release="v-test", repo="example.test/g",
                compiled_date="2026-08-27",
            )
            weasyprint_export.write_pdf(page, plain)
            n_refs = export_review.count_unique_dois(markdown)
            spill = export_review.count_terminal_reference_spill(plain, n_refs)
            self.assertGreater(spill, 0)
            self.assertLessEqual(spill, export_review.REBALANCE_MAX_SPILL)

            src = os.path.join(tmp, "review.md")
            with open(src, "w", encoding="utf-8") as stream:
                stream.write(markdown)
            out = os.path.join(tmp, "review.pdf")
            completed = subprocess.run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS, "export_review.py"),
                    "--in", src, "--out", out, "--pdf",
                    *synthetic_release_args(tmp),
                    "--release", "v-test", "--repo", "example.test/g",
                    "--compiled-date", "2026-08-27",
                ],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Rebalanced", completed.stderr)
            self.assertEqual(
                export_review.count_terminal_reference_spill(out, n_refs), 0
            )

    def test_made_with_band_is_style_keyed_and_compactable(self):
        """The band speaks each style's register, and its compact rebalance
        form keeps the link rather than dropping the band."""
        markdown = (
            "## Test review\n\n**TL;DR** \u2014 Test.\n\n"
            "A claim with a source. [Smith 2024](https://doi.org/10.1000/example)\n\n"
            "**Sources**\n\n"
            "**Smith 2024** A verified source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        openings = {
            "scientific": "You can run this protocol yourself.",
            "popsci": "You can point this at whatever you are curious about.",
            "eli5": "You can make one of these too.",
        }
        for style, opening in openings.items():
            with self.subTest(style=style):
                page = export_review.build_html(
                    markdown, style=style, release="v-test",
                    repo="example.test/g", compiled_date="2026-08-27")
                self.assertIn(opening, page)
        bullets = export_review.build_html(
            markdown, style="bullets", release="v-test",
            repo="example.test/g", compiled_date="2026-08-27")
        self.assertIn('Made with Grounded</b><ul>', bullets)
        self.assertIn('<aside class="madewith"><b><img class="mark" ', bullets)

        compact = export_review.build_html(
            markdown, made_with="compact", release="v-test",
            repo="example.test/g", compiled_date="2026-08-27")
        self.assertIn('<aside class="madewith compact">', compact)
        self.assertIn('<a href="https://example.test/g">example.test/g</a>',
                      compact)
        self.assertNotIn("You can run this protocol yourself.", compact)

    def test_no_spill_render_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            PdfExportTests.make_image(os.path.join(tmp, "figure.png"))
            src = os.path.join(tmp, "review.md")
            with open(src, "w", encoding="utf-8") as stream:
                stream.write(PdfExportTests.markdown())
            out = os.path.join(tmp, "review.pdf")
            completed = subprocess.run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS, "export_review.py"),
                    "--in", src, "--out", out, "--pdf",
                    *synthetic_release_args(tmp),
                    "--release", "v-test", "--repo", "example.test/g",
                    "--compiled-date", "2026-08-27",
                ],
                capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("Rebalanced", completed.stderr)


class SalonEditionTests(unittest.TestCase):
    """The salon edition (popsci default): literary typography and the
    classical devices over the same semantic document, with the evidence
    contract untouched (references/contracts.md)."""

    FIXTURE = os.path.join(REPO, "tests", "fixtures", "colic")

    def build(self, **kwargs):
        with open(os.path.join(self.FIXTURE, "review.md"), encoding="utf-8") as stream:
            markdown = stream.read()
        return export_review.build_html(
            markdown, base_dir=self.FIXTURE, style="popsci",
            release="v-test", repo="example.test/grounded",
            compiled_date="2026-08-28", **kwargs,
        )

    def test_popsci_defaults_to_salon_with_devices(self):
        page = self.build()
        self.assertIn("SALON edition", page)
        self.assertIn('<span class="dropcap">S</span>', page)
        self.assertEqual(export_review.resolve_edition("popsci"), "salon")
        self.assertEqual(export_review.resolve_edition("scientific"), "journal")

    def test_journal_override_carries_no_salon_devices(self):
        page = self.build(edition="journal")
        self.assertNotIn("SALON edition", page)
        self.assertNotIn("dropcap", page)

    def test_drop_cap_guards_skip_short_and_quote_openers(self):
        short = (
            "## T\n\n*Standfirst one. Standfirst two.*\n\n"
            "Colic ends by month four "
            f"[Smith 2024](https://doi.org/{'10.1000/example'}).\n\n"
            "**Sources**\n\n**Smith (2024)** A source. *Journal*. "
            "https://doi.org/10.1000/example\n"
        )
        page = export_review.build_html(
            short, style="popsci", release="v-test",
            repo="example.test/grounded", compiled_date="2026-08-28",
        )
        self.assertNotIn('class="dropcap"', page)
        quoted = short.replace(
            "Colic ends by month four",
            '"Colic" ends by month four ' + " ".join(["colic"] * 220),
        )
        page = export_review.build_html(
            quoted, style="popsci", release="v-test",
            repo="example.test/grounded", compiled_date="2026-08-28",
        )
        self.assertNotIn('class="dropcap"', page)

    def test_pull_quote_is_verbatim_placed_and_attributed(self):
        cited = self.build(
            pull_quote="benefit in breastfed infants, none in formula-fed"
        )
        self.assertIn('<aside class="pullquote">', cited)
        match = re.search(r'<span class="pullref">.*?</span>', cited)
        self.assertIsNotNone(match)
        self.assertIn("Sung et al. 2018", match.group(0))
        self.assertIn("doi.org/10.1542/peds.2017-1811", match.group(0))

    def test_authorial_pull_quote_gets_no_attribution(self):
        page = self.build(
            pull_quote='"Self-limiting" is cold comfort at 3 a.m.'
        )
        self.assertIn('<aside class="pullquote">', page)
        self.assertNotIn('<span class="pullref">', page)

    def test_invented_pull_quote_is_a_hard_error(self):
        with self.assertRaises(ValueError):
            self.build(pull_quote="This sentence appears nowhere.")

    def test_pull_quote_requires_salon(self):
        with self.assertRaises(ValueError):
            self.build(edition="journal", pull_quote="colic ends")

    def test_editions_registry_shape(self):
        for name, profile in export_review.EDITIONS.items():
            self.assertIn("css", profile)
            self.assertTrue(profile["fonts"], name)
        self.assertEqual(
            export_review.EDITIONS["journal"]["fonts"],
            ("Charter", "Helvetica-Neue"),
        )


class PrimerEditionTests(unittest.TestCase):
    """The primer edition (eli5 default): friendly explainer typography —
    step badges, answer card — over the same semantic document and evidence
    contract, in the canonical two-column measure."""

    FIXTURE = os.path.join(REPO, "tests", "fixtures", "colic-eli5")
    EVIDENCE = os.path.join(REPO, "tests", "fixtures", "colic")

    def build(self, **kwargs):
        with open(os.path.join(self.FIXTURE, "review.md"), encoding="utf-8") as stream:
            markdown = stream.read()
        return export_review.build_html(
            markdown, base_dir=self.EVIDENCE, style="eli5",
            release="v-test", repo="example.test/grounded",
            compiled_date="2026-08-28", **kwargs,
        )

    def test_eli5_defaults_to_primer(self):
        page = self.build()
        self.assertIn("PRIMER edition", page)
        self.assertEqual(export_review.resolve_edition("eli5"), "primer")
        self.assertEqual(export_review.resolve_edition("bullets"), "brief")

    def test_journal_override_is_clean(self):
        page = self.build(edition="journal")
        self.assertNotIn("PRIMER edition", page)

    def test_primer_carries_no_literary_devices(self):
        page = self.build()
        self.assertNotIn('class="dropcap"', page)
        with self.assertRaises(ValueError):
            self.build(pull_quote="Every baby cries")

    def test_primer_font_contract(self):
        self.assertEqual(
            export_review.EDITIONS["primer"]["fonts"],
            ("Seravek", "Helvetica-Neue"),
        )

    def test_primer_keeps_the_two_column_measure(self):
        """The explainer reads in two columns like every other edition: a
        phone can zoom one column to full width."""
        self.assertNotIn("column-count", export_review.PRIMER_CSS)
        self.assertIn(".body.cols, .column-run", export_review.PRIMER_CSS)

    def test_primer_uses_explicit_column_runs(self):
        """Primer's body type leaves little slack around a spanning display,
        and WeasyPrint drops the rest of the document when it has to fragment
        a column-span box. Explicit sibling runs express the same layout
        without asking it to."""
        self.assertEqual(
            export_review.EDITIONS["primer"].get("column_runs"), "explicit")
        page = self.build()
        self.assertIn('class="body structured-flow"', page)

    def test_primer_bounds_the_compact_pair_below_the_journal_budget(self):
        """The pair cannot fragment, so primer's taller opening furniture and
        larger type need a lower budget: an over-long pair is pushed whole to
        the next page and strands the one it left."""
        budget = export_review.EDITIONS["primer"]["compact_pair_max_chars"]
        self.assertLess(budget, export_review.COMPACT_PAIR_MAX_CHARS)

    def test_primer_keeps_every_reference_in_the_pdf(self):
        """Regression: the two-column primer once rendered one page and
        silently dropped the figure and the whole reference list."""
        page = self.build()
        self.assertEqual(page.count('class="refno"'), 19)


class BriefEditionTests(unittest.TestCase):
    """The brief edition (bullets default): condensed two-column brief with
    the drawn double-chevron marker; evidence contract untouched."""

    FIXTURE = os.path.join(REPO, "tests", "fixtures", "colic-bullets")
    EVIDENCE = os.path.join(REPO, "tests", "fixtures", "colic")

    def build(self, **kwargs):
        with open(os.path.join(self.FIXTURE, "review.md"), encoding="utf-8") as stream:
            markdown = stream.read()
        return export_review.build_html(
            markdown, base_dir=self.EVIDENCE, style="bullets",
            release="v-test", repo="example.test/grounded",
            compiled_date="2026-08-28", **kwargs,
        )

    def test_bullets_defaults_to_brief(self):
        page = self.build()
        self.assertIn("BRIEF edition", page)
        self.assertEqual(export_review.resolve_edition("bullets"), "brief")

    def test_journal_override_is_clean(self):
        page = self.build(edition="journal")
        self.assertNotIn("BRIEF edition", page)

    def test_brief_carries_no_literary_devices(self):
        page = self.build()
        self.assertNotIn('class="dropcap"', page)
        with self.assertRaises(ValueError):
            self.build(pull_quote="Colic is common")

    def test_brief_font_contract_matches_journal(self):
        self.assertEqual(
            export_review.EDITIONS["brief"]["fonts"],
            ("Charter", "Helvetica-Neue"),
        )


if __name__ == "__main__":
    unittest.main()
