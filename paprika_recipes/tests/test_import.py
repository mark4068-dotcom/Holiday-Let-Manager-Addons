import gzip
import json
import sqlite3
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

    def test_failed_database_publish_rolls_back_recipes_photos_and_metadata(self):
        photo = 'data:image/jpeg;base64,/9j/cGhvdG8='
        self.store.replace([{'uid': 'safe', 'name': 'Existing', 'photo': photo}], {'type': 'export'})
        before = self.store.status()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.store.replace([{'uid': 'new', 'name': 'Incomplete', 'photo': {'invalid': 'image'}}],
                               {'type': 'cloud'}, cloud_state={'account': 'test'})
        self.assertEqual(self.store.status(), before)
        self.assertEqual(self.store.recipe('safe')['photo'], photo)
        self.assertIsNone(self.store.recipe('new'))
        self.assertEqual(self.store.cloud_state(), {})

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

    def test_search_records_exclude_photo_payloads(self):
        photo = 'data:image/jpeg;base64,' + 'A' * 100000
        self.store.replace([{'uid': '1', 'name': 'Soup', 'photo': photo}], {})
        self.assertIs(self.store.recipes()[0]['photo'], True)
        self.assertEqual(self.store.recipe('1')['photo'], photo)
        self.store.replace([{'uid': '1', 'name': 'Soup', 'photo': None}], {})
        self.assertIsNone(self.store.recipe('1')['photo'])


if __name__ == '__main__':
    unittest.main()
