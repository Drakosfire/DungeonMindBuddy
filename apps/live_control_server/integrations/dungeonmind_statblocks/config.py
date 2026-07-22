"""Strict configuration for DungeonMind statblock v1 integration."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

BASE_URL_ENV = "DUNGEONMIND_STATBLOCKS_BASE_URL"
INTERNAL_API_KEY_ENV = "DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY"
ENABLED_ENV = "DUNGEONMIND_STATBLOCKS_ENABLED"
TIMEOUT_SECONDS_ENV = "DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS"

INTERNAL_KEY_HEADER = "X-DungeonBuddy-Internal-Key"
API_PREFIX = "/api/internal/dungeonbuddy/v1"

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 120.0
_SUPPORTED_SCHEMES = frozenset({"http", "https"})
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class StatblockIntegrationConfigError(ValueError):
    """Local configuration is disabled or invalid."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True, slots=True)
class StatblockIntegrationConfig:
    base_url: str
    internal_api_key: str
    enabled: bool
    timeout_seconds: float

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.base_url and self.internal_api_key)


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_base_url(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "DUNGEONMIND_STATBLOCKS_BASE_URL is required when enabled",
        )
    parsed = urlparse(cleaned)
    if parsed.scheme not in _SUPPORTED_SCHEMES or not parsed.netloc:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "DUNGEONMIND_STATBLOCKS_BASE_URL must be an http(s) URL with a host",
        )
    if parsed.username or parsed.password:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "DUNGEONMIND_STATBLOCKS_BASE_URL must not embed credentials",
        )
    path = parsed.path.rstrip("/")
    if path and path != "":
        # Allow optional trailing path only when empty after strip; reject extra path.
        # Base URL is origin only so clients build exact contract paths.
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "DUNGEONMIND_STATBLOCKS_BASE_URL must not include a path",
        )
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _parse_timeout(raw: str | None) -> float:
    if raw is None or not raw.strip():
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS must be a positive number",
        ) from exc
    if value <= 0 or value > MAX_TIMEOUT_SECONDS:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            f"DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS must be in (0, {MAX_TIMEOUT_SECONDS}]",
        )
    return value


def load_statblock_integration_config(
    *,
    environ: dict[str, str] | None = None,
) -> StatblockIntegrationConfig:
    env = os.environ if environ is None else environ
    enabled = _parse_bool(env.get(ENABLED_ENV), default=False)
    base_raw = (env.get(BASE_URL_ENV) or "").strip()
    key_raw = (env.get(INTERNAL_API_KEY_ENV) or "").strip()
    timeout_seconds = _parse_timeout(env.get(TIMEOUT_SECONDS_ENV))

    if not enabled:
        return StatblockIntegrationConfig(
            base_url="",
            internal_api_key="",
            enabled=False,
            timeout_seconds=timeout_seconds,
        )

    if not base_raw or not key_raw:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            "enabled integration requires base URL and internal API key",
        )

    return StatblockIntegrationConfig(
        base_url=_normalize_base_url(base_raw),
        internal_api_key=key_raw,
        enabled=True,
        timeout_seconds=timeout_seconds,
    )


def validate_resource_id(value: str, *, label: str) -> str:
    cleaned = value.strip()
    if not _ID_RE.fullmatch(cleaned):
        raise ValueError(f"invalid {label}")
    return cleaned
