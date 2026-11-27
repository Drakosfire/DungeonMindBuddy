"""Real APP admission/claim/read fence. No providers or retained product state."""

from importlib import import_module
import json

from alembic import command
import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.cli import alembic_config, _current_and_head, assert_at_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateValidationError,
)
from tests.application_state.test_agent_conversation_postgres import _new
from tests.test_surface_native_execution import controller, execution, native_writer
from tests.test_surface_native_context import seal
from tests.test_surface_native_turn_records import submission

HEAD = "20261101_0103"


def accept(surface="build"):
    service = AgentConversationService()
    sub = submission(surface)
    first = controller(surface, sub.graph_context_execution.policy)
    data = sub.graph_context_receipt.model_dump(mode="json", by_alias=True)
    data["assembled_input"]["tokenizer_name"] = first.input_estimator
    context = type(sub.graph_context_receipt).model_validate_json(
        json.dumps(seal(data))
    )
    sub = sub.model_copy(
        update={
            "graph_context_receipt": context,
            "graph_context_execution": execution(
                context.context_receipt_sha256, sub.graph_context_execution.policy
            ),
        }
    )
    conversation = _new(service, sub.world_id)
    sub = t.TurnSubmission.model_validate_json(
        sub.model_copy(
            update={"conversation_id": conversation.conversation_id}
        ).model_dump_json(by_alias=True)
    )
    return service, sub, service.accept_turn(sub)


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_actual_shared_native_accept_claim_replay_and_generic_dispatch_refusal(
    application_state_dsn, surface
):
    service, sub, accepted = accept(surface)
    assert service.accept_turn(sub) == accepted
    assert AgentConversationService().list_turns(sub.world_id, sub.conversation_id) == [
        accepted
    ]
    claim = service.claim_turn(
        sub.world_id,
        sub.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    )
    turn = claim.turn
    assert claim.disposition == "claimed" and turn.attempt == 1
    assert (
        AgentConversationService().inspect_turn(
            world_id=sub.world_id, turn_id=turn.turn_id
        )
        == turn
    )
    for forged in (
        controller(surface, turn.graph_context_execution.policy),
        native_writer(surface, turn.graph_context_execution.policy, sequence=0),
    ):
        with pytest.raises(
            ApplicationStateValidationError, match="prepared-input admission owner"
        ):
            service.authorize_provider_attempt(
                sub.world_id,
                sub.conversation_id,
                turn.turn_id,
                expected_revision=turn.revision,
                expected_attempt=turn.attempt,
                provider_attempt_event=forged,
            )
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == turn
    with pytest.raises(
        ApplicationStateValidationError, match="locked producing-output owner"
    ):
        service.complete_turn(
            t.TurnResult(
                world_id=sub.world_id,
                conversation_id=sub.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                assistant_text="Unproved answer",
            )
        )
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == turn
    # No dispatch occurred. The actual existing claim owner may recover expiry.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    reclaimed = service.claim_turn(
        sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision
    )
    assert reclaimed.disposition == "claimed" and reclaimed.turn.attempt == 2
    assert reclaimed.turn.graph_context_receipt == sub.graph_context_receipt


def test_shared_retained_authorization_is_nonreclaimable_and_keeps_telemetry(
    application_state_dsn,
):
    service, sub, accepted = accept()
    turn = service.claim_turn(
        sub.world_id,
        sub.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    # Frozen retained-ledger fixture only: this does not claim SDK input acceptance.
    auth = controller("build", turn.graph_context_execution.policy)
    ledger = execution(
        turn.graph_context_receipt.context_receipt_sha256,
        turn.graph_context_execution.policy,
        [auth],
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET graph_context_execution=%s,claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (Jsonb(ledger.model_dump(mode="json", by_alias=True)), turn.turn_id),
        )
    with pytest.raises(ApplicationStateConflictError):
        service.claim_turn(
            sub.world_id,
            sub.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
    recovered = service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id)
    assert (
        recovered.status == "interrupted"
        and recovered.failure_code == "provider_outcome_unknown"
    )
    assert recovered.graph_context_execution.events[0] == auth
    assert recovered.graph_context_execution.events[1].outcome == "outcome_unknown"
    with pytest.raises(ApplicationStateConflictError):
        service.claim_turn(
            sub.world_id,
            sub.conversation_id,
            turn.turn_id,
            expected_revision=recovered.revision,
        )
    assert (
        service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == recovered
    )


def test_shared_sql_family_rejects_crossed_halves_and_reader_rejects_altered_identity(
    application_state_dsn,
):
    service, sub, turn = accept()
    with psycopg.connect(application_state_dsn) as conn:
        for column in ("graph_context_receipt", "graph_context_execution"):
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute(
                        f"UPDATE agent.turn SET {column}=NULL WHERE turn_id=%s",
                        (turn.turn_id,),
                    )
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute(
                    "UPDATE agent.turn SET graph_context_receipt=jsonb_set(graph_context_receipt,'{schema}',%s) WHERE turn_id=%s",
                    (Jsonb("dmb_agent_build_graph_context_receipt_v1"), turn.turn_id),
                )
        # This field is a Python request commitment, not a second SQL hash authority.
        conn.execute(
            "UPDATE agent.turn SET submitted_intent_fingerprint_v2=%s WHERE turn_id=%s",
            ("f" * 64, turn.turn_id),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id)


def test_shared_reader_fence_preserves_rows_and_refuses_old_reader_and_downgrade(
    application_state_dsn, monkeypatch
):
    service, sub, turn = accept("plan")

    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return conn.execute(
                "SELECT to_jsonb(t)::text FROM agent.turn t WHERE turn_id=%s",
                (turn.turn_id,),
            ).fetchone()[0]

    before = snapshot()
    from application_state import cli

    with monkeypatch.context() as old:
        old.setattr(cli, "_alembic_head", lambda: "20261031_0102")
        with pytest.raises(ApplicationStateMigrationError):
            assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError, match="recovery forward"):
        command.downgrade(alembic_config(), "20261031_0102")
    assert _current_and_head(application_state_dsn) == (HEAD, HEAD)
    assert snapshot() == before
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == turn
    module = import_module(
        "application_state.migrations.versions.20261101_0103_shared_native_turns"
    )
    assert module.down_revision == "20261031_0102"


@pytest.fixture
def predecessor_dsn(monkeypatch, application_state_dsn, application_state_database):
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from tests.application_state.conftest import empty_app_state
    with empty_app_state(application_state_database) as dsn:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        command.upgrade(alembic_config(), "20261031_0102")
        yield dsn


def test_upgrade_retains_historical_row_and_closed_predicates_exactly(
    predecessor_dsn, monkeypatch
):
    from application_state import cli
    from tests.application_state.test_rules_authority_migration import turn_fixture

    with monkeypatch.context() as old:
        old.setattr(cli, "_alembic_head", lambda: "20261031_0102")
        turn = turn_fixture()

    def snapshot():
        with psycopg.connect(predecessor_dsn) as conn:
            return (
                conn.execute(
                    "SELECT to_jsonb(t)::text FROM agent.turn t WHERE turn_id=%s",
                    (turn.turn_id,),
                ).fetchone()[0],
                dict(
                    conn.execute(
                        "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent.turn'::regclass AND conname IN ('agent_turn_graph_context_receipt_check','agent_turn_graph_context_execution_check','agent_turn_graph_completion_check','agent_turn_lifecycle_check')"
                    ).fetchall()
                ),
            )

    before, constraints = snapshot()
    command.upgrade(alembic_config(), HEAD)
    after, extended = snapshot()
    assert after == before
    for name, previous in constraints.items():
        assert "".join(previous[len("CHECK (") : -1].split()) in "".join(
            extended[name].split()
        )
    assert (
        AgentConversationService().inspect_turn(
            world_id=turn.world_id, turn_id=turn.turn_id
        )
        == turn
    )
"""Selected-source recovery against one isolated App fixture; no provider calls."""
import json
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from application_state.agent_conversation import AgentConversationService, types as t
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services.world_container_registry import create_world_container
from tests.application_state.test_agent_conversation_postgres import _new
from tests.test_surface_native_context import provenance_for, seal
from tests.test_surface_native_execution import _selected_source_pending, controller, execution
from tests.test_surface_native_turn_records import submission


def test_selected_source_capture_survives_pre_dispatch_reclaim_but_not_provider_reclaim(application_state_dsn):
    world = create_world_container(name='Selected reader recovery ' + uuid4().hex).world_id
    context, policy, _ = _selected_source_pending()
    ref = policy.action.intent.authored_references.references[0].model_copy(update={'managed_world_id':world})
    refs = policy.action.intent.authored_references.model_copy(update={'references':(ref,)})
    intent = policy.action.intent.model_copy(update={'world_id':world,
        'graph_request':policy.action.intent.graph_request.model_copy(update={'world_id':world}),
        'authored_references':refs})
    authority = context.native_query.authority.model_copy(update={'managed_world_id':world})
    query = context.native_query.model_copy(update={'authority':authority,'selected_references_sha256':refs.sha256})
    source = context.source_authority.model_copy(update={'managed_world_id':world})
    data = context.model_dump(mode='json',by_alias=True)
    data['work_context']['source_basis']['world_id'] = world
    data['native_query'] = query.model_dump(mode='json',by_alias=True)
    data['source_authority'] = source.model_dump(mode='json',by_alias=True)
    work = type(context.work_context).model_validate(data['work_context'])
    provenance = provenance_for(work).model_copy(update={'surface_instance_id':intent.surface_instance_id})
    data['provenance_sha256'] = t.canonical_sha256(provenance)
    context = type(context).model_validate_json(json.dumps(seal(data)))
    policy = policy.model_copy(update={'action':policy.action.model_copy(update={'intent':intent}),
        'source_authority_sha256':t.canonical_sha256(source),
        'native_query_sha256':t.canonical_sha256(query.model_dump(mode='json',by_alias=True))})
    record = execution(context.context_receipt_sha256,policy,[])
    service = AgentConversationService()
    conversation = _new(service,world)
    sub = t.TurnSubmission.model_validate_json(submission('build').model_copy(update={
        'world_id':world,'conversation_id':conversation.conversation_id,'user_text':intent.message,
        'provenance':provenance,'submitted_intent_v2':intent,'graph_context_receipt':context,
        'graph_context_execution':record}).model_dump_json(by_alias=True))
    accepted = service.accept_turn(sub)
    assert AgentConversationService().inspect_turn(world_id=world,turn_id=accepted.turn_id) == accepted
    claimed = service.claim_turn(world,conversation.conversation_id,accepted.turn_id,expected_revision=accepted.revision).turn
    captured, fresh = service.capture_native_authored_references(world,conversation.conversation_id,claimed.turn_id,
        expected_revision=claimed.revision,expected_attempt=claimed.attempt,event_id=uuid4())
    assert fresh and AgentConversationService().inspect_turn(world_id=world,turn_id=captured.turn_id) == captured
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(captured.turn_id,))
    recovered = service.claim_turn(world,conversation.conversation_id,captured.turn_id,expected_revision=captured.revision).turn
    assert recovered.attempt == captured.attempt + 1
    assert AgentConversationService().inspect_turn(world_id=world,turn_id=recovered.turn_id) == recovered
    assert recovered.graph_context_execution.events[0].references == refs
    assert recovered.graph_context_execution.events[0].attempt == captured.attempt
    from apps.live_control_server.services.native_authored_references import capture_input
    fence = SimpleNamespace(turn=recovered,append=lambda *_args,**_kwargs:pytest.fail('duplicate capture'))
    capture_input(SimpleNamespace(fence=fence,turn=recovered))
    original = recovered.graph_context_execution.events[0]
    for tampered in (
        original.model_copy(update={'attempt':recovered.attempt+1}),
        original.model_copy(update={'references':refs.model_copy(update={'references':(
            ref.model_copy(update={'source_revision_id':'changed'}),)})}),
    ):
        altered = recovered.model_copy(update={'graph_context_execution':
            recovered.graph_context_execution.model_copy(update={'events':[tampered]})})
        with pytest.raises(ValueError):
            capture_input(SimpleNamespace(fence=SimpleNamespace(turn=altered),turn=altered))

    # Simulate only the durable authorization record; no provider was called.
    auth = controller('build',policy,sequence=1)
    authorized = execution(context.context_receipt_sha256,policy,[recovered.graph_context_execution.events[0],auth])
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET graph_context_execution=%s,claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (Jsonb(authorized.model_dump(mode='json',by_alias=True)),recovered.turn_id))
    with pytest.raises(ApplicationStateConflictError,match='cannot be reclaimed'):
        service.claim_turn(world,conversation.conversation_id,recovered.turn_id,expected_revision=recovered.revision)
    fenced = service.inspect_turn(world_id=world,turn_id=recovered.turn_id)
    assert fenced.status == 'interrupted' and fenced.attempt == recovered.attempt
    assert [e.outcome for e in fenced.graph_context_execution.events if e.kind=='provider_outcome'] == ['outcome_unknown']
