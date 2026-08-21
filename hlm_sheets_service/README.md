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

## Scope

This version is intentionally read-only. v1.0 reads only `20_published_ha`;
v1.1 reads only `21_published_ha_v1_1_draft`. They operate independently, so
a v1.1 draft issue cannot replace or alter the verified v1.0 path.
Append-only event export will be added separately after the status-feed cutover
is proven.
