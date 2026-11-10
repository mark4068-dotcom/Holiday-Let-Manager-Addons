## 0.3.2 — 10 November 2026

- Default cloud checks to every six hours, as requested by the owner.
- Resolve category IDs without case sensitivity; hide unresolved UUID references from display while retaining the original references for future resolution.
- Confirm transaction rollback preserves recipes, photos, metadata and cloud state if publication fails midway.

## 0.3.1 — 10 November 2026

- Support Paprika's observed S3 photo bucket (`uploads.paprikaapp.com` on `s3.amazonaws.com`) and upgrade its advertised HTTP URLs to HTTPS before any request.
- Keep photo requests unauthenticated, exact-host/bucket allowlisted and redirect-free.
- Add regression coverage for the legacy URL upgrade and rejected lookalike/storage hosts.

## 0.3.0 — 10 November 2026 (installed for testing; cloud login pending)

- Optional one-way Paprika Cloud source with private add-on settings and hourly refresh.
- Incremental recipe hashes, category resolution and locally cached primary photos.
- Complete atomic snapshots; failed/empty/racing refreshes preserve the last collection.
- Export mode remains the default; no Paprika recipe writes are implemented.
- Close SQLite connections explicitly, including during long cloud refreshes.
- Ten cloud tests added (17 total); live account verification remains outstanding.

# Changelog

## 0.2.1

- Include supplied author/source metadata in recipe search cards.
- Support native kiosk card thumbnails through its authenticated photo bridge.

## 0.2.0
+
+- Separate photos from searchable records, including migration of earlier databases.
+- Add bounded API pagination for the native Topgallant touchscreen page.
+- Report when favourite flags are absent from an export.
+- Validate the owner's Paprika 4 collection locally; deployment remains pending.
+
+## 0.1.0

- Initial export importer and searchable recipe dashboard.
- Atomic collection refresh and retention of the last successful import.
- Home Assistant ingress, optional LAN port, and a watched shared export folder.
- Separate source/store boundary for future cloud sync; cloud sync is not enabled.
