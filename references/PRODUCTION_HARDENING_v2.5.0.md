# Production hardening

These checks turn production safety assumptions into executable release gates. Real-project semantic acceptance additionally requires the independent numeric and actual-size checks in `REAL_PROJECT_VALIDATION.md`.

## P1 — Probe isolation

`probe_sd_semantics.py` creates a **fresh** `newUserPackage()` owned by the current probe run. It no longer searches for, reuses, clears, or deletes arbitrary unsaved packages. Cleanup iterates only graph objects explicitly registered by this probe run.

`SAFETY_INVARIANT_001`: the graph fingerprint of every pre-existing user package is captured before the probe and compared again during cleanup. Any detected change fails the probe.

## P2 — Output isolation

The fixed `E:\SD_AI\_probe\out` path is removed. Every run receives a unique `tempfile.mkdtemp(prefix="sd_pp_probe_")` directory, optionally under `SD_PIXEL_AGENT_PROBE_DIR`. No pre-existing directory is cleared. The owner-marker helper refuses to remove directories it did not create.

## P3 — Built-in Function identity

The native probe resolves library Functions only from the exact Adobe `resources/packages/functions.sbs` package. A user Function with the same identifier is ignored. Zero or multiple built-in matches are fatal; there is no global `hits[0]` fallback. `SD_PIXEL_AGENT_FUNCTIONS_PACKAGE` may supply an explicit absolute path for non-standard installations.

## P4 — Version gate

The bundled measured baseline is explicitly 16.0.3. Designer 16.0.5 and unknown versions are `RUNTIME_REPROBE_REQUIRED` until a same-version native probe report exists. This is fail-closed and prevents a stale 16.0.3 measurement from being presented as a 16.0.5 measurement.

## P5 — Behavioral release evals

`python scripts/eval_release.py` runs from the skill root without requiring a caller-supplied `PYTHONPATH` and executes every discovered `unittest.TestCase`:

- static skill validation;
- Python compile checks;
- manifest integrity verification;
- probe safety tests;
- shadowed/duplicate built-in Function resolution tests;
- owned-temp-directory deletion tests;
- version-gate tests;
- While `-1` policy separation tests.
- coordinate-policy tests and strict probe-report validation, including expected semantic matches;
- manifest file-set equality, so unlisted package files fail the gate.

A release is publishable only when this suite reports `RELEASE EVAL: PASS`.


## Runtime semantic checks

Release acceptance includes a pure-Python runtime-semantic policy layer and behavioral evals for normalized PP coordinates, Set→Sequence value transport, conservative pure terminal roots, `SAFETY_INVARIANT_002`, and the Sequence-vector `mul` broadcast rule. Known main-thread-hang topology is statically rejected rather than probed automatically. These static checks are not a substitute for the real-project numeric oracle.
