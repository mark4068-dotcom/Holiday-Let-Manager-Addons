"""Audit parity, durability, failure and privacy checks."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from hlm_sheets_service.parallel_audit import CHECKS, ParallelAudit, compare_ranges
from hlm_sheets_service.status import V1_1_HEADERS

NOW = datetime(2026, 9, 12, 15, tzinfo=timezone.utc)


def fixture():
    rows = [V1_1_HEADERS]
    for prop in ("skysail", "crossjack"):
        record = {key: "" for key in V1_1_HEADERS}
        record.update(
            property_id=prop,
            property_name=prop.title(),
            property_status="Vacant",
            schema_version="1.1",
            source_updated_at="12/09/2026 15:00:00",
            next_booking_reference="private-booking-reference",
            cleaner="private-cleaner",
        )
        rows.append([record[key] for key in V1_1_HEADERS])
    return [rows, deepcopy(rows), [[key, "PASS"] for key in sorted(CHECKS)]]


class AuditTest(unittest.TestCase):
    def test_parity_ignores_clock_and_normalizes_dates(self):
        data = fixture()
        data[0][1][V1_1_HEADERS.index("last_check_out")] = "11-Sep-26"
        data[1][1][V1_1_HEADERS.index("last_check_out")] = "11/09/2026"
        data[1][1][V1_1_HEADERS.index("source_updated_at")] = "12/09/2026 15:01:00"
        row = compare_ranges(data, NOW)
        self.assertEqual(row["status"], "matched")
        self.assertEqual(row["compared_fields"], 52)
        self.assertIn("private-booking-reference", json.dumps(row))
        self.assertIn("private-cleaner", json.dumps(row))

    def test_mismatch_records_authorized_diagnostic_values(self):
        data = fixture()
        data[1][1][V1_1_HEADERS.index("property_status")] = "Occupied"
        data[1][1][V1_1_HEADERS.index("booking_reference")] = "secret-reference"
        row = compare_ranges(data, NOW)
        self.assertEqual(row["status"], "different")
        self.assertEqual(len(row["differences"]), 2)
        self.assertEqual(row["differences"][1]["candidate"], "secret-reference")

    def test_empty_missing_or_invalid_candidate_is_never_matched(self):
        for candidate in ([], [V1_1_HEADERS], fixture()[1][:2], [["bad header"]]):
            data = fixture()
            data[1] = candidate
            self.assertEqual(compare_ranges(data, NOW)["status"], "error")

    def test_missing_failed_and_error_checks_are_errors_warnings_are_not(self):
        for checks in (
            [],
            [[k, "FAIL"] for k in CHECKS],
            [[k, "#REF!"] for k in CHECKS],
        ):
            data = fixture()
            data[2] = checks
            self.assertEqual(compare_ranges(data, NOW)["status"], "error")
        data = fixture()
        data[2] = [
            [k, "WARN" if k == "timestamp_semantics" else "PASS"] for k in CHECKS
        ]
        self.assertEqual(compare_ranges(data, NOW)["status"], "matched")

    def test_retention_restart_failures_and_monitoring_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Mock()
            source.read_ranges.return_value = fixture()
            audit = ParallelAudit(source, directory)
            audit.sample(NOW - timedelta(days=91))
            audit.sample(NOW)
            self.assertEqual(len(list(Path(directory).glob("*.jsonl"))), 1)
            source.read_ranges.side_effect = RuntimeError("private token must not leak")
            audit.sample(NOW + timedelta(minutes=5))
            source.read_ranges.side_effect = None
            audit.sample(NOW + timedelta(minutes=20))
            report = ParallelAudit(source, directory).report(
                NOW + timedelta(minutes=21)
            )
            self.assertEqual(report["counts"], {"matched": 2, "error": 1})
            self.assertEqual(len(report["gaps"]), 1)
            self.assertFalse(report["audit_stale"])
            self.assertTrue(audit.report(NOW + timedelta(minutes=31))["audit_stale"])
            content = next(Path(directory).glob("*.jsonl")).read_text()
            self.assertNotIn("private token", content)
            self.assertEqual(
                next(Path(directory).glob("*.jsonl")).stat().st_mode & 0o777, 0o600
            )

    def test_empty_and_truncated_log_cannot_claim_complete_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = ParallelAudit(Mock(), directory)
            self.assertTrue(audit.report(NOW)["audit_stale"])
            (Path(directory) / "2026-09-12.jsonl").write_text("{incomplete\n")
            self.assertEqual(audit.report(NOW)["corrupt_lines"], 1)

    def test_daily_export_preserves_diagnostics_and_rejects_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Mock()
            source.read_ranges.return_value = fixture()
            audit = ParallelAudit(source, directory)
            audit.sample(NOW)
            result = audit.read_day("2026-09-12")
            self.assertEqual(
                result["records"][0]["raw_rows"]["candidate"], fixture()[1]
            )
            for day in ("../../options", "2026-99-99", "2026-09-12/../options.json"):
                with self.assertRaises(ValueError):
                    audit.read_day(day)


if __name__ == "__main__":
    unittest.main()
