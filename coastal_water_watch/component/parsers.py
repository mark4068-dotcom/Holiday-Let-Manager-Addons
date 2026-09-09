"""Pure parsers for supported public source payloads."""

from datetime import UTC, datetime
from typing import Any

from .models import (
    BathingAdvice,
    ImpactState,
    OverflowReport,
    OverflowState,
    RegionalBathingSiteStatus,
    RegionalImpactReport,
    RegionalSiteState,
    RiskLevel,
)


def _datetime_from_epoch_ms(value: object) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _datetime_from_iso(value: object) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("_value")
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _text(value: object) -> str | None:
    if isinstance(value, dict):
        value = value.get("_value") or value.get("name")
    return str(value) if value not in (None, "") else None


def parse_stream_overflows(payload: dict[str, Any]) -> tuple[OverflowReport, ...]:
    """Parse a Water UK Stream-compatible ArcGIS feature response."""
    reports: list[OverflowReport] = []
    state_map = {
        1: OverflowState.ACTIVE,
        0: OverflowState.INACTIVE,
        -1: OverflowState.OFFLINE,
    }
    for feature in payload.get("features", []):
        attributes = feature.get("attributes", {})
        reports.append(
            OverflowReport(
                source="Water UK Stream",
                asset_id=str(attributes.get("Id", "")),
                company=str(attributes.get("Company", "")),
                receiving_water=_text(attributes.get("ReceivingWaterCourse")),
                state=state_map.get(attributes.get("Status"), OverflowState.UNKNOWN),
                state_started_at=_datetime_from_epoch_ms(attributes.get("StatusStart")),
                updated_at=_datetime_from_epoch_ms(attributes.get("LastUpdated")),
                latitude=attributes.get("Latitude"),
                longitude=attributes.get("Longitude"),
            )
        )
    return tuple(reports)


def parse_ea_advice(
    payload: dict[str, Any], bathing_water_id: str
) -> tuple[BathingAdvice, ...]:
    """Parse Environment Agency advice situations without inventing a clear state."""
    advice: list[BathingAdvice] = []
    items = payload.get("result", {}).get("items", [])
    for item in items:
        risk = item.get("riskLevel", {})
        risk_name = _text(risk.get("name"))
        risk_level = {
            "normal": RiskLevel.NORMAL,
            "increased": RiskLevel.INCREASED,
        }.get((risk_name or "").lower(), RiskLevel.UNKNOWN)
        bathing_water = item.get("stp_bathingWater", {})
        advice.append(
            BathingAdvice(
                source="Environment Agency",
                bathing_water_id=str(
                    bathing_water.get("eubwidNotation", bathing_water_id)
                ),
                bathing_water_name=_text(bathing_water.get("name")),
                risk_level=risk_level,
                advice=_text(item.get("comment")),
                published_at=_datetime_from_iso(item.get("publishedAt")),
                expires_at=_datetime_from_iso(item.get("expiresAt")),
            )
        )
    return tuple(advice)


def parse_southern_water_history(
    payload: dict[str, Any], bathing_site_id: str
) -> tuple[RegionalImpactReport, ...]:
    """Parse Southern Water release history and retain its modelled provenance."""
    reports: list[RegionalImpactReport] = []
    for feature in payload.get("features", []):
        attributes = feature.get("attributes", {})
        raw_impact = str(attributes.get("Impact_Status", "")).lower()
        impact = {
            "impacted": ImpactState.IMPACTED,
            "not impacted": ImpactState.NOT_IMPACTED,
        }.get(raw_impact, ImpactState.UNKNOWN)
        reports.append(
            RegionalImpactReport(
                source="Southern Water Rivers and Seas Watch",
                event_id=str(attributes.get("Event_ID", "")),
                bathing_site_id=str(attributes.get("BathingSiteID", bathing_site_id)),
                bathing_site_name=_text(attributes.get("BathingSite")),
                outfall_id=_text(attributes.get("OutfallID")),
                outfall_name=_text(attributes.get("Outfall")),
                state=impact,
                review_status=_text(attributes.get("Status")),
                started_at=_datetime_from_epoch_ms(attributes.get("Start")),
                ended_at=_datetime_from_epoch_ms(attributes.get("End_")),
                duration_seconds=attributes.get("Duration_Seconds"),
                model_version=_text(attributes.get("Tidal_Model_Version")),
            )
        )
    return tuple(reports)


def parse_southern_water_site_status(
    payload: dict[str, Any], bathing_site_id: str
) -> tuple[RegionalBathingSiteStatus, ...]:
    """Parse Southern Water's explicit current 24/72-hour site status."""
    states = {
        "1": RegionalSiteState.NO_REPORTED_IMPACT,
        "2": RegionalSiteState.POSSIBLE_IMPACT_72H,
        "3": RegionalSiteState.POSSIBLE_IMPACT_24H,
    }
    statuses: list[RegionalBathingSiteStatus] = []
    for feature in payload.get("features", []):
        attributes = feature.get("attributes", {})
        statuses.append(
            RegionalBathingSiteStatus(
                source="Southern Water Rivers and Seas Watch status",
                bathing_site_id=str(attributes.get("Id", bathing_site_id)),
                bathing_site_name=_text(attributes.get("Name")),
                bathing_water_id=_text(attributes.get("eubwid")),
                state=states.get(
                    str(attributes.get("ReleaseStatus", "")),
                    RegionalSiteState.UNKNOWN,
                ),
                message=_text(attributes.get("SpillMessage")),
                ea_classification=_text(attributes.get("Current_EA_Classification")),
                ea_classification_year=attributes.get("EA_Classification_Year"),
            )
        )
    return tuple(statuses)
