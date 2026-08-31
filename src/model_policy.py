"""Buddy-local MODEL_POLICY.json loading (E1B ownership boundary).

Active runtime and product-tooling code must resolve model policy only from the
DungeonMindBuddy repository root. Do not search parent/workspace trees.
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


def load_buddy_model_policy() -> dict[str, Any]:
    """Load Buddy-root policy JSON, or ``{}`` when absent/unreadable."""
    path = buddy_model_policy_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "buddy_model_policy_path",
    "buddy_repo_root",
    "load_buddy_model_policy",
]
