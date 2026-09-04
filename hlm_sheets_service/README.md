# HLM Sheets Service add-on

This local Home Assistant add-on exposes the private `20_published_ha` v1.0
status contract, plus an isolated v1.1 draft, to Home Assistant on its internal
add-on network. It does not publish a host port or expose the workbook to the
internet.

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

The existing v1.0 and v1.1 status endpoints remain read-only and operate
independently. Version 0.2 added a separate, disabled-by-default event writer at
`POST /api/v1/events` for `30_hlm_events`.

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

The v1.0 validator accepts the approved access, Easee EV and climate event
types. Evohome context is restricted to the existing typed climate columns,
aware override timestamps, numeric bounds, known system/zone modes and the safe
`clear`/`fault` classification. Arbitrary Home Assistant attributes and private
Evohome routing identifiers are rejected. This validation expansion is add-on
version 0.3.0.

`GET /healthz` reports only whether the event writer is enabled; it exposes no
configuration values. Keep the writer disabled until a separate development
test range, writer account, token and end-to-end reconciliation have passed.
