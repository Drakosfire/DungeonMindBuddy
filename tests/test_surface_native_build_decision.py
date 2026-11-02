"""Actual synthetic controller SDK proof through the one Build semantic owner."""
import asyncio
from dataclasses import asdict
from hashlib import sha256
import json
from uuid import UUID, uuid4

import httpx2
import pytest

from generationengine import GenerationClient
from generationengine.types import DecisionRequest, ChoiceDecisionQuestion
from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
from generationengine.decision_dispatch import DecisionDispatchGate
from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_intentional_response as semantic
from application_state.agent_conversation.native_writer import model_work_frame
from application_state.build_proposal.types import BuildWriteCapability
from tests.test_surface_native_execution import component, execution, controller, build_resolution, BUILD_TURN_ID
from tests.test_surface_native_context import seal, provenance_for
from tests.test_surface_native_work_input import work_case, produce
from tests.test_surface_native_writer import with_work_selection
from tests.test_surface_native_completion import answer
from tests.test_surface_native_writer import published_lane as published_lane


def sdk_case(requested='discuss',*,capable=False,auxiliary=False,probability=1.0,owner=None,context_record=None):
    context,record=context_record if context_record is not None else component('build',unavailable=True)
    conversation=owner.conversation_id if owner is not None else uuid4()
    if capable:
        basis=context.work_context.source_basis
        cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=conversation,expected_pointer_revision=1,
            basis=dict(**basis.model_dump(),draft_sha256=sha256(b'draft').hexdigest(),editor_sha256='b'*64,
                caret=0,draft_generation=0,selection_generation=0),draft_markdown='draft')
        action=record.policy.action
        action=action.model_copy(update={'intent':action.intent.model_copy(update={
            'build_write_capability_sha256':t.canonical_sha256(cap.model_dump(mode='json'))}),
            'write_capability':cap,'capabilities':semantic.Capabilities(
                ('answer_from_sources','propose_build_insertion','prepare_build_image'),
                ('questions','plan','connected_page','relationship'),True,None)})
        record=execution(context.context_receipt_sha256,record.policy.model_copy(update={'action':action}))
    action=record.policy.action
    state=dict(user_question=action.intent.message,requested_work_policy=semantic.POLICY,
        interaction=dict(allowed_operations=list(action.capabilities.operations),
            capability_sha256=action.intent.build_write_capability_sha256))
    request_id='select:'+semantic.digest(state)
    questions=[ChoiceDecisionQuestion(kind='choice',name='requested_work',question=semantic.decision_instructions(),
        options=tuple(semantic.WORK))]
    if auxiliary:
        questions.extend(ChoiceDecisionQuestion(kind='choice',name=name,question='Acquire this optional reference?',
            options=('read','skip')) for name in ('related_page_0','rules_query'))
    captured={}
    async def authorize(prepared):
        nonlocal context,record
        from application_state.agent_conversation.build_decision_context import identity
        auth=controller('build',record.policy).model_copy(update={'provider_attempt_id':UUID(prepared.attempt_id),
            'envelope_sha256':prepared.body_sha256,'dispatch_identity_sha256':identity(
                envelope_sha256=prepared.body_sha256,provider='typesafe',model=prepared.model,
                api_mode='typesafe_decision',context_mode='default')})
        if owner is not None:
            auth=owner.prepared_authorization(auth,prepared)
        wire=context.model_dump(mode='json',by_alias=True)
        wire['assembled_input'].update(assembled_input_sha256=prepared.body_sha256,
            provider_envelope_input_tokens=auth.input_tokens,output_token_reserve=auth.output_token_reserve,
            tokenizer_name=auth.input_estimator,**({"context_window_limit":64000} if owner is not None else {}))
        context=type(context).model_validate_json(json.dumps(seal(wire)))
        record=execution(context.context_receipt_sha256,record.policy,[auth])
        captured.update(auth=auth,request_json=prepared.body.decode())
        if owner is not None:
            owner.authorize(context,record,auth,prepared)
        return True
    async def lifecycle(event):
        nonlocal record
        if owner is not None and not owner.authorized:
            return False
        status={'sending':'sdk_entered','response_received':'response_received'}.get(event.outcome,event.outcome)
        value=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),sequence=len(record.events),
            provider_attempt_id=UUID(event.request.attempt_id),outcome=status)
        record=execution(context.context_receipt_sha256,record.policy,[*record.events,value])
        if owner is not None:
            owner.lifecycle(value)
        return True
    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self,request):
            body=json.loads(request.content)
            if owner is not None:
                owner.sent.append(request)
            answers={}
            for name,q in body['questions'].items():
                label=requested if name=='requested_work' else 'skip'
                scores={option:(probability if option==label else (1-probability)/(len(q['criteria'])-1))
                    for option in q['criteria']}
                answers[name]=dict(type='choice',choice=label,probabilities=scores,confidence=probability)
            return httpx2.Response(200,request=request,json=dict(model='jev-1.14.0',answers=answers,
                usage=dict(input_tokens=25,output_tokens=7)))
    async def run():
        provider=TypeSafeDecisionProvider(api_key='synthetic-only',transport=Wire(),
            dispatch_gate=DecisionDispatchGate(authorize,lifecycle))
        client=GenerationClient(decision_providers={'typesafe':provider})
        try:
            return await client.decide(DecisionRequest(model='jev-1.14.0',provider='typesafe',
                state={'decision':dict(request_id=request_id,state=state,**({'phase':'select'} if owner is not None else {})),
                    **({'context_accounting':owner.accounting.descriptor} if owner is not None else {})},questions=tuple(questions)))
        finally:
            await client.aclose()
    result=asyncio.run(run())
    proof=dict(request_json=captured['request_json'],response_json=result.model_dump_json())
    turn_id=owner.turn.turn_id if owner is not None else BUILD_TURN_ID
    event=build_resolution(record.policy,captured['auth'],len(record.events),turn_id=turn_id,requested=requested).model_copy(update={
        'machine_request_id':request_id,'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest(),
        'broker_operation_id':semantic.operation_id_for(turn_id,1,request_id,requested)})
    trace={'observations':[dict(kind='context_snapshot',materials=[dict(
        item_id=f'unvalidated-controller-decision:{event.controller_attempt_id}:selection',text=proof['response_json'])])]}
    work=dict(world_id=action.intent.world_id,conversation_id=conversation,turn_id=turn_id,attempt=1,
        provenance=provenance_for(context.work_context).model_copy(update={'surface_instance_id':action.intent.surface_instance_id}),
        idempotency_key=uuid4(),work_proof={})
    if owner is not None:
        owner.select(event,proof,trace)
    return context,record,event,proof,trace,work


@pytest.mark.parametrize('requested,capable',[('discuss',False),('clarify_request',False),('plan',True),
    ('write_current_page',True),('prepare_image',True),('change_mechanics',True),('publish_relationships',True)])
@pytest.mark.parametrize('auxiliary',[False,True])
def test_native_uses_actual_build_controller_proof_and_frozen_capabilities(requested,capable,auxiliary):
    context,record,event,proof,trace,work=sdk_case(requested,capable=capable,auxiliary=auxiliary)
    semantic.validate_selection_records(record,event,proof,trace,user_text=record.policy.action.intent.message,
        turn_id=work['turn_id'],attempt=work['attempt'])
    record=with_work_selection(execution(context.context_receipt_sha256,record.policy,[*record.events,event]))
    frame=model_work_frame(context,record,**work)
    assert frame['response_contract']==event.resolution
    assert event.response_capabilities_sha256==semantic.digest(asdict(record.policy.action.capabilities))
    assert 'response_capabilities_sha256' not in record.policy.model_dump()
    if requested in {'change_mechanics','publish_relationships'}:
        assert event.resolution['barrier']=='requested_executor_not_offered'
        assert event.operation=='answer_from_sources'


@pytest.mark.parametrize('mutation',['turn','attempt','message','capture','request','response','answer_names','vote'])
def test_controller_proof_cannot_change_identity_capture_or_auxiliary_answers(mutation):
    _context,record,event,proof,trace,work=sdk_case(auxiliary=True)
    identity=dict(user_text=record.policy.action.intent.message,turn_id=work['turn_id'],attempt=1)
    if mutation=='turn':
        identity['turn_id']=uuid4()
    elif mutation=='attempt':
        identity['attempt']=2
    elif mutation=='message':
        identity['user_text']='Changed question'
    elif mutation=='capture':
        trace['observations']=[]
    elif mutation=='request':
        proof['request_json']+=' '
    else:
        raw=json.loads(proof['response_json'])
        if mutation=='answer_names':
            raw['answers'].pop('rules_query')
        elif mutation=='vote':
            raw['answers']['requested_work']['selected']='plan'
        proof['response_json']=json.dumps(raw)
        if mutation in {'answer_names','vote'}:
            event=event.model_copy(update={'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest()})
            trace['observations'][0]['materials'][0]['text']=proof['response_json']
    with pytest.raises(ValueError):
        semantic.validate_selection_records(record,event,proof,trace,**identity)


def test_image_selection_keeps_its_existing_confidence_threshold():
    _context,record,event,proof,trace,work=sdk_case('prepare_image',capable=True,probability=.85)
    with pytest.raises(ValueError,match='admission threshold'):
        semantic.validate_selection_records(record,event,proof,trace,user_text=record.policy.action.intent.message,
            turn_id=work['turn_id'],attempt=1)


@pytest.mark.parametrize('mutation',['missing','duplicate','unacknowledged','operation','resolution','capabilities','menu','turn'])
def test_shared_writer_rejects_missing_or_changed_semantic_authority(mutation):
    context,record,work=work_case('build')
    events=list(record.events)
    index=next(i for i,e in enumerate(events) if isinstance(e,t.BuildRequestedWorkResolutionV1))
    event=events[index]
    if mutation=='missing':
        events.pop(index)
    elif mutation=='duplicate':
        events.insert(index,event.model_copy(update={'event_id':uuid4()}))
    elif mutation=='unacknowledged':
        before=next(i for i,e in enumerate(events) if isinstance(e,t.ProviderOutcomeEventV1) and e.outcome=='response_received')
        events[before]=events[before].model_copy(update={'outcome':'known_not_sent'})
    elif mutation=='turn':
        work['turn_id']=uuid4()
    else:
        changes={'operation':{'operation':'propose_build_insertion'},'resolution':{'resolution':{}},
            'capabilities':{'response_capabilities_sha256':'b'*64},'menu':{'menu_sha256':'b'*64}}[mutation]
        events[index]=event.model_copy(update=changes)
    with pytest.raises(ValueError):
        altered=execution(context.context_receipt_sha256,record.policy,
            [e.model_copy(update={'sequence':i}) for i,e in enumerate(events)])
        produce(context,altered,work,candidate=answer([dict(kind='discussion',text='Discuss the request.')]))


def test_writer_cannot_override_the_retained_response_contract():
    context,record,work=work_case('build')
    def mutate(frame):
        frame['response_contract']['requested_work']='prepare_image'
    stored,auth,proof,_=produce(context,record,work,mutate=mutate)
    from application_state.agent_conversation.native_completion import normalize_output
    with pytest.raises(ValueError,match='surface work'):
        normalize_output(context,stored,auth,**proof)


class _DurableBuildOwner:
    """Actual existing APP gates; the synthetic transport never decides authority."""
    def __init__(self, mutation=None, world_id="world-one"):
        from application_state.agent_conversation import AgentConversationService
        from tests.application_state.test_agent_conversation_postgres import _new
        from tests.test_build_decision_context import constant
        self.world_id = world_id
        self.service = AgentConversationService()
        self.conversation_id = _new(self.service, self.world_id).conversation_id
        self.accounting = constant(8000)
        self.trace_id = uuid4()
        self.mutation = mutation
        self.sent = []
        self.turn = None
        self.authorized = False

    def prepared_authorization(self, auth, prepared):
        from apps.live_control_server.services.build_jev_dispatch import prepared_view
        body = json.loads(prepared.body)
        view = prepared_view(prepared, body["state"], accounting=self.accounting)
        return auth.model_copy(update=dict(input_tokens=self.accounting.estimate(body),
            output_token_reserve=0, context_mode=view["contextMode"],
            context_phase=view["contextPhase"], max_question_input_tokens=view["maxQuestionInputTokens"],
            dispatch_identity_sha256=view["dispatchIdentitySha256"]))

    def authorize(self, context, record, auth, prepared):
        from datetime import UTC, datetime
        self.submission = t.TurnSubmission(world_id=self.world_id, conversation_id=self.conversation_id,
            idempotency_key=uuid4(), expected_conversation_revision=1,
            user_text=record.policy.action.intent.message,
            provenance=provenance_for(context.work_context).model_copy(update={
                "surface_instance_id":record.policy.action.intent.surface_instance_id}),
            submitted_intent_v2=record.policy.action.intent, graph_context_receipt=context,
            graph_context_execution=execution(context.context_receipt_sha256,record.policy))
        accepted = self.service.accept_turn(self.submission)
        self.turn = self.service.claim_turn(self.world_id,self.conversation_id,accepted.turn_id,
            expected_revision=accepted.revision).turn
        self.service.start_context_trace(world_id=self.world_id,conversation_id=self.conversation_id,
            turn_id=self.turn.turn_id,expected_revision=self.turn.revision,attempt=self.turn.attempt,
            trace_id=self.trace_id,started_at=datetime.now(UTC))
        self.auth = auth
        self.raw = prepared.body.decode()
        values = dict(provider_attempt_event=auth,prepared_decision_json=self.raw,
            expected_revision=self.turn.revision,expected_attempt=self.turn.attempt)
        if self.mutation == "missing":
            values["prepared_decision_json"] = None
        elif self.mutation == "body":
            values["prepared_decision_json"] += " "
        elif self.mutation == "role":
            values["provider_attempt_event"] = auth.model_copy(update={"api_mode":"decision"})
        elif self.mutation == "mode":
            values["provider_attempt_event"] = auth.model_copy(update={"context_mode":"long_context"})
        elif self.mutation == "phase":
            values["provider_attempt_event"] = auth.model_copy(update={"context_phase":"navigate"})
        elif self.mutation == "dispatch":
            values["provider_attempt_event"] = auth.model_copy(update={"dispatch_identity_sha256":"a"*64})
        elif self.mutation == "first-envelope":
            changed = json.loads(self.raw)
            changed["state"]["extra"] = "Another prepared request"
            values["prepared_decision_json"] = json.dumps(changed)
            from application_state.agent_conversation.build_decision_context import identity
            digest = sha256(values["prepared_decision_json"].encode()).hexdigest()
            values["provider_attempt_event"] = auth.model_copy(update={"envelope_sha256":digest,
                "dispatch_identity_sha256":identity(envelope_sha256=digest,provider=auth.provider,
                    model=auth.model,api_mode=auth.api_mode,context_mode=auth.context_mode)})
        elif self.mutation == "claim":
            values["expected_revision"] -= 1
        self.turn, fresh = self.service.authorize_provider_attempt_v2(self.world_id,self.conversation_id,
            self.turn.turn_id,**values)
        assert fresh
        self.authorized = True
        assert self.service.inspect_turn(world_id=self.world_id,turn_id=self.turn.turn_id) == self.turn

    def lifecycle(self, event):
        self.turn, fresh = self.service.record_provider_outcome(self.world_id,self.conversation_id,
            self.turn.turn_id,expected_revision=self.turn.revision,expected_attempt=self.turn.attempt,
            outcome=event)
        assert fresh

    def select(self,event,proof,trace):
        from application_state.agent_conversation.context_trace import TraceContextSnapshot, TraceContextMaterial
        if self.mutation != "capture":
            self.service.append_context_trace(world_id=self.world_id,conversation_id=self.conversation_id,
                turn_id=self.turn.turn_id,expected_revision=self.turn.revision,attempt=self.turn.attempt,trace_id=self.trace_id,
                observation=TraceContextSnapshot(sequence=0,elapsed_ms=1,stage="after",materials=[
                    TraceContextMaterial(item_id=trace["observations"][0]["materials"][0]["item_id"],
                        state="model_context",role="fact",text=proof["response_json"])]))
        if self.mutation == "result":
            proof = proof | {"response_json":proof["response_json"]+" "}
        self.turn, fresh = self.service.record_build_requested_work_resolution(self.world_id,self.conversation_id,
            self.turn.turn_id,expected_revision=self.turn.revision,expected_attempt=self.turn.attempt,
            selection=event,producer_proof=proof)
        assert fresh


@pytest.mark.parametrize("requested,capable",[("discuss",False),("clarify_request",False),
    ("write_current_page",True),("prepare_image",True),("plan",True),
    ("change_mechanics",True),("publish_relationships",True)])
def test_build_sdk_prepared_controller_uses_actual_native_app_admission(application_state_dsn,requested,capable):
    owner = _DurableBuildOwner()
    _context,_record,event,_proof,_trace,work = sdk_case(requested,capable=capable,auxiliary=True,owner=owner)
    stored = owner.service.inspect_turn(world_id="world-one",turn_id=owner.turn.turn_id)
    assert stored.graph_context_execution.policy.action.surface_id == "build"
    assert stored.graph_context_execution.events[-1] == event
    assert work["turn_id"] == stored.turn_id and len(owner.sent) == 1
    replay, fresh = owner.service.authorize_provider_attempt_v2("world-one",owner.conversation_id,
        stored.turn_id,expected_revision=stored.revision,expected_attempt=stored.attempt,
        provider_attempt_event=owner.auth,prepared_decision_json=owner.raw)
    assert not fresh and replay == stored and len(owner.sent) == 1


@pytest.mark.parametrize("mutation",["missing","body","role","mode","phase","dispatch","first-envelope","claim"])
def test_build_sdk_native_controller_refuses_unproved_input_before_send(application_state_dsn,mutation):
    from generationengine import GenerationEngineError
    owner = _DurableBuildOwner(mutation)
    with pytest.raises(GenerationEngineError):
        sdk_case(owner=owner)
    assert not owner.sent
    stored = owner.service.inspect_turn(world_id="world-one",turn_id=owner.turn.turn_id)
    assert stored.status == "running" and not stored.graph_context_execution.events


@pytest.mark.parametrize("mutation",["capture","result"])
def test_native_build_resolution_requires_the_actual_protected_result(application_state_dsn,mutation):
    from application_state.errors import ApplicationStateValidationError
    owner = _DurableBuildOwner(mutation)
    with pytest.raises(ApplicationStateValidationError):
        sdk_case(owner=owner)
    stored = owner.service.inspect_turn(world_id="world-one",turn_id=owner.turn.turn_id)
    assert len(owner.sent) == 1 and stored.status == "running"
    assert stored.graph_context_execution.events[-1].outcome == "response_received"
    assert not any(isinstance(event,t.BuildRequestedWorkResolutionV1) for event in stored.graph_context_execution.events)


@pytest.mark.parametrize("failure", [None, "long", "catalog", "scope", "accounting", "timeout"])
def test_actual_build_native_retrieval_uses_precommitted_sdk_selection_before_core_reads(
    application_state_dsn, published_lane, monkeypatch, failure
):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    from apps.live_control_server.services.agent_context_trace_collector import (
        _OBSERVATION,
    )
    from application_state.errors import (
        ApplicationStateValidationError,
        ApplicationStateConflictError,
    )
    from tests.test_surface_native_writer import published_case
    from tests.test_native_plan_statements import query
    from generationengine import GenerationEngineError

    context, record = published_case("build", published_lane)
    # Retrieval-only fixture: a real, empty saved page has no authored blocks.
    markdown = ""
    content_hash = sha256(markdown.encode()).hexdigest()
    data = context.model_dump(mode="json", by_alias=True)
    data["work_context"]["source_basis"]["content_sha256"] = content_hash
    work = type(context.work_context).model_validate(data["work_context"])
    data["provenance_sha256"] = t.canonical_sha256(provenance_for(work).model_copy(
        update={"surface_instance_id": record.policy.action.intent.surface_instance_id}))
    context = type(context).model_validate_json(json.dumps(seal(data)))
    action = record.policy.action
    intent = action.intent.model_copy(update={"primary_work": action.intent.primary_work.model_copy(
        update={"expected_content_sha256": content_hash})})
    action = action.model_copy(update={"intent": intent, "saved_source_char_count": 0})
    record = execution(context.context_receipt_sha256, record.policy.model_copy(update={"action": action}))
    owner = _DurableBuildOwner(world_id=record.policy.action.intent.world_id)
    long_context = failure == "long"
    if long_context:
        from apps.live_control_server.services.build_jev_accounting import ExperimentalAccounting

        def count(text):
            state = json.loads(text)["state"]
            estimate = 70000 if state.get("phase") == "navigate" else 8000
            return (estimate - 4096) // 2

        owner.accounting = ExperimentalAccounting("synthetic", count)
        failure = None
    sdk_case(owner=owner, context_record=(context, record))
    query_context, native_query = query(published_lane, scope_mode="world")
    assert native_query == owner.turn.graph_context_receipt.native_query
    initial = len(owner.turn.graph_context_execution.events)
    retrieval_calls = []
    grant = owner.service.authorize_plan_jev_provider
    if failure in {"catalog", "scope", "accounting"}:

        def changed_input(*args, **kwargs):
            proof = kwargs["producer_proof"]
            if failure == "accounting":
                event = kwargs["authorization"]
                kwargs["authorization"] = event.model_copy(
                    update={
                        "build_context": event.build_context.model_copy(
                            update={
                                "max_question_input_tokens": event.build_context.max_question_input_tokens
                                + 100000
                            }
                        )
                    }
                )
            else:
                parent = json.loads(proof["parent_request_json"])
                if failure == "catalog":
                    parent["candidates"][0]["handle"] = "unoffered-handle"
                else:
                    parent["scope_sha256"] = "f" * 64
                kwargs["producer_proof"] = proof | {
                    "parent_request_json": json.dumps(parent)
                }
            return grant(*args, **kwargs)

        monkeypatch.setattr(owner.service, "authorize_plan_jev_provider", changed_input)
    fence = _ClaimFence(owner.service, owner.turn)

    class Capture:
        sequence = 1

        def observe(self, value):
            observation = _OBSERVATION.validate_python(
                value | {"sequence": self.sequence, "elapsed_ms": 1}
            )
            self.sequence += 1
            owner.service.append_context_trace(
                world_id=owner.world_id,
                conversation_id=owner.conversation_id,
                turn_id=fence.turn.turn_id,
                expected_revision=fence.turn.revision,
                attempt=fence.turn.attempt,
                trace_id=owner.trace_id,
                observation=observation,
            )

        def provider_usage(self, _calls):
            pass  # Exact typed usage is independently joined by the APP selection owner.

    capture = Capture()

    def lifecycle(value):
        event = t.ProviderOutcomeEventV1(
            kind="provider_outcome",
            event_id=uuid4(),
            sequence=len(fence.turn.graph_context_execution.events),
            provider_attempt_id=adapter.last_provider_attempt_id,
            outcome=value["transition"],
            request_id=value.get("runtimeApiRequestId"),
        )
        _turn, fresh = fence.append("record_provider_outcome", "outcome", event)
        return fresh

    adapter = SimpleNamespace(
        work=SimpleNamespace(build_source=SimpleNamespace(markdown=markdown)),
        fence=fence,
        service=owner.service,
        world_id=owner.world_id,
        turn=owner.turn,
        request=SimpleNamespace(
            message=owner.turn.user_text, surface=SimpleNamespace(surface_id="build")
        ),
        bootstrap=None,
        native_query=native_query,
        native_query_context=query_context,
        native_corpus_context=None,
        native_source_authority=owner.turn.graph_context_receipt.source_authority,
        context_capture=capture,
        failure=None,
        last_provider_attempt_id=None,
        _build_jev_accounting=owner.accounting,
        budget={
            "estimator": "utf8_json_bytes_plus_64_per_node_v1",
            "outputReserveTokens": 0,
            "contextLimitTokens": 64000,
        },
        _broker_execution=lambda: fence.turn.graph_context_execution,
        _capture_prepared_prompt=lambda *_: None,
        record_lifecycle=lifecycle,
    )

    class Reads(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            retrieval_calls.append(request)
            if failure == "timeout":
                raise httpx2.ReadTimeout(
                    "Synthetic native Build decision timeout", request=request
                )
            body = json.loads(request.content)
            assert body["state"]["phase"] == "navigate"
            assert body["state"]["context_accounting"] == owner.accounting.descriptor
            answers = {}
            for name, q in body["questions"].items():
                value = (
                    "include" if name.startswith("candidate_") else "finish_retrieval"
                )
                answers[name] = dict(
                    type="choice",
                    choice=value,
                    confidence=1,
                    probabilities={
                        option: float(option == value) for option in q["criteria"]
                    },
                )
            return httpx2.Response(
                200,
                request=request,
                json=dict(
                    model="jev-1.14.0",
                    answers=answers,
                    usage=dict(input_tokens=35, output_tokens=6),
                ),
            )

    try:
        driver = PlanJevDriver(adapter)
        if failure:
            with pytest.raises(
                (GenerationEngineError, ApplicationStateValidationError)
            ):
                asyncio.run(driver.run(transport=Reads(), api_key="synthetic-only"))
            assert not any(
                isinstance(
                    e,
                    (
                        t.NativePlanStatementReadAuthorizedV1,
                        t.NativePlanAssertionReadAuthorizedV1,
                    ),
                )
                for e in fence.turn.graph_context_execution.events[initial:]
            )
            assert len(retrieval_calls) == (1 if failure == "timeout" else 0)
            if failure == "timeout":
                assert (
                    fence.turn.graph_context_execution.events[-1].outcome
                    == "outcome_unknown"
                )
            return
        assert (
            asyncio.run(driver.run(transport=Reads(), api_key="synthetic-only")) == {}
        )
        stored = owner.service.inspect_turn(
            world_id=owner.world_id, turn_id=fence.turn.turn_id
        )
        events = stored.graph_context_execution.events[initial:]
        grants = [e for e in events if isinstance(e, t.NativeRetrievalAuthorizedV1)]
        selections = [e for e in events if isinstance(e, t.NativeRetrievalSelectedV1)]
        assert len(grants) == len(selections) == len(retrieval_calls) == 2
        assert selections[-1].operation == "finish_retrieval"
        assert all(
            e.api_mode == "typesafe_decision" and e.build_context for e in grants
        )
        assert all(
            e.build_context.context_mode == ("long_context" if long_context else "default")
            and e.input_tokens == (70000 if long_context else 8000)
            for e in grants
        )
        assert all(
            e.parent_request_sha256 == a.parent_request_sha256
            and e.controller_attempt_id == a.provider_attempt_id
            for e, a in zip(selections, grants, strict=True)
        )
        observations = [
            e
            for e in events
            if isinstance(
                e,
                (
                    t.NativePlanStatementReadObservedV1,
                    t.NativePlanAssertionReadObservedV1,
                ),
            )
        ]
        assert len(observations) == 2 and all(e.reads for e in observations)
        assert stored.graph_context_receipt.work_context.surface_id == "build"
        assert stored.graph_context_receipt.native_query == native_query
        assert not any(
            type(e) in {t.PlanJevProviderAuthorizedV1, t.PlanJevRetrievalSelectionV1}
            for e in events
        )
        before = stored
        with pytest.raises(
            (ApplicationStateValidationError, ApplicationStateConflictError)
        ):
            PlanJevDriver(adapter)._read_native(
                "statement", [native_query.matches[0].statement_id]
            )
        assert (
            owner.service.inspect_turn(world_id=owner.world_id, turn_id=stored.turn_id)
            == before
        )
    finally:
        _turn, error = fence.stop()
        assert error is None
