"""Native owning session through Buddy's real object adapter, no runtime data."""
from unittest.mock import Mock

import pytest
from graph_memory.retrieval.models import WorldGraphObjectRequest
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reads
from apps.live_control_server.integrations.dungeonmind.object_read_wave import object_read_wave
from tests.test_world_graph_retrieval_contract import _selected_native_fixture


def case():
    services, search, _ = _selected_native_fixture(unrelated=1)
    request = WorldGraphObjectRequest.model_validate({
        'schema': 'dmb_world_graph_object_request_v1', 'worldId': search.world_id,
        'revisionPin': search.revision_pin, 'campaignId':search.campaign_id,
        'scopeMode':search.scope_mode, 'nodeId': 'obj:tavern'})
    return services, request


def test_native_objects_share_one_context_and_retained_facade_closes(monkeypatch):
    services, request = case()
    open_context = Mock(wraps=services.projection.open_read_context)
    monkeypatch.setattr(services.projection, 'open_read_context', open_context)
    with object_read_wave(services, request, object_ids=('obj:tavern', 'obj:noise:0')) as bound:
        assert bound is not services and services.object_read_wave is None
        assert open_context.call_count == 0
        first = reads.get_object_with_reviewed_sources_direct_v3(bound, request)
        second = reads.get_object_with_reviewed_sources_direct_v3(bound, request.model_copy(update={'node_id':'obj:noise:0'}))
        assert first.result.resolved_node_id == 'obj:tavern'
        assert second.result.resolved_node_id == 'obj:noise:0'
        assert first.result.snapshot == second.result.snapshot
        assert open_context.call_count == 1
        with pytest.raises(ValueError, match='nested'):
            with object_read_wave(bound, request, object_ids=('obj:tavern',)):
                pass
    with pytest.raises(reads.DirectWorldGraphReadError, match='closed'):
        reads.get_object_with_reviewed_sources_direct_v3(bound, request)
    assert open_context.call_count == 1
    with object_read_wave(services, request, object_ids=('obj:tavern',)) as fresh:
        reads.get_object_with_reviewed_sources_direct_v3(fresh, request)
    assert open_context.call_count == 2


@pytest.mark.parametrize('field,value', [('world_id','foreign'), ('revision_pin','foreign'),
    ('admissibility','player'), ('scope_mode','campaign'), ('node_id','foreign')])
def test_scope_and_target_drift_do_not_read_native(monkeypatch, field, value):
    services, request = case()
    open_context = Mock(wraps=services.projection.open_read_context)
    monkeypatch.setattr(services.projection, 'open_read_context', open_context)
    changed = request.model_copy(update={field:value, **({'campaign_id':'other'} if field=='scope_mode' else {})})
    with object_read_wave(services, request, object_ids=('obj:tavern',)) as bound:
        with pytest.raises(reads.DirectWorldGraphReadError):
            reads.get_object_with_reviewed_sources_direct_v3(bound, changed)
    assert open_context.call_count == 0


def test_request_mutation_does_not_retarget_and_exception_closes():
    services, request = case()
    captured = request.model_copy(deep=True)
    with pytest.raises(RuntimeError, match='stop'):
        with object_read_wave(services, request, object_ids=('obj:tavern',)) as bound:
            request.world_id = 'foreign'
            assert reads.get_object_with_reviewed_sources_direct_v3(bound, captured).result.resolved_node_id == 'obj:tavern'
            raise RuntimeError('stop')
    with pytest.raises(reads.DirectWorldGraphReadError, match='closed'):
        reads.get_object_with_reviewed_sources_direct_v3(bound, captured)
