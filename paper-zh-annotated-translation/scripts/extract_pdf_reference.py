#!/usr/bin/env python3
"""Extract mechanical PDF reference artifacts for paper translation work.

This script creates text/layout/page-preview artifacts for inspection only.
Do not use the previews as final translated body content.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> dict:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except FileNotFoundError as exc:
        return {"cmd": cmd, "returncode": None, "stdout": "", "stderr": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("paper_ref"))
    ap.add_argument("--dpi", type=int, default=144)
    args = ap.parse_args()

    pdf = args.pdf.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "pdf": str(pdf),
        "out_dir": str(out_dir),
        "dpi": args.dpi,
        "tools": {},
        "commands": [],
    }

    for tool in ["pdfinfo", "pdftotext", "pdftoppm", "pdftocairo"]:
        manifest["tools"][tool] = shutil.which(tool)

    if manifest["tools"]["pdfinfo"]:
        res = run(["pdfinfo", str(pdf)])
        (out_dir / "pdfinfo.txt").write_text(res["stdout"] + res["stderr"], encoding="utf-8")
        manifest["commands"].append(res)

    if manifest["tools"]["pdftotext"]:
        for layout, name in [(False, "source.raw.txt"), (True, "source.layout.txt")]:
            cmd = ["pdftotext"]
            if layout:
                cmd.append("-layout")
            cmd += [str(pdf), str(out_dir / name)]
            manifest["commands"].append(run(cmd))

    if manifest["tools"]["pdftoppm"]:
        prefix = out_dir / "page"
        cmd = ["pdftoppm", "-r", str(args.dpi), "-png", str(pdf), str(prefix)]
        manifest["commands"].append(run(cmd))
    elif manifest["tools"]["pdftocairo"]:
        prefix = out_dir / "page"
        cmd = ["pdftocairo", "-png", "-r", str(args.dpi), str(pdf), str(prefix)]
        manifest["commands"].append(run(cmd))

    (out_dir / "reference_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote reference artifacts to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

