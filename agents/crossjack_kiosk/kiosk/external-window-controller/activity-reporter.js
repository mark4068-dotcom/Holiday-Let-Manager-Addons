let lastActivityReport = 0;
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

function recordMetric(event) {
  fetch(METRICS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event }),
    mode: "no-cors",
    keepalive: true,
  }).catch(() => {});
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
