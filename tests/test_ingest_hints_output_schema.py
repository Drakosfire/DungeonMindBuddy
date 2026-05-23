"""Tests for the ingest-hints sidecar structured-output schema."""

from __future__ import annotations

import copy

import pytest

from src.agent.ingest_hints_output_schema import (
    FORBIDDEN_CANON_PAYLOAD_KEYS,
    INGEST_HINTS_SCHEMA_VERSION,
    PROMOTION_NOTE_SLUG,
    PROMOTION_NOTE_TITLE,
    ingest_hints_forbidden_payload_keys,
    ingest_hints_output_json_schema,
    validate_ingest_hints_payload,
)


def _evidence(
    *,
    block_id: str = "block_1",
    quote: str = "Frank apologizes",
    source: str = "raw_notes",
) -> dict:
    return {
        "source": source,
        "block_id": block_id,
        "quote": quote,
    }


def _minimal_payload() -> dict:
    return {
        "schema_version": INGEST_HINTS_SCHEMA_VERSION,
        "authority": {
            "status": "review_only",
            "may_modify_prose": False,
            "may_modify_canon": False,
            "may_modify_slug": False,
            "promotion_requires_operator_review": True,
        },
        "source": {
            "campaign_id": "longmont-c2",
            "session": 21,
            "raw_notes_path": (
                "Longmont Campaign/Campaign 2/_ingest_staging/session_21_raw_notes.md"
            ),
            "raw_notes_sha256": "abc123",
            "preprocessed_notes_path": None,
            "preprocess_profile": None,
        },
        "suggested_title": {
            "value": None,
            "confidence": "low",
            "evidence": [],
            "promotion_note": PROMOTION_NOTE_TITLE,
        },
        "suggested_slug": {
            "value": None,
            "confidence": "low",
            "evidence": [],
            "promotion_note": PROMOTION_NOTE_SLUG,
        },
        "entities": {
            "npcs": [],
            "locations": [],
            "items": [],
            "factions": [],
            "creatures": [],
        },
        "open_threads": [],
        "spelling_variants": [],
        "prep_cross_refs": [],
        "warnings": [],
        "notes_for_operator": "",
    }


def test_ingest_hints_output_json_schema_rejects_additional_properties() -> None:
    schema = ingest_hints_output_json_schema()
    assert schema.get("additionalProperties") is False
    assert schema["properties"]["schema_version"]["enum"] == [INGEST_HINTS_SCHEMA_VERSION]


def test_validate_ingest_hints_payload_accepts_minimal_payload() -> None:
    assert validate_ingest_hints_payload(_minimal_payload()) == []


def test_validate_ingest_hints_payload_flags_missing_schema_version() -> None:
    payload = _minimal_payload()
    payload["schema_version"] = "wrong"
    violations = validate_ingest_hints_payload(payload)
    assert any("schema_version" in v for v in violations)


def test_validate_ingest_hints_payload_requires_authority_review_only() -> None:
    payload = _minimal_payload()
    payload["authority"]["may_modify_prose"] = True
    violations = validate_ingest_hints_payload(payload)
    assert any("may_modify_prose" in v for v in violations)


def test_validate_ingest_hints_payload_requires_evidence_for_non_null_slug() -> None:
    payload = _minimal_payload()
    payload["suggested_slug"] = {
        "value": "drake-nest-mirathorn-call",
        "confidence": "medium",
        "evidence": [],
        "promotion_note": PROMOTION_NOTE_SLUG,
    }
    violations = validate_ingest_hints_payload(payload)
    assert any("suggested_slug.evidence" in v for v in violations)


def test_validate_ingest_hints_payload_requires_promotion_note_when_slug_set() -> None:
    payload = _minimal_payload()
    payload["suggested_slug"] = {
        "value": "drake-nest-mirathorn-call",
        "confidence": "medium",
        "evidence": [_evidence(quote="young drakes")],
        "promotion_note": "wrong note",
    }
    violations = validate_ingest_hints_payload(payload)
    assert any("suggested_slug.promotion_note" in v for v in violations)


def test_validate_ingest_hints_payload_entity_requires_evidence() -> None:
    payload = _minimal_payload()
    payload["entities"]["npcs"] = [
        {
            "name": "Frank",
            "confidence": "high",
            "evidence": [],
            "possible_slug": "frank",
            "notes": "Mirathorn contact",
        }
    ]
    violations = validate_ingest_hints_payload(payload)
    assert any("entities.npcs[0].evidence" in v for v in violations)


def test_validate_ingest_hints_payload_prep_cross_refs_require_evidence_and_path() -> None:
    payload = _minimal_payload()
    payload["prep_cross_refs"] = [
        {
            "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_21_foo.md",
            "relationship": "supports",
            "summary": "Prep mentioned Mossford storm beat.",
            "confidence": "medium",
            "evidence": [_evidence(source="prep_draft", quote="storm warning")],
        }
    ]
    assert validate_ingest_hints_payload(payload) == []


def test_validate_ingest_hints_payload_rejects_unknown_top_level_keys() -> None:
    payload = _minimal_payload()
    payload["recap_body"] = "should not be here"
    violations = validate_ingest_hints_payload(payload)
    assert any("forbidden canon/prose key" in v for v in violations)
    assert ingest_hints_forbidden_payload_keys(payload) == ["recap_body"]


@pytest.mark.parametrize("forbidden_key", sorted(FORBIDDEN_CANON_PAYLOAD_KEYS))
def test_forbidden_canon_keys_detected(forbidden_key: str) -> None:
    payload = _minimal_payload()
    payload[forbidden_key] = {"any": "value"}
    assert forbidden_key in ingest_hints_forbidden_payload_keys(payload)


def test_validate_ingest_hints_payload_open_thread_requires_evidence() -> None:
    payload = _minimal_payload()
    payload["open_threads"] = [
        {
            "summary": "Press on to swamp or return to Mirathorn.",
            "prep_relevance": "S22 opening fork.",
            "confidence": "high",
            "evidence": [],
        }
    ]
    violations = validate_ingest_hints_payload(payload)
    assert any("open_threads[0].evidence" in v for v in violations)


def test_validate_ingest_hints_payload_accepts_rich_payload() -> None:
    payload = copy.deepcopy(_minimal_payload())
    payload["suggested_title"] = {
        "value": "Session 21 - Drake Nest and Mirathorn Call",
        "confidence": "medium",
        "evidence": [_evidence(quote="young drakes")],
        "promotion_note": PROMOTION_NOTE_TITLE,
    }
    payload["entities"]["npcs"] = [
        {
            "name": "Frank",
            "confidence": "high",
            "evidence": [_evidence(quote="connected with Frank")],
            "possible_slug": "frank",
            "notes": "Mirathorn contact",
        }
    ]
    assert validate_ingest_hints_payload(payload) == []
