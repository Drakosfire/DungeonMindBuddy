"""Actual two-decision controller cycle through existing parent read authority."""
import json
from hashlib import sha256
from types import SimpleNamespace

import pytest

from application_state.agent_conversation import AgentConversationService
from generationengine import GenerationEngineError
from apps.live_control_server.services import agent_turn_service as owner
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.models.world_graph_object_projection import WorldGraphObjectReviewedSourceObservation
from graph_memory.interaction.session_store import create_session
from graph_memory.retrieval.models import WorldGraphRetrievalResult
from tests.test_agent_build_jev_dispatch import (
    build_case as _build_case, _adapter, _invoke, _prepared, Wire,
)


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def _native_reads(adapter, monkeypatch, *, truncated=False, large=False, unrelated=False):
    session = adapter.bootstrap.retrieval_session
    create_session(session)
    text = 'Frank believes the western gate is haunted.'
    observation = WorldGraphObjectReviewedSourceObservation(
        assertion_id='observation-one', subject_node_id='frank', observation_kind='worldbuilding_observation',
        text=text + (' Unrelated context.' * 2200 if large else ''), entity_kind='npc', review_id='review-one',
        contribution_id='contribution-one', publication_revision_id='native-rev-3', source_artifact_id='artifact-one',
        source_revision_id='source-rev-one', evidence_ref_ids=['evidence-one'], visibility='gm', epistemic_kind='belief')
    observations = (observation,)
    if unrelated:
        observations += (observation.model_copy(update={'assertion_id':'unrelated-observation',
            'text':'Unrelated detail. ' * 2200}),)
    result = WorldGraphRetrievalResult.model_validate({'operation':'object', 'outcome':'enough', 'requestedNodeId':'frank',
        'snapshot': {'worldId':'native-build-world', 'campaignId':'', 'scopeMode':'world',
            'focus': {'kind':'none', 'sessionId':None}, 'admissibility':'gm', 'revisionId':'native-rev-3',
            'headRevisionId':'native-rev-3', 'isHead':True},
        'sourceAnchors':[{'anchorId':'anchor-one', 'revisionId':'native-rev-3', 'evidenceRefId':'evidence-one',
            'sourceArtifactId':'artifact-one', 'sourceDomain':'worldbuilding', 'readable':True,
            'locatorKind':'source_span', 'supportingAssertionIds':[row.assertion_id for row in observations]}]})
    pin = SimpleNamespace(anchor_id='anchor-one', graph_revision='native-rev-3', evidence_ref_id='evidence-one',
        source_artifact_id='artifact-one', source_revision_id='source-rev-one')
    resolved = direct.ResolvedWorldGraphReviewedObjectV3(result,(pin,),observations,(),())
    calls = {'graph':0, 'source':0}
    def graph(*args, **kwargs):
        calls['graph'] += 1
        return resolved
    monkeypatch.setattr(direct,'direct_services_from_config',lambda _: SimpleNamespace())
    monkeypatch.setattr(direct,'get_object_with_reviewed_sources_direct_v3',graph)
    monkeypatch.setattr(owner._PolicyExecutionAdapter,'_related_recap_offers',lambda *_:[])
    def read(arguments, *, receipt_version, root):
        assert root is not None
        assert receipt_version == 2 and arguments['anchorIds'] == ['anchor-one']
        calls['source'] += 1
        digest = sha256(text.encode()).hexdigest()
        outcome = 'truncated' if truncated else 'enough'
        return {'schema':'dmb_internal_read_graph_source_batch_v2','retrievalSessionId':session.id,
            'reads':[{'sourceReadId':'source-read-one','result':{
                'schema':'dmb_world_graph_source_anchor_read_v1','anchorId':'anchor-one','evidenceRefId':'evidence-one',
                'sourceArtifactId':'artifact-one','outcome':outcome,'content':text,'contentSha256':digest,
                'lineStart':1,'lineEnd':1,'truncated':truncated},
                'receipt':{'source_read_id':'source-read-one','retrieval_session_id':session.id,
                    'graph_revision':'native-rev-3','anchor_id':'anchor-one','evidence_ref_id':'evidence-one',
                    'source_artifact_id':'artifact-one','source_revision_id':'source-rev-one',
                    'read_content_sha256':digest,'outcome':outcome,'truncated':truncated}}]}
    monkeypatch.setattr('graph_memory.interaction.expansion_executor.execute_read_graph_source',read)
    return calls, text


def _acquire(adapter, *, bundle=False):
    graph = adapter.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
        'schema':'dmb_expand_graph_retrieval_request_v1','retrievalSessionId':adapter.bootstrap.retrieval_session.id,
        'operation':'object','targets':[{'kind':'node','id':'frank'}], 'includeSources':bundle}})
    assert adapter.failure is None, adapter.failure
    if bundle:
        return graph['resultJson'], None
    source = adapter.broker_source_read({'toolName':'read_graph_source','arguments':{
        'retrievalSessionId':adapter.bootstrap.retrieval_session.id,'anchorIds':['anchor-one'],'maxChars':4000}})
    assert adapter.failure is None, adapter.failure
    return graph['resultJson'], source['resultJson']


def _start(build_case, monkeypatch, **read_options):
    adapter, state = _adapter(build_case)
    calls, text = _native_reads(adapter, monkeypatch, **read_options)
    _invoke(adapter,state,Wire(adapter),[])
    return adapter,calls,text


@pytest.mark.parametrize('bundle',[False,True])
def test_two_sdk_decisions_parent_graph_source_cycle_and_fresh_readback(build_case,monkeypatch,bundle):
    adapter,calls,text = _start(build_case,monkeypatch)
    graph,source = _acquire(adapter,bundle=bundle)
    state = adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,) if source else ())
    manifest = adapter._build_controller_exposure
    assert state == manifest.state()
    assert state['schema'] == 'dmb_build_jev_controller_state_v1'
    assert text in json.dumps(state)
    assert 'belief' in json.dumps(state)
    wire,seen = Wire(adapter),[]
    _invoke(adapter,state,wire,seen)
    assert len(wire.calls)==1 and calls=={'graph':1,'source':1}
    assert adapter.producing_provider_attempt_id is None
    turn = adapter.turn
    fresh = AgentConversationService().list_turns(turn.world_id,turn.conversation_id)[0]
    attempts = [event for event in fresh.graph_context_execution.events if owner._is_provider_authorization(event)]
    assert len(attempts)==2
    last = attempts[-1]
    assert last.included_assertion_ids==['observation-one']
    assert last.included_evidence_ref_ids==['evidence-one']
    assert sorted(map(str,last.included_graph_event_ids))==state['exposure']['graph_event_ids']
    assert sorted(map(str,last.included_source_read_event_ids))==state['exposure']['source_event_ids']
    assert last.envelope_sha256==sha256(wire.calls[0].content).hexdigest()
    traces = AgentConversationService().list_context_trace_attempts(world_id=turn.world_id,turn_id=turn.turn_id)
    assert any(getattr(observation,'text',None)==text for trace in traces for observation in trace.observations)
    assert adapter._build_controller_exposure is None
    assert not adapter.authorize_prepared_build_decision(_prepared(state))


def test_staged_state_is_immutable_and_omission_denies_second_send(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch)
    graph,source = _acquire(adapter)
    state = adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,))
    state['exposure']['sources']=[]
    assert adapter._build_controller_exposure.state()['exposure']['sources']==[source]
    wire = Wire(adapter)
    with pytest.raises(GenerationEngineError):
        _invoke(adapter,state,wire,[])
    assert wire.calls==[]
    assert len([e for e in adapter.turn.graph_context_execution.events if owner._is_provider_authorization(e)])==1


def test_performed_but_omitted_sources_and_unknown_payloads_are_not_evidence(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch)
    graph,source = _acquire(adapter)
    with pytest.raises(ValueError,match='omits opened source'):
        adapter.stage_build_controller_exposure(graph_payloads=(graph,))
    with pytest.raises(ValueError,match='Unknown or ambiguous'):
        adapter.stage_build_controller_exposure(graph_payloads=(graph+' ',),source_payloads=(source,))
    with pytest.raises(ValueError):
        adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(json.dumps(json.loads(source) | {'worldId':'foreign'}),))


def test_truncated_open_source_cannot_enter_controller_evidence(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch,truncated=True)
    graph,source = _acquire(adapter)
    with pytest.raises(ValueError,match='partial or unadmitted'):
        adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,))


def test_staged_sequence_is_invalidated_by_later_parent_read(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch)
    graph,source = _acquire(adapter)
    state = adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,))
    # Another genuine parent read changes the sequence; the earlier packet stays
    # immutable but cannot authorize against the newer execution ledger.
    adapter.broker_graph_operation({'toolName':'expand_graph_retrieval','arguments':{
        'schema':'dmb_expand_graph_retrieval_request_v1','retrievalSessionId':adapter.bootstrap.retrieval_session.id,
        'operation':'object','targets':[{'kind':'node','id':'frank'}]}})
    assert adapter.failure is None
    wire = Wire(adapter)
    with pytest.raises(GenerationEngineError):
        _invoke(adapter,state,wire,[])
    assert wire.calls==[]


@pytest.mark.parametrize("unknown",[False,True])
def test_unresolved_controller_cannot_stage_retrieval_evidence(build_case,unknown):
    adapter,state = _adapter(build_case)
    prepared = _prepared(state)
    assert adapter.authorize_prepared_build_decision(prepared)
    if unknown:
        from generationengine.decision_dispatch import DecisionDispatchEvent
        assert adapter.record_prepared_build_decision(DecisionDispatchEvent(prepared,'sending'))
        assert adapter.record_prepared_build_decision(DecisionDispatchEvent(prepared,'outcome_unknown'))
    with pytest.raises(ValueError,match='resolved controller response'):
        adapter.stage_build_controller_exposure(graph_payloads=('unknown',))


def test_partial_claim_fragment_is_not_complete_controller_evidence(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch,large=True)
    graph,source = _acquire(adapter)
    with pytest.raises(ValueError,match='complete exposed support'):
        adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,))


def test_complete_claim_does_not_require_unrelated_graph_rows(build_case,monkeypatch):
    adapter,_,_ = _start(build_case,monkeypatch,unrelated=True)
    graph,source = _acquire(adapter)
    exposure, = adapter._tool_presentation().inclusion('expand_graph_retrieval',[graph])
    assert not exposure.complete
    assert exposure.assertion_ids==frozenset({'observation-one'})
    state = adapter.stage_build_controller_exposure(graph_payloads=(graph,),source_payloads=(source,))
    _invoke(adapter,state,Wire(adapter),[])
    attempt = [e for e in adapter.turn.graph_context_execution.events if owner._is_provider_authorization(e)][-1]
    assert attempt.included_assertion_ids==['observation-one']
