# Changelog

## 0.1.9

- Capture Hovertravel's hidden disruption-contingency detail when service is not green.

## 0.1.8

- Add Hovertravel's official Ryde–Southsea hovercraft service status.
- Include Hovertravel disruption details only when its traffic light is not green.

## 0.1.7

- Extract only visible Red Funnel advisory text so embedded styles are excluded.

## 0.1.6

- Treat a successfully loaded Red Funnel service with no current notice as good service.
- Hide explicitly dated planned withdrawals until an affected local date.
- Collect all Red Funnel override notices so vehicle and Red Jet updates remain separate.

## 0.1.5

- Remove unnecessary blank lines from formatted operator updates.

## 0.1.4

- Fit the dashboard into HLM's available kiosk viewport without an outer scrollbar.
- Keep ferry content touch-scrollable and make operator links 108 px finger targets.
- Match established HLM kiosk label sizing at 1920 × 1080.

## 0.1.3

- Suppress Wightlink's recurring restricted-passenger-number notices.
- Avoid repeating a service update as an identical advisory.
- Improve paragraph and section spacing for long operator updates.

## 0.1.2

- Restrict Wightlink advisories to the official Travel Updates accordion.
- Read Red Funnel's active override notice without timetable contamination.

## 0.1.1

- Retry transient Chromium navigation failures.
- Isolate each operator scrape in its own browser page.

## 0.1.0

- Initial private development build.
- Collect current Red Funnel, Red Jet and Wightlink service status.
- Collect route-specific operator advisories.
- Expose a versioned JSON API for Holiday Let Manager.
- Provide grouped car-ferry and foot-passenger dashboard cards.
- Retain the last successful result when an operator source fails.
