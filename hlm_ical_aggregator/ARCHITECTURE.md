# HLM iCalendar Aggregator Architecture

## Purpose and boundary

The aggregator creates convenient calendar views from non-authoritative
calendar sources. It must never become a booking, occupancy or operational
decision source. HLM continues to obtain those facts from the private Google
Sheets exchange feed.

Initial inputs are the Crossjack and Skysail Guesty ICS feeds and the local HLM
Guest Guide ICS feed. Additional remote ICS feeds can be added through
configuration without changing the application.

## Production data flow

```text
Guesty Crossjack ICS ----+
Guesty Skysail ICS ------+--> filter/normalise/deduplicate --> combined.ics
HLM Guest Guide ICS -----+               |                       |
future ICS sources ------+               |                       +--> HA Remote Calendar
                                         |
                                         +--> outbound-only publisher
                                                       |
                                                       +--> Sailcottages HLM
                                                            private Google Calendar
```

Each source is fetched and processed independently. A successful filtered
source is written atomically to its own cache. If a later download fails, the
last successful source cache remains eligible for the combined calendar. A
failure must not replace a good cache with an empty or invalid response.

## Filtering and identity

Filters are source-specific regular expressions evaluated against event
summary and description. Exclusions run first; an optional inclusion must then
match. Cancelled events are omitted by default.

The initial Guesty exclusion is an exact case-insensitive summary match for
`Blocked by Guesty`. Exact matching avoids hiding a genuine entry that merely
mentions similar wording in a description.

Every output event receives a deterministic UID namespaced by source ID. The
original UID is retained in `X-HLM-ORIGINAL-UID`; `X-HLM-SOURCE-ID` and
`X-HLM-SOURCE-NAME` preserve provenance. This prevents cross-feed UID
collisions and gives the Google publisher a stable synchronization key.

## Outputs

- `/combined.ics`: all accepted events from enabled sources.
- `/sources/<source-id>.ics`: one filtered source, useful for diagnostics.
- `/api/v1/status`: source counts, cache state, timestamps and errors.
- `/health`: watchdog result. It reports degraded details but remains live
  while a last-known-good output is available. Before any source is enabled it
  returns HTTP 200 with state `setup`, preventing a first-run watchdog loop.
- `/`: admin status page available through Home Assistant ingress.

ICS endpoints can use optional HTTP Basic Authentication. Port 8789 stays on
the trusted LAN and must not be forwarded through the router.

## Deployment topology

The proven version is installed on Production from the public
`Holiday-Let-Manager-Addons` repository. Its source URLs and credentials exist
only in Home Assistant runtime configuration. The app starts on boot, is
protected by the Home Assistant watchdog and exposes its administrator view
through ingress.

Home Assistant imports the combined feed as
`calendar.hlm_combined_calendar`. Built-in polling is disabled and a dedicated
automation refreshes the entity every 15 minutes. The legacy Crossjack and
Skysail ICS Calendar entities remain enabled only for the seven-day parallel
comparison and are not dependencies of the aggregator.

Development proved the container, source configuration, dashboard and Google
publisher. Its publisher is now disabled and Production is the sole live
writer, so the Dev HA may remain powered off.

## External publication

Production synchronizes only aggregator-managed events outbound to the
dedicated private `Sailcottages HLM` Google Calendar owned by
`sailcottagesha@gmail.com`. Deterministic event
IDs and private `hlmManaged`, `hlmSyncKey` and `hlmFingerprint` properties make
publication idempotent. The reconciler lists only marked events and therefore
cannot update or delete unrelated calendar entries. A default-on empty-feed
guard prevents a transient empty aggregate from clearing the destination.

Dry-run uses the real destination inventory but performs no writes. Calendar
API rate-limit and server failures use bounded exponential backoff. Publication
has independent health state, so an internet or Google failure does not make
the local feed unavailable or cause the Home Assistant watchdog to restart a
working aggregator. Home Assistant does not require an internet-facing
endpoint.

Credentials remain in the app's runtime configuration directory and are never
stored in Git. The Production credential is readable only by root in the app's
private configuration directory. Temporary transfer copies were removed after
the handover. Guesty titles and details are retained because the source
calendars contain no private data. Sharing has been validated from a second
Google account.

Only one instance may publish live. A handover must validate the new instance
in dry-run, disable the old publisher, enable the new publisher and then run a
second reconciliation to confirm all managed events are unchanged.
