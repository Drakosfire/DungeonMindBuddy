"""Real two-turn APP/Plan writer proof; corpus and model transport are synthetic."""
import asyncio
from dataclasses import replace
from types import MethodType, SimpleNamespace
from uuid import uuid4
import json

import pytest
from application_state.agent_conversation import types as t
from application_state.agent_conversation.source_passage_reuse import eligible_passages
from application_state.agent_conversation import AgentConversationService
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from application_state.agent_conversation.rules_authority_policy import rules_capability
from graph_memory.interaction.session import GraphRetrievalSession, GraphReferent, SessionSnapshot
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_surface_source_answers import stage, answer
from tests.test_plan_jev_writer import WriterWire
from tests.test_plan_jev_driver import Decisions, fixture_reads


def capture_graphs(adapter):
    """Complete the synthetic broker's ordinary validated trace observation."""
    for event in adapter._broker_execution().events:
        if not isinstance(event,t.ValidatedGraphOperationEventV3): continue
        packet=json.loads(adapter.operation_payloads[event.event_id])
        nodes=[{'node_id':n['nodeId'],'label':n['label'],'kind':n['kind']} for n in packet['nodes']]
        counts=dict(nodes=len(nodes),relationships=len(event.relationship_ids),claims=len(event.assertion_ids),evidence_refs=len(event.evidence_ref_ids))
        adapter.context_capture.observe(dict(kind='graph_tool',tool_name='expand_graph_retrieval',
            execution_event_id=event.event_id,request_arguments_sha256=event.request_arguments_sha256,
            result_packet_sha256=event.result_packet_sha256,scope_mode='world',campaign_id=None,
            revision_pin=event.graph_revision,request=dict(operation='object',target_node_id='pond'),
            result=dict(outcome='enough',graph_revision=event.graph_revision,coverage_status='complete',
                projection_status='complete',nodes=nodes,relationship_ids=event.relationship_ids,
                claim_ids=event.assertion_ids,evidence_ref_ids=event.evidence_ref_ids,
                returned_counts=counts,total_counts=counts,omission_codes=[])))


def complete_origin(adapter):
    writer = stage(adapter)
    capture_graphs(adapter)
    turn = asyncio.run(writer.run(transport=WriterWire(adapter, json.dumps(answer(writer))), api_key='synthetic'))
    trace = adapter.service.list_context_trace_attempts(world_id=turn.world_id, turn_id=turn.turn_id)[0]
    return turn, trace


def next_adapter(first):
    request = first.request.model_copy(update={'turn_id': str(uuid4())})
    session = GraphRetrievalSession(snapshot=SessionSnapshot(world_id='native-park', campaign_id='',
        focus={'kind':'none'}, admissibility='gm', revision_id='park:1', is_head=True, scope_mode='world'),
        question=request.message, referents=[GraphReferent(id='pond',label='Park pond')])
    return owner._PolicyExecutionAdapter(service=AgentConversationService(), request=request,
        world_id=first.world_id, work=first.work, bootstrap=replace(first.bootstrap,retrieval_session=session),
        playable_target=None, submitted_intent=owner._submitted_turn_intent(request,world_id=first.world_id),
        existing_turn=None, budget=first.budget, context_read_enabled=True,
        expected_conversation_id=first.turn.conversation_id)


def stage_reuse(first, monkeypatch, holder=None, *, anchors=2, internal=False):
    adapter = next_adapter(first)
    if holder is not None: holder.append(adapter)
    _, fresh_calls = fixture_reads(adapter, anchors=anchors, node_only=True)
    adapter._broker_fresh_source_read = adapter.broker_source_read
    adapter.broker_source_read = MethodType(owner._PolicyExecutionAdapter.broker_source_read, adapter)
    if internal:
        broker = adapter.broker_source_read
        adapter.broker_source_read = lambda message, **kwargs: broker(message, bundle_internal=True)
    def session(_):
        actual = adapter.bootstrap.retrieval_session
        pins = adapter._broker_execution().effective_source_pins()
        return SimpleNamespace(snapshot=actual.snapshot,
            source_anchors=[SimpleNamespace(anchor_id=a,readable=True) for a in pins],
            project_for_hermes=lambda: {})
    monkeypatch.setattr('graph_memory.interaction.session_store.get_session', session)
    rules = PlanRulesRuntime(adapter, rules_capability(graph=True))
    proof = asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(),api_key='synthetic'))
    capture_graphs(adapter)
    return adapter, PlanJevWriter(adapter,proof,rules), fresh_calls


def test_two_actual_turns_reuse_without_corpus_io_and_reopen(plan_adapter,monkeypatch,application_state_dsn):
    origin, origin_trace = complete_origin(plan_adapter)
    second, writer, reads = stage_reuse(plan_adapter,monkeypatch)
    try:
        assert not reads
        events = second.fence.turn.graph_context_execution.events
        reuse = [e for e in events if isinstance(e,t.SourcePassageReuseEventV1)]
        assert len(reuse)==2 and not any(isinstance(e,t.SourceReadAuthorizationEventV2) for e in events)
        assert all(e.origin_turn_id==origin.turn_id for e in reuse)
        assert t.source_read_character_usage(second._broker_execution().policy,events)==sum(r.returned_chars for e in reuse for r in e.receipts)
        assert len(writer.projection.frame['opened_passages'])==2
        # Every literal is present once in the actual writer frame.
        for passage in writer.projection.frame['opened_passages']:
            assert json.dumps(writer.projection.frame).count(passage['text'])==1
        completed=asyncio.run(writer.run(transport=WriterWire(second,json.dumps(answer(writer))),api_key='synthetic'))
        reopened=AgentConversationService().inspect_turn(world_id=completed.world_id,turn_id=completed.turn_id)
        assert reopened.completion==completed.completion
        labels=AgentConversationService().source_name_labels(reopened.world_id,reopened.conversation_id,[reopened.turn_id])
        assert len(labels)==2 and all(label['source_name']=='Synthetic park journal' for label in labels)
        auth=next(e for e in reopened.graph_context_execution.events if isinstance(e,t.PlanJevWriterAuthorizedV2))
        assert not auth.included_source_read_event_ids and set(auth.included_source_reuse_event_ids)=={e.event_id for e in reuse}
        assert {c.read_event_id for c in reopened.completion.source_citations}=={e.event_id for e in reuse}
        trace=AgentConversationService().list_context_trace_attempts(world_id=reopened.world_id,turn_id=reopened.turn_id)[0]
        assert trace.capture_status=='complete' and len([o for o in trace.observations if o.kind=='source_passage_reuse'])==2
        assert all(o.origin_turn_id==origin.turn_id for o in trace.observations if o.kind=='source_passage_reuse')
        # The citation reopens via native immutable authority, never trace fallback.
        from apps.live_control_server.services.agent_source_passages import open_source_passage,SourcePassageOpenError
        from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
        from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult
        citation=reopened.completion.source_citations[0]
        saved=next(o for o in trace.observations if o.kind=='source_passage_reuse' and o.source_read_id==citation.receipt.source_read_id)
        result=WorldGraphSourceAnchorReadResult.model_validate(dict(outcome='enough',
            snapshot=dict(worldId='native-park',campaignId='',scopeMode='world',focus=dict(kind='none',sessionId=None),
                admissibility='gm',revisionId='park:1',headRevisionId='park:1',isHead=True),
            anchorId=saved.anchor_id,evidenceRefId=saved.evidence_ref_id,sourceArtifactId=saved.source_artifact_id,
            content=saved.text,contentSha256='a'*64,lineStart=saved.line_start,lineEnd=saved.line_end,truncated=False))
        opened=direct.ResolvedSourceAnchorReadV2(result=result,source_revision_id=saved.source_revision_id,
            source_revision_sha256='a'*64,evidence_ref_id=saved.evidence_ref_id,source_artifact_id=saved.source_artifact_id,
            source_span_ref_id='synthetic-span',locator_kind='source_span',locator_identity='synthetic-span',graph_revision='park:1')
        monkeypatch.setattr(direct,'direct_services_from_config',lambda _:object())
        calls=[]
        def native(_services,request,**_kwargs):
            calls.append(request)
            return opened
        monkeypatch.setattr(direct,'read_source_anchor_direct_v2',native)
        response=open_source_passage(world_id=reopened.world_id,turn_id=reopened.turn_id,citation_index=0)
        assert response.content==saved.text and len(calls)==1
        opened=replace(opened,source_revision_id='changed')
        with pytest.raises(SourcePassageOpenError,match='source_passage_binding_invalid'):
            open_source_passage(world_id=reopened.world_id,turn_id=reopened.turn_id,citation_index=0)
        # A database downgrade may not discard the newly retained event contract.
        from importlib import import_module
        from sqlalchemy import create_engine
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
        try:
            with engine.begin() as conn:
                with Operations.context(MigrationContext.configure(conn)):
                    with pytest.raises(RuntimeError,match='retained source reuse'):
                        import_module('application_state.migrations.versions.20261022_0047_source_passage_reuse').downgrade()
        finally: engine.dispose()
    finally: second.fence.stop()


@pytest.mark.parametrize('mutation',['conversation','world','graph','binding','source_revision','hash','status','trace_missing','trace_incomplete','producer_omitted'])
def test_retained_eligibility_rejects_changed_owners_and_missing_proof(plan_adapter,monkeypatch,mutation):
    origin, trace = complete_origin(plan_adapter)
    second, writer, _ = stage_reuse(plan_adapter,monkeypatch)
    try:
        current=second.fence.turn
        payload=trace.model_dump(mode='python',by_alias=True)
        if mutation=='conversation': current=current.model_copy(update={'conversation_id':uuid4()})
        if mutation=='world': current=current.model_copy(update={'world_id':'foreign'})
        if mutation in {'graph','binding'}:
            authority=current.graph_context_receipt.graph_authority.model_copy(update={
                'graph_revision':'different' if mutation=='graph' else current.graph_context_receipt.graph_authority.graph_revision,
                'binding_version':2 if mutation=='binding' else current.graph_context_receipt.graph_authority.binding_version})
            current=current.model_copy(update={'graph_context_receipt':current.graph_context_receipt.model_copy(update={'graph_authority':authority})})
        if mutation=='source_revision':
            execution=current.graph_context_execution.model_copy(deep=True)
            for event in execution.events:
                if isinstance(event,t.SourceScopeExtensionEventV3):
                    for pin in event.pins: pin.source_revision_id='different'
            current=current.model_copy(update={'graph_context_execution':execution})
        if mutation=='hash':
            for observation in payload['observations']:
                if observation['kind']=='source_passage': observation['text']+='changed'
        if mutation=='status': origin=origin.model_copy(update={'status':'interrupted'})
        if mutation=='trace_missing': payload=None
        if mutation=='trace_incomplete': payload['capture_status']='incomplete'
        if mutation=='producer_omitted':
            execution=origin.graph_context_execution.model_copy(deep=True)
            for event in execution.events:
                if isinstance(event,t.PlanJevWriterAuthorizedV1): event.included_source_read_event_ids=[]
            origin=origin.model_copy(update={'graph_context_execution':execution})
        assert not eligible_passages(current,origin,payload,set(current.graph_context_execution.effective_source_pins()),12000)
    finally: second.fence.stop()


def test_admission_replay_is_fenced_and_does_not_double_charge(plan_adapter,monkeypatch):
    complete_origin(plan_adapter)
    second, _writer, _reads = stage_reuse(plan_adapter,monkeypatch)
    try:
        current=second.fence.turn
        event=next(e for e in current.graph_context_execution.events if isinstance(e,t.SourcePassageReuseEventV1))
        request=dict(anchor_ids=['anchor:park:0','anchor:park:1'],max_chars=12000,
            elapsed_ms=second.context_capture.elapsed_ms,request_id=str(event.reuse_request_id))
        replay,fresh=second.service.admit_retained_source_passages(current.world_id,current.conversation_id,current.turn_id,
            expected_revision=event.request_turn_revision,expected_attempt=current.attempt,request=request)
        assert not fresh and replay.revision==current.revision and replay.graph_context_execution==current.graph_context_execution
        with pytest.raises(ApplicationStateConflictError,match='identity changed'):
            second.service.admit_retained_source_passages(current.world_id,current.conversation_id,current.turn_id,
                expected_revision=event.request_turn_revision,expected_attempt=current.attempt,
                request={**request,'max_chars':1000})
        with pytest.raises(ApplicationStateConflictError,match='revision'):
            second.service.admit_retained_source_passages(current.world_id,current.conversation_id,current.turn_id,
                expected_revision=event.request_turn_revision,expected_attempt=current.attempt,
                request={**request,'request_id':str(uuid4())})
    finally: second.fence.stop()


def test_play_reused_passage_requires_separate_actual_producer_inclusion():
    from tests.test_surface_source_play_binding import case
    from tests.test_play_graph_authority import native_events
    from application_state.agent_conversation.surface_source_answer import producing_passages
    from application_state.agent_conversation.native_answer_output import normalize_native_answer
    turn, provider, raw, support, candidate=case()
    original=next(e for e in turn.graph_context_execution.events if isinstance(e,t.ValidatedSourceReadEventV2))
    reuse=t.SourcePassageReuseEventV1(kind='source_passage_reused_v1',event_id=original.event_id,
        sequence=original.sequence,reuse_request_id=uuid4(),request_sha256='a'*64,request_turn_revision=1,
        origin_turn_id=uuid4(),origin_attempt=1,origin_read_event_id=uuid4(),origin_provider_attempt_id=uuid4(),
        read_call_id=original.read_call_id,receipts=original.receipts)
    current=t.ProviderAttemptAuthorizedEventV4.model_validate({**provider.model_dump(mode='python'),
        'kind':'provider_attempt_authorized_v4','included_source_read_event_ids':[],
        'included_source_reuse_event_ids':[reuse.event_id]})
    events=[reuse if e.event_id==original.event_id else current if e.event_id==provider.event_id else e
        for e in turn.graph_context_execution.events if not isinstance(e,t.SourceReadAuthorizationEventV2)]
    events=[e.model_copy(update={'sequence':i}) for i,e in enumerate(events)]
    execution=native_events(turn.graph_context_execution,events)
    turn=turn.model_copy(update={'graph_context_execution':execution})
    current=next(e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV4))
    passages,partial=producing_passages(turn,current,raw)
    support=SimpleNamespace(**{**vars(support),'passages':passages,'source_partial':partial})
    completed,_,_=normalize_native_answer(candidate,turn,current.provider_attempt_id,support=support)
    assert completed.source_citations[0].read_event_id==reuse.event_id
    omitted=current.model_copy(update={'included_source_reuse_event_ids':[]})
    with pytest.raises(ValueError,match='included successful read'):
        producing_passages(turn,omitted,raw)
    with pytest.raises(ValueError,match='fresh source read'):
        native_events(execution,[e.model_copy(update={'included_source_read_event_ids':[reuse.event_id],
            'included_source_reuse_event_ids':[]}) if e.event_id==current.event_id else e for e in execution.events])


def test_partial_trace_failure_rolls_back_entire_reuse_batch(plan_adapter,monkeypatch):
    complete_origin(plan_adapter)
    from application_state.agent_conversation import service as app_owner
    from application_state.errors import ApplicationStateValidationError
    original=app_owner.append_source_passages_locked
    writes=[]
    def fail_second(conn,**kwargs):
        if kwargs['passages'][0].kind=='source_passage_reuse':
            writes.append(kwargs['event_id'])
            if len(writes)==2: raise ApplicationStateValidationError('synthetic atomic capture failure')
        return original(conn,**kwargs)
    monkeypatch.setattr(app_owner,'append_source_passages_locked',fail_second)
    holder=[]
    try:
        with pytest.raises(owner.AgentTurnServiceError,match='durably validated'):
            stage_reuse(plan_adapter,monkeypatch,holder)
        current=holder[0].service.inspect_turn(world_id=holder[0].world_id,turn_id=holder[0].fence.turn.turn_id)
        assert len(writes)==2
        assert not any(isinstance(e,t.SourcePassageReuseEventV1) for e in current.graph_context_execution.events)
        trace=holder[0].service.list_context_trace_attempts(world_id=current.world_id,turn_id=current.turn_id)[0]
        assert not any(o.kind=='source_passage_reuse' for o in trace.observations)
    finally:
        if holder: holder[0].fence.stop()


def test_reset_revokes_even_an_identical_admission_replay(plan_adapter,monkeypatch):
    complete_origin(plan_adapter)
    second,_writer,_reads=stage_reuse(plan_adapter,monkeypatch)
    try:
        current=second.fence.turn
        event=next(e for e in current.graph_context_execution.events if isinstance(e,t.SourcePassageReuseEventV1))
        pointer=second.service.get_world_pointer(current.world_id)
        second.service.new_conversation(t.ConversationCommand(world_id=current.world_id,command_id=uuid4(),
            expected_pointer_revision=pointer.revision,expected_active_conversation_id=current.conversation_id))
        with pytest.raises(ApplicationStateConflictError,match='active claim'):
            second.service.admit_retained_source_passages(current.world_id,current.conversation_id,current.turn_id,
                expected_revision=event.request_turn_revision,expected_attempt=current.attempt,
                request=dict(anchor_ids=['anchor:park:0','anchor:park:1'],max_chars=12000,
                    elapsed_ms=second.context_capture.elapsed_ms,request_id=str(event.reuse_request_id)))
    finally: second.fence.stop()


def test_reuse_cannot_overbook_an_unresolved_read_reservation():
    from tests.test_settled_source_read_accounting import fixture_execution,authorization,receipt
    execution=fixture_execution()
    auth=authorization(execution,count=8)
    original=receipt(auth)
    reused=t.SourcePassageReuseEventV1(kind='source_passage_reused_v1',event_id=uuid4(),sequence=1,
        reuse_request_id=uuid4(),request_sha256='a'*64,request_turn_revision=1,origin_turn_id=uuid4(),
        origin_attempt=1,origin_read_event_id=uuid4(),origin_provider_attempt_id=uuid4(),
        read_call_id=uuid4(),receipts=[original.receipts[0]])
    # A later settlement cannot retroactively legalize overbooking at admission.
    done=original.model_copy(update={'sequence':2})
    with pytest.raises(ValueError,match='reservation budget'):
        t.source_read_character_usage(execution.policy,[auth,reused,done])


def test_mixed_batch_reads_only_the_new_anchor(plan_adapter,monkeypatch):
    complete_origin(plan_adapter)
    second,writer,reads=stage_reuse(plan_adapter,monkeypatch,anchors=3)
    try:
        assert [r['anchorIds'] for r in reads]==[['anchor:park:2']]
        assert len(writer.projection.frame['opened_passages'])==3
        completed=asyncio.run(writer.run(transport=WriterWire(second,json.dumps(answer(writer))),api_key='synthetic'))
        auth=next(e for e in completed.graph_context_execution.events if isinstance(e,t.PlanJevWriterAuthorizedV2))
        assert len(auth.included_source_read_event_ids)==1 and len(auth.included_source_reuse_event_ids)==2
    finally: second.fence.stop()


@pytest.mark.parametrize('compact_refs', [False, True])
def test_internal_reuse_has_no_unseen_donors_in_actual_bundle(plan_adapter, monkeypatch, compact_refs):
    complete_origin(plan_adapter)
    second, _writer, reads = stage_reuse(plan_adapter, monkeypatch, internal=True)
    try:
        assert not reads and second.failure is None
        graph_id, graph_raw = next(iter(second.operation_payloads.items()))
        bundle = second._tool_presentation().present_bundle(graph_raw, graph_id,
            list(second.source_payloads.items()), compact_refs=compact_refs,
            source_pins=second._broker_execution().effective_source_pins())
        exposures = second._tool_presentation().bundled_source_inclusion([bundle])
        assert {e.event_id for e in exposures} == set(second.source_payloads)
        assert all(e.complete for e in exposures)
        packet = json.loads(bundle)
        assert all(row.get('content') and not row.get('contentRef') for row in packet['sources'])
    finally:
        second.fence.stop()


@pytest.mark.parametrize('phase', ['empty', 'authorized', 'sdk_entered'])
def test_native_play_admission_requires_current_acknowledged_provider(application_state_dsn, phase):
    from tests.application_state.test_native_play_input_postgres import prepared_native, append
    from application_state.errors import ApplicationStateValidationError
    service, sub, turn, provider, raw = prepared_native(application_state_dsn)
    if phase != 'empty':
        turn, _ = append(service, sub, turn, provider, raw)
    if phase == 'sdk_entered':
        turn, _ = service.record_provider_outcome(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=provider.provider_attempt_id, outcome='sdk_entered'))
    with pytest.raises(ApplicationStateValidationError, match='acknowledged current provider'):
        service.admit_retained_source_passages(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            request=dict(anchor_ids=['anchor:new'], max_chars=4000, elapsed_ms=0, request_id=str(uuid4())))
    reopened = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert reopened.revision == turn.revision
    assert reopened.graph_context_execution == turn.graph_context_execution


def test_rules_final_writer_blocks_new_admission_but_allows_exact_replay(plan_adapter, monkeypatch):
    from application_state.errors import ApplicationStateValidationError
    from application_state.agent_conversation.rules_authority_events import RulesPlanPacketProviderAuthorizedV1
    complete_origin(plan_adapter)
    second, _writer, _reads = stage_reuse(plan_adapter, monkeypatch)
    try:
        current = second.fence.turn
        event = next(e for e in current.graph_context_execution.events if isinstance(e, t.SourcePassageReuseEventV1))
        request = dict(anchor_ids=['anchor:park:0', 'anchor:park:1'], max_chars=12000,
            elapsed_ms=second.context_capture.elapsed_ms, request_id=str(event.reuse_request_id))
        # Supply the typed final-writer state at its separate Rules-store boundary.
        monkeypatch.setattr('application_state.agent_conversation.rules_authority_store.load_turn_rules_locked',
            lambda conn, turn: SimpleNamespace(execution=SimpleNamespace(events=[
                RulesPlanPacketProviderAuthorizedV1.model_construct()])))
        replay, changed = second.service.admit_retained_source_passages(current.world_id,
            current.conversation_id, current.turn_id, expected_revision=event.request_turn_revision,
            expected_attempt=current.attempt, request=request)
        assert not changed and replay.revision == current.revision
        with pytest.raises(ApplicationStateValidationError, match='final writer forbids'):
            second.service.admit_retained_source_passages(current.world_id, current.conversation_id,
                current.turn_id, expected_revision=current.revision, expected_attempt=current.attempt,
                request={**request, 'request_id':str(uuid4())})
        assert second.service.inspect_turn(world_id=current.world_id, turn_id=current.turn_id).revision == current.revision
    finally:
        second.fence.stop()


@pytest.mark.parametrize('internal', [False, True])
def test_repeated_reuse_with_smaller_bound_delegates_to_bounded_reader(plan_adapter, monkeypatch, internal):
    complete_origin(plan_adapter)
    second, _writer, _reads = stage_reuse(plan_adapter, monkeypatch)
    try:
        before = second.fence.turn.graph_context_execution
        receipts = [r for e in before.events if isinstance(e, t.SourcePassageReuseEventV1) for r in e.receipts]
        original = next(r for r in receipts if r.anchor_id == 'anchor:park:0')
        assert original.returned_chars > 1
        calls = []
        def bounded_reader(message, *, bundle_internal):
            calls.append((message['arguments'], bundle_internal))
            # A native bounded miss carries no complete passage. Existing native
            # reader tests own the IO/receipt contract; this exercises dispatch.
            return {'resultJson':json.dumps({'statusCode':422, 'code':'source_not_sufficient'})}
        second._broker_fresh_source_read = bounded_reader
        scope = before.policy.source_read_scope
        reply = second.broker_source_read({'toolName':'read_graph_source', 'arguments':{
            'retrievalSessionId':scope.retrieval_session_id, 'anchorIds':[original.anchor_id], 'maxChars':1}},
            bundle_internal=internal)
        assert len(calls) == 1 and calls[0][0]['maxChars'] == 1 and calls[0][1] is internal
        assert json.loads(reply['resultJson']) == {'statusCode':422, 'code':'source_not_sufficient'}
        assert second.fence.turn.graph_context_execution == before
    finally:
        second.fence.stop()
