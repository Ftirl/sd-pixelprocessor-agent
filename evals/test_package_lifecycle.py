import unittest

from core.package_lifecycle import PackageRegistry


class PackageLifecycleTests(unittest.TestCase):
    def test_cleanup_requires_successful_host_action(self):
        registry = PackageRegistry()
        registry.register("t1")
        self.assertEqual(registry.cleanup_temporary(), [])
        self.assertEqual(registry.items["t1"]["status"], "created")
        self.assertEqual(registry.cleanup_temporary(lambda _: None), ["t1"])
        self.assertEqual(registry.items["t1"]["status"], "cleaned")

    def test_failed_cleanup_keeps_residue_registered(self):
        registry = PackageRegistry()
        registry.register("scratch")
        def fail(_):
            raise RuntimeError("Designer refused unload")
        with self.assertRaises(RuntimeError):
            registry.cleanup_temporary(fail)
        self.assertEqual(registry.items["scratch"]["status"], "created")


if __name__ == '__main__':
    unittest.main()
