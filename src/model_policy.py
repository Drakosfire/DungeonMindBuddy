"""Buddy-local MODEL_POLICY.json loading (E1B ownership boundary).

Active runtime and product-tooling code must resolve model policy only from the
DungeonMindBuddy repository root. Do not search parent/workspace trees.

Missing vs malformed/unreadable files are not the same state. Callers that
historically fell back only when the file was absent must use ``strict=True``.
Callers that historically swallowed parse/read failures use the default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_BUDDY_ROOT = Path(__file__).resolve().parents[1]
_POLICY_NAME = "MODEL_POLICY.json"


def buddy_repo_root() -> Path:
    """Return the DungeonMindBuddy repository root."""
    return _BUDDY_ROOT


def buddy_model_policy_path() -> Path:
    """Return the Buddy-owned ``MODEL_POLICY.json`` path (may not exist)."""
    return _BUDDY_ROOT / _POLICY_NAME


def load_buddy_model_policy(*, strict: bool = False) -> dict[str, Any]:
    """Load Buddy-root policy JSON.

    A missing file returns ``{}`` in both modes.

    ``strict=False`` (default): unreadable or malformed files return ``{}``,
    matching consumers that historically caught parse/read failures.

    ``strict=True``: ``OSError`` / ``UnicodeDecodeError`` / ``JSONDecodeError``
    propagate, matching consumers that historically called ``json.loads`` on an
    existing file without a local try/except.
    """
    path = buddy_model_policy_path()
    if not path.is_file():
        return {}
    if strict:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "buddy_model_policy_path",
    "buddy_repo_root",
    "load_buddy_model_policy",
]
