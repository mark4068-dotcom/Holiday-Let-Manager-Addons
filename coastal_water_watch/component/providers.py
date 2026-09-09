"""Catalogue of providers implementing the national Water UK Stream contract."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class StreamProvider:
    """One water company layer published through the Stream contract."""

    key: str
    company: str
    company_number: str | None
    layer_url: str
    verified: bool = False


def _load_providers() -> dict[str, StreamProvider]:
    records = json.loads(
        Path(__file__).with_name("providers.json").read_text(encoding="utf-8")
    )["providers"]
    return {
        record["key"]: StreamProvider(
            key=record["key"],
            company=record["company"],
            company_number=record["company_number"],
            layer_url=record["layer_url"],
            verified=record["verified"],
        )
        for record in records
    }


STREAM_PROVIDERS = _load_providers()


def get_stream_provider(company_key: str) -> StreamProvider:
    """Return a registered provider, raising a useful error for unknown keys."""
    try:
        return STREAM_PROVIDERS[company_key]
    except KeyError as err:
        raise ValueError(f"Unknown Stream provider: {company_key}") from err
