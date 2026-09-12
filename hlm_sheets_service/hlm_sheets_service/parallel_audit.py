"""Private, durable observation of the live and candidate Sheets contracts."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
import re
from pathlib import Path
import threading
import time
from typing import Any

from .status import ContractError, V1_1_HEADERS, build_v1_1_status_payload

RANGES = [
    "21_published_ha_v1_1_draft!A1:AA10",
    "22_parallel_ha!A1:AA10",
    "02_import_property_status!A6:B24",
]
CHECKS = {
    "booking_import",
    "booking_capacity",
    "booking_properties",
    "booking_dates",
    "booking_references",
    "duplicate_active_references",
    "overlapping_live_bookings",
    "changeover_errors",
    "published_errors",
    "timestamp_semantics",
    "history_policy",
    "next_changeover_policy",
    "mode",
    "historical_reference_quality",
    "changeover_properties",
    "changeover_capacity",
    "pat_formula_errors",
    "clock_controls",
}
EXPECTED_IDS = {"skysail", "crossjack"}


def compare_ranges(ranges: list, now: datetime) -> dict[str, Any]:
    record: dict[str, Any] = {
        "audit_version": 1,
        "checked_at": now.isoformat(),
        "status": "matched",
        "errors": {},
        "differences": [],
        "compared_fields": 0,
        "source_checks": {},
        "snapshots": {},
        "evaluation_timestamps": {},
        "raw_rows": dict(zip(("live", "candidate", "checks"), ranges)),
    }
    parsed = {}
    if len(ranges) != 3:
        record["errors"]["source"] = "missing_ranges"
    for index, side in enumerate(("live", "candidate")):
        try:
            parsed[side] = build_v1_1_status_payload(ranges[index])["properties"]
            if set(parsed[side]) != EXPECTED_IDS:
                record["errors"][side] = "unexpected_property_set"
            record["snapshots"][side] = {
                prop: {k: v for k, v in values.items() if k != "source_updated_at"}
                for prop, values in parsed[side].items()
                if prop in EXPECTED_IDS
            }
            record["evaluation_timestamps"][side] = {
                prop: values["source_updated_at"]
                for prop, values in parsed[side].items()
                if prop in EXPECTED_IDS
            }
        except (ContractError, IndexError, KeyError, TypeError, ValueError):
            record["errors"][side] = "invalid_contract"
    if len(ranges) >= 3:
        checks = {
            row[0]: row[1] for row in ranges[2] if len(row) >= 2 and row[0] in CHECKS
        }
        record["source_checks"] = {
            name: value
            if value in {"PASS", "FAIL", "WARN", "INFO", "PARALLEL_ONLY"}
            else "ERROR"
            for name, value in checks.items()
        }
        if set(checks) != CHECKS:
            record["errors"]["checks"] = "missing_checks"
        elif any(
            value in {"FAIL", "ERROR"} for value in record["source_checks"].values()
        ):
            record["errors"]["checks"] = "failed_checks"
    for prop in sorted(EXPECTED_IDS):
        if not all(prop in parsed.get(side, {}) for side in ("live", "candidate")):
            continue
        for field in V1_1_HEADERS:
            if field == "source_updated_at":
                continue
            a, b = parsed["live"][prop][field], parsed["candidate"][prop][field]
            record["compared_fields"] += 1
            if a != b or type(a) is not type(b):
                difference = {"property_id": prop, "field": field}
                difference.update(live=a, candidate=b)
                record["differences"].append(difference)
    if record["errors"]:
        record["status"] = "error"
    elif record["differences"]:
        record["status"] = "different"
    return record


class ParallelAudit:
    def __init__(
        self, source, directory: str, interval: int = 300, retention: int = 90
    ):
        self.source = source
        self.directory = Path(directory)
        self.interval = interval
        self.retention = retention
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.last_write_error = False

    def sample(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        try:
            record = compare_ranges(self.source.read_ranges(RANGES), now)
        except Exception as error:
            record = {
                "audit_version": 1,
                "checked_at": now.isoformat(),
                "status": "error",
                "errors": {"source": type(error).__name__},
                "differences": [],
                "compared_fields": 0,
            }
        with self.lock:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            path = self.directory / (now.date().isoformat() + ".jsonl")
            fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.last_write_error = False
            cutoff = (now - timedelta(days=self.retention)).date().isoformat()
            for old in self.directory.glob("????-??-??.jsonl"):
                if old.stem < cutoff:
                    old.unlink()
        return record

    def run(self):
        while not self.stop.is_set():
            started = time.monotonic()
            try:
                self.sample()
            except Exception:
                self.last_write_error = True
                print(
                    "WARNING: Parallel audit persistence failed; status service remains available.",
                    flush=True,
                )
            self.stop.wait(max(1, self.interval - (time.monotonic() - started)))

    def start(self):
        thread = threading.Thread(
            target=self.run, name="sheets-parallel-audit", daemon=True
        )
        thread.start()
        return thread

    def report(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        counts, fields, errors, days = Counter(), Counter(), Counter(), {}
        first = last = previous = None
        gaps, incidents, corrupt = [], [], 0
        with self.lock:
            for path in sorted(self.directory.glob("????-??-??.jsonl")):
                with path.open(encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            row = json.loads(line)
                            checked = datetime.fromisoformat(row["checked_at"])
                            status = row["status"]
                        except (ValueError, KeyError, TypeError):
                            corrupt += 1
                            continue
                        first = first or checked
                        if (
                            previous
                            and (checked - previous).total_seconds() > self.interval * 2
                        ):
                            gaps.append(
                                {
                                    "from": previous.isoformat(),
                                    "to": checked.isoformat(),
                                }
                            )
                        previous = last = checked
                        counts[status] += 1
                        daily = days.setdefault(checked.date().isoformat(), Counter())
                        daily[status] += 1
                        for d in row.get("differences", []):
                            fields[d["property_id"] + "." + d["field"]] += 1
                        for side, error in row.get("errors", {}).items():
                            errors[side + ":" + error] += 1
                        if status != "matched":
                            incidents.append(
                                {
                                    k: row[k]
                                    for k in (
                                        "checked_at",
                                        "status",
                                        "differences",
                                        "errors",
                                    )
                                }
                            )
            age = (now - last).total_seconds() if last else None
            return {
                "enabled": True,
                "interval_seconds": self.interval,
                "retention_days": self.retention,
                "first_check": first.isoformat() if first else None,
                "last_check": last.isoformat() if last else None,
                "audit_stale": age is None or age > self.interval * 2,
                "last_write_failed": self.last_write_error,
                "counts": dict(counts),
                "daily_counts": days,
                "mismatch_fields": dict(fields),
                "error_counts": dict(errors),
                "gaps": gaps,
                "corrupt_lines": corrupt,
                "recent_incidents": incidents[-100:],
                "incidents_total": len(incidents),
                "timestamp_semantics": "Independent evaluation clocks; excluded from parity. Upstream freshness unverified.",
            }

    def read_day(self, day: str) -> dict:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise ValueError("Expected YYYY-MM-DD")
        datetime.strptime(day, "%Y-%m-%d")
        records, corrupt = [], 0
        with self.lock:
            path = self.directory / (day + ".jsonl")
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        records.append(json.loads(line))
                    except ValueError:
                        corrupt += 1
        return {"date": day, "records": records, "corrupt_lines": corrupt}
