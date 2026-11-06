from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from hlm_sheets_service.booking_transport import HEADERS, INPUT_HEADERS, booking_transport_health, canonical, digest, projection_matches
NOW = datetime(2026,11,6,17,30,tzinfo=timezone.utc)

def fixture():
    rows=[INPUT_HEADERS,['Skysail','02/11/2026','13/11/2026','Airbnb','TEST-S',''],['Crossjack','28/12/2026','03/01/2027','Airbnb','TEST-C','']]
    outputs={'skysail':dict(live_booking='Yes',current_check_in='2026-11-02',current_check_out='2026-11-13',booking_reference='TEST-S'),'crossjack':dict(live_booking='No',next_booking_check_in='2026-12-28',next_booking_check_out='2027-01-03',next_booking_reference='TEST-C')}
    evidence=[HEADERS]+[[p,'2026-11-06T17:20:01Z','2026-11-06T17:20:02Z','ok','','calendar-1','booking-1','2026-11-06T17:20:00Z',digest(canonical(rows[1:],p)),1] for p in outputs]
    return evidence,rows,dict(fresh=True,snapshot_id='calendar-1',last_success_at='2026-11-06T17:20:00Z'),outputs

def test_complete_path_for_both_properties():
    r=booking_transport_health(*fixture(),NOW)
    assert r['verified'] and r['fresh']
    assert all(p['last_success_at'] for p in r['properties'].values())

@pytest.mark.parametrize('index',[1,2])
@pytest.mark.parametrize('fault,expected',[('generation','calendar_generation_not_consumed'),('failure','booking_import_failed'),('digest','booking_input_generation_mismatch'),('projection','published_booking_projection_mismatch'),('stale','booking_import_stale'),('future','invalid_import_times')])
def test_each_property_fails_closed(index,fault,expected):
    e,b,u,p=fixture();prop=e[index][0]
    if fault=='generation':e[index][5]='old'
    if fault=='failure':e[index][3]='error';e[index][4]='private detail'
    if fault=='digest':e[index][8]='wrong'
    if fault=='projection':p[prop]['live_booking']='No' if prop=='skysail' else 'Yes'
    now=NOW+timedelta(hours=2) if fault=='stale' else NOW
    if fault=='future':e[index][2]='2026-11-06T18:00:00Z'
    r=booking_transport_health(e,b,u,p,now)
    assert not r['fresh'] and r['properties'][prop]['error']==expected
    assert 'private detail' not in str(r)

def test_missing_duplicate_and_partial_evidence():
    for e in ([],[HEADERS],[HEADERS,fixture()[0][1],fixture()[0][1]]):
        _,b,u,p=fixture()
        assert not booking_transport_health(e,b,u,p,NOW)['verified']

def test_input_change_cannot_reuse_generation():
    e,b,u,p=fixture();b[1][2]='14/11/2026'
    assert booking_transport_health(e,b,u,p,NOW)['properties']['skysail']['error']=='booking_input_generation_mismatch'

def test_order_and_display_do_not_change_digest():
    _,b,_,_=fixture();x=deepcopy(b[1:]);x[0][1]='2026-11-02'
    assert digest(canonical(x,'skysail'))==digest(canonical(list(reversed(b[1:])),'skysail'))

@pytest.mark.parametrize('hour,occupied',[(9,True),(10,False)])
def test_checkout_boundary(hour,occupied):
    row=['skysail','2026-11-01','2026-11-06','Airbnb','TEST','']
    output=dict(live_booking='Yes' if occupied else 'No')
    if occupied:output.update(current_check_in=row[1],current_check_out=row[2],booking_reference='TEST')
    assert projection_matches([row],output,NOW.replace(hour=hour))
