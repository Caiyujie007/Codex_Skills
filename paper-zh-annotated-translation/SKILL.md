---
name: paper-zh-annotated-translation
description: Use when translating an English technical or academic paper PDF into a Chinese paper-style annotated HTML, preserving the original paper layout and typography style as much as practical, translating the main content, and adding short principle explanations after key technical points.
---

# Paper Chinese Annotated Translation

Use this skill when the user wants an English technical paper PDF turned into a Chinese annotated HTML reading version, especially when they ask for English-to-Chinese translation, a Chinese paper HTML, layout close to the original paper, or principle explanations after key technical points.

## Output Contract

- Treat the English PDF as the source of truth. The input is the source PDF plus the user's reading needs; the generated Chinese HTML is the deliverable.
- Produce HTML only. Do not generate or keep a PDF output as part of this skill.
- Preserve the original PDF.
- The Chinese HTML must preserve the source paper's visual paper style as much as practical: page size, text block width, column layout, typography density, title/author/front-matter treatment, section order, figure/table proximity, captions, and references. Match the input PDF's format rather than forcing a single house style.
- Translate the main technical content in paper order. Do not silently turn the paper into a loose summary if the user asked for translation.
- The result should be a translated paper, not a condensed guide. The source-mapped English provenance should cover most of the source paper's main content; a result whose EN source-map only covers a small fraction of the PDF text is under-translated even if every individual EN snippet is exact.
- Preserve source granularity unless there is a clear readability reason not to: source paragraphs should normally become translated paragraphs, source captions should become translated captions, and source tables should remain tables or table-like blocks. Do not merge several paper paragraphs into one long Chinese summary paragraph.
- Preserve source typographic emphasis and section style when it carries paper structure: bold abstract text, italic subsection headings, bold/italic keywords, table header weight, and emphasized technical terms should remain visually analogous in the Chinese HTML.
- Preserve source front-matter fields. If the paper has `Abstract` and `Index Terms`, the Chinese version should keep both, normally as `摘要` and `索引词` / `索引`, with their source emphasis and placement preserved.
- Treat translated front-matter fields as source text. Abstract paragraphs, index terms / keywords, paper notes, captions, and table notes should have EN provenance unless they are translator-authored notes.
- For a multi-page academic paper with a strong page/column rhythm, preserve that rhythm with semantic page-like HTML containers. The containers should hold translated text, captions, explanations, and figures as real HTML, not full-page screenshots.
- Add principle explanation paragraphs after key technical points, figures, tables, or sections. Explanations may be short for ordinary context, but technically central sections need enough explanatory density to help the reader understand the mechanism, motivation, and hardware/software intuition without replacing the translation. Do not let script-assisted generation collapse the output into a sparse set of notes.
- Prefer a single self-contained HTML: embed CSS, small inline interaction code, and cropped figure/table images directly in the HTML.
- Do not use full-page PDF screenshots/previews as body content, page backgrounds, or the primary layout mechanism.
- Do not leave intermediate extraction folders, asset folders, audit scratch files, or one-off generator scripts beside the delivered HTML.
- Before writing the final HTML/CSS, make a small source-layout inventory: which front-matter blocks are full-width, which section headings are single-column vs page-wide, and which figures/tables are single-column vs full-width. Use that inventory to assign classes in the HTML. Do not let generic CSS decide these structural choices.

## Default Behavior For Short User Prompts

This skill must work when the user only says something like: "Use Paper Zh Annotated Translation to translate paper.pdf".

In that case, infer and apply the full workflow:

- Use the named PDF as the only source of truth.
- If the named PDF path does not exist, do not invent a source file or silently switch papers. If the parent directory exists and exactly one PDF has a strong normalized filename-token match to the user's path, use that PDF and report the resolved filename. Otherwise ask for clarification.
- Do not inspect or reuse existing translated HTML, backup HTML, old generated drafts, or previous outputs as source material unless the user explicitly asks for revision of that existing file.
- If the user does not specify an output path, place the final HTML next to the PDF. Use a concise source-derived name such as `<paper_stem>_cn_annotated_translation.html`; if the paper title has a clear short system/product name, that short name may be used to keep the filename readable.
- Generate one final self-contained annotated HTML.
- Preserve the source PDF's layout style.
- Add source EN hover/click provenance and translator-authored principle explanations.
- Run practical quality checks and remove temporary extraction/build artifacts.

Do not depend on the user repeating the detailed constraints from this skill in the prompt.

## Script Boundary

This skill includes scripts again, but scripts are mechanical helpers only. They must not define the final document structure, CSS aesthetic, translation granularity, explanation placement, or paper layout.

Use scripts for:

- PDF reference extraction and page previews.
- Figure/table cropping and asset embedding.
- EN provenance coverage/exactness checks.
- Machine-translation proofreading reports.
- Static HTML sanity checks.

Do not use scripts as:

- a full HTML generator,
- a replacement for translation judgment,
- a layout engine that changes the document away from the source paper style,
- a reason to optimize for audit output over reading quality.

If a script-generated or script-influenced result is less readable, less paper-like, or less explanatory than a manually arranged annotated paper, revise the HTML. Passing scripts is necessary evidence, not the quality definition.

## Script Toolkit

Bundled scripts live under `scripts/`. Use them when they help, but keep final structure under the rules in this `SKILL.md`.

| Script | Purpose | Typical use |
|---|---|---|
| `scripts/extract_pdf_reference.py` | Capture PDF metadata, source text, layout text, and page preview images for visual reference only. | `python scripts/extract_pdf_reference.py paper.pdf --out-dir paper_ref --dpi 144` |
| `scripts/crop_pdf_figure.py` | Crop a high-resolution PNG from the original PDF using page and point bbox, with padding and optional data URI output. | `python scripts/crop_pdf_figure.py paper.pdf --page 3 --bbox-pt 72,120,540,360 --padding-pt 8 --out fig3.png` |
| `scripts/embed_assets_as_data_uri.py` | Embed local images, CSS files, scripts, and CSS `url(...)` assets into a portable single HTML. | `python scripts/embed_assets_as_data_uri.py draft.html --out final.html` |
| `scripts/audit_en_coverage.py` | Check translated source-paper paragraphs/captions have `data-en-id` and source-map entries, ignoring intentional notes/explanations. | `python scripts/audit_en_coverage.py final.html` |
| `scripts/audit_en_source_exactness.py` | Check every `EN` source-map value appears in source PDF text after only mechanical normalization. It uses strict, dash-normalized, chunk-order, and high-threshold token-coverage checks to tolerate PDF extraction debris without accepting rewritten English. | `python scripts/audit_en_source_exactness.py final.html --source-text paper_ref/source.raw.txt` |
| `scripts/audit_translation_reference_mt.py` | Optionally build a machine-translation proofreading report. It never edits the HTML. | `python scripts/audit_translation_reference_mt.py final.html --provider google --out mt_audit.json` |
| `scripts/check_paginated_html.py` | Run static checks for self-contained HTML, image refs, source-map JSON, EN/map counts, and encoding hazards. | `python scripts/check_paginated_html.py final.html --require-data-images` |

PDF page previews produced by scripts are visual references for layout comparison and crop positioning. Do not embed whole-page previews as translated body content.

## Core Workflow

1. Inspect the source PDF:
   - Use available PDF tools or `extract_pdf_reference.py` to understand page size, page count, column layout, title area, figures, tables, and reading order.
   - Extract text carefully enough to preserve paragraphs, headings, captions, citations, equations, numbers, and technical names.
   - Treat rendered pages as reference artifacts only.
2. Build the translation HTML:
   - Write semantic paper-style HTML from the source text: translated paragraphs, headings, captions, tables, and explanation blocks.
   - Keep title, authors, abstract, section headings, figures, tables, captions, references, and appendices in paper order.
   - Use paper-style typography and match the original column structure: one-column sources should stay one-column, two-column sources should stay two-column, and unusual paper layouts should be followed as closely as practical.
   - Preserve the source-specific visual system. IEEE two-column papers, magazine-style papers, digest papers, technical reports, manuals, and short workshop papers can have different title bars, author grids, section markers, colored rules, and figure spans; do not force them all into one generic IEEE-like template.
   - Preserve the source's local section presentation. If the source abstract is an inline bold `Abstract—...` paragraph, render it as an inline bold `摘要——...` paragraph rather than converting it into a separate centered heading plus normal-weight text.
   - When the source abstract or another structural paragraph is bold, the entire corresponding Chinese paragraph should use a comparable visible weight, not only the label word. Avoid weakening a bold source abstract into a lightly emphasized or normal-weight paragraph.
   - Preserve the source's section-heading flow. In compact two-column papers, section headings often live inside the current column; do not globally force `h2 { column-span: all; }` unless the source heading itself spans the page. Wrong column-spanning can make one section begin at a different visual boundary from the original PDF.
   - Implement section span explicitly: use normal in-column headings by default, and add a separate class such as `.heading-wide` only to headings that are visibly page-wide in the source PDF. Do not write global selectors such as `h1, h2 { column-span: all; }`, `h2 { break-before: column; }`, or `h2 { break-after: avoid; column-span: all; }` that silently change every section boundary.
   - Keep nearby section transitions local. If the source has `II. Motivation` near the bottom of a left column and `I. Introduction` near the bottom of the prior page/column, the HTML should preserve that local flow instead of lifting every major heading to a full-width separator.
   - Preserve technical terms where helpful, using Chinese plus English on first use.
   - Keep Chinese paragraph boundaries readable. Do not mechanically mirror every extracted PDF line, sentence fragment, or column artifact.
   - Preserve the stable reading shape of a translated paper: compact title block, compact abstract, dense two-column flow, figures close to their related text, and no website-like card layout.
   - For a two-column source paper, verify that each rendered body region actually uses both columns when the source does. Do not produce a page where abstract or main body text fills only the left column while the right column remains blank unless the source PDF also does that.
   - For long two-column papers, do not place the whole paper body in one unbounded `article.columns`. Browser multi-column layout can balance columns across the entire article, making the left side show later sections while the right side still shows earlier sections. Split the content into source-page-like or natural page-height chunks so each screen/page preserves local source order. A multi-page paper translation should normally scroll as a sequence of paper pages or page-like chunks, not as one continuous web article.
   - Do not compress a section by paraphrasing away source claims. If the paper spends several paragraphs on a mechanism, the Chinese version should also contain several source-mapped translated paragraphs plus optional explanations.
   - Keep enough source-mapped English coverage to prove this is a translation. As a practical sanity check, the total English token count in `en-source-map` should normally be at least about half of the extracted source PDF token count, and often much higher for short technical papers. If it is far below that, the output is probably a summary and must be expanded.
3. Add principle explanations:
   - Put each explanation immediately after the paragraph, figure, table, or section it clarifies.
   - Keep explanation boxes modest and paper-like, not blog-style callouts.
   - Treat explanations as translator-authored annotations, not source-paper translations.
   - Increase explanation density in technically central sections.
4. Add source provenance:
   - Add small `EN` hover/click provenance for translated source-paper text.
   - The English shown by `EN` must be the original PDF source text after only mechanical cleanup, not AI paraphrase, generated English, or back-translation.
5. Handle figures and tables:
   - Crop figures/tables from the original PDF with enough boundary padding.
   - Embed cropped images directly in the HTML when portability is desired.
   - Rebuild simple tables as HTML when reasonable.
6. Audit and validate:
   - Run source coverage and source exactness checks when practical.
   - Treat EN source exactness as a blocking provenance check. If the strict checker reports failures that appear to be PDF extraction artifacts, use the script's mechanical loose matching or manually inspect and fix/classify them; do not simply skip the check in the final report.
   - Treat EN source coverage as a blocking translation-completeness check. Exact English snippets are not enough; the source-map must also be large enough to cover the source paper's main content.
   - Check translation fidelity against the source English.
   - Use independent machine translation only as a proofreading reference when appropriate; never auto-replace the Chinese with machine output.
   - Open the HTML and inspect layout, figures, captions, source provenance, encoding, and final file cleanliness before delivery.
   - Inspect the first screen and several later screens in a browser. The page should look like a translated paper, not a generated report; section order should be visually local, figures should not appear before their nearby discussion, and the title/front matter should read naturally.
   - If direct `file://` browser inspection is blocked by local security policy, use a temporary local HTTP server or another headless browser path that can render the file, then shut the server down and remove any scratch files. Serving the generated HTML through `localhost` solely for inspection is the recommended validation path, not an unsafe bypass. Do not simply skip visual inspection because `file://` failed unless the user explicitly told you not to start a local server or browser.
   - Record a compact final quality note for yourself or the final response: output path, EN coverage status, EN source exactness status, source-map token coverage ratio or equivalent completeness check, self-contained image/resource check, layout inspection result, and temp cleanup status.
7. Clean up:
   - Remove temporary extraction/reference/image staging directories, machine-translation scratch files, and one-off generator scripts.
   - Treat leftover directories with names like `_figures`, `_assets`, `assets_tmp`, `_tmp`, `_ref`, `_extract`, `_crop`, or draft build folders beside the PDF as cleanup failures unless the user explicitly requested persistent assets.
   - Keep only the source PDF, final HTML, and user-requested persistent outputs.

## Original Paper Layout Fidelity

The Chinese HTML should feel like a translated version of the original paper, not a new website about the paper.

- Preserve the source paper's layout style as much as practical:
  - same broad page size and margins
  - same one-column or two-column body structure
  - same important text emphasis, including bold abstract/body lead-in styles
  - same abstract and index-term/front-matter structure
  - similar title block hierarchy
  - similar section/subsection style
  - similar section-heading column span and visual boundary
  - same figure/table column span whenever practical: single-column figures stay single-column, full-width figures stay full-width
  - similar figure/table placement relative to the text
  - compact paper captions
  - references near the end
- For two-column papers, default to a continuous two-column paper flow rather than a card-based web page. For one-column papers, keep a one-column paper flow. For reports, manuals, or papers with unusual layouts, preserve the source layout's intent instead of forcing the two-column template.
- If the PDF is clearly a slide deck or presentation rather than a paper, report that classification and preserve the slide-like source style if the user still wants a translation. Do not use slide-deck behavior as evidence that this paper-translation skill is working well for academic papers.
- Do not add web-app furniture such as navigation sidebars, metadata dashboards, glossary panels, hero sections, or large summary cards unless the user explicitly asks.
- Do not over-modernize the typography. The goal is not a beautiful blog post; the goal is a readable Chinese paper that still looks like the source paper.
- If exact visual mimicry conflicts with Chinese readability, make a small readability adjustment while keeping the paper's overall style.

Structural span rules are source-derived, not content-derived:

- A major section heading is not automatically full-width merely because it is an `h2`.
- A figure/table is not automatically full-width merely because it is detailed, important, or easier to read when enlarged.
- A principle explanation is not automatically full-width merely because it is translator-authored.
- Use full-width only when the corresponding source element is full-width, or when a tiny readability exception is explicitly justified and does not disturb nearby source order.
- After rendering, compare at least the first two pages against PDF previews: abstract/front matter, the first major section transition, and the first architecture figure should occupy the same broad column/page roles as the source.

## Stable HTML Layout Template

For a normal paper translation request, prefer this semantic structure, adapting `article.columns` to the source PDF's actual column style:

```html
<body>
  <div class="en-popover" id="enPopover" role="tooltip" aria-hidden="true"></div>
  <main class="paper source-paper">
    <section class="paper-page first-page">
      <header class="title-block">...</header>
      <article class="columns">...</article>
    </section>
    <section class="paper-page">
      <article class="columns">...</article>
    </section>
  </main>
</body>
```

Recommended defaults for a letter-size two-column source paper. Apply these only when the source PDF is actually a compact two-column paper:

- `html, body` at about `10pt`, with paper fonts and `line-height` around `1.28` to `1.36`.
- `main.paper.source-paper` centered on the screen.
- `.paper-page` about letter width with source-like margins; if source-page rhythm matters, give each page/page-like chunk a bounded min-height or fixed page-height that prevents whole-document column balancing.
- `article.columns { column-count: 2; column-gap: 0.24in to 0.30in; }`.
- Put body text sizing on the document or paper flow, not only inside `article.columns`, so title/front matter and body remain visually coherent.
- Paper fonts such as `"Times New Roman", "SimSun", "Songti SC", serif`.
- Justified paragraph text with modest indentation.
- Major headings compact and close to the paper's source style; subsection headings modest and close to the paragraph they introduce.
- Do not make all major headings page-wide by default. Use `column-span: all` only for title/front matter, references, or headings that are page-wide in the source PDF.
- Prefer CSS classes over element selectors for structural spanning. Good: `.title-block, .front-note, figure.wide { column-span: all; }`. Risky: `h2 { column-span: all; }`, `section { break-before: always; }`, or `figure { column-span: all; }`.
- Figures use `figure` / `figcaption`, `break-inside: avoid`, and `figure.wide { column-span: all; }` only for figures that are full-width or cross-column in the source PDF. Do not promote a source single-column figure to full-width merely because the cropped bitmap is large, detailed, or easier to read.
- Explanation boxes are compact, paper-note-like blocks inside the flow.
- `EN` chips are small and visually secondary, preferably one per natural paragraph/caption/table note.
- Multi-column flow must preserve local reading order on screen. After rendering, check that the right column at a given vertical position contains nearby continuation text, not content from a far later section caused by whole-document column balancing. If this happens, split the article into source-page-like chunks, fixed-height page chunks, or other natural chunks that preserve local order while keeping a paper-like appearance.
- Multi-column flow must also fill columns like a paper. Avoid CSS or block structure that leaves the right column empty for long stretches. In ordinary continuous HTML with auto height, `column-fill:auto` can cause content to fill only the first column; omit `column-fill` or use the browser's default/balanced behavior unless you are using fixed-height page/section boxes and have visually verified both columns.
- Do not wrap every short section in its own independent two-column container if that makes each section restart in the left column and wastes the right column. Prefer one continuous `article.columns` flow, or a small number of natural chunks whose height and balancing preserve the source PDF's page/column rhythm.
- For papers longer than a few pages, a single continuous `article.columns` flow is risky because the browser may balance columns across the entire paper. Prefer a sequence such as `<section class="paper-page columns">...</section>` or `<section class="flow-chunk columns">...</section>` where each chunk roughly corresponds to a source page, source page region, or a bounded amount of nearby text. These chunks are semantic HTML containers, not embedded PDF screenshots.
- Keep each bounded two-column chunk close to one source page or one local source-page region. A chunk that contains several major headings, such as `I`, `II`, and `III` together, is usually too large and can still produce misleading column balancing. Split it before the next major section or at a nearby figure/table boundary.

Avoid this default shape unless the user explicitly asks for fixed paginated preview behavior:

```html
<div class="viewer">
  <article class="page">...</article>
</div>
```

Large page cards, drop shadows, slide-like canvases, and fixed app-like viewers tend to make the output less stable and less like the original paper.

If the generated result starts to look like a web article, reset toward this compact paper baseline:

```css
html, body {
  margin: 0;
  padding: 0;
  background: #fff;
  color: #111;
  font-family: "Times New Roman", "SimSun", "Songti SC", serif;
  font-size: 10pt;
  line-height: 1.32;
}
.paper { max-width: 7.42in; margin: 0 auto; }
.columns { column-count: 2; column-gap: 0.25in; }
p { margin: 0 0 0.055in; text-indent: 1.35em; }
```

Use `column-fill:auto` only for explicit fixed-height paginated layouts where the column height is defined and verified. It is usually wrong for a normal continuous reading HTML because it can create a visually single-column result inside a two-column container. Conversely, a single unbounded balanced multi-column container is also wrong for a long paper because it can place far-later sections in the left column while earlier continuation text sits in the right column. The robust default for long two-column papers is bounded source-page-like chunks or paper pages.

Use padding or a light screen background only when it improves on-screen readability without making the paper look like a card. Avoid default `box-shadow` on the paper.

## Visual Style And Front Matter

Default to a quiet annotated-paper style.

- Use a clean paper canvas: pure white content area, dark ink text, restrained borders, and generous but not decorative margins. A very light neutral screen background is optional; the paper itself should not look like a floating web card.
- Do not use cream, ivory, beige, tan, pale yellow, sepia, parchment, or "aged paper" backgrounds. Avoid yellow-tinted off-whites such as `#fff8e1`, `#fffbe6`, `#fdf6e3`, `#faf3dd`, and `#f5ecd7`.
- Recommended defaults: content/page background `#ffffff`, text around `#111827` / `#172033`, muted blue accent around `#1f4f8f` / `#2563eb`, and explanation background around `#f3f6fa` / `#eef5ff`. Avoid decorative paper shadows by default.
- Explanation boxes should look like margin notes in a paper: modest background tint, thin border, compact spacing, and clear user-facing label `原理说明`. Do not label these blocks as `原理注释`, `译者注释`, `Translator note`, or other variants unless the user explicitly asks for different wording.
- Keep principle explanation colors stable across generated papers unless the source paper has an overwhelming reason to adapt. Use this baseline visual language:
  - background: `#f3f6fa` or `#eef4fb`
  - accent/border: `#1f4f8f` or `#2563eb`
  - text: `#1f2937` or `#233449`
  - label color: same blue accent as the border
  - border style: preferably a left rule such as `border-left: 2px solid #1f4f8f`
  - avoid neutral gray-only explanation boxes such as `border-left: 2px solid #555` with `background: #f8f8f8`; they make outputs across papers look unstable.
- Keep figure/table captions compact and close to their figures/tables.

Treat the beginning of the document as paper front matter, not a generic web-page hero:

- Put the translated paper title in a centered `title-block` near the top.
- Translate the title faithfully and naturally; do not turn it into a marketing slogan, do not introduce awkward punctuation that makes the title wrap badly, and prefer a concise Chinese title plus a subtitle containing the original English title when helpful.
- For titles with a product/system name followed by a colon, keep the name before the Chinese colon and translate the subtitle as a natural Chinese paper title. Prefer natural Chinese technical-paper wording over awkward literal phrasing.
- Preserve author names in the source spelling and source order.
- Preserve affiliation/institution lines when present.
- Add a short translator note after title/authors/affiliation and before the abstract when useful.
- Do not attach `EN` chips to title, authors, affiliation, or translator notes unless the user explicitly asks.
- Start the translated abstract immediately after the front matter. Do not put translator-authored principle explanation boxes before the abstract.

## Principle Explanation Density

Principle explanations are part of the deliverable, not decoration. Their density should follow the source paper's technical density.

For technically central sections:

- Add explanation near every major mechanism, module, figure, or non-obvious design tradeoff.
- Explain what problem the mechanism solves, how it works conceptually, why the authors likely chose it, and what assumption or limitation matters.
- Connect adjacent mechanisms when the paper's meaning depends on their interaction.
- Prefer several focused explanation boxes over one distant summary.
- Use general language that fits the paper's domain. Do not hard-code project-specific terminology unless it is actually in the source paper.
- For a short-to-medium technical architecture paper, a final result with only a handful of explanation blocks is usually under-annotated. Central architecture papers often need explanation near the abstract/design philosophy, each major architecture figure, each central module, each interconnect/dataflow/synchronization mechanism, and each evaluation tradeoff. The exact count depends on the paper, but explanation density should track technical density rather than page count alone.
- Compare explanation coverage against the source outline before delivery. If a key section has multiple non-obvious mechanisms but no explanation, add focused notes there.

For less central background, related work, or straightforward evaluation text, shorter explanations or no explanation may be appropriate. The goal is enough guidance where the paper is hardest and most important.

Keep explanation provenance clear:

- Do not attach `EN` chips to principle explanations.
- If an explanation includes a claim directly translated from the paper, split it out into a source-mapped translated paragraph first, then add the translator-authored explanation separately.
- Avoid inventing unsupported facts. When an explanation is an engineering inference from the source text, phrase it as an interpretation rather than a paper claim.

## Source Provenance And EN Chips

Treat `EN` chips as source provenance, not as decoration.

- Every translated source-paper body paragraph, figure caption, table caption, and source-derived table note should have a small `EN` chip.
- Translated front matter that came from the source PDF, including Abstract and Index Terms / Keywords, should also have `EN` chips. Translator notes and principle explanations should not.
- A `data-en-id` attribute alone is not enough. The reader needs a visible, focusable `EN` chip/button next to the translated source text so hover/click lookup works. The chip may be written statically in the HTML or inserted at load time by a small script that visits every `[data-en-id]`.
- On hover/focus, show the English source temporarily.
- On click, `Enter`, or `Space`, pin/unpin the source popover.
- `Esc` or clicking outside closes a pinned popover.
- Use document-level event delegation when practical.
- Give chips keyboard focus and a useful `aria-label`.

The English shown by `EN` must be verbatim source text after only mechanical cleanup:

- Joining PDF line wraps is allowed.
- Repairing line-break hyphenation is allowed: `regis-\nter` becomes `register`.
- True hyphenated terms keep the semantic hyphen: `8-\nbit` becomes `8-bit`.
- Normalizing ligatures and whitespace is allowed.
- Do not paraphrase, summarize, back-translate, reorder clauses, remove citations, or fill missing context from memory.
- If an exactness audit fails, first assume the source-map value or extraction normalization needs repair. Only classify a failure as a false positive after confirming the displayed English is still original PDF text after allowed mechanical cleanup.

Text without `EN` must be intentionally non-source text, such as a translator note, principle explanation, metadata note, or reference-list note. If a Chinese paragraph is partly translation and partly explanation, split it into a source-mapped translated paragraph plus a separate explanation block.

## Translation Fidelity Audit

Before final delivery, audit source-mapped Chinese against the English source. When useful and appropriate, use independent machine translation as a proofreading reference, not as an automatic replacement.

Check at least:

- Numbers, units, capacities, bandwidths, latency, dimensions, percentages, table values, and ranges.
- Equations, symbols, citations, section/table/figure references, and parenthesized abbreviations.
- Domain acronyms, block names, product names, protocol names, and alphanumeric technical tokens.
- Suspicious token merge/split errors.
- Missing source claims, invented claims, over-specific claims, or translator summaries that should have been direct translations.
- Subject/object reversal, condition reversal, negation loss, comparison reversal, and causal relationship changes.
- Captions and table titles.

Edit only high-confidence translation errors confirmed against the English source.

## Figure And Table Handling

For complex PDF figures:

1. Determine each figure's source page and crop area.
2. Crop from the original PDF at high resolution, usually around 288-300 DPI.
3. Leave enough padding for arrows, legends, thin lines, and labels near the figure boundary.
4. Embed the generated PNG as a `data:image/png;base64,...` URI when a single portable HTML is desired.
5. Set the visible CSS width in `pt` or `in` to match the paper's original figure size.
6. Translate the figure caption in HTML.

When deciding HTML figure width:

- Use the source PDF layout as the authority.
- If a figure occupies one source column, keep it inside one HTML column even if the image is visually dense.
- If a figure spans both source columns or is placed as a page-wide figure/table, mark it as wide/full-width.
- When uncertain, compare the rendered HTML against the PDF page preview before delivery and choose the closer source-layout match.

For simple tables, prefer reconstructing them as HTML tables instead of screenshots. If a table is too complex to reconstruct, crop only the table body and write a translated table caption in HTML.

Avoid these paths unless the user explicitly asks:

- Do not embed full-page PDF screenshots/previews as translated body content, page backgrounds, or the main page layout.
- Do not inline complex PDF-derived SVGs with thousands of glyph paths into the HTML.
- Do not add invisible SVG text layers only to make figure text searchable/selectable.
- Do not keep external figure folders for the final answer when the user asked for a portable single HTML.

## Source-Page-Like Layout

For multi-page academic papers, source-page-like semantic layout is often the most stable way to preserve the original PDF style. It is allowed and usually preferred when the source paper itself has clear page and two-column rhythm.

When using source-page-like layout:

- Keep translated text, captions, tables, explanations, and EN chips as real HTML.
- Do not use full-page screenshots as body content or backgrounds.
- Use source-like page dimensions, such as `8.5in x 11in` for letter, or page-like chunks that preserve similar visual boundaries.
- Use fixed or bounded two-column geometry inside each page/chunk.
- If the viewport is too narrow, allow horizontal scrolling instead of reflowing the paper.
- Wait for embedded images to load before paginating.
- Verify that figures and captions are not clipped by page or column boxes.
- Avoid decorative page shadows, thick borders, colored page chrome, and UI controls.

For one-page papers, short notes, or source PDFs that are themselves continuous one-column reports, a continuous flow can still be appropriate. The layout choice must follow the source PDF.

## Encoding And File Writes

Be careful on Windows with Chinese HTML.

- Write the final HTML as UTF-8.
- Avoid casual encoding-changing rewrites of large Chinese HTML.
- After any mechanical rewrite, search for the Unicode replacement character and fix the file before continuing.
- Validate embedded JSON source maps after edits.

## Final Cleanup

Before delivery, remove temporary implementation artifacts:

- source extraction folders
- page preview folders
- figure crop work folders
- figure or asset staging folders such as `_figures`, `_assets`, `assets_tmp`, `_tmp`, `_ref`, `_extract`, or `_crop`
- machine-translation scratch files
- one-off generator files such as `generate_*.py`, `build_*.py`, and `make_*.py`

Keep only the source PDF, the final HTML, and any persistent outputs explicitly requested by the user.

## Validation Checklist

Before finishing:

- The HTML opens and renders correctly.
- The output is HTML only.
- The original PDF is preserved.
- The result looks like a translated version of the original paper, not a blog post, dashboard, slide deck, or script-generated QA artifact.
- Page size, text block width, column layout, title block, section style, figure/table proximity, captions, and references are close to the source paper.
- Source typographic emphasis is preserved where it matters: for example, a bold source abstract remains bold in Chinese, rather than becoming normal body text with a new heading.
- Source front-matter is complete: abstract, index terms / keywords, author/affiliation notes, and captions are not dropped merely because they are short.
- Section headings obey the source PDF's column behavior. A heading that is single-column in the source should not become a page-wide break in the generated HTML.
- CSS does not contain broad selectors that force all major headings or all figures to span columns. Structural spans are assigned by explicit source-layout classes.
- Two-column sources visibly render as two-column text on the first paper page and in later technical sections. The right column is not accidentally blank because of `column-fill:auto` or per-section multi-column wrappers.
- The first screen/page does not show far-later sections in the left column while earlier continuation text remains in the right column. If this happens, the body is probably one unbounded balanced multi-column container and must be chunked.
- For a multi-page two-column paper, the first generated page/screen should have a similar section rhythm to the original first page. It should not show section `III` on the first page if the source first page only reaches `II`, unless the translation length makes a small unavoidable shift.
- Source-derived front matter such as `索引词` / `关键词` has EN provenance, not only the abstract paragraphs.
- Figure/table column span matches the source PDF whenever practical; source single-column figures are not widened into full-width figures just for readability.
- Whole-page PDF previews are not used as body content or backgrounds.
- The page background is white/neutral, not yellow, cream, beige, sepia, or parchment-like.
- Paragraphs are not over-fragmented by PDF extraction artifacts or one-`EN`-chip-per-sentence mechanics.
- Translated source-paper body paragraphs, figure captions, and table captions have `EN` chips unless intentionally classified as non-source text.
- `EN` hover/click shows original English source text, not generated English.
- Principle explanations do not have fake English provenance.
- The technically central sections have enough principle explanations.
- No known high-confidence translation errors remain.
- Figures are not clipped, collide with captions, or split awkwardly.
- Figure crops have enough boundary padding.
- Tables do not overflow columns.
- No Unicode replacement characters remain.
- Temporary directories and one-off generator files have been removed.
