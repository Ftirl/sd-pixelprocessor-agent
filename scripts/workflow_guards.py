"""Persistent evidence and recovery decisions; never mutates SD or kills a process."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from graph_evidence import digest

IDENTITY_FIELDS = ('package', 'resource', 'source_hash', 'graph_hash', 'interface_hash',
                   'environment_hash', 'cases_hash')


def identity_key(identity):
    if not isinstance(identity, dict) or any(not isinstance(identity.get(k), str) or
                                           not identity[k].strip() for k in IDENTITY_FIELDS):
        raise ValueError('INCOMPLETE_FUNCTION_IDENTITY')
    return digest({k: identity[k] for k in IDENTITY_FIELDS})


def case_evidence_hash(record):
    return digest({'required_paths': record.get('required_paths'), 'cases': record.get('cases')})


class EvidenceRegistry:
    """Content-bound verification; dependencies recursively checked at use time."""
    def __init__(self):
        self.records = {}

    def verify(self, identity, numeric_record, dependencies, current):
        from project_validation import check_function_numeric_gate
        key = identity_key(identity)
        required_paths = numeric_record.get('required_paths')
        if not isinstance(required_paths, list) or not required_paths:
            raise ValueError('SOURCE_PATH_INVENTORY_REQUIRED')
        if numeric_record.get('identity_key') != key or numeric_record.get('name') != identity['resource']:
            raise ValueError('NUMERIC_RECORD_IDENTITY_MISMATCH')
        if identity['cases_hash'] != case_evidence_hash(numeric_record):
            raise ValueError('CASE_EVIDENCE_CHANGED')
        if check_function_numeric_gate(numeric_record, required_paths) or numeric_record.get('source_hash') != identity.get('source_hash'):
            raise ValueError('NUMERIC_GATE_NOT_PASSED')
        resource = (identity['package'], identity['resource'])
        if current.get(resource) != identity:
            raise ValueError('CURRENT_IDENTITY_MISMATCH')
        deps = tuple(dependencies)
        if resource in deps:
            raise ValueError('CYCLIC_DEPENDENCY')
        for dep in deps:
            self.require(dep, current)
        self.records[resource] = {'key': identity_key(identity), 'dependencies': deps,
                                  'dependency_keys': {d: identity_key(current[d]) for d in deps}}

    def require(self, resource, current, trail=()):
        if resource in trail:
            raise ValueError('CYCLIC_DEPENDENCY')
        rec = self.records.get(resource)
        if rec is None or resource not in current or rec['key'] != identity_key(current[resource]):
            raise ValueError('STALE_OR_MISSING_EVIDENCE:' + str(resource))
        for dep in rec['dependencies']:
            if dep not in current or identity_key(current[dep]) != rec['dependency_keys'][dep]:
                raise ValueError('DEPENDENCY_CHANGED:' + str(dep))
            self.require(dep, current, trail + (resource,))

    def invalidate(self, resource):
        affected = {resource}
        while True:
            more = {k for k, v in self.records.items() if set(v['dependencies']) & affected}
            if more <= affected:
                break
            affected |= more
        for key in affected:
            self.records.pop(key, None)
        return affected


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, sort_keys=True, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class WriterLease:
    """Exclusive local lock. A crash leaves it for explicit state reconciliation."""
    def __init__(self, path, *, run_id, target):
        self.path=Path(path)
        self.owner={'run_id':run_id,'target':target,'pid':os.getpid()}
        self.active=False

    def __enter__(self):
        if not self.owner['run_id'] or not self.owner['target']:
            raise ValueError('LEASE_IDENTITY_REQUIRED')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('x',encoding='utf-8') as f:
            json.dump(self.owner,f);f.flush();os.fsync(f.fileno())
        self.active=True
        return self

    def __exit__(self,*exc):
        if self.active:
            if json.loads(self.path.read_text(encoding='utf-8')) != self.owner:
                raise RuntimeError('WRITER_LEASE_CHANGED')
            self.path.unlink();self.active=False


class OperationJournal:
    """Single-writer operation record. Exclusive creation prevents accidental replay.

    A separate project/session writer lock is required across multiple operations.
    Unknown/inflight is not a permission to reissue an SD request.
    """
    def __init__(self, path):
        self.path = Path(path)

    def begin(self, *, run_id, operation_id, target, before_hash, expected_after_hash, checkpoint):
        fields = locals().copy()
        fields.pop('self')
        if any(not isinstance(v, str) or not v for v in fields.values()):
            raise ValueError('INCOMPLETE_OPERATION')
        record = dict(fields, schema=1, state='prepared')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('x', encoding='utf-8') as f:
            json.dump(record, f)
            f.flush()
            os.fsync(f.fileno())
        return record

    def transition(self, state):
        r = json.loads(self.path.read_text(encoding='utf-8'))
        allowed = {'prepared': {'inflight'}, 'inflight': {'unknown'},
                   'unknown': {'reconciled', 'conflict'}, 'reconciled': set(),
                   'committed': set(), 'conflict': set()}
        if state not in allowed.get(r['state'], set()):
            raise ValueError('INVALID_OPERATION_TRANSITION')
        r['state'] = state
        atomic_json(self.path, r)

    def commit(self, *, target, observed_hash, output_checks):
        r = json.loads(self.path.read_text(encoding='utf-8'))
        if r['state'] != 'inflight' or target != r['target'] or observed_hash != r['expected_after_hash']:
            raise ValueError('COMMIT_STATE_OR_IDENTITY_MISMATCH')
        if not output_checks or any(v != 'PASS' for v in output_checks.values()):
            raise ValueError('COMMIT_OUTPUT_NOT_ACCEPTED')
        r.update(state='committed', output_checks=output_checks, observed_hash=observed_hash)
        atomic_json(self.path, r)

    def reconcile(self, *, target, observed_hash, alive):
        r = json.loads(self.path.read_text(encoding='utf-8'))
        if target != r['target']:
            return 'STOP_TARGET_MISMATCH'
        if not alive:
            return 'STOP_WRITES_HOST_UNRESPONSIVE'
        if observed_hash == r['expected_after_hash']:
            return 'ALREADY_APPLIED_VERIFY_OUTPUT'
        if observed_hash == r['before_hash']:
            return 'UNCHANGED_REPLAN_WITH_NEW_OPERATION_ID'
        return 'CONFLICT_PRESERVE_USER_STATE'


def check_visual_decision(record, *, scope, evidence_key):
    errors = []
    if record.get('mode') != 'PROVISIONAL_VISUAL_ASSEMBLY' or record.get('user_choice') != 'visual_first':
        errors.append('VISUAL_CHOICE_REQUIRED')
    for k in ('authorization_ref', 'residuals', 'visual_evidence', 'unverified_conditions', 'reopen_triggers'):
        if not record.get(k):
            errors.append('VISUAL_RECORD_MISSING:' + k)
    if not set(scope) <= set(record.get('scope', [])) or record.get('evidence_key') != evidence_key:
        errors.append('VISUAL_SCOPE_OR_EVIDENCE_CHANGED')
    if record.get('missing_features') or record.get('safety_failures'):
        errors.append('NON_WAIVABLE_GAP')
    for k in ('structure', 'state_order', 'transport', 'native_cook', 'finite', 'range'):
        if record.get('checks', {}).get(k) != 'PASS':
            errors.append('PROVISIONAL_CHECK_REQUIRED:' + k)
    return errors


def cook_budget_action(*, elapsed, limit, alive, finite, memory_ok):
    if limit <= 0 or elapsed < 0:
        raise ValueError('INVALID_COOK_BUDGET')
    if not alive:
        return 'STOP_WRITES_HOST_UNRESPONSIVE'
    if finite is not True or memory_ok is not True or elapsed > limit:
        return 'STOP_ESCALATION_DIAGNOSE'
    return 'NEXT_PLANNED_STAGE'


def check_frame_commit(previous, candidate):
    """Candidate becomes history only after complete ordered pass acceptance."""
    errors = []
    if candidate.get('frame') != previous.get('frame', -1) + 1:
        errors.append('FRAME_ORDER')
    if candidate.get('history_hash') != previous.get('output_hash'):
        errors.append('HISTORY_SNAPSHOT_MISMATCH')
    if candidate.get('configuration_hash') != previous.get('configuration_hash'):
        errors.append('RESET_REQUIRED')
    expected = candidate.get('expected_passes')
    if not expected or candidate.get('completed_passes') != expected:
        errors.append('INCOMPLETE_OR_REORDERED_FRAME')
    if candidate.get('accepted') is not True or not candidate.get('output_hash'):
        errors.append('FRAME_NOT_ACCEPTED')
    return errors
