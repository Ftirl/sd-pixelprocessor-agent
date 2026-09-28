import unittest

from scripts.graph_refactor import (
    HighNodeEvidence, SplitCandidate, SplitReview, constant_fold, node_budget_status,
    projected_caller_nodes,
)
from scripts.graph_author_score import score


class GraphRefactorTests(unittest.TestCase):
    def test_fold(self):
        self.assertEqual(constant_fold("mul", "x", 1), "x")

    def test_score(self):
        self.assertEqual(score({"overlap": 0}), 100)

    def test_revised_single_graph_budget_boundaries(self):
        reviewed = SplitReview(1048, (), 'No safe typed boundary after IR review')
        evidence = HighNodeEvidence('readback:graph-1', 'cook:case-1', 'layout:graph-1')
        high_review = SplitReview(1500, (), 'No safe typed boundary after IR review')
        verified = SplitReview(1500, (), 'No safe typed boundary after IR review', evidence)
        self.assertEqual(node_budget_status(399)[0], 'PASS')
        self.assertEqual(node_budget_status(400)[0], 'BLOCKED')
        self.assertEqual(node_budget_status(1048, split_review=reviewed)[0], 'PASS')
        self.assertEqual(node_budget_status(1199, split_review=SplitReview(
            1199, (), 'No safe typed boundary'))[0], 'PASS')
        self.assertEqual(node_budget_status(1200, split_review=high_review)[0], 'BLOCKED')
        self.assertEqual(node_budget_status(1200, split_review=SplitReview(
            1200, (), 'No safe typed boundary', HighNodeEvidence('readback:1', '', 'layout:1')))[1],
            'HIGH_NODE_READBACK_COOK_LAYOUT_REQUIRED')
        self.assertEqual(node_budget_status(1200, split_review=verified)[0], 'WARN')
        self.assertEqual(node_budget_status(1500, split_review=verified)[0], 'WARN')
        self.assertEqual(node_budget_status(1501, split_review=verified)[0], 'FAIL')
        self.assertEqual(node_budget_status(1501, split_review=SplitReview(
            1501, (), 'No safe typed boundary', evidence), over_budget_exception=True)[0], 'WARN')

    def test_safe_split_must_be_applied_or_excepted(self):
        untyped = SplitCandidate('waterH', 900, 9, 217, True, 'retain',
                                 'STRUCTURAL_EXCEPTION: layout only')
        self.assertEqual(node_budget_status(1048, split_review=SplitReview(
            1300, (untyped,), 'Candidate assessed'))[1], 'INCOMPLETE_TYPED_SPLIT_BOUNDARY')
        candidate = SplitCandidate('waterH', 900, 9, 217, True, 'retain', 'Not extracted',
                                   ('caller/waterH#1',), ('float2',), ('float1',))
        self.assertEqual(projected_caller_nodes(1300, candidate), 409)
        review = SplitReview(1300, (candidate,), 'Candidate assessed')
        self.assertEqual(node_budget_status(1048, split_review=review)[1],
                         'SAFE_SPLIT_RETAINED_WITHOUT_EXCEPTION')
        excepted = SplitCandidate('waterH', 900, 9, 217, True, 'retain',
                                  'STRUCTURAL_EXCEPTION: user requested layout only',
                                  ('caller/waterH#1',), ('float2',), ('float1',))
        self.assertEqual(node_budget_status(1048, split_review=SplitReview(
            1300, (excepted,), 'Out of structural-change scope'))[0], 'PASS')

    def test_extraction_requires_numeric_and_callsite_verification(self):
        def result(applied, numeric, callsite, count=409):
            candidate = SplitCandidate('waterH', 900, 9, 217, True, 'extract',
                                       'Repeated typed helper',
                                       ('caller/waterH#1',), ('float2',), ('float1',), applied,
                                       'oracle:waterH' if numeric else '',
                                       'i24:call-1' if callsite else '')
            return node_budget_status(count, split_review=SplitReview(
                1300, (candidate,), 'Selected and measured'))

        self.assertEqual(result(False, False, False)[1], 'SPLIT_SELECTED_NOT_APPLIED')
        self.assertEqual(result(True, False, False)[1], 'SPLIT_NOT_NUMERICALLY_VERIFIED')
        self.assertEqual(result(True, True, True)[0], 'PASS')
        self.assertEqual(result(True, True, True, 1300)[1], 'SPLIT_DID_NOT_REDUCE_CALLER')

    def test_new_function_is_reviewed_independently(self):
        parent = SplitCandidate('helper', 900, 9, 1200, True, 'extract',
                                'Repeated helper', ('caller/helper#1',), ('float2',),
                                ('float1',), True, 'oracle:helper', 'i24:call-1')
        self.assertEqual(node_budget_status(409, split_review=SplitReview(
            1300, (parent,), 'Caller reduced'))[0], 'PASS')
        self.assertEqual(node_budget_status(parent.function_nodes)[1],
                         'FUNCTION_SPLIT_REVIEW_REQUIRED')


if __name__ == '__main__':
    unittest.main()
