# HLM Guide Sheets Service — Phase 1

This is a separate private HA add-on following the canonical HLM Sheets Service
0.4.0 pattern. It does not alter, repoint or relax any existing HLM routes.
The canonical source version was inspected locally; the live installed HLM
version has not yet been verified. No credentials have been read, copied,
rotated or granted new permissions by this implementation.

## Boundaries

Guide HA app → authenticated internal HTTP → Guide Sheets Service → Google REST.
Only this service receives the existing approved Google reader/writer identities
and key material through masked options. Container-local credential files have
mode 0600. Keep its HTTP port internal; its config intentionally has no host
port mapping, ingress, public Apps Script deployment or spreadsheet publishing.
The guide app holds app-specific read/write bearer tokens, never Google keys.
Use different tokens, each at least 32 characters; do not reuse HLM's working
tokens or change its existing credentials.

- `GET /api/v1/guide`: read token, validated publication envelope version 1.0.
- `GET /api/v1/health`: read token, source/publication/read/write diagnostics.
- `GET /api/v1/files/<drive_id>/metadata` and `/content`: read token, only
  published attachments in the validated guide; no arbitrary Drive paths.
- `POST /api/v1/usage`: write token, strict guide usage schema, batches 1–100,
  separate enable flag, fixed Stats destination, RAW append, serialisation,
  immutable-ID dedup and ambiguous-response recovery.
- `GET /healthz`: availability only, no credentials or configuration values.

`api_token` never grants event writes. `usage_write_token` never grants guide
reads. There is no arbitrary range/read/write API. Google permissions remain
workbook-wide, rather than being restricted to a tab by Google.

## Publication contract

Manual editing tabs remain friendly and unchanged. A hidden **Guide Publication
v1** tab is the generated boundary. Its exact headers are:

`schema_version, record_type, record_id, record_json, source_revision, published_at_utc`

Each row has schema version `1.0`, an allowlisted entity/table name, a stable
unique ID, a typed JSON record, the SHA-256 of the complete canonical source and
an aware UTC publication timestamp. Category links use `place_id:category_id`.
The canonical allowed fields are in `FIELDS` in service.py. Numeric fields must
be finite numbers or blank; booleans must be booleans or blank. Missing required
IDs/status/links, unexpected fields, duplicate IDs, formula errors, inconsistent
checksums, invalid types and future timestamps are rejected. A record is limited
to 45,000 characters for the Sheets cell boundary. Publication includes Draft
and Archived records so relationships remain consistent; the guest app applies
its normal Published-only rule and does not expose the publication route.

Every ten minutes the service reads and validates the editing tabs through the
read identity. When the content hash changes, and publication writes are enabled,
it uses the writer identity to atomically replace the publication range using RAW,
clear obsolete tail rows and verify the result through the reader. This is a
service-generated publication, not a NOW()-based clock or a public Apps Script.
The writer is explicitly allowed only to replace this publication and append Stats.

The publication timestamp changes only for a changed source revision. Repeated
polls do not make an old publication appear newly edited. `source_modified_at`
is deliberately unknown: fetching the sheet does not establish the human edit
time. Health distinguishes successful source validation, publication time,
successful app reads and successful Google writes. The service fails closed on
source errors or a source-verification age above 30 minutes. Old unchanged guide
content remains valid when the source has been freshly verified. The guide app
retains its last good local snapshot/files if the private service is unavailable.

## Usage contract and privacy

See app/usage_stats.py and the app README. No booking lookup is performed.
The server queues events locally. Exact search text and result counts are recorded
only when a search completes, not per keystroke. Kiosk names must match the
configured property registry (`kiosk_properties_json`). They are configuration
labels, not proof of a physical device's identity. Read/write tokens stay on the
server; kiosk pages post only to the guide app's local usage route. Stats is
append-only from the private HTTP API. No search or credential payloads are logged.
Worksheet retention has not been automated; agree the retention period and policy
wording before guest collection. Preview is unconditionally excluded.

## Configuration and safe activation

1. Verify the live HLM Sheets Service version without changing it. Securely reuse
   its approved Google identities/key material in this service's masked options.
   Do not print JSON, keys or tokens, put them in Git, or change HLM's working setup.
2. Verify reader client_email has Viewer on the guide workbook and its file folders.
   The reader also needs read-only Drive scope for attachment downloads. This is
   additional to HLM's Sheets-only read scope; the Google identity/key is reused.
   Verify writer client_email has Editor on the guide workbook. No Drive write scope.
3. Configure new `api_token` and `usage_write_token`. Enable publication writes;
   keep usage writes disabled until controlled test reconciliation passes.
4. Install this service with no host port. Confirm its actual Supervisor hostname;
   it will typically resemble `<repository-prefix>-hlm-guide-sheets-service:8787`.
5. Set the guide app's `sheets_service_url`, `sheets_read_token` and
   `sheets_write_token`; set its property and configured kiosk label. Keep the
   content reader read-only. Enable usage only for the non-preview installation.
6. Test with no real guest activity first. Confirm denied tokens, invalid data,
   stale source verification, missing file permissions, duplicate/retried events,
   Google outages/restarts, closed browser tabs and actual workbook writes.
   Label controlled test events with a separate configured test kiosk name.
7. Check existing HLM reads/writes remain unchanged before enabling guest collection.

Source and private-service tests run with:
`python -m unittest discover -s private_sheets_service -p 'test_*.py'`.
The build script produces two installable add-on folders without credentials.
Hardware installation, live account permission verification and Google end-to-end
tests remain outstanding until secure HA configuration is available.

## Backup and rollback

Back up the workbook, HA add-on configuration and guide data directory before
activation. Keep private backups encrypted/access-controlled because the usage
outbox contains searches. Disable usage collection to stop new events, preserving
pending events. Disable the new add-ons to roll back; restore the previous guide
package/cache for the local preview. Existing HLM add-ons and Exchange routes are
not modified by this rollout. Do not restore an old sheet layout over later
manual edits. Publication is generated; preserve the editing tabs and Stats data.
