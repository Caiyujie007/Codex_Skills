---
name: circuit-design-verification
description: General digital circuit and RTL design/verification workflow for any EDA toolchain. Use for RTL design discipline, reusable primitive/library selection, synthesis/lint sanity checks, simulation timeout policy, deadlock diagnosis, TB-vs-RTL responsibility decisions, waveform evidence review, and per-test waveform organization; tool-independent across Vivado, VCS, DC, Verdi, and similar tools.
---

# Circuit Design And Verification

## Core Rule

Treat RTL verification as a chain of evidence:

```text
RTL intent -> synthesis/lint sanity -> simulation with bounded timeout -> waveform evidence -> logs/scoreboard
```

Do not accept a design only because a simulation log says PASS. A passing result must also be visible in waveform evidence, protocol monitors, assertions, or an independently parsed trace.

## Confirm Design Intent Before RTL Changes

Before changing RTL for protocol behavior, deadlock, flow control, arbitration, ordering, or back-pressure problems, first clarify the intended hardware behavior with the designer.

Do not start writing RTL until the design intent is agreed:

- real use case and legal operating scenarios
- interface contract and sampling phase
- which side may stall, throttle, retry, or drop
- forward-progress and completion conditions
- invariants that must never be violated
- whether the observed issue is a design problem or a testbench problem

After the designer confirms the intended behavior or provides the modification method, implement the RTL according to that agreed direction.

## Reuse Proven Design Units

When the designer or project provides a lower-level design unit library, prefer those units over creating a new module with similar behavior.

If the function you need is basically equivalent to a provided proven design unit, use the provided unit. Do not hand-roll similar logic merely because the behavior looks simple or can be written quickly. A small custom replacement still creates new verification, reset, handshake, timing, and maintenance risk.

Examples include:

- handshake or pipeline register slices
- synchronous or asynchronous FIFOs
- CDC synchronizers
- pulse/toggle synchronizers
- reset synchronizers
- clock gating or clock mux cells
- vendor or project-approved RAM wrappers

This is especially important for asynchronous logic, clock-domain crossing, reset crossing, and clock circuitry. Do not hand-roll these blocks unless the project explicitly lacks an appropriate primitive or the user asks for a new reusable primitive to be designed and verified.

## Synchronous Clocking Discipline

For ordinary synchronous RTL, rising-edge registers with nonblocking assignments are the baseline expectation, not a handshake-specific rule.

Unless the designer explicitly specifies a falling-edge scheme:

- do not use falling-edge logic to avoid RTL or testbench race concerns
- drive sequential RTL registers on `posedge clk`
- use nonblocking assignments for sequential logic
- sample DUT interface signals in the testbench on `posedge clk`

This is the normal synchronous design contract. If a race is suspected, first make the producer, consumer, and TB sampling phase follow the same rising-edge contract instead of moving stimulus or sampling to `negedge clk`.

## Reset Usage Discipline

For ordinary synchronous RTL, keep reset signals out of normal combinational datapath, arbitration, routing, and handshake expressions unless the designer explicitly requires reset to participate in that logic.

Reset signals should normally appear only in:

- module ports
- sequential block sensitivity lists
- reset branches inside sequential blocks
- reset synchronizer or reset-control circuitry
- comments or documentation

Avoid using reset directly in:

- `assign` statements
- `always_comb` logic
- combinational functions
- normal valid/ready, request/accept, arbitration, routing, or datapath decisions

If an output must have a known reset-time value, prefer deriving it from correctly reset registers or from a reset-controlled registered enable. Do not gate ordinary combinational outputs with reset just to force a reset-time value, unless that behavior is part of the intended reset architecture and has been confirmed by the designer.

## Handshake Interface Pipelining

For valid/ready-style handshake interfaces, treat `valid`, `ready`, and payload/control signals as one protocol bundle.

Do not add ordinary DFF stages to only `valid`, only `ready`, or only payload/control fields. Partial pipelining can phase-misalign the bundle and cause the interface to accept, drop, or duplicate transfers incorrectly.

If a handshake interface needs pipelining for timing, use the project-approved register slice, skid buffer, FIFO, or equivalent handshake-aware primitive so the handshake and payload/control signals remain protocol-aligned.

## Before Simulation

After an RTL change, run synthesis, lint, elaboration checks, or the closest available tool sanity pass before relying on functional simulation.

At minimum check:

- no errors
- no critical warnings
- no combinational loop / latch / multi-driver warnings
- clocks and resets are understood by the tool
- expected timing constraints exist for the checked top

If synthesis or lint reports a combinational loop or critical structural warning, stop before spending time on simulation. Preserve the report location, explain the suspected root cause to the designer, and discuss the intended fix. Do not hard-patch RTL just to remove the warning. Apply RTL changes only after the designer provides or approves the modification method.

## Timeout Discipline

Every testbench must have a timeout or watchdog.

Choose the timeout from the expected case length:

- estimate the normal completion cycles for the case
- add a modest margin for flow-control throttling, arbitration, or randomized stalls
- avoid very large timeouts that waste time when the design is deadlocked

When a timeout fires, do not keep waiting. Preserve the log and waveform, then debug the last meaningful protocol activity.

## TB Bug Or RTL Bug

When simulation fails, decide whether the failure is a design problem or a testbench problem before changing code.

Use this distinction:

- If the real hardware use case requires the behavior, the RTL must support it.
- If the TB is driving illegal protocol, sampling the wrong phase, or assuming behavior outside the spec, fix the TB.
- Do not modify the TB to “make the waveform pass” when it is exposing a real RTL flaw.
- Do not modify RTL to satisfy an unrealistic TB scenario that cannot happen in the intended system.

For deadlock-like problems, first write down the intended real use case, the legal producer/consumer behavior, and which side is allowed to stall or throttle. Then debug the smallest waveform window that shows forward progress stopping.

## Simulation Evidence

For each test item, run an independent simulation and save independent artifacts:

```text
case_name/
  sim.log
  waveform database or dump
  waveform view/config file
  optional parsed-check log
```

Prefer one verification goal per case. A single “run everything” simulation with only one large waveform is hard to review later.

For every case, define:

- what behavior the case proves
- expected transaction/order/count/end condition
- which waveforms are worth observing first
- what monitor/assertion/checker proves the case

## Waveform Review

Waveforms should be human-readable.

Treat waveform view/configuration files as verification handoff artifacts, not merely generated side files. After generating them, inspect the default view or the configuration text enough to confirm that a designer can quickly understand the protocol behavior. File existence alone is not enough.

Add the important signals to a waveform configuration before handing off the case:

- group signals by logical block, interface, agent, channel, or transaction
- use clear group names such as `Block00`, `InputSide`, `OutputSide`, `FlowControl`, `Status`
- avoid anonymous names such as `[0]`, `[1]`, `[2]` when a human needs to read them
- show the interface contract first: timing references, transfer qualifiers, data/control fields, transaction context, flow-control or status indicators, and error indicators
- hide internal implementation details unless they are needed for the current debug question

Use full wave databases for manual debug and smaller textual dumps for automated checkers when available.

## Checker Strategy

A good checker verifies invariants, not just final counts.

Examples:

- accepted transfers happen only when the interface contract allows them
- transaction framing, start/end markers, or command phases follow the specification
- flow-control counters, grants, or ownership indicators are legal and conserved
- observed data, control, ordering, and completion behavior match the intended case
- stalls, retries, or throttling do not corrupt accepted state
- illegal initiators, commands, or access modes are rejected or flagged as specified

If a checker reads waveform artifacts directly, keep the queried signal set small and stable. Use the tool-native full waveform database separately for manual inspection.

## Reporting

When reporting results, say exactly:

- which structural check or synthesis was run
- whether critical warnings or combinational loops exist
- after every RTL change that reaches synthesis, report resource usage in a compact table using the resource categories the designer cares about
- which simulation cases were run
- where the waveform files are
- what each case proves
- which waveform signals/groups should be inspected
- whether waveform/checker evidence agrees with the log

Use this generic shape when the project has no stricter reporting format:

| Resource | Estimation |
|---|---:|
| resource category 1 | value |
| resource category 2 | value |
