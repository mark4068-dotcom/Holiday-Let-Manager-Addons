# Cloud sign-in check — 10 November 2026

## Request and starting point

User saved credentials and restarted the add-on, then requested a sync check. Starting source commit: `75f6f17`, branch `codex/paprika-recipes`; clean working tree. Add-on 0.3.0 installed on HA `192.168.0.236`, slug `local_paprika_recipes`. Existing export collection contains 2,193 recipes. One-way sync only, no writes back to Paprika. Favourites optional.

## Actions and observed result

Safe local `/api/status` initially showed source export, sync mode export, phase watching, no error and count 2,193. The user had saved the sign-in fields but left the source selection at export.

Through the existing authenticated HA Terminal, a small server-side script read Supervisor add-on options privately, reported only that both credential fields were populated, changed only `source` to `cloud`, saved the complete preserved options and restarted the add-on. The user's request to set up and test one-way cloud sync authorised this selection. No credentials were displayed, copied to the Mac, put into chat or committed.

The subsequent status showed sync mode cloud, phase error, message “Paprika returned an unsupported response.” Count stayed 2,193 and the last successful source remained export. That source field describes the published snapshot; it does not mean cloud mode failed to save.

A read-only diagnostic used the same adapter and privately saved options on HA. It output response classifications only: the login endpoint returned JSON, an error, no result and no token; its error concerned authentication. No recipe index or category download was reached. No raw response, password, email or token was output. This establishes a sign-in failure, not a successful cloud sync or a recipe/category compatibility failure.

User was asked to re-enter their actual Paprika Cloud account email/password privately at `http://192.168.0.236:8123/config/app/local_paprika_recipes/config`, leave cloud selected, save and restart, then tell the chat to check again. Do not infer that elapsed time means the user completed this step.

## Current runtime and limits

- Add-on 0.3.0 remains running in cloud mode with failed authentication.
- Last good export snapshot of 2,193 recipes remains available; nothing has been replaced by cloud data.
- No Paprika recipe writes, deletion tests or category edits were performed.
- Cloud retry follows the configured interval (default 60 minutes); a restart triggers an immediate check.
- Topgallant source/frontend remain unchanged at 0.27.1. Its small caption still says Paprika export; defer cloud caption/progress work until a successful connection is established.
- Prior 17 fixture tests passed; no source code changed in this check session, so no implementation tests were rerun. Git whitespace validation is required before the documentation commit.

## Recovery and next steps

Read AGENTS.md, this report, README and actual Git/runtime status. Do not dump `ha apps info` or settings after credentials exist: those may reveal options. Inspect only safe `/api/status` via internal `http://local-paprika-recipes:8124` or the authenticated `topgallant_kiosk/recipes` status websocket action.

After the user confirms corrected private settings, check safe status. If sign-in still fails, distinguish account rejection from request-format/API changes using redacted diagnostics. Do not guess passwords, scrape Keychain or ask for passwords in chat. Once authenticated, verify full snapshot completion, counts, category mapping and photos, then incremental refresh. Recipe category reassignment is expected to change its hash; category renames are independently reloaded. These still require live verification.

Private rollback remains available: add-on backup `paprika-before-cloud-20261110` and old source `/config/topgallant-backups/paprika-source-before-cloud-20261110.tar.gz`. Selecting export and restarting restores export watching without erasing the current snapshot while waiting.

Temporary diagnostic scripts on HA: `/tmp/enable-paprika-cloud.py` and `/tmp/diagnose-paprika-cloud.py`; Mac copies under `/private/tmp`. Scripts contain no credentials, but read options privately at runtime. No local preview or transfer server was started. Canonical changes in this session are documentation only; standing order requires commit and push before handover.
