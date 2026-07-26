"""Server-compatible statblock definition canonicalization and digests.

Mirrors DungeonMindServer ``statblocks_v1.domain.canonicalization`` /
``digests.compute_definition_digest`` so Buddy can bind
``generation_receipt.source_definition_digest`` against the same bytes the
Server hashes after parse + contract-shape restore.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import Any

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    StatblockDefinitionV1Input,
)

DIGEST_ALGORITHM = "sha256"
CANONICALIZER_VERSION = "statblock-canonicalizer-v1"

_SET_LIKE_FIELD_NAMES = frozenset(
    {
        "adjudication_tags",
        "bypasses",
        "condition_immunities",
        "damage_types",
        "languages",
        "qualifiers",
        "special_modes",
        "subtypes",
        "tags",
    }
)


def _normalize_value(value: Any, field_name: str | None = None) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_value(item, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        normalized = [_normalize_value(item) for item in value]
        if field_name in _SET_LIKE_FIELD_NAMES:
            return sorted(set(normalized))
        return normalized
    return value


def canonicalize_definition_payload(definition: StatblockDefinitionV1Input) -> str:
    """Return version-1 canonical JSON text for a parsed definition."""
    payload = definition.model_dump(mode="json", exclude_none=False)
    normalized = _normalize_value(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def compute_definition_digest(definition: StatblockDefinitionV1Input) -> str:
    """Return ``sha256:<hex>`` over canonical UTF-8 definition JSON."""
    if not isinstance(definition, StatblockDefinitionV1Input):
        raise TypeError(
            "compute_definition_digest accepts only StatblockDefinitionV1Input; "
            f"got {type(definition).__name__}"
        )
    payload = canonicalize_definition_payload(definition).encode("utf-8")
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(payload).hexdigest()}"


def source_definition_digest_from_body(source_definition: dict[str, Any]) -> str:
    """Parse a wire/Buddy source_definition object and digest like Server."""
    if not isinstance(source_definition, dict):
        raise TypeError("source_definition must be an object")
    parsed = StatblockDefinitionV1Input.model_validate(source_definition)
    return compute_definition_digest(parsed)


__all__ = [
    "CANONICALIZER_VERSION",
    "DIGEST_ALGORITHM",
    "canonicalize_definition_payload",
    "compute_definition_digest",
    "source_definition_digest_from_body",
]
