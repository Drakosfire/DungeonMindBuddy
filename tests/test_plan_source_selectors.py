"""Exact captured Plan aliases -> real receipts/APP; synthetic evidence only."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.plan_source_selectors import FRAME_SCHEMA, resolve_selector, source_selector
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.surface_source_answer import passage_handle, producing_passages
from application_state.agent_conversation.surface_evidence_answer import normalize, PLAN_POLICY as SELECTOR_POLICY
from application_state.agent_conversation.plan_writer_output_schema import output_schema, output_format
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_writer import WriterWire
from tests.test_surface_source_answers import stage, answer


def finish(writer, adapter, payload=None):
    wire=WriterWire(adapter,json.dumps(answer(writer) if payload is None else payload))
    completed=asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    return completed,wire


def test_actual_short_selectors_keep_exact_receipts_and_reload(plan_adapter):
    writer=stage(plan_adapter)
    assert writer.projection.frame['schema']==FRAME_SCHEMA
    completed,wire=finish(writer,plan_adapter)
    turn=plan_adapter.fence.turn
    selectors=[r['passage_handle'] for r in writer.projection.frame['opened_passages']]
    for alias,citation in zip(selectors,completed.completion.source_citations,strict=True):
        event,read=resolve_selector(turn,writer.authorization,alias,'p')
        assert read==citation.receipt and event.event_id==citation.read_event_id
        assert len(alias)<len(passage_handle(read))
    reopened=AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id)
    assert reopened.completion==completed.completion and len(wire.calls)==1
    # Aliases remain raw producing-input syntax, not persisted source identities.
    assert all(alias not in reopened.completion.model_dump_json() for alias in selectors)


@pytest.mark.parametrize('change',['raw','scope','world','conversation','attempt','receipt','kind','noncanonical','duplicate'])
def test_current_writer_rejects_unexposed_selector_without_retry(plan_adapter,change):
    writer=stage(plan_adapter);payload=answer(writer)
    values=payload['answer_segments'][0]['passage_handles'];alias=values[0]
    prefix,scope,sequence,index=alias.split('-')
    execution=plan_adapter.fence.turn.graph_context_execution
    if change=='raw':alias=passage_handle(execution.events[int(sequence)].receipts[int(index)])
    elif change=='scope':alias=source_selector(plan_adapter.fence.turn.model_copy(update={'turn_id':uuid4()}),execution.events[int(sequence)],int(index))
    elif change=='world':alias=source_selector(plan_adapter.fence.turn.model_copy(update={'world_id':'foreign-world'}),execution.events[int(sequence)],int(index))
    elif change=='conversation':alias=source_selector(plan_adapter.fence.turn.model_copy(update={'conversation_id':uuid4()}),execution.events[int(sequence)],int(index))
    elif change=='attempt':alias=source_selector(plan_adapter.fence.turn.model_copy(update={'attempt':99}),execution.events[int(sequence)],int(index))
    elif change=='receipt':alias=f'{prefix}-{scope}-{sequence}-999999'
    elif change=='kind':alias=f'n-{scope}-{sequence}-{index}'
    elif change=='noncanonical':alias=f'{prefix}-{scope}-0{sequence}-{index}'
    if change=='duplicate':values[:]=[alias,alias]
    else:values[0]=alias
    wire=WriterWire(plan_adapter,json.dumps(payload))
    with pytest.raises(Exception):asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    stored=plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id,turn_id=plan_adapter.turn.turn_id)
    assert stored.completion is None and len(wire.calls)==1


def historical_request(writer,turn):
    body=json.loads(writer.prepared.body)
    frame=json.loads(body['input'][0]['content'])
    for row in frame['opened_passages']:
        if row.get('passage_handle'):
            _,read=resolve_selector(turn,writer.authorization,row['passage_handle'],'p')
            row['passage_handle']=passage_handle(read)
    frame['schema']='dmb_plan_jev_writer_frame_v3'
    body['input'][0]['content']=json.dumps(frame)
    body['text']['format']=output_format(frame,writer.rules.frame())
    raw=json.dumps(body)
    auth=writer.authorization.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest(),'frame_sha256':canonical_sha256(frame)})
    return raw,auth,frame


def test_retained_v3_input_uses_original_handles_not_current_alias_fallback(plan_adapter):
    writer=stage(plan_adapter);finish(writer,plan_adapter)
    turn=plan_adapter.fence.turn
    raw,auth,frame=historical_request(writer,turn)
    supports,_=producing_passages(turn,auth,raw)
    assert {p.handle for p in supports}=={r['passage_handle'] for r in frame['opened_passages']}
    frame['schema']=FRAME_SCHEMA
    body=json.loads(raw);body['input'][0]['content']=json.dumps(frame);raw=json.dumps(body)
    auth=auth.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest(),'frame_sha256':canonical_sha256(frame)})
    with pytest.raises(ValueError,match='kind, scope or shape'):producing_passages(turn,auth,raw)


def test_included_batch_sibling_without_literal_row_never_becomes_output_support(plan_adapter):
    writer=stage(plan_adapter);finish(writer,plan_adapter)
    turn=plan_adapter.fence.turn
    body=json.loads(writer.prepared.body);frame=json.loads(body['input'][0]['content'])
    shown,omitted=frame['opened_passages']
    shown_event,_=resolve_selector(turn,writer.authorization,shown['passage_handle'],'p')
    omitted_event,_=resolve_selector(turn,writer.authorization,omitted['passage_handle'],'p')
    assert shown_event.event_id==omitted_event.event_id and len(shown_event.receipts)==2
    frame['opened_passages']=[shown]
    body['input'][0]['content']=json.dumps(frame);raw=json.dumps(body)
    auth=writer.authorization.model_copy(update={'envelope_sha256':sha256(raw.encode()).hexdigest(),'frame_sha256':canonical_sha256(frame)})
    supports,_=producing_passages(turn,auth,raw)
    assert [p.handle for p in supports]==[shown['passage_handle']]
    # Decodability/authorized batch membership is insufficient: literal row is absent.
    rejected=answer(writer);rejected['answer_segments'][0]['passage_handles']=[omitted['passage_handle']]
    with pytest.raises(ValidationError):Draft202012Validator(output_schema(frame,writer.rules.frame())).validate(rejected)
    events=[auth if e.event_id==auth.event_id else e for e in turn.graph_context_execution.events]
    scoped=turn.model_copy(update={'graph_context_execution':turn.graph_context_execution.model_copy(update={'events':events})})
    support=SimpleNamespace(provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        context_receipt_sha256=turn.graph_context_receipt.context_receipt_sha256,
        graph_revision=turn.graph_context_receipt.graph_authority.graph_revision,current_policy=SELECTOR_POLICY,
        passages=supports,authored=(),native_sections=())
    with pytest.raises(ValueError,match='exact distinct eligible passage'):normalize(rejected,scoped,auth.provider_attempt_id,support)


def test_current_authorization_rejects_v3_frame_before_provider_dispatch(plan_adapter):
    writer=stage(plan_adapter)
    frame=deepcopy(writer.projection.frame);frame['schema']='dmb_plan_jev_writer_frame_v3'
    writer.messages[0]['content']=json.dumps(frame)
    wire=WriterWire(plan_adapter,json.dumps(answer(writer)))
    with pytest.raises(Exception):asyncio.run(writer.run(transport=wire,api_key='synthetic-not-secret'))
    assert not wire.calls
    assert plan_adapter.service.inspect_turn(world_id=plan_adapter.world_id,turn_id=plan_adapter.turn.turn_id).completion is None


from tests.application_state.test_native_source_citations_postgres import native_writer  # noqa: E402,F401


def test_native_alias_has_one_section_slot_and_exact_citation(native_writer):
    from tests.application_state.test_native_source_citations_postgres import finish as native_finish
    writer=native_writer
    alias=writer.projection.frame['native_source_sections']['sections'][0]['section_handle']
    completed=native_finish(writer)
    turn=writer.adapter.fence.turn
    event,read=resolve_selector(turn,writer.authorization,alias,'n')
    citation=completed.completion.native_source_citations[0]
    assert event==read and alias.endswith('-0')
    assert read.event_id==citation.read_event_id and read.section.section_id==citation.section_id
    assert read.excerpt_sha256==citation.excerpt_sha256
    reopened=AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id)
    assert reopened.completion==completed.completion
    with pytest.raises(ValueError):resolve_selector(turn,writer.authorization,alias[:-1]+'1','n')
