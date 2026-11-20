"""Private, local-only browser sessions for Buddy's exploratory index graph."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
from fastapi import HTTPException, Request
from psycopg.rows import dict_row

from application_state.engine import connect
from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.agent_graph_local_session import _origin_host
from apps.live_control_server.services.hosted_auth import (
    LOCAL_ENVIRONMENTS,
    LOCAL_MODE,
    auth_mode,
    deployment_environment,
    require_local_unproxied_loopback,
)
from apps.live_control_server.services.trusted_cookie_origin import (
    require_cookie_write_origin,
)


SESSION_COOKIE_PREFIX = "dmb_index_graph_session"
COOKIE_PATH = "/api/live/index-graph"
SESSION_TTL = timedelta(days=30)
MAX_ACTIVE_SESSIONS = 64
MAX_SESSION_RECORDS = 1024
_SESSION_ADVISORY_LOCK = (1145910596, 123456789)
_FORWARDED_HEADERS = (
    "forwarded",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
)


@dataclass(frozen=True)
class IndexGraphSession:
    session_id: str
    allocation_id: str
    expires_at: datetime


class IndexGraphSessionError(Exception):
    def __init__(self, code: str, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def local_profile() -> tuple[str, str, str]:
    """Return the configured loopback UI/API pair and its profile cookie key."""
    try:
        origin, host = _origin_host()
        ui = urlsplit(origin)
        api = urlsplit(f"http://{host}")
        cookie_profile = "\0".join(
            (
                ui.scheme,
                ipaddress.ip_address(ui.hostname or "").compressed,
                str(ui.port),
                api.scheme,
                ipaddress.ip_address(api.hostname or "").compressed,
                str(api.port),
            )
        )
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            503, detail={"code": "index_graph_profile_unavailable"}
        ) from exc
    suffix = hashlib.sha256(cookie_profile.encode("ascii")).hexdigest()[:24]
    return origin, host, f"{SESSION_COOKIE_PREFIX}_{suffix}"


def require_index_graph_boundary(request: Request, *, unsafe: bool) -> None:
    """Require the local Buddy profile even when another global route is hosted."""
    if deployment_environment() not in LOCAL_ENVIRONMENTS or auth_mode() != LOCAL_MODE:
        raise HTTPException(
            status_code=404,
            detail={"code": "index_graph_unavailable"},
        )
    require_local_unproxied_loopback(request)
    origin, host, _cookie = local_profile()
    host_values = request.headers.getlist("host")
    if len(host_values) != 1 or host_values[0] != host:
        raise HTTPException(
            status_code=403, detail={"code": "index_graph_host_rejected"}
        )
    if any(request.headers.getlist(name) for name in _FORWARDED_HEADERS):
        raise HTTPException(
            status_code=403, detail={"code": "index_graph_proxy_rejected"}
        )
    fetch_sites = request.headers.getlist("sec-fetch-site")
    if len(fetch_sites) != 1 or fetch_sites[0] not in {"same-origin", "same-site"}:
        raise HTTPException(
            status_code=403, detail={"code": "index_graph_cross_site_rejected"}
        )
    origins = request.headers.getlist("origin")
    if unsafe:
        require_cookie_write_origin(request, trusted_origins=(origin,))
    elif origins:
        if len(origins) != 1:
            raise HTTPException(
                status_code=403, detail={"code": "index_graph_origin_rejected"}
            )
        require_cookie_write_origin(
            _OriginRequest(request, origins[0]), trusted_origins=(origin,)
        )
    elif fetch_sites[0] != "same-origin":
        raise HTTPException(
            status_code=403, detail={"code": "index_graph_origin_rejected"}
        )


class _OriginRequest:
    """Narrow adapter to reuse canonical Origin validation for safe requests."""

    method = "POST"

    def __init__(self, request: Request, origin: str) -> None:
        self._request = request
        self._origin = origin

    @property
    def headers(self):
        return self

    def getlist(self, name: str) -> list[str]:
        if name.lower() == "origin":
            return [self._origin]
        return self._request.headers.getlist(name)


def _credential_hash(credential: str) -> bytes:
    return hashlib.sha256(credential.encode("ascii")).digest()


def csrf_token(credential: str, session_id: str) -> str:
    _origin, _host, cookie_name = local_profile()
    payload = f"dmb-index-graph-v1\0{cookie_name}\0{session_id}".encode("ascii")
    return hmac.new(credential.encode("ascii"), payload, hashlib.sha256).hexdigest()


def read_cookie_credential(request: Request, cookie_name: str) -> str | None:
    headers = request.headers.getlist("cookie")
    if len(headers) > 1:
        raise IndexGraphSessionError(
            "session_cookie_invalid", "The guest session cookie is ambiguous."
        )
    if not headers:
        return None
    matches: list[str] = []
    for item in headers[0].split(";"):
        name, separator, value = item.strip().partition("=")
        if separator and name == cookie_name:
            matches.append(value)
    if not matches:
        return None
    if len(matches) != 1 or not matches[0] or len(matches[0]) > 128:
        raise IndexGraphSessionError(
            "session_cookie_invalid", "The guest session cookie is invalid."
        )
    credential = matches[0]
    if any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in credential
    ):
        raise IndexGraphSessionError(
            "session_cookie_invalid", "The guest session cookie is invalid."
        )
    return credential


def create_session() -> tuple[str, IndexGraphSession]:
    credential = secrets.token_urlsafe(32)
    session_id = str(uuid4())
    allocation_id = f"buddy-index-graph:{uuid4().hex}"
    now = datetime.now(UTC)
    try:
        connection = connect()
        connection.row_factory = dict_row
        with connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)", _SESSION_ADVISORY_LOCK
            )
            counts = connection.execute(
                "SELECT count(*) FILTER (WHERE expires_at > clock_timestamp()) AS active, "
                "count(*) AS total FROM application_state.index_graph_sessions"
            ).fetchone()
            if (
                counts["active"] >= MAX_ACTIVE_SESSIONS
                or counts["total"] >= MAX_SESSION_RECORDS
            ):
                raise IndexGraphSessionError(
                    "session_limit_reached",
                    "Guest graph sessions are currently full. Existing graphs were left untouched.",
                    429,
                )
            expires_at = now + SESSION_TTL
            connection.execute(
                "INSERT INTO application_state.index_graph_sessions "
                "(session_id, credential_hash, allocation_id, created_at, last_seen_at, expires_at) "
                "VALUES (%s::uuid, %s, %s, %s, %s, %s)",
                (
                    session_id,
                    _credential_hash(credential),
                    allocation_id,
                    now,
                    now,
                    expires_at,
                ),
            )
    except IndexGraphSessionError:
        raise
    except (ApplicationStateUnavailableError, psycopg.Error) as exc:
        raise IndexGraphSessionError(
            "application_state_unavailable",
            "Buddy application state is unavailable; no new guest graph was allocated.",
            503,
        ) from exc
    finally:
        if "connection" in locals():
            connection.close()
    return credential, IndexGraphSession(session_id, allocation_id, expires_at)


def lookup_session(credential: str) -> IndexGraphSession:
    try:
        digest = _credential_hash(credential)
        connection = connect()
        connection.row_factory = dict_row
        with connection:
            row = connection.execute(
                "SELECT session_id::text AS session_id, allocation_id, expires_at "
                "FROM application_state.index_graph_sessions WHERE credential_hash = %s FOR UPDATE",
                (digest,),
            ).fetchone()
            if row is None:
                raise IndexGraphSessionError(
                    "session_unknown",
                    "This guest session is unknown. No replacement graph was created.",
                )
            now = datetime.now(UTC)
            if row["expires_at"] <= now:
                raise IndexGraphSessionError(
                    "session_expired",
                    "This guest session expired. Its graph was retained, but the lost session cannot be recovered automatically.",
                )
            connection.execute(
                "UPDATE application_state.index_graph_sessions SET last_seen_at = %s "
                "WHERE session_id = %s::uuid",
                (now, row["session_id"]),
            )
            session = IndexGraphSession(
                str(row["session_id"]), str(row["allocation_id"]), row["expires_at"]
            )
    except IndexGraphSessionError:
        raise
    except (ApplicationStateUnavailableError, psycopg.Error) as exc:
        raise IndexGraphSessionError(
            "application_state_unavailable",
            "Buddy application state is unavailable; the session was not changed.",
            503,
        ) from exc
    finally:
        if "connection" in locals():
            connection.close()
    return session


def request_session(request: Request, *, unsafe: bool) -> tuple[str, IndexGraphSession]:
    _origin, _host, cookie_name = local_profile()
    credential = read_cookie_credential(request, cookie_name)
    if credential is None:
        raise IndexGraphSessionError(
            "session_required",
            "Start a guest graph session before using this endpoint.",
        )
    session = lookup_session(credential)
    expected_csrf = csrf_token(credential, session.session_id)
    if unsafe:
        csrf_values = request.headers.getlist("x-dmb-index-graph-csrf")
        if len(csrf_values) != 1 or not hmac.compare_digest(
            csrf_values[0], expected_csrf
        ):
            raise IndexGraphSessionError(
                "csrf_rejected", "The graph session token is missing or invalid.", 403
            )
    return credential, session
