"""Guide-only usage outbox; follows HLM Sheets Service's RAW/idempotent append pattern.

No booking lookups, browser identifiers, addresses, cookies or HTTP access logs.
Search text is intentionally recorded verbatim as requested by the owner.
"""
import json
import os
from pathlib import Path
import sqlite3
import threading
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import UUID

HEADERS=['Event ID','Requested at (UTC)','Property','Kiosk','Action','Section',
         'Item reference','Item name','Search text','Result count','Category','Favourites only']
ACTIONS={'page_view','section_open','topic_open','place_open','document_open',
         'photos_shown','link_tap','qr_shown','category_filter','favourites_filter','search'}

class UsageStats:
    def __init__(self, folder, property_id, kiosk_ids, enabled=False, preview=False):
        self.enabled=enabled and not preview
        self.property_id=property_id
        self.kiosk_ids=set(kiosk_ids)
        if self.enabled and (not self.kiosk_ids or any(not k or len(k)>80 for k in self.kiosk_ids)):
            raise ValueError('Statistics need configured kiosk names')
        self.path=Path(folder)/'usage-outbox.sqlite3'
        self.upload_lock=threading.Lock()
        self.last_upload_error=None
        if self.enabled:
            with self.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, uploaded INTEGER NOT NULL DEFAULT 0)')
            os.chmod(self.path,0o600)

    def db(self): return sqlite3.connect(self.path,timeout=15)

    def record(self, event):
        if not self.enabled: return False
        allowed={'event_id','kiosk','action','section','item_id','item_name','search_text',
                 'result_count','category','favourites_only'}
        if not isinstance(event,dict) or set(event)-allowed: raise ValueError('Invalid event fields')
        UUID(event.get('event_id',''))
        if event.get('kiosk') not in self.kiosk_ids: raise ValueError('Unknown kiosk')
        if event.get('action') not in ACTIONS or event.get('section') not in ('house','places','home'):
            raise ValueError('Invalid action or section')
        for key in ('item_id','item_name','search_text','category'):
            if key in event and (not isinstance(event[key],str) or len(event[key])>2000):
                raise ValueError('Invalid event text')
        if 'result_count' in event and (isinstance(event['result_count'],bool) or not isinstance(event['result_count'],int) or not 0<=event['result_count']<=100000):
            raise ValueError('Invalid result count')
        if event['action']=='search':
            if not event.get('search_text','').strip(): raise ValueError('Empty search')
            count=event.get('result_count')
            if isinstance(count,bool) or not isinstance(count,int) or count<0: raise ValueError('Invalid result count')
        if 'favourites_only' in event and not isinstance(event['favourites_only'],bool): raise ValueError('Invalid filter')
        record={**event,'property':self.property_id,'timestamp':datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')}
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO events(id,payload) VALUES (?,?)',
                       (event['event_id'],json.dumps(record,ensure_ascii=False)))
        return True

    def pending(self):
        if not self.enabled: return []
        with self.db() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT payload FROM events WHERE uploaded=0 ORDER BY rowid LIMIT 100')]

    def flush(self,writer):
        if not self.enabled: return 0
        with self.upload_lock:
            events=self.pending()
            if not events: return 0
            try:
                writer.ensure_headers()
                known=writer.existing_event_ids()
                unseen=[e for e in events if e['event_id'] not in known]
                if unseen:
                    try: writer.append(unseen)
                    except Exception:
                        # HLM recovery rule: a committed append can lose its response.
                        after=writer.existing_event_ids()
                        if not {e['event_id'] for e in unseen}.issubset(after): raise
                with self.db() as db:
                    db.executemany('UPDATE events SET uploaded=1 WHERE id=?',[(e['event_id'],) for e in events])
                    # Only pending events and a bounded dedup ledger are needed locally.
                    db.execute('DELETE FROM events WHERE uploaded=1 AND rowid NOT IN (SELECT rowid FROM events ORDER BY rowid DESC LIMIT 10000)')
                self.last_upload_error=None
                return len(events)
            except Exception as exc:
                self.last_upload_error=type(exc).__name__
                return 0

class StatsWriter:
    """Fixed Stats destination, separate write-scoped OAuth client, server-side only."""
    def __init__(self,client,spreadsheet_id):
        self.client=client
        self.root='https://sheets.googleapis.com/v4/spreadsheets/'+quote(spreadsheet_id,safe='')+'/values/'

    def ensure_headers(self):
        result=json.loads(self.client.get(self.root+quote("'Stats'!A1:L1",safe='')))
        if result.get('values') != [HEADERS]: raise ValueError('Stats headers do not match')

    def existing_event_ids(self):
        result=json.loads(self.client.get(self.root+quote("'Stats'!A2:A",safe='')))
        return {r[0] for r in result.get('values',[]) if r}

    def append(self,events):
        if not events: return
        rows=[[e['event_id'],e['timestamp'],e['property'],e['kiosk'],e['action'],e['section'],
               e.get('item_id',''),e.get('item_name',''),e.get('search_text',''),
               e.get('result_count',''),e.get('category',''),e.get('favourites_only','')] for e in events]
        # RAW is essential: guest searches must never become spreadsheet formulas.
        # Append within A:L without shifting summary cells in adjacent columns.
        self.client.post(self.root+quote("'Stats'!A:L",safe='')+':append?valueInputOption=RAW&insertDataOption=OVERWRITE',
                         {'majorDimension':'ROWS','values':rows})
