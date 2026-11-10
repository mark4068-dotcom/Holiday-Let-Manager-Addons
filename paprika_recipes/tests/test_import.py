import gzip
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from recipe_dashboard.importer import ExportSource, read_export, search_text
from recipe_dashboard.store import Store


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'recipes.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, recipes, name='recipes.paprikarecipes'):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            for i, recipe in enumerate(recipes):
                archive.writestr(f'{i}.paprikarecipe', gzip.compress(json.dumps(recipe).encode()))
        return path

    def test_snapshot_updates_and_removes_without_duplicates(self):
        old = self.export([{'uid': '1', 'name': 'Old'}, {'uid': '2', 'name': 'Removed'}])
        self.store.replace(read_export(old), {'type': 'export'})
        new = self.export([{'uid': '1', 'name': 'Changed', 'ingredients': 'Crème fraîche'}])
        self.store.replace(read_export(new), {'type': 'export'})
        self.assertEqual(self.store.status()['count'], 1)
        self.assertEqual(self.store.recipe('1')['name'], 'Changed')
        self.assertIsNone(self.store.recipe('2'))
        self.assertEqual(search_text('Crème fraîche'), 'creme fraiche')

    def test_watcher_waits_and_retains_last_good_snapshot(self):
        path = self.export([{'uid': '1', 'name': 'Soup'}])
        source = ExportSource(self.root, self.store)
        source.poll()
        self.assertEqual(self.store.status()['count'], 0)
        source.poll()
        self.assertEqual(self.store.status()['count'], 1)
        path.write_bytes(b'partial export')
        source.poll()
        source.poll()
        self.assertEqual(self.store.status()['count'], 1)
        self.assertIn('Could not import', self.store.status()['error'])

    def test_duplicate_ids_cannot_erase_collection(self):
        self.store.replace([{'uid': 'safe', 'name': 'Safe'}], {})
        with self.assertRaises(ValueError):
            self.store.replace([{'uid': '1'}, {'uid': '1'}], {})
        self.assertEqual(self.store.recipe('safe')['name'], 'Safe')

    def test_archive_paths_are_never_extracted(self):
        path = self.root / 'unsafe.paprikarecipes'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('../escape.paprikarecipe', gzip.compress(b'{"name":"Safe data"}'))
        self.assertEqual(read_export(path)[0]['name'], 'Safe data')
        self.assertFalse((self.root.parent / 'escape.paprikarecipe').exists())

    def test_empty_and_invalid_exports_are_rejected(self):
        with self.assertRaises(ValueError):
            read_export(self.export([]))
        with self.assertRaises(ValueError):
            read_export(self.export([{'ingredients': 'missing name'}]))
        with self.assertRaises(ValueError):
            self.store.replace([], {})


if __name__ == '__main__':
    unittest.main()
