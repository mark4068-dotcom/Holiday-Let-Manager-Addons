"""Filter, namespace, cache and combine remote iCalendar feeds."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import urllib.request
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from icalendar import Calendar

MAX_FEED_BYTES = 10 * 1024 * 1024
USER_AGENT = "HLM-iCalendar-Aggregator/0.1"
SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


@dataclass(frozen=True)
class SourceConfig:
    """Configuration for one remote ICS source."""

    id: str
    name: str
    url: str
    enabled: bool = True
    exclude_regex: str = ""
    include_regex: str = ""
    title_prefix: str = ""
    exclude_cancelled: bool = True

    @classmethod
    def from_dict(cls, value: dict) -> SourceConfig:
        if not isinstance(value, dict):
            raise ValueError("each source must be an object")
        try:
            source = cls(
                id=str(value["id"]),
                name=str(value["name"]),
                url=str(value["url"]),
                enabled=bool(value.get("enabled", True)),
                exclude_regex=str(value.get("exclude_regex", "")),
                include_regex=str(value.get("include_regex", "")),
                title_prefix=str(value.get("title_prefix", "")),
                exclude_cancelled=bool(value.get("exclude_cancelled", True)),
            )
        except KeyError as error:
            raise ValueError(f"source is missing required field {error.args[0]!r}") from error
        source.validate()
        return source

    def validate(self) -> None:
        if not SOURCE_ID_PATTERN.fullmatch(self.id):
            raise ValueError(f"source {self.id!r} has an invalid id")
        if not self.name.strip():
            raise ValueError(f"source {self.id!r} has an empty name")
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"source {self.id!r} URL must use HTTP or HTTPS")
        if parsed.username or parsed.password:
            raise ValueError(f"source {self.id!r} URL must not contain credentials")
        for field_name, expression in (
            ("exclude_regex", self.exclude_regex),
            ("include_regex", self.include_regex),
        ):
            try:
                _compiled(expression)
            except ValueError as error:
                raise ValueError(f"source {self.id!r} {field_name}: {error}") from error


def parse_sources(values: object) -> list[SourceConfig]:
    """Validate configured sources and reject ambiguous identifiers."""

    if not isinstance(values, list):
        raise ValueError("sources must be a list")
    sources = [SourceConfig.from_dict(value) for value in values]
    seen: set[str] = set()
    for source in sources:
        if source.id in seen:
            raise ValueError(f"duplicate source id {source.id!r}")
        seen.add(source.id)
    return sources


@dataclass
class SourceStatus:
    """Non-sensitive source diagnostics."""

    id: str
    name: str
    enabled: bool
    source_events: int = 0
    accepted_events: int = 0
    excluded_events: int = 0
    cancelled_events: int = 0
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    cache_available: bool = False
    using_cached_output: bool = False
    error: str | None = None


@dataclass(frozen=True)
class FilterResult:
    """Filtered calendar bytes and event counts."""

    calendar: bytes
    source_events: int
    accepted_events: int
    excluded_events: int
    cancelled_events: int


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat()


def atomic_write(path: Path, content: bytes) -> None:
    """Replace a file without exposing a partial feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except Exception:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _compiled(expression: str) -> re.Pattern[str] | None:
    if not expression:
        return None
    try:
        return re.compile(expression)
    except re.error as error:
        raise ValueError(f"invalid regular expression: {error}") from error


def _matches(pattern: re.Pattern[str] | None, *values: str) -> bool:
    return pattern is not None and any(pattern.search(value) for value in values)


def _text(component, key: str) -> str:
    value = component.get(key)
    return "" if value is None else str(value)


def _event_key(source_id: str, event) -> str:
    original_uid = _text(event, "UID")
    if not original_uid:
        seed = "|".join((_text(event, "DTSTART"), _text(event, "DTEND"), _text(event, "SUMMARY")))
        original_uid = hashlib.sha256(seed.encode()).hexdigest()
    recurrence_id = _text(event, "RECURRENCE-ID")
    return f"{source_id}\0{original_uid}\0{recurrence_id}"


def _namespaced_uid(source_id: str, original_uid: str) -> str:
    digest = hashlib.sha256(f"{source_id}\0{original_uid}".encode()).hexdigest()
    return f"{digest}@hlm.local"


def _new_calendar(name: str) -> Calendar:
    calendar = Calendar()
    calendar.add("prodid", "-//Holiday Let Manager//iCalendar Aggregator 0.1//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", name)
    return calendar


def _add_timezones(target: Calendar, source: Calendar, seen: set[str]) -> None:
    for timezone in source.walk("VTIMEZONE"):
        tzid = _text(timezone, "TZID")
        key = tzid or hashlib.sha256(timezone.to_ical()).hexdigest()
        if key not in seen:
            target.add_component(copy.deepcopy(timezone))
            seen.add(key)


def filter_calendar(data: bytes, source: SourceConfig) -> FilterResult:
    """Return a filtered source calendar with stable, namespaced event UIDs."""

    try:
        parsed = Calendar.from_ical(data)
    except Exception as error:
        raise ValueError(f"invalid ICS data: {error}") from error

    exclude = _compiled(source.exclude_regex)
    include = _compiled(source.include_regex)
    output = _new_calendar(source.name)
    _add_timezones(output, parsed, set())

    source_events = excluded_events = cancelled_events = 0
    for incoming in parsed.walk("VEVENT"):
        source_events += 1
        summary = _text(incoming, "SUMMARY")
        description = _text(incoming, "DESCRIPTION")
        if source.exclude_cancelled and _text(incoming, "STATUS").upper() == "CANCELLED":
            cancelled_events += 1
            continue
        if _matches(exclude, summary, description):
            excluded_events += 1
            continue
        if include is not None and not _matches(include, summary, description):
            excluded_events += 1
            continue

        event = copy.deepcopy(incoming)
        original_uid = (
            _text(event, "UID") or hashlib.sha256(_event_key(source.id, event).encode()).hexdigest()
        )
        event["UID"] = _namespaced_uid(source.id, original_uid)
        event["X-HLM-ORIGINAL-UID"] = original_uid
        event["X-HLM-SOURCE-ID"] = source.id
        event["X-HLM-SOURCE-NAME"] = source.name
        if source.title_prefix:
            event["SUMMARY"] = f"{source.title_prefix}{summary}"
        output.add_component(event)

    accepted_events = source_events - excluded_events - cancelled_events
    return FilterResult(
        calendar=output.to_ical(),
        source_events=source_events,
        accepted_events=accepted_events,
        excluded_events=excluded_events,
        cancelled_events=cancelled_events,
    )


def combine_calendars(calendars: list[bytes], name: str = "HLM Combined Calendar") -> bytes:
    """Merge already-filtered source calendars and remove duplicate instances."""

    output = _new_calendar(name)
    seen_timezones: set[str] = set()
    seen_events: set[str] = set()
    for data in calendars:
        parsed = Calendar.from_ical(data)
        _add_timezones(output, parsed, seen_timezones)
        for event in parsed.walk("VEVENT"):
            key = f"{_text(event, 'UID')}\0{_text(event, 'RECURRENCE-ID')}"
            if key in seen_events:
                continue
            seen_events.add(key)
            output.add_component(copy.deepcopy(event))
    return output.to_ical()


def fetch_ics(url: str, timeout: int = 30) -> bytes:
    """Download one bounded HTTP(S) ICS source."""

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source URL must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("credentials embedded in a source URL are not supported")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("source calendar exceeds the 10 MiB limit")
    return data


class Aggregator:
    """Persistent source refresh and combined-calendar coordinator."""

    def __init__(
        self,
        data_dir: Path,
        sources: list[SourceConfig],
        fetcher: Callable[[str], bytes] = fetch_ics,
    ) -> None:
        for source in sources:
            source.validate()
        if len({source.id for source in sources}) != len(sources):
            raise ValueError("source ids must be unique")
        self.data_dir = data_dir
        self.sources = sources
        self.fetcher = fetcher
        self.lock = threading.Lock()
        self.started_at = iso_now()
        self.last_refresh_at: str | None = None
        self.combined_updated_at: str | None = None
        self.running = False
        self.statuses = {
            source.id: SourceStatus(
                id=source.id,
                name=source.name,
                enabled=source.enabled,
                cache_available=self.source_path(source.id).exists(),
            )
            for source in sources
        }
        self._restore_status()

    @property
    def combined_path(self) -> Path:
        return self.data_dir / "combined.ics"

    @property
    def status_path(self) -> Path:
        return self.data_dir / "status.json"

    def source_path(self, source_id: str) -> Path:
        return self.data_dir / "sources" / f"{source_id}.ics"

    def _restore_status(self) -> None:
        try:
            saved = json.loads(self.status_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return
        self.last_refresh_at = saved.get("last_refresh_at")
        self.combined_updated_at = saved.get("combined_updated_at")
        for source_id, status in self.statuses.items():
            previous = next(
                (entry for entry in saved.get("sources", []) if entry.get("id") == source_id),
                None,
            )
            if previous:
                status.last_success_at = previous.get("last_success_at")
                status.source_events = int(previous.get("source_events", 0))
                status.accepted_events = int(previous.get("accepted_events", 0))
                status.excluded_events = int(previous.get("excluded_events", 0))
                status.cancelled_events = int(previous.get("cancelled_events", 0))

    def snapshot(self) -> dict:
        enabled = [status for status in self.statuses.values() if status.enabled]
        combined_available = self.combined_path.exists()
        errors = sum(status.error is not None for status in enabled)
        if not enabled:
            state = "setup"
        elif combined_available and errors == 0:
            state = "healthy"
        elif combined_available:
            state = "degraded"
        else:
            state = "unhealthy"
        return {
            "state": state,
            "running": self.running,
            "started_at": self.started_at,
            "last_refresh_at": self.last_refresh_at,
            "combined_updated_at": self.combined_updated_at,
            "combined_available": combined_available,
            "configured_source_count": len(self.sources),
            "enabled_source_count": len(enabled),
            "accepted_event_count": sum(status.accepted_events for status in enabled),
            "excluded_event_count": sum(status.excluded_events for status in enabled),
            "sources": [asdict(status) for status in self.statuses.values()],
        }

    def _save_status(self) -> None:
        atomic_write(self.status_path, f"{json.dumps(self.snapshot(), indent=2)}\n".encode())

    def refresh(self) -> dict:
        if not self.lock.acquire(blocking=False):
            return self.snapshot()
        self.running = True
        try:
            for source in self.sources:
                status = self.statuses[source.id]
                status.enabled = source.enabled
                status.using_cached_output = False
                status.error = None
                if not source.enabled:
                    continue
                status.last_attempt_at = iso_now()
                try:
                    result = filter_calendar(self.fetcher(source.url), source)
                    atomic_write(self.source_path(source.id), result.calendar)
                    status.source_events = result.source_events
                    status.accepted_events = result.accepted_events
                    status.excluded_events = result.excluded_events
                    status.cancelled_events = result.cancelled_events
                    status.last_success_at = iso_now()
                    status.cache_available = True
                except Exception as error:
                    status.error = str(error)
                    status.cache_available = self.source_path(source.id).exists()
                    status.using_cached_output = status.cache_available

            available = [
                self.source_path(source.id).read_bytes()
                for source in self.sources
                if source.enabled and self.source_path(source.id).exists()
            ]
            if available:
                atomic_write(self.combined_path, combine_calendars(available))
                self.combined_updated_at = iso_now()
            self.last_refresh_at = iso_now()
        finally:
            self.running = False
            self._save_status()
            self.lock.release()
        return self.snapshot()
