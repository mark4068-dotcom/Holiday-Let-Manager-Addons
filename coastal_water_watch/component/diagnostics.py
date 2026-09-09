"""Redacted diagnostics for Coastal Water Watch."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CoastalWaterWatchCoordinator, LocationUpdate
from .source_health import SourceSnapshot


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return an allowlisted diagnostic view without location or record data."""
    coordinator: CoastalWaterWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    return diagnostic_data(
        entry_version=entry.version,
        entry_minor_version=entry.minor_version,
        polling_interval_minutes=int(coordinator.update_interval.total_seconds() / 60),
        update=coordinator.data,
    )


def diagnostic_data(
    *,
    entry_version: int,
    entry_minor_version: int,
    polling_interval_minutes: int = 10,
    update: LocationUpdate,
) -> dict[str, Any]:
    """Build diagnostics from a strict allowlist of non-location fields."""
    return {
        "config_entry": {
            "version": entry_version,
            "minor_version": entry_minor_version,
            "location": "**REDACTED**",
            "polling_interval_minutes": polling_interval_minutes,
        },
        "aggregate": {
            "status": update.status.level.value,
            "provenance": update.status.provenance.value,
            "sources": list(update.status.sources),
            "stale_sources": list(update.status.stale_sources),
            "updated_at": update.updated_at.isoformat(),
        },
        "source_health": {
            "stream": _source_diagnostics(update.overflows),
            "environment_agency": _source_diagnostics(update.advice),
            "regional": (
                _source_diagnostics(update.regional_impacts)
                if update.regional_impacts is not None
                else None
            ),
            "regional_status": (
                _source_diagnostics(update.regional_status)
                if update.regional_status is not None
                else None
            ),
            "latest_impacting_release": (
                _source_diagnostics(update.latest_impacting_release)
                if update.latest_impacting_release is not None
                else None
            ),
        },
    }


def _source_diagnostics(snapshot: SourceSnapshot) -> dict[str, Any]:
    """Exclude records and error details while retaining operational evidence."""
    return {
        "source": snapshot.source,
        "health": snapshot.health.value,
        "last_success": (
            snapshot.last_success_at.isoformat()
            if snapshot.last_success_at is not None
            else None
        ),
        "last_attempt": (
            snapshot.last_attempt_at.isoformat()
            if snapshot.last_attempt_at is not None
            else None
        ),
        "error_type": _error_type(snapshot.last_error),
        "record_count": len(snapshot.records),
    }


def _error_type(error: str | None) -> str | None:
    """Keep only a conservative exception class name from a stored error."""
    if error is None:
        return None
    candidate = error.partition(":")[0]
    return candidate if candidate.replace("_", "").isalnum() else "Error"
