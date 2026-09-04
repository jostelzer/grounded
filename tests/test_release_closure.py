"""Every module a shipped script imports must itself be shipped.

`SCRIPT_FILES` in build_release_skill.py is a hand-maintained allowlist, so a
new sibling module can be imported by a released script and silently left out
of the bundle. That ships a skill whose exporter and validator die on import,
and no existing test notices because the repository checkout is complete.
"""

import ast
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "grounded"
SCRIPTS = SKILL / "scripts"

sys.path.insert(0, str(SCRIPTS))

from build_release_skill import SCRIPT_FILES, REFERENCE_FILES  # noqa: E402


def _local_imports(path: Path) -> set[str]:
    """Sibling modules `path` imports, by file name."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {f"{name}.py" for name in names if (SCRIPTS / f"{name}.py").is_file()}


class ReleaseClosureTests(unittest.TestCase):
    def test_allowlist_is_closed_under_local_imports(self) -> None:
        shipped = set(SCRIPT_FILES)
        missing: dict[str, set[str]] = {}
        for name in sorted(shipped):
            needed = _local_imports(SCRIPTS / name) - shipped
            if needed:
                missing[name] = needed
        self.assertEqual(
            missing,
            {},
            "shipped scripts import modules absent from SCRIPT_FILES; the "
            "release bundle would fail at import time",
        )

    def test_allowlisted_scripts_all_exist(self) -> None:
        absent = [name for name in SCRIPT_FILES if not (SCRIPTS / name).is_file()]
        self.assertEqual(absent, [])

    def test_referenced_local_guides_are_in_the_archive(self) -> None:
        missing = set()
        for document in [SKILL / "SKILL.md", *(SKILL / "references" / name for name in REFERENCE_FILES if name.endswith(".md"))]:
            for name in re.findall(r"(?<![\w/-])(?:references/)?([\w-]+\.md)", document.read_text()):
                if (SKILL / "references" / name).is_file() and name not in REFERENCE_FILES:
                    missing.add(name)
        self.assertEqual(missing, set())


if __name__ == "__main__":
    unittest.main()
