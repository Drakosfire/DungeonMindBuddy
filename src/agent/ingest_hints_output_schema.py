"""Structured-output schema for the ``ingest-hints-sidecar`` skill.

Review-only metadata sidecar for raw session notes. Hints may seed downstream
judgment; they must never rewrite prose or promote canon without operator review.
"""

from __future__ import annotations

import re
from typing import Any

INGEST_HINTS_SCHEMA_VERSION = "ingest_hints_v1"
_INGEST_HINTS_TEXT_FORMAT_NAME = "ingest_hints_v1"

CONFIDENCE_ENUM = ("high", "medium", "low")
EVIDENCE_SOURCE_ENUM = ("raw_notes", "preprocessed_notes", "prep_draft")
AUTHORITY_STATUS = "review_only"
PROMOTION_NOTE_TITLE = "Operator must approve before recap title or _SLUGS use."
PROMOTION_NOTE_SLUG = "Operator must approve before _SLUGS or normalized filename use."
SPELLING_RECOMMENDATION = "audit_only_do_not_autocorrect"
_SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")

FORBIDDEN_CANON_PAYLOAD_KEYS = frozenset(
    {
        "recap_body",
        "normalized_body",
        "breadcrumbed_body",
        "session_memory_records",
    }
)

_EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source": {
            "type": "string",
            "enum": list(EVIDENCE_SOURCE_ENUM),
        },
        "block_id": {
            "type": "string",
            "minLength": 1,
        },
        "quote": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": ["source", "block_id", "quote"],
}

_AUTHORITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {
            "type": "string",
            "enum": [AUTHORITY_STATUS],
        },
        "may_modify_prose": {"type": "boolean", "enum": [False]},
        "may_modify_canon": {"type": "boolean", "enum": [False]},
        "may_modify_slug": {"type": "boolean", "enum": [False]},
        "promotion_requires_operator_review": {"type": "boolean", "enum": [True]},
    },
    "required": [
        "status",
        "may_modify_prose",
        "may_modify_canon",
        "may_modify_slug",
        "promotion_requires_operator_review",
    ],
}

_SOURCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "campaign_id": {"type": "string", "minLength": 1},
        "session": {"type": "integer", "minimum": 1},
        "raw_notes_path": {"type": "string", "minLength": 1},
        "raw_notes_sha256": {"type": "string", "minLength": 64},
        "preprocessed_notes_path": {"type": ["string", "null"]},
        "preprocess_profile": {"type": ["string", "null"]},
    },
    "required": [
        "campaign_id",
        "session",
        "raw_notes_path",
        "raw_notes_sha256",
        "preprocessed_notes_path",
        "preprocess_profile",
    ],
}

_HINT_WITH_EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {"type": ["string", "null"]},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_ENUM)},
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
        },
        "promotion_note": {"type": "string", "minLength": 1},
    },
    "required": ["value", "confidence", "evidence", "promotion_note"],
}

_ENTITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_ENUM)},
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
            "minItems": 1,
        },
        "possible_slug": {"type": ["string", "null"]},
        "notes": {"type": "string"},
    },
    "required": ["name", "confidence", "evidence", "possible_slug", "notes"],
}

_OPEN_THREAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "prep_relevance": {"type": "string", "minLength": 1},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_ENUM)},
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["summary", "prep_relevance", "confidence", "evidence"],
}

_SPELLING_VARIANT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "canonical_unknown": {"type": "boolean"},
        "variants": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 2,
        },
        "recommendation": {
            "type": "string",
            "enum": [SPELLING_RECOMMENDATION],
        },
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["canonical_unknown", "variants", "recommendation", "evidence"],
}

_PREP_CROSS_REF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "prep_path": {"type": "string", "minLength": 1},
        "relationship": {
            "type": "string",
            "enum": ["supports", "conflicts", "possibly_related"],
        },
        "summary": {"type": "string", "minLength": 1},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_ENUM)},
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["prep_path", "relationship", "summary", "confidence", "evidence"],
}

_WARNING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "code": {"type": "string", "minLength": 1},
        "message": {"type": "string", "minLength": 1},
        "evidence": {
            "type": "array",
            "items": _EVIDENCE_SCHEMA,
        },
    },
    "required": ["code", "message", "evidence"],
}

_ENTITIES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "npcs": {"type": "array", "items": _ENTITY_SCHEMA},
        "locations": {"type": "array", "items": _ENTITY_SCHEMA},
        "items": {"type": "array", "items": _ENTITY_SCHEMA},
        "factions": {"type": "array", "items": _ENTITY_SCHEMA},
        "creatures": {"type": "array", "items": _ENTITY_SCHEMA},
    },
    "required": ["npcs", "locations", "items", "factions", "creatures"],
}


def ingest_hints_output_json_schema() -> dict[str, Any]:
    """OpenAI strict JSON schema for ``ingest_hints_v1`` sidecar payloads."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": [INGEST_HINTS_SCHEMA_VERSION],
            },
            "authority": _AUTHORITY_SCHEMA,
            "source": _SOURCE_SCHEMA,
            "suggested_title": _HINT_WITH_EVIDENCE_SCHEMA,
            "suggested_slug": _HINT_WITH_EVIDENCE_SCHEMA,
            "entities": _ENTITIES_SCHEMA,
            "open_threads": {
                "type": "array",
                "items": _OPEN_THREAD_SCHEMA,
            },
            "spelling_variants": {
                "type": "array",
                "items": _SPELLING_VARIANT_SCHEMA,
            },
            "prep_cross_refs": {
                "type": "array",
                "items": _PREP_CROSS_REF_SCHEMA,
            },
            "warnings": {
                "type": "array",
                "items": _WARNING_SCHEMA,
            },
            "notes_for_operator": {"type": "string"},
        },
        "required": [
            "schema_version",
            "authority",
            "source",
            "suggested_title",
            "suggested_slug",
            "entities",
            "open_threads",
            "spelling_variants",
            "prep_cross_refs",
            "warnings",
            "notes_for_operator",
        ],
    }


def ingest_hints_text_format(*, strict: bool = True) -> dict[str, Any]:
    """``text=`` argument for ``client.responses.create`` on ingest-hints sidecar calls.

    Pair with :func:`src.prompts.ingest_hints_sidecar.build_ingest_hints_messages`.
    """
    return {
        "format": {
            "type": "json_schema",
            "name": _INGEST_HINTS_TEXT_FORMAT_NAME,
            "strict": strict,
            "schema": ingest_hints_output_json_schema(),
        }
    }


def ingest_hints_forbidden_payload_keys(payload: dict[str, Any]) -> list[str]:
    """Return forbidden canon/prose keys if present at top level."""
    return sorted(k for k in payload if k in FORBIDDEN_CANON_PAYLOAD_KEYS)


def _schema_types(schema: dict[str, Any]) -> list[str]:
    type_spec = schema.get("type")
    if isinstance(type_spec, list):
        return [t for t in type_spec if t != "null"]
    if isinstance(type_spec, str):
        return [type_spec]
    return []


def _allows_null(schema: dict[str, Any]) -> bool:
    type_spec = schema.get("type")
    return isinstance(type_spec, list) and "null" in type_spec


def _validate_string(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if not isinstance(value, str):
        violations.append(f"{path} must be a string, got {type(value).__name__}")
        return
    min_len = schema.get("minLength")
    if isinstance(min_len, int) and len(value) < min_len:
        violations.append(f"{path} must have minLength {min_len}, got {len(value)}")
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        violations.append(f"{path} must be one of {enum!r}, got {value!r}")


def _validate_integer(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        violations.append(f"{path} must be an integer, got {type(value).__name__}")
        return
    minimum = schema.get("minimum")
    if isinstance(minimum, int) and value < minimum:
        violations.append(f"{path} must be >= {minimum}, got {value}")


def _validate_boolean(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if not isinstance(value, bool):
        violations.append(f"{path} must be a boolean, got {type(value).__name__}")
        return
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        violations.append(f"{path} must be one of {enum!r}, got {value!r}")


def _validate_array(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if not isinstance(value, list):
        violations.append(f"{path} must be a list, got {type(value).__name__}")
        return
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(value) < min_items:
        violations.append(f"{path} must have at least {min_items} items, got {len(value)}")
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for i, item in enumerate(value):
            _validate_value(item, item_schema, f"{path}[{i}]", violations)


def _validate_object(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if not isinstance(value, dict):
        violations.append(f"{path} must be an object, got {type(value).__name__}")
        return
    properties = schema.get("properties") or {}
    if schema.get("additionalProperties") is False:
        unknown = set(value) - set(properties)
        if unknown:
            violations.append(f"{path} has unknown keys: {sorted(unknown)!r}")
    for key in schema.get("required") or []:
        if key not in value:
            violations.append(f"{path} missing required key: {key!r}")
    for key, prop_schema in properties.items():
        if key in value:
            _validate_value(value[key], prop_schema, f"{path}.{key}", violations)


def _validate_value(value: Any, schema: dict[str, Any], path: str, violations: list[str]) -> None:
    if value is None:
        if _allows_null(schema):
            return
        violations.append(f"{path} must not be null")
        return

    types = _schema_types(schema)
    if not types:
        return

    if len(types) == 1:
        t = types[0]
        if t == "object":
            _validate_object(value, schema, path, violations)
        elif t == "array":
            _validate_array(value, schema, path, violations)
        elif t == "string":
            _validate_string(value, schema, path, violations)
        elif t == "integer":
            _validate_integer(value, schema, path, violations)
        elif t == "boolean":
            _validate_boolean(value, schema, path, violations)
        else:
            violations.append(f"{path} has unsupported schema type {t!r}")
        return

    matched = False
    for t in types:
        if t == "string" and isinstance(value, str):
            _validate_string(value, schema, path, violations)
            matched = True
            break
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            _validate_integer(value, schema, path, violations)
            matched = True
            break
        if t == "boolean" and isinstance(value, bool):
            _validate_boolean(value, schema, path, violations)
            matched = True
            break
        if t == "object" and isinstance(value, dict):
            _validate_object(value, schema, path, violations)
            matched = True
            break
        if t == "array" and isinstance(value, list):
            _validate_array(value, schema, path, violations)
            matched = True
            break
    if not matched:
        violations.append(f"{path} must match one of {types!r}, got {type(value).__name__}")


def _validate_source_lineage(source: dict[str, Any], violations: list[str]) -> None:
    sha = source.get("raw_notes_sha256")
    if isinstance(sha, str) and sha and not _SHA256_HEX_RE.match(sha):
        violations.append(
            "source.raw_notes_sha256 must be 64 lowercase/uppercase hex characters"
        )
    prep_path = source.get("preprocessed_notes_path")
    profile = source.get("preprocess_profile")
    if prep_path is not None and profile is None:
        violations.append(
            "source.preprocess_profile must be set when preprocessed_notes_path is non-null"
        )
    if prep_path is None and profile is not None:
        violations.append(
            "source.preprocessed_notes_path must be set when preprocess_profile is non-null"
        )


def _validate_hint_promotion_rules(payload: dict[str, Any], violations: list[str]) -> None:
    for path, expected_note in (
        ("suggested_title", PROMOTION_NOTE_TITLE),
        ("suggested_slug", PROMOTION_NOTE_SLUG),
    ):
        obj = payload.get(path)
        if not isinstance(obj, dict):
            continue
        value = obj.get("value")
        evidence = obj.get("evidence")
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                violations.append(f"{path}.value must be a non-empty string when set")
            if not isinstance(evidence, list) or not evidence:
                violations.append(f"{path}.evidence must include at least one item when value is set")
            if obj.get("promotion_note") != expected_note:
                violations.append(
                    f"{path}.promotion_note must be {expected_note!r} when value is set"
                )


def validate_ingest_hints_payload(payload: dict[str, Any]) -> list[str]:
    """Return human-readable violations; empty list means structurally valid.

    Enforces the nested ``ingest_hints_v1`` contract (types, required keys,
    ``additionalProperties: false``, enums, evidence minima) plus sidecar-specific
    lineage and promotion rules. This is the operational trust boundary named in
    ``ingest-hints-sidecar`` skill docs — not a loose forensic helper.
    """
    violations: list[str] = []

    if not isinstance(payload, dict):
        return [f"payload must be a JSON object, got {type(payload).__name__}"]

    violations.extend(
        f"forbidden canon/prose key at top level: {k!r}"
        for k in ingest_hints_forbidden_payload_keys(payload)
    )

    _validate_value(payload, ingest_hints_output_json_schema(), "payload", violations)

    source = payload.get("source")
    if isinstance(source, dict):
        _validate_source_lineage(source, violations)

    _validate_hint_promotion_rules(payload, violations)

    return violations
