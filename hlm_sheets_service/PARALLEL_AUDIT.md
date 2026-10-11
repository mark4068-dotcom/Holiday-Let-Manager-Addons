# Sheets feed audit

Version 0.4.0 retains the opt-in background audit (`parallel_audit_enabled: true`)
and 90-day history. New records use `audit_mode: production_health`, validate
the new source's evaluation age and source checks, and record a separate
`upstream_import` heartbeat object. They have zero compared fields and no
legacy comparison. `status: healthy` describes model evaluation; inspect the
importer object and freshness flags separately. End-to-end booking transport
is still unverified. The event writer is unchanged.

## Historical 0.3.2 comparison records

The following describes the historical comparison samples preserved in the
same files and routes.

Every five minutes, one authenticated Google Sheets batch read fetches the
live v1.1 table, `22_parallel_ha` and imported source-check statuses. The
existing v1.1 validator parses both tables. All 26 non-timestamp fields per
property are compared, with both expected property IDs required. Missing or
failed checks and invalid contracts are errors, never successful matches.
WARN/INFO checks remain in the record without counting as parity failure.

## Storage and diagnostics

Each attempted check appends a UTC-timestamped JSON record to
`/data/parallel-audit/YYYY-MM-DD.jsonl`, flushed to disk. The directory is
private (0700), files are owner-readable/writable (0600), and the add-on's
persistent data survives restart/update. Files older than 90 days are removed
when a new sample is persisted; disabling the audit stops sampling and cleanup.
Backups can retain older copies under their own retention policy.

Records contain matched/different/error state, comparison count, actual old
and new values, parsed property snapshots, raw contract/check cells, and both
evaluation timestamps. Booking references, cleaner/company and form-result
values are included for diagnosis as explicitly authorized by the operator.
Credentials are never recorded. Exceptions are categorized without logging
raw exception messages; general add-on logs contain no audit payloads.

These records can reveal property occupancy and operational/personnel details.
They belong only in private runtime storage, not Git, public dashboards or
public exports. The operator maintains the privacy policy separately.

## Review after changeovers

Use the existing internal hostname and read bearer token:

- `GET /api/v1.1/parallel-audit`: retained daily counts, mismatch fields,
  failure categories, first/last check, gaps over ten minutes, stale-audit
  indicator, write-failure indicator and the latest 100 incident samples.
- `GET /api/v1.1/parallel-audit/YYYY-MM-DD`: full diagnostic records for one
  UTC day, including successful samples and recoveries.

Both endpoints require the existing read token and return `Cache-Control:
no-store`. No host port, public URL or new credential is introduced. Daily
downloads are private operational data. The summary is bounded to recent
incident details, but the daily files retain every sample within retention.

Review coverage first: missing/stale samples are not evidence of a clean feed.
Then review errors and mismatched fields, use daily records to establish onset,
duration and recovery, and correlate dates/status changes with changeovers.
Success after a divergence records recovery even if the service restarted.
The first recorded sample is the beginning of coverage; no history is backfilled.

The worker runs independently of HA polling and does not depend on a Mac or
Codex staying open. It cannot record while HA/the add-on is stopped. Short-lived
issues between samples can be missed. Reads are batched to reduce skew but
Sheets imports may still recalculate at different times. `source_updated_at`
remains an evaluation clock, not proof of upstream producer freshness.

This is logging, not a notification service or cutover. A stale report or
persistence warning needs investigation. Existing Apps Script monitoring and
production endpoint behaviour remain separate.
