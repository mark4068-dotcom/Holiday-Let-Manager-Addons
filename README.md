# Holiday Let Manager add-ons

Private Home Assistant add-ons supporting Holiday Let Manager.

## HLM Sheets Service

`hlm_sheets_service` reads the private `20_published_ha` tab from the HLM
Exchange workbook and exposes an authenticated JSON status feed only on Home
Assistant's internal add-on network.

It does not publish a host port, expose the workbook, or include credentials.
The detailed Dev HA installation procedure is in
[`hlm_sheets_service/README.md`](hlm_sheets_service/README.md).

## Security

- Keep the Google service-account JSON and bearer token in the masked add-on
  configuration, never in Git.
- Do not configure an internet-facing port, ingress, or reverse proxy.
