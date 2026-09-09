"""Source-aware normalised models for Coastal Water Watch."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class OverflowState(StrEnum):
    """Normalised operational state reported by a water company."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    """Normalised Environment Agency short-term pollution risk."""

    NORMAL = "normal"
    INCREASED = "increased"
    UNKNOWN = "unknown"


class ImpactState(StrEnum):
    """Normalised water-company modelled bathing-site impact."""

    IMPACTED = "impacted"
    NOT_IMPACTED = "not_impacted"
    UNKNOWN = "unknown"


class RegionalSiteState(StrEnum):
    """Southern Water's current bathing-site release window."""

    NO_REPORTED_IMPACT = "no_reported_impact"
    POSSIBLE_IMPACT_72H = "possible_impact_72h"
    POSSIBLE_IMPACT_24H = "possible_impact_24h"
    UNKNOWN = "unknown"


class Freshness(StrEnum):
    """Whether a successful source observation is recent enough to use."""

    FRESH = "fresh"
    STALE = "stale"


class StatusProvenance(StrEnum):
    """Origin of an aggregate location conclusion."""

    REPORTED = "reported"
    OFFICIAL_ADVICE = "official_advice"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class LocationStatusLevel(StrEnum):
    """Source-aware aggregate state; deliberately contains no `safe` value."""

    OFFICIAL_ADVICE = "official_advice"
    POSSIBLE_IMPACT = "possible_impact"
    OVERFLOW_REPORTED = "overflow_reported"
    NO_CURRENT_ALERT = "no_current_alert"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceObservation(Generic[T]):
    """Records returned by one successful request and when they were observed."""

    source: str
    observed_at: datetime
    records: tuple[T, ...]

    def freshness(self, now: datetime, max_age: timedelta) -> Freshness:
        """Classify this observation against a caller-selected source policy."""
        age = now - self.observed_at
        return Freshness.FRESH if timedelta(0) <= age <= max_age else Freshness.STALE


@dataclass(frozen=True, slots=True)
class LocationStatus:
    """Aggregate conclusion for one bathing location."""

    level: LocationStatusLevel
    provenance: StatusProvenance
    sources: tuple[str, ...]
    stale_sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OverflowReport:
    """One nationally standardised water-company overflow report."""

    source: str
    asset_id: str
    company: str
    receiving_water: str | None
    state: OverflowState
    state_started_at: datetime | None
    updated_at: datetime | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True, slots=True)
class BathingAdvice:
    """Official Environment Agency advice for one bathing water."""

    source: str
    bathing_water_id: str
    bathing_water_name: str | None
    risk_level: RiskLevel
    advice: str | None
    published_at: datetime | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class RegionalImpactReport:
    """A regional water-company release and modelled impact conclusion."""

    source: str
    event_id: str
    bathing_site_id: str
    bathing_site_name: str | None
    outfall_id: str | None
    outfall_name: str | None
    state: ImpactState
    review_status: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    model_version: str | None


@dataclass(frozen=True, slots=True)
class RegionalBathingSiteStatus:
    """Current regional bathing-site status, separate from release history."""

    source: str
    bathing_site_id: str
    bathing_site_name: str | None
    bathing_water_id: str | None
    state: RegionalSiteState
    message: str | None
    ea_classification: str | None
    ea_classification_year: int | None
