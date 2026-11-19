"""Booking publication must not change local feeds or the events destination."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import server
from aggregator import Aggregator, SourceConfig
from icalendar import Calendar
from publisher import PublicationConfig
from test_aggregator import calendar_bytes


class BookingConfigTests(unittest.TestCase):
    def test_disabled_by_default_and_reuses_only_shared_writer_settings(self):
        options = {
            "google_publish_enabled": True,
            "google_calendar_id": "events@test",
            "google_credentials_path": "/config/approved.json",
            "google_dry_run": False,
            "google_allow_empty_publish": True,
        }
        self.assertFalse(PublicationConfig.for_bookings(options).enabled)
        options.update(
            google_bookings_publish_enabled=True,
            google_bookings_calendar_id="bookings@test",
        )
        result = PublicationConfig.for_bookings(options)
        self.assertTrue(result.enabled)
        self.assertTrue(result.dry_run)
        self.assertFalse(result.allow_empty)
        self.assertEqual(result.credentials_path, "/config/approved.json")
        self.assertEqual(result.calendar_id, "bookings@test")
        options["google_bookings_calendar_id"] = "events@test"
        with self.assertRaisesRegex(ValueError, "must be different"):
            PublicationConfig.for_bookings(options)


class BookingScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        sources = [
            SourceConfig(key, key, "https://test.invalid/" + key)
            for key in ("crossjack", "skysail", "guest-guide", "viow")
        ]
        self.aggregator = Aggregator(
            Path(self.tmp.name),
            sources,
            fetcher=lambda url: calendar_bytes(
                {
                    "uid": url,
                    "summary": url,
                    "dtstart": date(2026, 11, 19),
                    "dtend": date(2026, 11, 23),
                }
            ),
        )
        self.aggregator.refresh()
        self.bookings = Mock()
        self.bookings.config.enabled = True
        self.events = Mock()
        self.patcher = patch.multiple(
            server,
            AGGREGATOR=self.aggregator,
            BOOKING_PUBLISHER=self.bookings,
            PUBLISHER=self.events,
            OPTIONS={"viow_enabled": True},
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_destinations_are_disjoint_and_local_files_unchanged(self):
        before = {p: p.read_bytes() for p in Path(self.tmp.name).rglob("*.ics")}
        server.publish_visit_iow()
        server.publish_bookings()
        data = self.bookings.publish.call_args.args[0]
        events = Calendar.from_ical(data).walk("VEVENT")
        self.assertEqual(
            {str(e["X-HLM-SOURCE-ID"]) for e in events}, {"crossjack", "skysail"}
        )
        self.assertEqual(len(events), 2)
        self.assertEqual({str(e["DTEND"].dt) for e in events}, {"2026-11-23"})
        self.events.publish.assert_called_once_with(
            self.aggregator.source_path("viow").read_bytes()
        )
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_missing_disabled_or_failed_source_never_clears_destination(self):
        for case in ("missing", "disabled", "failed"):
            with self.subTest(case=case):
                self.bookings.reset_mock()
                source = self.aggregator.statuses["skysail"]
                path = self.aggregator.source_path("skysail")
                saved = path.read_bytes()
                if case == "missing":
                    path.unlink()
                if case == "disabled":
                    source.enabled = False
                if case == "failed":
                    source.error = "Upstream unavailable"
                server.publish_bookings()
                self.bookings.publish.assert_not_called()
                self.bookings.unavailable.assert_called_once()
                path.write_bytes(saved)
                source.enabled = True
                source.error = None
        self.bookings.reset_mock()
        server.publish_bookings()
        self.bookings.publish.assert_called_once()

    def test_disabled_booking_writer_does_not_reconcile(self):
        self.bookings.config.enabled = False
        server.publish_bookings()
        self.bookings.publish.assert_not_called()

    def test_booking_error_is_visible_without_losing_local_feed(self):
        self.events.snapshot.return_value = {"enabled": True, "state": "healthy"}
        self.bookings.snapshot.return_value = {"enabled": True, "state": "error"}
        result = server.service_snapshot()
        self.assertEqual(result["state"], "degraded")
        self.assertTrue(result["combined_available"])
        self.assertEqual(result["publication"]["state"], "healthy")
        self.assertEqual(result["booking_publication"]["state"], "error")
