# IOW Ferry Status

This add-on collects current service conditions and operator-issued advisories
for five Isle of Wight ferry services. It does not collect timetables.

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
