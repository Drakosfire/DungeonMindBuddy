"""Acquisition-wave ownership at Buddy's actual selection/body-read boundary."""
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import Mock

import pytest

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reads
from apps.live_control_server.integrations.dungeonmind.reviewed_source_wave import reviewed_source_wave
from apps.live_control_server.integrations.dungeonmind.selected_observation_reads import select_observations_direct
from graph_memory.retrieval.models import WorldGraphObservationSelectionRequest
from tests.test_selected_observation_reads import case
from tests import test_batched_admitted_source_reads as batch_fixtures


@pytest.fixture
def source_case(tmp_path, monkeypatch):
    yield from batch_fixtures.setup.__wrapped__(tmp_path, monkeypatch)


def bind(native, services):
    events, captures = [], []
    @contextmanager
    def session(request):
        events.append('open')
        captures.append(request)
        try:
            yield native
        finally:
            events.append('closed')
    retrieval = N(reviewed_source_session=Mock(side_effect=session),
                  select_reviewed_source_observations=Mock(side_effect=AssertionError('outside session')),
                  resolve_source_anchors=Mock(side_effect=AssertionError('outside session')))
    return reads.DirectWorldGraphReadServices(services.bundle if hasattr(services, 'bundle') else None,
        None, retrieval, services.binding), events, captures


def test_selection_uses_copied_services_and_closes_retained_handle():
    native, request, original, _ = case()
    session = N(select_observations=Mock(return_value=native))
    services, events, captures = bind(session, original)
    with reviewed_source_wave(services, request) as bound:
        assert bound is not services and bound.retrieval is services.retrieval
        assert services.reviewed_source_wave is None
        result = select_observations_direct(bound, request)
        session.select_observations.assert_called_once_with(tuple(request.observation_ids), max_bytes=request.max_bytes)
        assert result.reviewed_source_observations[0].epistemic_kind == 'belief'
        assert captures[0].source_artifact_id == request.source_artifact_id
        assert captures[0].projection.revision_pin == 'rev:1'
        with pytest.raises(ValueError, match='nested'):
            with reviewed_source_wave(bound, request):
                pass
    assert events == ['open', 'closed']
    with pytest.raises(reads.DirectWorldGraphReadError, match='closed'):
        select_observations_direct(bound, request)
    services.retrieval.select_reviewed_source_observations.assert_not_called()


@pytest.mark.parametrize('field,value', [('world_id','foreign'), ('revision_pin','rev:foreign'),
    ('admissibility','player'), ('scope_mode','campaign'),
    ('source_artifact_id','foreign'), ('source_revision_id','foreign')])
def test_wave_rejects_scope_source_drift_before_native_call(field, value):
    native, request, original, _ = case()
    session = N(select_observations=Mock(return_value=native))
    services, events, _ = bind(session, original)
    changed = request.model_copy(update={field: value, **({'campaign_id': 'campaign:other'} if field == 'scope_mode' else {})})
    with reviewed_source_wave(services, request) as bound:
        with pytest.raises(reads.DirectWorldGraphReadError):
            select_observations_direct(bound, changed)
        session.select_observations.assert_not_called()
    assert events == ['open', 'closed']


def test_original_mutable_request_cannot_retarget_open_wave():
    native, request, original, _ = case()
    session = N(select_observations=Mock(return_value=native))
    services, _, _ = bind(session, original)
    unchanged = request.model_copy(deep=True)
    with reviewed_source_wave(services, request) as bound:
        request.world_id = 'foreign'
        request.source_revision_id = 'foreign'
        assert select_observations_direct(bound, unchanged).reviewed_source_observations


@pytest.mark.parametrize('status,code', [('overflow','observation_selection_overflow'),
                                        ('unavailable','selected_observation_unavailable')])
def test_partition_refusal_and_caller_failure_release_session(status, code):
    native, request, original, _ = case()
    session = N(select_observations=Mock(return_value=replace(native, status=status)))
    services, events, _ = bind(session, original)
    with pytest.raises(reads.DirectWorldGraphReadError) as caught:
        with reviewed_source_wave(services, request) as bound:
            select_observations_direct(bound, request)
    assert caught.value.code == code and events == ['open', 'closed']
    with pytest.raises(RuntimeError, match='closed'):
        bound.reviewed_source_wave.select(captures_request(request, services))


def captures_request(request, services):
    from dungeonmind.application.world_graph_retrieval import ReviewedObservationSelectionRequest
    return ReviewedObservationSelectionRequest(reads._map_retrieval_context(request, services.binding),
        request.source_artifact_id, request.source_revision_id, tuple(request.observation_ids))


def test_same_wave_anchor_resolution_keeps_real_body_joins_and_receipts(source_case):
    f = source_case
    ordinary = reads.read_source_anchors_direct_v2(f.services, f.requests, repo_root=f.root)
    session = N(resolve_anchors=Mock(side_effect=lambda ids: f.resolve(N(anchor_ids=ids))))
    services, events, _ = bind(session, f.services)
    request = WorldGraphObservationSelectionRequest.model_validate({
        'schema':'dmb_world_graph_observation_selection_v1', 'worldId':'world:test',
        'campaignId':'', 'scopeMode':'world', 'revisionPin':'rev:test', 'admissibility':'gm',
        'sourceArtifactId': 'artifact:test', 'sourceRevisionId':'source:test', 'observationIds':['assertion:test']})
    with reviewed_source_wave(services, request) as bound:
        actual = reads.read_source_anchors_direct_v2(bound, f.requests, repo_root=f.root)
    session.resolve_anchors.assert_called_once_with(tuple(r.anchor_id for r in f.requests))
    assert [r.result.model_dump() for r in actual] == [r.result.model_dump() for r in ordinary]
    assert [r.source_revision_sha256 for r in actual] == [r.source_revision_sha256 for r in ordinary]
    assert all(r.source_revision_id and r.evidence_ref_id for r in actual)
    assert events == ['open', 'closed']


def test_executor_retains_actual_open_receipts_inside_wave(source_case, monkeypatch):
    from tests.test_batched_admitted_source_reads import test_actual_executor_uses_one_batch_and_records_only_opened_bodies
    f = source_case
    session = N(resolve_anchors=Mock(side_effect=lambda ids: f.resolve(N(anchor_ids=ids))))
    services, events, _ = bind(session, f.services)
    request = WorldGraphObservationSelectionRequest.model_validate({
        'schema':'dmb_world_graph_observation_selection_v1', 'worldId':'world:test',
        'campaignId':'', 'scopeMode':'world', 'revisionPin':'rev:test', 'admissibility':'gm',
        'sourceArtifactId':'artifact:test', 'sourceRevisionId':'source:test', 'observationIds':['assertion:test']})
    with reviewed_source_wave(services, request) as bound:
        f.services = bound
        test_actual_executor_uses_one_batch_and_records_only_opened_bodies(f, monkeypatch)
    assert events == ['open', 'closed']
    assert session.resolve_anchors.call_count == 1
