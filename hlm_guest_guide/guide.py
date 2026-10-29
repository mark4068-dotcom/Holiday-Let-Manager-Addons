"""Local HLM guest guide. No access to Home Assistant controls or credentials."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import ipaddress
import json
import logging
import math
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

import qrcode
import qrcode.image.svg
from sheet_schema import normalize_tables
from usage_stats import UsageStats
from private_client import PrivateReader, PrivateStatsWriter

LOG=logging.getLogger('hlm-guide')
ROOT=Path(__file__).resolve().parent
TABS=['Properties','House Guide','Places','Categories','Files']
DEFAULT_SHEET='1TwFhxp1U1AiuIaoCRJ9RmROQQncbm_ctdncKwUaJOck'

def read_json(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default

def atomic_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    with tmp.open('w') as stream:
        os.chmod(tmp,0o600); json.dump(value,stream,ensure_ascii=False)
        stream.flush(); os.fsync(stream.fileno())
    tmp.replace(path)

def rows_to_records(rows):
    if not rows: return []
    headers=rows[0]
    if len(headers)!=len(set(headers)): raise ValueError('Duplicate column headers')
    return [dict(zip(headers,row+['']*(len(headers)-len(row)))) for row in rows[1:] if any(v!='' for v in row)]

def distance_miles(origin, destination):
    try:
        if any(p.get(k) in ('',None) for p in (origin,destination) for k in ('latitude','longitude')): return None
        lat1,lon1,lat2,lon2=[float(p[k]) for p in (origin,destination) for k in ('latitude','longitude')]
        if not all(math.isfinite(v) for v in (lat1,lon1,lat2,lon2)): return None
        if not (-90<=lat1<=90 and -90<=lat2<=90 and -180<=lon1<=180 and -180<=lon2<=180): return None
        p1,p2=map(math.radians,(lat1,lat2)); d1=math.radians(lat2-lat1); d2=math.radians(lon2-lon1)
        a=math.sin(d1/2)**2+math.cos(p1)*math.cos(p2)*math.sin(d2/2)**2
        return 3958.7613*2*math.asin(math.sqrt(min(1,max(0,a))))
    except (ValueError,TypeError): return None

def allowed(row, preview=False):
    return row.get('status')=='Published' or (preview and row.get('status')=='Draft')

def maps_url(place):
    query=place.get('address')
    if not query and distance_miles(place,place) is not None:
        query=str(place['latitude'])+','+str(place['longitude'])
    if not query and place.get('google_place_id'): query=place.get('name','')
    if not query: return ''
    params={'api':'1','query':query}
    if place.get('google_place_id'): params['query_place_id']=place['google_place_id']
    return 'https://www.google.com/maps/search/?'+urlencode(params)

class InstructionLinks(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.href=None; self.label=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href',''); self.href=href if urlparse(href).scheme in ('http','https') else None; self.label=[]
    def handle_data(self,data):
        if self.href: self.label.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:
            self.links.append({'url':self.href,'label':''.join(self.label).strip() or urlparse(self.href).hostname}); self.href=None

def validate(data):
    required={'Properties':['property_id','name','status'],'House Guide':['topic_id','property_id','title','instructions','category','status'],'Places':['place_id','name','status'],'Categories':['category_id','name','status'],'Place Categories':['place_id','category_id','status'],'Files':['attachment_id','drive_file_id','status']}
    for tab,keys in required.items():
        if tab not in data or not isinstance(data[tab],list): raise ValueError('Missing table: '+tab)
        for row in data[tab]:
            if not all(k in row for k in keys): raise ValueError('Missing columns: '+tab)
            if row.get('status') not in ('Draft','Published','Archived'): raise ValueError('Invalid publication status: '+tab)
    for tab,key in [('Properties','property_id'),('House Guide','topic_id'),('Places','place_id'),('Categories','category_id'),('Files','attachment_id')]:
        ids=[x[key] for x in data[tab]]
        if any(not x for x in ids) or len(ids)!=len(set(ids)): raise ValueError('Empty or duplicate IDs: '+tab)
    props={x['property_id'] for x in data['Properties']}; topics={x['topic_id']:x for x in data['House Guide']}
    places={x['place_id'] for x in data['Places']}; cats={x['category_id'] for x in data['Categories']}
    for x in data['House Guide']:
        if x['property_id'] not in props: raise ValueError('Unknown topic property')
        if x['status']=='Published' and (not x['title'] or not x['instructions'] or not x['category']): raise ValueError('Published topic is incomplete')
    for x in data['Place Categories']:
        if x['place_id'] not in places or x['category_id'] not in cats: raise ValueError('Unknown category relationship')
    for x in data['Files']:
        if x.get('topic_id'):
            if x['topic_id'] not in topics or x.get('property_id')!=topics[x['topic_id']]['property_id']: raise ValueError('Invalid attachment owner')
        elif x.get('place_id'):
            if x['place_id'] not in places: raise ValueError('Invalid attachment place')
        elif x.get('property_id') not in props: raise ValueError('Missing attachment owner')
        if x['status']=='Published' and not re.fullmatch(r'[A-Za-z0-9_-]+',x['drive_file_id']): raise ValueError('Published attachment needs a Drive file ID')
    return data


class Guide:
    def __init__(self,folder,property_id,preview=False):
        self.folder=Path(folder); self.folder.mkdir(parents=True,exist_ok=True); self.preview=preview; self.property_id=property_id
        self.lock=threading.RLock(); self.data=None; self.last_error=None
        self.reader=None; self.google_key=''; self.places_limit=100; self.places_counts=read_json(self.folder/'places-usage.json',{})
        self.terms_url=''; self.privacy_url=''
        self.stats=None; self.kiosk_id=''
        snapshot=read_json(self.folder/'snapshot.json')
        if snapshot: self.data=validate(snapshot)
    def sync(self,sheet_id):
        try:
            data=validate(self.reader.sheet(sheet_id)); files=self.folder/'media'; files.mkdir(exist_ok=True)
            previous={x['drive_file_id']:x for x in (self.data or {}).get('Files',[])}
            for f in data['Files']:
                if f.get('status')!='Published': continue
                fid=f['drive_file_id']; path=files/fid
                metadata=json.loads(self.reader.get('https://www.googleapis.com/drive/v3/files/'+quote(fid,safe='')+'?fields=id,mimeType,size,md5Checksum'))
                old=previous.get(fid,{})
                if metadata.get('md5Checksum') and old.get('_drive_md5')==metadata['md5Checksum'] and (files/old.get('_local_name','missing')).is_file():
                    f.update({k:old[k] for k in ('_local_name','_drive_md5','_download_sha256')}); f['mime_type']=metadata['mimeType']; continue
                content=self.reader.get('https://www.googleapis.com/drive/v3/files/'+quote(fid,safe='')+'?alt=media')
                if len(content)!=int(metadata['size']): raise ValueError('Incomplete attachment download')
                if metadata.get('md5Checksum') and hashlib.md5(content).hexdigest()!=metadata['md5Checksum']: raise ValueError('Attachment download checksum mismatch')
                if metadata.get('mimeType')=='application/pdf' and not content.startswith(b'%PDF-'): raise ValueError('Invalid PDF attachment')
                digest=hashlib.sha256(content).hexdigest(); versioned=files/(fid+'-'+digest)
                if not versioned.exists(): versioned.write_bytes(content)
                f.update(_local_name=versioned.name,_drive_md5=metadata.get('md5Checksum',''),_download_sha256=digest,mime_type=metadata.get('mimeType','application/octet-stream'))
            data['_synced_at']=datetime.now(timezone.utc).isoformat()
            atomic_json(self.folder/'snapshot.json',data)
            with self.lock: self.data=data; self.last_error=None
            LOG.info('Guide sync completed')
        except Exception as exc:
            self.last_error=type(exc).__name__; LOG.warning('Guide sync failed (%s); keeping previous snapshot',type(exc).__name__)
    def view(self,property_id=None):
        with self.lock:
            if self.data is None: return None
            d=self.data; pid=property_id if self.preview and property_id else self.property_id
            prop=next((x for x in d['Properties'] if x['property_id']==pid and allowed(x,self.preview)),None)
            if not prop: return {'preview':self.preview,'property':None,'topics':[],'places':[],'categories':[],'files':[],'synced_at':d.get('_synced_at')}
            topics=[{k:v for k,v in x.items() if k not in ('instructions_html','source_property_url')} for x in d['House Guide'] if x['property_id']==pid and allowed(x,self.preview)]
            source_topics={x['topic_id']:x for x in d['House Guide']}
            for topic in topics:
                links=InstructionLinks(); links.feed(source_topics[topic['topic_id']].get('instructions_html','')); topic['instruction_links']=links.links
                for line in str(topic.get('additional_links','')).splitlines():
                    label, separator, url=line.partition(' | ')
                    if not separator: url=label; label='More information'
                    if urlparse(url.strip()).scheme in ('https','http'):
                        topic['instruction_links'].append({'label':label.strip(),'url':url.strip()})
            categories=[x for x in d['Categories'] if allowed(x,self.preview)]; category_ids={x['category_id'] for x in categories}
            relations={}
            for x in d['Place Categories']:
                if allowed(x,self.preview) and x['category_id'] in category_ids: relations.setdefault(x['place_id'],[]).append(x['category_id'])
            places=[]
            for x in d['Places']:
                if not allowed(x,self.preview): continue
                place={k:v for k,v in x.items() if k not in ('source_location_url','source_image_url','migration_note')}
                place.update(categories=relations.get(x['place_id'],[]),distance=distance_miles(prop,x),maps_url=maps_url(x))
                places.append(place)
            places.sort(key=lambda x:(x['distance'] is None,x['distance'] if x['distance'] is not None else 0,x['name'].casefold()))
            tids={x['topic_id'] for x in topics}; pids={x['place_id'] for x in places}
            files=[{k:x.get(k,'') for k in ('attachment_id','drive_file_id','title','property_id','topic_id','place_id','display_order','mime_type')} for x in d['Files'] if allowed(x,self.preview) and ((x.get('topic_id') in tids) or (x.get('place_id') in pids) or (x.get('property_id')==pid and not x.get('topic_id')))]
            return {'preview':self.preview,'stats_enabled':bool(self.stats and self.stats.enabled),'kiosk_id':self.kiosk_id,'property':{**prop,'maps_url':maps_url(prop)},'properties':[{'property_id':x['property_id'],'name':x['name']} for x in d['Properties']] if self.preview else [],'topics':sorted(topics,key=lambda x:float(x.get('display_order') or 0)),'places':places,'categories':sorted(categories,key=lambda x:float(x.get('display_order') or 0)),'files':files,'synced_at':d.get('_synced_at'),'sync_issue':bool(self.last_error),'google_available':bool(self.google_key and self.terms_url and self.privacy_url),'terms_url':self.terms_url,'privacy_url':self.privacy_url}
    def media(self,fid,property_id=None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+',fid): return None
        if fid not in {x['drive_file_id'] for x in (self.view(property_id) or {}).get('files',[])}: return None
        f=next((x for x in (self.data or {}).get('Files',[]) if x.get('drive_file_id')==fid and allowed(x,self.preview)),None)
        if not f: return None
        local=self.folder/'media'/f.get('_local_name',fid)
        return (local,f) if local.is_file() else None
    def place_details(self,pid):
        view=self.view(); place=next((p for p in (view or {}).get('places',[]) if p['place_id']==pid),None)
        if not place or not place.get('google_place_id'): return 404,{'error':'This location has no verified Google Place ID yet.'}
        if not self.google_key or not self.terms_url or not self.privacy_url: return 503,{'error':'Live Google information is not configured.'}
        with self.lock:
            day=datetime.now(timezone.utc).strftime('%Y-%m-%d'); used=self.places_counts.get(day,0)
            if used>=self.places_limit: return 429,{'error':'The daily live-information limit has been reached.'}
            self.places_counts={day:used+1}; atomic_json(self.folder/'places-usage.json',self.places_counts)
        request=Request('https://places.googleapis.com/v1/places/'+quote(place['google_place_id'],safe=''),headers={'X-Goog-Api-Key':self.google_key,'X-Goog-FieldMask':'displayName,currentOpeningHours,websiteUri,nationalPhoneNumber,businessStatus,googleMapsUri,attributions'})
        try:
            with urlopen(request,timeout=15) as response: return 200,json.load(response)
        except Exception: return 503,{'error':'Live information is temporarily unavailable.'}

def handler(guide):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,mime='application/json'):
            if isinstance(body,dict): body=json.dumps(body,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' https://maps.gstatic.com; script-src 'self'; style-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'")
            self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            parsed=urlparse(self.path); path=parsed.path; query=parse_qs(parsed.query)
            if path=='/api/guide':
                result=guide.view(query.get('property',[''])[0]); return self.send(200 if result else 503,result or {'error':'No guide has been downloaded yet.'})
            if path=='/api/health': return self.send(200,{'snapshot_available':guide.data is not None,'preview':guide.preview,'last_sync_failed':bool(guide.last_error)})
            if path.startswith('/api/places/'):
                code,data=guide.place_details(path.rsplit('/',1)[-1]); return self.send(code,data)
            if path=='/api/qr':
                view=guide.view(query.get('property',[''])[0]); pid=query.get('place',[''])[0]
                place=next((x for x in (view or {}).get('places',[]) if x['place_id']==pid),None) if pid else (view or {}).get('property')
                url=maps_url(place) if place else ''
                if not url: return self.send(404,{'error':'Location unavailable'})
                qr=qrcode.make(url,image_factory=qrcode.image.svg.SvgPathImage,box_size=8,border=4); stream=io.BytesIO(); qr.save(stream)
                return self.send(200,stream.getvalue(),'image/svg+xml')
            if path.startswith('/media/'):
                found=guide.media(path.rsplit('/',1)[-1],query.get('property',[''])[0])
                if not found: return self.send(404,{'error':'File not downloaded or not published'})
                file,meta=found; mime=meta.get('mime_type') or ('application/pdf' if meta['attachment_id'].endswith('_manual') else mimetypes.guess_type(meta.get('title',''))[0]) or 'application/octet-stream'
                if mime not in ('application/pdf','image/png','image/jpeg','image/webp','image/avif','image/gif'): mime='application/octet-stream'
                return self.send(200,file.read_bytes(),mime)
            static={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/pdf-viewer.html':'pdf-viewer.html','/pdf-viewer.js':'pdf-viewer.js','/pdf-viewer.css':'pdf-viewer.css','/vendor/pdf.mjs':'vendor/pdf.mjs','/vendor/pdf.worker.mjs':'vendor/pdf.worker.mjs'}
            if path in static:
                target=ROOT/'web'/static[path]; mime=mimetypes.guess_type(str(target))[0] or 'application/javascript'; return self.send(200,target.read_bytes(),mime+'; charset=utf-8')
            return self.send(404,{'error':'Not found'})
        def do_POST(self):
            if self.path!='/api/usage': return self.send(404,{'error':'Not found'})
            if not guide.stats or not guide.stats.enabled: return self.send(200,{'recorded':False})
            origin=self.headers.get('Origin','')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'): return self.send(403,{'error':'Origin not allowed'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.send(415,{'error':'JSON required'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16000: return self.send(413,{'error':'Event too large'})
                event=json.loads(self.rfile.read(length))
                recorded=guide.stats.record(event)
            except (ValueError,TypeError,AttributeError): return self.send(400,{'error':'Invalid usage event'})
            except Exception: return self.send(503,{'error':'Usage storage unavailable'})
            return self.send(200,{'recorded':recorded})
    return Handler

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data',default=os.getenv('GUIDE_DATA','./data')); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8099); parser.add_argument('--property',default='crossjack'); parser.add_argument('--preview',action='store_true'); parser.add_argument('--credentials'); parser.add_argument('--sheet',default=DEFAULT_SHEET); parser.add_argument('--interval',type=int,default=600)
    parser.add_argument('--lan-preview',action='store_true',help='Allow the draft preview on an explicitly selected private LAN address')
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO)
    if args.preview and args.host not in ('127.0.0.1','localhost','::1'):
        try: lan=ipaddress.ip_address(args.host)
        except ValueError: parser.error('LAN preview needs an explicit private IP address')
        if not args.lan_preview or not lan.is_private or lan.is_unspecified:
            parser.error('Draft preview requires loopback or --lan-preview with a private LAN address')
    options=read_json('/data/options.json',{})
    guide=Guide(args.data,options.get('property_id',args.property),args.preview)
    guide.google_key=options.get('google_places_api_key') or os.getenv('GOOGLE_PLACES_API_KEY','')
    guide.terms_url=options.get('terms_url',''); guide.privacy_url=options.get('privacy_url','')
    guide.places_limit=int(options.get('places_daily_limit',100))
    guide.kiosk_id=options.get('kiosk_id','')
    kiosks=options.get('allowed_kiosk_ids',[]) or [guide.kiosk_id]
    guide.stats=UsageStats(args.data,guide.property_id,kiosks,enabled=options.get('usage_stats_enabled',False),preview=args.preview)
    if guide.stats.enabled:
        service_url=options.get('sheets_service_url','')
        read_token=options.get('sheets_read_token','')
        write_token=options.get('sheets_write_token','')
        if min(len(read_token),len(write_token))<32 or read_token==write_token:
            parser.error('Configure separate private-service read/write tokens')
        writer=PrivateStatsWriter(PrivateReader(service_url,read_token),write_token)
        def export_stats():
            while True:
                guide.stats.flush(writer)
                if guide.stats.last_upload_error: LOG.warning('Statistics upload unavailable; pending events retained (%s)',guide.stats.last_upload_error)
                time.sleep(60)
        threading.Thread(target=export_stats,daemon=True).start()
    if options.get('sheets_service_url'):
        guide.reader=PrivateReader(options['sheets_service_url'],options.get('sheets_read_token',''))
        def refresh():
            while True:
                guide.sync(options.get('spreadsheet_id',args.sheet)); time.sleep(max(60,args.interval))
        threading.Thread(target=refresh,daemon=True).start()
    server=ThreadingHTTPServer((args.host,args.port),handler(guide)); LOG.info('Guide listening on %s:%d (preview=%s)',args.host,args.port,args.preview)
    server.serve_forever()

if __name__=='__main__': main()
