from __future__ import annotations

import unittest
from datetime import date

from icalendar import Calendar, Event
from publisher import (
    FINGERPRINT_KEY,
    MANAGED_KEY,
    SYNC_KEY,
    GoogleCalendarClient,
    GoogleCalendarPublisher,
    PublicationConfig,
    build_event_resources,
)


def combined_calendar(*events: dict) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Test//EN")
    calendar.add("version", "2.0")
    for values in events:
        event = Event()
        for key, value in values.items():
            event.add(key, value)
        calendar.add_component(event)
    return calendar.to_ical()


class ResourceTests(unittest.TestCase):
    def test_builds_stable_all_day_resource_with_private_markers(self) -> None:
        data = combined_calendar(
            {
                "uid": "stable@hlm.local",
                "summary": "Crossjack — Smith",
                "description": "Guesty detail",
                "dtstart": date(2026, 9, 4),
                "dtend": date(2026, 9, 7),
                "x-hlm-source-id": "crossjack",
                "x-hlm-source-name": "Crossjack Guesty bookings",
            }
        )
        first = next(iter(build_event_resources(data).values()))
        second = next(iter(build_event_resources(data).values()))

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["start"], {"date": "2026-09-04"})
        self.assertEqual(first["end"], {"date": "2026-09-07"})
        self.assertEqual(first["description"], "Guesty detail")
        private = first["extendedProperties"]["private"]
        self.assertEqual(private[MANAGED_KEY], "true")
        self.assertIn(SYNC_KEY, private)
        self.assertNotIn("\0", private[SYNC_KEY])
        self.assertIn(FINGERPRINT_KEY, private)

    def test_privacy_safe_mode_hides_booking_detail(self) -> None:
        data = combined_calendar(
            {
                "uid": "stable@hlm.local",
                "summary": "Crossjack — Smith",
                "description": "Private notes",
                "location": "Cottage",
                "dtstart": date(2026, 9, 4),
                "x-hlm-source-id": "crossjack",
                "x-hlm-source-name": "Crossjack",
            }
        )
        resource = next(iter(build_event_resources(data, title_mode="privacy_safe").values()))

        self.assertEqual(resource["summary"], "Crossjack — Booked")
        self.assertNotIn("description", resource)
        self.assertNotIn("location", resource)

    def test_recurrence_override_excludes_original_master_occurrence(self) -> None:
        data = combined_calendar(
            {
                "uid": "recurring@hlm.local",
                "summary": "Weekly event",
                "dtstart": date(2026, 9, 4),
                "rrule": {"freq": "weekly", "count": 3},
            },
            {
                "uid": "recurring@hlm.local",
                "recurrence-id": date(2026, 9, 11),
                "summary": "Moved weekly event",
                "dtstart": date(2026, 9, 12),
            },
        )

        resources = build_event_resources(data)
        master = next(item for item in resources.values() if "recurrence" in item)

        self.assertEqual(len(resources), 2)
        self.assertIn("RRULE:FREQ=WEEKLY;COUNT=3", master["recurrence"])
        self.assertIn("EXDATE;VALUE=DATE:20260911", master["recurrence"])


class FakeClient:
    existing: list[dict] = []
    instances: list[FakeClient] = []

    def __init__(self, _config) -> None:
        self.inserted: list[dict] = []
        self.patched: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self.instances.append(self)

    def list_managed(self) -> list[dict]:
        return self.existing

    def insert(self, body: dict) -> None:
        self.inserted.append(body)

    def patch(self, event_id: str, body: dict) -> None:
        self.patched.append((event_id, body))

    def delete(self, event_id: str) -> None:
        self.deleted.append(event_id)


class ReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeClient.existing = []
        FakeClient.instances = []
        self.data = combined_calendar(
            {
                "uid": "wanted@hlm.local",
                "summary": "Wanted",
                "dtstart": date(2026, 9, 4),
                "x-hlm-source-id": "guest-guide",
            }
        )

    def test_dry_run_reports_changes_without_writes(self) -> None:
        FakeClient.existing = [
            {
                "id": "obsolete",
                "extendedProperties": {"private": {MANAGED_KEY: "true", SYNC_KEY: "gone\0"}},
            },
            {"id": "unmanaged", "summary": "Do not touch"},
        ]
        config = PublicationConfig(enabled=True, calendar_id="calendar", dry_run=True)
        publisher = GoogleCalendarPublisher(config, client_factory=FakeClient)

        status = publisher.publish(self.data)

        self.assertEqual(status["state"], "dry_run")
        self.assertEqual(status["created_events"], 1)
        self.assertEqual(status["deleted_events"], 1)
        client = FakeClient.instances[-1]
        self.assertEqual(client.inserted, [])
        self.assertEqual(client.deleted, [])

    def test_live_sync_updates_and_deletes_only_marked_events(self) -> None:
        desired = next(iter(build_event_resources(self.data).values()))
        key = desired["extendedProperties"]["private"][SYNC_KEY]
        FakeClient.existing = [
            {
                "id": "update-me",
                "extendedProperties": {
                    "private": {
                        MANAGED_KEY: "true",
                        SYNC_KEY: key,
                        FINGERPRINT_KEY: "old",
                    }
                },
            },
            {
                "id": "delete-me",
                "extendedProperties": {"private": {MANAGED_KEY: "true", SYNC_KEY: "gone\0"}},
            },
            {"id": "unmanaged", "summary": "Do not touch"},
        ]
        config = PublicationConfig(enabled=True, calendar_id="calendar", dry_run=False)
        publisher = GoogleCalendarPublisher(config, client_factory=FakeClient)

        status = publisher.publish(self.data)

        self.assertEqual(status["state"], "healthy")
        client = FakeClient.instances[-1]
        self.assertEqual([item[0] for item in client.patched], ["update-me"])
        self.assertEqual(client.deleted, ["delete-me"])
        self.assertNotIn("unmanaged", client.deleted)

    def test_empty_feed_cannot_clear_managed_events_by_default(self) -> None:
        FakeClient.existing = [
            {
                "id": "keep-me",
                "extendedProperties": {"private": {MANAGED_KEY: "true", SYNC_KEY: "existing"}},
            }
        ]
        empty = combined_calendar()
        config = PublicationConfig(enabled=True, calendar_id="calendar", dry_run=False)
        publisher = GoogleCalendarPublisher(config, client_factory=FakeClient)

        status = publisher.publish(empty)

        self.assertEqual(status["state"], "error")
        self.assertIn("refusing to remove every managed", status["error"])
        self.assertEqual(FakeClient.instances[-1].deleted, [])


class ConfigurationTests(unittest.TestCase):
    def test_enabled_publication_requires_calendar(self) -> None:
        with self.assertRaisesRegex(ValueError, "google_calendar_id"):
            PublicationConfig.from_options({"google_publish_enabled": True})


class RetryTests(unittest.TestCase):
    def test_transient_rate_limit_uses_bounded_retry(self) -> None:
        class Response:
            def __init__(self, status: int) -> None:
                self.status_code = status
                self.ok = status == 200
                self.text = "rateLimitExceeded"
                self.content = b"{}"

            def json(self) -> dict:
                return {"ok": True}

        class Session:
            def __init__(self) -> None:
                self.responses = [Response(429), Response(200)]

            def request(self, *_args, **_kwargs):
                return self.responses.pop(0)

        waits: list[float] = []
        client = GoogleCalendarClient.__new__(GoogleCalendarClient)
        client.session = Session()
        client.retry_count = 2
        client.sleeper = waits.append
        client.random_value = lambda: 0.25

        result = client._request("GET", "https://example.test")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(waits, [1.25])


if __name__ == "__main__":
    unittest.main()
