#!/usr/bin/env python3
"""Crop a high-resolution PNG from a PDF page.

The --bbox-pt argument is left,top,right,bottom in PDF points.
"""

from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
from pathlib import Path


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = [float(x.strip()) for x in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be left,top,right,bottom")
    left, top, right, bottom = parts
    if right <= left or bottom <= top:
        raise argparse.ArgumentTypeError("bbox right/bottom must exceed left/top")
    return left, top, right, bottom


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--bbox-pt", type=parse_bbox, required=True)
    ap.add_argument("--padding-pt", type=float, default=0.0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--print-data-uri", action="store_true")
    args = ap.parse_args()

    tool = shutil.which("pdftocairo")
    if not tool:
        raise SystemExit("pdftocairo was not found on PATH")

    left, top, right, bottom = args.bbox_pt
    pad = args.padding_pt
    left = max(0, left - pad)
    top = max(0, top - pad)
    right += pad
    bottom += pad

    scale = args.dpi / 72.0
    x = round(left * scale)
    y = round(top * scale)
    w = round((right - left) * scale)
    h = round((bottom - top) * scale)

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    prefix = out.with_suffix("")
    cmd = [
        tool,
        "-png",
        "-singlefile",
        "-f",
        str(args.page),
        "-l",
        str(args.page),
        "-rx",
        str(args.dpi),
        "-ry",
        str(args.dpi),
        "-x",
        str(x),
        "-y",
        str(y),
        "-W",
        str(w),
        "-H",
        str(h),
        str(args.pdf.resolve()),
        str(prefix),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise SystemExit(proc.stderr or proc.stdout or f"pdftocairo failed: {proc.returncode}")

    generated = prefix.with_suffix(".png")
    if generated != out:
        generated.replace(out)

    print(f"Wrote {out}")
    if args.print_data_uri:
        data = base64.b64encode(out.read_bytes()).decode("ascii")
        print("data:image/png;base64," + data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

