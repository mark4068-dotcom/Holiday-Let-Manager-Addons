import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const SCHEMA_VERSION = "2.0";
const PAGES = new Set([
  "welcome", "events_places", "house_guide", "heating",
  "weather_tides", "ferry_status", "ferry_maps",
]);
const ACTIONS = new Set([
  "directions", "event_detail", "place_detail", "document",
  "heating_control", "external_link", "video",
]);
const EVENTS = new Set([
  "reporter_heartbeat", "session_start", "session_engaged",
  "page_view", "action", "active_minute",
]);

const LEGACY = {
  session: ["session_start", null],
  tab_welcome: ["page_view", "welcome"],
  tab_events: ["page_view", "events_places"],
  tab_house: ["page_view", "house_guide"],
  tab_heating: ["page_view", "heating"],
  tab_weather: ["page_view", "weather_tides"],
  directions: ["action", "directions"],
  external_return: ["action", "external_link"],
  screensaver_wakeup: ["session_start", null],
};

const dayKey = (date = new Date()) => date.toISOString().slice(0, 10);

function emptyDay() {
  return {
    sessions: 0,
    engaged_sessions: 0,
    interactions: 0,
    active_seconds: 0,
    page_views: {},
    actions: {},
    last_event_at: null,
  };
}

function emptyStore() {
  return {
    schema_version: SCHEMA_VERSION,
    telemetry: {
      last_received_at: null,
      last_heartbeat: null,
      last_event_at: null,
      reporter_version: null,
    },
    days: {},
  };
}

function increment(target, key, count = 1) {
  target[key] = Number(target[key] || 0) + count;
}

function normalisePayload(payload) {
  if (typeof payload === "string") {
    const mapped = LEGACY[payload];
    return mapped ? { event: mapped[0], dimension: mapped[1], reporter_version: "legacy" } : null;
  }
  if (!payload || typeof payload !== "object") return null;
  const event = String(payload.event || "");
  const dimension = payload.dimension == null ? null : String(payload.dimension);
  const legacy = LEGACY[event];
  if (legacy) {
    return {
      event: legacy[0],
      dimension: legacy[1],
      reporter_version: String(payload.reporter_version || "legacy").slice(0, 32),
    };
  }
  if (!EVENTS.has(event)) return null;
  if (event === "page_view" && !PAGES.has(dimension)) return null;
  if (event === "action" && !ACTIONS.has(dimension)) return null;
  return {
    event,
    dimension,
    reporter_version: String(payload.reporter_version || "unknown").slice(0, 32),
  };
}

function migrate(raw) {
  if (raw?.schema_version === SCHEMA_VERSION && raw.days && raw.telemetry) return raw;
  const store = emptyStore();
  if (!raw || typeof raw !== "object") return store;
  for (const [day, legacyDay] of Object.entries(raw)) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !legacyDay || typeof legacyDay !== "object") continue;
    const converted = emptyDay();
    for (const [event, countValue] of Object.entries(legacyDay.events || {})) {
      const count = Number(countValue || 0);
      const mapped = LEGACY[event];
      if (!mapped || count <= 0) continue;
      if (mapped[0] === "session_start") converted.sessions += count;
      if (mapped[0] === "page_view") {
        increment(converted.page_views, mapped[1], count);
        converted.interactions += count;
      }
      if (mapped[0] === "action") {
        increment(converted.actions, mapped[1], count);
        converted.interactions += count;
      }
    }
    store.days[day] = converted;
  }
  return store;
}

async function readStore(path) {
  try { return migrate(JSON.parse(await readFile(path, "utf8"))); }
  catch { return emptyStore(); }
}

async function writeStore(path, store) {
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.tmp`;
  await writeFile(temporary, `${JSON.stringify(store, null, 2)}\n`);
  await rename(temporary, path);
}

let metricQueue = Promise.resolve();

async function recordMetricNow(path, payload, date) {
  const metric = normalisePayload(payload);
  if (!metric) return false;
  const store = await readStore(path);
  const cutoff = new Date(date);
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 1);
  for (const key of Object.keys(store.days)) if (key < dayKey(cutoff)) delete store.days[key];

  const timestamp = date.toISOString();
  store.telemetry.last_received_at = timestamp;
  store.telemetry.reporter_version = metric.reporter_version;
  if (metric.event === "reporter_heartbeat") {
    store.telemetry.last_heartbeat = timestamp;
    await writeStore(path, store);
    return true;
  }

  const day = dayKey(date);
  store.days[day] ||= emptyDay();
  const target = store.days[day];
  target.last_event_at = timestamp;
  store.telemetry.last_event_at = timestamp;
  if (metric.event === "session_start") target.sessions += 1;
  if (metric.event === "session_engaged") target.engaged_sessions += 1;
  if (metric.event === "active_minute") target.active_seconds += 60;
  if (metric.event === "page_view") {
    increment(target.page_views, metric.dimension);
    target.interactions += 1;
  }
  if (metric.event === "action") {
    increment(target.actions, metric.dimension);
    target.interactions += 1;
  }
  await writeStore(path, store);
  return true;
}

export function recordMetric(path, payload, date = new Date()) {
  const operation = metricQueue.then(() => recordMetricNow(path, payload, date));
  metricQueue = operation.catch(() => {});
  return operation;
}

export const allowedMetrics = EVENTS;
export const allowedPages = PAGES;
export const allowedActions = ACTIONS;

function periodSummary(store, days, now) {
  const cutoff = new Date(now);
  cutoff.setUTCDate(cutoff.getUTCDate() - days + 1);
  const cutoffKey = dayKey(cutoff);
  const result = {
    sessions: 0,
    engaged_sessions: 0,
    interactions: 0,
    active_minutes: 0,
    active_days: 0,
    page_views: {},
    actions: {},
  };
  for (const [key, value] of Object.entries(store.days)) {
    if (key < cutoffKey) continue;
    result.sessions += Number(value.sessions || 0);
    result.engaged_sessions += Number(value.engaged_sessions || 0);
    result.interactions += Number(value.interactions || 0);
    result.active_minutes += Number(value.active_seconds || 0) / 60;
    if (Number(value.sessions || 0) > 0 || Number(value.interactions || 0) > 0) result.active_days += 1;
    for (const [page, count] of Object.entries(value.page_views || {})) increment(result.page_views, page, Number(count));
    for (const [action, count] of Object.entries(value.actions || {})) increment(result.actions, action, Number(count));
  }
  result.active_minutes = Math.round(result.active_minutes);
  result.interactions_per_session = result.sessions
    ? Number((result.interactions / result.sessions).toFixed(1))
    : 0;
  return result;
}

function legacyEvents(day) {
  if (!day) return {};
  const events = {
    session: Number(day.sessions || 0),
    session_engaged: Number(day.engaged_sessions || 0),
  };
  for (const [page, count] of Object.entries(day.page_views || {})) events[`page_${page}`] = count;
  for (const [action, count] of Object.entries(day.actions || {})) events[`action_${action}`] = count;
  return events;
}

export async function metricsSummary(path, now = new Date()) {
  const store = await readStore(path);
  const usageDays = Object.keys(store.days)
    .filter((key) => Number(store.days[key]?.sessions || 0) > 0 || Number(store.days[key]?.interactions || 0) > 0)
    .sort();
  const latestDay = usageDays.at(-1) || null;
  const latest = latestDay ? store.days[latestDay] : null;
  const heartbeatAge = store.telemetry.last_heartbeat
    ? now.getTime() - new Date(store.telemetry.last_heartbeat).getTime()
    : Number.POSITIVE_INFINITY;
  const reporterStatus = !store.telemetry.last_heartbeat
    ? "never"
    : heartbeatAge <= 10 * 60 * 1000 ? "ok" : "stale";
  const sevenDay = periodSummary(store, 7, now);
  const thirtyDay = periodSummary(store, 30, now);
  const rollingYear = periodSummary(store, 365, now);
  return {
    schema_version: SCHEMA_VERSION,
    total: rollingYear.interactions,
    days: rollingYear.active_days,
    latest_day: latestDay,
    latest_total: Number(latest?.interactions || 0),
    latest_events: legacyEvents(latest),
    reporter_status: reporterStatus,
    reporter_version: store.telemetry.reporter_version,
    last_heartbeat: store.telemetry.last_heartbeat,
    last_event_at: store.telemetry.last_event_at,
    updated_at: store.telemetry.last_received_at,
    seven_day: sevenDay,
    thirty_day: thirtyDay,
    rolling_12_month: rollingYear,
  };
}
