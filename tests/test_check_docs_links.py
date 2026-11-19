import tempfile
import unittest
from pathlib import Path
from scripts.check_docs_links import check

class LinkPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
    def scan(self, text):
        (self.root / 'README.md').write_text(text, encoding='utf-8')
        return check(self.root, ['README.md'])
    def test_targets_and_reference_definitions(self):
        (self.root / 'a file.md').write_text('# Here\n', encoding='utf-8')
        n, errors = self.scan('[ok](<a file.md#here>) [bad](missing.md)\n\n[ref][r]\n\n[r]: <a file.md>\n')
        self.assertEqual(n, 3); self.assertEqual(len(errors), 1); self.assertIn('missing.md', errors[0])
    def test_fragments_collisions_and_explicit_id(self):
        n, errors = self.scan('# Same\n# Same-1\n# Same\n<a id="custom"></a>\n[yes](#same-2) [id](#custom) [no](#missing)\n')
        self.assertEqual(n, 3); self.assertEqual(len(errors), 1); self.assertIn('#missing', errors[0])
    def test_reference_escaping_and_fences(self):
        n, errors = self.scan('[bad][missing]\n\n\\[literal][missing]\n\n```md\n[example][missing]\n```\n')
        self.assertEqual(n, 0); self.assertEqual(len(errors), 1); self.assertIn('[bad][missing]', errors[0])
    def test_local_images(self):
        (self.root / 'ok.png').touch()
        n, errors = self.scan('![ok](ok.png) ![bad](missing.png)')
        self.assertEqual(n, 2); self.assertEqual(len(errors), 1); self.assertIn('missing.png', errors[0])
    def test_external_and_root_relative_urls_are_skipped(self):
        n, errors = self.scan('[web](https://example.com/x) [root](/outside)')
        self.assertEqual(n, 0)
        self.assertEqual(errors, [])

    def test_outside_repository_is_rejected(self):
        n, errors = self.scan('[outside](../outside.md)')
        self.assertEqual(n, 1)
        self.assertEqual(len(errors), 1)
        self.assertIn('out-of-repository', errors[0])

    def test_missing_entry(self):
        n, errors = check(self.root, ['missing.md'])
        self.assertEqual(n, 0); self.assertEqual(len(errors), 1)

if __name__ == '__main__': unittest.main()
