# HLM iCalendar Aggregator app

**Version 0.5.0:** retains property booking feeds and VisitIOW for HA and supports
two independent Google destinations: the existing VisitIOW events calendar and
an optional Crossjack/Skysail bookings calendar. Booking publication is disabled
by default and requires a separate calendar ID. See `DOCS.md` for setup and
diagnostics. The old scraper remains retired; the
[9 November report](session-reports/2026-11-09-old-guide-retirement.md) records
the earlier events-only deployment and rollback plan.

Home Assistant app that combines independently filtered remote ICS sources into
one read-only calendar feed. See `DOCS.md` for configuration.

This is a display/diary projection, not an authoritative booking or operations
source. See [`ARCHITECTURE.md`](ARCHITECTURE.md) and the
[production cutover report](session-reports/2026-09-04-icalendar-aggregator-production-cutover.md)
for the as-built design, migration state and restartable context.
