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


@pytest.fixture
def lane(application_state_dsn, tmp_path, monkeypatch):
    return make_lane(tmp_path, monkeypatch, narrow=True)


def publish(lane, *, qualified=False):
    meta = replace(lane.meta, claim_mode='dungeonbuddy.claim:belief', epistemic_basis='speculative', standing='provisional') if qualified else lane.meta
    runtime = transport.runtime(lane.repo, dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(), now=NOW, operation_id='ordinary-native-assertion-test')
    return runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(lane.world.world_id, 'fixture', (
        wk.UseExisting(lane.ids['B'], (wk.CreateFact('account', 'dnd5e:summary', wk.LiteralFactValue('A reports that B fled; uncertain.'), meta),)),
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
    publish(lane, qualified=True)
    from apps.live_control_server.services import native_graph_reads as native
    original = native.open_admitted_native_text
    def forbidden(*_args):
        pytest.fail('Source opened before selection')
    monkeypatch.setattr(native, 'open_admitted_native_text', forbidden)
    context, result = query(lane)
    assert result.schema_ == 'dmb_native_plan_query_v2' and result.assertion_matches and not result.matches
    assert BODY not in result.model_dump_json() and 'A reports' not in result.model_dump_json()
    monkeypatch.setattr(native, 'open_admitted_native_text', original)
    reads, unavailable = read_selected(context, grant(context), GM)
    assert not unavailable
    account = next(r for r in reads if r.assertion.predicate == 'dnd5e:summary')
    assert account.assertion.metadata.claim_mode == 'dungeonbuddy.claim:belief'
    assert account.assertion.metadata.epistemic_basis == 'speculative'
    assert account.assertion.metadata.standing == 'provisional'
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


@pytest.mark.parametrize('qualified,unavailable,advancement', [
    (False,False,None),(True,False,None),(False,True,None),
    (False,False,'original'),(False,False,'extension')])
def test_fresh_ordinary_plan_native_question_delivers_reloads_and_opens_exact_source(
        lane, tmp_path, monkeypatch, qualified, unavailable, advancement, native_read_admission_probes):
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
    if advancement == 'extension':
        select_extension_support(lane)
    publish(lane, qualified=qualified)
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
    request = _pinned_plan_request()
    request = type(request).model_validate(request.model_dump(mode='json',by_alias=True) | {
        'turn_id':str(uuid4()),'message':'What did B do?','owner_scope':{'kind':'world','world_id':world},
        'primary_work':request.primary_work.model_dump(mode='json',by_alias=True) | {'expected_content_sha256':work.content_basis.content_sha256},
        'plan_context_policy':{'schema':'dmb_plan_context_policy_v2','policy':'auto_plan_world','graph_source':'reviewed_native_graph'},
        'graph_request':{'mode':'none'}})
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
    class Decisions(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            body=json.loads(req.content)
            candidates=body.get('state',{}).get('candidates',[])
            native={i for i,c in enumerate(candidates) if c['kind'].startswith('Reviewed native Graph')}
            assert BODY not in req.content.decode()
            answers={}
            for name,entry in body['questions'].items():
                choice=('discuss' if name=='requested_work' else 'finish_retrieval' if name=='operation' else
                    'include' if name.startswith('candidate_') and int(name.split('_')[-1]) in native else 'exclude')
                answers[name]={'type':'choice','choice':choice,'confidence':1,
                    'probabilities':{key:float(key==choice) for key in entry['criteria']}}
            return httpx2.Response(200,request=req,json={'model':'jev-1.14.0','answers':answers,'usage':{'input_tokens':37,'output_tokens':9}})
    class Writer(WriterWire):
        async def handle_async_request(self, req):
            frame=json.loads(json.loads(req.content)['input'][0]['content'])
            assert frame['schema']=='dmb_plan_jev_writer_frame_v8'
            assert BODY not in req.content.decode() and 'span.text' not in req.content.decode()
            rows=frame['native_assertions']['assertions']
            if unavailable:
                assert not rows and frame['native_assertions']['status']=='partial'
                segments=[]
                limitations=['partial_retrieval','missing_requested_details']
            else:
                row=next(r for r in rows if r['assertion']['predicate']=='dnd5e:summary')
                assert row['assertion']['metadata']['claim_mode']==('dungeonbuddy.claim:belief' if qualified else 'dungeonbuddy.claim:fact')
                assert all('text' not in s for r in rows for s in r['supporting_sources'])
                segments=[{'kind':'native_assertion_claim','text':'A reports that B fled; uncertain.',
                    'assertion_handles':[row['assertion_handle']]}]
                limitations=[]
            self.text=json.dumps({'schema':frame['answer_policy'],'answer_segments':segments,
                'limitations':limitations,'requested_detail_gaps':[]})
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
        current=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.fence.turn.turn_id)
        grants=[e for e in current.graph_context_execution.events if isinstance(e,t.NativePlanAssertionReadAuthorizedV1)]
        assert grants and current.graph_context_receipt.native_query.sha256==grants[-1].query_sha256
        assert any(e.kind=='provider_outcome' and e.provider_attempt_id==grants[-1].provider_attempt_id
            and e.outcome=='response_received' for e in current.graph_context_execution.events)
        opened_with_grant.append(identity)
        return original_open(access,identity)
    monkeypatch.setattr(native_reads,'open_admitted_native_text',source_after_grant)
    original_head=lane.repo.get_head(world)
    response=client.post('/api/live/agent/turn',json=request.model_dump(mode='json',by_alias=True))
    assert response.status_code==200,response.text+getattr(wire,'failure','')
    assert opened_with_grant
    assert native_read_admission_probes
    data=response.json()
    completion=data['plan_context']['completion']
    assert completion['schema']=='dmb_surface_evidence_completion_v7'
    assert completion['answer_context_status']==('insufficient_evidence' if unavailable else 'graph_grounded')
    turn=AgentConversationService().inspect_turn(world_id=world,turn_id=wire.adapter.turn.turn_id)
    assert isinstance(turn.completion,t.SurfaceEvidenceCompletionV7)
    assert turn.graph_context_receipt.plan_context_policy.graph_source=='reviewed_native_graph'
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
    assert replay.json()['plan_context']['completion']==completion and len(wire.calls)==1
    assert lane.repo.get_head(world)==original_head
    if not unavailable:
        from application_state.agent_conversation.native_plan_statements import validate_execution
        from application_state.agent_conversation.native_plan_assertions import validate_citations
        execution=turn.graph_context_execution
        authorization=next(e for e in execution.events if isinstance(e,t.PlanNativeWriterAuthorizedV2))
        unsettled=execution.model_copy(update={'events':[e for e in execution.events if e not in observations]})
        with pytest.raises(ValueError,match='every selected read grant'):
            validate_execution(turn.graph_context_receipt,unsettled)
        foreign=grants[0].model_copy(update={'provider_attempt_id':uuid4()})
        # inspected records are equal but not necessarily the same Python identity
        substituted=execution.model_copy(update={'events':[foreign if e.event_id==grants[0].event_id else e for e in execution.events]})
        with pytest.raises(ValueError,match='current controller/query grant'):
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
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute('UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s',(Jsonb(bad_execution),turn.turn_id))
            conn.rollback()
        from application_state import cli
        from application_state.errors import ApplicationStateMigrationError
        with monkeypatch.context() as old_reader:
            old_reader.setattr(cli,'_alembic_head',lambda:'20261031_0101')
            with pytest.raises(ApplicationStateMigrationError):
                cli.assert_at_head(dsn=dsn)
    # Source choice is idempotency-bound, not a mutable retry preference.
    changed=request.model_dump(mode='json',by_alias=True)|{'plan_context_policy':{'policy':'auto_plan_world'}}
    assert client.post('/api/live/agent/turn',json=changed).status_code==409


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
