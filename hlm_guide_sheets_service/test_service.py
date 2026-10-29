import copy
import io
import json
import sys
import tempfile
import time
import unittest
from email.message import Message
from pathlib import Path
from uuid import uuid4

sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent.parent/'hlm_guest_guide')]
from service import Service, PUBLICATION_HEADERS, publication_rows,parse_publication,handler,now

def fixture():
    return {'Properties':[{'property_id':'crossjack','name':'Crossjack','status':'Published'}],
      'House Guide':[], 'Places':[], 'Categories':[], 'Place Categories':[], 'Files':[]}

class Client:
    def __init__(self):self.tables=fixture();self.publication=[PUBLICATION_HEADERS];self.events=[];self.ids=set();self.mode='ok'
    def sheet(self,spreadsheet):return copy.deepcopy(self.tables)
    def get(self,url):
        if 'Publication' in url:return json.dumps({'values':self.publication}).encode()
        if 'A1%3AL1' in url:
            from usage_stats import HEADERS
            return json.dumps({'values':[HEADERS]}).encode()
        if 'A2%3AA' in url:return json.dumps({'values':[[x] for x in self.ids]}).encode()
        raise ValueError('Unexpected destination')
    def post(self,url,body,method='POST'):
        if 'Publication' in url:
            assert method=='PUT';self.publication=body['values'];return
        self.events.extend(body['values']);self.ids.update(row[0] for row in body['values'])
        if self.mode=='lost':raise OSError('Lost response')

class PrivateServiceTests(unittest.TestCase):
    def setUp(self):
        self.client=Client();self.options={'spreadsheet_id':'guide-only','api_token':'r'*32,'usage_write_token':'w'*32,'publication_write_enabled':True,'usage_write_enabled':True,'kiosk_properties':{'hall':'crossjack'}}
        self.service=Service(self.options,self.client,self.client)
    def event(self):return {'event_id':str(uuid4()),'timestamp':now(),'property':'crossjack','kiosk':'hall','action':'search','section':'places','search_text':'=unfiltered','result_count':0}
    def test_publication_roundtrip_and_tamper_rejection(self):
        rows=publication_rows(fixture(),now());tables,_,_=parse_publication(rows);self.assertEqual(tables,fixture())
        rows[1][3]=rows[1][3].replace('Crossjack','Changed')
        with self.assertRaises(ValueError):parse_publication(rows)
    def test_source_validation_publication_and_unchanged_timestamp(self):
        self.service.refresh();first=self.service.read();self.service.refresh();second=self.service.read()
        self.assertEqual(first['published_at'],second['published_at'])
        self.assertIsNotNone(self.service.state['last_source_refresh_at'])
        self.client.tables['Properties'][0]['name']='#REF!';self.service.refresh()
        with self.assertRaises(ValueError):self.service.read()
    def test_stale_verified_source_and_future_publication(self):
        self.service.refresh();self.service.state['last_source_refresh_at']='2000-01-01T00:00:00Z'
        with self.assertRaises(ValueError):self.service.read()
        with self.assertRaises(ValueError):parse_publication(publication_rows(fixture(),'2099-01-01T00:00:00Z'))
    def test_usage_duplicate_and_lost_response(self):
        self.client.mode='lost';e=self.event();body={'schema_version':'1.0','events':[e]}
        self.assertEqual(self.service.usage(body)['acknowledged_ids'],[e['event_id']])
        self.service.usage(body);self.assertEqual(len(self.client.events),1)
    def test_usage_unknown_kiosk_batch_and_schema(self):
        e=self.event();e['kiosk']='unknown'
        with self.assertRaises(ValueError):self.service.usage({'schema_version':'1.0','events':[e]})
        with self.assertRaises(ValueError):self.service.usage({'schema_version':'1.0','events':[self.event() for _ in range(101)]})
        with self.assertRaises(ValueError):self.service.usage({'schema_version':'2.0','events':[self.event()]})
    def request(self,path,token,body=None):
        Handler=handler(self.service);r=Handler.__new__(Handler);r.path=path;r.headers=Message();r.headers['Authorization']='Bearer '+token
        raw=json.dumps(body).encode() if body else b'';r.headers['Content-Length']=str(len(raw));r.rfile=io.BytesIO(raw);out=[];r.send=lambda *args:out.append(args)
        (r.do_POST if body else r.do_GET)();return out[-1]
    def test_read_and_write_authentication_are_separate(self):
        self.service.refresh()
        self.assertEqual(self.request('/api/v1/guide','wrong')[0],401)
        self.assertEqual(self.request('/api/v1/guide','w'*32)[0],401)
        self.assertEqual(self.request('/api/v1/guide','r'*32)[0],200)
        self.assertEqual(self.request('/api/v1/usage','r'*32,{'schema_version':'1.0','events':[self.event()]})[0],401)
        self.assertEqual(self.request('/api/v1/usage','w'*32,{'schema_version':'1.0','events':[self.event()]})[0],200)

if __name__=='__main__':unittest.main()
