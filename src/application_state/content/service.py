"""Content domain service. Admitted kinds: plan, runbook."""

from __future__ import annotations

from uuid import UUID, uuid4

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content import repository as repo
from application_state.content.types import (
    AdmittedKind,
    CommittedPlayableRevision,
    ContentSnapshot,
    WorkObject,
    WorkRevision,
    WorkingCopy,
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


def _require_uuid(document_id: str) -> UUID:
    try:
        return UUID(document_id.strip())
    except ValueError as exc:
        raise ApplicationStateValidationError(
            "invalid document_id: must be a UUID"
        ) from exc


def _require_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise ApplicationStateValidationError("title is required")
    return cleaned


def _require_kind(obj: WorkObject, kind: AdmittedKind | None) -> WorkObject:
    if kind is not None and obj.kind != kind:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {obj.work_object_id}"
        )
    return obj


def create_work_object(
    *,
    kind: AdmittedKind,
    title: str,
    campaign_id: str | None,
    world_id: str | None = None,
    target_session: int | None = None,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    cleaned_world = world_id.strip() if world_id is not None else None
    cleaned_campaign = campaign_id.strip() if campaign_id is not None else None
    if cleaned_world is not None:
        if not cleaned_world:
            raise ApplicationStateValidationError("world_id is required")
        if cleaned_campaign is not None:
            raise ApplicationStateValidationError(
                "World-owned content cannot also have campaign_id"
            )
        if target_session is not None:
            raise ApplicationStateValidationError(
                "World-owned content cannot have target_session"
            )
    elif not cleaned_campaign:
        raise ApplicationStateValidationError("campaign_id is required")
    work_object_id = _require_uuid(document_id) if document_id else uuid4()
    now = repo.now_utc()
    obj = WorkObject(
        work_object_id=work_object_id,
        kind=kind,
        campaign_id=cleaned_campaign,
        world_id=cleaned_world,
        title=_require_title(title),
        target_session=target_session,
        target_relpath=target_relpath,
        status="active",
        current_revision_id=None,
        object_revision=1,
        created_at=now,
        updated_at=now,
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.insert_work_object(conn, obj)


def create_plan(
    *,
    title: str,
    campaign_id: str | None = None,
    world_id: str | None = None,
    target_session: int | None = None,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    return create_work_object(
        kind="plan",
        title=title,
        campaign_id=campaign_id,
        world_id=world_id,
        target_session=target_session,
        target_relpath=target_relpath,
        document_id=document_id,
    )


def create_world_plan(
    *,
    title: str,
    world_id: str,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    return create_plan(
        title=title,
        campaign_id=None,
        world_id=world_id,
        target_session=None,
        target_relpath=target_relpath,
        document_id=document_id,
    )


def create_world_runbook(
    *,
    title: str,
    world_id: str,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    return create_work_object(
        kind="runbook",
        title=title,
        campaign_id=None,
        world_id=world_id,
        target_session=None,
        target_relpath=target_relpath,
        document_id=document_id,
    )


def create_runbook(
    *,
    title: str,
    campaign_id: str,
    target_session: int | None = None,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    return create_work_object(
        kind="runbook",
        title=title,
        campaign_id=campaign_id,
        target_session=target_session,
        target_relpath=target_relpath,
        document_id=document_id,
    )


def get_content_optional(document_id: str) -> WorkObject | None:
    work_object_id = _require_uuid(document_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.get_work_object(conn, work_object_id)


def get_plan(document_id: str) -> WorkObject:
    found = get_plan_optional(document_id)
    if found is None:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {document_id}"
        )
    return found


def get_plan_optional(document_id: str) -> WorkObject | None:
    found = get_content_optional(document_id)
    if found is None or found.kind != "plan":
        return None
    return found


def get_runbook(document_id: str) -> WorkObject:
    found = get_runbook_optional(document_id)
    if found is None:
        raise ApplicationStateNotFoundError(
            f"workspace document not found: {document_id}"
        )
    return found


def get_runbook_optional(document_id: str) -> WorkObject | None:
    found = get_content_optional(document_id)
    if found is None or found.kind != "runbook":
        return None
    return found


def list_plans(
    *,
    campaign_id: str | None = None,
    world_id: str | None = None,
    status: str | None = "active",
) -> list[WorkObject]:
    if campaign_id is not None and world_id is not None:
        raise ApplicationStateValidationError(
            "campaign_id and world_id are mutually exclusive scopes"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.list_work_objects(
            conn, kind="plan", campaign_id=campaign_id, world_id=world_id, status=status
        )


def list_runbooks(
    *,
    campaign_id: str | None = None,
    status: str | None = "active",
) -> list[WorkObject]:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.list_work_objects(
            conn, kind="runbook", campaign_id=campaign_id, status=status
        )


def snapshot_content(document_id: str) -> ContentSnapshot:
    work_object_id = _require_uuid(document_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.get_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        working = repo.get_working_copy(conn, work_object_id)
        committed = None
        if obj.current_revision_id is not None:
            committed = repo.get_work_revision(conn, obj.current_revision_id)
            if committed is None:
                raise ApplicationStateConflictError(
                    "committed workspace document is missing its WorkRevision"
                )
            _require_revision_owner(obj, committed)
        if working is not None and (
            committed is None or working.content_sha256 != committed.content_sha256
        ):
            return ContentSnapshot(
                work_object=obj,
                markdown=working.markdown,
                content_sha256=working.content_sha256,
                loaded_revision=obj.object_revision,
                from_working_copy=True,
            )
        if committed is not None:
            return ContentSnapshot(
                work_object=obj,
                markdown=committed.markdown,
                content_sha256=committed.content_sha256,
                loaded_revision=obj.object_revision,
                from_working_copy=False,
            )
        empty = sha256_utf8("")
        return ContentSnapshot(
            work_object=obj,
            markdown="",
            content_sha256=empty,
            loaded_revision=obj.object_revision,
            from_working_copy=False,
        )


def snapshot_plan(document_id: str) -> ContentSnapshot:
    snap = snapshot_content(document_id)
    _require_kind(snap.work_object, "plan")
    return snap


def snapshot_runbook(document_id: str) -> ContentSnapshot:
    snap = snapshot_content(document_id)
    _require_kind(snap.work_object, "runbook")
    return snap


def _require_kind_for_mutation(obj: WorkObject, kind: AdmittedKind) -> WorkObject:
    if obj.kind != kind:
        raise ApplicationStateValidationError(
            f"workspace document kind mismatch: expected {kind}, current {obj.kind}"
        )
    return obj


def _require_world_plan_scope(obj: WorkObject, world_id: str | None) -> WorkObject:
    """Recheck the exact immutable World owner inside a Content transaction."""
    if world_id is None:
        return obj
    if (
        obj.kind != "plan"
        or obj.world_id != world_id
        or obj.campaign_id is not None
        or obj.target_session is not None
    ):
        raise ApplicationStateConflictError(
            f"workspace document is not owned by selected World {world_id}"
        )
    return obj


def _update_metadata(
    document_id: str,
    *,
    kind: AdmittedKind,
    title: str | None = None,
    target_session: int | None | object = None,
    expected_revision: int | None = None,
    status: str | None = None,
    target_session_set: bool = False,
) -> WorkObject:
    work_object_id = _require_uuid(document_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.lock_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        _require_kind_for_mutation(obj, kind)
        if expected_revision is not None and obj.object_revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {obj.object_revision}"
            )
        expected = obj.object_revision
        updates: dict = {"updated_at": repo.now_utc(), "object_revision": expected + 1}
        if title is not None:
            updates["title"] = _require_title(title)
        if target_session_set:
            updates["target_session"] = target_session
        if status is not None:
            if status not in {"active", "discarded"}:
                raise ApplicationStateValidationError(f"invalid status: {status}")
            updates["status"] = status
        updated = obj.model_copy(update=updates)
        persisted = repo.update_work_object(
            conn, updated, expected_object_revision=expected
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: concurrent {kind} update"
            )
        return persisted


def update_plan_metadata(
    document_id: str,
    *,
    title: str | None = None,
    target_session: int | None | object = None,
    expected_revision: int | None = None,
    status: str | None = None,
    target_session_set: bool = False,
) -> WorkObject:
    return _update_metadata(
        document_id,
        kind="plan",
        title=title,
        target_session=target_session,
        expected_revision=expected_revision,
        status=status,
        target_session_set=target_session_set,
    )


def _autosave(
    document_id: str,
    markdown: str,
    *,
    kind: AdmittedKind,
    expected_revision: int | None = None,
    expected_world_id: str | None = None,
) -> WorkObject:
    work_object_id = _require_uuid(document_id)
    content = normalize_markdown(markdown)
    digest = sha256_utf8(content)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.lock_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        _require_kind_for_mutation(obj, kind)
        _require_world_plan_scope(obj, expected_world_id)
        if obj.status == "discarded":
            raise ApplicationStateConflictError(
                f"workspace document is discarded: {document_id}"
            )
        if expected_revision is not None and obj.object_revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {obj.object_revision}"
            )
        existing = repo.get_working_copy(conn, work_object_id)
        wc_revision = 1 if existing is None else existing.working_copy_revision + 1
        copy = WorkingCopy(
            work_object_id=work_object_id,
            markdown=content,
            content_sha256=digest,
            base_revision_id=obj.current_revision_id,
            working_copy_revision=wc_revision,
            updated_at=repo.now_utc(),
        )
        if existing is None:
            repo.insert_working_copy(conn, copy)
        else:
            persisted_copy = repo.update_working_copy(
                conn,
                copy,
                expected_working_copy_revision=existing.working_copy_revision,
            )
            if persisted_copy is None:
                raise ApplicationStateConflictError(
                    f"working copy revision mismatch: concurrent {kind} autosave"
                )
        expected = obj.object_revision
        updated = obj.model_copy(
            update={
                "object_revision": expected + 1,
                "updated_at": repo.now_utc(),
            }
        )
        persisted = repo.update_work_object(
            conn, updated, expected_object_revision=expected
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: concurrent {kind} autosave"
            )
        return persisted


def autosave_plan(
    document_id: str,
    markdown: str,
    *,
    expected_revision: int | None = None,
    expected_world_id: str | None = None,
) -> WorkObject:
    return _autosave(
        document_id,
        markdown,
        kind="plan",
        expected_revision=expected_revision,
        expected_world_id=expected_world_id,
    )


def _commit(
    document_id: str,
    markdown: str,
    *,
    kind: AdmittedKind,
    expected_revision: int | None = None,
    expected_world_id: str | None = None,
) -> tuple[WorkObject, WorkRevision]:
    work_object_id = _require_uuid(document_id)
    content = normalize_markdown(markdown)
    digest = sha256_utf8(content)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.lock_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        _require_kind_for_mutation(obj, kind)
        _require_world_plan_scope(obj, expected_world_id)
        if obj.status == "discarded":
            raise ApplicationStateConflictError(
                f"workspace document is discarded: {document_id}"
            )
        if expected_revision is not None and obj.object_revision != expected_revision:
            # Identical replay: expected CAS already applied and digest matches
            # the current revision.
            if obj.current_revision_id is not None:
                current = repo.get_work_revision(conn, obj.current_revision_id)
                if current is not None:
                    _require_revision_owner(obj, current)
                if (
                    current is not None
                    and current.content_sha256 == digest
                    and expected_revision == obj.object_revision - 1
                ):
                    return obj, current
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {obj.object_revision}"
            )
        if obj.current_revision_id is not None:
            current = repo.get_work_revision(conn, obj.current_revision_id)
            if current is not None:
                _require_revision_owner(obj, current)
            if current is not None and current.content_sha256 == digest:
                # exact replay at current head
                return obj, current
        revision_n = repo.next_revision_n(conn, work_object_id)
        revision = WorkRevision(
            work_revision_id=uuid4(),
            work_object_id=work_object_id,
            world_id=obj.world_id,
            revision_n=revision_n,
            markdown=content,
            content_sha256=digest,
            created_at=repo.now_utc(),
        )
        repo.insert_work_revision(conn, revision)
        expected = obj.object_revision
        updated = obj.model_copy(
            update={
                "current_revision_id": revision.work_revision_id,
                "object_revision": expected + 1,
                "updated_at": repo.now_utc(),
            }
        )
        persisted = repo.update_work_object(
            conn, updated, expected_object_revision=expected
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: concurrent {kind} commit"
            )
        existing_copy = repo.get_working_copy(conn, work_object_id)
        repo.replace_working_copy(
            conn,
            WorkingCopy(
                work_object_id=work_object_id,
                markdown=content,
                content_sha256=digest,
                base_revision_id=revision.work_revision_id,
                working_copy_revision=(
                    1
                    if existing_copy is None
                    else existing_copy.working_copy_revision + 1
                ),
                updated_at=repo.now_utc(),
            ),
        )
        return persisted, revision


def commit_plan(
    document_id: str,
    markdown: str,
    *,
    expected_revision: int | None = None,
    expected_world_id: str | None = None,
) -> tuple[WorkObject, WorkRevision]:
    return _commit(
        document_id,
        markdown,
        kind="plan",
        expected_revision=expected_revision,
        expected_world_id=expected_world_id,
    )


def current_committed_revision(
    document_id: str,
    *,
    kind: AdmittedKind | None = None,
) -> CommittedPlayableRevision:
    work_object_id = _require_uuid(document_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.get_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        _require_kind(obj, kind)
        if obj.current_revision_id is None:
            raise ApplicationStateConflictError(
                "runbook workspace document is not committed"
            )
        committed = repo.get_work_revision(conn, obj.current_revision_id)
        if committed is None:
            raise ApplicationStateConflictError(
                "committed workspace document is missing its WorkRevision"
            )
        _require_revision_owner(obj, committed)
        working = repo.get_working_copy(conn, work_object_id)
        divergent = (
            working is not None and working.content_sha256 != committed.content_sha256
        )
        return CommittedPlayableRevision(
            work_object=obj,
            work_revision=committed,
            has_divergent_working_copy=divergent,
        )


def exact_committed_revision(
    document_id: str,
    revision_n: int,
    *,
    kind: AdmittedKind | None = None,
    expected_sha256: str | None = None,
    expected_world_id: str | None = None,
) -> CommittedPlayableRevision:
    if (
        not isinstance(revision_n, int)
        or isinstance(revision_n, bool)
        or revision_n <= 0
    ):
        raise ApplicationStateValidationError("revision_n must be a positive integer")
    work_object_id = _require_uuid(document_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        obj = repo.get_work_object(conn, work_object_id)
        if obj is None:
            raise ApplicationStateNotFoundError(
                f"workspace document not found: {document_id}"
            )
        _require_kind(obj, kind)
        if obj.kind == "runbook" and obj.world_id is not None and expected_sha256 is None:
            raise ApplicationStateValidationError(
                "expected_sha256 is required for an exact World Runbook revision"
            )
        if expected_world_id is not None:
            expected_world = expected_world_id.strip()
            if not expected_world:
                raise ApplicationStateValidationError("expected_world_id is required")
            if obj.world_id != expected_world:
                raise ApplicationStateConflictError(
                    f"workspace document is not owned by selected World {expected_world}"
                )
        revision = repo.get_work_revision_by_n(conn, work_object_id, revision_n)
        if revision is None:
            raise ApplicationStateNotFoundError(
                "historical revision bytes were never retained"
            )
        _require_revision_owner(obj, revision)
        if expected_sha256 is not None and revision.content_sha256 != expected_sha256:
            raise ApplicationStateConflictError("playable content SHA mismatch")
        working = repo.get_working_copy(conn, work_object_id)
        current = None
        if obj.current_revision_id is not None:
            current = repo.get_work_revision(conn, obj.current_revision_id)
            if current is not None:
                _require_revision_owner(obj, current)
        divergent = False
        if current is not None and working is not None:
            divergent = working.content_sha256 != current.content_sha256
        return CommittedPlayableRevision(
            work_object=obj,
            work_revision=revision,
            has_divergent_working_copy=divergent,
        )


def _require_revision_owner(obj: WorkObject, revision: WorkRevision) -> None:
    if revision.work_object_id != obj.work_object_id:
        raise ApplicationStateIntegrityError(
            "committed revision belongs to a different WorkObject"
        )
    if revision.world_id != obj.world_id:
        raise ApplicationStateIntegrityError(
            "committed revision World owner does not match its WorkObject"
        )
    if sha256_utf8(revision.markdown) != revision.content_sha256:
        raise ApplicationStateIntegrityError(
            "committed revision content SHA does not match its Markdown"
        )


def autosave_runbook(
    document_id: str,
    markdown: str,
    *,
    expected_revision: int | None = None,
) -> WorkObject:
    return _autosave(
        document_id, markdown, kind="runbook", expected_revision=expected_revision
    )


def commit_runbook(
    document_id: str,
    markdown: str,
    *,
    expected_revision: int | None = None,
) -> tuple[WorkObject, WorkRevision]:
    return _commit(
        document_id, markdown, kind="runbook", expected_revision=expected_revision
    )


def update_runbook_metadata(
    document_id: str,
    *,
    title: str | None = None,
    target_session: int | None | object = None,
    expected_revision: int | None = None,
    status: str | None = None,
    target_session_set: bool = False,
) -> WorkObject:
    return _update_metadata(
        document_id,
        kind="runbook",
        title=title,
        target_session=target_session,
        expected_revision=expected_revision,
        status=status,
        target_session_set=target_session_set,
    )
