#!/usr/bin/env python3
"""Canonical, browser-free PDF renderer for Grounded reviews.

Grounded's visual design lives in the HTML/CSS produced by ``export_review``.
This module renders that exact artifact with one pinned print engine.  It never
launches a browser, fetches the network, or silently changes renderer or fonts.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


REQUIRED_WEASYPRINT = "69.0"
REQUIRED_PYDYF = "0.12.1"
REQUIRED_FONTTOOLS = "4.63.0"
REQUIRED_PYPDF = "6.10.0"
REQUIRED_PILLOW = "12.3.0"
CANONICAL_FONT_FAMILIES = ("Charter", "Helvetica-Neue")


class PdfRuntimeError(RuntimeError):
    """Raised when the canonical renderer is unavailable or incompatible."""


class PdfInputError(ValueError):
    """Raised when an output path or rendered artifact is unsafe."""


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as exc:
        raise PdfRuntimeError(
            f"Grounded PDF export requires {distribution}; install the exact "
            "runtime in requirements-pdf.txt"
        ) from exc


def _weasyprint_cli() -> str | None:
    executable = shutil.which("weasyprint")
    if not executable:
        return None
    try:
        completed = subprocess.run(
            [executable, "--version"], check=False, capture_output=True,
            text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.fullmatch(
        r"WeasyPrint version ([0-9]+(?:\.[0-9]+)*)\s*",
        completed.stdout,
    )
    if completed.returncode == 0 and match and match.group(1) == REQUIRED_WEASYPRINT:
        return executable
    return None


def _python_weasyprint_available() -> bool:
    try:
        import weasyprint
        # Importing the package loads its native Pango bindings.  This is an
        # intentional readiness check, not merely a package-presence check.
        return weasyprint.__version__ == REQUIRED_WEASYPRINT
    except Exception:
        return False


def require_runtime() -> dict[str, str]:
    """Validate the sole renderer and the PDF inspection dependency."""
    versions = {
        "pypdf": _package_version("pypdf"),
        "pillow": _package_version("Pillow"),
    }
    required = {
        "pypdf": REQUIRED_PYPDF,
        "pillow": REQUIRED_PILLOW,
    }
    mismatches = [
        f"{name} {versions[name]} (required {required[name]})"
        for name in required if versions[name] != required[name]
    ]
    if mismatches:
        raise PdfRuntimeError(
            "Grounded PDF export requires the exact deterministic runtime: "
            + ", ".join(mismatches)
        )

    cli = _weasyprint_cli()
    if cli:
        versions.update(weasyprint=REQUIRED_WEASYPRINT, interface="cli")
        return versions
    if _python_weasyprint_available():
        versions.update(
            pydyf=_package_version("pydyf"),
            fonttools=_package_version("fonttools"),
        )
        python_requirements = {
            "pydyf": REQUIRED_PYDYF,
            "fonttools": REQUIRED_FONTTOOLS,
        }
        python_mismatches = [
            f"{name} {versions[name]} (required {required_version})"
            for name, required_version in python_requirements.items()
            if versions[name] != required_version
        ]
        if python_mismatches:
            raise PdfRuntimeError(
                "Grounded PDF export requires the exact deterministic runtime: "
                + ", ".join(python_mismatches)
            )
        versions.update(weasyprint=REQUIRED_WEASYPRINT, interface="python")
        return versions
    raise PdfRuntimeError(
        f"Grounded PDF export requires a working WeasyPrint "
        f"{REQUIRED_WEASYPRINT} runtime with its native Pango libraries. "
        "Install requirements-pdf.txt (Linux) or the matching Homebrew "
        "weasyprint formula (macOS), then rerun --check-pdf-runtime. Chrome "
        "and approximate renderers are never used as fallbacks."
    )


def _render_with_cli(executable: str, html_text: str, target: str) -> None:
    command = [
        executable,
        "--quiet",
        "--allowed-protocols", "data",
        "--fail-on-http-errors",
        "-", target,
    ]
    try:
        completed = subprocess.run(
            command, input=html_text, capture_output=True, text=True,
            timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PdfRuntimeError(f"WeasyPrint failed to render the PDF: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise PdfRuntimeError(f"WeasyPrint failed to render the PDF: {detail[:600]}")


def _render_with_python(html_text: str, target: str) -> None:
    from weasyprint import HTML
    from weasyprint.urls import URLFetcher

    data_only_fetcher = URLFetcher(
        allowed_protocols=("data",), allow_redirects=False, fail_on_errors=True,
    )

    try:
        HTML(string=html_text, url_fetcher=data_only_fetcher).write_pdf(target)
    except PdfInputError:
        raise
    except Exception as exc:
        raise PdfRuntimeError(f"WeasyPrint failed to render the PDF: {exc}") from exc


def _embedded_font_families(reader) -> set[str]:
    families: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        fonts = resources.get_object().get("/Font")
        if not fonts:
            continue
        for reference in fonts.get_object().values():
            base_font = str(reference.get_object().get("/BaseFont", ""))
            families.add(base_font.split("+", 1)[-1])
    return families


def _validate_rendered_pdf(path: str) -> None:
    try:
        from pypdf import PdfReader

        with open(path, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise PdfRuntimeError("WeasyPrint output is not a PDF")
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted or not reader.pages:
            raise PdfRuntimeError("WeasyPrint produced an invalid or encrypted PDF")
        producer = str((reader.metadata or {}).get("/Producer", ""))
        if producer != f"WeasyPrint {REQUIRED_WEASYPRINT}":
            raise PdfRuntimeError(
                f"unexpected PDF producer {producer!r}; expected pinned WeasyPrint"
            )
        embedded = _embedded_font_families(reader)
        missing = [
            family for family in CANONICAL_FONT_FAMILIES
            if not any(font.startswith(family) for font in embedded)
        ]
        if missing:
            raise PdfRuntimeError(
                "canonical Grounded fonts are unavailable: " + ", ".join(missing)
                + ". Refusing to ship a fallback-font redesign."
            )
    except PdfRuntimeError:
        raise
    except Exception as exc:
        raise PdfRuntimeError(f"rendered PDF failed strict validation: {exc}") from exc


def write_pdf(html_text: str, out_path: str) -> dict[str, object]:
    """Render canonical HTML atomically and return build metadata."""
    runtime = require_runtime()
    target = Path(out_path).resolve()
    if not target.parent.is_dir():
        raise PdfInputError(f"output directory does not exist: {target.parent}")

    with tempfile.TemporaryDirectory(
            prefix=".grounded-pdf-", dir=target.parent) as temporary:
        rendered = os.path.join(temporary, "rendered.pdf")
        if runtime["interface"] == "cli":
            executable = _weasyprint_cli()
            if executable is None:  # Runtime changed after the preflight.
                raise PdfRuntimeError("WeasyPrint runtime disappeared during export")
            _render_with_cli(executable, html_text, rendered)
        else:
            _render_with_python(html_text, rendered)
        if not os.path.isfile(rendered) or os.path.getsize(rendered) < 5:
            raise PdfRuntimeError("WeasyPrint did not produce a PDF")
        _validate_rendered_pdf(rendered)
        with open(rendered, "rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        os.replace(rendered, target)
    return {
        "renderer": f"weasyprint-{REQUIRED_WEASYPRINT}",
        "runtime": runtime,
        "sha256": digest,
    }
