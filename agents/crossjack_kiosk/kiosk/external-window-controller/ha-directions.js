const attachedRoots = new WeakSet();

function getDirectionsLink(event) {
  return event.composedPath().find((element) => {
    if (!(element instanceof Element)) {
      return false;
    }
    return element.matches("a.pill") && element.textContent.trim() === "Directions";
  });
}

function getExternalGuideLink(event) {
  return event.composedPath().find((element) => {
    if (!(element instanceof HTMLAnchorElement) || !element.href) return false;
    try {
      const url = new URL(element.href);
      // Event and guide detail links leave the HA shell for My Holiday Guide.
      return url.hostname === "myholidayguide.app" &&
        (url.searchParams.get("v") === "event" || url.searchParams.get("v") === "guide");
    } catch (_error) {
      return false;
    }
  });
}

function getPlaceQuery(link) {
  const card = link.closest("article.place-card");
  const name = card?.querySelector("h3")?.textContent.trim() || "";
  const location =
    card?.querySelector(".location")?.textContent.trim() || "";

  return [name, location].filter(Boolean).join(", ");
}

function visitElement(element) {
  if (!(element instanceof Element)) {
    return;
  }
  if (element.shadowRoot) {
    watchRoot(element.shadowRoot);
  }
  element.querySelectorAll("*").forEach((child) => {
    if (child.shadowRoot) {
      watchRoot(child.shadowRoot);
    }
  });
}

function watchRoot(root) {
  if (attachedRoots.has(root)) {
    return;
  }

  attachedRoots.add(root);
  root.addEventListener("click", handleDirectionsClick, true);
  root.addEventListener("click", handleExternalGuideClick, true);
  root.querySelectorAll("*").forEach((element) => {
    if (element.shadowRoot) {
      watchRoot(element.shadowRoot);
    }
  });

  new MutationObserver((records) => {
    records.forEach((record) => {
      record.addedNodes.forEach(visitElement);
    });
  }).observe(root, { childList: true, subtree: true });
}

function handleDirectionsClick(event) {
  if (!location.pathname.startsWith("/crossjack-guest")) {
    return;
  }

  const link = getDirectionsLink(event);
  if (!link) {
    return;
  }

  const query = getPlaceQuery(link);
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
}

function handleExternalGuideClick(event) {
  if (!location.pathname.startsWith("/crossjack-guest")) return;
  const link = getExternalGuideLink(event);
  if (!link?.href) return;
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  chrome.runtime.sendMessage({ type: "crossjack-open-external", url: link.href });
}

watchRoot(document);
