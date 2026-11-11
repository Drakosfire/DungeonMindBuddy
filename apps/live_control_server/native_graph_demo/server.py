"""Narrow same-origin, loopback-only HTTP transport for the isolated native demo.

This module deliberately does not import the normal Buddy application/config.
"""

from __future__ import annotations

from hmac import compare_digest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit

MAX_BODY_BYTES = 4096
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ASSET_BYTES = 8 * 1024 * 1024


class DemoHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    request_queue_size = 8

    def __init__(self, port: int, service, assets: Path):
        if not 0 <= port <= 65535:
            raise ValueError("invalid loopback port")
        self.service = service
        self.assets = assets.resolve(strict=True)
        if not self.assets.is_dir():
            raise ValueError("built demo assets must be a directory")
        self.capability = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(("127.0.0.1", port), DemoHandler)
        self.authority = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.authority}"

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class DemoHandler(BaseHTTPRequestHandler):
    server: DemoHTTPServer
    protocol_version = "HTTP/1.0"
    server_version = "DungeonMindNativeDemo"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        # A request path can contain user content or guessed capabilities. Keep
        # transport logs out of ordinary application logs and never echo paths.
        return

    def _send(
        self, status, body: bytes, content_type="application/json; charset=utf-8"
    ):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, value):
        body = json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()
        if len(body) > MAX_RESPONSE_BYTES:
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "response_limit",
                "Demo readback exceeded its response limit.",
            )
            return
        self._send(status, body)

    def _error(self, status, code, message):
        self._send(status, json.dumps({"error": message, "code": code}).encode())

    def _guard(self, *, api=False, mutation=False):
        if self.client_address[0] != "127.0.0.1" or self.headers.get_all("Host") != [
            self.server.authority
        ]:
            self._error(
                HTTPStatus.FORBIDDEN,
                "host_denied",
                "This demo accepts its exact loopback address only.",
            )
            return False
        top_level_entry = (
            not api
            and not mutation
            and self._path() in ("/", "/native-demo.html")
            and self.headers.get("Sec-Fetch-Mode") == "navigate"
            and self.headers.get("Sec-Fetch-Dest") == "document"
            and self.headers.get("Origin") is None
        )
        if (
            self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none")
            and not top_level_entry
        ):
            self._error(
                HTTPStatus.FORBIDDEN,
                "origin_denied",
                "Cross-site access is not permitted.",
            )
            return False
        origins = self.headers.get_all("Origin")
        if origins is not None and origins != [self.server.origin]:
            self._error(
                HTTPStatus.FORBIDDEN,
                "origin_denied",
                "The request origin does not match this demo.",
            )
            return False
        if mutation and origins != [self.server.origin]:
            self._error(
                HTTPStatus.FORBIDDEN,
                "origin_required",
                "Mutations require the demo origin.",
            )
            return False
        if api:
            tokens = self.headers.get_all("X-Demo-Capability")
            if (
                tokens is None
                or len(tokens) != 1
                or not compare_digest(
                    tokens[0].encode(), self.server.capability.encode()
                )
            ):
                self._error(
                    HTTPStatus.FORBIDDEN,
                    "capability_required",
                    "Reload this demo to establish the current session.",
                )
                return False
        return True

    def _path(self):
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            return None
        return parsed.path

    def _dispatch(self, operation):
        from .service import DemoError

        try:
            self._json(HTTPStatus.OK, operation())
        except DemoError as exc:
            self._error(exc.status, exc.code, str(exc))
        except Exception:
            # Persistence errors can contain connection information. Never expose
            # driver errors or guess that an unknown native outcome failed.
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "outcome_unavailable",
                "Native readback is unavailable. Preserve this operation and check its status before trying again.",
            )

    def do_GET(self):
        path = self._path()
        if path is None:
            self._error(
                HTTPStatus.BAD_REQUEST,
                "invalid_path",
                "Queries and alternate origins are not supported.",
            )
            return
        api = path.startswith("/api/")
        if not self._guard(api=api):
            return
        if path == "/api/graph":
            self._dispatch(self.server.service.graph)
        elif path.startswith("/api/operations/"):
            operation_id = path.removeprefix("/api/operations/")
            self._dispatch(lambda: self.server.service.operation(operation_id))
        elif api:
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Unknown demo operation.")
        else:
            self._asset(path)

    def _asset(self, path):
        if path in ("/", "/native-demo.html"):
            relative = "native-demo.html"
        elif path.startswith("/assets/") and "%" not in path and "\\" not in path:
            relative = path.lstrip("/")
        else:
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Unknown demo asset.")
            return
        candidate = (self.server.assets / relative).resolve()
        if (
            not candidate.is_relative_to(self.server.assets)
            or not candidate.is_file()
            or candidate.stat().st_size > MAX_ASSET_BYTES
        ):
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Unknown demo asset.")
            return
        data = candidate.read_bytes()
        if relative == "native-demo.html":
            meta = f'<meta name="native-demo-capability" content="{self.server.capability}">'.encode()
            # The controlled build contains no token. Replace its placeholder if
            # present, otherwise insert one before the close of the head.
            import re

            data = re.sub(
                rb"<meta\s+name=[\"\']native-demo-capability[\"\'][^>]*>", b"", data
            )
            if b"</head>" not in data:
                self._error(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "invalid_build",
                    "The demo build is incomplete.",
                )
                return
            data = data.replace(b"</head>", meta + b"</head>", 1)
        self._send(
            HTTPStatus.OK,
            data,
            mimetypes.guess_type(candidate.name)[0] or "application/octet-stream",
        )

    def do_POST(self):
        if not self._guard(api=True, mutation=True):
            return
        path = self._path()
        if path not in ("/api/prepare", "/api/confirm"):
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Unknown demo operation.")
            return
        lengths = self.headers.get_all("Content-Length")
        if (
            self.headers.get("Transfer-Encoding")
            or lengths is None
            or len(lengths) != 1
        ):
            self._error(
                HTTPStatus.BAD_REQUEST,
                "body_length",
                "A bounded request body is required.",
            )
            return
        try:
            length = int(lengths[0])
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY_BYTES:
            self._error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "body_limit",
                "The request exceeds the demo limit.",
            )
            return
        if self.headers.get_content_type() != "application/json":
            self._error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type", "Expected JSON."
            )
            return
        try:
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("incomplete request")

            def object_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate field")
                    result[key] = value
                return result

            payload = json.loads(
                data,
                object_pairs_hook=object_pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(
                    ValueError("invalid number")
                ),
            )
            if type(payload) is not dict:
                raise ValueError("object required")
        except (ValueError, UnicodeError, RecursionError):
            self._error(
                HTTPStatus.BAD_REQUEST,
                "invalid_json",
                "Expected one complete JSON object with unique fields.",
            )
            return
        if path == "/api/prepare":
            self._dispatch(lambda: self.server.service.prepare(payload))
        elif set(payload) != {"operation_id"} or not isinstance(
            payload["operation_id"], str
        ):
            self._error(
                HTTPStatus.BAD_REQUEST,
                "invalid_confirm",
                "Confirmation requires the prepared operation ID only.",
            )
        else:
            self._dispatch(lambda: self.server.service.confirm(payload["operation_id"]))

    def do_OPTIONS(self):
        self._error(
            HTTPStatus.FORBIDDEN, "cors_denied", "Cross-origin access is not supported."
        )
