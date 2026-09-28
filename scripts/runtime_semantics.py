#!/usr/bin/env python3
"""Pure helpers for current runtime-semantic defaults.

These helpers intentionally do not depend on the Substance SDK so they can be
unit-tested in the release gate and reused by graph builders/linters.
"""
from __future__ import annotations

CONTROL_ROOTS = frozenset({'set', 'sequence', 'while', 'ifelse_control'})
PURE_ROOT_PREFIXES = ('const_', 'get_float', 'vector', 'swizzle', 'instance:')


def shader_coord_lowering(*, square_target: bool, needs_pixel_indices: bool=False) -> dict:
    if needs_pixel_indices:
        return {
            'mode': 'explicit-virtual-resolution',
            'allowed_raw_pos_as_fragcoord': False,
            'reason': '$pos is normalized; pixel indices require an explicit resolution source',
        }
    if square_target:
        return {
            'mode': 'normalized-square',
            'expression': '$pos - 0.5',
            'allowed_raw_pos_as_fragcoord': False,
        }
    return {
        'mode': 'normalized-with-explicit-aspect',
        'allowed_raw_pos_as_fragcoord': False,
        'size_source': 'explicit-output-size-or-verified-formal',
        'reason': '$pos is normalized; do not infer shader resolution/aspect from an unprobed $size context',
    }


def post_set_transport() -> str:
    """Default to proving the ordered Get path, not an automatic value fallback."""
    return 'get_sequence_topology_required'


def state_read_transport(*, scope_verified: bool,
                         sequence_topology_verified: bool = False) -> str:
    """Get must occur in a reachable later Sequence branch in the same scope."""
    if not sequence_topology_verified:
        return 'get_sequence_topology_required'
    if not scope_verified:
        return 'get_scope_probe_required'
    return 'sequence_ordered_get'


def terminal_root_allowed(kind: str, *, current_session_probe_pass: bool = False,
                          caller_oracle_pass: bool = False) -> bool:
    """Conservative default; a control-root exception needs both proof layers."""
    if kind.lower() not in CONTROL_ROOTS:
        return True
    return current_session_probe_pass and caller_oracle_pass


def function_output_root_allowed(kind: str, *, current_session_probe_pass: bool = False,
                                 caller_oracle_pass: bool = False) -> bool:
    return terminal_root_allowed(kind, current_session_probe_pass=current_session_probe_pass,
                                 caller_oracle_pass=caller_oracle_pass)


def while_body_edge_allowed(source_kind: str, source_scope: str) -> bool:
    """Fail closed for external Sequence -> While-body consumption."""
    return not (source_kind.lower() == 'sequence' and source_scope.lower() != 'while_body')


def multiply_lowering(*, vector_dim: int, scalar: bool, sequence_derived_vector: bool) -> dict:
    if vector_dim not in (1,2,3,4):
        raise ValueError('vector_dim must be 1..4')
    if vector_dim == 1:
        return {'node': 'mul', 'broadcast': False}
    if scalar and sequence_derived_vector:
        return {'node': 'mul', 'broadcast': True, 'broadcast_dim': vector_dim}
    if scalar:
        return {'node': 'mulscalar', 'broadcast': False}
    return {'node': 'mul', 'broadcast': False}


def sequence_get_topology(*, edges: list[dict], set_node: str, get_node: str,
                          sequence_node: str, output_nodes: list[str]) -> bool:
    """Check Set in the Sequence first branch and Get in its later branch.

    Edges are source -> target with target_port; this is wiring evidence, not
    canvas position or a same-name inference. The Sequence may be part of a
    longer chain, so a Set upstream of its In branch is accepted.
    """
    inputs = {}
    consumers = {}
    for edge in edges:
        source, target = edge.get('source'), edge.get('target')
        if not source or not target:
            continue
        inputs.setdefault(target, []).append(edge)
        consumers.setdefault(source, set()).add(target)

    def upstream(start: str, wanted: str) -> bool:
        pending, seen = [start], set()
        while pending:
            node = pending.pop()
            if node == wanted:
                return True
            if node in seen:
                continue
            seen.add(node)
            pending.extend(e['source'] for e in inputs.get(node, []))
        return False

    def downstream(start: str, wanted: set[str]) -> bool:
        pending, seen = [start], set()
        while pending:
            node = pending.pop()
            if node in wanted:
                return True
            if node in seen:
                continue
            seen.add(node)
            pending.extend(consumers.get(node, ()))
        return False

    first = [e['source'] for e in inputs.get(sequence_node, [])
             if str(e.get('target_port', '')).lower() in {'in', 'seqin'}]
    last = [e['source'] for e in inputs.get(sequence_node, [])
            if str(e.get('target_port', '')).lower() in {'last', 'seqlast'}]
    return (bool(first) and bool(last) and
            any(upstream(node, set_node) for node in first) and
            any(upstream(node, get_node) for node in last) and
            not any(upstream(node, get_node) for node in first) and
            downstream(sequence_node, set(output_nodes)))


def validate_ir(ir: dict) -> list[str]:
    """Validate a compact builder IR. Returns stable error codes."""
    errors=[]
    if ir.get('mode') == 'statement' and 'statement_edges' not in ir:
        errors.append('RS_STATEMENT_EDGE_AUDIT_MISSING')
    for out in ir.get('outputs', []):
        if not terminal_root_allowed(str(out.get('kind','')),
                                     current_session_probe_pass=bool(out.get('current_session_probe_pass')),
                                     caller_oracle_pass=bool(out.get('caller_oracle_pass'))):
            errors.append('RS_TERMINAL')
    for out in ir.get('function_outputs', []):
        if not function_output_root_allowed(str(out.get('kind','')),
                                            current_session_probe_pass=bool(out.get('current_session_probe_pass')),
                                            caller_oracle_pass=bool(out.get('caller_oracle_pass'))):
            errors.append('RS_FUNCTION_OUTPUT')
    for edge in ir.get('while_body_inputs', []):
        if not while_body_edge_allowed(str(edge.get('source_kind','')), str(edge.get('source_scope',''))):
            errors.append('SAFETY_INVARIANT_002')
    for op in ir.get('multiplies', []):
        if (str(op.get('node','')).lower() == 'mulscalar' and
            bool(op.get('sequence_derived_vector'))):
            errors.append('RS_MULSEQ')
    for read in ir.get('post_set_reads', []):
        transport = str(read.get('transport','')).lower()
        if transport == 'bare_get':
            errors.append('RS_SETSEQ')
        elif transport == 'sequence_ordered_get':
            if 'wiring_edges' in read:
                topology_ok = sequence_get_topology(
                    edges=read['wiring_edges'], set_node=str(read.get('set_node', '')),
                    get_node=str(read.get('get_node', '')),
                    sequence_node=str(read.get('sequence_node', '')),
                    output_nodes=read.get('output_nodes', []))
            else:
                topology_ok = False
                errors.append('RS_GET_EDGE_AUDIT_MISSING')
            if not topology_ok:
                errors.append('RS_GET_SEQUENCE_TOPOLOGY')
            if not (read.get('scope_verified') is True and
                    read.get('dimension_match') is True):
                errors.append('RS_GET_NOT_PROVEN')
        elif transport in {'set_output', 'old_rhs'}:
            errors.append('RS_CROSS_STATEMENT_DAG')
        elif transport == 'get_scope_probe_required':
            errors.append('RS_GET_SCOPE_PROBE_REQUIRED')
        elif transport == 'get_sequence_topology_required':
            errors.append('RS_GET_SEQUENCE_TOPOLOGY')
        elif transport == 'statement_sequence_output' and ir.get('mode') == 'statement' and \
                not (read.get('fallback_reason') and read.get('numeric_verified') is True):
            errors.append('RS_SEQUENCE_FALLBACK_UNPROVEN')
    for edge in ir.get('statement_edges', []):
        source_statement, target_statement = edge.get('source_statement'), edge.get('target_statement')
        if not source_statement or not target_statement:
            errors.append('RS_STATEMENT_EDGE_ID_MISSING')
            continue
        source_kind = str(edge.get('source_kind', '')).lower()
        if source_statement != target_statement and \
                source_kind in {'set', 'old_rhs', 'expression'} and \
                str(edge.get('target_kind', '')).lower() not in {'sequence', 'control'} and \
                (source_kind != 'expression' or not edge.get('registered_exception')):
            errors.append('RS_CROSS_STATEMENT_DAG')
    if ir.get('shader_coords', {}).get('raw_pos_as_fragcoord'):
        errors.append('RS_COORD')
    if ir.get('shader_coords', {}).get('raw_size_as_resolution'):
        errors.append('RS_SIZE_SOURCE')
    return sorted(set(errors))
