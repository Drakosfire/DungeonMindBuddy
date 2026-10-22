"""Actual Plan owner/claim admission with real GE/SDK mock transport, no network."""
import asyncio
from datetime import datetime, UTC
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx2
import psycopg
import pytest
from generationengine import GenerationClient
from generationengine.decision_dispatch import DecisionDispatchGate
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.context_trace import TraceContextSnapshot, TraceContextMaterial
from application_state.agent_conversation.jev_retrieval_contract import (
    MODEL, PROVIDER, RetrievalCandidate, RetrievalDecisionInput, prepare_decision,
    decode_selection, validate_prepared_decision,
)
from application_state.agent_conversation.plan_jev_decision import scope_digest
from application_state.errors import ApplicationStateValidationError, ApplicationStateConflictError
from tests.application_state.test_agent_conversation_postgres import _accepted_execution_turn, _provider_authorization_event


def digest(raw): return sha256(raw.encode()).hexdigest()


def prepare_case(dsn, *, operation="select_candidates", missing_usage=False, unknown=False, capture=True,
                 question="Ask about this Plan Graph context.", plan_markdown="# Synthetic Plan\nPreserve the current scene.\n"):
    candidate = RetrievalCandidate(handle="synthetic:pond", label="Park pond", kind="location")
    from application_state.agent_conversation.plan_jev_rules_lookup import rules_candidate
    offered_rules = rules_candidate()
    host = RetrievalDecisionInput(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="a" * 64,
        revision="synthetic:1", question=question, candidates=(candidate, offered_rules),
        allowed_operations=("select_candidates", "discover_more", "finish_retrieval"))
    case = SimpleNamespace(dsn=dsn, host=host, sent=[], lifecycles=[], trace_id=uuid4(), plan_markdown=plan_markdown)

    class Service(AgentConversationService):
        def accept_turn(self, submission):
            # Freeze the actual GE wire in the genuine admitted Plan receipt.
            original = submission.graph_context_receipt
            assembled = original.assembled_input.model_copy(update={"assembled_input_sha256": case.prepared.body_sha256,
                "provider_envelope_input_tokens": 12, "output_token_reserve": 10,
                "tokenizer_name": "synthetic-tokenizer"})
            plan_sha = digest(plan_markdown)
            receipt = original.model_copy(update={"assembled_input": assembled,
                "plan_basis": original.plan_basis.model_copy(update={"content_sha256": plan_sha})})
            receipt = t.PlanWorldGraphContextReceiptV1.model_validate(receipt.model_dump(mode="json", by_alias=True) |
                {"context_receipt_sha256": t.plan_world_graph_context_receipt_digest(receipt)})
            old = submission.graph_context_execution
            policy = t.PlanJevRetrievalPolicyV1.model_validate(old.policy.model_dump(mode="json", by_alias=True) | {
                "source_read_accounting": "settled_receipts_v1", "max_source_read_chars": 96000,
                "driver_schema": "dmb_plan_jev_retrieval_v1", "provider_roles": {
                    "controller": {"provider": PROVIDER, "model": MODEL, "api_mode": "decision"},
                    "writer": {"provider": "test-provider", "model": "synthetic-model", "api_mode": "codex_responses"}}})
            execution = t.PlanWorldGraphExecutionV3(context_receipt_sha256=receipt.context_receipt_sha256,
                policy=policy, events=[], execution_policy_sha256=t.graph_execution_policy_digest_v3(receipt.context_receipt_sha256, policy))
            return super().accept_turn(submission.model_copy(update={"graph_context_receipt": receipt,
                "graph_context_execution": execution, "user_text": question,
                "provenance": submission.provenance.model_copy(update={"primary_work": submission.provenance.primary_work.model_copy(update={"content_sha256": plan_sha})}),
                "submitted_intent_v2": submission.submitted_intent_v2.model_copy(update={"message": question,
                    "primary_work": submission.submitted_intent_v2.primary_work.model_copy(update={"expected_content_sha256": plan_sha})})}))
    case.service = Service()

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, wire):
            case.sent.append(wire)
            body = json.loads(wire.content)
            assert set(body["state"]) == {"question", "candidates"}
            assert body["state"]["candidates"] == [{"label": c.label, "kind": c.kind} for c in (candidate, offered_rules)]
            answers = {}
            for name, entry in body["questions"].items():
                choice = ("finish_retrieval" if operation == "select_candidates" else operation) if name == "operation" else ("include" if operation == "select_candidates" else "exclude")
                answers[name] = {"type": "choice", "choice": choice, "confidence": 1.0,
                    "probabilities": {key: float(key == choice) for key in entry["criteria"]}}
            response = {"model": MODEL, "answers": answers, "usage": {}}
            if not missing_usage: response["usage"] = {"input_tokens": 123, "output_tokens": 17}
            return httpx2.Response(200, request=wire, json=response)

    async def authorize(prepared):
        case.prepared = prepared
        if not hasattr(case, "turn"):
            _, _, _, case.turn = _accepted_execution_turn(case.service, "plan-jev-owner", execution_version=3, uncapped=True)
        execution = case.turn.graph_context_execution
        case.host = host.model_copy(update={"parent_attempt_id": UUID(prepared.attempt_id),
            "scope_sha256": scope_digest(case.turn),
            "revision": case.turn.graph_context_receipt.graph_authority.graph_revision})
        validate_prepared_decision(case.host, prepared)
        base = _provider_authorization_event(attempt_id=UUID(prepared.attempt_id), sequence=len(case.turn.graph_context_execution.events))
        case.auth = t.PlanJevProviderAuthorizedV1.model_validate(base.model_dump(mode="json", by_alias=True) | {
            "kind": "plan_jev_provider_authorized_v1", "api_mode": "decision", "provider": PROVIDER,
            "model": MODEL, "serializer_version": "typesafe-sdk-json-v1", "envelope_sha256": prepared.body_sha256,
            "included_source_read_event_ids": [], "decision_request_id": case.host.request_id,
            "parent_request_sha256": case.host.digest})
        case.proof = {"parent_request_json": case.host.model_dump_json(by_alias=True),
            "request_json": prepared.body.decode()}
        case.turn, fresh = case.service.authorize_plan_jev_provider(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            authorization=case.auth, producer_proof=case.proof)
        assert fresh
        if not hasattr(case, "trace_sequence"):
            case.trace_sequence = 0
            case.service.start_context_trace(world_id=case.turn.world_id, conversation_id=case.turn.conversation_id,
                turn_id=case.turn.turn_id, expected_revision=case.turn.revision, attempt=case.turn.attempt,
                trace_id=case.trace_id, started_at=datetime.now(UTC))
        return True

    async def record(event):
        case.lifecycles.append(event.outcome)
        case.turn, _ = case.service.record_provider_outcome(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(case.turn.graph_context_execution.events), provider_attempt_id=UUID(event.request.attempt_id),
                outcome="sdk_entered" if event.outcome == "sending" else ("outcome_unknown" if unknown else event.outcome)))
        return True

    async def run():
        provider = TypeSafeDecisionProvider(api_key="synthetic-test-key", transport=Transport(),
            dispatch_gate=DecisionDispatchGate(authorize, record))
        client = GenerationClient(decision_providers={PROVIDER: provider})
        try: case.result = await client.decide(prepare_decision(host))
        finally: await client.aclose()
    def next_decision(next_operation):
        nonlocal operation, host
        operation = next_operation
        host = host.model_copy(update={"request_id": uuid4()})
        asyncio.run(run())
        raw = case.result.model_dump_json()
        case.proof = case.proof | {"response_json": raw}
        selected = decode_selection(case.host, case.result)
        case.selection = t.PlanJevRetrievalSelectionV1(kind="plan_jev_retrieval_selected_v1", event_id=uuid4(),
            sequence=len(case.turn.graph_context_execution.events), context_receipt_sha256=case.turn.graph_context_receipt.context_receipt_sha256,
            execution_policy_sha256=case.turn.graph_context_execution.execution_policy_sha256,
            decision_request_id=case.host.request_id, controller_attempt_id=case.auth.provider_attempt_id,
            controller_envelope_sha256=case.auth.envelope_sha256, controller_response_sha256=digest(raw),
            parent_request_sha256=case.host.digest, operation=selected.operation, selected_handles=list(selected.selected_handles),
            actual_input_tokens=case.result.observation.input_tokens, actual_output_tokens=case.result.observation.output_tokens)
        if capture:
            case.service.append_context_trace(world_id=case.turn.world_id, conversation_id=case.turn.conversation_id,
                turn_id=case.turn.turn_id, expected_revision=case.turn.revision, attempt=case.turn.attempt, trace_id=case.trace_id,
                observation=TraceContextSnapshot(sequence=case.trace_sequence, elapsed_ms=1, stage="after", materials=[TraceContextMaterial(
                    item_id=f"unvalidated-plan-jev-result:{case.auth.provider_attempt_id}", state="model_context", role="fact", text=raw)]))
        if capture: case.trace_sequence += 1
    case.redecide = next_decision
    next_decision(operation)
    return case


def append(case, **overrides):
    params = dict(expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        selection=case.selection, producer_proof=case.proof)
    turn, fresh = case.service.record_plan_jev_retrieval_selection(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, **(params | overrides))
    case.turn = turn
    return fresh


def snapshot(case):
    with psycopg.connect(case.dsn) as conn:
        return conn.execute("SELECT revision,graph_context_execution FROM agent.turn WHERE turn_id=%s", (case.turn.turn_id,)).fetchone()


@pytest.mark.parametrize("missing_usage", [False, True])
def test_actual_ge_plan_admission_replays_without_new_dispatch(application_state_dsn, missing_usage):
    case = prepare_case(application_state_dsn, missing_usage=missing_usage)
    before = case.turn.revision
    assert append(case)
    assert not append(case, expected_revision=case.turn.revision)
    assert case.turn.revision == before + 1 and len(case.sent) == 1
    assert case.lifecycles == ["sending", "response_received"]
    assert case.selection.actual_input_tokens == (None if missing_usage else 123)
    assert case.selection.actual_output_tokens == (None if missing_usage else 17)
    replay, fresh = case.service.authorize_plan_jev_provider(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        authorization=case.auth, producer_proof={key: case.proof[key] for key in ("parent_request_json", "request_json")})
    assert not fresh and replay == case.turn and len(case.sent) == 1
    # The selection is metadata only, no Graph operation or source-read receipt.
    assert not any(isinstance(e, (t.ValidatedGraphOperationEventV1, t.ValidatedSourceReadEventV2))
        for e in case.turn.graph_context_execution.events)


@pytest.mark.parametrize("mutation", ["parent", "request", "result", "handles", "usage", "receipt", "stale"])
def test_changed_or_stale_decision_cannot_write(application_state_dsn, mutation):
    case = prepare_case(application_state_dsn); before = snapshot(case)
    proof = dict(case.proof); selection = case.selection; kwargs = {}
    if mutation == "parent": proof["parent_request_json"] = case.host.model_copy(update={"revision": "foreign"}).model_dump_json(by_alias=True)
    elif mutation == "request": proof["request_json"] += " "
    elif mutation == "result": proof["response_json"] += " "
    elif mutation == "handles": selection = selection.model_copy(update={"selected_handles": ["foreign"]})
    elif mutation == "usage": selection = selection.model_copy(update={"actual_input_tokens": 0})
    elif mutation == "receipt": selection = selection.model_copy(update={"context_receipt_sha256": "0" * 64})
    else: kwargs["expected_revision"] = case.turn.revision - 1
    with pytest.raises((ApplicationStateValidationError, ApplicationStateConflictError)):
        append(case, selection=selection, producer_proof=proof, **kwargs)
    assert snapshot(case) == before


@pytest.mark.parametrize("unknown,capture", [(True, True), (False, False)])
def test_unresolved_or_uncaptured_result_is_not_a_decision(application_state_dsn, unknown, capture):
    case = prepare_case(application_state_dsn, unknown=unknown, capture=capture)
    before = snapshot(case)
    with pytest.raises(ApplicationStateValidationError): append(case)
    assert snapshot(case) == before


def test_plan_authorization_is_refused_in_actual_build_owner(application_state_dsn):
    from tests.application_state.test_build_graph_turns import _accept_claim
    case = prepare_case(application_state_dsn)
    _, build = _accept_claim(AgentConversationService())
    with pytest.raises(ApplicationStateValidationError, match="Plan owner"):
        case.service.authorize_plan_jev_provider(build.world_id, build.conversation_id, build.turn_id,
            expected_revision=build.revision, expected_attempt=build.attempt,
            authorization=case.auth, producer_proof={key: case.proof[key] for key in ("parent_request_json", "request_json")})


@pytest.mark.parametrize("operation,allowed", [("select_candidates", False), ("finish_retrieval", True)])
def test_writer_requires_explicit_finish_and_stays_one_shot(application_state_dsn, operation, allowed):
    case = prepare_case(application_state_dsn, operation=operation); append(case)
    base = _provider_authorization_event(attempt_id=uuid4(), sequence=len(case.turn.graph_context_execution.events))
    writer = t.ProviderAttemptAuthorizedEventV3.model_validate(base.model_dump(mode="json", by_alias=True) | {
        "kind": "provider_attempt_authorized_v3", "api_mode": "codex_responses", "included_source_read_event_ids": []})
    def authorize():
        return case.service.authorize_provider_attempt(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            provider_attempt_event=writer)
    before = snapshot(case)
    if not allowed:
        with pytest.raises(ApplicationStateValidationError): authorize()
        assert snapshot(case) == before
        return
    with pytest.raises(ApplicationStateValidationError, match="projection admission"):
        authorize()
    assert snapshot(case) == before


@pytest.mark.parametrize("field", ["parent_request_sha256", "decision_request_id"])
def test_new_plan_decision_cannot_reuse_foreign_parent_admission(application_state_dsn, field):
    case = prepare_case(application_state_dsn); append(case)
    attempt = uuid4()
    host = case.host.model_copy(update={"request_id": uuid4(), "parent_attempt_id": attempt})
    auth = case.auth.model_copy(update={"event_id": uuid4(), "provider_attempt_id": attempt,
        "sequence": len(case.turn.graph_context_execution.events), "decision_request_id": host.request_id,
        "parent_request_sha256": host.digest})
    auth = auth.model_copy(update={field: case.auth.parent_request_sha256 if field == "parent_request_sha256" else case.auth.decision_request_id})
    before = snapshot(case)
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_plan_jev_provider(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            authorization=auth, producer_proof={"parent_request_json": host.model_dump_json(by_alias=True),
                "request_json": case.proof["request_json"]})
    assert snapshot(case) == before


@pytest.mark.parametrize("field,value", [("scope_sha256", "f" * 64), ("question", "foreign question"), ("revision", "foreign revision")])
def test_even_rehashed_parent_cannot_change_current_owner(application_state_dsn, field, value):
    case = prepare_case(application_state_dsn); append(case)
    attempt = uuid4()
    host = case.host.model_copy(update={"request_id": uuid4(), "parent_attempt_id": attempt, field: value})
    auth = case.auth.model_copy(update={"event_id": uuid4(), "provider_attempt_id": attempt,
        "sequence": len(case.turn.graph_context_execution.events), "decision_request_id": host.request_id,
        "parent_request_sha256": host.digest})
    before = snapshot(case)
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_plan_jev_provider(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            authorization=auth, producer_proof={"parent_request_json": host.model_dump_json(by_alias=True),
                "request_json": case.proof["request_json"]})
    assert snapshot(case) == before


@pytest.mark.parametrize("operation,allowed", [("select_candidates", True), ("finish_retrieval", False)])
def test_graph_acquisition_requires_open_decision_phase(application_state_dsn, operation, allowed):
    case = prepare_case(application_state_dsn, operation=operation); append(case)
    event = t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3", event_id=uuid4(),
        sequence=len(case.turn.graph_context_execution.events), operation_id=uuid4(), operation="search_assertions",
        request_arguments_sha256="a" * 64, graph_revision=case.host.revision, result_packet_sha256="b" * 64,
        assertion_ids=[], relationship_ids=[], evidence_ref_ids=[], evidence_sufficiency_status="insufficient",
        coverage_status="complete", truncated=False, source_opened=False, returned_source_pins=[])
    def acquire():
        return case.service.append_validated_graph_operation(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, operation_event=event)
    if allowed:
        _, fresh = acquire(); assert fresh
    else:
        before = snapshot(case)
        with pytest.raises(ApplicationStateValidationError, match="active completed retrieval"): acquire()
        assert snapshot(case) == before


def rules_scope(case):
    from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
    from application_state.agent_conversation.rules_authority_types import RulesScopeV1
    cap = rules_capability(graph=True)
    turn = case.turn
    return RulesScopeV1(schema="dmb_rules_scope_v1", execution_id=uuid4(), world_id=turn.world_id,
        conversation_id=turn.conversation_id, turn_id=turn.turn_id, product_attempt=turn.attempt,
        ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256, capability_policy_sha256=cap.policy_sha256,
        authorization_id=rules_submission_authorization_id(world_id=turn.world_id, conversation_id=turn.conversation_id,
            idempotency_key=turn.idempotency_key, submitted_intent_sha256=turn.submitted_intent_fingerprint_v2, capability=cap),
        budget=cap.budget)


@pytest.mark.parametrize("operation,allowed", [("select_candidates", True), ("finish_retrieval", False)])
def test_rules_ledger_begun_after_decision_obeys_plan_phase(application_state_dsn, operation, allowed):
    from apps.live_control_server.services import rules_lookup_broker as broker
    from tests.test_rules_lookup_broker import args
    case = prepare_case(application_state_dsn, operation=operation); append(case)
    scope = rules_scope(case)
    record = case.service.begin_rules_execution(scope, expected_turn_revision=case.turn.revision)
    from application_state.agent_conversation.plan_jev_rules_lookup import prepare_authorization
    if not allowed:
        # The old unbound native carrier cannot bypass a completed Plan phase.
        auth = broker.prepare_authorization(record.execution, "rules:phase", args())
    else:
        auth = prepare_authorization(record.execution, case.turn, case.proof["parent_request_json"])
    def authorize():
        if not allowed:
            return case.service.authorize_rules_lookup(scope, expected_turn_revision=case.turn.revision,
                expected_ledger_revision=record.revision, event=auth)
        return case.service.authorize_plan_jev_rules_lookup(scope, expected_turn_revision=case.turn.revision,
            expected_ledger_revision=record.revision, event=auth, parent_request_json=case.proof["parent_request_json"])
    if not allowed:
        with pytest.raises(ApplicationStateValidationError, match="open Plan Jev"): authorize()
        return
    record = authorize()
    delivered = case.service.execute_rules_lookup(scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=lambda current: broker.prepare_plan_lookup(current, auth.call_id, case.turn.user_text))
    assert not delivered.replayed
    replay = case.service.execute_rules_lookup(scope, expected_turn_revision=case.turn.revision,
        call_id=auth.call_id, local_reader=lambda _: pytest.fail("replay must not perform a fresh Rules read"))
    assert replay.replayed and replay.prepared.raw_output == delivered.prepared.raw_output


@pytest.mark.parametrize("family", ["source", "related_recap"])
def test_phase_finish_waits_for_each_read_family_receipt(application_state_dsn, family):
    from application_state.agent_conversation.plan_jev_decision import validate_decision_phases
    case = prepare_case(application_state_dsn); append(case)
    events = list(case.turn.graph_context_execution.events)
    call_id = uuid4()
    # This unit isolates phase accounting. Outer Graph admission separately
    # validates the complete authorization/receipt fields and pinned sources.
    auth_type = t.SourceReadAuthorizationEventV2 if family == "source" else t.RelatedRecapContextAuthorizationEventV2
    receipt_type = t.ValidatedSourceReadEventV2 if family == "source" else t.ValidatedRelatedRecapContextEventV2
    pending = auth_type.model_construct(read_call_id=call_id)
    events.append(pending)
    attempt = uuid4(); request = uuid4()
    controller = case.auth.model_copy(update={"event_id": uuid4(), "provider_attempt_id": attempt, "decision_request_id": request})
    response = t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(), sequence=0,
        provider_attempt_id=attempt, outcome="response_received")
    finish = case.selection.model_copy(update={"event_id": uuid4(), "controller_attempt_id": attempt,
        "decision_request_id": request, "operation": "finish_retrieval", "selected_handles": []})
    tail = [controller, response, finish]
    with pytest.raises(ValueError, match="unresolved source read"):
        validate_decision_phases(case.turn.graph_context_execution.model_copy(update={"events": events + tail}))
    settled = receipt_type.model_construct(read_call_id=call_id)
    validate_decision_phases(case.turn.graph_context_execution.model_copy(update={"events": events + [settled] + tail}))
