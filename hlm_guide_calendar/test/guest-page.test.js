import test from "node:test";
import assert from "node:assert/strict";
import { guestPage } from "../src/guest-page.js";

test("renders events and favourite places as a carousel", () => {
  const html = guestPage({
    updatedAt: "2026-08-25T13:30:12Z",
    events: [{
      summary: "Powerboat Festival",
      start: "2026-08-28",
      end: "2026-08-31",
      location: "Cowes, UK",
      description: "A local event",
      url: "https://example.test/event",
    }],
    favourites: [{
      name: "Braai IOW",
      address: "Brading, Isle of Wight",
      description: "Farm to fork restaurant",
      maps_url: "https://maps.google.com/example",
      source_url: "https://example.test/place",
    }],
  });
  assert.match(html, /Powerboat Festival/);
  assert.match(html, /Braai IOW/);
  assert.match(html, /id="places-carousel"/);
  assert.match(html, /data-direction="1"/);
  assert.match(html, /scroll-snap-type:x mandatory/);
});

test("escapes guide text and rejects non-http links", () => {
  const html = guestPage({
    events: [{ summary: "<script>alert(1)</script>", start: "2026-09-05", end: "2026-09-06", url: "javascript:alert(1)" }],
  });
  assert.doesNotMatch(html, /<script>alert\(1\)<\/script>/);
  assert.doesNotMatch(html, /javascript:/);
  assert.match(html, /&lt;script&gt;/);
});
