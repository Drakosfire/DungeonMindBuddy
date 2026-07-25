"""SBW07a Server-transcript provenance proofs.

These tests assert facts recorded from DungeonMindServer's TestClient
(``scripts/capture_sbw07a_server_create_transcripts.py``), citing the Server
commit and server-owned route tests in MANIFEST.json. They do not invent
idempotency or terminality by unconditional Buddy mocks.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    CreateStatblockResponseEnvelopeV1,
    locator_from_create_response,
    locator_from_exact_revision,
    same_mechanics_locator,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ErrorEnvelopeV1,
    ExactRevisionResourceV1,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "statblocks" / "v1"
TRANSCRIPT_DIR = FIXTURE_DIR / "server_transcripts"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _transcript(name: str) -> dict:
    return json.loads((TRANSCRIPT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_manifest_cites_server_commit_and_owned_tests() -> None:
    manifest = json.loads((TRANSCRIPT_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "sbw07a_server_create_transcript_manifest_v1"
    server = manifest["dungeonmind_server"]
    assert isinstance(server["commit"], str) and len(server["commit"]) == 40
    assert server["subject"]
    owned = manifest["server_owned_tests"]
    assert owned
    names = set(owned[0]["names"])
    assert "test_create_append_and_exact_replay" in names
    assert "test_write_idempotency_parent_stale_and_exact_locator_errors" in names
    assert "test_persistence_validation_failure_returns_receipt" in names
    assert "test_open_provenance_field_rejected_and_actor_is_not_created_by" in names
    for key in (
        "create_success",
        "same_key_same_body_replay",
        "same_key_changed_body_conflict",
        "create_to_exact_read",
        "persistence_validation_failed",
        "request_validation_failed",
    ):
        assert key in manifest["transcripts"]
        assert (TRANSCRIPT_DIR / f"{key}.json").is_file()


def test_server_transcript_replay_preserves_logical_identity() -> None:
    transcript = _transcript("same_key_same_body_replay")
    first = CreateStatblockResponseEnvelopeV1.model_validate(
        transcript["first_response"]["json"]
    )
    second = CreateStatblockResponseEnvelopeV1.model_validate(
        transcript["second_response"]["json"]
    )
    left = locator_from_create_response(first)
    right = locator_from_create_response(second)
    assert same_mechanics_locator(left, right)
    assert transcript["request"]["json"]["idempotency_key"]
    assert transcript["first_response"]["status"] == 200
    assert transcript["second_response"]["status"] == 200


def test_server_transcript_changed_body_is_idempotency_conflict() -> None:
    transcript = _transcript("same_key_changed_body_conflict")
    original = transcript["original_request"]["json"]
    changed = transcript["changed_request"]["json"]
    assert original["idempotency_key"] == changed["idempotency_key"]
    assert original != changed
    conflict = ErrorEnvelopeV1.model_validate(transcript["conflict_response"]["json"])
    assert transcript["conflict_response"]["status"] == 409
    assert conflict.error.code == "idempotency_conflict"
    # Original create remains a successful Server commitment in the transcript.
    CreateStatblockResponseEnvelopeV1.model_validate(
        transcript["original_response"]["json"]
    )


def test_server_transcript_create_to_exact_read_identity() -> None:
    transcript = _transcript("create_to_exact_read")
    created = CreateStatblockResponseEnvelopeV1.model_validate(
        transcript["create_response"]["json"]
    )
    create_locator = locator_from_create_response(created)
    read = ExactRevisionResourceV1.model_validate(
        transcript["exact_read_response"]["json"]
    )
    read_locator = locator_from_exact_revision(read)
    assert same_mechanics_locator(create_locator, read_locator)
    path = transcript["exact_read_request"]["path"]
    assert path.endswith(
        f"/statblocks/{create_locator.statblock_id}/revisions/{create_locator.revision_id}"
    )
    assert "latest" not in path


def test_server_transcript_persistence_validation_proves_non_begin() -> None:
    transcript = _transcript("persistence_validation_failed")
    assert transcript["response"]["status"] == 422
    envelope = ErrorEnvelopeV1.model_validate(transcript["response"]["json"])
    assert envelope.error.code == "validation_failed"
    assert envelope.error.details is not None
    assert envelope.error.details["is_persistence_ready"] is False
    leaf = ErrorEnvelopeV1.model_validate(_load("create-persistence-validation-failed.json"))
    assert leaf.error.details is not None
    assert leaf.error.details["is_persistence_ready"] is False


def test_server_transcript_invalid_request_is_pre_handler() -> None:
    transcript = _transcript("request_validation_failed")
    assert transcript["response"]["status"] == 422
    envelope = ErrorEnvelopeV1.model_validate(transcript["response"]["json"])
    assert envelope.error.code == "invalid_request"
    assert "provenance" in transcript["request"]["json"]
