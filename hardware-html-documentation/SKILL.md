---
name: hardware-html-documentation
description: Use when creating or refactoring self-contained HTML documentation for RTL, digital circuits, microarchitecture, NoC/interconnect demos, or verification notes. The document should first explain the principle clearly, optionally with diagrams or animation, then describe circuit interfaces, map key principle-level ideas to RTL implementation, and finally summarize verification cases, waveform expectations, and artifacts.
---

# Hardware HTML Documentation

Use this skill when the user wants self-contained HTML documentation for RTL, digital circuits, microarchitecture, NoC/interconnect demos, or verification notes. The document should teach the design, not merely list files.

## Script Toolkit

Use the bundled scripts for repeatable mechanical checks and skeleton generation. Keep engineering judgment in the document; use scripts to catch missing artifacts, stale links, malformed HTML, or missing waveform evidence.

| Script | Purpose | Typical use |
|---|---|---|
| `scripts/New-HardwareReadmeSkeleton.ps1` | Create a self-contained `README.html` skeleton with the preferred hardware-doc structure. | `powershell -ExecutionPolicy Bypass -File scripts/New-HardwareReadmeSkeleton.ps1 path/README.html -Title "Demo"` |
| `scripts/Test-SelfContainedHtml.ps1` | Check UTF-8, duplicate IDs, JSON script tags, title, and external `src/href` references. | `powershell -ExecutionPolicy Bypass -File scripts/Test-SelfContainedHtml.ps1 README.html` |
| `scripts/Test-CaseArtifacts.ps1` | Check per-case `sim.log`, WDB/WCFG, checker logs, PASS/HOLD, and obvious failure markers. | `powershell -ExecutionPolicy Bypass -File scripts/Test-CaseArtifacts.ps1 sim/cases -Required sim.log waves.wdb waves.wcfg waves.vcd` |
| `scripts/Get-WaveEvidenceSummary.ps1` | Extract `TRACE_SUMMARY` metrics from case logs for verification tables. | `powershell -ExecutionPolicy Bypass -File scripts/Get-WaveEvidenceSummary.ps1 sim/cases -RequirePositive vc_alloc_events` |
| `scripts/Test-SvgDiagrams.ps1` | Run lightweight sanity checks on inline SVG diagrams, such as missing `viewBox` or oversized arrow markers. | `powershell -ExecutionPolicy Bypass -File scripts/Test-SvgDiagrams.ps1 README.html` |

These scripts are aids, not substitutes for inspection. After an SVG/canvas/animation change, still render the HTML and visually inspect the changed region. After a verification-document update, still confirm that the selected waveform metrics match the behavior the case claims to prove.

## Document Shape

Prefer a single self-contained `README.html` unless the user asks for another filename.

Organize the document in this order:

1. **Scope and mental model**: what the design is, what it is not, and the few ideas the reader must understand.
2. **Principle first**: explain the architecture in a logically self-contained way before implementation details.
3. **Interfaces and topology**: describe ports, clock/reset, handshake semantics, packet/flit fields, routing fields, and block connections.
4. **Principle-to-RTL mapping**: map each key idea to the RTL state, register, context, combinational decision, or module that implements it.
5. **Verification**: list tests, what each proves, expected waveform observations, artifacts, and pass criteria.
6. **Tool or synthesis notes**: include only when relevant, after the conceptual and RTL sections.

## Explanation Style

- Teach with simple language, terms tables, compact pseudocode, and visuals when they help.
- Do not turn the document into a line-by-line code review.
- Do not copy long RTL blocks into the document.
- Do not hide the principle behind implementation names before the reader has the idea.
- Use text to explain a figure, not to replace it.

Good principle-to-RTL pattern:

```text
Principle: one output channel must keep a whole packet atomic.

RTL realization:
  out_busy[channel] records whether a packet owns this output channel.
  out_owner[channel] records which source owns it.

Pseudocode:
  if output is idle and HEAD handshakes:
    out_busy  = 1
    out_owner = selected_source

  if output is busy:
    keep selecting out_owner until TAIL handshakes
```

## Interface And RTL Mapping

For each important block, capture:

- Clock and reset convention.
- Producer/consumer direction.
- Handshake meaning, such as `valid/ready`, request/accept, or credit/consume.
- Packet boundary fields such as type, last, or tail.
- Routing or identity fields such as source, destination mask, ID, VC, channel, or tag.
- Local interfaces versus internal interconnect interfaces.
- Debug or observation signals, clearly marked as non-functional if applicable.

Use tables for interfaces and short pseudocode for connection topology.

## Visual Explanations

Prefer a visual when a topology, datapath, handshake, arbitration path, flow-control relationship, timing relationship, or dynamic process is clearer as a picture than as paragraphs. Good options include topology diagrams, module/block diagrams, datapath diagrams, handshake/timing sketches, arbitration or flow-control sequences, and short animations.

Use animation especially for behavior over time, such as token movement, packet ordering, arbitration, deadlock, backpressure, or VC transitions.

Diagram discipline:

- Treat each diagram as an engineering artifact. Define module boxes, interface sides, signal directions, and port locations before drawing wires.
- Use IEEE/paper-style diagrams: rectangular modules, thin lines, small arrowheads, modest colors, and no decorative styling.
- Use color only for semantic categories such as protocol roles, channels, or traffic classes.
- Make every signal source, destination, and direction unambiguous. A wire should terminate on a module boundary, named port stub, junction dot, bus connector, or intentional off-page arrow.
- Avoid relying on visual near-contact. If a signal is meant to connect, make the connection unmistakable after browser rendering and anti-aliasing.
- Draw paired handshakes and flow-control protocols explicitly and consistently, including valid/ready, request/accept, command/response, credit/consume, and data/backpressure.
- Distinguish forward data/control paths from reverse flow-control paths by direction, line style, labels, or modest color use.
- Do not let labels substitute for wiring. A signal label near a floating line is not enough.
- Prefer short bundle labels such as `vld/dat/rdy`; explain detailed fields in an interface table or caption.
- Keep captions useful: state what the figure proves and how it maps to RTL.
- If a diagram becomes crowded, split it into smaller purpose-specific diagrams.
- When the designer provides example figures, use them as the style reference.
- When the designer points to a specific visual issue, make a targeted fix first. Do not broaden the change to nearby signals, style, or layout unless those are also part of the issue.

Animation discipline:

- Keep animations self-contained in the HTML when practical.
- Provide pause/reset/speed controls for non-trivial animations.
- Make labels and colors explain protocol roles, not decorative themes.
- Place HUD text, legends, status labels, and controls outside the drawing area when possible.
- If an overlay is unavoidable, place it in intentionally empty space; it must not cover the signal path, packet, token, state marker, or other behavior being taught.
- If converting from a standalone animation file, embed it into `README.html` and remove or update stale references as requested.

Visual validation:

- Render the HTML only with Google Chrome and inspect the relevant figure at normal reading size; source coordinates alone are not sufficient.
- Before rendering, check that Chrome is installed and callable. On macOS, prefer `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`; otherwise use a discovered `google-chrome`, `google-chrome-stable`, or `chrome` binary.
- If Google Chrome is not installed or cannot be launched, stop the HTML rendering/visual check. Do not substitute Safari, Quick Look, screenshots of another browser, or in-app browser automation for this skill's required render check. Tell the user that Chrome is required and ask them to install Google Chrome before continuing visual validation.
- After editing SVG or canvas content, inspect the changed region closely.
- Trace visible segments and endpoints, especially bends, dashed control lines, ready/backpressure paths, and external interface stubs.
- Check that arrows are small enough not to dominate the drawing.
- Check that wires, arrows, labels, HUDs, legends, and controls do not hide the key behavior.
- For animations, preview representative frames or scrub through important states, not only the first frame.

## Verification Content

For each case, include:

- Case name and directory.
- Stimulus or traffic pattern.
- What behavior it proves.
- Expected waveform observations, not only PASS/FAIL.
- Output artifacts such as logs, WDB/WCFG/VCD, reports, or checker logs.
- Known limitations or intentional failing/deadlock-learning cases, if any.

When waveform review matters, state the important signals or groups to inspect.

## File And Link Hygiene

- Use relative paths inside project documentation; avoid machine-specific absolute paths.
- If replacing `README.md` with `README.html`, update references that pointed to the Markdown file.
- Delete stale standalone docs or animation files only when the user asks or when they have been fully superseded.
- Keep generated docs self-contained enough to copy with the project to another machine.

## Final Validation

Before finishing:

- Inspect the relevant RTL or existing docs before describing implementation details.
- Check HTML structure and embedded script syntax.
- Perform the Chrome-only HTML render/visual check described above whenever diagrams, SVG, canvas, CSS layout, or animation changed.
- Run a lightweight runtime check when the HTML contains animation or non-trivial script.
- Search for stale references to deleted or renamed docs.
- Do not run synthesis or simulation unless the user asks, or the documentation depends on fresh results.
