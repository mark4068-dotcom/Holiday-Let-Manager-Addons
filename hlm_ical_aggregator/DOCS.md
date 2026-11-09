# HLM iCalendar Aggregator

This app combines independently filtered remote ICS calendars into one local
calendar for Home Assistant. It is a diary/display service only. Do not use its
calendar as HLM's booking or operations source; those facts come from the
private Google Sheets exchange feed.

## Initial source configuration

Add the agreed booking entries under **Sources** in the app configuration form. Keep the
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
```

The old `guest-guide` input is disabled in production and its scraper app is
uninstalled. Do not recreate it for the new guide. Version 0.4.3 preserves the
booking and VisitIOW feeds locally while publishing only VisitIOW to Google.
See [retirement, testing and rollback](session-reports/2026-11-09-old-guide-retirement.md).

## Home Assistant calendar

After all sources report a successful refresh:

1. Add Home Assistant's **Remote Calendar** integration.
2. Name it `HLM combined calendar`.
3. For an installation from `Holiday-Let-Manager-Addons`, use
   `http://32662a46-hlm-ical-aggregator:8789/combined.ics`. For a manually
   installed local app, use
   `http://local-hlm-ical-aggregator:8789/combined.ics` instead. Confirm the
   hostname shown on the app's Info page.
4. Enter the optional feed username and password configured in this app.
5. Disable the integration's default polling and call
   `homeassistant.update_entity` every 15 minutes.

The local app port must not be forwarded through the router or directly exposed
through Home Assistant Cloud.

## Visit Isle of Wight Phase 1 feed

Set **Enable VIOW events** to on to collect the public Visit Isle of Wight
What's On listings. Collection is cached for 24 hours by default even though
the other calendar sources refresh more frequently. Events have a visible
`VisitIOW — ` title prefix, stable `VIOW-<product-id>` identity and a link to the
original listing. Where the listing supplies **Visit website**, the destination
is retained separately in the calendar description and
`X-HLM-EVENT-WEBSITE` property.
Calendar descriptions also include the listing's category, a concise About
excerpt, guide price and telephone number when those fields are available.
Listings spanning more than 31 calendar days are excluded because they are
long-running attractions rather than useful diary events. Diagnostics report
the number removed as `long_events_filtered`.

The source is available separately at `/sources/viow.ics` and is also included
in `/combined.ics`. The legacy guide source is disabled; no third-party guide scraping is required.

## Crossjack kiosk public-events view

`/public-events.json` is the dashboard projection for the Crossjack **Events &
Places** view. It allows only enabled `guest-guide`/`viow` caches; with the legacy source disabled, production returns only VisitIOW and cannot expose Guesty booking events. Each record identifies its
source. An `external_url` is populated only for VisitIOW records with a valid
HTTP(S) `X-HLM-EVENT-WEBSITE`; local Guest Guide records always return an empty
external URL because the third-party guide did not handle kiosk links reliably.

The dashboard opens VisitIOW `external_url` values directly in a new window.
It must not route them through `hlm-external-link.html`, because that legacy
page embeds its destination in an iframe and many event websites prohibit
iframe embedding. The Crossjack kiosk external-window controller manages the
resulting direct-link popup.

Current V2 kiosks consume the existing public JSON/status endpoints and use the
new guide for places and house content. The older custom card example in
`homeassistant/` is historical; do not restore its old favourites dependency.
Keep `sensor.hlm_public_events`, `/combined.ics` and source status contracts.

## Endpoints

- `GET /combined.ics`
- `GET /sources/<source-id>.ics`
- `GET /public-events.json` — kiosk-safe Guest Guide and VisitIOW event data;
  deliberately excludes all booking sources
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

## Google publication scope (0.4.2)

Google Calendar publication uses only the enabled `viow` source cache. The combined calendar, individual booking calendars, public events and status endpoints remain unchanged. Switching an existing mixed Google destination removes HLM-managed non-VisitIOW events there; booking events remain available locally to HA. Publication is skipped when VisitIOW is disabled or its cache is missing. Existing cache fallback and empty-publication protection still apply.
