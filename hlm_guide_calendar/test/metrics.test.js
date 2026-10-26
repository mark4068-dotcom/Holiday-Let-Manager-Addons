import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { cutoverMetrics, metricsSummary, recordMetric } from "../src/metrics.js";

async function metricsPath() {
  return join(await mkdtemp(join(tmpdir(), "hlm-metrics-")), "metrics.json");
}

test("records anonymous sessions, engagement, page views, actions and active time", async () => {
  const path = await metricsPath();
  const at = (time) => new Date(`2026-10-21T${time}Z`);
  assert.equal(await recordMetric(path, { event: "reporter_heartbeat", reporter_version: "2.0.0" }, at("10:00:00")), true);
  await recordMetric(path, { event: "session_start", reporter_version: "2.0.0" }, at("10:01:00"));
  await recordMetric(path, { event: "page_view", dimension: "welcome", reporter_version: "2.0.0" }, at("10:01:01"));
  await recordMetric(path, { event: "page_view", dimension: "events_places", reporter_version: "2.0.0" }, at("10:02:00"));
  await recordMetric(path, { event: "session_engaged", reporter_version: "2.0.0" }, at("10:02:01"));
  await recordMetric(path, { event: "action", dimension: "directions", reporter_version: "2.0.0" }, at("10:03:00"));
  await recordMetric(path, { event: "active_minute", reporter_version: "2.0.0" }, at("10:04:00"));

  const summary = await metricsSummary(path, at("10:05:00"));
  assert.equal(summary.reporter_status, "ok");
  assert.equal(summary.reporter_version, "2.0.0");
  assert.equal(summary.seven_day.sessions, 1);
  assert.equal(summary.seven_day.engaged_sessions, 1);
  assert.equal(summary.seven_day.interactions, 3);
  assert.equal(summary.seven_day.active_minutes, 1);
  assert.equal(summary.seven_day.interactions_per_session, 3);
  assert.deepEqual(summary.seven_day.page_views, { welcome: 1, events_places: 1 });
  assert.deepEqual(summary.seven_day.actions, { directions: 1 });
});

test("rejects unknown events and dimensions", async () => {
  const path = await metricsPath();
  assert.equal(await recordMetric(path, { event: "interaction" }), false);
  assert.equal(await recordMetric(path, { event: "page_view", dimension: "secret_page" }), false);
  assert.equal(await recordMetric(path, { event: "action", dimension: "typed_text" }), false);
});

test("accepts legacy object payloads during reporter rollout", async () => {
  const path = await metricsPath();
  const now = new Date("2026-10-21T10:00:00.000Z");
  assert.equal(await recordMetric(path, { event: "tab_welcome" }, now), true);
  const summary = await metricsSummary(path, now);
  assert.equal(summary.seven_day.page_views.welcome, 1);
});

test("migrates the privacy-safe legacy daily aggregate", async () => {
  const path = await metricsPath();
  await writeFile(path, JSON.stringify({
    "2026-10-20": {
      total: 5,
      events: { session: 1, tab_welcome: 1, tab_house: 2, directions: 1 },
    },
  }));
  const summary = await metricsSummary(path, new Date("2026-10-21T10:00:00Z"));
  assert.equal(summary.thirty_day.sessions, 1);
  assert.equal(summary.thirty_day.interactions, 4);
  assert.deepEqual(summary.thirty_day.page_views, { welcome: 1, house_guide: 2 });
  assert.deepEqual(summary.thirty_day.actions, { directions: 1 });
});

test("retains only the rolling year when a new metric is written", async () => {
  const path = await metricsPath();
  await writeFile(path, JSON.stringify({
    "2025-09-01": { total: 1, events: { tab_welcome: 1 } },
    "2026-10-20": { total: 1, events: { tab_welcome: 1 } },
  }));
  await recordMetric(path, { event: "reporter_heartbeat", reporter_version: "2.0.0" }, new Date("2026-10-21T10:00:00Z"));
  const stored = JSON.parse(await readFile(path, "utf8"));
  assert.equal(stored.days["2025-09-01"], undefined);
  assert.ok(stored.days["2026-10-20"]);
});

test("marks reporter telemetry stale after ten minutes without heartbeat", async () => {
  const path = await metricsPath();
  await recordMetric(path, { event: "reporter_heartbeat", reporter_version: "2.0.0" }, new Date("2026-10-21T10:00:00Z"));
  assert.equal((await metricsSummary(path, new Date("2026-10-21T10:11:00Z"))).reporter_status, "stale");
});

test("archives legacy metrics and starts the signed reporter baseline only once", async () => {
  const directory = await mkdtemp(join(tmpdir(), "hlm-metrics-cutover-"));
  const path = join(directory, "metrics.json");
  const archive = join(directory, "metrics-legacy.json");
  const marker = join(directory, "metrics-cutover.json");
  const legacy = JSON.stringify({ "2026-10-20": { total: 2, events: { tab_welcome: 2 } } });
  await writeFile(path, legacy);

  assert.equal(await cutoverMetrics(path, archive, marker, new Date("2026-10-26T13:30:00Z")), true);
  assert.equal(await readFile(archive, "utf8"), legacy);
  assert.equal((await metricsSummary(path, new Date("2026-10-26T13:30:00Z"))).total, 0);

  await recordMetric(path, { event: "page_view", dimension: "welcome", reporter_version: "2.0.0" }, new Date("2026-10-26T13:31:00Z"));
  assert.equal(await cutoverMetrics(path, archive, marker, new Date("2026-10-26T13:32:00Z")), false);
  assert.equal((await metricsSummary(path, new Date("2026-10-26T13:32:00Z"))).total, 1);
});
