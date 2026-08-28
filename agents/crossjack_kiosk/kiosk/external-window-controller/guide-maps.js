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
