"""Host-independent readiness checks for SD graph plans and export reports.

The checks deliberately avoid claiming that a static plan or BMP header proves
native cook correctness; callers still need an independent numeric oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Mapping
import hashlib
import math
import ntpath
import os
import struct


@dataclass(frozen=True)
class StateRead:
    name: str
    dimension: int
    scope: str
    ordered_write: bool


def check_state_reads(writes: dict[tuple[str, str], int], reads: list[StateRead]) -> list[str]:
    """Return exact, actionable errors for Get/formal dimension and order."""
    errors: list[str] = []
    for read in reads:
        key = (read.scope, read.name)
        if key not in writes:
            errors.append(f'UNDECLARED_READ:{read.scope}:{read.name}')
        elif writes[key] != read.dimension:
            errors.append(f'DIMENSION_MISMATCH:{read.scope}:{read.name}:{writes[key]}->{read.dimension}')
        elif not read.ordered_write:
            errors.append(f'UNORDERED_READ:{read.scope}:{read.name}')
    return errors


def check_get_dimensions(graph: Mapping[str, object]) -> list[str]:
    """I43: scan a read-back, scope-resolved graph snapshot before numeric cook.

    Snapshot format: {'formals': {name: dimension}, 'sets': {name: dimension},
    'gets': [{'name': ..., 'dimension': ..., 'scope': ...}, ...]}.
    Built-ins must be supplied separately as {'builtins': {name: dimension}};
    the caller must first verify their availability in this graph/runtime.
    This does not infer Set/Get execution order or cross-scope visibility.
    """
    declarations = {key: graph.get(key, {}) for key in ('formals', 'sets', 'builtins')}
    errors: list[str] = []
    for index, read in enumerate(graph.get('gets', ())):
        name, actual = read.get('name'), read.get('dimension')
        scope = read.get('scope')
        if not name or actual not in (1, 2, 3, 4):
            errors.append(f'INVALID_GET:{index}')
            continue
        if scope not in declarations:
            errors.append(f'UNRESOLVED_GET_SCOPE:{name}')
            continue
        expected = declarations[scope].get(name)
        if expected is None:
            errors.append(f'UNDECLARED_GET:{scope}:{name}')
        elif expected != actual:
            errors.append(f'GET_DIMENSION_MISMATCH:{scope}:{name}:{expected}->{actual}')
    return errors


def check_vector_slots(records: Iterable[Mapping[str, object]]) -> list[str]:
    """I42: compare source component identities with vectorN port lowering."""
    errors: list[str] = []
    for record in records:
        key = str(record['id'])
        source = tuple(record['source_components'])
        front = tuple(record['componentsin'])
        last = record['componentslast']
        if len(source) not in (2, 3, 4) or front + (last,) != source:
            errors.append(f'VECTOR_SLOT_ORDER:{key}')
    return errors


def check_transform_application_coverage(source_sites: Iterable[str],
                                         ir_sites: Iterable[str]) -> list[str]:
    """I44: every unique source transform use must have a mapped IR site."""
    source, mapped = set(source_sites), set(ir_sites)
    return [f'UNMAPPED_TRANSFORM_SITE:{site}' for site in sorted(source - mapped)]


def check_branch_coverage(source_paths: Iterable[str],
                          covered_paths: Iterable[str]) -> list[str]:
    """Require discriminating cases for each source branch/return path."""
    return [f'UNCOVERED_SOURCE_PATH:{path}' for path in sorted(set(source_paths) - set(covered_paths))]


def check_function_numeric_gate(record: Mapping[str, object],
                                required_paths: Iterable[str] = ()) -> list[str]:
    """Check one Function before any caller/PP assembly is allowed.

    Cases must come from a separately evaluated oracle, not from graph output
    reused as the expectation. This static helper cannot itself native-cook SD.
    """
    name = str(record.get('name', ''))
    errors = []
    if not name or not record.get('source_hash'):
        errors.append('FUNCTION_GATE_IDENTITY_MISSING')
    if record.get('readback_ok') is not True or record.get('marked_output') is not True:
        errors.append(f'FUNCTION_GATE_READBACK:{name}')
    if record.get('native_cook_ok') is not True:
        errors.append(f'FUNCTION_GATE_COOK:{name}')
    cases = record.get('cases', ())
    if not isinstance(cases, (list, tuple)) or not cases:
        errors.append(f'FUNCTION_GATE_CASES_MISSING:{name}')
        cases = ()
    covered = set()
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            errors.append(f'FUNCTION_GATE_CASE_INVALID:{name}:{index}')
            continue
        if case.get('oracle_independent') is not True or 'inputs' not in case:
            errors.append(f'FUNCTION_GATE_ORACLE_EVIDENCE:{name}:{index}')
        native, oracle = case.get('native'), case.get('oracle')
        tolerance = case.get('tolerance')
        if not isinstance(native, (list, tuple)) or not isinstance(oracle, (list, tuple)) or \
                len(native) != len(oracle) or not native or \
                not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
            errors.append(f'FUNCTION_GATE_NUMERIC_INVALID:{name}:{index}')
            continue
        try:
            if any(not math.isfinite(float(x)) or not math.isfinite(float(y)) or
                   abs(float(x) - float(y)) > tolerance for x, y in zip(native, oracle)):
                errors.append(f'FUNCTION_GATE_NUMERIC_MISMATCH:{name}:{index}')
        except (TypeError, ValueError):
            errors.append(f'FUNCTION_GATE_NUMERIC_INVALID:{name}:{index}')
        if case.get('path'):
            covered.add(str(case['path']))
    errors.extend(check_branch_coverage(required_paths, covered))
    return errors


def check_build_stage_order(events: Iterable[Mapping[str, object]]) -> list[str]:
    """A caller cannot start before each dependency's ordered numeric gate."""
    expected = ('function_created', 'function_readback', 'function_cooked',
                'function_oracle_pass', 'function_gate_pass')
    stage: dict[str, int] = {}
    verified = set()
    errors = []
    for event in events:
        kind = event.get('kind')
        if kind in expected:
            function = str(event.get('function', ''))
            next_stage = stage.get(function, 0)
            if not function or next_stage >= len(expected) or kind != expected[next_stage]:
                errors.append(f'FUNCTION_GATE_STAGE_ORDER:{function}:{kind}')
            else:
                stage[function] = next_stage + 1
                if kind == 'function_gate_pass':
                    verified.add(function)
        elif kind == 'caller_start':
            caller = str(event.get('caller', ''))
            for dependency in event.get('requires', ()):
                if dependency not in verified:
                    errors.append(f'CALLER_BEFORE_FUNCTION_GATE:{caller}:{dependency}')
    return errors


def require_verified_dependencies(caller: str, dependencies: Iterable[str],
                                  verified: Iterable[str]) -> None:
    """Call immediately before a builder creates a caller or PP instance."""
    missing = sorted(set(dependencies) - set(verified))
    if missing:
        raise ValueError(f'CALLER_BEFORE_FUNCTION_GATE:{caller}:{",".join(missing)}')


def check_definite_component_reads(reads: Iterable[Mapping[str, object]]) -> list[str]:
    """IR-level must-defined-component check after control-flow joins.

    The front end computes ``definitely_written`` by intersection at branch
    merges; this helper prevents default zero from silently filling a gap.
    """
    errors = []
    for read in reads:
        name = str(read['name'])
        required = set(read['components'])
        written = set(read['definitely_written'])
        for component in sorted(required - written):
            errors.append(f'UNINITIALIZED_COMPONENT_READ:{name}.{component}')
    return errors


def check_time_channel_evidence(record: Mapping[str, object]) -> list[str]:
    """Separate static-frame, manual-time, and host-animation evidence.

    Returned *_UNVERIFIED findings limit the delivery claim; a Designer t=0
    cook is not evidence that Player's $time path is broken.
    """
    findings = []
    if record.get('system_source') != '$time' or record.get('manual_source') != 'iTime' or \
            record.get('selector_default') not in {'system', 'manual'}:
        findings.append('TIME_CHANNEL_IDENTITY_UNVERIFIED')
    if record.get('manual_parent_binding_verified') is not True:
        findings.append('TIME_MANUAL_BINDING_UNVERIFIED')
    frames = record.get('manual_frames', ())
    if not isinstance(frames, (list, tuple)) or not any(
            isinstance(frame, Mapping) and isinstance(frame.get('iTime'), (int, float)) and
            frame['iTime'] != 0 and frame.get('effectiveTime') == frame['iTime']
            for frame in frames) or record.get('manual_oracle_verified') is not True:
        findings.append('TIME_MANUAL_NONZERO_UNVERIFIED')
    if record.get('system_nonzero_verified') is not True:
        findings.append('TIME_SYSTEM_ANIMATION_UNVERIFIED')
    return findings


def can_hoist_leading_break(*, first_executable: bool, condition_pure: bool,
                            reads_entry_state: bool, targets_this_loop: bool,
                            prior_effects: bool = False) -> bool:
    """Only a side-effect-free body-entry break may join While Exit Cond."""
    return (first_executable and condition_pure and reads_entry_state and
            targets_this_loop and not prior_effects)


def check_call_formals(required: set[str], connected: set[str]) -> list[str]:
    return [f'UNCONNECTED_FORMAL:{name}' for name in sorted(required - connected)]


def check_definition_allowed(definition_id: str, graph_definitions: Iterable[str]) -> list[str]:
    """Use the *target graph's* definitions immediately before newNode."""
    return [] if definition_id in set(graph_definitions) else [f'UNKNOWN_DEFINITION_FOR_GRAPH:{definition_id}']


def check_formal_state_collisions(formals: Iterable[str], carried_states: Iterable[str]) -> list[str]:
    """A same-name Function formal can shadow a loop-carried Set/Get state."""
    return [f'FORMAL_SHADOWS_CARRIED_STATE:{name}'
            for name in sorted(set(formals) & set(carried_states))]


def exact_loaded_package_path(expected_path: str | Path,
                              loaded_paths: Iterable[str | Path]) -> str:
    """Fail closed if a saved target package is absent or duplicated in-session.

    The caller may then explicitly load the saved file; it must not fall through
    to creating a new empty package. Unsaved scratch packages need run-owned IDs.
    """
    expected = str(expected_path)
    if not (Path(expected).is_absolute() or ntpath.isabs(expected)):
        raise ValueError('expected package path must be absolute')
    windows_path = ntpath.isabs(expected)
    normalize = (lambda value: ntpath.normcase(ntpath.normpath(value))) if windows_path \
        else (lambda value: os.path.normcase(os.path.normpath(value)))
    normalized = normalize(expected)
    candidates = [str(path) for path in loaded_paths if str(path)]
    matches = [path for path in candidates if normalize(path) == normalized]
    if len(matches) != 1:
        raise ValueError(f'expected one loaded package for {normalized!s}; '
                         f'matches={matches!r}; loaded={[(p, normalize(p)) for p in candidates]!r}')
    return matches[0]


def exact_loaded_package_index(expected_path: str | Path,
                               loaded: Iterable[tuple[int, str]]) -> int:
    """Return only a scene-reported index whose current path exactly matches."""
    entries = list(loaded)
    matched_path = exact_loaded_package_path(expected_path, [path for _, path in entries])
    indices = [index for index, path in entries if path == matched_path]
    if len(indices) != 1:
        raise ValueError('loaded package index is ambiguous; refresh scene info')
    return indices[0]


def source_sha256(path: str | Path) -> str:
    """Log this at builder load/run time to detect stale imported source."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_arithmetic_dimensions(operands: Iterable[tuple[str, str, int, int]]) -> list[str]:
    """Reject mixed dimensions on ordinary binary arithmetic before wiring.

    Each record is (node_alias, operation, a_dimension, b_dimension).
    mulscalar is intentionally excluded because its vector/scalar ports differ.
    """
    errors = []
    for alias, op, a_dim, b_dim in operands:
        if op not in {'mul', 'add', 'sub', 'div', 'pow', 'min', 'max', 'mod'}:
            raise ValueError(f'unsupported ordinary arithmetic operation: {op}')
        if a_dim not in (1, 2, 3, 4) or b_dim not in (1, 2, 3, 4):
            errors.append(f'UNKNOWN_OPERAND_DIMENSION:{alias}')
        elif a_dim != b_dim:
            errors.append(f'MIXED_ARITHMETIC_DIMENSION:{alias}:{op}:{a_dim}x{b_dim}')
    return errors


def check_probe_precision(encoding: str, scale: float, downstream_step: float) -> list[str]:
    """Conservative one encoded LSB error budget versus downstream quantization."""
    if not math.isfinite(scale) or scale <= 0 or not math.isfinite(downstream_step) or downstream_step <= 0:
        return ['INVALID_PROBE_PRECISION']
    if encoding == 'direct':
        tolerance = 1 / 255
    elif encoding == 'affine':
        tolerance = 2 * scale / 255
    else:
        return ['UNKNOWN_PROBE_ENCODING']
    return ['PROBE_PRECISION_INSUFFICIENT'] if tolerance > downstream_step / 4 else []


def estimated_inline_nodes(call_count: int, helper_nodes: int, glue_nodes: int = 0) -> int:
    if min(call_count, helper_nodes, glue_nodes) < 0:
        raise ValueError('node counts must be nonnegative')
    return call_count * helper_nodes + glue_nodes


def check_source_coverage(source_sections: Iterable[str],
                          ported: Iterable[str], omitted: Iterable[str],
                          blocked: Iterable[str]) -> list[str]:
    """Every source section/branch needs an explicit delivery disposition."""
    source = set(source_sections)
    groups = [set(ported), set(omitted), set(blocked)]
    classified = set().union(*groups)
    errors = [f'UNCLASSIFIED_SOURCE_SECTION:{name}' for name in sorted(source - classified)]
    errors += [f'UNKNOWN_SOURCE_SECTION:{name}' for name in sorted(classified - source)]
    errors += [f'CONFLICTING_SOURCE_STATUS:{name}' for name in sorted(
        (groups[0] & groups[1]) | (groups[0] & groups[2]) | (groups[1] & groups[2]))]
    return errors


def bmp_dimensions(path: str | Path) -> tuple[int, int, str]:
    """Read a BMP DIB's signed height; no large pixel read or image library needed."""
    with Path(path).open('rb') as stream:
        header = stream.read(26)
    if len(header) < 26 or header[:2] != b'BM':
        raise ValueError('not a BMP')
    dib_size = struct.unpack_from('<I', header, 14)[0]
    if dib_size < 40:
        raise ValueError('unsupported BMP DIB header')
    width, signed_height = struct.unpack_from('<ii', header, 18)
    if width <= 0 or signed_height == 0:
        raise ValueError('invalid BMP dimensions')
    return width, abs(signed_height), 'top-down' if signed_height < 0 else 'bottom-up'


def check_export_size(actual: tuple[int, int], expected: tuple[int, int]) -> list[str]:
    return [] if actual == expected else [f'EXPORT_SIZE_MISMATCH:{actual[0]}x{actual[1]}!= {expected[0]}x{expected[1]}']


def check_marked_root(graph_kind: str, dimension: int, marked_count: int,
                      *, designer_version: str | None = None,
                      root_definition_id: str | None = None,
                      caller_numeric_verified: bool = False) -> list[str]:
    """Check the measured 16.0.3 PP root contract, not an all-version law."""
    errors = []
    if marked_count < 1:
        errors.append('NO_MARKED_OUTPUT')
    if graph_kind == 'pp_inner':
        if designer_version != '16.0.3':
            errors.append('PP_ROOT_DIM_VERSION_PROBE_REQUIRED')
        elif dimension not in (1, 4):
            errors.append(f'PP_ROOT_DIM_UNSUPPORTED:{dimension}')
    elif graph_kind == 'function' and dimension not in (1, 2, 3, 4):
        errors.append(f'FUNCTION_ROOT_DIM_UNSUPPORTED:{dimension}')
    if graph_kind == 'function' and designer_version == '16.0.3' and \
            root_definition_id in {'sbs::function::while', 'sbs::function::sequence',
                                   'sbs::function::set'} and not caller_numeric_verified:
        errors.append(f'CONTROL_ROOT_CALLER_PROBE_REQUIRED:{root_definition_id}')
    return errors


def backward_reachable(output: str, edges: Iterable[tuple[str, str]]) -> set[str]:
    """Follow explicit source→consumer data/control edges back from a root."""
    incoming: dict[str, set[str]] = {}
    for source, consumer in edges:
        incoming.setdefault(consumer, set()).add(source)
    seen = {output}
    pending = [output]
    while pending:
        for source in incoming.get(pending.pop(), ()):
            if source not in seen:
                seen.add(source)
                pending.append(source)
    return seen


def check_output_reachability(output: str, edges: Iterable[tuple[str, str]],
                              required_nodes: Iterable[str]) -> list[str]:
    """Require the planned live Sets/controls to reach the marked output.

    Callers exclude explicitly accepted dead stores. A same-name Get does not
    create an edge to its Set; only actual graph dependencies count.
    """
    seen = backward_reachable(output, edges)
    return [f'UNREACHABLE_REQUIRED_NODE:{node}' for node in sorted(set(required_nodes) - seen)]


def exact_export_match(files: Iterable[str], prefix: str, tag: str) -> str:
    """Select one output by the full graph/tag prefix, never a substring."""
    stem = f'{prefix}{tag}_'
    matches = sorted(name for name in files if name.startswith(stem) and name.lower().endswith('.bmp'))
    if len(matches) != 1:
        raise ValueError(f'expected one BMP for {stem!r}; found {matches!r}')
    return matches[0]


def exact_graph_export_match(files: Iterable[str], actual_graph_identifier: str,
                             extension: str = 'bmp') -> str:
    """SD export names derive from read-back graph id, including auto suffixes."""
    if not actual_graph_identifier:
        raise ValueError('graph identifier must be read back')
    if extension.lower() not in {'bmp', 'png', 'exr', 'tif', 'tiff'}:
        raise ValueError('unsupported export extension')
    stem = actual_graph_identifier + '_output_'
    matches = sorted(name for name in files if name.startswith(stem) and
                     name.lower().endswith('.' + extension.lower()))
    if len(matches) != 1:
        raise ValueError(f'expected one {extension.upper()} for actual graph '
                         f'{actual_graph_identifier!r}; found {matches!r}')
    return matches[0]


def check_rgba_export(*, width: int, height: int, channels: int,
                      expected_size: tuple[int, int],
                      alpha_probe_expected: Iterable[float],
                      alpha_probe_observed: Iterable[float],
                      tolerance: float = 1 / 255) -> list[str]:
    """Verify a known varying-alpha probe survived the export transport."""
    errors = check_export_size((width, height), expected_size)
    if channels != 4:
        errors.append('RGBA_EXPORT_CHANNELS_MISSING')
    expected, observed = list(alpha_probe_expected), list(alpha_probe_observed)
    if len(expected) < 2 or len(expected) != len(observed) or \
            not all(math.isfinite(x) for x in expected + observed) or \
            max(expected, default=0) - min(expected, default=0) <= tolerance:
        errors.append('ALPHA_PROBE_INVALID')
    elif any(abs(a - b) > tolerance for a, b in zip(expected, observed)):
        errors.append('ALPHA_EXPORT_NOT_PRESERVED')
    return errors


def preflight_affine_probe(oracle_values: Iterable[float], *, offset: float,
                           gain: float, margin: float = 1 / 255) -> list[str]:
    """Prove encoding range from independent oracle values before SD mutation."""
    if not all(math.isfinite(x) for x in (offset, gain, margin)) or \
            gain == 0 or not 0 < margin < 0.5:
        return ['INVALID_PROBE_ENCODING']
    errors = []
    for index, value in enumerate(oracle_values):
        encoded = offset + gain * value
        if not math.isfinite(value) or not math.isfinite(encoded) or \
                not margin < encoded < 1 - margin:
            errors.append(f'PROBE_ENCODING_OUT_OF_RANGE:{index}')
    return errors


def check_row_view_join(views: Iterable[str]) -> list[str]:
    """Cross-file pixel joins must use one normalized top/file-row view."""
    tags = list(views)
    if any(tag not in {'top_rows', 'file_rows'} for tag in tags):
        return ['UNKNOWN_ROW_VIEW']
    return [] if len(set(tags)) <= 1 else ['ROW_VIEW_MISMATCH']


def check_oracle_evidence(record: Mapping[str, object],
                          required_branches: Iterable[str]) -> list[str]:
    """Metadata gate for acceptance; caller still verifies the oracle itself."""
    required = {'command', 'source_hash', 'artifact_hash', 'view', 'width', 'height',
                'branches', 'regenerated_this_session'}
    errors = [f'ORACLE_MISSING_FIELD:{key}' for key in sorted(required - record.keys())]
    if errors:
        return errors
    for key in ('command', 'source_hash', 'artifact_hash'):
        if not isinstance(record[key], str) or not record[key].strip():
            errors.append(f'ORACLE_EMPTY_FIELD:{key}')
    if record['view'] not in {'top_rows', 'file_rows'}:
        errors.append('ORACLE_UNKNOWN_ROW_VIEW')
    if not isinstance(record['width'], int) or not isinstance(record['height'], int) or \
            record['width'] <= 0 or record['height'] <= 0:
        errors.append('ORACLE_INVALID_RESOLUTION')
    if record['regenerated_this_session'] is not True:
        errors.append('ORACLE_NOT_REGENERATED')
    branches = record['branches']
    if not isinstance(branches, (set, list, tuple)):
        errors.append('ORACLE_INVALID_BRANCH_SCOPE')
    else:
        errors.extend(f'ORACLE_MISSING_BRANCH:{name}'
                      for name in sorted(set(required_branches) - set(branches)))
    return errors


def check_oracle_provenance(source_path: str | Path, artifact_path: str | Path,
                            recorded_source_hash: str, recorded_artifact_hash: str) -> list[str]:
    """A cached oracle table is acceptance evidence only for its generating source."""
    errors = []
    if source_sha256(source_path) != recorded_source_hash:
        errors.append('STALE_ORACLE_SOURCE')
    if source_sha256(artifact_path) != recorded_artifact_hash:
        errors.append('STALE_ORACLE_ARTIFACT')
    return errors


def output_log2_pair(width: int, height: int) -> tuple[int, int]:
    """Convert an intended power-of-two pixel size to $outputsize exponents."""
    if width <= 0 or height <= 0 or width & (width - 1) or height & (height - 1):
        raise ValueError('$outputsize requires positive power-of-two dimensions')
    return width.bit_length() - 1, height.bit_length() - 1


def check_probe_encoding(raw_values: Iterable[float], scale: float,
                         encoded_values: Iterable[float]) -> list[str]:
    """Reject probes whose expected encoded channels clip or saturate."""
    raw, encoded = list(raw_values), list(encoded_values)
    if not math.isfinite(scale) or scale <= 0 or len(raw) != len(encoded):
        return ['INVALID_PROBE_ENCODING']
    errors = []
    for index, (value, channel) in enumerate(zip(raw, encoded)):
        if not math.isfinite(value) or not math.isfinite(channel):
            errors.append(f'NONFINITE_PROBE_CHANNEL:{index}')
        elif not 0 < channel < 1 or abs(value) > scale:
            errors.append(f'SATURATED_PROBE_CHANNEL:{index}')
    return errors


def glsl_matrix_rows(columns: Iterable[Iterable[float]]) -> tuple[tuple[float, ...], ...]:
    """GLSL matN constructor vectors are columns; return rows for M*v."""
    cols = tuple(tuple(col) for col in columns)
    n = len(cols)
    if n not in (2, 3, 4) or any(len(col) != n for col in cols):
        raise ValueError('expected 2x2, 3x3, or 4x4 GLSL matrix columns')
    return tuple(tuple(cols[j][i] for j in range(n)) for i in range(n))
