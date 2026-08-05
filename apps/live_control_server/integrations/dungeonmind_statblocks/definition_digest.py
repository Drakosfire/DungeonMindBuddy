"""Server-compatible statblock definition canonicalization and digests.

Mirrors DungeonMindServer ``statblocks_v1.domain.canonicalization`` /
``digests.compute_definition_digest`` so Buddy can bind
``generation_receipt.source_definition_digest`` against the same bytes the
Server hashes after parse + contract-shape restore.

OpenAPI-generated ``StatblockDefinitionV1Input`` treats many list fields as
nullable with default ``None``. Server domain models use
``Field(default_factory=list)`` for those fields. Before hashing we restore
those Server list defaults so omitted / null lists digest as ``[]``.
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

# Field names where Server StatblockDefinitionV1 uses default_factory=list.
# OpenAPI Input DTOs often expose these as list | None = None.
_SERVER_DEFAULT_EMPTY_LIST_FIELDS = frozenset(
    {
        "adjudication_tags",
        "bypasses",
        "condition_immunities",
        "costs",
        "damage_interactions",
        "disabled_element_keys",
        "effects",
        "enabled_element_keys",
        "explains",
        "failure_effects",
        "hit_effects",
        "languages",
        "miss_effects",
        "phases",
        "qualifiers",
        "resources",
        "saving_throws",
        "senses",
        "skills",
        "special_modes",
        "subtypes",
        "success_effects",
        "tags",
    }
)


def _restore_server_list_defaults(value: Any) -> Any:
    """Replace null Server-defaulted lists with [] (recursive)."""
    if isinstance(value, Mapping):
        restored: dict[str, Any] = {}
        for key, item in value.items():
            if key in _SERVER_DEFAULT_EMPTY_LIST_FIELDS and item is None:
                restored[str(key)] = []
            else:
                restored[str(key)] = _restore_server_list_defaults(item)
        return restored
    if isinstance(value, list):
        return [_restore_server_list_defaults(item) for item in value]
    return value


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


def canonicalize_definition_dict(source_definition: dict[str, Any]) -> str:
    """Canonical JSON text for a wire definition dict (Server-shaped defaults)."""
    if not isinstance(source_definition, dict):
        raise TypeError("source_definition must be an object")
    # Validate against the transport DTO, then restore Server domain list defaults
    # before hashing so omitted subtypes/languages/etc. match Server [].
    parsed = StatblockDefinitionV1Input.model_validate(source_definition)
    payload = _restore_server_list_defaults(
        parsed.model_dump(mode="json", exclude_none=False)
    )
    normalized = _normalize_value(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonicalize_definition_payload(definition: StatblockDefinitionV1Input) -> str:
    """Return version-1 canonical JSON text for a parsed definition."""
    payload = _restore_server_list_defaults(
        definition.model_dump(mode="json", exclude_none=False)
    )
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
    text = canonicalize_definition_dict(source_definition)
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "CANONICALIZER_VERSION",
    "DIGEST_ALGORITHM",
    "canonicalize_definition_dict",
    "canonicalize_definition_payload",
    "compute_definition_digest",
    "source_definition_digest_from_body",
]
