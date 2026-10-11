import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from test_parallel_audit import fixture

from hlm_sheets_service.parallel_audit import ParallelAudit
from hlm_sheets_service.production_health import (
    production_record,
    validate_evaluation_age,
)
from hlm_sheets_service.status import (
    V1_1_HEADERS,
    ContractError,
    build_v1_1_status_payload,
)

NOW = datetime(2026, 9, 12, 14, tzinfo=timezone.utc)


def test_production_logs_health_and_never_claims_parity():
    rows = fixture()
    record = production_record([rows[1], rows[2]], NOW)
    assert record["status"] == "healthy"
    assert record["audit_mode"] == "production_health"
    assert record["compared_fields"] == 0
    assert record["evaluation_age_seconds"] == {"skysail": 0, "crossjack": 0}
    assert set(record["snapshots"]) == {"production"}


def test_stale_future_and_missing_properties_fail_closed():
    payload = build_v1_1_status_payload(fixture()[1])
    for when in (NOW + timedelta(seconds=901), NOW - timedelta(seconds=121)):
        with pytest.raises(ContractError):
            validate_evaluation_age(payload, when)
    payload["properties"].pop("crossjack")
    with pytest.raises(ContractError):
        validate_evaluation_age(payload, NOW)


def test_explicit_utc_handles_bst_repeated_hour():
    rows = fixture()[1]
    index = V1_1_HEADERS.index("source_updated_at")
    for stamp in ("2026-10-25T00:30:00.000Z", "2026-10-25T01:30:00.000Z"):
        for row in rows[1:]:
            row[index] = stamp
        payload = build_v1_1_status_payload(rows)
        assert set(
            validate_evaluation_age(payload, datetime.fromisoformat(stamp)).values()
        ) == {0}


def test_production_audit_keeps_history_and_logs_stale_incidents():
    data = fixture()
    with tempfile.TemporaryDirectory() as directory:
        source = Mock(sheet_range="22_parallel_ha!A1:AA3")
        source.read_ranges.return_value = data
        ParallelAudit(source, directory).sample(NOW)
        source.read_ranges.return_value = [data[1], data[2]]
        audit = ParallelAudit(source, directory, production=True)
        audit.sample(NOW + timedelta(minutes=5))
        audit.sample(NOW + timedelta(minutes=20))
        report = audit.report(NOW + timedelta(minutes=21))
        assert report["counts"] == {"matched": 1, "healthy": 1, "error": 1}
        assert report["incidents_total"] == 1
        assert report["audit_mode"] == "production_health"


def test_failed_and_missing_source_checks_remain_incidents():
    rows = fixture()[1]
    assert production_record([rows, []], NOW)["status"] == "error"
    data = fixture()
    data[2][0][1] = "FAIL"
    assert production_record([rows, data[2]], NOW)["status"] == "error"
