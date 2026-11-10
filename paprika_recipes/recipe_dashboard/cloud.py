"""Read-only Paprika Cloud adapter. No recipe write endpoint is implemented."""
import base64
import gzip
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from .importer import normalize

MAX_RESPONSE = 16 * 1024 * 1024
MAX_PHOTO = 2 * 1024 * 1024


class CloudError(Exception):
    """Messages are deliberately safe to display; never include response bodies."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, email, password):
        self.email, self.password, self.token = email, password, None
        self.opener = build_opener(NoRedirect())
        self.retry_after = 0

    def request(self, url, data=None, authenticated=False, photo=False):
        headers = {'User-Agent': 'HLM-Paprika-Recipes/0.3.0', 'Accept-Encoding': 'gzip'}
        if authenticated:
            headers['Authorization'] = 'Bearer ' + self.token
        if data is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            with self.opener.open(Request(url, data=data, headers=headers), timeout=30) as response:
                limit = MAX_PHOTO if photo else MAX_RESPONSE
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise CloudError('Paprika response exceeded the size limit.')
                if response.headers.get('Content-Encoding', '').lower() == 'gzip' or body.startswith(b'\x1f\x8b'):
                    with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
                        body = stream.read(limit + 1)
                    if len(body) > limit:
                        raise CloudError('Paprika response exceeded the size limit.')
                return body
        except HTTPError as exc:
            exc.close()
            if exc.code == 401:
                raise CloudError('Paprika sign-in expired or credentials were rejected.') from None
            if exc.code == 429:
                try:
                    self.retry_after = min(86400, max(60, int(exc.headers.get('Retry-After', '3600'))))
                except ValueError:
                    self.retry_after = 3600
                raise CloudError('Paprika asked us to wait before retrying.') from None
            raise CloudError('Paprika request failed. The previous collection is retained.') from None
        except (URLError, OSError, EOFError):
            raise CloudError('Could not reach Paprika securely. Will retry automatically.') from None

    @staticmethod
    def result(body):
        try:
            value = json.loads(body)
            if not isinstance(value, dict) or value.get('error') or 'result' not in value:
                raise ValueError()
            return value['result']
        except (ValueError, TypeError):
            raise CloudError('Paprika returned an unsupported response.') from None

    def login(self):
        result = self.result(self.request('https://paprikaapp.com/api/v1/account/login',
                                         urlencode({'email': self.email, 'password': self.password}).encode()))
        if not isinstance(result, dict) or not isinstance(result.get('token'), str) or not result['token']:
            raise CloudError('Paprika sign-in failed. Check the add-on credentials.')
        self.token = result['token']

    def get(self, path):
        if not self.token:
            self.login()
        return self.result(self.request('https://www.paprikaapp.com/api/v2/sync/' + path,
                                        authenticated=True))

    def photo(self, url):
        parsed = urlsplit(url)
        # Do not send account credentials to photo hosts or follow redirects.
        if parsed.scheme != 'https' or parsed.hostname != 'uploads.paprikaapp.com' or parsed.port not in (None, 443) or parsed.username or parsed.password:
            raise CloudError('Paprika supplied an unsupported photo location.')
        return self.request(url, photo=True)


def index_map(value):
    if not isinstance(value, list) or not value or len(value) > 20000:
        raise CloudError('Paprika recipe list is empty or unsupported; previous collection retained.')
    result = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get('uid'), str) or not item['uid'] or not isinstance(item.get('hash'), str) or not item['hash'] or item['uid'] in result:
            raise CloudError('Paprika recipe list contains invalid or duplicate IDs.')
        result[item['uid']] = item['hash']
    return result


class CloudSource:
    def __init__(self, store, email, password, minutes=60, client=None):
        self.store = store
        self.client = client or Client(email, password)
        self.account = hashlib.sha256(email.strip().casefold().encode()).hexdigest()
        self.interval = max(15, min(1440, int(minutes))) * 60
        self.due = 0

    def progress(self, phase, **values):
        self.store.sync_status(dict(mode='cloud', phase=phase, **values))

    def poll(self):
        if time.monotonic() < self.due:
            return
        try:
            self.progress('checking')
            self.sync()
            self.progress('idle', checked=datetime.now(timezone.utc).isoformat())
        except Exception as exc:
            # Never log exception text from remote responses or credential-bearing objects.
            self.store.error(str(exc) if isinstance(exc, CloudError) else 'Cloud refresh failed; previous collection retained.')
            self.progress('error')
            self.client.token = None
        finally:
            self.due = time.monotonic() + max(self.interval, self.client.retry_after)
            self.client.retry_after = 0

    def sync(self):
        index = index_map(self.client.get('recipes'))
        categories = self.client.get('categories')
        if not isinstance(categories, list):
            raise CloudError('Paprika category list is unsupported.')
        names = {}
        for category in categories:
            if not isinstance(category, dict) or not isinstance(category.get('uid'), str) or not isinstance(category.get('name'), str):
                raise CloudError('Paprika category data is unsupported.')
            names[category['uid']] = category['name']
        previous = self.store.cloud_state()
        reusable = previous.get('account') == self.account and self.store.status().get('source', {}).get('type') == 'cloud'
        recipes = []
        total_bytes = 0
        for position, (uid, digest) in enumerate(index.items(), 1):
            old = self.store.recipe(uid) if reusable else None
            if old and old.get('_cloud_hash') == digest:
                recipe = old
            else:
                raw = self.client.get('recipe/' + quote(uid, safe=''))
                if not isinstance(raw, dict) or raw.get('uid') != uid:
                    raise CloudError('Paprika returned a mismatched recipe ID.')
                if raw.get('in_trash') or raw.get('deleted'):
                    continue
                recipe = normalize(raw)
                recipe['_cloud_categories'] = recipe['categories'][:]
                recipe['_cloud_hash'] = digest
                recipe['_cloud_photo_hash'] = raw.get('photo_hash')
                if not recipe['photo'] and raw.get('photo_url'):
                    if old and old.get('_cloud_photo_hash') and old['_cloud_photo_hash'] == raw.get('photo_hash') and old.get('photo'):
                        recipe['photo'] = old['photo']
                    else:
                        picture = self.client.photo(raw['photo_url'])
                        image = normalize(dict(uid=uid, name=recipe['name'], photo_data=base64.b64encode(picture).decode()))['photo']
                        if not image:
                            raise CloudError('Paprika supplied an unsupported recipe photo.')
                        recipe['photo'] = image
            recipe['categories'] = [names.get(c, c) for c in recipe['_cloud_categories']]
            total_bytes += len(json.dumps(recipe).encode())
            if total_bytes > 512 * 1024 * 1024:
                raise CloudError('Cloud collection exceeds the 512 MB limit.')
            recipes.append(recipe)
            if position == 1 or position % 25 == 0 or position == len(index):
                self.progress('downloading', completed=position, total=len(index))
        # A concurrent Paprika edit must not publish a mixture of snapshots.
        if index_map(self.client.get('recipes')) != index or self.client.get('categories') != categories:
            raise CloudError('Paprika changed during refresh. Will retry the complete collection later.')
        self.store.replace(recipes, {'type': 'cloud', 'name': 'Paprika Cloud'}, cloud_state={'account': self.account})
