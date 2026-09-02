(() => {
  if (window.top !== window) {
    return;
  }

  const ATTRACT_ID = "crossjack-attract-screen";
  const ATTRACT_ACTIVE_KEY = "crossjack-attract-active";
  const IDLE_TIMEOUT_MS = 15 * 60 * 1000;
  const KIOSK_PARAMS =
    "hide_header&hide_sidebar&hide_menubutton&hide_search&hide_assistant&hide_overflow&cache";
  let idleTimer;
  let clockTimer;
  let previousOverflow;

  function lockPageScroll() {
    if (previousOverflow) return;
    previousOverflow = {
      document: document.documentElement.style.overflow,
      body: document.body.style.overflow,
    };
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
  }

  function unlockPageScroll() {
    if (!previousOverflow) return;
    document.documentElement.style.overflow = previousOverflow.document;
    document.body.style.overflow = previousOverflow.body;
    previousOverflow = null;
  }

  function isGuestDashboard() {
    return (
      location.pathname === "/crossjack-guest" ||
      location.pathname.startsWith("/crossjack-guest/")
    );
  }

  if (!isGuestDashboard()) {
    return;
  }

  if (new URLSearchParams(location.search).has("crossjack_attract")) {
    sessionStorage.setItem(ATTRACT_ACTIVE_KEY, "1");
  }

  function welcomeUrl() {
    return `${location.origin}/crossjack-guest/0?${KIOSK_PARAMS}`;
  }

  function updateClock() {
    const overlay = document.getElementById(ATTRACT_ID);
    if (!overlay) {
      return;
    }

    const now = new Date();
    overlay.querySelector(".crossjack-attract-time").textContent =
      new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(now);
    overlay.querySelector(".crossjack-attract-date").textContent =
      new Intl.DateTimeFormat("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
      }).format(now);
  }

  function createOverlay() {
    if (document.getElementById(ATTRACT_ID) || !document.body) {
      return document.getElementById(ATTRACT_ID);
    }

    const overlay = document.createElement("section");
    overlay.id = ATTRACT_ID;
    overlay.setAttribute("role", "button");
    overlay.setAttribute("aria-label", "Touch to open the Crossjack guest guide");
    overlay.tabIndex = 0;
    overlay.innerHTML = `
      <div class="crossjack-attract-content">
        <img class="crossjack-attract-logo" alt="Sailcottages Isle of Wight"
             src="${chrome.runtime.getURL("sailcottages-logo.svg")}">
        <p class="crossjack-attract-welcome">Welcome to Crossjack Cottage</p>
        <p class="crossjack-attract-time"></p>
        <p class="crossjack-attract-date"></p>
        <div class="crossjack-attract-prompt">
          <span class="crossjack-attract-prompt-icon" aria-hidden="true">☝</span>
          <span>Touch to explore your property guide and local information</span>
        </div>
      </div>`;

    overlay.addEventListener("pointerdown", wake, { capture: true });
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        wake(event);
      }
    });
    document.body.appendChild(overlay);
    updateClock();
    return overlay;
  }

  function clearTimers() {
    clearTimeout(idleTimer);
    clearInterval(clockTimer);
  }

  function show() {
    clearTimers();
    sessionStorage.setItem(ATTRACT_ACTIVE_KEY, "1");
    chrome.runtime
      .sendMessage({ type: "crossjack-attract-start" })
      .catch(() => {});

    if (location.pathname !== "/crossjack-guest/0") {
      location.replace(welcomeUrl());
      return;
    }

    const overlay = createOverlay();
    if (!overlay) {
      return;
    }
    lockPageScroll();
    updateClock();
    clockTimer = setInterval(updateClock, 1000);
    requestAnimationFrame(() => {
      overlay.classList.add("crossjack-attract-active");
      overlay.focus({ preventScroll: true });
    });
  }

  function scheduleIdle() {
    clearTimeout(idleTimer);
    if (sessionStorage.getItem(ATTRACT_ACTIVE_KEY) === "1") {
      return;
    }
    idleTimer = setTimeout(show, IDLE_TIMEOUT_MS);
  }

  function wake(event) {
    event?.preventDefault();
    event?.stopImmediatePropagation();
    sessionStorage.removeItem(ATTRACT_ACTIVE_KEY);
    clearTimers();
    unlockPageScroll();
    document
      .getElementById(ATTRACT_ID)
      ?.classList.remove("crossjack-attract-active");
    scheduleIdle();
  }

  ["pointerdown", "keydown", "wheel"].forEach((eventName) => {
    window.addEventListener(eventName, scheduleIdle, {
      capture: true,
      passive: true,
    });
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "crossjack-attract-activity") {
      scheduleIdle();
    }
  });

  document.addEventListener("crossjack-activate-attract", show);

  function start() {
    createOverlay();
    if (sessionStorage.getItem(ATTRACT_ACTIVE_KEY) === "1") {
      show();
    } else {
      scheduleIdle();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
