"""Real Core/WK and ordinary Plan HTTP, with provider-free transport boundaries."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4
import json
from hashlib import sha256
from dungeonmind.application.vnext import publish_native_text_source_evidence, publish_native_source_evidence_extension, open_admitted_native_text
from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1, NativeSourceEvidenceExtensionV1
import pytest

from tests.test_source_statements import make_lane, GM, BODY, wk, transport, NOW
from tests.test_native_plan_statements import bound
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes
from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile
from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
from application_state.agent_conversation.native_plan_assertions import POLICY as NATIVE_ANSWER_POLICY


@pytest.fixture
def lane(application_state_dsn, tmp_path, monkeypatch):
    return make_lane(tmp_path, monkeypatch, narrow=True)


def publish(lane, *, qualified=False, extra_name=None):
    meta = replace(lane.meta, claim_mode='dungeonbuddy.claim:belief', epistemic_basis='speculative', standing='provisional') if qualified else lane.meta
    runtime = transport.runtime(lane.repo, dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(), now=NOW, operation_id='ordinary-native-assertion-test')
    return runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(lane.world.world_id, 'fixture', (
        wk.UseExisting(lane.ids['B'], (wk.CreateFact('account', 'dnd5e:summary', wk.LiteralFactValue('A reports that B fled; uncertain.'), meta),)
            + (() if extra_name is None else (wk.CreateFact('alternative-name','dnd5e:name',wk.LiteralFactValue(extra_name),meta),))),
    ))), confirmed_by=GM.subject)


def admit_unrelated(lane, identity):
    body = "An unrelated later session."
    raw = body.encode()
    return publish_native_text_source_evidence(
        repository=lane.repo, domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        request=NativeTextSourceAdmissionV1(
            space_id=lane.world.world_id, admission_id=identity,
            expected_parent_revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
            created_at=NOW, body_text=body, expected_body_sha256=sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility={"kind":"labels_any", "labels":["dungeonbuddy.visibility:gm"]},
            spans=[dict(client_ref="context", evidence_role="context", start_byte=0,
                        end_byte=len(raw), expected_slice_sha256=sha256(raw).hexdigest())],
        ),
    )


def select_extension_support(lane):
    root = lane.repo.get_native_source_admission_receipt(
        lane.world.world_id, lane.selection.source_admission_id)
    raw = BODY.encode()
    result = publish_native_source_evidence_extension(
        repository=lane.repo, domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        audience_labels=("dungeonbuddy.visibility:gm",),
        request=NativeSourceEvidenceExtensionV1(
            space_id=lane.world.world_id, extension_id="later-support-span",
            original_admission_id=root.admission_id, source_artifact_id=root.source_artifact_id,
            source_revision_id=root.source_revision_id, expected_body_sha256=sha256(raw).hexdigest(),
            expected_parent_revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
            expected_source_authority_epoch=lane.repo.open_native_source_view(lane.world.world_id).epoch,
            created_at=NOW, spans=[dict(client_ref="full-clause", evidence_role="support",
                start_byte=0, end_byte=len(raw), expected_slice_sha256=sha256(raw).hexdigest())],
        ),
    )
    lane.meta = replace(lane.meta, evidence_ref_ids=(result.bindings[0].evidence_ref_id,))


def query(lane):
    return prepare_query(lane.world.world_id, 'What did B do?', GM, repository=lane.repo,
        resolve_binding=lambda _: bound(lane), scope_mode='campaign', campaign_id='c1')


def grant(context, ids=None):
    return NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=0, provider_attempt_id=uuid4(),
        query_sha256=context.query.sha256, assertion_ids=ids or tuple(m.assertion_id for m in context.query.assertion_matches))


def test_core_assertions_keep_metadata_and_exact_support_without_summary_wrapper(lane, monkeypatch):
    lane.meta = replace(lane.meta, temporal_scope=wk.TemporalScope(
        kind='domain_ref', schema_term='dungeonbuddy.time:fictional_anchor_v1',
        payload={'episode': 'session-29', 'qualified': True, '_sample': {'_saved': [1, None]}},
    ), domain_metadata=(wk.DomainMetadata.from_json(
        'dungeonbuddy.domain_metadata:world_context_v1', {'uncertain': ['who reported it']}
    ),))
    publish(lane, qualified=True)
    from apps.live_control_server.services import native_graph_reads as native
    original = native.open_admitted_native_text
    def forbidden(*_args):
        pytest.fail('Source opened before selection')
    monkeypatch.setattr(native, 'open_admitted_native_text', forbidden)
    context, result = query(lane)
    assert result.schema_ == 'dmb_native_graph_query_v4' and result.assertion_matches and not result.matches
    assert BODY not in result.model_dump_json() and 'A reports' not in result.model_dump_json()
    monkeypatch.setattr(native, 'open_admitted_native_text', original)
    reads, unavailable = read_selected(context, grant(context), GM)
    assert not unavailable
    account = next(r for r in reads if r.assertion.predicate == 'dnd5e:summary')
    assert account.assertion.metadata.claim_mode == 'dungeonbuddy.claim:belief'
    assert account.assertion.metadata.epistemic_basis == 'speculative'
    assert account.assertion.metadata.standing == 'provisional'
    assert account.assertion.metadata.temporal_scope.payload == {'episode': 'session-29', 'qualified': True, '_sample': {'_saved': [1, None]}}
    assert account.assertion.metadata.domain_metadata[0].payload == {'uncertain': ['who reported it']}
    assert account.spans[0].text == BODY.splitlines(keepends=True)[0]
    assert account.spans[0].start_byte == 0
    with pytest.raises(ValueError, match='not discovered'):
        read_selected(context, grant(context, ('asrt:foreign',)), GM)
    with pytest.raises(ValueError, match='GM authority'):
        read_selected(context, grant(context), replace(GM, role='player'))
    changed = replace(context, resolve_binding=lambda _: SimpleNamespace(binding_version=99))
    with pytest.raises(ValueError, match='binding changed'):
        read_selected(changed, grant(context), GM)
    _, other_campaign = prepare_query(lane.world.world_id, 'B', GM, repository=lane.repo,
        resolve_binding=lambda _: bound(lane), scope_mode='campaign', campaign_id='c2')
    assert not other_campaign.assertion_matches and not other_campaign.universal_absence_claimed


def test_context_only_evidence_is_not_support(application_state_dsn, tmp_path, monkeypatch):
    lane = make_lane(tmp_path, monkeypatch)  # Existing admission is whole-source context.
    publish(lane)
    context, _ = query(lane)
    reads, unavailable = read_selected(context, grant(context), GM)
    assert not reads and set(unavailable) == {m.assertion_id for m in context.query.assertion_matches}


def _ordinary_native_case(
        lane, tmp_path, monkeypatch, qualified, unavailable, advancement, failure, mixed, native_read_admission_probes, authoring=False, authored=False, authored_source=None, plan_operation=None, extra_name=None):
    import httpx2
    from hashlib import sha256
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import native_graph_reads as native_query
    from apps.live_control_server.services import native_graph_reads as native_reads
    from apps.live_control_server.services import managed_world_graph_projection as managed, plan_jev_harness
    from apps.live_control_server.services.plan_jev_harness import PlanJevHarness
    from tests.test_agent_turn_service import _pinned_plan_request, _pinned_plan_work
    from tests.test_plan_jev_writer import WriterWire
    from application_state.agent_conversation import AgentConversationService, types as t
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1
    if advancement == 'extension':
        select_extension_support(lane)
    publish(lane, qualified=qualified, extra_name=extra_name)
    if advancement:
        admit_unrelated(lane, 'before-query')
    world = lane.world.world_id
    binding = SimpleNamespace(managed_world_id=world,native_world_id=world,binding_version=1,provisioning_id=None)
    monkeypatch.setattr(managed, 'resolve_managed_source_identity', lambda _: binding)
    monkeypatch.setattr(native_query, 'resolve_managed_world_binding', lambda _: binding)
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api','gpt-6-luna','https://api.openai.com/v1'))
    markdown = '# Query Plan\n\nA proposed visit.\n'
    work = _pinned_plan_work(markdown)
    work = replace(work, world_id=world, owner_id=world, content_basis=work.content_basis.model_copy(update={
        'world_id':world, 'content_sha256':sha256(markdown.encode()).hexdigest(), 'work_revision_id':str(uuid4())}))
    capture=None
    if authoring:
        from application_state.content.service import create_world_plan,commit_plan
        from application_state.agent_conversation.plan_authoring import PlanAuthoringCaptureV1
        from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV1
        from tests.application_state.test_plan_authoring import capture_payload
        obj=create_world_plan(title='Native authoring evidence',world_id=world)
        obj,revision=commit_plan(str(obj.work_object_id),markdown,expected_revision=obj.object_revision,expected_world_id=world)
        work=replace(work,object_id=str(obj.work_object_id),revision=obj.object_revision,content_basis=work.content_basis.model_copy(update={
            'document_id':str(obj.work_object_id),'object_revision':obj.object_revision,'work_revision_id':str(revision.work_revision_id),
            'revision_n':revision.revision_n,'content_sha256':revision.content_sha256}))
        service=AgentConversationService()
        service.new_conversation(t.ConversationCommand(world_id=world,command_id=uuid4(),expected_pointer_revision=0,expected_active_conversation_id=None))
        pointer=service.get_world_pointer(world)
        capture=PlanAuthoringCaptureV1.model_validate(capture_payload()|dict(world_id=world,document_id=str(obj.work_object_id),
            base_revision=obj.object_revision,base_content_sha256=revision.content_sha256,conversation_id=str(pointer.active_conversation_id),expected_pointer_revision=pointer.revision))
        catalog=PlanPlacementCatalogV1(original_capture_sha256=capture.sha256,editor_sha256=capture.editor_sha256,
            entries=({'selector':'captured','kind':'captured_target','label':'Captured caret','root_boundary':None,'position':None,'target_capture_sha256':capture.sha256},))
    selected_references=None
    if authored:
        from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredReferencesV2
        selected_references=AuthoredReferencesV2(references=(AuthoredGraphReferenceV1(
            managed_world_id=world,native_world_id=world,binding_version=1,
            graph_revision=lane.repo.get_head(world).head_revision_id,node_id=lane.ids['B'],label='DISPLAY ONLY Plan selection'),))
    if authored_source:
        from dungeonmind.application.vnext import list_admitted_native_text_sources
        from apps.live_control_server.integrations.dungeonmind.native_corpus_source import prepare_native_source_context
        from application_state.agent_conversation.authored_graph_references import AuthoredSourceReferenceV1, AuthoredReferencesV2
        from application_state.agent_conversation.native_source_catalog import section_catalog
        human_text='# Opening\nA proposed note.\n# Episode\nThe source describes a source-local episode. 🌿\n'
        raw=human_text.encode()
        admission=publish_native_text_source_evidence(repository=lane.repo,domain_contract=dungeonbuddy_world_domain_contract(),
            semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),request=NativeTextSourceAdmissionV1(
                space_id=world,admission_id='plan-human-source',expected_parent_revision_id=lane.repo.get_head(world).head_revision_id,
                created_at=NOW,body_text=human_text,expected_body_sha256=sha256(raw).hexdigest(),source_classification='dungeonbuddy.source:session_recap',authority='primary',
                visibility={'kind':'labels_any','labels':['dungeonbuddy.visibility:gm']},spans=[dict(client_ref='opening',evidence_role='context',start_byte=0,end_byte=len(raw),expected_slice_sha256=sha256(raw).hexdigest())]))
        source_context=prepare_native_source_context(managed_world_id=world,principal=GM,repository=lane.repo,resolve_identity=lambda _:binding)
        meta=next(row for row in list_admitted_native_text_sources(source_context.access).sources if row.source_artifact.source_artifact_id==admission.source_artifact_id)
        sections=section_catalog(human_text,source_artifact_id=admission.source_artifact_id,native_source_revision_id=admission.source_revision_id,content_sha256=sha256(raw).hexdigest())
        source_ref=AuthoredSourceReferenceV1(managed_world_id=world,native_world_id=world,binding_version=1,knowledge_revision=source_context.authority.revision_id,
            source_artifact_id=admission.source_artifact_id,source_revision_id=admission.source_revision_id,evidence_ref_id=meta.evidence_ref_ids[0],content_sha256=sha256(raw).hexdigest(),
            selection_kind='full_document' if authored_source=='full_document' else 'section',section_id=None if authored_source=='full_document' else sections[1].section_id,label='DISPLAY ONLY Plan source')
        selected_references=AuthoredReferencesV2(references=(() if authored_source=='source_only' else selected_references.references)+(source_ref,))
        if authored_source=='source_only':
            from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
            def no_object_binding(_):
                raise WorldGraphProjectionServiceError('No object Graph',code='native_graph_binding_missing',status_code=409)
            monkeypatch.setattr(native_query,'resolve_managed_world_binding',no_object_binding)
    request = _pinned_plan_request()
    request = type(request).model_validate(request.model_dump(mode='json',by_alias=True) | {
        **({'plan_requested_operation':plan_operation} if plan_operation is not None else {}),
        **({'authored_references':selected_references.model_dump(mode='json',by_alias=True)} if selected_references else {}),
        'turn_id':str(uuid4()),'message':('Describe the source-local episode.' if authored_source=='source_only' else 'Write a Plan note about what B did.' if authoring else 'What did B do?'),'owner_scope':{'kind':'world','world_id':world},
        'primary_work':request.primary_work.model_dump(mode='json',by_alias=True) | {'object_id':work.object_id,'expected_revision':work.revision,'expected_revision_n':work.content_basis.revision_n,'expected_content_sha256':work.content_basis.content_sha256},
        'plan_context_policy':{'schema':'dmb_plan_context_policy_v2','policy':'auto_plan_world','graph_source':'reviewed_native_graph'},
        'graph_request':{'mode':'none'},**({'plan_authoring_capture':capture.model_dump(mode='json',by_alias=True),'plan_placement_catalog':catalog.model_dump(mode='json',by_alias=True)} if capture is not None else {})})
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','local')
    token='synthetic-native-assertions-test-token-1234567890'
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN',token)
    monkeypatch.setattr(agent,'repo_root',lambda:tmp_path)
    monkeypatch.setattr(agent,'session_dir',lambda:tmp_path/'sessions')
    monkeypatch.setattr(agent,'_owner_resolver',lambda _: {'kind':'world','id':world,'name':'Synthetic World'})
    monkeypatch.setattr(agent,'_verified_world_id',lambda value:value)
    monkeypatch.setattr(agent,'_work_resolver',lambda *_:work)
    monkeypatch.setattr(agent,'_historical_work_resolver',lambda *_args,**_kwargs:work)
    monkeypatch.setattr(agent,'_graph_resolver',lambda *_:pytest.fail('Classic Graph fallback'))
    # Ordinary native selection must not read classic via the deeper Plan resolver.
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_:pytest.fail('Classic Plan resolver used for explicit native question'))
    if unavailable:
        monkeypatch.setattr(native_reads,'open_admitted_native_text',lambda *_:SimpleNamespace(status='unavailable'))
    seen_name_requests=[]
    class Decisions(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            body=json.loads(req.content)
            candidates=body.get('state',{}).get('candidates',[])
            if extra_name is not None and any(c['kind'].startswith('Native Graph object') for c in candidates):
                encoded=json.dumps(candidates,ensure_ascii=False)
                assert 'Multiple recorded names' in encoded and extra_name in encoded
                assert lane.ids['B'] not in req.content.decode()
                seen_name_requests.append(sha256(req.content).hexdigest())
            native={i for i,c in enumerate(candidates) if c['kind'].startswith('Native Graph object') or mixed and c['kind']=='public_rules_lookup'}
            if selected_references is not None and 'requested_work' in body['questions']:
                rows=body['state']['author_selected_references']
                assert len(rows)==len(selected_references.references)
                for row,ref in zip(rows,selected_references.references,strict=True):
                    if hasattr(ref,'selection_kind'):
                        assert row=={'kind':'source','label':ref.label,'selection_kind':ref.selection_kind}
                        assert json.dumps(ref.source_artifact_id) not in req.content.decode()
                        assert json.dumps(ref.content_sha256) not in req.content.decode()
                    else:
                        assert row=={'kind':'graph_object','label':ref.label}
                        assert json.dumps(ref.node_id) not in req.content.decode()
            if authored:
                native=set()  # Explicit human inclusion cannot depend on a model relevance vote.
            if authored_source and 'operation' in body['questions']:
                examined = body['state']['examined_subjects']
                assert any(c['kind'].startswith('Acquired user-selected source text; mandatory writer input')
                    and ('Full document' if authored_source == 'full_document' else 'Episode') in c['label'] for c in examined)
                assert human_text not in req.content.decode()
            assert BODY not in req.content.decode()
            answers={}
            for name,entry in body['questions'].items():
                choice=(('write:captured' if authoring else 'discuss') if name=='requested_work' else 'finish_retrieval' if name=='operation' else
                    'include' if name.startswith('candidate_') and int(name.split('_')[-1]) in native else 'exclude')
                answers[name]={'type':'choice','choice':choice,'confidence':1,
                    'probabilities':{key:float(key==choice) for key in entry['criteria']}}
            return httpx2.Response(200,request=req,json={'model':'jev-1.14.0','answers':answers,'usage':{'input_tokens':37,'output_tokens':9}})
    class Writer(WriterWire):
        async def handle_async_request(self, req):
            frames=[json.loads(item['content']) for item in json.loads(req.content)['input'][:-1]]
            frame=next(item for item in frames if set(item)=={'input_status','user_question','native_body_evidence','native_statements','native_assertions'})
            assert len(frames)==3
            assert frames[0 if authoring else -1] == frame
            assert NATIVE_ANSWER_POLICY in json.loads(req.content)['instructions']
            assert 'dmb_surface_evidence_answer_v6' not in json.loads(req.content)['instructions']
            assert BODY not in req.content.decode() and 'span.text' not in req.content.decode()
            rows=frame['native_assertions']['assertions'] if frame['native_assertions'] else []
            if authored:
                from application_state.agent_conversation.native_plan_work_view import is_semantic_frame
                work_frame=next(item for item in frames if is_semantic_frame(item))
                expected=[]
                for i,ref in enumerate(selected_references.references):
                    source=hasattr(ref,'selection_kind')
                    expected.append(dict(reference=f'reference{i}',label=ref.label,
                        kind='source' if source else 'object',
                        read_status='partial' if unavailable and not source else 'complete',
                        **({'extent':ref.selection_kind} if source else {})))
                assert work_frame['selected_references']==expected
                assert 'authored_references' not in work_frame
            if authored_source=='source_only':
                assert not rows
                segments=[]
                limitations=[]
            elif unavailable:
                assert not rows and frame['native_assertions']['status']=='partial'
                segments=[]
                limitations=['partial_retrieval','missing_requested_details']
            else:
                row=next(r for r in rows if r['assertion']['predicate']=='dnd5e:summary')
                assert row['assertion']['metadata']['claim_mode']==('dungeonbuddy.claim:belief' if qualified else 'dungeonbuddy.claim:fact')
                assert all('evidence' not in r and 'supporting_sources' not in r for r in rows)
                segments=[{'kind':'native_assertion_claim','text':'A reports that B fled; uncertain.',
                    'assertion_handles':[row['assertion_handle']]}]
                limitations=[]
            if authored_source:
                exposed=frame['native_body_evidence']['excerpts']
                assert len(exposed)==1 and 'source-local episode' in exposed[0]['text']
                assert 'DISPLAY ONLY Plan source' not in json.dumps(frame)  # Display selection is not evidence.
                segments.append({'kind':'native_body_claim','text':'The source describes a source-local episode.',
                    'excerpt_handles':[exposed[0]['excerpt_handle']]})
            candidate={'schema':NATIVE_ANSWER_POLICY,'answer_segments':segments,
                'limitations':limitations,'requested_detail_gaps':[]}
            if mixed:
                candidate={'schema':'dmb_rules_mixed_answer_v1','base_output':candidate,
                    'rules_segments':[{'kind':'rules_context','text':'No additional applicable rule is established.','category':'gap'}],
                    'ordered_refs':[{'domain':'base','segment_index':None},{'domain':'rules','segment_index':0}]}
            self.text='not-json' if failure=='malformed' else json.dumps(candidate)
            if failure=='incomplete':
                self.status='incomplete'
            if failure=='timeout':
                import httpx
                self.calls.append(req)
                raise httpx.ReadTimeout('synthetic selected writer timeout',request=req)
            return await super().handle_async_request(req)
    wire=Writer(None,'')
    class Harness(PlanJevHarness):
        def execute(self, adapter, **kwargs):
            wire.adapter=adapter
            try:
                return super().execute(adapter,**kwargs)
            except BaseException:
                import traceback
                wire.failure=traceback.format_exc()
                raise
    monkeypatch.setattr(plan_jev_harness,'default_plan_jev_runtime',lambda:Harness(decision_transport=Decisions(),
        writer_transport=wire,decision_api_key='synthetic-not-secret',writer_api_key='synthetic-not-secret'))
    app=FastAPI()
    app.include_router(agent.router,prefix='/api/live')
    client=TestClient(app,client=('127.0.0.1',42000),headers={'Authorization':'Bearer '+token})
    original_open=native_reads.open_admitted_native_text
    opened_with_grant=[]
    def source_after_grant(access,identity):
        current=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.turn.turn_id)
        from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
        if isinstance(current,MixedCompletedTurnV1):
            current=current.base_projection.turn
        if authored:
            from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
            grants=[e for e in current.graph_context_execution.events if isinstance(e,BuildAuthoredReferenceAuthorizedV2)]
            assert grants and grants[-1].node_id==lane.ids['B']
        else:
            grants=[e for e in current.graph_context_execution.events if isinstance(e,t.NativePlanAssertionReadAuthorizedV1)]
            assert any(e.kind=='provider_outcome' and e.provider_attempt_id==grants[-1].provider_attempt_id
                and e.outcome=='response_received' for e in current.graph_context_execution.events)
        assert grants and current.graph_context_receipt.native_query.sha256==grants[-1].query_sha256
        opened_with_grant.append(identity)
        return original_open(access,identity)
    monkeypatch.setattr(native_reads,'open_admitted_native_text',source_after_grant)
    original_head=lane.repo.get_head(world)
    if failure=='query_missing':
        prepare_query=native_query.prepare_query
        def missing_query(*args,**kwargs):
            context,_=prepare_query(*args,**kwargs)
            return context,None
        monkeypatch.setattr(native_query,'prepare_query',missing_query)
    wire_request=request.model_dump(mode='json',by_alias=True)
    if failure=='legacy_policy':
        wire_request['plan_context_policy']={'policy':'auto_plan_world'}
    if failure and failure.startswith('selected_source_'):
        field=failure.removeprefix('selected_source_')
        wire_request['authored_references']['references'][-1][field]='f'*64 if field in ('content_sha256','section_id') else 'unavailable-source-revision'
        selected_references=AuthoredReferencesV2.model_validate(wire_request['authored_references'])
    response=client.post('/api/live/agent/turn',json=wire_request)
    if failure and failure.startswith('selected_source_'):
        assert response.status_code==409,response.text+getattr(wire,'failure','')
        assert response.json()['detail']['code']=='authored_source_unavailable'
        assert not wire.calls
        retained=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.turn.turn_id)
        assert retained.failure_code=='authored_source_unavailable'
        assert not any(e.kind=='native_writer_authorized_v1' for e in retained.graph_context_execution.events)
        assert retained.graph_context_execution.policy.action.intent.authored_references.model_dump(mode='json',by_alias=True)==wire_request['authored_references']
        assert lane.repo.get_head(world)==original_head
        return
    if failure=='legacy_policy':
        assert response.status_code==409,response.text
        assert response.json()['detail']['code']=='plan_execution_contract_retired'
        assert not wire.calls and not opened_with_grant
        assert AgentConversationService().get_active_conversation(world) is None
        return
    if failure is not None:
        assert response.status_code==503,response.text
        if failure=='query_missing':
            assert wire.adapter.fence is None and not wire.calls
            assert AgentConversationService().get_active_conversation(world) is None
            return
        failed=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.turn.turn_id)
        assert failed.status=='interrupted' and failed.completion is None
        writer=next(e for e in failed.graph_context_execution.events if type(e) is NativeWriterAuthorizedV1)
        assert not any(type(e) is t.ProviderOutcomeEventV1 and e.provider_attempt_id==writer.provider_attempt_id
            and e.outcome=='response_received' for e in failed.graph_context_execution.events)
        before_replay_reads=len(opened_with_grant)
        replay=client.post('/api/live/agent/turn',json=request.model_dump(mode='json',by_alias=True))
        assert replay.status_code==409,replay.text+getattr(wire,'failure','')
        assert replay.json()['detail']['code']=='turn_already_authorized'
        assert len(wire.calls)==1 and len(opened_with_grant)==before_replay_reads
        assert AgentConversationService().inspect_turn(world_id=world,turn_id=failed.turn_id)==failed
        assert lane.repo.get_head(world)==original_head
        return
    assert response.status_code==200,response.text+getattr(wire,'failure','')
    assert authored_source=='source_only' or opened_with_grant
    assert authored or native_read_admission_probes
    data=response.json()
    if extra_name is not None:
        assert seen_name_requests
    # Native evidence belongs to its own receipt. No legacy Graph request was
    # made; its delivery descriptor must remain wholly not-requested.
    expected_graph = {'status': 'not_requested', **{key: None for key in (
        'world_id', 'campaign_id', 'scope_mode', 'revision_id', 'focus',
        'selection_node_id', 'selection_found', 'head_revision_id', 'is_head')}}
    assert data['graph'] == expected_graph
    context=data['rules_context']['base_context'] if mixed else data['plan_context']
    completion=context['completion']
    assert completion['schema']=='dmb_surface_native_completion_v1'
    if authored_source=='source_only':
        assert not data['answer']['graph_grounded']
    else:
        assert completion['answer_context_status']==('insufficient_evidence' if unavailable else 'graph_grounded')
    retained=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.turn.turn_id)
    turn=retained.base_projection.turn if mixed else retained
    assert type(turn.completion) is t.SurfaceNativeCompletionV1
    assert turn.graph_context_receipt.work_context.plan_context_policy.graph_source=='reviewed_native_graph'
    if authored:
        history=client.get(f'/api/live/agent/worlds/{world}/conversation?include_turn_correlation=true')
        assert history.status_code==200,history.text
        assert history.json()['turns'][-1]['authored_references']==selected_references.model_dump(mode='json',by_alias=True)
    if plan_operation is not None:
        assert turn.graph_context_execution.policy.action.intent.plan_requested_operation==plan_operation
        history=client.get(f'/api/live/agent/worlds/{world}/conversation?include_turn_correlation=true')
        assert history.status_code==200,history.text
        assert history.json()['turns'][-1]['plan_requested_operation']==plan_operation
        from pathlib import Path
        from application_state.agent_conversation.plan_jev_decision import verify_input_records
        frozen=json.loads((Path(__file__).parent/'fixtures/plan_requested_work_v2_wire.json').read_text())
        auth=next(e for e in turn.graph_context_execution.events if isinstance(e,t.PlanRequestedWorkAuthorizedV2))
        refs=selected_references.model_dump(mode='json',by_alias=True) if selected_references else None
        for altered in (
                frozen['parent'] | {'schema':'dmb_plan_requested_work_input_v5','authored_references':refs,
                    'plan_requested_operation':'discuss' if plan_operation=='write_current_page' else 'write_current_page'},
                frozen['parent'] | ({'schema':'dmb_plan_requested_work_input_v4','authored_references':refs}
                    if refs else {'schema':'dmb_plan_requested_work_input_v3'})):
            with pytest.raises(ValueError,match='explicit author operation'):
                verify_input_records(turn.graph_context_receipt,turn.graph_context_execution,auth,
                    {'parent_request_json':json.dumps(altered),'request_json':'{}'},
                    question=turn.user_text,scope_sha256='0'*64)
    if authored_source:
        reads=[e for e in turn.graph_context_execution.events if isinstance(e,t.NativeAuthoredSourceReadV1)]
        assert len(reads)==1 and reads[0].catalog.source.revision.source_revision_id==source_ref.source_revision_id
        assert not hasattr(reads[0],'provider_attempt_id')
        writer=next(e for e in turn.graph_context_execution.events if type(e) is NativeWriterAuthorizedV1)
        assert reads[0].event_id in writer.native_read_event_ids
        assert ('A proposed note.' in reads[0].excerpt.text)==(authored_source=='full_document')
        opened=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-body-excerpts/0')
        assert opened.status_code==200,opened.text
        assert opened.json()['content']==reads[0].excerpt.text
        replay=client.post('/api/live/agent/turn',json=request.model_dump(mode='json',by_alias=True))
        assert replay.status_code==200 and len(wire.calls)==1
        assert AgentConversationService().inspect_turn(world_id=world,turn_id=turn.turn_id)==retained
        return
    if authoring:
        from application_state.content.service import snapshot_content
        proposal=data['plan_proposal']
        assert proposal['capture']==capture.model_dump(mode='json',by_alias=True)
        assert proposal['replacement_markdown']==turn.completion.answer_segments[0].text+('\n\nNo additional applicable rule is established.' if mixed else '')
        writer=next(e for e in turn.graph_context_execution.events if type(e) is NativeWriterAuthorizedV1)
        assert proposal['origin']['evidence_event_ids']==[str(identity) for identity in writer.native_read_event_ids]
        assert snapshot_content(capture.document_id).markdown==markdown

    if authored:
        from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2,BuildAuthoredReferenceReadV2
        assert type(turn.graph_context_execution.policy.action.intent) is (t.SubmittedTurnIntentV4 if plan_operation is not None else t.SubmittedTurnIntentV3)
        assert turn.graph_context_execution.policy.action.intent.authored_references==selected_references
        grants=[e for e in turn.graph_context_execution.events if isinstance(e,BuildAuthoredReferenceAuthorizedV2)]
        observations=[e for e in turn.graph_context_execution.events if isinstance(e,BuildAuthoredReferenceReadV2)]
        assert not any(isinstance(e,t.NativePlanAssertionReadAuthorizedV1) for e in turn.graph_context_execution.events)
    else:
        grants=[e for e in turn.graph_context_execution.events if isinstance(e,t.NativePlanAssertionReadAuthorizedV1)]
        observations=[e for e in turn.graph_context_execution.events if isinstance(e,t.NativePlanAssertionReadObservedV1)]
    assert len(grants)==len(observations)==1 and grants[0].sequence<observations[0].sequence
    if unavailable:
        assert not completion['native_assertion_citations'] and observations[0].status=='partial'
    else:
        claim=completion['answer_segments'][0]
        assert claim['kind']=='native_assertion_claim' and claim['qualifications'][0]['standing']==('provisional' if qualified else 'established')
        if advancement:
            assert lane.repo.get_head(world)==original_head  # Query had no graph effect.
            admit_unrelated(lane, 'after-answer')
            original_head=lane.repo.get_head(world)  # Only this explicit admission advances it.
        opened=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-assertion-sources/0')
        assert opened.status_code==200,opened.text
        assert opened.json()['content']==(BODY if advancement=='extension' else BODY.splitlines(keepends=True)[0])
        assert opened.json()['citation']==completion['native_assertion_citations'][0]
        denied=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-assertion-sources/0?assertion=foreign')
        assert denied.status_code==422
    replay=client.post('/api/live/agent/turn',json=request.model_dump(mode='json',by_alias=True))
    assert replay.status_code==200,replay.text
    assert replay.json()['graph'] == expected_graph
    if authoring:
        assert replay.json()['plan_proposal']==data['plan_proposal']
    assert (replay.json()['rules_context']['base_context'] if mixed else replay.json()['plan_context'])['completion']==completion and len(wire.calls)==1
    assert lane.repo.get_head(world)==original_head
    if not unavailable:
        from application_state.agent_conversation.native_reads import validate_execution_binding as validate_execution
        from application_state.agent_conversation.native_plan_assertions import validate_citation_records
        def validate_citations(completion,receipt,execution,authorization):
            from application_state.agent_conversation.native_plan_assertions import selected_read_records
            reads={(e.event_id,r.assertion.assertion_id):(e,r) for e,r in selected_read_records(execution)
                if e.event_id in authorization.native_read_event_ids}
            return validate_citation_records(completion,receipt,authorization,reads)
        execution=turn.graph_context_execution
        authorization=next(e for e in execution.events if isinstance(e,NativeWriterAuthorizedV1))
        unsettled=execution.model_copy(update={'events':[e for e in execution.events if e not in observations]})
        with pytest.raises(ValueError,match='contiguous sequence'):
            validate_execution(turn.graph_context_receipt,unsettled)
        foreign=grants[0].model_copy(update={'query_sha256':'0'*64} if authored else {'provider_attempt_id':uuid4()})
        # inspected records are equal but not necessarily the same Python identity
        substituted=execution.model_copy(update={'events':[foreign if e.event_id==grants[0].event_id else e for e in execution.events]})
        with pytest.raises(ValueError,match='frozen context' if authored else 'current controller/query grant'):
            validate_execution(turn.graph_context_receipt,substituted)
        for field,value in [('provider_attempt_id',uuid4()),('read_revision_id','rev:foreign'),('span_sha256','0'*64)]:
            bad=turn.completion.native_assertion_citations[0].model_copy(update={field:value})
            changed_completion=turn.completion.model_copy(update={'native_assertion_citations':[bad]})
            with pytest.raises(ValueError,match='original source support'):
                validate_citations(changed_completion,turn.graph_context_receipt,execution,authorization)
        claim=turn.completion.answer_segments[0]
        changed_completion=turn.completion.model_copy(update={'answer_segments':[claim.model_copy(update={'qualifications':[]})]})
        with pytest.raises(ValueError,match='qualifications'):
            validate_citations(changed_completion,turn.graph_context_receipt,execution,authorization)
        import os
        import psycopg
        from psycopg.types.json import Jsonb
        dsn=os.environ['DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL']
        bad_execution=execution.model_dump(mode='json',by_alias=True)
        bad_execution['events'][0]['kind']='unregistered_assertion_reader'
        from application_state.errors import ApplicationStateIntegrityError
        with psycopg.connect(dsn) as conn:
            try:
                # SQL owns storage shape; the typed APP reader owns event meaning.
                conn.execute('UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s',(Jsonb(bad_execution),turn.turn_id))
                conn.commit()
                with pytest.raises(ApplicationStateIntegrityError):
                    AgentConversationService().inspect_turn(world_id=world,turn_id=turn.turn_id)
            finally:
                conn.execute('UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s',
                    (Jsonb(execution.model_dump(mode='json',by_alias=True)),turn.turn_id))
                conn.commit()
        assert AgentConversationService().inspect_turn(world_id=world,turn_id=turn.turn_id)==retained
        from application_state import cli
        from application_state.errors import ApplicationStateMigrationError
        with monkeypatch.context() as old_reader:
            old_reader.setattr(cli,'_alembic_head',lambda:'20261031_0101')
            with pytest.raises(ApplicationStateMigrationError):
                cli.assert_at_head(dsn=dsn)
    if plan_operation is not None:
        changed=request.model_dump(mode='json',by_alias=True) | {'plan_requested_operation':'discuss' if plan_operation=='write_current_page' else 'write_current_page'}
        assert client.post('/api/live/agent/turn',json=changed).status_code==409
    # Source choice is idempotency-bound, not a mutable retry preference.
    changed=request.model_dump(mode='json',by_alias=True)|{'plan_context_policy':{'policy':'auto_plan_world'}}
    assert client.post('/api/live/agent/turn',json=changed).status_code==(422 if authored or plan_operation is not None else 409)


@pytest.mark.parametrize('qualified,unavailable,advancement,failure,mixed', [
    (False,False,None,None,False),(True,False,None,None,False),(False,True,None,None,False),
    (False,False,'original',None,False),(False,False,'extension',None,False),
    (False,False,None,'malformed',False),(False,False,None,'incomplete',False),
    (False,False,None,'timeout',False),(False,False,None,None,True),
    (False,False,None,'query_missing',False)])
def test_fresh_ordinary_plan_native_question_delivers_reloads_and_opens_exact_source(
        lane,tmp_path,monkeypatch,qualified,unavailable,advancement,failure,mixed,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,qualified,unavailable,advancement,failure,mixed,native_read_admission_probes)


@pytest.mark.parametrize('mixed',[False,True])
def test_current_plan_authoring_keeps_actual_native_source_and_proposal_origin(lane,tmp_path,monkeypatch,mixed,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,None,mixed,native_read_admission_probes,authoring=True)


def test_recorded_name_ambiguity_reaches_actual_ordinary_controller_and_keeps_citations(
        lane,tmp_path,monkeypatch,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,None,False,
        native_read_admission_probes,extra_name='Bee')


@pytest.mark.parametrize('shape',['relationship','other-schema-json'])
def test_native_assertion_shapes_do_not_require_qualified_summary_json(lane,shape):
    runtime=transport.runtime(lane.repo,dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(),now=NOW,operation_id='ordinary-shape')
    operations=(wk.CreateRelationship('reported-about',wk.DurableObjectRef(lane.ids['A']),'dungeonbuddy.custom:reports_on',wk.DurableObjectRef(lane.ids['B']),lane.meta),) if shape=='relationship' else (
        wk.UseExisting(lane.ids['B'],(wk.CreateFact('json','dnd5e:summary',wk.LiteralFactValue('{"schema":"different","note":"an ordinary literal"}'),lane.meta),)),)
    runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(lane.world.world_id,'fixture',operations)),confirmed_by=GM.subject)
    before=lane.repo.get_head(lane.world.world_id)
    context,result=query(lane)
    reads,unavailable=read_selected(context,grant(context),GM)
    assert reads and not unavailable and not result.matches
    assert any(r.assertion.value.kind==('entity_ref' if shape=='relationship' else 'literal')
        and r.assertion.predicate==('dungeonbuddy.custom:reports_on' if shape=='relationship' else 'dnd5e:summary') for r in reads)
    if shape=='relationship':
        relationship=next(m for m in result.assertion_matches if 'reports_on' in m.label)
        assert relationship.subject_entity_id==lane.ids['A'] and not relationship.label.startswith('B ·')
    assert lane.repo.get_head(lane.world.world_id)==before


@pytest.mark.parametrize("extension", [False, True])
def test_older_support_remains_readable_after_unrelated_source_admission(lane, extension):
    if extension:
        select_extension_support(lane)
    publish(lane)
    admit_unrelated(lane, "newer-unrelated-source")
    context, result = query(lane)
    opened = open_admitted_native_text(context.pinned[1], lane.meta.evidence_ref_ids[0])
    assert opened.status == "available"
    assert opened.source_authority_epoch < result.authority.acquisition_epoch
    reads, unavailable = read_selected(context, grant(context), GM)
    assert not unavailable and reads
    account = next(row for row in reads if row.assertion.predicate == "dnd5e:summary")
    assert account.spans[0].text == (BODY if extension else BODY.splitlines(keepends=True)[0])


def test_core_source_integrity_failure_remains_fail_closed(lane, monkeypatch):
    from dungeonmind.application.vnext.errors import NativeTextSourceAccessIntegrityError
    publish(lane)
    context, _ = query(lane)
    view_type = type(context.pinned[1].source_view)
    original = view_type.get_native_text_source
    def damaged_body(view, **kwargs):
        stored = original(view, **kwargs)
        return replace(stored, body_bytes=b"tampered")
    monkeypatch.setattr(view_type, "get_native_text_source", damaged_body)
    with pytest.raises(NativeTextSourceAccessIntegrityError) as failure:
        read_selected(context, grant(context), GM)
    assert failure.value.reason == "body digest mismatch"


def test_fresh_plan_cannot_dispatch_the_retired_optional_graph_contract(lane,tmp_path,monkeypatch,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,'legacy_policy',False,native_read_admission_probes)


def test_navigation_labels_use_local_aliases_for_unnamed_conflicting_and_duplicate_names():
    from apps.live_control_server.services.native_graph_reads import _navigation_labels
    def entity(identity,names,*,complete=True):
        return SimpleNamespace(found=True,completeness=SimpleNamespace(status='complete' if complete else 'partial'),
            assertions=[SimpleNamespace(subject_entity_id=identity,predicate='dnd5e:name',
                value=SimpleNamespace(kind='literal',value=name),metadata=SimpleNamespace(scope=[])) for name in names])
    rows={'host-id-one':entity('host-id-one',['Twin']), 'host-id-two':entity('host-id-two',['Twin']),
        'host-id-three':entity('host-id-three',[]),'host-id-four':entity('host-id-four',['Old','New',' Old ']),
        'host-id-five':entity('host-id-five',['Literal context_accounting and phase']),
        'host-id-six':entity('host-id-six',['Partial name'],complete=False)}
    labels=_navigation_labels(rows)
    assert len(set(labels.values()))==len(rows)
    assert labels['host-id-one'].startswith('Twin (object ')
    assert labels['host-id-two'].startswith('Twin (object ')
    assert labels['host-id-three'].startswith('Unnamed object ')
    assert labels['host-id-four'].startswith('Multiple recorded names (object ')
    assert json.loads(labels['host-id-four'].split(': ',1)[1]) == ['New','Old']
    assert labels['host-id-five']=='Literal context_accounting and phase'
    assert all(identity not in label for identity in rows for label in labels.values())
    assert _navigation_labels(dict(reversed(list(rows.items()))))==labels
    assert _navigation_labels(rows,complete_only=True)['host-id-six'].startswith('Unnamed object ')
    # A literal authored name is context even if it resembles an identifier.
    assert _navigation_labels({'literal-id':entity('literal-id',['literal-id'])})['literal-id']=='literal-id'


def test_multiple_navigation_names_preserve_spelling_and_scoped_json_boundaries():
    from apps.live_control_server.services.native_graph_reads import _navigation_labels
    names=['Éname','E\u0301name','éname','Name, "quoted"\nnext']
    def name(value,campaign):
        return SimpleNamespace(subject_entity_id='host-id',predicate='dnd5e:name',
            value=SimpleNamespace(kind='literal',value=value),
            metadata=SimpleNamespace(scope=[SimpleNamespace(axis='campaign',value=campaign)]))
    entity=SimpleNamespace(found=True,completeness=SimpleNamespace(status='complete'),
        assertions=[*(name(n,'c1') for n in names),name('Foreign secret','c2')])
    label=_navigation_labels({'host-id':entity},scope=(('campaign','c1'),),complete_only=True)['host-id']
    assert label.startswith('Multiple recorded names (object 1): ')
    assert json.loads(label.split(': ',1)[1])==sorted(names)
    assert '\n' not in label and 'Foreign secret' not in label and 'host-id' not in label


def test_subject_navigation_keeps_exact_scope_complete_read_and_about_witness():
    from apps.live_control_server.services.native_graph_reads import _subject_labels
    from apps.live_control_server.services import source_statements as statements
    identity,statement='host-subject-id','host-statement-id'
    name=lambda text,campaign:SimpleNamespace(subject_entity_id=identity,predicate='dnd5e:name',
        value=SimpleNamespace(kind='literal',value=text),metadata=SimpleNamespace(scope=[SimpleNamespace(axis=statements.CAMPAIGN_SCOPE_AXIS,value=campaign)]))
    about=SimpleNamespace(assertion_id='host-about-id',subject_entity_id=statement,predicate=statements.mapping.ABOUT,value=SimpleNamespace(entity_id=identity))
    entity=SimpleNamespace(found=True,completeness=SimpleNamespace(status='complete'),assertions=[name('Right name','c2'),name('Other campaign','c1'),about])
    rows={identity:entity};paths=[(identity,['host-about-id'])]
    assert _subject_labels(statement,paths,rows,'c2')=='Right name'
    entity.completeness.status='partial'
    assert _subject_labels(statement,paths,rows,'c2').startswith('Unnamed object ')
    with pytest.raises(ValueError,match='ABOUT witness'):
        _subject_labels(statement,[(identity,['wrong-witness'])],rows,'c2')


def test_native_query_labels_do_not_expose_entity_identity(lane):
    publish(lane,qualified=True)
    _,result=query(lane)
    labels=[row.label for row in (*result.object_matches,*result.assertion_matches)]
    assert labels
    assert all(identity not in label for identity in result.discovered_entity_ids for label in labels)
    assert any(row.subject_entity_id==lane.ids['B'] for row in result.assertion_matches)


@pytest.mark.parametrize('scope_mode',['campaign','world'])
def test_native_navigation_does_not_name_c1_assertion_from_c2_name(lane,monkeypatch,scope_mode):
    from apps.live_control_server.services import native_graph_reads as native
    publish(lane)
    original=native.EntityReadService()
    def read(context,identity):
        entity=original.get_complete_entity(context,identity)
        if identity!=lane.ids['B']:return entity
        rows=[]
        for row in entity.assertions:
            if row.subject_entity_id==identity and row.predicate=='dnd5e:name':
                row=replace(row,metadata=replace(row.metadata,
                    scope=tuple(replace(binding,value='c2') for binding in row.metadata.scope)))
            rows.append(row)
        return replace(entity,assertions=tuple(rows))
    monkeypatch.setattr(native,'EntityReadService',lambda:SimpleNamespace(get_complete_entity=read))
    _,result=native.prepare_query(lane.world.world_id,'What did B do?',GM,repository=lane.repo,
        resolve_binding=lambda _:bound(lane),scope_mode=scope_mode,campaign_id='c1' if scope_mode=='campaign' else None)
    summaries=[row for row in result.assertion_matches if row.subject_entity_id==lane.ids['B'] and row.label.endswith(' · dnd5e:summary')]
    assert summaries and all(row.label.startswith('Unnamed object ') for row in summaries)
    if scope_mode=='campaign':
        assert next(row.label for row in result.object_matches if row.entity_id==lane.ids['B']).startswith('Unnamed object ')
    # Read identity and qualifications remain Core-owned; labels grant nothing.
    assert all(row.subject_entity_id==lane.ids['B'] for row in summaries)
