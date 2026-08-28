let lastActivityReport = 0;

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
