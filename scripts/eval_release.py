#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import py_compile
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_validator():
    cp = subprocess.run([sys.executable, str(ROOT/'scripts'/'validate_skill.py')], text=True, capture_output=True)
    print(cp.stdout, end='')
    if cp.returncode:
        print(cp.stderr, end='', file=sys.stderr)
        raise RuntimeError('validate_skill.py failed')


def compile_scripts():
    for p in sorted((ROOT/'scripts').glob('*.py')):
        py_compile.compile(str(p), doraise=True)
    print('PY_COMPILE: PASS')


def check_manifest():
    mf = json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8-sig'))
    if mf['version'] != (ROOT/'VERSION').read_text(encoding='utf-8').strip():
        raise RuntimeError('manifest version mismatch')
    records = mf['files']
    manifest_paths = [rec['path'] for rec in records]
    if len(manifest_paths) != len(set(manifest_paths)):
        raise RuntimeError('manifest contains duplicate paths')
    disk_paths = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel == 'MANIFEST.json' or rel.startswith('staging/') or '/__pycache__/' in '/' + rel + '/' or rel.endswith('.pyc'):
            continue
        disk_paths.append(rel)
    if set(manifest_paths) != set(disk_paths):
        missing = sorted(set(manifest_paths) - set(disk_paths))
        extra = sorted(set(disk_paths) - set(manifest_paths))
        raise RuntimeError('manifest file-set mismatch: missing=%s extra=%s' % (missing, extra))
    for rec in records:
        p = ROOT / rec['path']
        if not p.is_file():
            raise RuntimeError('manifest missing file: ' + rec['path'])
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != rec['sha256'] or p.stat().st_size != rec['bytes']:
            raise RuntimeError('manifest mismatch: ' + rec['path'])
    print('MANIFEST: PASS (%d files)' % len(mf['files']))


def run_unittests():
    suite = unittest.defaultTestLoader.discover(str(ROOT/'evals'), pattern='test_*.py')
    count = suite.countTestCases()
    if count == 0:
        raise RuntimeError('no behavioral evals discovered')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('behavioral evals failed')
    print('BEHAVIORAL EVALS: PASS (%d tests)' % count)


def main():
    run_validator()
    compile_scripts()
    check_manifest()
    run_unittests()
    print('RELEASE EVAL: PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('RELEASE EVAL: FAIL - %s' % exc, file=sys.stderr)
        raise SystemExit(1)
