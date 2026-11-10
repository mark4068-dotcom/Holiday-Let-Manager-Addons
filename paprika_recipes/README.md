# Paprika Recipes — The recipe shelf

**Live installation — 10 November 2026:** version0.2.1 runs as local_paprika_recipes on the main HA host, with no dashboard host port enabled. Topgallant Recipes page0.27.1 is connected and verified. Physical touchscreen review remains. [Deployment and rollback record](session-reports/2026-11-10-04-live-deployment.md).

A local, read-only Paprika recipe browser for a Home Assistant dashboard. Uses Python 3.10+ and its standard library; no packages or cloud accounts required.


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

The add-on stores its database under `/data` and uses the watched `/share/paprika-recipes` directory for exports. Back up both. amd64 and aarch64 are declared build targets, but container and live Home Assistant validation are pending. This source change does not deploy or update production.

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

If Home Assistant is served over HTTPS, use an HTTPS recipe URL too; browsers block HTTP pages inside HTTPS dashboards. Keep the default iframe restrictions. For a full-width view use a panel view containing the Webpage card. The same application is packaged here as a Home Assistant add-on. It has not yet been installed into your Home Assistant instance.

Optional Docker deployment (Docker must already be installed):

```sh
docker compose up -d --build
```

This uses the Home Assistant base image, keeps the database in a named volume, and mounts `imports` read-only. Copy new exports into the host `imports` folder. Docker binds port 8124 on the host network interfaces. Container builds and Home Assistant deployment require verification on the target host.

## Future cloud sync

`ExportSource` handles the export folder; `Store.replace(recipes, source)` accepts a complete, validated snapshot and publishes it in one transaction. A future `CloudSource` can fetch Paprika's recipe list and hashes, download changed recipes, resolve category IDs and photos, then publish through the same method. The dashboard only uses local `/api` endpoints and needs no changes or Paprika credentials.

Cloud credentials would belong only in the server's secret store. A cloud source must normalize remote data to the same fields, handle deletions and failed fetches, and only publish a complete snapshot. The current implementation supports exports only; no cloud polling or automated app export is enabled. A synced folder can automate file delivery, but generating a new export is still a Paprika action.

## Verification

```sh
python3 -m unittest discover -s tests -v
```

Tests cover replacement/deletions, duplicate IDs, incomplete exports, retaining a working collection, and archive traversal. Manual browser checks should cover search, categories, favourites, recipe navigation, ingredient checkboxes, print, and tablet layout.

## Session handover and recovery

At the user’s standing request, every work session ends with a detailed report, updates to relevant documents, and a commit and push of project changes. See [project instructions](AGENTS.md) and the [session report index](session-reports/README.md). Read the latest report when restoring a lost chat context.

## Topgallant touchscreen integration — 0.2.0

The native Recipes page is implemented in the separate Topgallant-Kiosk repository. It uses the existing authenticated HA websocket connection to read this service's status, paged metadata and one selected recipe. See [Topgallant recipe setup](https://github.com/mark4068-dotcom/Topgallant-Kiosk/blob/codex/recipes-page/docs/RECIPES.md). No browser-to-Paprika call or Paprika credential is required. Internal add-on networking allows the host port to remain disabled.

Photos are now stored separately from searchable records. Existing databases migrate at startup, and snapshot updates replace both tables atomically. `/api/recipes?limit=24&offset=0` returns `total` and a bounded page; requests without `limit` retain the standalone page's existing behaviour. Status reports whether favourite flags were supplied.

Real Paprika 4 export validation passed: 2,193 recipes, 50 categories and 1,373 embedded photos. The export supplied no favourite flags, so Topgallant explicitly disables that filter. The temporary local search-record load took about 18 ms on this Mac; this is not a Pi performance benchmark. Seven importer/API tests pass. Container builds, live HA connection and physical touchscreen acceptance remain pending.

### Recipe card attribution — 0.2.1

Search results include Paprika source metadata for the native kiosk cards. Topgallant displays the name, photo thumbnail, categories and supplied Author/source together, with explicit missing-value placeholders. Thumbnails use the existing photo endpoint through its authenticated HA bridge. No new export or database migration is needed for this refinement.
