import test from "node:test";
import assert from "node:assert/strict";
import { collectionTimeoutMs, isStale } from "../src/health.js";

const NOW = Date.parse("2026-10-12T09:00:00Z");
const fresh = { updated_at: "2026-10-12T08:58:00Z" };

test("marks an overdue running refresh as stale", () => {
  assert.equal(isStale({ running: true, next_update_at: "2026-10-12T08:59:00Z" }, fresh, { refresh_minutes: 5 }, NOW), true);
});

test("marks an old retained payload as stale", () => {
  assert.equal(isStale({ running: false }, { updated_at: "2026-10-11T22:06:13Z" }, { refresh_minutes: 5 }, NOW), true);
});

test("keeps a recent successful payload fresh", () => {
  assert.equal(isStale({ running: false, next_update_at: "2026-10-12T09:05:00Z" }, fresh, { refresh_minutes: 5 }, NOW), false);
});

test("gives a stuck collection a bounded timeout", () => {
  assert.equal(collectionTimeoutMs({ refresh_minutes: 5 }), 300_000);
});
