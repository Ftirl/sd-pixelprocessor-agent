import unittest

from scripts.layout_intelligence import (
    band_height_from_levels, infer_bands, validate_statement_layout,
    select_graph_mode, validate_layout_plan, validate_mode_readback,
    validate_position_application, x_from_producer_depth,
)


class LayoutIntelligenceTests(unittest.TestCase):
    def test_mode_is_locked_by_explicit_user_choice_and_source_kind(self):
        self.assertEqual(select_graph_mode('pure', 'fidelity'), 'expression')
        self.assertEqual(select_graph_mode('straight_line', 'fidelity'), 'statement')
        self.assertEqual(select_graph_mode('straight_line', 'dag'), 'expression')
        with self.assertRaisesRegex(ValueError, 'ASK_USER_FOR_LAYOUT_CHOICE'):
            select_graph_mode('straight_line', None)
        with self.assertRaisesRegex(ValueError, 'DAG_CONFLICTS_WITH_STATE_OR_LOOP'):
            select_graph_mode('stateful_or_loop', 'dag')

    def test_readback_rejects_unannounced_mode_switch(self):
        self.assertEqual(validate_mode_readback('statement', has_sequence=False,
                                                statement_count=3),
                         ['STATEMENT_MODE_MISSING_SEQUENCE'])
        self.assertEqual(validate_mode_readback('expression', has_sequence=True,
                                                statement_count=0),
                         ['EXPRESSION_MODE_HAS_SEQUENCE'])
        self.assertEqual(validate_mode_readback('expression', has_sequence=False,
                                                statement_count=0), [])

    def test_source_to_consumer_depth_moves_right(self):
        self.assertEqual(x_from_producer_depth(0), 0)
        self.assertEqual(x_from_producer_depth(1), 192)
        self.assertEqual(x_from_producer_depth(2), 384)

    def test_rejects_real_project_depth_sign_regression(self):
        # The Morphing builder used x = -192 * (source-to-consumer depth + 1).
        old = {'const': (-192, 0), 'set': (-384, 0), 'seq': (-576, 0)}
        errors = validate_statement_layout(old, [('set', 'seq')],
                                           private_expression_edges=[('const', 'set')])
        self.assertIn('SEQUENCE_NOT_RIGHT_OF_STATEMENT:set->seq', errors)
        self.assertIn('EXPRESSION_EDGE_REVERSED:const->set', errors)

    def test_accepts_right_spine_and_pure_output_to_its_right(self):
        pos = {'input': (-384, 0), 'set1': (-192, 0), 'seq1': (0, 0),
               'set2': (-192, 224), 'seq2': (0, 224), 'pure_output': (192, 224)}
        self.assertEqual(validate_statement_layout(
            pos, [('set1', 'seq1'), ('set2', 'seq2')],
            sequence_spines=[['seq1', 'seq2']],
            private_expression_edges=[('input', 'set1')]), [])

    def test_rejects_spine_drift_and_wrong_row(self):
        pos = {'set1': (-192, 0), 'seq1': (0, 20),
               'set2': (-192, 224), 'seq2': (100, 100)}
        errors = validate_statement_layout(pos, [('set1', 'seq1'), ('set2', 'seq2')],
                                           sequence_spines=[['seq1', 'seq2']])
        self.assertIn('STATEMENT_SEQUENCE_ROW_MISMATCH:set1->seq1', errors)
        self.assertIn('SEQUENCE_SPINE_X_DRIFT:seq1->seq2', errors)

    def test_precreation_plan_gate_is_distinct_from_position_readback(self):
        # Nested While, two Sets and a pure terminal: every position can be
        # applied exactly while the inner Sequence spine is still wrong.
        plan = {'inner_get': (0, 0), 'inner_set1': (192, 0), 'inner_seq1': (384, 0),
                'inner_set2': (192, 224), 'inner_seq2': (576, 224),
                'outer_set': (768, 448), 'outer_seq': (960, 448),
                'pure_output': (1152, 448)}
        self.assertEqual(validate_position_application(plan, dict(plan)), [])
        errors = validate_layout_plan(
            plan, [('inner_set1', 'inner_seq1'), ('inner_set2', 'inner_seq2'),
                   ('outer_set', 'outer_seq')],
            sequence_spines=[['inner_seq1', 'inner_seq2'], ['outer_seq']],
            private_expression_edges=[('inner_get', 'inner_set1')])
        self.assertIn('SEQUENCE_SPINE_X_DRIFT:inner_seq1->inner_seq2', errors)
        plan['inner_seq2'] = (384, 224)
        self.assertEqual(validate_layout_plan(
            plan, [('inner_set1', 'inner_seq1'), ('inner_set2', 'inner_seq2'),
                   ('outer_set', 'outer_seq')],
            sequence_spines=[['inner_seq1', 'inner_seq2'], ['outer_seq']],
            private_expression_edges=[('inner_get', 'inner_set1')]), [])

    def test_precreation_plan_rejects_same_coordinate(self):
        self.assertIn('DUPLICATE_PLANNED_COORDINATE:a->b',
                      validate_layout_plan({'a': (0, 0), 'b': (0, 0)}, []))

    def test_inline_constants_inherit_consumer_band(self):
        bands, errors = infer_bands({'const': None, 'mul': None, 'set': 3},
                                    [('const', 'mul'), ('mul', 'set')])
        self.assertEqual(errors, [])
        self.assertEqual(bands, {'const': 3, 'mul': 3, 'set': 3})

    def test_shared_or_dangling_band_does_not_fall_back_to_zero(self):
        bands, errors = infer_bands({'const': None, 'set_a': 1, 'set_b': 2, 'orphan': None},
                                    [('const', 'set_a'), ('const', 'set_b')])
        self.assertNotIn('const', bands)
        self.assertIn('AMBIGUOUS_SHARED_BAND:const', errors)
        self.assertIn('UNRESOLVED_BAND:orphan', errors)

    def test_shared_band_waits_for_all_consumer_bands(self):
        bands, errors = infer_bands(
            {'const': None, 'use_a': 1, 'use_b': None, 'set_b': 2},
            [('const', 'use_a'), ('const', 'use_b'), ('use_b', 'set_b')])
        self.assertNotIn('const', bands)
        self.assertIn('AMBIGUOUS_SHARED_BAND:const', errors)

    def test_band_height_uses_busiest_depth_not_total_nodes(self):
        self.assertEqual(band_height_from_levels({'a': 0, 'b': 1, 'c': 1, 'd': 2}), 192)


if __name__ == '__main__':
    unittest.main()
