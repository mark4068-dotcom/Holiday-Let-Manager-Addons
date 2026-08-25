import test from "node:test";
import assert from "node:assert/strict";
import { eventsToIcs, stableUid } from "../src/calendar.js";
import { parseDisplayedDate } from "../src/dates.js";

test("parses an inclusive multi-day event into an exclusive ICS end", () => {
  assert.deepEqual(parseDisplayedDate("28–30 August 2026"), {
    start: "2026-08-28",
    end: "2026-08-31",
    all_day: true,
  });
});

test("parses a single day event", () => {
  assert.deepEqual(parseDisplayedDate("5 September 2026"), {
    start: "2026-09-05",
    end: "2026-09-06",
    all_day: true,
  });
});

test("parses the live guide's month-first range", () => {
  assert.deepEqual(parseDisplayedDate("Aug 28 - Aug 30, 2026"), {
    start: "2026-08-28",
    end: "2026-08-31",
    all_day: true,
  });
});

test("stable UID ignores case and surrounding whitespace", () => {
  const first = stableUid({ summary: "Jazz Weekend", start: "2026-09-16", location: "Newport" });
  const second = stableUid({ summary: " jazz weekend ", start: "2026-09-16", location: "NEWPORT" });
  assert.equal(first, second);
});

test("generates a valid all-day VEVENT", () => {
  const ics = eventsToIcs([{
    summary: "The Ultimate Powerboat Festival",
    start: "2026-08-28",
    end: "2026-08-31",
    location: "Cowes, UK",
    description: "Marine and power festival",
    url: "https://example.test/event",
  }], new Date("2026-08-25T12:00:00Z"));
  assert.match(ics, /BEGIN:VCALENDAR\r\n/);
  assert.match(ics, /DTSTART;VALUE=DATE:20260828/);
  assert.match(ics, /DTEND;VALUE=DATE:20260831/);
  assert.match(ics, /LOCATION:Cowes\\, UK/);
  assert.match(ics, /END:VCALENDAR\r\n$/);
});
