# Cloud connection and photo compatibility — 10 November 2026

## Objective and starting state

User re-entered Paprika credentials privately and restarted, then asked to check sync. Continue one-way Paprika Cloud → local database → Topgallant; no writes to Paprika. Prior handover commit `bb8ec7f` on `codex/paprika-recipes` recorded initial authentication failure. Existing service 0.3.0; last good export has 2,193 recipes. No other project changes were present at the start of this follow-up.

## Connection and source selection

The next restart was again in export mode, apparently because saving the earlier configuration screen wrote its stale export selection. A server-side script changed only source to cloud and restarted, preserving credentials without displaying them. Corrected sign-in succeeded: Paprika supplied a token, recipe index and categories. Cloud index had 2,195 entries and 50 categories. This supersedes report06's authentication blocker. Credentials remain in private HA add-on options, token in memory; none entered chat, Mac files or Git.

## Actual compatibility issue and fix

The first authenticated refresh stopped before publication because the live API advertises primary photos as `http://s3.amazonaws.com/uploads.paprikaapp.com/...`. The original 0.3.0 adapter allowed only HTTPS uploads.paprikaapp.com. A diagnostic revealed only scheme, host and public bucket, never full private photo URLs or recipe content.

Version 0.3.1 accepts exactly that S3 host and bucket path, rejects other buckets, lookalike hosts, nonstandard ports, URL credentials and path traversal, and upgrades the advertised HTTP scheme to HTTPS before any request. It still forbids redirects, omits account credentials from all photo requests and applies the existing 2MB image limit. Existing HTTPS uploads.paprikaapp.com support remains. An early diagnostic was misread as Azure; that draft was corrected before the successful update. No Azure allowance is in the final source or installed build.

Changed files: recipe_dashboard/cloud.py, tests/test_cloud.py, config.yaml, Dockerfile and CHANGELOG.md. Version fields are 0.3.1. New photo regression test checks the actual legacy S3 path upgrade, no authenticated request flag, other-bucket/lookalike/traversal rejection. No UI or Topgallant source changes in this follow-up.

## Deployment and verification so far

Old 0.3.0 source files backed up on HA at `/config/topgallant-backups/paprika-cloud-0.3.0-before-photo-fix`. Existing complete add-on backup remains `paprika-before-cloud-20261110` and pre-cloud source backup remains `/config/topgallant-backups/paprika-source-before-cloud-20261110.tar.gz`. Preserve current private options when rolling source back.

Source transferred through authenticated HA Terminal with SHA256 comparisons. Store reload timed out at CLI but completed later in the background; premature update attempts found no update. After metadata refresh, `ha apps update local_paprika_recipes` completed successfully on amd64. A direct adapter check fetched a supported primary image (48,088 bytes) through HTTPS with no account credentials on the photo request.

All 20 importer/API/cloud fixture tests passed; repository metadata/version checks passed and git diff --check passed. Full initial refresh began in the running service; observed phase downloading at 450/2,195 while published source remained export, count2,193. The prior photo error remains in metadata until a successful snapshot clears it; phase/progress distinguish an active retry from a newly failed refresh.

## Recovery and pending verification

Use safe `/api/status` on internal `http://local-paprika-recipes:8124` or the authenticated HA websocket. Never dump saved options, token or raw Paprika responses. Temporary HA scripts `/tmp/watch-paprika-status.py`, `/tmp/diagnose-paprika-cloud.py` read credentials privately only where needed and output classifications/counts; no full photo URLs. No preview/transfer server started.

Await complete snapshot, verify cloud source, count, categories, local photos, optional favourites and HA websocket access, then repeat a check to confirm persisted hashes survive restart. Actual category reassignment and deletions require an owner-approved test recipe; no existing recipe should be edited merely for this verification. Native Topgallant still has its small “Paprika export” caption and no detailed cloud progress UI; it reads the same local API automatically. Final runtime outcome is appended below before handover.

## Owner-requested freshness and atomic-library confirmation

Owner requested a kiosk freshness/failure monitor and explicit protection against a partial download becoming the library. The existing Store.replace transaction already publishes only after the full source download, validation and end-of-download index/category checks. Added a database-write-failure test that fails after replacement starts and verifies recipes, photos, metadata and private cloud-state all roll back to the previous snapshot. Existing interrupted/failed-download and changing-index tests remain green.

Native Topgallant 0.27.2 now shows last successful sync/import with a London timestamp and relative age, download counts, current published library source/count, explicit retained-library text and a failed/service-unavailable state. Polls safe status every15seconds. An earlier attempt's error is not shown as a new failure while a retry is actively checking/downloading. This resolves the owner's observation that the old dashboard still said “latest import failed” during a healthy retry. Source is in Topgallant-Kiosk/codex/recipes-page with its own recovery report. This frontend deployment does not restart the recipe add-on or interrupt its initial download.

Observed live browser after deployment: downloading1,450/2,195, still serving2,193 exported recipes; categories, thumbnails and navigation working. The Pi browser was refreshed; its service reports active. The initial cloud snapshot is not yet established as completed by this observation. No recipe, category or favourite was edited to test sync. Repeat-check, actual cloud publication and real edit/deletion verification remain pending until a complete refresh is observed.

## Full first cloud publication verified

At16:50:21 Europe/London the first cloud snapshot published successfully. Authenticated HA websocket verification passed:2,193 published recipes,24-record page, detail ingredients/method, local photo, source attribution,72 multiword search matches and Recipes enabled exactly once. Full local metadata counts:1,373 photos and2 favourites; favourite flags are available. Safe Supervisor readback verified0.3.1 running in cloud mode with no host port. UI changed to “Cloud sync complete” and last successful sync timestamp/age. The2195 index entries produce2193 non-trash/non-deleted published recipes, matching the earlier export's collection size.

## Six-hour schedule and category-reference follow-up

Owner explicitly requested sync every six hours. Saved sync_minutes360 in private add-on options, preserving all other settings/credentials. The running initial download was allowed to finish before restarting for any schedule change.

The successful cloud snapshot exposed224 display categories instead of50. A private-safe comparison found174 unresolved identifiers (60 bare36-character IDs and114 compound58/59-character IDs), none resolvable by case folding, alongside50 readable names. Raw recipe category references can outlive the current category catalogue. The compound references did not match known IDs by their base UUID either. Version0.3.2 resolves known IDs case-insensitively, hides unresolved UUID-like/compound identifiers from display, deduplicates names and retains all raw references privately so they can be resolved if the category returns. Unknown human-readable legacy names remain supported. Cached recipes are remapped on every refresh; no recipe/photo redownload is needed solely for this fix.

Version0.3.2 sets the default/fallback interval to360minutes as well as preserving the user's saved360 option. Added a regression for case-insensitive category resolution, retained opaque references, readable legacy names and the six-hour default. All20 tests pass. Changed files additionally include __main__.py fallback interval and category/default metadata. Old0.3.1 source backed up at /config/topgallant-backups/paprika-cloud-0.3.1-before-category-fix. The store refresh again runs beyond CLI timeout; wait for metadata recognition before the explicit local app update.

The first category check failed because it handled bare UUIDs but left compound IDs. Safe counts showed60 bare IDs plus114 compound IDs; final filtering handles both shapes while always resolving a known full ID first. Tests include a known compound category ID to ensure valid categories are retained. Intermediate checks correctly refused to claim the expected50 display categories until the final source was rebuilt. Docker runtime inspection was blocked by the SSH app's protection mode; that protection was left enabled. No security setting was weakened.

## Final verified runtime —17:02:50 Europe/London

Final0.3.2 is installed/running on amd64, source cloud, sync_minutes360 (six hours), no host port. Complete repeated refresh after rebuild succeeded with a new success timestamp and persistent recipe hash metadata. Authenticated websocket list/detail/photo/search and unchanged page enablement passed again. Final collection:2,193 recipes,50 display categories,1,373 photos,2 favourites; favourite flags available. Error cleared and cloud phase idle. The local kiosk panel shows “Cloud sync complete” and the successful timestamp/relative age. No library fragments were published during the long initial download or failed checks.

Category cleanup final result was verified as50 after handling both bare and compound IDs; the174 unresolved references remain in private raw category arrays but are not shown as names. Known compound IDs are resolved before the opaque-ID filter. Intermediate0.3.2 builds were refined/rebuilt before the final source commit; only the final checked source is committed.

Next scheduled cloud check is six hours after the completed attempt (restarts check immediately). Source remains read-only towards Paprika. An actual owner-approved recipe edit/category reassignment/deletion propagation test is still outstanding; synthetic tests cover those cases, but no production recipe was changed just to test. The six-hour timer's full elapsed period has not been waited out; saved360-minute option and the running configured source were verified.

All20 companion tests pass; repository metadata/version check and whitespace validation pass before final commit. No unrelated files or private data are included. Reports and source are committed/pushed on codex/paprika-recipes; final commit hash is supplied in chat. The companion report and native kiosk report together reconstruct the session.
