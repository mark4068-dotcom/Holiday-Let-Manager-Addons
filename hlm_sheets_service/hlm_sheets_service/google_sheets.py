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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass
class GoogleSheetsSource:
    spreadsheet_id: str
    sheet_range: str
    credentials_path: str

    def _credentials(self) -> dict[str, Any]:
        return json.loads(Path(self.credentials_path).read_text(encoding="utf-8"))

    def _access_token(self) -> str:
        credentials = self._credentials()
        now = int(time.time())
        header = _base64url(b'{"alg":"RS256","typ":"JWT"}')
        claims = _base64url(
            json.dumps(
                {
                    "iss": credentials["client_email"],
                    "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
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
