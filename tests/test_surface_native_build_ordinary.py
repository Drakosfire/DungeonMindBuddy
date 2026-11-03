"""Ordinary Build HTTP/default factory proof, not a prebuilt native component."""
import json
from types import SimpleNamespace
from hashlib import sha256
from uuid import uuid4

import httpx
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.page_fixtures import create_page_fixture, save_page
from tests.test_native_plan_assertions import lane as lane, publish, admit_unrelated
from tests.test_build_jev_estimated_continuations import counter
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredGraphReferencesV1
from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot


@pytest.mark.parametrize('failure,with_draft,saved,proposal',
    [(f,d,s,False) for f,d,s in ([(f,d,False) for f in (None,'revision','node','reference_world') for d in (False,True)]
        +[(None,d,True) for d in (False,True)]+[(f,False,True) for f in ('section_scope','selection_text')])]
    +[(f,True,False,mode) for mode in (True,'image')
        for f in (None,'native_work','rules_frame','attempt_count','sdk_model','stale_rules','used_rules')]
    +[('unsafe_direction',True,False,'image')])
def test_fresh_build_default_factory_answers_human_reference_and_reopens_exact_support(lane, tmp_path, monkeypatch, failure, with_draft,saved,proposal):
    _fresh_case(lane,tmp_path,monkeypatch,failure,with_draft,saved,proposal)


def _fresh_case(lane,tmp_path,monkeypatch,failure,with_draft,saved,proposal,*,recovery_dsn=None,recovery_mutation=None,retry_mutation=None,connected_review=None,native_body=None):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import native_graph_reads as native, managed_world_graph_projection as managed
    from apps.live_control_server.services import build_jev_runtime as factory
    publish(lane, qualified=True)
    world = lane.world.world_id
    original_revision = lane.repo.get_head(world).head_revision_id
    page = create_page_fixture(tmp_path, world_id=world, campaign_id=world, title='Working page',
        kind='worldbuilding_source', source_domain='worldbuilding', document_class='lore',
        authority_state='draft', visibility_state='internal')
    save_page(tmp_path, page.document_id, '# Working page\n\nA proposed conversation.\n')
    source = get_workspace_document_snapshot(tmp_path, page.document_id)
    draft = None
    if with_draft:
        from hashlib import sha256
        from application_state.agent_conversation.build_draft_context import BuildDraftSnapshotV1, BuildDraftContextRequestV1
        from tests.application_state.test_agent_conversation_postgres import _new
        service = AgentConversationService()
        conversation = _new(service,world)
        pointer = service.get_world_pointer(world)
        text = 'An unsaved orchid possibility. Never a played fact. 🌸'
        snapshot = BuildDraftSnapshotV1(world_id=world,document_id=page.document_id,
            registry_revision=source.loaded_revision,content_sha256=source.content_sha256,visibility='internal',
            draft_markdown=text,draft_sha256=sha256(text.encode()).hexdigest(),editor_sha256='c'*64,draft_generation=3)
        draft = BuildDraftContextRequestV1(snapshot=snapshot,conversation_id=conversation.conversation_id,
            expected_pointer_revision=pointer.revision)
    selected = AuthoredGraphReferencesV1(references=(AuthoredGraphReferenceV1(managed_world_id=world,
        native_world_id=world, binding_version=1, graph_revision=original_revision,
        node_id=lane.ids['B'], label='DISPLAY ONLY: never evidence'),))
    if failure in {'revision','node','reference_world'}:
        field,value = {'revision':('graph_revision','rev:missing'), 'node':('node_id','ent:missing'),
            'reference_world':('managed_world_id','foreign-world')}[failure]
        selected = selected.model_copy(update={'references':(selected.references[0].model_copy(update={field:value}),)})
    admit_unrelated(lane, 'after-human-pick-before-http')
    current_revision = lane.repo.get_head(world).head_revision_id
    assert current_revision != original_revision
    binding = SimpleNamespace(managed_world_id=world, native_world_id=world, binding_version=1, provisioning_id=None)
    monkeypatch.setattr(managed, 'resolve_managed_source_identity', lambda _: binding)
    monkeypatch.setattr(native, 'resolve_managed_world_binding', lambda _: binding)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    monkeypatch.setattr(agent, '_managed_world_root', lambda: tmp_path)
    monkeypatch.setattr('apps.live_control_server.services.build_document_proposal.managed_world_data_root',lambda:tmp_path)
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    token = 'synthetic-native-build-test-token-1234567890'
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6.1-sol', 'https://api.openai.com/v1'))
    classic_calls = []
    def classic(*_args, **_kwargs):
        classic_calls.append('classic_graph_services')
        raise AssertionError('Fresh Build used classic Graph broker instead of shared native access')
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config', classic)

    class Decisions(httpx2.AsyncBaseTransport):
        def __init__(self):
            self.calls = []
            self.deny_routing=False
        async def handle_async_request(self, req):
            self.calls.append(req)
            body = json.loads(req.content)
            answers = {}
            candidates=body.get('state',{}).get('candidates',[])
            selected={i for i,c in enumerate(candidates) if (saved and c['kind'].startswith('Saved authored page block'))
                or (failure=='used_rules' and c['kind']=='public_rules_lookup')
                or (native_body and c['kind'] in {'Source lexical navigation; not evidence or semantic completeness','Explicit full-document read'})}
            for name, question in body['questions'].items():
                if self.deny_routing and name=='requested_work':
                    raise AssertionError('The reviewed operation must not be reselected by a model')
                choices = question['criteria']
                chosen = (('review_connected_page' if connected_review else 'prepare_image' if proposal=='image' else 'write_current_page' if proposal else 'discuss') if name=='requested_work' else ('select_candidates' if selected and 'select_candidates' in choices else 'finish_retrieval') if name=='operation'
                    else ('include' if int(name.split('_')[-1]) in selected else 'exclude') if name.startswith('candidate_')
                    else (native_body if native_body and body['state']['sources'][list(body['state']['sources'])[int(name[1:])]]['kind']=='native_body' else 'direct_support') if name.startswith('s') and name[1:].isdigit() else 'skip')
                assert chosen in choices, (name, choices)
                answers[name] = dict(type='choice', choice=chosen, confidence=1,
                    probabilities={key: float(key == chosen) for key in choices})
            return httpx2.Response(200, request=req, json=dict(model='jev-1.14.0', answers=answers,
                usage=dict(input_tokens=37, output_tokens=9)))

    class Writer(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = []
            self.adapter = None
            self.mode = proposal
            self.review = None
        async def handle_async_request(self,req):
            try:
                return await self._handle(req)
            except Exception as exc:
                import traceback
                traceback.print_exception(exc)
                raise
        async def _handle(self, req):
            mode=self.mode
            self.calls.append(req)
            if failure=='retry_unknown':
                raise httpx.ReadTimeout('synthetic unknown writer outcome',request=req)
            body = json.loads(req.content)
            assert body['model'] == 'gpt-6.1-sol'
            if body.get('reasoning', {}).get('effort') != 'low':
                return httpx.Response(400, request=req, json={'error': {
                    'message': 'Unsupported reasoning effort for configured writer',
                    'type': 'invalid_request_error', 'param': 'reasoning.effort',
                    'code': 'unsupported_value'}})
            inputs = [json.loads(body['input'])] if isinstance(body['input'], str) else [json.loads(row['content']) for row in body['input'] if row['content'].lstrip().startswith('{')]
            if mode:
                inputs=[inputs[0]['native_evidence'],inputs[0]['surface_work']]
            frame = next(row for row in inputs if row.get('schema') == 'dmb_surface_native_writer_evidence_v1')
            work = next(row for row in inputs if row.get('schema')=='dmb_build_primary_work_evidence_v1')
            if self.adapter.submitted_intent.reviewed_step is not None:
                from application_state.agent_conversation.reviewed_action import writer_scope,SCOPE_KEY
                scope=writer_scope(self.adapter._broker_execution())
                assert work.get(SCOPE_KEY)==scope
                if scope is not None:
                    assert scope['scope']['task']['text']=='Discuss where the lamp belongs.'
                    assert scope['scope']['sibling_context'][0]['selected'] is False
            if with_draft:
                assert work['working_draft_context']['draft_markdown']==draft.snapshot.draft_markdown
                if mode:
                    assert body['input'].count(json.dumps(draft.snapshot.draft_markdown,ensure_ascii=False)[1:-1])==1
                else:
                    assert sum(draft.snapshot.draft_markdown in row['content'] for row in body['input'])==1
            handles = [row['assertion_handle'] for row in frame['native_assertions']['assertions']]
            assert handles and 'DISPLAY ONLY' not in str(frame)
            read_ids=[row['read_id'] for row in work['artifact_under_edit']['sections']]
            if saved:
                assert read_ids and 'A proposed conversation.' in str(work)
            if mode:
                candidate=dict(destination='current_page',target='captured',replacement_markdown='A proposed copper lamp.',
                    summary='Proposed detail.',assumptions=['The lamp is invented.'])
                if mode=='image':
                    candidate=dict(prompt='https://not-an-image.test/directive' if failure=='unsafe_direction' else 'A proposed copper lamp beside an orchid.',alt='Proposed copper lamp illustration',purpose='illustration')
                text=json.dumps(candidate)
                response=dict(id='resp_native_build_proposal',object='response',created_at=1,status='completed',
                    model='foreign-model' if failure=='sdk_model' else body['model'],output=[dict(type='message',id='msg_native_build_proposal',role='assistant',
                        status='completed',content=[dict(type='output_text',text=text,annotations=[])])],
                    usage=dict(input_tokens=100,output_tokens=40,total_tokens=140))
                if mode=='image':
                    return httpx.Response(200,request=req,json=response)
                events=[dict(type='response.output_text.delta',sequence_number=1,item_id='msg_native_build_proposal',
                    output_index=0,content_index=0,delta=text),dict(type='response.completed',sequence_number=2,response=response)]
                return httpx.Response(200,request=req,headers={'content-type':'text/event-stream'},
                    content=''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
            candidate = dict(schema=frame['answer_policy'],
                answer_segments=[dict(kind='native_assertion_claim', text='The Graph retains the qualified description.', assertion_handles=handles)]+([dict(kind='saved_source_claim',text='The saved page proposes a conversation.',section_read_ids=read_ids,supporting_quotes=[r['text'] for r in work['artifact_under_edit']['sections']])] if saved else []),
                limitations=[], requested_detail_gaps=[], collaboration=self.review)
            if native_body:
                from application_state.agent_conversation import native_corpus as corpus
                acquired = corpus.acquired_body_reads(self.adapter._broker_execution())
                assert acquired
                exposed = frame['native_body_evidence']['excerpts']
                assert bool(exposed) == (native_body != 'irrelevant')
                if exposed:
                    candidate['answer_segments'].append(dict(kind='native_body_claim',
                        text='The source describes a source-local episode.',
                        excerpt_handles=[r['excerpt_handle'] for r in exposed]))
                else:
                    assert all(r.excerpt.text not in json.dumps(frame) for r in acquired)
            if connected_review:
                section=next(row for row in work['artifact_under_edit']['sections'] if 'A proposed conversation.' in row['text'])
                candidate['answer_segments']=[]
                candidate['collaboration']={'kind':'connected_page','title':'A proposed neighboring workshop',
                    'read_id':str(uuid4()) if connected_review=='foreign_read' else section['read_id'],
                    'quote':'A phrase absent from the source.' if connected_review=='foreign_quote' else 'A proposed conversation.',
                    'person_label':None,'relationships':[],'instructions':'Prepare a separate page for author review.'}
            return httpx.Response(200, request=req, json=dict(id='resp_native_build', object='response',
                created_at=1, status='completed', model=body['model'], output=[dict(type='message', id='msg_native_build',
                    role='assistant', status='completed', content=[dict(type='output_text', text=json.dumps(candidate), annotations=[])])],
                usage=dict(input_tokens=100, output_tokens=40, total_tokens=140)))
    decisions, writer = Decisions(), Writer()
    if proposal and failure in {'native_work','rules_frame'}:
        from apps.live_control_server.services import build_document_proposal as proposal_owner,build_image_writer
        selected_owner=build_image_writer if proposal=='image' else proposal_owner
        method='writer_request' if proposal=='image' else '_writer_request'
        original_request=getattr(selected_owner,method)
        def changed_request(*args,**kwargs):
            prepared=original_request(*args,**kwargs)
            packet=json.loads(prepared['input'])
            if failure=='native_work':
                packet['surface_work']['source_basis']['content_sha256']='0'*64
            else:
                packet['rules_evidence']['ruleset']='foreign-rules'
            prepared['input']=json.dumps(packet,ensure_ascii=False,separators=(',',':'))
            return prepared
        monkeypatch.setattr(selected_owner,method,changed_request)
    if proposal and failure=='attempt_count':
        from generationengine import GenerationClient,TextCompleted
        from dataclasses import replace
        original_stream=GenerationClient.stream_text
        async def changed_stream(self,*args,**kwargs):
            async for event in original_stream(self,*args,**kwargs):
                if isinstance(event,TextCompleted):
                    event=replace(event,observation=event.observation.model_copy(update={'provider_attempt_count':2}))
                yield event
        if proposal=='image':
            original_generate=GenerationClient.generate_structured
            async def changed_generate(self,*args,**kwargs):
                result=await original_generate(self,*args,**kwargs)
                return result.model_copy(update={'observation':result.observation.model_copy(update={'provider_attempt_count':2})})
            monkeypatch.setattr(GenerationClient,'generate_structured',changed_generate)
        else:
            monkeypatch.setattr(GenerationClient,'stream_text',changed_stream)
    if proposal and failure=='stale_rules':
        original_complete=AgentConversationService.complete_native_base_turn
        def stale_complete(self,*args,**kwargs):
            return original_complete(self,*args,**{**kwargs,'expected_rules_revision':kwargs['expected_rules_revision']+1})
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',stale_complete)
    rules_reads=[]
    if proposal and failure=='used_rules':
        from apps.live_control_server.services import rules_lookup_broker
        read_rules=rules_lookup_broker.prepare_plan_lookup
        def completed_rules(*args,**kwargs):
            result=read_rules(*args,**kwargs)
            rules_reads.append(result)
            return result
        monkeypatch.setattr(rules_lookup_broker,'prepare_plan_lookup',completed_rules)
    actual_harness = factory.BuildJevHarness
    if failure=='selection_text':
        from dataclasses import replace
        from apps.live_control_server.services.build_jev_writer_selection import WriterSelectionDriver
        original_stage=WriterSelectionDriver.stage
        def substituted_stage(self):
            plan=original_stage(self)
            state=plan.state()
            next(iter(state['sources'].values()))['text']='Substituted private-looking source body.'
            self._plan=replace(plan,state_json=json.dumps(state,sort_keys=True,separators=(',',':')))
            return self._plan
        monkeypatch.setattr(WriterSelectionDriver,'stage',substituted_stage)
    class Harness(actual_harness):
        def _capture_failure(self, adapter, exc):
            import traceback
            traceback.print_exception(exc)
            super()._capture_failure(adapter, exc)
        def __init__(self, **values):
            super().__init__(decision_transport=decisions, writer_transport=writer, **values)
        def execute(self, adapter):
            writer.adapter = adapter
            if failure=='section_scope':
                original_read=adapter.read_build_section
                adapter.read_build_section=lambda **args:original_read(line_start=args['line_start']+999,line_end=args['line_end']+999)
            return super().execute(adapter)
    monkeypatch.setattr(factory, 'BuildJevHarness', Harness)
    app = FastAPI()
    app.include_router(agent.router, prefix='/api/live')
    from apps.live_control_server.routes.conversation_library import router as conversations_router
    app.include_router(conversations_router)
    app.state.build_jev_runtime_factory = factory.PreparedBuildJevRuntime(accounting=counter())
    client = TestClient(app, client=('127.0.0.1', 42000), headers={'Authorization': 'Bearer ' + token})
    body = dict(schema='dmb_agent_turn_request_v1', client_thread_id=str(uuid4()), turn_id=str(uuid4()),
        surface=dict(surface_id='build', instance_id=page.document_id), owner_scope=dict(kind='world', world_id=world),
        primary_work=dict(kind='build', object_id=page.document_id, expected_revision=source.loaded_revision,
            expected_content_sha256=source.content_sha256), client_work_state='saved_clean',
        graph_request=dict(mode='world', world_id=world, campaign_id=None, revision_pin=None,
            focus=dict(kind='none', session_id=None, campaign_id=None)), graph_selection=None,
        build_authored_references=selected.model_dump(mode='json', by_alias=True), message='Describe the selected object and source-local episode.' if native_body else 'Describe the object I selected.')
    if draft is not None:
        body['build_draft_context']=draft.model_dump(mode='json',by_alias=True)
        body['client_work_state']='saved_dirty'
    if proposal:
        from application_state.build_proposal.types import BuildWriteCapability
        cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=draft.conversation_id,
            expected_pointer_revision=draft.expected_pointer_revision,draft_markdown=draft.snapshot.draft_markdown,
            basis=dict(**{k:getattr(draft.snapshot,k) for k in ('world_id','document_id','registry_revision',
                'content_sha256','visibility','draft_sha256','editor_sha256','draft_generation')},
                caret=1,selection_generation=0))
        body['build_write_capability']=cap.model_dump(mode='json')
        body['message']=('Add a scene about this: Can I end my move in an occupied space?'
            if failure=='used_rules' else 'Prepare an illustration of a copper lamp beside the orchid.'
            if proposal=='image' else 'Add a proposed copper lamp to this page.')
    def current_creative():
        if proposal=='image':
            from uuid import uuid5
            from application_state.build_proposal.images import BuildImageService
            return BuildImageService().get(uuid5(cap.idempotency_key,'image'),writer.adapter.build_image_owner)
        from application_state.build_proposal.service import BuildProposalService
        return BuildProposalService().get(world,cap.idempotency_key)
    if failure in {'crash_live','crash_expired','crash_interrupted'}:
        from application_state.agent_conversation import types as ledger
        from uuid import uuid5
        import psycopg
        original_complete=AgentConversationService.complete_native_base_turn
        def crash_after_persistence(*args,**kwargs):
            raise SystemExit('synthetic crash after native object persistence')
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',crash_after_persistence)
        with pytest.raises(SystemExit,match='synthetic crash'):
            client.post('/api/live/agent/turn',json=body)
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',original_complete)
        prior=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert prior.status=='running'
        if failure=='crash_expired':
            import psycopg
            with psycopg.connect(recovery_dsn) as conn:
                conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 minute' WHERE turn_id=%s",(prior.turn_id,))
        elif failure=='crash_interrupted':
            writer.adapter.service.fail_turn(ledger.TurnFailure(world_id=world,conversation_id=prior.conversation_id,
                turn_id=prior.turn_id,expected_revision=prior.revision,failure_code='synthetic_persistence_interrupt'),interrupted=True)
        save_page(tmp_path,page.document_id,'A newer author page must survive recovery.')
        newer=get_workspace_document_snapshot(tmp_path,page.document_id)
        assert newer.content_sha256!=source.content_sha256
        from apps.live_control_server.services import plan_source_turn
        def forbid_fresh_source(*args,**kwargs):
            raise AssertionError('Prepared recovery must not reacquire current source authority')
        monkeypatch.setattr(plan_source_turn,'prepare',forbid_fresh_source)
        if recovery_mutation is not None:
            import psycopg
            from psycopg.types.json import Jsonb
            with psycopg.connect(recovery_dsn) as conn:
                if recovery_mutation=='raw':
                    key=uuid5(cap.idempotency_key,'image') if proposal=='image' else cap.idempotency_key
                    obj=conn.execute('SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s',(world,key)).fetchone()[0]
                    if proposal=='image':
                        obj['writer_proof']['raw_response']='{}'
                    else:
                        obj['raw_response']='{}'
                    conn.execute('UPDATE agent.build_proposal SET payload=%s WHERE world_id=%s AND action_id=%s',(Jsonb(obj),world,key))
                elif recovery_mutation in {'seal','scope','unknown'}:
                    row=conn.execute('SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s',(prior.turn_id,prior.attempt)).fetchone()[0]
                    sealed=next(e for e in row['events'] if e['kind']=='native_provider_outcome')
                    if recovery_mutation=='scope':
                        row['scope']['conversation_id']=str(uuid4())
                    elif recovery_mutation=='unknown':
                        sealed['status']='unknown'
                    else:
                        sealed['output_sha256']='0'*64
                    conn.execute('UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s AND product_attempt=%s',(Jsonb(row),prior.turn_id,prior.attempt))
                elif recovery_mutation=='trace':
                    row=conn.execute('SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s',(prior.turn_id,prior.attempt)).fetchone()[0]
                    for observation in row['observations']:
                        if observation.get('kind')=='context_snapshot' and observation.get('stage')=='after':
                            observation['materials']=[m for m in observation['materials'] if not m.get('item_id','').startswith('unvalidated-provider-answer:')]
                    conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',(Jsonb(row),prior.turn_id,prior.attempt))
                else:
                    raise AssertionError(recovery_mutation)
        calls_before_recovery=len(decisions.calls),len(writer.calls)
        response=client.post('/api/live/agent/turn',json=body)
        if recovery_mutation is not None:
            assert response.status_code==409,response.text
            assert response.json()['detail']['code']=='build_prepared_recovery_invalid'
            assert (len(decisions.calls),len(writer.calls))==calls_before_recovery
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
            return
        assert response.status_code==200,response.text
        assert response.json()['knowledge_context']['delivery_replay'] is True
        assert (len(decisions.calls),len(writer.calls))==calls_before_recovery
        after=writer.adapter.service.inspect_turn(world_id=world,turn_id=prior.turn_id)
        assert after.status=='completed' and after.attempt==prior.attempt
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
        with psycopg.connect(recovery_dsn) as conn:
            state=conn.execute("SELECT payload->>'state' FROM agent.turn_rules_execution WHERE turn_id=%s AND product_attempt=%s",(prior.turn_id,prior.attempt)).fetchone()[0]
        assert state==('failed' if failure=='crash_interrupted' else 'unused')
        return
    if failure in {'retry_discussion','retry_unknown'}:
        original_complete=AgentConversationService.complete_native_base_turn
        def interrupted_delivery(*args,**kwargs):
            raise RuntimeError('synthetic delivery interruption after writer response')
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',interrupted_delivery)
        refused=client.post('/api/live/agent/turn',json=body)
        assert refused.status_code==503,refused.text
        monkeypatch.setattr(AgentConversationService,'complete_native_base_turn',original_complete)
        failed=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert failed.status=='interrupted'
        prefix=f'/api/live/agent/worlds/{world}/conversations/{failed.conversation_id}'
        eligible=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
        assert eligible.status_code==200,eligible.text
        eligibility=eligible.json()['turns'][0]['context']
        if failure=='retry_unknown':
            assert eligibility['eligible'] is False and eligibility['reason']=='unknown_outcome',eligible.text
            blocked=client.get(prefix+f'/turns/{failed.turn_id}/discussion-retry-input',params={'revision':failed.revision})
            assert blocked.status_code==409,blocked.text
            assert len(writer.calls)==1
            return
        assert eligibility['eligible'] is True,eligible.text
        retained=client.get(prefix+f'/turns/{failed.turn_id}/discussion-retry-input',params={'revision':failed.revision})
        assert retained.status_code==200,retained.text
        assert retained.json()['snapshot']==draft.snapshot.model_dump(mode='json',by_alias=True)
        assert retained.json()['authored_references']==selected.model_dump(mode='json',by_alias=True)
        assert retained.json()['message']==body['message']
        retry={**body,'turn_id':str(uuid4()),'retry_of':{'turn_id':str(failed.turn_id),'revision':failed.revision,
            'retained_snapshot_sha256':draft.snapshot.snapshot_sha256}}
        expected_page=source
        if retry_mutation=='newer_page':
            save_page(tmp_path,page.document_id,'A newer saved author page must survive explicit Retry.')
            expected_page=get_workspace_document_snapshot(tmp_path,page.document_id)
        elif retry_mutation=='question':
            retry['message']+=' Change the original question.'
        elif retry_mutation=='reference':
            retry['build_authored_references']=None
        elif retry_mutation=='revision':
            retry['retry_of']={**retry['retry_of'],'revision':failed.revision+1}
        count=len(writer.calls)
        all_calls=len(decisions.calls),len(writer.calls)
        if retry_mutation=='race':
            from concurrent.futures import ThreadPoolExecutor
            candidates=[retry,{**retry,'turn_id':str(uuid4())}]
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses=list(pool.map(lambda candidate:client.post('/api/live/agent/turn',json=candidate),candidates))
            assert sorted(r.status_code for r in responses)==[200,409],[r.text for r in responses]
            winner=next(i for i,r in enumerate(responses) if r.status_code==200)
            retry,answer=candidates[winner],responses[winner]
            import psycopg
            with psycopg.connect(recovery_dsn) as conn:
                edges=conn.execute('SELECT ordinal FROM agent.turn_retry WHERE predecessor_id=%s',(failed.turn_id,)).fetchall()
            assert edges==[(1,)]
        else:
            answer=client.post('/api/live/agent/turn',json=retry)
        if retry_mutation in {'question','reference','revision','newer_page'}:
            assert answer.status_code==409,answer.text
            assert (len(decisions.calls),len(writer.calls))==all_calls
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==expected_page
            return
        assert answer.status_code==200,answer.text
        assert len(writer.calls)==count+1
        assert answer.json()['knowledge_context']['delivery_replay'] is False
        replay=client.post('/api/live/agent/turn',json=retry)
        assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True,replay.text
        assert len(writer.calls)==count+1
        again=client.post('/api/live/agent/turn',json={**retry,'turn_id':str(uuid4())})
        assert again.status_code==409,again.text
        assert len(writer.calls)==count+1
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==expected_page
        after=client.get(prefix+'/retry-context',params={'turn_ids':str(failed.turn_id)})
        assert after.status_code==200 and after.json()['turns'][0]['context']['reason']=='retried',after.text
        original=writer.adapter.service.inspect_turn(world_id=world,turn_id=failed.turn_id)
        assert original.status=='interrupted' and original.failure_code==failed.failure_code
        return
    if connected_review:
        body['message']='Prepare a separate connected page from the saved proposal.'
    response = client.post('/api/live/agent/turn', json=body)
    if connected_review:
        if connected_review!='valid':
            assert response.status_code==503,response.text
            assert len(writer.calls)==1
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
            assert lane.repo.get_head(world).head_revision_id==current_revision
            return
        assert response.status_code==200,response.text
        completion=response.json()['knowledge_context']['completion']
        assert completion['answer_segments']==[] and completion['collaboration']['kind']=='connected_page'
        current=writer.adapter.service.inspect_turn(world_id=world,turn_id=writer.adapter.turn.turn_id)
        assert current.status=='completed'
        from apps.live_control_server.services.agent_connected_page_origin import open_origin
        direct_origin=open_origin(writer.adapter.service,world,current.turn_id)
        origin_url=f'/api/live/agent/worlds/{world}/conversation/turns/{current.turn_id}/connected-page-origin'
        opened=client.get(origin_url)
        assert opened.status_code==200,opened.text
        assert opened.json()==direct_origin
        origin=opened.json()['origin']
        assert origin['document_id']==page.document_id and origin['content_sha256']==source.content_sha256
        assert 'A proposed conversation.' in origin['selected_text']
        assert opened.json()['read_id']==completion['collaboration']['read_id']
        save_page(tmp_path,page.document_id,'A newer page must not replace the reviewed origin.')
        newer=get_workspace_document_snapshot(tmp_path,page.document_id)
        again=client.get(origin_url)
        assert again.status_code==200 and again.json()==opened.json(),again.text
        before=len(decisions.calls),len(writer.calls)
        history=client.get(f'/api/live/agent/worlds/{world}/conversation',params={'include_turn_correlation':'true'})
        assert history.status_code==200,history.text
        assert history.json()['turns'][0]['knowledge_context']['completion']==completion
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True,replay.text
        assert (len(decisions.calls),len(writer.calls))==before
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==newer
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure in {'revision','node','reference_world'}:
        assert response.status_code == (422 if failure=='reference_world' else 409), response.text
        if failure!='reference_world':
            assert response.json()['detail']['code']=='native_graph_query_rejected'
        assert not decisions.calls and not writer.calls and not classic_calls
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if failure in {'section_scope','selection_text'}:
        assert response.status_code==503,response.text
        assert not writer.calls and not classic_calls
        if failure=='selection_text':
            assert all('writer_selection' not in req.content.decode() for req in decisions.calls)
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    if proposal and failure is not None:
        from application_state.build_proposal.service import BuildProposalService
        assert response.status_code==503,response.text
        assert len(writer.calls)==(0 if failure in {'native_work','rules_frame','used_rules'} else 1)
        assert not classic_calls
        if failure=='used_rules':
            from application_state.errors import ApplicationStateNotFoundError
            assert len(rules_reads)==1 and rules_reads[0].observation.status=='evidence'
            used=writer.adapter.rules_runtime.native.record.execution
            assert used.budget_use.calls==1 and used.supports
            with pytest.raises(ApplicationStateNotFoundError):
                current_creative()
            assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
            assert lane.repo.get_head(world).head_revision_id==current_revision
            return
        if proposal=='image' and failure!='stale_rules':
            from application_state.errors import ApplicationStateNotFoundError
            with pytest.raises(ApplicationStateNotFoundError):
                current_creative()
        else:
            record=current_creative()
            if failure!='stale_rules':
                assert record.state in {'failed','unknown'} and record.proposal is None
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    assert response.status_code == 200, response.text + str(classic_calls)
    assert not classic_calls and len(writer.calls) == 1
    payload = response.json()
    context = payload['knowledge_context']
    assert context['schema'] == 'dmb_agent_surface_native_context_response_v1'
    assert context['receipt']['work_context']['surface_id'] == 'build'
    assert context['receipt']['native_query']['authority']['revision_id'] == current_revision
    assert context['receipt']['native_query']['authored_targets'][0]['selection_revision_id'] == original_revision
    service = AgentConversationService()
    turn = service.inspect_turn(world_id=world, turn_id=writer.adapter.turn.turn_id)
    assert turn.status == 'completed' and type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
    if with_draft:
        captured = next(e for e in turn.graph_context_execution.events if isinstance(e,t.BuildDraftContextCapturedV1))
        assert captured.record.snapshot==draft.snapshot
        assert captured.sequence < next(e.sequence for e in turn.graph_context_execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
        assert all('unsaved orchid' not in req.content.decode() for req in decisions.calls)
    assert not any(isinstance(e,(t.BuildDraftProviderInclusionV1,t.BuildSectionProviderInclusionV1))
        for e in turn.graph_context_execution.events)
    captures = [event for event in turn.graph_context_execution.events if isinstance(event, t.BuildAuthoredReferencesCapturedV1)]
    assert len(captures) == 1 and captures[0].references == selected
    if proposal:
        from application_state.build_proposal.service import BuildProposalService
        if proposal=='image':
            from uuid import uuid5
            from application_state.build_proposal.images import BuildImageService
            record=BuildImageService().get(uuid5(cap.idempotency_key,'image'),writer.adapter.build_image_owner)
            assert record.state=='prepared' and record.prompt=='A proposed copper lamp beside an orchid.'
            assert record.purpose=='illustration' and record.asset_id is None
            authorization=record.writer_proof.authorization
            assert context['completion']['schema']=='dmb_build_image_preparation_completion_v1'
        else:
            record=BuildProposalService().get(world,cap.idempotency_key)
            assert record.state=='proposed' and record.proposal.replacement_markdown=='A proposed copper lamp.'
            authorization=record.authorization
            assert context['completion']['schema']=='dmb_build_authoring_completion_v1'
        assert context['completion']['action_id']==str(record.action_id)
        assert authorization.provider_attempt_id==turn.completion.provider_attempt_id
        for correlated in (False,True):
            history=client.get(f'/api/live/agent/worlds/{world}/conversation',params={'include_turn_correlation':str(correlated).lower()})
            assert history.status_code==200,history.text
            assert history.json()['turns'][0]['knowledge_context']['completion']==context['completion']
        import os
        if proposal=='image' and (destination:=os.environ.get('DMB_NATIVE_BUILD_IMAGE_CONTEXT')):
            from pathlib import Path
            path=Path(destination)
            captured=json.loads(path.read_text())
            captured['image_context']=context
            path.write_text(json.dumps(captured,indent=2)+'\n')
        if proposal!='image' and (destination:=os.environ.get('DMB_NATIVE_BUILD_PROPOSAL_WIRE')):
            from pathlib import Path
            path=Path(destination)
            captured=json.loads(path.read_text())
            captured['proposal_wire']=dict(request=body,response=payload,history=history.json(),
                record=record.model_dump(mode='json',exclude={'raw_response'}))
            path.write_text(json.dumps(captured,indent=2)+'\n')
        before=len(decisions.calls),len(writer.calls)
        replay=client.post('/api/live/agent/turn',json=body)
        assert replay.status_code==200,replay.text
        assert replay.json()['knowledge_context']['delivery_replay'] is True
        assert replay.json()['knowledge_context']['completion']==context['completion']
        assert (len(decisions.calls),len(writer.calls))==before
        assert get_workspace_document_snapshot(tmp_path,page.document_id)==source
        assert lane.repo.get_head(world).head_revision_id==current_revision
        return
    citations = context['completion']['native_assertion_citations']
    assert citations and all(c['read_revision_id'] == current_revision for c in citations)
    opened = client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-assertion-sources/0')
    assert opened.status_code == 200, opened.text
    assert opened.json()['content'] and opened.json()['citation'] == citations[0]
    for correlated in (False, True):
        history = client.get(f'/api/live/agent/worlds/{world}/conversation',
            params={'include_turn_correlation': str(correlated).lower()})
        assert history.status_code == 200, history.text
        row = history.json()['turns'][0]
        assert 'plan_context' not in row
        assert ('idempotency_key' in row) is correlated
        assert row['knowledge_context']['receipt'] == context['receipt']
        assert row['knowledge_context']['completion'] == context['completion']
    import os
    if not with_draft and (destination := os.environ.get('DMB_NATIVE_BUILD_WIRE')):
        from pathlib import Path
        captured=dict(request=body,response=payload,history=history.json(),source=opened.json())
        if saved:
            cite=context['completion']['saved_source_citations'][0]
            saved_read=client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/saved-sections/{cite["segment_index"]}/{cite["section_event_ids"][0]}')
            assert saved_read.status_code==200,saved_read.text
            captured['saved_source']=saved_read.json()
        Path(destination).write_text(json.dumps(captured,indent=2)+'\n')
    before = (len(decisions.calls), len(writer.calls))
    replay = client.post('/api/live/agent/turn', json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()['knowledge_context']['delivery_replay'] is True
    if saved:
        from apps.live_control_server.services.agent_saved_sections import saved_section_targets
        targets=saved_section_targets(turn)
        assert targets
        cite=context['completion']['saved_source_citations'][0]
        assert cite['segment_index']==1
        assert any(isinstance(e,t.BuildWriterEvidenceSelectionV1) and e.mode=='jev' for e in turn.graph_context_execution.events)
        for identity in cite['section_event_ids']:
            url=f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/saved-sections/{cite["segment_index"]}/{identity}'
            original=client.get(url)
            assert original.status_code==200,original.text
            assert original.json()['target']['source_basis']==context['receipt']['work_context']['source_basis']
        save_page(tmp_path,page.document_id,'# Changed after the accepted reply\n\nNewer text must never replace a citation.\n')
        reopened=client.get(url)
        assert reopened.status_code==200 and reopened.json()==original.json()
        source=get_workspace_document_snapshot(tmp_path,page.document_id)
    assert (len(decisions.calls), len(writer.calls)) == before
    assert get_workspace_document_snapshot(tmp_path, page.document_id) == source
    assert lane.repo.get_head(world).head_revision_id == current_revision

    return SimpleNamespace(client=client,world=world,page=page,source=source,request=body,
        draft=draft,selected=selected,writer=writer,decisions=decisions,turn=turn,service=service,
        revision=current_revision)


@pytest.mark.parametrize('kind,related,mutation,output_review',[
    ('discuss',False,None,None),('discuss',False,None,'questions'),('discuss',False,None,'plan'),
    ('prepare_insertion',False,None,None),('prepare_insertion',True,None,None),
    ('discuss',False,'message',None),('prepare_insertion',False,'command',None)]
    +[(kind,False,mutation,None) for kind in ('discuss','prepare_insertion')
        for mutation in ('writer_allowance','writer_input')])
def test_native_reviewed_step_preserves_the_author_choice(lane,tmp_path,monkeypatch,application_state_dsn,kind,related,mutation,output_review):
    from application_state.agent_conversation import work_plan as w
    from application_state.build_proposal.types import BuildWriteCapability
    case=_fresh_case(lane,tmp_path,monkeypatch,None,True,False,False)
    if related:
        page=create_page_fixture(tmp_path,world_id=case.world,campaign_id=case.world,title='Related authored note',
            kind='worldbuilding_source',source_domain='worldbuilding',document_class='lore',
            authority_state='draft',visibility_state='internal')
        save_page(tmp_path,page.document_id,'A separate proposed lamp note.')
    step=w.StepV2(step_id=uuid4(),text='Discuss where the lamp belongs.' if kind=='discuss' else 'Prepare a proposed lamp detail.',
        selected=True,kind=kind,references=())
    deferred=w.StepV2(step_id=uuid4(),text='Write a useful paragraph only after placement is chosen.',selected=False,kind='prepare_insertion',references=())
    review=w.ReviewV3(expected_revision=0,objective='Choose placement, then prepare writing for review.',
        steps=[step,deferred],root_references=case.selected.references)
    plan=w.save(case.world,case.turn.conversation_id,case.turn.turn_id,review)
    continued=w.continue_step(case.world,case.turn.conversation_id,case.turn.turn_id,
        w.Continue(expected_revision=plan['revision'],step_id=step.step_id,command_id=uuid4()))
    dispatch=continued['dispatch']
    cap=BuildWriteCapability(idempotency_key=uuid4(),conversation_id=case.draft.conversation_id,
        expected_pointer_revision=case.draft.expected_pointer_revision,draft_markdown=case.draft.snapshot.draft_markdown,
        basis=dict(**{k:getattr(case.draft.snapshot,k) for k in ('world_id','document_id','registry_revision',
            'content_sha256','visibility','draft_sha256','editor_sha256','draft_generation')},caret=1,selection_generation=0))
    body={**case.request,'client_thread_id':dispatch['client_thread_id'],'turn_id':dispatch['client_turn_id'],
        'message':dispatch['message'],'reviewed_step':continued['reviewed_step'],
        'build_write_capability':cap.model_dump(mode='json'),
        'build_authored_references':dispatch['authored_references']}
    if mutation=='message':
        body['message']+=' Change this approved instruction.'
    if mutation=='command':
        body['reviewed_step']={**body['reviewed_step'],'command_id':str(uuid4())}
    before=len(case.decisions.calls),len(case.writer.calls)
    case.decisions.deny_routing=True
    case.writer.mode=kind=='prepare_insertion'
    if output_review is not None:
        case.writer.review=({'kind':'questions','questions':[{'text':'Where should the lamp stand?'}]} if output_review=='questions'
            else {'kind':'plan','objective':'Unapproved work','steps':[{'text':'Write the deferred paragraph.','kind':'prepare_insertion','selected':True}]})
    accounting_refusals=[]
    if mutation in {'writer_allowance','writer_input'}:
        from tests.application_state.test_surface_native_writers import snapshot
        from application_state.errors import ApplicationStateValidationError
        from apps.live_control_server.services.agent_turn_service import _json_node_count
        original=AgentConversationService.authorize_native_writer
        def changed_physical_request(owner,world_id,conversation_id,turn_id,**values):
            turn=owner.inspect_turn(world_id=world_id,turn_id=turn_id)
            assert turn.graph_context_receipt.assembled_input.assembler_version=='reviewed_author_admission_v1'
            auth=values['authorization']
            if mutation=='writer_allowance':
                request=json.loads(values['prepared_request_json'])
                request['max_output_tokens']=auth.output_token_reserve+1
                raw=json.dumps(request,ensure_ascii=False)
                values={**values,'prepared_request_json':raw,'authorization':auth.model_copy(update={
                    'envelope_sha256':sha256(raw.encode()).hexdigest(),
                    'input_tokens':len(raw.encode())+64*(1+_json_node_count(request))})}
            else:
                values={**values,'authorization':auth.model_copy(update={'input_tokens':0})}
            persisted=SimpleNamespace(dsn=application_state_dsn,turn=turn)
            prior=snapshot(persisted)
            try:
                original(owner,world_id,conversation_id,turn_id,**values)
            except ApplicationStateValidationError:
                assert snapshot(persisted)==prior
                accounting_refusals.append(mutation)
                raise
            raise AssertionError('APP admitted forged physical writer accounting')
        monkeypatch.setattr(AgentConversationService,'authorize_native_writer',changed_physical_request)
    response=case.client.post('/api/live/agent/turn',json=body)
    if mutation in {'writer_allowance','writer_input'}:
        assert response.status_code==503,response.text
        assert accounting_refusals==[mutation]
        assert len(case.writer.calls)==before[1]
        assert get_workspace_document_snapshot(tmp_path,case.page.document_id)==case.source
        return
    if mutation:
        assert response.status_code in {404,409},response.text
        assert (len(case.decisions.calls),len(case.writer.calls))==before
        return
    if output_review=='plan':
        assert response.status_code==503,response.text
        assert len(case.writer.calls)==before[1]+1
        return
    assert response.status_code==200,response.text
    context=response.json()['knowledge_context']
    if kind=='discuss':
        assert context['completion']['collaboration']==case.writer.review
    assert context['receipt']['assembled_input']['assembler_version']=='reviewed_author_admission_v1'
    actual=case.service.inspect_turn(world_id=case.world,turn_id=case.writer.adapter.turn.turn_id)
    assert actual.status=='completed'
    selections=[e for e in actual.graph_context_execution.events if isinstance(e,t.BuildReviewedActionSelectionV1)]
    assert len(selections)==1 and selections[0].operation==('answer_from_sources' if kind=='discuss' else 'propose_build_insertion')
    assert not any(isinstance(e,t.BuildRequestedWorkResolutionV1) for e in actual.graph_context_execution.events)
    expected='dmb_surface_native_completion_v1' if kind=='discuss' else 'dmb_build_authoring_completion_v1'
    assert context['completion']['schema']==expected
    assert len(case.writer.calls)==before[1]+1
    after=len(case.decisions.calls),len(case.writer.calls)
    replay=case.client.post('/api/live/agent/turn',json=body)
    assert replay.status_code==200 and replay.json()['knowledge_context']['delivery_replay'] is True,replay.text
    assert (len(case.decisions.calls),len(case.writer.calls))==after
    assert get_workspace_document_snapshot(tmp_path,case.page.document_id)==case.source


@pytest.mark.parametrize('proposal',[True,'image'])
@pytest.mark.parametrize('state',['live','expired','interrupted'])
def test_native_persisted_object_recovers_without_another_provider(lane,tmp_path,monkeypatch,application_state_dsn,proposal,state):
    _fresh_case(lane,tmp_path,monkeypatch,'crash_'+state,True,False,proposal,recovery_dsn=application_state_dsn)


@pytest.mark.parametrize('proposal',[True,'image'])
@pytest.mark.parametrize('mutation',['raw','seal','trace','scope','unknown'])
def test_native_persisted_object_recovery_refuses_corrupted_owners(lane,tmp_path,monkeypatch,application_state_dsn,proposal,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'crash_live',True,False,proposal,recovery_dsn=application_state_dsn,recovery_mutation=mutation)


@pytest.mark.parametrize('mutation',[None,'race','newer_page','question','reference','revision','unknown'])
def test_native_failed_discussion_exposes_original_context_and_one_explicit_retry(lane,tmp_path,monkeypatch,application_state_dsn,mutation):
    _fresh_case(lane,tmp_path,monkeypatch,'retry_unknown' if mutation=='unknown' else 'retry_discussion',True,False,False,
        recovery_dsn=application_state_dsn,retry_mutation=mutation)


@pytest.mark.parametrize('review',['valid','foreign_read','foreign_quote'])
def test_native_connected_page_review_uses_its_included_saved_origin(lane,tmp_path,monkeypatch,review):
    _fresh_case(lane,tmp_path,monkeypatch,None,True,True,False,connected_review=review)


@pytest.mark.parametrize('judgment',['direct_support','qualification_or_conflict','uncertain','irrelevant'])
def test_ordinary_build_selects_native_body_and_reopens_only_included_support(lane,tmp_path,monkeypatch,judgment):
    from application_state.agent_conversation import native_corpus as corpus
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body=judgment)
    events=case.turn.graph_context_execution.events
    vote,=[e for e in events if type(e) is t.BuildWriterEvidenceSelectionV2]
    acquired=corpus.acquired_body_reads(case.turn.graph_context_execution)
    assert acquired and not vote.source_event_ids
    assert {k:v for k,v in vote.judgments.items() if k.startswith('body:')}=={
        corpus.body_selection_unit_id(r):judgment for r in acquired}
    calls=[json.loads(r.content) for r in case.decisions.calls
           if json.loads(r.content)['state'].get('phase')=='writer_selection']
    assert len(calls)==1
    for read in acquired:
        unit=calls[0]['state']['sources'][corpus.body_selection_unit_id(read)]
        assert unit['text']==read.excerpt.text
    citations=case.turn.completion.native_body_citations
    assert bool(citations)==(judgment!='irrelevant')
    for index,citation in enumerate(citations):
        opened=case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{case.turn.turn_id}/native-body-excerpts/{index}')
        assert opened.status_code==200,opened.text
        assert opened.json()['content']


def test_ordinary_native_body_selector_rejects_substituted_input_before_dispatch(lane,tmp_path,monkeypatch):
    _fresh_case(lane,tmp_path,monkeypatch,'selection_text',False,False,False,native_body='direct_support')


@pytest.mark.parametrize('copies', [3200, 6200])
def test_native_writer_selector_uses_its_verified_long_context_at_app_boundary(lane,tmp_path,monkeypatch,copies):
    from dungeonmind.application.vnext import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract,dungeonbuddy_dnd5e_custom_predicate_profile
    from tests.test_source_statements import NOW
    from application_state.agent_conversation.build_decision_context import LONG_LIMIT
    # A real acquired body exceeds the initial64k envelope; the larger case also
    # exceeds the retired256KB request limit while fitting frozen token admission.
    text='# Retained source\n\n'+'An unrelated source-local episode was recorded.\n'*copies
    raw=text.encode()
    publish_native_text_source_evidence(repository=lane.repo,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        request=NativeTextSourceAdmissionV1(space_id=lane.world.world_id,admission_id='large-selector-source',
            expected_parent_revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
            created_at=NOW,body_text=text,expected_body_sha256=sha256(raw).hexdigest(),
            source_classification='dungeonbuddy.source:session_recap',authority='primary',
            visibility={'kind':'labels_any','labels':['dungeonbuddy.visibility:gm']},
            spans=[dict(client_ref='context',evidence_role='context',start_byte=0,end_byte=len(raw),
                        expected_slice_sha256=sha256(raw).hexdigest())]))
    from application_state.agent_conversation import writer_evidence_selection as selection
    from application_state.errors import ApplicationStateValidationError
    append=AgentConversationService.record_build_writer_evidence_selection
    checked=[]

    def check_append(self,world,conversation,turn_id,**kwargs):
        before=self.inspect_turn(world_id=world,turn_id=turn_id)
        proof=kwargs['producer_proof']
        vote=kwargs['selection']
        auth=next(e for e in before.graph_context_execution.events
                  if isinstance(e,t.ProviderAttemptAuthorizedEventV3)
                  and e.provider_attempt_id==vote.controller_attempt_id)
        assert sha256(proof['request_json'].encode()).hexdigest()==auth.envelope_sha256
        assert (len(proof['request_json'].encode())>256000)==(copies==6200)
        assert before.graph_context_execution.policy.controller_continuation_accounting.raw_wire_limit_bytes is None
        for kind in ('request','response','oversized_response'):
            changed=dict(proof)
            event=vote
            if kind=='oversized_response':
                changed['response_json']+=' '*256001
                event=vote.model_copy(update={'controller_response_sha256':sha256(changed['response_json'].encode()).hexdigest()})
            else:
                changed[kind+'_json']+=' '
            with pytest.raises(ApplicationStateValidationError,match='Selection producer bytes differ'):
                append(self,world,conversation,turn_id,**{**kwargs,'selection':event,'producer_proof':changed})
            assert self.inspect_turn(world_id=world,turn_id=turn_id)==before
        if copies==6200:
            # Frozen historical requests retain their bound, independently of the
            # current producer. No retained row or historical policy is rewritten.
            execution=before.graph_context_execution
            old=t.BuildControllerContinuationAccountingV3.model_validate({
                **execution.policy.controller_continuation_accounting.model_dump(),
                'policy':'o200k_double_plus_4096_adaptive_context_v3','raw_wire_limit_bytes':256000})
            historical=before.model_copy(update={'graph_context_execution':execution.model_copy(update={
                'policy':execution.policy.model_copy(update={'controller_continuation_accounting':old})})})
            trace,=self.list_context_trace_attempts(world_id=world,turn_id=turn_id)
            with pytest.raises(ValueError,match='Selection producer bytes differ'):
                selection.validate_selection_proof(historical,vote,trace.model_dump(mode='json',by_alias=True),proof)
        result=append(self,world,conversation,turn_id,**kwargs)
        checked.append(True)
        return result

    monkeypatch.setattr(AgentConversationService,'record_build_writer_evidence_selection',check_append)
    case=_fresh_case(lane,tmp_path,monkeypatch,None,False,False,False,native_body='irrelevant')
    assert checked==[True]
    record=case.turn.graph_context_execution
    event,=[e for e in record.events if type(e) is t.ProviderAttemptAuthorizedEventV5
            and e.context_phase=='writer_selection']
    assembled=case.turn.graph_context_receipt.assembled_input
    assert assembled.context_window_limit==64000
    assert assembled.context_window_limit < event.input_tokens <= LONG_LIMIT
    assert event.context_mode=='long_context'
    prefix=record.model_copy(update={'events':record.events[:event.sequence]})
    t.validate_provider_envelope_accounting(assembled,prefix,event)
    request,=[json.loads(req.content) for req in case.decisions.calls
              if json.loads(req.content)['state'].get('phase')=='writer_selection']
    assert any(row['text']==text for row in request['state']['sources'].values())
    assert len(case.writer.calls)==1 and text not in case.writer.calls[0].content.decode()
    # A mode declaration alone cannot relax scope, phase or accounting. These
    # are rejected by the same owner used for actual APP authorization above.
    for update in ({'context_mode':'default'},{'context_phase':'select'},
                   {'input_tokens':LONG_LIMIT+1},{'output_token_reserve':LONG_LIMIT},
                   {'dispatch_identity_sha256':'f'*64},{'model':'another-model'}):
        with pytest.raises(ValueError):
            t.validate_provider_envelope_accounting(assembled,prefix,event.model_copy(update=update))
    fields={k:v for k,v in event.model_dump().items() if k in t.ProviderAttemptAuthorizedEventV3.model_fields}
    fields['kind']='provider_attempt_authorized_v3'
    unbound=t.ProviderAttemptAuthorizedEventV3.model_validate(fields)
    with pytest.raises(ValueError,match='frozen context window'):
        t.validate_provider_envelope_accounting(assembled,prefix,unbound)
