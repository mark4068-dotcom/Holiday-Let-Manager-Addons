"""Google service-account OAuth; used only by the private Sheets service."""
import base64, json, os, subprocess, tempfile, time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from sheet_schema import normalize_tables
TABS=['Properties','House Guide','Places','Categories','Files']
def read_json(path):
    return json.loads(Path(path).read_text())
def rows_to_records(rows):
    if not rows:return []
    headers=rows[0]
    if len(set(headers))!=len(headers):raise ValueError('Duplicate headers')
    return [dict(zip(headers,row+['']*(len(headers)-len(row)))) for row in rows[1:] if any(v!='' for v in row)]
class GoogleReader:
    def __init__(self, credentials, scope='https://www.googleapis.com/auth/spreadsheets.readonly https://www.googleapis.com/auth/drive.readonly'):
        self.credentials=credentials; self.token=None; self.expires=0; self.scope=scope
    def access_token(self):
        if self.token and time.time()<self.expires-60: return self.token
        creds=read_json(self.credentials); now=int(time.time())
        b64=lambda b:base64.urlsafe_b64encode(b).rstrip(b'=').decode()
        claims={'iss':creds['client_email'],'scope':self.scope,'aud':'https://oauth2.googleapis.com/token','iat':now,'exp':now+3600}
        unsigned=(b64(b'{"alg":"RS256","typ":"JWT"}')+'.'+b64(json.dumps(claims).encode())).encode()
        with tempfile.NamedTemporaryFile() as key:
            os.chmod(key.name,0o600); key.write(creds['private_key'].encode()); key.flush()
            signature=subprocess.run(['openssl','dgst','-sha256','-sign',key.name],input=unsigned,capture_output=True,check=True).stdout
        body=urlencode({'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':unsigned.decode()+'.'+b64(signature)}).encode()
        with urlopen(Request('https://oauth2.googleapis.com/token',data=body),timeout=30) as response: result=json.load(response)
        self.token=result['access_token']; self.expires=now+int(result.get('expires_in',3600)); return self.token
    def get(self,url,maximum=50*1024*1024):
        with urlopen(Request(url,headers={'Authorization':'Bearer '+self.access_token()}),timeout=45) as response:
            data=response.read(maximum+1)
            if len(data)>maximum: raise ValueError('Google response exceeds file limit')
            return data
    def post(self,url,body,method='POST'):
        request=Request(url,data=json.dumps(body,ensure_ascii=False).encode(),method=method,headers={'Authorization':'Bearer '+self.access_token(),'Content-Type':'application/json'})
        with urlopen(request,timeout=45) as response: return json.load(response)
    def sheet(self,sheet_id):
        root='https://sheets.googleapis.com/v4/spreadsheets/'+quote(sheet_id,safe='')
        metadata=json.loads(self.get(root+'?fields=sheets(properties(title,gridProperties(rowCount,columnCount)))'))
        grids={s['properties']['title']:s['properties']['gridProperties'] for s in metadata['sheets']}
        if not all(tab in grids for tab in TABS): raise ValueError('Missing guide tab')
        ranges=[]
        for tab in TABS:
            grid=grids[tab]
            if grid['rowCount']>10000: raise ValueError('Guide tab exceeds supported row limit')
            end=chr(64+min(26,grid['columnCount']))
            ranges.append(('ranges',"'"+tab+"'!A1:"+end+str(grid['rowCount'])))
        query=urlencode(ranges+[('valueRenderOption','UNFORMATTED_VALUE')])
        raw=json.loads(self.get(root+'/values:batchGet?'+query))
        ranges=raw.get('valueRanges',[])
        if len(ranges)!=len(TABS): raise ValueError('Incomplete spreadsheet response')
        return normalize_tables({tab:rows_to_records(block.get('values',[])) for tab,block in zip(TABS,ranges)})

