"""Buddy statblock definition canonicalization and digests.

Mirrors DungeonMindServer ``statblocks_v1.domain.canonicalization`` /
``digests.compute_definition_digest`` so Buddy can bind
``generation_receipt.source_definition_digest`` against the same bytes the
Server hashes after parse + contract-shape restore for fields the accepted
Server contract supports. The generated Buddy DTO also carries ``explains``,
which current Server main rejects as an extra field. Non-null ``explains``
digests below are Buddy-local audit values only; they do not claim Server
acceptance or digest compatibility. The create client refuses to send them.

OpenAPI-generated ``StatblockDefinitionV1Input`` treats many list fields as
nullable with default ``None``. Server domain models use
``Field(default_factory=list)`` for most of those fields. Before hashing we
restore those Server list defaults so omitted / null lists digest as ``[]``.
``RuleElement.explains`` is intentionally different: omission must remain
omission for historical canonical bytes, while an explicit empty list remains
an explicit empty list.
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


def _canonical_payload(definition: StatblockDefinitionV1Input) -> dict[str, Any]:
    """Build Buddy canonical JSON while preserving local ``explains`` intent."""
    payload = definition.model_dump(mode="json", exclude_none=False)
    rule_elements = payload.get("rule_elements")
    if isinstance(rule_elements, list):
        for rule_model, rule_payload in zip(
            definition.rule_elements, rule_elements, strict=True
        ):
            # Current Server rejects the field entirely. Keep None equivalent
            # to omission in Buddy's audit digest; retain [] and populated
            # values locally, while the create adapter rejects them before HTTP.
            if rule_model.explains is None and isinstance(rule_payload, dict):
                rule_payload.pop("explains", None)
    return _restore_server_list_defaults(payload)


def canonicalize_definition_dict(source_definition: dict[str, Any]) -> str:
    """Canonical Buddy JSON with accepted Server defaults restored.

    Non-null ``RuleElement.explains`` is preserved for local audit identity, but
    is not accepted by current Server and is rejected by the create adapter.
    """
    if not isinstance(source_definition, dict):
        raise TypeError("source_definition must be an object")
    # Validate against the transport DTO, then restore Server domain list defaults
    # before hashing so omitted subtypes/languages/etc. match Server [].
    parsed = StatblockDefinitionV1Input.model_validate(source_definition)
    payload = _canonical_payload(parsed)
    normalized = _normalize_value(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonicalize_definition_payload(definition: StatblockDefinitionV1Input) -> str:
    """Return version-1 Buddy canonical JSON for a parsed definition."""
    payload = _canonical_payload(definition)
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
    """Digest a Buddy source definition; non-null explains remains local-only."""
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
