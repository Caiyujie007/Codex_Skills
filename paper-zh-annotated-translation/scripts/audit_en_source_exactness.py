#!/usr/bin/env python3
"""Check EN source-map values against source PDF text after mechanical normalization."""

from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata
from pathlib import Path


def normalize(text: str) -> str:
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"([A-Za-z])-\s*\n\s*([a-z])", r"\1\2", text)
    text = re.sub(r"-\s*\n\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def loose_normalize(text: str) -> str:
    """Mechanical fallback for PDF extraction variance, not paraphrase tolerance.

    Some PDF extractors disagree on semantic hyphens when a hyphenated term is
    line-wrapped, for example `compiler-\narchitecture` may become either
    `compilerarchitecture` or `compiler-architecture`.  This fallback normalizes
    dash code points and ignores alpha-alpha hyphens so exact source text is not
    rejected for that mechanical reason alone.
    """
    text = unicodedata.normalize("NFKC", normalize(text))
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"[\u2018\u2019\u02bc`´]", "'", text)
    text = re.sub(r"(?<=[A-Za-z])-\s*(?=[A-Za-z])", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9])['*＊∗](?=s\b)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_source_map(html: str) -> dict[str, str]:
    match = re.search(
        r"<script[^>]+id=[\"']en-source-map[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.S | re.I,
    )
    if not match:
        return {}
    return json.loads(match.group(1))


def check_chunks_in_source(text: str, source_loose: str) -> bool:
    """Fallback when PDF extraction interleaves footers/figures into a paragraph.

    The EN text still has to be made of source sentences in order.  This only
    tolerates unrelated extracted text appearing between source sentences.
    """
    loose = loose_normalize(text)
    chunks = [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?])\s+", loose)
        if len(chunk.strip()) >= 40
    ]
    if not chunks:
        return False

    pos = 0
    missing = 0
    for chunk in chunks:
        idx = source_loose.find(chunk, pos)
        if idx < 0:
            missing += 1
            continue
        pos = idx + max(1, len(chunk) // 3)

    return missing == 0


def check_words_in_order(text: str, source_loose: str) -> bool:
    """Last mechanical fallback for badly interleaved PDF text extraction.

    This verifies that the substantive English tokens appear in the source in
    the same order, while tolerating injected page numbers, footers, figure
    text, or column-order debris between tokens.
    """
    tokens = re.findall(r"[A-Za-z0-9]+", loose_normalize(text).lower())
    if len(tokens) < 8:
        return False

    source = source_loose.lower()
    pos = 0
    matched = 0
    for token in tokens:
        idx = source.find(token, pos)
        if idx < 0:
            continue
        matched += 1
        pos = idx + len(token)

    return matched / len(tokens) >= 0.98


def check_token_coverage(text: str, source_loose: str) -> bool:
    """Very conservative fallback for severe PDF column-order extraction.

    This is useful for PDFs where paragraph order in extracted text is damaged
    by figures, footers, or columns.  It does not prove contiguous order, so the
    threshold is intentionally high and should mainly rescue extraction-order
    artifacts, not rewritten text.
    """
    tokens = re.findall(r"[A-Za-z0-9]+", loose_normalize(text).lower())
    if len(tokens) < 8:
        return False
    source_tokens = collections.Counter(re.findall(r"[A-Za-z0-9]+", source_loose.lower()))
    want = collections.Counter(tokens)
    matched = sum(min(count, source_tokens.get(token, 0)) for token, count in want.items())
    return matched / len(tokens) >= 0.98


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--source-text", type=Path, required=True)
    ap.add_argument(
        "--min-source-token-ratio",
        type=float,
        default=0.50,
        help=(
            "Minimum ratio of source-map English tokens to extracted PDF English tokens. "
            "This catches summary-like outputs whose EN snippets are exact but incomplete."
        ),
    )
    args = ap.parse_args()

    html = args.html.read_text(encoding="utf-8")
    source_raw = args.source_text.read_text(encoding="utf-8", errors="replace")
    source = normalize(source_raw)
    source_loose = loose_normalize(source_raw)
    source_map = load_source_map(html)
    source_tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", source_loose)
    mapped_english = " ".join(str(value) for value in source_map.values())
    mapped_tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", loose_normalize(mapped_english))

    failures = []
    loose_matches = []
    chunk_matches = []
    word_order_matches = []
    token_coverage_matches = []
    for key, value in source_map.items():
        norm = normalize(str(value))
        if not norm:
            continue
        if norm in source:
            continue
        if loose_normalize(str(value)) in source_loose:
            loose_matches.append(key)
            continue
        if check_chunks_in_source(str(value), source_loose):
            chunk_matches.append(key)
            continue
        if check_words_in_order(str(value), source_loose):
            word_order_matches.append(key)
            continue
        if check_token_coverage(str(value), source_loose):
            token_coverage_matches.append(key)
            continue
        failures.append((key, norm[:180]))

    print(f"Source-map entries: {len(source_map)}")
    print(f"Source tokens: {len(source_tokens)}")
    print(f"Source-map tokens: {len(mapped_tokens)}")
    ratio = (len(mapped_tokens) / len(source_tokens)) if source_tokens else 0.0
    print(f"Source-map token ratio: {ratio:.3f}")
    print(f"Loose mechanical matches: {len(loose_matches)}")
    print(f"Chunk-order matches: {len(chunk_matches)}")
    print(f"Word-order matches: {len(word_order_matches)}")
    print(f"Token-coverage matches: {len(token_coverage_matches)}")
    print(f"Exactness failures: {len(failures)}")
    coverage_failure = bool(source_tokens) and ratio < args.min_source_token_ratio
    if coverage_failure:
        print(
            "COVERAGE_FAILURE",
            f"source-map token ratio {ratio:.3f} is below minimum {args.min_source_token_ratio:.3f};",
            "output may be a summary rather than a translation",
        )
    for item in failures[:30]:
        print("NOT_FOUND", item[0], item[1])
    return 1 if failures or coverage_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
