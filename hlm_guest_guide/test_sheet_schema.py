import unittest
from sheet_schema import normalize_tables

class ManualSheetTests(unittest.TestCase):
    def tables(self):
        return {'Properties':[{'Property name':'Crossjack','Property reference':'crossjack','Status':'Draft'}],
            'Places':[{'Place name':'Cafe','Place reference':'cafe','Categories':'Cafes; Dog friendly','Status':'Draft'}],
            'Categories':[{'Category name':'Cafes','Category reference':'cafes','Status':'Draft'},{'Category name':'Dog friendly','Category reference':'dogs','Status':'Draft'}],
            'House Guide':[{'Property':'Crossjack','House guide reference':'crossjack_tv'}],
            'Files':[{'Drive file link':'https://drive.google.com/file/d/abc123/view','Property':'Crossjack','House guide reference':'crossjack_tv'}]}
    def test_friendly_headers_and_category_links(self):
        d=normalize_tables(self.tables())
        self.assertEqual(d['House Guide'][0]['property_id'],'crossjack')
        self.assertEqual([r['category_id'] for r in d['Place Categories']],['cafes','dogs'])
        self.assertEqual(d['Files'][0]['drive_file_id'],'abc123')
        self.assertTrue(d['Files'][0]['attachment_id'])
    def test_unknown_category_stops_bad_import(self):
        t=self.tables();t['Places'][0]['Categories']='Misspelled'
        with self.assertRaisesRegex(ValueError,'Unknown place category'):normalize_tables(t)
    def test_shared_drive_url_id_and_archived_relationships(self):
        t=self.tables();t['Files'][0]['Drive file link']='https://drive.google.com/open?id=xyz456';t['Places'][0]['Status']='Archived'
        d=normalize_tables(t)
        self.assertEqual(d['Files'][0]['drive_file_id'],'xyz456')
        self.assertTrue(all(r['status']=='Archived' for r in d['Place Categories']))
