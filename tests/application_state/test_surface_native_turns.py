"""Real APP admission/claim/read fence. No providers or retained product state."""

from importlib import import_module
import json
from uuid import uuid4

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
def predecessor_dsn(monkeypatch):
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from tests.application_state.conftest import (
        _admin_dsn,
        _replace_database,
        _create_database,
        _drop_database,
    )

    admin = _admin_dsn()
    name = "dungeonbuddy_app_state_test_" + uuid4().hex[:12]
    _create_database(admin, name)
    dsn = _replace_database(admin, name)
    monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
    try:
        command.upgrade(alembic_config(), "20261031_0102")
        yield dsn
    finally:
        monkeypatch.delenv(APPLICATION_STATE_DSN_ENV, raising=False)
        _drop_database(admin, name)


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
