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
    campaign_id: str,
    target_session: int | None = None,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    cleaned_campaign = campaign_id.strip()
    if not cleaned_campaign:
        raise ApplicationStateValidationError("campaign_id is required")
    work_object_id = _require_uuid(document_id) if document_id else uuid4()
    now = repo.now_utc()
    obj = WorkObject(
        work_object_id=work_object_id,
        kind=kind,
        campaign_id=cleaned_campaign,
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
    campaign_id: str,
    target_session: int | None = None,
    target_relpath: str | None = None,
    document_id: str | None = None,
) -> WorkObject:
    return create_work_object(
        kind="plan",
        title=title,
        campaign_id=campaign_id,
        target_session=target_session,
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
        raise ApplicationStateNotFoundError(f"workspace document not found: {document_id}")
    return found


def get_plan_optional(document_id: str) -> WorkObject | None:
    found = get_content_optional(document_id)
    if found is None or found.kind != "plan":
        return None
    return found


def get_runbook(document_id: str) -> WorkObject:
    found = get_runbook_optional(document_id)
    if found is None:
        raise ApplicationStateNotFoundError(f"workspace document not found: {document_id}")
    return found


def get_runbook_optional(document_id: str) -> WorkObject | None:
    found = get_content_optional(document_id)
    if found is None or found.kind != "runbook":
        return None
    return found


def list_plans(
    *,
    campaign_id: str | None = None,
    status: str | None = "active",
) -> list[WorkObject]:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.list_work_objects(
            conn, kind="plan", campaign_id=campaign_id, status=status
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
) -> WorkObject:
    return _autosave(
        document_id, markdown, kind="plan", expected_revision=expected_revision
    )


def _commit(
    document_id: str,
    markdown: str,
    *,
    kind: AdmittedKind,
    expected_revision: int | None = None,
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
        if obj.status == "discarded":
            raise ApplicationStateConflictError(
                f"workspace document is discarded: {document_id}"
            )
        if expected_revision is not None and obj.object_revision != expected_revision:
            # Identical replay: expected CAS already applied and digest matches
            # the current revision.
            if obj.current_revision_id is not None:
                current = repo.get_work_revision(conn, obj.current_revision_id)
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
            if current is not None and current.content_sha256 == digest:
                # exact replay at current head
                return obj, current
        revision_n = repo.next_revision_n(conn, work_object_id)
        revision = WorkRevision(
            work_revision_id=uuid4(),
            work_object_id=work_object_id,
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
) -> tuple[WorkObject, WorkRevision]:
    return _commit(
        document_id, markdown, kind="plan", expected_revision=expected_revision
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
) -> CommittedPlayableRevision:
    if not isinstance(revision_n, int) or isinstance(revision_n, bool) or revision_n <= 0:
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
        revision = repo.get_work_revision_by_n(conn, work_object_id, revision_n)
        if revision is None:
            raise ApplicationStateNotFoundError(
                "historical revision bytes were never retained"
            )
        if expected_sha256 is not None and revision.content_sha256 != expected_sha256:
            raise ApplicationStateConflictError(
                "playable content SHA mismatch"
            )
        working = repo.get_working_copy(conn, work_object_id)
        current = None
        if obj.current_revision_id is not None:
            current = repo.get_work_revision(conn, obj.current_revision_id)
        divergent = False
        if current is not None and working is not None:
            divergent = working.content_sha256 != current.content_sha256
        return CommittedPlayableRevision(
            work_object=obj,
            work_revision=revision,
            has_divergent_working_copy=divergent,
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
