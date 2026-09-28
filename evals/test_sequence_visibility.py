import unittest

from scripts.runtime_semantics import state_read_transport


class SequenceVisibilityTests(unittest.TestCase):
    def test_unverified_topology_requires_repair_not_value_fallback(self):
        self.assertEqual(state_read_transport(scope_verified=False), 'get_sequence_topology_required')
        self.assertEqual(state_read_transport(scope_verified=True), 'get_sequence_topology_required')

    def test_verified_same_scope_read_can_use_ordered_get(self):
        self.assertEqual(state_read_transport(scope_verified=True,
                                              sequence_topology_verified=True),
                         'sequence_ordered_get')

    def test_requested_statement_get_does_not_silently_fall_back(self):
        self.assertEqual(state_read_transport(scope_verified=False,
                                              sequence_topology_verified=True),
                         'get_scope_probe_required')
        self.assertEqual(state_read_transport(scope_verified=True,
                                              sequence_topology_verified=True),
                         'sequence_ordered_get')


if __name__ == '__main__':
    unittest.main()
