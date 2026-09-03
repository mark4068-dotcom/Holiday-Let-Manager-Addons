"""Strict v1.0 validation and row projection for HLM event batches."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

EVENT_HEADERS = (
    "schema_version",
    "event_id",
    "timestamp",
    "recorded_at",
    "received_at",
    "property",
    "asset_type",
    "asset",
    "event_family",
    "event_type",
    "source",
    "adapter",
    "adapter_version",
    "operator",
    "method",
    "authenticated",
    "change_source",
    "correlation_id",
    "related_event_id",
    "snapshot_reference",
    "raw_reference",
    "old_value",
    "new_value",
    "access_component",
    "climate_component",
    "climate_system_mode",
    "climate_zone_mode",
    "climate_override_until",
    "climate_current_temperature",
    "climate_target_temperature",
    "climate_heat_demand",
    "climate_dhw_state",
    "climate_fault",
)
REQUIRED = {
    "schema_version",
    "event_id",
    "timestamp",
    "recorded_at",
    "property",
    "asset_type",
    "asset",
    "event_family",
    "event_type",
    "source",
    "adapter",
    "adapter_version",
}
FAMILY_ASSET = {
    "access": "access_point",
    "ev_charging": "ev_charger",
    "climate": "thermostat",
}
EVENT_TYPES = {
    "access": {
        "access_unlocked",
        "access_locked",
        "door_opened",
        "door_closed",
        "invalid_access_attempt",
        "health_changed",
        "availability_changed",
        "battery_low",
        "battery_critical",
        "battery_recovered",
    },
    "ev_charging": {
        "charge_status_changed",
        "charger_enabled_changed",
        "charger_health_changed",
        "charger_availability_changed",
    },
    "climate": {
        "target_temperature_changed",
        "hvac_mode_changed",
        "preset_mode_changed",
        "availability_changed",
    },
}


class EventContractError(ValueError):
    """A request cannot be safely represented by the event contract."""


def validate_batch(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "events"}:
        raise EventContractError("request must contain only schema_version and events")
    if payload["schema_version"] != "1.0":
        raise EventContractError("unsupported schema_version")
    events = payload["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= 100:
        raise EventContractError("events must contain between 1 and 100 items")
    return [_validate_event(event) for event in events]


def _validate_event(event: object) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EventContractError("each event must be an object")
    unknown = set(event) - (set(EVENT_HEADERS) - {"received_at"})
    missing = REQUIRED - set(event)
    if unknown or missing:
        raise EventContractError("event fields do not match the v1.0 contract")
    if event["schema_version"] != "1.0":
        raise EventContractError("event schema_version must be 1.0")
    try:
        UUID(str(event["event_id"]))
    except ValueError as error:
        raise EventContractError("event_id must be a UUID") from error
    for key in ("timestamp", "recorded_at"):
        _aware_timestamp(event[key], key)
    family = event.get("event_family")
    if family not in FAMILY_ASSET or event.get("asset_type") != FAMILY_ASSET[family]:
        raise EventContractError("event family and asset_type do not match")
    if event.get("event_type") not in EVENT_TYPES[family]:
        raise EventContractError("unsupported event_type")
    for key, value in event.items():
        if isinstance(value, str) and (not value.strip() or len(value) > 500):
            raise EventContractError(
                f"{key} must be non-empty and at most 500 characters"
            )
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise EventContractError(f"{key} must be a scalar")
    component = event.get("access_component")
    if component is not None and (
        family != "access"
        or component not in {"lock", "keypad", "lock_keypad", "door_sensor"}
    ):
        raise EventContractError("invalid access_component")
    return event


def rows_for_events(events: list[dict[str, Any]]) -> list[list[Any]]:
    received_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return [
        [
            event.get(header, received_at if header == "received_at" else "")
            for header in EVENT_HEADERS
        ]
        for event in events
    ]


def _aware_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str):
        raise EventContractError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EventContractError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventContractError(f"{field} must include a timezone")
