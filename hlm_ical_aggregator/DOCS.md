# HLM iCalendar Aggregator

This app combines independently filtered remote ICS calendars into one local
calendar for Home Assistant. It is a diary/display service only. Do not use its
calendar as HLM's booking or operations source; those facts come from the
private Google Sheets exchange feed.

## Initial source configuration

Add three entries under **Sources** in the app configuration form. Keep the
actual Guesty URLs in runtime configuration and never commit them to Git.

```yaml
sources:
  - id: crossjack
    name: Crossjack Guesty bookings
    url: https://REPLACE-WITH-CROSSJACK-GUESTY-FEED
    enabled: true
    exclude_regex: "(?i)^\\s*Blocked by Guesty\\s*$"
    include_regex: ""
    title_prefix: "Crossjack — "
    exclude_cancelled: true
  - id: skysail
    name: Skysail Guesty bookings
    url: https://REPLACE-WITH-SKYSAIL-GUESTY-FEED
    enabled: true
    exclude_regex: "(?i)^\\s*Blocked by Guesty\\s*$"
    include_regex: ""
    title_prefix: "Skysail — "
    exclude_cancelled: true
  - id: guest-guide
    name: HLM Guest Guide events
    url: http://32662a46-hlm-guide-calendar:8788/events.ics
    enabled: true
    exclude_regex: ""
    include_regex: ""
    title_prefix: "Local event — "
    exclude_cancelled: true
```

The Guest Guide app slug is `hlm_guide_calendar`. Home Assistant prefixes an
app's internal DNS hostname with its repository identifier. The confirmed Dev
hostname is `32662a46-hlm-guide-calendar`, as used above; confirm the hostname
shown by Supervisor before configuring another installation. If the Guest
Guide feed authentication is enabled, a later release will add per-source
credentials; do not embed a password in the URL.

## Home Assistant calendar

After all sources report a successful refresh:

1. Add Home Assistant's **Remote Calendar** integration.
2. Name it `HLM combined calendar`.
3. Use `http://local-hlm-ical-aggregator:8789/combined.ics`.
4. Enter the optional feed username and password configured in this app.
5. Disable the integration's default polling and call
   `homeassistant.update_entity` every 15 minutes.

The local app port must not be forwarded through the router or directly exposed
through Home Assistant Cloud.

## Endpoints

- `GET /combined.ics`
- `GET /sources/<source-id>.ics`
- `GET /api/v1/status`
- `GET /health`
- `POST /refresh`

The ICS endpoints require HTTP Basic Authentication when either feed credential
is configured. The status page and refresh button are intended for admin-only
Home Assistant ingress.

## Failure handling

Each source has its own last-known-good filtered cache. A download, parse or
filter failure leaves that cache unchanged and reports the error in diagnostics.
The combined feed is atomically replaced only after at least one valid source
cache is available.

## Private Google Calendar publication

Publication is outbound-only; it does not expose Home Assistant to inbound
internet traffic. Leave **Publish to Google Calendar** off until the local
calendar has passed its comparison period.

1. Create a Google Cloud project, enable the Google Calendar API and create a
   service account.
2. Create a dedicated private calendar owned by `sailcottagesha@gmail.com`.
3. Share only that calendar with the service-account email and grant permission
   to make changes to events.
4. Put the downloaded JSON key in this app's configuration directory as
   `google-service-account.json`. Never paste it into an app option or commit it.
5. Enter the calendar ID and keep **Google dry run** enabled for the first run.
6. Confirm the planned create/update/delete counts in app diagnostics, then
   disable dry-run to publish.

On an existing installation, open the Options menu and choose **Edit in YAML**
to add the publication settings without replacing the existing source list:

```yaml
google_publish_enabled: true
google_calendar_id: REPLACE-WITH-PRIVATE-CALENDAR-ID
google_credentials_path: /config/google-service-account.json
google_dry_run: true
google_title_mode: retain_details
google_default_timezone: Europe/London
google_retry_count: 4
google_allow_empty_publish: false
```

`retain_details` keeps the combined calendar titles, descriptions and locations.
`privacy_safe` changes Guesty events to `Crossjack — Booked` or
`Skysail — Booked` and omits their description and location. HLM currently uses
`retain_details` because the source calendars do not contain private data.

Every published event has a deterministic Google event ID and private
`hlmManaged`, `hlmSyncKey` and `hlmFingerprint` properties. Reconciliation only
updates or deletes events carrying these markers. An empty combined feed is
blocked from deleting every managed event unless **Allow empty publication** is
explicitly enabled.
