# HLM iCalendar Aggregator production cutover — 4 September 2026

## Outcome

HLM iCalendar Aggregator 0.2.2 is running on Production Home Assistant. It
combines the Crossjack and Skysail Guesty feeds with all current HLM Guest Guide
events, filters Guesty blockers, and supplies one Remote Calendar for display
and diary use.

Production also publishes the aggregate outbound to the private
`Sailcottages HLM` Google Calendar. It is the sole live Google publisher; Dev
publication is disabled and the Dev HA can remain powered off.

The aggregator is not authoritative for bookings, occupancy or operations.
Those facts continue to come from the private HLM Google Sheets exchange feed.

## Repositories and release

- Standalone source and design repository:
  `mark4068-dotcom/HLM_iCalendar_Aggregator`, branch `main`.
- Home Assistant app distribution repository:
  `mark4068-dotcom/Holiday-Let-Manager-Addons`, branch `main`.
- Installed app version: 0.2.2.
- Production app slug: `32662a46_hlm_ical_aggregator`.
- Production internal hostname: `32662a46-hlm-ical-aggregator`.
- Guest Guide internal hostname: `32662a46-hlm-guide-calendar`.
- The app supports `amd64`, matching the Home Assistant OS installation on the
  2011 Mac mini hardware.

The standalone source was copied into `hlm_ical_aggregator/` in the shared app
repository. No runtime configuration or credentials were copied into Git.

## Production configuration

Production has three enabled sources:

1. Crossjack Guesty, with title prefix `Crossjack — `.
2. Skysail Guesty, with title prefix `Skysail — `.
3. HLM Guest Guide, with title prefix `Local event — `.

Both Guesty sources exclude an exact case-insensitive summary match for
`Blocked by Guesty` and exclude cancelled events. Guesty URLs are retained only
in the Home Assistant app options. Guest Guide uses its internal app hostname
and a 365-day horizon, which currently exposes all six discovered events.

The app starts on boot, has watchdog protection enabled and exposes its
administrator status page through Home Assistant ingress. Port 8789 is for the
trusted LAN only and must not be forwarded through the router.

Home Assistant imports:

```text
http://32662a46-hlm-ical-aggregator:8789/combined.ics
```

as `calendar.hlm_combined_calendar`. Built-in polling is disabled. The enabled
`automation.hlm_combined_calendar_refresh` calls
`homeassistant.update_entity` every 15 minutes.

The existing Crossjack and Skysail ICS Calendar entities remain enabled for
parallel comparison and must not be removed before monitoring completes.

## Google Calendar publication

- Destination: private `Sailcottages HLM` calendar.
- Owner: `sailcottagesha@gmail.com`.
- Writer: dedicated `hlm-calendar-publisher` service account with no
  project-wide roles.
- Access: the service account can edit only the destination calendar.
- Direction: outbound only; Home Assistant has no inbound internet exposure.
- Title policy: retain Guesty titles and details because the source calendars
  contain no private data.
- Safety: stable event IDs, private HLM management markers, dry-run, bounded
  retries, publication health and an empty-feed deletion guard.

The credential exists only at runtime. On Production the host path is:

```text
/addon_configs/32662a46_hlm_ical_aggregator/google-service-account.json
```

The container sees it as `/config/google-service-account.json`. The host file
mode is 600. The calendar identifier remains only in app options. Neither value
may be printed into logs, copied into documentation or committed to Git.

## Validation completed

- Ruff formatting completed successfully.
- Ruff lint completed successfully.
- All 19 automated tests passed, including the end-to-end HTTP server test.
- The Home Assistant nested source-list schema was accepted by Supervisor.
- The amd64 container built and ran on the 2011 Mac mini HA OS hardware.
- Pre-configuration `/health` remains live with state `setup`, preventing a
  watchdog restart loop.
- Duplicate IDs, invalid regular expressions and malformed source settings are
  rejected at startup.
- Refresh status returns `running: false` after synchronous completion.
- A named pre-install Production backup was uploaded to all three configured
  backup locations.
- Production `/health` and `/api/v1/status` reported healthy.
- The final aggregate contained 16 events: six Crossjack, four Skysail and six
  Guest Guide events.
- Four Guesty blockers were excluded and no exact `Blocked by Guesty` summary
  remained.
- The combined feed had zero duplicate UIDs and every event retained original
  UID and source provenance.
- Home Assistant displayed the combined calendar alongside the legacy
  calendars with the expected booking boundaries and Guest Guide entries.
- Calendar sharing and event display were confirmed from a second Google
  account.

## Publisher handover

The Dev-to-Production transition preserved a single live writer:

1. The Google credential was copied without displaying it and validated on
   Production.
2. Production dry-run found 16 desired events, 15 unchanged, one pending
   update, and zero creates or deletes.
3. Dev publication was disabled and its status confirmed `disabled`.
4. Production live publication was enabled and applied the one update.
5. A second Production reconciliation reported all 16 events unchanged with no
   error.
6. Temporary transfer files and the temporary LAN file server were removed.

## Seven-day observation period

Until at least 11 September 2026:

- Keep the legacy Crossjack and Skysail ICS Calendar entities enabled.
- Keep `calendar.hlm_combined_calendar` and its 15-minute automation enabled.
- Keep Production as the only live Google publisher.
- Dev may remain powered off; do not re-enable its publisher while Production
  publishing is enabled.
- Compare booking arrival/departure boundaries and accepted event counts.
- Investigate any missing booking, duplicate event, blocker event, persistent
  source error, cached-output warning or Google publication error.
- Do not use the aggregate or Google Calendar as an operational booking source.

## Retirement checklist

After a stable seven-day observation period:

1. Review the combined and legacy calendars for the full period.
2. Confirm there are no missing bookings or boundary differences.
3. Confirm blocker filtering, Guest Guide uniqueness and Google publication
   health remain correct.
4. Exercise and record one controlled failed-source/last-known-good recovery
   drill.
5. Validate the shared calendar in the intended phone calendar application.
6. Update final Production dashboards to the combined calendar while
   preserving the intended entity ID.
7. Remove the legacy ICS Calendar integration only after all prior checks pass.
8. Complete the implementation checklist and record final as-built evidence.

## Rollback

If Production publication fails, first disable its Google publisher. Power on
Dev only if a temporary publisher rollback is required, confirm Dev still has
the correct aggregate, and enable Dev publication only after Production is
confirmed disabled. Never allow both instances to publish live concurrently.

If the Production aggregate fails materially, retain the existing legacy ICS
Calendar entities and inspect `/api/v1/status`. Last-known-good output should
remain available after an upstream failure. Restore the named pre-install Home
Assistant backup only for a wider app or configuration rollback.

Do not expose credentials, source URLs or the Google calendar identifier while
diagnosing a failure.

## Rebuilding context in a future session

Read these files in order:

1. `hlm_ical_aggregator/session-reports/2026-09-04-icalendar-aggregator-production-cutover.md`
2. `hlm_ical_aggregator/ARCHITECTURE.md`
3. `hlm_ical_aggregator/DOCS.md`
4. `hlm_ical_aggregator/config.yaml`
5. `hlm_ical_aggregator/CHANGELOG.md`

Then open the standalone `HLM_iCalendar_Aggregator` repository and read its
implementation checklist. Confirm all three repositories are on `main` and
clean. Verify the standalone source with:

```sh
cd /Users/mark/Documents/GitHub/HLM_iCalendar_Aggregator
PATH="$PWD/.venv/bin:$PATH" ./scripts/verify.sh
```

Production HA is at `192.168.0.236`; Dev HA is at `192.168.0.40` and may be
offline. Check Production without exposing configuration values:

```sh
curl -fsS http://192.168.0.236:8789/health
curl -fsS http://192.168.0.236:8789/api/v1/status
```

The expected baseline is healthy, three configured sources, 16 accepted
events, four excluded events, publication enabled and live, and a repeat
publication result of 16 unchanged events with no error. Counts can legitimately
change as Guesty bookings and Guide events change; investigate structure,
filtering and errors rather than assuming 16 is permanently correct.

Do not commit `.venv`, app options, ICS source URLs, service-account JSON,
downloaded calendar data or other credentials. The next planned work is the
seven-day parity review, controlled last-known-good drill, phone-app validation
and final legacy-calendar retirement.
