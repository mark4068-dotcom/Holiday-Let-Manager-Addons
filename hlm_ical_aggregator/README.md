# HLM iCalendar Aggregator app

**Current production, 9 November 2026:** aggregator 0.4.3 retains property booking feeds and VisitIOW for HA; Google publication is VisitIOW-only. The old scraper is uninstalled and its source disabled. Earlier mixed-feed diagrams/setup details below describe the original design. See the [session report and rollback plan](session-reports/2026-11-09-old-guide-retirement.md).

Home Assistant app that combines independently filtered remote ICS sources into
one read-only calendar feed. See `DOCS.md` for configuration.

This is a display/diary projection, not an authoritative booking or operations
source. See [`ARCHITECTURE.md`](ARCHITECTURE.md) and the
[production cutover report](session-reports/2026-09-04-icalendar-aggregator-production-cutover.md)
for the as-built design, migration state and restartable context.
