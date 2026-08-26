#!/usr/bin/env python3
"""HLM kiosk telemetry and tightly allowlisted remote controls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.request import urlopen

import paho.mqtt.client as mqtt
import websocket


VERSION = "1.0.3"
CONFIG_PATH = Path.home() / ".config" / "hlm-kiosk-agent.json"
DEVICE_ID = "crossjack_kiosk_pi"
BASE_TOPIC = "hlm/kiosks/crossjack"
STATE_TOPIC = f"{BASE_TOPIC}/state"
AVAILABILITY_TOPIC = f"{BASE_TOPIC}/availability"
COMMAND_TOPIC = f"{BASE_TOPIC}/command"
RESULT_TOPIC = f"{BASE_TOPIC}/command_result"
DISCOVERY_PREFIX = "homeassistant"


def run(command: list[str], timeout: float = 8.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def cpu_temperature() -> float | None:
    code, output = run(["/usr/bin/vcgencmd", "measure_temp"])
    if code == 0 and "=" in output:
        try:
            return round(float(output.split("=", 1)[1].split("'", 1)[0]), 1)
        except ValueError:
            pass
    try:
        return round(
            int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip())
            / 1000,
            1,
        )
    except (OSError, ValueError):
        return None


def throttling() -> tuple[str, int]:
    code, output = run(["/usr/bin/vcgencmd", "get_throttled"])
    if code != 0 or "=" not in output:
        return "unknown", 0
    raw = output.split("=", 1)[1].strip()
    try:
        value = int(raw, 16)
    except ValueError:
        return raw, 0
    return raw, value


def memory_used_percent() -> float | None:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
        total = values["MemTotal"]
        available = values["MemAvailable"]
        return round((total - available) * 100 / total, 1)
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return None


def process_running(fragment: str) -> bool:
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if fragment in path.read_bytes().replace(b"\0", b" ").decode(errors="ignore"):
                return True
        except OSError:
            continue
    return False


def display_connected() -> bool:
    statuses = list(Path("/sys/class/drm").glob("*/status"))
    for path in statuses:
        try:
            if "HDMI" in str(path).upper() and path.read_text().strip() == "connected":
                return True
        except OSError:
            continue
    return False


def touch_connected() -> bool:
    try:
        text = Path("/proc/bus/input/devices").read_text().lower()
    except OSError:
        return False
    return any(
        term in text
        for term in ("touchscreen", "waveshare", "touch screen", "ilitek", "multi-touch")
    )


def tailscale_status() -> tuple[bool, str | None]:
    code, output = run(["/usr/bin/tailscale", "status", "--json"])
    if code != 0:
        return False, None
    try:
        data = json.loads(output)
        addresses = data.get("Self", {}).get("TailscaleIPs", [])
        ipv4 = next((item for item in addresses if ":" not in item), None)
        return data.get("BackendState") == "Running", ipv4
    except json.JSONDecodeError:
        return False, None


def local_ip_address() -> str | None:
    """Return the IPv4 source address selected by the Pi's default route."""
    code, output = run(["/usr/bin/ip", "-4", "route", "get", "1.1.1.1"])
    if code != 0:
        return None
    fields = output.split()
    try:
        return fields[fields.index("src") + 1]
    except (ValueError, IndexError):
        return None


def pending_updates() -> int | None:
    code, output = run(["/usr/bin/apt", "list", "--upgradable"], timeout=30)
    if code not in (0, 100):
        return None
    return sum(1 for line in output.splitlines() if "/" in line and not line.startswith("Listing"))


def metrics(update_count: int | None) -> dict[str, object]:
    disk = shutil.disk_usage("/")
    throttle_hex, throttle_value = throttling()
    tailscale_ok, tailscale_ip = tailscale_status()
    try:
        uptime = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        uptime = 0
    warnings = []
    if throttle_value & 0x1:
        warnings.append("undervoltage_now")
    if throttle_value & 0x4:
        warnings.append("throttled_now")
    if throttle_value & 0x8:
        warnings.append("temperature_limit_now")
    if throttle_value & 0x10000:
        warnings.append("undervoltage_occurred")
    if throttle_value & 0x40000:
        warnings.append("throttling_occurred")
    if throttle_value & 0x80000:
        warnings.append("temperature_limit_occurred")
    return {
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "agent_version": VERSION,
        "cpu_temperature": cpu_temperature(),
        "memory_used_percent": memory_used_percent(),
        "disk_used_percent": round(disk.used * 100 / disk.total, 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "uptime_seconds": uptime,
        "load_1m": round(os.getloadavg()[0], 2),
        "browser_running": process_running("chromium-crossjack"),
        "display_connected": display_connected(),
        "touch_connected": touch_connected(),
        "tailscale_connected": tailscale_ok,
        "tailscale_ip": tailscale_ip,
        "local_ip": local_ip_address(),
        "throttled_raw": throttle_hex,
        "hardware_warning": bool(warnings),
        "hardware_warnings": warnings,
        "pending_updates": update_count,
    }


def device() -> dict[str, object]:
    return {
        "identifiers": [DEVICE_ID],
        "name": "Crossjack Guest Kiosk",
        "manufacturer": "Holiday Let Manager",
        "model": "Raspberry Pi 5 kiosk",
        "sw_version": VERSION,
    }


def discovery_messages() -> list[tuple[str, dict[str, object]]]:
    common = {
        "state_topic": STATE_TOPIC,
        "availability_topic": AVAILABILITY_TOPIC,
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": device(),
    }
    sensors = [
        ("cpu_temperature", "CPU temperature", "°C", "temperature", "mdi:thermometer"),
        ("memory_used_percent", "Memory used", "%", None, "mdi:memory"),
        ("disk_used_percent", "Disk used", "%", None, "mdi:harddisk"),
        ("disk_free_gb", "Disk free", "GB", None, "mdi:harddisk"),
        ("uptime_seconds", "Uptime", "s", "duration", "mdi:timer-outline"),
        ("load_1m", "CPU load 1 minute", None, None, "mdi:speedometer"),
        ("pending_updates", "Pending updates", None, None, "mdi:package-up"),
        ("last_seen", "Last seen", None, "timestamp", "mdi:clock-check-outline"),
        ("local_ip", "Local IP address", None, None, "mdi:lan"),
        ("tailscale_ip", "Tailscale IP", None, None, "mdi:vpn"),
        ("throttled_raw", "Throttling flags", None, None, "mdi:alert-circle-outline"),
        ("last_command", "Last command", None, None, "mdi:console"),
        ("last_command_result", "Last command result", None, None, "mdi:check-circle-outline"),
    ]
    messages: list[tuple[str, dict[str, object]]] = []
    for key, name, unit, device_class, icon in sensors:
        payload = {
            **common,
            "name": name,
            "unique_id": f"{DEVICE_ID}_{key}",
            "object_id": f"crossjack_kiosk_{key}",
            "value_template": "{{ value_json.%s }}" % key,
            "icon": icon,
            "entity_category": "diagnostic",
        }
        if unit:
            payload["unit_of_measurement"] = unit
        if device_class:
            payload["device_class"] = device_class
        messages.append((f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/{key}/config", payload))

    binary_sensors = [
        ("browser_running", "Kiosk browser", "connectivity", "mdi:web"),
        ("display_connected", "Display connected", "connectivity", "mdi:monitor"),
        ("touch_connected", "Touchscreen connected", "connectivity", "mdi:gesture-tap"),
        ("tailscale_connected", "Tailscale connected", "connectivity", "mdi:vpn"),
        ("hardware_warning", "Hardware warning", "problem", "mdi:alert"),
    ]
    for key, name, device_class, icon in binary_sensors:
        payload = {
            **common,
            "name": name,
            "unique_id": f"{DEVICE_ID}_{key}",
            "object_id": f"crossjack_kiosk_{key}",
            "value_template": "{{ 'ON' if value_json.%s else 'OFF' }}" % key,
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": device_class,
            "icon": icon,
            "entity_category": "diagnostic",
        }
        messages.append((f"{DISCOVERY_PREFIX}/binary_sensor/{DEVICE_ID}/{key}/config", payload))

    online = {
        "name": "Online",
        "unique_id": f"{DEVICE_ID}_online",
        "object_id": "crossjack_kiosk_online",
        "state_topic": AVAILABILITY_TOPIC,
        "payload_on": "online",
        "payload_off": "offline",
        "device_class": "connectivity",
        "device": device(),
    }
    messages.append((f"{DISCOVERY_PREFIX}/binary_sensor/{DEVICE_ID}/online/config", online))

    buttons = [
        ("refresh_dashboard", "Refresh dashboard", "mdi:refresh"),
        ("restart_browser", "Restart kiosk browser", "mdi:web-refresh"),
        ("screen_on", "Screen on", "mdi:monitor"),
        ("screen_off", "Screen off", "mdi:monitor-off"),
        ("health_report", "Run health report", "mdi:heart-pulse"),
        ("reboot", "Reboot Pi", "mdi:restart-alert"),
    ]
    for command, name, icon in buttons:
        payload = {
            "name": name,
            "unique_id": f"{DEVICE_ID}_{command}",
            "object_id": f"crossjack_kiosk_{command}",
            "command_topic": COMMAND_TOPIC,
            "payload_press": command,
            "availability_topic": AVAILABILITY_TOPIC,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": device(),
            "icon": icon,
        }
        messages.append((f"{DISCOVERY_PREFIX}/button/{DEVICE_ID}/{command}/config", payload))
    return messages


class Agent:
    def __init__(self, config: dict[str, object]) -> None:
        self.config = config
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=str(config.get("client_id", DEVICE_ID)),
            protocol=mqtt.MQTTv311,
        )
        self.client.username_pw_set(str(config["username"]), str(config["password"]))
        self.client.will_set(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.update_count: int | None = None
        self.last_update_check = 0.0
        self.last_command = "none"
        self.last_command_result = "No command received"

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            return
        for topic, payload in discovery_messages():
            client.publish(topic, json.dumps(payload), qos=1, retain=True)
        client.subscribe(COMMAND_TOPIC, qos=1)
        client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)
        self.publish_state(force_update_check=True)

    def on_message(self, client, userdata, message) -> None:
        try:
            command = message.payload.decode("utf-8").strip()
        except UnicodeDecodeError:
            return
        threading.Thread(target=self.execute_command, args=(command,), daemon=True).start()

    def publish_state(self, force_update_check: bool = False) -> None:
        now = time.monotonic()
        if force_update_check or now - self.last_update_check > 21600:
            self.update_count = pending_updates()
            self.last_update_check = now
        payload = metrics(self.update_count)
        payload["last_command"] = self.last_command
        payload["last_command_result"] = self.last_command_result
        self.client.publish(STATE_TOPIC, json.dumps(payload), qos=1, retain=True)

    def publish_result(self, command: str, success: bool, detail: str) -> None:
        self.last_command = command
        self.last_command_result = ("Success: " if success else "Failed: ") + detail
        payload = {
            "command": command,
            "success": success,
            "detail": detail,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.client.publish(RESULT_TOPIC, json.dumps(payload), qos=1, retain=True)
        self.publish_state()

    @staticmethod
    def wayland_environment() -> dict[str, str]:
        env = os.environ.copy()
        runtime = Path(f"/run/user/{os.getuid()}")
        env["XDG_RUNTIME_DIR"] = str(runtime)
        sockets = sorted(runtime.glob("wayland-*"))
        if sockets:
            env["WAYLAND_DISPLAY"] = sockets[0].name
        return env

    def refresh_dashboard(self) -> tuple[bool, str]:
        try:
            with urlopen("http://127.0.0.1:9222/json/list", timeout=3) as response:
                pages = json.load(response)
            target = next((page for page in pages if page.get("type") == "page"), None)
            if not target or not target.get("webSocketDebuggerUrl"):
                return False, "Chromium page not found"
            ws = websocket.create_connection(
                target["webSocketDebuggerUrl"], timeout=4, suppress_origin=True
            )
            ws.send(json.dumps({"id": 1, "method": "Page.reload", "params": {"ignoreCache": True}}))
            ws.close()
            return True, "Dashboard refresh requested"
        except Exception as exc:  # Network and WebSocket errors vary by release.
            return False, str(exc)

    def execute_command(self, command: str) -> None:
        if command == "health_report":
            self.publish_result(command, True, "Health report published")
            return
        if command == "refresh_dashboard":
            success, detail = self.refresh_dashboard()
            self.publish_result(command, success, detail)
            return
        if command == "restart_browser":
            code, output = run(["/usr/bin/pkill", "-TERM", "chromium"], timeout=5)
            self.publish_result(command, code == 0, output or "Browser restart requested")
            return
        if command in {"screen_on", "screen_off"}:
            mode = "--on" if command == "screen_on" else "--off"
            try:
                proc = subprocess.run(
                    ["/usr/bin/wlopm", mode, "*"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                    env=self.wayland_environment(),
                )
                self.publish_result(
                    command,
                    proc.returncode == 0,
                    (proc.stdout or proc.stderr).strip() or f"{command} requested",
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                self.publish_result(command, False, str(exc))
            return
        if command == "reboot":
            self.publish_result(command, True, "Reboot command accepted")
            time.sleep(1)
            code, output = run(
                ["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "reboot"],
                timeout=15,
            )
            if code != 0:
                self.publish_result(
                    command,
                    False,
                    output or f"systemctl reboot exited with status {code}",
                )
            return
        self.publish_result(command, False, "Command is not allowlisted")

    def run_forever(self) -> None:
        self.client.connect(
            str(self.config["broker_host"]),
            int(self.config.get("broker_port", 1883)),
            keepalive=60,
        )
        self.client.loop_start()
        interval = max(60, int(self.config.get("interval_seconds", 300)))
        try:
            while True:
                self.publish_state()
                time.sleep(interval)
        finally:
            self.client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
            self.client.disconnect()
            self.client.loop_stop()


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    Agent(config).run_forever()


if __name__ == "__main__":
    main()
