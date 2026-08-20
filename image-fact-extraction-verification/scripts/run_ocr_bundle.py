#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(command, *, stdout_path=None):
    if stdout_path is None:
        return subprocess.run(command, check=True, text=True, capture_output=True)
    with stdout_path.open("w", encoding="utf-8") as handle:
        return subprocess.run(command, check=True, text=True, stdout=handle, stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(
        description="Run independent Apple Vision and Tesseract OCR passes for verification."
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--languages", default="chi_sim+eng")
    args = parser.parse_args()

    image = args.image.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not image.is_file():
        parser.error(f"image does not exist: {image}")

    output_dir.mkdir(parents=True, exist_ok=True)
    script_dir = Path(__file__).resolve().parent
    manifest = {
        "source": str(image),
        "engines": {},
        "notes": [
            "OCR output is candidate evidence and must be checked against source pixels.",
            "Do not infer unresolved fields from patterns."
        ],
    }

    try:
        vision_path = output_dir / "vision.json"
        result = run(
            ["xcrun", "swift", str(script_dir / "apple_vision_ocr.swift"), str(image)]
        )
        vision_path.write_text(result.stdout, encoding="utf-8")
        manifest["engines"]["apple_vision"] = {"ok": True, "output": str(vision_path)}
    except (OSError, subprocess.CalledProcessError) as exc:
        manifest["engines"]["apple_vision"] = {"ok": False, "error": str(exc)}

    tesseract = shutil.which("tesseract")
    if tesseract:
        for psm in (6, 11):
            prefix = output_dir / f"tesseract_psm{psm}"
            try:
                text_result = run(
                    [tesseract, str(image), "stdout", "-l", args.languages, "--psm", str(psm)]
                )
                prefix.with_suffix(".txt").write_text(text_result.stdout, encoding="utf-8")
                tsv_result = run(
                    [tesseract, str(image), "stdout", "-l", args.languages, "--psm", str(psm), "tsv"]
                )
                prefix.with_suffix(".tsv").write_text(tsv_result.stdout, encoding="utf-8")
                manifest["engines"][f"tesseract_psm{psm}"] = {
                    "ok": True,
                    "text": str(prefix.with_suffix(".txt")),
                    "tsv": str(prefix.with_suffix(".tsv")),
                }
            except (OSError, subprocess.CalledProcessError) as exc:
                manifest["engines"][f"tesseract_psm{psm}"] = {
                    "ok": False,
                    "error": str(exc),
                }
    else:
        manifest["engines"]["tesseract"] = {
            "ok": False,
            "error": "tesseract executable not found",
        }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    successful = sum(1 for value in manifest["engines"].values() if value.get("ok"))
    if successful == 0:
        print(f"No OCR engine succeeded. See {manifest_path}", file=sys.stderr)
        return 1

    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
