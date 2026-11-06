"""Owning allocation construction and existing GE request/receipt boundary, offline."""
import json
import sys
from types import SimpleNamespace

import pytest
from generationengine.types import TextResult

from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient, DEEPSEEK_MODEL, RecapExecutionLimits,
)
from tests.test_bounded_recap_execution import (
    Engine, deepseek_observation, invoke, semantic_engine_seam,
)


def test_ordinary_v2_uses_owned_default_path_with_only_reasoning_disabled(tmp_path, monkeypatch):
    from apps.live_control_server.services import graph_preview_runner as owner
    from apps.live_control_server.services import managed_world_graph_projection as projection

    context = {'managed_world_id': 'managed:synthetic', 'native_world_id': 'world:synthetic',
               'binding_version': 1}
    source = SimpleNamespace(source_domain='recap', world_id='world:synthetic',
        campaign_id='synthetic', session_id='session-1', source_sha256='a' * 64,
        source_artifact_id='artifact:synthetic')
    monkeypatch.setattr(owner, 'artifact_data_root', lambda root: root)
    monkeypatch.setattr(owner, '_source_scope_lineage', lambda *a, **kw: ('world:synthetic', context))
    monkeypatch.setattr(owner, '_normalized_from_registered', lambda *a: source)
    monkeypatch.setattr(projection, 'resolve_managed_source_identity', lambda *a:
        SimpleNamespace(native_world_id='world:synthetic', binding_version=1))
    # The pinned study composition also retains the known-character donor.
    # This allocation-only test must not read its live graph context.
    monkeypatch.setitem(sys.modules,
        'apps.live_control_server.services.known_character_context',
        SimpleNamespace(read_known_character_catalog=lambda *a: None))
    constructed = []
    def client(limits, **kwargs):
        result = SimpleNamespace(limits=limits, context=kwargs)
        constructed.append(result)
        return result
    monkeypatch.setattr(owner, 'BoundedRecapPassClient', client)
    monkeypatch.setattr(owner, 'run_production_extraction', lambda request: request)
    request = owner.run_recap_production_extraction(repo_root=tmp_path, campaign_id='synthetic',
        session_id='session-1', source_artifact_id='artifact:synthetic', allow_llm=True,
        ingest_context=context)
    assert len(constructed) == 1 and request.category_client is constructed[0]
    assert request.model_id == DEEPSEEK_MODEL
    assert constructed[0].limits == RecapExecutionLimits(
        provider='openrouter', model=DEEPSEEK_MODEL, max_calls=7,
        max_output_tokens=32768, edge_max_output_tokens=32768,
        per_call_deadline_ms=240000, run_deadline_ms=900000, reasoning_effort='none')
    assert constructed[0].context['request_context_hashes']['source_content'] == source.source_sha256


@pytest.mark.parametrize('effort', ['low', 'none'])
def test_explicit_effort_reaches_existing_request_and_retained_telemetry(effort):
    engine = Engine(TextResult(text=json.dumps({'observation_nodes': []}), observation=deepseek_observation()))
    client = BoundedRecapPassClient(RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL,
        reasoning_effort=effort, max_calls=1, max_output_tokens=32768,
        edge_max_output_tokens=32768, per_call_deadline_ms=240000, run_deadline_ms=900000),
        engine_factory=lambda: engine)
    invoke(client, DEEPSEEK_MODEL)
    request = engine.requests[0]
    assert request.reasoning_effort == effort
    assert request.provider_route.order == ('DeepSeek',)
    assert request.provider_route.require_parameters and not request.provider_route.allow_fallbacks
    assert request.max_output_tokens == 32768 and request.deadline_ms == 240000
    assert client.calls[0]['reasoning_effort'] == effort
    assert len(engine.requests) == 1 and engine.closed == 1
