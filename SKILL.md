---
name: sd-pixelprocessor-agent
description: Analyze, create, repair, refactor, validate, and lay out Substance 3D Designer Pixel Processor and Function Graphs. Use for shader migration, While and Set/Sequence/Get semantics, Function Graph extraction, version-aware native probes, and code-structure layout. Do not use for unrelated Painter or ordinary material-authoring tasks.
---

# SD Pixel Processor Agent

Use this skill for Substance 3D Designer Pixel Processor and Function Graph work.
The current execution specification is:

`references/SD_PixelProcessor_AGENT_SPEC_v2.5.0.md`

Read only the sections needed for the current task, then expand when a dependency requires it. For real-project failure gates and evidence limits, use `references/REAL_PROJECT_VALIDATION.md`, `references/CASE_A_RETEST_GATES.md`, `references/CASE_B_RETEST_GATES.md`, `references/CASE_C_RETEST_GATES.md`, and `references/CASE_D_RETEST_GATES.md`; measured examples are not universal API contracts.

## Project workflow and operational revision ([historical validation])

For large or multi-pass migrations, load [LARGE_PROJECT_ASSEMBLY.md](references/LARGE_PROJECT_ASSEMBLY.md): visible layer milestones, typed multi-PP/LUT interfaces, large-function tiers, explicit visual-first decisions, and standalone package acceptance. It amends the strict SOP-5B/DI1 assembly lock only for the documented, user-selected `PROVISIONAL_VISUAL_ASSEMBLY` path; unverified functions never become verified dependencies by exception.

For layout, also load [DEPENDENCY_COMPACT_LAYOUT.md](references/DEPENDENCY_COMPACT_LAYOUT.md). Apply the existing Skill layout first, then dependency proximity within its constraints; do not replace the Sequence/Set/While baseline. These are behavior-document updates on the 2.5.0 runtime baseline, not a new runtime probe result.

## Trigger scope

Use this skill when the user asks to do one or more of the following in Substance 3D Designer:

- inspect, reconstruct, validate, create, repair, or migrate a Pixel Processor graph;
- inspect, create, repair, or call an `SDSBSFunctionGraph`;
- translate GLSL/HLSL/shader logic into Pixel Processor / Function Graph nodes;
- lower GLSL/HLSL loop formats (`for`, `while`, `do-while`, `for(;;)`, nested loops, `break`/`continue`, macro-expanded loops) into structured SD While nodes and plan their `init`/`cond`/`loop` wiring;
- debug Get/Set/Sequence/While/ifelse behavior, scope, execution order, type propagation, coordinates, sampling, or function interfaces;
- split an oversized graph, detect reusable subgraphs, or package reusable logic as Function Graphs;
- lay out nodes while preserving code/IR structure;
- verify that a graph refactor preserves semantics.

Do not use this skill for unrelated Substance Painter workflows, ordinary material authoring that does not involve PP/Function Graph execution semantics, or generic Python questions with no SD graph task.

## Mandatory startup

Before any SD write operation:

1. Determine authorization and requested scope from the current conversation.
2. Determine environment mode A/B/C using §2.1 of the reference.
3. Identify the exact package path, graph/resource identity, and PP node id when applicable. Never target by a short identifier alone when ambiguity is possible.
4. Read the current graph state before modifying it. Preserve unsaved-session state as a separate fact from disk state.
5. If the task is create/repair/refactor/layout, establish the relevant IR/snapshot before mutation.
6. Apply the version gate in `references/COMPATIBILITY_MATRIX_v2.5.0.md`: exact-version native measurements may be reused only for a matching `VERIFIED_BASELINE`. Designer 16.0.5 and unknown versions are `RUNTIME_REPROBE_REQUIRED`; before a write depends on measured numeric, While, or coordinate behavior, run the hardened `scripts/probe_sd_semantics.py` in that session and retain its `probe_report.json`. Never present the bundled 16.0.3 measurements as 16.0.5 evidence.

For a new build, migration, or structural layout choice, **ask once before the first style-dependent write** unless the user already chose: “这次希望采用哪种图结构？A. 结构保真：命令式部分用 Set/Sequence，纯表达式函数仍用 DAG；B. DAG 优先：直线计算可改成纯 DAG，但不保留源码赋值顺序结构；遇到状态/循环会先停下确认。” Record the answer and the selected mode for each graph in the IR/layout plan; do not switch modes later because a build is easier or an image metric improves. If B conflicts with a stateful/dynamic loop or a layout-only request would require adding/removing nodes, explain the conflict and get a separate structural decision; never silently substitute A. In a read-only task, do not ask merely to inspect a graph. See §7.8/L1 and `scripts/layout_intelligence.py`.

When SD MCP or equivalent live tools are available, calls that affect or inspect SD state must be serialized unless the reference explicitly permits otherwise. If the current environment exposes different tool names, map capabilities semantically; do not assume an API exists merely because an older tool had that name.

## Reference loading map

Read these sections before executing the corresponding task:

- Always: §0–§3. For GLSL/Shadertoy migration or builder/layout failures also read the relevant project gates in `references/REAL_PROJECT_VALIDATION.md`, `references/CASE_A_RETEST_GATES.md`, `references/CASE_B_RETEST_GATES.md`, and `references/CASE_C_RETEST_GATES.md`.
- General graph analysis/repair: §4, §5, §7, §9.
- Large graph or reusable-function work: §4.5 A1–A11, I21–I25, SOP-5A, §7.7, §10.
- Loop/state work: §4.2, SOP-3, SOP-3A, §7.2–§7.4, `references/WHILE_OFFICIAL_BASELINE_v2.5.0.md`, relevant D rules in §8.
- Loop format lowering / While wiring: N24–N26, I32–I36, W11–W16, SOP-3A, §7.9.1–§7.9.10, D26–D30, §11.6.
- While wiring template (default form for new/repair work): **§7.9.10** (role list, port-level connection chains, semantic conventions, geometry, template preconditions) + I36 + `WHILE_OFFICIAL_BASELINE_v2.5.0.md` §3.3.
- Statement-tree connections + span/node budget: **§7.10** (Set → statement Sequence → local value consumers → pure terminal, allowed/forbidden wires, measured geometry, normalized span in §7.10.4, node-count budget in §7.10.5, read-only statistics template) + N26, W15–W16, I37–I38, L14–L15, D31–D32, `§11.7`.
- Function Graph/interface work: §4.1, SOP-4, SOP-5A, §7.1, §7.7.
- **New build / source migration (functionize first, then assemble)**: **A12 + SOP-5B** (source function table → interfaces → bottom-up function creation with per-function I1/I2/I9/I10/I23 → instance assembly with I11 → main-graph statement structure), plus `§7.9.11` when a loop body is functionized. Use A8 only for repairing an existing graph.
- Case D retest issues in a new GLSL migration: `references/CASE_D_RETEST_GATES.md` DI1–DI8 (pre-caller Function numeric gate, precreation Sequence-spine plan check, undefined components, dual time channels, alpha-preserving export, diagnostic-encoding preflight, loaded-package save identity, proved body-entry break hoist).
- Layout-only work: I13/I13b/I20/I30, **I37/I38/I39**, SOP-8 (mode A new build / mode B existing graph), §10 (incl. L2–L4 and L12–L16), plus Architecture Gate rules from §4.5. Use `scripts/layout_intelligence.py` to check planned and read-back statement geometry.
- Built-in function semantics, availability and lookups (on demand): `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md` plus `scripts/lookup_sd_function.py` — consult it whenever a math function's SD identity, ports or exact semantics matter. For measured numeric/loop behaviour (including what SD silently does wrong) read `references/NATIVE_PROBE_RESULTS_v2.5.0.md` and run `scripts/probe_sd_semantics.py` for the current environment. For the **verified library catalogue** (171 built-in Functions, verified node-by-node against the shipped package) use `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md` / `references/library_functions_v2.5.0.json`, and regenerate with `scripts/dump_library_functions.py` + `scripts/verify_library_functions.py` when the SD version or package differs.
- Runtime semantic baseline: `references/RUNTIME_SEMANTICS_BASELINE_v2.5.0.md` (RS1–RS6, `SAFETY_INVARIANT_002`) and `scripts/runtime_semantics.py`.
- Runtime version safety / production hardening: `references/COMPATIBILITY_MATRIX_v2.5.0.md`, `references/PRODUCTION_HARDENING_v2.5.0.md`, `scripts/check_compatibility.py`, and `scripts/eval_release.py`.
- GLSL/HLSL migration: SOP-0A, §4.3, §7.3–§7.10, **§7.5.1** (mul/mulscalar selection table), **§7.5.2** (atan2/vector2/cartesian official semantics), **§7.5.3** (numeric semantics: mod/fmod/round/frac/trunc/sign/clamp/step/smoothstep), relevant diagnostics in §8, plus `REAL_PROJECT_VALIDATION.md`.
- Time-driven graphs, vector assembly, library availability, diagnostic taps, or branch-heavy shader migration: `CASE_C_RETEST_GATES.md` plus the relevant §7.5/§7.6/§7.11 sections. Apply the project-tested gates in the current graph/version, not as universal engine claims.
- Final delivery: §9 and SOP-9.

If a task crosses categories, load all relevant sections rather than applying one section in isolation.

## Before graph mutation

Load [EXECUTION_RULES.md](references/EXECUTION_RULES.md), selecting its semantic/layout sections for the task. It retains the original non-negotiable rules, Variable-version boundary, and While loop baseline. Read-only audits need only the relevant sections.

For evidence, retries, provisional assembly, performance escalation, frames or installation, load [OPERATIONAL_RECOVERY.md](references/OPERATIONAL_RECOVERY.md). `BEHAVIOR_REVISION` identifies policy/tool changes separately from the 2.5.0 runtime baseline.

Core constraints: preserve an anonymized case’s structural mode; every source loop uses structured While unless an explicit documented exception applies; protect exact package identity; plan placement before creation; keep numeric, structural, visual and native verdicts separate. Unknown tool outcomes are not permission to replay writes. Existing authorization persists.

## Mutation workflow

For authorized create/repair/refactor work, follow this order within each visible milestone. For large projects, first plan layers and interfaces per `references/LARGE_PROJECT_ASSEMBLY.md`; the strict flow below remains the default, with only its §4 explicit provisional assembly exception:

`target + snapshot -> typed source/Final IR -> loop ledger + While plan -> function table + interfaces -> layout plans -> bottom-up Function Graph creation + structural/port checks + independent numeric oracle for each function -> main-graph assembly from verified instances -> PP input/output and resolved-size readback -> Architecture/layout checks -> full-resolution native image comparison -> save -> read back`

For repairing an **existing** graph, replace the functionize-first segment with A8's replacement order: `snapshot -> candidate IR -> new Function Graph -> first instance -> port readback -> semantic validation -> remaining call sites -> delete replaced nodes`.

For pure layout work where the user forbids logic changes:

`target + logic fingerprint -> Architecture Gate report -> tree-layout plan -> position-only changes -> read back -> I13/I13b/I20 (mode B) -> save if authorized`

Do not mix logic rewrites into a position-only task.

## Verification and reporting

Use PASS / FAIL / WARN / N/A / 未验证 exactly as defined in the reference.

Report logic, structure/functionization, layout, native SD execution/rendering, and cross-engine/math checks separately. Do not convert an unexecuted check into PASS.

For engineering tasks, preserve the §9 report structure where applicable, including:

- environment mode and execution capability;
- exact target identity and authorization scope;
- concise conclusion;
- applicable I/A/L checks with evidence;
- reconstructed IR / loop ledger / function-call interface evidence as needed;
- for new builds: the source function table, per-function `FUNCTION_GRAPH`/`INLINE`/`BLOCKED` decisions, interface (formal/return) tables, creation order, instance and call-site list, and the I11 port readback per instance (A12/SOP-5B);
- the multiplication node selection table: every multiply/reduction with its operand dimensions, the resolution chain back to a dimension-fixing node, the chosen definition and port binding, and a probe record for same-dimension vector × vector (I40/§7.5.1);
- the numeric-semantics selection table: every `mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep` (or same-name-different-meaning function) with its semantics class, the evidence, the chosen supply (atomic / library Function instance / explicit construction), the port binding by formal id, and any divergence from the source (I41/§7.5.3);
- for functionized loop bodies: the cross-boundary state table showing each carried variable as both a formal and a return, the tail-Get source, and how cond/loop instances stay branch-private (§7.9.11);
- loop lowering and While connection plan: format→While mapping per source loop, whether any `LOOP_UNROLL_EXCEPTION` applies, the three wired inputs, `cond` direction, max-iteration source, branch isolation, and §7.9.10 template conformance (I36) with any recorded deviation;
- Architecture Pass decisions and any `STRUCTURAL_EXCEPTION` or `FUNCTIONIZATION_BLOCKED` reason;
- layout acceptance, including Sequence spine, statement bands, tree direction, collision status, span, and fingerprint/equivalence checks;
- statement-tree connection and normalized budget: per-edge dy/dx statistics, cross-band edges with their allowed-exception reasons, `nodes_per_statement`, `Y_per_statement`, `X_per_level`, and any `SPAN_JUSTIFICATION` (I37/I38/§7.10);
- layout plan consistency: entry mode (A new build / B existing graph), plan version, planned vs actual coordinates, reconciliation rounds, whether the pass was position-only (I20), and any `POSTHOC_LAYOUT` record (L16/I39);
- actual validation performed and saved artifact path/state;
- explicit unverified items.

## Safety against false completion

Never claim any of the following unless directly verified in the current environment:

- that a historic SD version/tool behavior still applies;
- that a planned position was actually applied;
- that zero planned-overlap means zero visible UI overlap;
- that a Function Graph refactor is equivalent merely because it compiled;
- that an empty tool response means no mutation occurred;
- that a large graph is acceptable merely because it can be laid out without overlap.

When evidence is incomplete, continue independent authorized work and mark the dependent conclusion as unverified.
