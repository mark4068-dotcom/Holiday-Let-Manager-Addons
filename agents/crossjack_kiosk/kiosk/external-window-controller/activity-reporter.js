const REPORTER_VERSION = "2.0.0";
const SESSION_KEY = "crossjack-anonymous-usage-session";
const SESSION_IDLE_MS = 15 * 60 * 1000;
const ACTIVE_GRACE_MS = 90 * 1000;
const HEARTBEAT_MS = 5 * 60 * 1000;
let lastActivityReport = 0;

function sendMetric(event, dimension = null) {
  return chrome.runtime.sendMessage({
    type: "crossjack-kiosk-metric",
    event,
    dimension,
    reporter_version: REPORTER_VERSION,
  }).catch(() => ({ accepted: false }));
}

function pageForLocation() {
  const path = location.pathname.replace(/\/$/, "");
  if (path === "/crossjack-guest" || path === "/crossjack-guest/0") return "welcome";
  if (path.includes("/events-places")) return "events_places";
  if (path.includes("/digital-house-guide") || path.includes("/house-guide")) return "house_guide";
  if (path.includes("/heating-controls") || path.includes("/heating")) return "heating";
  if (path.includes("/weather-tides")) return "weather_tides";
  if (path.includes("/ferrys")) return "ferry_status";
  if (path.includes("/tbd")) return "ferry_maps";
  return null;
}

function readSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); }
  catch { return null; }
}

function writeSession(session) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(session)); }
  catch { /* metrics remain best-effort if browser storage is unavailable */ }
}

function activeSession(now = Date.now()) {
  const session = readSession();
  return session && now - Number(session.last_activity || 0) < SESSION_IDLE_MS
    ? session
    : null;
}

function startSession(now = Date.now()) {
  const session = {
    last_activity: now,
    meaningful_events: 0,
    engaged: false,
    last_active_minute: now,
  };
  writeSession(session);
  sendMetric("session_start");
  return session;
}

function touchSession(now = Date.now()) {
  const session = activeSession(now) || startSession(now);
  session.last_activity = now;
  writeSession(session);
  return session;
}

function markMeaningful() {
  const session = touchSession();
  session.meaningful_events = Number(session.meaningful_events || 0) + 1;
  if (!session.engaged && session.meaningful_events >= 2) {
    session.engaged = true;
    sendMetric("session_engaged");
  }
  writeSession(session);
}

function recordPageView(page) {
  if (!page || !activeSession()) return;
  sendMetric("page_view", page);
  markMeaningful();
}

function actionForEvent(event) {
  const path = event.composedPath();
  const control = path.find((element) =>
    element instanceof Element && element.matches("a, button, [role='button'], [role='tab']"));
  if (!control) return null;
  const text = String(control.innerText || control.getAttribute("aria-label") || "").toLowerCase();
  const href = control instanceof HTMLAnchorElement ? control.href : control.getAttribute("href");
  if (text.includes("direction") || text.includes("view in map")) return "directions";
  if (location.pathname.includes("heating") && control.matches("button, [role='button']")) return "heating_control";
  if (!href) return null;
  try {
    const url = new URL(href, location.href);
    if (url.searchParams.get("v") === "event") return "event_detail";
    if (url.searchParams.get("v") === "guide") return "place_detail";
    if (url.origin === location.origin && url.pathname.startsWith("/crossjack-guest")) return null;
    if (/\.pdf($|\?)/i.test(url.href) || url.hostname.includes("docs.google")) return "document";
    if (url.hostname.includes("youtube")) return "video";
    return "external_link";
  } catch {
    return null;
  }
}

function isAttractTouch(event) {
  return event.composedPath().some((element) => element?.id === "crossjack-attract-screen");
}

function reportKioskActivity() {
  const now = Date.now();
  if (now - lastActivityReport < 750) return;
  lastActivityReport = now;
  chrome.runtime.sendMessage({ type: "crossjack-kiosk-activity" }).catch(() => {});
}

if (window.top === window.self) {
  sendMetric("reporter_heartbeat");
  setInterval(() => sendMetric("reporter_heartbeat"), HEARTBEAT_MS);

  const page = pageForLocation();
  if (page) recordPageView(page);
  let lastLocation = `${location.pathname}${location.search}`;

  setInterval(() => {
    const currentLocation = `${location.pathname}${location.search}`;
    if (currentLocation === lastLocation) return;
    lastLocation = currentLocation;
    recordPageView(pageForLocation());
  }, 1000);

  document.addEventListener("crossjack-kiosk-session-start", () => {
    startSession();
    const currentPage = pageForLocation();
    if (currentPage) {
      sendMetric("page_view", currentPage);
      markMeaningful();
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (isAttractTouch(event)) return;
    const existing = activeSession();
    touchSession();
    if (!existing) {
      const currentPage = pageForLocation();
      if (currentPage) {
        sendMetric("page_view", currentPage);
        markMeaningful();
      }
    }
  }, { capture: true, passive: true });

  document.addEventListener("click", (event) => {
    const action = actionForEvent(event);
    if (!action) return;
    touchSession();
    sendMetric("action", action);
    markMeaningful();
  }, { capture: true, passive: true });

  setInterval(() => {
    const now = Date.now();
    const session = activeSession(now);
    if (!session || now - Number(session.last_activity || 0) > ACTIVE_GRACE_MS) return;
    if (now - Number(session.last_active_minute || 0) < 60 * 1000) return;
    session.last_active_minute = now;
    writeSession(session);
    sendMetric("active_minute");
  }, 60 * 1000);
}

["pointerdown", "touchstart", "keydown", "wheel"].forEach((eventName) => {
  window.addEventListener(eventName, reportKioskActivity, {
    capture: true,
    passive: true,
  });
});
