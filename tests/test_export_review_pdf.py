import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import export_review  # noqa: E402


class WritePdfTests(unittest.TestCase):
    def test_chrome_success_atomically_replaces_existing_pdf(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "review.pdf")
            with open(out, "wb") as f:
                f.write(b"%PDF-old")

            def render(cmd, **_kwargs):
                target = next(arg.split("=", 1)[1] for arg in cmd
                              if arg.startswith("--print-to-pdf="))
                with open(target, "wb") as f:
                    f.write(b"%PDF-fresh")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            with mock.patch.object(export_review, "find_chrome", return_value="/fake/chrome"), \
                    mock.patch.object(export_review.subprocess, "run", side_effect=render):
                tool = export_review.write_pdf("<p>new</p>", out)

            self.assertEqual(tool, "chrome")
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-fresh")

    def test_stale_existing_pdf_is_not_mistaken_for_failed_render(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "review.pdf")
            with open(out, "wb") as f:
                f.write(b"%PDF-old")
            failed = subprocess.CompletedProcess([], 1, "", "renderer failed")

            with mock.patch.object(export_review, "find_chrome", return_value="/fake/chrome"), \
                    mock.patch.object(export_review.subprocess, "run", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "renderer failed"):
                    export_review.write_pdf("<p>new</p>", out)

            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"%PDF-old")


if __name__ == "__main__":
    unittest.main()
