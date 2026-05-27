#!/usr/bin/env python3
"""Extract regularly sampled candidate frames from MP4 lessons.

This script intentionally does not decide the final slide list. It creates
candidate images for later deduplication/contact-sheet review.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def safe_stem(path: Path) -> str:
    chars = []
    for ch in path.stem.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_") or "lesson"


def run_ffmpeg(video: Path, out_dir: Path, interval: int, width: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "frame_%05d.jpg"
    vf = f"fps=1/{interval},scale={width}:-1"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(video),
        "-vf",
        vf,
        "-q:v",
        "2",
        str(pattern),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--out-root", type=Path, default=Path("_candidate_frames"))
    parser.add_argument("--interval", type=int, default=5, help="seconds between sampled frames")
    parser.add_argument("--width", type=int, default=1600, help="output image width")
    args = parser.parse_args()

    for video in args.videos:
        if not video.exists():
            raise FileNotFoundError(video)
        out_dir = args.out_root / safe_stem(video)
        print(f"[extract] {video} -> {out_dir}")
        run_ffmpeg(video, out_dir, args.interval, args.width)


if __name__ == "__main__":
    main()

