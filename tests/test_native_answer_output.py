"""Deterministic native base normalization; no SDK/output acceptance claims."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_answer_output import normalize_native_answer,parse_native_answer,NativeAnswerError
from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
from application_state.agent_conversation.play_graph_context import prepare_play_source_provider_inclusion,validate_play_graph_provider_authorization
from tests.test_play_graph_completion import start,acknowledge
from tests.test_play_graph_records import retained,provenance
from tests.test_play_graph_context import fixture,seal_receipt
from tests.test_play_graph_authority import native_provider,native_events,MOMENT


def owner_turn(receipt,execution):
    return retained(status='running').model_copy(update={'graph_context_receipt':receipt,'graph_context_execution':execution,
        'play_context_receipt':receipt.play_basis,'provenance':provenance(receipt)})


def play_answer(*,expose=True):
    r,e,frame,auth=start(expose=expose);e=acknowledge(e,auth)
    candidate={'answer_context_status':'play_only_insufficient_evidence','answer_segments':[
        {'kind':'play_context_claim','text':'The saved note records the crossing 🦉.','source_ids':[entry.source_id for entry in frame.manifest.entries]}]}
    return candidate,owner_turn(r,e),auth


def graph_answer(*,withhold=False):
    from tests.test_settled_source_read_accounting import authorization,receipt as read_receipt
    r,e,frame=fixture();wire=r.model_dump(mode='json',by_alias=True)
    wire['assembled_input']['dispatched_evidence_ref_ids']=['e1','e2','e3','e4','e5','e6','e7'];r=seal_receipt(wire)
    e=t.PlayWorldGraphExecutionV1(context_receipt_sha256=r.context_receipt_sha256,policy=e.policy,
        execution_policy_sha256=play_graph_execution_policy_digest(r.context_receipt_sha256,e.policy),events=[])
    origin=t.ValidatedGraphOperationEventV3(kind='validated_graph_operation_v3',event_id=uuid4(),sequence=0,
        operation_id=uuid4(),operation='expand_graph_retrieval',request_arguments_sha256='a'*64,graph_revision='graph-one',
        result_packet_sha256='b'*64,assertion_ids=['assertion-one'],relationship_ids=[],evidence_ref_ids=['e0'],
        evidence_sufficiency_status='sufficient',coverage_status='complete',truncated=False,source_opened=False,returned_source_pins=[])
    source_auth=authorization(e,1,count=1);source_done=read_receipt(source_auth,2)
    e=native_events(e,[origin,source_auth,source_done])
    auth=native_provider(4).model_copy(update={'included_assertion_ids':['assertion-one'],'included_graph_event_ids':[origin.event_id],
        'included_evidence_ref_ids':['e0'],'included_source_read_event_ids':[] if withhold else [source_done.event_id]})
    included=prepare_play_source_provider_inclusion(r,e,frame,event_id=uuid4(),provider_attempt_id=auth.provider_attempt_id,
        envelope_sha256=auth.envelope_sha256,owner_resolved_current_moment_text=MOMENT)
    e=native_events(e,[*e.events,included]);e=validate_play_graph_provider_authorization(r,e,auth);e=acknowledge(e,auth)
    candidate={'answer_context_status':'graph_grounded','answer_segments':[
        {'kind':'graph_claim','claim_id':'claim:1','text':'An admitted Graph fact.','target_kind':'assertion','target_id':'assertion-one'},
        {'kind':'play_context_claim','text':'Prepared scene note.','source_ids':[entry.source_id for entry in frame.manifest.entries]}]}
    support=SimpleNamespace(provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        context_receipt_sha256=r.context_receipt_sha256,graph_revision='graph-one',closures=(('assertion','assertion-one',('e0',)),))
    return candidate,owner_turn(r,e),auth,support,origin,source_done


def test_play_attribution_uses_own_receipt_and_exact_producer_sources():
    candidate,turn,auth=play_answer()
    completion,bindings,text=parse_native_answer(json.dumps(candidate),turn,auth.provider_attempt_id)
    assert isinstance(completion,t.PlayWorldGraphCompletionV1)
    assert completion.answer_basis=='play_sources' and completion.answer_context_status=='play_only_insufficient_evidence'
    assert completion.citation_map is None and bindings=={}
    assert text==candidate['answer_segments'][0]['text']
    direct=normalize_native_answer(candidate,turn,auth.provider_attempt_id)
    assert direct==(completion,bindings,text)


def test_graph_refs_source_opening_bindings_and_status_are_owner_derived():
    candidate,turn,auth,support,origin,read=graph_answer()
    completion,bindings,text=normalize_native_answer(candidate,turn,auth.provider_attempt_id,support=support)
    assert completion.answer_basis=='play_sources_plus_world_graph'
    assert completion.answer_context_status=='graph_grounded'
    assert completion.answer_segments[0].evidence_ref_ids==['e0']
    assert bindings=={'claim:1':[origin.event_id]}
    citation=completion.citation_map.entries[0]
    assert citation.source_opened and citation.source_read_ids==[read.receipts[0].source_read_id]
    assert text=='An admitted Graph fact.\nPrepared scene note.'


@pytest.mark.parametrize('change',['provider','envelope','receipt','revision','target','ambiguous'])
def test_target_support_cannot_be_foreign_or_ambiguous(change):
    candidate,turn,auth,support,_,_=graph_answer();values=vars(support).copy()
    if change=='provider':values['provider_attempt_id']=uuid4()
    if change=='envelope':values['envelope_sha256']='f'*64
    if change=='receipt':values['context_receipt_sha256']='f'*64
    if change=='revision':values['graph_revision']='foreign'
    if change=='target':values['closures']=(('assertion','other',('e0',)),)
    if change=='ambiguous':values['closures']=(*values['closures'],('assertion','assertion-one',('e1',)))
    with pytest.raises(NativeAnswerError):normalize_native_answer(candidate,turn,auth.provider_attempt_id,support=SimpleNamespace(**values))


@pytest.mark.parametrize('kind',['plan_claim','saved_source_claim','session_evidence_claim','proposal'])
def test_play_cannot_reinterpret_another_domain_claim(kind):
    candidate,turn,auth=play_answer();candidate['answer_segments']=[{'kind':kind,'text':'Foreign claim'}]
    with pytest.raises(NativeAnswerError):normalize_native_answer(candidate,turn,auth.provider_attempt_id)


@pytest.mark.parametrize('change',['no_exposure','foreign_handle','metadata','legacy_citation','missing_producer','empty'])
def test_play_sources_and_output_are_closed(change):
    candidate,turn,auth=play_answer(expose=change!='no_exposure')
    producer=auth.provider_attempt_id
    if change=='foreign_handle':candidate['answer_segments'][0]['source_ids']=['play-source:'+'f'*64]
    if change=='metadata':candidate['answer_segments'][0]['content_sha256']='f'*64
    if change=='legacy_citation':candidate['citation_map']=None
    if change=='missing_producer':producer=uuid4()
    if change=='empty':candidate['answer_segments']=[]
    with pytest.raises(NativeAnswerError):normalize_native_answer(candidate,turn,producer)


def test_withheld_source_is_not_presented_as_opened():
    candidate,turn,auth,support,_,_=graph_answer(withhold=True)
    completion,_,_=normalize_native_answer(candidate,turn,auth.provider_attempt_id,support=support)
    assert not completion.citation_map.entries[0].source_opened
    assert completion.citation_map.entries[0].source_read_ids==[]


@pytest.mark.parametrize('raw',['{}','null','{"answer_segments":[],"answer_segments":[]}',
    '{"answer_context_status":NaN,"answer_segments":[]}','x'*262145, chr(0xD800)])
def test_invalid_raw_answer_never_returns_partial_text(raw):
    _,turn,auth=play_answer()
    with pytest.raises(NativeAnswerError) as failed:parse_native_answer(raw,turn,auth.provider_attempt_id)
    assert '262145' not in str(failed.value) and 'answer_segments' not in str(failed.value)


def plan_turn():
    from tests.test_agent_turn_service import _policy_turn
    from tests.test_settled_source_read_accounting import fixture_execution
    turn=_policy_turn(status='running',completion_present=False);r=turn.graph_context_receipt
    policy=fixture_execution().policy
    policy=policy.model_copy(update={'provider_input_accounting':t.GraphExecutionAccountingV1(kind='exact_token_count',estimator=r.assembled_input.tokenizer_name),
        'source_read_scope':policy.source_read_scope.model_copy(update={
        'world_id':turn.world_id,'graph_revision':r.graph_authority.graph_revision,'admitted_anchors':[]})})
    auth=native_provider(0).model_copy(update={'envelope_sha256':r.assembled_input.assembled_input_sha256,
        'input_tokens':r.assembled_input.provider_envelope_input_tokens,'input_estimator':r.assembled_input.tokenizer_name})
    e=t.PlanWorldGraphExecutionV3(context_receipt_sha256=r.context_receipt_sha256,policy=policy,
        execution_policy_sha256=t.graph_execution_policy_digest_v3(r.context_receipt_sha256,policy),events=[auth])
    # The lifecycle helper is native Play-only; construct actual shared events.
    events=[auth,*[t.ProviderOutcomeEventV1(event_id=uuid4(),sequence=i+1,kind='provider_outcome',
        provider_attempt_id=auth.provider_attempt_id,outcome=value) for i,value in enumerate(('sdk_entered','response_received'))]]
    e=t.PlanWorldGraphExecutionV3.model_validate(e.model_dump(mode='json',by_alias=True)|{'events':[x.model_dump(mode='json',by_alias=True) for x in events]})
    return turn.model_copy(update={'graph_context_execution':e}),auth


def test_current_plan_hash_and_session_citation_are_derived_from_frozen_owners():
    turn,auth=plan_turn();run=str(uuid4())
    ref=t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=run,revision='3',content_sha256='f'*64)
    turn=turn.model_copy(update={'provenance':turn.provenance.model_copy(update={'supporting_work':[ref]})})
    candidate={'answer_context_status':'plan_only_insufficient_evidence','answer_segments':[
        {'kind':'plan_claim','text':'The keeper waits.'},
        {'kind':'session_evidence_claim','text':'Saved recollections.','run_id':run,'review_revision':3}]}
    completion,bindings,text=normalize_native_answer(candidate,turn,auth.provider_attempt_id)
    assert completion.answer_segments[0].plan_content_sha256==turn.graph_context_receipt.plan_basis.content_sha256
    assert completion.answer_segments[1].evidence_sha256=='f'*64
    assert f'run={run}&evidence_revision=3' in text and bindings=={}
    assert completion.answer_basis=='committed_plan_plus_session_evidence'
    candidate['answer_segments'][1]['evidence_sha256']='e'*64
    with pytest.raises(NativeAnswerError):normalize_native_answer(candidate,turn,auth.provider_attempt_id)


def test_escaped_invalid_unicode_in_parsed_base_is_rejected_without_partial_text():
    candidate,turn,auth=play_answer()
    candidate['answer_segments'][0]['text']=chr(0xD800)
    with pytest.raises(NativeAnswerError):parse_native_answer(json.dumps(candidate),turn,auth.provider_attempt_id)


def test_current_plan_unclassified_binding_failure_stays_content_free(monkeypatch):
    turn,auth=plan_turn()
    candidate={'answer_context_status':'plan_only_insufficient_evidence','answer_segments':[{'kind':'plan_claim','text':'The keeper waits.'}]}
    def reject(*args):raise t.GraphCompletionValidationError('PRIVATE_UNCLOSED_REASON','PRIVATE_BINDING_BODY')
    monkeypatch.setattr(t,'validate_execution_completion',reject)
    with pytest.raises(NativeAnswerError) as failed:normalize_native_answer(candidate,turn,auth.provider_attempt_id)
    assert (failed.value.stage,failed.value.reason)==('binding','completion_binding')
    assert 'PRIVATE' not in str(failed.value)
