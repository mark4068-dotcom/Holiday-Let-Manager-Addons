# IOW Ferry Status timeout recovery — 30 October 2026

## Incident and cause

Production Home Assistant reported stale ferry data. Its last successful
collection was 28 October 2026 at 21:42:06 GMT. The next attempt began at
21:46:50 GMT and reported `Collection timed out after 300 seconds`; no later
attempts were recorded. All six services remained on the cached payload.

Version 0.1.11 raced the collector against a timeout but did not terminate the
underlying collection. If it never settled, `collectionInFlight` stayed true
and every later refresh was skipped even though the public `running` field
was false. Restarting the add-on restored a successful six-service collection
on 30 October at 17:25:53 GMT, with no source errors.

## Repair and release

Version 0.1.12 isolates collections in child processes, terminates the worker
and its browser descendants on timeout, and releases the refresh lock after
shutdown. Linux cleanup includes descendants in separate process groups,
which Playwright can use for Chromium. Failed collections still preserve the
last complete payload and report stale/error metadata.

The change was merged through
[PR #17](https://github.com/mark4068-dotcom/Holiday-Let-Manager-Addons/pull/17)
as commit `648ea25` and tagged `iow-ferry-status-v0.1.12`. Version metadata in
`config.yaml`, `package.json`, `package-lock.json`, and the Dockerfile was
updated together. Home Assistant's catalogue was refreshed and the user
installed the update through its normal add-on update flow.

The authoritative repository is `Holiday-Let-Manager-Addons`; production uses
slug `32662a46_iow_ferry_status`. The separate standalone ferry repository was
not changed. The previous production version was 0.1.11.

## Validation and observed result

- Local tests: 13 passed; the additional Linux-only detached-process test was
  skipped on macOS.
- Repository metadata validation passed. GitHub's required checks all passed,
  including Linux JavaScript tests and the amd64 ferry container build.
- Home Assistant displayed installed version 0.1.12 after the update.
- Live `/health` reported all six services, `stale: false`, no errors, and a
  successful collection at 17:52:52 GMT on 30 October.

The observed production collection verifies that the worker can collect live
operator data. Timeout recovery and descendant cleanup were tested with
controlled workers; a real operator hang was not deliberately induced in
production. There was no separate development-HA live scrape or aarch64
validation in this session. This repair does not address route parsing or
operator notice classification.

## Recovery reference

Use [the operating documentation](../DOCS.md#refresh-recovery-and-health) to
interpret health fields and diagnose delayed updates. For rollback, restore a
saved add-on backup of the previous version and its data. Version 0.1.11 retains
the defect; rollback is not the long-term remedy. No backup creation or rollback
was verified during this session.
