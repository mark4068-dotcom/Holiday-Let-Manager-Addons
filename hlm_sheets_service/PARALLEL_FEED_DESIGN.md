# Parallel Sheets feed design

Status: implemented for comparison on 12 September 2026; not cut over.
Acceptance order: establish output parity, record defects, then make separately
reviewed business-rule corrections.

## Source model

| Routine tab | Responsibility |
| --- | --- |
| HLM_control | One NOW clock, Europe/London operational date, 10:00 checkout, 16:00 check-in, explicit aliases |
| HLM_bookings | One Bookings!B4:H import; normalized IDs, cancellation, date and selection flags |
| HLM_changeovers | Normalized local checks retaining submission timestamp and original row |
| HLM_property_model | One calculated row per property using bookings, checks and existing PAT flags |
| HLM_property_export | Exact v1.1 headers and two data rows in A1:AA3, with diagnostics beneath |

Exchange imports `HLM_property_export!A1:AA25` once into
`02_import_property_status`. `22_parallel_ha` exposes only the contract table.
`92_parallel_compare` matches by property ID and header, compares values and
types, and reports mismatches or errors. `93_parallel_checks` exposes source
health; `94_parallel_issue_log` is the working findings register.

## Output contract

The ordered 27-column contract is unchanged:

```text
property_id, property_name, property_status, guest_ready_status, live_booking,
current_check_in, current_check_out, days_to_checkout, booking_reference,
last_check_out, days_since_checkout, last_changeover, booking_company, cleaner,
form_result, report_status, next_changeover_due, days_until_changeover,
changeover_priority, next_booking_check_in, next_booking_check_out,
next_booking_reference, changeover_window, days_until_next_arrival,
pat_testing_status, source_updated_at, schema_version
```

Property IDs are `skysail` and `crossjack`; schema version is the string `1.1`.
Dates use actual Sheets date values displayed as `dd/MM/yyyy`; day counts have
explicit integer formatting. Blank values remain blank. The existing
`build_v1_1_status_payload` function remains authoritative for JSON projection.

The comparison includes 26 fields per property. It displays timestamps
separately because independent recalculations cannot reliably be equal.
Excluding timestamps does not waive future freshness validation.

## Input checks

Output is gated on successful booking import, spare staging capacity,
explicit property mappings, valid active dates, current/future references,
unique current/future references, at most one live booking per property,
changeover formula health and mappings, changeover capacity, PAT formula
health and valid clock controls. Published formula errors are also reported.
Capacity checks require at least 100 spare rows; expand staging before limits
are reached. Historical reference exceptions are warnings, not silent repairs.

## Parity decisions and deferred fixes

| Existing behaviour or finding | Baseline decision / next work |
| --- | --- |
| Latest checkout searched within 60 days | Preserve window; test long vacancies before extending it |
| Vacant-property next changeover uses next booking checkout | Preserve; clarify post-stay versus pre-arrival cleaning meaning |
| Cancellation inferred from reference or notes | Preserve both checks; explicit status is future work |
| Same-day changeover records tie | Preserve date descending, original row ascending; defer timestamp tie-break |
| PAT status comes from existing flags | Preserve; separately review missing test dates |
| Historical references can be absent or reused | Warn; agree durable booking identity before cleanup |
| NOW is evaluation time | Preserve meaning; design authoritative producer freshness separately |
| Legacy IFERROR and copied range inconsistencies | Candidate input gates and normalized ranges can differ on exceptional data; test explicitly |

## Acceptance and migration

The initial snapshot matched all 52 non-timestamp values, and formatted rows
also produced equivalent service JSON. This is not proof for every possible
input. See the [validation record](session-reports/2026-09-12-parallel-sheets-feed.md).

Before cutover:

1. Compare natural arrivals, departures and changeovers, recording results.
2. Exercise isolated fixtures for no next booking, no recent checkout, missing
   check, source failure, cancellation, duplicate/overlapping bookings,
   first-record inclusion, same-day checks and missing PAT dates.
3. Test 10:00, 16:00, midnight and GMT/BST transitions and allow for import
   refresh skew. Do not insert synthetic bookings into production sources.
4. Resolve differences explicitly, distinguishing parity defects from agreed
   business-rule changes; validate expected JSON for each case.
5. Validate a private candidate endpoint before authorizing any runtime range
   change. Preserve the old range and deployment configuration for rollback.
6. Retire the old formula path and Apps Script backup only after separately
   agreed observation and rollback requirements are satisfied.

No background monitoring or retirement schedule was created by this work.
