# HLM Guest Guide

This app loads the configured public My Holiday Guide page once per day and creates:

- `events.ics` for Home Assistant's Remote Calendar integration;
- `events.json` for diagnostics and future dashboard cards;
- `favourites.json` for shared recommended places;
- a status page showing the last successful update and any extraction error.

The last successful files remain in place if the third-party page is unavailable or changes structure. A failed or empty scrape never erases the working calendar.

## Configuration

Keep the default Crossjack guide URL or replace it with another property URL from the same shared guide. The refresh interval defaults to 24 hours.

The feed username and password are optional. If supplied, enter the same credentials when configuring Remote Calendar.

## Add the calendar to Home Assistant

1. Start the app and wait until its status page reports at least one event.
2. Go to **Settings → Devices & services → Add integration**.
3. Select **Remote Calendar**.
4. Name it `Crossjack local events`.
5. Enter `http://HOME_ASSISTANT_IP:8788/events.ics`.
6. If configured above, enter the feed username and password.
7. Add the resulting calendar entity to a dashboard using Home Assistant's calendar card.

The app's port should not be forwarded through the router or exposed through Home Assistant Cloud.

## Diagnostics

Open the app from the Home Assistant sidebar to see its status. A manual **Refresh now** button is available for testing. Detailed messages are also written to the app log.
