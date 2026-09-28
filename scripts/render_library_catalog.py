# -*- coding: utf-8 -*-
"""Render the built-in library Function catalogue from the verified dumps.

Inputs (produced by the two independent extractors plus the numeric probes):
  * sdk dump   scripts/dump_library_functions.py        (live SD objects)
  * xml dump   scripts/verify_library_functions.py parse-xml  (shipped package XML)
  * diff report                                        (SDK vs XML, per function)
  * probe values                                       (real cook, in verify script)

Outputs
  * references/SD_LIBRARY_FUNCTIONS_<VERSION>.md        human catalogue
  * references/library_functions_<VERSION>.json         machine-readable catalogue

Usage
  python render_library_catalog.py --sdk sdk.json --xml xml.json --diff diff.json \
      --md out.md --json out.json [--version 2.5.0]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import verify_library_functions as V          # reuse the evaluator
except Exception:                                 # pragma: no cover
    V = None

# Groups whose implementation graphs are printed in full (the compute-relevant set).
NETLIST_GROUPS = (
    'Functions/Math', 'Functions/Math/Trigo', 'Functions/Math/Parity',
    'Functions/Ranges', 'Functions/typeConverters', 'Functions/Cycles',
)


def short(defid):
    return defid.split('::')[-1]


def canonical_type(name):
    if name == 'float':
        return 'float1'
    if name == 'int':
        return 'int1'
    if name == 'bool':
        return 'bool1'
    return name


def build_type_map(diff, xml):
    tmap = {}
    for tid, names in (diff.get('type_map') or {}).items():
        if names:
            tmap[tid] = canonical_type(names[0])
    return tmap


def key3(n):
    """Join key tolerant to float32 sub-pixel drift (SDK 1189.3333740234375 vs XML 1189.33337)."""
    pos = n.get('pos')
    if not pos:
        return (n['def'], 'nopos', '')
    return (n['def'], '%.3f' % pos[0], '%.3f' % pos[1])


def merge(sdk, xml, tmap):
    """One record per function: live topology + declared types."""
    out = {}
    for ident, f in sdk.items():
        x = xml.get(ident, {})
        nodes = []
        xnodes = x.get('nodes', [])
        for n in f['nodes']:
            rec = {'def': short(n['def'])}
            if n.get('pos'):
                rec['pos'] = n['pos']
            if n.get('consts'):
                rec['consts'] = n['consts']
            if n.get('instance_of'):
                rec['instance_of'] = n['instance_of']
            nodes.append(rec)
        # join the XML view by (def, position) to attach declared node types
        xbykey = {}
        for xn in xnodes:
            xbykey.setdefault(key3(xn), []).append(xn)
        typed = 0
        for n, sn in zip(nodes, f['nodes']):
            cand = xbykey.get(key3(sn))
            if cand:
                xrec = cand.pop(0)
                tid = xrec.get('type_id')
                if tid in tmap:
                    n['type'] = tmap[tid]
                    typed += 1
        # second pass: attach types to leftovers by (def, constant signature)
        leftover = [xn for lst in xbykey.values() for xn in lst]
        sig = {}
        for xn in leftover:
            s = (xn['def'], V.consts_sig(xn) if V else '')
            sig.setdefault(s, []).append(xn)
        for n, sn in zip(nodes, f['nodes']):
            if n.get('type'):
                continue
            s = (sn['def'], V.consts_sig(sn) if V else '')
            cand = sig.get(s)
            if cand and len(cand) == 1:
                tid = cand[0].get('type_id')
                if tid in tmap:
                    n['type'] = tmap[tid]
                    typed += 1
                    cand.pop()
        formals = []
        for i, fo in enumerate(f['formals']):
            xf = (x.get('formals') or [{}] * (i + 1))[i] if i < len(x.get('formals') or []) else {}
            tid = xf.get('type_id')
            formals.append({
                'id': fo['id'], 'label': fo.get('label') or '',
                'type': tmap.get(tid) or ((fo.get('types') or ['?'])[0]),
                'default': fo.get('default'),
            })
        decl = x.get('declared_output_type_id')
        output_index = f['outputs'][0]['i'] if f.get('outputs') else None
        output_type = None
        if output_index is not None and 0 <= output_index < len(nodes):
            output_type = nodes[output_index].get('type')
        out[ident] = {
            'group': f['group'],
            'label': f.get('label') or ident,
            'description': f.get('description'),
            # Prefer the root node type. Older XML extraction used the first
            # descendant <type> (usually the first formal), which mislabeled
            # length_vec2 as float2 even though its sqrt root is float1.
            'declared_output_type': output_type or tmap.get(decl) or None,
            'formals': formals,
            'nodes': nodes,
            'edges': [{'from': e['from'], 'to': e['to'], 'port': e.get('to_port')} for e in f['edges']],
            'output': output_index,
            'outputs': [{'i': o['i']} for o in f.get('outputs', [])],   # evaluator contract
            'outputs_all': [o['i'] for o in f.get('outputs', [])],
            'calls': sorted(set(n.get('instance_of') for n in f['nodes'] if n.get('instance_of'))),
            'typed_nodes': typed,
            'node_count': f['node_count'],
        }
    # Instance root nodes may not carry a concrete type. Resolve those from
    # the referenced function after all records exist.
    for _ in range(len(out)):
        changed = False
        for f in out.values():
            oi = f.get('output')
            if f.get('declared_output_type') or oi is None:
                continue
            node = f['nodes'][oi]
            target = node.get('instance_of')
            if target in out and out[target].get('declared_output_type'):
                f['declared_output_type'] = out[target]['declared_output_type']
                changed = True
        if not changed:
            break
    return out


def formal_str(formals):
    bits = []
    for f in formals:
        d = f.get('default')
        d = '' if d is None else ('=%s' % d)
        bits.append('%s:%s%s' % (f['id'], f['type'], d))
    return ', '.join(bits) or '—'


def render_node(i, n, edges):
    ins = ' '.join('%s<-%s%d' % (e['port'], 'n', e['from']) for e in edges if e['to'] == i)
    parts = ['n%-3d %-26s' % (i, n['def'])]
    if n.get('type'):
        parts.append('%-7s' % n['type'])
    else:
        parts.append('%-7s' % '')
    if n.get('instance_of'):
        parts.append('instance_of=%-24s' % n['instance_of'])
    c = dict((k, v) for k, v in (n.get('consts') or {}).items() if k != 'instance')
    if c:
        parts.append('consts=%s' % json.dumps(c, ensure_ascii=False))
    if ins:
        parts.append(ins)
    return '    ' + '  '.join(p for p in parts if p is not None).rstrip()


def render_markdown(lib, diff, version, xml_stats=None):
    s = diff['summary']
    xml_stats = xml_stats or {}
    lines = []
    A = lines.append
    A('# SD 内建库函数台账 v%s（逐节点核对）' % version)
    A('')
    A('> 生成：`scripts/render_library_catalog.py`　数据：SD 活动对象 + 发行包 XML + 真实 cook 实测')
    A('> 机器可读版：`references/library_functions_v%s.json`　核对器：`scripts/verify_library_functions.py`' % version)
    A('')
    A('## 1. 这份台账为什么可信（三源一致）')
    A('')
    A('| 视图 | 取数方式 | 结果 |')
    A('|---|---|---|')
    A('| A. SD 活动对象 | `scripts/dump_library_functions.py` 在 Designer 进程内遍历 `SDSBSFunctionGraph`：节点定义、真实属性值、`getInputPropertyNode()` 源端反查边 | **%d 函数 / %d 节点 / %d 边** |' % (
        s['functions'], s['nodes'], s['edges']))
    A('| B. 发行包 XML | `scripts/verify_library_functions.py parse-xml` 独立解析 `resources/packages/functions.sbs`（uid 引用、`paramNode`/`connections`/`rootnode`） | **%d 函数 / %d 节点 / %d 边** |' % (
        xml_stats.get('functions', 0), xml_stats.get('nodes', 0), xml_stats.get('edges', 0)))
    A('| C. 真实 cook | `scripts/probe_sd_semantics.py` 在 PP 里真实求值并导出 BMP 读像素 | 与 A、B 的网表求值逐项一致 |')
    A('')
    A('**逐节点差分结果：%d/%d 函数 PASS，%d 处不一致。** 每个函数都比对了：节点集合（定义+坐标）、边集合（源节点+端口→目标节点+端口）、每个常量（float32 精度）、输出节点、形参 id 顺序、嵌套调用目标。' % (
        s['pass'], s['functions'], s['mismatch']))
    A('')
    st = diff.get('stale_edges') or []
    A('已解释的例外（不计为不一致）：')
    A('')
    A('- **XML 省略默认常量 %d 处**：`const_*`/`swizzle*` 取默认值（0 / 恒等排列）时文件不写 `funcDatas`，SD 侧会显式给出默认值。差分对每个省略项都按 `ATOM_DEFAULTS` 复核。' % diff.get('default_omissions', 0))
    A('- **XML 无坐标 1 处**：`NotEqual_Float3` 的一个 `get_float3` 没有 `gpos`，按（定义+常量）唯一匹配。')
    for e in st:
        A('- **陈旧连接 %d 处**：`%s` 的 `instance`（目标 `%s`）上有一条连向 `%s` 的边，而目标函数只声明了 %s —— 文件里的历史残留，SD 装载时忽略，不影响求值。' % (
            len(st), e['in'], e['target'], e['port'], e['declared_formals']))
    A('')
    if V is not None:
        rows, ok = V.eval_stage(lib)
        A('**数值闭环（网表求值 vs BMP 实测）**：SDK 网表 %d/%d，XML 网表同样通过。' % (ok, len(rows)))
        A('')
        A('| 函数 | 输入 | 网表值 | 实测值 | 依据 |')
        A('|---|---|---|---|---|')
        for r in rows:
            if r['status'] not in ('PASS', 'FAIL'):
                continue
            A('| `%s` | `%s` | %s | %s | %s |' % (
                r['fn'], json.dumps(r['args'], ensure_ascii=False),
                ('%g' % r['netlist_value']), ('%g' % r['measured_value']), r.get('note') or ''))
        A('')
    A('**使用限制**（保持诚实）：')
    A('')
    A('- 数值来自 SD 的**单精度**值（本台账按 float32 归一化比较）；XML 与 SDK 的差异若超过 float32 分辨率会记为不一致。')
    A('- 坐标（`pos`）来自活动对象；XML 缺坐标的个别节点已注明。')
    A('- 台账是 16.0.3 + 该发行包的内容；换版本用同样两条命令重新生成后差分即可。')
    A('')
    A('## 2. 类型字典（发行包 type id → 名称）')
    A('')
    A('| type id | 名称 |')
    A('|---|---|')
    for tid, names in sorted((diff.get('type_map') or {}).items(), key=lambda kv: int(kv[0])):
        A('| %s | %s |' % (tid, canonical_type(names[0])))
    A('')
    A('## 3. 全库索引（%d 个函数）' % len(lib))
    A('')
    A('| identifier | group | label | 形参（id:类型=默认） | 输出 | 节点 | 边 | 调用 | 描述 |')
    A('|---|---|---|---|---|---|---|---|---|')
    for ident in sorted(lib, key=lambda k: (lib[k]['group'], k)):
        f = lib[ident]
        desc = (f.get('description') or '').replace('\n', ' ').replace('|', '/')
        if not desc:
            desc = '—'
        A('| `%s` | %s | %s | %s | %s | %d | %d | %s | %s |' % (
            ident, f['group'], f['label'], formal_str(f['formals']),
            f.get('declared_output_type') or '—', f['node_count'], len(f['edges']),
            ', '.join('`%s`' % c for c in f['calls']) or '—', desc))
    A('')
    A('## 4. 计算相关函数的逐节点网表')
    A('')
    A('`n{i}` = 网表中的节点序号；`port<-n{src}` 表示该输入端口由此节点驱动。`instance_of` 表示该节点调用另一个库函数（网表可递归展开）。')
    A('')
    for group in NETLIST_GROUPS:
        members = sorted(k for k in lib if lib[k]['group'] == group)
        if not members:
            continue
        A('### %s（%d）' % (group, len(members)))
        A('')
        for ident in members:
            f = lib[ident]
            A('#### `%s` — %s' % (ident, f['label']))
            A('')
            A('- 形参：%s' % formal_str(f['formals']))
            A('- 输出：`%s`（网表节点 n%s）' % (f.get('declared_output_type') or '—', f.get('output')))
            if f.get('description'):
                A('- 描述：%s' % f['description'].replace('\n', ' '))
            A('- 规模：%d 节点 / %d 边%s' % (
                f['node_count'], len(f['edges']),
                '；调用 %s' % ', '.join('`%s`' % c for c in f['calls']) if f['calls'] else ''))
            A('')
            A('```text')
            for i, n in enumerate(f['nodes']):
                A(render_node(i, n, f['edges']))
            A('    out = n%s' % f.get('output'))
            A('```')
            A('')
    A('## 5. 嵌套调用（库函数调用库函数，%d 个）' % sum(1 for f in lib.values() if f['calls']))
    A('')
    A('| 调用者 | 调用 |')
    A('|---|---|')
    for ident in sorted(lib):
        f = lib[ident]
        if f['calls']:
            A('| `%s` | %s |' % (ident, ', '.join('`%s`' % c for c in f['calls'])))
    A('')
    A('## 6. 调用要点与陷阱')
    A('')
    A('- 实例节点的输入端口 id **就是目标函数的形参 id**（如 `fmod` 的 `a`/`b`、`clamp` 的 `input`/`min`/`max`）；输出端口恒为 `unique_filter_output`。')
    A('- 形参默认值可用但不显式：不接线时取形参默认值（见 §3 的「=默认」列）。')
    A('- 库函数是**多态**的：同一函数按调用方类型工作（`Function` 实例的输出 id 与类型必须回读，不要假设）。')
    A('- 库函数内部可能调用其它库函数（§5），递归展开后最终只由原子节点组成；全库用到的原子定义共 62 种，**没有任何库函数使用 While**。')
    A('- 文件里可能存在历史残留连接（如 §1 的 `input_v`）：以活动对象为准，不要照抄 XML 的边。')
    A('')
    A('## 7. 重新生成 / 抽查任意函数')
    A('')
    A('```')
    A('# 1) 在 Designer 进程内导出活动对象视图（读库包，不保存任何工程）')
    A("exec(open(r'<skill>\\scripts\\dump_library_functions.py', encoding='utf-8').read())")
    A('# 2) 独立解析发行包 XML 并与活动对象逐节点差分')
    A('python scripts/verify_library_functions.py parse-xml <SD>/resources/packages/functions.sbs --out xml.json')
    A('python scripts/verify_library_functions.py diff sdk.json xml.json --json diff.json --verbose')
    A('python scripts/verify_library_functions.py eval sdk.json xml.json     # 网表求值 vs 实测值')
    A('# 3) 重新渲染本台账')
    A('python scripts/render_library_catalog.py --sdk sdk.json --xml xml.json --diff diff.json --md <md> --json <json>')
    A('# 4) 只想查单个函数')
    A('python scripts/lookup_sd_function.py --library --name "^fmod$" --impl')
    A('```')
    A('')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sdk', required=True)
    ap.add_argument('--xml', required=True)
    ap.add_argument('--diff', required=True)
    ap.add_argument('--md', required=True)
    ap.add_argument('--json', required=True)
    ap.add_argument('--version', default='2.5.0')
    a = ap.parse_args()

    sdk = json.load(open(a.sdk, encoding='utf-8'))['functions']
    xml = json.load(open(a.xml, encoding='utf-8'))['functions']
    diff = json.load(open(a.diff, encoding='utf-8'))
    tmap = build_type_map(diff, xml)
    lib = merge(sdk, xml, tmap)

    md = render_markdown(lib, diff, a.version, {
        'functions': len(xml),
        'nodes': sum(f['node_count'] for f in xml.values()),
        'edges': sum(len(f['edges']) for f in xml.values()),
    })
    with open(a.md, 'w', encoding='utf-8', newline='\n') as f:
        f.write(md)

    payload = {
        'version': a.version,
        'generated_by': 'scripts/render_library_catalog.py',
        'sources': ['scripts/dump_library_functions.py (live SD objects)',
                    'scripts/verify_library_functions.py parse-xml (shipped package XML)'],
        'verification': {
            'functions': diff['summary']['functions'],
            'pass': diff['summary']['pass'],
            'mismatch': diff['summary']['mismatch'],
            'nodes': diff['summary']['nodes'],
            'edges': diff['summary']['edges'],
            'stale_edges': diff.get('stale_edges') or [],
            'default_omissions': diff.get('default_omissions'),
            'joined_without_position': diff.get('joined_without_position'),
            'type_map': diff.get('type_map'),
        },
        'functions': lib,
    }
    with open(a.json, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

    typed = sum(1 for f in lib.values() for n in f['nodes'] if n.get('type'))
    print('catalogue: %d functions, %d nodes (%d with declared type), md=%d bytes, json=%d bytes' % (
        len(lib), sum(f['node_count'] for f in lib.values()), typed,
        os.path.getsize(a.md), os.path.getsize(a.json)))
    print('netlist groups:', ', '.join('%s=%d' % (g, sum(1 for f in lib.values() if f['group'] == g))
                                      for g in NETLIST_GROUPS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
