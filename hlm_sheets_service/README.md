# HLM Sheets Service add-on

This local Home Assistant add-on exposes the private `20_published_ha` status
contract to Home Assistant on its internal add-on network. It does not publish
a host port or expose the workbook to the internet.

## Dev HA installation

1. Copy the `homeassistant/addons` directory to Dev HA's local add-on folder
   (`/addons`) and reload the Add-on Store.
2. Install **HLM Sheets Service** from Local add-ons.
3. Generate a bearer token on a trusted Mac using `openssl rand -hex 32`, then
   set it in the add-on's `api_token` option. Do not put it in Git.
4. Copy the existing Google service-account JSON to:
   `/addon_configs/local_hlm_sheets_service/google-service-account.json`
   on Dev HA. The add-on mounts only this dedicated folder at `/config`.
5. Start the add-on and verify its log shows no credential error.

The internal hostname is `local-hlm-sheets-service`; the future HLM client will
use `http://local-hlm-sheets-service:8787/api/v1/status` with the bearer token.
Do not create a host port mapping, reverse proxy, or public URL.

## Scope

This version is intentionally read-only. It reads only `20_published_ha`.
Append-only event export will be added separately after the status-feed cutover
is proven.
