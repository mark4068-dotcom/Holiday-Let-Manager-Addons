"""Home Assistant update coordinator for Coastal Water Watch."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CoastalWaterWatchApiClient
from .events import overflow_transitions
from .locations import BathingLocation
from .models import (
    BathingAdvice,
    LocationStatus,
    OverflowReport,
    RegionalBathingSiteStatus,
    RegionalImpactReport,
)
from .source_health import SourceSnapshot
from .status import aggregate_location_status

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LocationUpdate:
    """One complete update for a bathing location."""

    status: LocationStatus
    updated_at: datetime
    overflows: SourceSnapshot[OverflowReport]
    advice: SourceSnapshot[BathingAdvice]
    regional_impacts: SourceSnapshot[RegionalImpactReport] | None
    regional_status: SourceSnapshot[RegionalBathingSiteStatus] | None = None
    latest_impacting_release: SourceSnapshot[RegionalImpactReport] | None = None


class CoastalWaterWatchCoordinator(DataUpdateCoordinator[LocationUpdate]):
    """Fetch and aggregate official data for one location."""

    def __init__(
        self,
        hass: HomeAssistant,
        location: BathingLocation,
        update_interval_minutes: int = 10,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Coastal Water Watch: {location.name}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.location = location
        self._client = CoastalWaterWatchApiClient(async_get_clientsession(hass))
        self._overflows: SourceSnapshot[OverflowReport] = SourceSnapshot(
            "Water UK Stream"
        )
        self._advice: SourceSnapshot[BathingAdvice] = SourceSnapshot(
            "Environment Agency"
        )
        self._regional: SourceSnapshot[RegionalImpactReport] | None = (
            SourceSnapshot("Southern Water Rivers and Seas Watch")
            if location.regional_bathing_site_id is not None
            else None
        )
        self._regional_status: SourceSnapshot[RegionalBathingSiteStatus] | None = (
            SourceSnapshot("Southern Water Rivers and Seas Watch status")
            if location.regional_bathing_site_id is not None
            else None
        )
        self._latest_impacting_release: SourceSnapshot[RegionalImpactReport] | None = (
            SourceSnapshot("Southern Water latest impacting release")
            if location.regional_bathing_site_id is not None
            else None
        )

    async def _async_update_data(self) -> LocationUpdate:
        tasks: dict[str, object] = {}
        if self.location.stream_asset_ids:
            tasks["stream"] = self._client.async_get_overflows(
                self.location.company_key,
                self.location.stream_asset_ids,
            )
        tasks["advice"] = self._client.async_get_bathing_advice(
            self.location.bathing_water_id
        )
        if self.location.regional_bathing_site_id is not None:
            tasks["regional"] = self._client.async_get_regional_history(
                self.location.regional_bathing_site_id
            )
            tasks["regional_status"] = self._client.async_get_regional_site_status(
                self.location.regional_bathing_site_id
            )
            tasks["latest_impacting_release"] = (
                self._client.async_get_latest_impacting_release(
                    self.location.regional_bathing_site_id
                )
            )
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results = dict(zip(tasks, gathered, strict=True))
        attempted_at = datetime.now(UTC)

        previous_overflows = self._overflows
        if "stream" in results:
            self._overflows = _updated_snapshot(
                self._overflows, results["stream"], attempted_at
            )
        self._advice = _updated_snapshot(
            self._advice, results["advice"], attempted_at
        )
        if self._regional is not None:
            self._regional = _updated_snapshot(
                self._regional, results["regional"], attempted_at
            )
        if self._regional_status is not None:
            self._regional_status = _updated_snapshot(
                self._regional_status, results["regional_status"], attempted_at
            )
        if self._latest_impacting_release is not None:
            self._latest_impacting_release = _updated_snapshot(
                self._latest_impacting_release,
                results["latest_impacting_release"],
                attempted_at,
            )

        snapshots = (
            self._overflows,
            self._advice,
            self._regional,
            self._regional_status,
            self._latest_impacting_release,
        )
        if not any(
            snapshot is not None and snapshot.last_success_at is not None
            for snapshot in snapshots
        ):
            errors = "; ".join(
                snapshot.last_error
                for snapshot in snapshots
                if snapshot is not None and snapshot.last_error is not None
            )
            raise UpdateFailed(
                f"No source has succeeded for {self.location.name}: {errors}"
            )

        if (
            previous_overflows.last_success_at is not None
            and "stream" in results
            and not isinstance(results["stream"], BaseException)
        ):
            for transition in overflow_transitions(
                previous_overflows.records, self._overflows.records
            ):
                report = transition.report
                self.hass.bus.async_fire(
                    transition.event_type,
                    {
                        "location": self.location.name,
                        "asset_id": report.asset_id,
                        "company": report.company,
                        "receiving_water": report.receiving_water,
                        "source": report.source,
                        "state": report.state.value,
                        "state_started_at": (
                            report.state_started_at.isoformat()
                            if report.state_started_at is not None
                            else None
                        ),
                    },
                )

        status = aggregate_location_status(
            now=attempted_at,
            overflows=self._overflows.observation,
            advice=self._advice.observation,
            regional_impacts=(self._regional.observation if self._regional else None),
            regional_status=(
                self._regional_status.observation if self._regional_status else None
            ),
        )
        return LocationUpdate(
            status,
            attempted_at,
            self._overflows,
            self._advice,
            self._regional,
            self._regional_status,
            self._latest_impacting_release,
        )


def _updated_snapshot(
    snapshot: SourceSnapshot, result: object, attempted_at: datetime
) -> SourceSnapshot:
    """Apply one gathered request result without affecting other sources."""
    if isinstance(result, asyncio.CancelledError):
        raise result
    if isinstance(result, BaseException):
        message = f"{type(result).__name__}: {result}"
        return snapshot.failed(message, attempted_at)
    return snapshot.succeeded(result, attempted_at)
