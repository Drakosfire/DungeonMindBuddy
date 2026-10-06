"""Durable, local-only operator sessions for the native Graph GM gate."""

from __future__ import annotations

import fcntl
import hmac
import ipaddress
import json
import os
import secrets
import tempfile
import time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

COOKIE_NAME = "dmb_local_graph_session"
COOKIE_PATH = "/api/live"
MAX_AGE = 8 * 60 * 60
MAX_SESSIONS = 64
ORIGIN_ENV = "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN"
HOST_ENV = "DMB_AGENT_GRAPH_LOCAL_API_HOST"
STORE_ENV = "DMB_AGENT_GRAPH_SESSION_STORE"


def _config_error() -> HTTPException:
    return HTTPException(503, detail={"code": "graph_auth_unavailable"})


def _origin_host() -> tuple[str, str]:
    origin = os.environ.get(ORIGIN_ENV, "http://127.0.0.1:5202")
    host = os.environ.get(HOST_ENV, "127.0.0.1:8000")
    parsed = urlsplit(origin)
    try:
        origin_loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
        backend = urlsplit(f"http://{host}")
        backend_loopback = ipaddress.ip_address(backend.hostname or "").is_loopback
    except ValueError as exc:
        raise _config_error() from exc
    if (
        parsed.scheme != "http" or not origin_loopback or parsed.port is None
        or parsed.path or parsed.query or parsed.fragment or parsed.username
        or parsed.password or not backend_loopback or backend.port is None
        or backend.path or backend.query or backend.fragment or backend.username
        or backend.password
    ):
        raise _config_error()
    return origin, host


def _peer_and_host(request: Request) -> str:
    from apps.live_control_server.services.agent_graph_auth import _read_server_token

    secret = _read_server_token(os.environ)
    try:
        peer_loopback = ipaddress.ip_address(
            request.client.host if request.client else ""
        ).is_loopback
    except ValueError:
        peer_loopback = False
    _origin, host = _origin_host()
    if not peer_loopback or request.headers.get("host") != host:
        raise HTTPException(403, detail={"code": "graph_auth_local_boundary"})
    return secret


def _trusted_origin(request: Request) -> None:
    origin, _host = _origin_host()
    if request.headers.get("origin") != origin or request.headers.get(
        "sec-fetch-site", "same-origin"
    ) != "same-origin":
        raise HTTPException(403, detail={"code": "graph_auth_origin_rejected"})


def _store_path() -> Path:
    configured = os.environ.get(STORE_ENV)
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            raise _config_error()
        return path
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return base / "dungeonmindbuddy" / "local_graph_sessions.json"


@contextmanager
def _locked_store() -> Iterator[tuple[Path, dict[str, int]]]:
    path = _store_path()
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.parent.stat().st_mode & 0o077:
            raise OSError("session directory permissions are too broad")
        lock_fd = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if os.fstat(lock_fd).st_mode & 0o077:
                raise OSError("session lock permissions are too broad")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            if path.exists():
                if path.stat().st_mode & 0o077:
                    raise OSError("session file permissions are too broad")
                entries = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(entries, dict) or len(entries) > MAX_SESSIONS:
                    raise OSError("session store is invalid")
                if any(not isinstance(k, str) or not isinstance(v, int) for k, v in entries.items()):
                    raise OSError("session store is invalid")
            else:
                entries = {}
            entries = {key: expiry for key, expiry in entries.items() if expiry > time.time()}
            yield path, entries
            tmp_fd, tmp_name = tempfile.mkstemp(prefix=".graph-session-", dir=path.parent)
            try:
                os.fchmod(tmp_fd, 0o600)
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
                    json.dump(entries, handle, separators=(",", ":"))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise _config_error() from exc


def _key(secret: str, session_id: str) -> str:
    return hmac.new(secret.encode(), session_id.encode(), sha256).hexdigest()


def _csrf(secret: str, session_id: str) -> str:
    return hmac.new(secret.encode(), f"csrf:{session_id}".encode(), sha256).hexdigest()


def issue_session(request: Request) -> tuple[str, str]:
    secret = _peer_and_host(request)
    _trusted_origin(request)
    session_id = secrets.token_urlsafe(32)
    with _locked_store() as (_path, entries):
        if len(entries) >= MAX_SESSIONS:
            raise _config_error()
        entries[_key(secret, session_id)] = int(time.time()) + MAX_AGE
    return session_id, _csrf(secret, session_id)


def require_session(request: Request, *, unsafe: bool = False) -> str:
    secret = _peer_and_host(request)
    session_id = request.cookies.get(COOKIE_NAME, "")
    if len(session_id) < 32 or len(session_id) > 128:
        raise HTTPException(401, detail={"code": "graph_auth_required"})
    with _locked_store() as (_path, entries):
        valid = _key(secret, session_id) in entries
    if not valid:
        raise HTTPException(401, detail={"code": "graph_auth_required"})
    if unsafe:
        _trusted_origin(request)
        if not hmac.compare_digest(
            request.headers.get("x-dmb-graph-csrf", ""), _csrf(secret, session_id)
        ):
            raise HTTPException(403, detail={"code": "graph_auth_csrf_rejected"})
    return _csrf(secret, session_id)


def revoke_session(request: Request) -> None:
    secret = _peer_and_host(request)
    require_session(request, unsafe=True)
    session_id = request.cookies[COOKIE_NAME]
    with _locked_store() as (_path, entries):
        entries.pop(_key(secret, session_id), None)
