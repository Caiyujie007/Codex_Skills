#!/usr/bin/env python3
"""Render a video lesson HTML file from a JSON spec.

Spec shape:
{
  "title": "01. Lesson",
  "video": "01. Lesson.mp4",
  "output": "01_lesson.html",
  "back_link": "README.html",
  "slides": [
    {"title": "Basics", "image": "_assets/01_lesson/slide_01.jpg",
     "paragraphs": ["...", "..."]}
  ]
}
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


STYLE = r"""
:root { --bg:#eef3f8; --paper:#fff; --ink:#102033; --muted:#607087; --line:#cbd8e6; --blue:#1f66b3; --nav:#101d2f; --shadow:0 10px 28px rgba(28,54,86,.10); }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:"Segoe UI","Microsoft YaHei",Arial,sans-serif; line-height:1.72; }
a { color:var(--blue); text-decoration:none; }
a:hover { text-decoration:underline; }
.layout { display:grid; grid-template-columns:270px minmax(0,1fr); gap:22px; width:min(1520px,calc(100vw - 44px)); margin:24px auto 56px; align-items:start; }
aside { position:sticky; top:20px; background:var(--nav); color:#dce7f7; border-radius:8px; padding:20px 16px; box-shadow:var(--shadow); max-height:calc(100vh - 40px); overflow:auto; }
aside h1 { margin:0 0 6px; color:#fff; font-size:20px; line-height:1.25; }
aside .sub { margin:0 0 14px; color:#aebbd0; font-size:13px; }
nav { display:grid; gap:6px; }
nav a { color:#dce7f7; padding:7px 8px; border-radius:6px; font-size:14px; }
nav a:hover { background:rgba(255,255,255,.08); text-decoration:none; }
header, section { background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:24px 28px; margin-bottom:20px; box-shadow:var(--shadow); }
.eyebrow { margin:0 0 8px; color:var(--blue); font-size:13px; font-weight:800; text-transform:uppercase; }
h2 { margin:0 0 12px; font-size:28px; line-height:1.25; }
header h2 { font-size:34px; }
p { margin:8px 0; }
.meta { color:var(--muted); font-size:13px; }
.slide img { display:block; width:100%; max-width:1180px; margin:0 auto; border:1px solid var(--line); border-radius:6px; background:#fff; }
.slide-title { display:flex; justify-content:space-between; gap:16px; align-items:baseline; margin-bottom:10px; }
.slide-title h2 { margin:0; font-size:24px; }
.slide-title .meta { white-space:nowrap; }
.answer { max-width:1180px; margin:18px auto 0; padding:18px 20px; border:1px solid #bdd2e8; border-left:5px solid var(--blue); border-radius:8px; background:#f7fbff; }
.answer h3 { margin:0 0 10px; font-size:21px; line-height:1.35; color:#12365f; }
.answer p { margin:9px 0; }
@media(max-width:900px){ .layout{display:block;width:min(100vw - 24px,900px)} aside{position:static;margin-bottom:16px;max-height:none} header,section{padding:20px} .slide-title{display:block} }
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render(spec: dict) -> str:
    title = spec["title"]
    video = spec.get("video", "")
    back = spec.get("back_link", "README.html")
    slides = spec["slides"]
    nav = "\n".join(
        f'        <a href="#s{i}">Slide {i} · {esc(slide.get("title", ""))}</a>'
        for i, slide in enumerate(slides, start=1)
    )
    sections = []
    for i, slide in enumerate(slides, start=1):
        paragraphs = "\n".join(f"          <p>{esc(p)}</p>" for p in slide.get("paragraphs", []))
        sections.append(
            f"""      <section id="s{i}" class="slide">
        <div class="slide-title">
          <h2>Slide {i}: {esc(slide.get("title", ""))}</h2>
          <p class="meta">{esc(Path(slide['image']).name)}</p>
        </div>
        <img src="{esc(slide['image'])}" alt="{esc(title)} slide {i}">
        <div class="answer">
          <h3>这是什么意思？</h3>
{paragraphs}
        </div>
      </section>"""
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} - PPT 逐页讲解</title>
  <style>{STYLE}</style>
</head>
<body>
  <div class="layout">
    <aside>
      <h1>{esc(title)}</h1>
      <p class="sub">PPT 逐页详细讲解</p>
      <nav>
        <a href="#top">课程信息</a>
{nav}
      </nav>
    </aside>
    <main>
      <header id="top">
        <p class="eyebrow">Video Course Notes</p>
        <h2>{esc(title)}</h2>
        <p>本页按“逐页截图问：这是什么意思？”的方式整理。只保留真正不同的 PPT 内容页；讲解过程中的批注重复页不单独保留。</p>
        <p class="meta">源视频文件名：{esc(video)} · <a href="{esc(back)}">返回本章索引</a></p>
      </header>
{chr(10).join(sections)}
    </main>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    out = args.out or Path(spec["output"])
    out.write_text(render(spec), encoding="utf-8")
    print(f"[render] {out}")


if __name__ == "__main__":
    main()
