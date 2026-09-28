from __future__ import annotations
import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_probe_report import verify_report, REQUIRED_PROBES, EXPECTED_BEST_FRAGMENTS
from check_compatibility import normalize_version, status_for


class ReleasePolicyTests(unittest.TestCase):
    def make_probe_report(self, version='16.0.5'):
        return {
            'schema': 3,
            'skill_version': '2.5.0',
            'runtime_semantics_reference': 'RUNTIME_SEMANTICS_BASELINE_v2.5.0.md',
            'known_hang_probes_skipped': ['external_sequence_into_while_body'],
            'designer_version': version,
            'functions_package': '/opt/Adobe/resources/packages/functions.sbs',
            'results': [
                {
                    'name': name,
                    'status': 'measured',
                    'dist': 0.001,
                    'value': 0.5,
                    'pixel': [128, 128, 128],
                    'bpp': 24,
                    'best': 'expected ' + EXPECTED_BEST_FRAGMENTS[name],
                }
                for name in sorted(REQUIRED_PROBES)
            ],
        }

    def test_1605_fails_closed_until_native_probe(self):
        m = json.loads((ROOT/'references'/'compatibility_matrix_v2.5.0.json').read_text(encoding='utf-8'))
        self.assertEqual(m['designer_versions']['16.0.5']['status'], 'runtime-reprobe-required')
        self.assertTrue(m['policy']['exact_designer_version_required_for_measured_semantics'])
        self.assertEqual(set(EXPECTED_BEST_FRAGMENTS), REQUIRED_PROBES)

    def test_probe_has_no_fixed_destructive_output_cleanup(self):
        s = (ROOT/'scripts'/'probe_sd_semantics.py').read_text(encoding='utf-8')
        self.assertNotIn(r'E:\\SD_AI\\_probe\\out', s)
        self.assertNotIn('scratches = [p for p in pkg_mgr.getUserPackages()', s)
        self.assertNotIn('PKG = scratches[0]', s)
        self.assertIn('PKG = pkg_mgr.newUserPackage()', s)
        self.assertIn('SAFETY_INVARIANT_001', s)

    def test_retest_gates_are_routed_and_exports_match_exact_graph_prefix(self):
        skill = (ROOT/'SKILL.md').read_text(encoding='utf-8')
        spec = (ROOT/'references'/'SD_PixelProcessor_AGENT_SPEC_v2.5.0.md').read_text(encoding='utf-8')
        probe = (ROOT/'scripts'/'probe_sd_semantics.py').read_text(encoding='utf-8')
        self.assertIn('MORPHING_RETEST_GATES.md', skill)
        self.assertIn('MORPHING_RETEST_GATES.md', spec)
        self.assertIn("stem = g.getIdentifier() + '_output_'", probe)
        self.assertNotIn('and name in f', probe)
        self.assertIn('SUN_SHOWER_RETEST_GATES.md', skill)
        self.assertIn('SUN_SHOWER_RETEST_GATES.md', spec)
        self.assertIn('return graph.newNode(definition_id)', probe)

    def test_probe_library_lookup_is_package_scoped(self):
        s = (ROOT/'scripts'/'probe_sd_semantics.py').read_text(encoding='utf-8')
        self.assertIn("'resources', 'packages', 'functions.sbs'", s)
        self.assertIn("if len(hits) != 1", s)
        self.assertNotIn('for pk in pkg_mgr.getPackages():\n        try:\n            res = pk.getChildrenResources(True)', s)

    def test_installers_guard_self_install_and_use_codex_skill_root(self):
        ps = (ROOT/'scripts'/'install.ps1').read_text(encoding='utf-8')
        sh = (ROOT/'scripts'/'install.sh').read_text(encoding='utf-8')
        self.assertIn('Already installed at:', ps)
        self.assertIn('Already installed at:', sh)
        self.assertIn("Join-Path $env:CODEX_HOME 'skills'", ps)
        self.assertIn('$CODEX_HOME/skills', sh)

    def test_while_policy_separates_engine_capability_and_agent_default(self):
        s = (ROOT/'references'/'COMPATIBILITY_MATRIX_v2.5.0.md').read_text(encoding='utf-8')
        self.assertIn('engine capability', s)
        self.assertIn('finite explained cap', s)
        self.assertIn('`-1` is permitted', s)

    def test_probe_report_requires_complete_same_version_measurements(self):
        good = self.make_probe_report()
        self.assertEqual(verify_report(good, '16.0.5'), [])
        bad = dict(good)
        bad['designer_version'] = '16.0.3'
        self.assertTrue(verify_report(bad, '16.0.5'))

    def test_probe_report_rejects_nan_duplicate_and_wrong_semantics(self):
        report = self.make_probe_report()
        report['results'][0]['dist'] = 'nan'
        report['results'][1]['best'] = 'wrong competing interpretation'
        report['results'].append(dict(report['results'][2]))
        errors = verify_report(report, '16.0.5')
        self.assertTrue(any('invalid match distance' in e for e in errors))
        self.assertTrue(any('unexpected semantics' in e for e in errors))
        self.assertIn('duplicate probe names', errors)

    def test_exact_version_does_not_truncate_build_component(self):
        self.assertEqual(normalize_version('Designer 16.0.3.99'), '16.0.3.99')
        version, record = status_for('Designer 16.0.3.99')
        self.assertEqual(version, '16.0.3.99')
        self.assertEqual(record['status'], 'runtime-reprobe-required')

    def test_library_catalog_output_types_follow_actual_roots(self):
        payload = json.loads(
            (ROOT/'references'/'library_functions_v2.5.0.json').read_text(encoding='utf-8')
        )
        functions = payload['functions']

        def root_type(name, seen=()):
            self.assertNotIn(name, seen)
            fn = functions[name]
            node = fn['nodes'][fn['output']]
            if node.get('type'):
                return node['type']
            target = node.get('instance_of')
            self.assertIn(target, functions)
            return root_type(target, seen + (name,))

        mismatches = {
            name: (fn.get('declared_output_type'), root_type(name))
            for name, fn in functions.items()
            if fn.get('declared_output_type') != root_type(name)
        }
        self.assertEqual(mismatches, {})
        self.assertEqual(functions['length_vec2']['declared_output_type'], 'float1')

    def test_field_evidence_guards_are_preserved(self):
        skill = (ROOT/'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('A Get takes the variable identifier, never a node alias', skill)
        self.assertIn('Do not use the deep tail of a long nested-`ifelse` mux', skill)
        self.assertIn('operator- and operand-order-dependent', skill)
        self.assertNotIn('mixed-dimension wiring is ACCEPTED by the SDK with no error and then cooks to a **silent 0**', skill)


if __name__ == '__main__':
    unittest.main()


# Runtime semantics are checked in test_runtime_semantics.py.
