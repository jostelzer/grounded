import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest
from urllib.parse import urlparse


ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "grounded",
)
SCRIPT = os.path.join(ROOT, "scripts", "download_figure_references.py")
sys.path.insert(0, os.path.dirname(SCRIPT))
MANIFEST = os.path.join(ROOT, "references", "nature-figure-corpus.json")
SPEC = importlib.util.spec_from_file_location("download_figure_references", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_png_header(path, width, height):
    with open(path, "wb") as stream:
        stream.write(b"\x89PNG\r\n\x1a\n")
        stream.write(struct.pack(">I", 13))
        stream.write(b"IHDR")
        stream.write(struct.pack(">II", width, height))


class FigureReferenceTests(unittest.TestCase):
    def test_manifest_is_official_source_metadata_not_bundled_pixels(self):
        manifest = MODULE.load_manifest(MANIFEST)
        entries = manifest["entries"]
        self.assertFalse(manifest["downloaded_images_are_repo_assets"])
        self.assertEqual(len(entries), 21)
        self.assertEqual(
            sum(e["journal"] == "Nature Reviews Neuroscience" for e in entries),
            15)
        self.assertEqual(
            sum(e["journal"] == "Nature Neuroscience" for e in entries), 6)
        self.assertEqual(len({e["article_url"] for e in entries}), 12)
        for entry in entries:
            self.assertEqual(urlparse(entry["article_url"]).hostname,
                             "www.nature.com")
            self.assertEqual(urlparse(entry["image_url"]).hostname,
                             "media.springernature.com")
            self.assertEqual(os.path.dirname(entry["filename"]), "")
            self.assertTrue(entry["filename"].endswith(".png"))
            self.assertGreaterEqual(len(entry["roles"]), 1)

    def test_png_dimensions_reads_ihdr_and_rejects_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            valid = os.path.join(tmp, "valid.png")
            invalid = os.path.join(tmp, "invalid.png")
            write_png_header(valid, 1536, 1024)
            with open(invalid, "wb") as stream:
                stream.write(b"not a png")
            self.assertEqual(MODULE.png_dimensions(valid), (1536, 1024))
            with self.assertRaisesRegex(ValueError, "valid PNG"):
                MODULE.png_dimensions(invalid)

    def test_manifest_rejects_duplicate_ids_and_filenames(self):
        cases = [
            [{"id": "same", "filename": "a.png"},
             {"id": "same", "filename": "b.png"}],
            [{"id": "a", "filename": "same.png"},
             {"id": "b", "filename": "same.png"}],
        ]
        for entries in cases:
            with self.subTest(entries=entries), tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", encoding="utf-8") as stream:
                json.dump({"entries": entries}, stream)
                stream.flush()
                with self.assertRaises(ValueError):
                    MODULE.load_manifest(stream.name)

    def test_manifest_rejects_path_traversal_and_nonofficial_hosts(self):
        base = {
            "id": "figure-one",
            "filename": "figure.png",
            "article_url": "https://www.nature.com/articles/example",
            "image_url": "https://media.springernature.com/example.png"
        }
        cases = [
            dict(base, filename="../figure.png"),
            dict(base, article_url="https://example.com/articles/example"),
            dict(base, image_url="https://example.com/figure.png"),
        ]
        for entry in cases:
            with self.subTest(entry=entry), tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", encoding="utf-8") as stream:
                json.dump({"entries": [entry]}, stream)
                stream.flush()
                with self.assertRaises(ValueError):
                    MODULE.load_manifest(stream.name)

    def test_main_reuses_existing_private_image_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = os.path.join(tmp, "figure.png")
            manifest_path = os.path.join(tmp, "manifest.json")
            write_png_header(image_path, 640, 480)
            manifest = {
                "entries": [{
                    "id": "figure-one",
                    "filename": "figure.png",
                    "article_url": "https://www.nature.com/articles/example",
                    "image_url": "https://media.springernature.com/example.png"
                }]
            }
            with open(manifest_path, "w", encoding="utf-8") as stream:
                json.dump(manifest, stream)
            self.assertIsNone(MODULE.main([
                "--manifest", manifest_path, "--out", tmp]))
            with open(os.path.join(tmp, "download-report.json"),
                      encoding="utf-8") as stream:
                report = json.load(stream)
            record = report["entries"][0]
            self.assertEqual(record["status"], "existing")
            self.assertEqual((record["width"], record["height"]), (640, 480))
            self.assertEqual(len(record["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
