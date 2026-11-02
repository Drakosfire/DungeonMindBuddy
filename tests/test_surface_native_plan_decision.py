"""Real SDK decision proof over shared records; no APP admission or providers."""

import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx2
import pytest
from generationengine import GenerationClient
from generationengine.decision_dispatch import DecisionDispatchGate
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider

from application_state.agent_conversation import types as t
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
    _scope_digest,
    _source_pins,
    verify_input_records,
    verify_selection_records,
)
from tests.test_surface_native_execution import component, execution
from tests.test_surface_native_context import seal


def sdk_case(*, mode="available"):
    context, ledger = component("plan", unavailable=mode == "unavailable")
    if mode in {"source_only", "graph_only"}:
        wire = context.model_dump(mode="json", by_alias=True)
        if mode == "source_only":
            wire["native_query"] = dict(
                schema="dmb_native_plan_query_unavailable_v1",
                managed_world_id="world-one",
                reason="native_graph_head_unavailable",
            )
        else:
            wire["source_authority"] = dict(
                schema="dmb_native_corpus_unavailable_v1",
                managed_world_id="world-one",
                failure_code="native_source_head_unavailable",
            )
        context = type(context).model_validate_json(json.dumps(seal(wire)))
        policy = ledger.policy.model_copy(
            update={
                "source_authority_sha256": t.canonical_sha256(context.source_authority),
                "native_query_sha256": t.canonical_sha256(context.native_query),
            }
        )
        ledger = execution(context.context_receipt_sha256, policy)
    if mode == "captured":
        from tests.application_state.test_plan_placement import (
            original_capture,
            catalog_for,
        )

        original = original_capture()
        capture = type(original).model_validate_json(
            original.model_copy(
                update={
                    "world_id": "world-one",
                    "document_id": "plan-one",
                    "base_revision": 4,
                }
            ).model_dump_json(by_alias=True)
        )
        catalog = catalog_for(capture)
        intent = ledger.policy.action.intent.model_copy(
            update={
                "plan_authoring_capture_sha256": capture.sha256,
                "plan_placement_catalog_sha256": catalog.sha256,
            }
        )
        action = ledger.policy.action.model_copy(
            update={
                "intent": intent,
                "authoring_capture": capture,
                "placement_catalog": catalog,
            }
        )
        ledger = execution(
            context.context_receipt_sha256,
            ledger.policy.model_copy(update={"action": action}),
        )
    identity = dict(
        world_id="world-one", conversation_id=uuid4(), turn_id=uuid4(), attempt=1
    )
    identity_args = identity | dict(question=ledger.policy.action.intent.message)
    steps = []
    sent = []
    for semantic in (True, False):
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
                target_available=ledger.policy.action.authoring_capture is not None,
                target_capture_sha256=ledger.policy.action.intent.plan_authoring_capture_sha256,
                placement_catalog=ledger.policy.action.placement_catalog,
                original_capture=ledger.policy.action.authoring_capture,
            )
            prepare = prepare_requested_work_decision
        else:
            parent = PlanSourceRetrievalDecisionInputV1(
                **common,
                **_source_pins(context),
                candidates=(),
                allowed_operations=("select_candidates", "finish_retrieval"),
            )
            prepare = prepare_decision
        state = SimpleNamespace(parent=parent)

        async def authorize(prepared):
            nonlocal context, ledger
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
            policy = ledger.policy.model_copy(
                update={"provider_input_accounting": accounting}
            )
            if semantic:
                wire = context.model_dump(mode="json", by_alias=True)
                wire["assembled_input"].update(
                    provider_envelope_input_tokens=count,
                    assembled_input_sha256=prepared.body_sha256,
                    context_window_limit=128000,
                    tokenizer_name=accounting.estimator,
                )
                context = type(context).model_validate_json(json.dumps(seal(wire)))
            ledger = execution(context.context_receipt_sha256, policy, ledger.events)
            scope = _scope_digest(context, ledger, **identity)
            state.parent = state.parent.model_copy(
                update={
                    "parent_attempt_id": UUID(prepared.attempt_id),
                    "scope_sha256": scope,
                }
            )
            cls = (
                t.PlanRequestedWorkAuthorizedV2
                if semantic
                else t.PlanJevProviderAuthorizedV1
            )
            auth = cls(
                kind="plan_requested_work_authorized_v2"
                if semantic
                else "plan_jev_provider_authorized_v1",
                event_id=uuid4(),
                sequence=len(ledger.events),
                provider_attempt_id=UUID(prepared.attempt_id),
                envelope_sha256=prepared.body_sha256,
                serializer_version="typesafe-sdk-json-v1",
                provider="typesafe",
                model="jev-1.14.0",
                api_mode="decision",
                tool_schema_sha256=sha256(b"[]").hexdigest(),
                input_accounting_kind=accounting.kind,
                input_estimator=accounting.estimator,
                input_tokens=count,
                output_token_reserve=200,
                included_assertion_ids=[],
                included_relationship_ids=[],
                included_evidence_ref_ids=[],
                included_graph_event_ids=[],
                included_source_read_event_ids=[],
                decision_request_id=state.parent.request_id,
                parent_request_sha256=state.parent.digest,
            )
            state.proof = dict(
                parent_request_json=state.parent.model_dump_json(by_alias=True),
                request_json=prepared.body.decode(),
            )
            assert (
                verify_input_records(
                    context,
                    ledger,
                    auth,
                    state.proof,
                    question=common["question"],
                    scope_sha256=scope,
                )
                == state.parent
            )
            ledger = execution(
                context.context_receipt_sha256, policy, [*ledger.events, auth]
            )
            state.auth = auth
            return True

        async def record(event):
            nonlocal ledger
            value = {
                "sending": "sdk_entered",
                "response_received": "response_received",
            }[event.outcome]
            outcome = t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(ledger.events),
                provider_attempt_id=UUID(event.request.attempt_id),
                outcome=value,
            )
            ledger = execution(
                context.context_receipt_sha256, ledger.policy, [*ledger.events, outcome]
            )
            return True

        class Wire(httpx2.AsyncBaseTransport):
            async def handle_async_request(self, request):
                sent.append(request)
                body = json.loads(request.content)
                answers = {}
                for name, question in body["questions"].items():
                    selected = (
                        "discuss" if name == "requested_work" else "finish_retrieval"
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
            provider = TypeSafeDecisionProvider(
                api_key="synthetic-not-secret",
                transport=Wire(),
                dispatch_gate=DecisionDispatchGate(authorize, record),
            )
            client = GenerationClient(decision_providers={"typesafe": provider})
            try:
                return await client.decide(prepare(state.parent))
            finally:
                await client.aclose()

        result = asyncio.run(run())
        raw = result.model_dump_json()
        proof = state.proof | dict(response_json=raw)
        fields = dict(
            event_id=uuid4(),
            sequence=len(ledger.events),
            context_receipt_sha256=context.context_receipt_sha256,
            execution_policy_sha256=ledger.execution_policy_sha256,
            controller_attempt_id=state.auth.provider_attempt_id,
            decision_request_id=state.parent.request_id,
            controller_envelope_sha256=state.auth.envelope_sha256,
            controller_response_sha256=sha256(raw.encode()).hexdigest(),
            parent_request_sha256=state.parent.digest,
            actual_input_tokens=result.observation.input_tokens,
            actual_output_tokens=result.observation.output_tokens,
        )
        if semantic:
            selected = decode_requested_work_decision(state.parent, result)
            event = t.PlanRequestedWorkSelectedV2(
                kind="plan_requested_work_selected_v2",
                **fields,
                **work_choice(state.parent, selected),
                original_capture_sha256=state.parent.target_capture_sha256,
                placement_catalog_sha256=state.parent.placement_catalog.sha256
                if state.parent.placement_catalog is not None
                else None,
                original_capture=state.parent.original_capture.model_dump(
                    mode="json", by_alias=True
                )
                if state.parent.original_capture is not None
                else None,
                placement_catalog=state.parent.placement_catalog.model_dump(
                    mode="json", by_alias=True
                )
                if state.parent.placement_catalog is not None
                else None,
            )
        else:
            selected = decode_selection(state.parent, result)
            event = t.PlanJevRetrievalSelectionV1(
                kind="plan_jev_retrieval_selected_v1",
                **fields,
                operation=selected.operation,
                selected_handles=list(selected.selected_handles),
            )
        trace = dict(
            world_id=identity["world_id"],
            conversation_id=str(identity["conversation_id"]),
            turn_id=str(identity["turn_id"]),
            attempt=1,
            capture_status="recording",
            observations=[
                dict(
                    kind="context_snapshot",
                    stage="after",
                    materials=[
                        dict(
                            item_id=f"unvalidated-plan-jev-result:{state.auth.provider_attempt_id}",
                            text=raw,
                        )
                    ],
                )
            ],
        )
        verify_selection_records(context, ledger, event, proof, trace, **identity_args)
        steps.append(
            SimpleNamespace(
                context=context,
                ledger=ledger,
                event=event,
                proof=proof,
                trace=trace,
                identity=identity_args,
            )
        )
        ledger = execution(
            context.context_receipt_sha256, ledger.policy, [*ledger.events, event]
        )
    return steps, sent


@pytest.fixture(
    params=["available", "unavailable", "source_only", "graph_only", "captured"],
    scope="module",
)
def decisions(request):
    return sdk_case(mode=request.param)


def test_actual_sdk_semantic_and_retrieval_results_bind_to_shared_records(decisions):
    steps, sent = decisions
    assert len(sent) == 2 and len(steps) == 2
    assert steps[0].event.requested_work == "discuss"
    assert steps[1].event.operation == "finish_retrieval"
    for index, step in enumerate(steps):
        verify_selection_records(
            step.context,
            step.ledger,
            step.event,
            step.proof,
            step.trace,
            **step.identity,
        )
        assert step.proof["request_json"].encode() == sent[index].content
        assert (
            step.event.actual_input_tokens == 37
            and step.event.actual_output_tokens == 9
        )
        assert "native-one" not in step.proof["request_json"]


@pytest.mark.parametrize(
    "mutation",
    [
        "parent",
        "wire",
        "response",
        "scope",
        "world",
        "question",
        "handles",
        "usage",
        "capture",
        "trace_owner",
    ],
)
def test_shared_plan_proof_rejects_changed_sdk_or_owner_material(decisions, mutation):
    steps, _ = decisions
    for step in steps:
        proof = dict(step.proof)
        trace = deepcopy(step.trace)
        event = step.event
        identity = dict(step.identity)
        if mutation == "parent":
            parent = json.loads(proof["parent_request_json"])
            parent["question"] = "A substituted parent question"
            proof["parent_request_json"] = json.dumps(parent)
        elif mutation == "wire":
            proof["request_json"] += " "
        elif mutation == "response":
            proof["response_json"] += " "
        elif mutation == "scope":
            identity["turn_id"] = uuid4()
        elif mutation == "world":
            identity["world_id"] = "foreign-world"
        elif mutation == "question":
            identity["question"] = "A substituted question"
        elif mutation == "handles":
            event = event.model_copy(
                update={"requested_work": "clarify"}
                if isinstance(event, t.PlanRequestedWorkSelectedV2)
                else {"operation": "select_candidates", "selected_handles": ["foreign"]}
            )
        elif mutation == "usage":
            event = event.model_copy(update={"actual_input_tokens": 0})
        elif mutation == "capture":
            trace["observations"] = []
        else:
            trace["turn_id"] = str(uuid4())
        with pytest.raises(ValueError):
            verify_selection_records(
                step.context, step.ledger, event, proof, trace, **identity
            )


@pytest.mark.parametrize("surface", ["build", "play"])
def test_plan_proof_scope_cannot_relabel_another_shared_action(surface):
    context, ledger = component(surface)
    with pytest.raises(ValueError, match="actual Plan action"):
        _scope_digest(
            context,
            ledger,
            world_id="world-one",
            conversation_id=uuid4(),
            turn_id=uuid4(),
            attempt=1,
        )


def test_rehashed_parent_cannot_replace_captured_plan_target():
    steps, _ = sdk_case(mode="captured")
    step = steps[0]
    captured = step.ledger.policy.action.authoring_capture
    assert captured is not None
    from tests.application_state.test_plan_placement import catalog_for

    changed = type(captured).model_validate_json(
        captured.model_copy(
            update={"draft_generation": captured.draft_generation + 1}
        ).model_dump_json(by_alias=True)
    )
    parent = PlanRequestedWorkInputV3.model_validate_json(
        step.proof["parent_request_json"]
    )
    parent = parent.model_copy(
        update={
            "target_capture_sha256": changed.sha256,
            "original_capture": changed,
            "placement_catalog": catalog_for(changed),
        }
    )
    auth = next(
        e for e in step.ledger.events if isinstance(e, t.PlanRequestedWorkAuthorizedV2)
    )
    auth = auth.model_copy(update={"parent_request_sha256": parent.digest})
    proof = {key: step.proof[key] for key in ("parent_request_json", "request_json")}
    proof["parent_request_json"] = parent.model_dump_json(by_alias=True)
    with pytest.raises(ValueError, match="frozen current intent|frozen capture"):
        verify_input_records(
            step.context,
            step.ledger,
            auth,
            proof,
            question=step.identity["question"],
            scope_sha256=_scope_digest(
                step.context,
                step.ledger,
                **{k: v for k, v in step.identity.items() if k != "question"},
            ),
        )
