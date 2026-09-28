# -*- coding: utf-8 -*-
"""Native numeric probes for Substance Designer function semantics.

Runs INSIDE Substance Designer (sd_mcp_plugin execute_sd_code):
  1. preflight: validate every definition/port id that will be used
  2. build throwaway comp graphs in a NEW scratch package
  3. cook with SDSBSCompGraph.compute()
  4. export outputs to BMP with sd.tools.export.exportSDGraphOutputs
  5. parse pixels back and compare with the two competing semantics
  6. delete only probe-owned scratch graphs (nothing is saved; no user package touched)

Known-hang topology external-Sequence -> While Body is intentionally NOT probed automatically (SAFETY_INVARIANT_002).

Key API facts learned the hard way:
  * a NEW Pixel Processor has no inner graph; create it with
    pp.newPropertyGraph(pp.getPropertyFromId('perpixel', Input), 'SDSBSFunctionGraph')
  * PP result = SDSBSFunctionGraph.setOutputNode(node, True); there is no
    output node *type*
  * library Functions are instantiated with SDSBSFunctionGraph.newInstanceNode(resource)
"""
import json
import math
import os
import shutil
import struct
import tempfile
import traceback
from pathlib import Path

import sd
from sd.api.sdproperty import SDPropertyCategory as C
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluestring import SDValueString
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
import sd.tools.export as EXPORT

ENC = 1.0 / 32.0
COORD_ENC = 1.0 / 16.0
PROBE_PREFIX = "sd_pp_probe_"
OWNER_MARKER = ".sd_pixelprocessor_agent_owned.json"

app = sd.getContext().getSDApplication()
pkg_mgr = app.getPackageMgr()
PKG = None
GRAPHS = []
RESULTS = []
OUT_DIR = None
LIB_PKG = None
LIB_PKG_LOADED_BY_PROBE = False
PREEXISTING_USER_PACKAGES = None


# ------------------------------------------------------------------ helpers
def mk(cls, v):
    f = getattr(cls, 'sNew', None)
    return f(v) if f is not None else cls(v)


def prop(node, pid, required=True):
    for cat in (C.Input, C.Annotation, C.Output):
        try:
            p = node.getPropertyFromId(pid, cat)
        except Exception:
            p = None
        if p is not None:
            return p
    if required:
        raise RuntimeError('property %r not found on %s' % (pid, node.getDefinition().getId()))
    return None


def first_output_id(node):
    outs = node.getProperties(C.Output)
    return outs[0].getId() if len(outs) else 'unique_filter_output'


def checked_new(graph, definition_id):
    # Unknown IDs can leave execute_sd_code with an empty/unknown result.
    # Definition availability belongs to this graph kind, not the session.
    ids = {d.getId() for d in graph.getNodeDefinitions()}
    if definition_id not in ids:
        raise RuntimeError('definition %r is unavailable in graph %r' %
                           (definition_id, graph.getIdentifier()))
    return graph.newNode(definition_id)


def const(ig, value):
    n = checked_new(ig, 'sbs::function::const_float1')
    n.setPropertyValue(prop(n, '__constant__'), mk(SDValueFloat, float(value)))
    return n


def named(ig, defid, name):
    n = checked_new(ig, 'sbs::function::' + defid)
    n.setPropertyValue(prop(n, '__constant__'), mk(SDValueString, name))
    return n


def atomic(ig, defid, **inputs):
    n = checked_new(ig, 'sbs::function::' + defid)
    for pid, src in inputs.items():
        node, out_id = src if isinstance(src, tuple) else (src, 'unique_filter_output')
        node.newPropertyConnectionFromId(out_id, n, pid)
    return n


def vec2(ig, x, y):
    return atomic(ig, 'vector2', componentsin=const(ig, x), componentslast=const(ig, y))


def scale(ig, vec, k):
    return atomic(ig, 'mulscalar', a=vec, scalar=const(ig, k))


def mul_k(ig, v, k):          # float1 * float1 must use mul (float1 has no Vector)
    return atomic(ig, 'mul', a=const(ig, k), b=v)


def encode01(ig, v):          # v*0.5 + 0.5  -> [-1,1] into [0,1]
    return atomic(ig, 'add', a=mul_k(ig, v, 0.5), b=const(ig, 0.5))


def encode32(ig, v):          # v/32
    return atomic(ig, 'mul', a=const(ig, ENC), b=v)


def _norm_path(path):
    return os.path.normcase(os.path.realpath(os.path.normpath(str(path)))) if path else ''


def _builtin_functions_path():
    override = os.environ.get('SD_PIXEL_AGENT_FUNCTIONS_PACKAGE')
    if override:
        if not os.path.isfile(override):
            raise RuntimeError('SD_PIXEL_AGENT_FUNCTIONS_PACKAGE does not exist: %s' % override)
        return _norm_path(override)
    cands = []
    try:
        import sd.tools.io as IO
        api_root = IO.getAPIRootDir()
        sd_root = os.path.dirname(os.path.dirname(os.path.dirname(api_root)))
        cands.append(os.path.join(sd_root, 'resources', 'packages', 'functions.sbs'))
    except Exception:
        pass
    for c in cands:
        if os.path.isfile(c):
            return _norm_path(c)
    raise RuntimeError(
        'Adobe resources/packages/functions.sbs could not be resolved. '
        'Set SD_PIXEL_AGENT_FUNCTIONS_PACKAGE to its exact absolute path.'
    )


def get_builtin_functions_package():
    global LIB_PKG, LIB_PKG_LOADED_BY_PROBE
    if LIB_PKG is not None:
        return LIB_PKG
    target = _builtin_functions_path()
    pk = None
    try:
        pk = pkg_mgr.getUserPackageFromFilePath(target)
    except Exception:
        pk = None
    if pk is None:
        for cand in pkg_mgr.getPackages():
            try:
                if _norm_path(cand.getFilePath()) == target:
                    pk = cand
                    break
            except Exception:
                continue
    if pk is None:
        pk = pkg_mgr.loadUserPackage(target, True, True)
        LIB_PKG_LOADED_BY_PROBE = True
    if pk is None or _norm_path(pk.getFilePath()) != target:
        raise RuntimeError('failed to load exact Adobe functions.sbs package: %s' % target)
    LIB_PKG = pk
    return pk


def find_function_resource(name):
    # Search only Adobe's exact shipped functions.sbs package.  User packages
    # with the same identifier are intentionally ignored.
    pk = get_builtin_functions_package()
    hits = []
    for r in pk.getChildrenResources(True):
        try:
            ident = r.getIdentifier()
        except Exception:
            continue
        if not ident:
            continue
        low = ident.lower()
        target = name.lower()
        if low == target or low.endswith('/' + target) or low.endswith('::' + target):
            hits.append((pk, r, ident))
    if len(hits) != 1:
        raise RuntimeError(
            'built-in Function %r resolved to %d resources in %s: %s' %
            (name, len(hits), pk.getFilePath(), [h[2] for h in hits])
        )
    return hits


def call_library(ig, fname):
    pk, res, ident = find_function_resource(fname)[0]
    n = ig.newInstanceNode(res)
    if n is None:
        raise RuntimeError('newInstanceNode returned None for %s (%s)' % (fname, ident))
    return n, first_output_id(n), ident


def _create_probe_run_dir():
    base = os.environ.get('SD_PIXEL_AGENT_PROBE_DIR') or None
    if base:
        os.makedirs(base, exist_ok=True)
    path = tempfile.mkdtemp(prefix=PROBE_PREFIX, dir=base)
    Path(path, OWNER_MARKER).write_text(
        json.dumps({'owner': 'sd-pixelprocessor-agent', 'schema': 1}),
        encoding='utf-8'
    )
    return path


def _designer_version():
    for name in ('getVersion', 'getApplicationVersion', 'getVersionString'):
        fn = getattr(app, name, None)
        if callable(fn):
            try:
                v = fn()
            except Exception:
                continue
            if v:
                import re
                m = re.search(r'\d+(?:\.\d+){1,3}', str(v))
                if m:
                    return m.group(0)
    import re
    m = re.search(r'\d+(?:\.\d+){1,3}', os.environ.get('SD_PIXEL_AGENT_DESIGNER_VERSION', ''))
    return m.group(0) if m else 'unknown'


def _graph_ids(package):
    out = []
    try:
        resources = package.getChildrenResources(False)
    except Exception:
        return tuple()
    for r in resources:
        if hasattr(r, 'getNodes'):
            try:
                out.append(str(r.getIdentifier()))
            except Exception:
                out.append('<?>')
    return tuple(sorted(out))


def _snapshot_preexisting_user_packages():
    return tuple(sorted([
        (id(p), str(p.getFilePath() or ''), _graph_ids(p))
        for p in pkg_mgr.getUserPackages()
    ]))


def _assert_preexisting_unchanged(before):
    current = {id(p): p for p in pkg_mgr.getUserPackages()}
    errs = []
    for oid, path, graphs in before:
        p = current.get(oid)
        if p is None:
            errs.append('pre-existing package disappeared: %s' % (path or '<unsaved>'))
            continue
        now = _graph_ids(p)
        if now != graphs:
            errs.append('pre-existing package changed: %s before=%s after=%s' %
                        (path or '<unsaved>', graphs, now))
    if errs:
        raise RuntimeError('SAFETY_INVARIANT_001 failed: ' + '; '.join(errs))


def new_graph(name):
    global PKG
    if PKG is None:
        PKG = pkg_mgr.newUserPackage()
    g = SDSBSCompGraph.sNew(PKG)
    g.setIdentifier(name)
    pp = checked_new(g, 'sbs::compositing::pixelprocessor')
    pprop = pp.getPropertyFromId('perpixel', C.Input)
    ig = pp.getPropertyGraph(pprop)
    if ig is None:
        ig = pp.newPropertyGraph(pprop, 'SDSBSFunctionGraph')
    if ig is None:
        raise RuntimeError('could not create Pixel Processor inner graph')
    out = checked_new(g, 'sbs::compositing::output')
    pp.newPropertyConnectionFromId('unique_filter_output', out, 'inputNodeOutput')
    g.setOutputNode(out, True)
    GRAPHS.append(g)
    return g, pp, ig


def finish(ig, result):
    ig.setOutputNode(result, True)


def srgb(v):
    if v <= 0.0031308:
        return 12.92 * v
    return 1.055 * (v ** (1.0 / 2.4)) - 0.055


def read_bmp_pixel(path, sample_x='left'):
    data = open(path, 'rb').read()
    off = struct.unpack_from('<I', data, 10)[0]
    w, h = struct.unpack_from('<ii', data, 18)
    bpp = struct.unpack_from('<H', data, 28)[0]
    hh = abs(h)
    row = 0 if h < 0 else hh - 1
    rs = ((bpp * w + 31) // 32) * 4
    col = w - 1 if sample_x == 'right' else 0
    base = off + row * rs
    if bpp == 8:
        idx = data[base + col]
        pal = off - 1024
        b, g, r = data[pal + idx * 4], data[pal + idx * 4 + 1], data[pal + idx * 4 + 2]
    elif bpp in (24, 32):
        base += col * (bpp // 8)
        b, g, r = data[base], data[base + 1], data[base + 2]
    else:
        raise RuntimeError('bpp=%d unsupported' % bpp)
    return {'size': (w, hh), 'bpp': bpp, 'rgb': (r, g, b), 'value': b / 255.0}


def resolve_expected(exp, pixel):
    """Resolve expectations that depend on the exported graph dimensions."""
    if not isinstance(exp, str):
        return exp
    width = float(pixel['size'][0])
    dynamic = {
        'coord_pos_normalized': math.log(1.0 + (width - 0.5) / width, 2.0) * COORD_ENC,
        'coord_pos_pixels': math.log(1.0 + width - 0.5, 2.0) * COORD_ENC,
        'coord_size_pixels': math.log(width, 2.0) * COORD_ENC,
        'coord_size_unit': 0.0,
    }
    if exp not in dynamic:
        raise RuntimeError('unknown dynamic expectation: %s' % exp)
    return dynamic[exp]


# ------------------------------------------------------------------- probes
def p_mod_neg_a(ig):
    m = atomic(ig, 'mod', a=const(ig, -0.25), b=const(ig, 1.0))
    finish(ig, encode01(ig, m))
    return [('mod(-0.25,1) floor-based (GLSL mod)', 0.875),
            ('mod(-0.25,1) trunc-based (C fmod)', 0.375)]


def p_mod_neg_b(ig):
    m = atomic(ig, 'mod', a=const(ig, 1.25), b=const(ig, -1.0))
    finish(ig, encode01(ig, m))
    return [('mod(1.25,-1) floor-based, sign follows divisor', 0.125),
            ('mod(1.25,-1) trunc-based', 0.625)]


def p_mul_vec2(ig):
    m = atomic(ig, 'mul', a=vec2(ig, 1.0, 2.0), b=vec2(ig, 3.0, 4.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, encode32(ig, d))
    return [('mul(float2,float2) component-wise -> dot((3,8),(1,1))=11', 11 * ENC),
            ('mul refused/mixed -> 0 or other', 0.0)]


def p_mul_float1(ig):
    m = atomic(ig, 'mul', a=const(ig, 3.0), b=const(ig, 4.0))
    finish(ig, encode32(ig, m))
    return [('mul(float1,float1) = 12', 12 * ENC),
            ('silent zero', 0.0)]


def p_mulscalar_vec2(ig):
    m = atomic(ig, 'mulscalar', a=vec2(ig, 1.0, 2.0), scalar=const(ig, 4.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, encode32(ig, d))
    return [('mulscalar(Vector=(1,2), Scale=4) -> dot=12', 12 * ENC),
            ('swapped/zero', 0.0)]


def p_round_half_neg(ig):
    n, oid, _ = call_library(ig, 'round_float1')
    const(ig, -2.5).newPropertyConnectionFromId('unique_filter_output', n, 'input')
    finish(ig, atomic(ig, 'add', a=mul_k(ig, (n, oid), 0.125), b=const(ig, 0.5)))
    return [('round_float1(-2.5)=floor(x+0.5)=-2', 0.25),
            ('round_float1(-2.5) half-away-from-zero=-3', 0.125)]


def p_frac_neg(ig):
    n, oid, _ = call_library(ig, 'frac')
    const(ig, -0.25).newPropertyConnectionFromId('unique_filter_output', n, 'input')
    finish(ig, encode01(ig, (n, oid)))
    return [('frac(-0.25)=x-floor(x)=0.75', 0.875),
            ('frac(-0.25) truncation-based=-0.25', 0.375)]


def p_fmod_neg(ig):
    n, oid, _ = call_library(ig, 'fmod')
    const(ig, -0.25).newPropertyConnectionFromId('unique_filter_output', n, 'a')
    const(ig, 1.0).newPropertyConnectionFromId('unique_filter_output', n, 'b')
    finish(ig, encode01(ig, (n, oid)))
    return [('fmod(-0.25,1) same sign as a = -0.25', 0.375),
            ('fmod(-0.25,1) floor-based = 0.75', 0.875)]


def p_sign_zero(ig):
    n, oid, _ = call_library(ig, 'sign')
    const(ig, 0.0).newPropertyConnectionFromId('unique_filter_output', n, 'x')
    finish(ig, mul_k(ig, (n, oid), 0.5))
    return [('sign(0) documented = 1 -> 0.5', 0.5),
            ('sign(0) mathematical = 0 -> 0.0', 0.0)]


def p_sign_neg(ig):
    n, oid, _ = call_library(ig, 'sign')
    const(ig, -3.0).newPropertyConnectionFromId('unique_filter_output', n, 'x')
    finish(ig, atomic(ig, 'add', a=mul_k(ig, (n, oid), 0.25), b=const(ig, 0.75)))
    return [('sign(-3) = -1 -> 0.5', 0.5),
            ('sign(-3) = 1 -> 1.0', 1.0),
            ('sign(-3) = 0 -> 0.75', 0.75)]


def p_mod_pos(ig):
    """Control: mod(5.5,2)=1.5 under both conventions."""
    m = atomic(ig, 'mod', a=const(ig, 5.5), b=const(ig, 2.0))
    finish(ig, mul_k(ig, m, 0.25))
    return [('mod(5.5,2)=1.5 (control) -> 0.375', 0.375),
            ('mod broken/zero -> 0.0', 0.0)]


def p_step_edge(ig):
    n, oid, _ = call_library(ig, 'step')
    const(ig, 0.5).newPropertyConnectionFromId('unique_filter_output', n, 'a')
    const(ig, 0.5).newPropertyConnectionFromId('unique_filter_output', n, 'x')
    finish(ig, mul_k(ig, (n, oid), 0.5))
    return [('step(0.5,0.5)=1 ("x >= a") -> 0.5', 0.5),
            ('step(0.5,0.5)=0 (strict "x > a") -> 0.0', 0.0)]


def p_mul_mixed_num(ig):
    """float2 * float1 through mul: promoted vector result or broken?"""
    m = atomic(ig, 'mul', a=vec2(ig, 1.0, 2.0), b=const(ig, 3.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, encode32(ig, d))
    return [('mul(float2,(float)3) promoted -> dot((3,6),(1,1))=9', 9 * ENC),
            ('mul refused -> 0', 0.0)]


def p_mulscalar_swapped_num(ig):
    """float1 into Vector and float2 into Scale: SD accepts the wires; result?"""
    m = atomic(ig, 'mulscalar', a=const(ig, 4.0), scalar=vec2(ig, 1.0, 2.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, encode32(ig, d))
    return [('swapped mulscalar -> 0 (silent zero)', 0.0),
            ('swapped mulscalar -> 12 (order ignored)', 12 * ENC)]


def _set_var(ig, value_node, name):
    s = named(ig, 'set', name)
    value_node.newPropertyConnectionFromId('unique_filter_output', s, 'value')
    return s


def _get_var(ig, name):
    return named(ig, 'get_float1', name)


def p_while_sum(ig):
    """Minimal While per spec 7.9.10; stop when 5 < i -> sum 1..6 = 21."""
    init = atomic(ig, 'sequence',
                  seqin=_set_var(ig, const(ig, 0.0), 'acc'),
                  seqlast=_set_var(ig, const(ig, 0.0), 'i'))
    cond = atomic(ig, 'lr', a=const(ig, 5.0), b=_get_var(ig, 'i'))
    acc_new = atomic(ig, 'add', a=atomic(ig, 'add', a=_get_var(ig, 'acc'), b=_get_var(ig, 'i')),
                     b=const(ig, 1.0))
    body = atomic(ig, 'sequence',
                  seqin=_set_var(ig, acc_new, 'acc'),
                  seqlast=_set_var(ig, atomic(ig, 'add', a=_get_var(ig, 'i'), b=const(ig, 1.0)), 'i'))
    w = atomic(ig, 'while', init=init, cond=cond, loop=body)
    after = atomic(ig, 'sequence', seqin=w, seqlast=_get_var(ig, 'acc'))
    finish(ig, encode32(ig, after))
    return [('while stops when 5<i -> sum 1..6 = 21', 21 * ENC),
            ('zero iterations -> 0', 0.0)]


def p_while_zero(ig):
    """Zero-iteration case: exit cond true at once -> Init value must survive."""
    init = _set_var(ig, const(ig, 7.0), 'acc')
    cond = atomic(ig, 'lr', a=const(ig, 0.0), b=const(ig, 1.0))   # 0<1 = true -> stop
    w = atomic(ig, 'while', init=init, cond=cond, loop=const(ig, 0.0))
    after = atomic(ig, 'sequence', seqin=w, seqlast=_get_var(ig, 'acc'))
    finish(ig, encode32(ig, after))
    return [('exit cond true immediately -> acc keeps 7', 7 * ENC),
            ('undefined/zero', 0.0)]


def p_mod_vec_neg(ig):
    """mod((-0.25,1.25), (1,1)): floor -> (0.75,0.25) dot=1.0 ; trunc -> (-0.25,0.25) dot=0."""
    m = atomic(ig, 'mod', a=vec2(ig, -0.25, 1.25), b=vec2(ig, 1.0, 1.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, mul_k(ig, d, 0.25))
    return [('mod(vec2,vec2) floor-based per component -> dot=1.0', 0.25),
            ('mod(vec2,vec2) trunc-based -> dot=0.0', 0.0)]


def p_mod_mixed_dim_num(ig):
    """mod(float2 A, float1 Divisor): same-type violation -> silent 0?"""
    m = atomic(ig, 'mod', a=vec2(ig, 5.5, 7.5), b=const(ig, 2.0))
    d = atomic(ig, 'dot', a=m, b=vec2(ig, 1.0, 1.0))
    finish(ig, mul_k(ig, d, 0.01))
    return [('mod(float2,float1) silently 0', 0.0),
            ('mod broadcast -> (1.5,1.5) dot=3.0', 0.03)]


def p_while_maxiter(ig):
    """Same minimal loop but with the While node's Constant (max iterations) set."""
    init = atomic(ig, 'sequence',
                  seqin=_set_var(ig, const(ig, 0.0), 'acc'),
                  seqlast=_set_var(ig, const(ig, 0.0), 'i'))
    cond = atomic(ig, 'lr', a=const(ig, 5.0), b=_get_var(ig, 'i'))
    acc_new = atomic(ig, 'add', a=atomic(ig, 'add', a=_get_var(ig, 'acc'), b=_get_var(ig, 'i')),
                     b=const(ig, 1.0))
    body = atomic(ig, 'sequence',
                  seqin=_set_var(ig, acc_new, 'acc'),
                  seqlast=_set_var(ig, atomic(ig, 'add', a=_get_var(ig, 'i'), b=const(ig, 1.0)), 'i'))
    w = atomic(ig, 'while', init=init, cond=cond, loop=body)
    cp = prop(w, '__constant__', required=False)
    info = []
    if cp is not None:
        try:
            info.append('type=%s' % cp.getType().getId())
        except Exception:
            pass
        try:
            from sd.api.sdvalueint import SDValueInt
            w.setPropertyValue(cp, mk(SDValueInt, 50))
            info.append('set 50 ok')
        except Exception as e:
            info.append('set ERR %s: %s' % (type(e).__name__, e))
    after = atomic(ig, 'sequence', seqin=w, seqlast=_get_var(ig, 'acc'))
    finish(ig, encode32(ig, after))
    return [('maxIterations=50 accepted, loop still sums 1..6 = 21', 21 * ENC),
            ('loop truncated/other', 0.0)]


def p_round_pos(ig):
    n, oid, _ = call_library(ig, 'round_float1')
    const(ig, 2.5).newPropertyConnectionFromId('unique_filter_output', n, 'input')
    finish(ig, mul_k(ig, (n, oid), 0.25))
    return [('round_float1(2.5)=3 (half up)', 0.75),
            ('round_float1(2.5)=2 (half down)', 0.5)]


def p_clamp_lo(ig):
    n, oid, _ = call_library(ig, 'clamp')
    const(ig, -3.0).newPropertyConnectionFromId('unique_filter_output', n, 'input')
    const(ig, 0.0).newPropertyConnectionFromId('unique_filter_output', n, 'min')
    const(ig, 1.0).newPropertyConnectionFromId('unique_filter_output', n, 'max')
    finish(ig, atomic(ig, 'add', a=mul_k(ig, (n, oid), 0.5), b=const(ig, 0.25)))
    return [('clamp(-3,0,1)=0 -> 0.25', 0.25),
            ('clamp passthrough -3 -> clamped to 0 anyway', None)]


def p_saturate_hi(ig):
    n, oid, _ = call_library(ig, 'saturate')
    const(ig, 2.0).newPropertyConnectionFromId('unique_filter_output', n, 'input')
    finish(ig, mul_k(ig, (n, oid), 0.5))
    return [('saturate(2)=1 -> 0.5', 0.5),
            ('saturate(2)=2 (no clamp) -> 1.0', 1.0)]


def p_coord_pos_x(ig):
    """Sample the right edge to distinguish normalized UV from pixel coordinates."""
    pos = named(ig, 'get_float2', '$pos')
    x = atomic(ig, 'dot', a=pos, b=vec2(ig, 1.0, 0.0))
    encoded = mul_k(ig, atomic(ig, 'log2', a=atomic(ig, 'add', a=x, b=const(ig, 1.0))), COORD_ENC)
    finish(ig, encoded)
    return [('normalized $pos.x', 'coord_pos_normalized'),
            ('pixel-space $pos.x', 'coord_pos_pixels')]


def p_coord_size_x(ig):
    """Distinguish documented pixel dimensions from the historical unit-size observation."""
    size = named(ig, 'get_float2', '$size')
    x = atomic(ig, 'dot', a=size, b=vec2(ig, 1.0, 0.0))
    finish(ig, mul_k(ig, atomic(ig, 'log2', a=x), COORD_ENC))
    return [('pixel-dimension $size.x', 'coord_size_pixels'),
            ('unit $size.x', 'coord_size_unit')]


PROBES = [
    ('mod_pos', p_mod_pos),
    ('mod_neg_a', p_mod_neg_a),
    ('mod_neg_b', p_mod_neg_b),
    ('mod_vec_neg', p_mod_vec_neg),
    ('mod_mixed_dim_num', p_mod_mixed_dim_num),
    ('mul_vec2', p_mul_vec2),
    ('mul_float1', p_mul_float1),
    ('mul_mixed_num', p_mul_mixed_num),
    ('mulscalar_vec2', p_mulscalar_vec2),
    ('mulscalar_swapped_num', p_mulscalar_swapped_num),
    ('round_half_neg', p_round_half_neg),
    ('round_pos', p_round_pos),
    ('frac_neg', p_frac_neg),
    ('fmod_neg', p_fmod_neg),
    ('sign_zero', p_sign_zero),
    ('sign_neg', p_sign_neg),
    ('step_edge', p_step_edge),
    ('clamp_lo', p_clamp_lo),
    ('saturate_hi', p_saturate_hi),
    ('while_sum', p_while_sum),
    ('while_maxiter', p_while_maxiter),
    ('while_zero', p_while_zero),
    ('coord_pos_x', p_coord_pos_x),
    ('coord_size_x', p_coord_size_x),
]

DEFIDS = ['const_float1', 'add', 'sub', 'mul', 'mulscalar', 'mod', 'dot',
          'vector2', 'sequence', 'set', 'get_float1', 'get_float2', 'while', 'lr', 'ifelse', 'pow', 'log2']


def preflight():
    global PKG
    print('== preflight ==')
    print('SDValueString.sNew:', hasattr(SDValueString, 'sNew'), '| SDValueFloat.sNew:', hasattr(SDValueFloat, 'sNew'))
    if PKG is None:
        PKG = pkg_mgr.newUserPackage()
    g = SDSBSCompGraph.sNew(PKG)
    g.setIdentifier('zz_preflight')
    GRAPHS.append(g)
    pp = checked_new(g, 'sbs::compositing::pixelprocessor')
    ig = pp.newPropertyGraph(pp.getPropertyFromId('perpixel', C.Input), 'SDSBSFunctionGraph')
    bad = []
    for d in DEFIDS:
        try:
            checked_new(ig, 'sbs::function::' + d)
        except Exception as e:
            bad.append('%s (%s)' % (d, e))
    print('atomic defs missing/failed: %s' % (bad if bad else 'none'))
    w = checked_new(ig, 'sbs::function::while')
    print('while node properties:')
    for p in w.getProperties(C.Input):
        try:
            dv = p.getDefaultValue()
        except Exception:
            dv = '?'
        print('   in  id=%-16s label=%-18r default=%s' % (p.getId(), p.getLabel(), dv))
    for p in w.getProperties(C.Annotation):
        try:
            dv = p.getDefaultValue()
        except Exception:
            dv = '?'
        print('   ann id=%-16s label=%-18r default=%s' % (p.getId(), p.getLabel(), dv))
    for fname in ('round_float1', 'frac', 'fmod', 'sign', 'clamp', 'saturate', 'step',
                  'smoothstep', 'truncate_float1_decimals'):
        try:
            pk, res, ident = find_function_resource(fname)[0]
            n = ig.newInstanceNode(res)
            outs = [p.getId() for p in n.getProperties(C.Output)] if n is not None else None
            ins = [p.getId() for p in n.getProperties(C.Input)] if n is not None else None
            print('  library %-26s ident=%-34s in=%s out=%s' % (fname, ident, ins, outs))
        except Exception as e:
            print('  library %-26s RESOLVE-FAIL %s: %s' % (fname, type(e).__name__, e))
            raise
    try:
        g.delete()
        GRAPHS.remove(g)
    except Exception as e:
        print('preflight cleanup ERR', e)


def run():
    global PKG, OUT_DIR, RESULTS, GRAPHS, PREEXISTING_USER_PACKAGES, LIB_PKG
    RESULTS = []
    GRAPHS = []
    PKG = None
    OUT_DIR = _create_probe_run_dir()
    PREEXISTING_USER_PACKAGES = _snapshot_preexisting_user_packages()
    print('probe output dir:', OUT_DIR)
    print('designer version:', _designer_version())

    # Always create a fresh package owned by this run.  Never enumerate/reuse/clear
    # unrelated unsaved packages: unsaved user work is a protected resource.
    PKG = pkg_mgr.newUserPackage()
    if PKG is None:
        raise RuntimeError('newUserPackage() returned None')

    try:
        preflight()

        print('== build ==')
        for name, fn in PROBES:
            try:
                g, pp, ig = new_graph('probe_' + name)
                expects = fn(ig)
                on = ig.getOutputNodes()
                RESULTS.append({'name': name, 'status': 'built', 'expects': expects,
                                'inner_nodes': len(ig.getNodes()),
                                'output_nodes': len(on)})
                print('  %-16s innerNodes=%-3d outputNodes=%d' % (name, len(ig.getNodes()), len(on)))
            except Exception as e:
                RESULTS.append({'name': name, 'status': 'BUILD-FAIL',
                                'note': '%s: %s' % (type(e).__name__, e),
                                'trace': traceback.format_exc()[-300:]})
                print('  BUILD-FAIL %-12s %s: %s' % (name, type(e).__name__, e))

        print('== wiring rejection ==')
        try:
            g, pp, ig = new_graph('probe_wiring')
            ms = checked_new(ig, 'sbs::function::mulscalar')
            v2 = vec2(ig, 1.0, 2.0)
            f4 = const(ig, 4.0)
            for label, src, dst, pid in (('mulscalar.a <- float1 (scalar into Vector)', f4, ms, 'a'),
                                         ('mulscalar.scalar <- float2 (vector into Scale)', v2, ms, 'scalar')):
                try:
                    c = src.newPropertyConnectionFromId('unique_filter_output', dst, pid)
                    print('  %-50s -> %s' % (label, 'ACCEPTED' if c is not None else 'None'))
                except Exception as e:
                    print('  %-50s -> REJECTED (%s)' % (label, type(e).__name__))
            mul = checked_new(ig, 'sbs::function::mul')
            for label, src, pid in (('mul.a <- float2 (same-dim OK)', v2, 'a'),
                                    ('mul.b <- float1 (mixed dimension)', f4, 'b')):
                try:
                    c = src.newPropertyConnectionFromId('unique_filter_output', mul, pid)
                    print('  %-50s -> %s' % (label, 'ACCEPTED' if c is not None else 'None'))
                except Exception as e:
                    print('  %-50s -> REJECTED (%s)' % (label, type(e).__name__))
            print('  mul input port types:', [(p.getId(), p.getLabel()) for p in mul.getProperties(C.Input)])
            ms2 = checked_new(ig, 'sbs::function::mulscalar')
            print('  mulscalar input port types:', [(p.getId(), p.getLabel()) for p in ms2.getProperties(C.Input)])
        except Exception as e:
            print('  wiring probe failed:', type(e).__name__, e)

        print('== cook + export + read ==')
        for r in RESULTS:
            if r['status'] != 'built':
                continue
            name = r['name']
            g = [x for x in GRAPHS if x.getIdentifier() == 'probe_' + name]
            if not g:
                continue
            g = g[0]
            try:
                g.compute()
                EXPORT.exportSDGraphOutputs(g, OUT_DIR, 'bmp')
                stem = g.getIdentifier() + '_output_'
                files = sorted(f for f in os.listdir(OUT_DIR)
                               if f.startswith(stem) and f.lower().endswith('.bmp'))
                if len(files) != 1:
                    r['status'] = 'NO-IMAGE' if not files else 'AMBIGUOUS-IMAGE'
                    r['matching_files'] = files
                    continue
                px = read_bmp_pixel(
                    os.path.join(OUT_DIR, files[0]),
                    sample_x='right' if name == 'coord_pos_x' else 'left',
                )
                val = px['value']
                cands = []
                for label, exp in r['expects']:
                    if exp is None:
                        continue
                    exp = resolve_expected(exp, px)
                    cands.append((abs(exp - val), label, 'linear'))
                    cands.append((abs(srgb(exp) - val), label + ' [sRGB]', 'srgb'))
                cands.sort(key=lambda x: x[0])
                r.update(status='measured', file=files[0], bpp=px['bpp'], pixel=px['rgb'],
                         value=val, best=cands[0][1], dist=cands[0][0], space=cands[0][2],
                         runner=cands[1][1], runner_dist=cands[1][0])
            except Exception as e:
                r['status'] = 'COOK-FAIL'
                r['note'] = '%s: %s' % (type(e).__name__, e)

        print()
        print('== results ==')
        for r in RESULTS:
            print('%-16s %-10s' % (r['name'], r['status']), end='')
            if r['status'] == 'measured':
                print(' bpp=%d rgb=%s value=%.4f' % (r['bpp'], r['pixel'], r['value']))
                print('        MATCH  : %s (dist %.4f, %s)' % (r['best'], r['dist'], r['space']))
                print('        runner : %s (dist %.4f)' % (r['runner'], r['runner_dist']))
            else:
                print(' ' + str(r.get('note', ''))[:260])

        report = {
            'schema': 3,
            'skill_version': '2.5.0',
            'runtime_semantics_reference': 'RUNTIME_SEMANTICS_BASELINE_v2.5.0.md',
            'known_hang_probes_skipped': ['external_sequence_into_while_body'],
            'designer_version': _designer_version(),
            'functions_package': str(get_builtin_functions_package().getFilePath()),
            'probe_output_dir': OUT_DIR,
            'results': RESULTS,
        }
        report_path = os.path.join(OUT_DIR, 'probe_report.json')
        with open(report_path, 'w', encoding='utf-8') as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print('probe report:', report_path)
        return RESULTS
    finally:
        # Delete only graph objects registered by this probe.  Never scan a package
        # and never delete resources whose ownership is unknown.
        removed = 0
        for g in list(reversed(GRAPHS)):
            try:
                g.delete()
                removed += 1
            except Exception as e:
                print('cleanup ERR', e)
        GRAPHS[:] = []
        try:
            _assert_preexisting_unchanged(PREEXISTING_USER_PACKAGES)
            print('SAFETY_INVARIANT_001: PASS (pre-existing user packages unchanged)')
        except Exception as e:
            print(str(e))
            raise
        if LIB_PKG_LOADED_BY_PROBE and LIB_PKG is not None:
            try:
                pkg_mgr.unloadUserPackage(LIB_PKG)
                LIB_PKG = None
            except Exception as e:
                print('library unload WARN', e)
        print('cleanup: deleted %d probe-owned graphs only' % removed)


run()
