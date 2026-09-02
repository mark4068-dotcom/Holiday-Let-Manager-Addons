# Changelog

## 0.2.0
- Add privacy-safe daily kiosk metrics with a rolling 12-month retention window.
- Expose local `POST /metrics` and `GET /metrics.json` endpoints for Home Assistant reporting.

## 0.2.1

- Add a metrics summary endpoint for Home Assistant totals and latest usage.

## 0.1.6

- Remove third-party “View event” and “Guide details” links from the guest page.
- Keep event information and working Directions links available without navigating away from the kiosk.

## 0.1.5

- Add an adjustable event horizon to the app configuration, defaulting to 10 days.
- Apply the horizon consistently to the guest page, JSON feed and ICS calendar.
- Keep events already in progress and include events starting on the horizon boundary.

## 0.1.4

- Wait for each favourite-place detail route to finish loading before extraction.
- Scope descriptions, addresses and opening hours to the selected place instead of the whole page.
- Reject incomplete place details rather than assigning unrelated recommendation text.

## 0.1.3

- Add a responsive guest display at `/guest`.
- Present upcoming events as easy-to-scan cards.
- Present favourite places in a touch-friendly swipe and arrow carousel.

## 0.1.2

- Initial repository release.
- Generate ICS and JSON feeds from shared My Holiday Guide events.
- Extract shared favourite places and their visitor information.
- Retry transient Chromium network-change errors on Home Assistant OS.
- Preserve last-good data after failed or incomplete scrapes.
## 0.2.2

- Preserve event titles when the guide detail layout exposes date text before the title.
