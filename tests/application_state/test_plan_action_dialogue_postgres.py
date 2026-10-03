from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import (
    PlanActionBasis,
    PlanActionReservation,
)


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
) -> PlanActionReservation:
    return PlanActionReservation(
        idempotency_key=key or uuid4(),
        request_fingerprint=fingerprint,
        action_type="revise" if target_kind == "replace_selection" else "compose",
        basis=basis or _basis(),
        draft_matches_basis=False,
        draft_sha256="c" * 64,
        target_kind=target_kind,
        selected_text_sha256="d" * 64 if target_kind == "replace_selection" else None,
        instruction=instruction,
    )


def _expire(dsn: str, action_id: UUID) -> None:
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE plan_action.action SET lease_expires_at = clock_timestamp() - interval '1 second' WHERE action_id = %s",
            (action_id,),
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

    done = service.finish(
        action_id=reserved.action_id,
        token=reserved.dispatch_token,
        fence=reserved.fence,
        status="completed",
        summary="A warning appears at dusk.",
    )
    assert done.status == "completed"
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


@pytest.mark.parametrize("terminal_status", ["completed", "failed"])
def test_expired_terminal_write_becomes_indeterminate_without_summary(
    application_state_dsn: str, terminal_status: str
) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created and reserved.dispatch_token is not None
    _expire(application_state_dsn, reserved.action_id)

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
    assert "STALE-SUMMARY-SENTINEL" not in str(service.list_status(request.basis).model_dump())
    assert service.completed_context(request.basis) == []


def test_concurrent_expiry_reconciliation_advances_fence_once(application_state_dsn: str) -> None:
    service = PlanActionDialogueService()
    request = _reservation()
    reserved, created = service.reserve(request)
    assert created
    _expire(application_state_dsn, reserved.action_id)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _index: service.get_by_key(request.idempotency_key), range(8)))
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
