"""Actual SDK bytes + shared record proof; no APP activation or real providers."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import native_corpus as corpus
from application_state.agent_conversation.native_writer import model_frame, model_work_frame, verify_input_records
from tests.test_native_corpus_source_access import lane as lane, admit, capture
from tests.test_surface_native_context import seal, provenance_for, WORK_MARKDOWN
from tests.test_surface_native_execution import (
    component, execution, controller, decision_prefix, outcomes, choice, native_writer, BUILD_TURN_ID,
)

BODY = '# Source\n\nThe check revealed an origin beyond this plane.\n\n## Other scene\nUnselected private context.\n'


def body_case(surface, lane, *, failed=False, full=False):
    admit(lane, body=BODY)
    sources = capture(lane)
    catalog = corpus.build_native_body_catalog(sources.authority, sources.members[0], BODY)
    context, record = component(surface, unavailable=True)
    data = context.model_dump(mode='json', by_alias=True)
    basis = 'source_basis' if surface == 'build' else 'plan_basis'
    data['work_context'][basis]['world_id'] = 'managed'
    data['native_query']['managed_world_id'] = 'managed'
    data['source_authority'] = sources.authority.model_dump(mode='json')
    first = controller(surface, record.policy)
    data['assembled_input']['tokenizer_name'] = first.input_estimator
    work=type(context.work_context).model_validate(data['work_context'])
    data['provenance_sha256']=t.canonical_sha256(provenance_for(work).model_copy(
        update={'surface_instance_id':surface+':one'}))
    context = type(context).model_validate_json(json.dumps(seal(data)))
    intent = record.policy.action.intent.model_copy(update={'world_id':'managed'})
    if surface == 'build':
        intent = intent.model_copy(update={'graph_request':intent.graph_request.model_copy(update={'world_id':'managed'})})
    action = record.policy.action.model_copy(update={'intent':intent})
    policy = record.policy.model_copy(update={'action':action,
        'source_authority_sha256':t.canonical_sha256(context.source_authority),
        'native_query_sha256':t.canonical_sha256(context.native_query)})
    record = execution(context.context_receipt_sha256, policy)
    events, active = decision_prefix(surface, context, record)
    query_sha = sha256(action.intent.message.encode()).hexdigest()
    events.append(choice(context, record, active, len(events), 'select_candidates',
        [corpus.native_corpus_search_handle(query_sha)]))
    grant = corpus.NativeBodySearchAuthorizedV1(event_id=uuid4(), sequence=len(events),
        provider_attempt_id=active.provider_attempt_id, context_receipt_sha256=context.context_receipt_sha256,
        execution_policy_sha256=record.execution_policy_sha256, authority=sources.authority, query_sha256=query_sha)
    events.append(grant)
    search = corpus.NativeBodySearchObservedV1(event_id=uuid4(), sequence=len(events),
        authorization_event_id=grant.event_id, catalogs=(catalog,), unavailable_source_count=0,
        matches=(corpus.NativeBodySectionMatchV1(catalog_sha256=catalog.catalog_sha256,
            section_id=catalog.sections[0].section_id, matched_terms=('check',)),))
    events.append(search)
    active = controller(surface, policy, sequence=len(events), semantic=False)
    events.extend([active, *outcomes(active, len(events)+1)])
    section = catalog.sections[0]
    handle = corpus.native_full_document_handle(catalog.catalog_sha256) if full else corpus.native_body_handle(
        catalog.catalog_sha256, section.section_id)
    events.append(choice(context, record, active, len(events), 'select_candidates', [handle]))
    read_grant = corpus.NativeBodyReadAuthorizedV1(event_id=uuid4(), sequence=len(events),
        provider_attempt_id=active.provider_attempt_id, search_event_id=search.event_id,
        catalog_sha256=catalog.catalog_sha256, retrieval_kind='full_document' if full else 'section',
        section_id=None if full else section.section_id)
    events.append(read_grant)
    read = corpus.NativeBodyReadObservedV1(event_id=uuid4(), sequence=len(events),
        authorization_event_id=read_grant.event_id,
        excerpt=None if failed else corpus.select_native_full_document(catalog, BODY) if full else
            corpus.select_native_body_excerpt(catalog, BODY, section.section_id),
        failure_code='native_body_unavailable' if failed else None)
    events.append(read)
    active = controller(surface, policy, sequence=len(events), semantic=False)
    events.extend([active, *outcomes(active, len(events)+1)])
    events.append(choice(context, record, active, len(events), 'finish_retrieval'))
    return context, with_work_selection(execution(context.context_receipt_sha256, policy, events)), read


def with_work_selection(record):
    if record.policy.action.surface_id != 'build' or any(isinstance(e,t.BuildWriterEvidenceSelectionV1) for e in record.events):
        return record
    controller_event=next(e for e in reversed(record.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    vote=t.BuildWriterEvidenceSelectionV1(kind='build_writer_evidence_selection_v1',event_id=uuid4(),sequence=len(record.events),
        policy='source_unit_selection_event_closure_v1',mode='jev',controller_attempt_id=controller_event.provider_attempt_id,
        controller_envelope_sha256=controller_event.envelope_sha256,controller_response_sha256='f'*64,
        catalog_sha256='a'*64,basis_sha256='b'*64,terminal_disposition={},judgments={},requested_unit_ids=[],
        expanded_unit_ids=[],omitted_unit_ids=[],source_event_ids=[],section_read_ids=[])
    return execution(record.context_receipt_sha256,record.policy,[*record.events,vote])


def work_submission(context,record):
    provenance=provenance_for(context.work_context).model_copy(update={
        'surface_instance_id':record.policy.action.intent.surface_instance_id})
    return dict(provenance=provenance,idempotency_key=uuid4(),world_id=record.policy.action.intent.world_id,
        conversation_id=uuid4(),turn_id=BUILD_TURN_ID if record.policy.action.surface_id=='build' else uuid4(),attempt=1,work_proof=(
            dict(plan_markdown=WORK_MARKDOWN,session_evidence=[],dialogue=[]) if record.policy.action.surface_id=='plan' else {}))


async def actual_sdk_request(frame, *, model='gpt-6-luna', work_frame=None):
    sent = []
    def wire(request):
        sent.append(request.content.decode())
        return httpx.Response(200, request=request, json={'id':'resp_synthetic', 'object':'response',
            'created_at':1, 'model':model, 'status':'completed', 'output':[]})
    async with AsyncOpenAI(api_key='synthetic-not-secret', http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(wire))) as client:
        await client.responses.create(model=model, input=[dict(role='user',content=json.dumps(value))
            for value in ([frame] if work_frame is None else [frame,work_frame])],
            tools=[], stream=False, max_output_tokens=4096)
    assert len(sent) == 1
    return sent[0]


def authorize(context, record, raw, frame):
    surface = record.policy.action.surface_id
    reads = tuple(sorted((e.event_id for e in record.events if isinstance(e, (
        t.NativeBodyReadObservedV1, t.NativePlanStatementReadObservedV1, t.NativePlanAssertionReadObservedV1))), key=str))
    auth = native_writer(surface, record.policy, sequence=len(record.events), read_ids=reads).model_copy(update={
        'envelope_sha256':sha256(raw.encode()).hexdigest(), 'frame_sha256':t.canonical_sha256(frame),
        'tool_schema_sha256':t.canonical_sha256([])})
    events=list(record.events)
    if surface=='build' and record.policy.action.related_page_catalog is not None:
        from application_state.agent_conversation.build_related_pages import records, RelatedPageInclusion
        events.append(RelatedPageInclusion(event_id=uuid4(),sequence=len(events),
            provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
            read_ids=sorted((read.read_id for read in records(record)),key=str)))
    if surface=='build':
        from application_state.agent_conversation import build_draft_context as draft, build_primary_context as primary
        if record.policy.action.intent.build_draft_context_sha256 is not None:
            captured=draft.context_record(record)
            events.append(t.BuildDraftProviderInclusionV1(kind='build_draft_provider_inclusion_v1',event_id=uuid4(),sequence=len(events),
                provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
                draft_event_id=captured.event_id,snapshot_sha256=captured.record.snapshot.snapshot_sha256))
        chosen=primary.records(record)
        if chosen:
            events.append(t.BuildSectionProviderInclusionV1(kind='build_section_provider_inclusion_v1',event_id=uuid4(),sequence=len(events),
                provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
                context_receipt_sha256=context.context_receipt_sha256,execution_policy_sha256=record.execution_policy_sha256,
                section_event_ids=sorted((row.event_id for row in chosen),key=str),sections_sha256=t.build_sections_digest(chosen)))
    auth=auth.model_copy(update={'sequence':len(events)})
    return execution(context.context_receipt_sha256, record.policy, [*events,auth]), auth


@pytest.mark.parametrize('surface', ['build','plan'])
@pytest.mark.parametrize('failed,full', [(False,False),(False,True),(True,False)])
def test_actual_sdk_native_body_input_returns_only_exact_selected_supports(lane, surface, failed, full):
    context, record, read = body_case(surface, lane, failed=failed, full=full)
    frame = model_frame(context, record)
    work=work_submission(context,record)
    raw = asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    stored, auth = authorize(context, record, raw, frame)
    supports = verify_input_records(context, stored, auth, raw,**work)
    assert supports.frame == frame
    assert supports.native_statements == supports.native_assertions == ()
    assert frame['native_statements']['status'] == 'unavailable' and frame['native_assertions'] is None
    assert frame['native_body_evidence']['source_authority_status'] == 'available'
    assert auth.native_read_event_ids == (read.event_id,)
    assert not hasattr(auth, 'native_statement_read_event_ids')
    if failed:
        assert supports.body_excerpts == () and frame['native_body_evidence']['excerpts'] == []
        assert 'The check revealed' not in raw
    else:
        (support,) = supports.body_excerpts
        assert support.read == read
        assert support.handle == frame['native_body_evidence']['excerpts'][0]['excerpt_handle']
        assert ('Unselected private context.' in raw) == full
        assert frame['native_body_evidence']['excerpts'][0]['extent_kind'] == ('full_document' if full else 'section')
    assert 'graph_records' not in frame and 'plan_markdown' not in frame
    # Later provider outcomes cannot change the already producing frame.
    finished = execution(context.context_receipt_sha256, stored.policy,
        [*stored.events, *outcomes(auth, len(stored.events))])
    assert verify_input_records(context, finished, auth, raw,**work) == supports


@pytest.mark.parametrize('surface', ['build','plan'])
@pytest.mark.parametrize('mutation', ['text','extent','integer_boolean','integer_float','missing','duplicate','tools','model','serializer','read_set','auth','bytes'])
def test_native_input_refuses_actual_sdk_and_stored_authorization_substitution(lane, surface, mutation):
    context, record, _ = body_case(surface, lane)
    frame = model_frame(context, record)
    work=work_submission(context,record)
    raw = asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    body = json.loads(raw)
    if mutation in {'text','extent'}:
        row = frame['native_body_evidence']['excerpts'][0]
        row['text' if mutation == 'text' else 'extent_kind'] = 'substituted'
        body['input'][0]['content'] = json.dumps(frame)
    elif mutation in {'integer_boolean','integer_float'}:
        row = frame['native_body_evidence']['excerpts'][0]
        assert row['line_start'] == 1
        row['line_start'] = True if mutation == 'integer_boolean' else 1.0
        body['input'][0]['content'] = json.dumps(frame)
    elif mutation == 'missing':
        body['input'] = []
    elif mutation == 'duplicate':
        body['input'].append(deepcopy(body['input'][0]))
    elif mutation == 'tools':
        body['tools'] = [{'type':'web_search'}]
    elif mutation == 'model':
        body['model'] = 'different-model'
    raw = json.dumps(body)
    stored, auth = authorize(context, record, raw, frame)
    if mutation == 'serializer':
        auth = auth.model_copy(update={'serializer_version':'canonical-json-utf8-v1'})
        stored = stored.model_copy(update={'events':[*record.events,auth]})
    elif mutation == 'read_set':
        auth = auth.model_copy(update={'native_read_event_ids':()})
        stored = stored.model_copy(update={'events':[*record.events,auth]})
    elif mutation == 'auth':
        auth = auth.model_copy(update={'event_id':uuid4()})
    elif mutation == 'bytes':
        raw += '\n'
    with pytest.raises(ValueError):
        verify_input_records(context, stored, auth, raw,**work)


@pytest.mark.parametrize('surface', ['build','plan'])
def test_frozen_source_authority_cannot_be_replaced_by_self_consistent_search(lane, surface):
    context, record, _ = body_case(surface, lane)
    events = list(record.events)
    index = next(i for i,e in enumerate(events) if isinstance(e, corpus.NativeBodySearchAuthorizedV1))
    # An unresolved search prefix is valid for persistence; its authority must
    # still match this receipt before any materializer/provider can consume it.
    original = events[index]
    events[index] = original.model_copy(update={'authority':original.authority.model_copy(update={'revision_id':'rev:foreign'})})
    with pytest.raises(ValueError, match='acknowledged current controller'):
        execution(context.context_receipt_sha256, record.policy, events[:index+1])


@pytest.fixture
def published_lane(application_state_dsn, tmp_path, monkeypatch):
    from tests.test_source_statements import make_lane, commit
    from tests.test_native_plan_assertions import publish
    value = make_lane(tmp_path, monkeypatch, narrow=True)
    commit(value)
    publish(value, qualified=True)
    return value


def published_case(surface, lane):
    from tests.test_native_plan_statements import query
    from tests.test_source_statements import GM
    from apps.live_control_server.services.native_graph_reads import read_selected
    from application_state.agent_conversation import native_plan_assertions as assertions
    from application_state.agent_conversation import native_plan_statements as statements
    prepared, result = query(lane, scope_mode='world')
    assert result.matches and result.assertion_matches
    context, record = component(surface, unavailable=True)
    data = context.model_dump(mode='json', by_alias=True)
    world = lane.world.world_id
    basis = 'source_basis' if surface == 'build' else 'plan_basis'
    data['work_context'][basis]['world_id'] = world
    data['source_authority']['managed_world_id'] = world
    data['native_query'] = result.model_dump(mode='json', by_alias=True)
    data['assembled_input']['tokenizer_name'] = controller(surface, record.policy).input_estimator
    work=type(context.work_context).model_validate(data['work_context'])
    data['provenance_sha256']=t.canonical_sha256(provenance_for(work).model_copy(
        update={'surface_instance_id':surface+':one'}))
    context = type(context).model_validate_json(json.dumps(seal(data)))
    intent = record.policy.action.intent.model_copy(update={'world_id':world,'message':result.question})
    if surface == 'build':
        intent = intent.model_copy(update={'graph_request':intent.graph_request.model_copy(update={'world_id':world})})
    action = record.policy.action.model_copy(update={'intent':intent})
    policy = record.policy.model_copy(update={'action':action,
        'source_authority_sha256':t.canonical_sha256(context.source_authority),
        'native_query_sha256':t.canonical_sha256(context.native_query)})
    record = execution(context.context_receipt_sha256, policy)
    events, active = decision_prefix(surface, context, record)
    handles = [statements.selection_handle(result, m) for m in result.matches]
    handles += [assertions.selection_handle(result, m) for m in result.assertion_matches]
    events.append(choice(context, record, active, len(events), 'select_candidates', handles))
    for grant_type, observed_type, ids_field, unavailable_field, matches, identity in (
        (t.NativePlanStatementReadAuthorizedV1,t.NativePlanStatementReadObservedV1,'statement_ids',
            'unavailable_statement_ids',result.matches,'statement_id'),
        (t.NativePlanAssertionReadAuthorizedV1,t.NativePlanAssertionReadObservedV1,'assertion_ids',
            'unavailable_assertion_ids',result.assertion_matches,'assertion_id')):
        grant = grant_type(event_id=uuid4(), sequence=len(events), provider_attempt_id=active.provider_attempt_id,
            query_sha256=result.sha256, **{ids_field:tuple(getattr(m, identity) for m in matches)})
        events.append(grant)
        reads, unavailable = read_selected(prepared, grant, GM)
        assert reads and not unavailable
        events.append(observed_type(event_id=uuid4(), sequence=len(events), authorization_event_id=grant.event_id,
            reads=reads, status='complete', **{unavailable_field:()}))
    if surface == 'plan':
        active = controller(surface, policy, sequence=len(events), semantic=False)
        events.extend([active, *outcomes(active, len(events)+1)])
        events.append(choice(context, record, active, len(events), 'finish_retrieval'))
    return context, with_work_selection(execution(context.context_receipt_sha256, policy, events))


@pytest.mark.parametrize('surface', ['build','plan'])
def test_shared_input_preserves_actual_core_statement_and_assertion_qualifications(published_lane, surface):
    context, record = published_case(surface, published_lane)
    frame = model_frame(context, record)
    work=work_submission(context,record)
    raw = asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    stored, auth = authorize(context, record, raw, frame)
    supports = verify_input_records(context, stored, auth, raw,**work)
    assert supports.body_excerpts == ()
    assert supports.native_statements and supports.native_assertions
    for handle, event, read in supports.native_statements:
        assert event.event_id in auth.native_read_event_ids
        row = next(r for r in frame['native_statements']['statements'] if r['statement_handle'] == handle)
        assert row['payload'] == read.support.payload
        assert row['payload']['embedded_content_factive'] is False
        assert row['payload']['episode'] == 'episode-1'
    for handle, event, read in supports.native_assertions:
        assert event.event_id in auth.native_read_event_ids
        row = next(r for r in frame['native_assertions']['assertions'] if r['assertion_handle'] == handle)
        assert row['assertion'] == read.assertion.model_dump(mode='json')
        assert all('text' not in span for span in row['supporting_sources'])
    assert any(r.assertion.metadata.claim_mode == 'dungeonbuddy.claim:belief'
        and r.assertion.metadata.epistemic_basis == 'speculative'
        for _,_,r in supports.native_assertions)
    assert frame['native_body_evidence']['source_authority_status'] == 'unavailable'
    assert frame['native_statements']['status'] == frame['native_assertions']['status'] == 'complete'
