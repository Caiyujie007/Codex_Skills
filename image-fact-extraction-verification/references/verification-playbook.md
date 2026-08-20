# Verification Playbook

## Evidence Model

For each extracted field, retain this mental or written record:

- source image and page/frame
- bounding box or crop location
- Apple Vision candidate and confidence
- Tesseract candidates from different page-segmentation modes
- normalized candidate
- status: confirmed, ambiguous, or unreadable

The final value must come from the source region. Engine agreement is supporting evidence, not a replacement for looking at the image.

## Layout Reconstruction

1. Detect the table or list boundary and visible row/column separators.
2. Cluster OCR boxes into lines by vertical overlap and baseline proximity.
3. Assign fields to columns by their horizontal centers and header positions.
4. Preserve empty cells. Do not shift later fields left merely because OCR missed one cell.
5. Handle wrapped text as one logical record only when its geometry shows continuation.

For forms or diagrams, bind each value to the nearest visible label or enclosure instead of using raw reading order.

## Resolving Disagreements

Use this order:

1. Inspect the original at high zoom.
2. Compare the field's shape with neighboring glyphs in the same image, especially `0/O`, `1/I/l`, `2/Z`, `5/S`, `6/8`, decimal points, and minus signs.
3. Crop tightly with a small margin and rerun Apple Vision and Tesseract.
4. Try both a block-oriented and sparse-text Tesseract pass.
5. Confirm using row/column position and visible separators, but never derive the value from an expected sequence.
6. If still unresolved, output `待确认` and preserve the competing candidates in notes.

## Validation Without Inference

Permitted checks:

- duplicate identifiers
- malformed numbers
- unexpected blank cells
- row-count mismatch
- column shift
- unit consistency
- impossible parsing caused by OCR punctuation

These checks identify fields needing review. They do not authorize automatic correction.

## Artifact Guidance

- XLSX: identifiers as text, numeric values as numbers only after confirmation, visible headers, filters, frozen header, and a status column when needed.
- CSV/TSV: UTF-8, explicit headers, no silent type coercion.
- JSON: preserve raw strings and include status/evidence keys when ambiguity matters.
- Markdown/text: use tables only when the source has stable columns; otherwise preserve line structure.
