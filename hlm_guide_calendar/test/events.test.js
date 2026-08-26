import test from "node:test";
import assert from "node:assert/strict";
import { dateInTimezone, upcomingEvents } from "../src/events.js";

const event = (summary, start, end) => ({ summary, start, end });

test("uses the configured timezone to determine today's date", () => {
  const instant = new Date("2026-08-25T23:30:00Z");
  assert.equal(dateInTimezone(instant, "Europe/London"), "2026-08-26");
  assert.equal(dateInTimezone(instant, "UTC"), "2026-08-25");
});

test("keeps ongoing events and starts through the inclusive horizon date", () => {
  const events = [
    event("Expired", "2026-08-20", "2026-08-26"),
    event("Already in progress", "2026-08-25", "2026-08-28"),
    event("Today", "2026-08-26", "2026-08-27"),
    event("Horizon boundary", "2026-09-05", "2026-09-07"),
    event("Beyond horizon", "2026-09-06", "2026-09-07"),
  ];

  assert.deepEqual(upcomingEvents(events, {
    horizonDays: 10,
    now: new Date("2026-08-26T12:00:00Z"),
    timezone: "Europe/London",
  }).map(({ summary }) => summary), [
    "Already in progress",
    "Today",
    "Horizon boundary",
  ]);
});

test("drops malformed events instead of leaking them into feeds", () => {
  assert.deepEqual(upcomingEvents([
    { summary: "No dates" },
    event("Valid", "2026-08-27", "2026-08-28"),
  ], {
    now: new Date("2026-08-26T12:00:00Z"),
  }).map(({ summary }) => summary), ["Valid"]);
});
