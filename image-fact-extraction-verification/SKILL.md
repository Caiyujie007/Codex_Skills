---
name: image-fact-extraction-verification
description: Extract and verify factual text or structured records from screenshots, scans, photos, forms, tables, labels, diagrams, and other images using layout-aware multi-pass OCR, source-region evidence, cross-engine comparison, and explicit uncertainty. Use when image-derived text or facts must be accurate and auditable, regardless of whether the requested output is XLSX, CSV, JSON, Markdown, or plain text.
---

# Image Fact Extraction And Verification

Treat image reading as evidence extraction, not visual guessing. Preserve the distinction between what is visible, what OCR proposes, and what has been verified.

## Core Rules

1. Use only the source images named by the user unless the user explicitly authorizes other evidence.
2. Never infer missing values from numbering patterns, neighboring rows, another diagram, or domain expectations.
3. Keep source order and source grouping. Do not silently sort, merge, deduplicate, or normalize identifiers.
4. Mark unresolved fields as `待确认`; do not choose the most plausible candidate.
5. Preserve leading zeros, signs, decimal points, units, separators, and identifier punctuation.
6. Every extracted record must remain traceable to a page/image and approximate region or row.
7. Output format is a delivery choice. Accuracy and auditability come before Excel, CSV, JSON, Markdown, or prose formatting.

## Workflow

### 1. Inspect the source

- Open every source image at original resolution.
- Determine orientation, row/column structure, reading order, repeated headers, merged cells, handwriting, blur, and occlusion.
- Record the expected fields before transcription.

### 2. Generate independent OCR evidence

Run the bundled helper:

```bash
python3 "<skill-directory>/scripts/run_ocr_bundle.py" \
  "/absolute/path/to/source-image" \
  --output-dir "/tmp/image-fact-ocr"
```

Replace `<skill-directory>` with the directory containing this `SKILL.md`.

It produces:

- `vision.json`: Apple Vision text, confidence, and normalized bounding boxes.
- `tesseract_psm6.tsv` and `.txt`: block-oriented OCR.
- `tesseract_psm11.tsv` and `.txt`: sparse-text OCR.
- `manifest.json`: source hash and dimensions, engine status, commands, and errors.

Do not treat engine agreement alone as proof. Compare both results against the actual pixels.

### 3. Reconstruct layout

- Use bounding boxes and visual row boundaries to associate fields.
- Build a provisional record table with one source row/region per record.
- For crowded tables, crop ambiguous rows or cells and rerun both engines.
- Keep an evidence column during working analysis, even when the final output will omit it.

Recommended working columns:

```text
source | region_or_row | field_1 | field_2 | ... | confidence | evidence | status
```

### 4. Verify field by field

For each field:

1. Compare Apple Vision, Tesseract PSM 6, and Tesseract PSM 11.
2. Inspect the original pixels at high zoom.
3. Check character-shape confusions such as `0/O`, `1/I/l`, `2/Z`, `5/S`, `6/8`, decimal points, and Chinese numerals.
4. Confirm row association separately from character recognition.
5. Assign:
   - `已核对`: visually confirmed against the source.
   - `待确认`: source remains ambiguous.

Never upgrade confidence merely because a value fits a pattern.

### 5. Produce the requested artifact

- Preserve source row order.
- Use one value per cell/field.
- Keep units in a dedicated column when useful.
- For Excel/CSV, store identifiers as text when leading zeros are possible.
- Put uncertain values in the field as `待确认` or in a clearly paired status column.
- Do not include invented rows or values.

For XLSX output, use the spreadsheet skill or a structured spreadsheet library. Apply a restrained table style, freeze the header row, set readable widths, and avoid merged data cells.

### 6. Validate before delivery

- Record count matches the visibly identifiable source rows.
- No source row was skipped or duplicated.
- Each identifier is paired with the value from the same visual row.
- Units and decimal precision are consistent with the source.
- All `待确认` fields are easy to find.
- Reopen the generated artifact and verify values, ordering, and rendering.

## Escalation

If the image is too blurred, cropped, or compressed to support a reliable answer, say exactly which rows or fields are unreadable and request a higher-resolution crop. Do not complete them by inference.

Use [verification-checklist.md](references/verification-checklist.md) before delivery. Read
[verification-playbook.md](references/verification-playbook.md) when reconstructing complex
layouts or adjudicating ambiguous fields.
