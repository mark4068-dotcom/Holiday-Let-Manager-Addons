# Guest Guide deployment and maintenance

**9 November 2026 update:** the separate old `hlm_guide_calendar` scraper has been uninstalled. This guide (0.5.1) and private Guide Sheets (0.2.0) remain running and unchanged. Booking/calendar feeds and kiosk guide/proxy/topic/PDF contracts are preserved. See the [retirement session report](../hlm_ical_aggregator/session-reports/2026-11-09-old-guide-retirement.md); the 1 November rollout record below remains historical evidence.

Recorded 1 November 2026. These are the verified versions for this guide rollout,
not an assertion that unrelated HLM components have remained unchanged since then.

| Component | Version | Access |
| --- | --- | --- |
| Guest Guide | 0.5.1 | LAN `http://192.168.0.236:8099/` |
| Private Guide Sheets Service | 0.2.0 | Internal `http://local-hlm-guide-sheets-service:8787` |
| Existing HLM Sheets Service | 0.4.0 at cutover | Separate service; not changed by this rollout |

Canonical source: Holiday-Let-Manager-Addons, `hlm_guest_guide/` and
`hlm_guide_sheets_service/`. Runtime installation uses local add-on slugs
`local_hlm_guest_guide` and `local_hlm_guide_sheets_service`. Changes in this work
were developed on `codex/guide-markdown` and reconciled with main for the shared
repository. The canonical checkout is
`/Users/mark/Documents/GitHub/Holiday-Let-Manager-Addons`; private migration data
remains outside Git. The development branch is retained for history.

## Current behaviour

- One shared places list, with distances from the selected property's coordinates.
- Separate Crossjack and Skysail house guides, categories, photos and attachments.
- Private Google Sheets and Drive access; administration uses
  `sailcottagesha@gmail.com`, with separate read-only and writer service identities.
- Published-only guest views. Draft and Archived records remain excluded.
- Local policy PDFs generated from private Word/Google Docs sources. Guests need
  neither Google sign-in nor published Google document links.
- Markdown in Instructions, Description and Our recommendation. Other columns
  retain their established formats. Workbook Start Here rows 117–134 explain it.
- Locally bundled Twemoji artwork for Markdown emoji; no CDN/font dependency.
- Usage/search statistics with 12-calendar-month detailed retention and no booking
  linkage. The outer kiosk owns the privacy notice and accessible credits.

See [KIOSK_HANDOVER.md](KIOSK_HANDOVER.md) for URLs, privacy policy, attribution,
kiosk labels, font recommendation and final hardware checks. Live Google opening
hours remain optional and disabled; what3words is not part of the solution.

## Content work completed

Skysail: all 29 Instructions cells formatted, 27 Published and two Archived.
Crossjack: all 30 formatted, 28 Published and two Archived. Counts describe the
conversion checks, not a fixed future schema requirement. Only Instructions cells
were changed; references, statuses, URLs, ordering and other property content were
preserved. The owner continues to edit wording, including BBQ content.

Original values, reversible row/reference conversion files and owner-review notes
are stored in the private project workspace's outputs directory. They contain
property content and are intentionally not committed. Google version history is
also available. Do not restore an old content backup over later owner edits.

## Release record and validation

- `e4eec1c`: private Drive policy sources served as cached local PDFs.
- `2869056`: safe Markdown rendering, version 0.5.0.
- `bf6f2eb`: local Twemoji 17.0.3 artwork, version 0.5.1.

For 0.5.1, 26 guide Python tests, Markdown/security checks, usage-client checks,
emoji sequence/asset tests and repository metadata checks passed. All 4,009 SVG
files were checked for script elements and external references. Preview and live
Dogs/House Rules checks confirmed local paw, leaf, fire, sun, globe and moon images.
Both properties' formatted source and Published guest content matched during the
conversion checks, and policy file buttons remained available.

Run from the repository root with the requirements installed:

```sh
python scripts/check_repository.py
python -m unittest discover -s hlm_guest_guide -p 'test_*.py'
node hlm_guest_guide/test_markdown.cjs
node hlm_guest_guide/test_emoji.cjs
node hlm_guest_guide/test_usage_client.cjs
```

Final Raspberry Pi fonts, iframe dimensions/navigation and host notices/credits
still need verification by the kiosk project. Browser preview does not prove the
physical kiosk's configuration.

## Updating safely

1. Record installed versions; back up the source, masked configuration and `/data`
   through the normal HA backup process. Do not print options or credential files.
2. Compare live source with the expected baseline before replacing it; another
   context may be maintaining the same HA host.
3. Copy the reviewed credential-free guide directory to `/addons/hlm_guest_guide`.
   Preserve `/data`, options and the separate private/HLM services.
4. Reload the local add-on store. For a higher version, use the normal **Update**
   action. A same-version rebuild is a different operation; 0.5.1 was installed
   successfully using Update after the new version became available.
5. Refresh the browser and verify the correct property, a document, an emoji and
   `GET /api/health`. Keep guest content available from the last good snapshot if
   a Google refresh is unavailable. A full Home Assistant restart is unnecessary.

Content refreshes normally occur in two approximately ten-minute stages. If a
controlled immediate refresh is needed, refresh the private service first, verify
its publication, then refresh the guide. Restarting both at once can initially
serve the previous cached content while files are still being downloaded.

## Backup and rollback

Before the emoji update, live source hashes matched 0.5.0 and the source was saved
on HA at `/tmp/hlm-guide-before-emoji-20261101.zip`. The earlier Markdown source
backup is `/tmp/hlm-guest-guide-before-markdown-20261101.zip`. These temporary files
are recovery aids, not durable backups; keep normal HA backups separately.

To roll back emoji rendering, restore the 0.5.0 guide source (or the reviewed
`2869056` version), reload the store and use the appropriate rebuild/reinstall
workflow for that local version, then start the guide and verify cached content.
Do not erase or replace `/data`, edit the workbook to undo a code release, change
service credentials, or repoint existing HLM routes. Restoring an image/version
may require the local add-on recovery workflow rather than the normal upgrade
button. Keep the current source/configuration backup until recovery is verified.
