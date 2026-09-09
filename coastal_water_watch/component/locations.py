"""Supported bathing locations and their official source identifiers."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BathingLocation:
    """Identifiers needed to update one bathing-water location."""

    key: str
    name: str
    company_key: str
    bathing_water_id: str
    stream_asset_ids: tuple[str, ...]
    regional_bathing_site_id: str | None = None
    mapping_status: str = "official"


def _load_locations() -> dict[str, BathingLocation]:
    """Load the generated, reviewed-only Home Assistant catalogue."""
    path = Path(__file__).with_name("catalogue.json")
    records = json.loads(path.read_text(encoding="utf-8"))["locations"]
    return {
        record["key"]: BathingLocation(
            key=record["key"],
            name=record["name"],
            company_key=record["company_key"],
            bathing_water_id=record["bathing_water_id"],
            stream_asset_ids=tuple(record["stream_asset_ids"]),
            regional_bathing_site_id=record.get("regional_bathing_site_id"),
            mapping_status=record.get("mapping_status", "official"),
        )
        for record in records
        if record["verification_status"] == "verified"
    }


LOCATIONS = _load_locations()
