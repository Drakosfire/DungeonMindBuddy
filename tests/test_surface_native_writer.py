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


def body_case(surface, lane, *, failed=False, full=False, all_sections=False):
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
        matches=tuple(corpus.NativeBodySectionMatchV1(catalog_sha256=catalog.catalog_sha256,
            section_id=section.section_id, matched_terms=('check',))
            for section in (catalog.sections if all_sections else catalog.sections[:1])))
    events.append(search)
    active = controller(surface, policy, sequence=len(events), semantic=False)
    events.extend([active, *outcomes(active, len(events)+1)])
    sections = catalog.sections if all_sections else catalog.sections[:1]
    handles = [corpus.native_full_document_handle(catalog.catalog_sha256) if full else
        corpus.native_body_handle(catalog.catalog_sha256, section.section_id) for section in sections]
    events.append(choice(context, record, active, len(events), 'select_candidates', handles))
    for section in sections:
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


async def actual_sdk_request(frame, *, model='gpt-6-luna', work_frame=None, output_limit=4096):
    sent = []
    def wire(request):
        sent.append(request.content.decode())
        return httpx.Response(200, request=request, json={'id':'resp_synthetic', 'object':'response',
            'created_at':1, 'model':model, 'status':'completed', 'output':[]})
    async with AsyncOpenAI(api_key='synthetic-not-secret', http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(wire))) as client:
        await client.responses.create(model=model, input=[dict(role='user',content=json.dumps(value))
            for value in ([frame] if work_frame is None else [frame,work_frame])],
            tools=[], stream=False, **({} if output_limit is None else {"max_output_tokens":output_limit}))
    assert len(sent) == 1
    return sent[0]


def authorize(context, record, raw, frame):
    surface = record.policy.action.surface_id
    from application_state.agent_conversation.native_execution import native_read_event_ids
    from application_state.agent_conversation.native_writer import json_container_count
    body = json.loads(raw)
    reads = native_read_event_ids(record.events)
    auth = native_writer(surface, record.policy, sequence=len(record.events), read_ids=reads).model_copy(update={
        'envelope_sha256':sha256(raw.encode()).hexdigest(), 'frame_sha256':t.canonical_sha256(frame),
        'tool_schema_sha256':t.canonical_sha256([]),
        'input_tokens':len(raw.encode())+64*(1+json_container_count(body)),
        'output_token_reserve':body['max_output_tokens']})
    events=list(record.events)
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
    acknowledged = outcomes(auth, len(stored.events))
    # The actual synthetic SDK response above contains no assistant output.
    acknowledged[-1] = acknowledged[-1].model_copy(update={
        'request_id':'resp_synthetic','response_sha256':sha256(b'').hexdigest()})
    finished = execution(context.context_receipt_sha256, stored.policy,
        [*stored.events, *acknowledged])
    assert verify_input_records(context, finished, auth, raw,**work) == supports


@pytest.mark.parametrize('surface', ['build','plan'])
def test_individually_authorized_sections_can_cover_the_complete_source(lane, surface):
    context, record, _ = body_case(surface, lane, all_sections=True)
    reads = corpus.acquired_body_reads(record)
    assert len(reads) == 2
    assert ''.join(read.excerpt.text for read in reads) == BODY
    assert all(read.excerpt.selector_policy == 'markdown_sections_v1' for read in reads)
    frame = model_frame(context, record)
    work = work_submission(context, record)
    raw = asyncio.run(actual_sdk_request(frame, work_frame=model_work_frame(context, record, **work)))
    stored, authorization = authorize(context, record, raw, frame)
    supports = verify_input_records(context, stored, authorization, raw, **work)
    assert len(authorization.native_read_event_ids) == len(reads)
    assert set(authorization.native_read_event_ids) == {read.event_id for read in reads}
    assert {support.read.event_id: support.read for support in supports.body_excerpts} == {
        read.event_id: read for read in reads}
    assert all(row['extent_kind'] == 'section' for row in frame['native_body_evidence']['excerpts'])
    assert 'The check revealed' in raw and 'Unselected private context.' in raw


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
def published_lane(application_state_dsn, tmp_path, monkeypatch, request):
    from tests.test_source_statements import make_lane, commit
    from tests.test_native_plan_assertions import publish
    value = make_lane(tmp_path, monkeypatch, narrow=True)
    from dataclasses import replace
    from tests.test_source_statements import wk
    value.meta = replace(value.meta,domain_metadata=(wk.DomainMetadata.from_json(
        'dungeonbuddy.domain_metadata:world_context_v1',
        getattr(request,'param',{'uncertain':['who reported it']})),))
    commit(value)
    publish(value, qualified=True)
    return value


def published_case(surface, lane):
    from tests.test_native_plan_statements import query
    from tests.test_source_statements import GM
    from apps.live_control_server.services.native_graph_reads import read_selected
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
    from application_state.agent_conversation.native_plan_assertions import object_selection_handle
    handles = [object_selection_handle(result, m.entity_id) for m in result.object_matches]
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
        assert 'evidence' not in row and 'supporting_sources' not in row
    assert any(r.assertion.metadata.claim_mode == 'dungeonbuddy.claim:belief'
        and r.assertion.metadata.epistemic_basis == 'speculative'
        for _,_,r in supports.native_assertions)
    assert frame['native_body_evidence']['source_authority_status'] == 'unavailable'
    assert frame['native_statements']['status'] == frame['native_assertions']['status'] == 'complete'


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_semantic_native_evidence_preserves_qualifiers_and_reopens_original_citations(
    published_lane, surface, monkeypatch
):
    from application_state.agent_conversation.native_writer import model_input_frame
    from application_state.agent_conversation.native_completion import normalize_output
    from application_state.agent_conversation.plan_writer_output_schema import (
        _native_variants,
    )
    from tests import test_surface_native_completion as completion

    context, record = published_case(surface, published_lane)
    host = model_frame(context, record)
    frame = model_input_frame(context, record)
    assert set(frame) == {
        "input_status",
        "user_question",
        "native_body_evidence",
        "native_statements",
        "native_assertions",
    }
    encoded = json.dumps(frame)
    from application_state.agent_conversation.native_evidence_view import output_frame
    inline = output_frame({}, frame)
    for row in host["native_assertions"]["assertions"]:
        assert row["assertion_handle"] not in encoded
        assert row["assertion"]["assertion_id"] not in encoded
        assert row["assertion"]["subject_entity_id"] not in encoded
    for old, new in zip(
        host["native_assertions"]["assertions"],
        inline["native_assertions"]["assertions"],
        strict=True,
    ):
        for key in (
            "scope",
            "epistemic_basis",
            "claim_mode",
            "standing",
            "temporal_scope",
        ):
            assert (
                new["assertion"]["metadata"][key] == old["assertion"]["metadata"][key]
            )
        assert new["assertion"]["metadata"]["domain_metadata"] == [
            {"world_context": entry["payload"]}
            if entry["schema"] == "dungeonbuddy.domain_metadata:world_context_v1" else entry
            for entry in old["assertion"]["metadata"]["domain_metadata"]]
        assert (
            "evidence_ref_ids" not in new["assertion"]["metadata"]
            and "visibility" not in new["assertion"]["metadata"]
        )
    for old, new in zip(
        host["native_statements"]["statements"],
        frame["native_statements"]["statements"],
        strict=True,
    ):
        for key in (
            "quote",
            "meaning",
            "mode",
            "uncertainty",
            "qualifications",
            "episode",
            "embedded_content_factive",
        ):
            assert new["payload"][key] == old["payload"][key]
        assert (
            old["source_artifact_id"] not in encoded
            and old["source_revision_id"] not in encoded
        )
        assert old["payload"]["reporter"] not in encoded
    variants = _native_variants(
        host["answer_policy"],
        {"type": "string"},
        statement_rows=frame["native_statements"]["statements"],
        assertion_rows=frame["native_assertions"]["assertions"],
        body_rows=frame["native_body_evidence"]["excerpts"],
    )
    assert all(
        row["assertion_handle"] not in json.dumps(variants)
        for row in host["native_assertions"]["assertions"]
    )
    monkeypatch.setattr(completion, "model_frame", model_input_frame)
    candidate = completion.answer(
        [
            dict(
                kind="native_statement_report",
                text="A reports that B fled, with uncertainty.",
                statement_handles=["statement0"],
            ),
            dict(
                kind="native_assertion_claim",
                text="The Graph retains a qualified account.",
                assertion_handles=["assertion0"],
            ),
        ]
    )
    stored, auth, proof = completion.producing_case(context, record, candidate)
    result = normalize_output(context, stored, auth, **proof)
    assert result.native_clause_citations and result.native_assertion_citations
    assert (
        result.native_assertion_citations[0].assertion_id
        == host["native_assertions"]["assertions"][0]["assertion"]["assertion_id"]
    )
    assert all(
        c.provider_attempt_id == auth.provider_attempt_id
        for c in result.native_assertion_citations
    )


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_semantic_body_aliases_are_input_local_and_cannot_select_unexposed_reads(
    lane, surface, monkeypatch
):
    from application_state.agent_conversation.native_writer import model_input_frame
    from application_state.agent_conversation.native_completion import normalize_output
    from tests import test_surface_native_completion as completion

    context, record, read = body_case(surface, lane)
    frame = model_input_frame(context, record)
    assert frame["native_body_evidence"]["excerpts"][0]["excerpt_handle"] == "body0"
    assert read.excerpt.catalog_sha256 not in json.dumps(frame)
    monkeypatch.setattr(completion, "model_frame", model_input_frame)
    for selector, valid in [
        ("body0", True),
        ("body999", False),
        (
            model_frame(context, record)["native_body_evidence"]["excerpts"][0][
                "excerpt_handle"
            ],
            False,
        ),
    ]:
        candidate = completion.answer(
            [
                dict(
                    kind="native_body_claim",
                    text="The check revealed an origin beyond this plane.",
                    excerpt_handles=[selector],
                )
            ]
        )
        stored, auth, proof = completion.producing_case(context, record, candidate)
        if valid:
            result = normalize_output(context, stored, auth, **proof)
            assert result.native_body_citations[0].read_event_id == read.event_id
        else:
            with pytest.raises(ValueError, match="excerpt selections"):
                normalize_output(context, stored, auth, **proof)


@pytest.mark.parametrize(
    "mutation",
    [
        "text",
        "hybrid",
        "duplicate",
        "unknown",
        "integer",
        "role",
        "competing_legacy",
        "unknown_schema",
    ],
)
def test_semantic_native_frame_tampering_fails_correlated_input_proof(lane, mutation):
    from application_state.agent_conversation.native_writer import model_input_frame

    context, record, _ = body_case("build", lane)
    frame = model_input_frame(context, record)
    work = work_submission(context, record)
    raw = asyncio.run(
        actual_sdk_request(frame, work_frame=model_work_frame(context, record, **work))
    )
    value = json.loads(raw)
    if mutation == "text":
        frame["native_body_evidence"]["excerpts"][0]["text"] = "Different evidence"
    elif mutation == "hybrid":
        frame["schema"] = "dmb_surface_native_writer_evidence_v2"
    elif mutation == "unknown":
        frame["unknown"] = "ignored?"
    elif mutation == "integer":
        frame["native_body_evidence"]["excerpts"][0]["line_start"] = True
    elif mutation == "role":
        value["input"][0]["role"] = "developer"
    elif mutation == "competing_legacy":
        value["input"].append(
            dict(role="user", content=json.dumps(model_frame(context, record)))
        )
    elif mutation == "unknown_schema":
        frame["schema"] = "unrecognized_world_evidence"
    value["input"][0]["content"] = json.dumps(frame)
    if mutation == "duplicate":
        value["input"].append(deepcopy(value["input"][0]))
    raw = json.dumps(value)
    stored, auth = authorize(context, record, raw, frame)
    with pytest.raises(ValueError):
        verify_input_records(context, stored, auth, raw, **work)


@pytest.mark.parametrize("failed", [False, True])
def test_semantic_multiple_or_missing_body_extents_remain_truthful(lane, failed):
    from application_state.agent_conversation.native_writer import model_input_frame

    context, record, _ = body_case("build", lane, all_sections=True, failed=failed)
    frame = model_input_frame(context, record)
    assert frame["input_status"] == "partial"
    assert frame["native_body_evidence"]["universal_absence_claimed"] is False
    assert [
        row["excerpt_handle"] for row in frame["native_body_evidence"]["excerpts"]
    ] == ([] if failed else ["body0", "body1"])
    if not failed:
        assert (
            "".join(row["text"] for row in frame["native_body_evidence"]["excerpts"])
            == BODY
        )


@pytest.mark.parametrize("family", ["statement", "assertion"])
def test_semantic_projection_refuses_unclassified_qualification(published_lane, family):
    from application_state.agent_conversation.native_evidence_view import semantic_frame

    context, record = published_case("build", published_lane)
    frame = model_frame(context, record)
    if family == "statement":
        frame["native_statements"]["statements"][0]["payload"]["new_semantic_field"] = (
            "must classify"
        )
    else:
        frame["native_assertions"]["assertions"][0]["assertion"]["metadata"][
            "new_semantic_field"
        ] = "must classify"
    with pytest.raises(ValueError, match="Unclassified"):
        semantic_frame(frame)


def test_semantic_world_qualification_separates_only_typed_publisher_provenance(
    published_lane,
):
    from application_state.agent_conversation.native_evidence_view import semantic_frame, output_frame

    context, record = published_case("build", published_lane)
    host = model_frame(context, record)
    descriptor = dict(
        schema_version="dmb_candidate_description_extent_v1",
        run_id="HOST-RUN-SENTINEL",
        run_revision=3,
        candidate_sha256="HOST-CANDIDATE-SENTINEL",
        record_id="HOST-RECORD-SENTINEL",
        field="description",
        start_byte=1,
        end_byte=9,
        slice_sha256="HOST-SLICE-SENTINEL",
        whole_field_selected=False,
    )
    payload = {
        "uncertain": ["who reported it"],
        "candidate_description_selection": descriptor,
    }
    metadata = host["native_assertions"]["assertions"][0]["assertion"]["metadata"]
    metadata["domain_metadata"] = [
        dict(
            schema="dungeonbuddy.domain_metadata:world_context_v1", payload=payload
        )
    ]
    before = deepcopy(host)
    frame = semantic_frame(host)
    assert host == before
    assert output_frame({}, frame)["native_assertions"]["assertions"][0]["assertion"]["metadata"][
        "domain_metadata"
    ] == [
        dict(world_context={"uncertain": ["who reported it"]})
    ]
    assert "HOST-" not in json.dumps(frame)
    # Similar user data without the publisher's type tag is semantic, not a blacklist hit.
    payload["candidate_description_selection"] = {
        "note": "Keep these literal words and IDs"
    }
    assert (
        output_frame({}, semantic_frame(host))["native_assertions"]["assertions"][0]["assertion"][
            "metadata"
        ]["domain_metadata"][0]["world_context"]
        == payload
    )


def _captured_world_context_cases():
    from pathlib import Path
    return json.loads((Path(__file__).parent / "fixtures" /
        "native_world_context_review_metadata.json").read_text())["cases"]


@pytest.mark.parametrize("case", _captured_world_context_cases(), ids=lambda c:c["case"])
def test_world_context_presentation_omits_only_proven_host_slots(case):
    from application_state.agent_conversation.native_evidence_view import _domain_meaning
    payload = deepcopy(case["payload"])
    literal = {"source_run_id":"a literal character name", "future_manifest_sha256":"c"*64}
    payload.update(unknown_host_looking_sha256="d"*64, notes=literal)
    original = [dict(schema="dungeonbuddy.domain_metadata:world_context_v1",payload=payload),
        dict(schema="custom:authored-context",payload=deepcopy(payload)),
        dict(schema="dungeonbuddy.domain_metadata:world_context_v1",payload=[literal,"source_run_id"])]
    before = deepcopy(original)
    projected = _domain_meaning(original)
    expected = {key:value for key,value in payload.items() if key not in case["host_fields"]}
    assert projected == [dict(world_context=expected), original[1], dict(world_context=original[2]["payload"])]
    assert original == before
    assert projected[0]["world_context"]["source_qualification"] == payload["source_qualification"]
    assert _domain_meaning([dict(schema=original[0]["schema"],payload={
        key:payload[key] for key in case["host_fields"]})]) == ([] if case["host_fields"] else [
            dict(world_context={})])


_ALL_HOST_REVIEW_FIELDS = {key:value for case in _captured_world_context_cases()
    for key,value in case["payload"].items()}
_ALL_HOST_REVIEW_FIELDS.update(uncertain=["who reported it"],
    unknown_host_looking_sha256="e"*64, notes={"source_run_id":"literal story words"})


@pytest.mark.parametrize("surface", ["build","plan"])
@pytest.mark.parametrize("published_lane", [_ALL_HOST_REVIEW_FIELDS], indirect=True)
def test_actual_sdk_world_context_roles_preserve_exact_host_reads(published_lane,surface):
    from application_state.agent_conversation.native_writer import model_input_frame
    context, record = published_case(surface,published_lane)
    frame = model_input_frame(context,record)
    before = record.model_dump_json(by_alias=True)
    work = work_submission(context,record)
    raw = asyncio.run(actual_sdk_request(frame,work_frame=model_work_frame(context,record,**work)))
    from application_state.agent_conversation.native_evidence_view import (
        semantic_frame_in_request, world_context_representation)
    actual = semantic_frame_in_request(json.loads(raw), legacy_schemas=())
    assert actual == frame and world_context_representation(actual) == "current"
    stored, grant = authorize(context,record,raw,frame)
    accepted = verify_input_records(context,stored,grant,raw,**work)
    assert accepted.native_assertions
    for _, _, read in accepted.native_assertions:
        for item in read.assertion.metadata.domain_metadata:
            if item.schema_term == "dungeonbuddy.domain_metadata:world_context_v1":
                assert item.payload["ingestion_code_head"] == "b"*40
    from application_state.agent_conversation.native_evidence_view import output_frame
    for row in output_frame({}, frame)["native_assertions"]["assertions"]:
        for item in row["assertion"]["metadata"]["domain_metadata"]:
            assert set(item) == {"world_context"}
            assert item["world_context"] == {key:_ALL_HOST_REVIEW_FIELDS[key] for key in
                ("source_qualification","uncertain","unknown_host_looking_sha256","notes")}
    assert record.model_dump_json(by_alias=True) == before


def test_world_context_reader_classifies_slots_without_scrubbing_literal_text():
    from application_state.agent_conversation.native_evidence_view import (
        world_context_representation)
    marker = "dungeonbuddy.domain_metadata:world_context_v1"
    def packet(entries):
        return {"native_assertions": {"assertions": [{"assertion": {
            "metadata": {"domain_metadata": entries}}}]}}
    literal = {"schema": marker, "payload": "literal story words"}
    assert world_context_representation(packet([
        {"world_context": {"notes": literal}},
        {"schema": "custom:authored-context", "payload": literal}])) == "current"
    assert world_context_representation(packet([
        {"schema": marker, "payload": [literal]}])) == "historical"
    with pytest.raises(ValueError, match="Mixed"):
        world_context_representation(packet([
            {"world_context": literal}, {"schema": marker, "payload": literal}]))
    with pytest.raises(ValueError, match="Malformed"):
        world_context_representation(packet([{"world_context": {}, "payload": {}}]))
    assert world_context_representation({"native_assertions": None}) == "current"


@pytest.mark.parametrize("surface", ["build", "plan"])
@pytest.mark.parametrize("historical", [False, True])
def test_world_context_current_and_historical_exact_sdk_bindings(published_lane, surface, historical):
    from application_state.agent_conversation.native_writer import model_input_frame
    from application_state.agent_conversation.native_evidence_view import output_frame
    context, record = published_case(surface, published_lane)
    frame = model_input_frame(context, record)
    if historical:
        frame = output_frame({}, frame)
        for row in frame["native_assertions"]["assertions"]:
            entries = row["assertion"]["metadata"]["domain_metadata"]
            for index, entry in enumerate(entries):
                if set(entry) == {"world_context"}:
                    entries[index] = {"schema": "dungeonbuddy.domain_metadata:world_context_v1",
                        "payload": entry["world_context"]}
    before = record.model_dump_json(by_alias=True)
    work = work_submission(context, record)
    raw = asyncio.run(actual_sdk_request(frame, work_frame=model_work_frame(context, record, **work)))
    stored, grant = authorize(context, record, raw, frame)
    assert verify_input_records(context, stored, grant, raw, **work).native_assertions
    assert record.model_dump_json(by_alias=True) == before
    # A self-consistent request/hash cannot replace exact admitted qualifications.
    changed = deepcopy(frame)
    entry = next(entry for row in output_frame({}, changed)["native_assertions"]["assertions"]
        for entry in row["assertion"]["metadata"]["domain_metadata"]
        if (entry.get("schema") == "dungeonbuddy.domain_metadata:world_context_v1"
            if historical else set(entry) == {"world_context"}))
    entry["payload" if historical else "world_context"] = {"uncertain": ["invented certainty"]}
    altered = asyncio.run(actual_sdk_request(changed, work_frame=model_work_frame(context, record, **work)))
    altered_record, altered_grant = authorize(context, record, altered, changed)
    with pytest.raises(ValueError, match="evidence differs"):
        verify_input_records(context, altered_record, altered_grant, altered, **work)

    # Historical and current forms may not be mixed, even with self-consistent hashes.
    mixed = deepcopy(frame)
    entries = next(row["assertion"]["metadata"]["domain_metadata"]
        for row in output_frame({}, mixed)["native_assertions"]["assertions"]
        if any((entry.get("schema") == "dungeonbuddy.domain_metadata:world_context_v1"
            if historical else set(entry) == {"world_context"})
            for entry in row["assertion"]["metadata"]["domain_metadata"]))
    known = next(entry for entry in entries if
        (entry.get("schema") == "dungeonbuddy.domain_metadata:world_context_v1"
            if historical else set(entry) == {"world_context"}))
    entries.append({"world_context": known["payload"]} if historical else
        {"schema": "dungeonbuddy.domain_metadata:world_context_v1", "payload": known["world_context"]})
    mixed_raw = asyncio.run(actual_sdk_request(mixed, work_frame=model_work_frame(context, record, **work)))
    mixed_record, mixed_grant = authorize(context, record, mixed_raw, mixed)
    with pytest.raises(ValueError, match="Mixed"):
        verify_input_records(context, mixed_record, mixed_grant, mixed_raw, **work)


@pytest.mark.parametrize("old_revision", ["20261108_0131", "20261108_0132", "20261108_0133"])
def test_old_readers_refuse_world_projection_database(application_state_dsn, monkeypatch, old_revision):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    cli.assert_at_head(dsn=application_state_dsn)
    assert cli._read_current_revision(application_state_dsn) == "20261108_0134"
    monkeypatch.setattr(cli, "_alembic_head", lambda: old_revision)
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn=application_state_dsn)
