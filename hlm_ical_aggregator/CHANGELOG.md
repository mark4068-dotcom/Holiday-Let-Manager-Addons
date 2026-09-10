# Changelog

## 0.3.1

- Recover from a Google Calendar retained-ID collision by retrying the insert
  with a second stable event identifier.

## 0.3.0

- Add the optional nightly Visit Isle of Wight event collector.
- Prefix collected titles with `VisitIOW —` and expose `/sources/viow.ics`.
- Keep VIOW and Guest Guide events independent during Phase 1 validation.
- Reject a refresh when fewer than 95% of discovered VIOW pages parse.
- Retain each listing's external Visit website destination when provided.

## 0.2.2

- Add the HTTP transport dependency required by `google-auth` at runtime.

## 0.2.1

- Correct the Home Assistant app configuration mount used for runtime-only
  Google credentials.

## 0.2.0

- Add outbound-only Google Calendar publication with deterministic event IDs.
- Mark managed events with private extended properties and never mutate unmarked events.
- Add dry-run reconciliation, bounded retries and publication diagnostics.

## 0.1.0

- Add configurable remote ICS sources and per-source include/exclude filters.
- Add stable source-namespaced event identifiers and provenance properties.
- Add filtered source feeds, combined feed, diagnostics and health endpoints.
- Retain last-known-good source and combined outputs after refresh failures.
