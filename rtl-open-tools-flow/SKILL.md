---
name: rtl-open-tools-flow
description: Open-source RTL checking and simulation workflow using Verilator, Yosys, Icarus Verilog, and GTKWave. Use when Codex needs to run or set up lightweight RTL syntax/lint checks, Yosys structural sanity checks, Icarus Verilog simulations, VCD/GTKWave waveform handoff, macOS Homebrew installation notes for these tools, or a reproducible open-source verification flow; pair with circuit-design-verification for tool-independent RTL intent and debugging methodology. Do not use for Vivado/xsim/WDB/WCFG flows.
---

# 基于开源工具的 RTL 检查与仿真流程

## Scope

Use this skill for open-source RTL tool mechanics:

- Verilator: syntax, lint, and RTL code-quality checks
- Yosys: elaboration, hierarchy, combinational-loop, multi-driver, undriven-net, and structural sanity checks
- Icarus Verilog: lightweight RTL simulation with `iverilog` and `vvp`
- GTKWave: VCD waveform viewing and `.gtkw` handoff

Pair this skill with `circuit-design-verification` when the task is about RTL intent, interface contracts, checker strategy, failure root cause, timeout policy, or whether a failure is caused by RTL or testbench behavior.

Do not use this skill for Vivado-specific flows. Use `vivado-workflow` for Vivado project-mode synthesis, xsim, WDB, WCFG, Vivado Tcl, or FPGA reports.

## macOS Tool Installation

On macOS, prefer Homebrew command-line tools:

```zsh
brew install verilator yosys icarus-verilog gtkwave
```

Check the installed tools before running the flow:

```zsh
verilator --version
yosys -V
iverilog -V
vvp -V
gtkwave --version
```

If a tool is missing:

- on macOS, suggest the Homebrew install command above
- on non-macOS systems, report the missing tool and do not guess a package-manager command unless the project already documents one

GTKWave notes for macOS:

- Prefer the Homebrew command-line executable: `gtkwave wave.vcd wave.gtkw`.
- Avoid depending on the GUI app bundle or `gtkwave-bin`; macOS 14+ may block or reject some app bundles because of Gatekeeper or compatibility checks.
- For double-click waveform launchers, create executable `.command` wrappers. Prefer resolving `GTKWAVE_BIN`, `/opt/homebrew/bin/gtkwave`, then `PATH`.
- If the launcher needs to auto-close the Apple Terminal window after GTKWave exits, do not use `exec`; run GTKWave normally, capture its exit status, then optionally close the Terminal window with `osascript`.
- Keep a user escape hatch such as `AUTO_CLOSE_TERMINAL=0` for debugging launch failures.

Recommended `open_wave.command`:

```zsh
#!/bin/zsh
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

terminal_window_id=""
if [[ "${TERM_PROGRAM:-}" == "Apple_Terminal" ]]; then
  terminal_window_id="$(/usr/bin/osascript -e 'tell application "Terminal" to id of front window' 2>/dev/null || true)"
fi

gtkwave_bin=""
if [[ -n "${GTKWAVE_BIN:-}" && -x "${GTKWAVE_BIN:-}" ]]; then
  gtkwave_bin="$GTKWAVE_BIN"
elif [[ -x /opt/homebrew/bin/gtkwave ]]; then
  gtkwave_bin="/opt/homebrew/bin/gtkwave"
elif command -v gtkwave >/dev/null 2>&1; then
  gtkwave_bin="$(command -v gtkwave)"
else
  echo "gtkwave was not found. Install it or set GTKWAVE_BIN, then reopen this script."
  exit 1
fi

"$gtkwave_bin" wave.vcd wave.gtkw
gtkwave_status=$?

if [[ "${AUTO_CLOSE_TERMINAL:-1}" != "0" && -n "$terminal_window_id" ]]; then
  /usr/bin/osascript <<OSA >/dev/null 2>&1 &
tell application "Terminal"
  try
    close (first window whose id is $terminal_window_id)
  end try
end tell
OSA
fi

exit $gtkwave_status
```

## Standard Flow

Keep paths portable:

- use repository-relative paths inside scripts when practical
- quote paths that may contain spaces
- keep logs, reports, traces, and waves under predictable output directories
- preserve generated evidence unless the user explicitly asks to clean it

Recommended output shape:

```text
sim_out/
  summary.log
  iverilog.version.log
  vvp.version.log
  tool_sanity/
    verilator_lint.log
    yosys_check.log
  <case_name>/
    compile.log
    sim.log
    scoreboard.log
    trace_ar_in.csv
    trace_ar_out.csv
    wave.vcd
    wave.gtkw
    open_wave.command
    <testbench>.vvp
```

Run the stages in order.

Use the TMA-style run directory as the preferred golden shape for small RTL blocks:

- keep one top-level `summary.log` that records start/end time, tool paths, static-check status, per-case PASS/FAIL, and final result
- model cases as `<case_dir>:<plusarg_case_name>` pairs so directory names can be ordered (`00_smoke`) while testbench plusargs remain readable (`+CASE=smoke`)
- generate each case independently so compile logs, simulation logs, traces, scoreboards, VCDs, and GTKWave views are reproducible
- write helper functions in scripts for `find_gtkwave`, `write_gtkw`, `write_open_wave`, `run_optional_checks`, and `run_case` when the flow has more than one case
- use `#!/bin/zsh` and `SCRIPT_DIR="${0:A:h}"` for macOS double-click `.command` scripts; this is more robust than relying on the caller's current directory

### Stage 0: Preflight

Check tool availability first:

```zsh
command -v verilator
command -v yosys
command -v iverilog
command -v vvp
command -v gtkwave
```

Record tool versions in the run summary and, when useful, into separate files such as `sim_out/iverilog.version.log` and `sim_out/vvp.version.log`.

For GTKWave discovery, prefer this search order:

1. `GTKWAVE_BIN`, if set and executable
2. `/opt/homebrew/bin/gtkwave`
3. `command -v gtkwave`

Do not continue to simulation when the required simulator (`iverilog` or `vvp`) is missing. GTKWave can be missing without blocking simulation, but generated `open_wave.command` scripts should print a clear install/path message.

### Stage 1: Verilator Lint

Use Verilator before simulation:

```zsh
verilator --lint-only -Wall --timing <rtl_files>
```

Treat these as blockers unless the designer explicitly waives them:

- syntax or elaboration failure
- width warnings that can change behavior
- inferred latch
- combinational-loop-related warnings such as `UNOPTFLAT`
- multiple drivers or undriven required nets
- clock/reset or timing-control errors

Style-only warnings, filename mismatches, or intentionally unused signals may be reported as reviewed/waived, but do not hide them silently.

For exploratory flows, Verilator can be treated as a non-blocking tool-sanity step if the script clearly records `PASS`, `WARN`, `FAIL`, or `SKIP` in `summary.log`. For signoff-like local checks, treat unreviewed Verilator warnings as blockers before simulation.

### Stage 2: Yosys Structure Sanity

Use Yosys after Verilator lint:

```zsh
yosys -p "read_verilog -sv <rtl_files>; hierarchy -check -top <top>; proc; opt; check; stat"
```

Inspect the `check` output. Stop before simulation if Yosys reports:

- unresolved hierarchy
- combinational loop
- multiple conflicting drivers
- unexpected undriven nets
- latch or memory inference that contradicts the design intent

For RTL sanity, no standard-cell library is required. A library is only needed for technology mapping, timing, or process-specific area estimates.

Like Verilator, Yosys can be run as a non-blocking sanity step during early exploration, but structural failures from `hierarchy -check` or `check` should be called out explicitly and normally fixed before trusting simulation evidence.

### Stage 3: Icarus Verilog Simulation

Run simulation only after syntax and structural checks are clean or explicitly waived.

Typical compile/run commands:

```zsh
iverilog -g2012 -Wall -o <case_dir>/simv <rtl_files> <tb_files>
vvp <case_dir>/simv +CASE=<case_name> +WAVE=<case_dir>/wave.vcd \
  +TRACE_IN=<case_dir>/trace_ar_in.csv \
  +TRACE_OUT=<case_dir>/trace_ar_out.csv \
  +SCOREBOARD=<case_dir>/scoreboard.log
```

Use one simulation invocation per verification case when separate waves are useful. Add a watchdog or timeout to every testbench. Inspect the log text, scoreboard, assertions, and traces; do not accept a case solely because the process returned success.

### Stage 4: GTKWave Handoff

Use VCD as the primary open-source waveform artifact and `.gtkw` as the view configuration.

For readable `.gtkw` files:

- group signals by clock/reset, input interface, output interface, internal control, FIFO/status, checker events, or protocol channels
- keep interface-level signals visible before deep implementation details
- use readable names for IDs, counters, payload snippets, and status bits
- avoid anonymous display labels such as only `[0]`, `[1]`, `[2]`
- generate view groups programmatically when the same layout is needed in every case; common groups include `Clock_Reset`, `Input_AR`, `Output_AR`, `FIFO_Status`, `RR_Gap_Control`, and `Checker_Events`

When waveform layout changes only affect `.gtkw`, run the smallest representative simulation that regenerates the VCD and verify the view opens.

## Verification Evidence

Treat verification as a chain of evidence:

```text
RTL intent -> Verilator lint -> Yosys structure check -> bounded simulation -> waveform/trace/scoreboard
```

For each case, define:

- what behavior the case proves
- expected accepted transactions, ordering, counts, and end condition
- the checker or trace condition that proves the behavior
- the waveform groups to inspect first

Preserve per-case evidence. Do not replace multiple focused cases with one large all-in-one waveform unless the user explicitly asks for a smoke-only flow.

## Result Summary

When reporting a run, include:

- tool versions: Verilator, Yosys, Icarus Verilog, GTKWave
- RTL target: top module and important RTL/TB files
- static checks: Verilator result, Yosys `check` result, and any reviewed warnings
- simulation: case list and PASS/FAIL status
- artifacts: log, trace, VCD, `.gtkw`, and `open_wave.command` locations
- evidence: whether waveform/checker/trace evidence matches the simulation log
- residual risk: uncovered cases, waived warnings, or known tool limitations
- summary: quote the final `summary.log` result and mention any non-blocking `WARN`, `FAIL`, or `SKIP` tool-sanity entries

## Common Pitfalls

- Icarus Verilog SystemVerilog support is useful but limited; keep RTL/TB syntax conservative when parser errors are tool-specific.
- Verilator may treat warnings as fatal depending on warning type and command options; classify warnings instead of blindly suppressing them.
- Yosys `check` catches many structural issues but is not timing signoff and does not replace backend STA.
- VCD files can become large; dump focused hierarchy or selected signals when cases are long.
- Generated `.command` files need execute permission: `chmod +x open_wave.command`.
- Apple Terminal auto-close from `.command` scripts is best-effort. If it gets in the way of debugging, run `AUTO_CLOSE_TERMINAL=0 ./open_wave.command` from a shell.
