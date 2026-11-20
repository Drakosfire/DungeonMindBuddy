from __future__ import annotations

import ipaddress
import re
import unicodedata
from collections.abc import Collection
from urllib.parse import urlsplit

import idna
from fastapi import HTTPException
from starlette.requests import Request


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\Z")
_NUMERIC_LABEL = re.compile(r"[0-9]+\Z")
_HEX_IPV4_NUMBER = re.compile(r"0x[0-9a-f]*\Z")


def require_cookie_write_origin(
    request: Request, *, trusted_origins: Collection[str]
) -> None:
    """Reject unsafe cookie-authenticated writes without an exact trusted Origin.

    Authentication selection belongs to the caller. This helper intentionally
    does not inspect cookies, authorization headers, Host, or proxy headers.
    """
    if request.method in _SAFE_METHODS:
        return

    try:
        configured_values = tuple(trusted_origins)
    except TypeError:
        _forbidden()
    if isinstance(trusted_origins, str) or not configured_values:
        _forbidden()

    allowed_origins: set[str] = set()
    for configured_value in configured_values:
        canonical = _canonical_http_origin(configured_value)
        if canonical is None:
            _forbidden()
        allowed_origins.add(canonical)

    try:
        request_origins = request.headers.getlist("origin")
    except (AttributeError, TypeError):
        _forbidden()
    if len(request_origins) != 1:
        _forbidden()

    request_origin = _canonical_http_origin(request_origins[0])
    if request_origin is None or request_origin not in allowed_origins:
        _forbidden()


def _forbidden() -> None:
    raise HTTPException(status_code=403, detail="Forbidden")


def _canonical_http_origin(value: object) -> str | None:
    if not isinstance(value, str) or not value or value.lower() == "null":
        return None
    if any(char.isspace() or unicodedata.category(char) == "Cc" for char in value):
        return None
    if "\\" in value or "?" in value or "#" in value:
        return None

    try:
        parsed = urlsplit(value)
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        return None
    if parsed.query or parsed.fragment:
        return None

    authority = parsed.netloc
    if "@" in authority or "%" in authority:
        return None

    if authority.startswith("["):
        match = re.fullmatch(r"\[([^\[\]]+)\](?::([0-9]+))?", authority)
        if match is None:
            return None
        host = match.group(1)
        port_text = match.group(2)
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return None
        if address.version != 6:
            return None
        canonical_host = f"[{address.compressed.lower()}]"
    else:
        if "[" in authority or "]" in authority or authority.count(":") > 1:
            return None
        host, separator, port_text = authority.partition(":")
        if separator and not port_text:
            return None
        if not separator:
            port_text = None
        if not host or host.endswith(".") or not host.isascii():
            return None

        try:
            ascii_host = idna.encode(
                host, uts46=True, transitional=False, std3_rules=True
            ).decode("ascii").lower()
        except (idna.IDNAError, UnicodeError, ValueError):
            return None
        if ascii_host != host.lower():
            return None
        if not ascii_host or ascii_host.endswith(".") or len(ascii_host) > 253:
            return None

        labels = ascii_host.split(".")
        if any(not _DNS_LABEL.fullmatch(label) for label in labels):
            return None

        # WHATWG-style numeric suffixes can be interpreted as legacy IPv4 by
        # browsers. Accept only canonical dotted-quad IPv4, never shorthand.
        numeric_suffix = bool(
            _NUMERIC_LABEL.fullmatch(labels[-1])
            or _HEX_IPV4_NUMBER.fullmatch(labels[-1])
            or (
                len(labels[-1]) > 1
                and labels[-1].startswith("0")
                and all(char in "01234567" for char in labels[-1][1:])
            )
        )
        if numeric_suffix:
            if not all(_NUMERIC_LABEL.fullmatch(label) for label in labels):
                return None
            try:
                address = ipaddress.IPv4Address(ascii_host)
            except ValueError:
                return None
            canonical_host = str(address)
            if canonical_host != ascii_host:
                return None
        else:
            canonical_host = ascii_host

    port: int | None = None
    if port_text is not None:
        if not port_text or not port_text.isascii() or not port_text.isdigit():
            return None
        significant_digits = port_text.lstrip("0") or "0"
        if len(significant_digits) > 5:
            return None
        port = int(significant_digits)
        if not 1 <= port <= 65535:
            return None

    if port == (80 if scheme == "http" else 443):
        port = None

    canonical = f"{scheme}://{canonical_host}"
    if port is not None:
        canonical += f":{port}"
    return canonical
