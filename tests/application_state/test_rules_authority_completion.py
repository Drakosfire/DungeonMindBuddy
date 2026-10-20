"""Real mixed completion/replay/rollback; no seeded completed rows in this suite."""

from hashlib import sha256
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
    MixedTurnResultV1,
    NativeRulesMixedTurnResultV1,
)
from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1
from application_state.agent_conversation.rules_authority_events import (
    RulesToolAuthorizedV1,
    RulesQueryObservedV1,
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
    RulesProviderOutcomeV1,
    RulesOutputRefV1,
    RulesExecutionV1,
)
from application_state.agent_conversation.rules_authority_reads import (
    MixedCompletedTurnV1,
)
from application_state.agent_conversation.rules_authority_store import (
    open_execution_locked,
    append_lookup_event_locked,
    append_provider_event_locked,
)
from application_state.agent_conversation.rules_authority_types import (
    RulesScopeV1,
    RULES_BUDGET_V1,
    RulesSupportRefV1,
    AnswerCompositionV1,
)
from application_state.agent_conversation.types import TurnResult, TurnFailure
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateValidationError,
)
from tests.application_state.test_rules_authority_store import admitted
from tests.test_rules_authority_events import fixture


def hashed(text):
    return sha256(text.encode()).hexdigest()


def ready_rules(dsn, turn=None):
    if turn is None:
        turn, scope = admitted()
    else:
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
    _, unit, raw, data, reference = fixture()
    for item in data["events"]:
        item["execution_id"] = str(scope.execution_id)
    auth = RulesToolAuthorizedV1.model_validate_json(json.dumps(data["events"][0]))
    observed = RulesQueryObservedV1.model_validate_json(json.dumps(data["events"][1]))
    ref = RulesSupportRefV1.model_validate_json(json.dumps(reference))
    body = json.dumps(
        dict(
            input=[
                dict(
                    type="function_call",
                    call_id=auth.call_id,
                    name="lookup_rules",
                    arguments=json.dumps(
                        dict(question="Occupied space?", ruleset_id=scope.ruleset_id)
                    ),
                ),
                dict(type="function_call_output", call_id=auth.call_id, output=raw),
            ]
        ),
        ensure_ascii=False,
    )
    producer = uuid4()
    fields = dict(
        execution_id=scope.execution_id,
        provider_attempt_id=producer,
        request_envelope_sha256=hashed(body),
    )
    outputs = (
        RulesOutputRefV1(call_id=auth.call_id, packet_sha256=observed.packet_sha256),
    )
    provider = RulesProviderAuthorizedV1(
        event_id=uuid4(),
        sequence=2,
        kind="provider_authorized",
        matched_outputs=outputs,
        declared_support_refs=(ref,),
        **fields,
    )
    included = RulesProviderIncludedV1(
        event_id=uuid4(),
        sequence=3,
        kind="provider_included",
        matched_outputs=outputs,
        support_refs=(ref,),
        **fields,
    )
    outcome = RulesProviderOutcomeV1(
        event_id=uuid4(),
        sequence=4,
        kind="provider_outcome",
        status="answered",
        **fields,
    )
    with psycopg.connect(dsn) as conn:
        record = open_execution_locked(
            conn, scope, expected_turn_revision=turn.revision
        )
        for item in (auth, observed):
            record, _ = append_lookup_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=record.revision,
                event=item,
                raw_output=raw if item is observed else None,
                new_supports=(unit,) if item is observed else (),
            )
        for item in (provider, included, outcome):
            record, _ = append_provider_event_locked(
                conn,
                scope,
                expected_turn_revision=turn.revision,
                expected_ledger_revision=record.revision,
                event=item,
                prepared_request_json=body if item is not outcome else None,
            )
    composition = AnswerCompositionV1.model_validate_json(
        json.dumps(
            dict(
                schema="dmb_answer_composition_v1",
                base_disposition="absent",
                ordered_refs=[dict(domain="rules", segment_index=0)],
                rules_segments=[
                    dict(
                        kind="rules_claim",
                        claim_id="occupancy",
                        text=unit.excerpt_text,
                        support_refs=[reference],
                    )
                ],
                assistant_text_sha256=hashed(unit.excerpt_text),
            )
        )
    )
    return turn, MixedTurnResultV1(
        schema="dmb_mixed_turn_result_v1",
        scope=scope,
        expected_turn_revision=turn.revision,
        expected_rules_revision=record.revision,
        assistant_text=unit.excerpt_text,
        composition=composition,
        producing_provider_attempt_id=producer,
        base_result=None,
    )


def persisted(dsn, turn):
    with psycopg.connect(dsn) as conn:
        owner = conn.execute(
            "SELECT status,revision,assistant_text,answer_composition_kind,completion,graph_context_execution,claim_expires_at FROM agent.turn WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()
        ledger = conn.execute(
            "SELECT revision,payload,accepted_binding,accepted_binding_sha256 FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",
            (turn.turn_id, turn.attempt),
        ).fetchone()
    return owner, ledger


def test_native_mixed_result_keeps_output_proof_separate_and_scope_bound(application_state_dsn):
    _, result = ready_rules(application_state_dsn)
    request = "{\"messages\":[]}"
    raw = "{\"schema\":\"dmb_rules_mixed_answer_v1\"}"
    proof = NativeRulesOutputProofV1(
        schema="dmb_native_rules_output_proof_v1",
        policy="exact_producer_composition_v1",
        rules_execution_id=result.scope.execution_id,
        producing_provider_attempt_id=result.producing_provider_attempt_id,
        request_envelope_sha256=hashed(request),
        authorization_id="host:authorized:1",
        api_request_id="api-request-1",
        prepared_request_json=request,
        raw_output_json=raw,
        raw_output_sha256=hashed(raw),
        raw_output_utf8_bytes=len(raw.encode("utf-8")),
    )
    native_composition = result.composition.model_copy(
        update={"base_disposition": "unclaimed"}
    )
    native = NativeRulesMixedTurnResultV1(
        schema="dmb_native_rules_mixed_turn_result_v1",
        scope=result.scope,
        expected_turn_revision=result.expected_turn_revision,
        expected_rules_revision=result.expected_rules_revision,
        assistant_text=result.assistant_text,
        composition=native_composition,
        producing_provider_attempt_id=result.producing_provider_attempt_id,
        base_result=None,
        output_proof=proof,
    )

    assert NativeRulesMixedTurnResultV1.model_validate_json(
        native.model_dump_json(by_alias=True)
    ) == native
    with pytest.raises(ValueError, match="exact output proof"):
        NativeRulesMixedTurnResultV1.model_validate(
            native.model_dump(mode="python", by_alias=True)
            | {"output_proof": proof.model_copy(update={"rules_execution_id": uuid4()})}
        )


def test_rules_only_completion_is_atomic_and_replays_without_a_live_claim(
    application_state_dsn,
):
    turn, result = ready_rules(application_state_dsn)
    service = AgentConversationService()
    completed = service.complete_mixed_turn(result)
    assert (
        isinstance(completed, MixedCompletedTurnV1)
        and completed.base_projection.kind == "absent"
    )
    assert (
        completed.assistant_text == result.assistant_text
        and len(completed.accepted_binding.support_table) == 1
    )
    state = persisted(application_state_dsn, turn)
    assert state[0][:4] == (
        "completed",
        turn.revision + 1,
        result.assistant_text,
        "rules_mixed_v1",
    )
    assert (
        state[1][0] == result.expected_rules_revision + 1
        and state[1][1]["state"] == "accepted"
    )
    assert service.complete_mixed_turn(result) == completed
    assert persisted(application_state_dsn, turn) == state
    assert (
        service.claim_turn(
            turn.world_id,
            turn.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
        ).turn
        == completed
    )
    changed = result.model_dump(mode="json", by_alias=True)
    changed["expected_rules_revision"] -= 1
    with pytest.raises(ApplicationStateConflictError):
        service.complete_mixed_turn(
            MixedTurnResultV1.model_validate_json(json.dumps(changed))
        )


def test_mixed_commit_rolls_back_after_real_turn_and_rules_writes(
    application_state_dsn, monkeypatch
):
    turn, result = ready_rules(application_state_dsn)
    before = persisted(application_state_dsn, turn)
    actual = repo.complete_mixed_claimed_turn

    def crash_after_writes(*args, **kwargs):
        completed = actual(*args, **kwargs)
        assert isinstance(completed, MixedCompletedTurnV1)
        raise RuntimeError("injected crash after actual mixed writes")

    monkeypatch.setattr(repo, "complete_mixed_claimed_turn", crash_after_writes)
    with pytest.raises(RuntimeError, match="injected crash"):
        AgentConversationService().complete_mixed_turn(result)
    assert persisted(application_state_dsn, turn) == before


def test_lost_turn_cas_rolls_back_the_preceding_rules_acceptance(
    application_state_dsn, monkeypatch
):
    from application_state.agent_conversation import rules_authority_store as store

    turn, result = ready_rules(application_state_dsn)
    before = persisted(application_state_dsn, turn)
    actual = store.persist_accepted_locked

    def expire_after_rules_write(conn, *args, **kwargs):
        actual(conn, *args, **kwargs)
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )

    monkeypatch.setattr(store, "persist_accepted_locked", expire_after_rules_write)
    with pytest.raises(ApplicationStateConflictError):
        AgentConversationService().complete_mixed_turn(result)
    assert persisted(application_state_dsn, turn) == before


def test_unknown_rules_producer_cannot_accept_a_cited_answer(application_state_dsn):
    turn, result = ready_rules(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        row = conn.execute(
            "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()[0]
        row["events"][-1]["status"] = "unknown"
        value = RulesExecutionV1.model_validate_json(json.dumps(row))
        conn.execute(
            "UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s",
            (Jsonb(value.model_dump(mode="json", by_alias=True)), turn.turn_id),
        )
    before = persisted(application_state_dsn, turn)
    with pytest.raises(ApplicationStateValidationError):
        AgentConversationService().complete_mixed_turn(result)
    assert persisted(application_state_dsn, turn) == before


def test_used_rules_cannot_complete_as_plain_text_and_failure_retains_evidence(
    application_state_dsn,
):
    turn, result = ready_rules(application_state_dsn)
    service = AgentConversationService()
    before = persisted(application_state_dsn, turn)
    with pytest.raises(ApplicationStateValidationError, match="mixed finalization"):
        service.complete_turn(
            TurnResult(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                assistant_text="Unattributed answer.",
            )
        )
    assert persisted(application_state_dsn, turn) == before
    failed = service.fail_turn(
        TurnFailure(
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            expected_revision=turn.revision,
            failure_code="cancelled",
        )
    )
    owner, ledger = persisted(application_state_dsn, turn)
    assert (
        failed.status == "failed"
        and owner[3] == "base"
        and ledger[1]["state"] == "failed"
    )
    assert ledger[1]["supports"] == before[1][1]["supports"] and ledger[2] is None


def test_unused_rules_scope_closes_with_ordinary_completion_in_one_transaction(
    application_state_dsn,
):
    turn, scope = admitted()
    with psycopg.connect(application_state_dsn) as conn:
        open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
    completed = AgentConversationService().complete_turn(
        TurnResult(
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            expected_revision=turn.revision,
            assistant_text="No lookup needed.",
        )
    )
    owner, ledger = persisted(application_state_dsn, turn)
    assert (
        completed.assistant_text == "No lookup needed."
        and owner[3] == "base"
        and ledger[1]["state"] == "unused"
    )


def join_graph_provider(dsn, service, turn, result):
    from tests.application_state.test_agent_conversation_postgres import (
        _provider_authorization_event,
    )
    from application_state.agent_conversation.types import (
        ProviderOutcomeEventV1,
        ProviderAttemptAuthorizedEventV2,
        PlanWorldGraphExecutionV2,
    )

    # The final Rules event and final Graph event name the identical raw request.
    with psycopg.connect(dsn) as conn:
        ledger = conn.execute(
            "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()[0]
    envelope = next(
        item["request_envelope_sha256"]
        for item in ledger["events"]
        if item["kind"] == "provider_authorized"
    )
    for producer, digest in [
        (uuid4(), "c" * 64),
        (result.producing_provider_attempt_id, envelope),
    ]:
        auth = _provider_authorization_event(
            attempt_id=producer, sequence=len(turn.graph_context_execution.events)
        ).model_copy(update={"envelope_sha256": digest})
        if isinstance(turn.graph_context_execution, PlanWorldGraphExecutionV2):
            auth = ProviderAttemptAuthorizedEventV2.model_validate(
                auth.model_dump(mode="python")
                | {
                    "kind": "provider_attempt_authorized_v2",
                    "included_source_read_event_ids": [],
                }
            )
            turn, _ = service.authorize_provider_attempt_v2(
                turn.world_id,
                turn.conversation_id,
                turn.turn_id,
                expected_revision=turn.revision,
                expected_attempt=turn.attempt,
                provider_attempt_event=auth,
            )
        else:
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
                    provider_attempt_id=producer,
                    outcome=state,
                ),
            )
    return turn


def test_real_plan_graph_enabled_rules_only_completion_is_unclaimed(
    application_state_dsn,
):
    from tests.application_state.test_agent_conversation_postgres import (
        _accepted_execution_turn,
    )

    service = AgentConversationService()
    _, _, _, turn = _accepted_execution_turn(service, "mixed-plan-completion-world")
    turn, result = ready_rules(application_state_dsn, turn)
    turn = join_graph_provider(application_state_dsn, service, turn, result)
    fields = result.model_dump(mode="json", by_alias=True)
    fields["expected_turn_revision"] = turn.revision
    fields["composition"]["base_disposition"] = "unclaimed"
    result = MixedTurnResultV1.model_validate_json(json.dumps(fields))
    completed = service.complete_mixed_turn(result)
    assert (
        completed.base_projection.kind == "unclaimed"
        and not completed.accepted_binding.graph_used
    )
    assert len(completed.base_projection.graph_context_execution.events) == 6
    pairs = service.list_completed_plan_ask_context(
        turn.world_id, turn.graph_context_receipt.plan_basis
    )
    assert (
        pairs[0].answer == result.assistant_text
        and pairs[0].history_attribution.base_attribution is None
    )
    assert service.complete_mixed_turn(result) == completed


def ready_build_mixed(dsn):
    from tests.application_state.test_build_graph_turns import (
        _accept_claim,
        _completion,
    )

    service = AgentConversationService()
    submission, turn = _accept_claim(service)
    turn, result = ready_rules(dsn, turn)
    turn = join_graph_provider(dsn, service, turn, result)
    base_completion = _completion(submission)
    base_text = "\n".join(item.text for item in base_completion.answer_segments)
    base_result = TurnResult(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        expected_revision=turn.revision,
        assistant_text=base_text,
        completion=base_completion,
        producing_provider_attempt_id=result.producing_provider_attempt_id,
        claim_graph_event_ids={},
    )
    fields = result.model_dump(mode="json", by_alias=True)
    fields["expected_turn_revision"] = turn.revision
    fields["base_result"] = base_result.model_dump(mode="json", by_alias=True)
    fields["assistant_text"] = base_text + "\n" + result.assistant_text
    fields["composition"].update(
        base_disposition="approved",
        ordered_refs=[
            dict(domain="base", segment_index=0),
            dict(domain="rules", segment_index=0),
        ],
        assistant_text_sha256=hashed(fields["assistant_text"]),
    )
    result = MixedTurnResultV1.model_validate_json(json.dumps(fields))
    return turn, result, base_completion


@pytest.mark.parametrize("crash", [False, True])
def test_real_build_mixed_completion_validates_and_stores_exact_base_subsequence(
    application_state_dsn,
    monkeypatch,
    crash,
):
    service = AgentConversationService()
    turn, result, base_completion = ready_build_mixed(application_state_dsn)
    base_text = "\n".join(item.text for item in base_completion.answer_segments)
    if crash:
        before = persisted(application_state_dsn, turn)
        actual = repo.complete_mixed_claimed_turn

        def crash_after_base_and_rules(*args, **kwargs):
            completed = actual(*args, **kwargs)
            assert completed.base_projection.turn.completion == base_completion
            raise RuntimeError("injected crash after Build and Rules writes")

        monkeypatch.setattr(
            repo, "complete_mixed_claimed_turn", crash_after_base_and_rules
        )
        with pytest.raises(RuntimeError, match="injected crash"):
            service.complete_mixed_turn(result)
        assert persisted(application_state_dsn, turn) == before
        return
    completed = service.complete_mixed_turn(result)
    assert (
        completed.base_projection.kind == "approved"
        and completed.base_projection.turn.assistant_text == base_text
    )
    assert (
        completed.base_projection.turn.completion == base_completion
        and completed.assistant_text == result.assistant_text
    )
    assert (
        service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id) == completed
    )
    assert service.complete_mixed_turn(result) == completed


def test_unused_closure_rolls_back_when_ordinary_turn_claim_expired(
    application_state_dsn,
):
    turn, scope = admitted()
    with psycopg.connect(application_state_dsn) as conn:
        open_execution_locked(conn, scope, expected_turn_revision=turn.revision)
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    before = persisted(application_state_dsn, turn)
    with pytest.raises(ApplicationStateConflictError):
        AgentConversationService().complete_turn(
            TurnResult(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                assistant_text="No lookup.",
            )
        )
    assert persisted(application_state_dsn, turn) == before


def test_completed_replay_does_not_reread_full_rules_ledger(
    application_state_dsn, monkeypatch
):
    from application_state.agent_conversation import rules_authority_store as store

    turn, result = ready_rules(application_state_dsn)
    service = AgentConversationService()
    completed = service.complete_mixed_turn(result)

    def reject_source_read(*args, **kwargs):
        raise AssertionError("completed replay must not load source-bearing ledger")

    monkeypatch.setattr(store, "load_turn_rules_locked", reject_source_read)
    assert service.complete_mixed_turn(result) == completed


@pytest.mark.parametrize("field", ["expected_turn_revision", "expected_rules_revision"])
def test_both_completion_cas_revisions_are_required(application_state_dsn, field):
    turn, result = ready_rules(application_state_dsn)
    before = persisted(application_state_dsn, turn)
    fields = result.model_dump(mode="json", by_alias=True)
    fields[field] -= 1
    with pytest.raises(ApplicationStateConflictError):
        AgentConversationService().complete_mixed_turn(
            MixedTurnResultV1.model_validate_json(json.dumps(fields))
        )
    assert persisted(application_state_dsn, turn) == before


def test_mixed_acceptance_receipt_and_reconcile_keep_the_exact_completed_record(
    application_state_dsn,
):
    from application_state.agent_conversation.types import (
        TurnSubmission,
        SubmittedTurnIntentV1,
        SubmittedGraphRequestIntentV1,
    )

    turn, result = ready_rules(application_state_dsn)
    service = AgentConversationService()
    completed = service.complete_mixed_turn(result)
    intent = SubmittedTurnIntentV1(
        world_id=turn.world_id,
        client_thread_id="rules-store-thread",
        message=turn.user_text,
        surface_id="index",
        surface_instance_id="rules-store",
        client_work_state="none",
        primary_work=None,
        graph_request=SubmittedGraphRequestIntentV1(mode="none"),
        graph_selection=None,
    )
    submission = TurnSubmission(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        idempotency_key=turn.idempotency_key,
        expected_conversation_revision=1,
        user_text=turn.user_text,
        provenance=turn.provenance,
        submitted_intent_v1=intent,
    )
    assert service.accept_turn(submission) == completed
    assert (
        service.reconcile_turn(
            world_id=turn.world_id,
            idempotency_key=turn.idempotency_key,
            submitted_intent=intent,
        )
        == completed
    )
    assert (
        persisted(application_state_dsn, turn)[1][0]
        == result.expected_rules_revision + 1
    )
