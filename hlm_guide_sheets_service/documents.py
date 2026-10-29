"""Convert approved Drive documents into versioned, private PDF cache entries."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.parse import quote

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
NATIVE_DOC = 'application/vnd.google-apps.document'
PDF = 'application/pdf'

class DocumentCache:
    def __init__(self, reader, folder='/data/documents'):
        self.reader = reader
        self.folder = Path(folder)
        self.lock = threading.Lock()

    def get(self, fid):
        # The caller must check its publication allowlist before calling this.
        with self.lock:
            root = 'https://www.googleapis.com/drive/v3/files/' + quote(fid, safe='')
            meta = json.loads(self.reader.get(root + '?fields=id,mimeType,size,md5Checksum,modifiedTime'))
            mime = meta['mimeType']
            if mime not in (DOCX, NATIVE_DOC):
                return meta, None
            revision = meta.get('md5Checksum') or meta.get('modifiedTime')
            if not revision:
                raise ValueError('Document revision unavailable')
            key = hashlib.sha256((fid + ':' + revision).encode()).hexdigest()
            self.folder.mkdir(parents=True, exist_ok=True)
            target = self.folder / (key + '.pdf')
            if not target.exists():
                if mime == NATIVE_DOC:
                    pdf = self.reader.get(root + '/export?mimeType=application%2Fpdf')
                else:
                    source = self.reader.get(root + '?alt=media')
                    if len(source) != int(meta['size']) or hashlib.md5(source).hexdigest() != meta['md5Checksum']:
                        raise ValueError('Document download checksum mismatch')
                    pdf = self.convert(source)
                if not pdf.startswith(b'%PDF-') or len(pdf) > 50*1024*1024:
                    raise ValueError('Invalid converted PDF')
                with tempfile.NamedTemporaryFile(dir=self.folder, delete=False) as out:
                    tmp = Path(out.name)
                    out.write(pdf)
                tmp.replace(target)
            pdf = target.read_bytes()
            return {'id': fid, 'mimeType': PDF, 'size': str(len(pdf)),
                    'md5Checksum': hashlib.md5(pdf).hexdigest()}, pdf

    @staticmethod
    def convert(source):
        with tempfile.TemporaryDirectory(prefix='guide-doc-') as tmp:
            folder = Path(tmp)
            doc = folder / 'document.docx'
            doc.write_bytes(source)
            subprocess.run(['libreoffice', '-env:UserInstallation=' + (folder/'profile').as_uri(),
                            '--headless', '--convert-to', 'pdf:writer_pdf_Export',
                            '--outdir', str(folder), str(doc)],
                           check=True, timeout=120, capture_output=True)
            return (folder/'document.pdf').read_bytes()
