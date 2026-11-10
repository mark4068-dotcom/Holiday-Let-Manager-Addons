import tempfile
import unittest
from pathlib import Path
from recipe_dashboard.__main__ import make_handler
from recipe_dashboard.importer import normalize
from recipe_dashboard.store import Store


class ApiTests(unittest.TestCase):
    def test_search_pagination_and_invalid_parameters(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / 'recipes.sqlite3')
            store.replace([normalize({'uid':str(i),'name':f'Soup {i:03}','ingredients':'tomato basil'}) for i in range(60)], {})
            handler = object.__new__(make_handler(store))
            captured = []
            handler.json = lambda status, data: captured.append((status,data))
            handler.path = '/api/recipes?q=tomato,basil&limit=24&offset=24'
            handler.do_GET()
            status, result = captured.pop()
            self.assertEqual(status,200)
            self.assertEqual(result['total'],60)
            self.assertEqual(len(result['recipes']),24)
            self.assertEqual(result['recipes'][0]['name'],'Soup 024')
            handler.path = '/api/recipes?limit=bad'
            handler.do_GET()
            self.assertEqual(captured.pop()[0],400)
            self.assertIs(store.status()['favorites_available'],False)
