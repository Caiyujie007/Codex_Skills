---
name: vivado-workflow
description: Xilinx Vivado tool workflow for project-mode RTL synthesis with preserved Vivado projects, DRC/timing/utilization reports, xvlog/xelab/xsim simulation, WDB waveform database generation and scripted querying, WCFG waveform view generation or cleanup, and Vivado Tcl automation. Use only when the task explicitly involves Vivado, xsim, xvlog, xelab, WDB, WCFG, Vivado Tcl, Vivado project-mode synthesis, or Vivado reports; pair with circuit-design-verification for tool-independent verification methodology.
---

# Vivado Workflow

## Scope

Use this skill for Vivado tool mechanics. Pair it with `circuit-design-verification` when the task is about design correctness, verification strategy, timeout policy, or interpreting whether a failure is RTL or TB.

## Environment

On Windows, prefer calling Vivado tools from a batch or PowerShell wrapper that sets the Vivado environment first.

Typical installation paths include:

```text
C:/Xilinx/Vivado/<version>/
```

Keep project scripts portable:

- use repository-relative paths inside project scripts and docs
- quote paths that may contain spaces
- keep generated reports, logs, and waves under predictable output directories

## Project-Mode Synthesis And Reports

When Vivado synthesis is needed, use one project-mode workflow: create an openable Vivado project, run `synth_1`, generate reports from that run, and keep the project directory after the run finishes.

Treat project creation, synthesis, and report generation as one flow rather than separate alternatives. Do not replace this with only non-project batch reports, checkpoints, or a separately saved synthesized design unless the designer explicitly asks for that style.

For this workspace, use `xcvu19p-fsva3824-2-e` as the default target FPGA part for new Vivado synthesis scripts and project-mode runs unless the user or an existing checked-in script explicitly requests another part. When updating an existing synthesis flow, change the `create_project ... -part` value to this part unless preserving old report comparability is the stated goal.

Use a simple project-mode Tcl flow:

```tcl
create_project <project_name> <project_dir> -part <part>
set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY none [get_runs synth_1]
import_files {
  <rtl_or_include_file_1>
  <rtl_or_include_file_2>
}
import_files -fileset constrs_1 {
  <constraint_file>
}
set_property top <top_module> [current_fileset]
update_compile_order -fileset sources_1
launch_runs synth_1 -jobs <n>
wait_on_run synth_1

open_run synth_1
report_drc -file reports/drc.rpt
check_timing -file reports/check_timing.rpt
report_timing_summary -file reports/timing_summary.rpt
report_utilization -file reports/utilization.rpt
report_methodology -file reports/methodology.rpt
```

Set `STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY` to `none` immediately after `create_project` so the synthesized project preserves RTL hierarchy for report inspection and follow-up experiments.

Preserve the generated `.xpr`, imported source tree, constraint set, run directory, and report directory so the designer can open the same project, inspect reports, rerun synthesis, edit constraints, or run experiments.

Passing criteria:

- `synth_design` has 0 errors and 0 critical warnings
- `report_drc` has no `LUTLP-1` or combinational loop critical warning
- `check_timing` reports `loops (0)` and no unexpected `no_clock`
- timing summary says user constraints are met, or the remaining violation is explicitly understood
- utilization is reported with the target FPGA part

Do not proceed as if verification passed when Vivado reports a combinational loop.

For Vivado resource reporting after RTL synthesis, always report the designer-facing resource table below:

| Resource | Estimation |
|---|---:|
| LUT | `<Slice LUTs or LUT as Logic>` |
| LUTRAM | `<LUT as Memory / LUTRAM>` |
| FF | `<Slice Registers>` |
| BRAM | `<Block RAM Tile / BRAM>` |

Use the closest names from `report_utilization` for the Vivado version and device family. Do not add extra resource rows unless the designer asks for them.

## XSim Flow

Typical command-line flow:

```bat
xvlog --sv <rtl and tb files>
xelab -debug typical -s <snapshot> work.<tb_top>
xsim <snapshot> -tclbatch <run.tcl> -testplusarg CASE_ID=<case>
```

Run one test item per xsim invocation when cases need separate waveforms. Save each case in its own directory with its own log and wave artifacts.

Remember that xsim may still return success when a TB calls `$finish` from a watchdog. Inspect the log text and checker output, not only the process return code.

## WDB And WCFG

Use WDB as the primary Vivado waveform artifact:

```tcl
log_wave -recursive *
run all
```

When launching xsim, set the WDB output path explicitly:

```bat
xsim <snapshot> --wdb <case_dir>/waves.wdb -tclbatch <run.tcl>
```

WCFG is a view configuration file. Editing WCFG does not require regenerating WDB.

When a change only affects WCFG layout, waveform grouping, display names, or
wave-only observation aliases, verify it with the smallest representative
simulation case that refreshes the affected WDB and WCFG. Do not run a full
simulation regression just to validate a waveform view unless the waveform
change also changes RTL behavior, testbench stimulus, monitors, checkers, or
case coverage. A suitable lightweight check is:

- run one simple case that exercises the relevant hierarchy or interface
- confirm the simulation log still passes and has no watchdog/failure text
- confirm the checker or trace for that case still holds, if one exists
- open/query the generated WDB and WCFG to confirm object paths resolve
- inspect that group names and display names are readable

For readable WCFG files:

- group signals by block, agent, interface, channel, or transaction
- name groups with meaningful labels such as `Block00`, `Agent01`, `RX`, `TX`, `FlowControl`
- avoid presenting bit lanes only as `[0]`, `[1]`, `[2]`
- keep default views focused on interface-level signals
- add internal RTL signals only for a specific debug purpose

When many signals must be added, generate or normalize WCFG with Tcl or a script so naming stays consistent.

Treat WCFG object paths and display names as separate concerns:

- `fp_name` must be a real object path that exists in the WDB
- `ObjectShortName` and `ElementShortName` should be human-readable labels
- packed-array bit paths such as `/tb/inj_valid[0]` may be valid but display as `[0]`; normalize the display names or prefer readable instance-port paths when practical
- generate-block paths can contain escaped names and trailing spaces, such as `/tb/dut/\g_node[0].u_node /inj_valid`; do not hand-guess these paths

Before writing a generated WCFG into the handoff, query or inspect the WDB enough to confirm object paths:

```tcl
open_wave_database <case_dir>/waves.wdb
get_objects -r /tb/*
get_objects -r /tb/dut/*inj_valid*
```

Remember that `[]` has meaning in Tcl pattern matching. If direct `get_objects` patterns fail for generated scopes, search recursively for a distinctive signal name and reuse the exact path returned by Vivado.

After WCFG generation, run a lightweight readability check:

- no default signal names like `[0]`, `[1]`, `[2]` remain in `ObjectShortName`
- group names are meaningful and consistent across cases
- radix choices are intentional for IDs, counters, types, masks, and payload snippets
- the same normalize flow is applied to every per-case WCFG
- opening the WCFG does not report missing waveform objects

## WDB Query Notes

Vivado can reopen a saved WDB from batch Tcl:

```tcl
open_wave_database waves.wdb
set objs [get_objects /tb/*]
set cycle_value [get_value_database -time 100ns /tb/cycle]
```

Use this path for lightweight waveform checks when the project should avoid TB-generated text dumps. A checker can sample selected HDL objects at known clock-edge times and compare protocol invariants against expected behavior.

Practical rules:

- query only a small set of stable top-level or interface-level objects
- use full hierarchical paths returned by `get_objects`
- sample at the intended clock edge plus the project’s chosen observation phase
- distinguish pre-edge combinational values from registered monitor pulses
- prefer explicit TB monitor pulses for “actual handshake accepted” events when phase ambiguity exists
- keep WDB for manual GUI review and scripted Tcl queries, and keep WCFG for human-readable layout

## Common Vivado Pitfalls

- Vivado 2021.x SystemVerilog support is useful but incomplete; keep syntax conservative when a parser error looks suspicious.
- Do not drive the same variable from both `initial` and `always_ff`.
- `unique case` can warn at time 0 before reset initializes state; use normal `case` unless uniqueness is important to the check.
- Missing clocks in synthesis reports often mean the script forgot `create_clock`.
- GUI wave viewing can leave `.Xil/`, `xsim.dir/`, `vivado.log`, and `vivado.jou` in the working directory.

Cleanup scripts should delete only temporary Vivado artifacts unless the user explicitly asks to delete simulation results.

## Result Summary

When summarizing a Vivado run, include:

- Vivado version if known
- top module and target part
- synthesis errors, critical warnings, and DRC loop status
- timing status and WNS if available
- the Vivado resource table: `LUT`, `LUTRAM`, `FF`, `BRAM`
- simulation cases run
- WDB/WCFG locations
- whether waveform/checker evidence matches the simulation log
