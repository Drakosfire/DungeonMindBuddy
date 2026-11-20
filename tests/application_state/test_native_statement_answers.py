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


@pytest.mark.parametrize("historical_status", ["completed", "interrupted"])
def test_retained_v1_turns_reconstruct_original_request_and_remain_readable(
    completed_native, historical_status
):
    """Retained data need the exact V1 contract, without enabling new V1 calls."""
    import json
    from hashlib import sha256
    from application_state.agent_conversation.native_statement_input import (
        NativeStatementWriterPolicyV1,
        canonical,
        digest,
        native_input_tokens,
    )
    from application_state.agent_conversation.native_statement_answer import (
        writer_contract,
        normalize_output,
        answer_text,
    )
    from application_state.agent_conversation.types import (
        ProviderAttemptAuthorizedEventV1,
    )

    service, turn, dsn = completed_native
    execution = turn.graph_context_execution.model_dump(mode="json", by_alias=True)
    policy = NativeStatementWriterPolicyV1(
        **{**execution["policy"], "policy_version": "native_statement_writer_v1"}
    )
    execution["policy"] = policy.model_dump(mode="json")
    execution["execution_policy_sha256"] = digest(policy)
    inclusion = next(
        e for e in execution["events"] if e["kind"] == "native_statement_input_v1"
    )
    request = json.loads(inclusion["prepared_request_json"])
    instructions, schema = writer_contract(turn.graph_context_receipt, policy)
    request["instructions"] = instructions
    request["text"]["format"]["schema"] = schema
    raw = canonical(request)
    envelope = sha256(raw.encode()).hexdigest()
    inclusion["prepared_request_json"] = raw
    for event in execution["events"]:
        if "envelope_sha256" in event:
            event["envelope_sha256"] = envelope
    execution["events"][0]["input_tokens"] = native_input_tokens(raw)
    capture = next(
        e
        for e in execution["events"]
        if e["kind"] == "native_statement_output_captured_v1"
    )
    auth = ProviderAttemptAuthorizedEventV1.model_validate(execution["events"][0])
    completion = normalize_output(
        turn.graph_context_receipt, auth, capture["raw_output_json"]
    )
    execution["events"][-1]["completion_sha256"] = digest(completion)
    if historical_status == "interrupted":
        execution["events"] = execution["events"][:-1]
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET graph_context_execution=%s, completion=%s, assistant_text=%s, status=%s, failure_code=CASE WHEN %s='interrupted' THEN 'retained_native_test_failure' ELSE NULL END WHERE turn_id=%s",
            (
                Jsonb(execution),
                Jsonb(completion.model_dump(mode="json", by_alias=True))
                if historical_status == "completed"
                else None,
                answer_text(completion) if historical_status == "completed" else None,
                historical_status,
                historical_status,
                turn.turn_id,
            ),
        )
    loaded = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert loaded.status == historical_status
    assert (
        loaded.graph_context_execution.policy.policy_version
        == "native_statement_writer_v1"
    )
    retained = next(
        e
        for e in loaded.graph_context_execution.events
        if e.kind == "native_statement_input_v1"
    )
    assert retained.prepared_request_json == raw
    if historical_status == "completed":
        assert loaded.completion == completion
    else:
        assert loaded.completion is None


def test_historical_empty_v1_execution_cannot_start_a_new_call(
    completed_native, monkeypatch, tmp_path, lane
):
    from application_state.agent_conversation.native_statement_input import (
        NativeStatementWriterPolicyV1,
        digest,
    )

    service, turn, dsn = completed_native
    execution = turn.graph_context_execution.model_dump(mode="json", by_alias=True)
    policy = NativeStatementWriterPolicyV1(
        **{**execution["policy"], "policy_version": "native_statement_writer_v1"}
    )
    execution.update(
        policy=policy.model_dump(mode="json"),
        execution_policy_sha256=digest(policy),
        events=[],
    )
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET graph_context_execution=%s, status='accepted', completion=NULL, assistant_text=NULL, completed_at=NULL WHERE turn_id=%s",
            (Jsonb(execution), turn.turn_id),
        )
    wire = Wire()
    client = native_client(lane, monkeypatch, tmp_path, wire)
    reply = client.post("/api/live/agent/turn", json=request_for(lane))
    assert reply.status_code == 409
    assert (
        reply.json()["detail"]["code"] == "native_statement_historical_policy_retained"
    )
    assert wire.requests == []
