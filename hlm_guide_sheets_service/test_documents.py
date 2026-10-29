import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from documents import DocumentCache, DOCX, NATIVE_DOC, PDF

class Reader:
    def __init__(self):
        self.source=b'word source';self.revision='one';self.mime=DOCX;self.exports=0
    def get(self,url):
        if '/export?' in url:self.exports+=1;return b'%PDF-native'
        if 'alt=media' in url:return self.source
        return json.dumps({'id':'doc','mimeType':self.mime,'size':len(self.source),
                           'md5Checksum':hashlib.md5(self.source).hexdigest() if self.mime==DOCX else '',
                           'modifiedTime':self.revision}).encode()

class DocumentTests(unittest.TestCase):
    def test_word_cache_and_source_update(self):
        with tempfile.TemporaryDirectory() as folder:
            reader=Reader();cache=DocumentCache(reader,folder)
            with patch.object(cache,'convert',return_value=b'%PDF-first') as convert:
                meta,pdf=cache.get('doc');cache.get('doc')
                self.assertEqual(convert.call_count,1)
                self.assertEqual(meta['mimeType'],PDF)
                self.assertEqual(meta['md5Checksum'],hashlib.md5(pdf).hexdigest())
                reader.source=b'changed';cache.get('doc')
                self.assertEqual(convert.call_count,2)
    def test_native_export_and_changed_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            reader=Reader();reader.mime=NATIVE_DOC;cache=DocumentCache(reader,folder)
            cache.get('doc');cache.get('doc');self.assertEqual(reader.exports,1)
            reader.revision='two';cache.get('doc');self.assertEqual(reader.exports,2)
    def test_failed_conversion_does_not_replace_cached_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            reader=Reader();cache=DocumentCache(reader,folder)
            with patch.object(cache,'convert',return_value=b'%PDF-lastgood'):cache.get('doc')
            reader.source=b'new invalid source'
            with patch.object(cache,'convert',return_value=b'not a PDF'):
                with self.assertRaises(ValueError):cache.get('doc')
            self.assertEqual([p.read_bytes() for p in Path(folder).glob('*.pdf')],[b'%PDF-lastgood'])
    def test_non_document_passthrough(self):
        with tempfile.TemporaryDirectory() as folder:
            reader=Reader();reader.mime='image/png'
            self.assertIsNone(DocumentCache(reader,folder).get('image')[1])

if __name__=='__main__':unittest.main()
