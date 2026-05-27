#!/usr/bin/env python3
"""Create contact sheets from extracted slide/frame images."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def iter_images(path: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return [p for p in sorted(path.iterdir()) if p.suffix.lower() in exts]


def make_sheet(images: list[Path], out_path: Path, columns: int, thumb_width: int) -> None:
    thumbs = []
    font = ImageFont.load_default()
    label_h = 24
    pad = 10
    for img_path in images:
        img = Image.open(img_path).convert("RGB")
        ratio = thumb_width / img.width
        thumb_h = max(1, int(img.height * ratio))
        img = img.resize((thumb_width, thumb_h), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb_width, thumb_h + label_h), "white")
        tile.paste(img, (0, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((4, thumb_h + 4), img_path.name, fill=(20, 30, 45), font=font)
        thumbs.append(tile)

    rows = math.ceil(len(thumbs) / columns)
    tile_w = thumb_width
    tile_h = max(t.height for t in thumbs) if thumbs else 1
    sheet = Image.new("RGB", (columns * (tile_w + pad) + pad, rows * (tile_h + pad) + pad), "white")
    for idx, tile in enumerate(thumbs):
        x = pad + (idx % columns) * (tile_w + pad)
        y = pad + (idx // columns) * (tile_h + pad)
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--thumb-width", type=int, default=360)
    args = parser.parse_args()

    images = iter_images(args.image_dir)
    if not images:
        raise SystemExit(f"No images found in {args.image_dir}")
    out = args.out or (args.image_dir / "contact_sheet.jpg")
    make_sheet(images, out, args.columns, args.thumb_width)
    print(f"[sheet] {len(images)} images -> {out}")


if __name__ == "__main__":
    main()

