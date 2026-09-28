"""Pure geometry checks for statement-tree layouts.

Positions use Designer's ordinary canvas coordinates: larger X is farther
right. These checks apply to planned coordinates and to positions read back
from Designer; they do not mutate graph connections or node positions.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping


def select_graph_mode(source_kind: str, user_choice: str | None) -> str:
    """Lock one graph's mode from the source IR and the user's explicit choice.

    A DAG preference can remove straight-line assignment structure, but it
    cannot silently erase stateful or loop execution semantics.
    """
    if user_choice not in {'fidelity', 'dag'}:
        raise ValueError('ASK_USER_FOR_LAYOUT_CHOICE')
    if source_kind not in {'pure', 'straight_line', 'stateful_or_loop'}:
        raise ValueError(f'UNKNOWN_SOURCE_KIND:{source_kind}')
    if source_kind == 'pure':
        return 'expression'
    if user_choice == 'dag':
        if source_kind == 'stateful_or_loop':
            raise ValueError('DAG_CONFLICTS_WITH_STATE_OR_LOOP')
        return 'expression'
    return 'statement'


def validate_mode_readback(mode: str, *, has_sequence: bool,
                           statement_count: int) -> list[str]:
    """Fail on a topology/layout-mode drift instead of silently switching."""
    if mode not in {'statement', 'expression'} or statement_count < 0:
        raise ValueError('invalid graph mode or statement count')
    errors = []
    if mode == 'statement' and statement_count > 0 and not has_sequence:
        errors.append('STATEMENT_MODE_MISSING_SEQUENCE')
    if mode == 'expression' and has_sequence:
        errors.append('EXPRESSION_MODE_HAS_SEQUENCE')
    return errors


def x_from_producer_depth(depth: int, *, origin: float = 0, column_step: float = 192) -> float:
    """A source-to-consumer depth must move right, not left."""
    if depth < 0 or column_step <= 0:
        raise ValueError('depth must be nonnegative and column_step positive')
    return origin + depth * column_step


def infer_bands(explicit: Mapping[str, int | None],
                edges: Iterable[tuple[str, str]]) -> tuple[dict[str, int], list[str]]:
    """Infer local expression/constant bands from consumers, without band-0 fallback.

    Multi-band consumers mean a shared node: the builder must explicitly place
    or clone it according to the IR, not silently choose the first consumer.
    """
    bands = dict(explicit)
    consumers: dict[str, set[str]] = {}
    for source, consumer in edges:
        consumers.setdefault(source, set()).add(consumer)
    errors: list[str] = []
    pending = {node for node, band in bands.items() if band is None}
    while pending:
        changed = False
        for node in sorted(pending):
            downstream = consumers.get(node, set())
            if any(consumer not in bands or bands[consumer] is None for consumer in downstream):
                continue
            known = {bands[consumer] for consumer in downstream}
            if len(known) == 1:
                bands[node] = known.pop()
                pending.remove(node)
                changed = True
            elif len(known) > 1:
                errors.append(f'AMBIGUOUS_SHARED_BAND:{node}')
                pending.remove(node)
        if not changed:
            break
    errors.extend(f'UNRESOLVED_BAND:{node}' for node in sorted(pending))
    return {node: band for node, band in bands.items() if band is not None}, errors


def band_height_from_levels(levels: Mapping[str, int], *, lane_step: float = 96) -> float:
    """Nodes in different X/depth columns can share a Y row."""
    if lane_step <= 0:
        raise ValueError('lane_step must be positive')
    counts: dict[int, int] = {}
    for level in levels.values():
        counts[level] = counts.get(level, 0) + 1
    return max(counts.values(), default=1) * lane_step


def validate_statement_layout(
    positions: Mapping[str, tuple[float, float]],
    statement_pairs: Iterable[tuple[str, str]],
    *,
    sequence_spines: Iterable[Iterable[str]] = (),
    private_expression_edges: Iterable[tuple[str, str]] = (),
    tolerance: float = 2.0,
) -> list[str]:
    """Return stable geometry errors for the left-to-right statement model.

    ``statement_pairs`` are (statement root, associated Sequence) in each
    statement band. ``sequence_spines`` list Sequence IDs in IR order per
    block. Pure final output nodes may sit right of a Sequence; the invariant
    is that a Sequence is right of its statement and private expression tree.
    """
    if tolerance < 0:
        raise ValueError('tolerance must be nonnegative')
    errors: list[str] = []

    def point(alias: str) -> tuple[float, float] | None:
        value = positions.get(alias)
        if value is None:
            errors.append(f'MISSING_POSITION:{alias}')
        return value

    for root, sequence in statement_pairs:
        rp, sp = point(root), point(sequence)
        if rp is None or sp is None:
            continue
        if not rp[0] + tolerance < sp[0]:
            errors.append(f'SEQUENCE_NOT_RIGHT_OF_STATEMENT:{root}->{sequence}')
        if abs(rp[1] - sp[1]) > tolerance:
            errors.append(f'STATEMENT_SEQUENCE_ROW_MISMATCH:{root}->{sequence}')

    for spine in sequence_spines:
        previous: tuple[str, tuple[float, float]] | None = None
        for sequence in spine:
            sp = point(sequence)
            if sp is None:
                continue
            if previous is not None:
                prior_alias, prior = previous
                if abs(prior[0] - sp[0]) > tolerance:
                    errors.append(f'SEQUENCE_SPINE_X_DRIFT:{prior_alias}->{sequence}')
                if not prior[1] + tolerance < sp[1]:
                    errors.append(f'SEQUENCE_ORDER_REVERSED:{prior_alias}->{sequence}')
            previous = (sequence, sp)

    for source, consumer in private_expression_edges:
        src, dst = point(source), point(consumer)
        if src is not None and dst is not None and not src[0] + tolerance < dst[0]:
            errors.append(f'EXPRESSION_EDGE_REVERSED:{source}->{consumer}')
    return errors


def validate_layout_plan(
    positions: Mapping[str, tuple[float, float]],
    statement_pairs: Iterable[tuple[str, str]],
    *,
    sequence_spines: Iterable[Iterable[str]] = (),
    private_expression_edges: Iterable[tuple[str, str]] = (),
    tolerance: float = 2.0,
) -> list[str]:
    """Pre-newNode structural gate; applying a bad plan faithfully is not PASS."""
    errors = validate_statement_layout(
        positions, statement_pairs, sequence_spines=sequence_spines,
        private_expression_edges=private_expression_edges, tolerance=tolerance)
    occupied: dict[tuple[float, float], str] = {}
    for alias, point in positions.items():
        if point in occupied:
            errors.append(f'DUPLICATE_PLANNED_COORDINATE:{occupied[point]}->{alias}')
        else:
            occupied[point] = alias
    return errors


def validate_position_application(
    planned: Mapping[str, tuple[float, float]],
    actual: Mapping[str, tuple[float, float]],
    *, tolerance: float = 2.0,
) -> list[str]:
    """Separate readback gate: did the host apply the validated plan?"""
    if tolerance < 0:
        raise ValueError('tolerance must be nonnegative')
    errors = []
    for alias, target in planned.items():
        value = actual.get(alias)
        if value is None:
            errors.append(f'MISSING_APPLIED_POSITION:{alias}')
        elif abs(value[0] - target[0]) > tolerance or abs(value[1] - target[1]) > tolerance:
            errors.append(f'POSITION_DIFFERS_FROM_PLAN:{alias}')
    return errors
