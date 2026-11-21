"""Database boundary checks for guest release state (no public routes)."""
import hashlib
import copy
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event, current_thread
from time import monotonic
from uuid import uuid4

import psycopg
import pytest

from application_state import guest_release
from application_state.content.pages import PageMetadata, commit_page, committed_page, create_page, snapshot_page
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.world_catalog.service import create_world


def _promote(**kwargs):
    return guest_release.commit_validated_promotion(operation_id=uuid4(), source_epoch=1, **kwargs)


def _bind(dsn, world):
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE workspace.world_native_binding SET native_world_id=%s,status='active', "
            "binding_version=1,validated_at='now',validated_head_revision_id='rev-1', "
            "provisioning_id=NULL,initialization_revision_id=NULL WHERE world_id=%s", ("native-" + world, world))
    return {"native_world_id": "native-" + world, "native_binding_version": 1, "graph_revision": "rev-1"}


def test_stage_rejects_graph_citation_without_release_excerpt():
    with pytest.raises(ApplicationStateValidationError):
        guest_release.stage(world_id="world", subject="owner", expected_owner_generation=0,
            native_world_id="native", native_binding_version=1, graph_revision="rev",
            manifest={"assets": [], "sources": [], "graph": {"edges": [{"citations": [str(uuid4())]}]}},
            assets=[])


def test_node_field_bindings_round_trip_and_require_both_citations(application_state_dsn):
    world = create_world(name="Field binding fixture", owner_subject="owner").record.world_id
    graph_binding = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="internal"))
    committed, revision = commit_page(str(page.page.work_object_id), "selected", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    excerpt_id, node_id = uuid4(), uuid4()
    source_binding = (excerpt_id, page.page.work_object_id, 0, 0, revision.revision_n,
        revision.content_sha256, 0, 8, committed.page.object_revision, "internal", "evidence")
    node = {"id": str(node_id), "label": "Sizzek", "kind": "character",
            "name_citations": [str(excerpt_id)], "kind_citations": [str(excerpt_id)]}
    private = (node_id, "entity", "name", "evidence", str(excerpt_id), "kind", "evidence", str(excerpt_id))
    args = dict(world_id=world, subject="owner", expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "selected"}],
                  "graph": {"nodes": [node], "edges": []}}, assets=[], source_bindings=[source_binding],
        node_bindings=[private], **graph_binding)
    release, digest = guest_release.stage(**args)
    material = guest_release.validation_material(world_id=world, subject="owner", release_id=release, digest=digest)
    assert material["node_bindings"] == [(node_id, "entity", "name", "evidence", excerpt_id, "kind", "evidence", excerpt_id)]
    node["kind_citations"] = []
    with pytest.raises(ApplicationStateValidationError):
        guest_release.stage(**args)


def test_release_lifecycle_isolated_and_revocation(application_state_dsn):
    world = create_world(name="Fixture World", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    asset_id = uuid4()
    manifest = {"title": "safe", "assets": [{"id": str(asset_id), "mime_type": "image/png",
                "sha256": hashlib.sha256(b"synthetic").hexdigest()}]}
    release_id, digest = guest_release.stage(
        world_id=world, subject="owner", expected_owner_generation=generation,
        manifest=manifest, assets=[(asset_id, "image/png", b"synthetic")], **graph,
    )
    assert [item["release_id"] for item in guest_release.list_candidates(world_id=world, subject="owner")] == [str(release_id)]
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.list_candidates(world_id=world, subject="other")
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.review(world_id=world, subject="other", release_id=release_id)
    assert guest_release.review(world_id=world, subject="owner", release_id=release_id)[1] == digest
    assert guest_release.pointer_status(world_id=world, subject="owner") == (None, 0)
    assert guest_release.review_asset(world_id=world, subject="owner", release_id=release_id,
                                      asset_id=asset_id) == ("image/png", b"synthetic")
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.review_asset(world_id=world, subject="other", release_id=release_id, asset_id=asset_id)
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest="0" * 64, expected_version=0)
    public_id, version = _promote(world_id=world, subject="owner", release_id=release_id,
                                                digest=digest, expected_version=0)
    assert guest_release.list_candidates(world_id=world, subject="owner") == []
    assert guest_release.list_published(world_id=world, subject="owner")[0] | {"published_at": "time"} == {
        "release_id": str(release_id), "published_at": "time", "current": True, "reviewable": True}
    assert guest_release.review(world_id=world, subject="owner", release_id=release_id)[1] == digest
    assert guest_release.pointer_status(world_id=world, subject="owner") == (public_id, version)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    assert guest_release.public_asset(public_id, release_id, asset_id) == ("image/png", b"synthetic")
    guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
    assert guest_release.list_published(world_id=world, subject="owner") == []
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_asset(public_id, release_id, asset_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.restore(world_id=world, subject="owner", release_id=release_id,
                              expected_version=version + 1)


def test_saved_example_is_reviewed_as_immutable_release_data(application_state_dsn):
    world = create_world(name="Saved example fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Private", metadata=PageMetadata(visibility_state="internal"))
    committed, revision = commit_page(str(page.page.work_object_id), "first second", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    first, second, asset = uuid4(), uuid4(), uuid4()
    def binding(local, start, end):
        return (local, page.page.work_object_id, 0, 0, revision.revision_n, revision.content_sha256,
                start, end, committed.page.object_revision, "internal", "synthetic-evidence")
    manifest = {"graph": {"nodes": [], "edges": []},
        "sources": [{"id": str(first), "text": "first", "evidence_role": "support"},
                    {"id": str(second), "text": "second", "evidence_role": "context"}],
        "assets": [{"id": str(asset), "mime_type": "image/png", "sha256": hashlib.sha256(b"image").hexdigest()}],
        "saved_example": {"version": "owner_saved_scene_v1", "title": "Scene", "body": "A scene",
                          "references": [str(first), str(second)], "image": {"id": str(asset), "description": "A tent"}}}
    args = dict(world_id=world, subject="owner", expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest=manifest, assets=[(asset, "image/png", b"image")], source_bindings=[binding(first, 0, 5), binding(second, 6, 12)], **graph)
    invalid = copy.deepcopy(manifest)
    invalid["saved_example"]["references"][1] = str(uuid4())
    with pytest.raises(ApplicationStateValidationError):
        guest_release.stage(**{**args, "manifest": invalid})
    release_id, digest = guest_release.stage(**args)
    changed = copy.deepcopy(manifest)
    changed["saved_example"]["body"] = "Another scene"
    _, changed_digest = guest_release.stage(**{**args, "manifest": changed})
    assert changed_digest != digest
    assert guest_release.review(world_id=world, subject="owner", release_id=release_id) == (manifest, digest)
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id, digest="0" * 64, expected_version=0)
    public_id, _ = _promote(world_id=world, subject="owner", release_id=release_id, digest=digest, expected_version=0)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    current = snapshot_page(str(page.page.work_object_id), world_id=world)
    commit_page(str(page.page.work_object_id), "private changed", world_id=world,
        expected_revision=current.page.object_revision, expected_working_copy_revision=current.working_copy_revision)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    assert str(page.page.work_object_id) not in str(manifest)
    guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)


def test_transfer_away_and_back_invalidates_candidate(application_state_dsn):
    world = create_world(name="Transfer Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=generation, manifest={"title": "safe", "assets": []}, assets=[], **graph)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.managed_world SET owner_subject='other' WHERE world_id=%s", (world,))
        conn.execute("UPDATE workspace.managed_world SET owner_subject='owner' WHERE world_id=%s", (world,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest=digest, expected_version=0)


def test_new_owner_can_revoke_current_copy_but_cannot_restore_old_approval(application_state_dsn):
    world = create_world(name="Transferred release", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    release_id, digest = guest_release.stage(world_id=world, subject="owner", expected_owner_generation=0,
        manifest={"assets": []}, assets=[], **graph)
    public_id, version = _promote(world_id=world, subject="owner", release_id=release_id, digest=digest, expected_version=0)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.managed_world SET owner_subject='new-owner' WHERE world_id=%s", (world,))
    history = guest_release.list_published(world_id=world, subject="new-owner")
    assert len(history) == 1 and history[0]["current"] and not history[0]["reviewable"]
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.restore(world_id=world, subject="new-owner", release_id=release_id, expected_version=version)
    guest_release.revoke(world_id=world, subject="new-owner", release_id=release_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)


def test_asset_request_never_crosses_pointer_promotion(application_state_dsn):
    world = create_world(name="Pointer Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    asset_id = uuid4()
    def stage(content):
        manifest = {"assets": [{"id": str(asset_id), "mime_type": "image/png",
                                 "sha256": hashlib.sha256(content).hexdigest()}]}
        return guest_release.stage(world_id=world, subject="owner", expected_owner_generation=generation,
                                   manifest=manifest, assets=[(asset_id, "image/png", content)], **graph)
    first, first_digest = stage(b"first")
    public_id, version = _promote(world_id=world, subject="owner", release_id=first,
                                               digest=first_digest, expected_version=0)
    assert guest_release.public_manifest(public_id)[0] == first
    second, second_digest = stage(b"second")
    _promote(world_id=world, subject="owner", release_id=second,
                          digest=second_digest, expected_version=version)
    history = {item["release_id"]: item for item in guest_release.list_published(world_id=world, subject="owner")}
    assert not history[str(first)]["current"] and history[str(second)]["current"]
    with pytest.raises(ApplicationStateConflictError):
        guest_release.restore(world_id=world, subject="owner", release_id=first, expected_version=version)
    guest_release.restore(world_id=world, subject="owner", release_id=first, expected_version=version + 1)
    assert guest_release.public_asset(public_id, first, asset_id) == ("image/png", b"first")
    guest_release.restore(world_id=world, subject="owner", release_id=second, expected_version=version + 2)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_asset(public_id, first, asset_id)
    assert guest_release.public_asset(public_id, second, asset_id) == ("image/png", b"second")


@pytest.mark.parametrize("first_operation", ["revoke", "promote"])
def test_promotion_and_revocation_serialize_without_reviving_release(application_state_dsn, monkeypatch, first_operation):
    world = create_world(name="Promotion revocation race", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    def stage(title):
        return guest_release.stage(world_id=world, subject="owner", expected_owner_generation=generation,
                                   manifest={"title": title, "assets": []}, assets=[], **graph)
    old, old_digest = stage("old")
    public_id, version = _promote(world_id=world, subject="owner", release_id=old,
                                  digest=old_digest, expected_version=0)
    new, new_digest = stage("new")
    owner = guest_release._owner
    locked, release, second_entered = Event(), Event(), Event()
    second_pid = []
    def pause_first_owner_check(conn, world_id, subject):
        if current_thread().name.startswith("guest-race") and locked.is_set():
            second_pid.append(conn.info.backend_pid)
            second_entered.set()
        result = owner(conn, world_id, subject)
        if current_thread().name.startswith("guest-race") and not locked.is_set():
            locked.set()
            if not release.wait(5):
                raise RuntimeError("race test failed to release first transaction")
        return result
    monkeypatch.setattr(guest_release, "_owner", pause_first_owner_check)
    def revoke():
        return guest_release.revoke(world_id=world, subject="owner", release_id=old)
    def promote():
        return _promote(world_id=world, subject="owner", release_id=new,
                        digest=new_digest, expected_version=version)
    first, second = (revoke, promote) if first_operation == "revoke" else (promote, revoke)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="guest-race") as pool:
        first_future = pool.submit(first)
        assert locked.wait(5)
        second_future = pool.submit(second)
        try:
            assert second_entered.wait(5)
            deadline = monotonic() + 5
            with psycopg.connect(application_state_dsn, autocommit=True) as observer:
                while True:
                    row = observer.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s",
                                           (second_pid[0],)).fetchone()
                    if row == ("Lock",):
                        break
                    if monotonic() >= deadline:
                        pytest.fail("second transaction did not wait for a PostgreSQL lock")
                    Event().wait(0.02)
            with pytest.raises(TimeoutError):
                second_future.result(timeout=0.3)
        finally:
            release.set()
        first_future.result(timeout=5)
        if first_operation == "revoke":
            with pytest.raises(ApplicationStateConflictError):
                second_future.result(timeout=5)
            with pytest.raises(ApplicationStateNotFoundError):
                guest_release.public_manifest(public_id)
        else:
            second_future.result(timeout=5)
            assert guest_release.public_manifest(public_id)[0] == new
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.restore(world_id=world, subject="owner", release_id=old,
                              expected_version=version + 1)


@pytest.mark.parametrize("first_operation", ["transfer", "promote"])
def test_ownership_transfer_and_promotion_serialize(application_state_dsn, monkeypatch, first_operation):
    world = create_world(name="Ownership promotion race", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"title": "approved copy", "assets": []}, assets=[], **graph)
    original_owner = guest_release._owner
    first_locked, release_first, waiter_entered = Event(), Event(), Event()
    waiter_pid = []

    def owner_check(conn, world_id, subject):
        if first_operation == "transfer" and current_thread().name.startswith("owner-race"):
            waiter_pid.append(conn.info.backend_pid)
            waiter_entered.set()
        result = original_owner(conn, world_id, subject)
        if first_operation == "promote" and current_thread().name.startswith("owner-race"):
            first_locked.set()
            if not release_first.wait(5):
                raise RuntimeError("race test failed to release promotion")
        return result

    monkeypatch.setattr(guest_release, "_owner", owner_check)

    def promote():
        return _promote(world_id=world, subject="owner", release_id=release_id,
                        digest=digest, expected_version=0)

    def transfer():
        with psycopg.connect(application_state_dsn) as conn:
            waiter_pid.append(conn.info.backend_pid)
            waiter_entered.set()
            conn.execute("UPDATE workspace.managed_world SET owner_subject='other' WHERE world_id=%s", (world,))

    def assert_waiting():
        assert waiter_entered.wait(5)
        deadline = monotonic() + 5
        with psycopg.connect(application_state_dsn, autocommit=True) as observer:
            while True:
                row = observer.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s", (waiter_pid[0],)).fetchone()
                if row == ("Lock",):
                    return
                if monotonic() >= deadline:
                    pytest.fail("competing transaction did not wait for a PostgreSQL lock")
                Event().wait(0.02)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="owner-race") as pool:
        if first_operation == "transfer":
            with psycopg.connect(application_state_dsn) as conn:
                conn.execute("UPDATE workspace.managed_world SET owner_subject='other' WHERE world_id=%s", (world,))
                future = pool.submit(promote)
                assert_waiting()
                conn.commit()
            with pytest.raises(ApplicationStateNotFoundError):
                future.result(timeout=5)
            assert guest_release.pointer_status(world_id=world, subject="other") == (None, 0)
        else:
            publication = pool.submit(promote)
            assert first_locked.wait(5)
            transfer_future = pool.submit(transfer)
            try:
                assert_waiting()
            finally:
                release_first.set()
            public_id, version = publication.result(timeout=5)
            transfer_future.result(timeout=5)
            assert guest_release.public_manifest(public_id)[0] == release_id
            assert guest_release.pointer_status(world_id=world, subject="other") == (public_id, version)
            with pytest.raises(ApplicationStateNotFoundError):
                guest_release.restore(world_id=world, subject="other", release_id=release_id, expected_version=version)
            guest_release.revoke(world_id=world, subject="other", release_id=release_id)
            with pytest.raises(ApplicationStateNotFoundError):
                guest_release.public_manifest(public_id)


def test_source_visibility_change_and_restore_invalidates_candidate(application_state_dsn):
    world = create_world(name="Visibility Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="player_safe"))
    document_id = page.page.work_object_id
    committed, revision = commit_page(str(document_id), "safe text", world_id=world,
                              expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    excerpt_id = uuid4()
    with pytest.raises(ApplicationStateConflictError):
        guest_release.stage(world_id=world, subject="owner", expected_owner_generation=generation,
            manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "wrong"}]}, assets=[],
            source_bindings=[(excerpt_id, document_id, 0, 0, revision.revision_n, revision.content_sha256, 0, 4, committed.page.object_revision, "player_safe", "native-evidence")], **graph)
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=generation, manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "safe"}]}, assets=[],
        source_bindings=[(excerpt_id, document_id, 0, 0, revision.revision_n, revision.content_sha256, 0, 4, committed.page.object_revision, "player_safe", "native-evidence")], **graph)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.page_metadata SET visibility_state='internal' WHERE work_object_id=%s", (document_id,))
        conn.execute("UPDATE content.page_metadata SET visibility_state='player_safe' WHERE work_object_id=%s", (document_id,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest=digest, expected_version=0)


def test_graph_rebind_invalidates_candidate(application_state_dsn):
    world = create_world(name="Graph Binding Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    release_id, digest = guest_release.stage(world_id=world, subject="owner", expected_owner_generation=generation,
        manifest={"assets": []}, assets=[], **graph)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.world_native_binding SET binding_version=2 WHERE world_id=%s", (world,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest=digest, expected_version=0)


def test_publication_receipt_recovers_without_reactivating_revoked_release(application_state_dsn):
    world = create_world(name="Receipt Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    generation = guest_release.owner_generation(world_id=world, subject="owner")
    release_id, digest = guest_release.stage(world_id=world, subject="owner", expected_owner_generation=generation,
        manifest={"assets": []}, assets=[], **graph)
    operation_id = uuid4()
    args = dict(world_id=world, subject="owner", release_id=release_id, digest=digest,
                expected_version=0, operation_id=operation_id)
    result = guest_release.commit_validated_promotion(**args, source_epoch=17)
    guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
    assert guest_release.recover_publication(**args) == result
    assert guest_release.commit_validated_promotion(**args, source_epoch=18) == result
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(result[0])
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT source_epoch FROM workspace.guest_release_publication_receipt WHERE operation_id=%s",
                            (operation_id,)).fetchone() == (17,)


def test_source_status_change_and_restore_invalidates_candidate(application_state_dsn):
    world = create_world(name="Status Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="player_safe"))
    committed, revision = commit_page(str(page.page.work_object_id), "safe text", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    excerpt_id = uuid4()
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "safe"}]}, assets=[],
        source_bindings=[(excerpt_id, page.page.work_object_id, 0, 0, revision.revision_n,
                          revision.content_sha256, 0, 4, committed.page.object_revision, "player_safe", "native-evidence")], **graph)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.work_object SET status='discarded' WHERE work_object_id=%s", (page.page.work_object_id,))
        conn.execute("UPDATE content.work_object SET status='active' WHERE work_object_id=%s", (page.page.work_object_id,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest=digest, expected_version=0)


def test_internal_source_can_be_staged_privately_but_visibility_change_invalidates(application_state_dsn):
    world = create_world(name="Private Source Fixture", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Private source", metadata=PageMetadata(visibility_state="internal"))
    committed, revision = commit_page(str(page.page.work_object_id), "selected", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    excerpt_id = uuid4()
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "selected"}]}, assets=[],
        source_bindings=[(excerpt_id, page.page.work_object_id, 0, 0, revision.revision_n,
            revision.content_sha256, 0, 8, committed.page.object_revision, "internal", "native-evidence")], **graph)
    assert guest_release.review(world_id=world, subject="owner", release_id=release_id)[0]["sources"][0]["text"] == "selected"
    assert guest_release.review_source_visibility(world_id=world, subject="owner", release_id=release_id) == {str(excerpt_id): "internal"}
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.page_metadata SET visibility_state='player_safe' WHERE work_object_id=%s", (page.page.work_object_id,))
        conn.execute("UPDATE content.page_metadata SET visibility_state='internal' WHERE work_object_id=%s", (page.page.work_object_id,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id, digest=digest, expected_version=0)


def test_unused_generation_bookkeeping_does_not_prevent_deletion(application_state_dsn):
    world = create_world(name="Cleanup Fixture", owner_subject="owner").record.world_id
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="player_safe"))
    document_id = page.page.work_object_id
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.work_object SET status='discarded' WHERE work_object_id=%s", (document_id,))
        conn.execute("DELETE FROM content.page_metadata WHERE work_object_id=%s", (document_id,))
        conn.execute("DELETE FROM content.work_object WHERE work_object_id=%s", (document_id,))
        assert conn.execute("SELECT 1 FROM workspace.guest_source_status_generation WHERE work_object_id=%s", (document_id,)).fetchone() is None
        conn.execute("UPDATE workspace.managed_world SET owner_subject='other' WHERE world_id=%s", (world,))
        conn.execute("DELETE FROM workspace.world_native_binding WHERE world_id=%s", (world,))
        conn.execute("DELETE FROM workspace.managed_world WHERE world_id=%s", (world,))
        assert conn.execute("SELECT 1 FROM workspace.guest_world_owner_generation WHERE world_id=%s", (world,)).fetchone() is None


def test_promotion_observes_concurrent_visibility_withdrawal(application_state_dsn):
    world = create_world(name="Concurrent Withdrawal", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="player_safe"))
    committed, revision = commit_page(str(page.page.work_object_id), "safe text", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    excerpt_id = uuid4()
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "safe"}]}, assets=[],
        source_bindings=[(excerpt_id, page.page.work_object_id, 0, 0, revision.revision_n,
                          revision.content_sha256, 0, 4, committed.page.object_revision, "player_safe", "native-evidence")], **graph)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE content.page_metadata SET visibility_state='internal' WHERE work_object_id=%s",
                         (page.page.work_object_id,))
            future = pool.submit(_promote, world_id=world, subject="owner", release_id=release_id,
                                 digest=digest, expected_version=0)
            with pytest.raises(TimeoutError):
                future.result(timeout=0.3)
            conn.commit()
        with pytest.raises(ApplicationStateConflictError):
            future.result(timeout=5)
    assert guest_release.pointer_status(world_id=world, subject="owner") == (None, 0)


def test_author_edits_do_not_change_staged_or_published_excerpt(application_state_dsn):
    world = create_world(name="Immutable Release", owner_subject="owner").record.world_id
    graph = _bind(application_state_dsn, world)
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="player_safe"))
    committed, revision = commit_page(str(page.page.work_object_id), "first safe text", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    excerpt_id = uuid4()
    manifest = {"assets": [], "sources": [{"id": str(excerpt_id), "text": "first"}]}
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=guest_release.owner_generation(world_id=world, subject="owner"),
        manifest=manifest, assets=[], source_bindings=[(excerpt_id, page.page.work_object_id, 0, 0,
            revision.revision_n, revision.content_sha256, 0, 5, committed.page.object_revision, "player_safe", "native-evidence")], **graph)
    updated, _ = commit_page(str(page.page.work_object_id), "second version", world_id=world,
        expected_revision=committed.page.object_revision,
        expected_working_copy_revision=committed_page(str(page.page.work_object_id), world_id=world).working_copy_revision)
    public_id, _ = _promote(world_id=world, subject="owner", release_id=release_id,
                                         digest=digest, expected_version=0)
    commit_page(str(page.page.work_object_id), "third version", world_id=world,
        expected_revision=updated.page.object_revision,
        expected_working_copy_revision=committed_page(str(page.page.work_object_id), world_id=world).working_copy_revision)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
