"""Exact capability selection/admission and retained proof; provider-free."""
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from generationengine.decision_dispatch import DecisionContextMode, PreparedDecisionDispatch
from application_state.agent_conversation import types as t
from application_state.agent_conversation import build_decision_context as context
from apps.live_control_server.services.build_jev_accounting import ExperimentalAccounting, DecisionCapacityError
from apps.live_control_server.services.build_jev_dispatch import prepared_view


def body(policy, phase="navigate", questions=1):
    return dict(model="jev-1.14.0", state={"decision":{"phase":phase}, "context_accounting":policy.descriptor},
        questions={f"q{i}":{"type":"noul","instructions":"Synthetic question"} for i in range(questions)})


def constant(estimate):
    return ExperimentalAccounting("synthetic", lambda _: (estimate-4096)//2)


def prepared(value, mode=DecisionContextMode.DEFAULT):
    raw=json.dumps(value,separators=(",",":"),ensure_ascii=False).encode()
    return PreparedDecisionDispatch(str(uuid4()),"typesafe","vercel_ai_gateway","jev-1.14.0","POST",
        "https://ai-gateway.vercel.sh/typesafe/v1/systemone",raw,sha256(raw).hexdigest(),len(raw),mode)


@pytest.mark.parametrize("estimate,mode,accepted",[(32000,"default",True),(32002,"long_context",True),(262000,"long_context",True),(262002,"long_context",False)])
def test_exact_question_thresholds_and_long_limit(estimate,mode,accepted):
    policy=constant(estimate);value=body(policy)
    assert policy.context_mode(value)==mode
    request=prepared(value,DecisionContextMode(mode))
    if accepted:
        view=prepared_view(request,value["state"],accounting=policy)
        assert view["contextMode"]==mode
    else:
        with pytest.raises(DecisionCapacityError):
            prepared_view(request,value["state"],accounting=policy)


@pytest.mark.parametrize("phase",["select","coverage","retention"])
def test_other_phases_keep_default_refusal(phase):
    policy=constant(32002);value=body(policy,phase)
    assert policy.context_mode(value)=="default"
    with pytest.raises(DecisionCapacityError):
        prepared_view(prepared(value),value["state"],accounting=policy)
    with pytest.raises(ValueError,match="mode differs"):
        prepared_view(prepared(value,DecisionContextMode.LONG_CONTEXT),value["state"],accounting=policy)


@pytest.mark.parametrize("phase",["navigate","writer_selection"])
def test_combined_multi_question_request_can_require_long_mode(phase):
    policy=ExperimentalAccounting("synthetic",lambda text: 13000 if len(json.loads(text)["questions"])==1 else 30000)
    value=body(policy,phase,questions=3)
    assert policy.question_estimate(value)==30096
    assert policy.estimate(value)==64096
    assert policy.context_mode(value)=="long_context"
    view=prepared_view(prepared(value,DecisionContextMode.LONG_CONTEXT),value["state"],accounting=policy)
    assert view["maxQuestionInputTokens"]==30096


def test_selector_disagreement_and_malformed_mode_fail():
    policy=constant(33000);value=body(policy)
    with pytest.raises(ValueError,match="mode differs"):
        prepared_view(prepared(value),value["state"],accounting=policy)
    with pytest.raises(ValueError,match="capability"):
        prepared_view(prepared(value,"long_context"),value["state"],accounting=policy)


def proof():
    policy=constant(33000);value=body(policy);request=prepared(value,DecisionContextMode.LONG_CONTEXT)
    view=prepared_view(request,value["state"],accounting=policy)
    descriptor=t.BuildControllerContinuationAccountingV4.model_validate(policy.descriptor)
    execution=SimpleNamespace(policy=SimpleNamespace(controller_continuation_accounting=descriptor,
        provider_roles=SimpleNamespace(controller=SimpleNamespace(identity=lambda:("typesafe","jev-1.14.0","typesafe_decision")))))
    event=t.ProviderAttemptAuthorizedEventV5(event_id=uuid4(),sequence=0,kind="provider_attempt_authorized_v5",
        provider_attempt_id=request.attempt_id,envelope_sha256=request.body_sha256,
        serializer_version="typesafe-sdk-json-v1",provider="typesafe",model="jev-1.14.0",api_mode="typesafe_decision",
        tool_schema_sha256="a"*64,input_accounting_kind="estimated_token_count",input_estimator=policy.descriptor["policy"],
        input_tokens=33000,output_token_reserve=0,included_assertion_ids=[],included_relationship_ids=[],
        included_evidence_ref_ids=[],included_graph_event_ids=[],included_source_read_event_ids=[],
        context_mode=view["contextMode"],context_phase=view["contextPhase"],max_question_input_tokens=33000,
        dispatch_identity_sha256=view["dispatchIdentitySha256"])
    return event,execution,request.body.decode()


def test_retained_proof_roundtrip_and_mode_body_phase_digest_tamper():
    event,execution,raw=proof()
    retained=t.ProviderAttemptAuthorizedEventV5.model_validate_json(event.model_dump_json())
    context.validate_prepared(retained,execution,raw)
    for field,value in [("context_mode","default"),("context_phase","select"),("dispatch_identity_sha256","b"*64),
                        ("max_question_input_tokens",262002)]:
        with pytest.raises(ValueError):
            context.validate_prepared(event.model_copy(update={field:value}),execution,raw)
    with pytest.raises(ValueError,match="hash"):
        context.validate_prepared(event,execution,raw+" ")
    with pytest.raises(ValueError,match="exact prepared"):
        context.validate_prepared(event,execution,None)


def test_historical_descriptor_stays_exact():
    policy=constant(33000)
    old={key:value for key,value in policy.descriptor.items()
         if key not in {"long_question_limit_tokens","long_request_limit_tokens","context_selection_policy"}}
    old.update(policy="o200k_double_plus_4096_experimental_v1",raw_wire_limit_bytes=256000)
    historical=t.BuildControllerContinuationAccountingV1.model_validate(old)
    assert historical.model_dump(mode="json")==old
    with pytest.raises(ValueError):
        t.BuildControllerContinuationAccountingV2.model_validate(old)
    event,execution,raw=proof()
    execution.policy.controller_continuation_accounting=historical
    with pytest.raises(ValueError,match="adaptive accounting"):
        context.validate_prepared(event,execution,raw)


@pytest.mark.parametrize("historical", [False, True])
def test_prepared_byte_admission_keeps_exact_historical_contract(historical):
    event,execution,raw=proof()
    value=json.loads(raw)
    value["state"]["text"]="🌿 café 中文 \"escaped\" " + " "*300000
    descriptor=execution.policy.controller_continuation_accounting
    if historical:
        descriptor=t.BuildControllerContinuationAccountingV3.model_validate({
            **descriptor.model_dump(mode="json"), "policy":context.HISTORICAL_SELECTION_POLICY,
            "raw_wire_limit_bytes":256000})
    execution.policy.controller_continuation_accounting=descriptor
    value["state"]["context_accounting"]=descriptor.model_dump(mode="json")
    raw=json.dumps(value,separators=(",",":"),ensure_ascii=False)
    assert len(raw.encode())>256000
    digest=sha256(raw.encode()).hexdigest()
    event=event.model_copy(update={"envelope_sha256":digest,"input_estimator":descriptor.policy,
        "dispatch_identity_sha256":context.identity(envelope_sha256=digest,provider=event.provider,
            model=event.model,api_mode=event.api_mode,context_mode=event.context_mode)})
    if historical:
        retained=type(descriptor).model_validate_json(descriptor.model_dump_json())
        assert retained==descriptor and retained.raw_wire_limit_bytes==256000
        assert context.selected_mode("writer_selection",33000,33000,policy=retained.policy)=="long_context"
        with pytest.raises(ValueError,match="historical byte bound"):
            context.validate_prepared(event,execution,raw)
    else:
        context.validate_prepared(event,execution,raw)
        with pytest.raises(ValueError,match="hash"):
            context.validate_prepared(event,execution,raw+" ")


@pytest.mark.parametrize("estimate,mode,accepted", [(32000,"default",True),(32002,"long_context",True),(262000,"long_context",True),(262002,"long_context",False)])
def test_writer_selection_current_thresholds(estimate,mode,accepted):
    policy=constant(estimate);value=body(policy,"writer_selection")
    assert policy.context_mode(value)==mode
    request=prepared(value,DecisionContextMode(mode))
    if accepted:
        assert prepared_view(request,value["state"],accounting=policy)["contextPhase"]=="writer_selection"
    else:
        with pytest.raises(DecisionCapacityError):
            prepared_view(request,value["state"],accounting=policy)


def test_historical_v2_authorizations_keep_exact_original_phase_semantics():
    event,execution,raw=proof()
    value=json.loads(raw)
    descriptor={**value["state"]["context_accounting"],"policy":context.HISTORICAL_POLICY,
                "context_selection_policy":context.HISTORICAL_SELECTION,"raw_wire_limit_bytes":256000}
    value["state"]["context_accounting"]=descriptor
    historical=t.BuildControllerContinuationAccountingV2.model_validate(descriptor)
    assert historical.model_dump(mode="json")==descriptor
    execution.policy.controller_continuation_accounting=historical
    raw=json.dumps(value,separators=(",",":"),ensure_ascii=False)
    digest=sha256(raw.encode()).hexdigest()
    event=event.model_copy(update={"envelope_sha256":digest,"input_estimator":context.HISTORICAL_POLICY,
        "dispatch_identity_sha256":context.identity(envelope_sha256=digest,provider=event.provider,
            model=event.model,api_mode=event.api_mode,context_mode=event.context_mode)})
    retained=t.ProviderAttemptAuthorizedEventV5.model_validate_json(event.model_dump_json())
    assert retained.model_dump_json()==event.model_dump_json()
    context.validate_prepared(retained,execution,raw)
    assert context.selected_mode("writer_selection",33000,33000,policy=historical.policy)=="default"
    with pytest.raises(ValueError,match="mode differs"):
        context.validate_event(retained.model_copy(update={"context_phase":"writer_selection"}),execution)
    # An old descriptor can be read, but the current host never authorizes it.
    with pytest.raises(ValueError,match="descriptor differs"):
        prepared_view(prepared(value,DecisionContextMode.LONG_CONTEXT),value["state"],accounting=constant(33000))


def test_harness_selects_long_context_for_large_multi_question_sdk_wire(monkeypatch):
    """Regression shape: final selector, 50 choices, >256kB, under token budget."""
    import asyncio
    import httpx2
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services.build_jev_transitions import DecisionQuestion

    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-no-network")
    policy=constant(156808)
    state={"phase":"writer_selection","context_accounting":policy.descriptor,
        "sources":[{"text":'🌿 café 中文 "quoted" \\ '+"evidence. "*32000}]}
    seen=[]

    def authorize(request):
        assert len(request.body)>256000
        view=prepared_view(request,state,accounting=policy)
        assert view["contextMode"]=="long_context"
        assert len(json.loads(request.body)["questions"])==50
        seen.append(view)
        return False  # Capture the actual SDK projection without entering transport.

    class Forbidden(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            raise AssertionError("Provider must not be called")

    driver=SimpleNamespace(stage=lambda:SimpleNamespace(state=lambda:state),authorize=authorize,
        step=SimpleNamespace(questions=tuple(DecisionQuestion(name=f"s{i}",kind="choice",
            question="Judge support",options=("direct_support","qualification_or_conflict","uncertain","irrelevant"))
            for i in range(50))))
    adapter=SimpleNamespace(_build_jev_accounting=policy,turn=None,failure=None)
    harness=BuildJevHarness(decision_transport=Forbidden(),accounting=policy)
    harness.calls,harness.timings,harness._inflight=[],[],{}
    with pytest.raises(GenerationEngineError):
        asyncio.run(harness._decide(adapter,driver))
    assert len(seen)==1 and not harness.calls


@pytest.mark.parametrize("estimate,mode", [(8000,"default"),(70000,"long_context")])
def test_clean_navigation_wire_retains_host_capacity_and_dispatch_checks(estimate, mode):
    policy = constant(estimate)
    value = dict(model="jev-1.14.0", state={"question":"Find the source"},
        questions={"q":{"type":"noul","instructions":"Relevant?"}})
    request = prepared(value, DecisionContextMode(mode))
    view = prepared_view(request, value["state"], accounting=policy, host_phase="navigate")
    assert view["contextPhase"] == "navigate"
    assert view["contextMode"] == mode
    event, execution, _ = proof()
    event = event.model_copy(update=dict(envelope_sha256=request.body_sha256,
        context_mode=mode, context_phase="navigate", input_tokens=estimate,
        max_question_input_tokens=estimate, dispatch_identity_sha256=view["dispatchIdentitySha256"]))
    context.validate_prepared(event, execution, request.body.decode(), host_phase="navigate")
    for change in ({"context_phase":"select"},{"dispatch_identity_sha256":"f"*64},
                   {"max_question_input_tokens":262002}):
        with pytest.raises(ValueError):
            context.validate_prepared(event.model_copy(update=change), execution,
                request.body.decode(), host_phase="navigate")
    for key, metadata in (("phase","navigate"),("context_accounting",policy.descriptor),("decision",{})):
        dirty = value | {"state":value["state"] | {key:metadata}}
        with pytest.raises(ValueError, match="host control metadata"):
            prepared_view(prepared(dirty, DecisionContextMode(mode)), dirty["state"],
                accounting=policy, host_phase="navigate")
    with pytest.raises(ValueError):
        prepared_view(request, value["state"], accounting=policy, host_phase="assess")


def test_clean_navigation_still_refuses_excess_capacity():
    value = dict(model="jev-1.14.0",state={"question":"Find source"},
        questions={"q":{"type":"noul","instructions":"Relevant?"}})
    with pytest.raises(DecisionCapacityError):
        prepared_view(prepared(value, DecisionContextMode.LONG_CONTEXT), value["state"],
            accounting=constant(262002), host_phase="navigate")


def test_navigation_dispatch_rejects_counter_different_from_frozen_policy():
    import asyncio
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from application_state.agent_conversation.jev_retrieval_contract import NativeBuildRetrievalDecisionInputV3
    policy = constant(8000)
    dispatch = object.__new__(PlanJevDispatch)
    dispatch.parent = NativeBuildRetrievalDecisionInputV3.model_construct()
    dispatch.adapter = SimpleNamespace(_build_jev_accounting=policy)
    dispatch._native_accounting = lambda: policy.descriptor | {"tokenizer_version":"different-frozen-counter"}
    with pytest.raises(ValueError, match="actual policy"):
        asyncio.run(dispatch.select_context(prepared(dict(model="jev-1.14.0",
            state={"question":"Find source"}, questions={"q":{"type":"noul","instructions":"Relevant?"}}))))


def test_semantic_build_context_preserves_proposed_work_and_text_without_host_identity():
    from application_state.agent_conversation.build_intentional_response import semantic_routing_state,semantic_request_id
    from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1,AuthoredReferencesV2
    ref=AuthoredGraphReferenceV1(managed_world_id='world-secret-SENTINEL',native_world_id='native-secret-SENTINEL',
        binding_version=9,graph_revision='revision-SENTINEL',node_id='node-SENTINEL',label='The Exchange')
    host=dict(allowed_operations=['answer_from_sources'],capability_sha256='cap-SENTINEL',
        conversation_id='conversation-SENTINEL',pointer_revision=123,current_page={'document_id':'document-SENTINEL','title':'A useful page'},
        page_target={'kind':'replace_selection','text':'Keep this exact 🌿 selected text.'},working_draft={'draft_sha256':'draft-SENTINEL'},
        related_page_catalog=[{'title':'Another page','document_id':'related-SENTINEL','registry_revision':88}],
        history=[{'turn_id':'turn-SENTINEL','user_sha256':sha256(b'Please propose a plan.').hexdigest(),'assistant_sha256':sha256(b'').hexdigest(),
            'user':'Please propose a plan.','assistant':'','collaboration_sha256':'collab-SENTINEL',
            'collaboration':{'kind':'plan','objective':'Develop the shop','steps':[{'kind':'prepare_insertion','text':'Draft the shop.','selected':False}]}}])
    state=semantic_routing_state('Keep the literal words context_accounting and phase in the story.',host,AuthoredReferencesV2(references=(ref,)))
    assert 'SENTINEL' not in json.dumps(state)
    assert state['interaction']['history'][0]['proposed_work']['steps'][0]['selected'] is False
    assert state['interaction']['page_target']['text']=='Keep this exact 🌿 selected text.'
    assert state['interaction']['author_selected_references']==[{'kind':'graph_object','label':'The Exchange'}]
    assert 'context_accounting and phase' in state['user_question']
    first=semantic_request_id(state,world_id='one',client_thread_id='thread',idempotency_key='key')
    assert first!=semantic_request_id(state,world_id='two',client_thread_id='thread',idempotency_key='key')
    assert first!=semantic_request_id(state,world_id='one',client_thread_id='other',idempotency_key='key')
    assert first!=semantic_request_id(state,world_id='one',client_thread_id='thread',idempotency_key='other')


@pytest.mark.parametrize('card',[
    {'kind':'questions','questions':[{'text':'Which shop?'}]},
    {'kind':'connected_page','read_id':'read-SENTINEL','title':'New shop','quote':'Exact quote.','person_label':None,'relationships':[],'instructions':'Develop it.'},
    {'kind':'relationship','read_id':'read-SENTINEL','quote':'Trade.','source':{'label':'A','kind':'person'},'target':{'label':'B','kind':'person'},'predicate':'trades_with','label':'Trades','context':'Proposed trade.'}])
def test_proposed_card_projection_keeps_meaning_but_not_read_identity(card):
    from application_state.agent_conversation.build_intentional_response import semantic_collaboration
    projected=semantic_collaboration(card)
    assert 'read_id' not in projected and 'SENTINEL' not in json.dumps(projected)
    assert projected=={key:value for key,value in card.items() if key!='read_id'}
