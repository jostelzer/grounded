import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_review  # noqa: E402


DOI = "10.1000/example"


def scientific_review(abstract_words=120):
    abstract = " ".join(["answer"] * abstract_words)
    return (
        "## Does the test pass?\n\n"
        f"**Abstract** — {abstract}\n\n"
        "### Introduction\n\n"
        f"The question has evidence [Smith 2024](https://doi.org/{DOI}).\n\n"
        "### Result\n\nThe evidence remains conditional.\n\n"
        "### Conclusion\n\nThe answer depends on context.\n\n"
        "**Sources**\n\n"
        f"**Smith (2024)** A source. *Journal*. https://doi.org/{DOI}\n"
    )


def strict_large_bullets(target_filler_words):
    dois = [f"10.1000/source{index}" for index in range(70)]
    sections = []
    per_section = target_filler_words // 10
    for section in range(10):
        citations = ", ".join(
            f"[Source {index}](https://doi.org/{dois[index]})"
            for index in range(section * 7, section * 7 + 7)
        )
        sections.append(
            f"### Finding {section + 1}\n\n- "
            + " ".join(["evidence"] * per_section)
            + f" {citations}."
        )
    tables = (
        "\n\n| Study | Result |\n|---|---|\n| A | B |\n\n"
        "| Boundary | Meaning |\n|---|---|\n| C | D |\n"
    )
    sources = "\n".join(
        f"**Source {index} (2024)** A study. https://doi.org/{doi}"
        for index, doi in enumerate(dois)
    )
    return (
        "## What does the large evidence base show?\n\n"
        "**TL;DR** — The evidence supports a conditional answer.\n\n"
        + "\n\n".join(sections) + tables + "\n**Sources**\n\n" + sources + "\n"
    )


class ValidateReviewTests(unittest.TestCase):
    def test_four_showcase_examples_pass(self):
        # seed-oils.md returns here once regenerated under the four-move
        # 120-180-word Abstract contract.
        examples = (
            ("ozempic-after-stopping.md", "popsci", "medium"),
            ("microplastics-health-eli5.md", "eli5", "small"),
        )
        for filename, style, size in examples:
            with self.subTest(filename=filename):
                path = ROOT / "examples" / filename
                result = validate_review.validate_review(
                    path.read_text(encoding="utf-8"),
                    style=style,
                    size=size,
                    # figure assets ship embedded in the example PDFs, not as
                    # repo files, so the asset-existence check stays off
                    base_dir=None,
                )
                self.assertTrue(result.ok, result.errors)

    def test_scientific_abstract_bounds_are_hard_failures(self):
        for count in (119, 181):
            with self.subTest(count=count):
                result = validate_review.validate_review(
                    scientific_review(count), style="scientific", size="small"
                )
                self.assertFalse(result.ok)
                self.assertTrue(
                    any("required 120–180" in error for error in result.errors)
                )

    def test_sources_must_be_unique_terminal_and_match_body_dois(self):
        markdown = scientific_review().replace(
            f"https://doi.org/{DOI}\n",
            "https://doi.org/10.1000/different\n",
            1,
        )
        result = validate_review.validate_review(
            markdown, style="scientific", size="small"
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("missing from Sources" in error for error in result.errors))
        self.assertTrue(any("uncited DOI" in error for error in result.errors))

    def test_unresolved_citation_key_fails(self):
        result = validate_review.validate_review(
            scientific_review().replace("The question", "The question [@Smith2024]"),
            style="scientific",
            size="small",
        )
        self.assertIn(
            "unresolved citation key remains in the finished review", result.errors
        )

    def test_chat_citations_follow_claims_and_precede_terminal_punctuation(self):
        correct = validate_review.validate_review(
            scientific_review(), style="scientific", size="small"
        )
        self.assertFalse(
            any("chat citation" in error for error in correct.errors),
            correct.errors,
        )

        after_period = scientific_review().replace(
            f"evidence [Smith 2024](https://doi.org/{DOI}).",
            f"evidence. [Smith 2024](https://doi.org/{DOI})",
        )
        result = validate_review.validate_review(
            after_period, style="scientific", size="small"
        )
        self.assertTrue(any(
            "chat citation follows sentence-ending punctuation" in error
            for error in result.errors
        ))

        sentence_initial = scientific_review().replace(
            f"The question has evidence [Smith 2024](https://doi.org/{DOI}).",
            f"[Smith 2024](https://doi.org/{DOI}) reports evidence.",
        )
        result = validate_review.validate_review(
            sentence_initial, style="scientific", size="small"
        )
        self.assertTrue(any(
            "chat citation starts a sentence or block" in error
            for error in result.errors
        ))

        citation_cell = (
            "| Finding | Source |\n|---|---|\n"
            f"| Supported | [Smith 2024](https://doi.org/{DOI}) |"
        )
        self.assertEqual(
            validate_review._chat_citation_placement_errors(citation_cell), []
        )

    def test_popsci_standfirst_is_immediately_after_headline_and_uncited(self):
        markdown = (
            "## A headline\n\nPreamble.\n\n*An italic aside.*\n\n"
            "### One\n\nText.\n\n### Two\n\nText.\n\n### Three\n\n"
            f"Evidence [Smith 2024](https://doi.org/{DOI}).\n\n"
            f"**Sources**\n\n**Smith** Source. https://doi.org/{DOI}\n"
        )
        result = validate_review.validate_review(markdown, style="popsci", size="small")
        self.assertIn(
            "popsci style requires an italic standfirst after the headline",
            result.errors,
        )

    def test_bullet_sections_require_bullets(self):
        markdown = (
            "## Question?\n\n**TL;DR** — Answer.\n\n"
            "### A punchline\n\n"
            f"Plain paragraph [Smith 2024](https://doi.org/{DOI}).\n\n"
            f"**Sources**\n\n**Smith** Source. https://doi.org/{DOI}\n"
        )
        result = validate_review.validate_review(
            markdown, style="bullets", size="small"
        )
        self.assertTrue(any("has no bullet body" in error for error in result.errors))

    def test_eli5_requires_flowing_paragraphs_and_rejects_bullet_bodies(self):
        markdown = (
            "## Why does this happen?\n\n**TL;DR** — Here is the short answer.\n\n"
            "### The first part is simple\n\n"
            f"- A listed fact [Smith 2024](https://doi.org/{DOI}).\n\n"
            f"**Sources**\n\n**Smith** Source. https://doi.org/{DOI}\n"
        )
        result = validate_review.validate_review(markdown, style="eli5", size="small")
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "must use flowing paragraphs, not lists" in error
                for error in result.errors
            )
        )

        prose = markdown.replace(
            f"- A listed fact [Smith 2024](https://doi.org/{DOI}).",
            f"This fact is part of one explanation [Smith 2024](https://doi.org/{DOI}). "
            "It leads naturally to the next idea.",
        )
        result = validate_review.validate_review(prose, style="eli5", size="small")
        self.assertTrue(result.ok, result.errors)

    def test_figures_require_equal_parts_reference_and_local_asset(self):
        markdown = scientific_review() + (
            '\n<a id="fig-example"></a>\n![Alt](missing.png)\n\n'
            "**Figure 2. Wrong number.** Caption.\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_review.validate_review(
                markdown, style="scientific", size="small", base_dir=Path(tmp)
            )
        self.assertFalse(result.ok)
        self.assertTrue(any("consecutively" in error for error in result.errors))
        self.assertTrue(any("unreferenced" in error for error in result.errors))
        self.assertTrue(any("does not exist" in error for error in result.errors))

    def test_cli_emits_json_and_nonzero_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.md"
            path.write_text(scientific_review(119), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_review.py"),
                    str(path),
                    "--style",
                    "scientific",
                    "--size",
                    "small",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)["status"], "fail")

    def test_cli_can_validate_stdin_and_pass_the_review_through(self):
        markdown = scientific_review()
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_review.py"),
                "-",
                "--style",
                "scientific",
                "--size",
                "small",
                "--pass-through",
            ],
            input=markdown,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, markdown)
        self.assertEqual(json.loads(completed.stderr)["status"], "pass")

    def test_strict_large_tier_hard_fails_short_body_and_passes_complete_body(self):
        manifest = {
            "records": [
                {"ledger_key": f"Key{index}", "status": "valid_fulltext", "counted": True}
                for index in range(25)
            ]
        }
        short = strict_large_bullets(1050)
        short_result = validate_review.validate_review(
            short, style="bullets", size="large", strict_tier=True,
            fulltext_manifest=manifest,
        )
        self.assertFalse(short_result.ok)
        self.assertTrue(any("body is" in error for error in short_result.errors))

        complete = strict_large_bullets(2100)
        complete_result = validate_review.validate_review(
            complete, style="bullets", size="large", strict_tier=True,
            fulltext_manifest=manifest,
        )
        self.assertTrue(complete_result.ok, complete_result.errors)

    def test_citations_require_distinct_verification_and_reading_layers(self):
        ledger = {
            "entries": [{
                "key": "Smith2024",
                "doi": DOI,
                "title": "A source",
                "abstract": "",
                "status": "verified",
                "canonical": {"type": "journal-article"},
                "verification": {
                    "bibliographic_status": "verified",
                    "retraction_status": "clear",
                },
            }]
        }
        result = validate_review.validate_review(
            scientific_review(), style="scientific", size="small", ledger=ledger
        )
        self.assertTrue(any("reading evidence" in error for error in result.errors))
        manifest = {"records": [{
            "ledger_key": "Smith2024", "status": "valid_fulltext", "counted": True
        }]}
        result = validate_review.validate_review(
            scientific_review(), style="scientific", size="small", ledger=ledger,
            fulltext_manifest=manifest,
        )
        self.assertFalse(any("reading evidence" in error for error in result.errors))

    def test_mojibake_and_scaffold_labels_are_hard_failures(self):
        broken = scientific_review().replace(
            "### Result", "Kicker: unfinished\n\n### Result"
        ).replace("conditional", "conditional â€” maybe")
        result = validate_review.validate_review(
            broken, style="scientific", size="small"
        )
        self.assertTrue(any("mojibake" in error for error in result.errors))
        self.assertTrue(any("scaffold" in error for error in result.errors))


class WordBreakdownTests(unittest.TestCase):
    """The tier range binds prose alone; tables, captions, and alt text are
    mandatory apparatus with their own caps, so a required figure never
    forces prose cuts (see references/contracts.md)."""

    @staticmethod
    def review_with_figure(prose_words=700, caption_words=40, alt_words=10):
        prose = " ".join(["evidence"] * prose_words)
        caption = " ".join(["shown"] * caption_words)
        alt = " ".join(["plot"] * alt_words)
        return (
            "## The headline\n\n"
            "*The question, plainly. The shape of the answer.*\n\n"
            f"The claim holds {prose} [Smith 2024](https://doi.org/{DOI}). "
            "The figure appears in [Figure 1](#fig-main).\n\n"
            "### The turn\n\n"
            f"Contrary evidence exists [Smith 2024](https://doi.org/{DOI}).\n\n"
            '<a id="fig-main"></a>\n'
            f"![{alt}](figure.png)\n\n"
            f"**Figure 1. The point.** {caption} "
            f"[Smith 2024](https://doi.org/{DOI}).\n\n"
            "**Sources**\n\n"
            f"**Smith (2024)** A source. *Journal*. https://doi.org/{DOI}\n"
        )

    def validate(self, markdown, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "figure.png").write_bytes(b"png")
            return validate_review.validate_review(
                markdown, style="popsci", size="small",
                base_dir=Path(tmp), **kwargs,
            )

    def test_breakdown_metric_reports_components(self):
        result = self.validate(self.review_with_figure())
        breakdown = result.metrics["word_breakdown"]
        self.assertGreaterEqual(breakdown["prose"], 700)
        self.assertGreaterEqual(breakdown["captions"], 40)
        self.assertGreaterEqual(breakdown["alt_text"], 10)
        self.assertEqual(
            breakdown["total"],
            breakdown["prose"] + breakdown["tables"]
            + breakdown["captions"] + breakdown["alt_text"],
        )

    def test_caption_words_do_not_break_the_prose_tier(self):
        markdown = self.review_with_figure(prose_words=930, caption_words=60)
        result = self.validate(markdown, strict_tier=True)
        word_errors = [e for e in result.errors if "words" in e]
        self.assertEqual(word_errors, [])

    def test_oversized_caption_fails_its_own_cap(self):
        markdown = self.review_with_figure(caption_words=120)
        result = self.validate(markdown, strict_tier=True)
        self.assertTrue(any("captions" in e for e in result.errors))

    def test_word_failures_name_the_component_and_overage(self):
        markdown = self.review_with_figure(prose_words=1200)
        result = self.validate(markdown, strict_tier=True)
        message = " ".join(result.errors)
        self.assertIn("prose body", message)
        self.assertIn("trim", message)

    def test_legacy_flag_restores_single_bucket_behavior(self):
        markdown = self.review_with_figure(prose_words=920, caption_words=70)
        modern = self.validate(markdown, strict_tier=True)
        legacy = self.validate(
            markdown, strict_tier=True, legacy_word_count=True
        )
        self.assertFalse(any("words" in e for e in modern.errors))
        self.assertTrue(any("body is" in e for e in legacy.errors))


class TermLinkCoverageTests(unittest.TestCase):
    def review(self, sentence):
        return (
            "## Does the test pass?\n\n"
            "**Abstract** — " + " ".join(["answer"] * 120) + "\n\n"
            "### Introduction\n\n"
            f"{sentence} [Smith 2024](https://doi.org/{DOI}).\n\n"
            "### Result\n\nThe evidence remains conditional.\n\n"
            "### Conclusion\n\nThe answer depends on context.\n\n"
            "**Sources**\n\n"
            f"**Smith (2024)** A source. *Journal*. https://doi.org/{DOI}\n"
        )

    def test_abbreviation_after_linked_expansion_is_covered(self):
        markdown = self.review(
            "The effect was 4.0 (95% "
            "[confidence interval](https://en.wikipedia.org/wiki/Confidence_interval)"
            " 2.0–8.1), and later the 95% CI narrowed"
        )
        result = validate_review.validate_review(
            markdown, style="scientific", size="small"
        )
        self.assertFalse(
            any("CI" in w for w in result.warnings), result.warnings
        )

    def test_unexplained_abbreviation_still_warns(self):
        markdown = self.review("The pooled SMD was 0.4")
        result = validate_review.validate_review(
            markdown, style="scientific", size="small"
        )
        self.assertTrue(any("SMD" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
