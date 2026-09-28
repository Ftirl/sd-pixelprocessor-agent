# Substance Designer compatibility matrix

This file separates **Adobe-documented capability** from **same-version native measurements**. The skill may use official documentation as documentation evidence, but a measured semantic baseline is only `VERIFIED` for the exact Designer version that produced the native cook/readback result.

| Designer | State in this release | What the agent may do |
|---|---|---|
| 16.0.3 | `VERIFIED_BASELINE` | Reuse the bundled native numeric/While measurements, subject to the normal target-graph checks. |
| 16.0.5 | `RUNTIME_REPROBE_REQUIRED` | Read-only analysis and planning are allowed. Before a mutation relies on version-sensitive measured semantics, execute `scripts/probe_sd_semantics.py` inside that 16.0.5 session and keep the resulting `probe_report.json` as evidence. |
| Any other/unknown version | `RUNTIME_REPROBE_REQUIRED` | Same fail-closed rule as 16.0.5. |

## Why 16.0.5 is gated

The bundled native measurements are from Designer 16.0.3. No 16.0.5 cook result is bundled; version-sensitive claims stay unverified until a same-version native probe succeeds.

## Runtime gate

1. Detect the current Designer version when possible.
2. If the exact version is `VERIFIED_BASELINE`, the matching baseline may be reused.
3. If the version is missing or marked `RUNTIME_REPROBE_REQUIRED`, execute the native probe before relying on measured numeric, mixed-dimension, While, or `$pos`/`$size` behavior for a mutation.
4. A failed/incomplete probe remains `UNVERIFIED`; never silently fall back to 16.0.3 as if it were same-version evidence.
5. The probe report records the detected Designer version and exact `functions.sbs` path.

## While capability vs safety policy

Adobe documents that While `Max iterations = -1` disables the maximum-iteration counter. Treat that as an **engine capability**, not the Agent default. The default remains a finite explained cap; `-1` is permitted only when the exit condition is demonstrably bounded or the user explicitly requires it, and the risk is recorded.

## Upstream references

- Adobe APSB26-115 (16.0.5 update): https://helpx.adobe.com/security/products/substance3d_designer/apsb26-115.html
- Adobe Function Graph Control / While documentation: https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/nodes-reference-for-substance-function-graphs/atomic-function-nodes/control-nodes



## Runtime-semantic requirements

In addition to the exact-version probe gate, all generated graphs apply `RUNTIME_SEMANTICS_BASELINE_v2.5.0.md` RS1–RS6. `$pos` follows Adobe's documented normalized PP behavior; `$size` is treated as pixel dimensions only when the current context or `coord_size_x` probe confirms it, otherwise an explicit size source is required. `SAFETY_INVARIANT_002` is fail-closed and must not be automatically probed in a working production session because the known failing topology can hang the Designer main thread.
