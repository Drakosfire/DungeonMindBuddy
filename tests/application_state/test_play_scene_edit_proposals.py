from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation.types import PlayRunTurnContextReceiptV2
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play_scene_edit.service import PlaySceneEditProposalService
from application_state.play_scene_edit.types import SceneEditProposalRecord, canonical_json_bytes


WORLD = "scene-edit-storage-test"
RUN_ID = uuid4()
EDITION_ID = uuid4()
ARTIFACT_ID = uuid4()
WORK_REVISION_ID = uuid4()
ORIGIN_SHA = "a" * 64
EDITION_SHA = "b" * 64


def _receipt(*, world_id: str = WORLD, run_id=RUN_ID) -> PlayRunTurnContextReceiptV2:
    return PlayRunTurnContextReceiptV2(
        schema="dmb_play_run_turn_context_receipt_v2", world_id=world_id,
        run_id=str(run_id), run_revision=2, runbook_object_id=str(ARTIFACT_ID),
        runbook_object_revision=3, runbook_work_revision_id=WORK_REVISION_ID,
        runbook_revision_n=1, runbook_content_sha256="a" * 64,
        beat_id="beat:arrival", scene_id="scene:arrival", marker_grammar_version="v2",
        edition_revision=1, edition_revision_id=EDITION_ID, content_sha256=EDITION_SHA,
        scene_note="Saved note", scene_note_sha256=hashlib.sha256(b"Saved note").hexdigest(),
    )


def _request(receipt=None):
    receipt = receipt or _receipt()
    return {
        "schema_version": "dmb_play_scene_edit_request_v1",
        "run_revision": receipt.run_revision,
        "content_basis": {
            "edition_revision": receipt.edition_revision,
            "edition_revision_id": str(receipt.edition_revision_id),
            "content_sha256": receipt.content_sha256,
        },
        "scene_id": receipt.scene_id,
        "instruction": "Make the doorway feel older.",
    }


def _result(candidate: str = "The old doorway waits."):
    return {
        "schema_version": "dmb_play_scene_edit_result_v1",
        "before_markdown": "The doorway waits.",
        "replacement_markdown": candidate,
        "candidate_markdown": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "summary": "A more weathered doorway.", "assumptions": [],
        "model": "test-model", "model_observed": True,
        "model_latency_ms": 10, "wall_latency_ms": 12,
    }


def test_typed_record_binds_request_receipt_and_fingerprint():
    receipt = _receipt()
    request = _request(receipt)
    digest = hashlib.sha256(canonical_json_bytes({
        "request": request, "context_receipt": receipt.model_dump(mode="json", by_alias=True),
    })).hexdigest()
    record = SceneEditProposalRecord(
        world_id=WORLD, run_id=RUN_ID, proposal_id=uuid4(), request_sha256=digest,
        request=request, context_receipt=receipt, status="pending",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    assert record.status == "pending"
    with pytest.raises(ValueError, match="fingerprint"):
        SceneEditProposalRecord.model_validate(record.model_dump(mode="json", by_alias=True) | {"request_sha256": "0" * 64})
    with pytest.raises(ValueError, match="content basis"):
        SceneEditProposalRecord.model_validate(record.model_dump(mode="json", by_alias=True) | {
            "request": request | {"content_basis": request["content_basis"] | {"content_sha256": "c" * 64}},
        })


def test_result_offsets_remain_in_original_coordinates_after_shrinking_replacement():
    from application_state.play_scene_edit.types import validate_result

    candidate = _result(candidate="short")
    replacement = "\nshort\n\n"
    candidate_markdown = "prefix\n" + replacement + "tail"
    candidate.update({
        "candidate_markdown": candidate_markdown,
        "candidate_sha256": hashlib.sha256(candidate_markdown.encode()).hexdigest(),
        "before_markdown": "a much longer original scene body",
        "replacement_markdown": replacement,
        "body_start_utf8": len("prefix\n".encode()),
        "body_end_utf8": len("prefix\na much longer original scene body".encode()),
    })
    validate_result(candidate)


def _insert_run(dsn):
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO play.run(run_id,campaign_id,playable_work_object_id,playable_revision_n,playable_work_revision_id,playable_content_sha256,run_revision,progress,created_at,updated_at,world_id) VALUES(%s,NULL,%s,1,%s,%s,2,'{}'::jsonb,now(),now(),%s)",
            (RUN_ID, ARTIFACT_ID, WORK_REVISION_ID, ORIGIN_SHA, WORLD),
        )
        conn.execute(
            "INSERT INTO play.run_edition(run_id,world_id,origin_artifact_id,origin_revision_n,origin_work_revision_id,origin_content_sha256,grammar_version,structure_sha256,head_revision,created_at) VALUES(%s,%s,%s,1,%s,%s,2,%s,1,now())",
            (RUN_ID, WORLD, ARTIFACT_ID, WORK_REVISION_ID, ORIGIN_SHA, "d" * 64),
        )
        conn.execute(
            "INSERT INTO play.run_edition_revision(run_id,revision_n,revision_id,previous_revision,markdown,content_sha256,committed_at,command_id,request_sha256,expected_revision,expected_sha256,observed_run_revision,expected_run_revision) VALUES(%s,1,%s,NULL,%s,%s,now(),%s,%s,0,%s,2,NULL)",
            (RUN_ID, EDITION_ID, "The current edition.", EDITION_SHA, uuid4(), "e" * 64, ORIGIN_SHA),
        )


def _advance_edition(dsn):
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "INSERT INTO play.run_edition_revision(run_id,revision_n,revision_id,previous_revision,markdown,content_sha256,committed_at,command_id,request_sha256,expected_revision,expected_sha256,observed_run_revision,expected_run_revision) VALUES(%s,2,%s,1,%s,%s,now(),%s,%s,1,%s,2,NULL)",
            (RUN_ID, uuid4(), "A newer edition.", "c" * 64, uuid4(), "f" * 64, EDITION_SHA),
        )
        conn.execute("UPDATE play.run_edition SET head_revision=2 WHERE run_id=%s", (RUN_ID,))


def test_reserve_replay_finish_terminal_immutability_and_scopes(application_state_dsn):
    _insert_run(application_state_dsn)
    service = PlaySceneEditProposalService()
    proposal_id = uuid4()
    receipt = _receipt()
    request = _request(receipt)
    record, created = service.reserve(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                                      request=request, context_receipt=receipt)
    assert created and record.status == "pending"
    replay, created = service.reserve(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                                      request=request, context_receipt=receipt)
    assert not created and replay.request_sha256 == record.request_sha256
    assert service.list_records(world_id=WORLD, run_id=RUN_ID) == [record]
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="reservation is immutable"):
            conn.execute("UPDATE play.scene_edit_proposal SET request_sha256=%s WHERE world_id=%s AND run_id=%s AND proposal_id=%s", ("f" * 64, WORLD, RUN_ID, proposal_id))
    assert service.get(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id).status == "pending"
    with pytest.raises(ApplicationStateConflictError, match="different frozen request"):
        service.reserve(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                        request=request | {"instruction": "Different intent."}, context_receipt=receipt)
    result = _result()
    ready = service.finish(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                           result=result, failure_code=None)
    assert ready.status == "ready" and service.get(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id) == ready
    assert service.finish(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                          result=result, failure_code=None) == ready
    with pytest.raises(ApplicationStateConflictError, match="already terminal"):
        service.finish(world_id=WORLD, run_id=RUN_ID, proposal_id=proposal_id,
                       result=None, failure_code="generation_failed")
    with pytest.raises(ApplicationStateNotFoundError):
        service.get(world_id="other-world", run_id=RUN_ID, proposal_id=proposal_id)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="terminal.*immutable"):
            conn.execute("UPDATE play.scene_edit_proposal SET failure_code='rewritten' WHERE world_id=%s AND run_id=%s AND proposal_id=%s", (WORLD, RUN_ID, proposal_id))
    failed_id = uuid4()
    service.reserve(world_id=WORLD, run_id=RUN_ID, proposal_id=failed_id,
                    request=request, context_receipt=receipt)
    failed = service.finish(world_id=WORLD, run_id=RUN_ID, proposal_id=failed_id,
                             result=None, failure_code="generation_failed")
    assert failed.status == "failed" and failed.result is None
    assert service.finish(world_id=WORLD, run_id=RUN_ID, proposal_id=failed_id,
                          result=None, failure_code="generation_failed") == failed


def test_reservation_checks_world_run_receipt_and_bounds_result(application_state_dsn):
    _insert_run(application_state_dsn)
    service = PlaySceneEditProposalService()
    receipt = _receipt()
    with pytest.raises(ApplicationStateValidationError, match="World/Run"):
        service.reserve(world_id="other-world", run_id=RUN_ID, proposal_id=uuid4(), request=_request(receipt), context_receipt=receipt)
    with pytest.raises(ValueError, match="candidate_sha256"):
        from application_state.play_scene_edit.types import validate_result
        validate_result(_result() | {"candidate_sha256": "0" * 64})
    unknown_run = uuid4()
    unknown_receipt = _receipt(run_id=unknown_run)
    with pytest.raises(ApplicationStateNotFoundError, match="Play Run"):
        service.reserve(world_id=WORLD, run_id=unknown_run, proposal_id=uuid4(), request=_request(unknown_receipt), context_receipt=unknown_receipt)
    with pytest.raises(ApplicationStateValidationError, match="revision"):
        bad = _request(receipt) | {"run_revision": 3}
        service.reserve(world_id=WORLD, run_id=RUN_ID, proposal_id=uuid4(), request=bad, context_receipt=receipt)


def test_reservation_rejects_edition_advanced_after_context_snapshot(application_state_dsn):
    _insert_run(application_state_dsn)
    receipt = _receipt()
    request = _request(receipt)
    _advance_edition(application_state_dsn)
    with pytest.raises(ApplicationStateConflictError, match="saved Play edition changed"):
        PlaySceneEditProposalService().reserve(
            world_id=WORLD, run_id=RUN_ID, proposal_id=uuid4(),
            request=request, context_receipt=receipt,
        )
