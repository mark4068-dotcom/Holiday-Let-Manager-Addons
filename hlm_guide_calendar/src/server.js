import http from "node:http";
import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { eventsToIcs } from "./calendar.js";
import { upcomingEvents } from "./events.js";
import { guestPage } from "./guest-page.js";
import { scrapeGuide } from "./scrape.js";
import { recordMetric } from "./metrics.js";

const OPTIONS_PATH = process.env.OPTIONS_PATH || "/data/options.json";
const DATA_DIR = process.env.DATA_DIR || "/data/holiday-guide-calendar";
const METRICS_PATH = `${DATA_DIR}/metrics.json`;
const PORT = Number(process.env.PORT || 8788);

const defaults = {
  guide_url: "https://myholidayguide.app/property/1772992311254x169748028166504450?v=Explore&poi=&cat=&pi=",
  refresh_hours: 24,
  event_horizon_days: 10,
  scrape_favourites: true,
  timezone: "Europe/London",
  feed_username: "",
  feed_password: "",
};

const state = {
  running: false,
  started_at: new Date().toISOString(),
  last_attempt_at: null,
  last_success_at: null,
  next_update_at: null,
  event_count: 0,
  source_event_count: 0,
  event_horizon_days: defaults.event_horizon_days,
  favourite_count: 0,
  error: null,
};

async function loadOptions() {
  try { return { ...defaults, ...JSON.parse(await readFile(OPTIONS_PATH, "utf8")) }; }
  catch (error) {
    if (process.env.NODE_ENV === "test") return defaults;
    console.warn(`Using default options: ${error.message}`);
    return defaults;
  }
}

async function atomicWrite(path, content) {
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.tmp`;
  await writeFile(temporary, content);
  await rename(temporary, path);
}

async function readOutput(name, fallback = "") {
  try { return await readFile(`${DATA_DIR}/${name}`, "utf8"); }
  catch { return fallback; }
}

async function readJsonOutput(name, fallback) {
  try { return JSON.parse(await readOutput(name)); }
  catch { return fallback; }
}

async function restoreStatus() {
  try {
    const saved = JSON.parse(await readFile(`${DATA_DIR}/status.json`, "utf8"));
    for (const key of ["last_success_at", "event_count", "source_event_count", "event_horizon_days", "favourite_count"]) {
      if (saved[key] !== undefined) state[key] = saved[key];
    }
  } catch { /* first run */ }
}

async function refresh(options) {
  if (state.running) return;
  state.running = true;
  state.last_attempt_at = new Date().toISOString();
  state.error = null;
  try {
    const output = await scrapeGuide({
      guideUrl: options.guide_url,
      scrapeFavourites: options.scrape_favourites,
      timezone: options.timezone,
    });
    const updatedAt = new Date();
    const events = upcomingEvents(output.events, {
      horizonDays: options.event_horizon_days,
      now: updatedAt,
      timezone: options.timezone,
    });
    const payload = {
      updated_at: updatedAt.toISOString(),
      source: options.guide_url,
      event_horizon_days: options.event_horizon_days,
      events,
    };
    await atomicWrite(`${DATA_DIR}/events.json`, `${JSON.stringify(payload, null, 2)}\n`);
    await atomicWrite(`${DATA_DIR}/events.ics`, eventsToIcs(events, updatedAt));
    await atomicWrite(`${DATA_DIR}/favourites.json`, `${JSON.stringify({
      updated_at: updatedAt.toISOString(),
      source: options.guide_url,
      favourites: output.favourites,
    }, null, 2)}\n`);
    state.last_success_at = updatedAt.toISOString();
    state.event_count = events.length;
    state.source_event_count = output.events.length;
    state.event_horizon_days = options.event_horizon_days;
    state.favourite_count = output.favourites.length;
    console.log(`Updated ${state.event_count} of ${state.source_event_count} events within the next ${state.event_horizon_days} days and ${state.favourite_count} favourite places`);
  } catch (error) {
    state.error = error instanceof Error ? error.message : String(error);
    console.error(`Scrape failed: ${state.error}`);
  } finally {
    state.running = false;
    state.next_update_at = new Date(Date.now() + options.refresh_hours * 3_600_000).toISOString();
    await atomicWrite(`${DATA_DIR}/status.json`, `${JSON.stringify(state, null, 2)}\n`);
  }
}

function authorised(request, options) {
  if (!options.feed_username && !options.feed_password) return true;
  const [scheme, token] = String(request.headers.authorization || "").split(" ");
  if (scheme !== "Basic" || !token) return false;
  const credentials = Buffer.from(token, "base64").toString("utf8");
  return credentials === `${options.feed_username}:${options.feed_password}`;
}

function send(response, status, type, body, extraHeaders = {}) {
  response.writeHead(status, {
    "Content-Type": type,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    ...extraHeaders,
  });
  response.end(body);
}

function statusHtml() {
  const error = state.error ? `<p><strong>Last error:</strong> ${escapeHtml(state.error)}</p>` : "";
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>HLM Guest Guide</title><style>body{font:16px system-ui;max-width:760px;margin:2rem auto;padding:0 1rem;color:#202124}dl{display:grid;grid-template-columns:12rem 1fr;gap:.6rem}code{background:#eee;padding:.15rem .3rem}button{padding:.6rem 1rem}</style></head><body><h1>HLM Guest Guide</h1><dl><dt>Status</dt><dd>${state.running ? "Updating" : state.error ? "Last update failed" : "Ready"}</dd><dt>Last success</dt><dd>${state.last_success_at || "Not yet"}</dd><dt>Next update</dt><dd>${state.next_update_at || "Pending"}</dd><dt>Event horizon</dt><dd>${state.event_horizon_days} days</dd><dt>Events shown</dt><dd>${state.event_count} of ${state.source_event_count}</dd><dt>Favourite places</dt><dd>${state.favourite_count}</dd></dl>${error}<p>Calendar feed: <code>/events.ics</code></p><form method="post" action="refresh"><button>Refresh now</button></form></body></html>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

await mkdir(DATA_DIR, { recursive: true });
await restoreStatus();
const options = await loadOptions();

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  if (url.pathname === "/health") {
    return send(response, 200, "application/json", JSON.stringify({ ok: true, ...state }));
  }
  if (request.method === "POST" && url.pathname === "/metrics") {
    let body = "";
    for await (const chunk of request) body += chunk;
    try {
      const payload = JSON.parse(body);
      const accepted = await recordMetric(METRICS_PATH, String(payload.event || ""));
      return send(response, accepted ? 204 : 400, "text/plain", "");
    } catch { return send(response, 400, "text/plain", "Invalid metric\n"); }
  }
  if (url.pathname === "/metrics.json") {
    return send(response, 200, "application/json", await readOutput("metrics.json", "{}"));
  }
  if (url.pathname === "/guest" || url.pathname === "/guest/") {
    const eventData = await readJsonOutput("events.json", { events: [], updated_at: null });
    const favouriteData = await readJsonOutput("favourites.json", { favourites: [], updated_at: null });
    return send(response, 200, "text/html; charset=utf-8", guestPage({
      events: eventData.events,
      favourites: favouriteData.favourites,
      updatedAt: eventData.updated_at || favouriteData.updated_at,
    }), {
      "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src https: data:; frame-ancestors *; base-uri 'none'; form-action 'none'",
    });
  }
  if (url.pathname === "/" || url.pathname.endsWith("/")) {
    return send(response, 200, "text/html; charset=utf-8", statusHtml());
  }
  if (request.method === "POST" && url.pathname.endsWith("/refresh")) {
    refresh(options);
    response.writeHead(303, { Location: "./" });
    return response.end();
  }
  if (["/events.ics", "/events.json", "/favourites.json"].includes(url.pathname)) {
    if (!authorised(request, options)) return send(response, 401, "text/plain", "Authentication required\n", { "WWW-Authenticate": 'Basic realm="Holiday Guide"' });
    const name = url.pathname.slice(1);
    const body = await readOutput(name);
    if (!body) return send(response, 503, "text/plain", "The first successful scrape has not completed.\n");
    const type = name.endsWith(".ics") ? "text/calendar; charset=utf-8" : "application/json; charset=utf-8";
    return send(response, 200, type, body);
  }
  return send(response, 404, "text/plain", "Not found\n");
});

server.listen(PORT, "0.0.0.0", () => console.log(`HLM Guest Guide listening on port ${PORT}`));
refresh(options);
setInterval(() => refresh(options), options.refresh_hours * 3_600_000).unref();
