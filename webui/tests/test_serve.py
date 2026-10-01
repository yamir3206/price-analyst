"""Standard-library tests for the Persian UI launcher/proxy (no backend install needed)."""

from __future__ import annotations

import http.client
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import serve  # noqa: E402


class FakeBackend(BaseHTTPRequestHandler):
    last_body: bytes = b""
    last_headers: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802
        self._reply({"path": self.path, "method": "GET"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        FakeBackend.last_body = self.rfile.read(length)
        FakeBackend.last_headers = {k.lower(): v for k, v in self.headers.items()}
        self._reply({"path": self.path, "method": "POST"})

    def _reply(self, data: dict[str, str]) -> None:
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Request-ID", "abc-123")
        self.send_header("Set-Cookie", "should=not-forward")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        pass


def _start(server: ThreadingHTTPServer) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()


class ServeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backend = ThreadingHTTPServer(("127.0.0.1", 0), FakeBackend)
        _start(cls.backend)
        backend_url = f"http://127.0.0.1:{cls.backend.server_address[1]}"
        cls.ui = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(backend_url))
        _start(cls.ui)
        cls.port = cls.ui.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        for server in (cls.ui, cls.backend):
            server.shutdown()
            server.server_close()

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            res = conn.getresponse()
            return res.status, {k.lower(): v for k, v in res.getheaders()}, res.read()
        finally:
            conn.close()

    def test_index_served_with_security_headers(self) -> None:
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('dir="rtl"', body.decode())
        self.assertIn("default-src 'self'", headers["content-security-policy"])
        self.assertEqual(headers["x-frame-options"], "DENY")

    def test_python_sources_not_served(self) -> None:
        self.assertEqual(self.request("GET", "/serve.py")[0], 404)
        self.assertEqual(self.request("GET", "/tests/test_serve.py")[0], 404)

    def test_get_proxied(self) -> None:
        status, headers, body = self.request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"path": "/api/v1/health", "method": "GET"})
        self.assertEqual(headers["x-request-id"], "abc-123")
        self.assertNotIn("set-cookie", headers)

    def test_post_proxied_with_body(self) -> None:
        payload = json.dumps({"query": "لپ‌تاپ", "refresh": False}).encode()
        status, _, body = self.request(
            "POST", "/api/v1/searches", payload,
            {"Content-Type": "application/json", "Cookie": "secret=1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["method"], "POST")
        self.assertEqual(FakeBackend.last_body, payload)
        self.assertNotIn("cookie", FakeBackend.last_headers)

    def test_oversized_body_rejected(self) -> None:
        big = b"x" * (serve.MAX_REQUEST_BODY_BYTES + 1)
        status, _, _ = self.request("POST", "/api/v1/searches", big)
        self.assertEqual(status, 413)

    def test_post_outside_api_rejected(self) -> None:
        self.assertEqual(self.request("POST", "/index.html", b"{}")[0], 405)

    def test_non_v1_paths_not_proxied(self) -> None:
        self.assertEqual(self.request("GET", "/api/v2/anything")[0], 404)

    def test_unreachable_backend_returns_502(self) -> None:
        ui = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler("http://127.0.0.1:9"))
        _start(ui)
        try:
            conn = http.client.HTTPConnection("127.0.0.1", ui.server_address[1], timeout=10)
            conn.request("GET", "/api/v1/health")
            res = conn.getresponse()
            self.assertEqual(res.status, 502)
            self.assertEqual(json.loads(res.read())["detail"], "backend_unreachable")
        finally:
            ui.shutdown()
            ui.server_close()

    def test_invalid_backend_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            serve.make_handler("ftp://example.com")


if __name__ == "__main__":
    unittest.main()
