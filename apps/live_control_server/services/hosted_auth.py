"""Fail-closed request authentication for hosted Buddy.

Identity comes from DungeonMindServer. World selectors are never authorization
claims. The production app has no reviewed route-to-World bindings, so hosted
World operations remain denied until handlers register explicit verified
bindings.
"""

from __future__ import annotations

import json
import os
import ipaddress
import inspect
from pathlib import Path
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import unquote, urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from apps.live_control_server.services.trusted_cookie_origin import (
    require_cookie_write_origin,
)


WorldScopeResolver = Callable[[Request], str | None | Awaitable[str | None]]
WorldScopeResolvers = Mapping[tuple[str, str], WorldScopeResolver]


DEPLOYMENT_ENVIRONMENT_ENV = "DMB_DEPLOYMENT_ENVIRONMENT"
AUTH_MODE_ENV = "DMB_AUTH_MODE"
DMS_API_ORIGIN_ENV = "DUNGEONMIND_SERVER_API_ORIGIN"
HOSTED_WORLD_ACCESS_ENV = "DMB_HOSTED_WORLD_ACCESS_JSON"
TRUSTED_FRONTEND_ORIGINS_ENV = "AUTH_TRUSTED_FRONTEND_ORIGINS"
APPLICATION_STATE_DSN_ENV = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
WORLD_GRAPH_DSN_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
PERSISTENT_ROOT_ENVS = (
    "DMB_MANAGED_WORLD_DATA_ROOT",
    "DMB_ARTIFACT_DATA_ROOT",
    "DUNGEONMIND_LIVE_SESSION_DIR",
    "DUNGEONMIND_WORLD_GRAPH_ROOT",
)
HOSTED_MODE = "hosted_dms"
LOCAL_MODE = "local_operator"
LOCAL_ENVIRONMENTS = frozenset({"local", "development", "dev"})
PRODUCTION_ENVIRONMENT = "production"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CURRENT_USER_PATH = "/api/auth/current-user"
LOGOUT_PATH = "/api/auth/logout"
_WORLD_KEYS = frozenset({"world_id", "worldid", "managed_world_id", "managedworldid"})
_FORWARDED_HEADERS = (
    "forwarded",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
    "x-real-ip",
)
MAX_WORLD_SCOPE_BODY_BYTES = 1024 * 1024
HOSTED_WORLD_ROUTE_POLICY_ERROR = "hosted_world_route_policy_unverified"


def deployment_environment(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    return source.get(DEPLOYMENT_ENVIRONMENT_ENV, "local").strip().lower()


def auth_mode(environ: Mapping[str, str] | None = None) -> str:
    source = os.environ if environ is None else environ
    return source.get(AUTH_MODE_ENV, "").strip().lower()


def hosted_world_access(
    environ: Mapping[str, str] | None = None,
) -> dict[str, frozenset[str]]:
    source = os.environ if environ is None else environ
    raw = source.get(HOSTED_WORLD_ACCESS_ENV, "")
    if not raw.strip() or len(raw.encode("utf-8")) > 64 * 1024:
        return {}

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate hosted access key")
            result[key] = value
        return result

    try:
        document = json.loads(raw, object_pairs_hook=strict_object)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}
    if not isinstance(document, dict) or not document:
        return {}

    access: dict[str, frozenset[str]] = {}
    for world_id, subjects in document.items():
        if (
            not isinstance(world_id, str)
            or not world_id.strip()
            or any(ord(character) < 0x21 for character in world_id)
            or not isinstance(subjects, list)
            or not subjects
            or any(
                not isinstance(subject, str)
                or not subject.strip()
                or any(ord(character) < 0x21 for character in subject)
                for subject in subjects
            )
            or len(set(subjects)) != len(subjects)
        ):
            return {}
        access[world_id] = frozenset(subjects)
    return access


def trusted_frontend_origins(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    source = os.environ if environ is None else environ
    raw = source.get(TRUSTED_FRONTEND_ORIGINS_ENV, "")
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    return values


def _valid_world_scope_resolvers(resolvers: WorldScopeResolvers | None) -> bool:
    if not isinstance(resolvers, Mapping) or not resolvers:
        return False
    for key, resolver in resolvers.items():
        if (
            not isinstance(key, tuple)
            or len(key) != 2
            or not isinstance(key[0], str)
            or not key[0]
            or key[0] != key[0].upper()
            or not isinstance(key[1], str)
            or not key[1].startswith("/api/")
            or key[1] in {CURRENT_USER_PATH, LOGOUT_PATH}
            or not callable(resolver)
        ):
            return False
    return True


def validate_hosted_auth_configuration(
    environ: Mapping[str, str] | None = None,
    *,
    world_scope_resolvers: WorldScopeResolvers | None = None,
) -> tuple[str, ...]:
    """Return missing/invalid configuration fields without including values."""
    source = os.environ if environ is None else environ
    errors: list[str] = []
    if deployment_environment(source) != PRODUCTION_ENVIRONMENT:
        errors.append(DEPLOYMENT_ENVIRONMENT_ENV)
    if auth_mode(source) != HOSTED_MODE:
        errors.append(AUTH_MODE_ENV)
    origin = source.get(DMS_API_ORIGIN_ENV, "").strip()
    try:
        parsed_origin = urlsplit(origin)
        origin_valid = (
            parsed_origin.scheme.lower() == "https"
            and bool(parsed_origin.hostname)
            and parsed_origin.username is None
            and parsed_origin.password is None
            and parsed_origin.path in {"", "/"}
            and not parsed_origin.query
            and not parsed_origin.fragment
            and parsed_origin.port in {None, 443}
        )
    except ValueError:
        origin_valid = False
    if not origin_valid:
        errors.append(DMS_API_ORIGIN_ENV)
    if "https://buddy.dungeonmind.net" not in trusted_frontend_origins(source):
        errors.append(TRUSTED_FRONTEND_ORIGINS_ENV)
    if not hosted_world_access(source):
        errors.append(HOSTED_WORLD_ACCESS_ENV)
    if not _valid_world_scope_resolvers(world_scope_resolvers):
        errors.append(HOSTED_WORLD_ROUTE_POLICY_ERROR)

    database_coordinates: list[tuple[str, str, str]] = []
    database_owners: list[str] = []
    for name in (APPLICATION_STATE_DSN_ENV, WORLD_GRAPH_DSN_ENV):
        raw_dsn = source.get(name, "").strip()
        try:
            parsed_dsn = urlsplit(raw_dsn)
            database = unquote(parsed_dsn.path.lstrip("/")).split("/", 1)[0]
            if (
                parsed_dsn.scheme not in {"postgres", "postgresql"}
                or not parsed_dsn.hostname
                or not database
                or not parsed_dsn.username
            ):
                raise ValueError
            database_coordinates.append(
                (parsed_dsn.hostname.lower(), str(parsed_dsn.port or 5432), database)
            )
            database_owners.append(unquote(parsed_dsn.username).lower())
        except ValueError:
            errors.append(name)
    if len(database_coordinates) == 2 and database_coordinates[0] == database_coordinates[1]:
        errors.extend((APPLICATION_STATE_DSN_ENV, WORLD_GRAPH_DSN_ENV))
    if len(database_owners) == 2 and database_owners[0] == database_owners[1]:
        errors.extend((APPLICATION_STATE_DSN_ENV, WORLD_GRAPH_DSN_ENV))

    try:
        from apps.live_control_server.config import repo_root

        code_root = repo_root().resolve()
    except (OSError, RuntimeError):
        code_root = None
    for name in PERSISTENT_ROOT_ENVS:
        raw_path = source.get(name, "").strip()
        path = Path(raw_path)
        if not path.is_absolute() or not path.exists() or not path.is_dir():
            errors.append(name)
            continue
        try:
            resolved = path.resolve(strict=True)
            if code_root is not None and (resolved == code_root or resolved.is_relative_to(code_root)):
                errors.append(name)
        except (OSError, RuntimeError):
            errors.append(name)
    recap_root = source.get("DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT", "").strip()
    recap_path = Path(recap_root)
    if (
        not recap_root
        or recap_path.is_absolute()
        or ".." in recap_path.parts
        or recap_root.startswith("file:")
    ):
        errors.append("DUNGEONMIND_RECAP_SOURCE_CONTENT_ROOT")
    return tuple(errors)


def require_local_unproxied_loopback(request: Request) -> None:
    peer = request.client.host if request.client is not None else ""
    try:
        loopback = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        loopback = False
    if not loopback or any(request.headers.getlist(name) for name in _FORWARDED_HEADERS):
        raise HTTPException(
            status_code=403,
            detail={"code": "hosted_auth_local_boundary"},
        )


def _collect_world_ids(value: Any, *, key: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for child_key, child_value in value.items():
            normalized = str(child_key).replace("-", "_").lower()
            compact = normalized.replace("_", "")
            if compact in {item.replace("_", "") for item in _WORLD_KEYS}:
                if isinstance(child_value, str) and child_value.strip():
                    found.add(child_value.strip())
            found.update(_collect_world_ids(child_value))
    elif isinstance(value, list):
        for child in value:
            found.update(_collect_world_ids(child))
    return found


async def request_world_ids(request: Request) -> frozenset[str]:
    found = {
        value.strip()
        for key in ("world_id", "worldId", "managed_world_id", "managedWorldId")
        for value in request.query_params.getlist(key)
        if value.strip()
    }
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        body = await request.body()
        if len(body) > MAX_WORLD_SCOPE_BODY_BYTES:
            return frozenset()
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return frozenset()
        found.update(_collect_world_ids(payload))
    return frozenset(found)


def authorize_world_access(
    subject: str,
    world_ids: frozenset[str],
    *,
    access: Mapping[str, frozenset[str]],
) -> None:
    if not subject or not world_ids:
        raise HTTPException(
            status_code=403,
            detail={"code": "hosted_world_context_required"},
        )
    if any(subject not in access.get(world_id, frozenset()) for world_id in world_ids):
        raise HTTPException(
            status_code=403,
            detail={"code": "hosted_world_forbidden"},
        )


async def _resolve_authoritative_world_id(
    request: Request,
    resolver: WorldScopeResolver,
) -> str:
    try:
        result = resolver(request)
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "hosted_world_context_required"},
        ) from exc
    if (
        not isinstance(result, str)
        or not result.strip()
        or result != result.strip()
        or any(ord(character) < 0x21 for character in result)
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "hosted_world_context_required"},
        )
    return result


def require_hosted_write_origin(request: Request) -> None:
    require_cookie_write_origin(
        request,
        trusted_origins=trusted_frontend_origins(),
    )


def install_hosted_request_boundary(
    application: FastAPI,
    *,
    world_scope_resolvers: WorldScopeResolvers | None = None,
) -> None:
    """Mount the API boundary with code-owned resource-to-World resolvers.

    Each key is an exact (HTTP method, route path) pair. A resolver must look
    up the requested resource using server-side state and return its single
    authoritative World ID. Client World selectors are checked for consistency
    only; they never establish authorization. The default is intentionally
    empty because production resource bindings have not been reviewed.
    """
    if world_scope_resolvers and not _valid_world_scope_resolvers(
        world_scope_resolvers
    ):
        raise ValueError("world_scope_resolvers_invalid")
    route_resolvers = dict(world_scope_resolvers or {})

    @application.middleware("http")
    async def hosted_request_boundary(request: Request, call_next):
        if request.url.path != "/api" and not request.url.path.startswith("/api/"):
            return await call_next(request)

        environment = deployment_environment()
        mode = auth_mode()
        if environment in LOCAL_ENVIRONMENTS and mode == LOCAL_MODE:
            try:
                require_local_unproxied_loopback(request)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            return await call_next(request)

        if environment != PRODUCTION_ENVIRONMENT or mode != HOSTED_MODE:
            return JSONResponse(
                status_code=503,
                content={"detail": {"code": "hosted_auth_unavailable"}},
            )

        # Logout is intentionally allowed to clear an expired session. Its
        # route still enforces DMS's exact Origin contract before proxying.
        if request.url.path != LOGOUT_PATH:
            resolver = getattr(request.app.state, "dms_principal_resolver", None)
            if resolver is None:
                return JSONResponse(
                    status_code=503,
                    content={"detail": {"code": "hosted_auth_unavailable"}},
                )
            principal = await resolver(request)
            if principal is None:
                return JSONResponse(
                    status_code=401,
                    headers={"WWW-Authenticate": "Session"},
                    content={"detail": {"code": "authentication_required"}},
                )
            request.state.dms_principal = principal

        if request.method.upper() not in SAFE_METHODS:
            try:
                require_hosted_write_origin(request)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        if request.url.path in {CURRENT_USER_PATH, LOGOUT_PATH}:
            return await call_next(request)

        resolver = route_resolvers.get((request.method.upper(), request.url.path))
        if resolver is None:
            return JSONResponse(
                status_code=403,
                content={"detail": {"code": HOSTED_WORLD_ROUTE_POLICY_ERROR}},
            )

        try:
            resolved_world_id = await _resolve_authoritative_world_id(request, resolver)
            requested_world_ids = await request_world_ids(request)
            if requested_world_ids and requested_world_ids != frozenset({resolved_world_id}):
                raise HTTPException(
                    status_code=403,
                    detail={"code": "hosted_world_context_mismatch"},
                )
            principal = getattr(request.state, "dms_principal", None)
            authorize_world_access(
                principal.subject if principal is not None else "",
                frozenset({resolved_world_id}),
                access=hosted_world_access(),
            )
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        return await call_next(request)


__all__ = [
    "AUTH_MODE_ENV",
    "CURRENT_USER_PATH",
    "DMS_API_ORIGIN_ENV",
    "DEPLOYMENT_ENVIRONMENT_ENV",
    "HOSTED_MODE",
    "HOSTED_WORLD_ACCESS_ENV",
    "APPLICATION_STATE_DSN_ENV",
    "LOCAL_ENVIRONMENTS",
    "LOCAL_MODE",
    "LOGOUT_PATH",
    "PRODUCTION_ENVIRONMENT",
    "PERSISTENT_ROOT_ENVS",
    "WORLD_GRAPH_DSN_ENV",
    "auth_mode",
    "authorize_world_access",
    "deployment_environment",
    "hosted_world_access",
    "install_hosted_request_boundary",
    "request_world_ids",
    "require_hosted_write_origin",
    "require_local_unproxied_loopback",
    "trusted_frontend_origins",
    "validate_hosted_auth_configuration",
]
