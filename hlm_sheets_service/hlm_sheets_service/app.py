"""Authenticated HTTP endpoint for the private HLM status feed."""

from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import Settings
from .google_sheets import GoogleSheetsSource
from .status import ContractError, build_status_payload


def make_server(settings: Settings) -> ThreadingHTTPServer:
    source = GoogleSheetsSource(
        settings.spreadsheet_id, settings.sheet_range, settings.credentials_path
    )

    class Handler(BaseHTTPRequestHandler):
        server_version = "HLMPrivateSheets/1.0"

        def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._json(HTTPStatus.OK, {"status": "ok"})
                return
            if self.path != "/api/v1/status":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), f"Bearer {settings.api_token}"
            ):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = build_status_payload(source.read_rows())
            except ContractError as error:
                self._json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "availability": "unavailable",
                        "error": "invalid_contract",
                        "detail": str(error),
                    },
                )
                return
            except Exception:
                self._json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"availability": "unavailable", "error": "source_unavailable"},
                )
                return
            self._json(HTTPStatus.OK, payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer((settings.host, settings.port), Handler)


def main() -> None:
    settings = Settings.from_env()
    source = GoogleSheetsSource(
        settings.spreadsheet_id, settings.sheet_range, settings.credentials_path
    )
    try:
        payload = build_status_payload(source.read_rows())
    except ContractError as error:
        print(f"ERROR: Published status contract check failed: {error}", flush=True)
        raise SystemExit(1) from error
    except Exception as error:
        print(
            "ERROR: Unable to read the private Google Sheets status feed: "
            f"{type(error).__name__}",
            flush=True,
        )
        raise SystemExit(1) from error

    property_ids = ", ".join(sorted(payload["properties"]))
    print(
        "INFO: Private Google Sheets status feed verified "
        f"({payload['property_count']} properties: {property_ids}).",
        flush=True,
    )
    make_server(settings).serve_forever()


if __name__ == "__main__":
    main()
