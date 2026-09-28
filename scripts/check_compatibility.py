#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / 'references' / 'compatibility_matrix_v2.5.0.json'


def normalize_version(value: str) -> str:
    m = re.search(r'\d+(?:\.\d+){1,3}', value or '')
    return m.group(0) if m else 'unknown'


def load_matrix():
    return json.loads(MATRIX.read_text(encoding='utf-8'))


def status_for(version: str):
    data = load_matrix()
    v = normalize_version(version)
    rec = data.get('designer_versions', {}).get(v)
    if rec is None:
        return v, {
            'status': data['policy']['unknown_or_unverified_version'],
            'notes': 'No exact-version bundled native baseline.'
        }
    return v, rec


def main():
    ap = argparse.ArgumentParser(description='Check SD Pixel Processor Agent compatibility state.')
    ap.add_argument('--version', required=True, help='Designer version string, e.g. 16.0.5')
    ap.add_argument('--json', action='store_true', dest='as_json')
    ap.add_argument('--probe-report', help='Optional same-version v2 probe_report.json')
    ns = ap.parse_args()
    version, rec = status_for(ns.version)
    if ns.probe_report:
        from verify_probe_report import verify_report
        data = json.loads(Path(ns.probe_report).read_text(encoding='utf-8'))
        errs = verify_report(data, expect_version=version)
        if not errs:
            rec = {'status': 'verified-runtime', 'notes': 'Same-version native probe report passed.'}
        else:
            rec = {'status': 'runtime-reprobe-required', 'notes': 'Probe report rejected: ' + '; '.join(errs)}
    out = {'designer_version': version, **rec}
    if ns.as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print('%s: %s' % (version, rec['status']))
        if rec.get('notes'):
            print(rec['notes'])
    return 0 if rec['status'] in ('verified-baseline', 'verified-runtime') else 2


if __name__ == '__main__':
    raise SystemExit(main())
