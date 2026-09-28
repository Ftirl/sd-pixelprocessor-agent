from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import runtime_semantics as rs

class RuntimeSemanticTests(unittest.TestCase):
    def test_coordinate_lowering_is_normalized(self):
        q=rs.shader_coord_lowering(square_target=True)
        self.assertEqual(q['expression'], '$pos - 0.5')
        self.assertFalse(q['allowed_raw_pos_as_fragcoord'])
        nonsquare=rs.shader_coord_lowering(square_target=False)
        self.assertEqual(nonsquare['size_source'], 'explicit-output-size-or-verified-formal')

    def test_post_set_transport_requires_ordered_get_topology(self):
        self.assertEqual(rs.post_set_transport(), 'get_sequence_topology_required')

    def test_cross_statement_set_dag_is_rejected_even_with_sequence_spine(self):
        ir = {'mode': 'statement',
              'post_set_reads': [{'transport': 'sequence_ordered_get',
                                  'scope_verified': True, 'dimension_match': True,
                                  'set_node': 'set_x', 'get_node': 'get_x',
                                  'sequence_node': 'seq', 'output_nodes': ['root'],
                                  'wiring_edges': [
                                      {'source': 'set_x', 'target': 'seq', 'target_port': 'in'},
                                      {'source': 'get_x', 'target': 'add', 'target_port': 'a'},
                                      {'source': 'add', 'target': 'seq', 'target_port': 'last'},
                                      {'source': 'seq', 'target': 'root', 'target_port': 'a'}]}],
              'statement_edges': [
                  {'source_statement': 'S0', 'target_statement': 'S1',
                   'source_kind': 'set', 'target_kind': 'mul',
                   'registered_exception': True},
                  {'source_statement': 'S0', 'target_statement': 'S0',
                   'source_kind': 'set', 'target_kind': 'sequence'}]}
        self.assertEqual(rs.validate_ir(ir), ['RS_CROSS_STATEMENT_DAG'])
        ir['statement_edges'][0] = {'source_statement': 'S1', 'target_statement': 'S1',
                                    'source_kind': 'get', 'target_kind': 'mul'}
        self.assertEqual(rs.validate_ir(ir), [])
        ir['post_set_reads'][0]['scope_verified'] = False
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_NOT_PROVEN'])
        ir['post_set_reads'][0]['scope_verified'] = True
        ir['post_set_reads'][0]['wiring_edges'] = [
            edge for edge in ir['post_set_reads'][0]['wiring_edges']
            if edge['source'] != 'get_x']
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_SEQUENCE_TOPOLOGY'])
        del ir['post_set_reads'][0]['wiring_edges']
        self.assertEqual(rs.validate_ir(ir),
                         ['RS_GET_EDGE_AUDIT_MISSING', 'RS_GET_SEQUENCE_TOPOLOGY'])
        self.assertEqual(rs.validate_ir({'mode': 'statement'}),
                         ['RS_STATEMENT_EDGE_AUDIT_MISSING'])
        fallback = {'mode': 'statement', 'statement_edges': [],
                    'post_set_reads': [{'transport': 'statement_sequence_output'}]}
        self.assertEqual(rs.validate_ir(fallback), ['RS_SEQUENCE_FALLBACK_UNPROVEN'])
        fallback['post_set_reads'][0].update(fallback_reason='Get returned zero in scope',
                                             numeric_verified=True)
        self.assertEqual(rs.validate_ir(fallback), [])

    def test_ordered_get_must_feed_later_sequence_branch(self):
        edges = [
            {'source': 'set_x', 'target': 'seq', 'target_port': 'in'},
            {'source': 'get_x', 'target': 'add', 'target_port': 'a'},
            {'source': 'const_1', 'target': 'add', 'target_port': 'b'},
            {'source': 'add', 'target': 'seq', 'target_port': 'last'},
            {'source': 'seq', 'target': 'root', 'target_port': 'a'},
        ]
        read = {'transport': 'sequence_ordered_get', 'scope_verified': True,
                'dimension_match': True, 'set_node': 'set_x', 'get_node': 'get_x',
                'sequence_node': 'seq', 'output_nodes': ['root'],
                'wiring_edges': edges}
        ir = {'mode': 'statement', 'statement_edges': [], 'post_set_reads': [read]}
        self.assertEqual(rs.validate_ir(ir), [])
        read['wiring_edges'] = [edge for edge in edges if edge['source'] != 'get_x']
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_SEQUENCE_TOPOLOGY'])
        read['wiring_edges'] = edges
        read['output_nodes'] = ['other_root']
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_SEQUENCE_TOPOLOGY'])
        read['output_nodes'] = ['root']
        read['wiring_edges'] = [{**edge, 'target_port': 'last'} if edge['source'] == 'set_x'
                                else edge for edge in edges]
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_SEQUENCE_TOPOLOGY'])
        read['wiring_edges'] = edges + [
            {'source': 'get_x', 'target': 'seq', 'target_port': 'in'}]
        self.assertEqual(rs.validate_ir(ir), ['RS_GET_SEQUENCE_TOPOLOGY'])

    def test_control_roots_are_not_deliverable_outputs(self):
        for k in ('set','sequence','while','ifelse_control'):
            self.assertFalse(rs.terminal_root_allowed(k))
        self.assertTrue(rs.terminal_root_allowed('add'))

    def test_control_root_exception_requires_probe_and_caller_oracle(self):
        self.assertFalse(rs.terminal_root_allowed('sequence', current_session_probe_pass=True))
        self.assertFalse(rs.terminal_root_allowed('sequence', caller_oracle_pass=True))
        self.assertTrue(rs.terminal_root_allowed('sequence', current_session_probe_pass=True,
                                                caller_oracle_pass=True))

    def test_external_sequence_into_while_body_is_forbidden(self):
        self.assertFalse(rs.while_body_edge_allowed('sequence','outer_block'))
        self.assertTrue(rs.while_body_edge_allowed('sequence','while_body'))
        self.assertTrue(rs.while_body_edge_allowed('const_float4','outer_block'))

    def test_sequence_vector_scalar_uses_mul_broadcast(self):
        x=rs.multiply_lowering(vector_dim=4, scalar=True, sequence_derived_vector=True)
        self.assertEqual(x, {'node':'mul','broadcast':True,'broadcast_dim':4})
        y=rs.multiply_lowering(vector_dim=4, scalar=True, sequence_derived_vector=False)
        self.assertEqual(y['node'],'mulscalar')

    def test_ir_linter_finds_runtime_regressions(self):
        ir={
          'outputs':[{'kind':'sequence'}],
          'function_outputs':[{'kind':'set'}],
          'while_body_inputs':[{'source_kind':'sequence','source_scope':'outer_block'}],
          'multiplies':[{'node':'mulscalar','sequence_derived_vector':True}],
          'post_set_reads':[{'transport':'bare_get'}],
          'shader_coords':{'raw_pos_as_fragcoord':True, 'raw_size_as_resolution':True},
        }
        self.assertEqual(rs.validate_ir(ir), sorted({
          'RS_TERMINAL','RS_FUNCTION_OUTPUT','SAFETY_INVARIANT_002','RS_MULSEQ','RS_SETSEQ','RS_COORD',
          'RS_SIZE_SOURCE'}))

if __name__=='__main__': unittest.main()
