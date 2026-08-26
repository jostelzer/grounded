#!/usr/bin/env python3
"""Download the private Nature-family figure corpus used for style analysis.

The manifest is committed; the copyrighted source pixels are not. Downloads go
only to an explicit output directory and a report records provenance, hashes,
dimensions and byte counts for reproducible local analysis.
"""
import argparse
import hashlib
import json
import os
import struct
import tempfile
import urllib.request
from urllib.parse import urlparse


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = os.path.join(ROOT, "references", "nature-figure-corpus.json")
USER_AGENT = "scientific-review-skill/1.8.0 figure-style analysis"


def png_dimensions(path):
    with open(path, "rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("download is not a valid PNG")
    return struct.unpack(">II", header[16:24])


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path):
    with open(path, encoding="utf-8") as stream:
        manifest = json.load(stream)
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must contain a non-empty entries list")
    ids = [entry.get("id") for entry in entries]
    filenames = [entry.get("filename") for entry in entries]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("every corpus entry must have a unique id")
    if None in filenames or len(filenames) != len(set(filenames)):
        raise ValueError("every corpus entry must have a unique filename")
    for entry in entries:
        for field in ("id", "filename", "article_url", "image_url"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("every corpus entry must define %s" % field)
        filename = entry["filename"]
        if filename != os.path.basename(filename) or not filename.endswith(".png"):
            raise ValueError("figure filenames must be plain .png basenames")
        article = urlparse(entry["article_url"])
        image = urlparse(entry["image_url"])
        if article.scheme != "https" or article.hostname != "www.nature.com":
            raise ValueError("article_url must use the official Nature host")
        if (image.scheme != "https" or
                image.hostname != "media.springernature.com"):
            raise ValueError("image_url must use the official Springer Nature host")
    return manifest


def download(entry, output_dir, force=False):
    destination = os.path.join(output_dir, entry["filename"])
    if os.path.exists(destination) and not force:
        width, height = png_dimensions(destination)
        return destination, width, height, "existing"

    request = urllib.request.Request(
        entry["image_url"], headers={"User-Agent": USER_AGENT}
    )
    fd, candidate = tempfile.mkstemp(
        prefix=".figure-reference-", suffix=".png", dir=output_dir
    )
    os.close(fd)
    try:
        with urllib.request.urlopen(request, timeout=60) as response, \
                open(candidate, "wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
        width, height = png_dimensions(candidate)
        os.replace(candidate, destination)
        return destination, width, height, "downloaded"
    finally:
        if os.path.exists(candidate):
            os.unlink(candidate)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--out", required=True,
                        help="private output directory; downloaded figures are not repo assets")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    os.makedirs(args.out, exist_ok=True)
    report = {
        "manifest": os.path.abspath(args.manifest),
        "output_directory": os.path.abspath(args.out),
        "entries": [],
    }
    for entry in manifest["entries"]:
        path, width, height, status = download(entry, args.out, args.force)
        record = {
            "id": entry["id"],
            "filename": entry["filename"],
            "source": entry["article_url"],
            "image_url": entry["image_url"],
            "status": status,
            "width": width,
            "height": height,
            "bytes": os.path.getsize(path),
            "sha256": sha256(path),
        }
        report["entries"].append(record)
        print("{status:10} {width:4}x{height:<4} {filename}".format(**record))

    report_path = os.path.join(args.out, "download-report.json")
    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print("report    {}".format(report_path))


if __name__ == "__main__":
    main()
