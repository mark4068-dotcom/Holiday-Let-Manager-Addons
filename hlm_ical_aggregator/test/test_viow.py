from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from icalendar import Calendar  # noqa: E402
from viow import (  # noqa: E402
    ViowSource,
    calendar_for,
    discover,
    duration_days,
    page_count,
    parse_detail,
)


LISTING = """
<a href="/whats-on/test-event-p123451">Test</a>
<a href="/whats-on/test-event-p123451">Duplicate</a>
<a href="?rd=on&amp;sr=1&amp;anydate=yes&amp;p=4">4</a>
"""

DETAIL = """
<h1 itemprop="name">Test &amp; Festival</h1>
<span class="category">Festival</span>
<meta itemprop="name" content="Western Gardens">
<meta itemprop="addressLocality" content="Ryde">
<meta itemprop="addressRegion" content="Isle of Wight">
<meta itemprop="postalCode" content="PO33 2HE">
<meta itemprop="startDate" content="2026-09-18">
<meta itemprop="endDate" content="2026-09-20">
<div class="node-Ad website contact"><p><a
 href="/engine/referrer.asp?web=https%3A%2F%2Fexample.org%2Fevent&amp;src=x">Visit website</a></p></div>
<div class="node telephone"><span itemprop="telephone">01983 123456</span></div>
<div class="node ticketInfo"><h2>Guide Prices</h2><p>Adults £10</p></div>
<div class="node description" itemprop="description"><h2>About</h2><p>A lovely event.</p></div>
"""


class ViowParserTests(unittest.TestCase):
    def test_discovers_unique_products_and_pagination(self) -> None:
        self.assertEqual(
            discover(LISTING),
            {
                "123451": (
                    "https://www.visitisleofwight.co.uk/whats-on/test-event-p123451"
                )
            },
        )
        self.assertEqual(page_count(LISTING), 4)

    def test_builds_tagged_all_day_calendar_event(self) -> None:
        item = parse_detail(
            DETAIL,
            "https://www.visitisleofwight.co.uk/whats-on/test-event-p123451",
        )
        parsed = Calendar.from_ical(calendar_for([item]))
        event = parsed.walk("VEVENT")[0]
        self.assertEqual(str(event["UID"]), "VIOW-123451@hlm.local")
        self.assertEqual(str(event["SUMMARY"]), "Test & Festival")
        self.assertEqual(event.decoded("DTSTART"), date(2026, 9, 18))
        self.assertEqual(event.decoded("DTEND"), date(2026, 9, 21))
        self.assertEqual(str(event["X-HLM-PROVIDER"]), "VisitIOW")
        self.assertEqual(
            str(event["X-HLM-EVENT-WEBSITE"]), "https://example.org/event"
        )
        self.assertIn("Event website: https://example.org/event", str(event["DESCRIPTION"]))
        self.assertIn("About: A lovely event.", str(event["DESCRIPTION"]))
        self.assertIn("Guide price: Adults £10", str(event["DESCRIPTION"]))
        self.assertIn("Telephone: 01983 123456", str(event["DESCRIPTION"]))

    def test_fresh_cache_avoids_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary) / "raw.ics"
            cache.write_bytes(b"cached")
            source = ViowSource(cache)
            self.assertEqual(source("ignored"), b"cached")
            self.assertTrue(source.status["using_cache"])

    def test_event_duration_is_inclusive(self) -> None:
        event = {"start": date(2026, 1, 1), "end": date(2026, 1, 31)}
        self.assertEqual(duration_days(event), 31)

        event["end"] = date(2026, 2, 1)
        self.assertEqual(duration_days(event), 32)


if __name__ == "__main__":
    unittest.main()
