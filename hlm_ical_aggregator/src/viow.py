"""Visit Isle of Wight HTML event source for the calendar aggregator."""

from __future__ import annotations

import html
import os
import re
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from icalendar import Calendar, Event

BASE_URL = "https://www.visitisleofwight.co.uk"
SEARCH_URL = f"{BASE_URL}/whats-on/searchresults?sr=1&rd=on&anydate=yes"
USER_AGENT = "HLM-iCalendar-Aggregator/VIOW (+private calendar service)"
EVENT_LINK = re.compile(r'href=["\'](?P<path>/whats-on/[^"\']+-p(?P<id>\d+))["\']')
PAGE_LINK = re.compile(r'href=["\']\?[^"\']*\bp=(?P<page>\d+)[^"\']*["\']')


def _clean(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _meta(document: str, itemprop: str) -> str:
    match = re.search(
        rf'<meta\s+itemprop=["\']{re.escape(itemprop)}["\']\s+content=["\']([^"\']*)',
        document,
        re.IGNORECASE,
    )
    return html.unescape(match.group(1)).strip() if match else ""


def _event_website(document: str) -> str:
    match = re.search(
        r'<div[^>]*class=["\'][^"\']*\bwebsite\b[^"\']*["\'][^>]*>.*?'
        r'<a[^>]*href=["\']([^"\']+)["\']',
        document,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    href = html.unescape(match.group(1))
    parsed = urlsplit(urljoin(BASE_URL, href))
    redirected = parse_qs(parsed.query).get("web", [""])[0]
    website = unquote(redirected) if redirected else href
    absolute = urljoin(BASE_URL, website)
    return absolute if urlsplit(absolute).scheme in {"http", "https"} else ""


def discover(document: str) -> dict[str, str]:
    return {
        match.group("id"): urljoin(BASE_URL, html.unescape(match.group("path")))
        for match in EVENT_LINK.finditer(document)
    }


def page_count(document: str) -> int:
    return max([1, *(int(match.group("page")) for match in PAGE_LINK.finditer(document))])


def parse_detail(document: str, source_url: str) -> dict[str, object]:
    product = re.search(r"-p(?P<id>\d+)(?:[/?#]|$)", source_url)
    title = re.search(
        r'<h1[^>]*itemprop=["\']name["\'][^>]*>(.*?)</h1>', document, re.I | re.S
    )
    category = re.search(
        r'<span[^>]*class=["\']category["\'][^>]*>(.*?)</span>',
        document,
        re.I | re.S,
    )
    start = _meta(document, "startDate")
    end = _meta(document, "endDate") or start
    if not product or not title or not start:
        raise ValueError("required product ID, title or start date is missing")
    return {
        "id": product.group("id"),
        "title": _clean(title.group(1)),
        "category": _clean(category.group(1)) if category else "",
        "start": date.fromisoformat(start),
        "end": date.fromisoformat(end),
        "venue": _meta(document, "name"),
        "locality": _meta(document, "addressLocality"),
        "region": _meta(document, "addressRegion"),
        "postcode": _meta(document, "postalCode"),
        "event_website": _event_website(document),
        "source_url": source_url,
    }


def calendar_for(events: list[dict[str, object]]) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//Holiday Let Manager//VIOW source 0.1//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "Visit Isle of Wight events")
    for item in events:
        event = Event()
        event.add("uid", f"VIOW-{item['id']}@hlm.local")
        event.add("summary", str(item["title"]))
        event.add("dtstart", item["start"])
        event.add("dtend", item["end"] + timedelta(days=1))
        location = ", ".join(
            str(item[key])
            for key in ("venue", "locality", "region", "postcode")
            if item[key]
        )
        if location:
            event.add("location", location)
        description = f"Category: {item['category']}"
        if item["event_website"]:
            description += f"\nEvent website: {item['event_website']}"
            event.add("x-hlm-event-website", str(item["event_website"]))
        description += f"\nSource: {item['source_url']}"
        event.add("description", description)
        event.add("url", str(item["source_url"]))
        event.add("x-hlm-provider", "VisitIOW")
        calendar.add_component(event)
    return calendar.to_ical()


class ViowSource:
    """Callable source with a persistent nightly raw-ICS cache."""

    def __init__(
        self, cache_path: Path, refresh_hours: int = 24, delay_seconds: float = 0.25
    ):
        self.cache_path = cache_path
        self.refresh_seconds = refresh_hours * 3600
        self.delay_seconds = delay_seconds
        self.status = {
            "using_cache": False,
            "discovered_events": 0,
            "parsed_events": 0,
            "parse_errors": 0,
        }

    def __call__(self, _url: str) -> bytes:
        cache_is_fresh = (
            self.cache_path.exists()
            and time.time() - self.cache_path.stat().st_mtime < self.refresh_seconds
        )
        if cache_is_fresh:
            self.status["using_cache"] = True
            return self.cache_path.read_bytes()
        self.status["using_cache"] = False
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        def get(url: str) -> str:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.text

        first = get(SEARCH_URL)
        urls = discover(first)
        for page in range(2, page_count(first) + 1):
            time.sleep(self.delay_seconds)
            urls.update(discover(get(f"{SEARCH_URL}&p={page}")))
        events, errors = [], []
        for product_id, url in urls.items():
            try:
                time.sleep(self.delay_seconds)
                events.append(parse_detail(get(url), url))
            except Exception as error:
                errors.append(f"VIOW-{product_id}: {error}")
        if not urls or len(events) / len(urls) < 0.95:
            raise RuntimeError(
                f"VIOW quality gate failed: parsed {len(events)}/{len(urls)}; "
                + "; ".join(errors[:5])
            )
        self.status.update(
            discovered_events=len(urls),
            parsed_events=len(events),
            parse_errors=len(errors),
        )
        output = calendar_for(events)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.cache_path.parent, prefix=".viow."
        )
        try:
            with os.fdopen(descriptor, "wb") as temporary:
                temporary.write(output)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, self.cache_path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
        return output
