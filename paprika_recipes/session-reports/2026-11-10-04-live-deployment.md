# 10 November 2026 — live Recipes deployment

## Owner authorisation and result

The owner explicitly said “ok please do it” after asking to add Recipes to the existing Topgallant kiosk. Installed the committed recipe companion and enabled the native page on the live Home Assistant dashboard. Topgallant remains owner-only and LAN-only; no household, charging, lock or audio command was sent. This report supersedes earlier source-only deployment status for this feature.

Source deployed: Topgallant integration/frontend 0.27.1 at `daeb644` on `codex/recipes-page`; Paprika Recipes add-on 0.2.1 at `0d632d3` on `codex/paprika-recipes`. Neither branch was merged to main. Local installation was used, consistent with other local apps on this HA host. Documentation/deployment-script commits follow this report; final hashes are in the chat response.

## Installation and transfer

- Home Assistant at `192.168.0.236`, amd64 HA OS 18.4. Existing signed-in HA Terminal was used; direct SSH root authentication was unavailable. No credentials were printed or committed.
- Source staged as `/addons/paprika_recipes`, installed as `local_paprika_recipes`, hostname `local-paprika-recipes`, version 0.2.1. Supervisor built the image successfully on amd64 and the service started.
- Private full export copied to `/share/paprika-recipes/My Recipes.paprikarecipes`. Import reported 2,193 recipes with no error and no supplied favourite flags. Mac original was untouched. Existing validation counted 50 categories and 1,373 embedded photos.
- Bundle and export SHA256 checks matched before extraction/copy. Temporary Mac transfer server was restricted to the HA IP and an unpredictable path; it was stopped immediately after transfer. No LAN dashboard host port was enabled. The service runs on its internal add-on network, port 8124.
- Initial `ha addons reload` was not the proper store command. `ha store reload` subsequently timed out at the CLI while scanning sources; a later explicit `ha store apps install local_paprika_recipes` succeeded. No duplicate app was installed. Current CLI uses apps rather than the deprecated addons wording.

## Backups and exact change scope

Private backup: `/config/topgallant-backups/recipes-20261110T150522Z`.

It contains the previous full integration directory, full live www frontend, configuration.yaml, kiosk dashboard JSON, resource registrations and a deployment manifest with source hashes and resource URL. These private backups are on HA, not in Git.

The deployment procedure checked that the live backend matched the exact tracked pre-recipe baseline before replacing it. Updated __init__.py, configuration.py and manifest.json, added recipe_source.py and recipe_websocket.py, and copied topgallant.js, recipes.js and home-shortcuts-editor.js to both bundled and live www frontend locations. Other frontend assets and backend modules were preserved.

The existing bare YAML block now reads:

```yaml
topgallant_kiosk:
  recipe_service_url: http://local-paprika-recipes:8124
```

Only recipes was appended to the existing kiosk card's runtime.pages. The entire saved dashboard was compared after removing that appended value, proving the deployment procedure did not alter other controls, mappings, shortcuts or settings. Only the existing Topgallant JavaScript resource URL was updated with its new source hash. The stored generic integration draft/active configuration was not published or replaced: this kiosk uses its existing dashboard runtime configuration.

Later live browser readback also showed a Welcome “Paprika recipes” shortcut, and it opened Recipes successfully. That shortcut was not created by this deployment script; preserve the live owner's current choices. Do not restore the old dashboard backup wholesale merely to change the recipe feature after subsequent owner edits.

## Checks and live verification

- `ha core check`: completed successfully before restart.
- `ha core restart`: completed successfully; live Welcome returned with weather, beach-window, battery and booking information after integrations finished startup.
- Authenticated live HA websocket verifier passed: status count 2,193, 24-result page, source metadata present, recipe detail, photo data and multiword search (72 results for the verification query); recipes enabled exactly once.
- Office Chrome live dashboard verified All pages → Recipes, live card names/categories/attribution, recipe detail/ingredients/method and photo connection. This used the actual HA websocket, not the earlier local mock adapter.
- Topgallant Pi identity `Topgallant-kiosk` verified at `192.168.0.145` using its established host-key alias `192.168.0.49`. Browser service refreshed. Browser, keyboard, presence and display services all report active afterwards.
- No real device controls were exercised. Physical touchscreen/keyboard hide/reopen, scroll, idle/presence and cold boot remain owner acceptance checks. The Office browser is an administrator session; a separate dedicated-user browser-session test was not performed. Existing source tests cover the allowed kiosk identity gate.
- Previous source verification: 44 Topgallant Python tests and seven companion tests passed. New deployment script is preserved in the Topgallant repository for reconstruction; it deliberately stops if recipes is already enabled or the baseline differs.

## Current operation and refresh

Reach Recipes through All pages, or the current Welcome Paprika recipes shortcut. The page displays name, thumbnail, categories and the supplied name/website without an Author/source prefix. Ingredient checks are transient; recipes are read-only. Favourite filtering is disabled because this export has no flags.

Future full exports must be copied to HA `/share/paprika-recipes`. The Mac project's imports folder is separate; no automatic Mac-to-HA file delivery or Paprika Cloud sync was added. The watcher imports the newest stable complete export and retains its previous collection if import fails. Do not commit exports, database contents, photos or credentials. Add-on database is private under `/data`; retain add-on backups and the shared export folder.

## Recovery and follow-up

Read current AGENTS, this report, RECIPES.md and actual Git/runtime state. Feature branches remain the source of this deployment until the owner decides how to merge them. Record the installed local app identity before any later migration to a repository-installed copy; never run two copies inadvertently. aarch64 is declared but not built or commissioned here.

For rollback, first account for any subsequent owner configuration edits. The backup contains the exact pre-deployment backend, both frontend copies, configuration and dashboard/resource records. Restore the relevant files/settings together, configuration-check, restart and refresh the kiosk. Stop only local_paprika_recipes if rolling back the service; retain its private export/database backup. Prefer removing only recipes and its URL/shortcut over overwriting later unrelated dashboard changes. No existing Pi companion configuration changed.

Next owner check: open Recipes on the actual touchscreen, search, open a recipe and test scrolling/Back. Continue the standing report/document/commit/push workflow at every session close.
