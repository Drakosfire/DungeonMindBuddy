"""Fail-closed adapter for DungeonMindServer session introspection."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import httpx
from starlette.requests import Request


DMS_SESSION_COOKIE_NAME = "dungeonmind_session"
DMS_CURRENT_USER_PATH = "/api/auth/current-user"
DMS_REQUEST_TIMEOUT_SECONDS = 5.0
MAX_DMS_COOKIE_VALUE_BYTES = 4096
MAX_DMS_RESPONSE_BODY_BYTES = 64 * 1024

_COOKIE_VALUE_FORBIDDEN = frozenset({ord('"'), ord(","), ord(";"), ord("\\")})


@dataclass(frozen=True)
class DmsPrincipal:
    """Minimal stable identity returned by DungeonMindServer."""

    subject: str


@dataclass(frozen=True)
class DmsPrincipalResolution:
    """Result that keeps an expired session distinct from DMS unavailability."""

    status: Literal["authenticated", "signed_out", "unavailable"]
    principal: DmsPrincipal | None = None


def _fixed_current_user_url(api_origin: str) -> str | None:
    """Build the sole allowed DMS URL from trusted server configuration."""

    if not isinstance(api_origin, str) or "?" in api_origin or "#" in api_origin:
        return None
    try:
        parsed = urlsplit(api_origin)
        # Accessing port validates malformed and out-of-range numeric ports.
        _ = parsed.port
    except (TypeError, ValueError):
        return None

    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in parsed.netloc)
    ):
        return None

    candidate = urlunsplit(
        ("https", parsed.netloc, DMS_CURRENT_USER_PATH, "", "")
    )
    try:
        validated = httpx.URL(candidate)
    except (TypeError, ValueError):
        return None
    if validated.scheme != "https" or not validated.host:
        return None
    return str(validated)


def fixed_dms_api_origin(api_origin: str) -> str | None:
    """Return only the validated server-configured DMS origin."""
    current_user_url = _fixed_current_user_url(api_origin)
    if current_user_url is None:
        return None
    return current_user_url[: -len(DMS_CURRENT_USER_PATH)]


def _valid_cookie_value(value: str) -> bool:
    try:
        encoded = value.encode("ascii")
    except (AttributeError, UnicodeEncodeError):
        return False
    return (
        0 < len(encoded) <= MAX_DMS_COOKIE_VALUE_BYTES
        and all(0x21 <= byte <= 0x7E and byte not in _COOKIE_VALUE_FORBIDDEN for byte in encoded)
    )


class DmsPrincipalResolver:
    """Resolve one request's DMS cookie using an injected HTTPX client.

    The resolver stores only the configured endpoint and the injected client.
    It never retains the request or cookie; request data remains request scoped.
    """

    def __init__(self, *, api_origin: str, http_client: httpx.AsyncClient) -> None:
        self._current_user_url = _fixed_current_user_url(api_origin)
        self._http_client = http_client

    async def __call__(self, request: Request) -> DmsPrincipal | None:
        result = await self.resolve(request)
        return result.principal

    async def resolve(self, request: Request) -> DmsPrincipalResolution:
        if self._current_user_url is None:
            return DmsPrincipalResolution(status="unavailable")

        cookie_value = request.cookies.get(DMS_SESSION_COOKIE_NAME)
        if not isinstance(cookie_value, str) or not _valid_cookie_value(cookie_value):
            return DmsPrincipalResolution(status="signed_out")

        outbound = httpx.Request(
            "GET",
            self._current_user_url,
            headers={
                "Accept": "application/json",
                "Cookie": f"{DMS_SESSION_COOKIE_NAME}={cookie_value}",
            },
            extensions={
                "timeout": {
                    "connect": DMS_REQUEST_TIMEOUT_SECONDS,
                    "read": DMS_REQUEST_TIMEOUT_SECONDS,
                    "write": DMS_REQUEST_TIMEOUT_SECONDS,
                    "pool": DMS_REQUEST_TIMEOUT_SECONDS,
                }
            },
        )

        response: httpx.Response | None = None
        try:
            async with asyncio.timeout(DMS_REQUEST_TIMEOUT_SECONDS):
                response = await self._http_client.send(
                    outbound,
                    auth=None,
                    follow_redirects=False,
                    stream=True,
                )
                try:
                    if response.status_code != 200:
                        status = "signed_out" if response.status_code in {401, 403} else "unavailable"
                        return DmsPrincipalResolution(status=status)
                    content_type = response.headers.get("content-type", "")
                    if content_type.split(";", 1)[0].strip().lower() != "application/json":
                        return DmsPrincipalResolution(status="unavailable")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_DMS_RESPONSE_BODY_BYTES:
                            return DmsPrincipalResolution(status="unavailable")
                        body.extend(chunk)
                    payload = json.loads(body)
                finally:
                    await response.aclose()
        except (httpx.HTTPError, TimeoutError, ValueError, RecursionError):
            return DmsPrincipalResolution(status="unavailable")

        if not isinstance(payload, dict):
            return DmsPrincipalResolution(status="unavailable")
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return DmsPrincipalResolution(status="unavailable")
        principal = DmsPrincipal(subject=subject)
        return DmsPrincipalResolution(status="authenticated", principal=principal)
