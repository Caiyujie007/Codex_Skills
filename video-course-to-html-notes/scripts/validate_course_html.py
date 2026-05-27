#!/usr/bin/env python3
"""Validate generated video-course HTML notes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BAD_PATTERNS = [
    "这一条可以作为",
    "按单独提问",
    "deep-dive",
    "single-ask",
    "红色批注版",
    "同页批注",
]

MOJIBAKE_PATTERNS = ["�", "鍚", "閫", "瑙", "绔", "涓"]


def validate_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    sections = len(re.findall(r"<section\\b", text))
    answers = len(re.findall(r'<div class="answer">', text))
    images = re.findall(r'<img\\b[^>]*\\bsrc="([^"]+)"', text)

    if sections != answers or sections != len(images):
        errors.append(f"count mismatch: sections={sections}, answers={answers}, images={len(images)}")

    for src in images:
        if re.match(r"^[A-Za-z]:[\\\\/]", src) or src.startswith("file://"):
            errors.append(f"absolute local image path: {src}")
        if not (path.parent / src).exists():
            errors.append(f"missing image: {src}")

    for pat in BAD_PATTERNS:
        if pat in text:
            errors.append(f"stale template text: {pat}")

    for pat in MOJIBAKE_PATTERNS:
        if pat in text:
            errors.append(f"possible mojibake: {pat}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for item in args.paths:
        files = sorted(item.glob("*.html")) if item.is_dir() else [item]
        for file in files:
            errors = validate_file(file)
            if errors:
                failed = True
                print(f"[FAIL] {file}")
                for err in errors:
                    print(f"  - {err}")
            else:
                print(f"[OK] {file}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

