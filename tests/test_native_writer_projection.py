"""Shared semantic writer input; full native proofs remain in acquired records."""
import asyncio
from copy import deepcopy

import pytest

from application_state.agent_conversation.native_writer import (
    SCHEMA, LEGACY_SCHEMA, model_frame, model_work_frame, verify_input_records,
)
from tests.test_surface_native_writer import (
    published_lane as published_lane, published_case, work_submission,
    actual_sdk_request, authorize,
)


@pytest.mark.parametrize('schema',[LEGACY_SCHEMA,SCHEMA])
@pytest.mark.parametrize('surface',['build','plan'])
def test_actual_sdk_versions_keep_exact_read_and_qualification_joins(published_lane,surface,schema):
    context,record=published_case(surface,published_lane)
    frame=model_frame(context,record,schema=schema)
    current=model_frame(context,record)
    assert current['schema']==SCHEMA
    before=record.model_dump_json(by_alias=True)
    work=work_submission(context,record)
    raw=asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    stored,grant=authorize(context,record,raw,frame)
    evidence=verify_input_records(context,stored,grant,raw,**work)
    assert evidence.native_assertions and evidence.native_statements
    assert record.model_dump_json(by_alias=True)==before
    for row,compact,(_handle,event,read) in zip(frame['native_assertions']['assertions'],
            current['native_assertions']['assertions'],evidence.native_assertions,strict=True):
        assert row['assertion']==compact['assertion']==read.assertion.model_dump(mode='json')
        assert row['assertion_handle']==compact['assertion_handle']
        assert event.event_id in grant.native_read_event_ids
        assert read.evidence and read.spans  # Original support remains available to citation validation.
        assert set(compact)=={'assertion_handle','assertion'}
        if schema==LEGACY_SCHEMA:
            assert row['evidence'] and row['supporting_sources']
    if schema==SCHEMA:
        legacy=asyncio.run(actual_sdk_request(model_frame(context,record,schema=LEGACY_SCHEMA),
            work_frame=model_work_frame(context,record,**work)))
        assert len(raw.encode()) < len(legacy.encode())


@pytest.mark.parametrize('mutation',['qualification','value','handle','extra-proof','missing','unknown-root','mixed-child'])
def test_compact_presentation_cannot_change_or_omit_admitted_support(published_lane,mutation):
    context,record=published_case('plan',published_lane)
    frame=deepcopy(model_frame(context,record))
    rows=frame['native_assertions']['assertions']
    if mutation=='qualification':
        meta=rows[0]['assertion']['metadata']
        meta['claim_mode']='dungeonbuddy.claim:belief' if meta['claim_mode']=='dungeonbuddy.claim:fact' else 'dungeonbuddy.claim:fact'
    elif mutation=='value':rows[0]['assertion']['value']={'kind':'literal','value':'invented'}
    elif mutation=='handle':rows[0]['assertion_handle']='assertion:foreign'
    elif mutation=='extra-proof':rows[0]['evidence']=[]
    elif mutation=='missing':rows.pop()
    elif mutation=='unknown-root':frame['schema']='dmb_surface_native_writer_evidence_v999'
    else:frame['native_assertions']['schema']='dmb_plan_native_assertion_frame_v1'
    work=work_submission(context,record)
    raw=asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    stored,grant=authorize(context,record,raw,frame)
    with pytest.raises(ValueError):
        verify_input_records(context,stored,grant,raw,**work)


def test_heavy_native_proofs_fit_unchanged_budget_without_losing_facts(published_lane):
    from types import SimpleNamespace
    from tests.test_source_statements import transport,wk,NOW,GM
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract,dungeonbuddy_dnd5e_custom_predicate_profile
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1
    from application_state.agent_conversation.rules_authority_types import canonical_bytes
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    lane=published_lane
    runtime=transport.runtime(lane.repo,dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(),now=NOW,operation_id='writer-proof-volume')
    runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(lane.world.world_id,'fixture',(
        wk.UseExisting(lane.ids['B'],tuple(wk.CreateFact(f'account-{i}','dnd5e:summary',
            wk.LiteralFactValue(f'Account {i} about B, retained with its source qualifications.'),lane.meta)
            for i in range(55))),))),confirmed_by=GM.subject)
    context,record=published_case('plan',lane)
    work=work_submission(context,record)
    turn=SimpleNamespace(graph_context_receipt=context,graph_context_execution=record,**{
        k:v for k,v in work.items() if k!='work_proof'})
    adapter=SimpleNamespace(fence=SimpleNamespace(turn=turn),_broker_execution=lambda:record,failure=None,
        budget={'outputReserveTokens':4096,'contextLimitTokens':128000,
            'estimator':record.policy.provider_input_accounting.estimator})
    rules=SimpleNamespace(frame=lambda:PlanRulesEvidenceFrameV1(schema='dmb_plan_rules_evidence_v1',
        ruleset='synthetic',lookups=(),supports=()),authoring=None)
    writer=PlanJevWriter(adapter,work['work_proof'],rules)
    assert len(writer.frame['native_assertions']['assertions'])>=37
    new={'model':writer.model,'input':writer.messages,'instructions':writer.instructions,
        'max_output_tokens':writer.output_reserve,'text':{'format':writer.output_format},
        'tools':[],'stream':False,'reasoning':{'effort':'low'},'service_tier':'fast'}
    old=deepcopy(new)
    old['input'][0]['content']=canonical_bytes(model_frame(context,record,schema=LEGACY_SCHEMA)).decode()
    import httpx
    from openai import AsyncOpenAI
    from hashlib import sha256
    from uuid import uuid4
    from generationengine.text_dispatch import PreparedTextDispatch
    async def wire(body):
        sent=[]
        def respond(request):
            sent.append(request.content)
            return httpx.Response(200,request=request,json={'id':'resp_synthetic','object':'response',
                'created_at':1,'model':writer.model,'status':'completed','output':[]})
        async with AsyncOpenAI(api_key='synthetic',http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(respond))) as client:
            await client.responses.create(**body)
        assert len(sent)==1
        raw=sent[0]
        return PreparedTextDispatch(str(uuid4()),'openai','responses',writer.model,'POST',
            'https://api.openai.com/v1/responses',raw,sha256(raw).hexdigest(),len(raw))
    old_prepared=asyncio.run(wire(old))
    current_prepared=asyncio.run(wire(new))
    admitted=[]
    class AdmissionReached(Exception):
        pass
    def append(*args, **kwargs):
        admitted.append(args[2])
        raise AdmissionReached
    # Exercise the actual shared capacity guard; stop only at its APP admission
    # seam. Mocking authorize_native_writer would also remove the guard itself.
    adapter.fence.append=append
    rules.native=SimpleNamespace(record=SimpleNamespace(revision=1))
    writer.messages=old['input']
    with pytest.raises(ValueError,match='context allowance'):
        writer.authorize(old_prepared)
    assert not admitted
    writer.messages=new['input']
    with pytest.raises(AdmissionReached):
        writer.authorize(current_prepared)
    assert len(admitted)==1 and writer.context_limit==128000
    assert [r['assertion'] for r in writer.frame['native_assertions']['assertions']]==[
        r['assertion'] for r in model_frame(context,record,schema=LEGACY_SCHEMA)['native_assertions']['assertions']]
    raw=current_prepared.body.decode()
    stored,grant=authorize(context,record,raw,writer.frame)
    accepted=verify_input_records(context,stored,grant,raw,**work)
    assert len(accepted.native_assertions)==len(writer.frame['native_assertions']['assertions'])
    assert all(read.evidence and read.spans for _,_,read in accepted.native_assertions)
