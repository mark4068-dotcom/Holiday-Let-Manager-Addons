"""Pure state selection rules for Home Assistant detail entities."""

from datetime import datetime

from .models import (
    BathingAdvice,
    ImpactState,
    OverflowReport,
    OverflowState,
    RegionalBathingSiteStatus,
    RegionalImpactReport,
    RiskLevel,
)


def overflow_state(records: tuple[OverflowReport, ...]) -> str:
    """Select the most important nationally reported overflow state."""
    states = {record.state for record in records}
    for state in (
        OverflowState.ACTIVE,
        OverflowState.OFFLINE,
        OverflowState.UNKNOWN,
        OverflowState.INACTIVE,
    ):
        if state in states:
            return state.value
    return "no_data"


def stream_data_is_current(
    records: tuple[OverflowReport, ...], now: datetime
) -> bool:
    """Return whether Stream records contain no future clock errors."""
    return all(
        record.updated_at is None or record.updated_at <= now
        for record in records
    )


def advice_state(records: tuple[BathingAdvice, ...]) -> str:
    """Select current official advice without inventing a normal result."""
    levels = {record.risk_level for record in records}
    if RiskLevel.INCREASED in levels:
        return RiskLevel.INCREASED.value
    if levels and levels == {RiskLevel.NORMAL}:
        return RiskLevel.NORMAL.value
    if levels:
        return RiskLevel.UNKNOWN.value
    return "no_current_advice"


def current_advice_records(
    records: tuple[BathingAdvice, ...], now: datetime
) -> tuple[BathingAdvice, ...]:
    """Remove expired EA situations and impossible future publications."""
    return tuple(
        record
        for record in records
        if (record.published_at is None or record.published_at <= now)
        and (record.expires_at is None or record.expires_at > now)
    )


def latest_regional_state(records: tuple[RegionalImpactReport, ...]) -> str:
    """Return the state of the newest regional history record."""
    if not records:
        return "no_events"
    return records[0].state.value


def latest_impacting_release(
    records: tuple[RegionalImpactReport, ...],
) -> RegionalImpactReport | None:
    """Return the newest release reported as impacting the bathing site."""
    return next(
        (record for record in records if record.state is ImpactState.IMPACTED),
        None,
    )


def regional_site_state(records: tuple[RegionalBathingSiteStatus, ...]) -> str:
    """Return the explicit current regional bathing-site state."""
    if not records:
        return "no_data"
    return records[0].state.value


def current_regional_impacts(
    records: tuple[RegionalImpactReport, ...],
) -> tuple[RegionalImpactReport, ...]:
    """Exclude ended history records from current impact conclusions."""
    return tuple(
        record
        for record in records
        if record.state is ImpactState.IMPACTED and record.ended_at is None
    )
