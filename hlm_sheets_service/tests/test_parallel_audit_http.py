"""Ensure audit detail stays behind the existing private read token."""

import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from hlm_sheets_service.app import make_server
from hlm_sheets_service.config import Settings


class AuditHTTPTest(unittest.TestCase):
    def test_authentication_daily_validation_and_no_worker_in_factory(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                "sheet",
                "live",
                "v1.1",
                "a" * 32,
                "unused",
                "127.0.0.1",
                0,
                parallel_audit_enabled=True,
                parallel_audit_directory=directory,
            )
            server = make_server(settings)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}/api/v1.1/parallel-audit"
            try:
                for suffix in ("", "/2026-09-12"):
                    with self.assertRaises(HTTPError) as context:
                        urlopen(base + suffix)
                    self.assertEqual(context.exception.code, 401)
                headers = {"Authorization": "Bearer " + "a" * 32}
                with urlopen(Request(base, headers=headers)) as response:
                    report = json.load(response)
                self.assertTrue(report["audit_stale"])
                self.assertEqual(report["counts"], {})
                with self.assertRaises(HTTPError) as context:
                    urlopen(Request(base + "/bad-date", headers=headers))
                self.assertEqual(context.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
