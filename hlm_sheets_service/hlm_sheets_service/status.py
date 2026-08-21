"""Validation and JSON projection for versioned HLM publication sheets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

V1_HEADERS = [
    "property_id",
    "property_name",
    "property_status",
    "guest_ready_status",
    "live_booking",
    "current_check_in",
    "current_check_out",
    "days_to_checkout",
    "booking_reference",
    "last_check_out",
    "days_since_checkout",
    "last_changeover",
    "booking_company",
    "cleaner",
    "form_result",
    "report_status",
    "source_updated_at",
    "schema_version",
]
V1_1_HEADERS = [
    *V1_HEADERS[:-2],
    "next_changeover_due",
    "days_until_changeover",
    "changeover_priority",
    "next_booking_check_in",
    "next_booking_check_out",
    "next_booking_reference",
    "changeover_window",
    "days_until_next_arrival",
    "pat_testing_status",
    *V1_HEADERS[-2:],
]
# Kept as a compatibility alias for the deployed v1.0 service tests/imports.
HEADERS = V1_HEADERS
ALLOWED_PROPERTY_STATUSES = {"Occupied", "Vacant", "Awaiting Changeover"}
SCHEMA_VERSION = "1.0"
SCHEMA_V1_1 = "1.1"
DATE_FIELDS = {
    "current_check_in",
    "current_check_out",
    "last_check_out",
    "last_changeover",
    "next_changeover_due",
    "next_booking_check_in",
    "next_booking_check_out",
}
INTEGER_FIELDS = {
    "days_to_checkout",
    "days_since_checkout",
    "days_until_changeover",
    "changeover_window",
    "days_until_next_arrival",
}
DATE_FORMATS = ("%d/%m/%Y", "%d-%b-%y", "%Y-%m-%d")
TIMESTAMP_FORMATS = (
    "%d/%m/%Y %H:%M:%S",
    "%d-%b-%y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
)
TIMESTAMP_OFFSET_FORMATS = ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z")


class ContractError(ValueError):
    """The published workbook does not meet the HLM status contract."""


def _date(value: Any, field: str, row_number: int) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    raise ContractError(f"Invalid {field} date at row {row_number}")


def _integer(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _timestamp(value: Any, field: str, row_number: int) -> str:
    text = str(value).strip()
    parsed: datetime | None = None
    for timestamp_format in TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(text, timestamp_format).replace(
                tzinfo=ZoneInfo("Europe/London")
            )
            break
        except ValueError:
            continue
    if parsed is None:
        for timestamp_format in TIMESTAMP_OFFSET_FORMATS:
            try:
                parsed = datetime.strptime(text, timestamp_format)
                break
            except ValueError:
                continue
    if parsed is None:
        raise ContractError(f"Invalid {field} timestamp at row {row_number}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_status_payload(
    rows: list[list[Any]],
    *,
    headers: list[str] = V1_HEADERS,
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    """Validate one versioned publication and return its safe JSON projection."""
    if not rows or rows[0] != headers:
        raise ContractError(
            f"Published header does not match schema_version {schema_version}"
        )
    properties: dict[str, dict[str, Any]] = {}
    exported_values: list[str] = []
    for row_number, source_row in enumerate(rows[1:], start=2):
        if not source_row or not any(value not in (None, "") for value in source_row):
            continue
        padded = list(source_row) + [""] * (len(headers) - len(source_row))
        record = dict(zip(headers, padded, strict=True))
        property_id = str(record["property_id"])
        if not property_id or property_id in properties:
            raise ContractError(f"Invalid or duplicate property_id at row {row_number}")
        if record["property_status"] not in ALLOWED_PROPERTY_STATUSES:
            raise ContractError(f"Invalid property_status at row {row_number}")
        if str(record["schema_version"]) != schema_version:
            raise ContractError(f"Invalid schema_version at row {row_number}")
        for field in DATE_FIELDS:
            record[field] = _date(record[field], field, row_number)
        for field in INTEGER_FIELDS:
            record[field] = _integer(record[field])
        record["source_updated_at"] = _timestamp(
            record["source_updated_at"], "source_updated_at", row_number
        )
        record["schema_version"] = str(record["schema_version"])
        exported_values.append(record["source_updated_at"])
        properties[property_id] = record
    if not properties:
        raise ContractError("Published feed contains no property rows")
    return {
        "version": schema_version,
        "exported": max(exported_values),
        "property_count": len(properties),
        "availability": "available",
        "properties": properties,
    }


def build_v1_1_status_payload(rows: list[list[Any]]) -> dict[str, Any]:
    """Build the isolated v1.1 draft payload without changing v1.0 behaviour."""
    return build_status_payload(rows, headers=V1_1_HEADERS, schema_version=SCHEMA_V1_1)
