import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "skills" / "grounded"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_figure_prompt  # noqa: E402
import figure_contract  # noqa: E402
import figure_provenance  # noqa: E402
import quantitative_drawing  # noqa: E402
import quantitative_figure_spec  # noqa: E402
import render_quantitative_figure  # noqa: E402


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


class FigureArchitectureTests(unittest.TestCase):
    def test_prompt_builder_reexports_shared_contract(self):
        self.assertIs(
            build_figure_prompt.validate_semantic_plan,
            figure_contract.validate_semantic_plan,
        )
        self.assertIs(
            build_figure_prompt.validate_annotation_plan,
            figure_contract.validate_annotation_plan,
        )

    def test_figure_qa_does_not_import_prompt_cli(self):
        imports = imported_modules(SCRIPTS / "qa_figure.py")
        self.assertIn("figure_contract", imports)
        self.assertIn("figure_provenance", imports)
        self.assertNotIn("build_figure_prompt", imports)

    def test_quantitative_geometry_qa_stays_independent(self):
        imports = imported_modules(SCRIPTS / "qa_quantitative_geometry.py")
        self.assertNotIn("render_quantitative_figure", imports)
        self.assertNotIn("quantitative_figure_spec", imports)
        self.assertNotIn("quantitative_drawing", imports)

    def test_renderer_keeps_compatible_public_symbols(self):
        self.assertIs(
            render_quantitative_figure.QuantitativeFigureError,
            quantitative_figure_spec.QuantitativeFigureError,
        )
        self.assertIs(
            render_quantitative_figure._text_boxes_overlap,
            quantitative_drawing._text_boxes_overlap,
        )

    def test_shared_recipe_contains_no_benchmark_topics(self):
        paths = [
            ROOT / "references" / "figure-generation-contract.md",
            ROOT / "references" / "figure-inspection-contract.md",
            ROOT / "references" / "figure-feedback-generalization.md",
            ROOT / "references" / "image-prompt-guide.md",
            ROOT / "references" / "media-modes.md",
        ]
        text = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
        for topic in (
            "seed oil",
            "breast lump",
            "microplastic",
            "ozempic",
            "smartphone ban",
            "maillard",
            "lisbon earthquake",
        ):
            self.assertNotIn(topic, text)


if __name__ == "__main__":
    unittest.main()
