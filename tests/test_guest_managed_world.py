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
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_HOSTED_GUEST_GRAPH_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_SPACE", source["world_id"])
    monkeypatch.setenv("DMB_GUEST_GRAPH_SOURCE_REVISION", source["revision_id"])
    from application_state.index_graph.sessions import hosted_guest_graph_enabled
    assert hosted_guest_graph_enabled()
    _, session = create_session()
    bound = index_graph.ensure_guest_managed_world(session)
    with index_graph.open_index_graph_service(session) as guest:
        copied = guest.graph()
    assert bound.record.native_graph_binding.native_world_id == copied["world_id"]
    assert copied["world_id"] != source["world_id"]
    assert len(copied["nodes"]) == len(source["nodes"])
    assert guest_repository.get_head(source["world_id"]).head_revision_id == source["revision_id"]


def test_released_pages_are_seeded_once_per_guest_and_reset(
    application_state_dsn, guest_repository, monkeypatch, tmp_path,
):
    import json
    import hashlib
    from concurrent.futures import ThreadPoolExecutor
    from application_state.content import pages
    from apps.live_control_server.native_graph_demo import NativeGraphDemoService

    source_service = NativeGraphDemoService(guest_repository, tmp_path / 'source', storage_label='memory')
    try:
        source = source_service.graph()
    finally:
        source_service.close()
    bundle = tmp_path / 'release.json'
    bundle.write_text(json.dumps({'version': 1, 'graph_space': source['world_id'],
                                  'graph_revision': source['revision_id'],
                                  'documents': [{'title': 'Apprentice', 'markdown': 'A source.'}]}))
    monkeypatch.setenv('DMB_DEPLOYMENT_ENVIRONMENT', 'production')
    monkeypatch.setenv('DMB_AUTH_MODE', 'hosted_dms')
    monkeypatch.setenv('DMB_HOSTED_GUEST_GRAPH_ENABLED', '1')
    monkeypatch.setenv('DMB_GUEST_GRAPH_SOURCE_SPACE', source['world_id'])
    monkeypatch.setenv('DMB_GUEST_GRAPH_SOURCE_REVISION', source['revision_id'])
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE', str(bundle))
    monkeypatch.setenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', hashlib.sha256(bundle.read_bytes()).hexdigest())
    credential, first = create_session()
    _, second = create_session()
    with index_graph.open_index_graph_service(first) as graph:
        graph.graph()
    from application_state.index_graph import guest_documents
    original_commit = guest_documents.content._commit_in_connection
    def fail_after_write(*args, **kwargs):
        original_commit(*args, **kwargs)
        raise RuntimeError('injected seed failure')
    with monkeypatch.context() as injected:
        injected.setattr(guest_documents.content, '_commit_in_connection', fail_after_write)
        with pytest.raises(RuntimeError, match='injected seed failure'):
            bind_initialized_guest_world(first)
    from uuid import UUID
    assert catalog.get_world(f'guest-{UUID(first.session_id).hex}') is None
    with ThreadPoolExecutor(max_workers=2) as pool:
        bindings = list(pool.map(bind_initialized_guest_world, (first, first)))
    assert bindings[0] == bindings[1]
    world1 = bindings[0].record.world_id
    world2 = index_graph.ensure_guest_managed_world(second).record.world_id
    page1, = pages.list_pages(world_id=world1)
    page2, = pages.list_pages(world_id=world2)
    assert page1.page.work_object_id != page2.page.work_object_id
    original = pages.snapshot_page(str(page1.page.work_object_id), world_id=world1)
    assert original.markdown == 'A source.'
    pages.save_draft(str(page1.page.work_object_id), 'Guest edit.', world_id=world1,
                     expected_revision=page1.page.object_revision,
                     expected_working_copy_revision=original.working_copy_revision)
    assert index_graph.ensure_guest_managed_world(first).record.world_id == world1
    assert len(pages.list_pages(world_id=world1)) == 1
    assert pages.snapshot_page(str(page1.page.work_object_id), world_id=world1).markdown == 'Guest edit.'
    assert pages.snapshot_page(str(page2.page.work_object_id), world_id=world2).markdown == 'A source.'
    _, reset = create_session(replace_credential=credential)
    world3 = index_graph.ensure_guest_managed_world(reset).record.world_id
    assert pages.snapshot_page(str(pages.list_pages(world_id=world3)[0].page.work_object_id), world_id=world3).markdown == 'A source.'


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


def test_catalog_write_failure_rolls_back_and_retry_recovers(
    application_state_dsn, guest_repository, monkeypatch,
):
    from application_state.index_graph import managed_world

    _, session = create_session()
    with index_graph.open_index_graph_service(session) as graph:
        native_id = graph.graph()["world_id"]
    write = catalog._write
    def fail_after_write(*args, **kwargs):
        write(*args, **kwargs)
        raise RuntimeError("simulated interrupted transaction")
    with monkeypatch.context() as patch:
        patch.setattr(catalog, "_write", fail_after_write)
        with pytest.raises(RuntimeError, match="interrupted transaction"):
            managed_world.bind_initialized_guest_world(session)
    recovered = managed_world.bind_initialized_guest_world(session)
    assert recovered.revision == 1
    assert recovered.record.native_graph_binding.native_world_id == native_id


def test_binding_rejects_naturally_expired_session(application_state_dsn, guest_repository):
    from application_state.engine import connect

    _, session = create_session()
    with index_graph.open_index_graph_service(session) as graph:
        graph.graph()
    with connect() as connection:
        connection.execute(
            "UPDATE application_state.index_graph_sessions SET expires_at = clock_timestamp() - interval '1 second' WHERE session_id = %s::uuid",
            (session.session_id,),
        )
        connection.commit()
    with pytest.raises(ApplicationStateConflictError, match="no longer active"):
        bind_initialized_guest_world(session)


def test_reset_waits_for_inflight_binding_and_then_revokes_it(
    application_state_dsn, guest_repository, monkeypatch,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    credential, session = create_session()
    with index_graph.open_index_graph_service(session) as graph:
        graph.graph()
    entered, release = Event(), Event()
    original_write = catalog._write
    def delayed_write(*args, **kwargs):
        entered.set()
        if not release.wait(10):
            raise RuntimeError("binding test timed out")
        return original_write(*args, **kwargs)
    monkeypatch.setattr(catalog, "_write", delayed_write)
    with ThreadPoolExecutor(max_workers=2) as pool:
        binding = pool.submit(bind_initialized_guest_world, session)
        try:
            assert entered.wait(10)
            reset = pool.submit(create_session, replace_credential=credential)
            assert not reset.done()
        finally:
            release.set()
        old_world = binding.result(timeout=10)
        _, replacement = reset.result(timeout=10)
    with pytest.raises(ApplicationStateConflictError, match="no longer active"):
        bind_initialized_guest_world(session)
    new_world = index_graph.ensure_guest_managed_world(replacement)
    assert old_world.record.world_id != new_world.record.world_id
