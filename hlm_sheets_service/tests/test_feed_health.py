from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from test_parallel_audit import fixture

from hlm_sheets_service.feed_health import FeedHealth
from hlm_sheets_service.status import V1_1_HEADERS

NOW = datetime(2026, 9, 12, 14, tzinfo=timezone.utc)


def source_fixture():
    rows = fixture()
    source = Mock(sheet_range="22_parallel_ha!A1:AA3")
    source.read_ranges.return_value = [rows[1], rows[2]]
    return source


def test_evaluation_health_never_claims_importer_freshness():
    health = FeedHealth(source_fixture()).read(NOW)
    assert health["evaluation_fresh"] is True
    assert health["freshness_verified"] is False
    assert health["upstream_import"]["verified"] is False
    assert health["last_success_at"] == NOW.isoformat()
    assert health["property_count"] == health["expected_property_count"] == 2


def test_failure_preserves_success_time_and_redacts_exception_details():
    source = source_fixture()
    health = FeedHealth(source)
    health.read(NOW)
    source.read_ranges.side_effect = RuntimeError("private credential")
    result = health.read(NOW + timedelta(minutes=1))
    assert result["last_success_at"] == NOW.isoformat()
    assert result["last_attempt_at"] != result["last_success_at"]
    assert result["evaluation_fresh"] is False
    assert result["error"] == "source_unavailable:RuntimeError"
    assert "private credential" not in str(result)


def test_stale_future_missing_property_and_failed_gates():
    for seconds in (901, -121):
        result = FeedHealth(source_fixture()).read(NOW + timedelta(seconds=seconds))
        assert result["evaluation_fresh"] is False
        assert result["last_success_at"] is None
    source = source_fixture()
    source.read_ranges.return_value[0].pop()
    result = FeedHealth(source).read(NOW)
    assert result["expected_properties_present"] is False
    assert result["error"]
    source = source_fixture()
    source.read_ranges.return_value[1][0][1] = "FAIL"
    result = FeedHealth(source).read(NOW)
    assert result["source_checks_ok"] is False
    assert result["last_success_at"] is None


def test_future_property_cannot_be_hidden_by_current_other_property():
    source = source_fixture()
    source.read_ranges.return_value[0][1][V1_1_HEADERS.index("source_updated_at")] = (
        "2026-09-12T14:03:00Z"
    )
    result = FeedHealth(source).read(NOW)
    assert result["evaluation_age_seconds"] == 0
    assert result["evaluation_fresh"] is False
