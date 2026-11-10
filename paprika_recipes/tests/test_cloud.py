import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from recipe_dashboard.cloud import Client, CloudError, CloudSource
from recipe_dashboard.importer import normalize
from recipe_dashboard.store import Store


class FakeClient:
    def __init__(self):
        self.items = {'a': {'uid': 'a', 'name': 'Soup', 'categories': ['cat'], 'on_favorites': True}}
        self.hashes = {'a': '1'}
        self.calls = []
        self.fail = None
        self.retry_after = 0
        self.token = None
        self.race = False
        self.index_reads = 0
        self.category_name = "Dinner"
        self.category_uid = "cat"

    def get(self, path):
        self.calls.append(path)
        if path == self.fail:
            raise CloudError('Download failed.')
        if path == 'recipes':
            self.index_reads += 1
            return [{'uid': k, 'hash': v + ('race' if self.race and self.index_reads % 2 == 0 else '')} for k, v in self.hashes.items()]
        if path == 'categories':
            return [{'uid': self.category_uid, 'name': self.category_name}]
        return dict(self.items[path.split('/')[-1]])

    def photo(self, url):
        self.calls.append('photo')
        return b'\xff\xd8\xffphoto'


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'recipes.sqlite3')
        self.store.replace([normalize({'uid': 'export', 'name': 'Export recipe'})], {'type': 'export'})
        self.client = FakeClient()
        self.source = CloudSource(self.store, 'example@example.test', 'secret', client=self.client)

    def tearDown(self):
        self.temp.cleanup()

    def test_full_incremental_deletions_and_favourites(self):
        self.source.sync()
        recipe = self.store.recipe('a')
        self.assertEqual(recipe['categories'], ['Dinner'])
        self.assertTrue(recipe['favorite'])
        self.assertTrue(self.store.status()['favorites_available'])
        self.assertIsNone(self.store.recipe('export'))
        self.client.calls.clear()
        # Recreate source to prove the hash cache survives service restarts.
        source = CloudSource(self.store, 'example@example.test', 'secret', client=self.client)
        source.sync()
        self.assertNotIn('recipe/a', self.client.calls)
        self.client.items['b'] = {'uid': 'b', 'name': 'Toast'}
        self.client.hashes = {'b': '2'}
        source.sync()
        self.assertIsNone(self.store.recipe('a'))
        self.assertEqual(self.store.status()['count'], 1)

    def test_category_rename_and_recipe_category_move(self):
        self.source.sync()
        self.client.calls.clear()
        self.client.category_name = 'Evening meals'
        self.source.sync()
        self.assertEqual(self.store.recipe('a')['categories'], ['Evening meals'])
        self.assertNotIn('recipe/a', self.client.calls)
        self.client.items['a']['categories'] = ['Breakfast']
        self.client.hashes['a'] = 'changed-category'
        self.source.sync()
        self.assertEqual(self.store.recipe('a')['categories'], ['Breakfast'])

    def test_unresolved_category_ids_are_hidden_but_raw_references_retained(self):
        orphan = '12345678-1234-1234-1234-123456789abc'
        self.client.items['a']['categories'] = ['CAT', orphan, '12345678-12345678-12345678-123456789', orphan + '-13993-0000000000000000', 'Breakfast', 'CAT']
        self.source.sync()
        recipe = self.store.recipe('a')
        self.assertEqual(recipe['categories'], ['Dinner', 'Breakfast'])
        self.assertIn(orphan, recipe['_cloud_categories'])
        self.client.category_name = 'Evening meals'
        self.source.sync()
        self.assertEqual(self.store.recipe('a')['categories'], ['Evening meals', 'Breakfast'])
        self.assertEqual(self.source.interval, 6 * 60 * 60)
        known_compound = orphan + '-13993-0000000000000000'
        self.client.category_uid = known_compound
        self.client.items['a']['categories'] = [known_compound]
        self.client.hashes['a'] = 'compound-category-change'
        self.source.sync()
        self.assertEqual(self.store.recipe('a')['categories'], ['Evening meals'])

    def test_failed_partial_download_retains_complete_snapshot(self):
        self.client.hashes['b'] = '2'
        self.client.fail = 'recipe/b'
        self.source.poll()
        self.assertEqual(self.store.status()['source']['type'], 'export')
        self.assertIsNotNone(self.store.recipe('export'))
        self.assertIsNone(self.store.recipe('a'))
        self.assertEqual(self.store.status()['sync']['phase'], 'error')

    def test_changed_index_and_empty_collection_retain_previous(self):
        self.client.race = True
        with self.assertRaises(CloudError):
            self.source.sync()
        self.client.hashes = {}
        with self.assertRaises(CloudError):
            self.source.sync()
        self.assertIsNotNone(self.store.recipe('export'))

    def test_account_switch_does_not_reuse_another_accounts_cache(self):
        self.source.sync()
        self.client.calls.clear()
        CloudSource(self.store, 'other@example.test', 'secret', client=self.client).sync()
        self.assertIn('recipe/a', self.client.calls)
        self.assertNotIn('account', json.dumps(self.store.status()))

    def test_photo_reused_only_with_matching_hash(self):
        self.client.items['a'].update(photo_url='https://uploads.paprikaapp.com/example.jpg', photo_hash='p1')
        self.source.sync()
        self.assertTrue(self.store.recipe('a')['photo'])
        self.client.calls.clear()
        self.client.hashes['a'] = '2'
        self.source.sync()
        self.assertNotIn('photo', self.client.calls)

    def test_unexpected_error_is_redacted(self):
        with patch.object(self.source, 'sync', side_effect=ValueError('PASSWORD SECRET RESPONSE')):
            self.source.poll()
        self.assertNotIn('SECRET', json.dumps(self.store.status()))

    def test_photo_host_and_credentials_are_isolated(self):
        client = Client('private@example.test', 'secret')
        client.token = 'private-token'
        for url in ['http://uploads.paprikaapp.com/a', 'https://evil.test/a', 'https://uploads.paprikaapp.com:444/a', 'https://user@uploads.paprikaapp.com/a']:
            with self.assertRaises(CloudError):
                client.photo(url)
        with patch.object(client, 'request', return_value=b'image') as request:
            client.photo('https://uploads.paprikaapp.com/a')
            self.assertEqual(request.call_args.kwargs, {'photo': True})

    def test_paprika_s3_photo_uses_https_without_authentication(self):
        client = Client('private@example.test', 'secret')
        client.token = 'private-token'
        with patch.object(client, 'request', return_value=b'image') as request:
            client.photo('http://s3.amazonaws.com/uploads.paprikaapp.com/photos/example.jpg?x=1')
            request.assert_called_once_with('https://s3.amazonaws.com/uploads.paprikaapp.com/photos/example.jpg?x=1', photo=True)
        for url in ['http://s3.amazonaws.com:80/uploads.paprikaapp.com/a', 'https://s3.amazonaws.com/other-bucket/a', 'https://s3.amazonaws.com.evil.test/uploads.paprikaapp.com/a', 'http://user@s3.amazonaws.com/uploads.paprikaapp.com/a', 'https://s3.amazonaws.com/uploads.paprikaapp.com/../other/a', 'https://s3.amazonaws.com/uploads.paprikaapp.com/%2e%2e/other/a']:
            with self.assertRaises(CloudError):
                client.photo(url)

    def test_network_errors_never_expose_remote_response(self):
        client = Client('private@example.test', 'secret')
        with patch.object(client.opener, 'open', side_effect=HTTPError('https://example.test', 429, 'SECRET', {'Retry-After': '7200'}, None)):
            with self.assertRaises(CloudError) as result:
                client.get('recipes')
        self.assertNotIn('SECRET', str(result.exception))
        self.assertEqual(client.retry_after, 7200)

    def test_login_and_read_endpoint_methods(self):
        client = Client('private@example.test', 'secret')
        with patch.object(client, 'request', side_effect=[b'{"result":{"token":"test-token"}}', b'{"result":[]}']) as request:
            self.assertEqual(client.get('recipes'), [])
        login, read = request.call_args_list
        self.assertEqual(login.args[0], 'https://paprikaapp.com/api/v1/account/login')
        self.assertIn(b'password=secret', login.args[1])
        self.assertEqual(read.args[0], 'https://www.paprikaapp.com/api/v2/sync/recipes')
        self.assertTrue(read.kwargs['authenticated'])
