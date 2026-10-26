"""Authored node context through the actual SDK and disposable APP boundaries."""
from dataclasses import replace
import json
import pytest
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1, AuthoredGraphReferencesV1
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_build_world_context import build_case, world_case, WorldDecisions
from tests.test_agent_build_jev_ordinary_harness import WriterWire, ordinary_case
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


def referenced_case(build_case, monkeypatch, *, authoring=True):
    authoring_case, _ = ordinary_case(build_case, monkeypatch, authoring=authoring)
    (source, request, bootstrap), reads = world_case(authoring_case, monkeypatch)
    # The native boundary is synthetic in this fixture; SDK and APP are real.
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
    from graph_memory.retrieval.models import WorldGraphRetrievalNode
    original_object = native.get_object_with_reviewed_sources_direct_v3
    def current_object(services, query):
        value = original_object(services, query)
        return replace(value, result=value.result.model_copy(update={'nodes': [WorldGraphRetrievalNode(node_id='frank',
            label='River Watch', kind='npc', role='match')] if query.node_id == 'frank' else []}))
    monkeypatch.setattr(native, 'get_object_with_reviewed_sources_direct_v3', current_object)
    monkeypatch.setattr(native, 'get_object_direct', lambda services, query: current_object(services, query).result)
    ref = AuthoredGraphReferenceV1(managed_world_id='elderwyld', native_world_id=bootstrap.world_scope.world_id,
        binding_version=bootstrap.binding_version, graph_revision=bootstrap.world_scope.revision_id,
        node_id='frank', label='CLIENT DISPLAY ONLY — NEVER PROVIDER CONTEXT')
    request = request.model_copy(update={'build_authored_references': AuthoredGraphReferencesV1(references=(ref,))})
    return (source, request, bootstrap), reads


@pytest.mark.parametrize('operation', ['propose_build_insertion', 'prepare_build_image'])
def test_authored_object_reaches_one_authoring_writer_with_durable_input_proof(build_case, monkeypatch, tmp_path, operation):
    case, reads = referenced_case(build_case, monkeypatch)
    decisions = WorldDecisions()
    decisions.operation = operation
    from tests.test_build_jev_image import ImageWire
    writer = ImageWire() if operation == 'prepare_build_image' else WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    response = execute(case, tmp_path, harness, operator_subject='local_operator')
    completion = response.knowledge_context.completion
    assert isinstance(completion, t.BuildImagePreparationCompletionV1 if operation == 'prepare_build_image' else t.BuildAuthoringCompletionV1)
    assert len(writer.calls) == 1
    body = json.loads(writer.calls[0].content)
    packet = json.loads(body['input'])
    assert packet['authored_reference_context']['selected_references']['references'][0]['node_id'] == 'frank'
    assert packet['authored_reference_passages']
    assert all('CLIENT DISPLAY ONLY' not in call.content.decode() for call in [*writer.calls, *decisions.calls])
    service = AgentConversationService()
    turns = service.list_turns('elderwyld', case[1].build_write_capability.conversation_id)
    turn = next(turn for turn in turns if turn.completion == completion)
    execution = turn.graph_context_execution
    assert len([e for e in execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1)]) == 1
    proofs = [e for e in execution.events if isinstance(e, t.BuildAuthoredProviderInclusionV1)]
    assert len(proofs) == 1 and proofs[0].source_read_event_ids
    assert proofs[0].provider_attempt_id == completion.provider_attempt_id
    assert proofs[0].envelope_sha256 == completion.envelope_sha256
    from application_state.agent_conversation.context_trace import TraceAuthoredGraphReferenceV1
    traces = service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)
    observed = [item.execution_event for trace in traces for item in trace.observations if isinstance(item, TraceAuthoredGraphReferenceV1)]
    actual = [item for item in execution.events if isinstance(item, (t.BuildAuthoredReferencesCapturedV1,
        t.BuildAuthoredReferenceAuthorizedV1,t.BuildAuthoredReferenceReadV1,t.BuildAuthoredProviderInclusionV1))]
    assert observed == actual
    assert len(observed) == 4



@pytest.mark.parametrize('mutation', ['source_text', 'missing_context'])
def test_self_consistent_host_packet_cannot_substitute_for_actual_source_authority(build_case, monkeypatch, tmp_path, mutation):
    case, _ = referenced_case(build_case, monkeypatch)
    from apps.live_control_server.services import build_authored_references as owner
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    original = owner.writer_material
    def corrupt(adapter):
        material = original(adapter)
        if mutation == 'source_text':
            material['authored_reference_passages'][0]['text'] = 'Unsupported replacement source text.'
        else:
            material.pop('authored_reference_context')
        return material
    monkeypatch.setattr(owner, 'writer_material', corrupt)
    decisions = WorldDecisions()
    decisions.operation = 'propose_build_insertion'
    writer = WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, harness)
    assert not writer.calls


def test_discussion_keeps_authored_reads_without_asking_for_a_relevance_vote(build_case, monkeypatch, tmp_path):
    case, reads = referenced_case(build_case, monkeypatch, authoring=False)
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    response = execute(case, tmp_path, harness)
    assert len(writer.calls) == 1
    # One original-snapshot membership check plus one current object acquisition.
    assert reads == {'graph': 2, 'source': 1}
    # Native object acquisition is host-owned; it must not reappear as an optional vote.
    assert all('world-object:frank' not in call.content.decode() for call in decisions.calls)
    packet = json.loads(json.loads(writer.calls[0].content)['input'])
    assert packet['authored_reference_context']['selected_references']['references'][0]['node_id'] == 'frank'
    assert packet['opened_passages']
    assert all('CLIENT DISPLAY ONLY' not in call.content.decode() for call in [*writer.calls, *decisions.calls])
    from application_state.agent_conversation.authored_graph_references import source_event_ids
    turn = AgentConversationService().list_turns('elderwyld', response.conversation.conversation_id)[0]
    mandatory = source_event_ids(turn.graph_context_execution)
    selections = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildWriterEvidenceSelectionV1)]
    assert len(selections) == 1
    assert not mandatory.intersection(selections[0].source_event_ids)

def test_missing_origin_retains_selected_input_without_authorizing_a_provider(build_case, monkeypatch, tmp_path):
    case, _ = referenced_case(build_case, monkeypatch, authoring=False)
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    original = native.get_object_direct
    monkeypatch.setattr(native, 'get_object_direct', lambda services, query: original(services, query).model_copy(update={'nodes': []}))
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True,
        accounting=counter(), decision_transport=decisions, writer_transport=writer)
    with pytest.raises(AgentTurnServiceError, match='absent from its original snapshot'):
        execute(case, tmp_path, harness)
    assert not decisions.calls and not writer.calls
    service = AgentConversationService()
    pointer = service.get_world_pointer('elderwyld')
    turn = service.list_turns('elderwyld', pointer.active_conversation_id)[0]
    captures = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildAuthoredReferencesCapturedV1)]
    assert len(captures) == 1 and captures[0].references == case[1].build_authored_references
    from application_state.agent_conversation import retry
    from application_state.unit_of_work import unit_of_work
    from application_state.agent_conversation.service import _ready_dsn
    with unit_of_work(_ready_dsn()) as conn:
        context = retry.context(conn, turn, active=True)
    assert context['schema'] == 'dmb_turn_retry_context_row_v2'
    assert context['authored_references'] == captures[0].references.model_dump(mode='json', by_alias=True)


@pytest.mark.parametrize('mutation', ['altered', 'duplicate', 'prior_attempt'])
def test_trace_readback_refuses_authored_events_not_equal_to_the_immutable_ledger(build_case, monkeypatch, tmp_path, application_state_dsn, mutation):
    import psycopg
    from psycopg.types.json import Jsonb
    from application_state.errors import ApplicationStateValidationError
    case, _ = referenced_case(build_case, monkeypatch)
    decisions=WorldDecisions();decisions.operation='propose_build_insertion'
    response=execute(case,tmp_path,BuildJevHarness(world_context=True,named_citations=True,related_pages=True,
        accounting=counter(),decision_transport=decisions,writer_transport=WriterWire()),operator_subject='local_operator')
    service=AgentConversationService();turn=service.list_turns('elderwyld',response.conversation.conversation_id)[0]
    trace=service.list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)[0]
    payload=trace.model_dump(mode='json',by_alias=True)
    observation=next(item for item in payload['observations'] if item['kind']=='authored_graph_reference_v1' and item['execution_event']['kind']=='build_authored_reference_authorized_v1')
    if mutation=='altered':observation['execution_event']['arguments_sha256']='f'*64
    elif mutation=='prior_attempt':payload['execution_start_sequence']=observation['execution_event']['sequence']+1
    else:payload['observations'].append({**observation,'sequence':len(payload['observations']),'elapsed_ms':payload['observations'][-1]['elapsed_ms']})
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',(Jsonb(payload),turn.turn_id,trace.attempt))
    with pytest.raises(ApplicationStateValidationError,match='exact turn ledger|already has an observation|predates this physical attempt'):
        service.list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)


@pytest.mark.parametrize('fault',['none','capture_then_read','object_changed','passage_missing','passage_changed','passage_duplicate','passage_pin','trace_owner','trace_attempt','selection_id','selection_future','object_authorized','source_authorized'])
def test_reviewed_authored_read_process_loss_reclaims_without_duplicate_work(build_case, monkeypatch, tmp_path, application_state_dsn, fault):
    """SDK/APP restart boundary; only native IO and process loss are synthetic."""
    import psycopg
    from tests.test_reviewed_action_binding import reviewed_case
    from apps.live_control_server.services import build_authored_references as owner
    case, reads = referenced_case(build_case, monkeypatch)
    case = reviewed_case(case, monkeypatch, authored_references=case[1].build_authored_references, prepared=True)
    from apps.live_control_server.services import build_related_pages
    monkeypatch.setattr(build_related_pages,'discover',lambda _:[])
    decisions, writer = WorldDecisions(), WriterWire()
    harness = BuildJevHarness(world_context=True,named_citations=True,related_pages=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    original = owner.acquire
    class ProcessLost(BaseException):
        pass
    def lose_process(adapter):
        original(adapter)
        raise ProcessLost()
    if fault=='capture_then_read':
        original_capture=owner.capture_input
        def lose_after_capture(adapter):
            original_capture(adapter)
            raise ProcessLost()
        monkeypatch.setattr(owner,'capture_input',lose_after_capture)
        with pytest.raises(ProcessLost):execute(case,tmp_path,harness)
        first=AgentConversationService().list_turns('elderwyld',case[1].build_write_capability.conversation_id)[-1]
        assert first.attempt==1 and len(first.graph_context_execution.events)==1
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(first.turn_id,))
        monkeypatch.setattr(owner,'capture_input',original_capture)
        from apps.live_control_server.routes import agent
        first_historical_resolver=agent._historical_work_resolver
    else:first_historical_resolver=None
    if fault=='object_authorized':
        original_append=owner.append
        def lose_after_authorization(adapter,event,**proof):
            original_append(adapter,event,**proof)
            if isinstance(event,t.BuildAuthoredReferenceAuthorizedV1):raise ProcessLost()
        monkeypatch.setattr(owner,'append',lose_after_authorization)
    elif fault=='source_authorized':
        original_authorize=AgentConversationService.authorize_source_read
        def lose_after_source_authorization(self,*args,**kwargs):
            original_authorize(self,*args,**kwargs)
            raise ProcessLost()
        monkeypatch.setattr(AgentConversationService,'authorize_source_read',lose_after_source_authorization)
    else:
        monkeypatch.setattr(owner,'acquire',lose_process)
    with pytest.raises(ProcessLost):
        execute(case,tmp_path,harness,**({'historical_work_resolver':first_historical_resolver} if first_historical_resolver else {}))
    service = AgentConversationService()
    turn = service.list_turns('elderwyld',case[1].build_write_capability.conversation_id)[-1]
    assert turn.status == 'running'
    assert not decisions.calls and not writer.calls
    assert len([e for e in turn.graph_context_execution.events if isinstance(e,t.BuildAuthoredReferenceReadV1)]) == (0 if fault.endswith('authorized') else 1)
    before = turn.graph_context_execution.model_dump(mode='json',by_alias=True)
    if fault in {'selection_id','selection_future'}:
        from psycopg.types.json import Jsonb
        from application_state.agent_conversation.authored_graph_references import digest
        selected=next(e for e in before['events'] if e['kind']=='build_reviewed_action_selected_v2')
        selected['broker_operation_id']='build-reviewed:'+('0'*64 if fault=='selection_id' else digest({
            'turn_id':str(turn.turn_id),'attempt':turn.attempt+99,'binding':selected['intent']['reviewed_step']}))
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute('UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s',(Jsonb(before),turn.turn_id))
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",(turn.turn_id,))
    monkeypatch.setattr(owner,'acquire',original)
    if fault=='object_authorized':monkeypatch.setattr(owner,'append',original_append)
    if fault=='source_authorized':monkeypatch.setattr(AgentConversationService,'authorize_source_read',original_authorize)
    if fault=='object_changed':
        from apps.live_control_server.integrations.dungeonmind import world_graph_reads as native
        getter=native.get_object_with_reviewed_sources_direct_v3
        def changed(services,query):
            result=getter(services,query)
            return replace(result,result=result.result.model_copy(update={'nodes':[n.model_copy(update={'label':'changed object'}) for n in result.result.nodes]}))
        monkeypatch.setattr(native,'get_object_with_reviewed_sources_direct_v3',changed)
    if fault in {'passage_missing','passage_changed','passage_duplicate','passage_pin','trace_owner','trace_attempt'}:
        from psycopg.types.json import Jsonb
        from hashlib import sha256
        with psycopg.connect(application_state_dsn) as conn:
            payload=conn.execute('SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s',(turn.turn_id,turn.attempt)).fetchone()[0]
            passage=next(p for p in payload['observations'] if p['kind']=='source_passage')
            if fault=='passage_missing':
                payload['observations'].remove(passage)
                for i,p in enumerate(payload['observations']):p['sequence']=i
            elif fault=='passage_duplicate':
                payload['observations'].append({**passage,'sequence':len(payload['observations']),'elapsed_ms':payload['observations'][-1]['elapsed_ms']})
            elif fault=='passage_pin':passage['source_artifact_id']='another-artifact'
            elif fault=='trace_owner':
                from uuid import uuid4
                payload['conversation_id']=str(uuid4())
            elif fault=='trace_attempt':payload['attempt']=3
            else:
                passage['text']='Changed unsupported bytes'
                passage['returned_chars']=len(passage['text'])
                passage['content_sha256']=sha256(passage['text'].encode()).hexdigest()
            if fault=='trace_attempt':
                with pytest.raises(psycopg.errors.CheckViolation):
                    conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',(Jsonb(payload),turn.turn_id,turn.attempt))
                conn.rollback()
                assert conn.execute('SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s',(turn.turn_id,turn.attempt)).fetchone()[0]['attempt']==turn.attempt
                return
            conn.execute('UPDATE agent.turn_context_trace SET payload=%s WHERE turn_id=%s AND attempt=%s',(Jsonb(payload),turn.turn_id,turn.attempt))
    from apps.live_control_server.routes import agent
    recovered_harness=BuildJevHarness(world_context=True,named_citations=True,related_pages=True,accounting=counter(),decision_transport=decisions,writer_transport=writer)
    if fault not in {'none','capture_then_read'}:
        from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
        with pytest.raises(AgentTurnServiceError) as failed:
            execute(case,tmp_path,recovered_harness,historical_work_resolver=agent._historical_work_resolver)
        assert failed.value.code == ('build_authored_reference_recovery_indeterminate' if fault.endswith('authorized') else 'build_authored_reference_recovery_unavailable')
        assert not decisions.calls and not writer.calls
        retained=service.list_turns('elderwyld',turn.conversation_id)[-1]
        assert retained.graph_context_execution.model_dump(mode='json',by_alias=True)['events']==before['events']
        if fault=='source_authorized':
            from uuid import uuid4
            from application_state.agent_conversation import work_plan as w
            source=case[1].reviewed_step.source_turn_id
            saved=w.read('elderwyld',turn.conversation_id,source)['plan']
            assert saved['execution'][0]['status'] in {'failed','interrupted'}
            continued=w.continue_step('elderwyld',turn.conversation_id,source,w.Continue(
                expected_revision=saved['revision'],step_id=saved['steps'][0]['step_id'],command_id=uuid4()))
            dispatch=continued['dispatch']
            request=case[1].model_copy(update={'client_thread_id':dispatch['client_thread_id'],
                'turn_id':dispatch['client_turn_id'],'message':dispatch['message'],
                'reviewed_step':case[1].reviewed_step.model_validate(continued['reviewed_step'])})
            retried=(case[0],request,replace(case[2],completed_discovery_query=request.message))
            result=execute(retried,tmp_path,BuildJevHarness(world_context=True,named_citations=True,related_pages=True,
                accounting=counter(),decision_transport=decisions,writer_transport=writer))
            assert isinstance(result.knowledge_context.completion,t.BuildAuthoringCompletionV1)
            assert len(writer.calls)==1 and not decisions.calls
            final=w.read('elderwyld',turn.conversation_id,source)['plan']
            assert len(final['dispatches'])==2 and final['dispatches'][0]==saved['dispatches'][0]
            assert final['execution'][0]['status']==saved['execution'][0]['status']
            assert final['execution'][1]['status']=='prepared'
        return
    response = execute(case,tmp_path,recovered_harness,historical_work_resolver=agent._historical_work_resolver)
    assert isinstance(response.knowledge_context.completion,t.BuildAuthoringCompletionV1)
    recovered = service.list_turns('elderwyld',turn.conversation_id)[-1]
    assert recovered.attempt == turn.attempt+1
    assert recovered.graph_context_execution.model_dump(mode='json',by_alias=True)['events'][:len(before['events'])] == before['events']
    assert len(writer.calls) == 1 and not decisions.calls
    assert reads['source']==1
    assert len([e for e in recovered.graph_context_execution.events if isinstance(e,t.BuildReviewedActionSelectionV1)])==1
    from application_state.agent_conversation.context_trace import TraceAuthoredGraphReferenceV1
    traces=service.list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)
    assert [trace.attempt for trace in traces]==list(range(1,recovered.attempt+1))
    current=[o.execution_event for o in traces[-1].observations if isinstance(o,TraceAuthoredGraphReferenceV1)]
    assert len(current)==1 and isinstance(current[0],t.BuildAuthoredProviderInclusionV1)
    assert traces[-1].capture_status=='complete'
    assert not any(o.kind=='source_passage' for o in traces[-1].observations)
    historical=[ref for o in traces[-1].observations if o.kind=='context_snapshot' and o.snapshot_kind=='provider_input'
        for material in o.materials for ref in material.historical_source_reads]
    assert len(historical)==1 and historical[0].turn_id==turn.turn_id and historical[0].attempt==turn.attempt
    original_passage=service.read_historical_source_passage(historical[0])
    packet=json.loads(json.loads(writer.calls[0].content)['input'])
    assert packet['authored_reference_passages'][0]['text']==original_passage.text
    from application_state.agent_conversation.context_trace_store import _historical_sources_available
    echoed=next(o for o in traces[-1].observations if o.kind=='context_snapshot' and o.snapshot_kind=='validated_answer')
    execution=recovered.graph_context_execution.model_dump(mode='json',by_alias=True)
    with psycopg.connect(application_state_dsn) as conn:
        assert _historical_sources_available(conn,traces[-1],echoed,recovered.sequence,execution)
        without_input=traces[-1].model_copy(update={'observations':[o for o in traces[-1].observations
            if not (o.kind=='context_snapshot' and o.snapshot_kind=='provider_input')]})
        assert not _historical_sources_available(conn,without_input,echoed,recovered.sequence,execution)
        assert not _historical_sources_available(conn,traces[-1],echoed.model_copy(update={'snapshot_kind':'compaction_input'}),recovered.sequence,execution)




def test_reviewed_authored_insertion_needs_no_controller_call_for_exact_object(build_case,monkeypatch,tmp_path):
    from tests.test_reviewed_action_binding import reviewed_case
    from apps.live_control_server.services import build_related_pages
    case,reads=referenced_case(build_case,monkeypatch)
    case=reviewed_case(case,monkeypatch,authored_references=case[1].build_authored_references,prepared=True)
    monkeypatch.setattr(build_related_pages,'discover',lambda _:[])
    decisions,writer=WorldDecisions(),WriterWire()
    response=execute(case,tmp_path,BuildJevHarness(world_context=True,named_citations=True,related_pages=True,
        accounting=counter(),decision_transport=decisions,writer_transport=writer))
    assert isinstance(response.knowledge_context.completion,t.BuildAuthoringCompletionV1)
    assert not decisions.calls and len(writer.calls)==1
    turn=AgentConversationService().list_turns('elderwyld',response.conversation.conversation_id)[-1]
    providers=[e for e in turn.graph_context_execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV1)]
    assert len(providers)==1 and providers[0].provider_attempt_id==response.knowledge_context.completion.provider_attempt_id
    assert reads=={'graph':2,'source':1}
