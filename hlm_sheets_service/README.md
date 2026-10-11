# HLM Sheets Service add-on

Version 0.4.0 exposes v1.1 from `22_parallel_ha!A1:AA3` and generates
v1.0 compatibility from that same source. Both endpoints remain private and
authenticated on the internal add-on network. The separately authenticated
event append boundary is unchanged; no host port or public feed is introduced.

## Architecture and source migration

Both status versions require exactly Skysail and Crossjack and reject evaluation
timestamps older than 900 seconds or more than 120 seconds in the future.
The scheduled Apps Script clock publishes an explicit UTC timestamp; this is
model evaluation time, not proof of successful calendar or booking ingestion.

`GET /api/v1.1/health` uses the existing read bearer token and exposes evaluation
age, source checks, property counts and separate authoritative calendar importer
diagnostics. The importer heartbeat comes through `03_import_source_health!A1:K2`.
Its hourly success must be at most 5,400 seconds old; failed/running attempts do
not count as fresh. An upstream modification timestamp remains unknown if the
calendar source supplies none. `freshness_verified` and
`booking_transport_verified` remain false until the intervening booking-log
generation transport is verified. HTTP 200 from this route means diagnostics
are readable, not that all freshness checks passed.

`parallel_audit_enabled` retains its configuration name. On 0.4.0 it logs
production evaluation health and separate importer diagnostics every five
minutes, retaining 90 days of private history. Earlier comparison records
remain readable, but legacy/self-parity is not a production health signal.
See [audit logging](PARALLEL_AUDIT.md).

The old `21_published_ha_v1_1_draft` and `20_published_ha` tabs are not service
dependencies. The old public HA Apps Script deployment is archived; booking
ingestion, forms, PAT reports and changeover emails remain operational.
Consult the main HLM repository's 11 October session for actual deployment
status, observation evidence, trigger ownership and recovery instructions.

- [Architecture and data boundaries](ARCHITECTURE.md)
- [Parallel feed design, parity decisions and acceptance gates](PARALLEL_FEED_DESIGN.md)
- [12 September implementation and validation record](session-reports/2026-09-12-parallel-sheets-feed.md)

## Dev HA installation

1. Copy the `homeassistant/addons` directory to Dev HA's local add-on folder
   (`/addons`) and reload the Add-on Store.
2. Install **HLM Sheets Service** from Local add-ons.
3. Generate a bearer token on a trusted Mac using `openssl rand -hex 32`, then
   set it in the add-on's `api_token` option. Do not put it in Git.
4. Convert the existing Google service-account JSON to one line and paste it
   into the masked `google_service_account_json` option. The add-on validates
   it and writes a runtime-only owner-readable copy in its `/data` directory.
5. Start the add-on. Its log must show `Private Google Sheets status feed
   verified` with the expected property count and IDs. It logs neither
   credentials nor sheet values.

HLM uses the add-on's Supervisor-assigned internal hostname with the bearer
token. The endpoints are `/api/v1/status` and `/api/v1.1/status`; both remain
private and authenticated. Do not create a host port mapping, reverse proxy,
or public URL.

If Google is temporarily unavailable during startup, the add-on stays running
and retries on the next authenticated status request. The status response then
reports `unavailable` rather than making the internal endpoint disappear.

## Scope

The v1.0 and v1.1 status endpoints remain read-only and share the same
validated property source. A separate, disabled-by-default configuration gate controls
`POST /api/v1/events`; the writer is enabled in Production and writes
to `30_hlm_events`.

The writer requires all three options before it can start enabled:

- `event_write_enabled: true`;
- `event_sheet_range` set to `31_hlm_events_test!A:AG` for development (change
  it to `30_hlm_events!A:AG` only for the approved production cutover);
- a separate `event_write_token` containing at least 32 characters;
- `google_writer_service_account_json` for a service account with access only
  to the private Exchange workbook.

The read token and read-only Google credentials do not grant write access. The
endpoint validates the exact 33-column v1.0 envelope, limits batches to 100,
writes with `valueInputOption=RAW`, serialises appends, and deduplicates using
the immutable `event_id`. It rereads IDs after an ambiguous append failure so a
successful Google write with a lost response is not repeated. Normal and error
logs do not include event payloads, identities, or credentials.

HLM's event contract retains timezone-aware ISO-8601 source timestamps in UTC,
including the `Z` suffix. At the final worksheet boundary, add-on version 0.3.1
converts `timestamp`, `recorded_at`, `received_at`, and
`climate_override_until` to real Google Sheets date/time values in the
`Europe/London` timezone at millisecond precision. It formats those columns as
`dd/mm/yyyy hh:mm:ss`, so Sheets can sort, filter, and calculate with them and
daylight-saving conversion follows GMT/BST automatically. Other values still
use `RAW`, preventing text beginning with `=` from being interpreted as a
spreadsheet formula.

The v1.0 validator accepts the approved access, Easee EV and climate event
types. Evohome context is restricted to the existing typed climate columns,
aware override timestamps, numeric bounds, known system/zone modes and the safe
`clear`/`fault` classification. Arbitrary Home Assistant attributes and private
Evohome routing identifiers are rejected. This validation expansion is add-on
version 0.3.0.

`GET /healthz` reports only whether the event writer is enabled; it exposes no
configuration values. For a new environment, keep the writer disabled until a
separate development test range, writer account, token and end-to-end
reconciliation have passed. Production completed that activation gate on
4 September 2026; first natural-event reconciliation and pilot observation are
tracked in the main HLM repository.

## Redesigned feed cutover (0.4.0)

The production v1.1 range is `22_parallel_ha!A1:AA3`; its name is retained to
avoid unnecessary worksheet renames. v1.0 is a compatibility projection of
this same source. `21_published_ha_v1_1_draft` and `20_published_ha` are no
longer service dependencies. Both endpoints reject stale evaluation clocks.

`parallel_audit_enabled` remains the option name for compatibility. On 0.4.0
it records `audit_mode: production_health`, with healthy/error counts and
zero compared fields. Earlier matched/different records remain readable.
The authenticated `/api/v1.1/parallel-audit` routes and 90-day retention remain.
A successful evaluation heartbeat does not prove calendar-import freshness.

Activate the source clock and its UTC publication before installing 0.4.0.
See the main HLM repository's 11 October retirement session for deployment
status, trigger ownership, the source archive and preserved operational scripts.
