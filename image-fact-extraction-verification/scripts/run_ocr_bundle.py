#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(command, *, stdout_path=None):
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if stdout_path is not None:
            stdout_path.write_text(result.stdout, encoding="utf-8")
        return {"ok": True, "command": command, "stderr": result.stderr.strip()}
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "") or str(exc)
        return {"ok": False, "command": command, "error": stderr.strip()}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path):
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    width = re.search(r"pixelWidth:\s*(\d+)", result.stdout)
    height = re.search(r"pixelHeight:\s*(\d+)", result.stdout)
    return {
        "width": int(width.group(1)) if width else None,
        "height": int(height.group(1)) if height else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run complementary local OCR engines and retain evidence outputs."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--languages", default="chi_sim+eng")
    parser.add_argument("--psm", nargs="+", type=int, default=[6, 11])
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.is_file():
        parser.error(f"source image does not exist: {source}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "sha256": sha256(source),
        "dimensions": image_dimensions(source),
        "runs": [],
    }

    swift = shutil.which("swift")
    vision_script = Path(__file__).with_name("apple_vision_ocr.swift")
    if swift:
        manifest["runs"].append(
            {
                "engine": "apple_vision",
                **run([swift, str(vision_script), str(source)], stdout_path=output_dir / "vision.json"),
            }
        )
    else:
        manifest["runs"].append(
            {"engine": "apple_vision", "ok": False, "error": "swift not found"}
        )

    tesseract = shutil.which("tesseract")
    if tesseract:
        version = subprocess.run(
            [tesseract, "--version"], check=False, capture_output=True, text=True
        ).stdout.splitlines()
        manifest["tesseract_version"] = version[0] if version else "unknown"
        for psm in args.psm:
            text_path = output_dir / f"tesseract_psm{psm}.txt"
            tsv_base = output_dir / f"tesseract_psm{psm}"
            text_run = run(
                [tesseract, str(source), "stdout", "-l", args.languages, "--psm", str(psm)],
                stdout_path=text_path,
            )
            tsv_run = run(
                [
                    tesseract,
                    str(source),
                    str(tsv_base),
                    "-l",
                    args.languages,
                    "--psm",
                    str(psm),
                    "tsv",
                ]
            )
            manifest["runs"].append(
                {
                    "engine": "tesseract",
                    "psm": psm,
                    "text": text_run,
                    "tsv": tsv_run,
                    "ok": text_run["ok"] or tsv_run["ok"],
                }
            )
    else:
        manifest["runs"].append(
            {"engine": "tesseract", "ok": False, "error": "tesseract not found"}
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if not any(run_info.get("ok") for run_info in manifest["runs"]):
        print(f"No OCR engine succeeded. See {manifest_path}", file=sys.stderr)
        return 1

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
