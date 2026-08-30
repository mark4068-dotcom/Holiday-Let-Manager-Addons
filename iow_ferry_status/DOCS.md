# IOW Ferry Status

This add-on collects current service conditions and operator-issued advisories
for six Isle of Wight services operated by Red Funnel, Wightlink and
Hovertravel. It does not collect timetables.

The monitored routes are Southampton–East Cowes, Southampton–West Cowes,
Portsmouth Harbour–Ryde Pier Head, Portsmouth–Fishbourne,
Lymington–Yarmouth and Southsea–Ryde.

Red Funnel notices containing explicit future dates are hidden until an
affected local date. A successfully loaded Red Funnel page without a current
vehicle-ferry issue is reported as good service. Hovertravel uses the official
website traffic-light status and includes its disruption-contingency paragraph
only while the service is not green.

## Configuration

- `refresh_minutes`: collection interval, from 2 to 60 minutes; default 5.
- `timezone`: browser timezone used by operator pages.
- `api_token`: optional bearer token required by the JSON API.

After starting the add-on, open **Ferry Status** in the Home Assistant sidebar.
The collector retains the last successful result if either operator is
temporarily unavailable.

HLM reads:

```text
http://HOME_ASSISTANT_IP:8790/api/v1/status
```

When `api_token` is configured, send:

```http
Authorization: Bearer YOUR_TOKEN
```

Keep port 8790 on the trusted local network. Do not forward it through the
router or expose it through a public reverse proxy.

On Home Assistant OS, an HLM REST sensor should use the internal add-on URL:

```text
http://local-iow-ferry-status:8790/api/v1/status
```

The response contains stable service IDs, an `updated_at` timestamp,
route-level status and messages, advisories, source errors and stale-state
metadata. HLM dashboards should consume this contract rather than scraping
operator websites directly.
