import copy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from guide import Guide, InstructionLinks, atomic_json, distance_miles, maps_url, validate

def fixture():
    return {'Properties':[{'property_id':'a','name':'A','status':'Published'},{'property_id':'b','name':'B','status':'Published'}],
    'House Guide':[{'topic_id':'a_tv','property_id':'a','title':'TV','instructions':'A instructions','category':'TV','status':'Published'},{'topic_id':'b_tv','property_id':'b','title':'TV','instructions':'B instructions','category':'TV','status':'Published'},{'topic_id':'a_draft','property_id':'a','title':'Draft','instructions':'Not ready','category':'TV','status':'Draft'}],
    'Places':[{'place_id':'open','name':'Open place','status':'Published'},{'place_id':'closed','name':'Closed place','status':'Archived'}],
    'Categories':[{'category_id':'food','name':'Food','status':'Published'}],
    'Place Categories':[{'place_id':'open','category_id':'food','status':'Published'}],
    'Files':[{'attachment_id':'a_manual','drive_file_id':'fileA','topic_id':'a_tv','property_id':'a','title':'TV manual','status':'Published'},{'attachment_id':'b_manual','drive_file_id':'fileB','topic_id':'b_tv','property_id':'b','title':'TV manual','status':'Published'}]}

class FakeReader:
    def __init__(self,data,contents,fail=None): self.data=data; self.contents=contents; self.fail=fail; self.downloads=0
    def sheet(self,_): return copy.deepcopy(self.data)
    def get(self,url):
        fid=url.split('/files/')[1].split('?')[0]
        if fid==self.fail: raise OSError('Simulated outage')
        content=self.contents[fid]
        if 'alt=media' in url: self.downloads+=1; return content
        return json.dumps({'mimeType':'application/pdf','size':str(len(content)),'md5Checksum':hashlib.md5(content).hexdigest()}).encode()

class GuideTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.data=fixture(); atomic_json(self.root/'snapshot.json',self.data); self.guide=Guide(self.root,'a')
    def tearDown(self): self.tmp.cleanup()
    def test_property_isolation(self):
        self.assertIsNone(self.guide.view('b'))
        self.guide.allowed_properties.add('b')
        view=self.guide.view('b'); self.assertEqual(view['property']['property_id'],'b'); self.assertEqual([x['topic_id'] for x in view['topics']],['b_tv']); self.assertEqual(len(view['places']),1)
        self.assertIsNone(self.guide.view('unknown'))
    def test_drafts_only_in_preview(self):
        self.guide.preview=True; self.assertEqual(len(self.guide.view()['topics']),2); self.assertEqual(self.guide.view('b')['property']['property_id'],'b')
    def test_media_cannot_cross_property(self):
        media=self.root/'media'; media.mkdir(); (media/'fileA').write_bytes(b'%PDF-a'); (media/'fileB').write_bytes(b'%PDF-b')
        self.assertIsNotNone(self.guide.media('fileA')); self.assertIsNone(self.guide.media('fileB','b')); self.assertIsNone(self.guide.media('../snapshot.json'))
        self.guide.preview=True; self.assertIsNotNone(self.guide.media('fileB','b'))
    def test_explicit_property_media_remains_isolated(self):
        self.guide.allowed_properties.add('b')
        media=self.root/'media';media.mkdir();(media/'fileA').write_bytes(b'%PDF-a');(media/'fileB').write_bytes(b'%PDF-b')
        self.assertIsNotNone(self.guide.media('fileB','b'))
        self.assertIsNone(self.guide.media('fileA','b'))
    def test_failed_sync_keeps_complete_previous_version(self):
        initial={'fileA':b'%PDF-old-a','fileB':b'%PDF-old-b'}; self.guide.reader=FakeReader(self.data,initial); self.guide.sync('sheet'); old=self.guide.media('fileA')[0]
        self.guide.reader=FakeReader(self.data,{'fileA':b'%PDF-new-a','fileB':b'%PDF-new-b'},fail='fileB'); self.guide.sync('sheet')
        self.assertEqual(self.guide.media('fileA')[0],old); self.assertEqual(old.read_bytes(),b'%PDF-old-a'); self.assertIsNotNone(self.guide.last_error)
        restarted=Guide(self.root,'a'); self.assertEqual(restarted.media('fileA')[0].read_bytes(),b'%PDF-old-a')
    def test_same_drive_id_new_contents_refreshes(self):
        reader=FakeReader(self.data,{'fileA':b'%PDF-one','fileB':b'%PDF-two'}); self.guide.reader=reader; self.guide.sync('sheet'); first=self.guide.media('fileA')[0]
        reader.contents['fileA']=b'%PDF-replaced'; self.guide.sync('sheet'); self.assertNotEqual(first,self.guide.media('fileA')[0]); self.assertEqual(self.guide.media('fileA')[0].read_bytes(),b'%PDF-replaced')
    def test_unchanged_files_not_redownloaded(self):
        reader=FakeReader(self.data,{'fileA':b'%PDF-one','fileB':b'%PDF-two'}); self.guide.reader=reader; self.guide.sync('sheet'); self.guide.sync('sheet'); self.assertEqual(reader.downloads,2)
    def test_bad_relationship_rejected(self):
        self.data['Files'][0]['property_id']='b'
        with self.assertRaises(ValueError): validate(self.data)
    def test_unknown_coordinates_not_zero(self):
        self.assertIsNone(distance_miles({'latitude':'','longitude':''},{'latitude':50,'longitude':-1})); self.assertIsNone(distance_miles({'latitude':'nan','longitude':0},{'latitude':0,'longitude':0}))
    def test_distance_sort(self):
        self.guide.data['Properties'][0].update(latitude=50,longitude=-1)
        self.guide.data['Places']=[{'place_id':'far','name':'Far','status':'Published','latitude':51,'longitude':-1},{'place_id':'missing','name':'Missing','status':'Published'},{'place_id':'near','name':'Near','status':'Published','latitude':50.01,'longitude':-1}]
        self.assertEqual([x['place_id'] for x in self.guide.view()['places']],['near','far','missing'])
    def test_qr_links_do_not_guess_property(self):
        self.assertEqual(maps_url({'name':'Crossjack'}),''); self.assertIn('query_place_id=',maps_url({'name':'Cafe','google_place_id':'verified'}))
    def test_instruction_links_reject_script_urls(self):
        links=InstructionLinks(); links.feed('<a href="javascript:alert(1)">Bad</a><a href="https://example.com">Guide</a>'); self.assertEqual(links.links,[{'url':'https://example.com','label':'Guide'}])
    def test_live_requests_require_configuration_and_enforce_persistent_limit(self):
        self.guide.data['Places'][0]['google_place_id']='verified'
        self.assertEqual(self.guide.place_details('open')[0],503)
        self.guide.google_key='test-key'; self.guide.terms_url='https://example.com/terms'; self.guide.privacy_url='https://example.com/privacy'; self.guide.places_limit=1
        with patch('guide.urlopen',side_effect=OSError('Offline')) as request:
            self.assertEqual(self.guide.place_details('open')[0],503)
            self.assertEqual(self.guide.place_details('open')[0],429)
            self.assertEqual(request.call_count,1)
        restarted=Guide(self.root,'a'); restarted.google_key='test-key'; restarted.terms_url=self.guide.terms_url; restarted.privacy_url=self.guide.privacy_url; restarted.places_limit=1
        restarted.data['Places'][0]['google_place_id']='verified'
        self.assertEqual(restarted.place_details('open')[0],429)

if __name__=='__main__': unittest.main()
