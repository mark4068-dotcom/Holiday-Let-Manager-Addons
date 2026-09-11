# Crossjack combined public-events kiosk rollout — 11 September 2026

## Outcome

The Crossjack **Events & Places** view now combines HLM Guest Guide local
events with the curated Visit Isle of Wight feed. HLM iCalendar Aggregator
0.4.0 supplies the kiosk-safe JSON projection at `/public-events.json`.

The projection deliberately reads only the `guest-guide` and `viow` cached
sources. Crossjack and Skysail Guesty booking calendars are excluded. External
website links are emitted only for VisitIOW records with a validated HTTP(S)
`X-HLM-EVENT-WEBSITE`; local-event links remain disabled because the
third-party Guest Guide did not handle them reliably in the kiosk.

## Production configuration

- REST entity: `sensor.hlm_public_events`
- App endpoint: `http://32662a46-hlm-ical-aggregator:8789/public-events.json`
- Dashboard card entity: `sensor.hlm_public_events`
- Card resource: `/local/hlm-guest-guide-card.js?v=1.1.0`
- Favourite places remain supplied by `sensor.hlm_guest_guide_favourites`.

Before the change, dated rollback copies of the REST configuration, dashboard
storage and JavaScript card were retained on Production Home Assistant with the
suffix `before-public-events-20260911`.

## Verification

- Home Assistant configuration check passed before restart.
- Production app version: 0.4.0.
- Public feed: 73 events (6 Guest Guide and 67 VisitIOW).
- VisitIOW records with an external website: 66.
- Guest Guide records with an external website: 0.
- The restarted dashboard rendered the combined event cards, source badges,
  descriptions and VisitIOW website buttons successfully.

## External-link correction

Testing found that VisitIOW destination URLs were being passed through the
legacy `hlm-external-link.html` iframe wrapper. Sites that disallow iframe
embedding then displayed “refused to connect”, despite the underlying URL being
valid. The card was corrected to open validated VisitIOW URLs directly with
`target="_blank"`; the kiosk external-window controller handles that popup.
Local Guest Guide event links remain disabled. The corrected card resource is
`/local/hlm-guest-guide-card.js?v=1.1.1`.
