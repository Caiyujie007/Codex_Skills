#!/usr/bin/env python3
"""Check that translated source-paper text has EN provenance."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SKIP_CLASSES = {
    "title-block",
    "authors",
    "affiliation",
    "subtitle",
    "translation-note",
    "explain",
    "ref-list",
    "metadata",
}


class CoverageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[set[str]] = []
        self.candidates: list[tuple[str, dict[str, str], str, bool]] = []
        self.current: dict | None = None
        self.source_map_text = ""
        self.in_source_map = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = set(attr.get("class", "").split())
        inherited = set(self.stack[-1]) if self.stack else set()
        self.stack.append(inherited | classes)
        if tag == "script" and attr.get("id") == "en-source-map":
            self.in_source_map = True
        if tag in {"p", "figcaption", "caption"}:
            self.current = {"tag": tag, "attrs": attr, "text": [], "skip": bool((inherited | classes) & SKIP_CLASSES)}

    def handle_endtag(self, tag: str) -> None:
        if self.current and tag == self.current["tag"]:
            text = "".join(self.current["text"]).strip()
            self.candidates.append((self.current["tag"], self.current["attrs"], text, self.current["skip"]))
            self.current = None
        if tag == "script":
            self.in_source_map = False
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.in_source_map:
            self.source_map_text += data
        if self.current is not None:
            self.current["text"].append(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    args = ap.parse_args()

    text = args.html.read_text(encoding="utf-8")
    parser = CoverageParser()
    parser.feed(text)

    try:
        source_map = json.loads(parser.source_map_text) if parser.source_map_text.strip() else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid en-source-map JSON: {exc}")

    missing = []
    missing_map = []
    for tag, attrs, content, skip in parser.candidates:
        if skip or not content:
            continue
        en_id = attrs.get("data-en-id")
        if not en_id:
            missing.append((tag, content[:120]))
        elif en_id not in source_map:
            missing_map.append((en_id, tag, content[:120]))

    print(f"Candidates checked: {len(parser.candidates)}")
    print(f"Missing data-en-id: {len(missing)}")
    print(f"Missing source-map entries: {len(missing_map)}")
    for item in missing[:20]:
        print("MISSING_ID", item)
    for item in missing_map[:20]:
        print("MISSING_MAP", item)
    return 1 if missing or missing_map else 0


if __name__ == "__main__":
    raise SystemExit(main())
