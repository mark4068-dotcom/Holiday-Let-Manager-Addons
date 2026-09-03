"""Tests for the strict HLM event write contract."""

from datetime import datetime
from uuid import uuid4

import pytest
from hlm_sheets_service.events import (
    EVENT_HEADERS,
    EventContractError,
    rows_for_events,
    validate_batch,
)


def access_event(**overrides):
    event = {
        "schema_version": "1.0",
        "event_id": str(uuid4()),
        "timestamp": "2026-09-03T13:00:00Z",
        "recorded_at": "2026-09-03T13:00:01Z",
        "property": "Topgallant",
        "asset_type": "access_point",
        "asset": "Front Door",
        "event_family": "access",
        "event_type": "battery_low",
        "source": "sensor.door_door_battery",
        "adapter": "yale",
        "adapter_version": "1.0.0",
        "access_component": "lock",
        "old_value": 25,
        "new_value": 24,
    }
    event.update(overrides)
    return event


def test_valid_batch_projects_exact_raw_header_order() -> None:
    event = access_event(operator="=not-a-formula")
    events = validate_batch({"schema_version": "1.0", "events": [event]})
    rows = rows_for_events(events)

    assert len(EVENT_HEADERS) == 33
    assert len(rows[0]) == 33
    assert rows[0][EVENT_HEADERS.index("event_id")] == event["event_id"]
    assert rows[0][EVENT_HEADERS.index("operator")] == "=not-a-formula"
    assert rows[0][EVENT_HEADERS.index("received_at")].endswith("Z")
    datetime.fromisoformat(
        rows[0][EVENT_HEADERS.index("received_at")].replace("Z", "+00:00")
    )


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"schema_version": "1.0", "events": []}, "between 1 and 100"),
        (
            {"schema_version": "1.0", "events": [access_event(extra="bad")]},
            "fields do not match",
        ),
        (
            {
                "schema_version": "1.0",
                "events": [access_event(timestamp="2026-09-03T13:00:00")],
            },
            "include a timezone",
        ),
        (
            {
                "schema_version": "1.0",
                "events": [access_event(access_component="camera")],
            },
            "invalid access_component",
        ),
        (
            {
                "schema_version": "1.0",
                "events": [access_event(event_type="made_up")],
            },
            "unsupported event_type",
        ),
    ],
)
def test_invalid_batches_are_rejected(payload, message) -> None:
    with pytest.raises(EventContractError, match=message):
        validate_batch(payload)
