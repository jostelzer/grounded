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


class ValidateReviewTests(unittest.TestCase):
    def test_four_showcase_examples_pass(self):
        examples = (
            ("scientific-sleeping-position.md", "scientific", "small"),
            ("popsci-mosquito-preference.md", "popsci", "small"),
            ("large-mediterranean-diet.md", "bullets", "large"),
            ("eli5-why-clouds-are-white.md", "eli5", "small"),
        )
        for filename, style, size in examples:
            with self.subTest(filename=filename):
                path = ROOT / "examples" / filename
                result = validate_review.validate_review(
                    path.read_text(encoding="utf-8"),
                    style=style,
                    size=size,
                    base_dir=path.parent,
                )
                self.assertTrue(result.ok, result.errors)

    def test_scientific_abstract_bounds_are_hard_failures(self):
        for count in (119, 251):
            with self.subTest(count=count):
                result = validate_review.validate_review(
                    scientific_review(count), style="scientific", size="small"
                )
                self.assertFalse(result.ok)
                self.assertTrue(
                    any("required 120–250" in error for error in result.errors)
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


if __name__ == "__main__":
    unittest.main()
