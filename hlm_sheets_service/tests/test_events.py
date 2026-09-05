"""Tests for the strict HLM event write contract."""

from datetime import datetime, timedelta
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


def evohome_event(**overrides):
    event = access_event(
        property="Topgallant",
        asset_type="thermostat",
        asset="Kitchen",
        event_family="climate",
        event_type="zone_override_changed",
        source="climate.kitchen",
        adapter="evohome",
        access_component=None,
        old_value="inactive",
        new_value="active_until:2026-09-04T18:00:00+01:00",
        climate_component="Kitchen",
        climate_zone_mode="TemporaryOverride",
        climate_override_until="2026-09-04T17:00:00Z",
        climate_current_temperature=22.5,
        climate_target_temperature=20.0,
        climate_fault="clear",
    )
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
    assert isinstance(rows[0][EVENT_HEADERS.index("received_at")], float)


def test_timestamp_columns_are_uk_local_google_sheets_date_values() -> None:
    event = access_event(
        timestamp="2026-09-04T16:24:41.079690Z",
        recorded_at="2026-01-04T16:24:42Z",
    )
    row = rows_for_events(validate_batch({"schema_version": "1.0", "events": [event]}))[
        0
    ]
    epoch = datetime(1899, 12, 30)

    summer = epoch + timedelta(days=row[EVENT_HEADERS.index("timestamp")])
    winter = epoch + timedelta(days=row[EVENT_HEADERS.index("recorded_at")])

    assert summer == datetime(2026, 9, 4, 17, 24, 41, 79000)
    assert winter == datetime(2026, 1, 4, 16, 24, 42)


def test_valid_evohome_context_projects_to_existing_contract_columns() -> None:
    event = evohome_event()

    events = validate_batch({"schema_version": "1.0", "events": [event]})
    row = rows_for_events(events)[0]

    assert row[EVENT_HEADERS.index("climate_component")] == "Kitchen"
    assert row[EVENT_HEADERS.index("climate_zone_mode")] == "TemporaryOverride"
    assert row[EVENT_HEADERS.index("climate_target_temperature")] == 20.0
    override = datetime(1899, 12, 30) + timedelta(
        days=row[EVENT_HEADERS.index("climate_override_until")]
    )
    assert override == datetime(2026, 9, 4, 18, 0)


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
        (
            {
                "schema_version": "1.0",
                "events": [evohome_event(climate_zone_mode="MadeUp")],
            },
            "unsupported climate_zone_mode",
        ),
        (
            {
                "schema_version": "1.0",
                "events": [
                    access_event(climate_component="Kitchen")
                ],
            },
            "climate context is valid only",
        ),
        (
            {
                "schema_version": "1.0",
                "events": [evohome_event(climate_heat_demand=101)],
            },
            "between 0 and 100",
        ),
    ],
)
def test_invalid_batches_are_rejected(payload, message) -> None:
    with pytest.raises(EventContractError, match=message):
        validate_batch(payload)
