"""Actual shared writer/Rules atomic dispatch, using SDK/local Rules/disposable APP."""

import asyncio
from copy import deepcopy
import json
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg.types.json import Jsonb
import pytest
from generationengine import GenerationClient, TextRequest, GenerationEngineError
from generationengine.text_dispatch import TextDispatchGate

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_execution import (
    NativeWriterAuthorizedV1,
)
from application_state.agent_conversation.native_writer import (
    model_frame,
    model_work_frame,
)
from application_state.agent_conversation.plan_writer_output_schema import (
    native_output_format,
)
from application_state.agent_conversation.rules_authority_events import (
    RulesProviderAuthorizedV1,
    RulesProviderIncludedV1,
)
from application_state.agent_conversation.rules_authority_policy import (
    rules_capability,
    rules_submission_authorization_id,
)
from application_state.agent_conversation.rules_authority_plan_packet import (
    build_plan_rules_frame,
)
from application_state.agent_conversation.rules_authority_types import (
    RulesScopeV1,
    canonical_bytes,
)
from application_state.agent_conversation.plan_jev_rules_lookup import (
    prepare_authorization,
)
from application_state.errors import (
    ApplicationStateValidationError,
    ApplicationStateConflictError,
)
from apps.live_control_server.services import rules_lookup_broker as broker
from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider
from tests.test_surface_native_context import WORK_MARKDOWN
from tests.test_surface_native_completion import answer
from tests.application_state.test_surface_native_decisions import (
    sdk_case,
    append,
    digest,
)


def open_rules(case):
    if not hasattr(case, "scope"):
        cap = rules_capability(graph=True)
        turn = case.turn
        case.scope = RulesScopeV1(
            schema="dmb_rules_scope_v1",
            execution_id=uuid4(),
            world_id=turn.world_id,
            conversation_id=turn.conversation_id,
            turn_id=turn.turn_id,
            product_attempt=turn.attempt,
            ruleset_id=cap.ruleset_id,
            corpus_sha256=cap.corpus_sha256,
            capability_policy_sha256=cap.policy_sha256,
            authorization_id=rules_submission_authorization_id(
                world_id=turn.world_id,
                conversation_id=turn.conversation_id,
                idempotency_key=turn.idempotency_key,
                submitted_intent_sha256=turn.submitted_intent_fingerprint_v2,
                capability=cap,
            ),
            budget=cap.budget,
        )
    case.rules = case.service.begin_rules_execution(
        case.scope, expected_turn_revision=case.turn.revision
    )
    return case.rules


def acquire_rules(case):
    current = open_rules(case)
    parent = case.steps[-1].proof["parent_request_json"]
    auth = prepare_authorization(current.execution, case.turn, parent)
    case.rules = case.service.authorize_plan_jev_rules_lookup(
        case.scope,
        expected_turn_revision=case.turn.revision,
        expected_ledger_revision=current.revision,
        event=auth,
        parent_request_json=parent,
    )
    case.delivery = case.service.execute_rules_lookup(
        case.scope,
        expected_turn_revision=case.turn.revision,
        call_id=auth.call_id,
        local_reader=lambda owner: broker.prepare_lookup(
            owner,
            auth.call_id,
            broker.LookupRulesArguments(
                question=case.turn.user_text, ruleset_id=case.scope.ruleset_id
            ),
        ),
    )
    case.rules = case.delivery.record


def prepared_case(dsn, *, used=False):
    case = sdk_case(
        dsn,
        rules_reader=acquire_rules if used else None,
        question="Can I end my move in an occupied space?" if used else None,
    )
    assert append(case)
    open_rules(case)
    turn = case.turn
    case.work_proof = dict(
        plan_markdown=WORK_MARKDOWN, session_evidence=[], dialogue=[]
    )
    work = dict(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        attempt=turn.attempt,
        provenance=turn.provenance,
        idempotency_key=turn.idempotency_key,
        work_proof=case.work_proof,
    )
    case.frame = model_frame(turn.graph_context_receipt, turn.graph_context_execution)
    case.work_frame = model_work_frame(
        turn.graph_context_receipt, turn.graph_context_execution, **work
    )
    calls = tuple(
        event.call_id
        for event in case.rules.execution.events
        if event.kind == "query_observed"
    )
    case.rule_frame = build_plan_rules_frame(case.rules.execution, calls)
    case.messages = [
        dict(role="user", content=canonical_bytes(value).decode())
        for value in (case.frame, case.rule_frame, case.work_frame)
    ]
    case.fmt = native_output_format(case.frame, case.rule_frame, case.work_frame)
    base = answer(
        [dict(kind="proposal", label="invented_idea", text="An unplayed possibility.")]
    )
    if used:
        base = dict(
            schema="dmb_rules_mixed_answer_v1",
            base_output=base,
            rules_segments=[
                dict(
                    kind="rules_claim",
                    text="An occupied space prevents ending movement.",
                    support_ids=[
                        str(
                            case.delivery.prepared.observation.support_refs[
                                0
                            ].support_id
                        )
                    ],
                )
            ],
            ordered_refs=[
                dict(domain="base", segment_index=None),
                dict(domain="rules", segment_index=0),
            ],
        )
    case.output = json.dumps(base)
    case.writer_calls = []
    return case


def writer_auth(case, raw, attempt=None):
    from apps.live_control_server.services.agent_turn_service import _json_node_count

    body = json.loads(raw)
    return NativeWriterAuthorizedV1(
        event_id=uuid4(),
        sequence=len(case.turn.graph_context_execution.events),
        provider_attempt_id=attempt or uuid4(),
        envelope_sha256=digest(raw),
        serializer_version="openai-sdk-json-v1",
        provider="openai",
        model=body["model"],
        api_mode="responses",
        tool_schema_sha256=t.canonical_sha256(body.get("tools", [])),
        input_accounting_kind="conservative_upper_bound",
        input_estimator=case.turn.graph_context_execution.policy.provider_input_accounting.estimator,
        input_tokens=len(raw.encode()) + 64 * (1 + _json_node_count(body)),
        output_token_reserve=4096,
        included_assertion_ids=[],
        included_relationship_ids=[],
        included_evidence_ref_ids=[],
        included_graph_event_ids=[],
        included_source_read_event_ids=[],
        frame_sha256=t.canonical_sha256(case.frame),
        native_read_event_ids=(),
    )


def admit(case, raw, auth, **updates):
    values = dict(
        expected_revision=case.turn.revision,
        expected_attempt=case.turn.attempt,
        expected_rules_revision=case.rules.revision,
        authorization=auth,
        prepared_request_json=raw,
        work_proof=case.work_proof,
    )
    case.turn, fresh = case.service.authorize_native_writer(
        case.turn.world_id,
        case.turn.conversation_id,
        case.turn.turn_id,
        **(values | updates),
    )
    if fresh:
        open_rules(case)
    return fresh


def snapshot(case):
    with psycopg.connect(case.dsn) as conn:
        return conn.execute(
            "SELECT t.revision,t.graph_context_execution,r.revision,r.payload FROM agent.turn t JOIN agent.turn_rules_execution r ON r.turn_id=t.turn_id AND r.product_attempt=t.attempt WHERE t.turn_id=%s",
            (case.turn.turn_id,),
        ).fetchone()


def raw_request(case):
    # Owner-built pre-send body for negative admission tests; positive tests use
    # the actual GE/SDK callback bytes and assert these fields in physical IO.
    return json.dumps(
        dict(
            model="gpt-6-luna",
            input=case.messages,
            tools=[],
            stream=False,
            text=dict(format=case.fmt),
            max_output_tokens=4096,
        ),
        ensure_ascii=False,
    )


def run_writer(case, *, timeout=False):
    async def authorize(prepared):
        case.prepared = prepared
        case.auth = writer_auth(case, prepared.body.decode(), UUID(prepared.attempt_id))
        assert admit(case, prepared.body.decode(), case.auth)
        return True

    async def record(event):
        transition = {
            "sending": "sdk_entered",
            "response_received": "response_received",
            "known_not_sent": "known_not_sent",
            "outcome_unknown": "outcome_unknown",
        }[event.outcome]
        outcome = t.ProviderOutcomeEventV1(
            kind="provider_outcome",
            event_id=uuid4(),
            sequence=len(case.turn.graph_context_execution.events),
            provider_attempt_id=case.auth.provider_attempt_id,
            outcome=transition,
            request_id=f"generationengine:{case.auth.provider_attempt_id}"
            if transition == "response_received"
            else None,
            response_sha256=digest(case.output)
            if transition == "response_received"
            else None,
        )
        case.turn, _ = case.service.record_provider_outcome(
            case.turn.world_id,
            case.turn.conversation_id,
            case.turn.turn_id,
            expected_revision=case.turn.revision,
            expected_attempt=case.turn.attempt,
            outcome=outcome,
        )
        return True

    def physical(request):
        case.writer_calls.append(request)
        assert request.content == case.prepared.body
        fresh = AgentConversationService().inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )
        assert fresh.graph_context_execution.events[-1].outcome == "sdk_entered"
        assert open_rules(case).execution.events[-1].kind == "provider_included"
        if timeout:
            raise httpx.ReadTimeout("synthetic writer timeout", request=request)
        return httpx.Response(
            200,
            request=request,
            json=dict(
                id="resp_shared_actual",
                object="response",
                created_at=1,
                model="gpt-6-luna",
                status="completed",
                output=[
                    dict(
                        type="message",
                        id="msg_native",
                        role="assistant",
                        status="completed",
                        content=[
                            dict(type="output_text", text=case.output, annotations=[])
                        ],
                    )
                ],
            ),
        )

    async def run():
        provider = PlanWriterProvider(
            api_key="synthetic-not-secret",
            dispatch_gate=TextDispatchGate(authorize, record),
            transport=httpx.MockTransport(physical),
        )
        client = GenerationClient(text_providers={"openai": provider})
        try:
            result = await client.generate_structured(
                TextRequest(
                    provider="openai",
                    model="gpt-6-luna",
                    user_prompt=json.dumps(case.messages),
                    temperature=None,
                    max_output_tokens=4096,
                    json_schema=case.fmt["schema"],
                    schema_name=case.fmt["name"],
                    max_conformance_retries=0,
                    max_transport_retries=0,
                )
            )
            case.selected = provider.consume_selected_text(provider.actual_response)
            assert case.selected == result.text == case.output
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("used", [False, True])
def test_actual_sdk_shared_writer_atomically_seals_rules_and_replay_cannot_send(
    application_state_dsn, used
):
    case = prepared_case(application_state_dsn, used=used)
    run_writer(case)
    owner = open_rules(case)
    auths = [e for e in owner.execution.events if type(e) is RulesProviderAuthorizedV1]
    included = [e for e in owner.execution.events if type(e) is RulesProviderIncludedV1]
    assert len(auths) == len(included) == len(case.writer_calls) == 1
    assert (
        auths[0].provider_attempt_id
        == included[0].provider_attempt_id
        == case.auth.provider_attempt_id
    )
    before = snapshot(case)
    assert not admit(case, case.prepared.body.decode(), case.auth)
    assert snapshot(case) == before and len(case.writer_calls) == 1
    assert (
        AgentConversationService().inspect_turn(
            world_id=case.turn.world_id, turn_id=case.turn.turn_id
        )
        == case.turn
    )
    # Actual writer is terminal for acquisition; a new generic Rules query cannot
    # reopen it, and its reader must never run.
    from tests.test_rules_lookup_broker import args

    event = broker.prepare_authorization(owner.execution, "late:rules", args())
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_rules_lookup(
            case.scope,
            expected_turn_revision=case.turn.revision,
            expected_ledger_revision=owner.revision,
            event=event,
        )
    assert snapshot(case) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "native",
        "work",
        "schema",
        "tools",
        "missing_rules",
        "rules_revision",
        "turn_revision",
        "attempt",
        "work_proof",
        "capture",
        "generic",
        "graph_cas",
    ],
)
def test_shared_writer_failure_leaves_both_ledgers_unchanged(
    application_state_dsn, monkeypatch, mutation
):
    case = prepared_case(application_state_dsn)
    body = json.loads(raw_request(case))
    if mutation == "native":
        body["input"][0]["content"] = body["input"][0]["content"].replace(
            "What did the check reveal?", "Foreign request"
        )
    elif mutation == "work":
        work = deepcopy(case.work_frame)
        work["dialogue_reference"] = [dict(role="user", content="Forged")]
        body["input"][2]["content"] = json.dumps(work)
    elif mutation == "schema":
        body["text"]["format"]["name"] = "wrong"
    elif mutation == "tools":
        body["tools"] = [dict(type="web_search")]
    elif mutation == "missing_rules":
        body["input"].pop(1)
    elif mutation == "capture":
        with psycopg.connect(case.dsn) as conn:
            conn.execute(
                "UPDATE agent.turn_context_trace SET payload=jsonb_set(payload,'{capture_status}',%s) WHERE turn_id=%s AND attempt=%s",
                (Jsonb("complete"), case.turn.turn_id, case.turn.attempt),
            )
    raw = json.dumps(body, ensure_ascii=False)
    auth = writer_auth(case, raw)
    options = {}
    if mutation == "rules_revision":
        options["expected_rules_revision"] = case.rules.revision + 1
    elif mutation == "turn_revision":
        options["expected_revision"] = case.turn.revision - 1
    elif mutation == "attempt":
        options["expected_attempt"] = case.turn.attempt + 1
    elif mutation == "work_proof":
        options["work_proof"] = dict(case.work_proof, plan_markdown="Forged")
    elif mutation == "graph_cas":
        from application_state.agent_conversation import repository

        monkeypatch.setattr(repository, "update_graph_execution", lambda *a, **k: None)
    before = snapshot(case)
    with pytest.raises(
        (ApplicationStateValidationError, ApplicationStateConflictError)
    ):
        if mutation == "generic":
            case.service.authorize_provider_attempt(
                case.turn.world_id,
                case.turn.conversation_id,
                case.turn.turn_id,
                expected_revision=case.turn.revision,
                expected_attempt=case.turn.attempt,
                provider_attempt_event=auth,
            )
        else:
            admit(case, raw, auth, **options)
    assert snapshot(case) == before and not case.writer_calls


def test_uncertain_shared_writer_retains_input_and_cannot_be_reclaimed(
    application_state_dsn,
):
    case = prepared_case(application_state_dsn)
    with pytest.raises(GenerationEngineError):
        run_writer(case, timeout=True)
    assert (
        len(case.writer_calls) == 1
        and case.turn.graph_context_execution.events[-1].outcome == "outcome_unknown"
    )
    before = snapshot(case)
    assert not admit(case, case.prepared.body.decode(), case.auth)
    assert snapshot(case) == before
    with psycopg.connect(case.dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (case.turn.turn_id,),
        )
    with pytest.raises(ApplicationStateConflictError):
        case.service.claim_turn(
            case.turn.world_id,
            case.turn.conversation_id,
            case.turn.turn_id,
            expected_revision=case.turn.revision,
        )
    restored = case.service.inspect_turn(
        world_id=case.turn.world_id, turn_id=case.turn.turn_id
    )
    assert (
        restored.status == "interrupted"
        and restored.graph_context_execution.events[0]
        == case.turn.graph_context_execution.events[0]
    )


def test_shared_rules_input_cannot_use_the_old_standalone_provider_route(
    application_state_dsn,
):
    case = prepared_case(application_state_dsn)
    raw = raw_request(case)
    auth = RulesProviderAuthorizedV1(
        kind="provider_authorized",
        event_id=uuid4(),
        sequence=len(case.rules.execution.events),
        execution_id=case.scope.execution_id,
        provider_attempt_id=uuid4(),
        request_envelope_sha256=digest(raw),
        matched_outputs=(),
        declared_support_refs=(),
    )
    before = snapshot(case)
    with pytest.raises(ApplicationStateValidationError, match="atomic"):
        case.service.append_rules_provider_event(
            case.scope,
            expected_turn_revision=case.turn.revision,
            expected_ledger_revision=case.rules.revision,
            event=auth,
            prepared_request_json=raw,
        )
    assert snapshot(case) == before
