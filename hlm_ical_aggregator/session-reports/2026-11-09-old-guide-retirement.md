# My Holiday Guide retirement — 9 November 2026

## Outcome and authorization

The owner requested retirement of the third-party My Holiday Guide scraper and its HA dependencies while preserving agreed booking calendars, the new local guide and all current kiosks. Work was initially read-only; the owner separately authorized VisitIOW-only Google publication, checked replacements and source disabling, stopping the old app after verification, and finally uninstalling it after a final healthy check. No unrelated kiosk controls or services were changed. The owner confirmed the V1 kiosk is no longer online and Skysail's current physical kiosk is temporarily offline.

The old app `32662a46_hlm_guide_calendar` is now uninstalled. This is distinct from the retained new guide `local_hlm_guest_guide`. The retired app's source remains for history; do not reinstall it as the new guide. The disabled `guest-guide` source entry/cache remains for deliberate rollback and is excluded from combined/public output and upstream fetching.

## Why the feeds remain separate

`/combined.ics` must continue carrying property bookings for HA calendars, seven Google Home booking voice scripts and V2 stay/message selection. Source IDs `crossjack`/`skysail`, title prefixes, event identities, date conventions and `/api/v1/status` freshness remain unchanged. The operational Sheets exchange remains the authority for access/heating/operations; this calendar work does not change it.

VisitIOW source `viow` supplies `/sources/viow.ics`, the public event projection and Google publication. Google reads only VisitIOW; it no longer receives booking or old-guide events. `/public-events.json` excludes booking sources and disabled caches. Current kiosks retain their VisitIOW allowlist and freshness handling.

The new guide on port 8099 and its private Sheets service remain separate. House topics, places, Dogs/emergency/maintenance/EV guidance, published property selectors, policy PDFs, media routes, per-Pi HTTPS proxies and existing usage/retention behavior are preserved. Kiosks do not gain direct private Sheets access.

## Changes and deployed versions

- Aggregator 0.4.2: Google publisher consumes enabled VisitIOW cache instead of combined feed; source commit `68a8aef`, merged through [PR 21](https://github.com/mark4068-dotcom/Holiday-Let-Manager-Addons/pull/21), merge `5758cabf397da1f576bc999e1bc95338fa6b80c4`.
- Aggregator 0.4.3: disabled-source caches are excluded from public JSON; source `2d139b9`, [PR 22](https://github.com/mark4068-dotcom/Holiday-Let-Manager-Addons/pull/22), merge `1a5c19e1c5b3d83e88712c02c23897a5bc1dcaf9`.
- Browser-checked replacements applied to legacy `crossjack-guest`, `topgallant` and `dashboard-operations` views via HA API. Current V2 Crossjack/Skysail and custom Topgallant dashboard configurations were preserved. Legacy event/places/house content now uses public events and the new guide/current V2 guest copy. Shared health summaries no longer require old scraper sensors.
- Old events, favourites, health and kiosk-usage REST blocks removed selectively from `/config/holiday_let_manager/rest.yaml`; all new-guide REST content preserved byte-for-byte. HA configuration check passed before Core restart. Public-event/calendar entities explicitly refreshed afterward to replace initial pre-cutover cached counts.
- Only aggregator source `guest-guide` disabled; all booking and VisitIOW options retained. After verification the old app was stopped/manual, then uninstalled under separate owner authorization.
- Final retained apps: aggregator **0.4.3**, new guide **0.5.1**, private Guide Sheets **0.2.0**, operational HLM Sheets **0.4.1**, all running.

## Testing and observed results

Read-only source review was followed by live HA file/registry/dashboard inspection, authenticated Supervisor app/options checks and an actual read-only Google managed-event comparison. No private keys/tokens were copied into reports or repositories. Sensitive evidence remains in the owner's private workspace.

Before the Google change, 73 managed events comprised 61 VisitIOW, six Crossjack bookings, four Skysail bookings and two old-guide events. Exact sync-key/fingerprint comparison predicted 61 unchanged, zero creates/updates and 12 deletions. Live publication matched that plan; subsequent Google listing confirmed 61 managed events, all `viow`. Those deletions affected Google only.

Thirty aggregator tests passed for 0.4.2; **31 tests** passed for 0.4.3, including disabled legacy-cache exclusion and publication/booking preservation regressions. Release metadata/diff checks and required GitHub CI/container checks passed. Production Supervisor builds succeeded. Development HA was unreachable, so no separate development deployment is claimed.

Candidate dashboard JSON, HA REST syntax and all 35 dashboard templates parsed. An isolated hidden admin review dashboard exercised replacement today events, house-guide iframes, legacy Topgallant guide, Operations Overall Health/Data Sources and reporting notices. Templates rendered without errors. Existing live files were hash-checked unchanged during review; cutover then compared live baseline before each save and retained originals.

With the old source disabled, HA combined calendar contains **71 events: 61 VisitIOW + six Crossjack bookings + four Skysail bookings**. All ten booking identities/content were preserved apart from refreshed `DTSTAMP`. Public sensor/feed counts are 61 and sources are only `viow`. Independent Crossjack, Skysail and Franklin calendar entities remain available; seven voice scripts retain the same combined calendar dependency. Voice announcements were not triggered.

Normal aggregator refresh completed healthy with the old app stopped; enabled sources had no errors. Post-uninstall checks confirmed retained app states, healthy new-guide web/property/private Sheets sensors, enabled guide usage writer, HA booking/public counts and a read-only Google listing of 61 VisitIOW events only.

Browser checks: Crossjack V2 reconnected, rendered stay messages/weather, 18 VisitIOW events for Next 7 days, 28 published house items, 123 shared places, a configured Dogs topic and policy PDF paging (pages 1 and 2 of 14). Topgallant rendered booking summaries, independent calendars including a Skysail reservation, 43 events in its 30-day view and 123 new-guide places. Counts are snapshot evidence, not fixed acceptance requirements. Post-stop/reload checks passed; post-uninstall Topgallant events and shared HA backends remained healthy.

## Legacy reporter and limits

Reporter `2.0.0` was traced to old Crossjack V1 `activity-reporter.js`; its background script posts to the old app's `/metrics`. Last heartbeat was 6 November 2026 at 14:03:01 UTC. The owner confirms V1 is offline. Current V2 uses a different controller with no legacy telemetry sender; its message/device-health services remain active. No V2 reporter migration was needed. Legacy usage was exported and the full old-app backup retained; these statistics were not relabeled as new-guide or V2 statistics.

Skysail's physical device is offline: its HA booking/guide backend is healthy, but no live physical screen/proxy acceptance is claimed. Browser checks do not prove physical touch, every external link, all attachment rendering, charging/billing, heating/music controls or extended offline/reboot soak behavior. No such device controls were exercised. The old app was observed through normal refresh with it stopped; no long-term observation or new reboot trial is claimed.

## Rollback plan

**Retain Supervisor backup `561fb6a6`, “Before old guide retirement 2026-11-09”.** It was verified present after uninstall, includes HA configuration plus old scraper 0.5.1 and aggregator 0.4.2, and reports approximately 1,521.89 MB. Additional pre-VisitIOW backup `f8fdec1f` predates the Google-only change. Do not treat the earlier backup as equivalent publication behavior.

Original legacy dashboard configs and `rest.yaml` are also saved under `/config/hlm-backups/old-guide-cutover-20261109`. Do not overwrite unrelated later edits or restore a whole HA backup casually.

1. Establish the failure and compare current configuration with saved originals. Preserve current private options and any newer guide/operational edits.
2. If the retired scraper is needed, use HA's backup restore to restore **only that app** from `561fb6a6`, including its data. Confirm installed slug/version/options before starting it. Never substitute the new guide or Guide Sheets service.
3. Re-enable only `guest-guide` if its feed is required. Restore only the relevant legacy REST/dashboard consumers through HA/API after reviewing differences. Validate configuration before restart; refresh the appropriate calendar/event entities after loading it.
4. Keep aggregator 0.4.2 or later for VisitIOW-only Google publishing. Restoring aggregator 0.4.1 with publishing enabled would republish bookings/old-guide events to Google. App backups alone do not restore deleted Google events.
5. Verify source states/freshness, booking IDs/dates, combined/public output, Google managed-event plan, both guide property endpoints, private guide usage writer and current kiosk views. If restoring the legacy reporter/device, explicitly address its obsolete metrics endpoint rather than reviving it accidentally.

No backups were deleted. Dormant source caches/resource files were retained for rollback; they are not active dependencies. The source-specific cached old ICS route can still serve its retained file, but no active consumer was found and the source is not fetched or included in combined/public output. Removing such historical artifacts is separate optional cleanup.

## Handover and publication

Runtime deployment is complete; documentation work does not perform further runtime changes. This report and repository-specific current-state notes are committed/pushed through isolated documentation branches so unrelated development and kiosk work remain untouched. Historical session reports remain historical. Current release source is in Holiday-Let-Manager-Addons; standalone older calendar repositories are historical baselines. The hidden admin review dashboard remains available for comparison.
