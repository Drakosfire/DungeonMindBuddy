"""Local operator authentication for native World Graph reads."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
import secrets
from typing import Literal, Mapping

from fastapi import Depends, HTTPException, Request


AUTH_MODE_ENV = "DMB_AGENT_GRAPH_AUTH_MODE"
AUTH_ENVIRONMENT_ENV = "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT"
LOCAL_OPERATOR_TOKEN_ENV = "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN"
_ALLOWED_ENVIRONMENTS = frozenset({"local", "development", "dev"})


@dataclass(frozen=True)
class NativeGraphPrincipal:
    subject: str
    role: Literal["gm", "player"]
    auth_method: Literal["local_operator"]


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "graph_auth_unavailable",
            "message": "Native Graph access is not configured for local use.",
        },
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        detail={
            "code": "graph_auth_required",
            "message": "A valid local operator credential is required for native Graph access.",
        },
    )


def _read_server_token(environ: Mapping[str, str]) -> str:
    mode = environ.get(AUTH_MODE_ENV, "").strip().lower()
    environment = environ.get(AUTH_ENVIRONMENT_ENV, "").strip().lower()
    token = environ.get(LOCAL_OPERATOR_TOKEN_ENV, "")
    if (
        mode != "local_operator"
        or environment not in _ALLOWED_ENVIRONMENTS
        or len(token) < 32
        or any(character.isspace() for character in token)
    ):
        raise _unavailable()
    return token


def authenticate_native_graph_principal(request: Request) -> NativeGraphPrincipal:
    """Authenticate the one explicitly configured local operator capability.

    Forwarded/client identity headers are intentionally ignored. The ASGI peer
    must be a loopback address, and the environment and long bearer must both
    be explicitly configured before this endpoint grants access.
    """

    expected = _read_server_token(os.environ)
    peer_host = request.client.host if request.client is not None else ""
    try:
        peer_is_loopback = ipaddress.ip_address(peer_host).is_loopback
    except ValueError:
        peer_is_loopback = False
    if not peer_is_loopback:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "graph_auth_loopback_required",
                "message": "Native Graph access is supported only from a loopback connection.",
            },
        )

    authorization = request.headers.get("authorization", "")
    scheme, separator, candidate = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not candidate
        or candidate != candidate.strip()
    ):
        raise _unauthorized()
    try:
        matches = secrets.compare_digest(
            candidate.encode("utf-8"), expected.encode("utf-8")
        )
    except UnicodeEncodeError:
        matches = False
    if not matches:
        raise _unauthorized()

    return NativeGraphPrincipal(
        subject="local_operator",
        role="gm",
        auth_method="local_operator",
    )


def require_native_graph_gm(principal: NativeGraphPrincipal) -> NativeGraphPrincipal:
    if principal.role != "gm":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "graph_gm_required",
                "message": "GM authority is required for native Graph access.",
            },
        )
    return principal


def native_graph_gm_dependency(
    principal: NativeGraphPrincipal = Depends(authenticate_native_graph_principal),
) -> NativeGraphPrincipal:
    return require_native_graph_gm(principal)


def enforce_native_graph_gm(request: Request) -> NativeGraphPrincipal:
    """Conditional guard for routes where only some request bodies read Graph."""

    return require_native_graph_gm(authenticate_native_graph_principal(request))


__all__ = [
    "AUTH_ENVIRONMENT_ENV",
    "AUTH_MODE_ENV",
    "LOCAL_OPERATOR_TOKEN_ENV",
    "NativeGraphPrincipal",
    "authenticate_native_graph_principal",
    "enforce_native_graph_gm",
    "native_graph_gm_dependency",
    "require_native_graph_gm",
]
