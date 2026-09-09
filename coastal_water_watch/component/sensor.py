"""Sensors for Coastal Water Watch."""

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CoastalWaterWatchCoordinator
from .entity_values import (
    advice_state,
    current_advice_records,
    latest_impacting_release,
    latest_regional_state,
    overflow_state,
    regional_site_state,
    stream_data_is_current,
)
from .models import LocationStatusLevel
from .source_health import SourceSnapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up aggregate, source-detail and source-health sensors."""
    coordinator: CoastalWaterWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        CoastalWaterWatchStatusSensor(coordinator),
        AdviceStateSensor(coordinator),
        SourceHealthSensor(
            coordinator, "environment_agency", "Environment Agency freshness"
        ),
    ]
    if coordinator.location.stream_asset_ids:
        entities.extend(
            [
                OverflowStateSensor(coordinator),
                SourceHealthSensor(coordinator, "stream", "Stream freshness"),
            ]
        )
    if coordinator.data.regional_impacts is not None:
        entities.extend(
            [
                RegionalEventSensor(coordinator),
                LatestImpactingReleaseSensor(coordinator),
                RegionalStatusSensor(coordinator),
                SourceHealthSensor(
                    coordinator, "regional", "Regional history freshness"
                ),
                SourceHealthSensor(
                    coordinator, "regional_status", "Regional status freshness"
                ),
            ]
        )
    async_add_entities(entities)


class CoastalWaterWatchSensorBase(
    CoordinatorEntity[CoastalWaterWatchCoordinator], SensorEntity
):
    """Common device metadata for location sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        location = coordinator.location
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, location.key)},
            name=location.name,
            manufacturer="Coastal Water Watch",
            model="Bathing-water location",
            configuration_url=(
                "https://environment.data.gov.uk/doc/bathing-water/"
                f"{location.bathing_water_id}"
            ),
        )


class CoastalWaterWatchStatusSensor(CoastalWaterWatchSensorBase):
    """Aggregate source-aware status for one bathing location."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:waves-arrow-up"
    _attr_translation_key = "status"
    _attr_options = [level.value for level in LocationStatusLevel]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_status"

    @property
    def native_value(self) -> str:
        """Return the aggregate status level."""
        return self.coordinator.data.status.level.value

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose aggregate provenance and source health."""
        data = self.coordinator.data
        return {
            "provenance": data.status.provenance.value,
            "sources": list(data.status.sources),
            "stale_sources": list(data.status.stale_sources),
            "mapping_status": self.coordinator.location.mapping_status,
            "linked_stream_assets": len(
                self.coordinator.location.stream_asset_ids
            ),
            "updated_at": data.updated_at.isoformat(),
        }


class OverflowStateSensor(CoastalWaterWatchSensorBase):
    """National Stream state for associated overflow records."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:pipe-leak"
    _attr_translation_key = "overflow_state"
    _attr_options = ["active", "offline", "unknown", "inactive", "no_data"]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_overflow_state"

    @property
    def native_value(self) -> str:
        records = self.coordinator.data.overflows.records
        if records and not stream_data_is_current(records, datetime.now(UTC)):
            return "unknown"
        return overflow_state(records)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.data.overflows
        active = [
            record for record in snapshot.records if record.state.value == "active"
        ]
        source_updated_at = max(
            (
                record.updated_at
                for record in snapshot.records
                if record.updated_at is not None
            ),
            default=None,
        )
        return {
            **snapshot.attributes(),
            "active_assets": [record.asset_id for record in active],
            "assets": [record.asset_id for record in snapshot.records],
            "source_updated_at": _iso(source_updated_at),
            "source_data_age_minutes": (
                max(
                    0,
                    round(
                        (datetime.now(UTC) - source_updated_at).total_seconds() / 60
                    ),
                )
                if source_updated_at is not None
                else None
            ),
        }


class AdviceStateSensor(CoastalWaterWatchSensorBase):
    """Official Environment Agency advice state."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:shield-alert"
    _attr_translation_key = "environment_agency_advice"
    _attr_options = ["increased", "normal", "unknown", "no_current_advice"]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_ea_advice"

    @property
    def native_value(self) -> str:
        records = current_advice_records(
            self.coordinator.data.advice.records, datetime.now(UTC)
        )
        return advice_state(records)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.data.advice
        records = current_advice_records(snapshot.records, datetime.now(UTC))
        latest = records[0] if records else None
        return {
            **snapshot.attributes(),
            "bathing_water": latest.bathing_water_name if latest else None,
            "risk_level": latest.risk_level.value if latest else None,
            "advice": latest.advice if latest else None,
            "published_at": _iso(latest.published_at) if latest else None,
            "expires_at": _iso(latest.expires_at) if latest else None,
        }


class RegionalEventSensor(CoastalWaterWatchSensorBase):
    """State of the newest optional regional history record."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:history"
    _attr_translation_key = "latest_regional_event"
    _attr_options = ["impacted", "not_impacted", "unknown", "no_events"]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_regional_event"

    @property
    def native_value(self) -> str:
        snapshot = self.coordinator.data.regional_impacts
        return latest_regional_state(snapshot.records if snapshot else ())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.data.regional_impacts
        if snapshot is None:
            return {}
        latest = snapshot.records[0] if snapshot.records else None
        return {
            **snapshot.attributes(),
            "event_id": latest.event_id if latest else None,
            "outfall": latest.outfall_name if latest else None,
            "review_status": latest.review_status if latest else None,
            "started_at": _iso(latest.started_at) if latest else None,
            "ended_at": _iso(latest.ended_at) if latest else None,
            "model_version": latest.model_version if latest else None,
        }


class LatestImpactingReleaseSensor(CoastalWaterWatchSensorBase):
    """Newest Southern Water release reported as impacting this bathing site."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:waves-arrow-right"
    _attr_translation_key = "latest_impacting_release"
    _attr_options = ["impacted", "no_events"]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_latest_impacting_release"

    @property
    def _release(self):
        snapshot = self.coordinator.data.latest_impacting_release
        return latest_impacting_release(snapshot.records if snapshot else ())

    @property
    def native_value(self) -> str:
        return "impacted" if self._release is not None else "no_events"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.data.latest_impacting_release
        release = self._release
        if snapshot is None:
            return {}
        return {
            **snapshot.attributes(),
            "event_id": release.event_id if release else None,
            "outfall": release.outfall_name if release else None,
            "started_at": _iso(release.started_at) if release else None,
            "ended_at": _iso(release.ended_at) if release else None,
            "duration_seconds": release.duration_seconds if release else None,
            "review_status": release.review_status if release else None,
            "model_version": release.model_version if release else None,
        }


class RegionalStatusSensor(CoastalWaterWatchSensorBase):
    """Southern Water's current 24/72-hour bathing-site status."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:waves"
    _attr_translation_key = "regional_bathing_site_status"
    _attr_options = [
        "possible_impact_24h",
        "possible_impact_72h",
        "no_reported_impact",
        "unknown",
        "no_data",
    ]

    def __init__(self, coordinator: CoastalWaterWatchCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.location.key}_regional_status"

    @property
    def native_value(self) -> str:
        snapshot = self.coordinator.data.regional_status
        return regional_site_state(snapshot.records if snapshot else ())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.data.regional_status
        if snapshot is None:
            return {}
        current = snapshot.records[0] if snapshot.records else None
        return {
            **snapshot.attributes(),
            "message": current.message if current else None,
            "ea_classification": (current.ea_classification if current else None),
            "ea_classification_year": (
                current.ea_classification_year if current else None
            ),
        }


class SourceHealthSensor(CoastalWaterWatchSensorBase):
    """Health and freshness timestamps for one upstream source."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:cloud-check-outline"
    _attr_options = ["ok", "error", "unknown"]

    def __init__(
        self,
        coordinator: CoastalWaterWatchCoordinator,
        source_key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._source_key = source_key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.location.key}_{source_key}_health"

    @property
    def _snapshot(self) -> SourceSnapshot[Any] | None:
        data = self.coordinator.data
        return {
            "stream": data.overflows,
            "environment_agency": data.advice,
            "regional": data.regional_impacts,
            "regional_status": data.regional_status,
            "latest_impacting_release": data.latest_impacting_release,
        }[self._source_key]

    @property
    def native_value(self) -> str:
        snapshot = self._snapshot
        return snapshot.health.value if snapshot else "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self._snapshot
        return snapshot.attributes() if snapshot else {}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
