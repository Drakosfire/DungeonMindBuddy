"""Selected native observations preserve scope, qualification and exact support."""
from dataclasses import replace
from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError
from dungeonmind.application.world_graph_retrieval import (
    ReviewedObservationSelectionResult, ReviewedObservationSubject,
    ReviewedSourceObservation, RetrievalCoverage, SourceAnchorMetadata,
)
from dungeonmind.contracts.projection_v2 import ScopeModeV2
from dungeonmind.contracts.vocabulary import Visibility
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.integrations.dungeonmind.selected_observation_reads import select_observations_direct
from apps.live_control_server.services.hermes_graph_interaction_tools import hermes_graph_interaction_tool_definitions
from graph_memory.interaction.expansion_executor import ExpandGraphRetrievalRequest, resolve_expansion_target_ids
from graph_memory.retrieval.models import WorldGraphObservationSelectionRequest


def case():
    observations = tuple(ReviewedSourceObservation(assertion_id=f'assertion:{i}',
        subject_object_id=f'npc:{i}', observation_kind='worldbuilding_observation',
        text=f'Person {i} believes the cult threatens their work.', entity_kind='npc',
        review_id='review:1', contribution_id='contribution:1', publication_revision_id='rev:1',
        source_artifact_id='artifact:1', source_revision_id='source:1', evidence_ref_ids=(f'evidence:{i}',),
        campaign_scope='campaign:old', visibility=Visibility.GM, epistemic_kind='belief',
        temporal_scope={'as_of': 'undated source'}) for i in range(2))
    anchors = tuple(SourceAnchorMetadata(anchor_id=f'dm-source-anchor:v1:{i}', evidence_ref_id=f'evidence:{i}',
        source_artifact_id='artifact:1', source_revision_id='source:1', locator_identity=f'span:{i}',
        source_span_ref_id=f'span:{i}', can_open_source=True, can_highlight_span=True,
        supporting_object_ids=(), supporting_relationship_ids=(), supporting_assertion_ids=(f'assertion:{i}',),
        evidence=N(source_domain='worldbuilding', session_id=None), artifact=N(uri='repo://source.md'))
        for i in range(2))
    native = ReviewedObservationSelectionResult(snapshot=N(world_id='native', campaign_id=None,
        revision_id='rev:1', head_revision_id='rev:1', is_head=True, admissibility='gm',
        scope_mode=ScopeModeV2.WORLD_CROSS_CAMPAIGN), source_artifact_id='artifact:1',
        source_revision_id='source:1', requested_assertion_ids=('assertion:0', 'assertion:1'),
        status='complete', max_bytes=262144, observations=observations,
        subjects=tuple(ReviewedObservationSubject(f'npc:{i}', f'Person {i}', 'npc') for i in range(2)),
        anchors=anchors, coverage=RetrievalCoverage())
    request = WorldGraphObservationSelectionRequest.model_validate({
        'schema': 'dmb_world_graph_observation_selection_v1', 'worldId': 'native',
        'campaignId': '', 'scopeMode': 'world', 'admissibility': 'gm', 'revisionPin': 'rev:1',
        'sourceArtifactId': 'artifact:1', 'sourceRevisionId': 'source:1',
        'observationIds': ['assertion:0', 'assertion:1']})
    calls = []
    def read(value):
        calls.append(value)
        return native
    services = N(binding=N(legacy_buddy_revision_id=None),
        retrieval=N(select_reviewed_source_observations=read))
    return native, request, services, calls


def test_adapter_preserves_full_records_disjoint_pins_and_actual_cross_campaign_request():
    native, request, services, calls = case()
    result = select_observations_direct(services, request)
    call, = calls
    assert call.projection.scope_mode == ScopeModeV2.WORLD_CROSS_CAMPAIGN
    assert call.projection.revision_pin == 'rev:1' and call.source_revision_id == 'source:1'
    assert call.source_artifact_id == 'artifact:1' and call.assertion_ids == ('assertion:0', 'assertion:1')
    assert result.result.operation == 'observations' and not result.result.attributes
    assert not result.result.relationships and len(result.result.nodes) == 2
    for observation in result.reviewed_source_observations:
        i = observation.assertion_id[-1]
        assert observation.epistemic_kind == 'belief' and observation.temporal_scope == {'as_of': 'undated source'}
        assert observation.evidence_ref_ids == [f'evidence:{i}']
        pin = next(p for p in result.source_pins if p.evidence_ref_id == f'evidence:{i}')
        assert pin.source_artifact_id == 'artifact:1' and pin.source_revision_id == 'source:1'
        anchor = next(a for a in result.result.source_anchors if a.anchor_id == pin.anchor_id)
        assert anchor.supporting_assertion_ids == [observation.assertion_id]
    assert native.observations[0].text == result.reviewed_source_observations[0].text


@pytest.mark.parametrize('status,code,http', [('unavailable', 'selected_observation_unavailable', 422),
                                           ('overflow', 'observation_selection_overflow', 413)])
def test_atomic_refusal_never_returns_a_partly_admitted_result(status, code, http):
    native, request, services, _ = case()
    services.retrieval.select_reviewed_source_observations = lambda _: replace(native,
        status=status, observations=(), anchors=(), subjects=())
    with pytest.raises(direct.DirectWorldGraphReadError) as caught:
        select_observations_direct(services, request)
    assert caught.value.code == code and caught.value.status_code == http


@pytest.mark.parametrize('change', ['wrong-source', 'wrong-revision', 'missing-record'])
def test_native_selection_mismatch_is_rejected(change):
    native, request, services, _ = case()
    changes = {'source_artifact_id': 'other'} if change == 'wrong-source' else (
        {'source_revision_id': 'other'} if change == 'wrong-revision' else {'observations': native.observations[:1]})
    services.retrieval.select_reviewed_source_observations = lambda _: replace(native, **changes)
    with pytest.raises(direct.DirectWorldGraphReadError):
        select_observations_direct(services, request)


@pytest.mark.parametrize('extra', [{'observationIds': []}, {'observationIds': ['a', 'a']},
    {'targets': [{'id': 'npc:other'}]}, {'queryText': 'cult'}, {'depth': 2},
    {'sourceArtifactId': 'forged'}, {'sourceRevisionId': 'forged'}])
def test_model_request_cannot_change_batch_scope_or_silently_fall_back(extra):
    with pytest.raises(ValidationError):
        ExpandGraphRetrievalRequest.model_validate({'retrievalSessionId': 'session', 'operation': 'observations',
            'observationIds': ['a'], **extra})


def test_worker_tool_schema_exposes_batch_and_no_implicit_object_targets():
    schema = hermes_graph_interaction_tool_definitions()[0]['function']['parameters']
    assert 'observations' in schema['properties']['operation']['enum']
    request = ExpandGraphRetrievalRequest.model_validate({'retrievalSessionId': 'session',
        'operation': 'observations', 'observationIds': ['a']})
    assert resolve_expansion_target_ids(request, N()) == []


def test_legacy_executor_refuses_batch_instead_of_falling_back_to_search(tmp_path):
    from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
    from graph_memory.interaction.session_store import create_session, clear_sessions
    from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval
    clear_sessions()
    try:
        session = create_session(GraphRetrievalSession(snapshot=SessionSnapshot(world_id='native',
            campaign_id='', revision_id='rev:1', scope_mode='world'), question='Cult concerns'))
        response = execute_expand_graph_retrieval({'retrievalSessionId': session.id,
            'operation': 'observations', 'observationIds': ['assertion:0']}, root=tmp_path)
        assert response['code'] == 'selected_observations_unavailable'
        assert not session.claims
    finally:
        clear_sessions()
