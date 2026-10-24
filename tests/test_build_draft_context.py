"""Current-draft identity and provenance tests; no provider or retained state IO."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.build_draft_context import (
    POLICY, BuildDraftSnapshotV1, BuildDraftContextRecordV1,
    validate_record, validate_writer_reference, writer_reference,
)


def snapshot(text="Unsaved orchid keepers 🌸"):
    return BuildDraftSnapshotV1(world_id="example-world", document_id="example-page",
        registry_revision=3, content_sha256="a" * 64, visibility="internal",
        draft_markdown=text, draft_sha256=sha256(text.encode()).hexdigest(),
        editor_sha256="b" * 64, draft_generation=8)


def owner(snap=None):
    snap = snap or snapshot()
    record = BuildDraftContextRecordV1(record_id=UUID(int=1), turn_id=UUID(int=2),
        conversation_id=UUID(int=3), attempt=1, request_fingerprint="c" * 64, snapshot=snap)
    turn = SimpleNamespace(turn_id=record.turn_id, conversation_id=record.conversation_id,
        world_id=snap.world_id, attempt=1, request_fingerprint=record.request_fingerprint,
        graph_context_execution=SimpleNamespace(policy=SimpleNamespace(
            working_draft_context_policy=POLICY, working_draft_snapshot_sha256=snap.snapshot_sha256)),
        graph_context_receipt=SimpleNamespace(source_basis=SimpleNamespace(
            model_dump=lambda **_: snap.saved_basis())))
    return record, turn


def test_draft_body_is_complete_in_writer_and_absent_from_routing_reference():
    record, turn = owner()
    validate_record(record, turn)
    value = writer_reference(record)
    validate_writer_reference(value, record, turn)
    assert value["draft_markdown"] == record.snapshot.draft_markdown
    assert "draft_markdown" not in record.snapshot.reference()
    assert "saved_source" not in value["role"] and "not_world_or_played_truth" in value["role"]
    assert not any(key in value for key in ("source_read_id", "section_read_ids", "evidence_ref_id"))


@pytest.mark.parametrize("text", ["", "A" * 100_000, "中文 🌸\nSecond paragraph"])
def test_no_new_arbitrary_length_limit_and_exact_utf8_digest(text):
    snap = snapshot(text)
    assert BuildDraftSnapshotV1.model_validate_json(snap.model_dump_json(by_alias=True)) == snap
    with pytest.raises(ValidationError, match="captured Markdown digest"):
        BuildDraftSnapshotV1.model_validate({**snap.model_dump(), "draft_markdown": text + "changed"})


@pytest.mark.parametrize("field,value", [
    ("world_id", "another-world"), ("attempt", 2), ("turn_id", UUID(int=4)),
    ("conversation_id", UUID(int=4)), ("request_fingerprint", "d" * 64),
])
def test_frozen_turn_identity_rejects_other_attempt_or_owner(field, value):
    record, turn = owner()
    setattr(turn, field, value)
    with pytest.raises(ValueError, match="accepted turn"):
        validate_record(record, turn)


def test_frozen_context_capability_and_complete_writer_body_are_required():
    record, turn = owner()
    changed = {**writer_reference(record), "draft_markdown": "Saved text substituted"}
    with pytest.raises(ValueError, match="included context record"):
        validate_writer_reference(changed, record, turn)
    turn.graph_context_execution.policy.working_draft_snapshot_sha256 = "d" * 64
    with pytest.raises(ValueError, match="frozen context capability"):
        validate_record(record, turn)


def test_newer_work_is_an_independent_snapshot_without_mutating_previous_record():
    first, turn = owner()
    second = snapshot("A newer unsaved paragraph")
    assert second.snapshot_sha256 != first.snapshot.snapshot_sha256
    assert first.snapshot.draft_markdown == "Unsaved orchid keepers 🌸"
    with pytest.raises(ValidationError):
        first.snapshot.draft_markdown = second.draft_markdown
    validate_record(first, turn)


@pytest.mark.parametrize("field,value", [("registry_revision", True), ("draft_generation", False),
    ("registry_revision", 0), ("draft_generation", -1), ("editor_sha256", "bad")])
def test_malformed_capture_identity_is_rejected(field, value):
    with pytest.raises(ValidationError):
        BuildDraftSnapshotV1.model_validate({**snapshot().model_dump(), field: value})
