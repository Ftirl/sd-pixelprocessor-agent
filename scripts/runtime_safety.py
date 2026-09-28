#!/usr/bin/env python3
"""Runtime safety primitives for sd-pixelprocessor-agent.

This module intentionally does not import ``sd`` so that its destructive-operation
rules can be unit-tested outside Substance Designer.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, Optional

PROBE_PREFIX = "sd_pp_probe_"
OWNER_MARKER = ".sd_pixelprocessor_agent_owned.json"
FUNCTIONS_PACKAGE_SUFFIX = os.path.normcase(os.path.normpath(os.path.join("resources", "packages", "functions.sbs")))


def _norm(path: object) -> str:
    if path is None:
        return ""
    s = str(path).strip()
    if not s:
        return ""
    return os.path.normcase(os.path.realpath(os.path.normpath(s)))


def package_file_path(package: object) -> str:
    try:
        return str(package.getFilePath() or "")
    except Exception:
        return ""


def is_builtin_functions_package(package: object, override: Optional[str] = None) -> bool:
    """Return True only for Adobe's shipped ``resources/packages/functions.sbs``.

    ``override`` is an explicit full path for non-standard installations.  It is
    compared by normalized real path, not by basename, so a user file named
    ``functions.sbs`` cannot shadow the built-in library.
    """
    actual = _norm(package_file_path(package))
    if not actual:
        return False
    if override:
        return actual == _norm(override)
    return actual.endswith(FUNCTIONS_PACKAGE_SUFFIX)


def _identifier_matches(identifier: str, name: str) -> bool:
    low = (identifier or "").lower()
    target = name.lower()
    return low == target or low.endswith("/" + target) or low.endswith("::" + target)


def resolve_unique_library_resource(packages: Iterable[object], name: str, override: Optional[str] = None):
    """Resolve exactly one Function from the built-in Adobe Functions package.

    Fail closed on zero or multiple matches.  Never returns the first global
    identifier match and therefore cannot be shadowed by user packages.
    """
    builtin_packages = [p for p in packages if is_builtin_functions_package(p, override)]
    if len(builtin_packages) != 1:
        paths = [package_file_path(p) or "<unsaved>" for p in builtin_packages]
        raise RuntimeError(
            "expected exactly one Adobe functions.sbs package, found %d: %s" %
            (len(builtin_packages), paths)
        )
    package = builtin_packages[0]
    matches = []
    try:
        resources = package.getChildrenResources(True)
    except Exception as exc:
        raise RuntimeError("cannot enumerate built-in functions.sbs: %s" % exc)
    for resource in resources:
        try:
            identifier = resource.getIdentifier()
        except Exception:
            continue
        if identifier and _identifier_matches(identifier, name):
            matches.append((package, resource, identifier))
    if len(matches) != 1:
        ids = [m[2] for m in matches]
        raise RuntimeError(
            "built-in Function %r resolved to %d resources in %s: %s" %
            (name, len(matches), package_file_path(package), ids)
        )
    return matches[0]


def create_probe_run_dir(base_dir: Optional[str] = None) -> str:
    """Create a unique owned run directory; never reuses or clears a directory."""
    base = base_dir or os.environ.get("SD_PIXEL_AGENT_PROBE_DIR") or None
    if base:
        os.makedirs(base, exist_ok=True)
    path = tempfile.mkdtemp(prefix=PROBE_PREFIX, dir=base)
    marker = Path(path) / OWNER_MARKER
    marker.write_text(json.dumps({"owner": "sd-pixelprocessor-agent", "schema": 1}), encoding="utf-8")
    return path


def is_owned_probe_dir(path: str) -> bool:
    p = Path(path)
    return p.is_dir() and p.name.startswith(PROBE_PREFIX) and (p / OWNER_MARKER).is_file()


def remove_owned_probe_dir(path: str) -> None:
    """Remove only a directory created by :func:`create_probe_run_dir`."""
    if not is_owned_probe_dir(path):
        raise RuntimeError("refusing to remove non-owned probe directory: %s" % path)
    shutil.rmtree(path)


def graph_identifiers(package: object):
    out = []
    try:
        resources = package.getChildrenResources(False)
    except Exception:
        return tuple()
    for r in resources:
        if not hasattr(r, "getNodes"):
            continue
        try:
            ident = r.getIdentifier()
        except Exception:
            ident = "<?>"
        out.append(str(ident))
    return tuple(sorted(out))


def snapshot_user_packages(package_manager: object):
    """Capture a non-mutating fingerprint of all pre-existing user packages."""
    records = []
    for p in list(package_manager.getUserPackages()):
        records.append({
            "object_id": id(p),
            "file_path": package_file_path(p),
            "graphs": graph_identifiers(p),
        })
    return tuple(sorted(records, key=lambda x: x["object_id"]))


def assert_preexisting_packages_unchanged(before, package_manager: object, owned_package: object = None) -> None:
    """Fail if a pre-existing package's graph fingerprint changed during a probe."""
    current_by_id = {id(p): p for p in list(package_manager.getUserPackages())}
    errors = []
    owned_id = id(owned_package) if owned_package is not None else None
    for rec in before:
        oid = rec["object_id"]
        if oid == owned_id:
            continue
        p = current_by_id.get(oid)
        if p is None:
            errors.append("pre-existing package disappeared: %s" % (rec["file_path"] or "<unsaved>"))
            continue
        now = graph_identifiers(p)
        if now != rec["graphs"]:
            errors.append(
                "pre-existing package graph set changed: %s before=%s after=%s" %
                (rec["file_path"] or "<unsaved>", rec["graphs"], now)
            )
    if errors:
        raise RuntimeError("SAFETY_INVARIANT_001 failed: " + "; ".join(errors))


def detect_designer_version(app: object) -> str:
    """Best-effort version detection without assuming one SDK method name."""
    for name in ("getVersion", "getApplicationVersion", "getVersionString"):
        fn = getattr(app, name, None)
        if callable(fn):
            try:
                value = fn()
            except Exception:
                continue
            if value is not None:
                m = re.search(r"\d+(?:\.\d+){1,3}", str(value))
                if m:
                    return m.group(0)
    env = os.environ.get("SD_PIXEL_AGENT_DESIGNER_VERSION", "")
    m = re.search(r"\d+(?:\.\d+){1,3}", env)
    return m.group(0) if m else "unknown"
