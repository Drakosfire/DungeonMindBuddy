from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import psycopg
import pytest
from alembic import command

from application_state.errors import ApplicationStateConflictError
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import (
    PlanActionBasis,
    PlanActionPlayableTargetReceipt,
    PlanActionReservation,
)
from application_state.cli import _current_and_head, alembic_config


def _basis(revision: int = 4, digest: str = "a" * 64) -> PlanActionBasis:
    return PlanActionBasis(
        world_id="world-plan-actions",
        document_id="plan-document-1",
        object_revision=revision,
        work_revision_id=UUID("00000000-0000-4000-8000-000000000401"),
        revision_n=9,
        content_sha256=digest,
    )


def _reservation(
    *,
    key: UUID | None = None,
    basis: PlanActionBasis | None = None,
    instruction: str = "Add a quiet warning.",
    target_kind: str = "replace_selection",
    fingerprint: str = "b" * 64,
    playable_target_receipt: PlanActionPlayableTargetReceipt | None = None,
) -> PlanActionReservation:
    return PlanActionReservation(
        idempotency_key=key or uuid4(),
        request_fingerprint=fingerprint,
        action_type="compose" if target_kind == "insert_at_caret" else "revise",
        basis=basis or _basis(),
        draft_matches_basis=False,
        draft_sha256="c" * 64,
        target_kind=target_kind,
        selected_text_sha256="d" * 64 if target_kind == "replace_selection" else None,
        playable_target_receipt=playable_target_receipt,
        instruction=instruction,
    )


def _expire(dsn: str, action_id: UUID, *, stale_updated_at: bool = False) -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            UPDATE plan_action.action
            SET lease_expires_at = clock_timestamp() - interval '1 second',
                updated_at = CASE WHEN %s
                    THEN clock_timestamp() - interval '1 hour' ELSE updated_at END
            WHERE action_id = %s
            """,
            (stale_updated_at, action_id),
        )


def test_reservation_idempotency_live_pending_and_privacy(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    first, created = service.reserve(request)
    assert created is True
    assert first.status == "pending"
    assert first.dispatch_token is not None
    assert first.fence == 1
    assert 119 <= (first.lease_expires_at - first.accepted_at).total_seconds() <= 121

    duplicate, created_again = service.reserve(request)
    assert created_again is False
    assert duplicate.action_id == first.action_id
    assert duplicate.status == "pending"
    assert duplicate.fence == first.fence

    with pytest.raises(ApplicationStateConflictError, match="different request"):
        service.reserve(request.model_copy(update={"request_fingerprint": "e" * 64}))

    projection = service.list_status(request.basis)
    assert len(projection.actions) == 1
    item = projection.actions[0]
    assert item.status == "pending"
    assert item.assistant_summary is None
    serialized = item.model_dump_json()
    assert "draft_sha256" not in serialized
    assert "selected_text_sha256" not in serialized
    assert "replacement_markdown" not in serialized
    assert "provider" not in serialized
    assert "Add a quiet warning." in serialized


@pytest.mark.parametrize(
    ("marker_grammar_version", "body_scope"),
    [("v1", "heading_body"), ("v2", "option_item_content")],
)
def test_playable_target_receipt_survives_reservation_and_projection(
    application_state_dsn: str,
    marker_grammar_version: str,
    body_scope: str,
) -> None:
    service = PlanActionDialogueService()
    receipt = PlanActionPlayableTargetReceipt(
        schema_version="dmb_plan_playable_target_receipt_v1",
        kind="option",
        id="option:go",
        marker_grammar_version=marker_grammar_version,
        body_scope=body_scope,
        range_semantics_version="plan-playable-ranges-v1",
        body_serialization_version="plan-playable-body-markdown-v1",
        target_body_sha256="e" * 64,
    )
    request = _reservation(target_kind="replace_playable_body", playable_target_receipt=receipt)
    action, created = service.reserve(request)
    assert created is True
    assert action.selected_text_sha256 is None
    assert action.playable_target_receipt == receipt

    loaded = PlanActionDialogueService().get_by_key(request.basis.world_id, request.idempotency_key)
    assert loaded is not None
    assert loaded.playable_target_receipt == receipt
    assert loaded.request_fingerprint == request.request_fingerprint
    assert loaded.basis == request.basis
    assert loaded.draft_sha256 == request.draft_sha256
    projection = service.list_status(request.basis)
    assert projection.actions[0].playable_target_receipt == receipt

    different_target = receipt.model_copy(update={"id": "option:wait"})
    with pytest.raises(ApplicationStateConflictError, match="different request"):
        service.reserve(request.model_copy(update={"playable_target_receipt": different_target}))


def _playable_target_receipt_payload(kind: str, grammar: str, scope: str) -> dict[str, str]:
    return {
        "schema_version": "dmb_plan_playable_target_receipt_v1",
        "kind": kind,
        "id": f"{kind}:fixture",
        "marker_grammar_version": grammar,
        "body_scope": scope,
        "range_semantics_version": "plan-playable-ranges-v1",
        "body_serialization_version": "plan-playable-body-markdown-v1",
        "target_body_sha256": "e" * 64,
    }


def test_database_accepts_each_supported_playable_target_receipt_scope(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    receipt = PlanActionPlayableTargetReceipt(
        schema_version="dmb_plan_playable_target_receipt_v1",
        kind="option",
        id="option:go",
        marker_grammar_version="v2",
        body_scope="option_item_content",
        range_semantics_version="plan-playable-ranges-v1",
        body_serialization_version="plan-playable-body-markdown-v1",
        target_body_sha256="e" * 64,
    )
    request = _reservation(target_kind="replace_playable_body", playable_target_receipt=receipt)
    action, created = service.reserve(request)
    assert created
    valid_combinations = [
        ("scene", "v1", "heading_body"),
        ("beat", "v1", "heading_body"),
        ("choice", "v1", "heading_body"),
        ("option", "v1", "heading_body"),
        ("scene", "v2", "heading_body"),
        ("beat", "v2", "beat_direct_body"),
        ("choice", "v2", "heading_body"),
        ("option", "v2", "option_item_content"),
    ]
    with psycopg.connect(application_state_dsn) as conn:
        for kind, grammar, scope in valid_combinations:
            payload = _playable_target_receipt_payload(kind, grammar, scope)
            conn.execute(
                "UPDATE plan_action.action SET playable_target_receipt = %s::jsonb WHERE action_id = %s",
                (json.dumps(payload), action.action_id),
            )


def test_database_rejects_malformed_playable_target_receipt(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    receipt = PlanActionPlayableTargetReceipt(
        schema_version="dmb_plan_playable_target_receipt_v1",
        kind="option",
        id="option:go",
        marker_grammar_version="v2",
        body_scope="option_item_content",
        range_semantics_version="plan-playable-ranges-v1",
        body_serialization_version="plan-playable-body-markdown-v1",
        target_body_sha256="e" * 64,
    )
    request = _reservation(target_kind="replace_playable_body", playable_target_receipt=receipt)
    action, created = service.reserve(request)
    assert created
    valid = receipt.model_dump(mode="json")
    invalid_payloads: list[object] = [None]
    for key in valid:
        invalid_payloads.extend([
            {**valid, key: None},
            {**valid, key: 7},
        ])
    invalid_payloads.extend([
        {**valid, "unexpected": "extra"},
        {key: value for key, value in valid.items() if key != "id"},
        {**valid, "body_scope": "heading_body"},
        {**valid, "target_body_sha256": "not-a-digest"},
    ])
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        for malformed in invalid_payloads:
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(
                    "UPDATE plan_action.action SET playable_target_receipt = %s::jsonb WHERE action_id = %s",
                    (json.dumps(malformed), action.action_id),
                )


def test_0015_upgrade_preserves_populated_0014_legacy_action_history(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation(key=uuid4(), target_kind="replace_selection")
    action, created = service.reserve(request)
    assert created and action.dispatch_token is not None
    completed = service.finish(
        action_id=action.action_id,
        token=action.dispatch_token,
        fence=action.fence,
        status="completed",
        summary="Legacy summary survives the additive migration.",
    )
    assert completed.status == "completed"

    command.downgrade(alembic_config(), "20261003_0014")
    with psycopg.connect(application_state_dsn) as conn:
        legacy_row = conn.execute(
            "SELECT action_id, target_kind, selected_text_sha256, instruction, assistant_summary "
            "FROM plan_action.action WHERE idempotency_key = %s",
            (request.idempotency_key,),
        ).fetchone()
    assert legacy_row == (
        action.action_id,
        "replace_selection",
        request.selected_text_sha256,
        request.instruction,
        "Legacy summary survives the additive migration.",
    )

    command.upgrade(alembic_config(), "head")
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20261004_0015"
    loaded = PlanActionDialogueService().get_by_key(request.basis.world_id, request.idempotency_key)
    assert loaded is not None
    assert loaded.action_id == action.action_id
    assert loaded.status == "completed"
    assert loaded.instruction == request.instruction
    assert loaded.assistant_summary == "Legacy summary survives the additive migration."
    assert loaded.selected_text_sha256 == request.selected_text_sha256
    assert loaded.playable_target_receipt is None
    projection = PlanActionDialogueService().list_status(request.basis)
    assert any(item.action_id == action.action_id and item.playable_target_receipt is None for item in projection.actions)


def test_concurrent_same_key_reservations_have_one_dispatch_owner(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _index: service.reserve(request), range(8)))

    records = [record for record, _created in results]
    assert sum(created for _record, created in results) == 1
    assert len({record.action_id for record in records}) == 1
    assert len({record.dispatch_token for record in records}) == 1
    assert {record.status for record in records} == {"pending"}


def test_terminal_compare_and_set_wins_once_before_expiry(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created and reserved.dispatch_token is not None

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET updated_at = clock_timestamp() - interval '1 hour' WHERE action_id = %s",
            (reserved.action_id,),
        )
        stale_updated_at, transition_start = conn.execute(
            "SELECT updated_at, clock_timestamp() FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()

    done = service.finish(
        action_id=reserved.action_id,
        token=reserved.dispatch_token,
        fence=reserved.fence,
        status="completed",
        summary="A warning appears at dusk.",
    )
    with psycopg.connect(application_state_dsn) as conn:
        completed_at, updated_at, transition_end = conn.execute(
            "SELECT completed_at, updated_at, clock_timestamp() FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()
    assert done.status == "completed"
    assert done.completed_at is not None
    assert completed_at is not None
    assert stale_updated_at < transition_start <= updated_at <= transition_end
    again = service.finish(
        action_id=reserved.action_id,
        token=reserved.dispatch_token,
        fence=reserved.fence,
        status="failed",
        failure_code="late_failure",
    )
    assert again.status == "completed"
    assert again.assistant_summary == "A warning appears at dusk."
    context = service.completed_context(request.basis)
    assert len(context) == 1
    assert context[0].instruction == request.instruction
    assert context[0].assistant_summary == "A warning appears at dusk."


def test_failed_terminal_write_keeps_completed_at_null_and_updates_timestamp(
    application_state_dsn: str,
) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created and reserved.dispatch_token is not None

    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET updated_at = clock_timestamp() - interval '1 hour' WHERE action_id = %s",
            (reserved.action_id,),
        )
        stale_updated_at, transition_start = conn.execute(
            "SELECT updated_at, clock_timestamp() FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()

    failed = service.finish(
        action_id=reserved.action_id,
        token=reserved.dispatch_token,
        fence=reserved.fence,
        status="failed",
        failure_code="provider_failed",
    )
    with psycopg.connect(application_state_dsn) as conn:
        completed_at, updated_at, transition_end = conn.execute(
            "SELECT completed_at, updated_at, clock_timestamp() FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()

    assert failed.status == "failed"
    assert failed.completed_at is None
    assert completed_at is None
    assert stale_updated_at < transition_start <= updated_at <= transition_end


@pytest.mark.parametrize("terminal_status", ["completed", "failed"])
def test_expired_terminal_write_becomes_indeterminate_without_summary(
    application_state_dsn: str, terminal_status: str
) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created and reserved.dispatch_token is not None
    _expire(application_state_dsn, reserved.action_id, stale_updated_at=True)
    with psycopg.connect(application_state_dsn) as conn:
        stale_updated_at = conn.execute(
            "SELECT updated_at FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()[0]

    stale = service.finish(
        action_id=reserved.action_id,
        token=reserved.dispatch_token,
        fence=reserved.fence,
        status=terminal_status,
        summary="STALE-SUMMARY-SENTINEL" if terminal_status == "completed" else None,
        failure_code="provider_failed" if terminal_status == "failed" else None,
    )
    assert stale.status == "indeterminate"
    assert stale.fence == reserved.fence + 1
    assert stale.assistant_summary is None
    assert stale.completed_at is None
    with psycopg.connect(application_state_dsn) as conn:
        completed_at, updated_at = conn.execute(
            "SELECT completed_at, updated_at FROM plan_action.action WHERE action_id = %s",
            (reserved.action_id,),
        ).fetchone()
    assert completed_at is None
    assert updated_at > stale_updated_at
    assert "STALE-SUMMARY-SENTINEL" not in str(service.list_status(request.basis).model_dump())
    assert service.completed_context(request.basis) == []


def test_concurrent_expiry_reconciliation_advances_fence_once(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created
    _expire(application_state_dsn, reserved.action_id)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _index: service.get_by_key(
                    request.basis.world_id, request.idempotency_key
                ),
                range(8),
            )
        )
    assert all(result is not None for result in results)
    assert {result.status for result in results if result is not None} == {"indeterminate"}
    assert {result.fence for result in results if result is not None} == {reserved.fence + 1}
    assert all(result.dispatch_token is None for result in results if result is not None)


def test_completed_context_filters_exact_basis_before_six_pair_limit(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    basis = _basis()
    completed = []
    for index in range(8):
        reservation = _reservation(
            basis=basis,
            instruction=f"Completed instruction {index}",
            fingerprint=f"{index + 1:064x}",
        )
        row, created = service.reserve(reservation)
        assert created and row.dispatch_token is not None
        result = service.finish(
            action_id=row.action_id,
            token=row.dispatch_token,
            fence=row.fence,
            status="completed",
            summary=f"Completed summary {index}",
        )
        assert result.status == "completed"
        completed.append(result)

    for index in range(6):
        reservation = _reservation(
            basis=basis,
            instruction=f"Unfinished instruction {index}",
            fingerprint=f"{index + 101:064x}",
        )
        row, created = service.reserve(reservation)
        assert created
        _expire(application_state_dsn, row.action_id)

    # A newer document revision is isolated even when the Plan and World match.
    foreign_basis = basis.model_copy(update={"object_revision": basis.object_revision + 1})
    assert service.completed_context(foreign_basis) == []
    current_context = service.completed_context(basis)
    assert len(current_context) == 6
    assert [item.instruction for item in current_context] == [
        f"Completed instruction {index}" for index in range(2, 8)
    ]
    status = service.list_status(basis)
    assert len(status.actions) == 14
    assert sum(item.status == "indeterminate" for item in status.actions) == 6
    assert sum(item.status == "completed" for item in status.actions) == 8
