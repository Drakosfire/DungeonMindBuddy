"""Typed authored-page operations over the shared Content storage owner.

Page authoring and committed-source reads share this owner. No file fallback,
automatic adoption or native source/publication authority is provided here.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content import repository as repo
from application_state.content import service as content
from application_state.content.types import (
    AuthoredPageObject,
    WorkRevision,
    normalize_markdown,
    sha256_utf8,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work
from application_state.world_catalog.service import get_world


class PageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] = "draft"
    visibility_state: Literal["internal", "player_safe"] = "internal"
    connected_page_operation_id: UUID | None = None


class PageState(BaseModel):
    page: AuthoredPageObject
    metadata: PageMetadata


class CommittedPageSnapshot(PageState):
    revision: WorkRevision | None
    working_copy_revision: int | None


class PageSnapshot(PageState):
    committed_revision: WorkRevision | None
    markdown: str
    content_sha256: str
    from_working_copy: bool
    working_copy_revision: int | None


def _dsn() -> str:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    return dsn


def _state(conn, document_id: str, world_id: str, *, lock: bool = False) -> PageState:
    if not world_id or world_id != world_id.strip():
        raise ApplicationStateValidationError("an exact World owner is required")
    ident = content._require_uuid(document_id)
    page = (repo.lock_work_object if lock else repo.get_work_object)(conn, ident)
    if not isinstance(page, AuthoredPageObject) or page.world_id != world_id:
        raise ApplicationStateNotFoundError("authored page not found in selected World")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT document_class,authority_state,visibility_state,connected_page_operation_id "
            "FROM content.page_metadata WHERE work_object_id=%s",
            (ident,),
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("authored page metadata is missing")
    return PageState(page=page, metadata=PageMetadata.model_validate(row))


def get_page(document_id: str, *, world_id: str) -> PageState:
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return _state(conn, document_id, world_id)


def create_page(
    *,
    world_id: str,
    title: str,
    campaign_id: str | None = None,
    metadata: PageMetadata | None = None,
    document_id: str | None = None,
) -> PageState:
    """Allocate one page. Connected intent approval belongs to its operation owner."""
    if not world_id or world_id != world_id.strip() or get_world(world_id) is None:
        raise ApplicationStateNotFoundError(
            "registered World is required for an authored page"
        )
    metadata = PageMetadata.model_validate((metadata or PageMetadata()).model_dump())
    ident = content._require_uuid(document_id) if document_id else uuid4()
    if metadata.connected_page_operation_id is not None and document_id is None:
        raise ApplicationStateValidationError(
            "connected-page reservation requires its allocated document ID"
        )
    now = repo.now_utc()
    page = AuthoredPageObject(
        work_object_id=ident,
        world_id=world_id,
        campaign_id=campaign_id,
        title=content._require_title(title),
        object_revision=1,
        created_at=now,
        updated_at=now,
    )
    try:
        with unit_of_work(_dsn()) as conn:
            repo.insert_work_object(conn, page)
            conn.execute(
                """INSERT INTO content.page_metadata
                (work_object_id,document_class,authority_state,visibility_state,connected_page_operation_id)
                VALUES (%s,%s,%s,%s,%s)""",
                (
                    ident,
                    metadata.document_class,
                    metadata.authority_state,
                    metadata.visibility_state,
                    metadata.connected_page_operation_id,
                ),
            )
            return _state(conn, str(ident), world_id)
    except psycopg.IntegrityError:
        # Only return the original active allocation. Never rewrite a retried
        # page's current title, body or metadata, or allocate another ID.
        if metadata.connected_page_operation_id is not None:
            try:
                existing = get_page(str(ident), world_id=world_id)
            except ApplicationStateNotFoundError:
                existing = None
            if (
                existing is not None
                and existing.page.status == "active"
                and existing.page.campaign_id == campaign_id
                and existing.metadata.connected_page_operation_id
                == metadata.connected_page_operation_id
            ):
                return existing
        raise ApplicationStateConflictError(
            "authored page identity or reservation is already allocated"
        ) from None


def list_pages(
    *, world_id: str, status: Literal["active", "discarded"] | None = "active"
) -> list[PageState]:
    if (
        not world_id
        or world_id != world_id.strip()
        or status not in {None, "active", "discarded"}
    ):
        raise ApplicationStateValidationError(
            "exact World and valid page status are required"
        )
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows = repo.list_work_objects(
            conn, kind="worldbuilding_source", world_id=world_id, status=status
        )
        return [_state(conn, str(row.work_object_id), world_id) for row in rows]


def _editor_snapshot(conn, state: PageState) -> PageSnapshot:
    markdown, digest, working, copy, committed = content._snapshot_body(
        conn, state.page
    )
    return PageSnapshot(
        **state.model_dump(),
        markdown=markdown,
        content_sha256=digest,
        from_working_copy=working,
        working_copy_revision=copy.working_copy_revision if copy else None,
        committed_revision=committed,
    )


def snapshot_page(document_id: str, *, world_id: str) -> PageSnapshot:
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return _editor_snapshot(conn, _state(conn, document_id, world_id))


def _basis_values(
    expected_revision: int, expected_working_copy_revision: int | None
) -> None:
    if type(expected_revision) is not int or expected_revision < 1:
        raise ApplicationStateValidationError("positive page revision is required")
    if expected_working_copy_revision is not None and (
        type(expected_working_copy_revision) is not int
        or expected_working_copy_revision < 1
    ):
        raise ApplicationStateValidationError(
            "positive working-copy revision or null is required"
        )


def _basis(
    conn,
    page: AuthoredPageObject,
    expected_revision: int,
    expected_working_copy_revision: int | None,
) -> None:
    _basis_values(expected_revision, expected_working_copy_revision)
    copy = repo.get_working_copy(conn, page.work_object_id)
    if (
        page.object_revision != expected_revision
        or (copy.working_copy_revision if copy else None)
        != expected_working_copy_revision
    ):
        raise ApplicationStateConflictError("authored page or working copy changed")


def save_draft(
    document_id: str,
    markdown: str,
    *,
    world_id: str,
    expected_revision: int,
    expected_working_copy_revision: int | None,
) -> PageState:
    with unit_of_work(_dsn()) as conn:
        state = _state(conn, document_id, world_id, lock=True)
        _basis(conn, state.page, expected_revision, expected_working_copy_revision)
        content._autosave_in_connection(
            conn,
            document_id,
            markdown,
            kind="worldbuilding_source",
            expected_revision=expected_revision,
        )
        return _state(conn, document_id, world_id)


def commit_page(
    document_id: str,
    markdown: str,
    *,
    world_id: str,
    expected_revision: int,
    expected_working_copy_revision: int | None,
) -> tuple[PageState, WorkRevision]:
    _basis_values(expected_revision, expected_working_copy_revision)
    with unit_of_work(_dsn()) as conn:
        state = _state(conn, document_id, world_id, lock=True)
        copy = repo.get_working_copy(conn, state.page.work_object_id)
        # An identical immediate retry may recover the shared committed result;
        # any intervening draft/metadata change invalidates this basis.
        replay = (
            type(expected_revision) is int
            and state.page.object_revision == expected_revision + 1
            and copy is not None
            and copy.working_copy_revision == (expected_working_copy_revision or 0) + 1
            and copy.base_revision_id == state.page.current_revision_id
            and copy.content_sha256 == sha256_utf8(normalize_markdown(markdown))
        )
        if not replay:
            _basis(conn, state.page, expected_revision, expected_working_copy_revision)
        _page, revision = content._commit_in_connection(
            conn,
            document_id,
            markdown,
            kind="worldbuilding_source",
            expected_revision=expected_revision,
        )
        copy = repo.get_working_copy(conn, state.page.work_object_id)
        if copy is not None and copy.content_sha256 != revision.content_sha256:
            # Saving the already committed text explicitly discards a divergent
            # draft. Reuse the shared draft transaction, retaining body history.
            content._autosave_in_connection(
                conn,
                document_id,
                revision.markdown,
                kind="worldbuilding_source",
                expected_revision=_page.object_revision,
            )
        return _state(conn, document_id, world_id), revision


def update_page(
    document_id: str,
    *,
    world_id: str,
    expected_revision: int,
    title: str | None = None,
    metadata: PageMetadata | None = None,
    status: Literal["active", "discarded"] | None = None,
) -> PageState:
    with unit_of_work(_dsn()) as conn:
        state = _state(conn, document_id, world_id, lock=True)
        if (
            type(expected_revision) is not int
            or state.page.object_revision != expected_revision
        ):
            raise ApplicationStateConflictError("authored page changed")
        updated_meta = (
            state.metadata
            if metadata is None
            else PageMetadata.model_validate(metadata.model_dump())
        )
        if (
            updated_meta.connected_page_operation_id
            != state.metadata.connected_page_operation_id
        ):
            raise ApplicationStateValidationError(
                "connected-page reservation is immutable"
            )
        if status not in {None, "active", "discarded"}:
            raise ApplicationStateValidationError("invalid authored page status")
        updates = {
            "title": content._require_title(title)
            if title is not None
            else state.page.title,
            "status": status or state.page.status,
        }
        if (
            all(getattr(state.page, key) == value for key, value in updates.items())
            and updated_meta == state.metadata
        ):
            return state
        updates.update(object_revision=expected_revision + 1, updated_at=repo.now_utc())
        persisted = repo.update_work_object(
            conn,
            state.page.model_copy(update=updates),
            expected_object_revision=expected_revision,
        )
        if persisted is None:
            raise ApplicationStateConflictError("authored page changed")
        conn.execute(
            "UPDATE content.page_metadata SET document_class=%s,authority_state=%s,visibility_state=%s "
            "WHERE work_object_id=%s",
            (
                updated_meta.document_class,
                updated_meta.authority_state,
                updated_meta.visibility_state,
                state.page.work_object_id,
            ),
        )
        return _state(conn, document_id, world_id)


def read_revision(
    document_id: str, *, world_id: str, revision_n: int, expected_sha256: str
) -> WorkRevision:
    if type(revision_n) is not int or revision_n < 1:
        raise ApplicationStateValidationError(
            "positive saved page revision is required"
        )
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        state = _state(conn, document_id, world_id)
        revision = repo.get_work_revision_by_n(
            conn, state.page.work_object_id, revision_n
        )
        if revision is None:
            raise ApplicationStateNotFoundError("saved page revision not found")
        content._require_revision_owner(state.page, revision)
        if revision.content_sha256 != expected_sha256:
            raise ApplicationStateConflictError("saved page revision digest differs")
        return revision


def find_page(document_id: str) -> PageState | None:
    """Exact opaque-ID dispatch for the workspace API, never Playable admission."""
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        obj = repo.get_work_object(conn, content._require_uuid(document_id))
        if not isinstance(obj, AuthoredPageObject):
            return None
        return _state(conn, document_id, obj.world_id)


def page_inventory(
    *, world_id: str | None = None, campaign_id: str | None = None,
    status: str | None = "active"
) -> list[PageState]:
    """Workspace inventory over the same Page owner; campaign is only a tag."""
    if status not in {None, "active", "discarded"}:
        raise ApplicationStateValidationError("invalid page status")
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        clauses, params = ["w.kind='worldbuilding_source'"], []
        if world_id is not None:
            clauses.append("w.world_id=%s")
            params.append(world_id)
        if campaign_id is not None:
            clauses.append("w.campaign_id=%s")
            params.append(campaign_id)
        if status is not None:
            clauses.append("w.status=%s")
            params.append(status)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT w.*,m.document_class,m.authority_state,m.visibility_state,m.connected_page_operation_id "
                "FROM content.work_object w LEFT JOIN content.page_metadata m ON m.work_object_id=w.work_object_id "
                "WHERE " + " AND ".join(clauses) + " ORDER BY w.updated_at DESC",
                params,
            )
            rows = cur.fetchall()
        result = []
        for row in rows:
            meta = {key: row.pop(key) for key in PageMetadata.model_fields}
            if meta["authority_state"] is None:
                raise ApplicationStateIntegrityError(
                    "authored page metadata is missing"
                )
            result.append(
                PageState(
                    page=AuthoredPageObject.model_validate(row),
                    metadata=PageMetadata.model_validate(meta),
                )
            )
        return result


def _committed_snapshot(conn, state: PageState) -> CommittedPageSnapshot:
    revision = None
    if state.page.current_revision_id is not None:
        revision = repo.get_work_revision(conn, state.page.current_revision_id)
        if revision is None:
            raise ApplicationStateIntegrityError("saved Page revision is missing")
        content._require_revision_owner(state.page, revision)
    copy = repo.get_working_copy(conn, state.page.work_object_id)
    return CommittedPageSnapshot(
        **state.model_dump(),
        revision=revision,
        working_copy_revision=copy.working_copy_revision if copy else None,
    )


def committed_page(document_id: str, *, world_id: str) -> CommittedPageSnapshot:
    """Read saved bytes and current CAS basis coherently, ignoring draft content."""
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return _committed_snapshot(conn, _state(conn, document_id, world_id))


def workspace_page_snapshot(
    document_id: str, *, committed: bool = False
) -> PageSnapshot | CommittedPageSnapshot | None:
    """Opaque-ID workspace dispatch and body projection in one observation."""
    with unit_of_work(_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        obj = repo.get_work_object(conn, content._require_uuid(document_id))
        if not isinstance(obj, AuthoredPageObject):
            return None
        state = _state(conn, document_id, obj.world_id)
        return (
            _committed_snapshot(conn, state)
            if committed
            else _editor_snapshot(conn, state)
        )
