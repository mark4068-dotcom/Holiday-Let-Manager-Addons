# Holiday Let Manager add-ons

Private Home Assistant add-ons supporting Holiday Let Manager.

## HLM Sheets Service

`hlm_sheets_service` reads the private `20_published_ha` tab from the HLM
Exchange workbook and exposes an authenticated JSON status feed only on Home
Assistant's internal add-on network.

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
- Give each kiosk its own MQTT login and never commit the live agent JSON file.
- Keep the Chromium DevTools endpoint bound to `127.0.0.1` only.
