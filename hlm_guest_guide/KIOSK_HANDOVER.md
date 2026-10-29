# Guest guide service: kiosk handover

## Purpose and ownership

HLM Guest Guide is a local web application for property-specific house instructions, photos/PDFs and a shared, categorised places guide. Places sort by geographic distance from the selected property. Google Maps QR codes let guests take a location onto their phones. what3words is not used. Live Google opening-hours lookup is not enabled; Google Maps links work without it.

The kiosk embeds this existing application; it does not read Google Sheets or hold Google credentials. Keep the guide and its private Google service separate from the existing HLM Exchange service. No changes to bookings, access or climate services are required.

## Live browser endpoint and exact URLs

Base URL: `http://192.168.0.236:8099/`. This is the HA host, not the old Mac preview at 192.168.0.64. The browser/Raspberry Pi needs LAN access to this host and port.

| Property | Full embedded guide (guide section controls visible) |
| --- | --- |
| Crossjack | `http://192.168.0.236:8099/?property=crossjack&embed=1` |
| Skysail | `http://192.168.0.236:8099/?property=skysail&embed=1` |

`embed=1` hides the guide's branding header and entire footer, including its attribution, sync-time and privacy/footer links. It uses the iframe width. Content headings, search, category filter, favourites, detail dialogs and document controls remain. Standalone URLs without embed keep header/footer.

If the kiosk supplies the section navigation, add `nav=0` and select a starting section:

- Skysail house: `http://192.168.0.236:8099/?property=skysail&embed=1&nav=0&section=house`
- Skysail places: `http://192.168.0.236:8099/?property=skysail&embed=1&nav=0&section=places`
- Skysail return directions: `http://192.168.0.236:8099/?property=skysail&embed=1&nav=0&section=home`

Use the same URLs with `property=crossjack` for Crossjack. Without a section parameter, house is the default. Only `house`, `places` and `home` are recognised. An unknown property is rejected rather than falling back to another property's content.

## Host iframe behaviour

Use a normal iframe or HA webpage card with the complete URL above. Give it the available content height and allow scrolling. There is no postMessage navigation/resize API: the host changes iframe src to change property/section. Do not recreate the iframe on unrelated dashboard updates; reloads count as page views and discard unfinished in-memory searches. Dialogs/PDF rendering occur inside the frame. External links/videos may open a separate tab. An iframe sandbox must permit the application's scripts and same-origin local requests; do not add a restrictive sandbox without testing documents and external links.

Current service is HTTP. An HTTPS parent may block it as mixed content: use a suitable HTTPS reverse proxy for the guide if the kiosk dashboard uses HTTPS. Do not disable browser security checks. No internet/public exposure is needed. Kiosk layout/theme/navigation work belongs to the kiosk context.

## Property and statistics configuration

The shared HA installation explicitly allows `crossjack` and `skysail`. It maps `crossjack_hall` to Crossjack and `skysail_hall` to Skysail. The view chooses the matching default kiosk label, so the property URLs alone are enough for these two kiosks. An optional `kiosk=` query parameter is for another deliberately configured kiosk; add its mapping to BOTH add-ons before use. Kiosk names are configuration labels, not authenticated device identities. Any browser opening the same guide URL is counted under that configured label.

The browser sends usage only to its guide server. The guide queues records locally; its separate private service uploads to the private workbook Stats tab roughly every minute. Completed searches retain exact text and result count, including zero; typing each character is not logged. Page/section/item/document/link/filter interactions and photo/QR display are also recorded. Displaying a QR does not prove scanning, nor does opening a manual prove reading. Records are not joined to bookings; no client IP, cookie, fingerprint or persistent visitor identity is collected by this feature.

Both collection and private usage writes are enabled. Detailed live Stats and local records expire after 12 calendar months, including search text. No longer-term aggregate archive is currently created. HA backups and Google version history have a separate lifecycle. Preview remains excluded.

## REQUIRED kiosk attribution and privacy presentation

The owner has assigned these responsibilities to the outer kiosk because embedded mode removes the guide footer. Provide them before guest rollout:

1. In a readily accessible kiosk credits/about area, include the coordinate-source credit **© OpenStreetMap contributors** linked to `https://www.openstreetmap.org/copyright`, and identify ODbL where the kiosk lists data licences. Keep this reachable from guide/map/location pages. Do not remove any provider attribution rendered inside a document, map or future Google live-data result.
2. Display an accessible link to the owner's CURRENT published privacy policy from the guest guide/search experience. Obtain the final policy URL from the owner; do not link to a draft or invent a URL. The owner confirmed the policy was updated on 29 October 2026.
3. Put a concise collection notice in the kiosk guide/search UI, for example: **“We record guide usage and search terms to improve our guest information. Please do not enter personal or sensitive information. See our Privacy Policy.”** Link Privacy Policy to the published policy. This is notice, not an optional analytics consent toggle.
4. The policy addition covers property/kiosk, interaction time/actions, exact searches/result counts, local and private Google spreadsheet storage, no booking linkage, proposed legitimate-interests basis, objection/contact details and **12-month** detailed retention. The owner is responsible for the final lawful-basis assessment, controller/contact/rights wording and applicable Google/backup/transfer disclosures. Do not describe raw searches as fully anonymous.

Embedding the guide does not automatically put any of this wording into the parent dashboard. The kiosk implementation must add it. Until complete, use standalone mode if the host cannot provide the required information.

## Data and operational contract

Content is maintained manually in Sailcottages_hlm_guest_guide:
`https://docs.google.com/spreadsheets/d/1TwFhxp1U1AiuIaoCRJ9RmROQQncbm_ctdncKwUaJOck/edit`.

Only Published content is served to guests; Archived remains excluded. The private source refresh and guide refresh run approximately every 10 minutes, so edits may take two refresh cycles to appear. File updates are verified and cached locally before a complete new snapshot is exposed. Last good content/PDFs remain usable through Google/service outages and guide restart. Internet is still required for external sites, videos and phone Google Maps destinations.

HA add-ons: `local_hlm_guest_guide` (public LAN port 8099), `local_hlm_guide_sheets_service` (internal port 8787, no host port). The kiosk must never call the private service directly. Google reader is read-only; a separate writer handles publication and append-only HTTP usage events plus server-owned retention. Read/write bearer tokens and Google keys remain in masked HA configuration. No credentials belong in dashboard YAML, iframe URLs, source control or this handover.

Diagnostics: `GET /api/health` on the guide returns snapshot availability, preview and sync-failure flags, without secrets. For a freshness issue show a small unavailable/stale message; do not replace existing cached content just because Google is offline. The guide already shows its own sync-warning banner even in embedded mode.

## Verification checklist for the kiosk context

- Open each property's URL: correct house instructions, return-location QR and distance order.
- Check photos and PDF next-page/zoom controls inside the actual iframe size.
- With nav=0, host buttons reach house/places/home without stale property selection.
- Confirm host privacy notice/link and attribution are reachable.
- Confirm Stats records the correct property/kiosk and searches once with result count.
- Check a cached guide/manual remains usable during an internet outage.
- Do not change existing HLM Exchange/service settings for kiosk integration.
