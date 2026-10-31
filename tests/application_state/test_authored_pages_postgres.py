"""Authored pages share Content storage, never Plan/Runbook/Play admission."""

from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from pydantic import ValidationError

from application_state import cli
from application_state.content import pages, repository, service
from application_state.content.types import WorkObject
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.world_catalog.service import create_world


@pytest.fixture
def world(application_state_dsn):
    return create_world(
        name="Page owner", owner_subject="subject:owner"
    ).record.world_id


def ident(state):
    return str(state.page.work_object_id)


def test_page_draft_save_history_and_database_only_reads(world, tmp_path):
    metadata = pages.PageMetadata(
        document_class="place",
        authority_state="reviewed",
        visibility_state="player_safe",
    )
    page = pages.create_page(
        world_id=world, title="An editable place", metadata=metadata
    )
    empty = pages.snapshot_page(ident(page), world_id=world)
    assert empty.markdown == "" and empty.working_copy_revision is None
    drafted = pages.save_draft(
        ident(page),
        "First\r\nbody\r",
        world_id=world,
        expected_revision=page.page.object_revision,
        expected_working_copy_revision=None,
    )
    draft = pages.snapshot_page(ident(page), world_id=world)
    assert draft.from_working_copy and draft.markdown == "First\nbody\n"
    committed, first = pages.commit_page(
        ident(page),
        draft.markdown,
        world_id=world,
        expected_revision=drafted.page.object_revision,
        expected_working_copy_revision=draft.working_copy_revision,
    )
    replay, replay_revision = pages.commit_page(
        ident(page),
        draft.markdown,
        world_id=world,
        expected_revision=drafted.page.object_revision,
        expected_working_copy_revision=draft.working_copy_revision,
    )
    assert replay == committed and replay_revision == first
    assert pages.snapshot_page(ident(page), world_id=world).from_working_copy is False
    mirror = tmp_path / "page.md"
    mirror.write_text("unrelated file contents")
    second, revision = pages.commit_page(
        ident(page),
        "Second body",
        world_id=world,
        expected_revision=committed.page.object_revision,
        expected_working_copy_revision=pages.snapshot_page(
            ident(page), world_id=world
        ).working_copy_revision,
    )
    mirror.unlink()
    assert (
        revision.revision_n == 2 and first.work_revision_id != revision.work_revision_id
    )
    assert (
        pages.read_revision(
            ident(page),
            world_id=world,
            revision_n=1,
            expected_sha256=first.content_sha256,
        )
        == first
    )
    assert pages.snapshot_page(ident(page), world_id=world).markdown == "Second body"
    assert second.metadata == metadata and pages.list_pages(world_id=world) == [second]
    assert second.page.campaign_id is None and second.page.world_id == world
    assert second.page.target_relpath is None


@pytest.mark.parametrize("change", ["draft", "metadata"])
def test_stale_confirm_never_overwrites_new_draft_or_metadata(world, change):
    page = pages.create_page(world_id=world, title="Original")
    draft = pages.save_draft(
        ident(page),
        "draft",
        world_id=world,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    basis = pages.snapshot_page(ident(page), world_id=world)
    if change == "draft":
        pages.save_draft(
            ident(page),
            "newer",
            world_id=world,
            expected_revision=draft.page.object_revision,
            expected_working_copy_revision=basis.working_copy_revision,
        )
    else:
        pages.update_page(
            ident(page),
            world_id=world,
            expected_revision=draft.page.object_revision,
            title="Newer",
        )
    before = pages.snapshot_page(ident(page), world_id=world)
    with pytest.raises(ApplicationStateConflictError):
        pages.commit_page(
            ident(page),
            "draft",
            world_id=world,
            expected_revision=draft.page.object_revision,
            expected_working_copy_revision=basis.working_copy_revision,
        )
    assert pages.snapshot_page(ident(page), world_id=world) == before


def test_working_copy_basis_and_explicit_return_to_saved_text(world):
    page = pages.create_page(world_id=world, title="Editable")
    page, first = pages.commit_page(
        ident(page),
        "saved",
        world_id=world,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    copy = pages.snapshot_page(ident(page), world_id=world)
    page = pages.save_draft(
        ident(page),
        "divergent",
        world_id=world,
        expected_revision=page.page.object_revision,
        expected_working_copy_revision=copy.working_copy_revision,
    )
    current = pages.snapshot_page(ident(page), world_id=world)
    with pytest.raises(ApplicationStateConflictError):
        pages.save_draft(
            ident(page),
            "stale",
            world_id=world,
            expected_revision=page.page.object_revision,
            expected_working_copy_revision=copy.working_copy_revision,
        )
    restored, same = pages.commit_page(
        ident(page),
        "saved",
        world_id=world,
        expected_revision=page.page.object_revision,
        expected_working_copy_revision=current.working_copy_revision,
    )
    assert same == first and restored.page.object_revision > page.page.object_revision
    assert pages.snapshot_page(ident(page), world_id=world).markdown == "saved"
    assert not pages.snapshot_page(ident(page), world_id=world).from_working_copy


def test_world_scope_and_page_lifecycle(world):
    page = pages.create_page(world_id=world, title="Keep")
    other = create_world(name="Other", owner_subject="subject:owner").record.world_id
    for operation in [
        lambda: pages.get_page(ident(page), world_id=other),
        lambda: pages.snapshot_page(ident(page), world_id=other),
        lambda: pages.update_page(
            ident(page), world_id=other, expected_revision=1, title="Wrong"
        ),
    ]:
        with pytest.raises(ApplicationStateNotFoundError):
            operation()
    assert pages.list_pages(world_id=other) == []
    trashed = pages.update_page(
        ident(page), world_id=world, expected_revision=1, status="discarded"
    )
    assert pages.list_pages(world_id=world) == []
    assert pages.list_pages(world_id=world, status="discarded") == [trashed]
    with pytest.raises(ApplicationStateConflictError):
        pages.commit_page(
            ident(page),
            "not allowed",
            world_id=world,
            expected_revision=trashed.page.object_revision,
            expected_working_copy_revision=None,
        )
    restored = pages.update_page(
        ident(page),
        world_id=world,
        expected_revision=trashed.page.object_revision,
        status="active",
    )
    assert restored.page.work_object_id == page.page.work_object_id
    assert (
        pages.update_page(
            ident(page), world_id=world, expected_revision=restored.page.object_revision
        )
        == restored
    )


@pytest.mark.parametrize(
    "reader",
    [
        service.get_content_optional,
        service.get_plan_optional,
        service.get_runbook_optional,
        service.snapshot_content,
        service.snapshot_plan,
        service.snapshot_runbook,
        service.current_committed_revision,
        lambda document_id: service.exact_committed_revision(document_id, 1),
    ],
)
def test_generic_and_playable_readers_reject_pages_terminally(world, reader):
    page = pages.create_page(world_id=world, title="Not a Playable")
    pages.commit_page(
        ident(page),
        "A page",
        world_id=world,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    with pytest.raises(ApplicationStateValidationError, match="page-specific"):
        reader(ident(page))
    with pytest.raises(ValidationError):
        WorkObject.model_validate(page.page.model_dump())


def test_playable_mutators_cannot_write_a_page(world):
    page = pages.create_page(world_id=world, title="Not a Plan")
    for mutate in [
        service.autosave_plan,
        service.autosave_runbook,
        service.commit_plan,
        service.commit_runbook,
    ]:
        with pytest.raises(ApplicationStateValidationError, match="kind mismatch"):
            mutate(ident(page), "wrong", expected_revision=1)
    assert pages.snapshot_page(ident(page), world_id=world).markdown == ""


def test_reservation_replay_preserves_edited_allocation_and_uniqueness(world):
    operation, document = uuid4(), str(uuid4())
    metadata = pages.PageMetadata(connected_page_operation_id=operation)
    page = pages.create_page(
        world_id=world, title="Initial", metadata=metadata, document_id=document
    )
    changed = pages.update_page(
        document, world_id=world, title="Edited by author", expected_revision=1
    )
    assert (
        pages.create_page(
            world_id=world, title="Initial", metadata=metadata, document_id=document
        )
        == changed
    )
    with pytest.raises(ApplicationStateConflictError):
        pages.create_page(
            world_id=world, title="Another", metadata=metadata, document_id=str(uuid4())
        )
    with pytest.raises(ApplicationStateValidationError, match="immutable"):
        pages.update_page(
            document,
            world_id=world,
            expected_revision=changed.page.object_revision,
            metadata=pages.PageMetadata(connected_page_operation_id=uuid4()),
        )
    assert pages.list_pages(world_id=world) == [changed]
    assert ident(page) == document


@pytest.mark.parametrize("same_document", [True, False])
def test_concurrent_reservations_leave_one_complete_allocation(
    world, same_document, application_state_dsn
):
    operation = uuid4()
    document = str(uuid4())
    barrier = Barrier(2)

    def create(_):
        barrier.wait(timeout=10)
        try:
            return pages.create_page(
                world_id=world,
                title="Concurrent",
                metadata=pages.PageMetadata(connected_page_operation_id=operation),
                document_id=document if same_document else str(uuid4()),
            )
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    allocated = pages.list_pages(world_id=world)
    assert len(allocated) == 1
    assert len([result for result in results if result]) == (2 if same_document else 1)
    with psycopg.connect(application_state_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM content.work_object WHERE kind='worldbuilding_source'"
            ).fetchone()[0]
            == 1
        )
        assert (
            conn.execute("SELECT count(*) FROM content.page_metadata").fetchone()[0]
            == 1
        )


def test_missing_metadata_and_tampered_revision_fail_closed(
    world, application_state_dsn
):
    page = pages.create_page(world_id=world, title="Protected")
    page, revision = pages.commit_page(
        ident(page),
        "Retained body",
        world_id=world,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE content.work_revision SET markdown=%s WHERE work_revision_id=%s",
            ("tampered", revision.work_revision_id),
        )
    with pytest.raises(ApplicationStateIntegrityError, match="SHA"):
        pages.snapshot_page(ident(page), world_id=world)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "DELETE FROM content.page_metadata WHERE work_object_id=%s",
            (page.page.work_object_id,),
        )
    with pytest.raises(ApplicationStateIntegrityError, match="metadata"):
        pages.get_page(ident(page), world_id=world)


def test_failed_commit_rolls_back_body_pointer_draft_and_revision(world, monkeypatch):
    page = pages.create_page(world_id=world, title="Atomic")
    before = pages.snapshot_page(ident(page), world_id=world)
    real_update = repository.update_work_object

    def fail_after_revision(*_args, **_kwargs):
        return None

    monkeypatch.setattr(repository, "update_work_object", fail_after_revision)
    with pytest.raises(ApplicationStateConflictError):
        pages.commit_page(
            ident(page),
            "must roll back",
            world_id=world,
            expected_revision=1,
            expected_working_copy_revision=None,
        )
    monkeypatch.setattr(repository, "update_work_object", real_update)
    assert pages.snapshot_page(ident(page), world_id=world) == before
    with pytest.raises(ApplicationStateNotFoundError):
        pages.read_revision(
            ident(page), world_id=world, revision_n=1, expected_sha256="0" * 64
        )


def test_page_schema_is_separate_from_live_adoption_and_requires_forward_recovery(
    world, application_state_dsn
):
    page = pages.create_page(world_id=world, title="No auto adoption")
    with pytest.raises(RuntimeError, match="Authored page storage.*recovery forward"):
        # Exercise this owner's fence; a newer fence stops Alembic first.
        import_module(
            "application_state.migrations.versions.20261031_0101_authored_pages"
        ).downgrade()
    cli.assert_at_head(dsn=application_state_dsn)
    assert pages.get_page(ident(page), world_id=world) == page


@pytest.mark.parametrize(
    "revision,copy_revision", [(True, None), (0, None), (1, True), (1, 0)]
)
def test_invalid_basis_is_not_a_commit_retry(world, revision, copy_revision):
    page = pages.create_page(world_id=world, title="Exact basis")
    with pytest.raises(ApplicationStateValidationError):
        pages.commit_page(
            ident(page),
            "body",
            world_id=world,
            expected_revision=revision,
            expected_working_copy_revision=copy_revision,
        )
    assert pages.get_page(ident(page), world_id=world) == page


def test_concurrent_draft_and_commit_accept_only_one_basis(world):
    page = pages.create_page(world_id=world, title="One authoring basis")
    barrier = Barrier(2)

    def write(commit):
        barrier.wait(timeout=10)
        try:
            if commit:
                pages.commit_page(
                    ident(page),
                    "committed winner",
                    world_id=world,
                    expected_revision=1,
                    expected_working_copy_revision=None,
                )
            else:
                pages.save_draft(
                    ident(page),
                    "draft winner",
                    world_id=world,
                    expected_revision=1,
                    expected_working_copy_revision=None,
                )
            return commit
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, [True, False]))
    winners = [result for result in outcomes if result is not None]
    assert len(winners) == 1
    snapshot = pages.snapshot_page(ident(page), world_id=world)
    assert snapshot.markdown == ("committed winner" if winners[0] else "draft winner")
    assert snapshot.from_working_copy is not winners[0]


def test_unknown_world_and_wrong_saved_digest_do_not_admit_page_data(world):
    with pytest.raises(ApplicationStateNotFoundError):
        pages.create_page(world_id="unknown-world", title="Not allocated")
    assert pages.list_pages(world_id=world) == []
    page = pages.create_page(world_id=world, title="Exact saved source")
    page, revision = pages.commit_page(
        ident(page),
        "saved source",
        world_id=world,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    with pytest.raises(ApplicationStateConflictError):
        pages.read_revision(
            ident(page),
            world_id=world,
            revision_n=revision.revision_n,
            expected_sha256="0" * 64,
        )
    with pytest.raises(ApplicationStateNotFoundError):
        pages.read_revision(
            ident(page),
            world_id="wrong-world",
            revision_n=revision.revision_n,
            expected_sha256=revision.content_sha256,
        )
    assert pages.get_page(ident(page), world_id=world) == page


def test_page_campaign_tag_is_preserved_without_widening_playable_scope(world):
    plain = pages.create_page(world_id=world, title="World page")
    tagged = pages.create_page(
        world_id=world, campaign_id="longmont-c2", title="Campaign context"
    )
    equal_tag = pages.create_page(
        world_id=world, campaign_id=world, title="Unadjudicated equal tag"
    )
    assert plain.page.campaign_id is None
    assert (
        pages.get_page(ident(tagged), world_id=world).page.campaign_id == "longmont-c2"
    )
    assert pages.get_page(ident(equal_tag), world_id=world).page.campaign_id == world
    assert {ident(row) for row in pages.list_pages(world_id=world)} == {
        ident(plain),
        ident(tagged),
        ident(equal_tag),
    }
    with pytest.raises(ValidationError):
        WorkObject.model_validate(tagged.page.model_dump() | {"kind": "plan"})
    assert service.list_plans(world_id=world) == []


@pytest.mark.parametrize("tag", ["", " padded", "padded "])
def test_page_campaign_tag_cannot_be_silently_normalized(world, tag):
    with pytest.raises(ValidationError, match="exact and nonblank"):
        pages.create_page(world_id=world, campaign_id=tag, title="Unchanged tag")
    assert pages.list_pages(world_id=world) == []


def test_connected_page_reservation_cannot_change_campaign_tag(world):
    metadata = pages.PageMetadata(connected_page_operation_id=uuid4())
    page = pages.create_page(
        world_id=world,
        campaign_id="longmont-c2",
        title="Reserved",
        metadata=metadata,
        document_id=str(uuid4()),
    )
    with pytest.raises(ApplicationStateConflictError):
        pages.create_page(
            world_id=world,
            campaign_id="longmont-c1",
            title="Reserved",
            metadata=metadata,
            document_id=ident(page),
        )
    assert pages.get_page(ident(page), world_id=world) == page
