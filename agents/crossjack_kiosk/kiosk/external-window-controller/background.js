const CHILD_BOUNDS = {
  left: 160,
  top: 70,
  width: 1600,
  height: 900,
};

const handledTabs = new Set();
const externalWindowIds = new Set();
const kioskOwners = new Map();

function isKioskUrl(rawUrl) {
  try {
    const url = new URL(rawUrl || "");
    const isGuestDashboard =
      url.pathname === "/crossjack-guest" ||
      url.pathname.startsWith("/crossjack-guest/");
    const isDigitalGuide =
      url.hostname === "myholidayguide.app" &&
      url.pathname.startsWith("/property/");
    return isGuestDashboard || isDigitalGuide;
  } catch (_error) {
    return false;
  }
}

function isTrustedOpener(tab) {
  return isKioskUrl(tab.pendingUrl || tab.url || "");
}

function isWeatherTidesDashboard(tab) {
  try {
    const url = new URL(tab?.pendingUrl || tab?.url || "");
    return url.pathname === "/crossjack-guest/weather-tides";
  } catch (_error) {
    return false;
  }
}

function isEmbeddedDashboardWidget(rawUrl) {
  try {
    const url = new URL(rawUrl || "");
    return url.hostname === "swimsafeuk.com" && url.pathname === "/widget.php";
  } catch (_error) {
    return false;
  }
}

async function maximizeKioskTab(tab) {
  if (!isTrustedOpener(tab)) {
    return;
  }

  try {
    await chrome.windows.update(tab.windowId, {
      state: "maximized",
      focused: true,
    });
  } catch (error) {
    console.error("Unable to maximize Crossjack kiosk window", error);
  }
}

async function placeExternalTab(tab) {
  if (!tab.id || tab.openerTabId === undefined || handledTabs.has(tab.id)) {
    return;
  }

  let opener;
  try {
    opener = await chrome.tabs.get(tab.openerTabId);
  } catch (_error) {
    return;
  }

  if (!isTrustedOpener(opener)) {
    return;
  }

  handledTabs.add(tab.id);
  kioskOwners.set(tab.id, opener.id);
  try {
    const childWindow = await chrome.windows.get(tab.windowId);
    if (childWindow.type !== "popup") {
      const popup = await chrome.windows.create({
        tabId: tab.id,
        type: "popup",
        focused: true,
        ...CHILD_BOUNDS,
      });
      if (popup.id !== undefined) {
        externalWindowIds.add(popup.id);
      }
      return;
    }

    externalWindowIds.add(tab.windowId);
    await chrome.windows.update(tab.windowId, {
      state: "normal",
      focused: true,
      ...CHILD_BOUNDS,
    });
  } catch (error) {
    console.error("Unable to place Crossjack external window", error);
  }
}

chrome.tabs.onCreated.addListener((tab) => {
  setTimeout(() => placeExternalTab(tab), 150);
});

chrome.tabs.onUpdated.addListener((_tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.status === "complete") {
    maximizeKioskTab(tab);
  }
});

chrome.tabs.query({}).then((tabs) => {
  tabs.forEach((tab) => maximizeKioskTab(tab));
});

chrome.webNavigation.onCommitted.addListener(async (details) => {
  if (
    details.frameId === 0 ||
    isKioskUrl(details.url) ||
    isEmbeddedDashboardWidget(details.url)
  ) {
    return;
  }

  try {
    const tab = await chrome.tabs.get(details.tabId);
    if (isWeatherTidesDashboard(tab)) {
      return;
    }

    const target = { tabId: details.tabId, frameIds: [details.frameId] };

    if (details.url.startsWith("https://www.youtube.com/embed/")) {
      await chrome.scripting.insertCSS({
        target,
        files: ["youtube-controls.css"],
      });
      await chrome.scripting.executeScript({
        target,
        files: ["youtube-controls.js"],
      });
      return;
    }

    // External place websites replace My Holiday Guide's direct iframe.
    // Do not add this control to deeper widgets embedded by those sites.
    if (details.parentFrameId !== 0) {
      return;
    }

    await chrome.scripting.insertCSS({
      target,
      files: ["close-control.css"],
    });
    await chrome.scripting.executeScript({
      target,
      files: ["close-control.js"],
    });
  } catch (error) {
    console.error("Unable to add return control to external frame", error);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  handledTabs.delete(tabId);
  kioskOwners.delete(tabId);
});

chrome.windows.onRemoved.addListener((windowId) => {
  externalWindowIds.delete(windowId);
});

function isExternalPage(tab) {
  return Boolean(tab) && !isTrustedOpener(tab);
}

async function kioskOwnerForTab(tab) {
  if (!tab?.id) {
    return undefined;
  }
  if (isTrustedOpener(tab)) {
    return tab.id;
  }

  const knownOwner = kioskOwners.get(tab.id);
  if (knownOwner !== undefined) {
    return knownOwner;
  }

  if (tab.openerTabId === undefined) {
    return undefined;
  }

  try {
    const opener = await chrome.tabs.get(tab.openerTabId);
    if (isTrustedOpener(opener)) {
      kioskOwners.set(tab.id, opener.id);
      return opener.id;
    }
  } catch (_error) {
    return undefined;
  }
  return undefined;
}

async function closeExternalWindows(mainWindowId) {
  const windowIds = Array.from(externalWindowIds);
  await Promise.allSettled(
    windowIds
      .filter((windowId) => windowId !== mainWindowId)
      .map((windowId) => chrome.windows.remove(windowId)),
  );
  externalWindowIds.clear();
  handledTabs.clear();
  kioskOwners.clear();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !sender.tab) {
    return false;
  }

  if (message.type === "crossjack-kiosk-activity") {
    kioskOwnerForTab(sender.tab).then(async (ownerTabId) => {
      if (ownerTabId !== undefined && ownerTabId !== sender.tab.id) {
        await chrome.tabs
          .sendMessage(ownerTabId, { type: "crossjack-attract-activity" })
          .catch(() => {});
      }
      sendResponse({ reported: ownerTabId !== undefined });
    });
    return true;
  }

  if (message.type === "crossjack-attract-start") {
    kioskOwnerForTab(sender.tab).then(async (ownerTabId) => {
      if (ownerTabId !== sender.tab.id) {
        sendResponse({ reset: false });
        return;
      }

      await closeExternalWindows(sender.tab.windowId);
      await chrome.windows
        .update(sender.tab.windowId, { state: "maximized", focused: true })
        .catch(() => {});
      sendResponse({ reset: true });
    });
    return true;
  }

  if (message.type === "crossjack-open-map") {
    const query = String(message.query || "").trim();
    if (!isTrustedOpener(sender.tab) || !query) {
      sendResponse({ opened: false });
      return false;
    }

    const url =
      "https://www.google.com/maps/search/?api=1&query=" +
      encodeURIComponent(query);

    chrome.windows
      .create({
        url,
        type: "popup",
        focused: true,
        ...CHILD_BOUNDS,
      })
      .then((popup) => {
        if (popup.id !== undefined) {
          externalWindowIds.add(popup.id);
        }
        const popupTab = popup.tabs?.[0];
        if (popupTab?.id !== undefined && sender.tab.id !== undefined) {
          kioskOwners.set(popupTab.id, sender.tab.id);
        }
        sendResponse({ opened: true });
      })
      .catch((error) => {
        console.error("Unable to open Google Maps place", error);
        sendResponse({ opened: false });
      });

    return true;
  }

  if (message.type !== "crossjack-close-control") {
    return false;
  }

  Promise.resolve(isExternalPage(sender.tab)).then(async (allowed) => {
    if (allowed && message.action === "close") {
      await chrome.windows.remove(sender.tab.windowId);
    }
    sendResponse({ allowed });
  });

  return true;
});
