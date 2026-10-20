"""Claim/CAS and transaction proof against fixture-owned disposable PostgreSQL."""

from hashlib import sha256
import json
from uuid import uuid4

import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_events import (
    RulesToolAuthorizedV1,
    RulesQueryObservedV1,
    query_identity,
)
from application_state.agent_conversation.rules_authority_store import (
    open_execution_locked,
    append_lookup_event_locked,
)
from application_state.agent_conversation.rules_authority_types import (
    RulesScopeV1,
    RULES_BUDGET_V1,
)
from application_state.agent_conversation.types import (
    ConversationCommand,
    HistoricalReference,
    TurnProvenance,
    TurnSubmission,
    SubmittedTurnIntentV1,
    SubmittedGraphRequestIntentV1,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)


def admitted():
    service = AgentConversationService()
    world = "rules-store-fixture"
    receipt = service.new_conversation(
        ConversationCommand(
            world_id=world,
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    conversation = service.get_conversation(world, receipt.conversation_id)
    turn = service.accept_turn(
        TurnSubmission(
            world_id=world,
            conversation_id=conversation.conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=conversation.revision,
            user_text="Rules fixture",
            provenance=TurnProvenance(
                world_id=world,
                surface_resolution="resolved",
                surface_id="index",
                surface_instance_id="rules-store",
                primary_work=HistoricalReference(resolution="absent"),
                supporting_work=[],
                selected_object=HistoricalReference(resolution="absent"),
            ),
            submitted_intent_v1=SubmittedTurnIntentV1(
                world_id=world,
                client_thread_id="rules-store-thread",
                message="Rules fixture",
                surface_id="index",
                surface_instance_id="rules-store",
                client_work_state="none",
                primary_work=None,
                graph_request=SubmittedGraphRequestIntentV1(mode="none"),
                graph_selection=None,
            ),
        )
    )
    turn = service.claim_turn(
        world, turn.conversation_id, turn.turn_id, expected_revision=turn.revision
    ).turn
    scope = RulesScopeV1(
        schema="dmb_rules_scope_v1",
        execution_id=uuid4(),
        world_id=world,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        product_attempt=turn.attempt,
        ruleset_id="srd_2024",
        corpus_sha256="a" * 64,
        authorization_id=uuid4(),
        capability_policy_sha256="b" * 64,
        budget=RULES_BUDGET_V1,
    )
    return turn, scope


def authorization(scope):
    return RulesToolAuthorizedV1(
        event_id=uuid4(),
        sequence=0,
        execution_id=scope.execution_id,
        kind="tool_authorized",
        call_id="lookup:1",
        query_id=query_identity(scope, "travel"),
        normalized_question="travel",
        packet_limit=4,
    )


def observation(scope, auth):
    raw = json.dumps(
        dict(
            schema="dmb_rules_packet_v1",
            call_id=auth.call_id,
            query_id=auth.query_id,
            normalized_question=auth.normalized_question,
            corpus_sha256=scope.corpus_sha256,
            ruleset_id=scope.ruleset_id,
            status="no_evidence",
            support_refs=[],
            emitted_support_ids=[],
            previous_support_ids=[],
            support_capsules=[],
            diagnostic=None,
        ),
        ensure_ascii=False,
    )
    event = RulesQueryObservedV1(
        event_id=uuid4(),
        sequence=1,
        execution_id=scope.execution_id,
        kind="query_observed",
        call_id=auth.call_id,
        query_id=auth.query_id,
        packet_sha256=sha256(raw.encode()).hexdigest(),
        presentation_utf8=len(raw.encode()),
        status="no_evidence",
        support_refs=(),
        emitted_support_ids=(),
    )
    return event, raw


def test_open_and_exact_append_replay_do_not_renew_claim_or_increment_twice(
    application_state_dsn,
):
    turn, scope = admitted()
    auth = authorization(scope)
    observed, raw = observation(scope, auth)
    with psycopg.connect(application_state_dsn) as conn:
        record = open_execution_locked(
            conn, scope, expected_turn_revision=turn.revision
        )
        assert record.revision == 1
        assert (
            open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
            == record
        )
        record, changed = append_lookup_event_locked(
            conn,
            scope,
            expected_turn_revision=turn.revision,
            expected_ledger_revision=1,
            event=auth,
        )
        assert changed and record.revision == 2
        record, changed = append_lookup_event_locked(
            conn,
            scope,
            expected_turn_revision=turn.revision,
            expected_ledger_revision=2,
            event=observed,
            raw_output=raw,
        )
        assert changed and record.revision == 3
        replay, changed = append_lookup_event_locked(
            conn,
            scope,
            expected_turn_revision=turn.revision,
            expected_ledger_revision=2,
            event=observed,
            raw_output=raw,
        )
        assert not changed and replay == record
        assert record.execution.budget_use.presentation_utf8 == len(raw.encode())
        row = conn.execute(
            "SELECT revision,attempt,claim_expires_at FROM agent.turn WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()
        assert row == (turn.revision, turn.attempt, turn.claim_expires_at)


@pytest.mark.parametrize(
    "fence", ["revision", "attempt", "world", "conversation", "expired"]
)
def test_scope_and_current_claim_are_required_before_any_ledger_write(
    application_state_dsn, fence
):
    turn, scope = admitted()
    revision = turn.revision
    fields = scope.model_dump(mode="python", by_alias=True)
    if fence == "revision":
        revision -= 1
    if fence == "attempt":
        fields["product_attempt"] += 1
    if fence == "world":
        fields["world_id"] = "another-world"
    if fence == "conversation":
        fields["conversation_id"] = uuid4()
    scope = RulesScopeV1(**fields)
    if fence == "expired":
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
                (turn.turn_id,),
            )
    with pytest.raises((ApplicationStateConflictError, ApplicationStateNotFoundError)):
        with psycopg.connect(application_state_dsn) as conn:
            open_execution_locked(conn, scope, expected_turn_revision=revision)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM agent.turn_rules_execution"
        ).fetchone() == (0,)


def test_changed_authority_and_stale_ledger_revision_reject_without_mutation(
    application_state_dsn,
):
    turn, scope = admitted()
    auth = authorization(scope)
    with psycopg.connect(application_state_dsn) as conn:
        open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
    changed = scope.model_dump(mode="python", by_alias=True)
    changed["corpus_sha256"] = "c" * 64
    with pytest.raises(ApplicationStateConflictError):
        with psycopg.connect(application_state_dsn) as conn:
            open_execution_locked(
                conn, RulesScopeV1(**changed), expected_turn_revision=turn.revision
            )
    with pytest.raises(ApplicationStateConflictError):
        with psycopg.connect(application_state_dsn) as conn:
            append_lookup_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=99,
                event=auth,
            )
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            open_execution_locked(
                conn, scope, expected_turn_revision=turn.revision
            ).revision
            == 1
        )


def test_invalid_output_rolls_back_all_writes_in_the_callers_transaction(
    application_state_dsn,
):
    turn, scope = admitted()
    auth = authorization(scope)
    observed, raw = observation(scope, auth)
    with pytest.raises(ApplicationStateValidationError):
        with psycopg.connect(application_state_dsn) as conn:
            open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
            append_lookup_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=1,
                event=auth,
            )
            append_lookup_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=2,
                event=observed,
                raw_output=raw + " ",
            )
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM agent.turn_rules_execution"
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT status,revision FROM agent.turn WHERE turn_id=%s", (turn.turn_id,)
        ).fetchone() == ("running", turn.revision)
