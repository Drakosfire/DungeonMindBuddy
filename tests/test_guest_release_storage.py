"""Database boundary checks for guest release state (no public routes)."""
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from uuid import uuid4

import psycopg
import pytest

from application_state import guest_release
from application_state.content.pages import PageMetadata, commit_page, committed_page, create_page
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
    assert guest_release.pointer_status(world_id=world, subject="owner") == (public_id, version)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    assert guest_release.public_asset(public_id, release_id, asset_id) == ("image/png", b"synthetic")
    guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_asset(public_id, release_id, asset_id)
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.restore(world_id=world, subject="owner", release_id=release_id,
                              expected_version=version + 1)


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
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_asset(public_id, first, asset_id)
    assert guest_release.public_asset(public_id, second, asset_id) == ("image/png", b"second")


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
            source_bindings=[(excerpt_id, document_id, 0, 0, revision.revision_n, revision.content_sha256, 0, 4, committed.page.object_revision)], **graph)
    release_id, digest = guest_release.stage(world_id=world, subject="owner",
        expected_owner_generation=generation, manifest={"assets": [], "sources": [{"id": str(excerpt_id), "text": "safe"}]}, assets=[],
        source_bindings=[(excerpt_id, document_id, 0, 0, revision.revision_n, revision.content_sha256, 0, 4, committed.page.object_revision)], **graph)
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
                          revision.content_sha256, 0, 4, committed.page.object_revision)], **graph)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE content.work_object SET status='discarded' WHERE work_object_id=%s", (page.page.work_object_id,))
        conn.execute("UPDATE content.work_object SET status='active' WHERE work_object_id=%s", (page.page.work_object_id,))
    with pytest.raises(ApplicationStateConflictError):
        _promote(world_id=world, subject="owner", release_id=release_id,
                              digest=digest, expected_version=0)


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
                          revision.content_sha256, 0, 4, committed.page.object_revision)], **graph)
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
            revision.revision_n, revision.content_sha256, 0, 5, committed.page.object_revision)], **graph)
    updated, _ = commit_page(str(page.page.work_object_id), "second version", world_id=world,
        expected_revision=committed.page.object_revision,
        expected_working_copy_revision=committed_page(str(page.page.work_object_id), world_id=world).working_copy_revision)
    public_id, _ = _promote(world_id=world, subject="owner", release_id=release_id,
                                         digest=digest, expected_version=0)
    commit_page(str(page.page.work_object_id), "third version", world_id=world,
        expected_revision=updated.page.object_revision,
        expected_working_copy_revision=committed_page(str(page.page.work_object_id), world_id=world).working_copy_revision)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
