"""Translate the owner-friendly workbook into the guide's stable internal schema."""
import hashlib
import re
from urllib.parse import urlparse, parse_qs

HEADERS = {
    'Place name':'name', 'Property name':'name', 'Category name':'name',
    'Title':'title', 'Instructions':'instructions', 'Description':'description',
    'Our recommendation':'recommendation', 'Address':'address', 'Latitude':'latitude',
    'Longitude':'longitude', 'Google Place ID':'google_place_id',
    'Parking / access notes':'arrival_notes', 'Website / booking URL':'custom_url',
    'Link button text':'custom_link_label', 'Guest offer':'discount',
    'HLM favourite':'favourite', 'Status':'status', 'Sort order':'display_order',
    'Property':'property_id', 'House category':'category',
    'External guide URL':'manual_url', 'Video URL':'video_url',
    'Additional links':'additional_links', 'Categories':'category_names',
    'Drive file link':'drive_url', 'House guide reference':'topic_id',
    'Place reference':'place_id', 'Property reference':'property_id',
    'Category reference':'category_id', 'File reference':'attachment_id',
}

def normalize_tables(tables):
    data={tab:[{HEADERS.get(k,k):v for k,v in row.items()} for row in rows]
          for tab,rows in tables.items()}
    properties={r['name']:r['property_id'] for r in data['Properties']}
    for tab in ('House Guide','Files'):
        for row in data[tab]:
            row['property_id']=properties.get(row.get('property_id'),row.get('property_id',''))
    for row in data['Files']:
        url=str(row.get('drive_url',''))
        match=re.search(r'/d/([A-Za-z0-9_-]+)',url)
        fid=match.group(1) if match else parse_qs(urlparse(url).query).get('id',[''])[0]
        if fid: row['drive_file_id']=fid
        if not row.get('attachment_id'):
            row['attachment_id']='file_'+hashlib.sha256((fid+str(row.get('topic_id',''))+str(row.get('place_id',''))+str(row.get('property_id',''))).encode()).hexdigest()[:20]
    if any('category_names' in r for r in data['Places']):
        categories={r['name'].casefold():r['category_id'] for r in data['Categories']}
        relations=[]
        for place in data['Places']:
            for name in dict.fromkeys(x.strip() for x in re.split(r'[;,\n]',str(place.get('category_names',''))) if x.strip()):
                if name.casefold() not in categories:
                    raise ValueError('Unknown place category: '+name)
                relations.append({'place_id':place['place_id'],'category_id':categories[name.casefold()],'status':place['status']})
        data['Place Categories']=relations
    data.setdefault('Place Categories',[])
    return data
