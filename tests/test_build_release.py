import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_release', ROOT/'scripts/build_release.py')
m = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)


class ReleaseTests(unittest.TestCase):
    def test_archive_contains_manifest_only_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as base:
            output = Path(base)/'release.zip'
            result = m.build_release(ROOT, output)
            with ZipFile(output) as archive:
                names = [name.split('/', 1)[1] for name in archive.namelist()]
                self.assertEqual(names, json.loads((ROOT/'release-files.json').read_text(encoding='utf-8')))
                self.assertFalse(any(n.startswith(('local/', 'node_modules/')) or n.endswith('.mp4') for n in names))
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):m.build_release(ROOT, output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(result['public_files'], len(names))

    def test_manifest_rejects_private_paths_and_missing_files(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            for name in m.REQUIRED:
                file=root/name;file.parent.mkdir(parents=True, exist_ok=True);file.write_text('',encoding='utf-8')
            for bad in ('local/user/profile.json', '../outside.txt', 'scripts/missing.py'):
                (root/'release-files.json').write_text(json.dumps(sorted(m.REQUIRED)+[bad]),encoding='utf-8')
                with self.subTest(path=bad),self.assertRaises(ValueError):m.public_files(root)


if __name__ == '__main__':unittest.main()
