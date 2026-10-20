from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from apps.live_control_server.services.trusted_cookie_origin import (
    require_cookie_write_origin,
)


def _request(method: str, origins: Iterable[str] = ()) -> Request:
    headers = [(b"host", b"buddy.example")]
    headers.extend((b"origin", origin.encode("latin-1")) for origin in origins)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": "/write",
        "raw_path": b"/write",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("buddy.example", 443),
    }
    return Request(scope)


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
def test_safe_methods_do_not_require_origin_or_trusted_configuration(method: str) -> None:
    require_cookie_write_origin(_request(method), trusted_origins=[])


@pytest.mark.parametrize("method", ["get", "head", "options"])
def test_lowercase_safe_method_tokens_are_not_exempt(method: str) -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(_request(method), trusted_origins=[])
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("request_origin", "trusted_origin"),
    [
        ("HTTPS://ExAmPlE.com:443", "https://example.com"),
        ("http://EXAMPLE.com:80", "http://example.com"),
        ("https://xn--bcher-kva.example", "https://xn--bcher-kva.example"),
        ("https://xn--fa-hia.example", "https://xn--fa-hia.example"),
        ("https://[2001:0db8::1]:443", "https://[2001:db8::1]"),
        ("https://example.com:0008443", "https://example.com:8443"),
        ("https://127.0.0.1", "https://127.0.0.1"),
    ],
)
def test_allowed_origins_use_exact_canonical_equivalence(
    request_origin: str, trusted_origin: str
) -> None:
    require_cookie_write_origin(
        _request("POST", [request_origin]), trusted_origins=[trusted_origin]
    )


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT"])
def test_trusted_origin_allows_mutation_only_after_guard(method: str) -> None:
    mutation_count = 0

    def mutate() -> None:
        nonlocal mutation_count
        require_cookie_write_origin(
            _request(method, ["https://buddy.example"]),
            trusted_origins=["https://buddy.example"],
        )
        mutation_count += 1

    mutate()
    assert mutation_count == 1


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "NULL",
        "https://buddy.example, https://attacker.example",
        " https://buddy.example",
        "https://buddy.example ",
        "https://buddy.example\t",
        "https://buddy.example\r\nX-Fake: yes",
        "https://",
        "//buddy.example",
        "https://buddy.example/",
        "https://buddy.example?",
        "https://buddy.example#",
        "https://*.buddy.example",
        "https://.buddy.example",
        "https://user@buddy.example",
        "https://buddy.example.",
        "https://bu%64dy.example",
        "https://buddy..example",
        "https://buddy_example",
        "https://buddy.example:0",
        "https://buddy.example:65536",
        "https://buddy.example:not-a-port",
        "https://buddy.example:",
        "https://127.1",
        "https://2130706433",
        "https://0x7f.0.0.1",
        "https://example.com\\@buddy.example",
        "https://attacker.example",
        "https://faß.example",
    ],
)
def test_rejected_origin_never_reaches_the_mutation(origin: str) -> None:
    mutation_count = 0

    def mutate() -> None:
        nonlocal mutation_count
        require_cookie_write_origin(
            _request("POST", [origin]), trusted_origins=["https://buddy.example"]
        )
        mutation_count += 1

    with pytest.raises(HTTPException) as error:
        mutate()

    assert error.value.status_code == 403
    assert error.value.detail == "Forbidden"
    assert mutation_count == 0


@pytest.mark.parametrize(
    "origins",
    [
        [],
        ["https://buddy.example", "not-an-origin"],
        ["https://buddy.example", "https://buddy.example/path"],
        ["https://buddy.example", "https://buddy.example."],
        ["https://buddy.example", "https://example.com:65536"],
        ["https://buddy.example", "https://127.1"],
    ],
)
def test_empty_or_partially_invalid_configuration_fails_closed(
    origins: list[str],
) -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", ["https://buddy.example"]), trusted_origins=origins
        )
    assert error.value.status_code == 403
    assert error.value.detail == "Forbidden"


@pytest.mark.parametrize(
    "origins",
    [
        [],
        ["https://buddy.example", "https://buddy.example"],
        ["https://buddy.example", "https://attacker.example"],
    ],
)
def test_missing_or_duplicate_origin_fails_closed(origins: list[str]) -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", origins), trusted_origins=["https://buddy.example"]
        )
    assert error.value.status_code == 403


def test_canonical_duplicate_configuration_entries_collapse() -> None:
    require_cookie_write_origin(
        _request("POST", ["https://buddy.example"]),
        trusted_origins=[
            "HTTPS://BUDDY.EXAMPLE:443",
            "https://buddy.example",
        ],
    )


@pytest.mark.parametrize(
    ("request_origin", "trusted_origin"),
    [
        ("https://fass.example", "https://xn--fa-hia.example"),
        ("https://xn--fa-hia.example", "https://fass.example"),
    ],
)
def test_sharp_s_a_label_is_distinct_from_fass(
    request_origin: str, trusted_origin: str
) -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", [request_origin]), trusted_origins=[trusted_origin]
        )
    assert error.value.status_code == 403


def test_unicode_u_label_configuration_fails_closed() -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", ["https://fass.example"]),
            trusted_origins=["https://faß.example"],
        )
    assert error.value.status_code == 403


def test_invalid_ascii_idna_a_label_request_fails_closed() -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", ["https://xn--a.example"]),
            trusted_origins=["https://xn--a.example"],
        )
    assert error.value.status_code == 403


def test_invalid_ascii_idna_a_label_configuration_fails_closed() -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", ["https://buddy.example"]),
            trusted_origins=["https://buddy.example", "https://xn--a.example"],
        )
    assert error.value.status_code == 403


def test_proxy_and_referer_headers_do_not_substitute_for_origin() -> None:
    request = _request("POST")
    request.scope["headers"].extend(
        [
            (b"forwarded", b"host=buddy.example;proto=https"),
            (b"x-forwarded-host", b"buddy.example"),
            (b"referer", b"https://buddy.example/page"),
        ]
    )

    with pytest.raises(HTTPException):
        require_cookie_write_origin(
            request, trusted_origins=["https://buddy.example"]
        )


def test_forbidden_response_does_not_disclose_received_or_configured_origins() -> None:
    request_origin = "https://attacker.example"
    configured_origin = "https://private.example"

    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", [request_origin]), trusted_origins=[configured_origin]
        )

    assert error.value.detail == "Forbidden"
    assert request_origin not in str(error.value.detail)
    assert configured_origin not in str(error.value.detail)


def test_string_is_not_accepted_as_a_configuration_collection() -> None:
    with pytest.raises(HTTPException) as error:
        require_cookie_write_origin(
            _request("POST", ["https://buddy.example"]),
            trusted_origins="https://buddy.example",  # type: ignore[arg-type]
        )
    assert error.value.status_code == 403
