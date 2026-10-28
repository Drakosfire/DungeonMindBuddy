"""Captured current Play input through APP owner admission, output and reload. No provider sends."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.play_graph_input import NativePlayInputV6
from application_state.agent_conversation.play_session_input import pack
from application_state.agent_conversation.surface_evidence_answer import PLAN_INSTRUCTIONS, PLAN_POLICY
from application_state.play.session_review import commit_review, ReviewCommand
from apps.live_control_server.services.session_evidence import playing_session_evidence
from tests.application_state.test_native_play_graph_postgres import make_submission
from tests.application_state.test_native_play_input_postgres import append
from tests.test_play_graph_authority import native_provider


def review(sub, action='end', revision=0, thoughts='Rehearsal only: talk next; no battle resolved.'):
    basis=sub.play_context_receipt
    return commit_review(world_id=sub.world_id,run_id=basis.run_id,command_id=str(uuid4()),request=ReviewCommand(
        action=action,expected_revision=revision,expected_run_revision=basis.run_revision,
        expected_content_sha256=basis.content_sha256,final_thoughts=thoughts))


def staged(*, with_review=True, change=None):
    service,sub,frame=make_submission()
    if with_review:review(sub)
    packets=playing_session_evidence(sub.world_id,sub.play_context_receipt)['sessions']
    if change:
        packets=deepcopy(packets)
        if change=='text':packets[0]['sources'][0]['text']='Forged saved note.'
        elif change=='world':packets[0]['world_id']='foreign'
        elif change=='run':packets[0]['run_id']=str(uuid4())
        elif change=='checkpoint':packets[0]['checkpoint_run_revision']+=1
        packet=packets[0];packet['sha256']=t.canonical_sha256({k:v for k,v in packet.items() if k!='sha256'})
    refs=[t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=p['run_id'],revision=str(p['review_revision']),content_sha256=p['sha256']) for p in packets]
    sub=sub.model_copy(update={'provenance':sub.provenance.model_copy(update={'supporting_work':[*sub.provenance.supporting_work,*refs]})})
    frame_wire,session_wire=pack(frame,str(sub.idempotency_key),packets)
    carrier=NativePlayInputV6(submission_id=sub.idempotency_key,message=sub.user_text,source_frame=frame_wire,
        session_evidence=session_wire,answer_instructions=PLAN_INSTRUCTIONS)
    raw=json.dumps(dict(model='native-model',messages=[dict(role='user',content=carrier.model_dump_json(by_alias=True))]))
    from tests.test_play_graph_context import seal_receipt
    from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
    wire=sub.graph_context_receipt.model_dump(mode='json',by_alias=True)
    wire['assembled_input']['assembled_input_sha256']=sha256(raw.encode()).hexdigest()
    receipt=seal_receipt(wire)
    policy=t.PlayNativeSourceSectionsPolicyV1.model_validate(sub.graph_context_execution.policy.model_dump(mode='json',by_alias=True)|{'native_source_section_policy':'exact_native_source_sections_v1'})
    execution=sub.graph_context_execution.model_copy(update={'policy':policy,'context_receipt_sha256':receipt.context_receipt_sha256,'execution_policy_sha256':play_graph_execution_policy_digest(receipt.context_receipt_sha256,policy)})
    sub=sub.model_copy(update={'graph_context_receipt':receipt,'graph_context_execution':execution})
    turn=service.accept_turn(sub)
    turn=service.claim_turn(sub.world_id,sub.conversation_id,turn.turn_id,expected_revision=turn.revision).turn
    producer=native_provider(1).model_copy(update={'model':'native-model','envelope_sha256':sha256(raw.encode()).hexdigest(),'api_mode':'chat_completions'})
    return service,sub,turn,producer,raw,carrier,packets


def test_selected_review_retry_preserves_absence_and_frozen_revision(application_state_dsn):
    service,sub,frame=make_submission();basis=sub.play_context_receipt
    assert playing_session_evidence(sub.world_id,basis)['sessions']==[]
    empty=sub.provenance
    review(sub)
    assert playing_session_evidence(sub.world_id,basis,empty)['sessions']==[]
    packet=playing_session_evidence(sub.world_id,basis)['sessions'][0]
    frozen=empty.model_copy(update={'supporting_work':[*empty.supporting_work,t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=basis.run_id,revision='1',content_sha256=packet['sha256'])]})
    review(sub,'save',1,'Later corrected reflection.')
    assert playing_session_evidence(sub.world_id,basis,frozen)['sessions']==[packet]
    review(sub,'reopen',2)
    assert playing_session_evidence(sub.world_id,basis)['sessions']==[]
    assert playing_session_evidence(sub.world_id,basis,frozen)['sessions']==[packet]
    with pytest.raises(Exception):playing_session_evidence(sub.world_id,basis.model_copy(update={'run_revision':basis.run_revision+1}),frozen)


@pytest.mark.parametrize('change',['text','world','run','checkpoint'])
def test_recomputed_packet_digest_cannot_replace_immutable_owner(application_state_dsn,change):
    service,sub,turn,producer,raw,*_=staged(change=change)
    with pytest.raises(Exception):append(service,sub,turn,producer,raw)
    assert service.inspect_turn(world_id=sub.world_id,turn_id=turn.turn_id).graph_context_execution.events==[]


def test_combined_catalog_retains_distinct_current_and_checkpoint_note_owners(application_state_dsn):
    service,sub,turn,producer,raw,carrier,packets=staged()
    live=carrier.source_frame['sources'][0]['text_blocks'][0]
    frozen=carrier.session_evidence[0]['sources'][0]['text_blocks'][0]
    assert live['text']==frozen['text']
    assert live['selection_id']!=frozen['selection_id']
    updated,_=append(service,sub,turn,producer,raw)
    assert updated.graph_context_execution.events[0].kind=='play_source_provider_inclusion_v1'
    forged=carrier.model_dump(mode='json',by_alias=True)
    forged['session_evidence'][0]['sources'][0]['text_blocks'][0]['selection_id']=live['selection_id']
    with pytest.raises(ValueError):NativePlayInputV6.model_validate_json(json.dumps(forged))
    with pytest.raises(ValueError):NativePlayInputV6.model_validate_json(json.dumps(carrier.model_dump(mode='json',by_alias=True)|{'message':'x'*32001}))
    oversized=deepcopy(packets);oversized[0]['sources'][0]['text']='x'*140000
    oversized[0]['sha256']=t.canonical_sha256({k:v for k,v in oversized[0].items() if k!='sha256'})
    large_frame,large_packets=pack(carrier.resolved_source_frame(),str(sub.idempotency_key),oversized)
    with pytest.raises(ValueError,match='budget'):
        NativePlayInputV6(submission_id=sub.idempotency_key,message=sub.user_text,source_frame=large_frame,session_evidence=large_packets,answer_instructions=PLAN_INSTRUCTIONS)


def test_native_summary_delivers_and_reopens_both_exact_citations(application_state_dsn):
    from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1,normalize_unused_native_output
    from application_state.agent_conversation.rules_authority_events import RulesProviderAuthorizedV1,RulesProviderIncludedV1,RulesNativeProviderOutcomeV1
    from tests.application_state.test_plan_jev_decision_admission import rules_scope
    from application_state.agent_conversation.session_summary_projection import citation_target
    service,sub,turn,producer,raw,carrier,packets=staged()
    turn,_=append(service,sub,turn,producer,raw)
    scope=rules_scope(SimpleNamespace(turn=turn));ledger=service.begin_rules_execution(scope,expected_turn_revision=turn.revision)
    for cls,kind,key in [(RulesProviderAuthorizedV1,'provider_authorized','declared_support_refs'),(RulesProviderIncludedV1,'provider_included','support_refs')]:
        event=cls(**dict(kind=kind,event_id=uuid4(),sequence=len(ledger.execution.events),execution_id=scope.execution_id,
            provider_attempt_id=producer.provider_attempt_id,request_envelope_sha256=producer.envelope_sha256,matched_outputs=(),**{key:()}))
        ledger=service.append_rules_provider_event(scope,expected_turn_revision=turn.revision,expected_ledger_revision=ledger.revision,event=event,prepared_request_json=raw)
    for outcome in ('sdk_entered','response_received'):
        turn,_=service.record_provider_outcome(turn.world_id,turn.conversation_id,turn.turn_id,expected_revision=turn.revision,expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind='provider_outcome',event_id=uuid4(),sequence=len(turn.graph_context_execution.events),provider_attempt_id=producer.provider_attempt_id,outcome=outcome))
    ids=[entry['text_blocks'][0]['selection_id'] for entry in carrier.session_evidence[0]['sources']]
    from application_state.agent_conversation.surface_evidence_answer import producing_authored,normalize
    support=SimpleNamespace(provider_attempt_id=producer.provider_attempt_id,envelope_sha256=producer.envelope_sha256,
        context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,graph_revision=turn.graph_context_receipt.graph_authority.graph_revision,
        current_policy=PLAN_POLICY,authored=producing_authored(turn,producer,raw))
    live_id=carrier.source_frame['sources'][0]['text_blocks'][0]['selection_id']
    for bad_ids in ([live_id],['unexposed'],[ids[0],ids[0]]):
        with pytest.raises(ValueError):
            normalize(dict(schema=PLAN_POLICY,limitations=[],requested_detail_gaps=[],answer_segments=[dict(kind='session_summary',text='Unsupported claim.',selection_ids=bad_ids)]),turn,producer.provider_attempt_id,support)
    with pytest.raises(ValueError):producing_authored(turn,producer,raw+' ')
    output=json.dumps(dict(schema=PLAN_POLICY,limitations=[],requested_detail_gaps=[],answer_segments=[dict(kind='session_summary',text='The saved rehearsal note is retained; the reflection leaves battle unresolved and proposes talking next.',selection_ids=ids)]))
    capture=SimpleNamespace(authorization_id='synthetic-play',api_request_id='synthetic-answer',provider=producer.provider,model=producer.model,api_mode=producer.api_mode,request_sha256=producer.envelope_sha256,status='answered',finish_reason='stop',text=output,text_sha256=sha256(output.encode()).hexdigest(),text_utf8_bytes=len(output.encode()),tool_calls=())
    ledger=service.append_rules_provider_event(scope,expected_turn_revision=turn.revision,expected_ledger_revision=ledger.revision,event=RulesNativeProviderOutcomeV1.from_capture(capture,event_id=uuid4(),sequence=len(ledger.execution.events),execution_id=scope.execution_id,provider_attempt_id=producer.provider_attempt_id,request_envelope_sha256=producer.envelope_sha256))
    proof=NativeRulesOutputProofV1.from_capture(capture,prepared_request_json=raw,rules_execution_id=scope.execution_id,producing_provider_attempt_id=producer.provider_attempt_id)
    completion,bindings,text=normalize_unused_native_output(turn,ledger.execution,proof)
    result=t.TurnResult(world_id=turn.world_id,conversation_id=turn.conversation_id,turn_id=turn.turn_id,expected_revision=turn.revision,assistant_text=text,completion=completion,producing_provider_attempt_id=producer.provider_attempt_id,claim_graph_event_ids=bindings)
    completed=service.complete_native_base_turn(result,output_proof=proof,expected_rules_revision=ledger.revision)
    reopened=AgentConversationService().inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)
    assert reopened==completed and completion.surface_id=='play' and completion.schema_=='dmb_surface_evidence_completion_v4'
    supports=completion.answer_segments[0].supports
    assert [s.entry_kind for s in supports]==['scene_note','closing_reflections']
    for support in supports:
        assert support.owner_sha256==packets[0]['sha256']
        assert 'evidence_revision=1' in citation_target(turn.world_id,support)
    from pydantic import TypeAdapter
    from apps.live_control_server.models.agent_turn import AgentPlayWorldGraphContextResponseV1
    assert TypeAdapter(AgentPlayWorldGraphContextResponseV1.model_fields['completion'].annotation).validate_python(completion.model_dump(mode='json',by_alias=True))==completion
    # Downgrade must also fence interrupted v6 and literal v4, not only summaries.
    from importlib import import_module
    with pytest.raises(RuntimeError,match='forward'):
        import_module('application_state.migrations.versions.20261028_0088_play_session_summary').downgrade()
