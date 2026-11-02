"""Shared captured output acceptance through real SDK, claim, Rules and read owners."""

from datetime import datetime, timezone
import json
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.context_trace import (
    TraceContextSnapshot,
    TraceContextMaterial,
)
from application_state.agent_conversation.native_rules_output import (
    NativeRulesOutputProofV1,
    normalize_shared_native_output,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesNativeProviderOutcomeV1,
)
from application_state.agent_conversation.rules_authority_completion import (
    NativeRulesMixedTurnResultV1,
    prepare_rules_acceptance,
)
from application_state.agent_conversation.rules_authority_reads import (
    MixedCompletedTurnV1,
    CompletedTurnEnvelopeV1,
)
from application_state.errors import (
    ApplicationStateValidationError,
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
)
from apps.live_control_server.services.native_rules_capture import NativeProviderReply
from tests.application_state.test_surface_native_writers import (
    prepared_case,
    run_writer,
    snapshot,
    digest,
)
from tests.test_surface_native_execution import execution


def completed_input(dsn, *, used=False, base=True, acquired=None, answer_rows=None):
    case = prepared_case(dsn, used=used, acquired=acquired)
    candidate = json.loads(case.output)
    selection = next(
        b["selection_id"]
        for b in case.work_frame["committed_plan_blocks"]
        if b.get("selection_id")
    )
    authored = {"kind": "authored_excerpt", "selection_id": selection}
    rows = answer_rows(case) if answer_rows is not None else [authored]
    if used:
        candidate["base_output"]["answer_segments"] = rows
        if not base:
            candidate["base_output"] = None
            candidate["ordered_refs"] = [
                r for r in candidate["ordered_refs"] if r["domain"] != "base"
            ]
    else:
        candidate["answer_segments"] = rows
    case.output = json.dumps(candidate)
    run_writer(case)
    case.capture = NativeProviderReply(
        str(case.scope.authorization_id),
        f"generationengine:{case.auth.provider_attempt_id}",
        case.auth.provider,
        case.auth.model,
        case.auth.api_mode,
        case.auth.envelope_sha256,
        "stop",
        "answered",
        case.selected,
        digest(case.selected),
        len(case.selected.encode()),
        (),
    )
    case.rules = case.service.append_rules_provider_event(
        case.scope,
        expected_turn_revision=case.turn.revision,
        expected_ledger_revision=case.rules.revision,
        event=RulesNativeProviderOutcomeV1.from_capture(
            case.capture,
            event_id=uuid4(),
            sequence=len(case.rules.execution.events),
            execution_id=case.scope.execution_id,
            provider_attempt_id=case.auth.provider_attempt_id,
            request_envelope_sha256=case.auth.envelope_sha256,
        ),
    )
    case.proof = NativeRulesOutputProofV1.from_capture(
        case.capture,
        prepared_request_json=case.prepared.body.decode(),
        rules_execution_id=case.scope.execution_id,
        producing_provider_attempt_id=case.auth.provider_attempt_id,
    )
    case.service.append_context_trace(
        world_id=case.turn.world_id,
        conversation_id=case.turn.conversation_id,
        turn_id=case.turn.turn_id,
        expected_revision=case.turn.revision,
        attempt=case.turn.attempt,
        trace_id=case.trace_id,
        observation=TraceContextSnapshot(
            sequence=len(case.steps),
            elapsed_ms=1,
            stage="after",
            materials=[
                TraceContextMaterial(
                    item_id=f"unvalidated-provider-answer:{case.auth.provider_attempt_id}:{case.turn.graph_context_receipt.context_receipt_sha256}",
                    state="model_context",
                    role="assistant",
                    text=case.selected,
                )
            ],
        ),
    )
    case.trace = case.service.list_context_trace_attempts(
        world_id=case.turn.world_id, turn_id=case.turn.turn_id
    )[0].model_dump(mode="json")
    case.normalized = normalize_shared_native_output(
        case.turn.graph_context_receipt,
        case.turn.graph_context_execution,
        case.rules.execution,
        case.proof,
        case.capture,
        trace=case.trace,
        idempotency_key=case.turn.idempotency_key,
        submitted_intent_fingerprint=case.turn.submitted_intent_fingerprint_v2,
        world_id=case.turn.world_id,
        conversation_id=case.turn.conversation_id,
        turn_id=case.turn.turn_id,
        attempt=case.turn.attempt,
        provenance=case.turn.provenance,
        work_proof=case.work_proof,
    )
    case.result = None
    if base:
        case.result = t.TurnResult(
            world_id=case.turn.world_id,
            conversation_id=case.turn.conversation_id,
            turn_id=case.turn.turn_id,
            expected_revision=case.turn.revision,
            assistant_text="\n".join(
                s.text for s in case.normalized.base_completion.answer_segments
            ),
            completion=case.normalized.base_completion,
            producing_provider_attempt_id=case.auth.provider_attempt_id,
            claim_graph_event_ids={},
        )
    if used:
        case.result = NativeRulesMixedTurnResultV1(
            schema="dmb_native_rules_mixed_turn_result_v1",
            scope=case.scope,
            expected_turn_revision=case.turn.revision,
            expected_rules_revision=case.rules.revision,
            assistant_text=case.normalized.assistant_text,
            composition=case.normalized.composition,
            producing_provider_attempt_id=case.auth.provider_attempt_id,
            base_result=case.result,
            output_proof=case.proof,
        )
    return case


def finish(case, *, work_proof=None):
    work = case.work_proof if work_proof is None else work_proof
    if isinstance(case.result, NativeRulesMixedTurnResultV1):
        return case.service.complete_mixed_turn(case.result, work_proof=work)
    return case.service.complete_native_base_turn(
        case.result,
        output_proof=case.proof,
        expected_rules_revision=case.rules.revision,
        work_proof=work,
    )


@pytest.mark.parametrize("used,base", [(False, True), (True, True), (True, False)])
def test_actual_native_sdk_output_is_accepted_reloaded_and_replayed(
    application_state_dsn, used, base
):
    case = completed_input(application_state_dsn, used=used, base=base)
    completed = finish(case)
    assert completed.assistant_text == case.normalized.assistant_text
    if used:
        from apps.live_control_server.services.rules_answer_presentation import project_rules_answer_context
        projected=project_rules_answer_context(completed,delivery_replay=True)
        assert (projected.base_context is not None) == base
        assert (projected.unclaimed_context is not None) != base
        projected.validate_answer(completed.assistant_text)
    assert finish(case) == completed and len(case.writer_calls) == 1
    assert (
        AgentConversationService().inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )
        == completed
    )
    assert AgentConversationService().list_turns(
        case.turn.world_id, case.turn.conversation_id
    ) == [completed]
    actual = (
        completed.base_projection.turn
        if used and base
        else completed
        if not used
        else None
    )
    if actual is not None:
        assert actual.completion == case.normalized.base_completion
        assert (
            actual.completion.answer_segments[0].object_id
            == case.turn.provenance.primary_work.object_id
        )
        assert actual.graph_context_execution.events[
            -1
        ].completion_sha256 == t.canonical_sha256(actual.completion)
    else:
        assert completed.base_projection.kind == "unclaimed"
        assert completed.base_projection.completion is None


@pytest.mark.parametrize(
    "mutation",
    [
        "work",
        "output",
        "trace",
        "outcome",
        "result",
        "no_proof",
        "rules_revision",
        "claim",
        "turn_cas",
    ],
)
def test_failed_native_acceptance_cannot_change_either_ledger(
    application_state_dsn, monkeypatch, mutation
):
    case = completed_input(application_state_dsn)
    if mutation == "work":
        case.work_proof = dict(case.work_proof, plan_markdown="Foreign body")
    elif mutation == "output":
        case.proof = case.proof.model_copy(
            update={"raw_output_json": case.proof.raw_output_json + " "}
        )
    elif mutation == "result":
        case.result = case.result.model_copy(update={"assistant_text": "Forged result"})
    elif mutation == "rules_revision":
        case.rules = case.rules.model_copy(update={"revision": case.rules.revision + 1})
    elif mutation in {"trace", "outcome", "claim"}:
        with psycopg.connect(case.dsn) as conn:
            if mutation == "trace":
                conn.execute(
                    "UPDATE agent.turn_context_trace SET payload=jsonb_set(payload,'{observations}',%s) WHERE turn_id=%s",
                    (Jsonb([]), case.turn.turn_id),
                )
            elif mutation == "outcome":
                payload = case.rules.execution.model_dump(mode="json", by_alias=True)
                payload["events"][-1]["output_sha256"] = "a" * 64
                conn.execute(
                    "UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s",
                    (Jsonb(payload), case.turn.turn_id),
                )
            else:
                conn.execute(
                    "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
                    (case.turn.turn_id,),
                )
    elif mutation == "turn_cas":
        from application_state.agent_conversation import repository

        monkeypatch.setattr(repository, "complete_claimed_turn", lambda *a, **k: None)
    before = snapshot(case)
    with pytest.raises(
        (
            ApplicationStateValidationError,
            ApplicationStateConflictError,
            ApplicationStateIntegrityError,
        )
    ):
        if mutation == "no_proof":
            case.service.complete_turn(case.result)
        else:
            finish(case)
    assert snapshot(case) == before and len(case.writer_calls) == 1


def test_retained_native_authored_owner_cannot_be_rebound(application_state_dsn):
    case = completed_input(application_state_dsn)
    completed = finish(case)
    completion = completed.completion.model_dump(mode="json", by_alias=True)
    completion["answer_segments"][0]["object_id"] = "foreign-plan"
    graph = completed.graph_context_execution.model_dump(mode="json", by_alias=True)
    graph["events"][-1]["completion_sha256"] = t.canonical_sha256(completion)
    with psycopg.connect(case.dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET completion=%s,graph_context_execution=%s WHERE turn_id=%s",
            (Jsonb(completion), Jsonb(graph), case.turn.turn_id),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )


def test_object_only_mixed_native_review_remains_typed_without_approved_text():
    # Component/read boundary: Build controller activation is a separate gate.
    from tests.test_surface_native_collaboration import case as review_case, output
    from tests.test_surface_native_rules import producing_case, normalize
    from application_state.agent_conversation.native_writer import model_work_frame

    context, ledger, work = review_case("questions")
    frame = model_work_frame(context, ledger, **work)
    produced = producing_case(
        None,
        "build",
        context_record=(context, ledger),
        work_override=work,
        candidate_mutation=lambda candidate: candidate.update(
            base_output=output(frame)
        ),
    )
    context, ledger, rules, auth, proof, _capture, _kwargs = produced
    normalized = normalize(produced)
    assert normalized.composition.base_disposition == "unclaimed"
    result = t.TurnResult(
        world_id=work["world_id"],
        conversation_id=work["conversation_id"],
        turn_id=work["turn_id"],
        expected_revision=8,
        assistant_text="",
        completion=normalized.base_completion,
        producing_provider_attempt_id=auth.provider_attempt_id,
        claim_graph_event_ids={},
    )
    mixed = NativeRulesMixedTurnResultV1(
        schema="dmb_native_rules_mixed_turn_result_v1",
        scope=rules.scope,
        expected_turn_revision=8,
        expected_rules_revision=5,
        assistant_text=normalized.assistant_text,
        composition=normalized.composition,
        producing_provider_attempt_id=auth.provider_attempt_id,
        base_result=result,
        output_proof=proof,
    )
    _, binding = prepare_rules_acceptance(
        rules,
        normalized.composition,
        producing_provider_attempt_id=auth.provider_attempt_id,
        accepted_turn_revision=9,
        event_id=uuid4(),
    )
    event = t.CompletionBindingEventV1(
        kind="completion_binding",
        event_id=uuid4(),
        sequence=len(ledger.events),
        provider_attempt_id=auth.provider_attempt_id,
        completion_sha256=t.canonical_sha256(result.completion),
        claim_graph_event_ids={},
    )
    ledger = execution(
        context.context_receipt_sha256, ledger.policy, [*ledger.events, event]
    )
    now = datetime.now(timezone.utc)
    envelope = CompletedTurnEnvelopeV1(
        turn_id=work["turn_id"],
        conversation_id=work["conversation_id"],
        world_id=work["world_id"],
        idempotency_key=work["idempotency_key"],
        sequence=1,
        revision=9,
        status="completed",
        user_text=ledger.policy.action.intent.message,
        failure_code=None,
        provenance=work["provenance"],
        submitted_intent_fingerprint_v1=None,
        submitted_intent_fingerprint_v2=t.submitted_turn_intent_fingerprint_v2(
            ledger.policy.action.intent
        ),
        play_context_receipt=None,
        attempt=1,
        claim_expires_at=None,
        accepted_at=now,
        completed_at=now,
        updated_at=now,
    )
    retained = MixedCompletedTurnV1(
        schema="dmb_mixed_completed_turn_v1",
        envelope=envelope,
        assistant_text=mixed.assistant_text,
        accepted_binding=binding,
        accepted_binding_sha256=t.canonical_sha256(binding),
        base_projection=dict(
            kind="unclaimed",
            graph_context_receipt=context,
            graph_context_execution=ledger,
            completion=result.completion,
        ),
    )
    assert (
        MixedCompletedTurnV1.model_validate_json(
            retained.model_dump_json(by_alias=True)
        )
        == retained
    )
    assert (
        retained.base_projection.completion.collaboration
        == result.completion.collaboration
    )
    assert retained.accepted_binding.base_disposition == "unclaimed"
    from apps.live_control_server.services.rules_answer_presentation import project_rules_answer_context
    projected=project_rules_answer_context(retained,delivery_replay=True)
    assert projected.base_context is None
    assert projected.unclaimed_context.completion == retained.base_projection.completion
    assert not projected.unclaimed_context.completion.answer_segments
    projected.validate_answer(retained.assistant_text)

    dropped = retained.model_dump(mode="json", by_alias=True)
    dropped["base_projection"]["completion"] = None
    with pytest.raises(ValueError, match="completion|binding"):
        MixedCompletedTurnV1.model_validate_json(json.dumps(dropped))

    changed = retained.model_dump(mode="json", by_alias=True)
    changed["envelope"]["user_text"] = "Different admitted question"
    with pytest.raises(ValueError, match="request"):
        MixedCompletedTurnV1.model_validate_json(json.dumps(changed))
