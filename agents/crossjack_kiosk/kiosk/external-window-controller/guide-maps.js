function addGuideCloseControl() {
  if (document.getElementById("crossjack-kiosk-close-control")) return;
  const button = document.createElement("button");
  button.id = "crossjack-kiosk-close-control";
  button.type = "button";
  button.innerHTML = "✕&nbsp; Close &amp; return";
  Object.assign(button.style, {
    position: "fixed", zIndex: "2147483647", top: "18px", right: "22px",
    minWidth: "190px", minHeight: "64px", padding: "12px 20px",
    border: "3px solid #fff", borderRadius: "14px",
    boxShadow: "0 3px 14px rgba(0,0,0,.45)", background: "#174f65",
    color: "#fff", font: "700 22px/1.2 sans-serif", cursor: "pointer",
  });
  button.addEventListener("click", () => {
    if (window.top !== window) {
      history.back();
      return;
    }
    chrome.runtime.sendMessage({ type: "crossjack-close-control", action: "close" });
  });
  document.documentElement.appendChild(button);
}

addGuideCloseControl();

// My Holiday Guide is a single-page app and can rebuild portions of its DOM
// after navigation. Keep the return control present even when that happens.
const guideCloseObserver = new MutationObserver(() => addGuideCloseControl());
guideCloseObserver.observe(document.documentElement, { childList: true, subtree: true });
for (const method of ["pushState", "replaceState"]) {
  const original = history[method];
  history[method] = function (...args) {
    const result = original.apply(this, args);
    setTimeout(addGuideCloseControl, 0);
    return result;
  };
}
addEventListener("popstate", addGuideCloseControl, true);
addEventListener("hashchange", addGuideCloseControl, true);

function isViewInMapControl(element) {
  const control = element.closest(".clickable-element");
  if (!control) {
    return null;
  }

  return control.textContent.trim() === "View in map" ? control : null;
}

function getMapDestination() {
  const destinations = Array.from(
    document.querySelectorAll('input[placeholder="Start typing..."]'),
  )
    .map((input) => input.value.trim())
    .filter(Boolean);

  // My Holiday Guide renders the property address first and the selected
  // place destination second.
  return destinations.at(-1) || "";
}

document.addEventListener(
  "click",
  (event) => {
    if (!(event.target instanceof Element) || !isViewInMapControl(event.target)) {
      return;
    }

    const query = getMapDestination();
    if (!query) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    chrome.runtime.sendMessage({
      type: "crossjack-open-map",
      query,
    });
  },
  true,
);
