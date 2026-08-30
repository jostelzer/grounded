import hashlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_release_skill  # noqa: E402
import grounded_metadata  # noqa: E402


class ReleaseSkillTests(unittest.TestCase):
    @staticmethod
    def fixture(root: Path):
        (root / "references").mkdir()
        (root / "assets").mkdir()
        (root / "evals").mkdir()
        (root / "scripts" / "__pycache__").mkdir(parents=True)
        (root / "examples").mkdir()
        (root / "tmp").mkdir()
        for filename, content in {
            "SKILL.md": "---\nname: grounded\n---\n",
            "VERSION": "9.1.0\n",
            "LICENSE": "MIT\n",
            "requirements-pdf.txt": "example==1\n",
        }.items():
            (root / filename).write_text(content, encoding="utf-8")
        for filename in build_release_skill.REFERENCE_FILES:
            (root / "references" / filename).write_text("guide\n", encoding="utf-8")
        for filename in build_release_skill.ASSET_FILES:
            (root / "assets" / filename).write_bytes(b"png")
        for filename in build_release_skill.EVAL_FILES:
            (root / "evals" / filename).write_text("{}\n", encoding="utf-8")
        for filename in build_release_skill.SCRIPT_FILES:
            (root / "scripts" / filename).write_text("print('ok')\n", encoding="utf-8")
        (root / "scripts" / "scratch.py").write_text(
            "ignore = True\n", encoding="utf-8"
        )
        (root / "scripts" / "__pycache__" / "tool.pyc").write_bytes(b"cache")
        (root / "examples" / "huge.pdf").write_bytes(b"example")
        (root / "tmp" / "scratch.txt").write_text("scratch", encoding="utf-8")

    def test_archive_is_allowlisted_versioned_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            self.fixture(root)
            first = Path(tmp) / "first.skill"
            second = Path(tmp) / "second.skill"
            options = {
                "commit": "a" * 40,
                "epoch": 1_700_000_000,
                "expected_version": "v9.1.0",
            }
            result = build_release_skill.build_release(root, first, **options)
            build_release_skill.build_release(root, second, **options)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                result["sha256"], hashlib.sha256(first.read_bytes()).hexdigest()
            )
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.comment, ("a" * 40).encode("ascii"))
                expected = {
                    *(
                        f"grounded/{filename}"
                        for filename in build_release_skill.TOP_LEVEL_FILES
                    ),
                    *(
                        f"grounded/assets/{filename}"
                        for filename in build_release_skill.ASSET_FILES
                    ),
                    *(
                        f"grounded/evals/{filename}"
                        for filename in build_release_skill.EVAL_FILES
                    ),
                    *(
                        f"grounded/references/{filename}"
                        for filename in build_release_skill.REFERENCE_FILES
                    ),
                    *(
                        f"grounded/scripts/{filename}"
                        for filename in build_release_skill.SCRIPT_FILES
                    ),
                }
                self.assertEqual(set(archive.namelist()), expected)
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                self.assertNotIn("grounded/scripts/scratch.py", archive.namelist())
                self.assertIn(
                    "grounded/references/claim-verification.md",
                    archive.namelist(),
                )
                self.assertIn("grounded/scripts/verify_claims.py", archive.namelist())
                self.assertIn("grounded/scripts/figure_contract.py", archive.namelist())
                self.assertIn(
                    "grounded/references/figure-inspection-contract.md",
                    archive.namelist(),
                )
                self.assertFalse(
                    any(name.startswith("grounded/evals/") for name in archive.namelist())
                )
                self.assertIsNone(archive.testzip())

    def test_version_mismatch_fails_before_replacing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            self.fixture(root)
            output = Path(tmp) / "release.skill"
            output.write_bytes(b"known-good")
            with self.assertRaises(build_release_skill.ReleaseBuildError):
                build_release_skill.build_release(
                    root,
                    output,
                    commit="b" * 40,
                    epoch=1_700_000_000,
                    expected_version="9.2.0",
                )
            self.assertEqual(output.read_bytes(), b"known-good")

    def test_required_files_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            os.rename(root / "SKILL.md", root / "WRONG.md")
            with self.assertRaises(build_release_skill.ReleaseBuildError):
                build_release_skill.build_release(
                    root,
                    root / "release.skill",
                    commit="c" * 40,
                    epoch=1_700_000_000,
                    expected_version="9.1.0",
                )

    def test_commit_provenance_must_be_an_exact_object_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with self.assertRaisesRegex(
                build_release_skill.ReleaseBuildError, "hexadecimal git object ID"
            ):
                build_release_skill.build_release(
                    root,
                    root / "release.skill",
                    commit="main",
                    epoch=1_700_000_000,
                    expected_version="9.1.0",
                )

    def test_archive_root_and_skill_name_cannot_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / "SKILL.md").write_text(
                "---\nname: old-name\n---\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                build_release_skill.ReleaseBuildError, "frontmatter name"
            ):
                build_release_skill.build_release(
                    root,
                    root / "release.skill",
                    commit="d" * 40,
                    epoch=1_700_000_000,
                    expected_version="9.1.0",
                )

    def test_shared_user_agent_uses_current_identity(self):
        agent = grounded_metadata.user_agent(
            mailto="person@example.org", qualifier="test-client"
        )
        self.assertIn(f"grounded/{grounded_metadata.version()} test-client", agent)
        self.assertIn("github.com/jostelzer/grounded", agent)
        self.assertNotIn("scientific-review-skill", agent)
        self.assertNotIn("1.8.0", agent)


if __name__ == "__main__":
    unittest.main()
