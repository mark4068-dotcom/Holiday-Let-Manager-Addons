"""Exercise fail-closed behavior through both deployed HTTP contracts."""

import threading
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import pytest
from test_parallel_audit import fixture

from hlm_sheets_service.app import make_server
from hlm_sheets_service.config import Settings
from hlm_sheets_service.status import V1_1_HEADERS


@pytest.mark.parametrize("fault", ["stale", "future", "missing_property", "source_error"])
def test_both_status_endpoints_reject_source_faults(fault):
    data = fixture()[1]
    stamp_index = V1_1_HEADERS.index("source_updated_at")
    now = datetime.now(timezone.utc)
    for row in data[1:]:
        row[stamp_index] = now.isoformat()
    if fault == "stale":
        data[1][stamp_index] = (now - timedelta(seconds=901)).isoformat()
    elif fault == "future":
        data[1][stamp_index] = (now + timedelta(seconds=180)).isoformat()
    elif fault == "missing_property":
        data.pop()
    else:
        data[1][stamp_index] = "#N/A"
    settings = Settings("sheet", "old", "new", "a" * 32, "unused", "127.0.0.1", 0,
                        production_feed=True)
    server = make_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with patch("hlm_sheets_service.google_sheets.GoogleSheetsSource.read_rows",
                   return_value=data):
            for version in ("v1", "v1.1"):
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/api/{version}/status",
                    headers={"Authorization": "Bearer " + "a" * 32},
                )
                with pytest.raises(HTTPError) as error:
                    urlopen(request, timeout=10)
                assert error.value.code == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
