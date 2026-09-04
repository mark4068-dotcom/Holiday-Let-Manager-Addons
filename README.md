# Holiday Let Manager add-ons

Private Home Assistant add-ons supporting Holiday Let Manager.

## HLM Sheets Service

`hlm_sheets_service` reads the private v1.0/v1.1 published tabs from the HLM
Exchange workbook and exposes authenticated JSON status feeds only on Home
Assistant's internal add-on network. It also validates and idempotently appends
HLM operational events to `30_hlm_events` through a separately authenticated
write boundary.

It does not publish a host port, expose the workbook, or include credentials.
The detailed Dev HA installation procedure is in
[`hlm_sheets_service/README.md`](hlm_sheets_service/README.md).

## HLM Guest Guide

`hlm_guide_calendar` reads the shared events and favourite places from the
public My Holiday Guide page once every 24 hours. It exposes a Home
Assistant-compatible ICS calendar, structured JSON feeds, and an admin-only
status panel. A failed or incomplete scrape never replaces the last successful
data.

The calendar/feed port is intended for the local HA network only and must not
be forwarded through the router. Installation and Remote Calendar setup are in
[`hlm_guide_calendar/DOCS.md`](hlm_guide_calendar/DOCS.md).

## HLM iCalendar Aggregator

`hlm_ical_aggregator` combines multiple ICS sources into one display/diary
calendar. It applies source-specific filters and title prefixes, preserves
recurrence and timezone data, namespaces event identifiers, deduplicates
events, and retains last-known-good output when an upstream source fails.

It is not a booking or operational data source; the private HLM Google Sheets
feed remains authoritative. Installation, feed configuration, and optional
outbound-only Google Calendar publishing are documented in
[`hlm_ical_aggregator/DOCS.md`](hlm_ical_aggregator/DOCS.md).

## IOW Ferry Status

`iow_ferry_status` collects current service conditions and operator advisories
for Red Funnel, Red Jet and all three Wightlink Isle of Wight routes. Holiday
Let Manager consumes its versioned JSON API, while its admin dashboard groups
the services into car-ferry and foot-passenger cards. Timetables are
intentionally excluded. Installation details are in
[`iow_ferry_status/DOCS.md`](iow_ferry_status/DOCS.md).

## Crossjack kiosk companion agent

`agents/crossjack_kiosk` contains the versioned Raspberry Pi monitoring and
control agent for the Crossjack guest kiosk. It publishes health and a tightly
allowlisted set of controls to Home Assistant through MQTT Discovery. It also
contains the Chromium kiosk launcher, narrow reboot-only sudoers rule and the
HLM Operations dashboard view.

This component runs on the remote Pi, so it is not presented as a Home
Assistant add-on. Install the official Mosquitto Broker from the Home Assistant
add-on store; install/update the companion agent on the Pi from this repository.
See [`agents/crossjack_kiosk/README.md`](agents/crossjack_kiosk/README.md).

## Security

- Keep the Google service-account JSON and bearer token in the masked add-on
  configuration, never in Git.
- Do not configure an internet-facing port, ingress, or reverse proxy.
- Do not expose the HLM Guest Guide feed port to the public internet.
- Do not expose the HLM iCalendar Aggregator feed port to the public internet.
- Keep source URLs and Google publisher credentials in runtime configuration,
  never in Git.
- Do not expose the IOW Ferry Status API outside the trusted local network.
- Give each kiosk its own MQTT login and never commit the live agent JSON file.
- Keep the Chromium DevTools endpoint bound to `127.0.0.1` only.
