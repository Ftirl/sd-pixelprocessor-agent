# -*- coding: utf-8 -*-
"""Independently verify every built-in library Function Graph.

Three independent views of the same 171 function graphs are compared:

  A. SDK view      -- scripts/dump_library_functions.py, produced inside Designer
                      by walking the live SDSBSFunctionGraph objects.
  B. XML view      -- this script parsing resources/packages/functions.sbs
                      (a different code path: raw disk XML, uid references).
  C. Cooked values -- the measured BMP results from scripts/probe_sd_semantics.py.

Stages
  parse-xml  : write the XML view as JSON (same shape as the SDK dump)
  diff       : per-function structural diff of A vs B (nodes, edges, constants,
               output node, nested-call targets, formals) -> PASS/MISMATCH
  eval       : evaluate the A netlist for the functions whose value was measured
               by a real cook, and compare -> closes the loop A vs C
  report     : diff + eval + a Markdown/JSON report

Usage
  python verify_library_functions.py parse-xml <functions.sbs> --out xml.json
  python verify_library_functions.py diff      <sdk.json> <xml.json> [--json out.json] [--verbose]
  python verify_library_functions.py eval      <sdk.json> <xml.json>
"""
import argparse
import json
import os
import re
import struct
import sys

# ---------------------------------------------------------------- XML parsing

RE_FUNCTION = re.compile(r'<function>(.*?)</function>', re.S)
RE_PARAM_NODE = re.compile(r'<paramNode>(.*?)</paramNode>', re.S)
RE_PARAM_INPUT = re.compile(r'<paraminput>(.*?)</paraminput>', re.S)


def _v(blob, tag):
    m = re.search(r'<%s v="([^"]*)"' % tag, blob)
    return m.group(1) if m else None


def _all_v(blob, tag):
    return re.findall(r'<%s v="([^"]*)"' % tag, blob)


def f32(x):
    """Round-trip through single precision: SD stores its constants as float32."""
    try:
        return struct.unpack('f', struct.pack('f', float(x)))[0]
    except (TypeError, ValueError, OverflowError):
        return float(x)


def canon_const(v):
    """Canonicalise a constant so the SDK and XML spellings compare equal.

    Floats are normalised to float32 and printed with 9 significant digits, which
    is exactly what single precision can round-trip; the SDK's own value
    stringification truncates at 6 decimals and is NOT used.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return '%.9g' % f32(v)
    if isinstance(v, (list, tuple)):
        return ','.join(canon_const(x) for x in v)
    s = str(v).strip()
    pairs = re.findall(r'([xyzw]):\s*(-?[\d.eE+]+)', s)
    if pairs and len(pairs) >= 2:
        return ','.join('%.9g' % f32(p[1]) for p in pairs)
    if ',' in s:
        return ','.join('%.9g' % f32(p) for p in s.split(',') if p.strip())
    try:
        return '%.9g' % f32(float(s))
    except ValueError:
        return s


def xml_constants(node_blob, defname=None):
    """funcDatas/funcData/constantValue children -> {'__constant__': canonical value}.

    XML keys constants by the atom's own name (e.g. const_float1 / swizzle1); the
    SDK exposes the same slot as the property id ``__constant__``.  Absent
    funcDatas means "atom defaults" (e.g. swizzle index 0), handled by the diff.
    """
    out = {}
    fd = re.search(r'<funcDatas>(.*?)</funcDatas>', node_blob, re.S)
    if not fd:
        return out
    for data in re.findall(r'<funcData>(.*?)</funcData>', fd.group(1), re.S):
        name = _v(data, 'name')
        cv = re.search(r'<constantValue>(.*?)</constantValue>', data, re.S)
        if cv is None:
            continue
        inner = cv.group(1)
        kind = re.search(r'<(constantValue\w+)', inner)
        if kind is None:
            continue
        tag = kind.group(1)
        raw = _v(inner, tag)
        if raw is None:
            continue
        if tag == 'constantValueString':
            val = raw
        elif tag.startswith('constantValueFloat'):
            parts = [p for p in re.split(r'[\s,]+', raw.strip()) if p]
            val = float(parts[0]) if len(parts) == 1 else tuple(float(p) for p in parts)
        elif tag.startswith('constantValueInt'):
            parts = [p for p in re.split(r'[\s,]+', raw.strip()) if p]
            val = int(parts[0]) if len(parts) == 1 else tuple(int(p) for p in parts)
        elif tag == 'constantValueBool':
            val = '1' if raw in ('1', 'true', 'True') else '0'
        else:
            val = raw
        if name == 'instance' or name != defname:
            key = name or 'value'
        else:
            key = '__constant__'
        out[key] = val if key != 'instance' and not str(name).startswith('constantValue') else val
        if key == '__constant__':
            out[key] = canon_const(val)
    return out


def parse_xml(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    functions = {}
    for fm in RE_FUNCTION.finditer(text):
        blob = fm.group(1)
        ident = _v(blob, 'identifier')
        attrs = re.search(r'<attributes>(.*?)</attributes>', blob, re.S)
        attr = attrs.group(1) if attrs else ''
        label = _v(attr, 'label')
        description = _v(attr, 'description')
        tags = _v(attr, 'tags')
        author = _v(attr, 'author')

        # group path: walk the enclosing <group> identifiers by prefix scan
        prefix = text[:fm.start()]
        groups = _all_v(prefix, 'identifier')[-0:] if False else None
        open_groups = re.findall(r'<group>|<identifier v="([^"]*)"/>|</group>', prefix)
        stack = []
        for g in re.finditer(r'<group>(.*?)(?=<group>|</group>)', prefix, re.S):
            pass
        # cheap and reliable: keep the last group identifiers seen in the stack
        depth = 0
        stack = []
        for m in re.finditer(r'<group>|</group>|<identifier v="([^"]*)"/>', prefix):
            tok = m.group(0)
            if tok == '<group>':
                depth += 1
                stack.append(None)
            elif tok == '</group>':
                if stack:
                    stack.pop()
                depth -= 1
            else:
                if stack and stack[-1] is None:
                    stack[-1] = m.group(1)
        group = '/'.join([s for s in stack if s])

        formals = []
        pi = re.search(r'<paraminputs>(.*?)</paraminputs>', blob, re.S)
        if pi:
            for pm in RE_PARAM_INPUT.finditer(pi.group(1)):
                pblob = pm.group(1)
                dv = re.search(r'<defaultValue>(.*?)</defaultValue>', pblob, re.S)
                dtag = None
                draw = None
                if dv:
                    k = re.search(r'<(constantValue\w+)', dv.group(1))
                    if k:
                        dtag = k.group(1)
                        draw = _v(dv.group(1), dtag)
                formals.append({
                    'id': _v(pblob, 'identifier'),
                    'uid': _v(pblob, 'uid'),
                    'type_id': _v(pblob, 'type'),
                    'default_tag': dtag,
                    'default_raw': draw,
                })

        rootnode = _v(blob, 'rootnode')

        pv = re.search(r'<paramNodes>(.*?)</paramNodes>', blob, re.S)
        nodes = []
        uid_to_i = {}
        uid_to_key = {}
        if pv:
            for i, nm in enumerate(RE_PARAM_NODE.finditer(pv.group(1))):
                nb = nm.group(1)
                uid = _v(nb, 'uid')
                gpos = _v(nb, 'gpos')
                pos = [float(x) for x in gpos.split()[:2]] if gpos else None
                defname = _v(nb, 'function')
                consts = xml_constants(nb, defname)
                rec = {
                    'i': i, 'uid': uid, 'def': 'sbs::function::%s' % defname,
                    'pos': pos, 'type_id': _v(nb, 'type'), 'consts': consts,
                }
                if defname == 'instance':
                    rec['instance_of_url'] = consts.get('instance')
                    rec['instance_of'] = (consts.get('instance') or '').split('?')[0].rstrip('/').split('/')[-1]
                nodes.append(rec)
                uid_to_i[uid] = i
                uid_to_key[uid] = (rec['def'], pos)

        edges = []
        if pv:
            for nm in RE_PARAM_NODE.finditer(pv.group(1)):
                nb = nm.group(1)
                dst_uid = _v(nb, 'uid')
                conns = re.search(r'<connections>(.*?)</connections>', nb, re.S)
                if not conns:
                    continue
                for cm in re.finditer(r'<connection>(.*?)</connection>', conns.group(1), re.S):
                    cblob = cm.group(1)
                    port = _v(cblob, 'identifier')
                    src_uid = _v(cblob, 'connRef')
                    edges.append({
                        'from': uid_to_i.get(src_uid), 'from_uid': src_uid,
                        'to': uid_to_i.get(dst_uid), 'to_uid': dst_uid,
                        'to_port': port, 'from_port': 'unique_filter_output',
                    })

        root_index = uid_to_i.get(rootnode)
        # ``_v(blob, 'type')`` returns the first descendant <type>, which is
        # commonly the first formal's type rather than the graph output type.
        # The root node is the actual typed output in functions.sbs.
        declared_output_type = (
            nodes[root_index].get('type_id')
            if root_index is not None and root_index < len(nodes)
            else None
        )

        functions[ident] = {
            'group': group, 'label': label, 'description': description,
            'tags': tags, 'author': author, 'formals': formals,
            'declared_output_type_id': declared_output_type,
            'root_uid': rootnode,
            'outputs': [{'i': root_index, 'uid': rootnode,
                         'def': (uid_to_key.get(rootnode) or ('?',))[0]}],
            'node_count': len(nodes), 'nodes': nodes, 'edges': edges,
        }
    return {
        'source_file': path,
        'generator': 'scripts/verify_library_functions.py (parse-xml)',
        'functions': functions,
    }


# ------------------------------------------------------------------ XML vs SDK

def consts_sig(node):
    c = dict((k, canon_const(v)) for k, v in (node.get('consts') or {}).items()
             if k not in ('label', 'description'))
    return ';'.join('%s=%s' % (k, c[k]) for k in sorted(c))


def key_of(node):
    """Node identity used to join the two dumps: definition + rounded position."""
    pos = node.get('pos')
    if not pos:
        return (node['def'], 'nopos', consts_sig(node))
    return (node['def'], '%.3f' % pos[0], '%.3f' % pos[1])


def sort_key(node):
    return '%s|%s|%s' % key_of(node)


# Atoms whose funcDatas the XML omits when the value equals the atom default.
# Values derived from the SDK dump (each def showed exactly one value across all
# omissions -- the diff re-checks every omission against this table, so a
# deviation surfaces as a mismatch instead of being silently accepted).
ATOM_DEFAULTS = {
    'sbs::function::const_float1': '0', 'sbs::function::const_float2': '0,0',
    'sbs::function::const_float3': '0,0,0', 'sbs::function::const_float4': '0,0,0,0',
    'sbs::function::const_int1': '0', 'sbs::function::const_int2': '0,0',
    'sbs::function::const_int3': '0,0,0', 'sbs::function::const_int4': '0,0,0,0',
    'sbs::function::swizzle1': '0', 'sbs::function::swizzle2': '0,1',
    'sbs::function::swizzle3': '0,1,2', 'sbs::function::swizzle4': '0,1,2,3',
}
ABSENT_MEANS_DEFAULT = dict((k, {v}) for k, v in ATOM_DEFAULTS.items())


def edge_key(edge, nodes):
    src = nodes[edge['from']] if edge.get('from') is not None else None
    dst = nodes[edge['to']] if edge.get('to') is not None else None
    return (key_of(src) if src else None, key_of(dst) if dst else None, edge.get('to_port'))


def diff(sdk, xml, verbose=False):
    res = {'functions': {}, 'summary': {}, 'type_map': {}, 'notes': []}
    mismatches = 0
    type_pairs = {}
    type_conflicts = []
    joined_without_position = 0
    default_omissions = 0

    for ident in sorted(set(sdk) | set(xml)):
        a = sdk.get(ident)
        b = xml.get(ident)
        issues = []
        if a is None:
            issues.append('missing in SDK dump')
        elif b is None:
            issues.append('missing in XML dump')
        else:
            # ---- formals / declared types
            for fa, fb in zip(a['formals'], b['formals']):
                tid = fb.get('type_id')
                names = tuple(fa.get('types') or [])
                if tid is not None and names:
                    prev = type_pairs.get(tid)
                    if prev is None:
                        type_pairs[tid] = names
                    elif prev != names:
                        type_conflicts.append((ident, tid, prev, names))
            fa = [f['id'] for f in a['formals']]
            fb = [f['id'] for f in b['formals']]
            if fa != fb:
                issues.append('formal ids differ: sdk=%s xml=%s' % (fa, fb))

            # ---- nodes: two-pass identity join
            map_xml_to_sdk = {}
            used_sdk = set()
            kbmap = {}
            for j, n in enumerate(b['nodes']):
                kbmap.setdefault(key_of(n), []).append(j)
            for i, n in enumerate(a['nodes']):
                cand = kbmap.get(key_of(n)) or []
                if len(cand) == 1:
                    map_xml_to_sdk[cand[0]] = i
                    used_sdk.add(i)
            left_xml = [j for j in range(len(b['nodes'])) if j not in map_xml_to_sdk]
            left_sdk = [i for i in range(len(a['nodes'])) if i not in used_sdk]
            if left_xml or left_sdk:
                # fallback: match by definition + constant signature when unique
                sig_sdk = {}
                for i in left_sdk:
                    sig_sdk.setdefault((a['nodes'][i]['def'], consts_sig(a['nodes'][i])), []).append(i)
                for j in list(left_xml):
                    n = b['nodes'][j]
                    cand = sig_sdk.get((n['def'], consts_sig(n))) or []
                    if len(cand) == 1:
                        map_xml_to_sdk[j] = cand[0]
                        left_xml.remove(j)
                        left_sdk.remove(cand[0])
                        joined_without_position += 1
            if left_xml or left_sdk:
                issues.append('unmatched nodes: sdk=%d xml=%d (e.g. %s / %s)' % (
                    len(left_sdk), len(left_xml),
                    [key_of(a['nodes'][i]) for i in left_sdk[:2]],
                    [key_of(b['nodes'][j]) for j in left_xml[:2]]))

            # ---- node counts and identities
            if a['node_count'] != b['node_count']:
                issues.append('node count %d vs %d' % (a['node_count'], b['node_count']))

            # ---- edges, expressed in node identity space
            def edge_set(dump, side):
                out = []
                for e in dump['edges']:
                    if e.get('from') is None or e.get('to') is None:
                        out.append(('UNRESOLVED', e))
                        continue
                    out.append((key_of(dump['nodes'][e['from']]),
                                key_of(dump['nodes'][e['to']]),
                                e.get('to_port')))
                return out
            ea = edge_set(a, 'sdk')
            eb_xml = edge_set(b, 'xml')
            # XML is the reference for edges (it records what the file declares);
            # SDK edges are mapped into SDK identity then reversed via the join.
            eb = []
            stale_edges = []
            for e in b['edges']:
                if e.get('from') is None or e.get('to') is None:
                    eb.append(('UNRESOLVED', e))
                    continue
                sj = map_xml_to_sdk.get(e['from'])
                tj = map_xml_to_sdk.get(e['to'])
                if sj is None or tj is None:
                    eb.append(('UNJOINED', key_of(b['nodes'][e['from']]),
                               key_of(b['nodes'][e['to']]), e.get('to_port')))
                else:
                    eb.append((key_of(a['nodes'][sj]), key_of(a['nodes'][tj]), e.get('to_port')))
                # explained XML-only edges: connection into a formal the target
                # function does not declare (stale data in the shipped file)
                dst = b['nodes'][e['to']]
                if dst['def'].endswith('::instance'):
                    target = dst.get('instance_of')
                    tformals = set(f['id'] for f in (xml.get(target) or {}).get('formals', []))
                    if tformals and e.get('to_port') not in tformals:
                        stale_edges.append({
                            'in': ident, 'target': target, 'port': e.get('to_port'),
                            'declared_formals': sorted(tformals),
                        })
                        if sj is not None:
                            eb[-1] = ('STALE', key_of(a['nodes'][sj]), key_of(a['nodes'][tj]),
                                      e.get('to_port'))
            ev = [x for x in eb if x[0] != 'STALE']
            ca, cb = sorted(map(str, ea)), sorted(map(str, ev))
            if ca != cb:
                only_a = [x for x in ca if x not in cb][:3]
                only_b = [x for x in cb if x not in ca][:3]
                issues.append('edge topology differs: sdk-only=%s xml-only=%s' % (only_a, only_b))
            if stale_edges:
                res.setdefault('stale_edges', []).extend(stale_edges)

            # ---- constants
            for j, i in sorted(map_xml_to_sdk.items()):
                na, nb = a['nodes'][i], b['nodes'][j]
                cax = dict((k, canon_const(v)) for k, v in (na.get('consts') or {}).items()
                           if k not in ('label', 'description', 'instance'))
                cbx = dict((k, canon_const(v)) for k, v in (nb.get('consts') or {}).items()
                           if k not in ('label', 'description', 'instance'))
                xml_only = set(cbx) - set(cax)
                sdk_only = set(cax) - set(cbx)
                if xml_only:
                    issues.append('consts only in XML at %s: %s' % (
                        key_of(na), dict((k, cbx[k]) for k in xml_only)))
                for k in sdk_only:
                    allowed = ABSENT_MEANS_DEFAULT.get(na['def'], set())
                    if cax[k] in allowed:
                        default_omissions += 1
                    else:
                        issues.append('consts only in SDK at %s: %s=%s (not a known default)' % (
                            key_of(na), k, cax[k]))
                for k in set(cax) & set(cbx):
                    if cax[k] != cbx[k]:
                        issues.append('consts differ at %s: %s sdk=%s xml=%s' % (
                            key_of(na), k, cax[k], cbx[k]))

            # ---- output node
            oa = [key_of(a['nodes'][o['i']]) if o.get('i') is not None else None for o in a['outputs']]
            ob = [key_of(b['nodes'][o['i']]) if o.get('i') is not None else None for o in b['outputs']]
            if oa != ob:
                issues.append('output node differs: sdk=%s xml=%s' % (oa, ob))

            # ---- nested-call targets
            ia = sorted(n.get('instance_of') or '' for n in a['nodes'] if n['def'].endswith('::instance'))
            ib = sorted(n.get('instance_of') or '' for n in b['nodes'] if n['def'].endswith('::instance'))
            if ia != ib:
                issues.append('instance targets differ: sdk=%s xml=%s' % (ia, ib))

        if issues:
            mismatches += 1
        res['functions'][ident] = {
            'status': 'MISMATCH' if issues else 'PASS',
            'issues': issues,
            'nodes': (a or {}).get('node_count'),
            'edges': len((a or {}).get('edges', [])),
            'group': (a or b or {}).get('group'),
        }
        if verbose and issues:
            print('MISMATCH %-26s %s' % (ident, '; '.join(issues)[:220]))

    if type_conflicts:
        res['notes'].append('type-id conflicts: %s' % type_conflicts[:5])
    res['type_map'] = dict((k, list(v)) for k, v in sorted(type_pairs.items()))
    res['derived_defaults'] = ATOM_DEFAULTS
    res['joined_without_position'] = joined_without_position
    res['default_omissions'] = default_omissions
    res['notes'].append('nodes joined by (def,consts) because XML had no position: %d' % joined_without_position)
    res['notes'].append('SDK-reported defaults absent from XML (known atoms): %d' % default_omissions)
    res['notes'].append('XML-only stale connections (target formal does not exist): %d' % len(res.get('stale_edges', [])))
    res['summary'] = {
        'functions': len(res['functions']),
        'pass': sum(1 for v in res['functions'].values() if v['status'] == 'PASS'),
        'mismatch': mismatches,
        'nodes': sum(v['nodes'] or 0 for v in res['functions'].values()),
        'edges': sum(v['edges'] for v in res['functions'].values()),
    }
    return res


# ------------------------------------------------------- netlist evaluation

class NotEvaluable(Exception):
    pass


UNARY = {
    'floor': lambda a: _map1(a, _floor), 'ceil': lambda a: _map1(a, _ceil),
    'abs': lambda a: _map1(a, abs), 'neg': lambda a: _map1(a, lambda x: -x),
    'sqrt': lambda a: _map1(a, lambda x: x ** 0.5 if x >= 0 else float('nan')),
    'exp': lambda a: _map1(a, lambda x: 2.718281828459045 ** x),
    'pow2': lambda a: _map1(a, lambda x: x * x),
    'log2': lambda a: _map1(a, _log2), 'log': lambda a: _map1(a, _log2),
    'sign': lambda a: _map1(a, lambda x: 1.0 if x >= 0 else -1.0),
}
BINARY = {
    'add': lambda a, b: _map2(a, b, lambda x, y: x + y),
    'sub': lambda a, b: _map2(a, b, lambda x, y: x - y),
    'mul': lambda a, b: _map2(a, b, lambda x, y: x * y),
    'div': lambda a, b: _map2(a, b, lambda x, y: x / y if y else float('inf')),
    'mod': lambda a, b: _map2(a, b, lambda x, y: x - y * _floor(x / y)),
    'min': lambda a, b: _map2(a, b, min), 'max': lambda a, b: _map2(a, b, max),
    'pow': lambda a, b: _map2(a, b, lambda x, y: x ** y),
    'lr': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x < y else 0.0),
    'lreq': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x <= y else 0.0),
    'gt': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x > y else 0.0),
    'gteq': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x >= y else 0.0),
    'eq': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x == y else 0.0),
    'neq': lambda a, b: _map2(a, b, lambda x, y: 1.0 if x != y else 0.0),
    'atan2': lambda a, b: _map2(a, b, lambda x, y: _atan2(x, y)),
}
VAR_DEFS = ('get_float1', 'get_float2', 'get_float3', 'get_float4', 'get_integer1',
            'get_integer2', 'get_integer3', 'get_integer4')


def _floor(x):
    import math
    return float(math.floor(x))


def _ceil(x):
    import math
    return float(math.ceil(x))


def _log2(x):
    import math
    return float(math.log2(x)) if x > 0 else float('-inf')


def _atan2(y, x):
    import math
    return float(math.atan2(y, x))


def _map1(a, f):
    if isinstance(a, (list, tuple)):
        return tuple(f(x) for x in a)
    return f(a)


def _map2(a, b, f):
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        aa = a if isinstance(a, (list, tuple)) else (a,) * len(b)
        bb = b if isinstance(b, (list, tuple)) else (a,) * len(a)
        if len(aa) != len(bb):
            raise NotEvaluable('dimension mismatch %s vs %s' % (len(aa), len(bb)))
        return tuple(f(x, y) for x, y in zip(aa, bb))
    return f(a, b)


def _num(v):
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            raise NotEvaluable('non-numeric constant %r' % v)
    return float(v)


def _const(rec):
    c = rec.get('consts') or {}
    v = c.get('__constant__')
    if v is None:
        v = ATOM_DEFAULTS.get(rec['def'])          # XML omits default-valued constants
        if v is None:
            raise NotEvaluable('no __constant__ on %s' % rec['def'])
        return tuple(float(x) for x in v.split(',')) if ',' in v else float(v)
    if isinstance(v, (list, tuple)):
        return tuple(_num(x) for x in v)
    if isinstance(v, str) and re.search(r'[xyz]:', v):
        parts = re.findall(r'[xyz]:\s*(-?[\d.eE+]+)', v)
        return tuple(float(p) for p in parts)
    return _num(v)


def evaluate(fn_name, inputs, lib, depth=0):
    if depth > 12:
        raise NotEvaluable('recursion too deep')
    fn = lib[fn_name]
    nodes = fn['nodes']
    edges = fn['edges']
    incoming = {}
    for e in edges:
        port = e.get('to_port') or e.get('port') or 'input'
        incoming.setdefault(e['to'], {})[port] = e['from']
    memo = {}
    env = dict(inputs)

    def ev(i):
        if i in memo:
            return memo[i]
        rec = nodes[i]
        d = rec['def'].split('::')[-1]
        src = lambda port: ev(incoming[i][port]) if port in incoming.get(i, {}) else None
        if d in VAR_DEFS:
            name = (rec.get('consts') or {}).get('__constant__')
            if name not in env:
                raise NotEvaluable('unbound variable %r' % name)
            val = env[name]
        elif d.startswith('const_'):
            val = _const(rec)
        elif d == 'instance':
            target = rec.get('instance_of')
            if target not in lib:
                raise NotEvaluable('unknown instance target %r' % target)
            tfn = lib[target]
            args = {}
            for f in tfn['formals']:
                v = src(f['id'])
                if v is None:
                    raise NotEvaluable('instance %s: unbound formal %s' % (target, f['id']))
                args[f['id']] = v
            val = evaluate(target, args, lib, depth + 1)
        elif d in UNARY:
            val = UNARY[d](src('a') if src('a') is not None else src('input'))
        elif d in BINARY:
            val = BINARY[d](src('a'), src('b'))
        elif d in ('mulscalar',):
            vec = src('a')
            sc = src('scalar')
            val = _map2(vec, sc, lambda x, y: x * y)
        elif d == 'ifelse':
            c = src('condition')
            a = src('ifpath')
            b = src('elsepath')
            if isinstance(c, (list, tuple)):
                val = tuple(x if y else z for x, y, z in zip(c, a, b))
            else:
                val = a if c else b
        elif d == 'dot':
            a, b = src('a'), src('b')
            val = sum(x * y for x, y in zip(a, b))
        elif d in ('vector2', 'vector3', 'vector4'):
            n = int(d[-1])
            parts = []
            for i2 in range(n):
                v = src('componentsin' if i2 == 0 else ('componentslast' if i2 == n - 1 else None))
                if v is None:
                    raise NotEvaluable('%s unhandled port for component %d' % (d, i2))
                parts.append(v)
            val = tuple(parts)
        elif d.startswith('swizzle'):
            raise NotEvaluable('swizzle not modelled')
        else:
            raise NotEvaluable('atom %s not modelled' % d)
        memo[i] = val
        return val

    out = fn['outputs'][0]['i']
    return ev(out)


# Values measured by a real cook (8-bit linear BMP, see NATIVE_PROBE_RESULTS).
MEASURED = [
    # (function, {formal: value}, expected, note)
    ('frac', {'input': -0.25}, 0.75, 'floor-based; fmod(x,1) would be -0.25'),
    ('frac', {'input': 1.25}, 0.25, ''),
    ('round_float1', {'input': -2.5}, -2.0, 'floor(x+0.5), half-up toward +inf'),
    ('round_float1', {'input': 2.5}, 3.0, ''),
    ('round_float1', {'input': 2.4}, 2.0, ''),
    ('fmod', {'a': -0.25, 'b': 1.0}, -0.25, 'sign follows the dividend'),
    ('fmod', {'a': 1.25, 'b': -1.0}, 0.25, ''),
    ('sign', {'x': 0.0}, 1.0, 'documented X==0 -> 1'),
    ('sign', {'x': -3.0}, -1.0, ''),
    ('step', {'a': 0.5, 'x': 0.5}, 1.0, 'inclusive x >= a'),
    ('step', {'a': 0.5, 'x': 0.49}, 0.0, ''),
    ('clamp', {'input': -3.0, 'min': 0.0, 'max': 1.0}, 0.0, ''),
    ('clamp', {'input': 2.0, 'min': 0.0, 'max': 1.0}, 1.0, ''),
    ('saturate', {'input': 2.0}, 1.0, ''),
    ('saturate', {'input': -1.0}, 0.0, ''),
]


def eval_stage(lib, tol=1e-6):
    rows = []
    ok = 0
    for name, args, expected, note in MEASURED:
        if name not in lib:
            rows.append({'fn': name, 'args': args, 'status': 'MISSING', 'note': note})
            continue
        try:
            got = evaluate(name, dict(args), lib)
        except NotEvaluable as e:
            rows.append({'fn': name, 'args': args, 'status': 'NOT_EVALUABLE',
                         'detail': str(e), 'note': note})
            continue
        got_f = float(got) if not isinstance(got, (list, tuple)) else float(got[0])
        good = abs(got_f - expected) <= tol
        ok += 1 if good else 0
        rows.append({'fn': name, 'args': args, 'netlist_value': got_f,
                     'measured_value': expected, 'status': 'PASS' if good else 'FAIL', 'note': note})
    return rows, ok


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p1 = sub.add_parser('parse-xml')
    p1.add_argument('sbs')
    p1.add_argument('--out', required=True)
    p2 = sub.add_parser('diff')
    p2.add_argument('sdk')
    p2.add_argument('xml')
    p2.add_argument('--json')
    p2.add_argument('--verbose', action='store_true')
    p3 = sub.add_parser('eval')
    p3.add_argument('sdk')
    p3.add_argument('xml')
    a = ap.parse_args()

    if a.cmd == 'parse-xml':
        dump = parse_xml(a.sbs)
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(dump, f, ensure_ascii=False, separators=(',', ':'))
        print('parsed %d functions, %d nodes, %d edges -> %s (%d bytes)' % (
            len(dump['functions']),
            sum(v['node_count'] for v in dump['functions'].values()),
            sum(len(v['edges']) for v in dump['functions'].values()),
            a.out, os.path.getsize(a.out)))
        groups = {}
        for k, v in dump['functions'].items():
            groups[v['group']] = groups.get(v['group'], 0) + 1
        print('groups: %d, e.g. %s' % (len(groups), sorted(groups)[:4]))
        return 0

    sdk = json.load(open(a.sdk, encoding='utf-8'))['functions']
    xmld = json.load(open(a.xml, encoding='utf-8'))['functions']

    if a.cmd == 'diff':
        res = diff(sdk, xmld, verbose=a.verbose)
        s = res['summary']
        print('DIFF: %d functions, PASS=%d MISMATCH=%d, nodes=%d, edges=%d' % (
            s['functions'], s['pass'], s['mismatch'], s['nodes'], s['edges']))
        for k, v in sorted(res['functions'].items()):
            if v['status'] != 'PASS':
                print('  %-26s %s' % (k, '; '.join(v['issues'])[:200]))
        if a.json:
            json.dump(res, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('report ->', a.json)
        return 0 if s['mismatch'] == 0 else 1

    if a.cmd == 'eval':
        rows, ok = eval_stage(sdk)
        print('EVAL (SDK netlist vs measured cook value): %d/%d PASS' % (ok, len(rows)))
        for r in rows:
            if r['status'] == 'PASS':
                print('  PASS %-16s %-28s netlist=%-10s measured=%s' % (
                    r['fn'], r['args'], ('%g' % r['netlist_value']), ('%g' % r['measured_value'])))
            else:
                print('  %-13s %-16s %-28s %s' % (r['status'], r['fn'], r['args'],
                                                  r.get('detail') or r.get('note') or ''))
        rows2, ok2 = eval_stage(xmld) if xmld else ([], 0)
        print('EVAL (XML netlist vs measured cook value): %d/%d PASS' % (ok2, len(rows2)))
        return 0 if ok == len(rows) and ok2 == len(rows2) else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
