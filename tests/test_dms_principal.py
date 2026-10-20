from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
from starlette.requests import Request

from apps.live_control_server.services import dms_principal
from apps.live_control_server.services.dms_principal import (
    DMS_CURRENT_USER_PATH,
    DMS_REQUEST_TIMEOUT_SECONDS,
    DMS_SESSION_COOKIE_NAME,
    DmsPrincipal,
    DmsPrincipalResolver,
)


def _request(
    *,
    cookie_value: str | None = None,
    user_id: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie_value is not None:
        headers.append(
            (
                b"cookie",
                f"{DMS_SESSION_COOKIE_NAME}={cookie_value}".encode("latin-1"),
            )
        )
    if user_id is not None:
        headers.append((b"x-user-id", user_id.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("buddy.example.test", 443),
        }
    )


def test_valid_dms_sub_is_the_only_identity_and_cookie_stays_request_scoped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cookie_value = "synthetic-session-value=="
    seen: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        seen.append(outbound)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"sub": "google-sub-123", "email": "user@example.test"},
        )

    async def run() -> tuple[DmsPrincipal | None, httpx.AsyncClient, DmsPrincipalResolver]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={"X-User-ID": "client-default-user"},
            cookies={"unrelated": "client-default-cookie"},
            follow_redirects=True,
        ) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            principal = await resolver(
                _request(cookie_value=cookie_value, user_id="caller-user")
            )
            return principal, client, resolver

    caplog.set_level(logging.DEBUG)
    principal, client, resolver = asyncio.run(run())

    assert principal == DmsPrincipal(subject="google-sub-123")
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert str(seen[0].url) == f"https://dms.example.test{DMS_CURRENT_USER_PATH}"
    assert seen[0].headers["cookie"] == f"{DMS_SESSION_COOKIE_NAME}={cookie_value}"
    assert "x-user-id" not in seen[0].headers
    assert "unrelated=" not in seen[0].headers.get("cookie", "")
    assert client.cookies.get(DMS_SESSION_COOKIE_NAME) is None
    assert cookie_value not in repr(vars(resolver))
    assert cookie_value not in caplog.text


def test_x_user_id_alone_does_not_create_a_principal() -> None:
    requests: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        requests.append(outbound)
        return httpx.Response(200, json={"sub": "should-not-be-used"})

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(user_id="attacker-chosen-user"))

    assert asyncio.run(run()) is None
    assert requests == []


@pytest.mark.parametrize("status_code", [401, 500, 503, 302])
def test_non_success_responses_fail_closed_and_redirects_are_not_followed(
    status_code: int,
) -> None:
    seen: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        seen.append(outbound)
        headers = {"location": "https://attacker.example.test/collect"} if status_code == 302 else {}
        return httpx.Response(status_code, headers=headers, json={"sub": "ignored"})

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value="synthetic-cookie"))

    assert asyncio.run(run()) is None
    assert len(seen) == 1
    assert str(seen[0].url) == f"https://dms.example.test{DMS_CURRENT_USER_PATH}"


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"not-json", "application/json"),
        (b"[]", "application/json"),
        (b'{"sub":""}', "application/json"),
        (b'{"sub":"   "}', "application/json"),
        (b'{"sub":42}', "application/json"),
        (b'{"email":"user@example.test"}', "application/json"),
        (b'{"sub":"google-sub"}', "text/plain"),
    ],
)
def test_malformed_current_user_responses_fail_closed(
    body: bytes,
    content_type: str,
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": content_type},
            content=body,
        )

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value="synthetic-cookie"))

    assert asyncio.run(run()) is None


@pytest.mark.parametrize(
    "api_origin",
    [
        "http://dms.example.test",
        "https://user:password@dms.example.test",
        "https://dms.example.test/api",
        "https://dms.example.test?next=https://attacker.example.test",
        "https://dms.example.test#fragment",
        "https://dms.example.test:99999",
        "not-an-origin",
    ],
)
def test_invalid_api_origins_fail_closed_without_transport_call(api_origin: str) -> None:
    requests: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        requests.append(outbound)
        return httpx.Response(200, json={"sub": "should-not-be-used"})

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(api_origin=api_origin, http_client=client)
            return await resolver(_request(cookie_value="synthetic-cookie"))

    assert asyncio.run(run()) is None
    assert requests == []


def test_timeout_fails_closed_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dms_principal, "DMS_REQUEST_TIMEOUT_SECONDS", 0.01)
    seen: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        seen.append(outbound)
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"sub": "too-late"})

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value="synthetic-cookie"))

    assert asyncio.run(run()) is None
    assert len(seen) == 1


def test_transport_failure_fails_closed_without_logging_cookie(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cookie_value = "synthetic-secret-cookie"
    seen: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        seen.append(outbound)
        raise httpx.ConnectError("simulated offline transport", request=outbound)

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value=cookie_value))

    caplog.set_level(logging.DEBUG)
    assert asyncio.run(run()) is None
    assert len(seen) == 1
    assert cookie_value not in caplog.text


@pytest.mark.parametrize("cookie_value", ["", "bad\r\nvalue", 'bad"value', "x" * 4097])
def test_invalid_cookie_values_fail_closed_before_http(cookie_value: str) -> None:
    requests: list[httpx.Request] = []

    async def handler(outbound: httpx.Request) -> httpx.Response:
        requests.append(outbound)
        return httpx.Response(200, json={"sub": "should-not-be-used"})

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value=cookie_value))

    assert asyncio.run(run()) is None
    assert requests == []


def test_oversized_response_fails_closed() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b" " * (dms_principal.MAX_DMS_RESPONSE_BODY_BYTES + 1),
        )

    async def run() -> DmsPrincipal | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            resolver = DmsPrincipalResolver(
                api_origin="https://dms.example.test",
                http_client=client,
            )
            return await resolver(_request(cookie_value="synthetic-cookie"))

    assert asyncio.run(run()) is None


def test_timeout_is_finite_and_matches_reviewed_contract() -> None:
    assert DMS_REQUEST_TIMEOUT_SECONDS == 5.0
