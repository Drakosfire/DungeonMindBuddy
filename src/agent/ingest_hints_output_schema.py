"""Structured-output schema for the ``ingest-hints-sidecar`` skill.

Review-only metadata sidecar for raw session notes. Hints may seed downstream
judgment; they must never rewrite prose or promote canon without operator review.
"""

from __future__ import annotations

from typing import Any

INGEST_HINTS_SCHEMA_VERSION = "ingest_hints_v1"

CONFIDENCE_ENUM = ("high", "medium", "low")
EVIDENCE_SOURCE_ENUM = ("raw_notes", "preprocessed_notes", "prep_draft")
AUTHORITY_STATUS = "review_only"
PROMOTION_NOTE_TITLE = "Operator must approve before recap title or _SLUGS use."
PROMOTION_NOTE_SLUG = "Operator must approve before _SLUGS or normalized filename use."
SPELLING_RECOMMENDATION = "audit_only_do_not_autocorrect"

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
        "raw_notes_sha256": {"type": "string"},
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


def ingest_hints_forbidden_payload_keys(payload: dict[str, Any]) -> list[str]:
    """Return forbidden canon/prose keys if present at top level."""
    return sorted(k for k in payload if k in FORBIDDEN_CANON_PAYLOAD_KEYS)


def _validate_evidence_list(
    violations: list[str],
    *,
    path: str,
    evidence: Any,
    required: bool,
) -> None:
    if not isinstance(evidence, list):
        violations.append(f"{path} must be a list")
        return
    if required and not evidence:
        violations.append(f"{path} must include at least one evidence object")
        return
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            violations.append(f"{path}[{i}] must be an object")
            continue
        for key in _EVIDENCE_SCHEMA["required"]:
            if key not in item:
                violations.append(f"{path}[{i}] missing required key: {key!r}")
        source = item.get("source")
        if source is not None and source not in EVIDENCE_SOURCE_ENUM:
            violations.append(f"{path}[{i}].source invalid: {source!r}")


def _validate_hint_with_evidence(
    violations: list[str],
    *,
    path: str,
    obj: Any,
    promotion_note_expected: str,
) -> None:
    if not isinstance(obj, dict):
        violations.append(f"{path} must be an object")
        return
    for key in _HINT_WITH_EVIDENCE_SCHEMA["required"]:
        if key not in obj:
            violations.append(f"{path} missing required key: {key!r}")
    value = obj.get("value")
    evidence = obj.get("evidence")
    if value is not None:
        if not isinstance(value, str) or not value.strip():
            violations.append(f"{path}.value must be a non-empty string when set")
        _validate_evidence_list(
            violations, path=f"{path}.evidence", evidence=evidence, required=True
        )
        note = obj.get("promotion_note")
        if note != promotion_note_expected:
            violations.append(
                f"{path}.promotion_note must be {promotion_note_expected!r} when value is set"
            )
    else:
        _validate_evidence_list(
            violations, path=f"{path}.evidence", evidence=evidence, required=False
        )
    conf = obj.get("confidence")
    if conf not in CONFIDENCE_ENUM:
        violations.append(f"{path}.confidence must be one of {CONFIDENCE_ENUM}, got {conf!r}")


def validate_ingest_hints_payload(payload: dict[str, Any]) -> list[str]:
    """Return human-readable violations; empty list means structurally valid."""
    violations: list[str] = []

    if not isinstance(payload, dict):
        return [f"payload must be a JSON object, got {type(payload).__name__}"]

    violations.extend(
        f"forbidden canon/prose key at top level: {k!r}"
        for k in ingest_hints_forbidden_payload_keys(payload)
    )

    unknown = set(payload) - set(ingest_hints_output_json_schema()["properties"])
    if unknown:
        violations.append(f"unknown top-level keys: {sorted(unknown)!r}")

    schema = ingest_hints_output_json_schema()
    for key in schema["required"]:
        if key not in payload:
            violations.append(f"missing required top-level key: {key!r}")

    if payload.get("schema_version") != INGEST_HINTS_SCHEMA_VERSION:
        violations.append(
            f"schema_version must be {INGEST_HINTS_SCHEMA_VERSION!r}, "
            f"got {payload.get('schema_version')!r}"
        )

    authority = payload.get("authority")
    if isinstance(authority, dict):
        if authority.get("status") != AUTHORITY_STATUS:
            violations.append(f"authority.status must be {AUTHORITY_STATUS!r}")
        for flag in (
            "may_modify_prose",
            "may_modify_canon",
            "may_modify_slug",
        ):
            if authority.get(flag) is not False:
                violations.append(f"authority.{flag} must be false")
        if authority.get("promotion_requires_operator_review") is not True:
            violations.append("authority.promotion_requires_operator_review must be true")
    elif authority is not None:
        violations.append("authority must be an object")

    _validate_hint_with_evidence(
        violations,
        path="suggested_title",
        obj=payload.get("suggested_title"),
        promotion_note_expected=PROMOTION_NOTE_TITLE,
    )
    _validate_hint_with_evidence(
        violations,
        path="suggested_slug",
        obj=payload.get("suggested_slug"),
        promotion_note_expected=PROMOTION_NOTE_SLUG,
    )

    entities = payload.get("entities")
    if isinstance(entities, dict):
        for bucket in _ENTITIES_SCHEMA["required"]:
            items = entities.get(bucket)
            if not isinstance(items, list):
                violations.append(f"entities.{bucket} must be a list")
                continue
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    violations.append(f"entities.{bucket}[{i}] must be an object")
                    continue
                for key in _ENTITY_SCHEMA["required"]:
                    if key not in item:
                        violations.append(
                            f"entities.{bucket}[{i}] missing required key: {key!r}"
                        )
                _validate_evidence_list(
                    violations,
                    path=f"entities.{bucket}[{i}].evidence",
                    evidence=item.get("evidence"),
                    required=True,
                )
    elif entities is not None:
        violations.append("entities must be an object")

    for i, thread in enumerate(payload.get("open_threads") or []):
        if not isinstance(thread, dict):
            violations.append(f"open_threads[{i}] must be an object")
            continue
        for key in _OPEN_THREAD_SCHEMA["required"]:
            if key not in thread:
                violations.append(f"open_threads[{i}] missing required key: {key!r}")
        _validate_evidence_list(
            violations,
            path=f"open_threads[{i}].evidence",
            evidence=thread.get("evidence"),
            required=True,
        )

    for i, variant in enumerate(payload.get("spelling_variants") or []):
        if not isinstance(variant, dict):
            violations.append(f"spelling_variants[{i}] must be an object")
            continue
        for key in _SPELLING_VARIANT_SCHEMA["required"]:
            if key not in variant:
                violations.append(f"spelling_variants[{i}] missing required key: {key!r}")
        _validate_evidence_list(
            violations,
            path=f"spelling_variants[{i}].evidence",
            evidence=variant.get("evidence"),
            required=True,
        )

    for i, ref in enumerate(payload.get("prep_cross_refs") or []):
        if not isinstance(ref, dict):
            violations.append(f"prep_cross_refs[{i}] must be an object")
            continue
        for key in _PREP_CROSS_REF_SCHEMA["required"]:
            if key not in ref:
                violations.append(f"prep_cross_refs[{i}] missing required key: {key!r}")
        if not ref.get("prep_path"):
            violations.append(f"prep_cross_refs[{i}].prep_path is required")
        _validate_evidence_list(
            violations,
            path=f"prep_cross_refs[{i}].evidence",
            evidence=ref.get("evidence"),
            required=True,
        )

    notes = payload.get("notes_for_operator")
    if not isinstance(notes, str):
        violations.append("notes_for_operator must be a string")

    return violations
