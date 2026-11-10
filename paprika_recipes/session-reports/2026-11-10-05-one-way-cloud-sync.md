# One-way Paprika Cloud sync — 10 November 2026

## Objective and decisions

User prioritised one-way Paprika Cloud → local recipes → Topgallant sync. Favourites are optional; no local favourites and no writes back to Paprika. Preserve the working export collection during testing. Standing order remains: reports, relevant docs, commit and push every session.

## State at this handover

Installed add-on 0.3.0 on `codex/paprika-recipes`, based on preceding commit `910ff22`. Live HA now runs `local_paprika_recipes` 0.3.0 with 2,193 exported recipes, source still export. Topgallant remains 0.27.1 on `codex/recipes-page`; no kiosk code changed this session. The update is deployed; no Paprika login or cloud recipe download has yet been performed. The user explicitly authorised “Install for live testing”. A partial add-on backup named `paprika-before-cloud-20261110` completed successfully before any source changes. Old local source was archived at `/config/topgallant-backups/paprika-source-before-cloud-20261110.tar.gz`. New source was transferred through the authenticated HA Terminal and verified by SHA256 before writing. Store reload timed out at the CLI and the first update attempt reported no update; runtime outcome is recorded below when verified.

## Implementation

`recipe_dashboard/cloud.py` implements fixed HTTPS login and GET-only sync requests, no redirects, bounded compressed/expanded responses, safe errors and rate-limit delay. It fetches recipe UID/hash index and categories, reuses unchanged local recipes for the same account, downloads changed details and primary photos, maps category IDs to names, then rechecks indexes before atomic publication. Empty, duplicate-ID, mismatched-ID, concurrent-change or partial snapshots leave the last good database intact. Missing/deleted recipes disappear only following a successful full refresh. No recipe write endpoint exists.

`store.py` adds a private cloud-state table committed with the snapshot; cloud recipe hashes/category IDs/photo hashes live in stored recipe records. The account fingerprint is not exposed in status. Export replacement clears cloud-state reuse. SQLite connections now explicitly close after transactions, fixing warnings observed under Python 3.14 and preventing long-refresh connection accumulation.

`__main__.py` accepts a private `--settings` file. In the add-on, `run.sh` reads `/data/options.json`. `config.yaml` adds source export/cloud, email, masked password and interval (15–1440 min, default 60). Default export behaviour is preserved. Cloud mode never runs the export watcher. Restart performs a check immediately; failures retry on the interval, extended for 429 if needed. Tokens are memory-only. No credentials were collected or committed.

`static/app.js` disables unavailable favourites and uses cloud-aware initial waiting text. Native Topgallant's small caption remains “Paprika export”; change it when enabling cloud mode. Detailed cloud progress is available in `/api/status` but not rendered by the kiosk.

## Verification

`PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v` in prepared app: 17 passed. Ten new cloud tests cover successful incremental/restart behaviour, deletions/favourites, failed partial snapshot retention, empty/racing index rejection, account separation, primary-photo reuse, safe errors, photo destination/credential isolation, rate limit handling and login/read request construction. Existing seven export/API tests still pass. These use synthetic fixtures, not an authenticated account.

Canonical repository metadata check passed: JSON, workflows and release versions validated. `git diff --check` passed before documentation completion; repeated at commit time. The tests alone establish no live account behaviour. Subsequent amd64 container build and export-mode live verification succeeded; real cloud initial download, category/deletion tests and physical touchscreen acceptance remain pending.

## Resume and live-test steps

1. Read AGENTS.md, README and this report; inspect Git status/branch. Never edit the historical ChatGPT workspace.
2. Confirm deployment authorisation. Back up current add-on data/options before upgrading. Existing installation and rollback details are in report04. Source is `/addons/paprika_recipes`, slug `local_paprika_recipes`, HA `192.168.0.236`, internal service `http://local-paprika-recipes:8124`; keep the host port disabled.
3. Install/rebuild the prepared 0.3.0 source with source still export. Verify existing collection/API first. Do not merge default branches or publish releases implicitly.
4. Have the user enter credentials privately in Home Assistant add-on Configuration, select cloud and restart. Do not request passwords in chat, scrape Keychain, dump add-on options, or log remote bodies. HA admins/backups can read these options despite the masked UI.
5. Watch safe `/api/status` phase/completed/total/error fields. First full download is sequential and may take several minutes. Verify cloud counts, categories, photos and representative known recipes, then confirm a small edit synced from Paprika; perform deletion checks only on an owner-approved disposable test recipe.
6. Resolve actual v4 API/host differences if any. Photo allowlist currently only `uploads.paprikaapp.com`, HTTPS, no credential forwarding, 2MB limit. API is undocumented and may change. A failed photo blocks publication to avoid silent loss.
7. Update the native kiosk caption and deployment docs, complete checks, report, commit and push. If login fails or scope differs, retain export mode and the current collection.

No preview server was started. Staging is `/private/tmp/paprika-cloud-work`; canonical source is the Addons repo. Do not commit staging caches, private exports, databases, logs, or secrets.

## Category changes

The user specifically asked whether category changes are recognised. Added a test for a category rename without a recipe hash change, and for a recipe moving category with a changed hash. Both pass. Live hash behaviour still requires confirmation against the actual account.

## Verified deployment outcome

Store reload eventually finished in the background after the CLI timeout. The initial “No update available” response was premature; once the update appeared, `ha apps update local_paprika_recipes` completed successfully. The amd64 0.3.0 container is running, export mode is selected, and host ports remain disabled. Safe filtered Supervisor readback asserted these facts without printing credentials/options. The existing authenticated HA websocket verifier passed: count 2,193, 24-result page, source metadata, selected detail, photo data and multiword search (72 matches); Recipes remains enabled exactly once.

The configuration screen visibly shows export/cloud selection, email, masked password and 60-minute interval. Left it open for the user at `http://192.168.0.236:8123/config/app/local_paprika_recipes/config`, with instructions to choose cloud, privately enter existing Paprika credentials, save and restart. Do not read the settings screen after credentials are entered; query only safe `/api/status` via the HA websocket. Screenshot before entry: `/private/tmp/paprika-cloud-settings.png` (not in Git).

Resume task: check whether user completed private setup, inspect safe cloud status, resolve actual account/API response compatibility as necessary, and verify one-way edits/category changes. No HA core restart or kiosk frontend deployment was needed for this add-on update. Existing Topgallant source remains untouched; small export caption/progress UI follow-up remains.
