from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aggregator import (
    Aggregator,
    SourceConfig,
    combine_calendars,
    filter_calendar,
    parse_sources,
)
from icalendar import Calendar, Event


def calendar_bytes(*events: dict) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Test//EN")
    calendar.add("version", "2.0")
    for values in events:
        event = Event()
        for key, value in values.items():
            event.add(key, value)
        calendar.add_component(event)
    return calendar.to_ical()


def summaries(data: bytes) -> list[str]:
    return [str(event.get("SUMMARY", "")) for event in Calendar.from_ical(data).walk("VEVENT")]


class FilterTests(unittest.TestCase):
    def test_exact_case_insensitive_guesty_blocker_is_removed(self) -> None:
        source = SourceConfig(
            id="crossjack",
            name="Crossjack",
            url="https://example.test/crossjack.ics",
            exclude_regex=r"(?i)^\s*Blocked by Guesty\s*$",
            title_prefix="Crossjack — ",
        )
        result = filter_calendar(
            calendar_bytes(
                {"uid": "blocked", "summary": "BLOCKED BY GUESTY"},
                {"uid": "booking", "summary": "Smith booking"},
                {"uid": "mention", "summary": "Review Blocked by Guesty handling"},
            ),
            source,
        )

        self.assertEqual(result.source_events, 3)
        self.assertEqual(result.accepted_events, 2)
        self.assertEqual(result.excluded_events, 1)
        self.assertEqual(
            summaries(result.calendar),
            ["Crossjack — Smith booking", "Crossjack — Review Blocked by Guesty handling"],
        )

    def test_cancelled_and_non_included_events_are_removed(self) -> None:
        source = SourceConfig(
            id="events",
            name="Events",
            url="https://example.test/events.ics",
            include_regex=r"(?i)ferry|festival",
        )
        result = filter_calendar(
            calendar_bytes(
                {"uid": "one", "summary": "Harbour festival"},
                {"uid": "two", "summary": "Private meeting"},
                {"uid": "three", "summary": "Ferry day", "status": "CANCELLED"},
            ),
            source,
        )

        self.assertEqual(summaries(result.calendar), ["Harbour festival"])
        self.assertEqual(result.excluded_events, 1)
        self.assertEqual(result.cancelled_events, 1)

    def test_namespaces_equal_source_uids_and_keeps_provenance(self) -> None:
        raw = calendar_bytes({"uid": "shared", "summary": "Booking"})
        first = filter_calendar(raw, SourceConfig("one", "One", "https://one.test/a.ics"))
        second = filter_calendar(raw, SourceConfig("two", "Two", "https://two.test/a.ics"))
        first_event = Calendar.from_ical(first.calendar).walk("VEVENT")[0]
        second_event = Calendar.from_ical(second.calendar).walk("VEVENT")[0]

        self.assertNotEqual(str(first_event["UID"]), str(second_event["UID"]))
        self.assertEqual(str(first_event["X-HLM-ORIGINAL-UID"]), "shared")
        self.assertEqual(str(first_event["X-HLM-SOURCE-ID"]), "one")

    def test_invalid_expression_is_rejected(self) -> None:
        source = SourceConfig("bad", "Bad", "https://bad.test/a.ics", exclude_regex="[")
        with self.assertRaisesRegex(ValueError, "invalid regular expression"):
            filter_calendar(calendar_bytes({"uid": "one", "summary": "Booking"}), source)


class CombineTests(unittest.TestCase):
    def test_combines_sources_and_deduplicates_same_namespaced_instance(self) -> None:
        raw = calendar_bytes({"uid": "one", "summary": "Booking"})
        source = SourceConfig("one", "One", "https://one.test/a.ics")
        filtered = filter_calendar(raw, source).calendar
        combined = combine_calendars([filtered, filtered])
        self.assertEqual(summaries(combined), ["Booking"])


class RetentionTests(unittest.TestCase):
    def test_failed_refresh_retains_previous_source_and_combined_feed(self) -> None:
        responses = [calendar_bytes({"uid": "one", "summary": "Booking"})]

        def fetcher(_url: str) -> bytes:
            if responses:
                return responses.pop()
            raise OSError("temporary source failure")

        with tempfile.TemporaryDirectory() as temporary:
            source = SourceConfig("one", "One", "https://one.test/a.ics")
            aggregator = Aggregator(Path(temporary), [source], fetcher=fetcher)
            first = aggregator.refresh()
            expected = aggregator.combined_path.read_bytes()
            second = aggregator.refresh()

            self.assertEqual(first["state"], "healthy")
            self.assertEqual(second["state"], "degraded")
            self.assertTrue(second["sources"][0]["using_cached_output"])
            self.assertEqual(aggregator.combined_path.read_bytes(), expected)

    def test_completed_refresh_reports_not_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = SourceConfig("one", "One", "https://one.test/a.ics")
            aggregator = Aggregator(
                Path(temporary),
                [source],
                fetcher=lambda _url: calendar_bytes({"uid": "one", "summary": "Booking"}),
            )

            self.assertFalse(aggregator.refresh()["running"])


class ConfigurationTests(unittest.TestCase):
    def test_duplicate_source_ids_are_rejected(self) -> None:
        source = {"id": "same", "name": "One", "url": "https://one.test/a.ics"}
        with self.assertRaisesRegex(ValueError, "duplicate source id 'same'"):
            parse_sources([source, {**source, "name": "Two"}])

    def test_invalid_regex_is_rejected_during_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "source 'bad' exclude_regex"):
            parse_sources(
                [
                    {
                        "id": "bad",
                        "name": "Bad",
                        "url": "https://bad.test/a.ics",
                        "exclude_regex": "[",
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()
