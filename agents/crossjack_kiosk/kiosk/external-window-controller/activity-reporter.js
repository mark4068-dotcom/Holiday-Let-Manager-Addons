let lastActivityReport = 0;
let lastMetricReport = 0;
const METRICS_ENDPOINT = "http://192.168.0.236:8788/metrics";

function metricForLocation() {
  const path = location.pathname;
  if (path.includes("/events-places")) return "tab_events";
  if (path.includes("/house-guide")) return "tab_house";
  if (path.includes("/heating")) return "tab_heating";
  if (path.includes("/weather-tides")) return "tab_weather";
  if (path.includes("/crossjack-guest")) return "tab_welcome";
  return "";
}

function metricForText(text) {
  const value = String(text || "").toLowerCase();
  if (value.includes("events") || value.includes("places")) return "tab_events";
  if (value.includes("house guide")) return "tab_house";
  if (value.includes("heating")) return "tab_heating";
  if (value.includes("weather") || value.includes("tides")) return "tab_weather";
  if (value.includes("welcome")) return "tab_welcome";
  return "";
}

function recordMetric(event) {
  fetch(METRICS_ENDPOINT, {
    method: "POST",
    body: JSON.stringify({ event }),
    mode: "no-cors",
    keepalive: true,
  }).catch(() => {});
}

function recordInteraction(target) {
  const now = Date.now();
  if (now - lastMetricReport < 1000) return;
  lastMetricReport = now;
  recordMetric("interaction");
  const metric = metricForText(target?.innerText || target?.getAttribute("aria-label"));
  if (metric) recordMetric(metric);
}

const sectionMetric = metricForLocation();
if (sectionMetric) {
  recordMetric(sectionMetric);
  try {
    if (!sessionStorage.getItem("crossjack-metrics-session")) {
      sessionStorage.setItem("crossjack-metrics-session", "1");
      recordMetric("session");
    }
  } catch (_error) { /* storage may be unavailable */ }
}

if (window.top === window.self) {
  ["pointerdown", "touchstart", "click"].forEach((eventName) => {
    document.addEventListener(eventName, (event) => {
      const target = event.target instanceof Element
        ? event.target.closest("button, a, [role='button'], [role='tab']")
        : null;
      recordInteraction(target);
    }, { capture: true, passive: true });
  });
}

function reportKioskActivity() {
  const now = Date.now();
  if (now - lastActivityReport < 750) {
    return;
  }

  lastActivityReport = now;
  chrome.runtime
    .sendMessage({ type: "crossjack-kiosk-activity" })
    .catch(() => {});
}

["pointerdown", "touchstart", "keydown", "wheel"].forEach((eventName) => {
  window.addEventListener(eventName, reportKioskActivity, {
    capture: true,
    passive: true,
  });
});
