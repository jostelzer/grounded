import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compose_hybrid_figure  # noqa: E402


class HybridCompositorTests(unittest.TestCase):
    @staticmethod
    def make_base(path, size=(1200, 600)):
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB", size, "#FBFAF6")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((700, 100, 1100, 500), fill="#D3E5EF")
        canvas.save(path)

    @staticmethod
    def spec():
        return {
            "review_style": "popsci",
            "render_route": "hybrid",
            "render_context": "article",
            "title": "Caption only",
            "exact_text": ["Caption only", "Exact natural-width label"],
            "generated_text": [],
            "target_aspect_ratio": 2.0,
            "overlay": {
                "items": [
                    {
                        "type": "circle", "x": 0.2, "y": 0.5, "radius": 0.12,
                        "color": "#D00000", "stroke_px_at_1536": 8,
                    },
                    {
                        "type": "text", "x": 0.58, "y": 0.35,
                        "max_width": 0.3, "text": "Exact natural-width label",
                        "size_px_at_1536": 42, "weight": "bold",
                        "background": "#FBFAF6",
                    },
                ]
            },
        }

    def test_composition_preserves_source_dimensions_and_true_circle(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            out = Path(tmp) / "final.png"
            report = Path(tmp) / "composition.json"
            self.make_base(base)
            result = compose_hybrid_figure.compose(base, self.spec(), out, report)

            self.assertEqual(result["source_size_px"], [1200, 600])
            self.assertEqual(result["output_size_px"], [1200, 600])
            self.assertFalse(result["anisotropic_resize"])
            self.assertIn("bold", result["fonts"][0]["face_style"].lower())
            self.assertEqual(json.loads(report.read_text())["output_size_px"], [1200, 600])

            with Image.open(out).convert("RGB") as image:
                red = []
                for y in range(image.height):
                    for x in range(image.width):
                        r, g, b = image.getpixel((x, y))
                        if r > 170 and g < 60 and b < 60:
                            red.append((x, y))
            self.assertTrue(red)
            circle_width = max(x for x, _y in red) - min(x for x, _y in red)
            circle_height = max(y for _x, y in red) - min(y for _x, y in red)
            self.assertEqual(circle_width, circle_height)

    def test_mismatched_base_aspect_is_refused_instead_of_stretched(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base, size=(1200, 700))
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError, "refusing to stretch"):
                compose_hybrid_figure.compose(
                    base, self.spec(), Path(tmp) / "final.png")

    def test_non_hybrid_specs_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            spec = self.spec()
            spec["render_route"] = "generated"
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError, "render_route=hybrid"):
                compose_hybrid_figure.compose(
                    base, spec, Path(tmp) / "final.png")

    def test_overlay_must_cover_the_exact_deterministic_text_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            spec = self.spec()
            spec["exact_text"].append("Missing label")
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError, "missing 'Missing label'"):
                compose_hybrid_figure.compose(
                    base, spec, Path(tmp) / "final.png")

    def test_transparency_is_flattened_onto_the_style_paper_not_black(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            rgba = Image.new("RGBA", (1200, 600), (0, 0, 0, 0))
            rgba.paste((95, 143, 141, 255), (700, 100, 1100, 500))
            rgba.save(base)
            out = Path(tmp) / "final.png"
            result = compose_hybrid_figure.compose(base, self.spec(), out)
            self.assertTrue(result["alpha_composited"])
            self.assertEqual(result["background_color"], "#FFFFFF")
            with Image.open(out).convert("RGB") as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_unmasked_text_is_refused_even_in_apparently_quiet_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            spec = self.spec()
            del spec["overlay"]["items"][1]["background"]
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError,
                    "no explicit opaque mask"):
                compose_hybrid_figure.compose(
                    base, spec, Path(tmp) / "final.png")

    def test_opaque_replacement_mask_allows_text_repair(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            with Image.open(base).convert("RGB") as canvas:
                draw = ImageDraw.Draw(canvas)
                draw.rectangle((700, 205, 1060, 300), fill="#111111")
                canvas.save(base)
            spec = self.spec()
            del spec["overlay"]["items"][1]["background"]
            spec["overlay"]["items"].insert(1, {
                "type": "rectangle", "x": 0.57, "y": 0.33,
                "width": 0.32, "height": 0.19,
                "fill": "#FBFAF6", "color": "#FBFAF6",
            })
            result = compose_hybrid_figure.compose(
                base, spec, Path(tmp) / "final.png")
            self.assertTrue(result["mask_checks"][0]["opaque_mask"])

    def test_transparent_rectangle_cannot_claim_to_erase_base_text(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            with Image.open(base).convert("RGB") as canvas:
                draw = ImageDraw.Draw(canvas)
                draw.rectangle((700, 205, 1060, 300), fill="#111111")
                canvas.save(base)
            spec = self.spec()
            del spec["overlay"]["items"][1]["background"]
            spec["overlay"]["items"].insert(1, {
                "type": "rectangle", "x": 0.57, "y": 0.33,
                "width": 0.32, "height": 0.19,
                "fill": "#FBFAF600", "color": "#FBFAF600",
            })
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError,
                    "no explicit opaque mask"):
                compose_hybrid_figure.compose(
                    base, spec, Path(tmp) / "final.png")

    def test_transparent_text_background_cannot_claim_to_be_a_mask(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.png"
            self.make_base(base)
            spec = self.spec()
            spec["overlay"]["items"][1]["background"] = "#FBFAF600"
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError,
                    "background must be an opaque hex colour"):
                compose_hybrid_figure.compose(
                    base, spec, Path(tmp) / "final.png")

    def test_identity_regions_repeat_one_canonical_crop_without_stretching(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.png"
            canonical = root / "canonical.png"
            out = root / "final.png"
            self.make_base(base)
            asset = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
            draw = ImageDraw.Draw(asset)
            draw.polygon([(5, 55), (40, 5), (75, 55)], fill="#008C8CFF")
            asset.save(canonical)
            spec = self.spec()
            spec["overlay"]["items"][:0] = [
                {"type": "image_region", "asset": "canonical.png",
                 "identity_key": "specimen-1", "x": 0.08, "y": 0.08},
                {"type": "image_region", "asset": "canonical.png",
                 "identity_key": "specimen-1", "x": 0.38, "y": 0.08},
            ]
            result = compose_hybrid_figure.compose(base, spec, out)
            self.assertEqual(result["identity_keys_verified"], ["specimen-1"])
            self.assertEqual(len(result["identity_layers"]), 2)
            first, second = result["identity_layers"]
            self.assertEqual(first["asset_sha256"], second["asset_sha256"])
            self.assertEqual(first["source_box_px"], second["source_box_px"])
            self.assertEqual(first["scale"], second["scale"])
            self.assertFalse(first["anisotropic_resize"])
            with Image.open(out).convert("RGB") as final:
                first_box = tuple(first["destination_box_px"])
                second_box = tuple(second["destination_box_px"])
                self.assertEqual(
                    final.crop(first_box).tobytes(),
                    final.crop(second_box).tobytes())

    def test_identity_region_key_must_actually_repeat(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.png"
            canonical = root / "canonical.png"
            self.make_base(base)
            Image.new("RGBA", (40, 40), "#008C8CFF").save(canonical)
            spec = self.spec()
            spec["overlay"]["items"].insert(0, {
                "type": "image_region", "asset": "canonical.png",
                "identity_key": "singleton", "x": 0.1, "y": 0.1,
            })
            with self.assertRaisesRegex(
                    compose_hybrid_figure.HybridFigureError,
                    "repeat each identity_key"):
                compose_hybrid_figure.compose(base, spec, root / "final.png")


if __name__ == "__main__":
    unittest.main()
