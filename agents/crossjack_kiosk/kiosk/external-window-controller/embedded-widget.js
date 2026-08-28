const removeCrossjackControl = () => {
  document.getElementById("crossjack-kiosk-close-control")?.remove();
};

removeCrossjackControl();

new MutationObserver(removeCrossjackControl).observe(document, {
  childList: true,
  subtree: true,
});
