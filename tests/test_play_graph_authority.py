"""Pure Play intent/source commitments; no APP admission, DB or SDK claims."""
import json
from hashlib import sha256
from uuid import UUID

import pytest

from application_state.agent_conversation.play_graph_authority import (
    PlayGraphIntentV1, PlaySourceFrameV1, PlaySourceLocatorV1, PlaySourcePayloadV1,
    play_graph_intent_fingerprint, play_source_frame, source_entry,
    validate_play_source_owner_join,
)
from application_state.agent_conversation.rules_authority_types import canonical_bytes, canonical_sha256
from application_state.agent_conversation.types import PlayContentBasis, PlayRunTurnContextReceiptV2

MOMENT = "# North\nThe prepared boardwalk 🦉 scene."
NOTE = "Saved 🦉 note."


def basis():
    return PlayRunTurnContextReceiptV2(world_id="world-one", run_id="run-one", run_revision=3,
        runbook_object_id="plan-one", runbook_object_revision=7,
        runbook_work_revision_id=UUID("00000000-0000-4000-8000-000000000001"), runbook_revision_n=2,
        runbook_content_sha256="a" * 64, beat_id="beat:north", scene_id="scene:boardwalk",
        edition_revision=0, edition_revision_id=None, content_sha256="a" * 64,
        scene_note=NOTE, scene_note_sha256=sha256(NOTE.encode()).hexdigest())


def payload(kind="current_moment", text=None, **locator_changes):
    b = basis()
    locator = dict(world_id=b.world_id, run_id=b.run_id, run_revision=b.run_revision,
        edition=PlayContentBasis(edition_revision=0, edition_revision_id=None, content_sha256=b.content_sha256),
        beat_id=b.beat_id, scene_id=b.scene_id)
    locator.update(locator_changes)
    return PlaySourcePayloadV1(source_kind=kind, locator=PlaySourceLocatorV1(**locator),
        text=text if text is not None else NOTE if kind == "scene_note" else MOMENT)


def intent_wire():
    return dict(schema="dmb_play_graph_intent_v1", world_id="world-one", client_thread_id="client-one",
        message="Discuss occupied space 🦉.", surface_id="play", surface_instance_id="play:run-one",
        client_work_state="saved_clean", primary_work=dict(kind="run", object_id="run-one", expected_revision=3,
            play_content_basis=dict(edition_revision=0, edition_revision_id=None, content_sha256="a" * 64)),
        play_graph_policy=dict(schema="dmb_play_graph_policy_v1", policy="native_play_world_v1"),
        play_target=dict(schema="dmb_submitted_play_target_v1", beat_id="beat:north", scene_id="scene:boardwalk", marker_grammar_version="v2"),
        graph_request=dict(mode="world", world_id="world-one", campaign_id=None, revision_pin=None, focus=dict(kind="none")),
        graph_selection=None)


def test_native_play_intent_is_explicit_and_fingerprints_only_original_submission():
    first = PlayGraphIntentV1.model_validate_json(json.dumps(intent_wire()))
    assert PlayGraphIntentV1.model_validate_json(first.model_dump_json(by_alias=True)) == first
    assert play_graph_intent_fingerprint(first) == canonical_sha256(first.model_dump(mode="json", by_alias=True, exclude={"client_thread_id"}))
    routed = intent_wire()
    routed["client_thread_id"] = "resolved-or-renewed-thread"
    assert play_graph_intent_fingerprint(PlayGraphIntentV1.model_validate_json(json.dumps(routed))) == play_graph_intent_fingerprint(first)
    changed = intent_wire()
    changed["play_target"]["scene_id"] = "scene:other"
    second = PlayGraphIntentV1.model_validate_json(json.dumps(changed))
    assert play_graph_intent_fingerprint(first) != play_graph_intent_fingerprint(second)
    assert first.message == "Discuss occupied space 🦉."


@pytest.mark.parametrize("change", ["old_schema", "surface", "work", "edition", "graph_none", "foreign_world", "focus", "policy", "target", "resolved_state"])
def test_native_play_intent_rejects_other_protocols_and_unpinned_or_resolved_inputs(change):
    value = intent_wire()
    if change == "old_schema": value["schema"] = "dmb_agent_submitted_turn_intent_v1"
    if change == "surface": value["surface_id"] = "plan"
    if change == "work": value["primary_work"]["kind"] = "combat"
    if change == "edition": value["primary_work"]["play_content_basis"] = None
    if change == "graph_none": value["graph_request"] = dict(mode="none")
    if change == "foreign_world": value["graph_request"]["world_id"] = "other"
    if change == "focus": value["graph_request"]["focus"] = dict(kind="session", session_id="other")
    if change == "policy": value["play_graph_policy"]["policy"] = "auto_plan_world"
    if change == "target": value["play_target"]["scene_id"] = "beat:wrong"
    if change == "resolved_state": value["graph_authority"] = dict(native_world_id="not-operator-input")
    with pytest.raises(ValueError):
        PlayGraphIntentV1.model_validate_json(json.dumps(value))


def test_manifest_is_deterministic_sorted_exact_and_unicode_codepoint_bounded():
    moment, note = payload(), payload("scene_note")
    first = play_source_frame((moment, note))
    assert play_source_frame((note, moment)) == first
    assert PlaySourceFrameV1.model_validate_json(first.model_dump_json(by_alias=True)) == first
    assert len(canonical_bytes(first)) <= 65536
    entry = source_entry(note)
    assert entry.text_codepoints == len(NOTE)
    assert entry.text_utf8_bytes == len(NOTE.encode()) > entry.text_codepoints
    assert entry.payload_sha256 == canonical_sha256(note)
    assert entry.source_id == "play-source:" + entry.payload_sha256
    validate_play_source_owner_join(first, basis(), owner_resolved_current_moment_text=MOMENT)


def test_empty_frame_exposes_no_source_and_does_not_invent_missing_text():
    frame = play_source_frame(())
    assert frame.manifest.entries == () and frame.sources == ()
    validate_play_source_owner_join(frame, basis(), owner_resolved_current_moment_text=None)
    with pytest.raises(ValueError, match="independent source owner"):
        validate_play_source_owner_join(play_source_frame((payload(),)), basis(), owner_resolved_current_moment_text=None)


@pytest.mark.parametrize("change", ["world", "run", "revision", "edition", "beat", "scene", "note", "moment"])
def test_owner_join_requires_exact_independently_resolved_owner_and_body(change):
    updates = {}
    if change == "world": updates["world_id"] = "other"
    if change == "run": updates["run_id"] = "other"
    if change == "revision": updates["run_revision"] = 4
    if change == "edition": updates["edition"] = PlayContentBasis(edition_revision=1,
        edition_revision_id=UUID("00000000-0000-4000-8000-000000000002"), content_sha256="b" * 64)
    if change == "beat": updates["beat_id"] = "beat:other"
    if change == "scene": updates["scene_id"] = "scene:other"
    source = payload("scene_note" if change == "note" else "current_moment",
        text="Other body" if change in {"note", "moment"} else None, **updates)
    with pytest.raises(ValueError):
        validate_play_source_owner_join(play_source_frame((source,)), basis(), owner_resolved_current_moment_text=MOMENT)


@pytest.mark.parametrize("change", ["text", "payload_digest", "text_digest", "byte_count", "seal", "unknown", "order"])
def test_frame_rejects_self_inconsistent_wire_materials(change):
    frame = play_source_frame((payload(), payload("scene_note")))
    wire = frame.model_dump(mode="json", by_alias=True)
    if change == "text": wire["sources"][0]["text"] += "changed"
    if change == "payload_digest":
        wire["manifest"]["entries"][0]["payload_sha256"] = "0" * 64
        wire["manifest"]["entries"][0]["source_id"] = "play-source:" + "0" * 64
    if change == "text_digest": wire["manifest"]["entries"][0]["text_sha256"] = "0" * 64
    if change == "byte_count": wire["manifest"]["entries"][0]["text_utf8_bytes"] += 1
    if change == "seal": wire["manifest"]["manifest_sha256"] = "0" * 64
    if change == "unknown": wire["sources"][0]["source_uri"] = "file:/private"
    if change == "order": wire["sources"].reverse()
    if change != "seal":
        wire["manifest"]["manifest_sha256"] = canonical_sha256({key: value for key, value in wire["manifest"].items() if key != "manifest_sha256"})
    with pytest.raises(ValueError):
        PlaySourceFrameV1.model_validate_json(json.dumps(wire))


def test_duplicate_or_unsupplied_kind_cannot_become_more_source_authority():
    with pytest.raises(ValueError):
        play_source_frame((payload(), payload()))
    two_moments = play_source_frame((payload(), payload(text="Other")))
    with pytest.raises(ValueError):
        validate_play_source_owner_join(two_moments, basis(), owner_resolved_current_moment_text=MOMENT)
    wire = payload().model_dump(mode="json", by_alias=True)
    wire["source_kind"] = "closing_reflections"
    with pytest.raises(ValueError):
        PlaySourcePayloadV1.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("text", [" ", "🦉" * 8193, "\x01" * 10000])
def test_oversized_or_blank_sources_fail_without_truncation(text):
    with pytest.raises(ValueError):
        payload(text=text)


def test_combined_frame_utf8_budget_is_independent_of_individual_payload_budgets():
    text = "x" * 32000
    moment, note = payload(text=text), payload("scene_note", text=text)
    assert len(canonical_bytes(moment)) < 49152 and len(canonical_bytes(note)) < 49152
    with pytest.raises(ValueError, match="frame exceeds"):
        play_source_frame((moment, note))
