#!/usr/bin/env python3
"""VIOW event scraper proof of concept.

This is intentionally isolated from the production aggregator. It discovers
Visit Isle of Wight event pages, extracts their factual metadata and emits JSON.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

BASE_URL = "https://www.visitisleofwight.co.uk"
SEARCH_URL = f"{BASE_URL}/whats-on/searchresults?sr=1&rd=on&anydate=yes"
USER_AGENT = "HLM-VIOW-POC/0.1 (+private calendar evaluation)"
EVENT_LINK = re.compile(r'href=["\'](?P<path>/whats-on/[^"\']+-p(?P<id>\d+))["\']')
PAGE_LINK = re.compile(r'href=["\'](?P<url>\?[^"\']*\bp=(?P<page>\d+)[^"\']*)["\']')


@dataclass(frozen=True)
class ViowEvent:
    source_id: str
    title: str
    category: str
    start_date: str
    end_date: str
    venue: str
    locality: str
    region: str
    postcode: str
    latitude: float | None
    longitude: float | None
    event_website: str
    source_url: str


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


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
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(BASE_URL, href))
    redirected = urllib.parse.parse_qs(parsed.query).get("web", [""])[0]
    website = urllib.parse.unquote(redirected) if redirected else href
    absolute = urllib.parse.urljoin(BASE_URL, website)
    return absolute if urllib.parse.urlsplit(absolute).scheme in {"http", "https"} else ""


def discover_events(document: str) -> dict[str, str]:
    """Return unique VIOW product IDs and absolute detail URLs."""
    return {
        f"VIOW-{match.group('id')}": urllib.parse.urljoin(
            BASE_URL, html.unescape(match.group("path"))
        )
        for match in EVENT_LINK.finditer(document)
    }


def discover_page_count(document: str) -> int:
    pages = [1, *(int(match.group("page")) for match in PAGE_LINK.finditer(document))]
    return max(pages)


def parse_event(document: str, source_url: str) -> ViowEvent:
    product = re.search(r"-p(?P<id>\d+)(?:[/?#]|$)", source_url)
    if not product:
        raise ValueError("event URL has no VIOW product ID")

    title_match = re.search(
        r'<h1[^>]*itemprop=["\']name["\'][^>]*>(.*?)</h1>', document, re.I | re.S
    )
    category_match = re.search(
        r'<div[^>]*class=["\'][^"\']*\bcategory\b[^"\']*["\'][^>]*>.*?'
        r'<span[^>]*class=["\']category["\'][^>]*>(.*?)</span>',
        document,
        re.I | re.S,
    )
    if not title_match:
        raise ValueError("event title selector was not found")

    start_date = _meta(document, "startDate")
    end_date = _meta(document, "endDate") or start_date
    if not start_date:
        raise ValueError("event startDate selector was not found")

    latitude = _meta(document, "latitude")
    longitude = _meta(document, "longitude")
    return ViowEvent(
        source_id=f"VIOW-{product.group('id')}",
        title=_clean(title_match.group(1)),
        category=_clean(category_match.group(1)) if category_match else "",
        start_date=start_date,
        end_date=end_date,
        venue=_meta(document, "name"),
        locality=_meta(document, "addressLocality"),
        region=_meta(document, "addressRegion"),
        postcode=_meta(document, "postalCode"),
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        event_website=_event_website(document),
        source_url=source_url,
    )


def fetch(url: str, timeout: float = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        return response.read(5_000_001).decode(response.headers.get_content_charset() or "utf-8")


def run(limit: int, delay: float) -> dict:
    first_page = fetch(SEARCH_URL)
    page_count = discover_page_count(first_page)
    discovered = discover_events(first_page)
    for page in range(2, page_count + 1):
        time.sleep(delay)
        page_url = f"{SEARCH_URL}&p={page}"
        discovered.update(discover_events(fetch(page_url)))

    events, errors = [], []
    for source_id, url in list(discovered.items())[:limit or None]:
        try:
            time.sleep(delay)
            events.append(asdict(parse_event(fetch(url), url)))
        except Exception as error:  # keep the POC report useful when one page is malformed
            errors.append({"source_id": source_id, "url": url, "error": str(error)})
    return {
        "prefix": "VIOW",
        "listing_pages": page_count,
        "discovered_events": len(discovered),
        "parsed_events": len(events),
        "errors": errors,
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5, help="detail pages to parse; 0 means all")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    parser.add_argument("--output", help="write JSON to this path instead of stdout")
    args = parser.parse_args()
    report = json.dumps(run(args.limit, args.delay), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
