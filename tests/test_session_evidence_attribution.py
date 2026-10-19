from urllib.parse import urlencode
from uuid import uuid4
import pytest
from application_state.agent_conversation.types import Turn,SessionEvidenceClaimV1,plan_answer_basis
from tests.test_agent_turn_service import _policy_turn


def test_session_claim_is_a_distinct_provenance_bound_source_not_a_plan_or_graph_fact():
    turn=_policy_turn();run_id=str(uuid4())
    url='/play?'+urlencode({'world':turn.world_id,'run':run_id,'evidence_revision':54})
    segment=SessionEvidenceClaimV1(kind='session_evidence_claim',text=f'Your closing reflections say players want combat. [Closing reflections]({url})',run_id=run_id,review_revision=54,evidence_sha256='a'*64)
    payload=turn.model_dump(mode='json',by_alias=True)
    payload['provenance']['supporting_work'].append({'resolution':'resolved','kind':'session_evidence_v1','object_id':run_id,'revision':'54','content_sha256':'a'*64})
    payload['completion']['answer_segments'].append(segment.model_dump())
    payload['completion']['answer_basis']=plan_answer_basis([*turn.completion.answer_segments,segment])
    payload['assistant_text']+='\n'+segment.text
    saved=Turn.model_validate(payload)
    assert saved.completion.answer_basis=='committed_plan_plus_session_evidence'
    assert saved.completion.answer_segments[-1].run_id==run_id
    payload['completion']['answer_segments'][-1]['evidence_sha256']='b'*64
    with pytest.raises(ValueError,match='frozen turn provenance'):Turn.model_validate(payload)


def test_session_claim_cannot_cite_mutable_current_review():
    turn=_policy_turn();run_id=str(uuid4());payload=turn.model_dump(mode='json',by_alias=True)
    payload['provenance']['supporting_work'].append({'resolution':'resolved','kind':'session_evidence_v1','object_id':run_id,'revision':'54','content_sha256':'a'*64})
    payload['completion']['answer_segments']=[{'kind':'session_evidence_claim','text':'[Notes](/play?run='+run_id+'&review=1)','run_id':run_id,'review_revision':54,'evidence_sha256':'a'*64}]
    payload['completion']['answer_basis']='committed_plan_plus_session_evidence'
    with pytest.raises(ValueError,match='exact pinned citation'):Turn.model_validate(payload)


def test_provider_session_claim_omits_digest_and_server_binds_exact_revision():
    import json
    from application_state.agent_conversation import types as graph_types
    from apps.live_control_server.services import agent_turn_service as service
    turn=_policy_turn();run_id=str(uuid4());attempt=uuid4()
    provenance=turn.provenance.model_copy(update={"supporting_work":[graph_types.HistoricalReference(resolution="resolved",kind="session_evidence_v1",object_id=run_id,revision="54",content_sha256="a"*64)]})
    auth=graph_types.ProviderAttemptAuthorizedEventV1(event_id=uuid4(),sequence=0,kind="provider_attempt_authorized",provider_attempt_id=attempt,envelope_sha256="b"*64,serializer_version="canonical-json-utf8-v1",provider="synthetic",model="synthetic",api_mode="synthetic",tool_schema_sha256="c"*64,input_accounting_kind="exact_token_count",input_estimator="synthetic",input_tokens=1,output_token_reserve=1,included_assertion_ids=[],included_relationship_ids=[],included_evidence_ref_ids=[],included_graph_event_ids=[])
    outcome=graph_types.ProviderOutcomeEventV1(event_id=uuid4(),sequence=2,kind="provider_outcome",provider_attempt_id=attempt,outcome="response_received")
    entered=graph_types.ProviderOutcomeEventV1(event_id=uuid4(),sequence=1,kind="provider_outcome",provider_attempt_id=attempt,outcome="sdk_entered")
    policy=graph_types.GraphExecutionPolicyV1(policy_version="synthetic",allowed_graph_operations=["expand_graph_retrieval"],max_provider_attempts=1,max_graph_operations=0,max_results_per_operation=0,max_total_provider_input_tokens=100,max_total_provider_output_tokens=100,provider_input_accounting=graph_types.GraphExecutionAccountingV1(kind="exact_token_count",estimator="synthetic"),source_opened=False)
    execution=graph_types.PlanWorldGraphExecutionV1(context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,policy=policy,events=[auth,entered,outcome])
    turn=turn.model_copy(update={"provenance":provenance,"graph_context_execution":execution})
    candidate={"answer_context_status":"plan_only_graph_unused","answer_segments":[{"kind":"session_evidence_claim","text":"Closing reflections: players want more combat.","run_id":run_id,"review_revision":54}],"citation_map":None}
    completion,bindings,answer=service._parse_policy_completion(json.dumps(candidate),turn,attempt)
    assert completion.answer_basis=="committed_plan_plus_session_evidence"
    assert completion.answer_segments[0].evidence_sha256=="a"*64
    assert "evidence_revision=54" in answer and bindings=={}
    assert "Do not supply evidence_sha256" in service._PLAN_GRAPH_ANSWER_INSTRUCTIONS
    candidate["answer_segments"][0]["evidence_sha256"]="d"*64
    with pytest.raises(service._AnswerValidationFailure):service._parse_policy_completion(json.dumps(candidate),turn,attempt)
