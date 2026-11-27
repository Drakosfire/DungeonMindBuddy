"""Authored pages share Content storage, never Plan/Runbook/Play admission."""

from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from pydantic import ValidationError

from application_state import cli
from application_state.content import page_presentation, pages, repository, service
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.types import WorkObject, sha256_utf8
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.world_catalog.service import create_world
from tests.test_hosted_native_graph_access import hosted, recap_lane  # noqa: F401


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


def test_page_inventory_keyset_preserves_world_scope_and_timestamp_ties(world, application_state_dsn):
    other_world = create_world(name="Other page owner", owner_subject="subject:owner").record.world_id
    metadata = pages.PageMetadata(
        document_class="place", authority_state="draft", visibility_state="internal"
    )
    expected = [
        pages.create_page(world_id=world, title=f"Place {index}", metadata=metadata)
        for index in range(3)
    ]
    pages.create_page(world_id=other_world, title="Outside scope", metadata=metadata)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE content.work_object SET updated_at = '2026-01-01T00:00:00Z' WHERE world_id = %s",
            (world,),
        )

    first = pages.page_inventory(world_id=world, limit=2)
    boundary = first[-1].page
    second = pages.page_inventory(
        world_id=world, limit=2, before=(boundary.updated_at, boundary.work_object_id)
    )

    assert len(first) == 2
    assert [row.page.work_object_id for row in first + second] == sorted(
        (row.page.work_object_id for row in expected), reverse=True
    )
    assert all(row.metadata == metadata for row in first + second)


def test_authored_page_inventory_route_continues_within_world(world):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from apps.live_control_server.routes.workspace_documents import router

    metadata = pages.PageMetadata(
        document_class="place", authority_state="draft", visibility_state="internal"
    )
    older = pages.create_page(world_id=world, title="Older", campaign_id="off-page", metadata=metadata)
    newer = pages.create_page(world_id=world, title="Newer", metadata=metadata)
    other = create_world(name="Other World", owner_subject="subject:owner").record.world_id
    pages.create_page(world_id=other, title="Outside scope", campaign_id="foreign", metadata=metadata)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/live/workspace-documents/pages/inventory"
    params = {"world_id": world, "limit": 1}
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    first = response.json()
    assert [row["document_id"] for row in first["records"]] == [ident(newer)]

    assert first["campaign_tags"] == ["off-page"]

    params["before_updated_at"] = first["next_before_updated_at"]
    assert client.get(url, params=params).status_code == 422
    params["before_document_id"] = first["next_before_document_id"]
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    second = response.json()
    assert [row["document_id"] for row in second["records"]] == [ident(older)]
    assert second["campaign_tags"] is None
    assert second["next_before_document_id"] is None
    assert second["next_before_updated_at"] is None


def test_committed_lore_page_joins_the_owner_transaction(world, application_state_dsn):
    class RollbackProbe(Exception):
        pass

    with pytest.raises(RollbackProbe), psycopg.connect(application_state_dsn) as conn:
        rolled_back, _ = pages.create_committed_lore_page(
            conn, world_id=world, title="Rollback probe", markdown="Uncommitted body",
        )
        raise RollbackProbe
    with pytest.raises(ApplicationStateNotFoundError):
        pages.get_page(ident(rolled_back), world_id=world)

    with psycopg.connect(application_state_dsn) as conn:
        saved, revision = pages.create_committed_lore_page(
            conn, world_id=world, title="Reviewed lore", markdown="Approved body",
        )
    reopened = pages.committed_page(ident(saved), world_id=world)
    assert reopened.page.title == "Reviewed lore"
    assert reopened.metadata.authority_state == "reviewed"
    assert reopened.revision == revision
    assert reopened.revision.markdown == "Approved body"


PLAN_PRESENTATION_WORLD = "world:plan-presentation"
PLAN_PRESENTATION_MARKDOWN = "A lantern marks the entrance.\n\nLeave the stair clear."


def _presentation(markdown, *, first_width=6, identity_only=False):
    bindings = []
    for key, (start, end) in zip(
        ("entrance", "stair"), source_block_spans(markdown), strict=True
    ):
        text = markdown.encode("utf-8")[start:end].decode("utf-8")
        bindings.append(page_presentation.BlockBinding(
            id=key, byte_start=start, byte_end=end, sha256=sha256_utf8(text)
        ))
    items = bindings if identity_only else [page_presentation.Row(
        id="arrival-row",
        slots=[
            page_presentation.Slot(id="entrance-slot", width=first_width, blocks=bindings[:1]),
            page_presentation.Slot(id="exit-slot", width=12 - first_width, blocks=bindings[1:]),
        ],
    )]
    return page_presentation.PagePresentation(
        markdown_sha256=sha256_utf8(markdown), items=items
    )


@pytest.fixture
def plain_plan(application_state_dsn):
    plan = service.create_world_plan(title="Arrival", world_id=PLAN_PRESENTATION_WORLD)
    return service.commit_plan(
        str(plan.work_object_id), PLAN_PRESENTATION_MARKDOWN,
        expected_revision=plan.object_revision, expected_world_id=PLAN_PRESENTATION_WORLD,
    )


def _commit_layout(plan, markdown, layout, *, world_id=PLAN_PRESENTATION_WORLD, title=None):
    return service.commit_plan(
        str(plan.work_object_id), markdown, expected_revision=plan.object_revision,
        expected_world_id=world_id, title=title, page_presentation=layout,
    )


def test_plan_presentation_layout_only_save_and_lost_ack_replay_preserve_exact_revision(plain_plan):
    plain, plain_revision = plain_plan
    document = str(plain.work_object_id)
    assert "page_presentation" not in service.snapshot_plan(document).model_dump()

    layout = _presentation(PLAN_PRESENTATION_MARKDOWN)
    composed, revision = _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, layout, title="Composed arrival")
    assert composed.object_revision == plain.object_revision + 1
    assert revision.revision_n == plain_revision.revision_n + 1
    assert revision.content_sha256 == plain_revision.content_sha256

    assert _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, layout, title="Composed arrival") == (composed, revision)
    with pytest.raises(ApplicationStateConflictError, match="revision mismatch"):
        _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, _presentation(PLAN_PRESENTATION_MARKDOWN, first_width=8),
                       title="Composed arrival")
    with pytest.raises(ApplicationStateConflictError, match="revision mismatch"):
        _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, layout, title="Different title")

    snapshot = service.snapshot_plan(document)
    assert (snapshot.markdown, snapshot.page_presentation) == (PLAN_PRESENTATION_MARKDOWN, layout)
    assert snapshot.loaded_revision == composed.object_revision
    assert not snapshot.from_working_copy


def test_plan_presentation_explicit_prose_edit_and_unwrap_keep_block_identities(plain_plan):
    plain, _ = plain_plan
    composed, _ = _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, _presentation(PLAN_PRESENTATION_MARKDOWN))
    updated_markdown = PLAN_PRESENTATION_MARKDOWN.replace("A lantern", "A blue lantern")
    updated_layout = _presentation(updated_markdown)
    edited, edited_revision = _commit_layout(composed, updated_markdown, updated_layout)
    document = str(edited.work_object_id)
    saved = service.snapshot_plan(document)
    assert (saved.markdown, saved.page_presentation) == (updated_markdown, updated_layout)
    assert [slot.id for slot in saved.page_presentation.items[0].slots] == [
        "entrance-slot", "exit-slot"
    ]
    assert saved.page_presentation.items[0].id == "arrival-row"

    identities = _presentation(updated_markdown, identity_only=True)
    unwrapped, revision = _commit_layout(edited, updated_markdown, identities)
    assert unwrapped.object_revision == edited.object_revision + 1
    assert revision.content_sha256 == edited_revision.content_sha256
    assert [item.id for item in service.snapshot_plan(document).page_presentation.items] == [
        "entrance", "stair"
    ]
    with pytest.raises(ApplicationStateValidationError, match="explicit retained presentation"):
        _commit_layout(unwrapped, updated_markdown, None)
    assert service.snapshot_plan(document).page_presentation == identities


def test_plan_presentation_enrolled_plan_refuses_older_writers_and_foreign_scope(plain_plan, application_state_dsn):
    plain, _ = plain_plan
    layout = _presentation(PLAN_PRESENTATION_MARKDOWN)
    with pytest.raises(ApplicationStateValidationError, match="exact World and revision"):
        service.commit_plan(str(plain.work_object_id), PLAN_PRESENTATION_MARKDOWN, page_presentation=layout)
    composed, _ = _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, layout)
    document = str(composed.work_object_id)
    basis = {"expected_revision": composed.object_revision, "expected_world_id": PLAN_PRESENTATION_WORLD}
    edited_markdown = PLAN_PRESENTATION_MARKDOWN.replace("lantern", "candle")
    original = service.snapshot_plan(document)

    with pytest.raises(ApplicationStateValidationError, match="explicit retained presentation"):
        service.commit_plan(document, edited_markdown, **basis)
    with pytest.raises(ApplicationStateValidationError, match="explicit retained presentation"):
        service.commit_plan(document, edited_markdown, page_presentation=None, **basis)
    with pytest.raises(ApplicationStateValidationError, match="Markdown-only working copy"):
        service.autosave_plan(document, edited_markdown, **basis)
    with pytest.raises(ApplicationStateValidationError, match="explicit retained presentation"):
        with psycopg.connect(application_state_dsn) as conn:
            service.commit_plan_in_connection(conn, document, edited_markdown, **basis)
    with pytest.raises(ApplicationStateConflictError, match="not owned by selected World"):
        _commit_layout(composed, PLAN_PRESENTATION_MARKDOWN, layout, world_id="world:foreign")
    assert service.snapshot_plan(document) == original


def test_plan_presentation_failed_revision_cas_rolls_back_layout_and_markdown(plain_plan, application_state_dsn, monkeypatch):
    plan, revision = plain_plan
    document = str(plan.work_object_id)
    original = service.snapshot_plan(document)
    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(repository, "update_work_object", lambda *args, **kwargs: None)
        with pytest.raises(ApplicationStateConflictError, match="concurrent plan commit"):
            _commit_layout(plan, PLAN_PRESENTATION_MARKDOWN, _presentation(PLAN_PRESENTATION_MARKDOWN))

    assert service.snapshot_plan(document) == original
    with psycopg.connect(application_state_dsn) as conn:
        rows = conn.execute(
            "SELECT r.work_revision_id, p.work_revision_id FROM content.work_revision r "
            "LEFT JOIN content.page_presentation p USING (work_revision_id) "
            "WHERE r.work_object_id = %s",
            (plan.work_object_id,),
        ).fetchall()
    assert rows == [(revision.work_revision_id, None)]


def test_plan_presentation_cold_read_refuses_divergent_markdown_only_draft(plain_plan, application_state_dsn):
    plain, _ = plain_plan
    composed, _ = _commit_layout(plain, PLAN_PRESENTATION_MARKDOWN, _presentation(PLAN_PRESENTATION_MARKDOWN))
    divergent = "A legacy draft with no matching presentation."
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE content.working_copy SET markdown = %s, content_sha256 = %s "
            "WHERE work_object_id = %s",
            (divergent, sha256_utf8(divergent), composed.work_object_id),
        )
    with pytest.raises(ApplicationStateConflictError, match="divergent Markdown-only working copy"):
        service.snapshot_plan(str(composed.work_object_id))


PLAN_MARKDOWN_WRITE = "/api/live/tiptap/markdown-write"


def _plan_presentation_http_body(world_id):
    plan = service.create_world_plan(title="Arrival", world_id=world_id)
    markdown = PLAN_PRESENTATION_MARKDOWN + "\n"
    plan, _ = service.commit_plan(
        str(plan.work_object_id), markdown, expected_world_id=world_id,
        expected_revision=plan.object_revision,
    )
    return {
        "schema_version": "dmb_tiptap_markdown_write_prepare_v2",
        "scope_mode": "world",
        "world_id": world_id,
        "document_id": str(plan.work_object_id),
        "title": plan.title,
        "markdown": markdown,
        "expected_revision": plan.object_revision,
        "page_presentation": _presentation(markdown).model_dump(mode="json"),
    }


def _plan_presentation_http_commit(body, prepared):
    return {
        **body,
        "schema_version": "dmb_tiptap_markdown_write_commit_v2",
        "writer_confirm_token": prepared["writer_confirm_token"],
    }


def test_plan_presentation_http_prepare_commit_replay_and_cold_load(monkeypatch, application_state_dsn):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app

    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    body = _plan_presentation_http_body(PLAN_PRESENTATION_WORLD)
    url = f"/api/live/workspace-documents/{body['document_id']}/snapshot"
    layout = _presentation(body["markdown"])
    competing = {**body, "page_presentation": _presentation(
        body["markdown"], first_width=8).model_dump(mode="json")}
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        original = client.get(url)
        assert original.status_code == 200, original.text
        assert "page_presentation" not in original.json()
        prepared = client.post(f"{PLAN_MARKDOWN_WRITE}/prepare", json=body)
        other = client.post(f"{PLAN_MARKDOWN_WRITE}/prepare", json=competing)
        assert prepared.status_code == other.status_code == 200, (prepared.text, other.text)
        assert prepared.json()["registry_revision"] == body["expected_revision"]
        assert prepared.json()["page_presentation_sha256"] == layout.fingerprint()
        assert client.get(url).json() == original.json()

        commit = _plan_presentation_http_commit(body, prepared.json())
        wrong_revision = {**commit, "expected_revision": body["expected_revision"] + 1}
        assert client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json=wrong_revision).status_code == 409
        changed = {**commit, "page_presentation": competing["page_presentation"]}
        assert client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json=changed).status_code == 409
        saved = client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json=commit)
        assert saved.status_code == 200, saved.text
        assert saved.json()["committed_revision"] == body["expected_revision"] + 1
        assert saved.json()["page_presentation_sha256"] == layout.fingerprint()
        assert saved.json()["normalized_content_sha256"] == original.json()["content_sha256"]
        repeated = client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json=commit)
        assert repeated.status_code == 200 and repeated.json() == saved.json()
        stale = _plan_presentation_http_commit(competing, other.json())
        assert client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json=stale).status_code == 409
        newer = {**body, "expected_revision": saved.json()["committed_revision"]}
        old_writer = {k: v for k, v in newer.items() if k != "page_presentation"}
        assert client.post(f"{PLAN_MARKDOWN_WRITE}/prepare", json=old_writer).status_code == 422
        assert client.post(f"{PLAN_MARKDOWN_WRITE}/prepare",
                           json={**newer, "page_presentation": None}).status_code == 422

    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        read = client.get(url)
        assert read.status_code == 200, read.text
        assert read.json()["loaded_revision"] == saved.json()["committed_revision"]
        assert read.json()["markdown"] == body["markdown"]
        assert read.json()["page_presentation"] == layout.model_dump(mode="json")
        assert read.json()["page_presentation_sha256"] == layout.fingerprint()


def test_plan_presentation_http_preserves_hosted_world_authorization(hosted, monkeypatch, application_state_dsn):
    from fastapi import HTTPException
    from apps.live_control_server.services import hosted_native_graph_access, tiptap_markdown_write

    body = _plan_presentation_http_body("managed")
    document = body["document_id"]
    url = f"/api/live/workspace-documents/{document}/snapshot"
    client = hosted.client
    original = client.request("GET", url).json()
    changed = body["markdown"].replace("A lantern", "A blue lantern")
    layout = _presentation(changed)
    body.update(markdown=changed, page_presentation=layout.model_dump(mode="json"))

    assert client.request("POST", f"{PLAN_MARKDOWN_WRITE}/prepare",
                          json=body, session="other-session").status_code == 403
    assert client.request("POST", f"{PLAN_MARKDOWN_WRITE}/prepare",
                          json={**body, "world_id": "foreign"}).status_code == 403
    prepared = client.request("POST", f"{PLAN_MARKDOWN_WRITE}/prepare", json=body)
    assert prepared.status_code == 200, prepared.text
    commit = _plan_presentation_http_commit(body, prepared.json())
    assert client.request("POST", f"{PLAN_MARKDOWN_WRITE}/commit",
                          json=commit, session="other-session").status_code == 403
    validate_media = tiptap_markdown_write.validate_saved_media_references
    with monkeypatch.context() as patch:
        def changed_owner(*_):
            raise HTTPException(403, detail="World ownership changed")

        def transfer_during_validation(markdown, owner):
            validate_media(markdown, owner)
            patch.setattr(hosted_native_graph_access, "_owned_world", changed_owner)

        patch.setattr(tiptap_markdown_write, "validate_saved_media_references", transfer_during_validation)
        denied = client.request("POST", f"{PLAN_MARKDOWN_WRITE}/commit", json=commit)
        assert denied.status_code == 403, denied.text
    assert client.request("GET", url).json() == original

    saved = client.request("POST", f"{PLAN_MARKDOWN_WRITE}/commit", json=commit)
    assert saved.status_code == 200, saved.text
    read = client.request("GET", url)
    assert read.status_code == 200, read.text
    assert read.json()["markdown"] == changed
    assert read.json()["page_presentation"] == layout.model_dump(mode="json")
    assert read.json()["page_presentation_sha256"] == saved.json()["page_presentation_sha256"] == layout.fingerprint()
    assert client.request("GET", url, session="other-session").status_code == 403


@pytest.fixture
def composed_page(world):
    page = pages.create_page(world_id=world, title="Arrival")
    markdown = PLAN_PRESENTATION_MARKDOWN + "\n"
    saved, _ = pages.commit_page(
        ident(page), markdown, world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None,
        page_presentation=_presentation(markdown),
    )
    return pages.snapshot_page(ident(saved), world_id=world)


def test_page_layout_writer_profile_fences_fresh_legacy_and_preserves_replay(composed_page, monkeypatch):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app

    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    document = ident(composed_page)
    world_id = composed_page.page.world_id
    body = {
        "document_id": document,
        "markdown": composed_page.markdown,
        "expected_revision": composed_page.page.object_revision,
    }
    moved = _presentation(composed_page.markdown, first_width=8)
    protected = {**body, "layout_writer_profile": pages.PAGE_LAYOUT_WRITER_PROFILE,
                 "page_presentation": moved.model_dump(mode="json")}
    prepare, commit = f"{PLAN_MARKDOWN_WRITE}/prepare", f"{PLAN_MARKDOWN_WRITE}/commit"
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        legacy = client.post(prepare, json={**body, "page_presentation": None})
        assert legacy.status_code == 200, legacy.text
        offered = client.post(prepare, json=protected)
        assert offered.status_code == 200, offered.text
        request = {**protected, "writer_confirm_token": offered.json()["writer_confirm_token"]}
        saved = client.post(commit, json=request)
        assert saved.status_code == 200, saved.text
        assert saved.json()["layout_writer_profile"] == pages.PAGE_LAYOUT_WRITER_PROFILE
        assert client.post(commit, json=request).json() == saved.json()
        snapshot = client.get(f"/api/live/workspace-documents/{document}/snapshot")
        assert snapshot.status_code == 200, snapshot.text
        assert snapshot.json()["layout_writer_profile"] == pages.PAGE_LAYOUT_WRITER_PROFILE
        current = pages.snapshot_page(document, world_id=world_id)
        assert current.layout_writer_profile == pages.PAGE_LAYOUT_WRITER_PROFILE
        assert current.presentation == moved and current.markdown == composed_page.markdown
        fresh = {**body, "expected_revision": current.page.object_revision}
        assert client.post(prepare, json=fresh).status_code == 409
        assert client.post(prepare, json={**fresh, "page_presentation": None}).status_code == 409
        assert client.post(commit, json={**fresh, "page_presentation": None,
                           "writer_confirm_token": legacy.json()["writer_confirm_token"]}).status_code == 409
        assert client.post(prepare, json={**fresh, "layout_writer_profile": pages.PAGE_LAYOUT_WRITER_PROFILE,
                           "page_presentation": None}).status_code == 422
        assert pages.snapshot_page(document, world_id=world_id) == current
        identities = _presentation(current.markdown, identity_only=True)
        unwrap = {**fresh, "layout_writer_profile": pages.PAGE_LAYOUT_WRITER_PROFILE,
                  "page_presentation": identities.model_dump(mode="json")}
        offered = client.post(prepare, json=unwrap)
        assert offered.status_code == 200, offered.text
        result = client.post(commit, json={**unwrap, "writer_confirm_token": offered.json()["writer_confirm_token"]})
        assert result.status_code == 200, result.text
        reopened = pages.snapshot_page(document, world_id=world_id)
        assert reopened.presentation == identities
        assert reopened.layout_writer_profile == pages.PAGE_LAYOUT_WRITER_PROFILE
        assert client.post(prepare, json={**fresh, "expected_revision": reopened.page.object_revision,
                           "page_presentation": None}).status_code == 409


def test_page_layout_writer_enrollment_rolls_back_and_legacy_database_write_fails(
    composed_page, application_state_dsn, monkeypatch,
):
    document = ident(composed_page)
    world_id = composed_page.page.world_id
    basis = dict(world_id=world_id, expected_revision=composed_page.page.object_revision,
                 expected_working_copy_revision=composed_page.working_copy_revision)
    moved = _presentation(composed_page.markdown, first_width=8)

    def broken_insert(*args):
        raise RuntimeError("sidecar insert failed")

    with monkeypatch.context() as patch:
        patch.setattr(page_presentation, "insert", broken_insert)
        with pytest.raises(RuntimeError, match="sidecar insert failed"):
            pages.commit_page(document, composed_page.markdown, page_presentation=moved,
                              layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE, **basis)
    assert pages.snapshot_page(document, world_id=world_id) == composed_page
    with pytest.raises(ApplicationStateNotFoundError):
        pages.commit_page(document, composed_page.markdown, page_presentation=moved,
                          layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE,
                          **{**basis, "world_id": "foreign"})
    pages.commit_page(document, composed_page.markdown, page_presentation=moved,
                      layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE, **basis)
    current = pages.snapshot_page(document, world_id=world_id)
    with pytest.raises(ApplicationStateConflictError):
        pages.commit_page(document, composed_page.markdown, page_presentation=composed_page.presentation,
                          layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE, **basis)
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="layout-aware writer"), conn.transaction():
            conn.execute("UPDATE content.work_object SET current_revision_id = %s WHERE work_object_id = %s",
                         (composed_page.committed_revision.work_revision_id, document))
        with pytest.raises(psycopg.errors.CheckViolation, match="layout-aware writer"), conn.transaction():
            conn.execute("UPDATE content.working_copy SET markdown = 'legacy' WHERE work_object_id = %s", (document,))
    assert pages.snapshot_page(document, world_id=world_id) == current


def test_page_v2_empty_paragraph_cold_reopen_and_old_writer_fence(world, monkeypatch):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app

    page = pages.create_page(world_id=world, title='Empty paragraph test')
    markdown = PLAN_PRESENTATION_MARKDOWN + '\n'
    old = _presentation(markdown, identity_only=True)
    items = [old.items[0], page_presentation.EmptyParagraph(id='blank'), *old.items[1:]]
    layout = page_presentation.PagePresentation(
        schema_version='dmb_page_presentation_v2', markdown_sha256=sha256_utf8(markdown), items=items,
    ).checked(markdown)
    with pytest.raises(ApplicationStateValidationError, match='layout-aware writer'):
        pages.commit_page(ident(page), markdown, world_id=world, expected_revision=page.page.object_revision,
                          expected_working_copy_revision=None, page_presentation=layout)
    monkeypatch.setenv('DMB_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_DEPLOYMENT_ENVIRONMENT', 'local')
    with TestClient(create_app(), base_url='http://127.0.0.1', client=('127.0.0.1', 50000)) as client:
        rejected = client.post(f'{PLAN_MARKDOWN_WRITE}/prepare', json={
            'document_id': ident(page), 'markdown': markdown, 'expected_revision': page.page.object_revision,
            'page_presentation': layout.model_dump(mode='json'),
        })
        assert rejected.status_code == 422, rejected.text
    saved, _ = pages.commit_page(
        ident(page), markdown, world_id=world, expected_revision=page.page.object_revision,
        expected_working_copy_revision=None, page_presentation=layout,
        layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE,
    )
    document = ident(saved)
    reopened = pages.snapshot_page(document, world_id=world)
    assert reopened.markdown == markdown
    assert reopened.presentation == layout
    monkeypatch.setenv('DMB_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_DEPLOYMENT_ENVIRONMENT', 'local')
    body = {'document_id': document, 'markdown': markdown, 'expected_revision': reopened.page.object_revision}
    with TestClient(create_app(), base_url='http://127.0.0.1', client=('127.0.0.1', 50000)) as client:
        snapshot = client.get(f'/api/live/workspace-documents/{document}/snapshot')
        assert snapshot.status_code == 200, snapshot.text
        assert snapshot.json()['page_presentation'] == layout.model_dump(mode='json')
        for legacy in (body, {**body, 'page_presentation': None}):
            rejected = client.post(f'{PLAN_MARKDOWN_WRITE}/prepare', json=legacy)
            assert rejected.status_code == 409, rejected.text
    assert pages.snapshot_page(document, world_id=world) == reopened


def test_page_table_break_prepare_commit_reopen_preserves_neighbors(world, monkeypatch):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app

    page = pages.create_page(world_id=world, title="Table breaks")
    source = "| Item | Details |\n| --- | --- |\n| Mine | First<br>Second |\n\nNeighbor remains.\n"
    plain, _ = pages.commit_page(
        ident(page), source, world_id=world, expected_revision=page.page.object_revision,
        expected_working_copy_revision=None,
    )
    initial, _ = pages.commit_page(
        ident(plain), source, world_id=world, expected_revision=plain.page.object_revision,
        expected_working_copy_revision=pages.snapshot_page(ident(plain), world_id=world).working_copy_revision,
        page_presentation=_presentation(source),
    )
    edited = source.replace("Second", "Second edited")
    layout = _presentation(edited)
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    body = {"document_id": ident(initial), "markdown": edited,
            "expected_revision": initial.page.object_revision,
            "layout_writer_profile": pages.PAGE_LAYOUT_WRITER_PROFILE,
            "page_presentation": layout.model_dump(mode="json")}
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        offered = client.post(f"{PLAN_MARKDOWN_WRITE}/prepare", json=body)
        assert offered.status_code == 200, offered.text
        assert offered.json()["writer_confirm_token"], offered.text
        saved = client.post(f"{PLAN_MARKDOWN_WRITE}/commit", json={
            **body, "writer_confirm_token": offered.json()["writer_confirm_token"],
        })
        assert saved.status_code == 200, saved.text
        reopened = client.get(f"/api/live/workspace-documents/{ident(initial)}/snapshot")
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["markdown"] == edited
        assert reopened.json()["page_presentation"] == layout.model_dump(mode="json")
    assert pages.snapshot_page(ident(initial), world_id=world).markdown == edited


@pytest.mark.parametrize("unsafe", ["Before<br>After\n\nNeighbor.\n", "| A |\n| --- |\n| <br onclick='x'> |\n\nNeighbor.\n"])
def test_presentation_still_refuses_unrelated_html(unsafe):
    with pytest.raises(ApplicationStateValidationError, match="unsupported source blocks"):
        _presentation(unsafe, identity_only=True).checked(unsafe)


def test_plan_rejects_page_v2_presentation(plain_plan):
    layout = _presentation(PLAN_PRESENTATION_MARKDOWN, identity_only=True)
    v2 = page_presentation.PagePresentation(
        schema_version='dmb_page_presentation_v2', markdown_sha256=layout.markdown_sha256,
        items=[layout.items[0], page_presentation.EmptyParagraph(id='empty'), *layout.items[1:]],
    )
    with pytest.raises(ApplicationStateValidationError, match='Plan does not support'):
        _commit_layout(plain_plan[0], PLAN_PRESENTATION_MARKDOWN, v2)


def _empty_v2_fixture():
    source = 'First.\n\nSecond.\n'
    raw = source.encode()
    digest = lambda b: sha256(b).hexdigest()
    data = {'schema_version': 'dmb_page_presentation_v2', 'markdown_sha256': digest(raw), 'items': [
        {'kind': 'empty_paragraph', 'id': 'leading'},
        {'kind': 'block', 'id': 'first', 'byte_start': 0, 'byte_end': 8, 'sha256': digest(raw[:8])},
        {'kind': 'empty_paragraph', 'id': 'middle'},
        {'kind': 'block', 'id': 'second', 'byte_start': 8, 'byte_end': len(raw), 'sha256': digest(raw[8:])},
        {'kind': 'empty_paragraph', 'id': 'trailing'},
    ]}
    return source, data


def test_v2_accepts_ordered_empty_blocks_without_changing_source_binding():
    source, data = _empty_v2_fixture()
    result = page_presentation.PagePresentation.model_validate(data).checked(source)
    assert [item.id for item in result.items] == ['leading', 'first', 'middle', 'second', 'trailing']
    with pytest.raises(ApplicationStateValidationError):
        result.checked(source + 'changed')


def test_empty_blocks_require_v2_and_unique_ids():
    source, data = _empty_v2_fixture()
    with pytest.raises(ApplicationStateValidationError):
        page_presentation.PagePresentation.model_validate({**data, 'schema_version': 'dmb_page_presentation_v1'}).checked(source)
    data['items'][-1]['id'] = 'leading'
    with pytest.raises(ApplicationStateValidationError):
        page_presentation.PagePresentation.model_validate(data).checked(source)


def test_old_writers_cannot_remove_or_downgrade_v2():
    source, data = _empty_v2_fixture()
    current = page_presentation.PagePresentation.model_validate(data).checked(source)
    for old_value in (None, page_presentation.UNSET):
        with pytest.raises(ApplicationStateValidationError):
            page_presentation.candidate(old_value, source, current)
    v1 = {**data, 'schema_version': 'dmb_page_presentation_v1', 'items': [item for item in data['items'] if item['kind'] == 'block']}
    with pytest.raises(ApplicationStateValidationError):
        page_presentation.candidate(v1, source, current)


def test_v2_refuses_unknown_and_nested_empty_items():
    source, data = _empty_v2_fixture()
    with pytest.raises(ValidationError):
        page_presentation.PagePresentation.model_validate({**data, 'items': [{'kind': 'empty_paragraph', 'id': 'x', 'text': 'hidden'}]})
    row = {'kind': 'row', 'id': 'r', 'slots': [{'id': 's', 'width': 12, 'blocks': [{'kind': 'empty_paragraph', 'id': 'x'}]}]}
    with pytest.raises(ValidationError):
        page_presentation.PagePresentation.model_validate({**data, 'items': [row]})


def test_v2_allows_empty_body_after_exact_yaml_frontmatter():
    source = '---\ntitle: Test\n---\n'
    payload = {
        'schema_version': 'dmb_page_presentation_v2',
        'markdown_sha256': sha256(source.encode()).hexdigest(),
        'items': [{'kind': 'empty_paragraph', 'id': 'blank'}],
    }
    assert page_presentation.PagePresentation.model_validate(payload).checked(source).items[0].id == 'blank'


def test_existing_schema_upgrade_with_restricted_migration_role(application_state_dsn, monkeypatch):
    from psycopg import sql
    from urllib.parse import urlsplit, urlunsplit
    from application_state.config import APPLICATION_STATE_DSN_ENV

    role = 'buddy_migration_test_' + uuid4().hex[:12]
    expected_head = cli._alembic_head()
    with psycopg.connect(application_state_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD 'synthetic-only'").format(sql.Identifier(role)))
        try:
            assert not admin.execute("SELECT has_database_privilege(%s, current_database(), 'CREATE')", (role,)).fetchone()[0]
            admin.execute(sql.SQL('GRANT USAGE ON SCHEMA application_state TO {}').format(sql.Identifier(role)))
            admin.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON application_state.schema_migrations TO {}').format(sql.Identifier(role)))
            admin.execute("UPDATE application_state.schema_migrations SET version_num = '20261122_0198'")
            parsed = urlsplit(application_state_dsn)
            endpoint = f'{role}:synthetic-only@{parsed.hostname}:{parsed.port}'
            monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, urlunsplit(parsed._replace(netloc=endpoint)))
            assert cli.upgrade_to_head() == (expected_head, expected_head)
        finally:
            admin.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def test_working_copy_revision_projection_excludes_draft_text():
    """The committed read retrieves the CAS number without draft contents."""

    class Cursor:
        def __init__(self, row):
            self.row, self.query, self.params = row, None, None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params):
            self.query, self.params = query, params

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self, row):
            self.cursor_value = Cursor(row)

        def cursor(self, **kwargs):
            return self.cursor_value

    page_id = uuid4()
    for row, expected in ((None, None), ({"working_copy_revision": 7}, 7)):
        connection = Connection(row)
        assert repository.get_working_copy_revision(connection, page_id) == expected
        query = " ".join(connection.cursor_value.query.lower().split())
        assert query == "select working_copy_revision from content.working_copy where work_object_id = %s"
        assert connection.cursor_value.params == (page_id,)


def test_committed_snapshot_projects_revision_and_preserves_stale_draft(world, monkeypatch):
    page = pages.create_page(world_id=world, title="Synthetic committed page")
    with monkeypatch.context() as patch:
        patch.setattr(repository, "get_working_copy", lambda *_: pytest.fail("committed snapshot read full draft"))
        initial = pages.committed_page(ident(page), world_id=world)
    assert initial.revision is None and initial.working_copy_revision is None
    committed, revision = pages.commit_page(
        ident(page), "saved text", world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None,
    )
    editor = pages.snapshot_page(ident(committed), world_id=world)
    with monkeypatch.context() as patch:
        patch.setattr(repository, "get_working_copy", lambda *_: pytest.fail("committed snapshot read full draft"))
        clean = pages.committed_page(ident(committed), world_id=world)
    assert clean.revision == revision and clean.working_copy_revision == editor.working_copy_revision
    drafted = pages.save_draft(
        ident(committed), "first draft", world_id=world,
        expected_revision=committed.page.object_revision, expected_working_copy_revision=clean.working_copy_revision,
    )
    with monkeypatch.context() as patch:
        patch.setattr(repository, "get_working_copy", lambda *_: pytest.fail("committed snapshot read full draft"))
        basis = pages.committed_page(ident(drafted), world_id=world)
    assert basis.revision == revision and basis.working_copy_revision == (clean.working_copy_revision or 0) + 1
    pages.save_draft(
        ident(drafted), "newer draft", world_id=world,
        expected_revision=basis.page.object_revision, expected_working_copy_revision=basis.working_copy_revision,
    )
    with pytest.raises(ApplicationStateConflictError):
        pages.commit_page(
            ident(drafted), "stale overwrite", world_id=world,
            expected_revision=basis.page.object_revision, expected_working_copy_revision=basis.working_copy_revision,
        )
    current = pages.snapshot_page(ident(drafted), world_id=world)
    assert current.markdown == "newer draft" and current.from_working_copy
    assert pages.committed_page(ident(drafted), world_id=world).revision == revision
