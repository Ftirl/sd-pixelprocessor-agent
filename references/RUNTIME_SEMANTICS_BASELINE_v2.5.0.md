# Runtime semantics and conservative construction defaults

This document records Substance Designer Pixel Processor / Function Graph observations and conservative construction defaults. A project observation is not a universal engine contract; the evidence limits and conflicting real-project results are in `REAL_PROJECT_VALIDATION.md` and `MORPHING_RETEST_GATES.md`.

Evidence class: `FIELD_VERIFIED` means observed while executing/cooking a specific real project. Record its Designer build, graph, input, and result. Use a current-session minimal probe and independent oracle when a decision depends on a behavior not established in that scope.

## RS1 — Pixel Processor coordinates are normalized

Adobe documents Pixel Processor `$pos` as normalized `[0,1]`. Adobe's system-variable reference documents `$size` as the current node size in pixels. A historical 16.0.3 project observation reported `$size≈(1,1)` in one PP context; that observation is context-specific and must not override the documented meaning without a same-session probe.

Consequences:

- Never translate shader `fragCoord` as raw `$pos`.
- Do not translate shader `iResolution.xy` from `$size` until the current PP context confirms the documented pixel-size behavior; otherwise use an explicit output-size/formal input.
- For a square target, `(F - 0.5*R) / R.y` maps to `$pos - 0.5` when `F/R` is represented by normalized PP coordinates.
- For non-square targets, reconstruct the source aspect convention from normalized UV plus a verified output-size source.
- Any migration that depends on true pixel indices must introduce an explicit virtual-resolution/output-size input or another verified source of resolution.
- The native probe includes `coord_pos_x` and `coord_size_x`; version promotion requires both results and rejects a report that matches pixel-space `$pos` or unit `$size` instead of the documented semantics.

## RS2 — Post-Set Get requires shared Sequence execution topology

**HISTORICAL OBSERVATION, CAUSE UNRESOLVED:** one project's same-name `Get` returned `0` while a statement Sequence output carried the expected value. The recorded test did not establish that the Get's consumer joined the later branch of the same output-reachable Sequence chain. Do not infer that a correctly sequenced Get is unreliable from this observation.

**COUNTER-OBSERVATION (Morphing Abstract_text1, 16.0.3):** fresh same-scope Gets read written values (about 0.698/0.8 for 0.7/0.8); a nested While accumulator advanced across two outer iterations (decoded about 22). Adobe's documented model is that Sequence fully executes its first branch before the second and Get reads a typed variable in the current scope. An unconnected/unused Get does not itself execute a Set.

Default connection proof for a lower statement reading `x`:

`Set(x) -> Sequence.In (earlier branch); Get(x) -> lower expression -> Sequence.Last (later branch) -> reachable output`

For a chain of Sequences, the earlier `In` path may itself include preceding Sequence nodes; the Get's downstream consumer must join a later `Last` branch of that same chain. `Get` has no Sequence input port: “Get connected to Sequence” means its **output-to-consumer path** feeds that later branch. Verify actual port identities/edges and output reachability, not canvas top/bottom coordinates or node-name equality. Also verify same scope, exact identifier, typed dimension and a nonzero changing native read.

If a Get reads `0` or an old value, diagnose in this order: (1) Set truly feeds the earlier `In` path; (2) Get's consumer feeds the later `Last` path, and this Sequence reaches the marked/cooked output; (3) Set/Get are in the same valid scope with exact matching identifier and type; (4) parameter-stack order or control branch, if crossing parameter/functions; (5) native nonzero/change oracle and Console diagnostics. Repair a missing later-branch connection before trying an alternative carrier. The CRATE builder added a Sequence spine only after constructing lower expressions from earlier Set outputs; that is a structural FAIL even though Sequence nodes exist. A Sequence-value path may be used only as a documented, approved and numerically verified exception after topology-correct Get behavior is still unresolved; never silently switch to Set/RHS DAG.

Distinguish:

- **execution/state naming:** Set/Get/Sequence;
- **normal post-statement state read:** a typed Get on the later branch of the same ordered, output-reachable Sequence chain;
- **exceptional direct-value transport:** the associated Sequence output, only with documented approval and numeric evidence;
- **deliverable terminal value:** a pure-operator root (RS3/RS4).

## RS3 — Pure output roots are the conservative default

**PROJECT OBSERVATION:** marking a Sequence node as the final output cooked to a constant white result in one project. In a second project, a small Sequence-root probe worked but the full graph still failed its oracle. This does not establish a universal prohibition or a universally safe Sequence-root pattern.

For generated work, default to a pure operator that preserves the value and type, and verify `getOutputNodes()` plus native numeric output. Examples:

- float1: `add(value, 0.0)` or another identity pure operator;
- floatN: `add(value, zeroN)` or `mul(value, oneN)` with an explicit same-dimension constant/broadcast;
- never rely on `mulscalar` for a Sequence-derived vector terminal (RS6).

The identity operator is a construction strategy, not proof of correct return semantics. A deviation needs a current-session minimal probe and caller-level numeric validation.

## RS4 — Verify Function Graph marked outputs and caller values

**PROJECT OBSERVATION:** one `Set`-root Function returned `0`; appending a pure operator such as `add(spine, 0.0)` produced the expected value in that case. In `rain_text1`, one `mulscalar` marking attempt left `getOutputNodes()` empty, with cause unresolved.

Default and acceptance rule:

- Function Graph output root = pure expression/operator or a verified Function instance output.
- Avoid `Set`, `Sequence`, and control nodes as generated deliverable roots unless a current-session probe and caller oracle justify the exception.
- When a function is imperative internally, bridge its final statement spine into a pure identity operator, mark it, read back the actual output list, and run discriminating numeric cases before instantiating it upstream.

## RS5 — While body isolation: external Sequence input is unsafe

**FIELD_VERIFIED / SAFETY CRITICAL:** consuming a Sequence produced **outside** a While body from inside the body can hang the Designer main thread; MCP then appears to time out.

`SAFETY_INVARIANT_002`:

> A While `loop`/body closure MUST NOT consume a Sequence node whose producer is outside that body closure.

Values entering the body must be reconstructed as body-private pure values: constants, formal inputs, verified loop-local Get/state reads, or body-private pure operators. Never "thread" an outer statement Sequence directly into the While body.

This invariant is fail-closed. Do not automatically probe the known-hang pattern in a production Designer session.

## RS6 — Sequence-derived vectors avoid mulscalar

**FIELD_VERIFIED:** `mulscalar(Sequence(float4), const)` is unreliable. The safe identity/scale form is same-dimension `mul` after explicit scalar broadcast, e.g.:

`Sequence(float4) -> mul(a=value4, b=vector4(s,s,s,s))`

Rules:

- If a vector operand is statement-/Sequence-derived, prefer same-dimension `mul` + explicit broadcast.
- For terminal normalization use `mul(valueN, oneN)` or `add(valueN, zeroN)`.
- `mulscalar` may still be used for ordinary pure vector × scalar expressions when the vector is not Sequence-derived and current-version validation supports it.

## Execution model

The generator must treat these as three distinct layers:

1. **Statement spine** — `Set` / `Sequence` establish execution and state-update order.
2. **Value spine** — later-branch Get consumers read named state; Sequence outputs may carry a direct value only as an explicit exception, and may not cross into a While body from outside.
3. **Terminal spine** — the value is normalized through a pure operator before a Function Graph or PP result is marked.

Mnemonic: **Sequence orders both Set and consuming Get paths; pure operators deliver outputs.**

## Required acceptance checks

A generated/modified graph is not semantically accepted until all applicable checks pass:

- `RS_COORD`: shader coordinate lowering explicitly records normalized-vs-pixel convention.
- `RS_SIZE_SOURCE`: shader resolution/aspect does not rely on an unprobed `$size` context.
- `RS_SETSEQ` / `RS_GET_SEQUENCE_TOPOLOGY`: a post-Set Get participates through its consumer in the later branch of the same output-reachable Sequence chain; the Set participates in the earlier branch.
- `RS_TERMINAL`: generated outputs default to a pure root; exceptions require recorded current-session evidence.
- `RS_FUNCTION_OUTPUT`: read back every generated Function Graph's marked output and validate its cooked value and caller path.
- `SAFETY_INVARIANT_002`: no While body edge originates from an external Sequence.
- `RS_MULSEQ`: no `mulscalar` consumes a Sequence-derived vector; use same-dimension mul+broadcast.
