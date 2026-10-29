# HLM Guest Guide

Local kiosk guide for Crossjack and Skysail. One shared places catalogue, separate house instructions and files for each property. This is a reviewable prototype; it has not yet been installed or tested on the Mac mini.

## Editing and publishing

Edit the HLM Guide workbook in the sailcottagesha Google account. Keep the column headers and IDs unchanged. Give every house topic a category. A topic may have text, attachments, an external link and a video link.

Files are registered in the Files tab. Paste the Drive sharing link and set the owning property/topic reference or shared place reference. Keep independent Drive copies in each property's folder even when the content starts out identical. Changes to a file with the same Drive ID are picked up at the next successful refresh.

Imported content remains Draft for review. The normal guest app shows only Published rows, including their parent property and relevant category/attachment rows. Archived content is hidden. The private local preview includes Draft rows and is visibly labelled.

Fill in verified latitude and longitude for each property and place to enable distance ordering. Distances are straight-line miles, not walking/driving routes. The Google Maps QR code opens the public location link on a phone without requiring access to the kiosk LAN.

## Home Assistant installation

1. Back up Home Assistant. Copy this entire app directory to `/addons/hlm_guest_guide` on the Home Assistant machine. Refresh the local app/add-on store, then install **HLM Guest Guide**. The image is built locally for amd64.
2. Set `property_id` to `crossjack` or `skysail`. Configure a separate instance/server for each property's kiosk. Guests cannot switch properties in normal mode.
3. Grant the existing runtime service account `hlm-sheets-reader@hlm-sheets-service.iam.gserviceaccount.com` Viewer access to the guide workbook and guide files folder. This sharing still needs to be completed and verified. Do not make the files public. Editing and migration use the sailcottagesha account; the automated reader has no write scopes.
4. Install the separate HLM Guide Sheets Service package with no host port. Configure its masked Google reader/writer credentials securely using the approved HLM identities, then configure this guide app with `sheets_service_url` and separate `sheets_read_token` / `sheets_write_token`. Google service-account keys belong only in the private service; they are not guide-app options. See the private service README for publication and access tests.
5. Start the app and open `http://HOME_ASSISTANT_LAN_ADDRESS:8099` from the kiosk. A Home Assistant webpage dashboard can point to the same address where the browser allows it. An HTTPS dashboard may block an HTTP embedded frame; a direct kiosk page or an existing HTTPS reverse proxy can resolve that.
6. Publish a small reviewed selection first. Confirm instructions, photos, PDF navigation and QR codes on the actual kiosk, then publish the remaining approved content.

The guide refreshes from the authenticated private service every ten minutes and keeps a last-successful local copy. After an initial successful sync, cached guide text, photos and PDFs remain available during an internet outage. External websites, YouTube, maps and live Google information need internet access. A failed refresh keeps the previous complete copy. Local old file versions are retained, so monitor disk usage over time.

The app listens on LAN port 8099 and provides no guest authentication. Use only the intended trusted kiosk/guest LAN, with no internet port forwarding. It has no Home Assistant controls or API access. The default standalone Python mode binds only to localhost. The content preview defaults to localhost; an explicit `--lan-preview --host PRIVATE_LAN_IP` enables owner-authorised local kiosk review of Draft content.

## Optional live Google information

Google Places is disabled until an API key, a terms URL and a privacy URL are configured. It makes an on-demand Place Details request when a guest asks for current information and the entry has a verified Google place ID. The key remains on the server. Returned opening information is not saved into the guide cache. Google attribution is shown with the result.

`places_daily_limit` is a local request-count limit, not a Google billing cap or a monetary guarantee. Configure Google Cloud API restrictions, quotas and billing alerts separately before enabling paid requests. No Google key or billing setup is supplied or enabled here.

## Local review and checks

Install `requirements.txt` in a Python environment, then run `python guide.py --data PATH_TO_CACHE --preview`. A migration-only helper in the parent workspace prepares a private local cache; migration source files and guest data are intentionally excluded from the installation package.

Run the server checks from the parent directory with `python -m unittest discover -s app -p 'test_*.py'`. Automated checks cover publication rules, property separation, attachment ownership, distance calculation, safe links and retaining a complete previous cache on refresh failure. The kiosk browser has also been used to check category filtering, property switching, the PDF viewer and the Maps QR panel. Hardware installation and a real read-only Google sync remain to be tested.

The PDF viewer uses the bundled PDF.js distribution; its license is in `web/vendor/LICENSE`.


Location data updated 29 October 2026: all 124 places have coordinates and Google Place IDs; both properties have reference coordinates. Mapped venue centres support approximate straight-line distance sorting; entrances and parking remain subject to owner review. OpenStreetMap coordinate data is © OpenStreetMap contributors, available under ODbL: https://www.openstreetmap.org/copyright. Coordinate provenance is retained in the local migration archive. Google Place IDs identify listings and do not provide live opening hours without the separate Places integration.


## Manual workbook layout
The workbook uses readable column names; `sheet_schema.py` converts them to internal fields. Places categories use the multi-select dropdown sourced from Categories; the reader accepts its comma-separated values and legacy semicolons. The old Place Categories tab is no longer read. Files accepts a Drive sharing link and derives the Drive file ID. Internal permanent references are hidden in the final column; retain existing references and assign a unique code for each new place, house item, property or category. Additional house-guide links use one line per link: `Button label | https://example.com`. Start Here documents every editable column. The full pre-simplification values and coordinate provenance are saved in `migration/manual-editing-backup-2026-10-29.json` in the project workspace. This workbook needs the updated app, including `sheet_schema.py`.

## Usage statistics (0.3.0)

`usage_stats.py` reuses the HLM Sheets Service approach: service-account OAuth, separate read/write clients, batches of at most 100 events, a serialised exporter, immutable event IDs and an ID re-read following an ambiguous append failure. It adapts that pattern to the guide's own 12-column Stats schema; it does not send events to HLM's existing access/climate/EV endpoint or modify that service.

The private service reader retains Sheets/Drive read-only scopes. Its separate Google writer has only the Sheets scope; its destinations are fixed to the guide workbook's Stats and generated publication tabs. The guide app itself has only private HTTP bearer tokens. Google permissions are workbook-wide: use a dedicated guide writer account where possible; code-level destination restriction is not Google tab-level access control. Do not put credentials in browser code, spreadsheet cells or source control. No Google writer credentials or workbook edit permissions have been provisioned by this implementation.

To activate on HA, configure the private service and its separate write boundary first, then set `kiosk_id`, `usage_stats_enabled: true`, and the guide app's masked `sheets_read_token` / `sheets_write_token` options. Grant the private service writer the required access to the guide workbook, with content-sheet protections if desired. The pre-created Stats header must remain unchanged. `allowed_kiosk_ids` can list the configured kiosk names for an instance; a kiosk may use `?kiosk=crossjack_hall`. Without a URL value it uses the configured default. Kiosk labels are operator-assigned names, not device authentication. Configure a distinct label on each kiosk; never derive it from an IP, cookie or browser fingerprint. The server supplies the configured property and the received-at UTC timestamp.

Statistics remain disabled by default and are unconditionally disabled in preview, including LAN preview. The current preview produces no guest statistics. No live Google statistics export has yet been tested: a configured writer and a controlled non-preview test are required before claiming end-to-end operation.

Events: page view, section selected, topic/place opened, document opened, photos shown with an entry, external-link tapped, QR displayed, category/favourites filter selected, and completed search with result count (including zero). Photo/QR display does not establish viewing/scanning; document-open does not establish reading. External-link events store a label and item reference, not the destination URL. Searches retain their exact text (up to 2,000 characters) and record active category/favourites filters. Submission means Enter, leaving the search field, opening an item or leaving the page; per-keystroke filtering is not logged. No names, bookings, HTTP client IPs, user agents, cookies, persistent visitor IDs or booking joins are collected by this feature. Typed searches are not screened and may themselves contain personal information.

Events first queue in browser memory and retry while the page remains open; if the kiosk cannot reach the guide server and is closed/restarted, these unacknowledged browser events may be lost. After the server acknowledges an event, SQLite retains it across restarts and Google outages. Pending events are not expired; the local uploaded-ID ledger retains the latest 10,000 records. The Stats worksheet has no automatic deletion/retention rule yet. Set an appropriate retention schedule before guest collection. Server HTTP access logging is disabled. Searches and event bodies are not written to normal/error logs. RAW Sheets writes prevent searches beginning with `=` from becoming formulas. Local outbox and credential files are owner-readable only.

### Draft privacy-policy addition — review before enabling guest collection

We use usage information from our property guide kiosks to understand which information is helpful and improve our guides. This includes the property and configured kiosk name, time of interaction, guide pages and places opened, document and external-link selections, use of filters, and location QR codes displayed. We also record search terms exactly as entered and the number of results returned, including searches with no results. Please avoid entering personal or sensitive information into the guide search.

We do not link this information to booking records, and this feature does not collect guest names, IP addresses, advertising identifiers, cookies or browser fingerprints. Search terms may contain personal information if someone chooses to enter it. Usage records are stored on our local guide server and transferred to our private Google spreadsheet for analysis by authorised staff. Operational measures limit access to the records.

Before publication, complete the retention period, controller/contact details, applicable rights and lawful-basis assessment in the existing privacy policy. Raw records currently remain in the Stats worksheet until removed; this draft must not promise an automatic deletion period that is not implemented. Include Google in the policy's relevant service-provider/transfer information as appropriate to the organisation's existing arrangements. This text is a draft, not a live policy update.


The final Google integration is a separate private HA service, documented in `private_sheets_service/README.md` in the project workspace. Build both installation folders with `python build_packages.py`. The old direct-service-account option has been removed from the guide app. Use the two-add-on package `hlm-phase1-addons.zip`; do not use an older direct-Google installation package.
