"""Read Paprika ZIP exports without extracting archive paths to disk."""
import base64
import gzip
import hashlib
import io
import json
import unicodedata
import zipfile
import zlib
from pathlib import Path

MAX_ARCHIVE = 256 * 1024 * 1024
MAX_RECIPE = 16 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
TEXT_FIELDS = ('name', 'ingredients', 'directions', 'notes', 'description', 'servings',
               'prep_time', 'cook_time', 'total_time', 'source', 'source_url', 'nutritional_info', 'difficulty')


def search_text(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


def normalize(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('name'), str) or not raw['name'].strip():
        raise ValueError('A recipe has no valid name.')
    recipe = {k: str(raw.get(k) or '') for k in TEXT_FIELDS}
    recipe['name'] = recipe['name'].strip()
    recipe['uid'] = str(raw.get('uid') or hashlib.sha256(recipe['name'].encode()).hexdigest())
    categories = raw.get('categories') or []
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise ValueError('Invalid recipe categories.')
    recipe['categories'] = categories
    recipe['favorite'] = raw.get('on_favorites') in (True, 1, '1', 'yes', 'true')
    recipe['favorite_available'] = 'on_favorites' in raw
    try:
        recipe['rating'] = max(0, min(5, int(raw.get('rating') or 0)))
    except (ValueError, TypeError):
        recipe['rating'] = 0
    recipe['photo'] = None
    photo = raw.get('photo_data')
    if photo:
        try:
            if isinstance(photo, str) and photo.startswith('data:'):
                photo = photo.split(',', 1)[1]
            decoded = base64.b64decode(photo, validate=True)
            kind = ('image/jpeg' if decoded.startswith(b'\xff\xd8\xff') else
                    'image/png' if decoded.startswith(b'\x89PNG\r\n\x1a\n') else
                    'image/webp' if decoded[:4] == b'RIFF' and decoded[8:12] == b'WEBP' else None)
            if kind:
                recipe['photo'] = 'data:' + kind + ';base64,' + base64.b64encode(decoded).decode()
        except (ValueError, TypeError):
            pass
    return recipe


def read_export(path):
    path = Path(path)
    if path.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Export exceeds the 256 MB limit.')
    recipes, total = [], 0
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith('.paprikarecipe')]
        if not members or len(members) > 20000:
            raise ValueError('Not a supported Paprika recipe export.')
        for member in members:
            if member.file_size > MAX_RECIPE:
                raise ValueError('A compressed recipe exceeds the size limit.')
            packed = archive.read(member)
            if packed.startswith(b'\x1f\x8b'):
                with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
                    content = stream.read(MAX_RECIPE + 1)
            else:
                content = packed
            total += len(content)
            if len(content) > MAX_RECIPE or total > MAX_TOTAL:
                raise ValueError('Expanded export exceeds the size limit.')
            raw = json.loads(content)
            if not isinstance(raw, dict):
                raise ValueError('A recipe file is not a JSON object.')
            if raw.get('in_trash') or raw.get('deleted'):
                continue
            recipes.append(normalize(raw))
    return recipes


class ExportSource:
    """A source supplies full snapshots to Store, independent of the web UI."""
    def __init__(self, folder, store):
        self.folder, self.store = Path(folder), store
        self.seen, self.pending, self.failed = None, None, None

    def poll(self):
        files = list(self.folder.glob('*.paprikarecipes'))
        if not files:
            return
        latest = max(files, key=lambda p: (p.stat().st_mtime_ns, p.name))
        stat = latest.stat()
        signature = (str(latest), stat.st_mtime_ns, stat.st_size)
        if signature == self.seen or signature == self.failed:
            return
        # Two identical observations avoid ingesting an export while it is being written.
        if signature != self.pending:
            self.pending = signature
            return
        try:
            recipes = read_export(latest)
            after = latest.stat()
            if (after.st_mtime_ns, after.st_size) != signature[1:]:
                return
            self.store.replace(recipes, {'type': 'export', 'file': latest.name})
            self.seen, self.failed = signature, None
        except (OSError, ValueError, zipfile.BadZipFile, EOFError, RuntimeError, zlib.error) as exc:
            self.failed = signature
            self.store.error(f'Could not import {latest.name}: {exc}')
