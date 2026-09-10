# VIOW scraper proof of concept

This isolated POC tests whether Visit Isle of Wight event listings can be used
as an input to the HLM iCalendar Aggregator. It does not alter or run inside the
production app.

Run a five-event live smoke test:

```sh
python3 poc/viow_scraper.py --limit 5 --output /tmp/viow-poc.json
```

Use `--limit 0` to parse every discovered event. The collector traverses the
server-rendered search pagination, uses the numeric Visit Isle of Wight product
ID as `VIOW-<id>`, and extracts factual machine-readable metadata from each
detail page. It deliberately does not copy descriptions or images.

Success criteria before integration:

- every search-results page is discovered;
- at least 95% of detail pages parse without error;
- IDs and dates remain stable across repeated runs;
- malformed pages are reported without aborting the collection;
- the live run remains polite: one request at a time with a delay.

Phase 1 has now been incorporated into version 0.3.0 of the aggregator with
nightly caching, a parsing quality gate, diagnostics and ICS conversion. It
does not yet perform cross-source duplicate matching. Some repeating listings
only expose their overall advertised date range; this is a specific quality
item to assess during Phase 1.
