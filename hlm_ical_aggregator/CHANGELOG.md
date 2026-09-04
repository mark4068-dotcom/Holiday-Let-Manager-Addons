# Changelog

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
