import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class GitExclusionTests(unittest.TestCase):
    def test_builder_excludes_git_metadata_but_preserves_gitignore(self):
        spec = importlib.util.spec_from_file_location('manifest_fixture', ROOT/'scripts/build_manifest.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'.git').mkdir()
            (root/'.git/config').write_text('local metadata')
            (root/'.gitignore').write_text('__pycache__/')
            (root/'VERSION').write_text('2.5.0')
            module.ROOT = root
            self.assertEqual({x['path'] for x in module.collect()}, {'.gitignore', 'VERSION'})

    def test_release_checkout_contains_no_git_manifest_entries(self):
        import json
        manifest = json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
        self.assertFalse(any(r['path'].startswith('.git/') for r in manifest['files']))
