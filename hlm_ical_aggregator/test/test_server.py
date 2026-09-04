from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
from aggregator import Aggregator, SourceConfig
from test_aggregator import calendar_bytes


class HttpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        source = SourceConfig("one", "One", "https://one.test/a.ics")
        server.OPTIONS = {
            "feed_username": "calendar",
            "feed_password": "secret",
        }
        server.AGGREGATOR = Aggregator(
            Path(self.temporary.name),
            [source],
            fetcher=lambda _url: calendar_bytes({"uid": "one", "summary": "Booking"}),
        )
        server.AGGREGATOR.refresh()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_status_health_authentication_and_refresh(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["state"], "healthy")

        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(f"{self.base_url}/combined.ics")
        self.assertEqual(raised.exception.code, 401)

        request = urllib.request.Request(f"{self.base_url}/combined.ics")
        request.add_header("Authorization", "Basic Y2FsZW5kYXI6c2VjcmV0")
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"BEGIN:VCALENDAR", response.read())

        refresh = urllib.request.Request(f"{self.base_url}/refresh", method="POST")
        refresh.add_header("Authorization", "Basic Y2FsZW5kYXI6c2VjcmV0")
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(refresh) as response:
            self.assertEqual(response.status, 200)

    def test_health_is_live_during_initial_setup(self) -> None:
        server.AGGREGATOR = Aggregator(Path(self.temporary.name) / "empty", [])
        with urllib.request.urlopen(f"{self.base_url}/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["state"], "setup")
