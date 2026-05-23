"""Contract tests for ingest-hints sidecar prompt copy."""

from __future__ import annotations

from src.prompts import ingest_hints_sidecar as mod


def test_ingest_hints_prompt_includes_not_the_recap_writer() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "NOT the recap writer" in prompt


def test_ingest_hints_prompt_includes_do_not_rewrite() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "Do not rewrite" in prompt or "NOT allowed to rewrite prose" in prompt


def test_ingest_hints_prompt_includes_review_only() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "review-only" in prompt


def test_ingest_hints_prompt_includes_strict_json_only() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "Output strict JSON only" in prompt


def test_ingest_hints_prompt_includes_prep_cross_refs_constraint() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "prep_cross_refs must be empty unless prep draft inputs were provided" in prompt


def test_ingest_hints_prompt_includes_evidence_requirement() -> None:
    prompt = mod.ingest_hints_system_prompt()
    assert "Every hint must include evidence" in prompt


def test_build_ingest_hints_messages_shape() -> None:
    messages = mod.build_ingest_hints_messages(
        campaign_id="longmont-c2",
        session=21,
        raw_notes_path=(
            "Longmont Campaign/Campaign 2/_ingest_staging/session_21_raw_notes.md"
        ),
        raw_notes_sha256="deadbeef",
        preprocessed_notes_path=None,
        preprocess_profile=None,
        raw_or_preprocessed_text="Session 21 Recap\n\nWhile still waiting...",
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "longmont-c2" in messages[1]["content"]
    assert "<BEGIN_NOTES>" in messages[1]["content"]


def test_ingest_hints_prompt_template_id_is_stable_hex() -> None:
    assert len(mod.INGEST_HINTS_PROMPT_TEMPLATE_ID) == 24
    assert all(c in "0123456789abcdef" for c in mod.INGEST_HINTS_PROMPT_TEMPLATE_ID)


def test_mock_llm_response_rejects_forbidden_canon_keys() -> None:
    from src.agent.ingest_hints_output_schema import (
        FORBIDDEN_CANON_PAYLOAD_KEYS,
        ingest_hints_forbidden_payload_keys,
    )

    fake_response = {
        "schema_version": "ingest_hints_v1",
        "recap_body": "# Session 21 Recap\n\nRewritten prose.",
        "normalized_body": "nope",
    }
    hits = ingest_hints_forbidden_payload_keys(fake_response)
    assert hits == sorted(k for k in fake_response if k in FORBIDDEN_CANON_PAYLOAD_KEYS)
