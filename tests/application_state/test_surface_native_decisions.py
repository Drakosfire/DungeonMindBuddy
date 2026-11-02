"""Actual shared Plan claim → TypeSafe SDK → protected selection; no network."""

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx2
import pytest
from generationengine import GenerationClient
from generationengine.decision_dispatch import DecisionDispatchGate
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.context_trace import (
    TraceContextSnapshot,
    TraceContextMaterial,
)
from application_state.agent_conversation.jev_retrieval_contract import (
    PlanSourceRetrievalDecisionInputV1,
    prepare_decision,
    decode_selection,
)
from application_state.agent_conversation.plan_authoring import (
    prepare_requested_work_decision,
    decode_requested_work_decision,
)
from application_state.agent_conversation.plan_placement import (
    PlanRequestedWorkInputV3,
    work_choice,
)
from application_state.agent_conversation.plan_jev_decision import (
    scope_digest,
    _source_pins,
)
from application_state.errors import (
    ApplicationStateValidationError,
    ApplicationStateConflictError,
)
from tests.application_state.test_agent_conversation_postgres import _new
from tests.test_surface_native_context import provenance_for, seal
from tests.test_surface_native_execution import component, execution


def digest(raw):
    return sha256(raw.encode()).hexdigest()


def append(case, **updates):
    step = case.steps[-1]
    params = dict(
        expected_revision=case.turn.revision,
        expected_attempt=case.turn.attempt,
        selection=step.selection,
        producer_proof=step.proof,
    )
    method = (
        case.service.record_plan_requested_work_selection
        if step.semantic
        else case.service.record_plan_jev_retrieval_selection
    )
    case.turn, fresh = method(
        case.turn.world_id,
        case.turn.conversation_id,
        case.turn.turn_id,
        **(params | updates),
    )
    return fresh


def sdk_case(
    dsn,
    *,
    unavailable=False,
    capture=True,
    unknown=False,
    acquisitions=(),
    context_record=None,
    question=None,
):
    context, ledger = (
        context_record
        if context_record is not None
        else component("plan", unavailable=unavailable)
    )
    if question is not None:
        wire = context.model_dump(mode="json", by_alias=True)
        if "question" in wire["native_query"]:
            wire["native_query"]["question"] = question
        context = type(context).model_validate_json(json.dumps(seal(wire)))
        action = ledger.policy.action.model_copy(
            update={
                "intent": ledger.policy.action.intent.model_copy(
                    update={"message": question}
                )
            }
        )
        ledger = execution(
            context.context_receipt_sha256,
            ledger.policy.model_copy(
                update={
                    "action": action,
                    "native_query_sha256": t.canonical_sha256(context.native_query),
                }
            ),
        )
    case = SimpleNamespace(
        dsn=dsn, service=AgentConversationService(), sent=[], steps=[], trace_id=uuid4()
    )
    for phase, semantic in enumerate((True, *([False] * (len(acquisitions) + 1)))):
        common = dict(
            request_id=uuid4(),
            parent_attempt_id=uuid4(),
            scope_sha256="0" * 64,
            question=ledger.policy.action.intent.message,
        )
        if semantic:
            parent = PlanRequestedWorkInputV3(
                **common,
                page_title="Synthetic Plan",
                target_available=False,
                target_capture_sha256=None,
                placement_catalog=None,
                original_capture=None,
            )
            prepare = prepare_requested_work_decision
        else:
            parent = PlanSourceRetrievalDecisionInputV1(
                **common,
                **_source_pins(case.turn.graph_context_receipt),
                candidates=tuple(acquisitions[phase - 1][0](case))
                if 0 < phase <= len(acquisitions)
                else (),
                allowed_operations=("select_candidates", "finish_retrieval"),
            )
            prepare = prepare_decision
        step = SimpleNamespace(parent=parent, semantic=semantic)

        async def authorize(prepared):
            from apps.live_control_server.services.agent_turn_service import (
                _json_node_count,
            )

            count = len(prepared.body) + 64 * (
                1 + _json_node_count(json.loads(prepared.body))
            )
            accounting = t.GraphExecutionAccountingV1(
                kind="conservative_upper_bound",
                estimator="utf8_json_bytes_plus_64_per_node_v1",
            )
            if semantic:
                # Freeze the actual SDK body BEFORE APP admission and claim.
                wire = context.model_dump(mode="json", by_alias=True)
                wire["assembled_input"].update(
                    assembled_input_sha256=prepared.body_sha256,
                    provider_envelope_input_tokens=count,
                    output_token_reserve=200,
                    context_window_limit=128000,
                    tokenizer_name=accounting.estimator,
                )
                admitted_context = type(context).model_validate_json(
                    json.dumps(seal(wire))
                )
                policy = ledger.policy.model_copy(
                    update={"provider_input_accounting": accounting}
                )
                admitted_execution = execution(
                    admitted_context.context_receipt_sha256, policy
                )
                intent = policy.action.intent
                provenance = provenance_for(admitted_context.work_context).model_copy(
                    update={"surface_instance_id": intent.surface_instance_id}
                )
                conversation = _new(case.service, intent.world_id)
                case.submission = t.TurnSubmission(
                    world_id=intent.world_id,
                    conversation_id=conversation.conversation_id,
                    idempotency_key=uuid4(),
                    expected_conversation_revision=1,
                    user_text=intent.message,
                    provenance=provenance,
                    submitted_intent_v2=intent,
                    graph_context_receipt=admitted_context,
                    graph_context_execution=admitted_execution,
                )
                accepted = case.service.accept_turn(case.submission)
                case.turn = case.service.claim_turn(
                    accepted.world_id,
                    accepted.conversation_id,
                    accepted.turn_id,
                    expected_revision=accepted.revision,
                ).turn
                case.service.start_context_trace(
                    world_id=case.turn.world_id,
                    conversation_id=case.turn.conversation_id,
                    turn_id=case.turn.turn_id,
                    expected_revision=case.turn.revision,
                    attempt=case.turn.attempt,
                    trace_id=case.trace_id,
                    started_at=datetime.now(UTC),
                )
            step.parent = parent.model_copy(
                update={
                    "parent_attempt_id": UUID(prepared.attempt_id),
                    "scope_sha256": scope_digest(case.turn),
                }
            )
            cls = (
                t.PlanRequestedWorkAuthorizedV2
                if semantic
                else t.PlanJevProviderAuthorizedV1
            )
            step.auth = cls(
                kind="plan_requested_work_authorized_v2"
                if semantic
                else "plan_jev_provider_authorized_v1",
                event_id=uuid4(),
                sequence=len(case.turn.graph_context_execution.events),
                provider_attempt_id=UUID(prepared.attempt_id),
                envelope_sha256=prepared.body_sha256,
                serializer_version="typesafe-sdk-json-v1",
                provider="typesafe",
                model="jev-1.14.0",
                api_mode="decision",
                tool_schema_sha256=digest("[]"),
                input_accounting_kind=accounting.kind,
                input_estimator=accounting.estimator,
                input_tokens=count,
                output_token_reserve=200,
                included_assertion_ids=[],
                included_relationship_ids=[],
                included_evidence_ref_ids=[],
                included_graph_event_ids=[],
                included_source_read_event_ids=[],
                decision_request_id=step.parent.request_id,
                parent_request_sha256=step.parent.digest,
            )
            step.proof = dict(
                parent_request_json=step.parent.model_dump_json(by_alias=True),
                request_json=prepared.body.decode(),
            )
            case.turn, fresh = case.service.authorize_plan_jev_provider(
                case.turn.world_id,
                case.turn.conversation_id,
                case.turn.turn_id,
                expected_revision=case.turn.revision,
                expected_attempt=case.turn.attempt,
                authorization=step.auth,
                producer_proof=step.proof,
            )
            assert fresh
            assert (
                AgentConversationService().inspect_turn(
                    world_id=case.turn.world_id, turn_id=case.turn.turn_id
                )
                == case.turn
            )
            return True

        async def record(event):
            transition = (
                "sdk_entered"
                if event.outcome == "sending"
                else "outcome_unknown"
                if unknown and not semantic
                else event.outcome
            )
            outcome = t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(case.turn.graph_context_execution.events),
                provider_attempt_id=UUID(event.request.attempt_id),
                outcome=transition,
            )
            case.turn, fresh = case.service.record_provider_outcome(
                case.turn.world_id,
                case.turn.conversation_id,
                case.turn.turn_id,
                expected_revision=case.turn.revision,
                expected_attempt=case.turn.attempt,
                outcome=outcome,
            )
            assert fresh
            return True

        class Wire(httpx2.AsyncBaseTransport):
            async def handle_async_request(self, request):
                case.sent.append(request)
                assert request.content == step.proof["request_json"].encode()
                body = json.loads(request.content)
                assert not {"scope_sha256", "request_id", "parent_attempt_id"} & set(
                    body["state"]
                )
                answers = {}
                for name, question in body["questions"].items():
                    selected = (
                        "discuss"
                        if name == "requested_work"
                        else "include"
                        if 0 < phase <= len(acquisitions) and name != "operation"
                        else "finish_retrieval"
                    )
                    answers[name] = dict(
                        type="choice",
                        choice=selected,
                        confidence=1,
                        probabilities={
                            key: float(key == selected) for key in question["criteria"]
                        },
                    )
                return httpx2.Response(
                    200,
                    request=request,
                    json=dict(
                        model="jev-1.14.0",
                        answers=answers,
                        usage=dict(input_tokens=37, output_tokens=9),
                    ),
                )

        async def run():
            client = GenerationClient(
                decision_providers={
                    "typesafe": TypeSafeDecisionProvider(
                        api_key="synthetic-not-secret",
                        transport=Wire(),
                        dispatch_gate=DecisionDispatchGate(authorize, record),
                    )
                }
            )
            try:
                return await client.decide(prepare(parent))
            finally:
                await client.aclose()

        result = asyncio.run(run())
        raw = result.model_dump_json()
        step.proof |= dict(response_json=raw)
        fields = dict(
            event_id=uuid4(),
            sequence=len(case.turn.graph_context_execution.events),
            context_receipt_sha256=case.turn.graph_context_receipt.context_receipt_sha256,
            execution_policy_sha256=case.turn.graph_context_execution.execution_policy_sha256,
            decision_request_id=step.parent.request_id,
            controller_attempt_id=step.auth.provider_attempt_id,
            controller_envelope_sha256=step.auth.envelope_sha256,
            controller_response_sha256=digest(raw),
            parent_request_sha256=step.parent.digest,
            actual_input_tokens=result.observation.input_tokens,
            actual_output_tokens=result.observation.output_tokens,
        )
        if semantic:
            step.selection = t.PlanRequestedWorkSelectedV2(
                kind="plan_requested_work_selected_v2",
                **fields,
                **work_choice(
                    step.parent, decode_requested_work_decision(step.parent, result)
                ),
                original_capture_sha256=None,
                placement_catalog_sha256=None,
                original_capture=None,
                placement_catalog=None,
            )
        else:
            choice = decode_selection(step.parent, result)
            step.selection = t.PlanJevRetrievalSelectionV1(
                kind="plan_jev_retrieval_selected_v1",
                **fields,
                operation=choice.operation,
                selected_handles=list(choice.selected_handles),
            )
        if semantic or capture:
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
                            item_id=f"unvalidated-plan-jev-result:{step.auth.provider_attempt_id}",
                            state="model_context",
                            role="fact",
                            text=raw,
                        )
                    ],
                ),
            )
        case.steps.append(step)
        if semantic or 0 < phase <= len(acquisitions):
            assert append(case)
            if not semantic:
                acquisitions[phase - 1][1](case)
    return case


@pytest.mark.parametrize("unavailable", [False, True])
def test_actual_shared_plan_sdk_selection_reload_and_no_resend(
    application_state_dsn, unavailable
):
    case = sdk_case(application_state_dsn, unavailable=unavailable)
    assert append(case)
    assert not append(case)
    step = case.steps[-1]
    replay, fresh = case.service.authorize_plan_jev_provider(
        case.turn.world_id,
        case.turn.conversation_id,
        case.turn.turn_id,
        expected_revision=case.turn.revision,
        expected_attempt=case.turn.attempt,
        authorization=step.auth,
        producer_proof={
            key: step.proof[key] for key in ("parent_request_json", "request_json")
        },
    )
    assert not fresh and replay == case.turn and len(case.sent) == 2
    assert AgentConversationService().list_turns(
        case.turn.world_id, case.turn.conversation_id
    ) == [case.turn]
    assert not hasattr(case.turn.graph_context_receipt, "graph_authority")


@pytest.mark.parametrize(
    "mutation",
    [
        "parent",
        "wire",
        "scope",
        "response",
        "usage",
        "handles",
        "stale",
        "missing_capture",
        "unknown",
    ],
)
def test_shared_selection_refuses_changed_or_unacknowledged_proof_without_appending(
    application_state_dsn, mutation
):
    case = sdk_case(
        application_state_dsn,
        capture=mutation != "missing_capture",
        unknown=mutation == "unknown",
    )
    before = case.turn
    proof = dict(case.steps[-1].proof)
    selection = case.steps[-1].selection
    params = {}
    if mutation == "parent":
        proof["parent_request_json"] = (
            case.steps[-1]
            .parent.model_copy(update={"request_id": uuid4()})
            .model_dump_json(by_alias=True)
        )
    elif mutation == "wire":
        proof["request_json"] += " "
    elif mutation == "scope":
        proof["parent_request_json"] = (
            case.steps[-1]
            .parent.model_copy(update={"scope_sha256": "f" * 64})
            .model_dump_json(by_alias=True)
        )
    elif mutation == "response":
        proof["response_json"] += " "
    elif mutation == "usage":
        selection = selection.model_copy(update={"actual_input_tokens": 0})
    elif mutation == "handles":
        selection = selection.model_copy(update={"selected_handles": ["foreign"]})
    elif mutation == "stale":
        params["expected_revision"] = before.revision - 1
    with pytest.raises(
        (ApplicationStateValidationError, ApplicationStateConflictError)
    ):
        append(case, selection=selection, producer_proof=proof, **params)
    assert (
        AgentConversationService().inspect_turn(
            world_id=before.world_id, turn_id=before.turn_id
        )
        == before
    )
    assert len(case.sent) == 2


def test_native_plan_proof_cannot_authorize_another_actual_turn_or_generic_path(
    application_state_dsn,
):
    case = sdk_case(application_state_dsn)
    before = case.turn
    step = case.steps[0]
    proof = {key: step.proof[key] for key in ("parent_request_json", "request_json")}
    # Same frozen SDK body, another actual Turn; host-only scope must still fail.
    conversation = case.service.get_conversation(
        before.world_id, before.conversation_id
    )
    sub = case.submission.model_copy(
        update={
            "idempotency_key": uuid4(),
            "expected_conversation_revision": conversation.revision,
        }
    )
    accepted = case.service.accept_turn(sub)
    foreign = case.service.claim_turn(
        accepted.world_id,
        accepted.conversation_id,
        accepted.turn_id,
        expected_revision=accepted.revision,
    ).turn
    for generic in (False, True):
        kwargs = dict(
            expected_revision=foreign.revision, expected_attempt=foreign.attempt
        )
        with pytest.raises(ApplicationStateValidationError):
            if generic:
                case.service.authorize_provider_attempt(
                    foreign.world_id,
                    foreign.conversation_id,
                    foreign.turn_id,
                    **kwargs,
                    provider_attempt_event=step.auth,
                )
            else:
                case.service.authorize_plan_jev_provider(
                    foreign.world_id,
                    foreign.conversation_id,
                    foreign.turn_id,
                    **kwargs,
                    authorization=step.auth,
                    producer_proof=proof,
                )
        assert (
            case.service.inspect_turn(
                world_id=foreign.world_id, turn_id=foreign.turn_id
            )
            == foreign
        )
    assert (
        case.service.inspect_turn(world_id=before.world_id, turn_id=before.turn_id)
        == before
    )
