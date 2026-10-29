import json
from pathlib import Path
import tempfile
import unittest
import io
from email.message import Message
from types import SimpleNamespace
from uuid import uuid4
from usage_stats import UsageStats, StatsWriter, HEADERS

class FakeWriter:
    def __init__(self,mode='ok'): self.ids=set(); self.events=[]; self.mode=mode
    def ensure_headers(self): pass
    def existing_event_ids(self): return set(self.ids)
    def append(self,events):
        if self.mode=='offline': raise OSError('offline')
        self.events.extend(events); self.ids.update(e['event_id'] for e in events)
        if self.mode=='lost_response': raise OSError('response lost')

class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.stats=UsageStats(self.temp.name,'crossjack',['hall'],enabled=True)
    def event(self,**extra):
        return dict(event_id=str(uuid4()),kiosk='hall',action='search',section='places',search_text='=coffee + cake',result_count=0,**extra)
    def test_raw_search_zero_results_and_no_identity_fields(self):
        event=self.event();self.stats.record(event);r=self.stats.pending()[0]
        self.assertEqual(r['search_text'],'=coffee + cake');self.assertEqual(r['result_count'],0)
        self.assertEqual(r['property'],'crossjack');self.assertTrue(r['timestamp'].endswith('Z'))
        self.assertNotIn('ip',r)
        with self.assertRaises(ValueError):self.stats.record({**self.event(),'ip':'192.168.1.1'})
    def test_preview_never_records_or_creates_database(self):
        folder=Path(self.temp.name)/'preview';folder.mkdir()
        stats=UsageStats(folder,'crossjack',['hall'],enabled=True,preview=True)
        self.assertFalse(stats.record(self.event()));self.assertFalse(stats.path.exists())
    def test_restart_and_offline_recovery(self):
        e=self.event();self.stats.record(e)
        self.assertEqual(self.stats.flush(FakeWriter('offline')),0)
        reboot=UsageStats(self.temp.name,'crossjack',['hall'],enabled=True)
        writer=FakeWriter();self.assertEqual(reboot.flush(writer),1);self.assertEqual(reboot.pending(),[])
        self.assertEqual(writer.events[0]['event_id'],e['event_id'])
    def test_lost_append_response_and_retry_dedup(self):
        e=self.event();self.stats.record(e);self.stats.record(e)
        writer=FakeWriter('lost_response');self.assertEqual(self.stats.flush(writer),1)
        self.assertEqual(len(writer.events),1)
        self.stats.record(e);self.stats.flush(writer);self.assertEqual(len(writer.events),1)
    def test_only_configured_kiosks_and_valid_search_counts(self):
        e=self.event();e['kiosk']='unknown'
        with self.assertRaises(ValueError):self.stats.record(e)
        e=self.event();e['result_count']=-1
        with self.assertRaises(ValueError):self.stats.record(e)
    def test_writer_raw_fixed_tab_and_header_guard(self):
        class Client:
            def get(self,url): return json.dumps({'values':[HEADERS]}).encode()
            def post(self,url,body):self.url=url;self.body=body
        client=Client();writer=StatsWriter(client,'guide-only');writer.ensure_headers()
        e={**self.event(),'property':'crossjack','timestamp':'2026-10-29T12:00:00Z'};writer.append([e])
        self.assertIn('valueInputOption=RAW',client.url);self.assertIn('Stats',client.url)
        self.assertIn('insertDataOption=OVERWRITE',client.url)
        self.assertEqual(client.body['values'][0][8],'=coffee + cake')
        self.assertEqual(client.body['values'][0][9],0)
    def test_http_event_boundary_and_origin(self):
        from guide import handler
        Handler=handler(SimpleNamespace(stats=self.stats))
        request=Handler.__new__(Handler)
        request.path='/api/usage';request.headers=Message()
        payload=json.dumps(self.event()).encode()
        request.headers['Content-Length']=str(len(payload));request.headers['Content-Type']='application/json'
        request.headers['Host']='guide.local:8099';request.headers['Origin']='http://guide.local:8099'
        request.rfile=io.BytesIO(payload);responses=[];request.send=lambda *args:responses.append(args)
        request.do_POST();self.assertEqual(responses[-1][0],200);self.assertEqual(len(self.stats.pending()),1)
        request.headers.replace_header('Origin','http://other.local')
        request.do_POST();self.assertEqual(responses[-1][0],403)
