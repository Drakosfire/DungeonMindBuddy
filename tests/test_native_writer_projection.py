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


@pytest.mark.parametrize('surface', ['build', 'plan'])
def test_current_qualification_dictionary_and_retained_inline_bind_exactly(published_lane, surface):
    from application_state.agent_conversation.native_writer import model_input_frame
    from application_state.agent_conversation.native_evidence_view import output_frame
    context, record = published_case(surface, published_lane)
    frame = model_input_frame(context, record)
    collection = frame['native_assertions']
    assert collection['qualifications']
    assert all('metadata' not in r['assertion'] for r in collection['assertions'])
    inline = output_frame({}, frame)
    assert 'qualifications' not in inline['native_assertions']
    assert [r['assertion_handle'] for r in inline['native_assertions']['assertions']] == [
        r['assertion_handle'] for r in collection['assertions']]
    work = work_submission(context, record)
    for actual in [frame, inline]:
        raw = asyncio.run(actual_sdk_request(actual, work_frame=model_work_frame(context, record, **work)))
        stored, grant = authorize(context, record, raw, actual)
        assert verify_input_records(context, stored, grant, raw, **work).native_assertions


@pytest.mark.parametrize('mutation', ['dangling', 'unused', 'changed', 'inline-mixed', 'rebound'])
def test_qualification_dictionary_tampering_cannot_rebind_support(published_lane, mutation):
    from application_state.agent_conversation.native_writer import model_input_frame
    context, record = published_case('plan', published_lane)
    frame = model_input_frame(context, record)
    collection = frame['native_assertions']
    row = collection['assertions'][0]['assertion']
    alias = row['qualification']
    if mutation == 'dangling': row['qualification'] = 'foreign'
    elif mutation == 'unused': collection['qualifications']['unused'] = deepcopy(collection['qualifications'][alias])
    elif mutation == 'changed': collection['qualifications'][alias]['standing'] = 'invented'
    elif mutation == 'inline-mixed': row['metadata'] = deepcopy(collection['qualifications'][alias])
    else:
        other = next(k for k, v in collection['qualifications'].items() if v != collection['qualifications'][alias])
        row['qualification'] = other
    work = work_submission(context, record)
    raw = asyncio.run(actual_sdk_request(frame, work_frame=model_work_frame(context, record, **work)))
    stored, grant = authorize(context, record, raw, frame)
    with pytest.raises(ValueError): verify_input_records(context, stored, grant, raw, **work)


def test_qualification_dedup_preserves_boolean_and_integer_literals(published_lane):
    from application_state.agent_conversation.native_evidence_view import semantic_frame
    context, record = published_case('plan', published_lane)
    host = model_frame(context, record)
    first, second = host['native_assertions']['assertions'][:2]
    second['assertion']['metadata'] = deepcopy(first['assertion']['metadata'])
    first['assertion']['metadata']['domain_metadata'] = [{'schema': 'literal', 'payload': True}]
    second['assertion']['metadata']['domain_metadata'] = [{'schema': 'literal', 'payload': 1}]
    before = deepcopy(host)
    collection = semantic_frame(host)['native_assertions']
    a, b = collection['assertions'][:2]
    assert a['assertion']['qualification'] != b['assertion']['qualification']
    assert host == before


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
    original = [r['assertion'] for r in
        model_frame(context,record,schema=LEGACY_SCHEMA)['native_assertions']['assertions']]
    presented = [r['assertion'] for r in writer.frame['native_assertions']['assertions']]
    assert len(presented) == len(original)
    semantic_qualifiers = {'scope','epistemic_basis','claim_mode','standing',
        'temporal_scope','domain_metadata'}
    for semantic, host in zip(presented, original, strict=True):
        assert set(semantic) == {'subject','predicate','value','metadata'}
        assert semantic['subject'].startswith('entity')
        assert semantic['subject'] != host['subject_entity_id']
        assert semantic['predicate'] == host['predicate']
        assert semantic['value'] == host['value']  # This fixture contains literal values.
        expected_metadata = {key: host['metadata'][key] for key in semantic_qualifiers}
        expected_metadata['domain_metadata'] = [
            {'world_context': entry['payload']}
            if entry['schema'] == 'dungeonbuddy.domain_metadata:world_context_v1' else entry
            for entry in host['metadata']['domain_metadata']]
        assert semantic['metadata'] == expected_metadata
    raw=current_prepared.body.decode()
    import json
    actual_frame = next(value for message in new['input']
        if isinstance(message.get('content'),str)
        for value in [json.loads(message['content'])]
        if set(value) == {'input_status','user_question','native_body_evidence',
            'native_statements','native_assertions'})
    stored,grant=authorize(context,record,raw,actual_frame)
    accepted=verify_input_records(context,stored,grant,raw,**work)
    assert len(accepted.native_assertions)==len(writer.frame['native_assertions']['assertions'])
    assert all(read.evidence and read.spans for _,_,read in accepted.native_assertions)
    assert [read.assertion.model_dump(mode='json') for _,_,read in
        accepted.native_assertions] == original  # Exact host identities/proofs remain admitted.


def semantic_plan_produce(*, candidate=None, mutate=None):
    from tests.test_surface_native_work_input import work_case, produce
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    context, record, work = work_case('plan')
    host = model_work_frame(context, record, **work)
    provider = semantic_frame(host, record)
    def project(frame):
        frame.clear()
        frame.update(deepcopy(provider))
        if mutate:
            mutate(frame)
    stored, auth, proof, _ = produce(context, record, work, candidate=candidate, mutate=project)
    return context, record, work, host, provider, stored, auth, proof


def test_semantic_plan_sdk_and_normalization_keep_exact_session_and_saved_owners():
    from application_state.agent_conversation.native_completion import normalize_output, verify_completion
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from tests.test_surface_native_authored_output import candidate_for
    from tests.test_plan_writer_output_schema import rules
    from jsonschema import Draft202012Validator
    case = semantic_plan_produce()
    context, record, work, host, provider = case[:5]
    candidate = candidate_for(provider)
    context, record, work, host, provider, stored, auth, proof = semantic_plan_produce(candidate=candidate)
    accepted = verify_input_records(context, stored, auth, proof['prepared_request_json'], **work)
    assert accepted.authored_local and accepted.work_frame == host
    Draft202012Validator(native_output_format(model_frame(context, record), rules(), host | provider)['schema']).validate(candidate)
    result = normalize_output(context, stored, auth, **proof)
    assert verify_completion(result, context, stored, auth, **proof) == result
    plan, note, summary = result.answer_segments[:3]
    assert plan.text == host['committed_plan_blocks'][0]['text'] and '\r\n' in plan.text
    assert note.object_id == work['work_proof']['session_evidence'][0]['run_id']
    assert all(s.revision == '3' and s.checkpoint_content_sha256 == 'e'*64 for s in summary.supports)
    assert {s.entry_kind for s in summary.supports} == {'scene_note', 'closing_reflections'}
    assert plan.source_handle.startswith('q') and not plan.source_handle.startswith('work')
    import json
    wire = json.dumps(provider)
    for secret in (context.work_context.plan_basis.document_id, work['work_proof']['session_evidence'][0]['run_id'],
                   'e'*64, host['authored_sources'][0]['handle'], host['committed_plan_blocks'][0]['selection_id']):
        assert str(secret) not in wire
    assert not {'run_id','review_revision','session_content_sha256'} & provider['session_evidence'][0].keys()
    assert provider['session_evidence'][0]['ended_at'] == host['session_evidence'][0]['ended_at']
    assert provider['focused_edit_target'] == host['focused_edit_target']


@pytest.mark.parametrize('mutation', ['text','date','role','alias','extra','host_selector','session_kind'])
def test_semantic_plan_work_cannot_change_meaning_or_owner_projection(mutation):
    def change(frame):
        if mutation == 'text': frame['committed_plan_blocks'][0]['text'] += 'Invented'
        elif mutation == 'date': frame['session_evidence'][0]['ended_at'] = '1900-01-01T00:00:00Z'
        elif mutation == 'role': frame['current_page_draft']['state'] = 'published_fact'
        elif mutation == 'alias': frame['committed_plan_blocks'][0]['selection_id'] = 'body0'
        elif mutation == 'extra': frame['world_id'] = 'foreign'
        elif mutation == 'host_selector': frame['authored_sources'][0]['handle'] = 'q' + 'a'*64
        else: frame['session_evidence'][0]['sources'][0]['kind'] = 'played_fact'
    context, _, work, _, _, stored, auth, proof = semantic_plan_produce(mutate=change)
    with pytest.raises(ValueError):
        verify_input_records(context, stored, auth, proof['prepared_request_json'], **work)


@pytest.mark.parametrize('mutation',['world_alias','old_alias','duplicate','plan_summary'])
def test_local_plan_output_cannot_borrow_world_historical_or_wrong_source_family(mutation):
    from tests.test_surface_native_authored_output import candidate_for, selected_rows
    from application_state.agent_conversation.native_completion import normalize_output
    _, _, _, host, provider, *_ = semantic_plan_produce()
    candidate = candidate_for(provider)
    if mutation == 'world_alias': candidate['answer_segments'][0]['selection_id'] = 'body0'
    elif mutation == 'old_alias': candidate['answer_segments'][0]['selection_id'] = selected_rows(host)[0]
    elif mutation == 'duplicate': candidate['answer_segments'] = [candidate['answer_segments'][0]]*2
    else: candidate['answer_segments'] = [dict(kind='session_summary',text='Unsupported session claim.',
        selection_ids=[selected_rows(provider)[0]])]
    context, _, _, _, _, stored, auth, proof = semantic_plan_produce(candidate=candidate)
    with pytest.raises(ValueError):
        normalize_output(context, stored, auth, **proof)


@pytest.mark.parametrize('mutation',['duplicate','hybrid','wrong_role','missing'])
def test_semantic_plan_request_codec_has_no_historical_fallback(mutation):
    import json
    from tests.test_surface_native_writer import authorize
    context, record, work, host, _, _, _, proof = semantic_plan_produce()
    body = json.loads(proof['prepared_request_json'])
    if mutation == 'duplicate': body['input'].append(deepcopy(body['input'][1]))
    elif mutation == 'hybrid': body['input'].append(dict(role='user',content=json.dumps(host)))
    elif mutation == 'wrong_role': body['input'][1]['role'] = 'developer'
    else: body['input'] = body['input'][:1]
    raw = json.dumps(body)
    stored, auth = authorize(context, record, raw, model_frame(context, record))
    with pytest.raises(ValueError):
        verify_input_records(context, stored, auth, raw, **work)


def test_plan_view_keeps_host_looking_literals_and_duplicate_text_as_distinct_blocks():
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    from tests.test_surface_native_work_input import work_case
    context, record, work = work_case('plan')
    host = model_work_frame(context, record, **work)
    # Literal content is data, even when it resembles internal metadata or JSON.
    literal = 'source_run_id=550e8400-e29b-41d4-a716-446655440000; ' + 'f'*64
    host['dialogue_reference'][0]['content'] = literal
    host['current_page_draft']['markdown'] = literal
    host['committed_plan_blocks'][1]['text'] = host['committed_plan_blocks'][0]['text']
    view = semantic_frame(host, record)
    assert view['dialogue_reference'][0]['content'] == literal
    assert view['current_page_draft']['markdown'] == literal
    first, second = view['committed_plan_blocks'][:2]
    assert first['text'] == second['text'] and first['selection_id'] != second['selection_id']
    host['current_page_draft'] = dict(state='same_as_committed',primary_authoring_context=True,
        body_path=['committed_plan_blocks'])
    assert semantic_frame(host,record)['current_page_draft'] == dict(state='same_as_committed',
        primary_authoring_context=True,uses_committed_plan=True)


@pytest.mark.parametrize('authoring',[False,True])
def test_current_plan_producer_uses_local_work_in_context_and_output_schema(authoring):
    import json
    from types import SimpleNamespace
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from tests.test_surface_native_work_input import work_case
    from tests.test_plan_writer_output_schema import rules
    context,record,work=work_case('plan',draft=authoring)
    turn=SimpleNamespace(graph_context_receipt=context,graph_context_execution=record,
        **{key:value for key,value in work.items() if key!='work_proof'})
    adapter=SimpleNamespace(fence=SimpleNamespace(turn=turn),_broker_execution=lambda:record,
        budget={'outputReserveTokens':4096,'contextLimitTokens':128000})
    writer=PlanJevWriter(adapter,work['work_proof'],SimpleNamespace(frame=rules,
        authoring=object() if authoring else None))
    assert writer.provider_work['requested_work']==('write_current_page' if authoring else 'discuss')
    wire=json.dumps({'input':writer.messages,'text':{'format':writer.output_format}})
    assert writer.work_frame['authored_sources'][0]['handle'] not in wire
    assert writer.work_frame['committed_plan_blocks'][0]['selection_id'] not in wire
    assert 'work0' in wire and 'schema' not in writer.provider_work
    assert writer.work_frame['session_evidence'][0]['run_id'] not in wire
    raw=asyncio.run(actual_sdk_request(writer.provider_frame,work_frame=writer.provider_work))
    stored,grant=authorize(context,record,raw,writer.provider_frame)
    assert verify_input_records(context,stored,grant,raw,**work).authored_local


@pytest.mark.parametrize('status',['unread','partial','complete'])
def test_plan_selected_reference_labels_do_not_disclose_host_identity_or_claim_read_support(monkeypatch,status):
    import json
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state.agent_conversation import authored_graph_references as refs
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    from tests.test_surface_native_work_input import work_case
    context,record,work=work_case('plan')
    host=model_work_frame(context,record,**work)
    reference=refs.AuthoredGraphReferenceV1(managed_world_id='private-managed',native_world_id='private-native',
        binding_version=1,graph_revision='rev:private',node_id='private-node',label='The selected lighthouse')
    selected=refs.AuthoredGraphReferencesV1(references=(reference,))
    monkeypatch.setattr(refs,'native_references',lambda execution:selected)
    events=[] if status=='unread' else [refs.BuildAuthoredReferenceReadV2(
        event_id=uuid4(),sequence=0,capture_event_id=uuid4(),authorization_event_id=uuid4(),node_id=reference.node_id,
        statement_reads=(),assertion_reads=(),unavailable_statement_ids=('unavailable',) if status=='partial' else (),
        unavailable_assertion_ids=(),status=status)]
    view=semantic_frame(host,SimpleNamespace(events=events))
    assert view['selected_references']==[dict(reference='reference0',label=reference.label,
        kind='object',read_status=status)]
    assert all(secret not in json.dumps(view) for secret in ('private-managed','private-native','rev:private','private-node'))


def test_plan_source_reference_extent_is_navigation_only_until_its_native_read(monkeypatch):
    from types import SimpleNamespace
    from application_state.agent_conversation import authored_graph_references as refs
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    from tests.test_surface_native_work_input import work_case
    context,record,work=work_case('plan')
    host=model_work_frame(context,record,**work)
    reference=refs.AuthoredSourceReferenceV1(managed_world_id='private-managed',native_world_id='private-native',
        binding_version=1,knowledge_revision='rev:private',source_artifact_id='private-artifact',
        source_revision_id='private-revision',evidence_ref_id='private-evidence',content_sha256='a'*64,
        selection_kind='section',section_id='b'*64,label='Session 20 — arrival')
    native=model_frame(context,record)
    monkeypatch.setattr(refs,'native_references',lambda execution:refs.AuthoredReferencesV2(references=(reference,)))
    view=semantic_frame(host,SimpleNamespace(events=[]))
    assert view['selected_references']==[dict(reference='reference0',label=reference.label,
        kind='source',read_status='unread',extent='section')]
    # These navigation slots never enter the authored-excerpt enum.
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from tests.test_plan_writer_output_schema import rules
    import json
    output=json.dumps(native_output_format(native,rules(),host|view))
    assert 'reference0' not in output


def test_play_authored_local_aliases_resolve_exact_run_work_without_host_prompt_fields():
    from uuid import uuid4
    from tests.test_surface_native_context import native_play_supplied
    from application_state.agent_conversation.native_play_work import (
        project_work,semantic_frame,frame_in_request,producing_authored_records)
    from application_state.agent_conversation.surface_evidence_answer import authored_block_index,authored_selected_segment
    import json
    work,provenance,proof=native_play_supplied(note='A saved possibility.\n\nStill unresolved.')
    submission=uuid4()
    host=project_work(work,provenance,submission,proof)
    semantic=semantic_frame(host)
    packet={'input':[{'role':'user','content':json.dumps(semantic)}]}
    assert frame_in_request(packet)==semantic
    sources=producing_authored_records(work,provenance,host,submission)
    blocks,selectors=authored_block_index(sources,str(submission),local=True)
    expected=[block['text'] for source in semantic['current_play'] for block in source['text_blocks']]
    assert [blocks[selectors[f'work{i}']][1].text for i in range(len(selectors))]==expected
    for i in range(len(selectors)):
        segment=authored_selected_segment({'kind':'authored_excerpt','selection_id':f'work{i}'},
            blocks=blocks,selectors=selectors,selected_blocks=set())
        assert segment.source_kind=='play' and segment.text==expected[i]
    for changed in [dict(packet,input=packet['input']*2),
            {'input':[{'role':'user','content':json.dumps(host)}]},
            {'input':[{'role':'assistant','content':json.dumps(semantic)}]}]:
        with pytest.raises(ValueError):frame_in_request(changed)
    altered=deepcopy(host);altered['source_frame']['sources'][0]['text_blocks'][0]['text']='Changed body.'
    with pytest.raises(ValueError):producing_authored_records(work,provenance,altered,submission)


def test_play_output_schema_offers_only_included_local_work_selections():
    from uuid import uuid4
    from tests.test_surface_native_context import native_play_supplied
    from tests.test_surface_native_execution import component
    from application_state.agent_conversation.native_play_work import project_work,semantic_frame
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1
    work,provenance,proof=native_play_supplied(note='Retained note.')
    host=project_work(work,provenance,uuid4(),proof)
    context,execution=component('play',unavailable=True)
    frame=model_frame(context,execution)
    rules=model_rules_frame(PlanRulesEvidenceFrameV1(schema='dmb_plan_rules_evidence_v1',ruleset='synthetic',lookups=(),supports=()))
    schema=native_output_format(frame,rules,host|semantic_frame(host))['schema']
    variants=schema['properties']['answer_segments']['items']['anyOf']
    selected=next(v for v in variants if v['properties']['kind'].get('const')=='authored_excerpt'
        or v['properties']['kind'].get('enum')==['authored_excerpt'])
    assert selected['properties']['selection_id']['enum']==['work0','work1']


def test_play_actual_sdk_work_proof_requires_original_receipt_and_exact_semantic_frame():
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.play_graph_authority import play_source_frame
    from application_state.agent_conversation.native_play_work import semantic_frame
    from tests.test_surface_native_execution import component,decision_prefix,choice,execution
    context,record=component('play',unavailable=True)
    data=context.model_dump(mode='json',by_alias=True)
    data['assembled_input']['tokenizer_name']='synthetic'
    from tests.test_surface_native_context import seal
    context=type(context).model_validate_json(__import__('json').dumps(seal(data)))
    record=execution(context.context_receipt_sha256,record.policy)
    prefix,active=decision_prefix('play',context,record)
    prefix.append(choice(context,record,active,len(prefix),'finish_retrieval'))
    record=execution(context.context_receipt_sha256,record.policy,prefix)
    work=work_submission(context,record)
    basis=context.work_context.play_basis
    source=play_source_frame((t.PlaySourcePayloadV1(source_kind='current_moment',
        locator=t.play_source_locator(basis),text='Exact saved Play moment.'),))
    work.update(play_context_receipt=basis,work_proof=dict(
        source_frame=source.model_dump(mode='json',by_alias=True),session_evidence=[],dialogue=[]))
    frame=model_frame(context,record)
    host=model_work_frame(context,record,**work)
    view=semantic_frame(host)
    raw=asyncio.run(actual_sdk_request(frame,work_frame=view))
    stored,grant=authorize(context,record,raw,frame)
    verified=verify_input_records(context,stored,grant,raw,**work)
    assert verified.authored_local and [s.text for s in verified.authored]==['Exact saved Play moment.']
    with pytest.raises(ValueError,match='exact retained Run snapshot'):
        verify_input_records(context,stored,grant,raw,**(work|{'play_context_receipt':None}))
    for altered in [host,dict(view,current_play=[])]:
        bad=asyncio.run(actual_sdk_request(frame,work_frame=altered))
        record2,grant2=authorize(context,record,bad,frame)
        with pytest.raises(ValueError):verify_input_records(context,record2,grant2,bad,**work)


def test_play_retrieval_has_one_dialogue_location_and_rejects_divergent_host_copy():
    from uuid import uuid4
    from tests.test_surface_native_context import native_play_supplied
    from application_state.agent_conversation.native_play_work import project_work
    from application_state.agent_conversation.jev_retrieval_contract import NativePlayRetrievalDecisionInputV1,prepare_decision
    work,provenance,proof=native_play_supplied(note='Saved note.')
    proof['dialogue']=[dict(role='user',content='A unique prior request.'),
        dict(role='assistant',content='A unique prior reply.')]
    host=project_work(work,provenance,uuid4(),proof)
    args=dict(request_id=uuid4(),parent_attempt_id=uuid4(),scope_sha256='0'*64,
        question='What is here?',dialogue=tuple(proof['dialogue']),candidates=(),examined_candidates=(),
        allowed_operations=('select_candidates','finish_retrieval'),source_authority_status='unavailable',
        source_revision=None,graph_revision=None,play_work=host)
    parent=NativePlayRetrievalDecisionInputV1(**args)
    state=prepare_decision(parent).state
    assert state['dialogue_reference']==proof['dialogue']
    assert 'dialogue_reference' not in state['surface_work']
    assert str(state).count('A unique prior request.')==str(state).count('A unique prior reply.')==1
    for changed in [[],[dict(role='user',content='Substituted previous request.')]]:
        with pytest.raises(ValueError,match='actual retrieval parent'):
            NativePlayRetrievalDecisionInputV1(**(args|{'play_work':host|{'dialogue':changed}}))
