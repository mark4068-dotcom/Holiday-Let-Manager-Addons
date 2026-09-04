"""Outbound-only publication of the combined feed to Google Calendar."""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from icalendar import Calendar

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
MANAGED_KEY = "hlmManaged"
SYNC_KEY = "hlmSyncKey"
FINGERPRINT_KEY = "hlmFingerprint"


@dataclass(frozen=True)
class PublicationConfig:
    """Runtime-only Google Calendar publication settings."""

    enabled: bool = False
    calendar_id: str = ""
    credentials_path: str = "/config/google-service-account.json"
    dry_run: bool = True
    title_mode: str = "retain_details"
    default_timezone: str = "Europe/London"
    retry_count: int = 4
    allow_empty: bool = False

    @classmethod
    def from_options(cls, options: dict) -> PublicationConfig:
        config = cls(
            enabled=bool(options.get("google_publish_enabled", False)),
            calendar_id=str(options.get("google_calendar_id", "")).strip(),
            credentials_path=str(
                options.get("google_credentials_path", "/config/google-service-account.json")
            ).strip(),
            dry_run=bool(options.get("google_dry_run", True)),
            title_mode=str(options.get("google_title_mode", "retain_details")).strip(),
            default_timezone=str(options.get("google_default_timezone", "Europe/London")).strip(),
            retry_count=int(options.get("google_retry_count", 4)),
            allow_empty=bool(options.get("google_allow_empty_publish", False)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.title_mode not in {"retain_details", "privacy_safe"}:
            raise ValueError("google_title_mode must be retain_details or privacy_safe")
        if not self.default_timezone:
            raise ValueError("google_default_timezone must not be empty")
        if not 0 <= self.retry_count <= 8:
            raise ValueError("google_retry_count must be between 0 and 8")
        if self.enabled and not self.calendar_id:
            raise ValueError("google_calendar_id is required when publication is enabled")
        if self.enabled and not self.credentials_path:
            raise ValueError("google_credentials_path is required when publication is enabled")


@dataclass
class PublicationStatus:
    """Non-sensitive publication diagnostics."""

    enabled: bool
    dry_run: bool
    state: str
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    desired_events: int = 0
    created_events: int = 0
    updated_events: int = 0
    deleted_events: int = 0
    unchanged_events: int = 0
    error: str | None = None


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _text(component, key: str) -> str:
    value = component.get(key)
    return "" if value is None else str(value)


def _event_id(sync_key: str) -> str:
    # Google-created IDs accept base32hex characters; hexadecimal is a safe subset.
    return hashlib.sha256(f"hlm-google-v1\0{sync_key}".encode()).hexdigest()[:40]


def _sync_key(uid: str, recurrence_id: str) -> str:
    return hashlib.sha256(f"{uid}\0{recurrence_id}".encode()).hexdigest()


def _date_time(value: date | datetime, timezone: str) -> dict[str, str]:
    if isinstance(value, datetime):
        result = {"dateTime": value.isoformat()}
        if value.tzinfo is None:
            result["timeZone"] = timezone
        return result
    return {"date": value.isoformat()}


def _decoded(component, key: str) -> date | datetime | timedelta | None:
    value = component.get(key)
    return getattr(value, "dt", None) if value is not None else None


def _recurrence_lines(event) -> list[str]:
    lines: list[str] = []
    for key, value in event.property_items():
        name = str(key).upper()
        if name not in {"RRULE", "RDATE", "EXDATE"}:
            continue
        encoded = value.to_ical().decode("utf-8")
        parameters = f";{value.params.to_ical().decode('utf-8')}" if value.params else ""
        lines.append(f"{name}{parameters}:{encoded}")
    return lines


def _privacy_safe_title(source_id: str, source_name: str) -> str:
    names = {"crossjack": "Crossjack", "skysail": "Skysail"}
    label = names.get(source_id, source_name or source_id or "HLM")
    return f"{label} — Booked"


def build_event_resources(
    calendar_data: bytes,
    *,
    title_mode: str = "retain_details",
    default_timezone: str = "Europe/London",
) -> dict[str, dict[str, Any]]:
    """Convert VEVENTs to stable Google event resources keyed by HLM identity."""

    calendar = Calendar.from_ical(calendar_data)
    resources: dict[str, dict[str, Any]] = {}
    master_keys: dict[str, str] = {}
    overrides: list[tuple[str, Any]] = []
    for event in calendar.walk("VEVENT"):
        uid = _text(event, "UID")
        if not uid:
            raise ValueError("combined event is missing UID")
        recurrence_id = _text(event, "RECURRENCE-ID")
        sync_key = _sync_key(uid, recurrence_id)
        start = _decoded(event, "DTSTART")
        if not isinstance(start, date | datetime):
            raise ValueError(f"event {uid!r} is missing a valid DTSTART")
        end = _decoded(event, "DTEND")
        duration = _decoded(event, "DURATION")
        if not isinstance(end, date | datetime):
            if isinstance(duration, timedelta):
                end = start + duration
            elif isinstance(start, datetime):
                end = start + timedelta(minutes=1)
            else:
                end = start + timedelta(days=1)

        source_id = _text(event, "X-HLM-SOURCE-ID")
        source_name = _text(event, "X-HLM-SOURCE-NAME")
        summary = _text(event, "SUMMARY") or "Untitled event"
        body: dict[str, Any] = {
            "id": _event_id(sync_key),
            "summary": (
                _privacy_safe_title(source_id, source_name)
                if title_mode == "privacy_safe" and source_id in {"crossjack", "skysail"}
                else summary
            ),
            "start": _date_time(start, default_timezone),
            "end": _date_time(end, default_timezone),
            "extendedProperties": {
                "private": {
                    MANAGED_KEY: "true",
                    SYNC_KEY: sync_key,
                    "hlmSourceId": source_id,
                }
            },
        }
        if title_mode == "retain_details":
            for source_field, target_field in (
                ("DESCRIPTION", "description"),
                ("LOCATION", "location"),
            ):
                value = _text(event, source_field)
                if value:
                    body[target_field] = value
        if not recurrence_id:
            recurrence = _recurrence_lines(event)
            if recurrence:
                body["recurrence"] = recurrence
            master_keys[uid] = sync_key
        else:
            overrides.append((uid, event.get("RECURRENCE-ID")))
        resources[sync_key] = body

    # Represent recurrence overrides as standalone stable events and exclude their
    # original occurrence from the recurring master to avoid a duplicate.
    for uid, recurrence_id in overrides:
        master = resources.get(master_keys.get(uid, ""))
        if master is None or recurrence_id is None:
            continue
        encoded = recurrence_id.to_ical().decode("utf-8")
        parameters = (
            f";{recurrence_id.params.to_ical().decode('utf-8')}" if recurrence_id.params else ""
        )
        exclusion = f"EXDATE{parameters}:{encoded}"
        if exclusion not in master.setdefault("recurrence", []):
            master["recurrence"].append(exclusion)

    for body in resources.values():
        fingerprint_source = {key: value for key, value in body.items() if key != "id"}
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_source, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        body["extendedProperties"]["private"][FINGERPRINT_KEY] = fingerprint
    return resources


class GoogleCalendarClient:
    """Small authenticated Calendar v3 REST client with bounded retries."""

    def __init__(
        self,
        config: PublicationConfig,
        *,
        sleeper=time.sleep,
        random_value=random.random,
    ) -> None:
        try:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2.service_account import Credentials
        except ImportError as error:
            raise RuntimeError("google-auth is not installed") from error

        credentials = Credentials.from_service_account_file(
            config.credentials_path, scopes=[CALENDAR_SCOPE]
        )
        self.session = AuthorizedSession(credentials)
        self.calendar_id = quote(config.calendar_id, safe="")
        self.retry_count = config.retry_count
        self.sleeper = sleeper
        self.random_value = random_value

    @property
    def events_url(self) -> str:
        return f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events"

    def _request(self, method: str, url: str, **kwargs) -> dict:
        for attempt in range(self.retry_count + 1):
            response = self.session.request(method, url, timeout=30, **kwargs)
            retryable = response.status_code == 429 or response.status_code >= 500
            if response.status_code == 403:
                retryable = any(
                    reason in response.text
                    for reason in ("rateLimitExceeded", "userRateLimitExceeded", "usageLimits")
                )
            if response.ok:
                return response.json() if response.content else {}
            if not retryable or attempt == self.retry_count:
                raise RuntimeError(
                    f"Google Calendar API {method} failed with HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )
            self.sleeper(min(2**attempt + self.random_value(), 32))
        raise AssertionError("unreachable")

    def list_managed(self) -> list[dict]:
        events: list[dict] = []
        params: dict[str, Any] = {
            "privateExtendedProperty": f"{MANAGED_KEY}=true",
            "singleEvents": "false",
            "showDeleted": "false",
            "maxResults": 2500,
        }
        while True:
            page = self._request("GET", self.events_url, params=params)
            events.extend(page.get("items", []))
            token = page.get("nextPageToken")
            if not token:
                return events
            params["pageToken"] = token

    def insert(self, body: dict) -> None:
        self._request("POST", self.events_url, json=body)

    def patch(self, event_id: str, body: dict) -> None:
        url = f"{self.events_url}/{quote(event_id, safe='')}"
        patch_body = {key: value for key, value in body.items() if key != "id"}
        self._request("PATCH", url, json=patch_body)

    def delete(self, event_id: str) -> None:
        url = f"{self.events_url}/{quote(event_id, safe='')}"
        self._request("DELETE", url)


class GoogleCalendarPublisher:
    """Reconcile only HLM-marked events in one private Google Calendar."""

    def __init__(self, config: PublicationConfig, client_factory=GoogleCalendarClient) -> None:
        self.config = config
        self.client_factory = client_factory
        state = "disabled" if not config.enabled else "not_run"
        self.status = PublicationStatus(config.enabled, config.dry_run, state)
        self.lock = threading.Lock()

    def snapshot(self) -> dict:
        return asdict(self.status)

    def publish(self, calendar_data: bytes) -> dict:
        if not self.config.enabled:
            return self.snapshot()
        if not self.lock.acquire(blocking=False):
            return self.snapshot()
        self.status.last_attempt_at = _iso_now()
        self.status.state = "running"
        self.status.error = None
        try:
            desired = build_event_resources(
                calendar_data,
                title_mode=self.config.title_mode,
                default_timezone=self.config.default_timezone,
            )
            client = self.client_factory(self.config)
            existing: dict[str, dict] = {}
            duplicates: list[dict] = []
            for event in client.list_managed():
                private = event.get("extendedProperties", {}).get("private", {})
                sync_key = private.get(SYNC_KEY)
                if not sync_key:
                    continue
                if sync_key in existing:
                    duplicates.append(event)
                else:
                    existing[sync_key] = event

            if not desired and existing and not self.config.allow_empty:
                raise RuntimeError(
                    "refusing to remove every managed Google event from an empty combined feed"
                )

            creates = [body for key, body in desired.items() if key not in existing]
            updates = [
                (existing[key]["id"], body)
                for key, body in desired.items()
                if key in existing
                and existing[key]
                .get("extendedProperties", {})
                .get("private", {})
                .get(FINGERPRINT_KEY)
                != body["extendedProperties"]["private"][FINGERPRINT_KEY]
            ]
            unchanged = len(desired) - len(creates) - len(updates)
            deletes = [event for key, event in existing.items() if key not in desired] + duplicates

            if not self.config.dry_run:
                for body in creates:
                    client.insert(body)
                for event_id, body in updates:
                    client.patch(event_id, body)
                for event in deletes:
                    client.delete(event["id"])

            self.status.desired_events = len(desired)
            self.status.created_events = len(creates)
            self.status.updated_events = len(updates)
            self.status.deleted_events = len(deletes)
            self.status.unchanged_events = unchanged
            self.status.last_success_at = _iso_now()
            self.status.state = "dry_run" if self.config.dry_run else "healthy"
        except Exception as error:
            self.status.state = "error"
            self.status.error = str(error)
        finally:
            self.lock.release()
        return self.snapshot()


def credentials_file_exists(config: PublicationConfig) -> bool:
    """Return credential availability without including its contents in status."""

    return Path(config.credentials_path).is_file()
