"""Authenticated HTTP endpoint for the private HLM status feed."""

from __future__ import annotations

import hmac
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import Settings
from .events import EventContractError, rows_for_events, validate_batch
from .google_sheets import GoogleSheetsEventWriter, GoogleSheetsSource
from .status import ContractError, build_status_payload, build_v1_1_status_payload


def append_events_idempotently(
    writer: GoogleSheetsEventWriter, events: list[dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Append each event ID once and recover an ambiguous successful append."""
    existing = writer.existing_event_ids()
    known = set(existing)
    unseen = []
    duplicate_ids = []
    for event in events:
        event_id = event["event_id"]
        if event_id in known:
            duplicate_ids.append(event_id)
            continue
        known.add(event_id)
        unseen.append(event)

    accepted_ids = [event["event_id"] for event in unseen]
    try:
        writer.append_rows(rows_for_events(unseen))
    except Exception:
        # Google can commit an append while its response is lost. Re-read the
        # immutable IDs before allowing the caller to retry the batch.
        after_failure = writer.existing_event_ids()
        if not set(accepted_ids).issubset(after_failure):
            raise
    return accepted_ids, duplicate_ids


def make_server(settings: Settings) -> ThreadingHTTPServer:
    v1_source = GoogleSheetsSource(
        settings.spreadsheet_id, settings.sheet_range, settings.credentials_path
    )
    v1_1_source = GoogleSheetsSource(
        settings.spreadsheet_id, settings.v1_1_sheet_range, settings.credentials_path
    )
    writer = (
        GoogleSheetsEventWriter(
            settings.spreadsheet_id,
            settings.event_sheet_range,
            settings.writer_credentials_path,
        )
        if settings.event_write_enabled
        else None
    )
    write_lock = threading.Lock()

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
                self._json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "event_writer": "enabled" if writer is not None else "disabled",
                    },
                )
                return
            if self.path == "/api/v1/status":
                source = v1_source
                payload_builder = build_status_payload
            elif self.path == "/api/v1.1/status":
                source = v1_1_source
                payload_builder = build_v1_1_status_payload
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), f"Bearer {settings.api_token}"
            ):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = payload_builder(source.read_rows())
            except ContractError as error:
                print(
                    f"WARNING: Private status endpoint contract failure: {error}",
                    flush=True,
                )
                self._json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "availability": "unavailable",
                        "error": "invalid_contract",
                        "detail": str(error),
                    },
                )
                return
            except Exception as error:
                print(
                    "WARNING: Private status endpoint source failure: "
                    f"{type(error).__name__}",
                    flush=True,
                )
                self._json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"availability": "unavailable", "error": "source_unavailable"},
                )
                return
            self._json(HTTPStatus.OK, payload)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/v1/events":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            if writer is None:
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "writer_disabled"})
                return
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""),
                f"Bearer {settings.event_write_token}",
            ):
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0
            if not 0 < content_length <= 1_000_000:
                self._json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_size"}
                )
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
                events = validate_batch(payload)
            except (json.JSONDecodeError, EventContractError) as error:
                self._json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid_event_batch", "detail": str(error)},
                )
                return
            with write_lock:
                try:
                    accepted_ids, duplicate_ids = append_events_idempotently(
                        writer, events
                    )
                except Exception as error:
                    print(
                        "WARNING: Private event writer failure: "
                        f"{type(error).__name__}",
                        flush=True,
                    )
                    self._json(
                        HTTPStatus.SERVICE_UNAVAILABLE, {"error": "writer_unavailable"}
                    )
                    return
            self._json(
                HTTPStatus.OK,
                {
                    "accepted_ids": accepted_ids,
                    "duplicate_ids": duplicate_ids,
                    "rejected_ids": [],
                },
            )

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
        print(
            "WARNING: Published status contract check failed at startup: "
            f"{error}. The service will remain running and retry on request.",
            flush=True,
        )
    except Exception as error:
        print(
            "WARNING: Unable to read the private Google Sheets status feed at "
            f"startup: {type(error).__name__}. The service will remain running "
            "and retry on request.",
            flush=True,
        )
    else:
        property_ids = ", ".join(sorted(payload["properties"]))
        print(
            "INFO: Private Google Sheets status feed verified "
            f"({payload['property_count']} properties: {property_ids}).",
            flush=True,
        )
    print(
        "INFO: Version 1.1 draft endpoint is available for parallel validation.",
        flush=True,
    )
    server = make_server(settings)
    print(
        f"INFO: Private status endpoints listening on port {settings.port}.",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
