# 10 November 2026 — Paprika Recipes touchscreen page

## Outcome and owner decisions

The owner asked to optimise the new Paprika recipe service for a new page in the existing Topgallant touchscreen kiosk, referring to the chat **Add Topgallant home kiosk**. That chat was located and its latest closeout reviewed. The repository instructions, current requirements, build status and text-entry audit were read. Topgallant remains an independent, owner-only LAN kiosk. The reusable recipe service stays in the HLM add-ons repository; no HLM production change is implied.

Implementation and local browser verification are complete. **Nothing was deployed to Home Assistant or the Pi.** Container builds, the real HA websocket connection and physical touchscreen/keyboard acceptance remain pending. Both projects require session reports, relevant document updates, commits and pushes at each session close.

## Source and branches

- Topgallant: `/Users/mark/Documents/GitHub/Topgallant-Kiosk`, new branch `codex/recipes-page`, based on `main` at `9bd485b`.
- Recipe service: `/Users/mark/Documents/GitHub/Holiday-Let-Manager-Addons/paprika_recipes`, existing branch `codex/paprika-recipes`, preceding published commit `51d4b72`.
- Reports precede their own final commits; final commit IDs and push outcomes are given in the chat response. No merge, release or live update was performed.
- Development continues in these canonical checkouts, not the historical ChatGPT workspace. No recipe export, database, photo or credential is committed.

## Implementation

### Topgallant

New `frontend/recipes.js` renders within the existing 1280×800 header, body and bottom navigation. It displays 24 text cards per result page in three columns with internal scrolling. Search applies on the explicit Search button or Return, respects IME composition, and blurs the field for the existing native keyboard. The shared clear button immediately resets search. Category and favourite filters combine with the submitted query.

Opening a recipe shows its embedded photo, servings/times, separate scrolling ingredients and method/notes/nutrition/source, and transient ingredient checkboxes. Back preserves result/filter state. Leaving the page clears it. No external source links or print windows are opened. Status is checked every minute; an open cooking view is kept stable when a newer export arrives. Navigation disposes timers and invalidates pending replies. Ordinary HA state updates do not rebuild the recipe page.

The shell, allowed-page schema, configuration example and Welcome shortcut editor now recognise `recipes`. Existing shortcut defaults are unchanged. Existing live runtime page lists must explicitly enable the new page. Frontend nested imports and integration manifest are versioned 0.27.0.

New `recipe_source.py` and `recipe_websocket.py` provide read-only `list`, `detail` and `status` through the existing authenticated HA websocket. Existing active administrator or Topgallant kiosk identity is required. An administrator sets a fixed `recipe_service_url` in YAML; the browser cannot choose a destination URL. Validation permits private LAN IPs, .local names and Paprika add-on hostnames, without credentials, paths, queries or fragments. Requests use fixed API paths, no redirects, a 15-second timeout and bounded response reads. No Paprika Cloud credential or generic URL proxy is introduced.

### Recipe companion 0.2.0

Photos move into a separate SQLite table, including migration from early databases. Search reads lightweight records rather than image payloads. Full snapshot replacement remains atomic across recipes and photos. The list API supports bounded `limit`, `offset` and `total`; the kiosk requests 24 records. Requests without `limit` retain the standalone dashboard's previous behaviour. Import/status now records whether favourite flags were supplied.

Deployment and rollback are documented in Topgallant `docs/RECIPES.md`. Requirements, architecture, build status, text-entry audit, both READMEs, companion changelog and session indexes were updated.

## Actual export and validation

The user saved `My Recipes.paprikarecipes` privately in the canonical recipe project's `imports` directory. The original file is unchanged. Local import succeeded with **2,193 recipes, 50 categories and 1,373 embedded photos**. The export did not supply favourite flags, so the native page explicitly disables that filter. The private validation database is under `/private/tmp/paprika-real-validation` and is outside Git.

Passed:

- 44 Topgallant Python tests, including existing suites and two new source/identity tests.
- Seven companion importer/API tests, including pagination, invalid parameters, photo isolation, atomic replacement and failed-import retention.
- Existing Photos JavaScript fixture through the Node runtime.
- Local 1280×800 browser verification using the actual kiosk shell, real recipe API and a temporary HA adapter: collection count, typing without submission, explicit multiword Search, recipe selection, decoded embedded photo, ingredient checkbox, internal scrolling, fixed bottom navigation and Recipes in All pages. No document horizontal overflow was observed.

A lightweight search-record load measured about 18 ms on this Mac. This is not a Pi performance benchmark. A private screenshot is at `/private/tmp/topgallant-recipes-preview.png`; it is not committed.

Limits: Docker was unavailable. The browser adapter bypassed the live HA websocket, so this does not establish backend commissioning or dedicated-user access on HA. Native Pi keyboard hide/reopen, idle/presence, cold startup and physical touch remain untested. The earlier full unrelated HLM Python suite failed collection because its selected environment lacked `icalendar`; it must not be described as passing. No household or media command was sent. The temporary preview server is stopped at session close.

## Resume and deployment gates

1. Read the applicable AGENTS.md, latest reports, current requirements and Topgallant `docs/RECIPES.md`. Check actual Git branches/status and runtime state.
2. Review/build the recipe add-on 0.2.0 on development HA. Default-branch merge/install remains a separate step. Transfer the private full export to HA `/share/paprika-recipes`; no Mac-to-HA sync is configured.
3. Obtain the installed add-on's actual internal hostname. Set the existing `topgallant_kiosk.recipe_service_url` without changing unrelated YAML. Enable `recipes` in the existing runtime pages while preserving all mappings and shortcut choices.
4. Back up backend files, both frontend copies (bundled and live www), resource URL and dashboard/YAML configuration. Deploy only intended files, run HA configuration checks, restart when needed, update the frontend resource hash and refresh the Pi. Do not blindly rerun the old full Welcome deployment script, which can rebuild mappings.
5. Verify the real websocket as the kiosk user, then physically accept Search/Return/clear/keyboard hide and reopen, both scroll columns, Back/All pages, photo, error/refresh states and idle/presence behaviour.
6. Roll back by restoring those exact backed-up files, resource URL and configurations together, disabling only newly enabled recipe settings and preserving the private database/export. Existing household, Music, photos and presence settings need no change.
7. Finish every subsequent session with report, relevant documentation updates, commit and push. Record any failed check or push explicitly.
