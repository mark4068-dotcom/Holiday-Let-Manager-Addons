"""Private, versioned guide publication and usage service on HA's add-on network."""
import hashlib
import hmac
import json
import os
import math
from pathlib import Path
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote
from uuid import UUID

from google_client import GoogleReader
from guide import validate, atomic_json, TABS
from usage_stats import ACTIONS, HEADERS, StatsWriter, retention_cutoff

PUBLICATION_HEADERS=['schema_version','record_type','record_id','record_json','source_revision','published_at_utc']
TAB_KEYS={'Properties':'property_id','House Guide':'topic_id','Places':'place_id','Categories':'category_id','Files':'attachment_id','Place Categories':None}
FIELDS={
 'Properties':{'property_id','name','latitude','longitude','arrival_notes','status'},
 'House Guide':{'property_id','title','category','instructions','display_order','status','manual_url','video_url','additional_links','topic_id'},
 'Places':{'name','category_names','description','recommendation','address','favourite','status','custom_url','custom_link_label','discount','google_place_id','latitude','longitude','place_id'},
 'Files':{'title','drive_url','property_id','topic_id','place_id','display_order','status','attachment_id','drive_file_id'},
 'Categories':{'name','display_order','status','category_id'},
 'Place Categories':{'place_id','category_id','status'},
}
def typed_validate(tables):
    if set(tables)!=set(TAB_KEYS):raise ValueError('Unexpected table schema')
    validate(tables);formula_check(tables)
    for tab,rows in tables.items():
        for r in rows:
            if set(r)-FIELDS[tab]:raise ValueError('Unexpected record schema')
            for k,v in r.items():
                if k in ('latitude','longitude','display_order'):
                    if v not in ('',None) and (type(v) not in (int,float) or not math.isfinite(v)):
                        raise ValueError('Invalid numeric field')
                elif k=='favourite':
                    if v not in ('',None) and type(v) is not bool:raise ValueError('Invalid favourite')
                elif v is not None and not isinstance(v,str):raise ValueError('Invalid text field')
            for k,limit in [('latitude',90),('longitude',180)]:
                if r.get(k) not in ('',None) and not -limit<=r[k]<=limit:raise ValueError('Coordinate out of range')
            if len(json.dumps(r,ensure_ascii=False))>45000:raise ValueError('Record exceeds publication cell size')
    return tables
def now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def formula_check(value):
    if isinstance(value,str) and value in ('#REF!','#VALUE!','#N/A','#ERROR!','#DIV/0!','#NAME?','#NUM!','#SPILL!'):
        raise ValueError('Source formula error')
    if isinstance(value,dict):
        for item in value.values():formula_check(item)
    if isinstance(value,list):
        for item in value:formula_check(item)
def revision(tables):
    return hashlib.sha256(json.dumps(tables,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def publication_rows(tables,stamp):
    typed_validate(tables);rev=revision(tables);rows=[PUBLICATION_HEADERS]
    for tab,key in TAB_KEYS.items():
        for r in tables[tab]:
            rid=r[key] if key else r['place_id']+':'+r['category_id']
            rows.append(['1.0',tab,rid,json.dumps(r,ensure_ascii=False,separators=(',',':')),rev,stamp])
    return rows
def parse_publication(rows):
    if not rows or rows[0]!=PUBLICATION_HEADERS:raise ValueError('Unexpected publication schema')
    tables={tab:[] for tab in TAB_KEYS};revs=set();stamps=set();ids=set()
    for row in rows[1:]:
        if not any(row):continue
        if len(row)!=6 or row[0]!='1.0' or row[1] not in TAB_KEYS:raise ValueError('Malformed publication row')
        key=(row[1],row[2])
        if key in ids:raise ValueError('Duplicate publication ID')
        ids.add(key);record=json.loads(row[3]);field=TAB_KEYS[row[1]]
        expected=record[field] if field else record['place_id']+':'+record['category_id']
        if expected!=row[2]:raise ValueError('Publication reference mismatch')
        tables[row[1]].append(record);revs.add(row[4]);stamps.add(row[5])
    if len(revs)!=1 or len(stamps)!=1:raise ValueError('Mixed publication revisions')
    stamp=next(iter(stamps));date=datetime.fromisoformat(stamp.replace('Z','+00:00'))
    if date.tzinfo is None or date.timestamp()>time.time()+120:raise ValueError('Invalid publication timestamp')
    typed_validate(tables)
    if revision(tables)!=next(iter(revs)):raise ValueError('Publication checksum mismatch')
    return tables,stamp,next(iter(revs))

class Service:
    def __init__(self,options,reader,writer=None):
        self.options=options;self.reader=reader;self.writer=writer;self.lock=threading.RLock();self.write_lock=threading.Lock()
        self.root='https://sheets.googleapis.com/v4/spreadsheets/'+quote(options['spreadsheet_id'],safe='')+'/values/'
        self.payload=None;self.state={'last_source_refresh_at':None,'source_modified_at':None,'published_at':None,'last_successful_read_at':None,'last_successful_write_at':None,'error':'not_refreshed'}
    def rows(self,range_):
        return json.loads(self.reader.get(self.root+quote(range_,safe='')+'?valueRenderOption=UNFORMATTED_VALUE')).get('values',[])
    def refresh(self):
        try:
            source=self.reader.sheet(self.options['spreadsheet_id']);typed_validate(source)
            with self.lock:self.state['last_source_refresh_at']=now()
            source_rev=revision(source)
            rows=self.rows("'Guide Publication v1'!A1:F10000")
            try: tables,stamp,pub_rev=parse_publication(rows)
            except (ValueError,KeyError,TypeError):tables=None;pub_rev=None
            if source_rev!=pub_rev:
                if not self.writer or not self.options.get('publication_write_enabled'):raise ValueError('Publication needs refresh')
                stamp=now();new_rows=publication_rows(source,stamp)
                if len(new_rows)>10000:raise ValueError('Publication row limit exceeded')
                # One RAW update replaces the complete publication and clears stale tail rows.
                target=max(len(rows),len(new_rows));values=new_rows+[['']*6 for _ in range(target-len(new_rows))]
                self.writer.post(self.root+quote("'Guide Publication v1'!A1:F"+str(target),safe='')+'?valueInputOption=RAW',{'majorDimension':'ROWS','values':values},method='PUT')
                with self.lock:self.state['last_successful_write_at']=now()
                tables,stamp,pub_rev=parse_publication(self.rows("'Guide Publication v1'!A1:F10000"))
                if pub_rev!=source_rev:raise ValueError('Publication verification failed')
            with self.lock:
                self.payload={'schema_version':'1.0','tables':tables,'source_revision':pub_rev,'published_at':stamp,'source_verified_at':now()}
                self.state.update(last_source_refresh_at=now(),published_at=stamp,error=None)
        except Exception as exc:
            with self.lock:self.state['error']=type(exc).__name__
    def read(self):
        with self.lock:
            stamp=self.state['last_source_refresh_at']
            if self.state['error'] or not stamp or time.time()-datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp()>1800:
                raise ValueError('Guide publication unavailable')
            self.state['last_successful_read_at']=now();return self.payload
    def usage(self,body):
        if not self.writer or not self.options.get('usage_write_enabled'):raise ValueError('Writer disabled')
        if not isinstance(body,dict) or set(body)!={'schema_version','events'} or body['schema_version']!='1.0':raise ValueError('Invalid envelope')
        events=body['events']
        if not isinstance(events,list) or not 1<=len(events)<=100:raise ValueError('Invalid batch')
        kiosks=self.options.get('kiosk_properties',{})
        allowed={'event_id','timestamp','property','kiosk','action','section','item_id','item_name','search_text','result_count','category','favourites_only'}
        for e in events:
            if not isinstance(e,dict) or set(e)-allowed:raise ValueError('Invalid fields')
            UUID(e.get('event_id',''))
            if kiosks.get(e.get('kiosk'))!=e.get('property'):raise ValueError('Unknown kiosk/property')
            if e.get('action') not in ACTIONS or e.get('section') not in ('house','places','home'):raise ValueError('Invalid event')
            dt=datetime.fromisoformat(e.get('timestamp','').replace('Z','+00:00'))
            if dt.tzinfo is None or dt.timestamp()>time.time()+120:raise ValueError('Invalid timestamp')
            if dt<retention_cutoff():raise ValueError('Expired usage event')
            for k in ('item_id','item_name','search_text','category'):
                if k in e and (not isinstance(e[k],str) or len(e[k])>2000):raise ValueError('Invalid text')
            if 'result_count' in e and (type(e['result_count']) is not int or not 0<=e['result_count']<=100000):raise ValueError('Invalid count')
            if e['action']=='search' and (not e.get('search_text','').strip() or 'result_count' not in e):raise ValueError('Incomplete search')
            if 'favourites_only' in e and type(e['favourites_only']) is not bool:raise ValueError('Invalid filter')
        with self.write_lock:
            sink=StatsWriter(self.writer,self.options['spreadsheet_id']);sink.ensure_headers();known=sink.existing_event_ids()
            unique={e['event_id']:e for e in events if e['event_id'] not in known}
            try:sink.append(list(unique.values()))
            except Exception:
                if not set(unique).issubset(sink.existing_event_ids()):raise
            with self.lock:self.state['last_successful_write_at']=now()
        return {'acknowledged_ids':[e['event_id'] for e in events]}

    def retain_usage(self):
        if not self.writer:return
        try:
            with self.write_lock:removed=StatsWriter(self.writer,self.options['spreadsheet_id']).purge_expired()
            with self.lock:self.state.update(last_retention_at=now(),retention_removed=removed,retention_error=None)
        except Exception as exc:
            with self.lock:self.state['retention_error']=type(exc).__name__

def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,code,data,mime='application/json'):
            raw=json.dumps(data).encode() if not isinstance(data,bytes) else data
            self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
        def auth(self,write=False):
            key='usage_write_token' if write else 'api_token'
            return hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+service.options[key])
        def do_GET(self):
            if self.path=='/healthz':return self.send(200,{'service':'guide_sheets','writer_enabled':bool(service.options.get('usage_write_enabled'))})
            if not self.auth():return self.send(401,{'error':'unauthorized'})
            if self.path=='/api/v1/health':
                with service.lock:return self.send(200,{'schema_version':'1.0',**service.state})
            try:
                if self.path=='/api/v1/guide':return self.send(200,service.read())
                match=re.fullmatch(r'/api/v1/files/([A-Za-z0-9_-]+)/(metadata|content)',self.path)
                if match:
                    fid,kind=match.groups();tables=service.read()['tables']
                    if fid not in {f['drive_file_id'] for f in tables['Files'] if f['status']=='Published'}:return self.send(404,{'error':'unknown file'})
                    url='https://www.googleapis.com/drive/v3/files/'+fid
                    url+='?fields=id,mimeType,size,md5Checksum' if kind=='metadata' else '?alt=media'
                    return self.send(200,service.reader.get(url),'application/json' if kind=='metadata' else 'application/octet-stream')
            except Exception:return self.send(503,{'error':'guide_unavailable'})
            return self.send(404,{'error':'not_found'})
        def do_POST(self):
            if self.path!='/api/v1/usage':return self.send(404,{'error':'not_found'})
            if not self.auth(True):return self.send(401,{'error':'unauthorized'})
            if not service.options.get('usage_write_enabled'):return self.send(403,{'error':'writer_disabled'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1500000:return self.send(413,{'error':'batch_too_large'})
                result=service.usage(json.loads(self.rfile.read(length)))
            except (ValueError,KeyError,TypeError,AttributeError):return self.send(400,{'error':'invalid_batch'})
            except Exception:return self.send(503,{'error':'write_unavailable'})
            return self.send(200,result)
    return Handler

def main():
    options=json.loads(Path('/data/options.json').read_text())
    options['kiosk_properties']=json.loads(options.get('kiosk_properties_json','{}'))
    if len(options.get('api_token',''))<32:raise SystemExit('Configure the private read token')
    needs_writer=options.get('usage_write_enabled') or options.get('publication_write_enabled')
    if needs_writer and (len(options.get('usage_write_token',''))<32 or options['usage_write_token']==options['api_token']):raise SystemExit('Configure a separate write token')
    for option,path in [('google_service_account_json','/data/google-service-account.json'),('google_writer_service_account_json','/data/google-writer-service-account.json')]:
        if option.startswith('google_writer') and not needs_writer:continue
        try:
            credential=json.loads(options[option])
            if not credential.get('client_email') or not credential.get('private_key'):raise ValueError()
            atomic_json(path,credential)
        except Exception:raise SystemExit('Missing or invalid Google credentials; configure masked options')
    reader=GoogleReader('/data/google-service-account.json')
    writer=GoogleReader('/data/google-writer-service-account.json',scope='https://www.googleapis.com/auth/spreadsheets') if needs_writer else None
    service=Service(options,reader,writer)
    def refresh():
        while True:service.refresh();service.retain_usage();time.sleep(600)
    threading.Thread(target=refresh,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',8787),handler(service)).serve_forever()
if __name__=='__main__':main()
