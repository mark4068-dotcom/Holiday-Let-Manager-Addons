"""Validate the calendar producer's own heartbeat, independently of model time."""

from datetime import datetime

HEARTBEAT_RANGE = "03_import_source_health!A1:K2"
MAX_IMPORT_AGE_SECONDS = 5400  # Hourly trigger plus 30 minutes for delay/transport.


def importer_health(rows, now):
    result = {
        "verified": False, "fresh": False, "last_attempt_at": None,
        "last_success_at": None, "source_timestamp": None, "status": "unverified",
        "error": "invalid_importer_heartbeat", "records_imported": None,
        "snapshot_id": None, "attempt_id": None, "source_received_at": None,
        "source_timestamp_kind": None, "source_count": None,
        "success_age_seconds": None, "max_success_age_seconds": MAX_IMPORT_AGE_SECONDS,
        "source_range": HEARTBEAT_RANGE,
    }
    try:
        required = {"last_attempt_at", "last_success_at", "source_timestamp", "status",
                    "error", "records_imported", "snapshot_id", "attempt_id",
                    "source_received_at", "source_timestamp_kind", "source_count"}
        if len(rows) != 2 or len(rows[0]) != len(required) or set(rows[0]) != required:
            return result
        values = dict(zip(rows[0], rows[1]))
        for key in required:
            result[key] = values.get(key) or None
        def utc(value):
            stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("ambiguous timestamp")
            return stamp
        attempt = utc(result["last_attempt_at"])
        success = utc(result["last_success_at"])
        received = utc(result["source_received_at"])
        age = (now - success).total_seconds()
        result["success_age_seconds"] = age
        result["records_imported"] = int(result["records_imported"])
        result["source_count"] = int(result["source_count"])
        if result["records_imported"] < 0 or result["source_count"] != 2:
            raise ValueError("invalid counts")
        if not result["snapshot_id"] or not result["attempt_id"]:
            raise ValueError("missing generation")
        if result["source_timestamp_kind"] == "http_last_modified":
            utc(result["source_timestamp"])
        elif result["source_timestamp_kind"] != "not_provided" or result["source_timestamp"]:
            raise ValueError("invalid upstream timestamp semantics")
        if result["status"] not in {"ok", "running", "error"}:
            raise ValueError("invalid status")
        if received > success or (now - attempt).total_seconds() < -120 or age < -120:
            raise ValueError("inconsistent timestamps")
        if result["status"] == "ok" and (
            success < attempt or received < attempt
            or result["snapshot_id"] != result["attempt_id"] or result["error"]
        ):
            raise ValueError("inconsistent successful generation")
        # Do not expose arbitrary upstream error text, which could contain URLs.
        result["error"] = "import_failed" if result["status"] == "error" else None
        result["verified"] = True
        result["fresh"] = result["status"] == "ok" and age <= MAX_IMPORT_AGE_SECONDS
        if result["status"] == "ok" and not result["fresh"]:
            result["error"] = "import_success_stale"
    except (ValueError, TypeError, IndexError, KeyError):
        result["verified"] = result["fresh"] = False
        result["error"] = "invalid_importer_heartbeat"
    return result
