# -*- coding: utf-8 -*-
"""Dump every built-in library Function Graph node-by-node (runs INSIDE Designer).

This is view A of the three-way library verification.  For each
``SDSBSFunctionGraph`` in ``resources/packages/functions.sbs`` it records:

  * group path, identifier, label, description, tags (from the live resource)
  * formal inputs: property id / label / declared type names / default value
  * output node(s) and the output-node definition
  * nodes: definition id, position, ``instance_of`` target, every non-connected
    property value (constants and variable names) at **exact float32 precision**
  * edges: source node + source port -> target node + target port

Connection direction note (measured, easy to get wrong): on an
``SDConnection`` obtained from ``node.getPropertyConnections(inputProperty)``,
``getInputPropertyNode()`` is the **source** (data producer) and
``getOutputPropertyNode()`` is the **consumer** (this node).

Value precision note (measured): ``SDValueFloat3.get()`` returns a structured
``sdbasetypes.float3``; ``str()`` on it truncates to 6 decimals, so components
are read individually here.  The XML view is compared at float32 resolution.

Side effect: the library package may be loaded into the session (read-only; it
is never modified or saved by this script). Record whether this run loaded it;
unload only a run-owned, confirmed-unmodified package when the host can do so
safely. Otherwise leave it loaded and report that residue.

Usage (from an MCP ``execute_sd_code`` call or the SD Python console):
    exec(open(r'<skill>\\scripts\\dump_library_functions.py', encoding='utf-8').read())

Then verify against the shipped XML and render the catalogue:
    python scripts/verify_library_functions.py parse-xml <SD>/resources/packages/functions.sbs --out xml.json
    python scripts/verify_library_functions.py diff <sdk.json> xml.json --json diff.json --verbose
    python scripts/verify_library_functions.py eval <sdk.json> xml.json
    python scripts/render_library_catalog.py --sdk <sdk.json> --xml xml.json --diff diff.json \
        --md references/SD_LIBRARY_FUNCTIONS_<version>.md --json references/library_functions_<version>.json
"""
import json
import os

import sd
from sd.api.sdproperty import SDPropertyCategory as C

OUT_JSON = os.environ.get('SD_LIB_DUMP', r'E:\SD_AI\_probe\library_dump.json')
LIB_PKG = None          # set to an absolute path to override detection

app = sd.getContext().getSDApplication()
mgr = app.getPackageMgr()


def find_library_package():
    if LIB_PKG:
        return LIB_PKG
    cands = []
    try:
        import sd.tools.io as IO
        api_root = IO.getAPIRootDir()                      # <SD>/resources/python
        sd_root = os.path.dirname(os.path.dirname(os.path.dirname(api_root)))
        cands.append(os.path.join(sd_root, 'resources', 'packages', 'functions.sbs'))
    except Exception:
        pass
    cands.append(r'C:\Program Files\Adobe\Adobe Substance 3D Designer\resources\packages\functions.sbs')
    for c in cands:
        if os.path.isfile(c):
            return c
    raise RuntimeError('functions.sbs not found')


def val_str(v):
    """Exact value string; structured floatN/intN values are read per component."""
    if v is None:
        return None
    try:
        x = v.get()
    except Exception:
        try:
            x = str(v)
        except Exception:
            return '<?>'
    if isinstance(x, float):
        return '%.9g' % x
    if isinstance(x, (int, bool, str)) or x is None:
        return x
    comps = []
    for a in ('x', 'y', 'z', 'w'):
        if hasattr(x, a):
            c = getattr(x, a)
            comps.append('%.9g' % c if isinstance(c, float) else str(c))
    if comps:
        return ','.join(comps)
    return str(x)


def prop_value(node, p):
    for getter in ('getPropertyValue',):
        try:
            return val_str(getattr(node, getter)(p))
        except Exception:
            pass
    try:
        return val_str(p.getDefaultValue())
    except Exception:
        return None


def read_annotation(r, pid):
    for cat in (C.Annotation, C.Input):
        try:
            v = r.getPropertyValueFromId(pid, cat)
        except Exception:
            v = None
        if v is not None:
            s = val_str(v)
            if s:
                return s
    return None


def formal_types(p):
    out = []
    try:
        tid = str(p.getType().getId())
        if tid:
            out.append(tid)
    except Exception:
        pass
    try:
        for bt in p.getType().getBaseTypes() or []:
            t = str(bt.getId())
            if t not in out:
                out.append(t)
    except Exception:
        pass
    try:
        if p.getType().isVariadic():
            out.append('variadic')
    except Exception:
        pass
    return out


pkg_path = find_library_package()
pk = mgr.getUserPackageFromFilePath(pkg_path)
if pk is None:
    pk = mgr.loadUserPackage(pkg_path, True, True)
print('library package: %s' % pk.getFilePath())

resources = pk.getChildrenResources(True)
funcs = [r for r in resources if type(r).__name__ == 'SDSBSFunctionGraph']
folders = [r for r in resources if type(r).__name__ == 'SDResourceFolder']
print('resources=%d  functionGraphs=%d  folders=%d' % (len(resources), len(funcs), len(folders)))

dump = {
    'source_file': pk.getFilePath(),
    'generator': 'scripts/dump_library_functions.py',
    'functions': {},
}

problems = []
for r in funcs:
    ident = r.getIdentifier()
    url = r.getUrl() if hasattr(r, 'getUrl') else ''
    group = url.split('pkg:///')[-1].split('?')[0]
    group = '/'.join(group.split('/')[:-1])
    nodes = list(r.getNodes())
    index = {}      # id(pyobject) -> i   (SDSBSFunctionNode exposes no getUID)
    by_pos = {}     # (def, x, y) -> i
    for i, n in enumerate(nodes):
        index[id(n)] = i
        try:
            by_pos[(str(n.getDefinition().getId()), float(n.getPosition()[0]), float(n.getPosition()[1]))] = i
        except Exception:
            pass

    def node_index(n):
        i = index.get(id(n))
        if i is not None:
            return i
        try:
            return by_pos.get((str(n.getDefinition().getId()), float(n.getPosition()[0]), float(n.getPosition()[1])))
        except Exception:
            return None

    node_recs = []
    for i, n in enumerate(nodes):
        defid = str(n.getDefinition().getId())
        rec = {'i': i, 'def': defid}
        try:
            rec['pos'] = [float(n.getPosition()[0]), float(n.getPosition()[1])]
        except Exception:
            pass
        try:
            rec['id'] = n.getIdentifier()
        except Exception:
            pass
        if defid == 'sbs::function::instance':
            try:
                rr = n.getReferencedResource()
                rec['instance_of'] = rr.getIdentifier() if rr is not None else None
                if rr is not None and hasattr(rr, 'getUrl'):
                    rec['instance_group'] = rr.getUrl().split('pkg:///')[-1].split('?')[0]
            except Exception as e:
                rec['instance_of'] = 'ERR:%s' % e
        consts = {}
        for p in n.getProperties(C.Input):
            try:
                connected = bool(n.getPropertyConnections(p))
            except Exception:
                connected = False
            if connected:
                continue
            v = prop_value(n, p)
            if v is not None:
                consts[p.getId()] = v
        for p in n.getProperties(C.Annotation):
            if p.getId() in ('label', 'description'):
                v = prop_value(n, p)
                if v:
                    consts[p.getId()] = v
        if consts:
            rec['consts'] = consts
        node_recs.append(rec)

    edges = []
    for i, n in enumerate(nodes):
        for p in n.getProperties(C.Input):
            for c in (n.getPropertyConnections(p) or []):
                try:
                    src = c.getInputPropertyNode()           # source (data producer)
                    src_port = c.getInputProperty().getId()  # source output port
                    dst_port = c.getOutputProperty().getId()  # this node's input port
                    si = node_index(src)
                    if si is None:
                        raise RuntimeError('source node not in node list: %s' % src)
                except Exception as e:
                    problems.append('%s: edge read failed on %s.%s (%s)' % (ident, i, p.getId(), e))
                    continue
                edges.append({'from': si, 'from_port': src_port, 'to': i, 'to_port': dst_port or p.getId()})

    formals = []
    for p in r.getProperties(C.Input):
        dv = None
        try:
            dv = val_str(r.getPropertyValue(p))
        except Exception:
            dv = None
        if dv is None:
            dv = prop_value(r, p)
        formals.append({
            'id': p.getId(),
            'label': p.getLabel(),
            'types': formal_types(p),
            'default': dv,
        })

    graph_outputs = []
    for p in r.getProperties(C.Output):
        graph_outputs.append({'id': p.getId(), 'label': p.getLabel(), 'types': formal_types(p)})

    outs = []
    for o in r.getOutputNodes():
        rec = {'i': node_index(o), 'def': str(o.getDefinition().getId())}
        try:
            types = []
            for p in o.getProperties(C.Output):
                for bt in (p.getType().getBaseTypes() or []):
                    types.append(str(bt.getId()))
            rec['out_types'] = sorted(set(types))
        except Exception:
            pass
        outs.append(rec)

    dump['functions'][ident] = {
        'group': group,
        'label': read_annotation(r, 'label'),
        'description': read_annotation(r, 'description'),
        'tags': read_annotation(r, 'tags'),
        'formals': formals,
        'graph_outputs': graph_outputs,
        'outputs': outs,
        'node_count': len(nodes),
        'nodes': node_recs,
        'edges': edges,
    }

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(dump, f, ensure_ascii=False, separators=(',', ':'))

size = os.path.getsize(OUT_JSON)
print('wrote %s (%d bytes, %d functions)' % (OUT_JSON, size, len(dump['functions'])))
print('problems: %d' % len(problems))
for p in problems[:10]:
    print('   ', p)

by_group = {}
for k, v in dump['functions'].items():
    by_group.setdefault(v['group'], []).append(k)
print()
print('groups:')
for g in sorted(by_group):
    print('  %-28s %d' % (g, len(by_group[g])))
print()
tot_nodes = sum(v['node_count'] for v in dump['functions'].values())
tot_edges = sum(len(v['edges']) for v in dump['functions'].values())
empty_outs = [k for k, v in dump['functions'].items() if not v['outputs']]
no_desc = [k for k, v in dump['functions'].items() if not v['description']]
inst_users = sorted(k for k, v in dump['functions'].items()
                    if any(n['def'] == 'sbs::function::instance' for n in v['nodes']))
print('total nodes=%d total edges=%d' % (tot_nodes, tot_edges))
print('functions without an output node: %d %s' % (len(empty_outs), empty_outs[:8]))
print('functions without a description: %d %s' % (len(no_desc), no_desc[:8]))
print('functions calling other library functions: %d' % len(inst_users))
print('  sample:', inst_users[:12])
