#!/usr/bin/env python3
"""Build a deterministic, allowlisted Grounded ``.skill`` release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

from grounded_metadata import NAME


TOP_LEVEL_FILES = ("SKILL.md", "VERSION", "LICENSE", "requirements-pdf.txt")
ASSET_FILES = ("grounded-logo-512.png",)
# Visual evaluation topics are deliberately private and replaceable. They are
# never bundled as canonical templates in a public skill release.
EVAL_FILES = ()
REFERENCE_FILES = (
    "citation-rules.md",
    "claim-verification.md",
    "deck-guide.md",
    "evidence-weighing.md",
    "figure-archetypes.json",
    "figure-captions.md",
    "figure-feedback-generalization.md",
    "figure-generation-contract.md",
    "figure-inspection-contract.md",
    "figure-reference-analysis.md",
    "figure-style-presets.json",
    "figure-style-system.md",
    "figure-writing-style-overlays.json",
    "image-prompt-guide.md",
    "media-modes.md",
    "nature-figure-corpus.json",
    "no-script-fallback.md",
    "production-workflow.md",
    "quality-gates.md",
    "search-playbook.md",
    "sizes.md",
    "style-bullets.md",
    "style-eli5.md",
    "style-popsci.md",
    "style-scientific.md",
    "synthesis-guide.md",
    "writing-guide.md",
)
SCRIPT_FILES = (
    "artifact_io.py",
    "audit_fulltexts.py",
    "audit_production.py",
    "audit_search.py",
    "build_figure_prompt.py",
    "build_release_skill.py",
    "claim_evidence.py",
    "compose_hybrid_figure.py",
    "download_figure_references.py",
    "export_deck.py",
    "export_review.py",
    "fetch_fulltext.py",
    "figure_typography.py",
    "figure_contract.py",
    "figure_provenance.py",
    "find_papers.py",
    "format_references.py",
    "grounded_metadata.py",
    "normalize_figure_canvas.py",
    "qa_deck_pdf.py",
    "qa_figure.py",
    "qa_quantitative_geometry.py",
    "qa_review_pdf.py",
    "quantitative_drawing.py",
    "quantitative_figure_spec.py",
    "render_quantitative_figure.py",
    "validate_review.py",
    "verify_citations.py",
    "verify_claims.py",
    "weasyprint_export.py",
)


class ReleaseBuildError(RuntimeError):
    """Raised when the release bundle cannot be built safely."""


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ReleaseBuildError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def _release_files(root: Path) -> list[Path]:
    paths = [root / filename for filename in TOP_LEVEL_FILES]
    paths.extend(root / "assets" / filename for filename in ASSET_FILES)
    paths.extend(root / "evals" / filename for filename in EVAL_FILES)
    paths.extend(root / "references" / filename for filename in REFERENCE_FILES)
    paths.extend(root / "scripts" / filename for filename in SCRIPT_FILES)
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise ReleaseBuildError(
            "required release file(s) missing: " + ", ".join(missing)
        )
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


def _zip_timestamp(epoch: int) -> tuple[int, int, int, int, int, int]:
    stamp = time.gmtime(max(epoch, 315532800))[:6]
    # ZIP stores seconds at two-second precision.
    return (*stamp[:5], stamp[5] - stamp[5] % 2)


def build_release(
    root: Path,
    output: Path,
    *,
    commit: str,
    epoch: int,
    expected_version: str | None = None,
) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    files = _release_files(root)
    actual = (root / "VERSION").read_text(encoding="utf-8").strip().removeprefix("v")
    expected = (expected_version or actual).removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", actual):
        raise ReleaseBuildError(f"VERSION is not semantic: {actual!r}")
    if actual != expected:
        raise ReleaseBuildError(
            f"VERSION declares {actual!r}, but release expects {expected!r}"
        )
    if not re.fullmatch(r"[0-9a-fA-F]{7,64}", commit):
        raise ReleaseBuildError("commit must be an exact hexadecimal git object ID")

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_text, re.S)
    name_match = re.search(
        r"^name:\s*['\"]?([^'\"\s]+)['\"]?\s*$",
        frontmatter.group(1) if frontmatter else "",
        re.M,
    )
    if name_match is None or name_match.group(1) != NAME:
        raise ReleaseBuildError(f"SKILL.md frontmatter name must be {NAME!r}")

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    timestamp = _zip_timestamp(epoch)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.comment = commit.encode("ascii")
            for path in files:
                relative = path.relative_to(root)
                member = PurePosixPath(NAME, *relative.parts).as_posix()
                info = zipfile.ZipInfo(member, timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.flag_bits |= 0x800
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        with zipfile.ZipFile(temporary, "r") as archive:
            corrupt = archive.testzip()
            if corrupt:
                raise ReleaseBuildError(
                    f"release archive contains a corrupt member: {corrupt}"
                )
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        "archive": str(output),
        "archive_root": NAME,
        "bytes": output.stat().st_size,
        "commit": commit,
        "files": len(files),
        "sha256": digest,
        "version": actual,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="output .skill or .zip path")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument(
        "--version", help="expected release version (for example vX.Y.Z)"
    )
    parser.add_argument("--commit", help="commit recorded in the ZIP comment")
    parser.add_argument("--epoch", type=int, help="reproducible ZIP timestamp")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow a build from a dirty worktree (never use for a published release)",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        head = _git(root, "rev-parse", "HEAD")
        commit = args.commit or head
        if commit != head:
            raise ReleaseBuildError(
                f"release commit {commit} does not match checked-out HEAD {head}"
            )
        epoch = args.epoch
        if epoch is None:
            epoch = int(_git(root, "show", "-s", "--format=%ct", commit))
        if not args.allow_dirty and _git(root, "status", "--porcelain"):
            raise ReleaseBuildError(
                "worktree is dirty; commit the intended release contents first"
            )
        result = build_release(
            root,
            Path(args.out),
            commit=commit,
            epoch=epoch,
            expected_version=args.version,
        )
    except (OSError, ValueError, ReleaseBuildError) as exc:
        print(f"Release build failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
