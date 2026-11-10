"""Transactional recipe snapshots. Future cloud sources publish through replace()."""
import json
import sqlite3
from datetime import datetime, timezone


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS recipes (uid TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS photos (uid TEXT PRIMARY KEY, data TEXT NOT NULL);
            ''')
            # Upgrade early snapshots once, so searches never read the photo payloads.
            for uid, body in db.execute('SELECT uid,body FROM recipes').fetchall():
                recipe = json.loads(body)
                if isinstance(recipe.get('photo'), str):
                    db.execute('INSERT OR REPLACE INTO photos VALUES (?,?)', (uid, recipe['photo']))
                    recipe['photo'] = True
                    db.execute('UPDATE recipes SET body=? WHERE uid=?', (json.dumps(recipe), uid))

    def connect(self):
        return sqlite3.connect(self.path)

    def status(self):
        with self.connect() as db:
            result = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
            result['count'] = db.execute('SELECT count(*) FROM recipes').fetchone()[0]
            return result

    def error(self, message):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('error', json.dumps(message)))

    def replace(self, recipes, source):
        """Publish a validated, complete snapshot atomically; never merge partial exports."""
        ids = [r['uid'] for r in recipes]
        if not recipes or len(set(ids)) != len(ids):
            raise ValueError('Export is empty or contains duplicate recipe IDs; previous collection retained.')
        with self.connect() as db:
            db.execute('DELETE FROM recipes')
            db.execute('DELETE FROM photos')
            db.executemany('INSERT INTO recipes VALUES (?,?)', [(r['uid'], json.dumps(dict(r, photo=bool(r.get('photo'))))) for r in recipes])
            db.executemany('INSERT INTO photos VALUES (?,?)', [(r['uid'], r['photo']) for r in recipes if r.get('photo')])
            meta = dict(source=source, refreshed=datetime.now(timezone.utc).isoformat(), error=None,
                        favorites_available=any(r.get('favorite_available', False) for r in recipes))
            db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)', [(k, json.dumps(v)) for k, v in meta.items()])

    def recipes(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT body FROM recipes')]

    def recipe(self, uid):
        with self.connect() as db:
            row = db.execute('SELECT body FROM recipes WHERE uid=?', (uid,)).fetchone()
            if not row:
                return None
            recipe = json.loads(row[0])
            photo = db.execute('SELECT data FROM photos WHERE uid=?', (uid,)).fetchone()
            recipe['photo'] = photo[0] if photo else None
            return recipe
