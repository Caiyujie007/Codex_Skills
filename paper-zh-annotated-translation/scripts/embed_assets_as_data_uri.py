#!/usr/bin/env python3
"""Embed local HTML assets as data URIs or inline tags.

This is a mechanical portability helper. It does not decide document layout.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
from pathlib import Path


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def embed_css_urls(css: str, base: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1).strip().strip('"\'')
        if raw.startswith(("data:", "http:", "https:", "#")):
            return match.group(0)
        path = (base / raw).resolve()
        if not path.exists():
            return match.group(0)
        return f"url('{data_uri(path)}')"

    return re.sub(r"url\(([^)]+)\)", repl, css)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    html_path = args.html.resolve()
    base = html_path.parent
    html = html_path.read_text(encoding="utf-8")

    def img_repl(match: re.Match[str]) -> str:
        before, src, after = match.group(1), match.group(2), match.group(3)
        if src.startswith(("data:", "http:", "https:", "#")):
            return match.group(0)
        path = (base / src).resolve()
        if not path.exists():
            return match.group(0)
        return f"<img{before}src=\"{data_uri(path)}\"{after}>"

    html = re.sub(r"<img([^>]*?)src=[\"']([^\"']+)[\"']([^>]*)>", img_repl, html, flags=re.I)

    def link_repl(match: re.Match[str]) -> str:
        href = match.group(1)
        path = (base / href).resolve()
        if not path.exists():
            return match.group(0)
        css = embed_css_urls(path.read_text(encoding="utf-8"), path.parent)
        return f"<style>\n{css}\n</style>"

    html = re.sub(
        r"<link[^>]+rel=[\"']stylesheet[\"'][^>]+href=[\"']([^\"']+)[\"'][^>]*>",
        link_repl,
        html,
        flags=re.I,
    )

    def script_repl(match: re.Match[str]) -> str:
        src = match.group(1)
        path = (base / src).resolve()
        if not path.exists():
            return match.group(0)
        js = path.read_text(encoding="utf-8")
        return f"<script>\n{js}\n</script>"

    html = re.sub(r"<script[^>]+src=[\"']([^\"']+)[\"'][^>]*></script>", script_repl, html, flags=re.I)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

