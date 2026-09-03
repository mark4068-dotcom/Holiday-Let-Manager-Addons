"""Environment-backed configuration for the Sheets wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    spreadsheet_id: str
    sheet_range: str
    v1_1_sheet_range: str
    api_token: str
    credentials_path: str
    host: str
    port: int
    event_write_enabled: bool = False
    event_write_token: str = ""
    writer_credentials_path: str = ""
    event_sheet_range: str = "30_hlm_events!A:AG"

    @classmethod
    def from_env(cls) -> "Settings":
        api_token = os.environ.get("HLM_SHEETS_API_TOKEN", "")
        if len(api_token) < 32:
            raise ValueError("HLM_SHEETS_API_TOKEN must contain at least 32 characters")

        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS must be configured")

        event_write_enabled = os.environ.get("HLM_EVENT_WRITE_ENABLED", "false") == "true"
        event_write_token = os.environ.get("HLM_EVENT_WRITE_TOKEN", "")
        writer_credentials_path = os.environ.get(
            "HLM_EVENT_WRITER_CREDENTIALS", ""
        )
        if event_write_enabled and len(event_write_token) < 32:
            raise ValueError("HLM_EVENT_WRITE_TOKEN must contain at least 32 characters")
        if event_write_enabled and not writer_credentials_path:
            raise ValueError("HLM_EVENT_WRITER_CREDENTIALS must be configured")

        return cls(
            spreadsheet_id=os.environ["HLM_SHEETS_SPREADSHEET_ID"],
            sheet_range=os.environ["HLM_SHEETS_STATUS_RANGE"],
            v1_1_sheet_range=os.environ["HLM_SHEETS_V1_1_STATUS_RANGE"],
            api_token=api_token,
            credentials_path=credentials_path,
            host=os.environ.get("HLM_SHEETS_HOST", "0.0.0.0"),
            port=int(os.environ.get("HLM_SHEETS_PORT", "8787")),
            event_write_enabled=event_write_enabled,
            event_write_token=event_write_token,
            writer_credentials_path=writer_credentials_path,
            event_sheet_range=os.environ.get(
                "HLM_EVENT_SHEET_RANGE", "30_hlm_events!A:AG"
            ),
        )
