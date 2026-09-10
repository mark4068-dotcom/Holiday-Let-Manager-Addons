from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "poc"))

from viow_scraper import discover_events, discover_page_count, parse_event  # noqa: E402


LISTING = """
<a href="/whats-on/test-event-p123451">Test</a>
<a href="/whats-on/test-event-p123451">Duplicate</a>
<ul class="paging"><li><a href="?rd=on&amp;sr=1&amp;anydate=yes&amp;p=4">4</a></li></ul>
"""

DETAIL = """
<h1 itemprop="name">Test &amp; Festival</h1>
<div class="node category"><h2><span class="category">Festival</span></h2></div>
<meta itemprop="name" content="Western Gardens">
<meta itemprop="latitude" content="50.73317">
<meta itemprop="longitude" content="-1.16095">
<meta itemprop="addressLocality" content="Ryde">
<meta itemprop="addressRegion" content="Isle of Wight">
<meta itemprop="postalCode" content="PO33 2HE">
<meta itemprop="startDate" content="2026-09-18">
<meta itemprop="endDate" content="2026-09-20">
<div class="node website"><a
 href="/engine/referrer.asp?web=https%3A%2F%2Fexample.org%2Fevent&amp;src=x">Visit website</a></div>
<div class="node telephone"><span itemprop="telephone">01983 123456</span></div>
<div class="node ticketInfo"><p>Adults £10</p></div>
<div class="node description"><p>A lovely event.</p></div>
"""


class ViowScraperTests(unittest.TestCase):
    def test_discovers_unique_namespaced_events_and_pages(self) -> None:
        self.assertEqual(
            discover_events(LISTING),
            {"VIOW-123451": "https://www.visitisleofwight.co.uk/whats-on/test-event-p123451"},
        )
        self.assertEqual(discover_page_count(LISTING), 4)

    def test_parses_machine_readable_event_fields(self) -> None:
        event = parse_event(
            DETAIL,
            "https://www.visitisleofwight.co.uk/whats-on/test-event-p123451",
        )
        self.assertEqual(event.source_id, "VIOW-123451")
        self.assertEqual(event.title, "Test & Festival")
        self.assertEqual(event.start_date, "2026-09-18")
        self.assertEqual(event.end_date, "2026-09-20")
        self.assertEqual(event.venue, "Western Gardens")
        self.assertEqual(event.locality, "Ryde")
        self.assertEqual(event.latitude, 50.73317)
        self.assertEqual(event.event_website, "https://example.org/event")
        self.assertEqual(event.guide_price, "Adults £10")
        self.assertEqual(event.about, "A lovely event.")
        self.assertEqual(event.telephone, "01983 123456")

    def test_rejects_detail_without_a_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "startDate"):
            parse_event(
                '<h1 itemprop="name">Undated</h1>',
                "https://www.visitisleofwight.co.uk/whats-on/undated-p9",
            )


if __name__ == "__main__":
    unittest.main()
