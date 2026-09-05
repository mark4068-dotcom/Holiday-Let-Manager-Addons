"""Minimal private Google Sheets reader using service-account OAuth."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .events import SHEET_DATETIME_COLUMN_INDEXES


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass
class GoogleSheetsSource:
    spreadsheet_id: str
    sheet_range: str
    credentials_path: str

    def _credentials(self) -> dict[str, Any]:
        return json.loads(Path(self.credentials_path).read_text(encoding="utf-8"))

    def _access_token(
        self, scope: str = "https://www.googleapis.com/auth/spreadsheets.readonly"
    ) -> str:
        credentials = self._credentials()
        now = int(time.time())
        header = _base64url(b'{"alg":"RS256","typ":"JWT"}')
        claims = _base64url(
            json.dumps(
                {
                    "iss": credentials["client_email"],
                    "scope": scope,
                    "aud": credentials.get(
                        "token_uri", "https://oauth2.googleapis.com/token"
                    ),
                    "iat": now,
                    "exp": now + 3600,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
        unsigned = f"{header}.{claims}".encode("ascii")

        key_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        try:
            os.chmod(key_file.name, 0o600)
            key_file.write(credentials["private_key"])
            key_file.close()
            signed = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", key_file.name],
                input=unsigned,
                check=True,
                capture_output=True,
            ).stdout
        finally:
            try:
                os.unlink(key_file.name)
            except FileNotFoundError:
                pass

        assertion = f"{header}.{claims}.{_base64url(signed)}"
        body = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            }
        ).encode("ascii")
        request = urllib.request.Request(
            credentials.get("token_uri", "https://oauth2.googleapis.com/token"),
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)["access_token"]

    def read_rows(self) -> list[list[Any]]:
        encoded_range = urllib.parse.quote(self.sheet_range, safe="")
        query = urllib.parse.urlencode(
            {
                "majorDimension": "ROWS",
                "valueRenderOption": "FORMATTED_VALUE",
                "dateTimeRenderOption": "FORMATTED_STRING",
            }
        )
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{urllib.parse.quote(self.spreadsheet_id, safe='')}/values/"
            f"{encoded_range}?{query}"
        )
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self._access_token()}"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response).get("values", [])


@dataclass
class GoogleSheetsEventWriter(GoogleSheetsSource):
    """Append validated rows and inspect immutable event IDs."""

    _WRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
    _datetime_format_applied: bool = field(default=False, init=False, repr=False)

    def _sheet_id(self) -> int:
        sheet_title = self.sheet_range.split("!", 1)[0].strip("'")
        spreadsheet = urllib.parse.quote(self.spreadsheet_id, safe="")
        query = urllib.parse.urlencode({"fields": "sheets.properties(sheetId,title)"})
        request = urllib.request.Request(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet}?{query}",
            headers={
                "Authorization": f"Bearer {self._access_token(self._WRITE_SCOPE)}"
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            sheets = json.load(response).get("sheets", [])
        for sheet in sheets:
            properties = sheet.get("properties", {})
            if properties.get("title") == sheet_title:
                return int(properties["sheetId"])
        raise ValueError(f"Event worksheet {sheet_title!r} was not found")

    def ensure_datetime_format(self) -> None:
        """Give numeric event timestamps an explicit UK date/time display."""
        if self._datetime_format_applied:
            return
        sheet_id = self._sheet_id()
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": column,
                        "endColumnIndex": column + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "DATE_TIME",
                                "pattern": "dd/mm/yyyy hh:mm:ss",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
            for column in SHEET_DATETIME_COLUMN_INDEXES
        ]
        spreadsheet = urllib.parse.quote(self.spreadsheet_id, safe="")
        request = urllib.request.Request(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet}:batchUpdate",
            data=json.dumps({"requests": requests}).encode(),
            headers={
                "Authorization": f"Bearer {self._access_token(self._WRITE_SCOPE)}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20):
            self._datetime_format_applied = True

    def existing_event_ids(self) -> set[str]:
        id_range = self.sheet_range.split("!", 1)[0] + "!B2:B"
        encoded_range = urllib.parse.quote(id_range, safe="")
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{urllib.parse.quote(self.spreadsheet_id, safe='')}/values/"
            f"{encoded_range}?majorDimension=COLUMNS"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._access_token(self._WRITE_SCOPE)}"
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            columns = json.load(response).get("values", [])
        return set(columns[0]) if columns else set()

    def append_rows(self, rows: list[list[Any]]) -> None:
        if not rows:
            return
        self.ensure_datetime_format()
        encoded_range = urllib.parse.quote(self.sheet_range, safe="")
        query = urllib.parse.urlencode(
            {"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}
        )
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{urllib.parse.quote(self.spreadsheet_id, safe='')}/values/"
            f"{encoded_range}:append?{query}"
        )
        request = urllib.request.Request(
            url,
            data=json.dumps({"majorDimension": "ROWS", "values": rows}).encode(),
            headers={
                "Authorization": f"Bearer {self._access_token(self._WRITE_SCOPE)}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20):
            return
