"""Unit tests for both private HLM publication contracts."""

from __future__ import annotations

import unittest

from hlm_sheets_service.status import (
    SCHEMA_V1_1,
    V1_1_HEADERS,
    build_v1_1_status_payload,
)


class V1_1StatusTest(unittest.TestCase):
    """The v1.1 draft must remain isolated and contract-validated."""

    def test_projects_the_v1_1_contract(self) -> None:
        values = {
            "property_id": "skysail",
            "property_name": "Skysail",
            "property_status": "Vacant",
            "guest_ready_status": "Ready",
            "live_booking": "No",
            "current_check_in": "",
            "current_check_out": "",
            "days_to_checkout": "",
            "booking_reference": "",
            "last_check_out": "17-Aug-26",
            "days_since_checkout": "4",
            "last_changeover": "18/08/2026",
            "booking_company": "",
            "cleaner": "",
            "form_result": "",
            "report_status": "Not Required",
            "next_changeover_due": "28/08/2026",
            "days_until_changeover": "7",
            "changeover_priority": "Scheduled",
            "next_booking_check_in": "29/08/2026",
            "next_booking_check_out": "05/09/2026",
            "next_booking_reference": "example-ref",
            "changeover_window": "1",
            "days_until_next_arrival": "8",
            "pat_testing_status": "OK",
            "source_updated_at": "2026-08-21 10:00:00",
            "schema_version": SCHEMA_V1_1,
        }

        payload = build_v1_1_status_payload(
            [V1_1_HEADERS, [values[header] for header in V1_1_HEADERS]]
        )

        self.assertEqual(payload["version"], SCHEMA_V1_1)
        self.assertEqual(
            payload["properties"]["skysail"]["next_booking_check_in"],
            "2026-08-29",
        )
        self.assertEqual(payload["properties"]["skysail"]["days_until_next_arrival"], 8)


if __name__ == "__main__":
    unittest.main()
