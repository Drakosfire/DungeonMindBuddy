"""Marker-first SQL read proof. Seeded rows are read fixtures, not finalizer proof."""

import json
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import (
    AgentConversationService,
    repository as repo,
)
from application_state.agent_conversation.rules_authority_completion import (
    prepare_rules_acceptance,
)
from application_state.agent_conversation.rules_authority_events import RulesExecutionV1
from application_state.agent_conversation.rules_authority_reads import (
    MixedCompletedTurnV1,
)
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.errors import ApplicationStateIntegrityError
from tests.application_state.test_rules_authority_store import admitted
from tests.test_rules_authority_events import accepted_fixture


def seed_read_fixture(dsn, *, plan=False):
    if plan:
        from tests.application_state.test_agent_conversation_postgres import (
            _accepted_execution_turn,
        )
        from application_state.agent_conversation.rules_authority_types import (
            RulesScopeV1,
            RULES_BUDGET_V1,
        )

        service = AgentConversationService()
        _, _, _, turn = _accepted_execution_turn(service, "rules-read-plan-world")
        scope = RulesScopeV1(
            schema="dmb_rules_scope_v1",
            execution_id=uuid4(),
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            product_attempt=turn.attempt,
            ruleset_id="srd_2024",
            corpus_sha256="a" * 64,
            authorization_id=uuid4(),
            capability_policy_sha256="b" * 64,
            budget=RULES_BUDGET_V1,
        )
    else:
        turn, scope = admitted()
    data = accepted_fixture()
    composition = RulesExecutionV1.model_validate_json(json.dumps(data)).composition
    producer = RulesExecutionV1.model_validate_json(
        json.dumps(data)
    ).rules_completion.producing_provider_attempt_id
    if plan:
        from tests.application_state.test_agent_conversation_postgres import (
            _provider_authorization_event,
        )
        from application_state.agent_conversation.types import ProviderOutcomeEventV1

        # Keep the initial frozen envelope and the later Rules-producing input
        # as distinct real Graph lifecycle records; never weaken first dispatch.
        for attempt_id, envelope in [(uuid4(), "c" * 64), (producer, "f" * 64)]:
            auth = _provider_authorization_event(
                attempt_id=attempt_id, sequence=len(turn.graph_context_execution.events)
            ).model_copy(update={"envelope_sha256": envelope})
            turn, _ = service.authorize_provider_attempt(
                turn.world_id,
                turn.conversation_id,
                turn.turn_id,
                expected_revision=turn.revision,
                expected_attempt=turn.attempt,
                provider_attempt_event=auth,
            )
            for state in ("sdk_entered", "response_received"):
                turn, _ = service.record_provider_outcome(
                    turn.world_id,
                    turn.conversation_id,
                    turn.turn_id,
                    expected_revision=turn.revision,
                    expected_attempt=turn.attempt,
                    outcome=ProviderOutcomeEventV1(
                        event_id=uuid4(),
                        sequence=len(turn.graph_context_execution.events),
                        kind="provider_outcome",
                        provider_attempt_id=attempt_id,
                        outcome=state,
                    ),
                )
        composition = type(composition).model_validate_json(
            composition.model_dump_json(by_alias=True).replace(
                '"absent"', '"unclaimed"'
            )
        )
    data.update(
        scope=scope.model_dump(mode="json", by_alias=True),
        state="active",
        composition=None,
        rules_completion=None,
    )
    data["events"].pop()
    for event in data["events"]:
        event["execution_id"] = str(scope.execution_id)
    active = RulesExecutionV1.model_validate_json(json.dumps(data))
    execution, binding = prepare_rules_acceptance(
        active,
        composition,
        producing_provider_attempt_id=producer,
        accepted_turn_revision=turn.revision + 1,
        event_id=uuid4(),
    )
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """INSERT INTO agent.turn_rules_execution(turn_id,product_attempt,revision,payload,accepted_binding,accepted_binding_sha256)
            VALUES(%s,%s,1,%s,%s,%s)""",
            (
                turn.turn_id,
                turn.attempt,
                Jsonb(execution.model_dump(mode="json", by_alias=True)),
                Jsonb(binding.model_dump(mode="json", by_alias=True)),
                canonical_sha256(binding),
            ),
        )
        conn.execute(
            """UPDATE agent.turn SET status='completed',revision=revision+1,assistant_text=%s,claim_expires_at=NULL,
            completed_at=clock_timestamp(),updated_at=clock_timestamp(),answer_composition_kind='rules_mixed_v1' WHERE turn_id=%s""",
            (composition.render(), turn.turn_id),
        )
    return turn, binding


def test_all_repository_reads_classify_marker_before_ordinary_turn(
    application_state_dsn,
):
    turn, binding = seed_read_fixture(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        direct = repo.get_turn(conn, turn.world_id, turn.turn_id)
        locked = repo.lock_turn(conn, turn.world_id, turn.turn_id)
        page = repo.list_turns(
            conn, turn.world_id, turn.conversation_id, limit=100, before_sequence=None
        )
        keyed = repo.get_turn_by_world_key(conn, turn.world_id, turn.idempotency_key)[0]
        assert repo.get_turn(conn, "another-world", turn.turn_id) is None
    assert isinstance(direct, MixedCompletedTurnV1)
    assert direct == locked == keyed == page[0]
    assert direct.envelope.revision == turn.revision + 1
    assert (
        direct.accepted_binding == binding and direct.base_projection.kind == "absent"
    )
    assert AgentConversationService().list_turns(
        turn.world_id, turn.conversation_id
    ) == [direct]


@pytest.mark.parametrize(
    "corruption",
    ["base_marker", "missing_ledger", "wrong_seal", "wrong_owner", "missing_binding"],
)
def test_corrupt_mixed_authority_never_falls_back_to_plain_text(
    application_state_dsn, corruption
):
    turn, binding = seed_read_fixture(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        if corruption == "base_marker":
            conn.execute(
                "UPDATE agent.turn SET answer_composition_kind='base' WHERE turn_id=%s",
                (turn.turn_id,),
            )
        elif corruption == "missing_ledger":
            conn.execute(
                "DELETE FROM agent.turn_rules_execution WHERE turn_id=%s",
                (turn.turn_id,),
            )
        elif corruption == "wrong_seal":
            conn.execute(
                "UPDATE agent.turn_rules_execution SET accepted_binding_sha256=%s WHERE turn_id=%s",
                ("f" * 64, turn.turn_id),
            )
        elif corruption == "wrong_owner":
            data = binding.model_dump(mode="json", by_alias=True)
            data["world_id"] = "other-world"
            conn.execute(
                "UPDATE agent.turn_rules_execution SET accepted_binding=%s,accepted_binding_sha256=%s WHERE turn_id=%s",
                (Jsonb(data), canonical_sha256(data), turn.turn_id),
            )
        else:
            # Deliberate corruption in this generated fixture DB only; prove the
            # read boundary still rejects after SQL constraint protection is lost.
            conn.execute(
                "ALTER TABLE agent.turn_rules_execution DROP CONSTRAINT rules_execution_accepted_binding_check"
            )
            conn.execute(
                "UPDATE agent.turn_rules_execution SET accepted_binding=NULL WHERE turn_id=%s",
                (turn.turn_id,),
            )
    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().list_turns(turn.world_id, turn.conversation_id)


def test_oversized_summary_is_rejected_by_sql_guard_before_model_transfer(
    application_state_dsn,
):
    turn, binding = seed_read_fixture(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "ALTER TABLE agent.turn_rules_execution DROP CONSTRAINT rules_execution_accepted_binding_check"
        )
        data = binding.model_dump(mode="json", by_alias=True)
        data["oversized"] = "x" * 50000
        conn.execute(
            "UPDATE agent.turn_rules_execution SET accepted_binding=%s WHERE turn_id=%s",
            (Jsonb(data), turn.turn_id),
        )
        with pytest.raises(
            ApplicationStateIntegrityError, match="missing or invalid accepted"
        ):
            repo.get_turn(conn, turn.world_id, turn.turn_id)


def test_completed_claim_returns_mixed_without_renewal_and_ordinary_mutations_reject(
    application_state_dsn,
):
    from application_state.errors import ApplicationStateConflictError
    from application_state.agent_conversation.types import (
        TurnResult,
        TurnFailure,
        TurnClaimReceipt,
    )
    from pydantic import ValidationError

    turn, binding = seed_read_fixture(application_state_dsn)
    service = AgentConversationService()
    completed = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    receipt = service.claim_turn(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
    )
    assert receipt.disposition == "completed" and receipt.turn == completed
    with pytest.raises(ValidationError):
        TurnClaimReceipt(disposition="claimed", turn=completed)
    with pytest.raises(ApplicationStateConflictError):
        service.renew_turn_claim(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        )
    with pytest.raises(ApplicationStateConflictError):
        service.complete_turn(
            TurnResult(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                assistant_text=completed.assistant_text,
            )
        )
    with pytest.raises(ApplicationStateConflictError):
        service.fail_turn(
            TurnFailure(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                failure_code="late",
            )
        )
    assert (
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id) == completed
    )


def test_plan_rules_only_history_keeps_graph_unclaimed_and_source_controls(
    application_state_dsn,
):
    from application_state.agent_conversation.rules_authority_reads import (
        MixedHistoryAttributionV1,
    )

    turn, binding = seed_read_fixture(application_state_dsn, plan=True)
    service = AgentConversationService()
    completed = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert completed.base_projection.kind == "unclaimed"
    pairs = service.list_completed_plan_ask_context(
        turn.world_id, turn.graph_context_receipt.plan_basis
    )
    assert len(pairs) == 1 and pairs[0].answer == completed.assistant_text
    attribution = pairs[0].history_attribution
    assert isinstance(attribution, MixedHistoryAttributionV1)
    assert (
        attribution.base_attribution is None
        and not attribution.accepted_binding.graph_used
    )
    assert attribution.accepted_binding.support_table == binding.support_table
