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
from tests.test_surface_source_answers import stage, answer as source_answer
from tests.test_plan_jev_writer import WriterWire
from tests.test_plan_jev_driver import Decisions, fixture_reads
from tests import test_native_play_source_acquisition as play_acquisition
from tests.test_native_play_source_acquisition import (
    _admit_native_search_anchor, _source_request, _selector_after_admission,
)


acquired = play_acquisition.acquired


def answer(writer):
    return source_answer(writer) | {'schema': writer.projection.frame['answer_policy']}


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


def prepare_source_claim(adapter):
    if adapter.native_source_authority is not None:
        from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
        from tests.test_plan_jev_harness import Finish
        asyncio.run(PlanJevDispatch.requested_work(adapter, page_title='Synthetic park Plan').run(
            transport=Finish(), api_key='synthetic'))


def complete_origin(adapter):
    prepare_source_claim(adapter)
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
        native_source_authority=first.native_source_authority, native_corpus_context=first.native_corpus_context,
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
    prepare_source_claim(adapter)
    rules = PlanRulesRuntime(adapter, rules_capability(graph=True))
    proof = asyncio.run(PlanJevDriver(adapter).run(transport=Decisions(),api_key='synthetic'))
    capture_graphs(adapter)
    return adapter, PlanJevWriter(adapter,proof,rules), fresh_calls


@pytest.mark.parametrize('source_root', [False, True])
def test_two_actual_turns_reuse_without_corpus_io_and_reopen(plan_adapter,monkeypatch,application_state_dsn,source_root):
    if source_root:
        plan_adapter.native_source_authority = t.NativeCorpusUnavailableV1(
            managed_world_id=plan_adapter.world_id, failure_code='native_source_head_unavailable')
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



def _play_acknowledge(f, provider):
    for outcome in ("sdk_entered", "response_received"):
        turn = f.adapter.fence.turn
        updated, _ = f.service.record_provider_outcome(
            turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=provider.provider_attempt_id, outcome=outcome),
        )
        f.adapter.fence.renewer.update_turn(updated)


def _complete_captured_play(f, response):
    """Actual Play input/output/APP owners; only model response and corpus are fake."""
    from hashlib import sha256
    from tests.test_play_graph_authority import native_provider
    from tests.application_state.test_native_play_input_postgres import append
    from tests.application_state.test_plan_jev_decision_admission import rules_scope
    from application_state.agent_conversation.native_rules_output import (
        NativeRulesOutputProofV1, normalize_unused_native_output,
    )
    from application_state.agent_conversation.rules_authority_events import (
        RulesProviderAuthorizedV1, RulesProviderIncludedV1, RulesNativeProviderOutcomeV1,
    )
    body = json.loads(f.raw)
    body["messages"].extend([
        {"role": "assistant", "tool_calls": [{"id": "captured-read", "type": "function",
            "function": {"name": "read_graph_source", "arguments": json.dumps(_source_request(f)["arguments"])}}]},
        {"role": "tool", "tool_call_id": "captured-read", "content": response["resultJson"]},
    ])
    raw = json.dumps(body)
    turn = f.adapter.fence.turn
    source = turn.graph_context_execution.events[-1]
    assert isinstance(source, (t.ValidatedSourceReadEventV2, t.SourcePassageReuseEventV1))
    reused = isinstance(source, t.SourcePassageReuseEventV1)
    provider = native_provider(len(turn.graph_context_execution.events) + 1).model_copy(update={
        "envelope_sha256": sha256(raw.encode()).hexdigest(), "api_mode": "chat_completions",
        "included_source_read_event_ids": [] if reused else [source.event_id],
        "included_evidence_ref_ids": [],
    })
    if reused:
        provider = t.ProviderAttemptAuthorizedEventV4.model_validate({
            **provider.model_dump(mode="python"), "kind": "provider_attempt_authorized_v4",
            "included_source_reuse_event_ids": [source.event_id],
        })
    turn, _ = append(f.service, f.sub, turn, provider, raw)
    f.adapter.fence.renewer.update_turn(turn)
    scope = rules_scope(SimpleNamespace(turn=turn))
    ledger = f.service.begin_rules_execution(scope, expected_turn_revision=turn.revision)
    for cls, kind in ((RulesProviderAuthorizedV1, "provider_authorized"),
                      (RulesProviderIncludedV1, "provider_included")):
        fields = dict(kind=kind, event_id=uuid4(), sequence=len(ledger.execution.events),
            execution_id=scope.execution_id, provider_attempt_id=provider.provider_attempt_id,
            request_envelope_sha256=provider.envelope_sha256, matched_outputs=())
        fields["declared_support_refs" if cls is RulesProviderAuthorizedV1 else "support_refs"] = ()
        ledger = f.service.append_rules_provider_event(scope,
            expected_turn_revision=turn.revision, expected_ledger_revision=ledger.revision,
            event=cls(**fields), prepared_request_json=raw)
    _play_acknowledge(f, provider)
    turn = f.adapter.fence.turn
    output = json.dumps({"schema": "dmb_surface_evidence_answer_v2", "limitations": [],
        "requested_detail_gaps": [], "answer_segments": [{"kind": "source_passage_claim",
            "text": "Bridge journal describes three lanterns.",
            "passage_handles": [json.loads(response["resultJson"])["passageHandle"]]}]})
    capture = SimpleNamespace(authorization_id="synthetic-native", api_request_id=str(uuid4()),
        provider=provider.provider, model=provider.model, api_mode=provider.api_mode,
        request_sha256=provider.envelope_sha256, status="answered", finish_reason="stop",
        text=output, text_sha256=sha256(output.encode()).hexdigest(),
        text_utf8_bytes=len(output.encode()), tool_calls=())
    ledger = f.service.append_rules_provider_event(scope,
        expected_turn_revision=turn.revision, expected_ledger_revision=ledger.revision,
        event=RulesNativeProviderOutcomeV1.from_capture(capture, event_id=uuid4(),
            sequence=len(ledger.execution.events), execution_id=scope.execution_id,
            provider_attempt_id=provider.provider_attempt_id,
            request_envelope_sha256=provider.envelope_sha256))
    proof = NativeRulesOutputProofV1.from_capture(capture, prepared_request_json=raw,
        rules_execution_id=scope.execution_id, producing_provider_attempt_id=provider.provider_attempt_id)
    completion, bindings, text = normalize_unused_native_output(turn, ledger.execution, proof)
    completed = f.service.complete_native_base_turn(t.TurnResult(world_id=turn.world_id,
        conversation_id=turn.conversation_id, turn_id=turn.turn_id,
        expected_revision=turn.revision, assistant_text=text, completion=completion,
        producing_provider_attempt_id=provider.provider_attempt_id, claim_graph_event_ids=bindings),
        output_proof=proof, expected_rules_revision=ledger.revision)
    return completed, provider


def _captured_play_origin(acquired, monkeypatch):
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    f = _admit_native_search_anchor(acquired, monkeypatch)
    _selector_after_admission(monkeypatch, "unset")
    f.adapter.context_capture = ContextTraceCollector(f.adapter.fence)
    response = f.adapter.broker_source_read(_source_request(f))
    assert json.loads(response["resultJson"]).get("content") == f.text, response
    origin, provider = _complete_captured_play(f, response)
    f.adapter.fence.renewer.stop_and_join()
    trace, = f.service.list_context_trace_attempts(world_id=origin.world_id, turn_id=origin.turn_id)
    assert trace.capture_status == "complete"
    assert trace.terminal_status == "completed"
    return f, origin, provider, trace


def _next_captured_play(f, monkeypatch):
    from tests.test_play_graph_authority import native_provider
    from tests.application_state.test_native_play_input_postgres import append
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from graph_memory.interaction.session_store import create_session
    identity = uuid4()
    sub = f.sub.model_copy(update={"idempotency_key": identity,
        "expected_conversation_revision": f.service.get_conversation(f.sub.world_id, f.sub.conversation_id).revision})
    body = json.loads(f.raw)
    carrier = json.loads(body["messages"][0]["content"])
    carrier["submission_id"] = str(identity)
    body["messages"][0]["content"] = json.dumps(carrier)
    raw = json.dumps(body)
    from hashlib import sha256
    # This is a newly sealed request for the same immutable Play source frame.
    from tests.test_play_graph_context import seal_receipt
    from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
    wire = sub.graph_context_receipt.model_dump(mode="json", by_alias=True)
    wire["assembled_input"]["assembled_input_sha256"] = sha256(raw.encode()).hexdigest()
    receipt = seal_receipt(wire)
    execution = sub.graph_context_execution.model_copy(update={
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "execution_policy_sha256": play_graph_execution_policy_digest(receipt.context_receipt_sha256, sub.graph_context_execution.policy)})
    sub = sub.model_copy(update={"graph_context_receipt": receipt, "graph_context_execution": execution})
    turn = f.service.accept_turn(sub)
    turn = f.service.claim_turn(sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision).turn
    initial = native_provider(1).model_copy(update={"envelope_sha256": sha256(raw.encode()).hexdigest(), "api_mode": "chat_completions"})
    turn, _ = append(f.service, sub, turn, initial, raw)
    session = f.session.model_copy(deep=True, update={"source_anchors": [], "source_reads": [], "operations": []})
    create_session(session)
    adapter = owner._PolicyExecutionAdapter(service=f.service, request=f.adapter.request,
        world_id=turn.world_id, work=None, bootstrap=replace(f.adapter.bootstrap, retrieval_session=session),
        playable_target=None, submitted_intent=None, existing_turn=turn, budget={})
    adapter.fence = owner._ClaimFence(f.service, turn)
    adapter.last_provider_attempt_id = initial.provider_attempt_id
    current = SimpleNamespace(**{**vars(f), "adapter": adapter, "sub": sub, "raw": raw, "session": session})
    _play_acknowledge(current, initial)
    _admit_native_search_anchor(current, monkeypatch)
    _selector_after_admission(monkeypatch, "stale")
    adapter.context_capture = ContextTraceCollector(adapter.fence)
    return current


@pytest.mark.parametrize("acquired", ["native_search"], indirect=True)
def test_actual_play_capture_reuse_producer_completion_and_reload(acquired, monkeypatch):
    f, origin, origin_provider, trace = _captured_play_origin(acquired, monkeypatch)
    current = _next_captured_play(f, monkeypatch)
    try:
        f.calls.clear()
        def no_io(*args, **kwargs):
            pytest.fail("retained Play passage reopened corpus IO")
        monkeypatch.setattr("graph_memory.interaction.expansion_executor.execute_read_graph_source", no_io)
        response = current.adapter.broker_source_read(_source_request(current))
        assert json.loads(response["resultJson"]).get("content") == f.text, response
        execution = current.adapter.fence.turn.graph_context_execution
        reuse, = [e for e in execution.events if isinstance(e, t.SourcePassageReuseEventV1)]
        assert reuse.origin_turn_id == origin.turn_id
        assert reuse.origin_provider_attempt_id == origin_provider.provider_attempt_id
        assert not any(isinstance(e, t.SourceReadAuthorizationEventV2) for e in execution.events)
        before = execution.model_dump(mode="json")
        again = current.adapter.broker_source_read(_source_request(current))
        assert json.loads(again["resultJson"])["content"] == f.text
        assert current.adapter.fence.turn.graph_context_execution.model_dump(mode="json") == before
        completed, provider = _complete_captured_play(current, response)
        assert provider.included_source_read_event_ids == []
        assert provider.included_source_reuse_event_ids == [reuse.event_id]
        reopened = AgentConversationService().inspect_turn(world_id=completed.world_id, turn_id=completed.turn_id)
        assert reopened == completed
        citation, = reopened.completion.source_citations
        assert citation.read_event_id == reuse.event_id
        assert citation.receipt == reuse.receipts[0]
        assert f.calls == []
        saved, = f.service.list_context_trace_attempts(world_id=completed.world_id, turn_id=completed.turn_id)
        passage, = [p for p in saved.observations if p.kind == "source_passage_reuse"]
        assert passage.text == f.text and passage.origin_turn_id == origin.turn_id
        assert saved.capture_status == "complete"
    finally:
        current.adapter.fence.renewer.stop_and_join()


@pytest.mark.parametrize("acquired", ["native_search"], indirect=True)
def test_play_retained_eligibility_rejects_foreign_or_unproven_passages(acquired, monkeypatch):
    f, origin, _producer, trace = _captured_play_origin(acquired, monkeypatch)
    current = _next_captured_play(f, monkeypatch)
    try:
        turn = current.adapter.fence.turn
        requested = {f.pin.anchor_id}
        payload = trace.model_dump(mode="python", by_alias=True)
        valid, = eligible_passages(turn, origin, payload, requested, 1000)
        assert valid.passage.text == f.text
        for damage in ("world", "conversation", "native_world", "binding", "graph", "scope",
                       "source_revision", "unadmitted", "hash", "trace_missing", "trace_incomplete",
                       "producer_omitted", "incomplete_origin", "small_bound"):
            now, previous, captured, limit = turn.model_copy(deep=True), origin.model_copy(deep=True), trace.model_dump(mode="python", by_alias=True), 1000
            if damage == "world":
                now = now.model_copy(update={"world_id": "foreign"})
            elif damage == "conversation":
                now = now.model_copy(update={"conversation_id": uuid4()})
            elif damage in {"native_world", "binding", "graph", "scope"}:
                field, value = {"native_world": ("native_world_id", "native:foreign"),
                    "binding": ("binding_version", 999), "graph": ("graph_revision", "revision:other"),
                    "scope": ("admissibility_version", "player-v1")}[damage]
                authority = now.graph_context_receipt.graph_authority.model_copy(update={field: value})
                now = now.model_copy(update={"graph_context_receipt": now.graph_context_receipt.model_copy(update={"graph_authority": authority})})
            elif damage in {"source_revision", "unadmitted"}:
                events = []
                for event in now.graph_context_execution.events:
                    if isinstance(event, t.SourceScopeExtensionEventV3):
                        pins = [] if damage == "unadmitted" else [p.model_copy(update={"source_revision_id": "revision:foreign"}) for p in event.pins]
                        event = event.model_copy(update={"pins": pins})
                    events.append(event)
                now = now.model_copy(update={"graph_context_execution": now.graph_context_execution.model_copy(update={"events": events})})
            elif damage == "hash":
                for observation in captured["observations"]:
                    if observation["kind"] == "source_passage":
                        observation["text"] += "forged"
            elif damage == "trace_missing":
                captured = None
            elif damage == "trace_incomplete":
                captured["capture_status"] = "incomplete"
            elif damage == "producer_omitted":
                events = [event.model_copy(update={"included_source_read_event_ids": []})
                    if isinstance(event, t.ProviderAttemptAuthorizedEventV3) else event
                    for event in previous.graph_context_execution.events]
                previous = previous.model_copy(update={"graph_context_execution": previous.graph_context_execution.model_copy(update={"events": events})})
            elif damage == "incomplete_origin":
                previous = previous.model_copy(update={"status": "running"})
            else:
                limit = 1
            assert not eligible_passages(now, previous, captured, requested, limit), damage
        assert current.adapter.fence.turn == turn
    finally:
        current.adapter.fence.renewer.stop_and_join()


@pytest.mark.parametrize("acquired", ["native_search"], indirect=True)
def test_play_reuse_trace_failure_rolls_back_public_broker_admission(acquired, monkeypatch):
    from application_state.agent_conversation import service as app_owner
    from application_state.errors import ApplicationStateValidationError
    f, _origin, _producer, _trace = _captured_play_origin(acquired, monkeypatch)
    current = _next_captured_play(f, monkeypatch)
    try:
        before = current.adapter.fence.turn
        attempts = []
        original = app_owner.append_source_passages_locked
        def fail_reuse(conn, **kwargs):
            if kwargs["passages"][0].kind == "source_passage_reuse":
                attempts.append(kwargs["event_id"])
                raise ApplicationStateValidationError("synthetic Play capture failure")
            return original(conn, **kwargs)
        monkeypatch.setattr(app_owner, "append_source_passages_locked", fail_reuse)
        f.calls.clear()
        reply = current.adapter.broker_source_read(_source_request(current))
        assert json.loads(reply["resultJson"])["code"] == "source_reuse_indeterminate"
        assert len(attempts) == 1 and f.calls == []
        restored = AgentConversationService().inspect_turn(world_id=before.world_id, turn_id=before.turn_id)
        assert restored.graph_context_execution == before.graph_context_execution
        assert restored.revision == before.revision
        trace, = f.service.list_context_trace_attempts(world_id=before.world_id, turn_id=before.turn_id)
        assert not any(p.kind == "source_passage_reuse" for p in trace.observations)
    finally:
        current.adapter.fence.renewer.stop_and_join()


@pytest.mark.parametrize("acquired", ["native_search"], indirect=True)
def test_play_reuse_exact_replay_and_reset_keep_claim_fences(acquired, monkeypatch):
    f, _origin, _producer, _trace = _captured_play_origin(acquired, monkeypatch)
    current = _next_captured_play(f, monkeypatch)
    try:
        reply = current.adapter.broker_source_read(_source_request(current))
        assert json.loads(reply["resultJson"]).get("content") == f.text, reply
        turn = current.adapter.fence.turn
        reused = turn.graph_context_execution.events[-1]
        request = dict(anchor_ids=[f.pin.anchor_id], max_chars=1000,
            elapsed_ms=current.adapter.context_capture.elapsed_ms, request_id=str(reused.reuse_request_id))
        kwargs = dict(expected_revision=reused.request_turn_revision, expected_attempt=turn.attempt, request=request)
        replay, fresh = f.service.admit_retained_source_passages(turn.world_id, turn.conversation_id, turn.turn_id, **kwargs)
        assert not fresh and replay.graph_context_execution == turn.graph_context_execution
        pointer = f.service.get_world_pointer(turn.world_id)
        f.service.new_conversation(t.ConversationCommand(world_id=turn.world_id, command_id=uuid4(),
            expected_pointer_revision=pointer.revision, expected_active_conversation_id=turn.conversation_id))
        with pytest.raises(ApplicationStateConflictError, match="active claim"):
            f.service.admit_retained_source_passages(turn.world_id, turn.conversation_id, turn.turn_id, **kwargs)
    finally:
        current.adapter.fence.renewer.stop_and_join()


def test_source_graph_basis_has_closed_receipt_families():
    from application_state.agent_conversation.source_passage_reuse import source_graph_basis
    from tests.test_play_graph_context import fixture
    play, _execution, _frame = fixture()
    assert source_graph_basis(play) is play
    # Type-dispatch unit only: deliberately do not claim these minimal objects
    # are independently validated receipts. Actual Plan/Play owners are exercised above.
    plan = t.PlanWorldGraphContextReceiptV1.model_construct()
    combined = t.PlanSourceContextReceiptV1.model_construct(graph_capability=plan)
    source_only = t.PlanSourceContextReceiptV1.model_construct(graph_capability=None)
    assert source_graph_basis(plan) is plan
    assert source_graph_basis(combined) is plan
    assert source_graph_basis(source_only) is None
    for unsupported in (None, {}, play.model_dump(mode="json", by_alias=True),
                        SimpleNamespace(graph_authority=play.graph_authority)):
        assert source_graph_basis(unsupported) is None
