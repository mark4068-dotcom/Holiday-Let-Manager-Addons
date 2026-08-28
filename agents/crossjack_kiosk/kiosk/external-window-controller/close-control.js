const CONTROL_ID = "crossjack-kiosk-close-control";

function isKioskPage() {
  const isGuestDashboard =
    location.pathname === "/crossjack-guest" ||
    location.pathname.startsWith("/crossjack-guest/");
  const isDigitalGuide =
    location.hostname === "myholidayguide.app" &&
    location.pathname.startsWith("/property/");
  return isGuestDashboard || isDigitalGuide;
}

function isEmbeddedDashboardWidget() {
  return location.hostname === "swimsafeuk.com" && location.pathname === "/widget.php";
}

function addCloseControl() {
  if (document.getElementById(CONTROL_ID)) {
    return;
  }

  const button = document.createElement("button");
  button.id = CONTROL_ID;
  button.type = "button";
  button.setAttribute("aria-label", "Close this page and return to the guest guide");
  button.innerHTML = '<span aria-hidden="true">&#10005;</span> Close &amp; return';
  button.addEventListener("click", () => {
    button.disabled = true;

    // Some My Holiday Guide links navigate its embedded frame rather than
    // opening a child window. Return that frame to its previous guide page.
    if (window.top !== window) {
      history.back();
      return;
    }

    chrome.runtime.sendMessage({
      type: "crossjack-close-control",
      action: "close",
    });
  });
  document.documentElement.appendChild(button);
}

if (isEmbeddedDashboardWidget()) {
  document.getElementById(CONTROL_ID)?.remove();
} else if (!isKioskPage()) {
  if (window.top !== window) {
    addCloseControl();
  } else {
    chrome.runtime.sendMessage(
      { type: "crossjack-close-control", action: "query" },
      (response) => {
        if (response?.allowed) {
          addCloseControl();
        }
      },
    );
  }
}
