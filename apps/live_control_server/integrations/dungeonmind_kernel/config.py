"""DungeonMind kernel integration configuration (non-authoritative flags)."""

from __future__ import annotations

import os

_SHADOW_ENV = "DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED"


def dungeonmind_threat_shadow_enabled() -> bool:
    """Return True only when the shadow flag is exactly ``1``.

    Any other value (unset, empty, typo, ``true``, ``yes``, ``0``) is disabled.
    Unknown/invalid values must never break the Threat query endpoint.
    """
    return os.environ.get(_SHADOW_ENV) == "1"


__all__ = [
    "dungeonmind_threat_shadow_enabled",
]
