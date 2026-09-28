---
name: sd-pixelprocessor-agent
description: Analyze, create, repair, refactor, validate, and lay out Substance 3D Designer Pixel Processor and Function Graphs. Use for shader migration, While and Set/Sequence/Get semantics, Function Graph extraction, version-aware native probes, and code-structure layout. Do not use for unrelated Painter or ordinary material-authoring tasks.
---

# SD Pixel Processor Agent

Use this skill for Substance 3D Designer Pixel Processor and Function Graph work.
The current execution specification is:

`references/SD_PixelProcessor_AGENT_SPEC_v2.5.0.md`

Read only the sections needed for the current task, then expand when a dependency requires it. For real-project failure gates and evidence limits, use `references/REAL_PROJECT_VALIDATION.md`, `references/MORPHING_RETEST_GATES.md`, `references/SUN_SHOWER_RETEST_GATES.md`, `references/CRATE_AT_DUSK_RETEST_GATES.md`, and `references/DESCENTE_INFINIE_RETEST_GATES.md`; measured examples are not universal API contracts.

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

- Always: §0–§3. For GLSL/Shadertoy migration or builder/layout failures also read the relevant project gates in `references/REAL_PROJECT_VALIDATION.md`, `references/MORPHING_RETEST_GATES.md`, `references/SUN_SHOWER_RETEST_GATES.md`, and `references/CRATE_AT_DUSK_RETEST_GATES.md`.
- General graph analysis/repair: §4, §5, §7, §9.
- Large graph or reusable-function work: §4.5 A1–A11, I21–I25, SOP-5A, §7.7, §10.
- Loop/state work: §4.2, SOP-3, SOP-3A, §7.2–§7.4, `references/WHILE_OFFICIAL_BASELINE_v2.5.0.md`, relevant D rules in §8.
- Loop format lowering / While wiring: N24–N26, I32–I36, W11–W16, SOP-3A, §7.9.1–§7.9.10, D26–D30, §11.6.
- While wiring template (default form for new/repair work): **§7.9.10** (role list, port-level connection chains, semantic conventions, geometry, template preconditions) + I36 + `WHILE_OFFICIAL_BASELINE_v2.5.0.md` §3.3.
- Statement-tree connections + span/node budget: **§7.10** (Set → statement Sequence → local value consumers → pure terminal, allowed/forbidden wires, measured geometry, normalized span in §7.10.4, node-count budget in §7.10.5, read-only statistics template) + N26, W15–W16, I37–I38, L14–L15, D31–D32, `§11.7`.
- Function Graph/interface work: §4.1, SOP-4, SOP-5A, §7.1, §7.7.
- **New build / source migration (functionize first, then assemble)**: **A12 + SOP-5B** (source function table → interfaces → bottom-up function creation with per-function I1/I2/I9/I10/I23 → instance assembly with I11 → main-graph statement structure), plus `§7.9.11` when a loop body is functionized. Use A8 only for repairing an existing graph.
- Descente retest issues in a new GLSL migration: `references/DESCENTE_INFINIE_RETEST_GATES.md` DI1–DI8 (pre-caller Function numeric gate, precreation Sequence-spine plan check, undefined components, dual time channels, alpha-preserving export, diagnostic-encoding preflight, loaded-package save identity, proved body-entry break hoist).
- Layout-only work: I13/I13b/I20/I30, **I37/I38/I39**, SOP-8 (mode A new build / mode B existing graph), §10 (incl. L2–L4 and L12–L16), plus Architecture Gate rules from §4.5. Use `scripts/layout_intelligence.py` to check planned and read-back statement geometry.
- Built-in function semantics, availability and lookups (on demand): `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md` plus `scripts/lookup_sd_function.py` — consult it whenever a math function's SD identity, ports or exact semantics matter. For measured numeric/loop behaviour (including what SD silently does wrong) read `references/NATIVE_PROBE_RESULTS_v2.5.0.md` and run `scripts/probe_sd_semantics.py` for the current environment. For the **verified library catalogue** (171 built-in Functions, verified node-by-node against the shipped package) use `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md` / `references/library_functions_v2.5.0.json`, and regenerate with `scripts/dump_library_functions.py` + `scripts/verify_library_functions.py` when the SD version or package differs.
- Runtime semantic baseline: `references/RUNTIME_SEMANTICS_BASELINE_v2.5.0.md` (RS1–RS6, `SAFETY_INVARIANT_002`) and `scripts/runtime_semantics.py`.
- Runtime version safety / production hardening: `references/COMPATIBILITY_MATRIX_v2.5.0.md`, `references/PRODUCTION_HARDENING_v2.5.0.md`, `scripts/check_compatibility.py`, and `scripts/eval_release.py`.
- GLSL/HLSL migration: SOP-0A, §4.3, §7.3–§7.10, **§7.5.1** (mul/mulscalar selection table), **§7.5.2** (atan2/vector2/cartesian official semantics), **§7.5.3** (numeric semantics: mod/fmod/round/frac/trunc/sign/clamp/step/smoothstep), relevant diagnostics in §8, plus `REAL_PROJECT_VALIDATION.md`.
- Time-driven graphs, vector assembly, library availability, diagnostic taps, or branch-heavy shader migration: `CRATE_AT_DUSK_RETEST_GATES.md` plus the relevant §7.5/§7.6/§7.11 sections. Apply the project-tested gates in the current graph/version, not as universal engine claims.
- Final delivery: §9 and SOP-9.

If a task crosses categories, load all relevant sections rather than applying one section in isolation.

## Non-negotiable execution rules

These are a compact routing summary; the full rules in the reference remain authoritative.

- Do not call `arrange_nodes` as the layout solution.
- Do not hand-edit `.sbs` XML as the creation/repair deliverable. Creation and modification must be performed through Substance Designer and saved by SD when live execution is authorized.
- `MANIFEST.json` intentionally excludes itself because a file cannot stably contain its own size/hash. Release validation compares the manifest with every other shipped file and verifies those hashes; `N` manifest entries for `N+1` on-disk files is correct only when the sole omission is `MANIFEST.json`.
- Validate a definition against **the target graph's** `getNodeDefinitions()` immediately before each `newNode`; compositing and Function Graph definition sets differ, and a bad id produced an empty MCP result in the Sun shower run. Validate real port ids/types before connecting nodes. After an empty response, read the exact graph and stage marker before retrying.
- **Every source loop format lowers to a structured `While`** (`for`, `while`, `do-while`, `for(;;)`, nested, `break`/`continue`, macro-expanded). Never keep a "for-like" structure, never simulate a loop with a plain DAG chain, and never silently unroll: unroll requires one of the §7.9.8 conditions plus a recorded `LOOP_UNROLL_EXCEPTION:<reason>`.
- **Plan While connections before wiring, then assert them.** `init` / `cond` / `loop` must each have a real source connection, `cond` must be a bool exit condition (continue conditions are inverted), and `cond`/`loop` closures stay branch-private. `__constant__` uses a finite explained cap by default; Adobe supports `-1` as an unlimited engine mode, but the Agent may use it only when the exit condition is provably bounded or the user explicitly requires it, with the risk recorded. Port names are fixed but types are polymorphic — read the instance, never the definition default.
- **Build While in the §7.9.10 template form by default**: Init holds only initial values, `cond` only reads (never writes, never shares a Get instance with `loop`), every `set.value` starts from a freshly created Get, the Body spine's `seqlast` carries an independently created tail Get, constants stay private per statement/branch, and the three sub-regions stay intact. Deviations require recorded reasons (I36), and the template preconditions (real output node, no dangling Get, PP wired to a compositing output) must hold before claiming delivery.
- **Function formals and loop-carried states need disjoint names** (`SUN_SHOWER_RETEST_GATES.md`): a Function formal `p` shadowed a carried `p` in the measured `fbm`, freezing its input despite structurally valid While wiring. Check name intersection in the IR, rename the state (for example `q`), initialize it from the formal, and verify later iterations numerically. If a conforming While still fails, bisect its body and instance call rather than declaring While broken.
- **Do not confuse a Sequence spine with Statement dataflow** (RS2/N26/W15/I37): CRATE built its Sequence after all expressions and still wired previous `Set` outputs straight into lower statements. For a user-selected Statement graph, anchor `Set(x)` on the earlier Sequence `In` path; the lower fresh typed `Get(x)` must feed an expression on the same reachable chain's later `Last` branch. A Get has no Sequence input port: its **output/consumer path** must join that later branch. Check actual ports, reachability, same scope/name/type and a nonzero changing native case; top/bottom placement or matching names alone prove nothing. A historical Get=0 observation did not establish the precise branch wiring, so first diagnose missing later-branch membership rather than blaming Get. Never route an old Set/RHS output across bands; Sequence-value transport is only an approved, numerically verified exception.
- **Span and node-count budgets are structure-normalized, not absolute** (§7.10.4–§7.10.5/I38): report `nodes_per_statement`, `Y_per_statement = spanY/statement bands`, `X_per_level = spanX/max expression depth` plus per-edge dy/dx statistics. Absolute `spanY`/`spanX` only trigger a visual-review note; compressing row steps or interleaving statement bands to game the ratios is itself a FAIL.
- **For a new build or source migration, functionize first and assemble second** (A12/SOP-5B/DI1): derive typed source functions and interfaces, create Function Graphs bottom-up, and validate each one **numerically against an independent oracle before the first dependent instance or main PP is created**. Call `check_function_numeric_gate` and `require_verified_dependencies` at that boundary; a post-assembly unit test cannot retroactively satisfy it. A structural/port audit is necessary but not sufficient: the Morphing project passed structural audit while only 3/20 unit cases and 0/5 images passed. Record explicit formals, dimensions, Set/Get order, output readback, source hash, discriminating nonzero/branch cases and native-vs-oracle error. One case per function is a smoke test, not full coverage. Building a monolith first and extracting afterwards is a repair path, not the default for new work.
- **A functionized loop body always keeps the outer `While`** (§7.9.11): the `loop` statement root may be a Function instance, but every state the body updates must be an explicit formal of that function **and** an explicit return; the caller `Set`s the returned state on a Sequence `In` path, and a later caller-side typed Get consumer joins that chain's `Last` path. Never rely on a function-internal `Set` name being visible to the caller — that visibility is unverified in 16.0.3, so treat function-internal `Set` as function-local.
- **Plan the placement before generating, and create every node at its planned coordinate** (L16/I39/DI2, `SOP-8` mode A): the layout plan is pure data derived from the IR (L13 steps 1–4). Before the first `newNode`, call `validate_layout_plan` on each graph and nested execution block; Sequence nodes in one block must share a right-side X column in IR order, Set/Sequence must align by row, private inputs stay left, and planned positions must be distinct. Only then create nodes at planned coordinates, and separately check application with `validate_position_application` and structural readback. Exact application of an invalid plan is FAIL. Generating first and sweeping a global layout afterwards is the existing-graph path (mode B) and requires `POSTHOC_LAYOUT:<reason>` for new work. Reconciliation is position-only, moves whole subtrees/statement bands, and must not become a disguised global re-layout.
- **Reject mirrored statement layouts before placement and after readback.** In Designer canvas coordinates, larger X is farther right. For each statement, assert `x(private input) < x(Set/statement root) < x(associated Sequence)` and `y(root) ≈ y(Sequence)`; Sequence nodes in the same block share a right-side X column and descend in IR order. A final pure output may sit to the right of that spine. If depth increases from producer to consumer, X must increase with depth; using `x = base - depth×step` reverses the tree. Geometry/span/collision statistics and correct pixels do not waive this gate (I30/L2/L12).
- **Angle work uses `atan2` only, and its input is a vector, not swapped scalars** (§7.5.2/T41/I17): SD provides **no single-argument `atan`**; `sbs::function::atan2` takes one float2 input with id **`a`** (label **`Vector`**) and returns the angle in radians between that vector and the horizontal. Adobe's definition states it needs **no x/y swap** as in the usual atan2, and it is the reciprocal of `cartesian`. Assemble the vector with `vector2` (ids **`componentsin`**/`componentslast`, labels `In`/`Last`): `componentsin` is the first component = x = **horizontal**, `componentslast` is the last = y = **vertical**, so source `atan2(y, x)` becomes `vector2(componentsin = x, componentslast = y)` → `atan2`. Map by "which quantity is horizontal/vertical", never by argument-name order, and never by the superseded "feed `p.yx`" guidance (that mirrors the angle). `atan(t)` becomes `atan2(a = vector2(1, t))`; `cartesian`'s port ids have not been read back (no instance in the corpus) and must be read or probed before use. The label `Vector` does not resolve in `getPropertyFromId` — use `a`.
- **Numeric semantics come from two supply sources, and both must be checked before claiming anything is missing** (§7.5.3/N27/I41/D35, branch file `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md`): SD ships **85 atomic** `sbs::function::*` definitions and a separate built-in **Functions** library (`resources/packages/functions.sbs`, **171** function graphs used through **instance** nodes). `round`, `frac`, `trunc`, `sign`, `clamp`, `saturate`, `step`, `smoothstep` and `fmod` are **not atomic** — they exist only in that library, so never conclude "SD has no X" from the atomic list alone. Semantics that bite: GLSL `mod(x,y)` is floor-based while C/HLSL `fmod(x,y)` keeps the dividend's sign — never substitute the atomic `mod` for `fmod` (the library `fmod` says "same sign as a", and the atomic `mod` description does not specify negative behaviour at all: either construct `x - y*floor(x/y)` explicitly or probe first); `round_float1` is `floor(x+0.5)` ("rounds up when decimal is ≥ 0.5"), so half-way negatives differ from round-half-away-from-zero; `sign(0)` returns **1**, not 0; `frac` is `x - floor(x)` (floor-based, unlike `fmod(x,1)`); `step` returns one when **x ≥ a**. Prefer instantiating the existing library Function over hand-building an equivalent, use the formal's `identifier` as the instance port id (never the label), register library instances in the layout/expression tables like any other node, and record a **numeric-semantics selection table** in the IR phase before creating nodes. Look the details up on demand with `scripts/lookup_sd_function.py --name <regex>` (atomic) or `--library --name <regex> --impl` (library), which read Adobe's own shipped files: `resources/documentation/pythonapi/html/_sources/pythonapi/modules/sbs_function.rst.txt` (Label/Description/ports for all 85) and `resources/packages/functions.sbs` (descriptions + implementation graphs).
- **Connection success never proves the types are right** (spec T44/§7.5.3 rules 9–10, §11.11): mixed-dimension wiring is ACCEPTED by the SDK with no error, but the cook result is operator- and operand-order-dependent. The native probes measured silent 0 for `mul(float2,float1)`, swapped `mulscalar`, and `mod(float2,float1)`; a separate 16.0.3 project measurement found that mixed `add`/`sub`/`pow` can instead expose a partial or identity-looking value and that the result shape follows input `a`. None of these are broadcasting contracts. Resolve dimensions from the IR before creating nodes (I40), read every port back after wiring, and treat any plausible-looking mixed-dimension result as invalid evidence until rebuilt with same-dimension operands or the correct scalar node.
- **CRATE retest type/coverage gates** (`CRATE_AT_DUSK_RETEST_GATES.md`): before numeric tests, check Get declaration dimension and scope (I43), vector constructor component order (I42), explicit GLSL scalar broadcast lowering (I16), every source transform application site (I44), and source-derived branch coverage. A passing image or a few hand-picked unit cases do not waive these checks.
- **Do not trust a numeric run until its plumbing is live** (`SUN_SHOWER_RETEST_GATES.md`): reacquire the exact saved package after a reset/unload, never silently replace a missing package, run a known-constant cook each diagnostic round, load owned builders from current source (or invalidate only those modules), and log source hashes. If every independent probe reads zero, check package/output transport before rewriting graph math.
- **A Get takes the variable identifier, never a node alias.** The `__constant__` string on `get_floatN` must be the exact Set/formal/parameter name. Builder handles such as `set_x#1413`, node ids, labels, or aliases are not variable names and can resolve to 0 without an SDK error. Keep `(variable_name, node_handle, dimension)` as distinct fields and assert every emitted Get name against the graph's declared state/interface table.
- **Debug transports must be validated independently.** Do not use the deep tail of a long nested-`ifelse` mux as sole numeric evidence: a 41-level 16.0.3 diagnostic mux produced repeatable wrong tail values even though the plan and brackets were correct. Prefer one channel per cook or a shallow scratch mux; bracket the same level and the deepest level, repeat the value at another level or through the real output path, and downgrade earlier tail readings when the transport later fails. For signed values, `v/scale` clips negatives to zero; use a bounded affine encoding `(v+A)/(2A)` with its inverse, and reject clipped evidence.
- **Drive PP test values through graph parameters, not PP-node port property writes over MCP.** In the 16.0.3 project run, direct PP port-property writes hung twice and the batch silently produced no mutation; graph-level parameters were inherited and verified by calibration. Treat direct port-property mutation as version-specific and unverified unless a minimal current-session probe succeeds.
- **Pixel Processor `$pos` is normalized; `$size`, Y orientation, and effective resolution must be verified** (RS1): record the source coordinate convention. In `rain_text1`, a bottom-origin Shadertoy source required `uv.y = 0.5 - $pos.y`; this is not a universal flip. Compare an asymmetric sample in both orientations and inspect BMP row order. Read back composition and PP inheritance modes, then verify actual cooked/exported width and height before a full-size export; a reported direct PP `$outputsize` write silently left an 8192² result. Do not infer `iResolution` from an unprobed `$size`.
- **Retest-specific parameter and resolution gates** (`MORPHING_RETEST_GATES.md` P1/P2): `$outputsize` uses log2 exponents, so `(5,5)` means 32²; dual Absolute worked in this retest but is not universal. An unconnected PP `#iTime` read 0 while `Get('iTime')` could read a calibrated parent parameter even when `getInputIdentifiers()` was empty. Verify the actual source, inheritance modes, exported dimensions, `$pos` orientation, and `$size` in the current graph; do not assume these observations generalize across versions or projects.
- **Preserve both time channels** (`CRATE_AT_DUSK_RETEST_GATES.md`): `$time` is built-in Engine/Player animation time; custom `iTime` is for manual control and deterministic per-frame Designer cook. Keep both and select an explicit `effectiveTime` (default `$time` for playback, `iTime` for test/manual mode); do not rename one into the other or infer Player behavior from Designer's static `$time`. Verify both nonzero paths and record the selected mode/time for each oracle comparison.
- **Scope time and RGBA evidence to the channels actually tested** (DI4–DI6): for a time-driven build, version-check parent input/PP parameter creation and inheritance, read back both time paths and `effectiveTime`, and cook t=0 plus nonzero manual time; a static t=0 image does not prove animation. For four-channel acceptance, prove the chosen export preserves varying alpha with a known two-value probe; an alpha-flattened BMP supports RGB-only metrics. Before building any diagnostic encoder, use independent-oracle bounds and `preflight_affine_probe` to keep every encoded case away from 0/1 clipping and record the inverse/tolerance.
- **Diagnose loaded-package path mismatches without inventing a new package** (DI7): compare normalized absolute scene paths and resource identity; if a path selector fails, refresh scene info and use only a currently verified package object/index. The index is session state, not a constant; an unknown save outcome requires readback before retry.
- **GLSL matrices need explicit column-to-row translation** (`MORPHING_RETEST_GATES.md` P2): `matN` constructor vectors are columns. For `M*v` dot each transposed row with `v`; for `v*M` dot each original column. Validate each distinct matrix with a non-symmetric numeric case before image comparisons.
- **Use a pure deliverable root by default** (RS3/RS4): bridge a final statement value through a type-preserving pure operator and verify `getOutputNodes()` plus cooked numeric result. `Set`/`Sequence` output behavior differed across the two real projects, including small-probe/full-graph disagreement. Treat the pure-root rule as a conservative construction default, not a claim that Designer can never output a Sequence. A deviation needs a current-session minimal probe and caller-level oracle.
- **Gate PP roots and output reachability before cooking** (`MORPHING_RETEST_GATES.md` P0): in the observed 16.0.3 PP context, marked float2/float3 roots silently produced zero output nodes and black, while float1/float4 worked; ordinary Function Graph roots differed. Read back `getOutputNodes()` and verify the marked dimension in a version-matched probe. Reverse-traverse real edges from the output and require every IR-live pre-loop Set/Sequence and While/control result to be reachable; a same-name Get does not create an edge. Diagnose black output with separate shallow probes before changing math.
- **Acceptance is scoped to the actual source and oracle paths** (`SUN_SHOWER_RETEST_GATES.md`): inventory source sections and top-level branches as ported/omitted/blocked; verify the reference generator's command, branch coverage, row view, resolution, file/source hashes, and same-session reproducibility. A mode name, fossil bitmap, lower flipped MAD, or unit-passing function does not establish full-image correctness. Report partial delivery and image/node-budget holds separately, including the evidence that would lift a hold.
- **Resolve statement bands before placement** (`MORPHING_RETEST_GATES.md` P0): inline constants inherit a unique consumer band; shared/ambiguous or unresolved nodes require an explicit IR decision, never silent band 0. Size bands from the busiest expression depth and validate X-depth and sibling Y separation.
- **`SAFETY_INVARIANT_002`: no external Sequence may feed a While body.** A While body consuming a Sequence produced outside the body has field-tested main-thread hang risk. Reconstruct the value inside the body from body-private constants/formals/verified loop state/pure operators. Do not automatically probe this known-hang pattern in a production session.
- **Sequence-derived vectors do not use `mulscalar`** (RS6): `mulscalar(Sequence(floatN), scalar)` is treated as unreliable. Explicitly broadcast the scalar to floatN and use same-dimension `mul`; this is also the preferred terminal identity form.
- **Verify numeric and loop semantics with a native cook probe** (SOP-0B, T46, `scripts/probe_sd_semantics.py`, measured baseline in `references/NATIVE_PROBE_RESULTS_v2.5.0.md`): build the probe in an unsaved scratch package, mark the result with `setOutputNode`, read back the marked root, cook with `graph.compute()`, export via `sd.tools.export.exportSDGraphOutputs(graph, dir, 'bmp')` (measured **linear** 24-bit), affine-encode expected channels strictly inside `(0,1)` to avoid saturation, select one exact run-owned file, and compare against **two competing semantics** taking the nearest. Measured facts to reuse: atomic `mod` is floor-based (`mod(−0.25,1)=0.75`) while library `fmod` keeps the dividend sign (`fmod(−0.25,1)=−0.25`); `round_float1` = `floor(x+0.5)`; `sign(0)=1`; `step` is inclusive; the §7.9.10 minimal While sums correctly and **zero iterations are well defined** (Init runs, body does not, state survives).
- Do not infer execution order from node coordinates. Get/Set/Sequence/While semantics come from graph execution structure.
- Do not assume a Function Graph can directly read caller-local values. Cross-boundary data must be explicit inputs unless the reference identifies a verified built-in mechanism.
- Do not assume function-instance output ids. Read the actual interface.
- Preserve exact names, including case and `$` / `#` prefixes.
- A successful compile, visible image, or collision-free layout does not by itself prove semantic correctness.
- An empty MCP response is an unknown outcome. Read state and logs before retrying a mutating batch; never equate `{}` with no mutation. For a generated Function, a connected formal and numerically validated call site matter more than a nominal default value.

## Architecture Pass before final layout

For create/repair/refactor tasks, run the Architecture Gate before investing in final layout.

Use A1–A11 and SOP-5A from the reference. In particular:

- graph size, semantic-region size, repeated/parameterized-isomorphic DAGs, and planned layout span can trigger Architecture Pass; after Function extraction, a pre-layout must feed span/repetition results back into Architecture Pass;
- **the A1 numbers are structure-normalized and coupled to Function splitting** (§4.5/§7.10.4–§7.10.5): node count ≥400 triggers Architecture Pass, not an automatic delivery failure. Record concrete typed split candidates (or why none is safe), each candidate's removable caller nodes, replacement instance/glue nodes, projected caller count, new Function count, decision and reason. An authorized safe, count-reducing split must be applied and numerically checked at the Function and first call site, or retained only with a documented structural/scope exception. Recount and re-run the same gate for the caller **and each new Function Graph**; a split cannot merely move an oversized graph. A completed pass permits a single graph through 1199 nodes when other gates pass; 1200–1500 additionally requires readback/cook/layout evidence and is WARN; >1500 is outside the normal single-graph delivery budget without explicit user approval. Independent normalized limits remain: `nodes_per_statement > 24` or `Y_per_statement > 512` / `X_per_level > 384` with a safe extraction point requires restructuring or a recorded exception. Absolute `spanY`/`spanX` are reporting flags only;
- source-code function boundaries and fixed-loop bodies should be evaluated as candidate Function Graph boundaries before blindly inlining everything into one PP;
- repeated structures may differ only by constants or input sources; promote varying constants to function inputs when safe;
- a single large but semantically closed pure-compute region can be extracted even if it appears only once;
- newly created Function Graphs are recursively re-evaluated so complexity is actually reduced rather than moved elsewhere;
- do not delete the original region until the new function and at least the first call site have been validated;
- topology-changing refactors use semantic-equivalence validation, not pure-layout I20 identity;
- **for new builds, the Architecture decision is applied before anything is created**: functions are designed and validated first, then the main graph is assembled from instances (A12/SOP-5B). Applying A1's normalized budget to an assembled graph and then extracting is the fallback repair path (A8), not the default.

If Architecture Pass finds a safe split and the task authorizes structural repair/refactor, perform or plan the split before final layout. If structural modification is not authorized, report the candidate without crossing the user's scope.

## Source-structure lowering before layout

Classify the source before node placement:

For GLSL source, run per-component definite-assignment analysis on the typed IR before choosing constants: intersect defined components at branch joins and flag reads of undefined components with `check_definite_component_reads`. Ask for a migration decision when source behavior is undefined; put that choice into both the target IR and independent oracle. Do not silently treat `vec3 v; v.y=...` as `v.x=v.z=0` (DI3).

- **Statement mode** for imperative code when the user selects A: assignments/state updates become real `Set` statement roots; executable statements are anchored in a `Sequence` chain in source/IR order. Pure sub-functions can still be DAGs. Every source loop format is lowered to a structured `While` with the §7.9 connection plan — a fixed count is not a reason to unroll. Only a recorded `LOOP_UNROLL_EXCEPTION` (§7.9.8) allows unrolling, and then one statement block per iteration is preserved. In a subsequent statement, use a fresh same-type `Get(name)` in the lower band **whose consumer reaches the later `Last` branch of the same ordered, output-reachable Sequence chain**; the producing Set is on its earlier `In` path. This is not a literal Sequence→Get input wire. Check scope/name/type and a nonzero changing read. On failure, inspect port topology and output reachability before considering a documented Sequence-value exception; never quietly route an old Set/RHS output across bands. See §7.10 and RS2.
- **Expression mode** for genuinely side-effect-free single-expression Function Graphs, or a straight-line imperative graph only when the user expressly chooses B with the stated loss of structural fidelity; record `USER_SELECTED_DAG` and mark structure preservation as a deliberate deviation, not PASS. A stateful/dynamic loop cannot be turned into pure DAG merely by choosing B; resolve that conflict with the user before building.

Do not accept “the generated graph has no Sequence” as evidence that Expression mode is appropriate. A numerically equivalent pure DAG is not a structure-preserving final translation of imperative source; it requires the user's explicit B choice, `USER_SELECTED_DAG`, and a non-PASS structure-fidelity verdict. If the environment truly prevents Set/Sequence representation, separately record `STRUCTURAL_FALLBACK`.

Set liveness is semantic, not cosmetic: a Set must be on a reachable Sequence/output/real-consumer path. A same-name Get does not by itself make the Set live.

### Variable-version boundary

Treat every `Set` as a code-level variable-version boundary.

- `Set x = expr` consumes the RHS expression for that statement. The RHS wire terminates at the Set.
- A later statement consuming x uses a fresh typed `Get("x")` in its own band. Assert `Set(x)` is on the Sequence `In`/earlier path and the Get's consumer is on the later `Last` path of that same reachable chain; then check name, type, scope and a nonzero changing native case. Top/bottom geometry and a matching name alone are not execution proof. If the read fails, first repair missing later-branch/output connectivity; only a topology-correct, still-failing case may motivate an explicitly approved and numerically verified Sequence-value fallback—not the preceding Set output.
- Never carry the pre-Set RHS node, Set.value source, or another old-version node across later statement bands merely to save a Get.
- For `x += y`, the RHS starts with a scope-valid `Get(x)` on the appropriate later branch. After `Set(x)`, a later statement uses a new `Get(x)` only after the `In`→`Last` topology, same-scope read and output reachability are verified; otherwise repair/probe before considering an approved Sequence-value exception.
- Use Sequence/control-flow structure to prove Set-before-Get order. Do not infer variable versions from node coordinates.

This is both semantic and visual: later statement bands should show `Get(x)` leaves rather than long cross-row wires from earlier assignments. The measured reference package (`OKColor_LCH.sbs`, §11.7) shows this profile: 285 `get→op` read edges versus only 36 direct `set→op` edges, with just 7.8% of edges crossing more than one row step.

## While loop baseline

Use `references/WHILE_OFFICIAL_BASELINE_v2.5.0.md` and §7.3–§7.4 plus §7.9 as the authoritative loop model.

- Adobe officially supports While in Function Graphs and identifies Pixel Processor as a primary loop use case. Do **not** treat the Accretion per-pixel While failure as a universal engine restriction.
- **Every source loop format defaults to a structured While**: `for`, `while`, `do-while`, `for(;;)`, nested loops, `break`/`continue` loops, macro/template-expanded loops. Unless a recorded §7.9.8 `LOOP_UNROLL_EXCEPTION` applies, one source loop maps to one While and nested loops get one While per level. Never keep a for-like structure or silently replace a loop with a plain DAG chain.
- `Init` runs once. `Exit Cond.` is a **stop condition**: True stops; False proceeds to the body. Variables retain values across iterations. Migrating a C/GLSL *continue* condition requires inverting it.
- State naming is expressed with Set/Get; body-local Sequence places a Set on its earlier `In` path and the next Get consumer on its later `Last` path. Multiple writes or read-after-write inside Init/Body must maintain this ordered, output-reachable chain. Never feed an outer Sequence into a While body (SAFETY_INVARIANT_002).
- Nodes belonging to Exit Cond. and Loop Body are branch-private: do not share those node instances with outside branches. Recreate Get/constants/expressions/instances where needed.
- **Connection plan (spec §7.9.3) and template form (§7.9.10)**: `init`/`cond`/`loop` are planned, then wired, then asserted; check the real port ids on the instance (definition `sbs::function::while`, inputs `init`/`cond`/`loop`/`__constant__`, output `unique_filter_output`). Port names are fixed but types are polymorphic, so verify types per instance. `__constant__` is the max-iteration property, not a connection. Unless a recorded reason says otherwise, the wiring follows the §7.9.10 template: Init = initial values only, `cond` = bool comparison reading a private Get with the bound constant on `a` and the live state on `b`, `loop` = (nested) Sequence spine ending in an independently created tail Get.
- **Control-flow lowering**: `do-while` keeps a first-pass flag so the body always runs at least once; `break` uses an exit flag folded into `cond` plus `ifelse` wrapping of the following statements; `continue` wraps the remaining statements and a `for` increment must stay outside that wrapper, otherwise the counter never advances.
- A `break` that is the first executable body action may instead be folded into Exit Cond only with DI8's proof: pure condition, same loop-entry state, no prior effects, and correct loop target; record `BREAK_HOISTED_TO_EXIT_COND`. A preceding assignment, side-effecting condition, or nested target uses the standard flag path.
- To read final loop state outside, prefer an explicit pure return/While output or a post-While statement value path whose ordering has been verified. Do not assume a bare same-name Get reflects the loop write, and never wire a Body-internal node outside. The While output is only the last Body result.
- Pixel Processor runs one Function Graph independently per output pixel. Loop state is per-pixel invocation; it is not memory shared between neighboring pixels.
- Fixed iteration count alone is **not** a reason to unroll. While is the mandatory default target; unroll requires an explicit §7.9.8 condition and a recorded `LOOP_UNROLL_EXCEPTION:<reason>`. Functionize a large body either way.
- Derive `Max iterations` per loop and record its source (static bound, provable upper bound, or explained safety cap). `Max iterations = -1` is not the default for generated graphs because Adobe warns it can create an infinite loop and make Designer unresponsive.
- Probe only undocumented/ambiguous behavior (for example zero-iteration direct output) or a current graph that still fails after the documented constraints are satisfied.

## Final layout model

The final layout for a user-selected Statement-mode graph is a code-structure tree, not a globally compressed DAG. A user-selected Expression-mode graph follows its own pure-DAG layout; the two modes are locked per graph before creation.

For each executable block:

1. Put the `Sequence` chain on a stable right-side vertical spine.
2. Order the Sequence chain from top to bottom according to source/IR execution order.
3. Place each `Set`, return expression, or control statement root immediately to the left of its corresponding Sequence node and on the same row when the reference requires it.
4. Expand that statement's value/dependency expression recursively to the left as a tree.
5. Single-input chains extend mainly leftward; multi-input siblings branch vertically while remaining within that statement's band.
6. Each top-level statement owns a `statement band`; private expression trees from different statements must not be interleaved merely to save space or shorten wires.
7. Nested init/cond/loop or branch blocks use their own local structure and, when applicable, their own local Sequence spine. While subregions are ordered `init → cond → loop` from top to bottom, left of the While; `__constant__` is a node property, not a fourth subtree.
8. Shared DAG nodes remain single real nodes. Treat them as explicit shared exceptions; do not duplicate logic for visual symmetry.
9. If a shared or single-statement region becomes too large to read as a tree, return to Architecture Pass and evaluate Function Graph extraction instead of flattening the layout into an arbitrary 2D packing.
10. Resolve collisions by moving whole subtrees or statement bands, then snap to the chosen relative grid and re-check tree direction, Sequence order, row relationships, and collisions. Collision/span checks are per graph; Function Graph coordinate spaces are independent.
11. If the pre-layout still exceeds Architecture thresholds, return to Architecture Pass before applying coordinates; `planned overlap = 0` is not sufficient.
12. **Row/column steps are structural, not cosmetic** (L14): row step 192/224/288 and column step 128/160/192/224, snapped to 32. Never shrink the row step below 192 or interleave bands to shrink the bounding box; report `nodes_per_statement`, `Y_per_statement`, `X_per_level`, and per-edge dy/dx statistics instead of raw span (I38).
13. **No cross-band wires** (L15/N26/I37): every link stays inside one statement band (dy = 0 preferred, ≤ one row step). A post-Set cross-band read uses a fresh typed Get whose consumer joins the later branch of the same reachable Sequence chain; a bare fresh Get is not proof without this path. Allowed exceptions only: Sequence spine chaining, control-block structure edges, function-instance fan-out, registered L8 sharing, and explicitly approved Sequence-value transport — each listed with a reason.
14. **The plan comes first and the nodes land on it** (L16): for a new build, the complete layout plan (statement bands, spine column, per-node role/depth/planned coordinate, grid origin, sub-regions) is finished and validated (L12/L14/L15, zero planned overlap, predicted cross-band edges) before any node exists, and each `newNode` is immediately followed by `setPosition` to that planned coordinate. After creation only geometric reconciliation is allowed — position-only, whole subtree/statement band at a time, then re-snap and re-check collisions (I20/I39).

Apply the same left-to-right assertions to the **read-back** coordinates. `spanX`, `X_per_level`, collision counts, and numeric image comparisons do not reveal a globally mirrored graph; failure of the Sequence-right assertion means layout FAIL even when logic is PASS.

Never make compactness the primary criterion. Source/IR structure has priority over shortest wires, global symmetry, or minimum total height.

## Field-tested builder guards

For migration/build tasks, apply these guards unless current-environment evidence supersedes them:

- Create and register all atomic nodes and Function instances before the builder's bulk wiring phase; then assert final output source connections.
- For every While, assert after wiring that `init`, `cond`, and `loop` each have a real source connection, that `cond` terminates in a bool, and that `__constant__` follows W7: finite and explained by default, or `-1` only under the explicit bounded-exit/user-request exception; `cond`/`loop` closures must not share node instances with other branches or with the region outside the loop. Build it in the §7.9.10 template form and check I36 conformance, including the template preconditions: the graph output is **marked** (`getOutputNodes()` non-empty — `setOutputNode` flags an ordinary node; there is no output node type), no dangling Get remains, and the PP node is wired into a compositing output when the PP is meant to deliver a result.
- **`mul` vs `mulscalar` is a forced choice with fixed, non-swappable ports** (§7.5.1/T40/I40/N20): `mul` inputs are id **`a`/`b`** (labels `A`/`B`) and accept same-dimension operands including float1 × float1 **and same-dimension vectors** (confirmed); `mulscalar` inputs are id **`a`/`scalar`** (labels **`Vector`**/**`Scale`**) and the order **cannot be swapped** — the vector always goes to `a`, the scalar always to `scalar`, regardless of how the source writes it. Only the lowercase ids resolve in `getPropertyFromId`; `A`/`B`/`Vector`/`Scale` return None, so never use a label as a port id, and there is no `input1`/`input2`.
- **Operand dimension must be traced, not read back**: resolve it from a node that actually fixes it (`get_floatN`, `const_floatN`, a function formal, a PP `#` port, a swizzle selection, or `dot`) or from the source IR; polymorphic nodes (`add`/`sub`/`mul`/`div`/`pow`/`lerp`/`ifelse`) must be resolved recursively. Atomic `sbs::function::length` was absent in the 16.0.3 preflight; check the library `length_vecN` or use a verified `sqrt(dot(v,v))` construction. Never decide from the node definition's default type, the instance's port type readback, or an upstream node's type string: in the measured corpus 21 of 24 `mulscalar.a` ports report Float2 while their upstreams read back as generic `Float`, and `dot` reports Float2 while its sources are Float3. Produce a **multiplication node selection table** in the IR phase, before creation. Different-dimension operands are a source/IR type error to fix, not a node-choice problem; `mulscalar(a=float1, scalar=float1)` silently returns 0 in 16.0.3 (T33), and mixed-up selection shows up as wrong values with a successful compile (D34).
- If the design depends on `$pos/$size`, Function-instance behavior, export/readback conventions, or a **While behavior not explicitly covered by the official baseline / currently failing in this graph**, run the minimal SOP-0A capability probe. Do not probe merely to re-prove documented While semantics.
- Shared non-leaf DAG nodes must be fully laid out on first encounter; only later references reuse their position. Every Function instance participates in the expression/layout registry.
- After wiring, run the §7.10.6 read-only statistics: per-edge dy/dx percentiles, cross-band edge count (dy > 288) with its exception list, `nodes_per_statement`, `Y_per_statement`, `X_per_level`. An unallowed cross-band edge must be rebuilt using a local Get consumer on the later branch of the same output-reachable Sequence chain before delivery (I37/RS2).
- When classifying a graph as too large or too tall, use the normalized ratios first (§7.10.4–§7.10.5). Node count alone never proves a graph is badly structured: the referenced package ships 15 Function Graphs up to 368 nodes / 43 statement bands as an acceptable statement-tree form (§11.7).
- For a new build, never start bulk creation before the layout plan exists; a creation helper must take the planned coordinate as an argument and apply it immediately (`newNode` → `setPosition`). A creation pass that leaves nodes at default positions for a later sweep is an I39 finding.

## Mutation workflow

For authorized create/repair/refactor work, follow this order:

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
