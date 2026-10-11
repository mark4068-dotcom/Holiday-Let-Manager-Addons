# 0.4.0 — Redesigned production feed

- Read v1.1 from 22_parallel_ha; project v1.0 from the same source.
- Reject stale (>15 minutes), future (>2 minutes) evaluation clocks and
  unexpected property sets. Upstream calendar freshness remains separate.
- Preserve historical comparison logs and record production health without
  claiming self-comparison parity. Keep five-minute sampling and 90-day retention.
- Accept UTC ISO timestamps with fractional seconds across the BST/GMT change.

Deployment prerequisite: activate and verify the scheduled source clock,
publish its UTC timestamp, and change the source diagnostic mode to PRODUCTION.

# Changelog

## 0.3.2 — 12 September 2026

- Add opt-in five-minute live/candidate Sheets audit with 90-day persistent
  diagnostic history, including successes, differences and source failures.
- Add private authenticated summary and per-day history endpoints.
- Preserve existing production read ranges and event-writing behaviour.
