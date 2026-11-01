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

The [Sheets architecture](hlm_sheets_service/ARCHITECTURE.md) and
[parallel feed design](hlm_sheets_service/PARALLEL_FEED_DESIGN.md) describe the
live and candidate paths. The candidate built on 12 September 2026 remains
under comparison; it has not replaced the production feed.

## HLM Guest Guide

`hlm_guest_guide` is the local guest-facing web application for Crossjack and
Skysail: property-specific house instructions, manuals and policy PDFs, plus a
shared categorised places list ordered by distance from the selected property.
Content is maintained in a private Google Sheet, with Markdown formatting and
locally bundled emoji. The guide is installed as version **0.5.1** and ready for
testing with the new kiosk; final kiosk layout, privacy notice and credits are
owned by the kiosk project.

See the [guide README](hlm_guest_guide/README.md),
[kiosk handover and exact iframe URLs](hlm_guest_guide/KIOSK_HANDOVER.md), and
[deployment, validation and rollback record](hlm_guest_guide/OPERATIONS.md).
The local guide port 8099 is not intended for public internet exposure.

## HLM Guide Sheets Service

`hlm_guide_sheets_service` is the guide's separate private Google integration,
installed as version **0.2.0**. It provides validated content publication,
read-only Drive attachment access and separately authenticated usage export to
the guide workbook. Word/Google Docs policies are served as cached local PDFs.
Detailed kiosk usage and exact completed searches expire after 12 calendar months.

It has no host port and does not replace or modify the HLM Exchange service.
Reader/writer credentials remain in masked HA configuration. See the
[private guide service README](hlm_guide_sheets_service/README.md).

## Holiday guide calendar (external source)

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
The [as-built architecture](hlm_ical_aggregator/ARCHITECTURE.md) and
[Production cutover report](hlm_ical_aggregator/session-reports/2026-09-04-icalendar-aggregator-production-cutover.md)
record the current deployment, migration and rollback position.

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
- Do not expose the guest guide or the external-source calendar feed to the public internet.
- Keep the Guide Sheets Service internal; the kiosk must call the guest guide,
  not Google or the private service directly.
- Do not expose the HLM iCalendar Aggregator feed port to the public internet.
- Keep source URLs and Google publisher credentials in runtime configuration,
  never in Git.
- Do not expose the IOW Ferry Status API outside the trusted local network.
- Give each kiosk its own MQTT login and never commit the live agent JSON file.
- Keep the Chromium DevTools endpoint bound to `127.0.0.1` only.

## Repository maintenance

See [repository and release policy](REPOSITORY_POLICY.md) for source ownership,
validation, update and rollback requirements. Automated checks are defined in
`.github/workflows/checks.yml`.
