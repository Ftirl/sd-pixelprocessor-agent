from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import runtime_safety as rs


class FakeResource:
    def __init__(self, ident): self.ident = ident
    def getIdentifier(self): return self.ident


class FakePackage:
    def __init__(self, path, ids): self.path, self.ids = path, ids
    def getFilePath(self): return self.path
    def getChildrenResources(self, recursive): return [FakeResource(x) for x in self.ids]




class FakeGraph:
    def __init__(self, ident): self.ident = ident
    def getIdentifier(self): return self.ident
    def getNodes(self): return []


class FakeMutablePackage:
    def __init__(self, path, graphs): self.path, self.graphs = path, list(graphs)
    def getFilePath(self): return self.path
    def getChildrenResources(self, recursive): return list(self.graphs)


class FakePackageManager:
    def __init__(self, packages): self.packages = packages
    def getUserPackages(self): return list(self.packages)

class RuntimeSafetyTests(unittest.TestCase):
    def test_owned_tempdir_only(self):
        with tempfile.TemporaryDirectory() as base:
            owned = rs.create_probe_run_dir(base)
            self.assertTrue(rs.is_owned_probe_dir(owned))
            rs.remove_owned_probe_dir(owned)
            self.assertFalse(Path(owned).exists())
            foreign = Path(base) / 'foreign'
            foreign.mkdir()
            with self.assertRaises(RuntimeError):
                rs.remove_owned_probe_dir(str(foreign))
            self.assertTrue(foreign.exists())

    def test_user_shadow_is_ignored(self):
        user = FakePackage('/work/functions.sbs', ['fmod'])
        adobe = FakePackage('/opt/Adobe/resources/packages/functions.sbs', ['fmod', 'sign'])
        pk, res, ident = rs.resolve_unique_library_resource([user, adobe], 'fmod')
        self.assertIs(pk, adobe)
        self.assertEqual(ident, 'fmod')

    def test_duplicate_builtin_match_fails_closed(self):
        adobe = FakePackage('/opt/Adobe/resources/packages/functions.sbs', ['fmod', 'Functions/Math/fmod'])
        with self.assertRaises(RuntimeError):
            rs.resolve_unique_library_resource([adobe], 'fmod')

    def test_exact_override_does_not_accept_same_basename(self):
        a = FakePackage('/A/resources/packages/functions.sbs', ['fmod'])
        b = FakePackage('/B/resources/packages/functions.sbs', ['fmod'])
        pk, _, _ = rs.resolve_unique_library_resource([a, b], 'fmod', '/B/resources/packages/functions.sbs')
        self.assertIs(pk, b)

    def test_preexisting_package_change_is_detected(self):
        pkg = FakeMutablePackage('/work/user.sbs', [FakeGraph('A')])
        mgr = FakePackageManager([pkg])
        before = rs.snapshot_user_packages(mgr)
        rs.assert_preexisting_packages_unchanged(before, mgr)
        pkg.graphs.append(FakeGraph('B'))
        with self.assertRaises(RuntimeError):
            rs.assert_preexisting_packages_unchanged(before, mgr)


if __name__ == '__main__':
    unittest.main()
