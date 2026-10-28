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


def test_selector_disagreement_malformed_mode_and_byte_fence_fail():
    policy=constant(33000);value=body(policy)
    with pytest.raises(ValueError,match="mode differs"):
        prepared_view(prepared(value),value["state"],accounting=policy)
    with pytest.raises(ValueError,match="capability"):
        prepared_view(prepared(value,"long_context"),value["state"],accounting=policy)
    value["state"]["text"]="x"*256000
    with pytest.raises(DecisionCapacityError,match="raw wire"):
        prepared_view(prepared(value,DecisionContextMode.LONG_CONTEXT),value["state"],accounting=policy)


def proof():
    policy=constant(33000);value=body(policy);request=prepared(value,DecisionContextMode.LONG_CONTEXT)
    view=prepared_view(request,value["state"],accounting=policy)
    descriptor=t.BuildControllerContinuationAccountingV3.model_validate(policy.descriptor)
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
    with pytest.raises(ValueError,match="exact bounded"):
        context.validate_prepared(event,execution,None)


def test_raw_fence_does_not_invoke_counter_and_historical_descriptor_stays_exact():
    def forbidden(_):
        raise AssertionError("Oversized raw wire must not be tokenized")
    policy=ExperimentalAccounting("synthetic",forbidden)
    value=body(policy);value["state"]["text"]="x"*256000
    with pytest.raises(DecisionCapacityError,match="raw wire"):
        prepared_view(prepared(value),value["state"],accounting=policy)
    old={key:value for key,value in policy.descriptor.items()
         if key not in {"long_question_limit_tokens","long_request_limit_tokens","context_selection_policy"}}
    old["policy"]="o200k_double_plus_4096_experimental_v1"
    historical=t.BuildControllerContinuationAccountingV1.model_validate(old)
    assert historical.model_dump(mode="json")==old
    with pytest.raises(ValueError):
        t.BuildControllerContinuationAccountingV2.model_validate(old)
    event,execution,raw=proof()
    execution.policy.controller_continuation_accounting=historical
    with pytest.raises(ValueError,match="adaptive accounting"):
        context.validate_prepared(event,execution,raw)


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
                "context_selection_policy":context.HISTORICAL_SELECTION}
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
