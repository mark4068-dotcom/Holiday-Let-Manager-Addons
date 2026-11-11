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
The collector retains the last successful result if any operator is
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
http://32662a46-iow-ferry-status:8790/api/v1/status
```

The response contains stable service IDs, an `updated_at` timestamp,
route-level status and messages, advisories, source errors and stale-state
metadata. HLM dashboards should consume this contract rather than scraping
operator websites directly.

## Refresh recovery and health

From version 0.1.12, each collection runs in a separate Node.js worker process.
The deadline is the greater of two minutes and `refresh_minutes` (five minutes
with the default options). On timeout, the server terminates the worker and its
browser descendants, including Chromium processes in separate process groups.
It releases the refresh lock after worker shutdown so a later scheduled refresh
can try again. This also bounds a hang during browser launch or shutdown.

Only a complete, error-free set of six services replaces the saved payload.
A failed or timed-out collection retains the last complete payload and exposes
`stale: true`, `source_errors`, and collector error details. Data is also stale
when its age exceeds the greater of twice the refresh interval and 15 minutes.
An individual route can still report `unknown` when its page loads but its
status cannot be extracted; a complete service set does not guarantee every
route has a known status.

Inspect `GET /health` for `last_attempt_at`, `last_success_at`, `next_update_at`,
`running`, `error`, `source_errors`, and `service_count`. `ok: true` means a saved
payload exists, not that it is fresh; check `stale` and the timestamps too. The
health endpoint returns HTTP 200 even when stale, so an HTTP-only watchdog is
not a freshness check. `GET /api/v1/status` includes the retained data and the
same collector diagnostics. Health is unauthenticated; the API requires the
configured bearer token, if any.

For delayed updates, check these diagnostics and the add-on log first. A restart
can recover a stuck installation of 0.1.11, but updating to 0.1.12 installs the
worker cleanup that prevents the same refresh-lock failure from persisting.
Successful recovery should show a recent `last_success_at`, `stale: false`, six
services, and no source errors.

## Updating and rollback

The installed production add-on is supplied by
`https://github.com/mark4068-dotcom/Holiday-Let-Manager-Addons`, with slug
`32662a46_iow_ferry_status`. Make future changes under `iow_ferry_status/` in
this repository. The standalone `IOW_ferry_status` repository is a historical
baseline; pushing there will not update this installation. The internal hostname
shown above applies to this repository installation; use the hostname displayed
in Home Assistant for installations from other repositories.

After a release is merged to `main`, refresh Home Assistant's app/add-on update
list, open **IOW Ferry Status**, and install the offered version. Verify the
installed version and health after the first collection. Keep a backup of the
previous version and its data before updating. If rollback is required, restore
the saved add-on backup and verify health; rolling back to 0.1.11 also restores
the timeout defect and may require manual restarts.

The [30 October 2026 incident and release record](session-reports/2026-10-30-timeout-recovery.md)
records the 0.1.12 deployment and validation.
