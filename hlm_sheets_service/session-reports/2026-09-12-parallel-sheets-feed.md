# Session record: parallel Sheets feed

Date: 12 September 2026. Outcome: parallel candidate built and checked;
production remains on the existing feed.

## Purpose and completed work

Refactor the spreadsheet source into a cleaner path for Home Assistant while
preserving current output. The agreed sequence is parity first, followed by
explicit review of defects rather than silently changing operational rules.

Earlier in the session, the booking appender was adjusted to select the next
safe wholly empty row, retaining duplicate checks and document locking. The
user then moved the displaced data and removed the old trailing rows. A read
confirmed 129 booking records in rows 4–132 with no content below row 132.
That bound Apps Script change is separate from the add-on source in this repo.

Using the designated HA spreadsheet editing account, five tabs were added to
Routine checks log: HLM_control, HLM_bookings, HLM_changeovers,
HLM_property_model and HLM_property_export. Five were added to Exchange:
02_import_property_status, 22_parallel_ha, 92_parallel_compare,
93_parallel_checks and 94_parallel_issue_log.

The implementation centralizes the booking import, property aliases, clock
and calculations. It publishes the existing 27-column v1.1 contract, includes
source validation and compares both properties with the current live table.
The [architecture](../ARCHITECTURE.md) and
[design](../PARALLEL_FEED_DESIGN.md) describe the resulting structure.

## Validation performed

| Check | Result |
| --- | --- |
| Contract headers and property count | Exact 27 headers; two properties |
| Sheet comparison | 52 non-timestamp matches; zero differences; zero comparison errors |
| Blocking source checks | All passed at validation time |
| Local service JSON projection | Live and candidate formatted rows passed build_v1_1_status_payload; zero property-field differences excluding source_updated_at |
| Live table preservation | A1:AA3 formulas and literals identical before and after |
| Native layout review | Five Routine tabs plus candidate, comparison, checks and issue log inspected |

Day-count cells initially inherited date formatting from date arithmetic.
Explicit integer formats corrected this, and the JSON projection comparison
passed afterward. Final visual inspection of the Exchange import staging tab
was interrupted by browser detachment.

These results cover the current data snapshot, not all possible future states.
No candidate service endpoint was deployed or queried. Independent evaluation
timestamps were excluded; upstream freshness is still unverified. Expected
warnings remain for timestamp semantics and historical booking references.

## Findings register and ownership of follow-up

The live working register is **Exchange → 94_parallel_issue_log**. It records
evidence, potential effect, parity decision, follow-up and state. The table
below is its repository snapshot. Future sessions should update both this
snapshot and the working sheet when a finding is resolved or changes scope.
No GitHub issues or automatic monitoring were created.

| ID | Finding | Required follow-up | State |
| --- | --- | --- | --- |
| SF-01 | NOW timestamps do not establish upstream freshness | Design producer heartbeat and freshness contract | Deferred |
| SF-02 | Historical references are reused or missing | Agree durable booking key; repair known exceptions | Deferred |
| SF-03 | Last checkout disappears after 60 days | Test long vacancy and agree full-history lookup | Deferred |
| SF-04 | Next changeover may mean next booking checkout rather than outstanding clean | Agree operational meaning before changing dates | Deferred |
| SF-05 | Cancellation depends on reference/notes text | Define explicit status and calendar-discrepancy review | Deferred |
| SF-06 | Legacy IFERROR can hide missing/failed input | Test missing booking/check/source cases against candidate gates | Open test |
| SF-07 | Boundary times and refresh skew may cause mismatches | Exercise 10:00, 16:00, midnight and GMT/BST | Open test |
| SF-08 | Copied legacy ranges can omit a source row | Test first-record inclusion in isolated fixtures | Open test |
| SF-09 | Same-day checks depend on row ordering | Agree submission-time tie-break separately | Deferred |
| SF-10 | Missing PAT dates may not appear due | Review missing-test semantics | Deferred |
| SF-11 | Sheet parity is not an HA cutover | Validate candidate endpoint and migration/rollback decision | Not cut over |

IDs are repository tracking labels for the corresponding issue titles in the
sheet. Deferred means deliberately unchanged for parity, not resolved.

## Unchanged production boundaries

No add-on code/version, live output table, runtime read range, HA entity,
event writer or Apps Script backup deployment was changed by the parallel
feed implementation. The live source remains
21_published_ha_v1_1_draft and the production endpoint remains
/api/v1.1/status. Old imports remain active during comparison.

## Remaining acceptance work

Observe natural transitions, exercise the isolated edge cases in the design,
record and resolve parity differences, then review business-rule corrections.
A candidate endpoint and explicit cutover decision are subsequent steps.
The comparison is recalculating, not a historical record; evidence must be
captured when checks are performed. Full formula manifests and private
workbook review links remain in the local workspace session records.
