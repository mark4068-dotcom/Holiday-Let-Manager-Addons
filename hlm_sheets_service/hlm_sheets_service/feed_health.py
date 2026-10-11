"""Authenticated feed diagnostics; evaluation and importer freshness are distinct."""

from datetime import datetime, timezone
from threading import Lock

from .production_health import production_record
from .status import ContractError, build_v1_1_status_payload

SERVICE_VERSION = "0.4.0"


class FeedHealth:
    def __init__(self, source):
        self.source = source
        self.lock = Lock()
        self.last_success_at = None

    def read(self, now=None):
        with self.lock:
            return self._read(now or datetime.now(timezone.utc))

    def _read(self, now):
        result = {
            "service_version": SERVICE_VERSION,
            "checked_at": now.isoformat(),
            "evaluation_timestamp": None,
            "evaluation_age_seconds": None,
            "evaluation_fresh": False,
            "freshness_verified": False,
            "source_range": self.source.sheet_range,
            "property_count": 0,
            "expected_property_count": 2,
            "expected_properties_present": False,
            "source_checks_ok": False,
            "last_success_at": self.last_success_at,
            "last_attempt_at": now.isoformat(),
            "error": None,
            "max_evaluation_age_seconds": 900,
            "max_future_skew_seconds": 120,
            "upstream_import": {
                "verified": False,
                "last_attempt_at": None,
                "last_success_at": None,
                "source_timestamp": None,
                "status": "unverified",
                "error": "authoritative_importer_heartbeat_not_connected",
                "records_imported": None,
                "snapshot_id": None,
            },
        }
        try:
            ranges = self.source.read_ranges(
                [self.source.sheet_range, "02_import_property_status!A6:B24"]
            )
            payload = build_v1_1_status_payload(ranges[0])
            properties = payload["properties"]
            result["property_count"] = len(properties)
            result["expected_properties_present"] = set(properties) == {
                "skysail",
                "crossjack",
            }
            timestamps = [row["source_updated_at"] for row in properties.values()]
            ages = [
                (
                    now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                ).total_seconds()
                for stamp in timestamps
            ]
            # The oldest property determines the age; a future timestamp on
            # either property is also rejected, even if the other is current.
            result["evaluation_timestamp"] = min(timestamps)
            result["evaluation_age_seconds"] = max(ages)
            result["evaluation_fresh"] = all(-120 <= age <= 900 for age in ages)
            record = production_record(ranges, now)
            result["source_checks_ok"] = "checks" not in record["errors"]
            if record["errors"]:
                result["error"] = record["errors"]
            else:
                self.last_success_at = now.isoformat()
                result["last_success_at"] = self.last_success_at
        except (ContractError, ValueError, IndexError, KeyError, TypeError):
            result["error"] = "invalid_contract"
        except Exception as error:  # noqa: BLE001 - diagnostics must report provider failures without leaking messages
            result["error"] = "source_unavailable:" + type(error).__name__
        result["status"] = (
            "error" if result["error"] else "evaluation_fresh_upstream_unverified"
        )
        return result
