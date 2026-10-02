"""Zero-dependency launcher for the Persian web UI.

Serves the static files in this directory and reverse-proxies ``/api/v1/...``
to the FastAPI backend so the browser only ever talks to one same-origin URL
(no CORS changes, no ``localhost`` calls from browser code).

Only the Python standard library is used. Optionally starts the backend
(``uvicorn``) as a child process with ``--start-backend``.

Usage::

    python webui/serve.py          # UI on 127.0.0.1:8080, backend expected on :8000
    python webui/serve.py --start-backend --open
    python webui/serve.py --backend http://127.0.0.1:9000 --port 8081
"""

from __future__ import annotations

import argparse
import http.client
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEBUI_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEBUI_DIR.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"

API_PREFIX = "/api/v1/"
MAX_REQUEST_BODY_BYTES = 64 * 1024  # API request bodies are tiny ({"query", "refresh"})
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
PROXY_TIMEOUT_SECONDS = 180.0  # searches with several live sources/AI can be slow
FORWARDED_REQUEST_HEADERS = ("content-type", "accept", "x-request-id")
FORWARDED_RESPONSE_HEADERS = (
    "content-type",
    "x-request-id",
    "cache-control",
    "x-content-type-options",
    "referrer-policy",
)

STATIC_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    # Offer images are external HTTPS URLs; everything else is same-origin.
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' https: data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"
    ),
}


class UIRequestHandler(SimpleHTTPRequestHandler):
    backend: urllib.parse.SplitResult  # set on the subclass in make_handler()

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(WEBUI_DIR), **kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ routing
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self._is_api():
            self._proxy("GET")
            return
        path = urllib.parse.urlsplit(self.path).path
        if path.endswith(".py") or "/tests" in path or path.startswith("/__"):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if self._is_api():
            self.send_error(405)
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        if not self._is_api():
            self.send_error(405)
            return
        self._proxy("POST")

    def end_headers(self) -> None:
        if not self._is_api():
            for name, value in STATIC_SECURITY_HEADERS.items():
                self.send_header(name, value)
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        sys.stderr.write(f"[ui] {self.address_string()} {format % args}\n")

    # ------------------------------------------------------------------ proxy
    def _is_api(self) -> bool:
        return urllib.parse.urlsplit(self.path).path.startswith(API_PREFIX)

    def _proxy(self, method: str) -> None:
        split = urllib.parse.urlsplit(self.path)
        if ".." in split.path or "\\" in split.path:
            self.send_error(400)
            return
        body = b""
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length < 0 or length > MAX_REQUEST_BODY_BYTES:
                self.send_error(413)
                return
            body = self.rfile.read(length)

        headers = {
            name: self.headers[name]
            for name in FORWARDED_REQUEST_HEADERS
            if self.headers.get(name) is not None
        }
        target = split.path + (f"?{split.query}" if split.query else "")
        backend = self.backend
        conn_cls = (
            http.client.HTTPSConnection if backend.scheme == "https" else http.client.HTTPConnection
        )
        conn = conn_cls(backend.netloc, timeout=PROXY_TIMEOUT_SECONDS)
        try:
            conn.request(
                method, backend.path.rstrip("/") + target, body=body or None, headers=headers
            )
            response = conn.getresponse()
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                self._json_error(502, "backend_response_too_large")
                return
            self.send_response(response.status)
            for name in FORWARDED_RESPONSE_HEADERS:
                value = response.getheader(name)
                if value is not None:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (OSError, http.client.HTTPException):
            self._json_error(502, "backend_unreachable")
        finally:
            conn.close()

    def _json_error(self, status: int, code: str) -> None:
        payload = f'{{"detail":"{code}"}}'.encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class UIServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a socket share a port another program already
    # uses, so it is disabled there and binding fails loudly instead.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def port_is_bindable(host: str, port: int) -> bool:
    """True if ``host:port`` can be bound right now.

    Catches ports in use and, on Windows, ports in reserved/excluded ranges
    (Hyper-V, WSL, Docker), which fail with WinError 10013.
    """
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)  # Windows only
        if exclusive is not None:
            probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def free_port(host: str) -> int:
    """Ask the OS for a currently free port (never inside a reserved range)."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def choose_port(host: str, preferred: int, what: str) -> int:
    if preferred and port_is_bindable(host, preferred):
        return preferred
    port = free_port(host)
    print(
        f"[ui] port {preferred} is unavailable for the {what} (in use or reserved by "
        f"Windows); using port {port} instead."
    )
    return port


def make_handler(backend_url: str) -> type[UIRequestHandler]:
    parsed = urllib.parse.urlsplit(backend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--backend must be an http(s) URL such as http://127.0.0.1:8000")
    return type("ConfiguredUIRequestHandler", (UIRequestHandler,), {"backend": parsed})


def start_backend(host: str, port: int) -> subprocess.Popen[bytes]:
    """Start uvicorn with the current interpreter (run from the repo root so .env is read)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(BACKEND_SRC), env.get("PYTHONPATH")]))
    command = [
        sys.executable, "-m", "uvicorn", "price_analyst.main:app",
        "--app-dir", str(BACKEND_SRC), "--host", host, "--port", str(port),
        "--no-use-colors",  # plain cmd.exe windows would show raw ANSI codes
    ]
    print(f"[ui] starting backend: {' '.join(command)}")
    return subprocess.Popen(command, cwd=str(REPO_ROOT), env=env)


def wait_for_backend(backend_url: str, process: subprocess.Popen[bytes], timeout: float) -> bool:
    parsed = urllib.parse.urlsplit(backend_url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            conn = http.client.HTTPConnection(parsed.netloc, timeout=2)
            conn.request("GET", "/api/v1/health")
            if conn.getresponse().status == 200:
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def launch_backend(preferred_port: int) -> tuple[subprocess.Popen[bytes] | None, str]:
    """Start uvicorn on a usable port, retrying on a fresh port if binding fails."""
    port = choose_port("127.0.0.1", preferred_port, "backend")
    for attempt in range(3):
        url = f"http://127.0.0.1:{port}"
        process = start_backend("127.0.0.1", port)
        if wait_for_backend(url, process, timeout=60):
            return process, url
        if process.poll() is None:  # running but never healthy: a real problem
            process.terminate()
            break
        if attempt < 2:
            port = free_port("127.0.0.1")
            print(f"[ui] backend could not start; retrying on port {port} ...")
    print("[ui] backend did not become healthy; check the log above.", file=sys.stderr)
    return None, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Price Analyst Persian web UI")
    parser.add_argument("--host", default="127.0.0.1",
                        help="UI bind address (default 127.0.0.1; the API has no auth)")
    parser.add_argument("--port", type=int, default=8080, help="UI port (default 8080)")
    parser.add_argument("--backend", default=None,
                        help="backend base URL (default http://127.0.0.1:<backend-port>)")
    parser.add_argument("--start-backend", action="store_true",
                        help="also start the FastAPI backend with uvicorn")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="open the UI in the default browser")
    args = parser.parse_args(argv)
    # Show launcher messages immediately and in order with uvicorn's output.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(line_buffering=True)

    backend_process: subprocess.Popen[bytes] | None = None
    if args.start_backend and args.backend is None:
        backend_process, backend_url = launch_backend(args.backend_port)
        if backend_process is None:
            return 1
    else:
        backend_url = args.backend or f"http://127.0.0.1:{args.backend_port}"
        if args.start_backend:
            print("[ui] --backend was given, so --start-backend is ignored.", file=sys.stderr)
    handler = make_handler(backend_url)

    ui_port = choose_port(args.host, args.port, "web UI")
    try:
        server = UIServer((args.host, ui_port), handler)
    except OSError:
        ui_port = free_port(args.host)
        print(f"[ui] could not bind the web UI port; using port {ui_port} instead.")
        server = UIServer((args.host, ui_port), handler)
    shown_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{shown_host}:{ui_port}/"
    print(f"[ui] Persian UI:  {url}")
    print(f"[ui] backend API: {backend_url}  (proxied at {API_PREFIX})")
    print("[ui] press Ctrl+C to stop")
    if args.open:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()

    def shutdown(*_: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if backend_process is not None and backend_process.poll() is None:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
