"""Content-bound booking transport evidence; never infer freshness from clocks."""
import hashlib
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TRANSPORT_RANGE = '04_booking_transport_health!A1:J3'
BOOKINGS_RANGE = '05_consumed_bookings!A1:F2000'
HEADERS = ['property_id', 'last_attempt_at', 'last_success_at', 'status', 'error',
           'calendar_generation', 'booking_generation', 'calendar_success_at',
           'booking_digest', 'calendar_records']
INPUT_HEADERS = ['source_property', 'check_in', 'check_out', 'booking_channel',
                 'booking_reference', 'source_notes']


def stamp(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timezone required')
    return parsed


def day(value):
    if not value:
        return ''
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%b-%y'):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    return str(value)


def canonical(rows, prop):
    values = []
    for row in rows:
        row = list(row) + [''] * (6 - len(row))
        if str(row[0]).strip().lower() == prop:
            values.append([prop, day(row[1]), day(row[2]),
                           *[str(v or '') for v in row[3:6]]])
    return sorted(values, key=lambda r: json.dumps(r, ensure_ascii=False, separators=(',', ':')).encode('utf-16-be'))


def digest(rows):
    data = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(data.encode()).hexdigest()


def projection_matches(rows, output, now):
    local = now.astimezone(ZoneInfo('Europe/London'))
    today = local.date().isoformat()
    operational = (local.date() + timedelta(days=local.hour >= 16)).isoformat()
    active = [r for r in rows if 'cancelled' not in (r[4]+' '+r[5]).lower()
              and r[1] and r[2] and r[2] > r[1]]
    live = [r for r in active if (r[1] < today < r[2])
            or (r[1] == today and local.hour >= 16)
            or (r[2] == today and local.hour < 10)]
    if len(live) > 1 or (output.get('live_booking') == 'Yes') != bool(live):
        return False
    current = live[0] if live else None
    future = sorted([r for r in active if r[1] >= operational], key=lambda r: r[1])
    upcoming = future[0] if future else None
    for row, fields in ((current, ('current_check_in', 'current_check_out', 'booking_reference')),
                        (upcoming, ('next_booking_check_in', 'next_booking_check_out', 'next_booking_reference'))):
        expected = row[1:3] + [row[4]] if row else [None, None, None]
        if any((output.get(field) or None) != (value or None) for field, value in zip(fields, expected)):
            return False
    return True


def booking_transport_health(evidence, bookings, upstream, published, now):
    properties = {p: {'fresh': False, 'error': 'transport_evidence_missing',
                      'last_attempt_at': None, 'last_success_at': None,
                      'calendar_generation': None, 'booking_generation': None}
                  for p in ('skysail', 'crossjack')}
    result = {'verified': False, 'fresh': False, 'properties': properties,
              'max_success_age_seconds': 5400}
    try:
        if len(evidence) != 3 or evidence[0] != HEADERS or not bookings or bookings[0] != INPUT_HEADERS:
            return result
        if {r[0] for r in evidence[1:]} != set(properties) or len(bookings) >= 2000:
            return result
        for raw in evidence[1:]:
            row = dict(zip(HEADERS, raw))
            item = properties[row['property_id']]
            item.update({k: row.get(k) for k in item if k in row})
            success = stamp(row['last_success_at'])
            attempt = stamp(row['last_attempt_at'])
            calendar = stamp(row['calendar_success_at'])
            age = (now-success).total_seconds()
            item['success_age_seconds'] = age
            if row['status'] != 'ok' or row.get('error'):
                item['error'] = 'booking_import_failed'
            elif age < -120 or (now-attempt).total_seconds() < -120 or success < attempt or calendar > success:
                item['error'] = 'invalid_import_times'
            elif age > 5400:
                item['error'] = 'booking_import_stale'
            elif not upstream.get('fresh') or row['calendar_generation'] != upstream.get('snapshot_id'):
                item['error'] = 'calendar_generation_not_consumed'
            elif not row.get('booking_generation') or calendar != stamp(upstream['last_success_at']):
                item['error'] = 'invalid_generation_evidence'
            else:
                consumed = canonical(bookings[1:], row['property_id'])
                if digest(consumed) != row.get('booking_digest'):
                    item['error'] = 'booking_input_generation_mismatch'
                elif not published or not projection_matches(consumed, published[row['property_id']], now):
                    item['error'] = 'published_booking_projection_mismatch'
                else:
                    item.update(fresh=True, error=None)
        result['fresh'] = result['verified'] = all(p['fresh'] for p in properties.values())
    except (ValueError, TypeError, KeyError, IndexError):
        for item in properties.values():
            item.update(fresh=False, error='invalid_transport_evidence')
    return result
