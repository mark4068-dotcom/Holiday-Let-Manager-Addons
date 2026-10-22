import test from "node:test";
import assert from "node:assert/strict";
import { collectionTimeoutMs, isStale, withCollectionTimeout, collectorHealth } from "../src/health.js";

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

test("a hung collection requests watchdog recovery after its deadline", async () => {
  const state = { running: true, recovery_required: false };
  const hungCollection = new Promise(() => {});
  await assert.rejects(
    withCollectionTimeout(hungCollection, 10, () => { state.recovery_required = true; }),
    /Collection timed out/,
  );
  const health = collectorHealth(state, { ...fresh, services: Array(6).fill({}) }, {}, NOW);
  assert.equal(health.statusCode, 503);
  assert.equal(health.payload.recovery_required, true);
  assert.equal(health.payload.stale, true);
  assert.equal(health.payload.service_count, 6);
});

test("a successful collection does not request recovery", async () => {
  let requested = false;
  assert.equal(await withCollectionTimeout(Promise.resolve("complete"), 100, () => { requested = true; }), "complete");
  assert.equal(requested, false);
});

test("ordinary upstream rejection does not become a stuck-browser restart", async () => {
  const state = { running: false, recovery_required: false, error: "Upstream unavailable" };
  await assert.rejects(
    withCollectionTimeout(Promise.reject(new Error("Upstream unavailable")), 100, () => { state.recovery_required = true; }),
    /Upstream unavailable/,
  );
  const health = collectorHealth(state, { ...fresh, services: Array(6).fill({}) }, {}, NOW);
  assert.equal(health.statusCode, 200);
  assert.equal(health.payload.stale, true);
  assert.equal(health.payload.recovery_required, false);
});

test("the first collection has startup grace before cached data exists", () => {
  const health = collectorHealth(
    { running: true, recovery_required: false },
    { updated_at: null, services: [] }, {}, NOW,
  );
  assert.equal(health.statusCode, 200);
  assert.equal(health.payload.ok, false);
  assert.equal(health.payload.stale, true);
});

test("a timed-out collector stays unhealthy even with a recent retained payload", () => {
  const health = collectorHealth(
    { running: false, recovery_required: true },
    { ...fresh, services: Array(6).fill({}) }, {}, NOW,
  );
  assert.equal(health.statusCode, 503);
  assert.equal(health.payload.stale, true);
});
