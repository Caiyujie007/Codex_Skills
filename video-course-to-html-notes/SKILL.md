---
name: video-course-to-html-notes
description: Use when converting MP4/video lecture or screen-recorded slide courses into HTML study notes by extracting distinct PPT/slides, deduplicating annotation-only frames, generating per-slide screenshots plus Chinese "这是什么意思？" explanations, chapter index pages, and validation checks.
---

# Video Course To HTML Notes

Use this skill when the user wants MP4 lessons, screen-recorded PPT courses, or lecture videos turned into readable HTML notes.

The output should be useful when the user cannot conveniently watch video: each real slide appears once, followed by a clear "这是什么意思？" explanation.

## Core Principle

Extract **distinct teaching slides**, not every video frame change.

Do not split these into separate slides:

- the same PPT page with red pen marks added during explanation
- mouse movement, playback controls, cursor overlays, or short occlusions
- brief pause frames or small compression/color changes

Prefer the cleanest representative image for each slide. If a clean image is unavailable, choose the least obstructed frame.

## Output Shape

For a chapter directory containing videos:

```text
chapter_dir/
  README.html
  01_lesson_name.html
  02_lesson_name.html
  _assets/
    01_lesson_name/
      slide_01_0000s.jpg
      slide_02_0123s.jpg
```

Use relative paths in HTML. Do not embed all images as base64; large HTML files become slow to browse.

## Workflow

1. Inspect videos and target directory.
2. Extract candidate frames from each MP4.
3. Deduplicate frames into real slides.
4. Make contact sheets and inspect them before writing final HTML.
5. Generate one HTML per video.
6. Add or update `README.html` as the chapter index.
7. Validate every generated HTML.

Useful helper scripts are in `scripts/`. Read or run only the ones needed:

- `extract_candidate_frames.py`: sample frames from MP4 files.
- `make_contact_sheet.py`: build image contact sheets for manual slide review.
- `render_course_html.py`: render HTML from a JSON lesson spec.
- `validate_course_html.py`: verify images, slide counts, stale templates, mojibake, and absolute paths.

Script assumptions: `extract_candidate_frames.py` requires `ffmpeg` on `PATH`; `make_contact_sheet.py` requires Python 3 with Pillow installed.

## Explanation Rules

Write the explanation as if the user had sent that single slide and asked: "这是什么意思？"

Use this scale:

- Title slide: briefly say what this lesson will cover and why it matters.
- Ordinary technical slide: explain the visible bullets, key terms, intuition, and local context.
- Complex concept slide: add an example, counterexample, formula interpretation, or engineering consequence.
- Tool/list/table slide: do not memorize every row; explain what the table or tool category is trying to teach.

Avoid shallow or template-like text. Never include filler such as:

```text
这一条可以作为该页主题的一个具体表述来读。
```

OCR is only an aid. Do not paste OCR noise, mojibake, or hallucinated bullet text into the HTML.

## Deduplication Guidance

Use automatic similarity as a first pass, then inspect contact sheets. For slide videos, false positives and false negatives are common.

When deciding whether two frames are one slide:

- Same title and same bullet layout usually means same slide.
- Red pen/circle/underline additions usually mean same slide.
- A newly revealed bullet, animation step, or changed diagram may be a new slide if it changes the teaching content.
- If unsure, keep both during contact-sheet review, then merge manually after seeing context.

## Validation Checklist

Before finishing, verify:

- Every lesson HTML has `section` count equal to image count and answer count.
- Every `<img src>` resolves to an existing relative file.
- No absolute local paths are embedded.
- No mojibake or replacement characters remain.
- No old template phrases remain.
- Red-annotation duplicates are not preserved as independent slides unless the annotation itself is the subject.
- `README.html` links to every generated lesson HTML.

## HTML Style

Keep the HTML simple and durable:

- left navigation with slide anchors
- one screenshot per slide
- one "这是什么意思？" block per slide
- consistent CSS across lesson files
- readable text width and image width
- no heavy JavaScript unless the user asks for interaction
