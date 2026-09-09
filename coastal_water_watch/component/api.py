"""Asynchronous read-only client for Coastal Water Watch public sources."""

import asyncio
from typing import Any

from .const import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    EA_BASE_URL,
    SOUTHERN_WATER_RSW_SERVICE,
)
from .models import (
    BathingAdvice,
    OverflowReport,
    RegionalBathingSiteStatus,
    RegionalImpactReport,
)
from .parsers import (
    parse_ea_advice,
    parse_southern_water_history,
    parse_southern_water_site_status,
    parse_stream_overflows,
)
from .providers import get_stream_provider


class CoastalWaterWatchApiClient:
    """Fetch supported public JSON endpoints using Home Assistant's HTTP session."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        async with asyncio.timeout(DEFAULT_REQUEST_TIMEOUT_SECONDS):
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def async_get_overflows(
        self, company_key: str, asset_ids: tuple[str, ...]
    ) -> tuple[OverflowReport, ...]:
        """Get records from a company layer using the national Stream contract."""
        layer_url = get_stream_provider(company_key).layer_url
        if not asset_ids:
            raise ValueError("At least one verified Stream asset ID is required")
        quoted_ids = ",".join(
            f"'{asset_id.replace(chr(39), chr(39) * 2)}'" for asset_id in asset_ids
        )
        where = f"Id IN ({quoted_ids})"
        payload = await self._get_json(
            f"{layer_url}/query",
            {
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "f": "json",
            },
        )
        return parse_stream_overflows(payload)

    async def async_get_bathing_advice(
        self, bathing_water_id: str
    ) -> tuple[BathingAdvice, ...]:
        """Get current official EA advice situations."""
        payload = await self._get_json(
            f"{EA_BASE_URL}/doc/bathing-water-quality/advice-against-bathing/"
            f"bathing-water/{bathing_water_id}/situations.json",
            {},
        )
        return parse_ea_advice(payload, bathing_water_id)

    async def async_get_regional_history(
        self, bathing_site_id: str, limit: int = 20
    ) -> tuple[RegionalImpactReport, ...]:
        """Get Southern Water's regional release and impact history."""
        payload = await self._get_json(
            f"{SOUTHERN_WATER_RSW_SERVICE}/4/query",
            {
                "where": f"BathingSiteID={int(bathing_site_id)}",
                "outFields": "*",
                "orderByFields": "Start DESC",
                "resultRecordCount": limit,
                "f": "json",
            },
        )
        return parse_southern_water_history(payload, bathing_site_id)

    async def async_get_latest_impacting_release(
        self, bathing_site_id: str
    ) -> tuple[RegionalImpactReport, ...]:
        """Get the newest release explicitly reported as impacting a site."""
        payload = await self._get_json(
            f"{SOUTHERN_WATER_RSW_SERVICE}/4/query",
            {
                "where": (
                    f"BathingSiteID={int(bathing_site_id)} AND IsImpacting='true'"
                ),
                "outFields": "*",
                "orderByFields": "Start DESC",
                "resultRecordCount": 1,
                "f": "json",
            },
        )
        return parse_southern_water_history(payload, bathing_site_id)

    async def async_get_regional_site_status(
        self, bathing_site_id: str
    ) -> tuple[RegionalBathingSiteStatus, ...]:
        """Get Southern Water's explicit current bathing-site release window."""
        payload = await self._get_json(
            f"{SOUTHERN_WATER_RSW_SERVICE}/0/query",
            {
                "where": f"Id={int(bathing_site_id)}",
                "outFields": (
                    "Id,Name,eubwid,ReleaseStatus,SpillMessage,"
                    "Current_EA_Classification,EA_Classification_Year"
                ),
                "returnGeometry": "false",
                "f": "json",
            },
        )
        return parse_southern_water_site_status(payload, bathing_site_id)
