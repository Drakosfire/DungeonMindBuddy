from __future__ import annotations

import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.index_graph.managed_world import bind_initialized_guest_world
from application_state.index_graph.sessions import create_session
from application_state.world_catalog import service as catalog
from apps.live_control_server.services import index_graph
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository


@pytest.fixture
def guest_repository(monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    repository = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(index_graph, "repository", lambda: repository)
    return repository


def test_guest_world_uses_same_graph_and_replays_without_cross_session_access(
    application_state_dsn, guest_repository,
):
    credential, first = create_session()
    _, second = create_session()
    first_world = index_graph.ensure_guest_managed_world(first)
    replay = index_graph.ensure_guest_managed_world(first)
    second_world = index_graph.ensure_guest_managed_world(second)
    with index_graph.open_index_graph_service(first) as graph:
        first_graph = graph.graph()
    assert replay == first_world
    assert first_world.record.native_graph_binding.native_world_id == first_graph["world_id"]
    assert second_world.record.world_id != first_world.record.world_id
    assert second_world.record.native_graph_binding.native_world_id != first_graph["world_id"]
    assert catalog.get_world(first_world.record.world_id) == first_world

    _, reset_session = create_session(replace_credential=credential)
    with pytest.raises(ApplicationStateConflictError, match="no longer active"):
        bind_initialized_guest_world(first)
    reset_world = index_graph.ensure_guest_managed_world(reset_session)
    assert reset_world.record.world_id not in {first_world.record.world_id, second_world.record.world_id}
    assert reset_world.record.native_graph_binding.native_world_id != first_graph["world_id"]


def test_guest_world_rejects_uninitialized_and_conflicting_metadata(
    application_state_dsn, guest_repository,
):
    _, session = create_session()
    with pytest.raises(ApplicationStateConflictError, match="not initialized"):
        bind_initialized_guest_world(session)
    world = index_graph.ensure_guest_managed_world(session)
    altered = world.record.model_copy(update={"name": "Unexpected World"})
    catalog.save_world(altered, expected_revision=world.revision)
    with pytest.raises(ApplicationStateConflictError, match="conflicts"):
        bind_initialized_guest_world(session)


def test_concurrent_binding_recovers_one_world_and_refuses_changed_allocation(
    application_state_dsn, guest_repository,
):
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace

    _, session = create_session()
    with index_graph.open_index_graph_service(session) as graph:
        native_id = graph.graph()["world_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(bind_initialized_guest_world, (session, session)))
    assert results[0] == results[1]
    assert results[0].record.native_graph_binding.native_world_id == native_id
    with pytest.raises(ApplicationStateConflictError, match="no longer active"):
        bind_initialized_guest_world(replace(session, allocation_id="buddy-index-graph:forged"))


def test_hosted_snapshot_world_binding_preserves_source_and_guest_graph(
    application_state_dsn, guest_repository, monkeypatch, tmp_path,
):
    from apps.live_control_server.native_graph_demo import NativeGraphDemoService

    source_service = NativeGraphDemoService(guest_repository, tmp_path / "source", storage_label="memory")
    try:
        source = source_service.graph()
    finally:
        source_service.close()
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted")
    monkeypatch.setenv("DMB_HOSTED_GUEST_GRAPH_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_SPACE", source["world_id"])
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_REVISION", source["revision_id"])
    _, session = create_session()
    bound = index_graph.ensure_guest_managed_world(session)
    with index_graph.open_index_graph_service(session) as guest:
        copied = guest.graph()
    assert bound.record.native_graph_binding.native_world_id == copied["world_id"]
    assert copied["world_id"] != source["world_id"]
    assert len(copied["nodes"]) == len(source["nodes"])
    assert guest_repository.get_head(source["world_id"]).head_revision_id == source["revision_id"]


def test_retries_catalog_failure_against_original_copied_graph(
    application_state_dsn, guest_repository, monkeypatch,
):
    from application_state.index_graph import managed_world

    _, session = create_session()
    original = managed_world.bind_initialized_guest_world
    def unavailable(_session):
        raise RuntimeError("simulated catalog interruption")
    monkeypatch.setattr(managed_world, "bind_initialized_guest_world", unavailable)
    with pytest.raises(RuntimeError, match="interruption"):
        index_graph.ensure_guest_managed_world(session)
    with index_graph.open_index_graph_service(session) as graph:
        original_id = graph.graph()["world_id"]
    monkeypatch.setattr(managed_world, "bind_initialized_guest_world", original)
    recovered = index_graph.ensure_guest_managed_world(session)
    assert recovered.record.native_graph_binding.native_world_id == original_id
