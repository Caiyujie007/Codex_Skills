#!/usr/bin/env python3
"""Build a machine-translation proofreading report.

This script never edits the HTML. It only creates a review artifact.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


def load_source_map(html: str) -> dict[str, str]:
    match = re.search(
        r"<script[^>]+id=[\"']en-source-map[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.S | re.I,
    )
    if not match:
        return {}
    return json.loads(match.group(1))


def google_translate(text: str) -> str:
    url = (
        "https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=en&tl=zh-CN&dt=t&q="
        + urllib.parse.quote(text)
    )
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--provider", choices=["google"], default="google")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.1)
    args = ap.parse_args()

    source_map = load_source_map(args.html.read_text(encoding="utf-8"))
    items = list(source_map.items())
    if args.limit > 0:
        items = items[: args.limit]

    report = []
    for key, en in items:
        try:
            mt = google_translate(en)
            err = None
        except Exception as exc:  # noqa: BLE001
            mt = ""
            err = str(exc)
        report.append({"id": key, "en": en, "mt_zh": mt, "error": err})
        if args.sleep:
            time.sleep(args.sleep)

    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

