"""Checks for multi-PP transport and local layout refinement; no SD mutation."""
import math


def check_transport(producer, consumer):
    keys = ('schema_version', 'fields', 'size', 'format', 'encoding', 'pixel_center',
            'filter', 'wrap', 'mip', 'vflip', 'frame_role', 'snapshot_id')
    errors = []
    for k in keys:
        if k not in producer or k not in consumer:
            errors.append('TRANSPORT_FIELD_MISSING:' + k)
        elif producer[k] != consumer[k]:
            errors.append('TRANSPORT_MISMATCH:' + k)
    slots = []
    for field in producer.get('fields', []):
        if not all(k in field for k in ('name', 'type', 'channels', 'range')):
            errors.append('FIELD_SCHEMA_INCOMPLETE')
            continue
        slots.extend(field['channels'])
        bounds = field['range']
        if len(bounds) != 2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in bounds) or bounds[0]>bounds[1]:
            errors.append('INVALID_FIELD_RANGE')
        elif field['type'] == 'uint32' and producer.get('encoding') == 'identity' and producer.get('format') == 'RGBA32F' and bounds[1] > 2**24:
            errors.append('LOSSY_UINT32_FLOAT_TRANSPORT')
    if not producer.get('fields') or len(slots) != len(set(slots)):
        errors.append('EMPTY_OR_OVERLAPPING_CHANNELS')
    size=producer.get('size', [])
    if len(size)!=2 or any(type(x) is not int or x<=0 for x in size):
        errors.append('INVALID_TRANSPORT_SIZE')
    if any(type(c) is not int or c not in range(4) for c in slots):
        errors.append('INVALID_CHANNEL')
    return errors


def check_compact_layout(before, after, *, edges, leaf_pairs=(), rigid_groups=(),
                         fixed_nodes=(), logic_before, logic_after, tolerance=0.01):
    """Supplement only: run baseline validate_layout_plan separately first.

    leaf_pairs are deliberately selected single-consumer leaves, not all constants.
    rigid_groups preserve internal geometry; they may move as complete subtrees.
    """
    errors=[]
    if logic_before != logic_after:
        errors.append('LAYOUT_CHANGED_LOGIC')
    if set(before)!=set(after):
        return errors+['LAYOUT_NODE_SET_CHANGED']
    if any(len(p)!=2 or any(not math.isfinite(x) for x in p) for p in after.values()):
        return errors+['INVALID_LAYOUT_POSITION']
    consumers={}; incoming=set()
    for src,dst in edges:
        consumers.setdefault(src,set()).add(dst); incoming.add(dst)
    for leaf,consumer in leaf_pairs:
        if leaf not in before or consumer not in before:
            errors.append('LAYOUT_UNKNOWN_NODE'); continue
        if consumers.get(leaf)!= {consumer} or leaf in incoming:
            errors.append('NOT_PRIVATE_LEAF:'+leaf); continue
        old=math.dist(before[leaf],before[consumer]); new=math.dist(after[leaf],after[consumer])
        if new>old+tolerance:
            errors.append('LEAF_DISTANCE_INCREASED:'+leaf)
    for group in rigid_groups:
        if not group or any(n not in before for n in group):
            errors.append('INVALID_RIGID_GROUP'); continue
        delta=[after[group[0]][i]-before[group[0]][i] for i in range(2)]
        if any(abs(after[n][i]-before[n][i]-delta[i])>tolerance for n in group for i in range(2)):
            errors.append('RIGID_GROUP_DISTORTED:'+group[0])
    for n in fixed_nodes:
        if n not in before or math.dist(before[n],after[n])>tolerance:
            errors.append('UNRELATED_NODE_MOVED:'+n)
    return errors


def check_portable_delivery(record):
    """Audit a run-owned closure + isolated reload evidence, not file existence."""
    errors=[]
    if not record.get('artifact_hash') or not record.get('scan_evidence'):
        errors.append('DELIVERY_IDENTITY_OR_SCAN_MISSING')
    required={'instances','nested_graphs','parent_resources','bitmap_paths','external_files'}
    if not required <= set(record.get('scanned_categories',[])) or record.get('unresolved_dependencies'):
        errors.append('DEPENDENCY_CLOSURE_INCOMPLETE')
    if record.get('external_dependencies'):
        errors.append('NOT_SELF_CONTAINED')
    if not record.get('isolated_directory') or record.get('reload_artifact_hash') != record.get('artifact_hash'):
        errors.append('ISOLATED_RELOAD_IDENTITY_MISSING')
    for key in ('native_reload','final_output','intermediate_outputs','global_parameters'):
        if record.get('checks',{}).get(key) != 'PASS':
            errors.append('DELIVERY_CHECK_REQUIRED:'+key)
    if record.get('requires_host_scheduler') and not record.get('scheduler_disclosed'):
        errors.append('SCHEDULER_REQUIREMENT_NOT_DISCLOSED')
    return errors
