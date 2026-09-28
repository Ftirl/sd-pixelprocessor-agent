"""Graph Refactoring Engine v2.5.0.
Deterministic, SDK-independent planning helpers.
"""
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class GraphNode:
    id:str
    kind:str
    inputs:tuple=()
    params:tuple=()

def structural_signature(nodes):
    return tuple((n.kind,n.inputs,n.params) for n in nodes)

def find_duplicate_subgraphs(candidates):
    groups=defaultdict(list)
    for c in candidates:
        groups[structural_signature(c)] .append(c)
    return [v for v in groups.values() if len(v)>1]

def constant_fold(kind,a,b):
    if kind=="add" and b==0: return a
    if kind=="mul" and b==1: return a
    if kind=="sub" and b==0: return a
    if kind=="div" and b==1: return a
    return None


@dataclass(frozen=True)
class SplitCandidate:
    name: str
    replaceable_nodes: int
    caller_replacement_nodes: int
    function_nodes: int
    safe: bool
    decision: str  # extract / retain / blocked
    reason: str
    call_sites: tuple[str, ...] = ()
    input_types: tuple[str, ...] = ()
    output_types: tuple[str, ...] = ()
    applied: bool = False
    function_numeric_evidence: str = ''  # independent oracle result id
    first_callsite_evidence: str = ''  # I24 result id


@dataclass(frozen=True)
class HighNodeEvidence:
    readback_id: str
    cook_id: str
    layout_id: str


@dataclass(frozen=True)
class SplitReview:
    source_nodes_before: int
    candidates: tuple[SplitCandidate, ...]
    reason: str  # required even when no safe candidate exists
    high_node_evidence: HighNodeEvidence | None = None


def projected_caller_nodes(source_nodes: int, candidate: SplitCandidate) -> int:
    """Projection for replacing the candidate's exact caller-owned nodes."""
    if source_nodes < 0 or candidate.replaceable_nodes <= 0 or \
            candidate.replaceable_nodes > source_nodes or \
            candidate.caller_replacement_nodes <= 0 or candidate.function_nodes <= 0:
        raise ValueError('invalid split projection inputs')
    return source_nodes - candidate.replaceable_nodes + candidate.caller_replacement_nodes


def node_budget_status(node_count: int, *, split_review: SplitReview | None = None,
                       over_budget_exception: bool = False) -> tuple[str, str]:
    """Final delivery gate couples node count to a concrete function split review.

    Other semantic, normalized-structure, cook and layout gates are independent.
    over_budget_exception is only for an explicitly user-approved exception.
    """
    if node_count < 0:
        raise ValueError('node_count must be nonnegative')
    if node_count > 1500 and not over_budget_exception:
        return 'FAIL', 'OVER_SINGLE_GRAPH_CAP'
    if node_count >= 400 and split_review is None:
        return 'BLOCKED', 'FUNCTION_SPLIT_REVIEW_REQUIRED'
    if split_review is not None:
        if split_review.source_nodes_before < node_count or not split_review.reason.strip():
            return 'BLOCKED', 'INCOMPLETE_FUNCTION_SPLIT_REVIEW'
        names = [candidate.name for candidate in split_review.candidates]
        if len(names) != len(set(names)) or any(not name for name in names):
            return 'BLOCKED', 'INVALID_FUNCTION_SPLIT_CANDIDATES'
        for candidate in split_review.candidates:
            try:
                projected = projected_caller_nodes(split_review.source_nodes_before, candidate)
            except ValueError:
                return 'BLOCKED', 'INVALID_FUNCTION_SPLIT_PROJECTION'
            if candidate.decision not in {'extract', 'retain', 'blocked'} or not candidate.reason.strip():
                return 'BLOCKED', 'INCOMPLETE_FUNCTION_SPLIT_DECISION'
            if candidate.safe and (not candidate.call_sites or not candidate.output_types or
                                   any(not item.strip() for item in
                                       (*candidate.call_sites, *candidate.input_types,
                                        *candidate.output_types))):
                return 'BLOCKED', 'INCOMPLETE_TYPED_SPLIT_BOUNDARY'
            if candidate.decision == 'extract':
                if not candidate.safe or projected >= split_review.source_nodes_before:
                    return 'BLOCKED', 'UNSAFE_OR_NONREDUCING_SPLIT'
                if not candidate.applied:
                    return 'BLOCKED', 'SPLIT_SELECTED_NOT_APPLIED'
                if not candidate.function_numeric_evidence.strip() or \
                        not candidate.first_callsite_evidence.strip():
                    return 'BLOCKED', 'SPLIT_NOT_NUMERICALLY_VERIFIED'
                if node_count >= split_review.source_nodes_before:
                    return 'BLOCKED', 'SPLIT_DID_NOT_REDUCE_CALLER'
            elif candidate.decision == 'retain' and node_count >= 400 and candidate.safe \
                    and projected < node_count and \
                    not candidate.reason.startswith('STRUCTURAL_EXCEPTION:'):
                return 'BLOCKED', 'SAFE_SPLIT_RETAINED_WITHOUT_EXCEPTION'
            elif candidate.decision == 'blocked' and candidate.safe:
                return 'BLOCKED', 'SAFE_SPLIT_MISLABELED_BLOCKED'
    evidence = split_review.high_node_evidence if split_review is not None else None
    if node_count >= 1200 and (evidence is None or not evidence.readback_id.strip() or
                               not evidence.cook_id.strip() or not evidence.layout_id.strip()):
        return 'BLOCKED', 'HIGH_NODE_READBACK_COOK_LAYOUT_REQUIRED'
    if node_count > 1500:
        return 'WARN', 'USER_APPROVED_OVER_BUDGET_EXCEPTION'
    if node_count >= 1200:
        return 'WARN', 'HIGH_NODE_COUNT'
    return 'PASS', 'NODE_COUNT_WITHIN_BUDGET'
