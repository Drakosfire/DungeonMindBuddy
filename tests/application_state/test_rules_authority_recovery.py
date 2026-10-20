"""Expired Rules attempts retain uncertainty and never inherit old evidence."""

import json
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_events import (
    RulesExecutionV1,
    RulesToolAuthorizedV1,
    query_identity,
)
from application_state.agent_conversation.rules_authority_store import (
    open_execution_locked,
    append_lookup_event_locked,
)
from application_state.agent_conversation.rules_authority_types import RulesScopeV1
from application_state.errors import ApplicationStateConflictError
from tests.application_state.test_rules_authority_completion import (
    ready_rules,
    persisted,
    join_graph_provider,
)
from tests.application_state.test_rules_authority_store import admitted


@pytest.mark.parametrize("outcome", ["missing", "unknown", "answered", "failed"])
def test_expired_provider_authorization_is_interrupted_once_and_never_redispatched(
    application_state_dsn, outcome
):
    turn, result = ready_rules(application_state_dsn)
    service = AgentConversationService()
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute(
            "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()[0]
        if outcome == "missing":
            payload["events"].pop()
        else:
            payload["events"][-1]["status"] = outcome
        value = RulesExecutionV1.model_validate_json(json.dumps(payload))
        conn.execute(
            "UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s",
            (Jsonb(value.model_dump(mode="json", by_alias=True)), turn.turn_id),
        )
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    before = persisted(application_state_dsn, turn)
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        service.claim_turn(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
    interrupted = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert (
        interrupted.status == "interrupted"
        and interrupted.attempt == turn.attempt
        and interrupted.revision == turn.revision + 1
    )
    expected = (
        "rules_provider_outcome_unknown"
        if outcome in {"missing", "unknown"}
        else "rules_provider_authorized_nonreclaimable"
    )
    assert interrupted.failure_code == expected
    after = persisted(application_state_dsn, turn)
    assert (
        after[1][1]["state"] == "failed"
        and after[1][1]["events"] == before[1][1]["events"]
    )
    assert after[1][1]["supports"] == before[1][1]["supports"] and after[1][2] is None
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        service.claim_turn(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=interrupted.revision,
        )
    assert persisted(application_state_dsn, turn) == after


def test_no_dispatch_reclaim_retires_pending_lookup_and_starts_empty_attempt(
    application_state_dsn,
):
    turn, scope = admitted()
    service = AgentConversationService()
    event = RulesToolAuthorizedV1(
        event_id=uuid4(),
        sequence=0,
        execution_id=scope.execution_id,
        kind="tool_authorized",
        call_id="pending:1",
        query_id=query_identity(scope, "Travel?"),
        normalized_question="travel?",
        packet_limit=4,
    )
    with psycopg.connect(application_state_dsn) as conn:
        open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
        append_lookup_event_locked(
            conn,
            scope,
            expected_turn_revision=turn.revision,
            expected_ledger_revision=1,
            event=event,
        )
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    claimed = service.claim_turn(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
    ).turn
    assert claimed.attempt == turn.attempt + 1
    fields = scope.model_dump(mode="python", by_alias=True)
    fields.update(
        product_attempt=claimed.attempt, execution_id=uuid4(), authorization_id=uuid4()
    )
    fresh_scope = RulesScopeV1(**fields)
    with psycopg.connect(application_state_dsn) as conn:
        fresh = open_execution_locked(
            conn, fresh_scope, expected_turn_revision=claimed.revision
        )
        assert (
            fresh.execution.events == ()
            and fresh.execution.supports == {}
            and fresh.execution.budget_use.calls == 0
        )
    with pytest.raises(ApplicationStateConflictError):
        with psycopg.connect(application_state_dsn) as conn:
            append_lookup_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=2,
                event=event,
            )
    with psycopg.connect(application_state_dsn) as conn:
        old = conn.execute(
            "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",
            (turn.turn_id, turn.attempt),
        ).fetchone()[0]
    assert old["state"] == "failed" and old["budget_use"]["calls"] == 1


def test_expired_graph_dispatch_closes_rules_in_the_same_transaction(
    application_state_dsn,
):
    from tests.application_state.test_agent_conversation_postgres import (
        _accepted_execution_turn,
    )

    service = AgentConversationService()
    _, _, _, turn = _accepted_execution_turn(service, "rules-graph-recovery-world")
    turn, result = ready_rules(application_state_dsn, turn)
    turn = join_graph_provider(application_state_dsn, service, turn, result)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    with pytest.raises(ApplicationStateConflictError, match="cannot be reclaimed"):
        service.claim_turn(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
    owner, ledger = persisted(application_state_dsn, turn)
    assert (
        owner[0] == "interrupted"
        and ledger[1]["state"] == "failed"
        and ledger[2] is None
    )
