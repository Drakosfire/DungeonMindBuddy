"""Persisted native-policy rejection and strict reload, on real disposable APP."""

import psycopg
import pytest
from psycopg.types.json import Jsonb

from application_state.agent_conversation import AgentConversationService
from application_state.errors import ApplicationStateIntegrityError
from tests.test_source_statements import lane as lane
from tests.test_source_statements import commit
from tests.test_agent_native_statement_answers import native_client, request_for, Wire


@pytest.fixture
def completed_native(lane, application_state_dsn, monkeypatch, tmp_path):
    commit(lane)
    wire = Wire()
    client = native_client(lane, monkeypatch, tmp_path, wire)
    assert (
        client.post("/api/live/agent/turn", json=request_for(lane)).status_code == 200
    )
    service = AgentConversationService()
    world = lane.selection.managed_world_id
    (turn,) = service.list_turns(
        world, service.get_active_conversation(world).conversation_id
    )
    return service, turn, application_state_dsn


@pytest.mark.parametrize(
    "attack",
    ["absent_completion", "legacy_completion", "missing_input", "classic_receipt"],
)
def test_sql_refuses_native_policy_completion_shape_bypass(completed_native, attack):
    _, turn, dsn = completed_native
    with psycopg.connect(dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            if attack == "absent_completion":
                conn.execute(
                    "UPDATE agent.turn SET completion=NULL WHERE turn_id=%s",
                    (turn.turn_id,),
                )
            elif attack == "legacy_completion":
                conn.execute(
                    "UPDATE agent.turn SET completion=jsonb_set(completion,'{schema}','\"dmb_surface_evidence_completion_v4\"') WHERE turn_id=%s",
                    (turn.turn_id,),
                )
            elif attack == "missing_input":
                execution = turn.graph_context_execution.model_dump(
                    mode="json", by_alias=True
                )
                execution["events"] = [
                    e
                    for e in execution["events"]
                    if e["kind"] != "native_statement_input_v1"
                ]
                conn.execute(
                    "UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s",
                    (Jsonb(execution), turn.turn_id),
                )
            else:
                conn.execute(
                    "UPDATE agent.turn SET graph_context_receipt=jsonb_set(graph_context_receipt,'{schema}','\"dmb_agent_plan_world_graph_context_receipt_v1\"') WHERE turn_id=%s",
                    (turn.turn_id,),
                )


def test_reload_reconstructs_citations_instead_of_trusting_stored_completion(
    completed_native,
):
    service, turn, dsn = completed_native
    payload = turn.completion.model_dump(mode="json", by_alias=True)
    payload["native_clause_citations"][0]["source_revision_id"] = (
        turn.graph_context_receipt.frame.revision_id
    )
    # Update the completion binding too: consistency of two attacker-controlled
    # digests is not sufficient to replace original output/source correspondence.
    execution = turn.graph_context_execution.model_dump(mode="json", by_alias=True)
    from application_state.agent_conversation.native_statement_input import digest

    execution["events"][-1]["completion_sha256"] = digest(payload)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET completion=%s,graph_context_execution=%s WHERE turn_id=%s",
            (Jsonb(payload), Jsonb(execution), turn.turn_id),
        )
    with pytest.raises(
        (ApplicationStateIntegrityError, ValueError), match="Native completion differs"
    ):
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)


def test_authorized_native_claim_expiry_is_unknown_and_cannot_redispatch(
    completed_native,
):
    from application_state.errors import ApplicationStateConflictError

    service, turn, dsn = completed_native
    execution = turn.graph_context_execution.model_dump(mode="json", by_alias=True)
    execution["events"] = execution["events"][:2]
    # Simulate death after durable authorization/input, before SDK-entry recording.
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET status='running', assistant_text=NULL, completion=NULL, "
            "completed_at=NULL, claim_expires_at=clock_timestamp()-interval '1 second', "
            "graph_context_execution=%s WHERE turn_id=%s",
            (Jsonb(execution), turn.turn_id),
        )
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        service.claim_turn(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
    retained = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert retained.status == "interrupted"
    assert retained.attempt == turn.attempt
    assert retained.failure_code == "provider_outcome_unknown"
    assert retained.graph_context_execution.events[-1].outcome == "outcome_unknown"
    assert len(retained.graph_context_execution.events) == 3
