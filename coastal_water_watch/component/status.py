"""Aggregate bathing-location status with explicit freshness and provenance."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import (
    BathingAdvice,
    Freshness,
    LocationStatus,
    LocationStatusLevel,
    OverflowReport,
    OverflowState,
    RegionalBathingSiteStatus,
    RegionalImpactReport,
    RegionalSiteState,
    RiskLevel,
    SourceObservation,
    StatusProvenance,
)


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Maximum ages for successful observations from each source class."""

    stream: timedelta = timedelta(minutes=30)
    environment_agency: timedelta = timedelta(hours=6)
    regional: timedelta = timedelta(hours=6)


def aggregate_location_status(
    *,
    now: datetime,
    overflows: SourceObservation[OverflowReport] | None = None,
    advice: SourceObservation[BathingAdvice] | None = None,
    regional_impacts: SourceObservation[RegionalImpactReport] | None = None,
    regional_status: SourceObservation[RegionalBathingSiteStatus] | None = None,
    policy: FreshnessPolicy = FreshnessPolicy(),
) -> LocationStatus:
    """Combine fresh facts using documented precedence without inferring safety."""
    overflows = _validated_stream_observation(overflows, now, policy.stream)
    advice = _validated_advice_observation(advice, now, policy.environment_agency)
    observations = (
        (overflows, policy.stream),
        (advice, policy.environment_agency),
        (regional_status, policy.regional),
    )
    fresh = {
        observation.source
        for observation, max_age in observations
        if observation is not None
        and observation.freshness(now, max_age) is Freshness.FRESH
    }
    stale = tuple(
        observation.source
        for observation, max_age in observations
        if observation is not None
        and observation.freshness(now, max_age) is Freshness.STALE
    )

    if (
        advice is not None
        and advice.source in fresh
        and any(record.risk_level is RiskLevel.INCREASED for record in advice.records)
    ):
        return LocationStatus(
            LocationStatusLevel.OFFICIAL_ADVICE,
            StatusProvenance.OFFICIAL_ADVICE,
            (advice.source,),
            stale,
        )

    if (
        regional_status is not None
        and regional_status.source in fresh
        and any(
            record.state
            in (
                RegionalSiteState.POSSIBLE_IMPACT_24H,
                RegionalSiteState.POSSIBLE_IMPACT_72H,
            )
            for record in regional_status.records
        )
    ):
        return LocationStatus(
            LocationStatusLevel.POSSIBLE_IMPACT,
            StatusProvenance.REPORTED,
            (regional_status.source,),
            stale,
        )

    if (
        overflows is not None
        and overflows.source in fresh
        and any(record.state is OverflowState.ACTIVE for record in overflows.records)
    ):
        return LocationStatus(
            LocationStatusLevel.OVERFLOW_REPORTED,
            StatusProvenance.REPORTED,
            (overflows.source,),
            stale,
        )

    clear_sources: set[str] = set()
    if (
        advice is not None
        and advice.source in fresh
        and all(record.risk_level is RiskLevel.NORMAL for record in advice.records)
    ):
        clear_sources.add(advice.source)
    if (
        overflows is not None
        and overflows.source in fresh
        and overflows.records
        and all(record.state is OverflowState.INACTIVE for record in overflows.records)
    ):
        clear_sources.add(overflows.source)
    if (
        regional_status is not None
        and regional_status.source in fresh
        and regional_status.records
        and all(
            record.state is RegionalSiteState.NO_REPORTED_IMPACT
            for record in regional_status.records
        )
    ):
        clear_sources.add(regional_status.source)

    if clear_sources:
        return LocationStatus(
            LocationStatusLevel.NO_CURRENT_ALERT,
            StatusProvenance.REPORTED,
            tuple(sorted(clear_sources)),
            stale,
        )

    return LocationStatus(
        LocationStatusLevel.UNKNOWN,
        StatusProvenance.UNKNOWN,
        (),
        stale,
    )


def _stale_observation(
    observation: SourceObservation,
    now: datetime,
    max_age: timedelta,
) -> SourceObservation:
    """Return an equivalent observation guaranteed to fail freshness checks."""
    return SourceObservation(
        observation.source,
        now - max_age - timedelta(microseconds=1),
        observation.records,
    )


def _validated_stream_observation(
    observation: SourceObservation[OverflowReport] | None,
    now: datetime,
    max_age: timedelta,
) -> SourceObservation[OverflowReport] | None:
    """Reject impossible Stream timestamps without treating event age as feed age.

    Stream's per-asset ``LastUpdated`` records the last asset change, not a feed
    heartbeat. An inactive asset can legitimately retain an old timestamp while
    a successful exact-ID query still asserts its current state.
    """
    if observation is None or not observation.records:
        return observation
    if any(
        record.updated_at is not None and record.updated_at > now
        for record in observation.records
    ):
        return _stale_observation(observation, now, max_age)
    return observation


def _validated_advice_observation(
    observation: SourceObservation[BathingAdvice] | None,
    now: datetime,
    max_age: timedelta,
) -> SourceObservation[BathingAdvice] | None:
    """Exclude expired EA situations and reject future-dated publications."""
    if observation is None:
        return None
    if any(
        record.published_at is not None and record.published_at > now
        for record in observation.records
    ):
        return _stale_observation(observation, now, max_age)
    current = tuple(
        record
        for record in observation.records
        if record.expires_at is None or record.expires_at > now
    )
    return SourceObservation(observation.source, observation.observed_at, current)
