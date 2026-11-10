import argparse
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from .importer import ExportSource, read_export, search_text
from .store import Store

STATIC = Path(__file__).parent / 'static'


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, content, content_type='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(content)

        def json(self, status, value):
            self.send(status, json.dumps(value).encode())

        def do_GET(self):
            url = urlsplit(self.path)
            path = unquote(url.path)
            if path == '/api/status':
                return self.json(200, store.status())
            if path == '/api/recipes':
                query = parse_qs(url.query)
                terms = search_text(query.get('q', [''])[0]).replace(',', ' ').split()
                category = query.get('category', [''])[0]
                favorite = query.get('favorite', [''])[0] == '1'
                all_recipes = store.recipes()
                categories = sorted({c for r in all_recipes for c in r['categories']}, key=str.casefold)
                results = []
                for recipe in all_recipes:
                    haystack = search_text(' '.join(str(recipe.get(k, '')) for k in ('name', 'ingredients', 'notes', 'directions', 'source')) + ' ' + ' '.join(recipe['categories']))
                    if all(t in haystack for t in terms) and (not category or category in recipe['categories']) and (not favorite or recipe['favorite']):
                        results.append({k: recipe[k] for k in ('uid', 'name', 'categories', 'favorite', 'rating', 'prep_time', 'cook_time', 'total_time') } | {'has_photo': bool(recipe['photo'])})
                results.sort(key=lambda r: r['name'].casefold())
                total = len(results)
                if 'limit' in query:
                    try:
                        limit = max(1, min(100, int(query['limit'][0])))
                        offset = max(0, int(query.get('offset', ['0'])[0]))
                    except ValueError:
                        return self.json(400, {'error': 'Invalid pagination'})
                    results = results[offset:offset + limit]
                return self.json(200, dict(recipes=results, categories=categories, total=total))
            if path.startswith('/api/recipe/'):
                recipe = store.recipe(path[len('/api/recipe/'):])
                return self.json(200 if recipe else 404, recipe or {'error': 'Recipe not found'})
            if path.startswith('/api/photo/'):
                recipe = store.recipe(path[len('/api/photo/'):])
                if recipe and recipe['photo']:
                    import base64
                    header, data = recipe['photo'].split(',', 1)
                    return self.send(200, base64.b64decode(data), header[5:].split(';')[0])
                return self.json(404, {'error': 'Photo not found'})
            assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path in assets:
                file, kind = assets[path]
                return self.send(200, (STATIC / file).read_bytes(), kind)
            self.json(404, {'error': 'Not found'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description='Local Paprika recipe dashboard')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8124, type=int)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--imports', type=Path, default=Path('imports'))
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--import-file', type=Path, help='Import a full collection and exit')
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    args.imports.mkdir(parents=True, exist_ok=True)
    store = Store(args.data / 'recipes.sqlite3')
    if args.import_file:
        store.replace(read_export(args.import_file), {'type': 'export', 'file': args.import_file.name})
        print(f"Imported {store.status()['count']} recipes")
        return
    source = ExportSource(args.imports, store)
    stop = threading.Event()
    def watch():
        while not stop.is_set():
            try:
                source.poll()
            except Exception:
                logging.exception('Export watcher failed; retrying on next check')
            stop.wait(max(1, args.interval))
    threading.Thread(target=watch, daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(f'Recipe dashboard: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
