"""Guide-only usage outbox; follows HLM Sheets Service's RAW/idempotent append pattern.

No booking lookups, browser identifiers, addresses, cookies or HTTP access logs.
Search text is intentionally recorded verbatim as requested by the owner.
"""
import json
import os
from pathlib import Path
import sqlite3
import threading
import calendar
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import UUID

HEADERS=['Event ID','Requested at (UTC)','Property','Kiosk','Action','Section',
         'Item reference','Item name','Search text','Result count','Category','Favourites only']
ACTIONS={'page_view','section_open','topic_open','place_open','document_open',
         'photos_shown','link_tap','qr_shown','category_filter','favourites_filter','search'}

def retention_cutoff(at=None):
    at=at or datetime.now(timezone.utc)
    return at.replace(year=at.year-1,day=min(at.day,calendar.monthrange(at.year-1,at.month)[1]))

def event_time(value):
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.tzinfo is None: raise ValueError('Usage timestamp needs timezone')
    return stamp

class UsageStats:
    def __init__(self, folder, property_id, kiosk_ids, enabled=False, preview=False, kiosk_properties=None):
        self.enabled=enabled and not preview
        self.property_id=property_id
        self.kiosk_ids=set(kiosk_ids)
        self.kiosk_properties=kiosk_properties or {k:property_id for k in kiosk_ids}
        if self.enabled and (not self.kiosk_ids or any(not k or len(k)>80 for k in self.kiosk_ids)):
            raise ValueError('Statistics need configured kiosk names')
        self.path=Path(folder)/'usage-outbox.sqlite3'
        self.upload_lock=threading.Lock()
        self.last_upload_error=None
        if self.enabled:
            with self.db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL, uploaded INTEGER NOT NULL DEFAULT 0)')
            os.chmod(self.path,0o600)
        if not preview: self.prune()

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=15)
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:yield db
        finally:db.close()

    def prune(self,at=None):
        if not self.path.exists(): return 0
        cutoff=retention_cutoff(at)
        with self.db() as db:
            expired=[(id_,) for id_,payload in db.execute('SELECT id,payload FROM events')
                     if event_time(json.loads(payload)['timestamp'])<cutoff]
            db.executemany('DELETE FROM events WHERE id=?',expired)
        return len(expired)

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
        record={**event,'property':self.kiosk_properties[event['kiosk']],'timestamp':datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')}
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
            try:
                self.prune()
                events=self.pending()
                if not events: return 0
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

    def purge_expired(self,at=None):
        self.ensure_headers()
        url=self.root+quote("'Stats'!A2:L",safe='')+'?valueRenderOption=UNFORMATTED_VALUE'
        rows=json.loads(self.client.get(url)).get('values',[])
        cutoff=retention_cutoff(at);kept=[];removed=0
        for row in rows:
            if not any(x!='' for x in row): continue
            if len(row)<2 or len(row)>12: raise ValueError('Invalid Stats record')
            UUID(row[0]);stamp=event_time(row[1])
            if stamp<cutoff: removed+=1
            else: kept.append(row+['']*(12-len(row)))
        if not removed: return 0
        values=kept+[['']*12 for _ in range(len(rows)-len(kept))]
        root=self.root.removesuffix('/values/')
        sheets=json.loads(self.client.get(root+'?fields=sheets(properties(sheetId,title))'))['sheets']
        sheet_id=next(s['properties']['sheetId'] for s in sheets if s['properties']['title']=='Stats')
        def cell(value):
            if value=='':return {}
            kind='boolValue' if type(value) is bool else 'numberValue' if type(value) in (int,float) else 'stringValue'
            return {'userEnteredValue':{kind:value}}
        # Explicit literal types preserve formula-looking searches. Empty cells
        # must be cleared, not written as empty strings (which COUNTA counts).
        body={'requests':[{'updateCells':{'range':{'sheetId':sheet_id,'startRowIndex':1,'endRowIndex':len(rows)+1,'startColumnIndex':0,'endColumnIndex':12},
              'rows':[{'values':[cell(v) for v in row]} for row in values],'fields':'userEnteredValue'}}]}
        try: self.client.post(root+':batchUpdate',body)
        except Exception:
            if self._retained_rows(url)!=kept: raise
        if self._retained_rows(url)!=kept: raise ValueError('Retention verification failed')
        return removed

    def _retained_rows(self,url):
        rows=json.loads(self.client.get(url)).get('values',[])
        return [r+['']*(12-len(r)) for r in rows if any(x!='' for x in r)]

    def append(self,events):
        if not events: return
        rows=[[e['event_id'],e['timestamp'],e['property'],e['kiosk'],e['action'],e['section'],
               e.get('item_id',''),e.get('item_name',''),e.get('search_text',''),
               e.get('result_count',''),e.get('category',''),e.get('favourites_only','')] for e in events]
        existing=json.loads(self.client.get(self.root+quote("'Stats'!A2:L",safe='')+'?valueRenderOption=UNFORMATTED_VALUE')).get('values',[])
        for row in existing:
            if any(v!='' for v in row):UUID(row[0])
        start=len(existing)+2
        root=self.root.removesuffix('/values/')
        sheets=json.loads(self.client.get(root+'?fields=sheets(properties(sheetId,title,gridProperties(rowCount)))'))['sheets']
        grid=next(s['properties'] for s in sheets if s['properties']['title']=='Stats')
        end=start+len(rows)-1
        if end>grid['gridProperties']['rowCount']:
            self.client.post(root+':batchUpdate',{'requests':[{'appendDimension':{'sheetId':grid['sheetId'],'dimension':'ROWS','length':max(1000,end-grid['gridProperties']['rowCount'])}}]})
        # Server write_lock serialises allocation. Explicit A:L avoids Sheets'
        # logical-table detection shifting an append into B:M after blank rows.
        self.client.post(self.root+quote("'Stats'!A"+str(start)+':L'+str(end),safe='')+'?valueInputOption=RAW',
                         {'majorDimension':'ROWS','values':rows},method='PUT')
