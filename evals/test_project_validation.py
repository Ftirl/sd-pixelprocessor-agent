from __future__ import annotations
import sys
import struct
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from project_validation import (
    StateRead, backward_reachable, bmp_dimensions, check_arithmetic_dimensions,
    can_hoist_leading_break, check_branch_coverage, check_build_stage_order,
    check_call_formals, check_definite_component_reads, check_definition_allowed,
    check_export_size, check_function_numeric_gate, check_rgba_export,
    check_time_channel_evidence,
    check_formal_state_collisions, check_get_dimensions, check_marked_root,
    check_oracle_evidence, check_oracle_provenance, check_output_reachability,
    check_probe_encoding, check_probe_precision, check_row_view_join,
    check_source_coverage, check_state_reads, check_transform_application_coverage,
    check_vector_slots, estimated_inline_nodes,
    exact_loaded_package_index, exact_loaded_package_path, preflight_affine_probe,
    require_verified_dependencies, source_sha256,
    exact_export_match, exact_graph_export_match, glsl_matrix_rows,
    output_log2_pair,
)


class ProjectValidationTests(unittest.TestCase):
    def test_morphing_dimension_and_order_fail_before_caller(self):
        writes = {('rot2', 'rx'): 1, ('rot2', 'ry'): 1}
        reads = [StateRead('rx', 2, 'rot2', True), StateRead('ry', 1, 'rot2', False)]
        self.assertEqual(check_state_reads(writes, reads), [
                         'DIMENSION_MISMATCH:rot2:rx:1->2', 'UNORDERED_READ:rot2:ry'])

    def test_crate_get_vector_and_transform_gates(self):
        graph = {'formals': {'p': 2}, 'sets': {}, 'gets': [
            {'name': 'p', 'dimension': 1, 'scope': 'formals'}]}
        self.assertEqual(check_get_dimensions(graph), ['GET_DIMENSION_MISMATCH:formals:p:2->1'])
        self.assertEqual(check_vector_slots([{'id': 'camPos',
            'source_components': ('camX', 'camY', 'camZ'),
            'componentsin': ('camX', 'camZ'), 'componentslast': 'camY'}]),
            ['VECTOR_SLOT_ORDER:camPos'])
        self.assertEqual(check_transform_application_coverage(
            {'vertex', 'normal', 'soft_normal'}, {'normal', 'soft_normal'}),
            ['UNMAPPED_TRANSFORM_SITE:vertex'])
        self.assertEqual(check_branch_coverage({'outer.true', 'outer.false'},
                                               {'outer.true'}),
                         ['UNCOVERED_SOURCE_PATH:outer.false'])

    def test_crate_root_precision_and_oracle_provenance(self):
        self.assertEqual(check_marked_root('function', 4, 1, designer_version='16.0.3',
                         root_definition_id='sbs::function::while'),
                         ['CONTROL_ROOT_CALLER_PROBE_REQUIRED:sbs::function::while'])
        self.assertEqual(check_probe_precision('affine', 2, 1 / 31),
                         ['PROBE_PRECISION_INSUFFICIENT'])
        self.assertEqual(check_probe_precision('direct', 1, 1 / 31), [])
        with tempfile.TemporaryDirectory() as tmp:
            source, table = Path(tmp) / 'oracle.py', Path(tmp) / 'units.json'
            source.write_text('a=1', encoding='utf-8')
            table.write_text('{"a":1}', encoding='utf-8')
            source_hash, table_hash = source_sha256(source), source_sha256(table)
            self.assertEqual(check_oracle_provenance(source, table, source_hash, table_hash), [])
            source.write_text('a=2', encoding='utf-8')
            self.assertEqual(check_oracle_provenance(source, table, source_hash, table_hash),
                             ['STALE_ORACLE_SOURCE'])

    def test_missing_formal_is_explicit(self):
        self.assertEqual(check_call_formals({'p', 'time'}, {'p'}), ['UNCONNECTED_FORMAL:time'])

    def test_large_export_is_not_accepted_as_requested_size(self):
        self.assertEqual(check_export_size((8192, 8192), (1024, 1024)),
                         ['EXPORT_SIZE_MISMATCH:8192x8192!= 1024x1024'])

    def test_bmp_header_preserves_signed_row_order(self):
        header = bytearray(54)
        header[:2] = b'BM'
        struct.pack_into('<I', header, 14, 40)
        struct.pack_into('<ii', header, 18, 1024, -512)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'top_down.bmp'
            path.write_bytes(header)
            self.assertEqual(bmp_dimensions(path), (1024, 512, 'top-down'))

    def test_pp_root_dimension_and_marked_count(self):
        self.assertEqual(check_marked_root('pp_inner', 2, 0, designer_version='16.0.3'),
                         ['NO_MARKED_OUTPUT', 'PP_ROOT_DIM_UNSUPPORTED:2'])
        self.assertEqual(check_marked_root('pp_inner', 4, 1, designer_version='16.0.3'), [])
        self.assertEqual(check_marked_root('function', 2, 1, designer_version='16.0.3'), [])
        self.assertEqual(check_marked_root('pp_inner', 4, 1, designer_version='16.0.5'),
                         ['PP_ROOT_DIM_VERSION_PROBE_REQUIRED'])

    def test_preloop_set_and_while_must_reach_output(self):
        broken = [('set_W', 'pre_sequence'), ('while', 'unused'), ('get_color', 'root')]
        self.assertEqual(backward_reachable('root', broken), {'get_color', 'root'})
        self.assertEqual(check_output_reachability('root', broken, {'set_W', 'while'}),
                         ['UNREACHABLE_REQUIRED_NODE:set_W', 'UNREACHABLE_REQUIRED_NODE:while'])
        fixed = [('set_W', 'pre_sequence'), ('pre_sequence', 'while'), ('while', 'root')]
        self.assertEqual(check_output_reachability('root', fixed, {'set_W', 'while'}), [])

    def test_export_tag_must_match_exact_prefix(self):
        files = ['mcap_coords2_output_0.bmp', 'mcap_coords_output_0.bmp']
        self.assertEqual(exact_export_match(files, 'mcap_', 'coords'), 'mcap_coords_output_0.bmp')
        with self.assertRaises(ValueError):
            exact_export_match(files + ['mcap_coords_output_1.bmp'], 'mcap_', 'coords')

    def test_outputsize_uses_log2_exponents(self):
        self.assertEqual(output_log2_pair(32, 32), (5, 5))
        self.assertEqual(output_log2_pair(1024, 512), (10, 9))
        with self.assertRaises(ValueError):
            output_log2_pair(1000, 512)

    def test_saturated_probe_cannot_prove_large_value(self):
        self.assertEqual(check_probe_encoding([22], 64, [22 / 64]), [])
        self.assertEqual(check_probe_encoding([22], 1, [1]), ['SATURATED_PROBE_CHANNEL:0'])

    def test_glsl_matrix_columns_are_transposed_for_matrix_vector_product(self):
        columns = ((1, 2, 3), (4, 5, 6), (7, 8, 9))
        self.assertEqual(glsl_matrix_rows(columns), ((1, 4, 7), (2, 5, 8), (3, 6, 9)))

    def test_graph_kind_definition_guard(self):
        comp = {'sbs::compositing::pixelprocessor', 'sbs::compositing::output'}
        self.assertEqual(check_definition_allowed('sbs::function::const_float1', comp),
                         ['UNKNOWN_DEFINITION_FOR_GRAPH:sbs::function::const_float1'])
        self.assertEqual(check_definition_allowed('sbs::compositing::output', comp), [])

    def test_formal_name_must_not_shadow_carried_state(self):
        self.assertEqual(check_formal_state_collisions({'p', 'time'}, {'p', 'amp'}),
                         ['FORMAL_SHADOWS_CARRIED_STATE:p'])

    def test_missing_package_does_not_become_new_scratch_package(self):
        target = Path(tempfile.gettempdir()) / 'sun_shower_target.sbs'
        self.assertEqual(exact_loaded_package_path(target, [target]), str(target))
        with self.assertRaises(ValueError):
            exact_loaded_package_path(target, [])

    def test_source_hash_changes_with_disk_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'builder.py'
            path.write_text('VALUE = 1\n', encoding='utf-8')
            before = source_sha256(path)
            path.write_text('VALUE = 2\n', encoding='utf-8')
            self.assertNotEqual(before, source_sha256(path))

    def test_mixed_arithmetic_fails_before_cook(self):
        self.assertEqual(check_arithmetic_dimensions([
            ('rdx', 'mul', 3, 1), ('rgb', 'mul', 3, 3),
            ('clamp_upper', 'min', 2, 1)]),
            ['MIXED_ARITHMETIC_DIMENSION:rdx:mul:3x1',
             'MIXED_ARITHMETIC_DIMENSION:clamp_upper:min:2x1'])

    def test_actual_identifier_controls_export_match(self):
        files = ['probe_coords_output_0.bmp', 'probe_coords_1_output_0.bmp']
        self.assertEqual(exact_graph_export_match(files, 'probe_coords_1'), files[1])
        with self.assertRaises(ValueError):
            exact_graph_export_match(files, '')

    def test_inlining_estimate_and_source_coverage(self):
        self.assertEqual(estimated_inline_nodes(9, 217, 106), 2059)
        self.assertEqual(check_source_coverage(
            {'sky', 'water', 'grade'}, {'sky', 'grade'}, set(), {'water'}), [])
        self.assertEqual(check_source_coverage(
            {'sky', 'water', 'grade'}, {'sky'}, set(), set()),
            ['UNCLASSIFIED_SOURCE_SECTION:grade', 'UNCLASSIFIED_SOURCE_SECTION:water'])

    def test_cross_file_views_and_oracle_scope(self):
        self.assertEqual(check_row_view_join(['top_rows', 'file_rows']), ['ROW_VIEW_MISMATCH'])
        self.assertEqual(check_row_view_join(['top_rows', 'top_rows']), [])
        record = {'command': 'oracle --mode image', 'source_hash': 'a',
                  'artifact_hash': 'b', 'view': 'file_rows', 'width': 1024,
                  'height': 1024, 'branches': ['sky', 'water'],
                  'regenerated_this_session': True}
        self.assertEqual(check_oracle_evidence(record, {'sky', 'water'}), [])
        record['branches'] = ['sky']
        record['regenerated_this_session'] = False
        self.assertEqual(check_oracle_evidence(record, {'sky', 'water'}),
                         ['ORACLE_NOT_REGENERATED', 'ORACLE_MISSING_BRANCH:water'])

    def test_function_numeric_gate_blocks_early_caller_and_swapped_vector(self):
        record = {'name': 'cameraRay', 'source_hash': 'abc', 'readback_ok': True,
                  'marked_output': True, 'native_cook_ok': True, 'cases': [
                      {'path': 'base', 'inputs': {'uv': [0.2, 0.7]},
                       'native': [0.2, 0.7], 'oracle': [0.2, 0.7],
                       'tolerance': 0.01, 'oracle_independent': True}]}
        self.assertEqual(check_function_numeric_gate(record, {'base'}), [])
        with self.assertRaisesRegex(ValueError, 'CALLER_BEFORE_FUNCTION_GATE'):
            require_verified_dependencies('main', ['cameraRay'], [])
        events = [{'kind': 'caller_start', 'caller': 'main', 'requires': ['cameraRay']},
                  {'kind': 'function_gate_pass', 'function': 'cameraRay'}]
        self.assertEqual(check_build_stage_order(events),
                         ['CALLER_BEFORE_FUNCTION_GATE:main:cameraRay',
                          'FUNCTION_GATE_STAGE_ORDER:cameraRay:function_gate_pass'])
        ordered = [{'kind': kind, 'function': 'cameraRay'} for kind in (
            'function_created', 'function_readback', 'function_cooked',
            'function_oracle_pass', 'function_gate_pass')]
        self.assertEqual(check_build_stage_order(ordered + [
            {'kind': 'caller_start', 'caller': 'main', 'requires': ['cameraRay']}]), [])
        record['cases'][0]['native'] = [0.7, 0.2]
        self.assertEqual(check_function_numeric_gate(record, {'base'}),
                         ['FUNCTION_GATE_NUMERIC_MISMATCH:cameraRay:0'])

    def test_uninitialized_components_require_explicit_decision(self):
        self.assertEqual(check_definite_component_reads([{
            'name': 'positionRayon', 'components': ['x', 'y', 'z'],
            'definitely_written': ['y']}]),
            ['UNINITIALIZED_COMPONENT_READ:positionRayon.x',
             'UNINITIALIZED_COMPONENT_READ:positionRayon.z'])

    def test_rgba_transport_and_probe_range(self):
        self.assertEqual(check_rgba_export(width=128, height=128, channels=4,
            expected_size=(128, 128), alpha_probe_expected=[0.2, 0.8],
            alpha_probe_observed=[1.0, 1.0]), ['ALPHA_EXPORT_NOT_PRESERVED'])
        self.assertEqual(check_rgba_export(width=128, height=128, channels=4,
            expected_size=(128, 128), alpha_probe_expected=[0.2, 0.8],
            alpha_probe_observed=[0.2, 0.8]), [])
        self.assertEqual(preflight_affine_probe([6.05], offset=.5, gain=.1),
                         ['PROBE_ENCODING_OUT_OF_RANGE:0'])
        self.assertEqual(preflight_affine_probe([6.05], offset=.5, gain=.04), [])

    def test_package_selector_normalizes_windows_separators_and_unicode(self):
        target = r'E:\SD_AI\Descente infinie\测试\Descente_infinie_PP.sbs'
        loaded = [(2, 'e:/sd_ai/Descente infinie/测试/Descente_infinie_PP.sbs')]
        self.assertEqual(exact_loaded_package_index(target, loaded), 2)
        with self.assertRaisesRegex(ValueError, 'loaded='):
            exact_loaded_package_path(target, [])
        self.assertEqual(exact_graph_export_match(
            ['DI_Main_output_0.bmp', 'DI_Main_output_0.png'], 'DI_Main', 'png'),
            'DI_Main_output_0.png')

    def test_only_pure_body_entry_break_can_be_hoisted(self):
        base = dict(first_executable=True, condition_pure=True,
                    reads_entry_state=True, targets_this_loop=True)
        self.assertTrue(can_hoist_leading_break(**base))
        self.assertFalse(can_hoist_leading_break(**{**base, 'prior_effects': True}))
        self.assertFalse(can_hoist_leading_break(**{**base, 'condition_pure': False}))
        self.assertFalse(can_hoist_leading_break(**{**base, 'targets_this_loop': False}))

    def test_t_zero_does_not_claim_manual_or_player_animation(self):
        record = {'system_source': '$time', 'manual_source': 'iTime',
                  'selector_default': 'system', 'manual_parent_binding_verified': False,
                  'manual_frames': [{'iTime': 0, 'effectiveTime': 0}],
                  'manual_oracle_verified': False, 'system_nonzero_verified': False}
        self.assertEqual(check_time_channel_evidence(record), [
            'TIME_MANUAL_BINDING_UNVERIFIED', 'TIME_MANUAL_NONZERO_UNVERIFIED',
            'TIME_SYSTEM_ANIMATION_UNVERIFIED'])
        record.update(manual_parent_binding_verified=True,
                      manual_frames=[{'iTime': 0, 'effectiveTime': 0},
                                     {'iTime': 2.0, 'effectiveTime': 2.0}],
                      manual_oracle_verified=True, system_nonzero_verified=True)
        self.assertEqual(check_time_channel_evidence(record), [])


if __name__ == '__main__':
    unittest.main()
