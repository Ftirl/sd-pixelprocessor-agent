# Operational evidence, recovery and release

Behavior revision: `BEHAVIOR_REVISION`. Runtime measurements remain tied to `VERSION` and their exact Designer version. These tools validate evidence and decide safe next steps; they do not provide a watchdog, restart Designer, automatically recover unsaved work, or implement a host frame scheduler.

## Entry and adapters

Before mutations, obtain the exact target, a semantic readback, a durable checkpoint and current authorization. `graph_evidence.graph_snapshot` reads nodes, values, types, input edges, roots, instance identities and nested property graphs. `package_snapshot` enumerates recursively; unsupported resource/value types or SDK exceptions fail closed as unavailable evidence. Add a tested adapter for unsupported types; never fall back to names, empty lists, `repr()` or disk contents when unsaved state matters.

`runtime_safety.snapshot_user_packages` and the native probe use this same implementation. In exec-based SD calls, first put this installed Skill's absolute `scripts` directory on `sys.path`, then import its helpers; do not assume `__file__` belongs to the executed file. Confirm module `__file__` if a module of the same name was previously imported, and reload only the intended module when testing a revision. A pre-existing package cannot be exempted by labeling it run-owned.

Coordinates are excluded from semantic fingerprints and separately validated. Render caches/thumbnails are not semantic inputs. A complete artifact identity includes external dependency content hashes, not merely URLs; instance URLs in local graph snapshots do not attest external package contents. Record the dependency closure separately. Unknown coverage is not PASS.

## Verified function lifecycle

`workflow_guards.EvidenceRegistry` replaces name-only release permission. Its identity has package, resource, source_hash, graph_hash, interface_hash, environment_hash and cases_hash. Canonicalize package paths/resource URLs and include all numeric-sensitive settings in environment_hash. Build current identities from fresh readback and the actual source/test definitions, not by copying old records.

Set numeric_record.name to the exact resource key and record a nonempty required_paths inventory from source control flow (use an explicit straight-line path for branchless functions). Compute identity.cases_hash with case_evidence_hash(numeric_record), then bind numeric_record.identity_key using identity_key(identity). The registry checks both bindings and covered paths. Call `verify(identity, numeric_record, dependencies, current)` only after the strict numeric gate; dependencies use `(package, resource)` keys. Then call `require_verified_dependencies(caller, dependencies, registry, current=current)` immediately before dependent creation. Old name lists now raise CONTENT_BOUND_EVIDENCE_REQUIRED; migrate callers rather than catching and bypassing it. Source/interface/graph/environment/cases changes invalidate evidence. Dependencies are recursively checked; `invalidate` propagates to callers. A pure layout edit may reuse numeric evidence only when semantic hashes remain unchanged.

`check_build_stage_order` remains an event-order audit, not an artifact identity proof. `function_modified` invalidates its named stage; unknown event kinds fail. Record all changes, including edits outside the Agent. The registry must be rebuilt from trusted evidence after restart; an in-memory PASS set is never a checkpoint.

## Persistent operation journal and stopping rules

Serialize all SD writes. Acquire WriterLease on a project/session-wide canonical lock path before any operation; use the same path across runs. One project/session writer owns the operation stream; tool-call serialization is not a cross-process lock. Persist run_id, operation_id, target, before_hash, expected_after_hash and checkpoint with `OperationJournal.begin`, which refuses an existing operation file. `prepared → inflight → committed`; lost replies use `inflight → unknown → reconciled/conflict`. Expected-after comes from the planned semantic change, not from an arbitrary observed result. Use OperationJournal.commit(target=..., observed_hash=..., output_checks=...) only after fresh target readback matches the plan and required outputs pass; transition("committed") is rejected.

Recovery decision table:

| Trigger | Immediate action | Stop / recover / acceptance |
| --- | --- | --- |
| Empty reply, timeout or disconnect | Stop dependent writes; inspect bounded logs, stage and host liveness | Read-only state reconciliation; never blindly replay the batch |
| Observed expected-after hash | Operation likely applied | Verify output; record reconciliation, do not create duplicate nodes |
| Observed before hash | No observed semantic change | Replan under a new operation ID after confirming host idle; do not reuse old inflight request |
| Different target or third hash | Preserve checkpoint and current unsaved state | Conflict; compare user edits and partial changes before authorized repair |
| Host unresponsive | Stop submitting more requests | Keep evidence; do not infer crash or kill/restart without authorization for unsaved-state consequences |
| Save/export failure | Preserve live state and last known valid file | Check path/access/space; save a new owned checkpoint if authorized, verify reload and output before replacement |
| Recovery interrupted | Read journal and target again | A durable journal is evidence, not proof of completion; reconcile before progressing |

Use a configurable timeout per operation based on measured small cases. A timed-out MCP call may still be running. At most one retry after a diagnosed, resolved cause and readback proving the first mutation did not apply; another failure requires a new diagnosis, not repeated identical batches. Read-only status retries can be bounded separately. Never assume the SDK can cancel compute. Do not run known hang topologies to test a recovery policy.

`OperationJournal` is single-writer and atomic per update; it is not a general distributed lease. Before resuming from another process, establish exclusive ownership and host idle state. Crashed or corrupt records require reconciliation, never silent overwrite.

## Provisional visual assembly

Use LARGE_PROJECT_ASSEMBLY §4 and `check_visual_decision`. Bind authorization to scope and evidence_key, record residuals, images, untested conditions and reopen triggers. A prior valid user choice is reused; scope/evidence drift triggers reassessment. Missing features and safety failures cannot be waived by the precision decision. Structure, state order, transport, native cook, finite values and range must pass. This branch never calls the strict gate with a fabricated verified set.

Completion states: PROVISIONAL_VISUAL_ASSEMBLY → VISUAL_ACCEPTED_NUMERIC_PENDING (tested image accepted, residual retained) or STRICT_VERIFIED (all applicable numeric, temporal and image gates truly passed). No automatic promotion from visual acceptance. Full numeric promotion uses a fresh EvidenceRegistry entry. A new feature omission requires a separate user decision.

## Performance and frame state

Before cook, record dimensions, iteration caps, expected output, measured baseline, elapsed-time budget and available resource indicators. Escalate through small diagnostic resolution to the authorized target. `cook_budget_action` stops escalation on timeout, nonfinite results, resource pressure or unresponsive host. It never changes quality automatically; final acceptance must run the target conditions. If memory information is unavailable, mark it unknown and choose a conservative bounded stage rather than inventing a healthy metric.

Cross-frame work requires an explicit host scheduler. `check_frame_commit` guards consecutive frame ID, previous-output hash, configuration identity, ordered complete pass list, output acceptance and output hash. Persist accepted history only after all checks. Failed/partial frames do not replace history. Resolution/camera/config changes require a recorded reset transaction and reinitialized history; do not force acceptance by retaining the old configuration hash. Duplicate/skipped frames fail. These checks are not proof of actual pass contents; native per-pass outputs and multi-frame results remain required.

## Multi-PP and layout refinements

`assembly_contracts.check_transport` compares producer/consumer field/channel/range, size, format, encoding, pixel center, filter, wrap, mip, orientation and frame snapshot. It rejects overlapping channels and unsafe full-range uint32 in identity RGBA32F. Contracts model a single image; atlas regions and multiple returns use separate contracts with explicit addressing tests. Do not equate matching declarations with observed transport: run sentinel samples and a native source-function fixture.

Run baseline `validate_layout_plan` first, then `check_compact_layout` for selected private leaves, rigid complex subtrees, unchanged unrelated nodes and logic hash equality. Apply through SD, read back, rerun both checks and compare outputs. This adds a deterministic acceptance checker, not an automatic optimizer. The bundled KSR positions are real user examples, not a universal grid or coordinates to copy. FTP rows and archived raw outputs are historical regression evidence, not a new runtime probe.

## Transactional Skill installation

Both install wrappers delegate to `install_transaction.py`; set SD_PIXEL_AGENT_PYTHON if Python is not on PATH. Verify source manifest, copy only listed files to a sibling stage, verify it, move existing installation to a unique backup, swap the verified stage and verify again. Exceptions after backup trigger restoration. Keep failed stage/backup for diagnosis. The install-lock prevents competing installers; after process termination, inspect its recorded stage/backup/target identities before manually completing or restoring. Never delete a stale lock without reconciliation.

Backup restoration failure is a blocking incident: retain backup and lock evidence and report exact paths. Portable rename is not a multi-directory atomic transaction; the lock/journal and backups close ordinary exception paths, not arbitrary power-loss guarantees.

## Validation boundaries and maintenance

Release checks cover manifests, helper behavior, fault injection and project-derived fixtures. Native readback results, numeric cooks and model decision behavior have separate verdicts. Do not report all three PASS from unit tests. Consult `evals/fixtures` only when running its tests. The entrypoint routes to detailed EXECUTION_RULES, keeping a single copy of long operational rules. Update the behavior revision for policy/tool changes while leaving historical runtime baseline files intact.

## Minimal content-bound caller example

```python
# source/interface/environment hashes and snapshots must be freshly measured.
from graph_evidence import digest
from workflow_guards import EvidenceRegistry, identity_key, case_evidence_hash
from project_validation import require_verified_dependencies
record["required_paths"] = source_path_inventory
identity["cases_hash"] = case_evidence_hash(record)
record["identity_key"] = identity_key(identity)
key = (identity["package"], identity["resource"])
current[key] = identity
registry = EvidenceRegistry()  # rebuild dependencies first after restarting
registry.verify(identity, record, dependencies, current)
require_verified_dependencies("main", [key], registry, current=current)
```

Do not derive expected values from native outputs merely to satisfy this example. All inputs above are caller-supplied evidence; helpers verify consistency, not honesty or external facts. If no source oracle can be run, use the explicit provisional decision workflow, not a fabricated numeric record.

## Requirements to tests

| Audit item | Executable layer | Evidence / remaining boundary |
| --- | --- | --- |
| A01 snapshot blindness | graph_evidence + runtime_safety | Content-mutation and unreadable-type controls; live project readback recorded outside release package |
| A02 stale verification | EvidenceRegistry + require_verified_dependencies | Artifact/case/branch mismatch and transitive dependency controls |
| A03 interrupted operations | OperationJournal + WriterLease | Lost reply, restart, duplicate, conflict and commit controls; no forced-crash SD test |
| A04 provisional path | check_visual_decision | Reused authorization, scope drift, missing feature and safety controls; model conversation behavior not automatically certified |
| A05 layout / multi-PP | check_compact_layout + check_transport | User KSR positions and archived FTP native raw regression; optimizer implementation remains caller-owned |
| A06 performance / frames | cook_budget_action + check_frame_commit | Timeout/unknown health and incomplete/reordered/history-reset controls; host scheduling remains explicit |
| A07 release rollback | install_transaction | Copy/swap/restore failure injection and persistent recovery evidence |
| A08 maintainability | routed EXECUTION_RULES + revision + release tests | Route/reference and entrypoint size checks; tests are not universal behavior coverage |
| Single-file delivery | check_portable_delivery | All closure categories and isolated reload required; actual scanning/cooking is still native work |
