"""Guide app to private HA service. Contains no Google credentials."""
import json
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import Request, urlopen

class PrivateReader:
    def __init__(self,url,token):
        self.root=url.rstrip('/');self.token=token
    def request(self,path,body=None,token=None):
        request=Request(self.root+path,data=json.dumps(body).encode() if body is not None else None,
                        headers={'Authorization':'Bearer '+(token or self.token),'Content-Type':'application/json'})
        with urlopen(request,timeout=180 if path.startswith('/api/v1/files/') else 45) as response:return response.read(50*1024*1024)
    def sheet(self,_sheet_id):
        envelope=json.loads(self.request('/api/v1/guide'))
        if envelope.get('schema_version')!='1.0':raise ValueError('Unsupported guide contract')
        return envelope['tables']
    def get(self,url,maximum=50*1024*1024):
        parsed=urlparse(url)
        prefix='/drive/v3/files/'
        if parsed.hostname!='www.googleapis.com' or not parsed.path.startswith(prefix):
            raise ValueError('Unsupported private file request')
        fid=parsed.path.removeprefix(prefix)
        suffix='/content' if parse_qs(parsed.query).get('alt')==['media'] else '/metadata'
        return self.request('/api/v1/files/'+quote(fid,safe='')+suffix)

class PrivateStatsWriter:
    def __init__(self,reader,token):self.reader=reader;self.token=token
    def ensure_headers(self):pass
    def existing_event_ids(self):return set()
    def append(self,events):
        result=json.loads(self.reader.request('/api/v1/usage',{'schema_version':'1.0','events':events},self.token))
        if set(result.get('acknowledged_ids',[]))!={e['event_id'] for e in events}:raise ValueError('Incomplete event acknowledgement')
