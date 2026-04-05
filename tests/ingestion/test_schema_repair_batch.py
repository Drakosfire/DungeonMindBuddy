from __future__ import annotations

from src.contracts.schema_validation import list_validation_failures, validate_instance
from src.ingestion.schema_repair_batch import build_entity_repair_user_prompt


def _minimal_bad_entity() -> dict:
    return {
        "schema_version": "0.1.0",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "record_status": "active",
        "entity_id": "ent_test",
        "entity_class": "actor",
        "entity_type": "npc",
        "entity_kind": "actor",
        "decision": "entity",
        "exclude_reason": None,
        "source_profile": "session_recap",
        "authority": "rumor_or_b_belief",
        "confidence": 0.5,
        "span_text": "Test NPC",
        "extraction_method": "llm",
        "display_name": "Test NPC",
        "canonical_name": None,
        "aliases": ["Test NPC"],
        "entity_status": "provisional",
        "merged_into_entity_id": None,
        "source_mention_ids": ["men_x_0"],
        "review_state": "unreviewed",
        "entity_tags": [],
        "semantic_facets": [],
        "subtype_facets": [],
        "narrative_tags": [],
        "document_tags": [],
        "notes": None,
    }


def test_list_validation_failures_finds_bad_authority() -> None:
    rec = _minimal_bad_entity()
    bad = list_validation_failures([rec], "entity.schema.json")
    assert len(bad) == 1
    idx, _obj, err = bad[0]
    assert idx == 0
    assert "rumor_or_b_belief" in err or "authority" in err.lower()


def test_build_entity_repair_user_prompt_includes_debug_context() -> None:
    rec = _minimal_bad_entity()
    bad = list_validation_failures([rec], "entity.schema.json")
    assert len(bad) == 1
    prompt = build_entity_repair_user_prompt(record=rec, validation_error=bad[0][2])
    assert "rumor_or_b_belief" in prompt
    assert "authority" in prompt
    assert "entity.schema.json" in prompt or "constraints" in prompt


def test_authority_fix_validates() -> None:
    rec = _minimal_bad_entity()
    rec["authority"] = "rumor_or_belief"
    validate_instance(rec, "entity.schema.json")
