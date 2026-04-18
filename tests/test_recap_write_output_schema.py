"""Tests for the ``recap-write`` skill structured-output schema and parser."""

from __future__ import annotations

import copy

import pytest

from src.agent.recap_write_output_schema import (
    RECAP_WRITE_SCHEMA_VERSION,
    extract_recap_write_payload,
    extract_recap_write_payload_loose,
    recap_write_output_json_schema,
    validate_recap_write_payload,
)


def _valid_payload() -> dict:
    return {
        "schema_version": RECAP_WRITE_SCHEMA_VERSION,
        "recap_preview": {
            "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "mode": "create",
            "confirm_token": "1c3063abf61d330a34c83cdd4aa1dbe4",
        },
        "duplicate_paragraphs": [
            {
                "source_lines": [6, 10],
                "paragraph_preview": "Back in town, Bonogo and Stuart approach the warehouse...",
                "recommended_action": "remove_later",
            }
        ],
        "npc_audit": {
            "timeline_append_candidates": [
                {
                    "slug": "captain_lysandra_ironveil",
                    "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "reason": "Recurring NPC; significant beat (charm + tower blueprint reveal).",
                }
            ],
            "new_hub_proposals": [
                {
                    "proposed_slug": "marla_brambleback",
                    "campaign_or_setting": "campaign",
                    "proposed_location": "Longmont Campaign/Campaign 2/NPCs/marla_brambleback/",
                    "initial_files": [
                        "README.md",
                        "marla_brambleback_character_dossier.md",
                        "timeline.md",
                    ],
                    "evidence_quote": "Marla approached Caelynn about Bonogo...",
                    "rationale": "First appearance, named with surname in prep doc, Mossford power center.",
                }
            ],
            "dismissed": [
                {
                    "name": "Stuart (halfling boy)",
                    "reason": "Sidekick role, not power center; covered by prep doc.",
                }
            ],
        },
        "plot_artifacts": [
            {
                "name": "tower blueprint (Lysandra dirt sketch)",
                "evidence_quote": "she has drawn a top-down blueprint of a tower in the dirt",
                "proposed_locations": [
                    "Longmont Campaign/Campaign 2/Locations/tower_of_voices.md",
                    "Longmont Campaign/Campaign 2/Plot Artifacts/tower_blueprint_lysandra_dirt.md",
                ],
            }
        ],
        "prep_pointer_proposal": {
            "prep_path": "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
            "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "prep_append_line": "> **Played:** See `Session Recaps/Session 20 - Recap.md`. ...",
            "recap_append_line": "> **Prep:** See `Session Prep/session_20_stacey_stuart_marla_reference.md`. ...",
        },
        "notes_for_gm": "",
    }


def test_recap_write_output_json_schema_shape_is_object_with_required_keys() -> None:
    schema = recap_write_output_json_schema()
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    required = schema["required"]
    assert set(required) == {
        "schema_version",
        "recap_preview",
        "duplicate_paragraphs",
        "npc_audit",
        "plot_artifacts",
        "prep_pointer_proposal",
        "notes_for_gm",
    }
    assert schema["properties"]["schema_version"]["enum"] == [RECAP_WRITE_SCHEMA_VERSION]


def test_validate_recap_write_payload_accepts_valid_session_20_payload() -> None:
    assert validate_recap_write_payload(_valid_payload()) == []


def test_validate_recap_write_payload_accepts_empty_lists_and_null_prep_pointer() -> None:
    payload = _valid_payload()
    payload["duplicate_paragraphs"] = []
    payload["plot_artifacts"] = []
    payload["npc_audit"] = {
        "timeline_append_candidates": [],
        "new_hub_proposals": [],
        "dismissed": [],
    }
    payload["prep_pointer_proposal"] = None
    assert validate_recap_write_payload(payload) == []


def test_validate_recap_write_payload_flags_missing_top_level_keys() -> None:
    payload = _valid_payload()
    del payload["plot_artifacts"]
    del payload["notes_for_gm"]
    violations = validate_recap_write_payload(payload)
    assert any("plot_artifacts" in v for v in violations)
    assert any("notes_for_gm" in v for v in violations)


def test_validate_recap_write_payload_flags_wrong_recap_preview_mode() -> None:
    payload = _valid_payload()
    payload["recap_preview"]["mode"] = "append"
    violations = validate_recap_write_payload(payload)
    assert any("recap_preview.mode" in v for v in violations)


def test_validate_recap_write_payload_flags_short_source_lines() -> None:
    payload = _valid_payload()
    payload["duplicate_paragraphs"][0]["source_lines"] = [6]
    violations = validate_recap_write_payload(payload)
    assert any("source_lines" in v for v in violations)


def test_validate_recap_write_payload_flags_short_proposed_locations() -> None:
    payload = _valid_payload()
    payload["plot_artifacts"][0]["proposed_locations"] = ["Locations/tower.md"]
    violations = validate_recap_write_payload(payload)
    assert any("proposed_locations" in v for v in violations)


def test_validate_recap_write_payload_flags_wrong_schema_version() -> None:
    payload = _valid_payload()
    payload["schema_version"] = "recap_write_v0"
    violations = validate_recap_write_payload(payload)
    assert any("schema_version" in v for v in violations)


def test_validate_recap_write_payload_flags_npc_audit_missing_subkeys() -> None:
    payload = _valid_payload()
    payload["npc_audit"] = {"timeline_append_candidates": []}
    violations = validate_recap_write_payload(payload)
    assert any("new_hub_proposals" in v for v in violations)
    assert any("dismissed" in v for v in violations)


def test_extract_recap_write_payload_finds_fenced_json_block() -> None:
    body = (
        "Drafted Session 20 recap. Structured follow-ups below.\n\n"
        "```json\n"
        '{"schema_version": "recap_write_v1", "notes_for_gm": ""}\n'
        "```\n\n"
        "Type `apply` to commit."
    )
    parsed = extract_recap_write_payload(body)
    assert parsed == {"schema_version": "recap_write_v1", "notes_for_gm": ""}


def test_extract_recap_write_payload_accepts_no_language_tag() -> None:
    body = "preamble\n```\n{\"schema_version\": \"recap_write_v1\"}\n```\nepilogue"
    parsed = extract_recap_write_payload(body)
    assert parsed == {"schema_version": "recap_write_v1"}


def test_extract_recap_write_payload_returns_none_when_missing() -> None:
    assert extract_recap_write_payload("no fenced block here") is None
    assert extract_recap_write_payload("") is None
    assert extract_recap_write_payload("```\nnot-json\n```") is None


def test_extract_recap_write_payload_returns_none_when_block_is_array() -> None:
    body = "```json\n[1,2,3]\n```"
    assert extract_recap_write_payload(body) is None


def test_extract_recap_write_payload_handles_nested_json_objects() -> None:
    """Regression: non-greedy regex used to stop at the first inner ``}``."""
    body = (
        "Here is the payload.\n\n```json\n"
        '{"outer": {"inner": 1}, "schema_version": "recap_write_v1"}\n'
        "```\n"
    )
    parsed = extract_recap_write_payload(body)
    assert parsed == {"outer": {"inner": 1}, "schema_version": "recap_write_v1"}


def test_extract_recap_write_payload_prefers_outer_recap_object() -> None:
    """Inner ``{...}`` dicts must not win over the full recap_write root."""
    body = (
        "```json\n"
        '{"inner": {"x": 1}, "schema_version": "recap_write_v1", '
        '"recap_preview": {"path": "a", "mode": "create", "confirm_token": "t"}, '
        '"duplicate_paragraphs": [], "npc_audit": {"timeline_append_candidates": [], '
        '"new_hub_proposals": [], "dismissed": []}, "plot_artifacts": [], '
        '"prep_pointer_proposal": null, "notes_for_gm": ""}\n'
        "```\n"
    )
    parsed = extract_recap_write_payload(body)
    assert parsed is not None
    assert parsed.get("schema_version") == RECAP_WRITE_SCHEMA_VERSION
    assert "inner" in parsed


def test_extract_recap_write_payload_after_diff_fence_pairing() -> None:
    """Closing `` ``` `` must not be mistaken for opening a JSON fence."""
    body = (
        "Preview.\n\n```diff\n--- a/foo\n+++ b/foo\n```\n\n"
        "```json\n"
        '{"schema_version": "recap_write_v1", "notes_for_gm": ""}\n'
        "```\n"
    )
    parsed = extract_recap_write_payload(body)
    assert parsed == {"schema_version": "recap_write_v1", "notes_for_gm": ""}


def test_extract_recap_write_payload_loose_finds_embedded_object() -> None:
    """No fence: still recover the recap root from a larger JSON soup."""
    payload = _valid_payload()
    import json

    soup = (
        'prefix junk {"user_intent": null} more '
        + json.dumps(payload, ensure_ascii=False)
        + " trailing"
    )
    got = extract_recap_write_payload_loose(soup)
    assert got is not None
    assert got.get("schema_version") == RECAP_WRITE_SCHEMA_VERSION


def test_validate_recap_write_payload_round_trip_via_extractor() -> None:
    """The extractor + validator stack accepts a model-shaped message body."""
    import json

    payload = _valid_payload()
    body = (
        "Drafted Session 20 recap. Structured follow-ups below.\n\n"
        "```json\n"
        + json.dumps(payload)
        + "\n```\n"
    )
    parsed = extract_recap_write_payload(body)
    assert parsed is not None
    assert validate_recap_write_payload(parsed) == []


@pytest.mark.parametrize(
    "drop_key",
    [
        "schema_version",
        "recap_preview",
        "duplicate_paragraphs",
        "npc_audit",
        "plot_artifacts",
        "prep_pointer_proposal",
        "notes_for_gm",
    ],
)
def test_validate_recap_write_payload_each_required_key_is_required(drop_key: str) -> None:
    payload = _valid_payload()
    del payload[drop_key]
    violations = validate_recap_write_payload(payload)
    assert any(drop_key in v for v in violations), f"expected violation mentioning {drop_key}"


def test_valid_payload_isolation_helper_does_not_share_state() -> None:
    """Ensure mutations in one test do not leak into another."""
    a = _valid_payload()
    b = _valid_payload()
    a["notes_for_gm"] = "mutated"
    assert b["notes_for_gm"] == ""
    assert copy.deepcopy(a) == a
