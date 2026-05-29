#!/usr/bin/env python3
"""Static sanity checks for a self-contained annotated HTML file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--require-data-images", action="store_true")
    args = ap.parse_args()

    text = args.html.read_text(encoding="utf-8")
    problems: list[str] = []

    if "\ufffd" in text:
        problems.append("Unicode replacement character found")

    srcs = re.findall(r"\s(?:src|href)=[\"']([^\"']+)[\"']", text, flags=re.I)
    external = [s for s in srcs if not s.startswith(("data:", "#", "mailto:"))]
    if external:
        problems.append(f"External src/href references: {external[:20]}")

    if args.require_data_images:
        bad_imgs = [
            s
            for s in re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", text, flags=re.I)
            if not s.startswith("data:")
        ]
        if bad_imgs:
            problems.append(f"Non-data img src values: {bad_imgs[:20]}")

    ids = re.findall(r"\sid=[\"']([^\"']+)[\"']", text, flags=re.I)
    dup_ids = sorted({x for x in ids if ids.count(x) > 1})
    if dup_ids:
        problems.append(f"Duplicate ids: {dup_ids[:20]}")

    style_text = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, flags=re.S | re.I))
    if re.search(r"h2[^{}]*\{[^{}]*column-span\s*:\s*all", style_text, flags=re.I | re.S):
        problems.append("Global h2 column-span:all found; use explicit source-derived classes instead")
    if re.search(r"figure\s*\{[^{}]*column-span\s*:\s*all", style_text, flags=re.I | re.S):
        problems.append("Global figure column-span:all found; only source-wide figures should span columns")
    if re.search(r"column-fill\s*:\s*auto", style_text, flags=re.I):
        # This can be valid inside a hand-built fixed-height paginated layout, but it is a common
        # cause of accidental one-column rendering in normal continuous paper HTML.
        if not re.search(r"(paper-page|page|fixed-height|height\s*:)", style_text, flags=re.I):
            problems.append("column-fill:auto found without an obvious fixed-height paginated layout")

    columns_class_count = len(re.findall(r"class=[\"'][^\"']*\bcolumns\b", text, flags=re.I))
    body_text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", text, flags=re.I)
    body_text = re.sub(r"\s+", " ", body_text).strip()
    if columns_class_count == 1 and len(body_text) > 12000:
        problems.append(
            "Only one .columns container in a long document; this often causes whole-paper column balancing. "
            "Use source-page-like or bounded flow chunks."
        )
    if len(body_text) > 12000 and columns_class_count > 0 and not re.search(
        r"\b(paper-page|source-page|flow-chunk|page-like)\b", text, flags=re.I
    ):
        problems.append(
            "Long two-column-looking document has .columns but no source-page-like chunk class "
            "(paper-page/source-page/flow-chunk/page-like); page rhythm may be lost"
        )
    for idx, match in enumerate(
        re.finditer(r"<(article|section|div)\b([^>]*\bclass=[\"'][^\"']*\bcolumns\b[^\"']*[\"'][^>]*)>([\s\S]*?)</\1>", text, flags=re.I),
        start=1,
    ):
        inner = match.group(3)
        inner_no_assets = re.sub(r"data:image/[^\"']+", "", inner, flags=re.I)
        inner_text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", inner_no_assets, flags=re.I)
        inner_text = re.sub(r"\s+", " ", inner_text).strip()
        h2_count = len(re.findall(r"<h2\b", inner, flags=re.I))
        if len(inner_text) > 9000 or h2_count >= 3:
            problems.append(
                f".columns chunk #{idx} looks too large for source-page-like layout "
                f"(text chars={len(inner_text)}, h2={h2_count}); split into bounded chunks"
            )
            break

    for match in re.finditer(r"<(?:p|div|section)\b([^>]*)>([\s\S]*?)(?:</(?:p|div|section)>)", text, flags=re.I):
        attrs, inner = match.group(1), match.group(2)
        class_attr = re.search(r"class=[\"']([^\"']*)[\"']", attrs, flags=re.I)
        classes = set(class_attr.group(1).split()) if class_attr else set()
        plain = re.sub(r"<[^>]+>", " ", inner)
        plain = re.sub(r"\s+", "", plain)
        is_keywords = "keywords" in classes or plain.startswith(("索引词", "关键词", "关键字", "IndexTerms"))
        if is_keywords:
            has_en = "data-en-id" in attrs or re.search(r"class=[\"'][^\"']*\ben-chip\b|data-en-(?:id|ref)=", inner, flags=re.I)
            if not has_en:
                problems.append("Source-derived keywords/index terms block lacks EN provenance")
                break

    dynamic_en_chips = bool(
        re.search(r"querySelectorAll\(\s*['\"]\[data-en-id\]['\"]\s*\)[\s\S]{0,1200}en-chip[\s\S]{0,1200}appendChild", text, flags=re.I)
        or re.search(r"en-chip[\s\S]{0,1200}querySelectorAll\(\s*['\"]\[data-en-id\]['\"]\s*\)[\s\S]{0,1200}appendChild", text, flags=re.I)
    )

    for match in re.finditer(r"<(p|figcaption|caption)\b([^>]*\bdata-en-id=[\"'][^\"']+[\"'][^>]*)>([\s\S]*?)</\1>", text, flags=re.I):
        tag, attrs, inner = match.group(1), match.group(2), match.group(3)
        class_attr = re.search(r"class=[\"']([^\"']*)[\"']", attrs, flags=re.I)
        classes = set(class_attr.group(1).split()) if class_attr else set()
        if classes & {"translation-note", "explain", "metadata"}:
            continue
        if not dynamic_en_chips and not re.search(r"\ben-chip\b", inner, flags=re.I):
            plain = re.sub(r"<[^>]+>", " ", inner)
            plain = re.sub(r"\s+", " ", plain).strip()
            problems.append(f"Source-mapped {tag} lacks a visible EN chip: {plain[:120]}")
            break

    match = re.search(r"<script[^>]+id=[\"']en-source-map[\"'][^>]*>(.*?)</script>", text, flags=re.S | re.I)
    if match:
        try:
            source_map = json.loads(match.group(1))
            if not isinstance(source_map, dict):
                problems.append("en-source-map is not a JSON object")
        except json.JSONDecodeError as exc:
            problems.append(f"Invalid en-source-map JSON: {exc}")

    print(f"HTML bytes: {args.html.stat().st_size}")
    print(f"src/href refs: {len(srcs)}")
    print(f"id count: {len(ids)}")
    print(f"Problems: {len(problems)}")
    for problem in problems:
        print("PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
