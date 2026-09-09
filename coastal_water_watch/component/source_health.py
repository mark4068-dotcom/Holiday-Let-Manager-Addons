"""Per-source cache and health state independent of Home Assistant."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

from .models import SourceObservation

T = TypeVar("T")


class SourceHealth(StrEnum):
    """Result of the most recent attempt to update one source."""

    OK = "ok"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceSnapshot(Generic[T]):
    """Last successful records plus health of the latest source attempt."""

    source: str
    records: tuple[T, ...] = ()
    last_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_error: str | None = None

    @property
    def health(self) -> SourceHealth:
        """Return health based on whether the source has been attempted."""
        if self.last_error is not None:
            return SourceHealth.ERROR
        if self.last_attempt_at is not None:
            return SourceHealth.OK
        return SourceHealth.UNKNOWN

    @property
    def observation(self) -> SourceObservation[T] | None:
        """Return reusable evidence only after at least one successful request."""
        if self.last_success_at is None:
            return None
        return SourceObservation(self.source, self.last_success_at, self.records)

    def succeeded(
        self, records: tuple[T, ...], attempted_at: datetime
    ) -> "SourceSnapshot[T]":
        """Replace cached records after a successful request."""
        return SourceSnapshot(
            self.source,
            records,
            last_success_at=attempted_at,
            last_attempt_at=attempted_at,
        )

    def failed(self, error: str, attempted_at: datetime) -> "SourceSnapshot[T]":
        """Retain prior records while recording the latest request failure."""
        return SourceSnapshot(
            self.source,
            self.records,
            last_success_at=self.last_success_at,
            last_attempt_at=attempted_at,
            last_error=error,
        )

    def attributes(self) -> dict[str, str | int | None]:
        """Return serialisable diagnostic attributes for Home Assistant."""
        return {
            "health": self.health.value,
            "last_success": (
                self.last_success_at.isoformat()
                if self.last_success_at is not None
                else None
            ),
            "last_attempt": (
                self.last_attempt_at.isoformat()
                if self.last_attempt_at is not None
                else None
            ),
            "last_error": self.last_error,
            "record_count": len(self.records),
        }
