"""Fail-closed semantic snapshots. No SDK import until native readback is requested.

Coordinates are separate from semantics. Unknown values are errors, never repr()
or an empty graph. Snapshots describe readback, not numeric equivalence.
"""
from __future__ import annotations
import hashlib
import json
import math


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def exact_value(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # Preserve exceptional values without JSON NaN or lossy decimal strings.
        return value if math.isfinite(value) else {'float': value.hex()}
    if isinstance(value, (list, tuple)):
        return [exact_value(v) for v in value]
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('NON_STRING_SNAPSHOT_KEY')
        return {k: exact_value(v) for k, v in value.items()}
    if hasattr(value, 'getSize') and hasattr(value, 'getItem'):
        return [exact_value(value.getItem(i)) for i in range(value.getSize())]
    if hasattr(value, 'get'):
        return exact_value(value.get())
    fields = [k for k in ('x', 'y', 'z', 'w') if hasattr(value, k)]
    if fields:
        return {k: exact_value(getattr(value, k)) for k in fields}
    raise ValueError('UNSUPPORTED_SNAPSHOT_VALUE:' + type(value).__name__)


def graph_snapshot(graph, *, include_positions=False):
    """Read every node/property/edge/root and nested property graph.

    SDK exceptions propagate; callers must stop before mutation on unavailable
    evidence. No saving, loading, cooking or modification occurs here.
    """
    from sd.api.sdproperty import SDPropertyCategory as C

    def properties(obj):
        rows = []
        for label, cat in (('input', C.Input), ('output', C.Output), ('annotation', C.Annotation)):
            for p in obj.getProperties(cat):
                if cat == C.Annotation and p.getId() == 'icon':
                    # SDK graph preview icon is a render/UI cache, not an input.
                    continue
                row = {'category': label, 'id': p.getId(), 'type': str(p.getType().getId())}
                # Output values can be transient render data; their types/edges are semantic.
                if cat != C.Output:
                    row['value'] = exact_value(obj.getPropertyValue(p))
                rows.append(row)
        return sorted(rows, key=lambda r: (r['category'], r['id']))

    nodes, edges = [], []
    for node in graph.getNodes():
        nid = str(node.getIdentifier())
        row = {'id': nid, 'definition': str(node.getDefinition().getId()),
               'properties': properties(node), 'nested': {}}
        if include_positions:
            pos = node.getPosition()
            row['position'] = [float(pos.x), float(pos.y)]
        if 'instance' in row['definition']:
            resource = node.getReferencedResource()
            if resource is None:
                raise ValueError('UNRESOLVED_INSTANCE:' + nid)
            row['reference'] = [str(resource.getPackage().getFilePath()), str(resource.getUrl())]
        for prop in node.getProperties(C.Input):
            for conn in node.getPropertyConnections(prop):
                edges.append([str(conn.getInputPropertyNode().getIdentifier()),
                              str(conn.getInputProperty().getId()), nid, str(prop.getId())])
            sub = node.getPropertyGraph(prop)
            if sub is not None:
                row['nested'][prop.getId()] = graph_snapshot(sub, include_positions=include_positions)
        nodes.append(row)
    ids = [n['id'] for n in nodes]
    if len(set(ids)) != len(ids):
        raise ValueError('DUPLICATE_NODE_ID')
    # Both function and compositing graph SDKs expose getOutputNodes in supported runtime.
    return {'id': str(graph.getIdentifier()), 'properties': properties(graph),
            'nodes': sorted(nodes, key=lambda n: n['id']), 'edges': sorted(edges),
            'roots': sorted(str(n.getIdentifier()) for n in graph.getOutputNodes())}


def package_snapshot(package, graph_reader=None):
    reader = graph_reader or graph_snapshot
    resources = []
    for r in package.getChildrenResources(True):
        if hasattr(r, 'getNodes'):
            resources.append({'id': str(r.getIdentifier()), 'content': reader(r)})
        else:
            # Unsupported resource contents cannot silently count as protected.
            if type(r).__name__ != 'SDResourceFolder':
                raise ValueError('UNSUPPORTED_PACKAGE_RESOURCE:' + type(r).__name__)
            resources.append({'id': str(r.getIdentifier()), 'folder': str(r.getUrl())})
    return {'path': str(package.getFilePath() or ''),
            'resources': sorted(resources, key=lambda r: (r['id'], digest(r)))}
