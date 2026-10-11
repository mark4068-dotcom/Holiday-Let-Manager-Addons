import json
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from test_parallel_audit import fixture

from hlm_sheets_service.app import make_server
from hlm_sheets_service.config import Settings
from hlm_sheets_service.status import V1_1_HEADERS, V1_HEADERS


def test_both_versions_use_new_feed_and_reject_stale_data():
    settings = Settings(
        "sheet", "old", "new", "a" * 32, "unused", "127.0.0.1", 0, production_feed=True
    )
    data = fixture()[1]
    stamp_index = V1_1_HEADERS.index("source_updated_at")
    for row in data[1:]:
        row[stamp_index] = datetime.now(timezone.utc).isoformat()
    seen = []

    def read(source):
        seen.append(source.sheet_range)
        return data

    server = make_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    headers = {"Authorization": "Bearer " + "a" * 32}
    try:
        with patch(
            "hlm_sheets_service.google_sheets.GoogleSheetsSource.read_rows", read
        ):
            for version in ("v1", "v1.1"):
                url = f"http://127.0.0.1:{server.server_port}/api/{version}/status"
                with pytest.raises(HTTPError) as error:
                    urlopen(url)
                assert error.value.code == 401
                with urlopen(Request(url, headers=headers)) as response:
                    body = json.load(response)
                assert body["version"] == ("1.0" if version == "v1" else "1.1")
                expected = V1_HEADERS if version == "v1" else V1_1_HEADERS
                assert set(body["properties"]["skysail"]) == set(expected)
            assert seen == ["new", "new"]
            data[1][stamp_index] = (
                datetime.now(timezone.utc) - timedelta(minutes=16)
            ).isoformat()
            for version in ("v1", "v1.1"):
                with pytest.raises(HTTPError) as error:
                    urlopen(
                        Request(
                            f"http://127.0.0.1:{server.server_port}/api/{version}/status",
                            headers=headers,
                        )
                    )
                assert error.value.code == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
