#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Look up Substance Designer function semantics from Adobe's own shipped files (READ-ONLY).

Two supply sources, because SD exposes them differently:

  1. ATOMIC function nodes (85 definitions, sbs::function::*) -- semantics, port ids,
     port labels and port types are documented in the Python API reference shipped
     with SD itself:
         resources/documentation/pythonapi/html/_sources/pythonapi/modules/sbs_function.rst.txt
     This is the file that contains strings such as
         "The <b>Arc tangent 2</b> function returns the angle in radians between the
          2D vector <b>Vector</b> and the horizontal. (No need to switch x and y ...)"

  2. BUILT-IN library FUNCTIONS (the library "Functions" category, used through instance
     nodes) -- label, description, formals and the *implementation graph* live in:
         resources/packages/functions.sbs
     These are NOT among the 85 atomic definitions: e.g. fmod, frac, round_float1,
     clamp, saturate, sign, step, smoothstep, truncate_float1_decimals,
     normalize_vec2/3/4, rotate_vec2, polar_to_carthesian, carthesian_to_polar.

Nothing here writes to SD or to any package; it only reads files shipped with the
installed application. Use it during IR/port planning, before creating nodes.

Examples
--------
  python lookup_sd_function.py --name "^mod$|^floor$|^ceil$|^abs$"
  python lookup_sd_function.py --name "sign|clamp|round|frac|trunc" --library
  python lookup_sd_function.py --all --json atomic_functions.json
  python lookup_sd_function.py --list-groups --library
  python lookup_sd_function.py --library --name "fmod|round_float1" --impl

Options
-------
  --name REGEX     case-insensitive regex matched against identifier and label
  --all            every entry from the selected source
  --library        read functions.sbs (built-in library Functions) instead of atomics
  --impl           (library only) also print the implementation node/connection list
  --list-groups    (library only) print the group tree with entry counts
  --json PATH      write machine-readable JSON instead of (in addition to) text
  --source PATH    explicit path to the .rst.txt (atomic) or functions.sbs (library)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SD_FALLBACK_DIRS = [
    r"C:\Program Files\Adobe\Adobe Substance 3D Designer",
    r"C:\Program Files (x86)\Adobe\Adobe Substance 3D Designer",
    r"C:\Program Files\Adobe\Adobe Substance 3D Designer (Beta)",
]
RST_REL = Path(
    "resources/documentation/pythonapi/html/_sources/pythonapi/modules/sbs_function.rst.txt"
)
FUNCS_REL = Path("resources/packages/functions.sbs")

# Historical SD type codes seen in .sbs XML (read-only knowledge; never hand-edit XML).
TYPE_CODES = {
    "1": "bool",
    "2": "string",
    "16": "int1",
    "32": "int2",
    "64": "int3",
    "128": "int4",
    "256": "float1",
    "512": "float2",
    "1024": "float3",
    "2048": "float4",
}


def find_install(explicit: str | None = None) -> Path:
    """Locate the Substance Designer installation directory."""
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    for var in ("SD_INSTALL_DIR", "SUBSTANCE_DESIGNER_DIR"):
        if os.environ.get(var):
            cands.append(Path(os.environ[var]))
    cands += [Path(p) for p in SD_FALLBACK_DIRS]
    for base in (r"C:\Program Files\Adobe", r"C:\Program Files (x86)\Adobe"):
        b = Path(base)
        if b.is_dir():
            for child in sorted(b.iterdir()):
                if child.is_dir() and "designer" in child.name.lower():
                    cands.append(child)
    for c in cands:
        if (c / "resources").is_dir():
            return c
    raise SystemExit(
        "Could not locate the Substance Designer install. Pass --source explicitly."
    )


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<nobr>|</nobr>|<br\s*/?>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


# --------------------------------------------------------------------------- atomic


def parse_atomic(rst_path: Path) -> list[dict]:
    """Parse sbs_function.rst.txt into [{identifier,label,description,inputs,outputs}]."""
    lines = rst_path.read_text(encoding="utf-8", errors="replace").splitlines()
    head = re.compile(r"^\[(\d+)/(\d+)\]\s+'(sbs::function::[^']+)'\s*$")
    entries: list[dict] = []
    cur: dict | None = None
    section: str | None = None  # 'Input' | 'Output'
    port: dict | None = None
    in_types = False

    def flush_port():
        nonlocal port
        if cur is not None and port is not None:
            key = "inputs" if section == "Input" else "outputs"
            cur[key].append(port)
        port = None

    for raw in lines:
        line = raw.rstrip()
        m = head.match(line.strip())
        if m:
            flush_port()
            cur = {
                "index": int(m.group(1)),
                "total": int(m.group(2)),
                "identifier": m.group(3),
                "short": m.group(3).split("::")[-1],
                "label": "",
                "description": "",
                "inputs": [],
                "outputs": [],
            }
            entries.append(cur)
            section = None
            in_types = False
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("* SDPropertyCategory"):
            flush_port()
            section = "Input" if "'Input'" in s else "Output"
            in_types = False
            continue
        if s.startswith("* Label:") and port is None:
            cur["label"] = s.split("Label:", 1)[1].strip().strip("'")
            continue
        if s.startswith("* Description:") and port is None:
            cur["description"] = strip_html(s.split("Description:", 1)[1].strip())
            continue
        if s.startswith("* Types:"):
            in_types = True
            continue
        pm = re.match(r"^\*\s+'([^']+)'\s*\[(.+)\]\s*$", s)
        if pm and section:
            flush_port()
            port = {"id": pm.group(1), "flags": pm.group(2), "label": "", "types": []}
            in_types = False
            continue
        if port is not None and s.startswith("* Label:") and not port["label"]:
            port["label"] = s.split("Label:", 1)[1].strip().strip("'")
            continue
        if port is not None and in_types:
            tm = re.match(r"^\*\s+'([^']+)'\s*\((.+)\)\s*$", s)
            if tm:
                port["types"].append(tm.group(1))
                continue
        if not s:
            in_types = False
    flush_port()
    return entries


def report_atomic(entries: list[dict], show_all: bool) -> None:
    for e in entries:
        print("[%d/%d] %s" % (e["index"], e["total"], e["identifier"]))
        print("   label      : %s" % e["label"])
        print("   description: %s" % (e["description"] or "(none)"))
        for p in e["inputs"]:
            print(
                "   in  id=%-18s label=%-14r type=%s"
                % (p["id"], p["label"], ",".join(p["types"]) or "?")
            )
        for p in e["outputs"]:
            print(
                "   out id=%-18s label=%-14r type=%s"
                % (p["id"], p["label"], ",".join(p["types"]) or "?")
            )
        print()


# -------------------------------------------------------------------------- library

XML_TAG = lambda t: t.split("}")[-1]  # noqa: E731
XML_VAL = lambda e: e.get("v")  # noqa: E731


def parse_library(sbs_path: Path) -> tuple[list[dict], dict]:
    """Parse functions.sbs into library Function entries (+ parent map for groups)."""
    tree = ET.fromstring(
        sbs_path.read_text(encoding="utf-8", errors="replace").encode("utf-8", "replace")
    )
    parent = {c: pa for pa in tree.iter() for c in pa}

    def group_path(el) -> str:
        parts: list[str] = []
        node = el
        while node is not None:
            if XML_TAG(node.tag) == "group":
                for ch in node:
                    if XML_TAG(ch.tag) == "identifier" and XML_VAL(ch):
                        parts.append(XML_VAL(ch))
                        break
            node = parent.get(node)
        return "/".join(reversed(parts))

    def attrs(fn) -> dict:
        out: dict[str, str] = {}
        for a in fn:
            if XML_TAG(a.tag) == "attributes":
                for ch in a:
                    out[XML_TAG(ch.tag)] = XML_VAL(ch)
        return out

    def formals(fn) -> list[dict]:
        out = []
        for pi in fn.iter():
            if XML_TAG(pi.tag) != "paraminput":
                continue
            ident = lab = typ = None
            default = None
            for ch in pi:
                tag = XML_TAG(ch.tag)
                if tag == "identifier":
                    ident = XML_VAL(ch)
                elif tag == "attributes":
                    for x in ch:
                        if XML_TAG(x.tag) == "label":
                            lab = XML_VAL(x)
                elif tag == "type":
                    typ = XML_VAL(ch)
                elif tag == "defaultValue":
                    for x in ch:
                        default = XML_VAL(x)
            out.append(
                {
                    "id": ident,
                    "label": lab,
                    "type": TYPE_CODES.get(typ or "", typ),
                    "default": default,
                }
            )
        return out

    def out_type(fn):
        for ch in fn:
            if XML_TAG(ch.tag) == "type":
                return TYPE_CODES.get(XML_VAL(ch) or "", XML_VAL(ch))
        return None

    def implementation(fn) -> list[str]:
        """Node/connection list, uid-resolved.

        NOTE (measured, T47): the uid lives in a *child* ``<uid v=...>`` element and
        the atom name in a child ``<function v=...>``; reading them off the
        ``<paramNode>`` element itself yields None for every node and collapses all
        connections onto one node.  Prefer the verified catalogue (see
        ``load_catalogue``) over this parser.
        """
        nodes: dict[str, list] = {}
        order: list[str] = []
        for pn in fn.iter():
            if XML_TAG(pn.tag) != "paramNode":
                continue
            uid = None
            name = None
            consts: list[str] = []
            for ch in pn:
                tag = XML_TAG(ch.tag)
                if tag == "uid":
                    uid = XML_VAL(ch)
                elif tag == "function":
                    name = XML_VAL(ch)
                elif tag == "funcDatas":
                    for fd in ch.iter():
                        if XML_TAG(fd.tag) == "funcData":
                            cname = None
                            cval = None
                            for sub in fd.iter():
                                st = XML_TAG(sub.tag)
                                if st == "name":
                                    cname = XML_VAL(sub)
                                elif st.startswith("constantValue"):
                                    cval = XML_VAL(sub)
                            if cname and cval is not None:
                                consts.append("%s=%s" % (cname, cval))
            nodes[uid] = [name, [], " ".join(consts)]
            order.append(uid)
        for pn in fn.iter():
            if XML_TAG(pn.tag) != "paramNode":
                continue
            uid = None
            for ch in pn:
                if XML_TAG(ch.tag) == "uid":
                    uid = XML_VAL(ch)
            for cn in pn:
                if XML_TAG(cn.tag) != "connections":
                    continue
                for c in cn:
                    pid = None
                    src = None
                    for ch in c:
                        if XML_TAG(ch.tag) == "identifier":
                            pid = XML_VAL(ch)
                        elif XML_TAG(ch.tag) == "connRef":
                            src = XML_VAL(ch)
                    if uid in nodes and pid:
                        nodes[uid][1].append((pid, src))
        index = dict((u, i) for i, u in enumerate(order))
        out = []
        for i, uid in enumerate(order):
            name, links, consts = nodes[uid]
            parts = ["n%-3d %-26s" % (i, name)]
            if consts:
                parts.append(consts)
            if links:
                parts.append(" ".join(
                    "%s<-%s" % (pid, ("n%d" % index[s]) if s in index else str(s))
                    for pid, s in sorted(links)))
            out.append("  ".join(parts).rstrip())
        return out

    entries: list[dict] = []
    for fn in tree.iter():
        if XML_TAG(fn.tag) != "function":
            continue
        holder = parent.get(fn)
        if holder is None or XML_TAG(holder.tag) != "content":
            continue
        ident = None
        for ch in fn:
            if XML_TAG(ch.tag) == "identifier":
                ident = XML_VAL(ch)
        a = attrs(fn)
        entries.append(
            {
                "group": group_path(fn),
                "identifier": ident,
                "label": a.get("label", ""),
                "tags": a.get("tags", ""),
                "author": a.get("author", ""),
                "description": strip_html(a.get("description")),
                "output_type": out_type(fn),
                "formals": formals(fn),
                "implementation": implementation(fn),
            }
        )
    entries.sort(key=lambda e: (e["group"], e["identifier"] or ""))
    groups: dict[str, int] = {}
    for e in entries:
        groups[e["group"]] = groups.get(e["group"], 0) + 1
    return entries, groups


def load_catalogue() -> dict | None:
    """The verified library catalogue (scripts/render_library_catalog.py output).

    Preferred over parsing the package XML: it was diffed node-by-node against the
    live SD objects (171/171 PASS, spec 11.12) and its netlists reproduce the cooked
    probe values.
    """
    here = Path(__file__).resolve().parent
    for cand in sorted((here.parent / "references").glob("library_functions_v*.json")):
        try:
            return json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def catalogue_impl(fn: dict) -> list[str]:
    edges = fn.get("edges") or []
    out = []
    for i, n in enumerate(fn.get("nodes") or []):
        parts = ["n%-3d %-26s" % (i, n.get("def"))]
        if n.get("type"):
            parts.append("%-7s" % n["type"])
        if n.get("instance_of"):
            parts.append("instance_of=%s" % n["instance_of"])
        c = dict((k, v) for k, v in (n.get("consts") or {}).items() if k != "instance")
        if c:
            parts.append("consts=%s" % json.dumps(c, ensure_ascii=False))
        links = " ".join("%s<-%d" % (e.get("port"), e["from"]) for e in edges if e["to"] == i)
        if links:
            parts.append(links)
        out.append("  ".join(parts).rstrip())
    return out


def report_library(entries: list[dict], show_impl: bool) -> None:
    for e in entries:
        print("[%s] %s" % (e["group"], e["identifier"]))
        print("   label      : %s" % e["label"])
        print("   description: %s" % (e["description"] or "(none)"))
        print("   output     : %s" % e["output_type"])
        for f in e["formals"]:
            print(
                "   in  id=%-14s label=%-12r type=%-7s default=%s"
                % (f["id"], f["label"], f["type"], f["default"])
            )
        if show_impl:
            impl = e.get("implementation") or []
            print("   impl source: %s" % e.get("impl_source", "package XML"))
            for line in impl:
                print("      %s" % line)
        print()


# ----------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default=None, help="case-insensitive regex on identifier/label")
    ap.add_argument("--all", action="store_true", help="print every entry")
    ap.add_argument("--library", action="store_true", help="read functions.sbs (library Functions)")
    ap.add_argument("--impl", action="store_true", help="(library) print implementation nodes")
    ap.add_argument("--no-catalog", dest="no_catalog", action="store_true",
                    help="(library) ignore the verified catalogue and parse the package XML")
    ap.add_argument("--list-groups", action="store_true", help="(library) print group counts")
    ap.add_argument("--json", dest="json_out", default=None, help="write JSON to this path")
    ap.add_argument("--source", default=None, help="explicit source file path")
    ap.add_argument("--install", default=None, help="explicit SD install directory")
    args = ap.parse_args(argv)

    cat = load_catalogue() if (args.library and not args.no_catalog) else None

    src = None
    if args.source:
        src = Path(args.source)
    else:
        try:
            src = find_install(args.install) / (FUNCS_REL if args.library else RST_REL)
        except SystemExit:
            if cat is None:
                raise
    if src is None or not src.is_file():
        if cat is None:
            raise SystemExit("source not found: %s" % src)
        src = Path("(not needed: using the verified catalogue)")

    if args.library:
        if cat is not None:
            print("source: verified catalogue %s (v%s, %d/%d functions diffed clean vs live SD objects)"
                  % (cat.get("generated_by", "render_library_catalog.py"), cat.get("version"),
                     (cat.get("verification") or {}).get("pass"), (cat.get("verification") or {}).get("functions")))
            entries = []
            for ident, fn in cat["functions"].items():
                entries.append({
                    "group": fn["group"],
                    "identifier": ident,
                    "label": fn["label"],
                    "tags": "",
                    "author": "",
                    "description": fn.get("description") or "",
                    "output_type": fn.get("declared_output_type"),
                    "formals": [{"id": f["id"], "label": f["label"], "type": f["type"], "default": f["default"]}
                                for f in fn.get("formals") or []],
                    "implementation": catalogue_impl(fn) if args.impl else [],
                    "impl_source": "verified catalogue",
                })
            groups: dict[str, int] = {}
            for e in entries:
                groups[e["group"]] = groups.get(e["group"], 0) + 1
        else:
            if args.impl and not args.no_catalog:
                print("WARNING: verified catalogue not found; falling back to the package XML parser.")
                print("         NOTE: the XML omits constants equal to the atom default, so some")
                print("         const_*/swizzle* nodes print without a value (spec T47/11.12).")
            entries, groups = parse_library(src)
        if args.list_groups:
            print("source: %s" % src)
            print("entries: %d" % len(entries))
            for g, n in sorted(groups.items()):
                print("   %-42s %d" % (g or "(root)", n))
            print()
        rx = re.compile(args.name, re.I) if args.name else None
        sel = [
            e
            for e in entries
            if args.all
            or rx is None
            or (rx.search(e["identifier"] or "") or rx.search(e["label"] or ""))
        ]
        if rx is None and not args.all and not args.list_groups:
            sel = entries
        if sel and not args.list_groups or (sel and args.list_groups):
            report_library(sel, args.impl)
        payload = {
            "source": str(src),
            "kind": "library-functions",
            "count": len(sel),
            "groups": groups,
            "entries": sel,
        }
        print("matched %d / %d library Functions" % (len(sel), len(entries)))
    else:
        entries = parse_atomic(src)
        rx = re.compile(args.name, re.I) if args.name else None
        sel = [
            e
            for e in entries
            if args.all
            or rx is None
            or rx.search(e["short"])
            or rx.search(e["identifier"])
            or rx.search(e["label"])
        ]
        report_atomic(sel, args.all)
        payload = {
            "source": str(src),
            "kind": "atomic-functions",
            "count": len(sel),
            "total": len(entries),
            "entries": sel,
        }
        print("matched %d / %d atomic function definitions" % (len(sel), len(entries)))

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("json written: %s" % args.json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())