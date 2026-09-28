#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

REQUIRED_PROBES = {
    'mod_pos', 'mod_neg_a', 'mod_neg_b', 'mod_vec_neg', 'mod_mixed_dim_num',
    'mul_vec2', 'mul_float1', 'mul_mixed_num', 'mulscalar_vec2', 'mulscalar_swapped_num',
    'round_half_neg', 'round_pos', 'frac_neg', 'fmod_neg', 'sign_zero', 'sign_neg',
    'step_edge', 'clamp_lo', 'saturate_hi', 'while_sum', 'while_maxiter', 'while_zero',
    'coord_pos_x', 'coord_size_x',
}

EXPECTED_BEST_FRAGMENTS = {
    'mod_pos': 'control',
    'mod_neg_a': 'floor-based',
    'mod_neg_b': 'floor-based',
    'mod_vec_neg': 'floor-based',
    'mod_mixed_dim_num': 'silently 0',
    'mul_vec2': 'component-wise',
    'mul_float1': '= 12',
    'mul_mixed_num': 'refused -> 0',
    'mulscalar_vec2': 'dot=12',
    'mulscalar_swapped_num': '-> 0',
    'round_half_neg': 'floor(x+0.5)',
    'round_pos': 'half up',
    'frac_neg': 'x-floor(x)',
    'fmod_neg': 'same sign',
    'sign_zero': 'documented = 1',
    'sign_neg': '= -1',
    'step_edge': 'x >= a',
    'clamp_lo': '=0',
    'saturate_hi': '=1',
    'while_sum': 'sum 1..6 = 21',
    'while_maxiter': 'loop still sums',
    'while_zero': 'acc keeps 7',
    'coord_pos_x': 'normalized',
    'coord_size_x': 'pixel-dimension',
}


def verify_report(data, expect_version=None, max_distance=0.01):
    errors = []
    if data.get('schema') != 3:
        errors.append('unsupported probe report schema')
    if data.get('skill_version') != '2.5.0':
        errors.append('probe report skill_version mismatch')
    if data.get('runtime_semantics_reference') != 'RUNTIME_SEMANTICS_BASELINE_v2.5.0.md':
        errors.append('probe report runtime semantics reference mismatch')
    if 'external_sequence_into_while_body' not in data.get('known_hang_probes_skipped', []):
        errors.append('probe report does not record the skipped known-hang topology')
    if not math.isfinite(max_distance) or max_distance <= 0:
        errors.append('max_distance must be finite and positive')
    version = str(data.get('designer_version', 'unknown'))
    if expect_version and version != expect_version:
        errors.append('designer version mismatch: report=%s expected=%s' % (version, expect_version))
    package_path = str(data.get('functions_package') or '').replace('\\', '/').lower()
    if not package_path.endswith('/resources/packages/functions.sbs'):
        errors.append('functions_package is not Adobe resources/packages/functions.sbs')
    raw_results = data.get('results', [])
    if not isinstance(raw_results, list):
        errors.append('results must be a list')
        raw_results = []
    names = [str(r.get('name')) for r in raw_results if isinstance(r, dict)]
    if len(names) != len(set(names)):
        errors.append('duplicate probe names')
    results = {str(r.get('name')): r for r in raw_results if isinstance(r, dict)}
    missing = sorted(REQUIRED_PROBES - set(results))
    if missing:
        errors.append('missing probes: ' + ', '.join(missing))
    for name in sorted(REQUIRED_PROBES & set(results)):
        r = results[name]
        if r.get('status') != 'measured':
            errors.append('%s status=%s' % (name, r.get('status')))
            continue
        try:
            dist = float(r.get('dist'))
        except Exception:
            errors.append('%s has no numeric match distance' % name)
            continue
        if not math.isfinite(dist) or dist < 0:
            errors.append('%s has invalid match distance %r' % (name, r.get('dist')))
            continue
        if dist > max_distance:
            errors.append('%s match distance %.6f > %.6f' % (name, dist, max_distance))
        try:
            value = float(r.get('value'))
        except Exception:
            errors.append('%s has no numeric measured value' % name)
        else:
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                errors.append('%s has invalid measured value %r' % (name, r.get('value')))
        pixel = r.get('pixel')
        if (not isinstance(pixel, (list, tuple)) or len(pixel) != 3 or
                any(not isinstance(c, int) or not 0 <= c <= 255 for c in pixel)):
            errors.append('%s has invalid pixel sample' % name)
        if r.get('bpp') not in (8, 24, 32):
            errors.append('%s has unsupported or missing bpp' % name)
        expected_fragment = EXPECTED_BEST_FRAGMENTS[name]
        if expected_fragment not in str(r.get('best', '')):
            errors.append('%s matched unexpected semantics: %r' % (name, r.get('best')))
    if version == 'unknown':
        errors.append('Designer version could not be detected; set SD_PIXEL_AGENT_DESIGNER_VERSION and re-run')
    return errors


def main():
    ap = argparse.ArgumentParser(description='Verify a v2 native probe report before promoting exact-version semantics.')
    ap.add_argument('report')
    ap.add_argument('--expect-version')
    ap.add_argument('--max-distance', type=float, default=0.01)
    ap.add_argument('--certificate', help='Optional output JSON certificate path')
    ns = ap.parse_args()
    path = Path(ns.report)
    data = json.loads(path.read_text(encoding='utf-8'))
    errors = verify_report(data, ns.expect_version, ns.max_distance)
    if errors:
        print('PROBE REPORT: FAIL')
        for e in errors:
            print('-', e)
        return 1
    cert = {
        'schema': 1,
        'status': 'verified-runtime',
        'skill_version': '2.5.0',
        'designer_version': data['designer_version'],
        'source_report': str(path.resolve()),
        'functions_package': data.get('functions_package'),
        'required_probe_count': len(REQUIRED_PROBES),
        'max_distance': ns.max_distance,
    }
    print('PROBE REPORT: PASS')
    print(json.dumps(cert, ensure_ascii=False, indent=2))
    if ns.certificate:
        Path(ns.certificate).write_text(json.dumps(cert, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
