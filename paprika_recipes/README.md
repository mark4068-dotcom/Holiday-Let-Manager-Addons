# Paprika Recipes — The recipe shelf

**Live installation — 10 November 2026:** version 0.3.2 runs as `local_paprika_recipes` on the main HA host, currently in cloud mode with no host port enabled. Topgallant Recipes page 0.27.2 is connected and verified. One-way cloud support is installed for testing. Paprika Cloud published a complete collection of2,193 recipes,1,373 photos and2 favourites. The kiosk shows successful sync freshness and retains its current library until each future full refresh succeeds. The owner selected a six-hour schedule. Physical touchscreen review remains. [Deployment and rollback record](session-reports/2026-11-10-04-live-deployment.md).

A local, read-only Paprika recipe browser for a Home Assistant dashboard. Uses Python 3.10+ and its standard library. Export mode needs no cloud account; optional cloud mode downloads from an existing Paprika account.


## Canonical project location

This project lives in `Holiday-Let-Manager-Addons/paprika_recipes`, alongside the other HLM add-ons. The previous ChatGPT workspace is a historical copy; make future changes here. Recipe exports and the database are local-only and must not be committed.

On this Mac save new exports to:

`/Users/mark/Documents/GitHub/Holiday-Let-Manager-Addons/paprika_recipes/imports`

Double-click `Start dashboard.command` for local use, then open http://127.0.0.1:8124.

## Home Assistant add-on installation

Once this change is merged to the repository's default branch:

1. Refresh the existing HLM add-on repository in the Home Assistant add-on store.
2. Install **Paprika Recipes**, start it, and choose **Open Web UI** or the **Recipes** sidebar panel.
3. Copy a full `.paprikarecipes` export to `/share/paprika-recipes` on Home Assistant. With Samba this is the `share/paprika-recipes` folder. It is distinct from the Mac's local `imports` folder; no file transfer between the two is configured yet.

Ingress provides authenticated access through Home Assistant without enabling a host port. For a Webpage dashboard/card accessed directly over your trusted LAN, optionally enable port 8124 under the add-on's Network settings and use the HA server's address. That direct port has no authentication; keep it disabled unless needed. The sidebar ingress entry works without it. A permanently saved ingress-session URL should not be used as the URL of a dashboard card.

The add-on stores its database under `/data` and uses the watched `/share/paprika-recipes` directory for exports. Back up both. The amd64 container is built and running on the live HA host. aarch64 remains a declared but unverified build target.

## Start on this Mac

From this project directory:

```sh
python3 -m recipe_dashboard
```

Open http://127.0.0.1:8124. Leave the process running while using the dashboard; Ctrl-C stops it. This command starts a loopback-only preview. It does not install a background service.

## Import and refresh

1. In Paprika 4 choose **File → Export…**.
2. Select **All Cookbooks**, **All Recipes**, and **Paprika Recipe Format**.
3. Save the `.paprikarecipes` file in this project's `imports` folder.

The service checks the folder every 10 seconds and waits for two unchanged observations before importing. The dashboard checks for refreshes every 15 seconds. Allow about 35 seconds after an export completes. Each new full export replaces the collection, including removing recipes absent from that export. Always export the whole collection, not an individual category.

The newest file by modification time wins. You can overwrite the same file or save a new one. The original export remains untouched. Invalid, empty, or duplicate-ID imports leave the last successful collection available and display a refresh error. Empty snapshots require a future explicit reset workflow, rather than silently deleting the collection. Recipe photos embedded in `photo_data` are supported; remote photos and additional galleries are not downloaded. Text is displayed safely as plain text, preserving line breaks; Paprika Markdown styling is not rendered.

For immediate import, without starting the server:

```sh
python3 -m recipe_dashboard --import-file '/absolute/path/All Recipes.paprikarecipes'
```

Exports, the local SQLite collection, and generated files are ignored by Git. Keep them private and backed up. There is no upload or edit endpoint. Exports are read as ZIP archives containing gzipped JSON `.paprikarecipe` members; archive paths are never extracted. Archive and expanded-data size limits apply.

## Home Assistant

Run the service on an always-on computer or server reachable by the dashboard's browser. For a trusted home network, bind to the computer's network interfaces:

```sh
python3 -m recipe_dashboard --host 0.0.0.0
```

This makes recipes readable to devices that can reach port 8124. The service has no built-in authentication: do not expose it directly to the internet. For remote access or an HTTPS Home Assistant installation, put it behind your existing authenticated HTTPS reverse proxy. Home Assistant's login does not automatically protect a separately hosted page. A remote browser must be able to reach the recipe URL itself; a Home Assistant Cloud URL does not automatically proxy this service.

In Home Assistant choose **Settings → Dashboards → Add dashboard → Webpage**, or add a Webpage card to an existing dashboard. Use your server's address, not `127.0.0.1` (which would refer to the tablet itself):

```yaml
type: iframe
url: http://YOUR-MAC-OR-SERVER-IP:8124/
aspect_ratio: 100%
```

If Home Assistant is served over HTTPS, use an HTTPS recipe URL too; browsers block HTTP pages inside HTTPS dashboards. Keep the default iframe restrictions. For a full-width view use a panel view containing the Webpage card. The same application is installed as the local Home Assistant add-on described above.

Optional Docker deployment (Docker must already be installed):

```sh
docker compose up -d --build
```

This uses the Home Assistant base image, keeps the database in a named volume, and mounts `imports` read-only. Copy new exports into the host `imports` folder. Docker binds port 8124 on the host network interfaces. Container builds and Home Assistant deployment require verification on the target host.

## One-way Paprika Cloud sync — 0.3.2 (installed for testing)

The optional cloud adapter reads from Paprika Cloud into the local recipe database. It never uploads, edits or deletes anything in Paprika. Export mode remains the default. The update was authorised and installed on the live amd64 host, with cloud mode subsequently selected for testing. Corrected private sign-in and a full first cloud publication are verified. The owner selected six-hour refreshes; the service retains its last complete snapshot if a later refresh fails.

Open the add-on Configuration page, enter `cloud_email` and `cloud_password` privately, select `source: cloud`, and save/restart. The password field is masked; HA administrators and backups can still access add-on options. Never paste credentials into chat or commit them. Leave `sync_minutes: 360` for six-hour refreshes (supported range 15–1440 minutes). Restart triggers a check immediately. The first full download may take several minutes; the existing collection stays readable throughout.

Cloud mode disables export watching, so an old export cannot overwrite a cloud snapshot. To roll back, set `source: export` and restart; the watched full export replaces the collection after two stable observations. Back up the add-on data before installing the update. Source selection changes do not erase the previous database while waiting for a successful refresh.

Cloud refresh downloads changed recipes using Paprika UID/hash pairs, resolves current category names while hiding unresolved opaque IDs (raw references are retained for future resolution), caches supported primary photos locally and removes recipes absent from a successfully downloaded full collection. Recipe/category lists are rechecked before publishing. Invalid, empty, interrupted, oversized or changed-during-download collections retain the previous snapshot. Failed checks retry on the configured interval; HTTP 429 can extend the wait. Tokens stay in memory, credentials stay in server options, and neither is sent to the dashboard or photo server. Favourite flags are imported if supplied, with no local favourites editing.

Photo downloads accept HTTPS `uploads.paprikaapp.com` or the exact `uploads.paprikaapp.com` bucket path on `s3.amazonaws.com`, without redirects or account credentials. Legacy HTTP links for that S3 bucket are upgraded to HTTPS before requesting. JPEG, PNG and WebP primary images are supported up to 2 MB each; additional galleries are not synced. Unsupported photos currently fail the refresh rather than silently losing them. Cloud support uses Paprika's undocumented API; account login, v4 index/category/recipe shape and a real HTTPS primary photo have now been checked. Full first publication is verified. Actual edit/deletion propagation still requires an owner-approved live test. Local fixture tests are not proof of a working cloud account.

The login flow was checked against [the existing Paprika HA client](https://github.com/rbrunt/paprika-ha/blob/main/custom_components/paprika/api.py); recipe endpoints were researched in [Paprika Tools API notes](https://github.com/aarons22/paprika-tools/blob/main/API_REFERENCE.md). This project implements its own small standard-library adapter and adds no dependency on either project.

The native Topgallant page reads the same local API and needs no credentials. Native page 0.27.2 displays last successful sync/import and age, current library, download progress and failure/unavailable warnings. Status updates every15seconds; an earlier failed attempt is not presented as a new failure while a retry is downloading.

For private local testing, place the same options in a JSON file outside the repository with owner-only permissions, then run `python3 -m recipe_dashboard --settings /absolute/private/options.json`. Do not put credentials in command-line arguments. The add-on automatically reads `/data/options.json`.

## Verification

```sh
python3 -m unittest discover -s tests -v
```

Twenty tests cover export replacement, archive safety, cloud incremental refresh/deletions, account separation, photo reuse and host restrictions, redacted failures, concurrent changes, and retaining a working collection. Manual browser checks should cover search, categories, favourites, recipe navigation, ingredient checkboxes, print, and tablet layout.

## Session handover and recovery

At the user’s standing request, every work session ends with a detailed report, updates to relevant documents, and a commit and push of project changes. See [project instructions](AGENTS.md) and the [session report index](session-reports/README.md). Read the latest report when restoring a lost chat context.

## Topgallant touchscreen integration — 0.2.0

The native Recipes page is implemented in the separate Topgallant-Kiosk repository. It uses the existing authenticated HA websocket connection to read this service's status, paged metadata and one selected recipe. See [Topgallant recipe setup](https://github.com/mark4068-dotcom/Topgallant-Kiosk/blob/codex/recipes-page/docs/RECIPES.md). No browser-to-Paprika call or Paprika credential is required. Internal add-on networking allows the host port to remain disabled.

Photos are now stored separately from searchable records. Existing databases migrate at startup, and snapshot updates replace both tables atomically. `/api/recipes?limit=24&offset=0` returns `total` and a bounded page; requests without `limit` retain the standalone page's existing behaviour. Status reports whether favourite flags were supplied.

Real Paprika 4 export validation passed: 2,193 recipes, 50 categories and 1,373 embedded photos. The export supplied no favourite flags, so Topgallant explicitly disables that filter. The temporary local search-record load took about 18 ms on this Mac; this is not a Pi performance benchmark. The original seven importer/API tests pass; the full suite now has 20 passing tests. Container build and live HA connection are verified on amd64; physical touchscreen acceptance remains pending.

### Recipe card attribution — 0.2.1

Search results include Paprika source metadata for the native kiosk cards. Topgallant displays the name, photo thumbnail, categories and supplied Author/source together, with explicit missing-value placeholders. Thumbnails use the existing photo endpoint through its authenticated HA bridge. No new export or database migration is needed for this refinement.
