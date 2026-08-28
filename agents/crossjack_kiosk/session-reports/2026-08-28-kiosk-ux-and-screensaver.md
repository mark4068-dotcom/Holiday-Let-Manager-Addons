# Crossjack kiosk UX and screensaver session — 28 August 2026

## Outcome

The guest kiosk now has consistent touch navigation, controlled handling of
external content and a branded idle screen. The tested live deployment uses
kiosk agent `1.0.8` and external-window controller `1.0.19`.

## Completed work

- Standardised the five dashboard navigation buttons, including larger text,
  rounded corners, active-page colouring and consistent vertical placement.
- Made the Digital House Guide fill the available kiosk area without its former
  narrow iframe or unwanted scrollbars.
- Opened external websites, PDFs and maps without an address bar and supplied a
  prominent **Close & return** control.
- Corrected Holiday Guide website and Google Maps links, including links opened
  from the Events & places route.
- Added embedded YouTube volume controls, preserved a 16:9 player and stopped
  playback when the guest leaves the guide page.
- Prevented the external close control from appearing inside the embedded
  SwimSafe weather widget.
- Added a 15-minute Sailcottages attract screen showing the property welcome,
  live time/date and “Touch to explore your property guide and local
  information”. The first touch dismisses the overlay without passing through.
- Added an MQTT-discovered **Activate screensaver** button to HLM Operations for
  testing the attract-screen path on demand.

## Screensaver implementation

The extension records activity only in the top-level Crossjack guest dashboard.
On timeout it closes tracked external windows, stops media, returns to the
Welcome route and displays the attract screen. The Operations test command
creates `/run/user/<uid>/crossjack-attract-once` and restarts Chromium; the
launcher consumes the marker once and appends `crossjack_attract=1`.

The Sailcottages vector was cropped to its visible artwork before display. This
keeps the enlarged logo while leaving room for the welcome, clock, date and
touch prompt on the 1920×1080 panel.

## Live verification

- Controller `1.0.19` loaded after Chromium restart.
- Automatic overlay and Operations test button both activate the screensaver.
- First-touch wake returns to Welcome and does not activate content beneath it.
- Enlarged logo and the complete touch prompt fit on the panel.

## Backup

A dated configuration archive and SHA-256 sidecar were captured after this
checkpoint. The archive contains the launcher, agent, extension source and CRX,
Chromium policy/descriptor, Labwc/display settings and system inventory. MQTT
credentials and the extension signing private key are not committed to Git.

## Next session

Begin the content and layout design for the guest dashboard Home/Welcome tab.
