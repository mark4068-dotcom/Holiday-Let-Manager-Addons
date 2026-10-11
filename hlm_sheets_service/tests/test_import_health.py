from datetime import datetime, timedelta, timezone

import pytest

from hlm_sheets_service.import_health import importer_health

NOW = datetime(2026, 10, 11, 16, 20, tzinfo=timezone.utc)


def heartbeat(**changes):
    values = {
        "last_attempt_at": "2026-10-11T16:18:18.466Z",
        "last_success_at": "2026-10-11T16:18:21.452Z",
        "source_timestamp": "", "status": "ok", "error": "",
        "records_imported": "8", "snapshot_id": "generation-1",
        "attempt_id": "generation-1", "source_received_at": "2026-10-11T16:18:21.156Z",
        "source_timestamp_kind": "not_provided", "source_count": "2",
    }
    values.update(changes)
    return [list(values), list(values.values())]


def test_success_does_not_invent_source_modification_time():
    result = importer_health(heartbeat(), NOW)
    assert result["verified"] and result["fresh"]
    assert result["source_timestamp"] is None
    assert result["records_imported"] == 8
    assert result["source_timestamp_kind"] == "not_provided"


@pytest.mark.parametrize("status", ["running", "error"])
def test_later_unsuccessful_attempt_is_not_fresh(status):
    result = importer_health(heartbeat(
        status=status, last_attempt_at="2026-10-11T16:19:00Z",
        attempt_id="generation-2", error="private calendar URL"), NOW)
    assert result["verified"] and not result["fresh"]
    assert result["last_success_at"] == "2026-10-11T16:18:21.452Z"
    assert result["snapshot_id"] == "generation-1"
    assert "private calendar" not in str(result)


def test_stale_import_cannot_be_hidden_by_new_evaluation_clock():
    result = importer_health(heartbeat(), NOW + timedelta(hours=2))
    assert result["verified"] and not result["fresh"]
    assert result["error"] == "import_success_stale"


@pytest.mark.parametrize("changes", [
    {"last_success_at": "2026-10-11T16:30:00Z"},
    {"last_success_at": "2026-10-11T16:18:21"},
    {"source_count": "1"}, {"records_imported": "-1"},
    {"snapshot_id": "wrong-generation"},
    {"source_timestamp_kind": "guessed"},
    {"source_received_at": "2026-10-11T16:19:00Z"},
])
def test_invalid_heartbeat_fails_closed(changes):
    result = importer_health(heartbeat(**changes), NOW)
    assert not result["verified"] and not result["fresh"]
    assert result["error"] == "invalid_importer_heartbeat"


def test_missing_range_fails_closed():
    assert not importer_health([["#REF!"]], NOW)["verified"]


def test_success_threshold_boundary():
    success = datetime.fromisoformat("2026-10-11T16:18:21.452+00:00")
    assert importer_health(heartbeat(), success + timedelta(seconds=5400))["fresh"]
    assert not importer_health(heartbeat(), success + timedelta(seconds=5401))["fresh"]


def test_audit_retains_producer_generation_separately(tmp_path):
    from unittest.mock import Mock
    from test_parallel_audit import fixture
    from hlm_sheets_service.parallel_audit import ParallelAudit
    from hlm_sheets_service.import_health import HEARTBEAT_RANGE
    from hlm_sheets_service.status import V1_1_HEADERS

    model = fixture()
    for row in model[1][1:]:
        row[V1_1_HEADERS.index("source_updated_at")] = NOW.isoformat()
    source = Mock(sheet_range="22_parallel_ha!A1:AA3")
    source.read_ranges.side_effect = lambda ranges: (
        [heartbeat()] if ranges == [HEARTBEAT_RANGE] else [model[1], model[2]]
    )
    audit = ParallelAudit(source, str(tmp_path), production=True)
    audit.sample(NOW)
    record = audit.read_day("2026-10-11")["records"][0]
    assert record["upstream_import"]["snapshot_id"] == "generation-1"
    assert record["upstream_import"]["fresh"]
    assert record["compared_fields"] == 0
    assert not record["freshness_verified"]
