"""Real Content-owner adoption; synthetic files/disposable APP only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
import json
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest

from application_state.content import pages, repository, service
from application_state.content.import_pages import FrozenPage, adopt_pages
from application_state.content.types import AuthoredPageObject, sha256_utf8
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.world_catalog.service import create_world
from scripts import adopt_authored_pages as tool


@pytest.fixture
def world(application_state_dsn):
    return create_world(name="Adopt pages").record.world_id


def seed(world, *, body="Retained body\n", committed=True, **updates):
    page = AuthoredPageObject(
        work_object_id=uuid4(), world_id=world, campaign_id="longmont-c2",
        title="Retained page", object_revision=17,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC), **updates,
    )
    return FrozenPage(page=page,
                      metadata=pages.PageMetadata(document_class="place", authority_state="reviewed",
                                                  connected_page_operation_id=uuid4()),
                      content_status="committed" if committed else "draft", markdown=body,
                      content_sha256=sha256_utf8(body) if body is not None else None)


def count(dsn, table):
    # Only internal literal table names in this test.
    with psycopg.connect(dsn) as conn:
        return conn.execute("SELECT count(*) FROM " + table).fetchone()[0]


def test_atomic_adoption_preserves_identity_scope_cas_timestamps_body(world, application_state_dsn):
    a, b, c = (seed(world), seed(world, body="Uncommitted", committed=False, status="discarded"),
               seed(world, body=None, committed=False))
    batch = [a, b, c]
    assert adopt_pages(batch).status == "would_adopt"
    assert count(application_state_dsn, "content.work_object") == 0
    before = datetime.now(UTC)
    assert adopt_pages(batch, dry_run=False).status == "adopted"
    assert adopt_pages(batch, dry_run=False).status == "already_adopted"
    assert adopt_pages(batch).status == "already_adopted"
    for item in batch:
        ident = str(item.page.work_object_id)
        snapshot = pages.snapshot_page(ident, world_id=world)
        assert snapshot.page.model_copy(update={"current_revision_id": None}) == item.page
        assert snapshot.metadata == item.metadata
        assert snapshot.page.target_relpath is None
        assert snapshot.markdown == (item.markdown or "")
        assert snapshot.page.object_revision == 17
        assert snapshot.page.campaign_id == "longmont-c2"
    revision = pages.read_revision(str(a.page.work_object_id), world_id=world, revision_n=1,
                                   expected_sha256=a.content_sha256)
    assert revision.created_at >= before and revision.created_at != a.page.updated_at
    assert count(application_state_dsn, "content.work_revision") == 1
    assert count(application_state_dsn, "content.working_copy") == 1
    state, saved = pages.commit_page(str(a.page.work_object_id), "New Save", world_id=world,
                                     expected_revision=17, expected_working_copy_revision=None)
    assert state.page.object_revision == 18 and saved.revision_n == 2
    assert pages.read_revision(str(a.page.work_object_id), world_id=world, revision_n=1,
                               expected_sha256=a.content_sha256) == revision
    with pytest.raises(ApplicationStateConflictError):
        adopt_pages(batch, dry_run=False)


def test_matching_world_campaign_tag_is_not_reinterpreted(world):
    original = seed(world)
    original = original.model_copy(update={"page": original.page.model_copy(update={"campaign_id": world})})
    adopt_pages([original], dry_run=False)
    assert pages.get_page(str(original.page.work_object_id), world_id=world).page.campaign_id == world


@pytest.mark.parametrize("variation", ["extra", "missing", "body", "title", "metadata", "status", "campaign"])
def test_replay_compares_complete_inventory_and_all_retained_values(world, variation):
    a, b = seed(world), seed(world)
    adopt_pages([a, b], dry_run=False)
    batch = [a, b]
    if variation == "extra":
        batch.append(seed(world))
    elif variation == "missing":
        batch.pop()
    elif variation == "body":
        batch[0] = a.model_copy(update={"markdown": "changed", "content_sha256": sha256_utf8("changed")})
    elif variation == "metadata":
        batch[0] = a.model_copy(update={"metadata": a.metadata.model_copy(update={"document_class": "lore"})})
    else:
        field = "campaign_id" if variation == "campaign" else variation
        value = {"title": "changed", "status": "discarded", "campaign": world}[variation]
        batch[0] = a.model_copy(update={"page": a.page.model_copy(update={field: value})})
    with pytest.raises(ApplicationStateConflictError):
        adopt_pages(batch, dry_run=False)
    assert pages.snapshot_page(str(a.page.work_object_id), world_id=world).markdown == a.markdown


def test_partial_inventory_and_unrelated_page_both_refuse(world):
    a, b = seed(world), seed(world)
    adopt_pages([a], dry_run=False)
    with pytest.raises(ApplicationStateConflictError):
        adopt_pages([a, b], dry_run=False)
    with pytest.raises(ApplicationStateConflictError):
        adopt_pages([], dry_run=False)


def test_unknown_world_and_foreign_kind_collision_leave_nothing(world, application_state_dsn):
    plan = service.create_plan(title="Existing Plan", campaign_id="longmont-c1")
    a, b = seed(world), seed(world)
    b = b.model_copy(update={"page": b.page.model_copy(update={"work_object_id": plan.work_object_id})})
    for batch in ([a, seed("unknown-world")], [a, b]):
        with pytest.raises((ApplicationStateValidationError, ApplicationStateConflictError)):
            adopt_pages(batch, dry_run=False)
    assert count(application_state_dsn, "content.work_object") == 1
    assert count(application_state_dsn, "content.page_metadata") == 0


def test_mid_batch_failure_rolls_back_all_tables(world, application_state_dsn, monkeypatch):
    insert = repository.insert_work_object
    calls = 0

    def fail_second(conn, obj):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("deliberate second page failure")
        return insert(conn, obj)

    monkeypatch.setattr(repository, "insert_work_object", fail_second)
    with pytest.raises(RuntimeError, match="deliberate"):
        adopt_pages([seed(world), seed(world)], dry_run=False)
    for table in ("content.work_object", "content.work_revision", "content.working_copy", "content.page_metadata"):
        assert count(application_state_dsn, table) == 0


def test_concurrent_imports_serialize_exact_replay(world, application_state_dsn):
    batch = [seed(world)]
    barrier = Barrier(2)

    def run():
        barrier.wait()
        return adopt_pages(batch, dry_run=False).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(results) == ["adopted", "already_adopted"]
    assert count(application_state_dsn, "content.work_revision") == 1


@pytest.mark.parametrize("variation", ["duplicate_id", "duplicate_reservation", "locator", "digest", "revision", "timestamp"])
def test_malformed_frozen_input_fails_before_write(world, application_state_dsn, variation):
    a, b = seed(world), seed(world)
    if variation == "duplicate_id":
        b = a
    elif variation == "duplicate_reservation":
        b = b.model_copy(update={"metadata": a.metadata})
    elif variation == "digest":
        b = b.model_copy(update={"content_sha256": "0" * 64})
    else:
        field, value = {"locator": ("target_relpath", "old.md"), "revision": ("object_revision", 0),
                        "timestamp": ("created_at", datetime(2025, 1, 1))}[variation]
        b = b.model_copy(update={"page": b.page.model_copy(update={field: value})})
    with pytest.raises(ApplicationStateValidationError):
        adopt_pages([a, b], dry_run=False)
    assert count(application_state_dsn, "content.work_object") == 0


def legacy(root, world):
    body = root / "body.md"
    body.write_bytes("Original Ω\r\nbody\r".encode())
    item = seed(world)
    record = dict(schema_version="dmb_workspace_document_record_v1", document_id=str(item.page.work_object_id),
                  title=item.page.title, campaign_id=item.page.campaign_id, world_id=world,
                  target_session=None, kind="worldbuilding_source", target_relpath="body.md",
                  status="active", content_status="committed", connected_page_operation_id=str(item.metadata.connected_page_operation_id),
                  revision=17, created_at=item.page.created_at.isoformat(), updated_at=item.page.updated_at.isoformat(),
                  source_domain="worldbuilding", document_class="place", authority_state="reviewed", visibility_state="internal")
    registry = root / "registry.json"
    registry.write_text(json.dumps({"schema_version": "dmb_workspace_document_registry_v1", "records": [record]}))
    return body, registry, record


def capture(root, capsys):
    manifest = root / "manifest.json"
    assert tool.main(["--root", str(root), "capture", "--registry", "registry.json", "--output", str(manifest)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    return manifest, result["manifest_sha256"]


def test_cli_capture_dryrun_apply_replay_then_file_loss(world, application_state_dsn, tmp_path, capsys):
    body, registry, record = legacy(tmp_path, world)
    original = (body.read_bytes(), registry.read_bytes())
    backup = tmp_path / "historical.backup"
    backup.write_text("Unique old Save; not imported")
    manifest, digest = capture(tmp_path, capsys)
    assert "Original Ω" not in manifest.read_text()  # Metadata/digest-only.
    args = ["--root", str(tmp_path), "adopt", "--manifest", str(manifest), "--expected-sha256", digest]
    assert tool.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "would_adopt"
    assert count(application_state_dsn, "content.work_object") == 0
    assert tool.main([*args, "--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "adopted"
    assert tool.main([*args, "--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "already_adopted"
    assert (body.read_bytes(), registry.read_bytes()) == original
    assert backup.read_text() == "Unique old Save; not imported"
    body.unlink()
    registry.unlink()
    assert pages.snapshot_page(record["document_id"], world_id=world).markdown == "Original Ω\nbody\n"


@pytest.mark.parametrize("change", ["body", "raw_newlines", "registry", "missing", "manifest", "symlink", "directory_symlink", "escape", "invalid_utf8", "duplicate_path", "unknown_field"])
def test_cli_pin_and_shape_failures_leave_database_empty(world, application_state_dsn, tmp_path, capsys, change):
    body, registry, record = legacy(tmp_path, world)
    manifest, digest = capture(tmp_path, capsys)
    if change == "body":
        body.write_text("Different body")
    elif change == "raw_newlines":
        body.write_bytes(body.read_bytes().replace(b"\r", b"\n"))
    elif change == "registry":
        registry.write_text(registry.read_text() + " ")
    elif change == "missing":
        body.unlink()
    elif change == "manifest":
        manifest.write_text(manifest.read_text() + " ")
    elif change == "symlink":
        other = tmp_path / "other.md"
        body.rename(other)
        body.symlink_to(other)
    elif change == "invalid_utf8":
        body.write_bytes(b"\xff")
    else:
        if change == "directory_symlink":
            (tmp_path / "redirect").symlink_to(tmp_path, target_is_directory=True)
            record["target_relpath"] = "redirect/body.md"
        if change == "escape":
            record["target_relpath"] = "../body.md"
        if change == "unknown_field":
            record["unrepresentable_metadata"] = "do not drop silently"
        records = [record]
        if change == "duplicate_path":
            records.append({**record, "document_id": str(uuid4()), "connected_page_operation_id": None})
        registry.write_text(json.dumps({"schema_version": "dmb_workspace_document_registry_v1", "records": records}))
    assert tool.main(["--root", str(tmp_path), "adopt", "--manifest", str(manifest),
                      "--expected-sha256", digest, "--apply"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert count(application_state_dsn, "content.work_object") == 0


def test_absent_draft_and_nonpage_records_are_explicit(world, tmp_path):
    body, registry, record = legacy(tmp_path, world)
    body.unlink()
    record["content_status"] = "draft"
    registry.write_text(json.dumps({"schema_version": "dmb_workspace_document_registry_v1",
                                    "records": [record, {"kind": "plan", "document_id": str(uuid4())}]}))
    manifest, seeds = tool.freeze(tmp_path, "registry.json")
    assert len(seeds) == 1 and seeds[0].markdown is None
    assert manifest["pages"][0]["raw_sha256"] is None


def test_capture_preserves_absent_draft_with_missing_parent_and_protects_its_path(world, tmp_path, capsys):
    body, registry, record = legacy(tmp_path, world)
    body.unlink()
    record.update(content_status="draft", target_relpath="not-created/body.md")
    registry.write_text(json.dumps({"schema_version": "dmb_workspace_document_registry_v1", "records": [record]}))
    manifest, seeds = tool.freeze(tmp_path, "registry.json")
    assert seeds[0].markdown is None and manifest["pages"][0]["raw_sha256"] is None
    (tmp_path / "not-created").mkdir()
    assert tool.main(["--root", str(tmp_path), "capture", "--registry", "registry.json",
                      "--output", str(tmp_path / record["target_relpath"])]) == 1
    assert "cannot replace" in json.loads(capsys.readouterr().out)["error"]
    assert not (tmp_path / record["target_relpath"]).exists()


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_capture_rejects_page_identity_shared_with_skipped_kind(world, application_state_dsn, tmp_path, capsys, kind):
    _, registry, record = legacy(tmp_path, world)
    # Reverse order and a different UUID spelling must both remain collisions.
    registry.write_text(json.dumps({"schema_version": "dmb_workspace_document_registry_v1",
                                    "records": [{"kind": kind, "document_id": record["document_id"].upper()}, record]}))
    output = tmp_path / "manifest.json"
    assert tool.main(["--root", str(tmp_path), "capture", "--registry", "registry.json", "--output", str(output)]) == 1
    assert "duplicate workspace identity" in json.loads(capsys.readouterr().out)["error"]
    assert not output.exists()
    assert count(application_state_dsn, "content.work_object") == 0
