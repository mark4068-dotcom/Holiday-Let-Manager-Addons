# HLM Crossjack kiosk agent

Companion monitoring and control agent for the Crossjack Raspberry Pi kiosk.
It publishes Home Assistant MQTT Discovery entities and accepts only a fixed
allowlist of remote commands.

This is deliberately a companion Pi application, not a Home Assistant add-on:
Home Assistant Supervisor cannot install or update software on a separate Pi.
The official Mosquitto Broker add-on provides MQTT on the Home Assistant server;
this agent runs under the `kioskadmin` user on the kiosk.

## Reported health

- online/last-seen state;
- CPU temperature, load, memory and disk use;
- undervoltage and throttling flags;
- Chromium kiosk, HDMI display and touchscreen state;
- Tailscale state and address;
- uptime and pending package updates.

## Remote controls

- refresh the current dashboard;
- activate the guest screensaver for testing;
- restart Chromium;
- screen on/off;
- show/hide the on-screen keyboard;
- immediate health report;
- reboot the Pi.

There is no arbitrary shell-command topic. Unknown payloads are rejected and
reported back through MQTT.

## Secrets

The live file `/home/kioskadmin/.config/hlm-kiosk-agent.json` contains the
dedicated MQTT password and is deliberately not stored in Git. Start from
`config.example.json` and set its mode to `0600`.

## Installation/update

Run `install.sh` as `kioskadmin`. The script installs the pinned Python
dependencies into a private virtual environment and enables the user service
only when the live configuration file already exists.

The optional reboot command requires the root-owned sudoers rule in
`../hardening/hlm-kiosk-reboot-sudoers`; install and validate that rule manually
with `visudo` during commissioning.

The user service intentionally avoids systemd filesystem namespace directives.
For a per-user service those directives remap host root ownership to `nobody`,
which prevents the setuid `sudo` executable from validating itself. Security is
instead enforced by the unprivileged account, the fixed MQTT command allowlist,
the absence of an arbitrary shell interface and the exact reboot-only sudoers
rule.

The repository also contains:

- `kiosk/crossjack-kiosk`, the locked-down Chromium launcher with a local-only
  DevTools endpoint used for dashboard refresh, automatic `wvkbd` startup and
  a direct Chromium launch so Raspberry Pi OS cannot discard the local
  external-window extension. The launcher also opts out of Chromium's
  command-line extension block for this one trusted, local extension;
- `kiosk/labwc-rc.xml`, which removes the maximized title bar while allowing
  the keyboard to reserve display space and gives external child windows a
  large Close-only titlebar;
- `kiosk/external-window-controller/`, a local Manifest V3 extension that
  keeps links opened by the guest dashboard or guide in a centred 1600 x 900
  popup without an address bar;
- `kiosk/chromium-policy.json`, the managed kiosk policy. It continues to
  block every other extension while allowlisting the signed controller's
  fixed ID;
- `home_assistant/operations_view.json`, the HLM Operations dashboard view;
- `hardening/hlm-kiosk-reboot-sudoers`, the narrow reboot-only privilege rule.

## Home Assistant setup

1. Install the official Mosquitto Broker add-on and create a dedicated MQTT
   login for the kiosk.
2. Add the discovered MQTT integration in **Settings > Devices & services**.
3. Start the Pi agent. Home Assistant creates the Crossjack Guest Kiosk device
   and its sensors/buttons through MQTT Discovery.
4. Add `home_assistant/operations_view.json` to the HLM Operations dashboard.

The dashboard exposes health, diagnostics and fixed controls for refresh,
screensaver activation, browser restart, screen on/off, health report and
reboot. Destructive controls include Home Assistant confirmation prompts.

## HDMI display without EDID

The Waveshare panel may expose an empty EDID and therefore fall back to
1024x768. With the panel on HDMI0 (`HDMI-A-1`), append the following setting to
the single line in `/boot/firmware/cmdline.txt`, then reboot:

```text
video=HDMI-A-1:1920x1080M@60
```

The launcher starts `wvkbd` hidden and runs Chromium as a borderless maximized
application. This avoids Chromium fullscreen covering the keyboard's reserved
screen area. Install `kiosk/labwc-rc.xml` as
`/home/kioskadmin/.config/labwc/rc.xml`. Use the Operations dashboard buttons
to show or hide the keyboard. The launcher caches Kiosk Mode parameters that
hide the sidebar and Home Assistant header. The Crossjack dashboard's labelled,
touch-friendly navigation strip replaces the former icon-only view tabs. These
settings apply only to this Pi's browser and do not change the experience in
admin browsers.

Package `kiosk/external-window-controller/` as a signed CRX, retaining the same
private key for each release. Install the CRX as
`/usr/local/share/crossjack-kiosk/external-window-controller.crx` and install
its `external-extension.json` descriptor under `/usr/share/chromium/extensions/`
using the signed extension ID as the filename.
Install `kiosk/chromium-policy.json` as
`/etc/chromium/policies/managed/crossjack-kiosk.json`.
When the dashboard or Digital Holiday Guide opens Google Maps, a website or a
PDF in a new tab/window, the extension moves it into a centred child popup. The
popup has no browser address bar, and Labwc supplies a large Close button. On
close, the unchanged Home Assistant kiosk is immediately visible underneath.

After 15 minutes without touch or pointer activity, the extension displays a
Sailcottages attract screen with the current date and time and the prompt
“Touch to explore your property guide and local information”. The first touch
dismisses the screen, returns to the Welcome page and is swallowed so it cannot
activate a dashboard control underneath. Starting the attract screen also
closes tracked external windows and stops embedded media. The Operations
dashboard button uses a one-shot launcher marker to exercise the same behaviour
on demand.
