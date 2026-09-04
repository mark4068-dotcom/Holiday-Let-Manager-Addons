"""HTTP service for the HLM iCalendar Aggregator Home Assistant app."""

from __future__ import annotations

import base64
import hmac
import html
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from aggregator import Aggregator, parse_sources
from publisher import GoogleCalendarPublisher, PublicationConfig

OPTIONS_PATH = Path(os.environ.get("OPTIONS_PATH", "/data/options.json"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data/hlm-ical-aggregator"))
PORT = int(os.environ.get("PORT", "8789"))


def load_options() -> dict:
    defaults = {
        "refresh_minutes": 15,
        "feed_username": "",
        "feed_password": "",
        "sources": [],
        "google_publish_enabled": False,
        "google_calendar_id": "",
        "google_credentials_path": "/config/google-service-account.json",
        "google_dry_run": True,
        "google_title_mode": "retain_details",
        "google_default_timezone": "Europe/London",
        "google_retry_count": 4,
        "google_allow_empty_publish": False,
    }
    try:
        loaded = json.loads(OPTIONS_PATH.read_text())
    except FileNotFoundError:
        return defaults
    if not isinstance(loaded, dict):
        raise ValueError("app options must be a JSON object")
    return {**defaults, **loaded}


OPTIONS = load_options()
SOURCES = parse_sources(OPTIONS.get("sources", []))
AGGREGATOR = Aggregator(DATA_DIR, SOURCES)
PUBLISHER = GoogleCalendarPublisher(PublicationConfig.from_options(OPTIONS))


def service_snapshot() -> dict:
    snapshot = AGGREGATOR.snapshot()
    snapshot["publication"] = PUBLISHER.snapshot()
    return snapshot


def authorised(headers) -> bool:
    username = str(OPTIONS.get("feed_username", ""))
    password = str(OPTIONS.get("feed_password", ""))
    if not username and not password:
        return True
    try:
        scheme, encoded = headers.get("Authorization", "").split(" ", 1)
        supplied = base64.b64decode(encoded, validate=True).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    return scheme == "Basic" and hmac.compare_digest(supplied, f"{username}:{password}")


def refresh_in_background() -> None:
    def refresh_and_publish() -> None:
        AGGREGATOR.refresh()
        if AGGREGATOR.combined_path.exists():
            PUBLISHER.publish(AGGREGATOR.combined_path.read_bytes())

    threading.Thread(target=refresh_and_publish, name="calendar-refresh", daemon=True).start()


def status_page(snapshot: dict) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(source['name'])}</td>"
        f"<td>{'yes' if source['enabled'] else 'no'}</td>"
        f"<td>{source['source_events']}</td>"
        f"<td>{source['accepted_events']}</td>"
        f"<td>{source['excluded_events'] + source['cancelled_events']}</td>"
        f"<td>{html.escape(source['last_success_at'] or 'not yet')}</td>"
        f"<td>{html.escape(source['error'] or '')}</td>"
        "</tr>"
        for source in snapshot["sources"]
    )
    publication = snapshot["publication"]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>HLM Calendars</title><style>
body{{font:15px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1d2a36}}
table{{border-collapse:collapse;width:100%}}
th,td{{padding:.55rem;border-bottom:1px solid #d8e0e7;text-align:left}}
code{{background:#eef2f5;padding:.15rem .3rem}}button{{padding:.6rem 1rem}}
</style></head><body><h1>HLM iCalendar Aggregator</h1>
<p>State: <strong>{html.escape(snapshot["state"])}</strong>; accepted events:
{snapshot["accepted_event_count"]}; last refresh:
{html.escape(snapshot["last_refresh_at"] or "not yet")}.</p>
<p>Combined feed: <code>/combined.ics</code></p>
<form method="post" action="refresh"><button>Refresh now</button></form>
<h2>Google publication</h2><p>State: <strong>{html.escape(publication["state"])}</strong>;
desired: {publication["desired_events"]}; create: {publication["created_events"]};
update: {publication["updated_events"]}; delete: {publication["deleted_events"]};
error: {html.escape(publication["error"] or "none")}.</p>
<h2>Sources</h2><table><thead><tr><th>Name</th><th>Enabled</th><th>Input</th>
<th>Accepted</th><th>Removed</th><th>Last success</th><th>Error</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "HLMCalendarAggregator/0.1"

    def log_message(self, format_string: str, *args) -> None:
        print(f"{self.address_string()} - {format_string % args}", flush=True)

    def send_body(
        self,
        status: int,
        content_type: str,
        body: bytes,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def require_auth(self) -> bool:
        if authorised(self.headers):
            return True
        self.send_body(
            401,
            "text/plain; charset=utf-8",
            b"Authentication required\n",
            {"WWW-Authenticate": 'Basic realm="HLM Calendars"'},
        )
        return False

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        snapshot = service_snapshot()
        if path == "/health":
            status = 200 if snapshot["state"] == "setup" or snapshot["combined_available"] else 503
            return self.send_body(status, "application/json", json.dumps(snapshot).encode())
        if path == "/api/v1/status":
            return self.send_body(200, "application/json", json.dumps(snapshot).encode())
        if path in {"/", ""} or path.endswith("/"):
            return self.send_body(200, "text/html; charset=utf-8", status_page(snapshot).encode())
        if path == "/combined.ics":
            if not self.require_auth():
                return
            return self._send_calendar(AGGREGATOR.combined_path)
        if path.startswith("/sources/") and path.endswith(".ics"):
            if not self.require_auth():
                return
            source_id = path.removeprefix("/sources/").removesuffix(".ics")
            if source_id not in AGGREGATOR.statuses:
                return self.send_body(404, "text/plain", b"Unknown source\n")
            return self._send_calendar(AGGREGATOR.source_path(source_id))
        return self.send_body(404, "text/plain", b"Not found\n")

    def _send_calendar(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self.send_body(503, "text/plain", b"Calendar not available\n")
        self.send_body(200, "text/calendar; charset=utf-8", body)

    def do_POST(self) -> None:
        if urlsplit(self.path).path.rstrip("/") != "/refresh":
            return self.send_body(404, "text/plain", b"Not found\n")
        if not self.require_auth():
            return
        refresh_in_background()
        self.send_response(303)
        self.send_header("Location", "./")
        self.end_headers()


def refresh_loop() -> None:
    refresh_in_background()
    interval = int(OPTIONS.get("refresh_minutes", 15)) * 60
    while True:
        time.sleep(interval)
        refresh_in_background()


if __name__ == "__main__":
    threading.Thread(target=refresh_loop, name="refresh-loop", daemon=True).start()
    print(f"HLM iCalendar Aggregator listening on port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
