"""Strict configuration for DungeonMind statblock v1 integration."""
from __future__ import annotations

import math
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
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})

# Published DungeonMindServer identity patterns (statblocks_v1.domain.resources).
_STATBLOCK_ID_RE = re.compile(r"^sb_[a-z0-9]+$")
_REVISION_ID_RE = re.compile(r"^rev_[a-z0-9]+$")


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

    def __repr__(self) -> str:
        return (
            "StatblockIntegrationConfig("
            f"base_url={self.base_url!r}, "
            "internal_api_key=***, "
            f"enabled={self.enabled!r}, "
            f"timeout_seconds={self.timeout_seconds!r})"
        )


def _parse_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or not raw.strip():
        return default
    cleaned = raw.strip().lower()
    if cleaned in _TRUE_VALUES:
        return True
    if cleaned in _FALSE_VALUES:
        return False
    raise StatblockIntegrationConfigError(
        "integration_misconfigured",
        "DUNGEONMIND_STATBLOCKS_ENABLED must be one of "
        "1/true/yes/on or 0/false/no/off",
    )


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
    if path:
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
    if not math.isfinite(value) or value <= 0 or value > MAX_TIMEOUT_SECONDS:
        raise StatblockIntegrationConfigError(
            "integration_misconfigured",
            f"DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS must be a finite value in "
            f"(0, {MAX_TIMEOUT_SECONDS}]",
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


def validate_statblock_id(value: str) -> str:
    cleaned = value.strip()
    if not _STATBLOCK_ID_RE.fullmatch(cleaned):
        raise ValueError("invalid statblock_id")
    return cleaned


def validate_revision_id(value: str) -> str:
    cleaned = value.strip()
    if not _REVISION_ID_RE.fullmatch(cleaned):
        raise ValueError("invalid revision_id")
    return cleaned
