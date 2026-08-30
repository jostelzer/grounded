import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import normalize_figure_canvas  # noqa: E402


class NormalizeFigureCanvasTests(unittest.TestCase):
    def test_whitens_only_border_connected_paper_and_flattens_alpha(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            image = Image.new("RGBA", (200, 120), (250, 248, 244, 220))
            draw = ImageDraw.Draw(image)
            draw.rectangle((30, 20, 170, 100), fill=(20, 80, 120, 255))
            draw.rectangle((80, 50, 120, 70), fill=(250, 248, 244, 255))
            image.save(source)

            report = normalize_figure_canvas.normalize_canvas(source, output)
            with Image.open(output) as result:
                self.assertEqual(result.mode, "RGB")
                self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(result.getpixel((100, 60)), (250, 248, 244))
            self.assertGreater(report["pixels_whitened"], 0)

    def test_fails_instead_of_erasing_content_in_the_safety_band(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            image = Image.new("RGB", (200, 120), "white")
            ImageDraw.Draw(image).rectangle((0, 50, 30, 70), fill="#315A70")
            image.save(source)
            with self.assertRaisesRegex(
                    normalize_figure_canvas.CanvasNormalizationError,
                    "safety-band pixels remain non-white"):
                normalize_figure_canvas.normalize_canvas(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
