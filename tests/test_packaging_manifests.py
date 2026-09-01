"""The three published manifests must declare one shared version."""

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "grounded"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PackagingManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
        self.plugin = _json(REPO / ".claude-plugin" / "plugin.json")
        self.marketplace = _json(REPO / ".claude-plugin" / "marketplace.json")
        self.gemini = _json(REPO / "gemini-extension.json")

    def test_plugin_manifest_tracks_the_packaged_version(self) -> None:
        self.assertEqual(self.plugin["version"], self.version)

    def test_gemini_manifest_tracks_the_packaged_version(self) -> None:
        self.assertEqual(self.gemini["version"], self.version)

    def test_manifest_names_match_the_skill_directory(self) -> None:
        self.assertEqual(self.plugin["name"], SKILL.name)
        self.assertEqual(self.gemini["name"], SKILL.name)
        self.assertEqual(
            [entry["name"] for entry in self.marketplace["plugins"]], [SKILL.name]
        )

    def test_marketplace_points_at_this_repository(self) -> None:
        sources = [entry["source"] for entry in self.marketplace["plugins"]]
        self.assertEqual(sources, ["./"])

    def test_every_platform_finds_the_same_skill_file(self) -> None:
        self.assertTrue((SKILL / "SKILL.md").is_file())
        # The release allowlist requires a LICENSE inside the bundle itself.
        self.assertTrue((SKILL / "LICENSE").is_file())


if __name__ == "__main__":
    unittest.main()
