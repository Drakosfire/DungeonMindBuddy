"""Retry ownership, atomic acceptance and immutable lineage at real PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from uuid import uuid4
import psycopg
import pytest
from application_state.agent_conversation import (
    AgentConversationService,
    retry,
    library,
)
from application_state.agent_conversation.types import (
    RetryTurnReference,
    submitted_turn_intent_fingerprint_v2,
)
from application_state.errors import (
    ApplicationStateConflictError,
)
from tests.test_build_turn_retry import failed_case as _failed_case


@pytest.fixture
def failed_case(tmp_path, monkeypatch, application_state_dsn):
    return _failed_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def with_intent(submission, intent, *, capability=None, user_text=None):
    from application_state.agent_conversation.native_execution import (
        SurfaceNativeExecutionV1,
    )
    from application_state.agent_conversation.types import canonical_sha256

    previous_execution = submission.graph_context_execution
    action = previous_execution.policy.action
    capability = capability or action.write_capability
    action = action.model_copy(
        update={"intent": intent, "write_capability": capability}
    )
    policy = previous_execution.policy.model_copy(update={"action": action})
    wire = {
        "schema": previous_execution.schema_,
        "context_receipt_sha256": submission.graph_context_receipt.context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True),
    }
    execution = SurfaceNativeExecutionV1.model_validate_json(
        json.dumps(
            {**wire, "execution_policy_sha256": canonical_sha256(wire), "events": []}
        )
    )
    return submission.model_copy(
        update={
            "submitted_intent_v2": intent,
            "graph_context_execution": execution,
            "user_text": submission.user_text if user_text is None else user_text,
        }
    )


def successor(parent, submission):
    service = AgentConversationService()
    from application_state.agent_conversation.types import canonical_sha256

    capability = (
        submission.graph_context_execution.policy.action.write_capability.model_copy(
            update={"idempotency_key": uuid4()}
        )
    )
    intent = submission.submitted_intent_v2.model_copy(
        update={
            "retry_of": RetryTurnReference(
                turn_id=parent.turn_id, revision=parent.revision
            ),
            "build_write_capability_sha256": canonical_sha256(
                capability.model_dump(mode="json")
            ),
        }
    )
    candidate = with_intent(submission, intent, capability=capability).model_copy(
        update={
            "idempotency_key": uuid4(),
            "expected_conversation_revision": service.get_conversation(
                parent.world_id, parent.conversation_id
            ).revision,
        }
    )
    assert candidate.submitted_intent_v1 is None
    assert (
        candidate.submitted_intent_v2
        == candidate.graph_context_execution.policy.action.intent
    )
    assert candidate.submitted_intent_v2.world_id == candidate.world_id
    assert candidate.submitted_intent_v2.message == candidate.user_text
    assert not candidate.graph_context_execution.events
    assert (
        candidate.submitted_intent_v2.surface_instance_id
        == candidate.provenance.surface_instance_id
    )
    return candidate


def test_concurrent_successors_have_one_winner_and_edge_is_immutable(
    failed_case, application_state_dsn
):
    *_, parent, submission, _harness, _writer = failed_case
    one = successor(parent, submission)
    two = one.model_copy(update={"idempotency_key": uuid4()})
    start = Barrier(2)

    def accept(value):
        start.wait(timeout=5)
        try:
            return AgentConversationService().accept_turn(value)
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, [one, two]))
    winners = [r for r in results if r]
    assert len(winners) == 1
    winner = winners[0]
    receipt = one if results[0] else two
    assert AgentConversationService().accept_turn(receipt) == winner
    changed = with_intent(
        receipt,
        receipt.submitted_intent_v2.model_copy(
            update={
                "retry_of": RetryTurnReference(
                    turn_id=uuid4(), revision=parent.revision
                )
            }
        ),
    )
    with pytest.raises(ApplicationStateConflictError):
        AgentConversationService().accept_turn(changed)
    with psycopg.connect(application_state_dsn) as conn:
        edge = conn.execute("SELECT root_id,ordinal FROM agent.turn_retry").fetchall()
        assert edge == [(parent.turn_id, 1)]
        for sql in (
            "UPDATE agent.turn_retry SET ordinal=2",
            "DELETE FROM agent.turn_retry",
        ):
            with pytest.raises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute(sql)


def test_chain_root_pagination_and_read_only_history(
    failed_case, application_state_dsn
):
    *_, parent, submission, _harness, _writer = failed_case
    service = AgentConversationService()
    child = service.accept_turn(successor(parent, submission))
    # This physical successor has not authorized a provider; a known terminal failure is safe.
    from application_state.agent_conversation.types import TurnFailure

    running = service.begin_turn(
        parent.world_id,
        parent.conversation_id,
        child.turn_id,
        expected_revision=child.revision,
    )
    child = service.fail_turn(
        TurnFailure(
            world_id=parent.world_id,
            conversation_id=parent.conversation_id,
            turn_id=child.turn_id,
            expected_revision=running.revision,
            failure_code="synthetic_before_dispatch",
        ),
        interrupted=True,
    )
    grand = service.accept_turn(successor(child, submission))
    with pytest.raises(ApplicationStateConflictError, match="successor"):
        service.claim_turn(
            parent.world_id,
            parent.conversation_id,
            child.turn_id,
            expected_revision=child.revision,
        )
    context = retry.read_context(
        parent.world_id, parent.conversation_id, [grand.turn_id]
    )["turns"][0]["context"]
    assert context["root_id"] == str(parent.turn_id) and context["ordinal"] == 2
    page = library.read_retry_attempts(
        parent.world_id, parent.conversation_id, grand.turn_id, limit=1
    )
    assert (
        len(page["turns"]) == 1
        and page["turns"][0]["turn_id"] == str(child.turn_id)
        and page["next_before_sequence"] == child.sequence
    )
    older = library.read_retry_attempts(
        parent.world_id,
        parent.conversation_id,
        grand.turn_id,
        limit=1,
        before_sequence=page["next_before_sequence"],
    )
    assert (
        older["turns"][0]["turn_id"] == str(parent.turn_id)
        and older["next_before_sequence"] is None
    )
    snapshot = service.list_turns(parent.world_id, parent.conversation_id)
    assert not library.read_turns(parent.world_id, parent.conversation_id)["turns"][0][
        "retry_context"
    ]["eligible"]
    assert service.list_turns(parent.world_id, parent.conversation_id) == snapshot


@pytest.mark.parametrize(
    "change", ["revision", "message", "page", "foreign", "unknown"]
)
def test_bad_parent_is_rejected_before_acceptance(
    failed_case, application_state_dsn, change
):
    *_, parent, submission, _harness, _writer = failed_case
    value = successor(parent, submission)
    if change == "revision":
        value = with_intent(
            value,
            value.submitted_intent_v2.model_copy(
                update={
                    "retry_of": RetryTurnReference(
                        turn_id=parent.turn_id, revision=parent.revision + 1
                    )
                }
            ),
        )
    elif change == "foreign":
        value = with_intent(
            value,
            value.submitted_intent_v2.model_copy(
                update={
                    "retry_of": RetryTurnReference(
                        turn_id=uuid4(), revision=parent.revision
                    )
                }
            ),
        )
    elif change == "message":
        value = with_intent(
            value,
            value.submitted_intent_v2.model_copy(
                update={"message": "Different question"}
            ),
            user_text="Different question",
        )
    elif change == "page":
        # Build a self-consistent other-page admission so rejection occurs at
        # the retry parent boundary rather than at native receipt validation.
        from application_state.agent_conversation.native_context import (
            SurfaceNativeContextReceiptV1,
        )
        from application_state.agent_conversation.types import canonical_sha256

        foreign = "foreign-page"
        provenance = value.provenance.model_copy(
            update={
                "primary_work": value.provenance.primary_work.model_copy(
                    update={"object_id": foreign}
                )
            }
        )
        context = value.graph_context_receipt
        work = context.work_context.model_copy(
            update={
                "source_basis": context.work_context.source_basis.model_copy(
                    update={"document_id": foreign}
                )
            }
        )
        provisional = context.model_copy(
            update={
                "work_context": work,
                "provenance_sha256": canonical_sha256(provenance),
            }
        )
        wire = provisional.model_dump(
            mode="json", by_alias=True, exclude={"context_receipt_sha256"}
        )
        receipt = SurfaceNativeContextReceiptV1.model_validate_json(
            json.dumps({**wire, "context_receipt_sha256": canonical_sha256(wire)})
        )
        capability = value.graph_context_execution.policy.action.write_capability
        capability = capability.model_copy(
            update={
                "basis": capability.basis.model_copy(update={"document_id": foreign})
            }
        )
        intent = value.submitted_intent_v2.model_copy(
            update={
                "primary_work": value.submitted_intent_v2.primary_work.model_copy(
                    update={"object_id": foreign}
                ),
                "build_write_capability_sha256": canonical_sha256(
                    capability.model_dump(mode="json")
                ),
            }
        )
        value = with_intent(
            value.model_copy(
                update={"provenance": provenance, "graph_context_receipt": receipt}
            ),
            intent,
            capability=capability,
        )
    else:
        # Preserve a valid immutable event sequence except the final known outcome.
        from psycopg.types.json import Jsonb

        with psycopg.connect(application_state_dsn) as conn:
            data = conn.execute(
                "SELECT graph_context_execution FROM agent.turn WHERE turn_id=%s",
                (parent.turn_id,),
            ).fetchone()[0]
            data["events"][-1]["outcome"] = "outcome_unknown"
            conn.execute(
                "UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s",
                (Jsonb(data), parent.turn_id),
            )
    reason = {
        "revision": "failed attempt changed",
        "foreign": "predecessor is unavailable",
        "message": "same question and Build page",
        "page": "same question and Build page",
        "unknown": "unknown_outcome",
    }[change]
    with pytest.raises(retry.RetryUnavailableError, match=reason):
        AgentConversationService().accept_turn(value)
    assert (
        len(
            AgentConversationService().list_turns(
                parent.world_id, parent.conversation_id
            )
        )
        == 1
    )


def test_no_retry_fingerprint_unchanged_and_retry_identity_is_bound(failed_case):
    *_, parent, submission, _harness, _writer = failed_case
    intent = submission.submitted_intent_v2
    assert "retry_of" not in intent.model_dump(mode="json")
    first = successor(parent, submission).submitted_intent_v2
    assert submitted_turn_intent_fingerprint_v2(
        first
    ) != submitted_turn_intent_fingerprint_v2(intent)


@pytest.mark.parametrize("state", ["unknown", "proposed", "image_variant"])
def test_existing_or_unresolved_object_blocks_retry(
    failed_case, application_state_dsn, state
):
    *_, parent, submission, _harness, _writer = failed_case
    from psycopg.types.json import Jsonb
    from application_state.build_proposal.types import normalize_proposal_output

    with psycopg.connect(application_state_dsn) as conn:
        action, payload = conn.execute(
            "SELECT action_id,payload FROM agent.build_proposal WHERE world_id=%s",
            (parent.world_id,),
        ).fetchone()
        if state == "image_variant":
            payload["schema_version"] = "dmb_build_image_preparation_v2"
        else:
            payload["state"] = state
            if state == "proposed":
                payload["proposal"] = normalize_proposal_output(
                    payload["raw_response"]
                ).model_dump(mode="json")
                payload["failure_code"] = None
        conn.execute(
            "UPDATE agent.build_proposal SET payload=%s WHERE action_id=%s",
            (Jsonb(payload), action),
        )
    assert not retry.read_context(
        parent.world_id, parent.conversation_id, [parent.turn_id]
    )["turns"][0]["context"]["eligible"]
    with pytest.raises(ApplicationStateConflictError, match="existing_result"):
        AgentConversationService().accept_turn(successor(parent, submission))


def test_accepted_retry_receipt_survives_archive_but_new_retry_cannot_switch_conversation(
    failed_case,
):
    *_, parent, submission, _harness, _writer = failed_case
    service = AgentConversationService()
    request = successor(parent, submission)
    accepted = service.accept_turn(request)
    from tests.application_state.test_conversation_library import new

    new(service, parent.world_id)
    assert service.accept_turn(request) == accepted
    assert not retry.read_context(
        parent.world_id, parent.conversation_id, [parent.turn_id]
    )["turns"][0]["context"]["eligible"]
    changed = request.model_copy(update={"idempotency_key": uuid4()})
    with pytest.raises(ApplicationStateConflictError):
        service.accept_turn(changed)
