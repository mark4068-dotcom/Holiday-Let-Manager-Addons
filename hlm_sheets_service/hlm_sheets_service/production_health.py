"""Validate the production evaluation clock without claiming upstream freshness."""

from datetime import datetime, timezone

from .status import ContractError, build_v1_1_status_payload


def validate_evaluation_age(payload, now=None, max_age=900):
    now = now or datetime.now(timezone.utc)
    if set(payload["properties"]) != {"skysail", "crossjack"}:
        raise ContractError("Unexpected production property set")
    ages = {}
    for prop, values in payload["properties"].items():
        stamp = datetime.fromisoformat(
            values["source_updated_at"].replace("Z", "+00:00")
        )
        age = (now - stamp).total_seconds()
        if age < -120 or age > max_age:
            raise ContractError("Production evaluation clock is stale or in the future")
        ages[prop] = age
    return ages


def production_record(ranges, now):
    # Imported lazily to avoid a cycle with the durable audit implementation.
    from .parallel_audit import CHECKS

    record = {
        "audit_version": 2,
        "audit_mode": "production_health",
        "checked_at": now.isoformat(),
        "status": "healthy",
        "errors": {},
        "differences": [],
        "compared_fields": 0,
        "source_checks": {},
        "snapshots": {},
        "evaluation_timestamps": {},
        "raw_rows": dict(zip(("production", "checks"), ranges)),
    }
    try:
        payload = build_v1_1_status_payload(ranges[0])
        record["snapshots"]["production"] = payload["properties"]
        record["evaluation_timestamps"]["production"] = {
            prop: row["source_updated_at"]
            for prop, row in payload["properties"].items()
        }
        record["evaluation_age_seconds"] = validate_evaluation_age(payload, now)
    except (ContractError, ValueError, IndexError, KeyError, TypeError):
        record["errors"]["production"] = "invalid_or_stale_contract"
    checks = (
        {row[0]: row[1] for row in ranges[1] if len(row) >= 2 and row[0] in CHECKS}
        if len(ranges) == 2
        else {}
    )
    record["source_checks"] = {
        name: value
        if value in {"PASS", "FAIL", "WARN", "INFO", "PRODUCTION"}
        else "ERROR"
        for name, value in checks.items()
    }
    if set(checks) != CHECKS:
        record["errors"]["checks"] = "missing_checks"
    elif any(value in {"FAIL", "ERROR"} for value in record["source_checks"].values()):
        record["errors"]["checks"] = "failed_checks"
    if record["errors"]:
        record["status"] = "error"
    return record
