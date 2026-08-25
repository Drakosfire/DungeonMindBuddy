"""File-backed opaque workspace document registry for /plan authoring."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
    workspace_document_mutation_lock,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/workspace_documents.json"
REGISTRY_SCHEMA = "dmb_workspace_document_registry_v1"
RECORD_SCHEMA = "dmb_workspace_document_record_v1"

_SAFE_WORLD_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")

_UNSET: Any = object()


def _iso_timestamp(value: object) -> str:
    if isinstance(value, str):
        return value
    from datetime import UTC, datetime

    if isinstance(value, datetime):
        stamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _map_application_state_error(exc: Exception) -> WorkspaceDocumentRegistryError:
    status = int(getattr(exc, "status_code", 500))
    return WorkspaceDocumentRegistryError(str(exc), status_code=status)


def _record_from_work_object(
    obj: object,
    *,
    from_working_copy: bool = False,
) -> WorkspaceDocumentRecord:
    current_revision_id = getattr(obj, "current_revision_id", None)
    if from_working_copy or current_revision_id is None:
        content_status: Literal["draft", "committed"] = "draft"
    else:
        content_status = "committed"
    return WorkspaceDocumentRecord(
        document_id=str(obj.work_object_id),
        title=obj.title,
        campaign_id=obj.campaign_id,
        world_id=getattr(obj, "world_id", None),
        target_session=obj.target_session,
        kind=str(obj.kind),
        target_relpath=obj.target_relpath,
        status=obj.status,
        content_status=content_status,
        revision=int(obj.object_revision),
        created_at=_iso_timestamp(obj.created_at),
        updated_at=_iso_timestamp(obj.updated_at),
    )


def unswitched_workspace_record(
    root: Path, document_id: str
) -> WorkspaceDocumentRecord | None:
    """Return a file-backed worldbuilding record without touching PostgreSQL.

    Leftover ``kind=plan`` and ``kind=runbook`` file rows are not authority after
    the Content switch.
    """
    document, _token = _load_unlocked(root)
    record = _find_record(document, document_id)
    if record is None or record.kind in ("plan", "runbook"):
        return None
    return record


def capture_legacy_runbook_snapshots(root: Path) -> list:
    """Capture leftover file-backed runbook rows + current bytes under predecessor locks.

    Lock order matches the file-backed writer: ``workspace_document_mutation_lock``
    first, then the registry file lock. Import consumes this snapshot and never
    re-reads the target file.
    """
    from application_state.content.import_runbooks import freeze_legacy_runbook
    from application_state.content.types import normalize_markdown

    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        leftover_ids = [
            r.document_id
            for r in _load_unlocked(root)[0].records
            if r.kind == "runbook"
        ]
    snapshots = []
    for document_id in leftover_ids:
        with workspace_document_mutation_lock(root, document_id):
            with registry_mutation_lock(path):
                record = next(
                    (
                        r
                        for r in _load_unlocked(root)[0].records
                        if r.document_id == document_id and r.kind == "runbook"
                    ),
                    None,
                )
                if record is None:
                    continue
                markdown = None
                if record.target_relpath:
                    target = root / record.target_relpath
                    if target.is_file():
                        markdown = normalize_markdown(
                            target.read_text(encoding="utf-8")
                        )
                snapshots.append(freeze_legacy_runbook(record, markdown))
    return snapshots


class WorkspaceDocumentRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkspaceDocumentRecord(BaseModel):
    schema_version: Literal["dmb_workspace_document_record_v1"] = RECORD_SCHEMA
    document_id: str
    title: str
    campaign_id: str
    world_id: str | None = None
    target_session: int | None = None
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    revision: int = 1
    created_at: str
    updated_at: str
    # Worldbuilding-source metadata (null for plan/runbook).
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class WorkspaceDocumentRegistryDocument(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class WorkspaceDocumentsListResponse(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class CreateWorkspaceDocumentRequest(BaseModel):
    title: str
    campaign_id: str
    world_id: str | None = None
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_session: int | None = None
    target_relpath: str | None = None
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class UpdateWorkspaceDocumentMetadataRequest(BaseModel):
    title: str | None = None
    target_session: int | None = None
    target_relpath: str | None = None
    expected_revision: int | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class WorkspaceDocumentRevisionRequest(BaseModel):
    expected_revision: int | None = None


class WorkspaceDocumentSnapshot(BaseModel):
    """Coherent registry record + Markdown bytes for one loaded revision."""

    schema_version: Literal["dmb_workspace_document_snapshot_v1"] = (
        "dmb_workspace_document_snapshot_v1"
    )
    record: WorkspaceDocumentRecord
    markdown: str
    content_sha256: str
    file_fingerprint: str
    file_exists: bool
    loaded_revision: int


class WorkspaceCommittedRevision(BaseModel):
    """Committed WorkRevision for Playable binding. ``revision_n`` is playable_revision."""

    schema_version: Literal["dmb_workspace_committed_revision_v1"] = (
        "dmb_workspace_committed_revision_v1"
    )
    document_id: str
    kind: Literal["plan", "runbook"]
    campaign_id: str
    title: str
    status: Literal["active", "discarded"]
    object_revision: int
    work_revision_id: str
    revision_n: int
    markdown: str
    content_sha256: str
    has_divergent_working_copy: bool = False
    target_relpath: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def workspace_documents_path(root: Path) -> Path:
    return root / DEFAULT_REGISTRY_REL


def _validate_document_id(document_id: str) -> str:
    cleaned = document_id.strip()
    try:
        uuid.UUID(cleaned)
    except ValueError as exc:
        raise WorkspaceDocumentRegistryError(
            "invalid document_id: must be a UUID",
            status_code=422,
        ) from exc
    return cleaned


def _validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise WorkspaceDocumentRegistryError("title is required", status_code=422)
    return cleaned


def _load_unlocked(root: Path) -> tuple[WorkspaceDocumentRegistryDocument, str]:
    path = workspace_documents_path(root)
    token = registry_token(path)
    if not path.is_file():
        return WorkspaceDocumentRegistryDocument(), token
    try:
        document = WorkspaceDocumentRegistryDocument.model_validate(load_json(path))
    except (TypeError, ValueError) as exc:
        raise WorkspaceDocumentRegistryError(
            f"malformed workspace document registry: {exc}",
            status_code=500,
        ) from exc
    return document, token


def _load_registry_document(root: Path) -> WorkspaceDocumentRegistryDocument:
    document, _token = _load_unlocked(root)
    return document


def _save_cas(
    root: Path,
    document: WorkspaceDocumentRegistryDocument,
    *,
    expected_token: str,
) -> Path:
    path = workspace_documents_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = registry_token(path)
    if current != expected_token:
        raise WorkspaceDocumentRegistryError(
            "workspace document registry changed concurrently",
            status_code=409,
        )
    try:
        write_json(path, document.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as exc:
        raise WorkspaceDocumentRegistryError(
            f"failed to persist workspace document registry: {exc}",
            status_code=500,
        ) from exc
    return path


def _replace_record(
    document: WorkspaceDocumentRegistryDocument,
    updated: WorkspaceDocumentRecord,
) -> None:
    document.records = [
        updated if r.document_id == updated.document_id else r for r in document.records
    ]


def load_workspace_document_under_registry_lock(
    root: Path,
    document_id: str,
) -> WorkspaceDocumentRecord:
    """Load one record under the shared registry-file lock.

    Lock order: callers performing an isolated snapshot or mutation must hold
    ``workspace_document_mutation_lock(document_id)`` first, then this acquires
    the registry lock.
    """
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, _token = _load_unlocked(root)
        record = _find_record(document, document_id)
        if record is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        return record


def _find_record(
    document: WorkspaceDocumentRegistryDocument, document_id: str
) -> WorkspaceDocumentRecord | None:
    cleaned = _validate_document_id(document_id)
    return next((r for r in document.records if r.document_id == cleaned), None)


def _check_expected_revision(
    record: WorkspaceDocumentRecord, expected_revision: int | None
) -> None:
    if expected_revision is not None and record.revision != expected_revision:
        raise WorkspaceDocumentRegistryError(
            f"revision mismatch: expected {expected_revision}, current {record.revision}",
            status_code=409,
        )


def list_workspace_documents(
    root: Path,
    *,
    campaign_id: str | None = None,
    kind: Literal["plan", "runbook", "worldbuilding_source"] | None = None,
    status: Literal["active", "discarded"] | None = "active",
) -> list[WorkspaceDocumentRecord]:
    records = [
        r for r in _load_registry_document(root).records if r.kind not in ("plan", "runbook")
    ]
    if kind in (None, "plan", "runbook"):
        from application_state.content.service import list_plans, list_runbooks
        from application_state.errors import (
            ApplicationStateError,
            ApplicationStateMigrationError,
            ApplicationStateUnavailableError,
        )

        try:
            if kind in (None, "plan"):
                records.extend(
                    _record_from_work_object(obj)
                    for obj in list_plans(campaign_id=campaign_id, status=status)
                )
            if kind in (None, "runbook"):
                records.extend(
                    _record_from_work_object(obj)
                    for obj in list_runbooks(campaign_id=campaign_id, status=status)
                )
        except (ApplicationStateUnavailableError, ApplicationStateMigrationError) as exc:
            raise _map_application_state_error(exc) from exc
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
    if status is not None:
        records = [r for r in records if r.status == status]
    if campaign_id is not None:
        records = [r for r in records if r.campaign_id == campaign_id]
    if kind is not None:
        records = [r for r in records if r.kind == kind]
    records.sort(key=lambda row: row.updated_at, reverse=True)
    return records


def _worldbuilding_target_relpath(document_id: str) -> str:
    return f"out/workspace/worldbuilding/{document_id}.md"


def _validate_world_id(world_id: str) -> str:
    cleaned = world_id.strip()
    if not cleaned or not _SAFE_WORLD_ID_RE.fullmatch(cleaned):
        raise WorkspaceDocumentRegistryError(
            "world_id must match ^[a-z][a-z0-9_-]{0,62}$",
            status_code=422,
        )
    return cleaned


def _world_markdown_root_relpath(world_id: str) -> str:
    return f"corpus/{world_id}-markdown"


def _worldbuilding_world_scoped_target_relpath(world_id: str, document_id: str) -> str:
    return (
        f"{_world_markdown_root_relpath(world_id)}"
        f"/_dungeonbuddy/sources/{document_id}/source.md"
    )


def _require_existing_world_markdown_root(root: Path, world_id: str) -> None:
    world_root = root / _world_markdown_root_relpath(world_id)
    if not world_root.is_dir():
        raise WorkspaceDocumentRegistryError(
            f"world source root is missing: {_world_markdown_root_relpath(world_id)}",
            status_code=422,
        )


def _plan_workspace_target_relpath(document_id: str) -> str:
    return f"out/workspace/plan/{document_id}.md"


def _require_unique_target_relpath(
    document: WorkspaceDocumentRegistryDocument,
    target_relpath: str | None,
    *,
    exclude_document_id: str | None = None,
) -> None:
    """Fail closed when another record already owns a non-null target_relpath.

    Call only while holding the registry mutation lock. Null/empty paths are
    unrestricted. ``exclude_document_id`` lets an update keep or restate its own path.
    """
    if target_relpath is None or target_relpath == "":
        return
    conflict = next(
        (
            existing
            for existing in document.records
            if existing.target_relpath == target_relpath
            and (exclude_document_id is None or existing.document_id != exclude_document_id)
        ),
        None,
    )
    if conflict is not None:
        raise WorkspaceDocumentRegistryError(
            "target_relpath is already owned by another workspace document: "
            f"{conflict.document_id}",
            status_code=409,
        )


def _validate_worldbuilding_metadata(
    *,
    source_domain: Literal["worldbuilding"] | None,
    document_class: str | None,
    authority_state: Literal["draft", "reviewed", "canonical"] | None,
    visibility_state: Literal["internal", "player_safe"] | None,
) -> dict[str, Any]:
    if source_domain != "worldbuilding":
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires source_domain='worldbuilding'",
            status_code=422,
        )
    cleaned_class = (document_class or "").strip()
    if not cleaned_class:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires document_class",
            status_code=422,
        )
    if authority_state is None:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires authority_state",
            status_code=422,
        )
    if visibility_state is None:
        raise WorkspaceDocumentRegistryError(
            "worldbuilding_source requires visibility_state",
            status_code=422,
        )
    return {
        "source_domain": source_domain,
        "document_class": cleaned_class,
        "authority_state": authority_state,
        "visibility_state": visibility_state,
    }


def _content_target_owner(target_relpath: str | None) -> str | None:
    if target_relpath is None or target_relpath == "":
        return None
    from application_state.content.service import list_plans, list_runbooks

    for obj in [*list_plans(status=None), *list_runbooks(status=None)]:
        if obj.target_relpath == target_relpath:
            return str(obj.work_object_id)
    return None


def create_workspace_document(
    root: Path,
    *,
    title: str,
    campaign_id: str,
    kind: Literal["plan", "runbook", "worldbuilding_source"],
    world_id: str | None = None,
    target_session: int | None = None,
    target_relpath: str | None = None,
    source_domain: Literal["worldbuilding"] | None = None,
    document_class: str | None = None,
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None,
    visibility_state: Literal["internal", "player_safe"] | None = None,
) -> WorkspaceDocumentRecord:
    cleaned_title = _validate_title(title)
    cleaned_campaign = campaign_id.strip()
    if not cleaned_campaign:
        raise WorkspaceDocumentRegistryError("campaign_id is required", status_code=422)

    document_id = str(uuid.uuid4())
    worldbuilding_fields: dict[str, Any] = {
        "source_domain": None,
        "document_class": None,
        "authority_state": None,
        "visibility_state": None,
    }
    resolved_target = target_relpath
    resolved_world_id: str | None = None

    if kind == "worldbuilding_source":
        if target_relpath is not None:
            raise WorkspaceDocumentRegistryError(
                "target_relpath is registry-owned for worldbuilding_source",
                status_code=422,
            )
        worldbuilding_fields = _validate_worldbuilding_metadata(
            source_domain=source_domain,
            document_class=document_class,
            authority_state=authority_state,
            visibility_state=visibility_state,
        )
        if world_id is not None and world_id.strip():
            resolved_world_id = _validate_world_id(world_id)
            _require_existing_world_markdown_root(root, resolved_world_id)
            resolved_target = _worldbuilding_world_scoped_target_relpath(
                resolved_world_id,
                document_id,
            )
        else:
            resolved_target = _worldbuilding_target_relpath(document_id)
    else:
        if world_id is not None and world_id.strip():
            raise WorkspaceDocumentRegistryError(
                "world_id is only valid for kind=worldbuilding_source",
                status_code=422,
            )
        if source_domain is not None or document_class is not None or authority_state is not None or visibility_state is not None:
            raise WorkspaceDocumentRegistryError(
                "worldbuilding metadata is only valid for kind=worldbuilding_source",
                status_code=422,
            )
        if kind == "plan":
            if target_relpath is None or target_relpath == "":
                # Product Create New Prep omits path; server owns UUID workspace draft storage.
                # Explicit caller-supplied Plan paths remain for fixtures/compat only.
                resolved_target = _plan_workspace_target_relpath(document_id)
            else:
                # Compatibility create must fail closed before append: illegal explicit
                # paths cannot become active durable records that PATCH cannot repair.
                from apps.live_control_server.services.tiptap_markdown_write import (
                    TiptapMarkdownWriteError,
                    require_legal_plan_target_relpath,
                )

                try:
                    resolved_target = require_legal_plan_target_relpath(
                        document_id, target_relpath
                    )
                except TiptapMarkdownWriteError as exc:
                    raise WorkspaceDocumentRegistryError(
                        str(exc),
                        status_code=422,
                    ) from exc

    now = _utc_now_iso()
    record = WorkspaceDocumentRecord(
        document_id=document_id,
        title=cleaned_title,
        campaign_id=cleaned_campaign,
        world_id=resolved_world_id,
        target_session=target_session,
        kind=kind,
        target_relpath=resolved_target,
        created_at=now,
        updated_at=now,
        **worldbuilding_fields,
    )
    if kind in ("plan", "runbook"):
        from application_state.content.service import create_plan, create_runbook
        from application_state.errors import ApplicationStateError

        create_fn = create_plan if kind == "plan" else create_runbook
        try:
            owner = _content_target_owner(resolved_target)
            if owner is not None:
                raise WorkspaceDocumentRegistryError(
                    "target_relpath is already owned by another workspace document: "
                    f"{owner}",
                    status_code=409,
                )
            obj = create_fn(
                title=cleaned_title,
                campaign_id=cleaned_campaign,
                target_session=target_session,
                target_relpath=resolved_target,
                document_id=document_id,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_work_object(obj)
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        if kind == "worldbuilding_source" and resolved_world_id is not None:
            _require_existing_world_markdown_root(root, resolved_world_id)
        _require_unique_target_relpath(document, resolved_target)
        document.records.append(record)
        _save_cas(root, document, expected_token=token)
    return record


def get_workspace_document(root: Path, document_id: str) -> WorkspaceDocumentRecord:
    file_record = unswitched_workspace_record(root, document_id)
    if file_record is not None:
        return file_record
    from application_state.content.service import snapshot_content
    from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

    try:
        snap = snapshot_content(document_id)
    except ApplicationStateNotFoundError as exc:
        raise WorkspaceDocumentRegistryError(
            f"workspace document not found: {_validate_document_id(document_id)}",
            status_code=404,
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    return _record_from_work_object(
        snap.work_object, from_working_copy=snap.from_working_copy
    )


def get_workspace_document_snapshot(root: Path, document_id: str) -> WorkspaceDocumentSnapshot:
    """Load record + target Markdown as one coherent revision snapshot.

    Holds ``workspace_document_mutation_lock`` across registry-record read, target
    authorization, file-byte read, and digest/fingerprint construction so a concurrent
    commit cannot mix revision N metadata with revision N+1 bytes.

    ``content_status=committed`` with a missing/unreadable target is an integrity
    failure (409), not an empty editor payload.
    """
    file_record = unswitched_workspace_record(root, document_id)
    if file_record is not None:
        with workspace_document_mutation_lock(root, document_id):
            return get_workspace_document_snapshot_unlocked(root, document_id)
    return _postgres_plan_snapshot(document_id)


def _postgres_plan_snapshot(document_id: str) -> WorkspaceDocumentSnapshot:
    from application_state.content.service import snapshot_content
    from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

    try:
        snap = snapshot_content(document_id)
    except ApplicationStateNotFoundError as exc:
        raise WorkspaceDocumentRegistryError(
            f"workspace document not found: {_validate_document_id(document_id)}",
            status_code=404,
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    record = _record_from_work_object(
        snap.work_object, from_working_copy=snap.from_working_copy
    )
    return WorkspaceDocumentSnapshot(
        record=record,
        markdown=snap.markdown,
        content_sha256=snap.content_sha256,
        file_fingerprint="postgres",
        file_exists=False,
        loaded_revision=snap.loaded_revision,
    )


def get_committed_playable_revision(
    document_id: str,
    *,
    revision_n: int | None = None,
    expected_sha256: str | None = None,
    kind: Literal["plan", "runbook"] | None = "runbook",
) -> WorkspaceCommittedRevision:
    from application_state.content.service import (
        current_committed_revision,
        exact_committed_revision,
    )
    from application_state.errors import ApplicationStateError, ApplicationStateNotFoundError

    canonical_id = _validate_document_id(document_id)
    try:
        if revision_n is None:
            committed = current_committed_revision(canonical_id, kind=kind)
        else:
            committed = exact_committed_revision(
                canonical_id,
                revision_n,
                kind=kind,
                expected_sha256=expected_sha256,
            )
    except ApplicationStateNotFoundError as exc:
        raise WorkspaceDocumentRegistryError(str(exc), status_code=404) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    obj = committed.work_object
    revision = committed.work_revision
    return WorkspaceCommittedRevision(
        document_id=str(obj.work_object_id),
        kind=obj.kind,
        campaign_id=obj.campaign_id,
        title=obj.title,
        status=obj.status,
        object_revision=obj.object_revision,
        work_revision_id=str(revision.work_revision_id),
        revision_n=revision.revision_n,
        markdown=revision.markdown,
        content_sha256=revision.content_sha256,
        has_divergent_working_copy=committed.has_divergent_working_copy,
        target_relpath=obj.target_relpath,
    )


def get_workspace_document_snapshot_unlocked(
    root: Path, document_id: str
) -> WorkspaceDocumentSnapshot:
    """Snapshot read for callers that already hold ``workspace_document_mutation_lock``."""
    import hashlib

    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteError,
        authorize_target_for_record,
        resolve_tiptap_markdown_target,
    )

    try:
        record = load_workspace_document_under_registry_lock(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        if exc.status_code != 404:
            raise
        return _postgres_plan_snapshot(document_id)
    if record.kind in ("plan", "runbook"):
        return _postgres_plan_snapshot(document_id)
    if record.target_relpath is None or record.target_relpath == "":
        if record.content_status == "committed":
            raise WorkspaceDocumentRegistryError(
                "committed workspace document has no target_relpath",
                status_code=409,
            )
        empty_digest = hashlib.sha256(b"").hexdigest()
        return WorkspaceDocumentSnapshot(
            record=record,
            markdown="",
            content_sha256=empty_digest,
            file_fingerprint="absent",
            file_exists=False,
            loaded_revision=record.revision,
        )

    try:
        relpath = authorize_target_for_record(record)
        target = resolve_tiptap_markdown_target(root, relpath)
    except TiptapMarkdownWriteError as exc:
        raise WorkspaceDocumentRegistryError(str(exc), status_code=422) from exc

    if not target.is_file():
        if record.content_status == "committed":
            raise WorkspaceDocumentRegistryError(
                "committed workspace target file is missing",
                status_code=409,
            )
        empty_digest = hashlib.sha256(b"").hexdigest()
        return WorkspaceDocumentSnapshot(
            record=record,
            markdown="",
            content_sha256=empty_digest,
            file_fingerprint="absent",
            file_exists=False,
            loaded_revision=record.revision,
        )

    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkspaceDocumentRegistryError(
            f"failed to read workspace target: {exc}",
            status_code=500,
        ) from exc

    # Normalize newlines the same way SourceArtifact packaging does for digests.
    content = raw.replace("\r\n", "\n").replace("\r", "\n")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    stat = target.stat()
    fingerprint = f"present:{stat.st_mtime_ns}:{stat.st_size}"
    return WorkspaceDocumentSnapshot(
        record=record,
        markdown=content,
        content_sha256=digest,
        file_fingerprint=fingerprint,
        file_exists=True,
        loaded_revision=record.revision,
    )


def update_workspace_document_metadata(
    root: Path,
    document_id: str,
    *,
    title: str | object = _UNSET,
    target_session: int | None | object = _UNSET,
    target_relpath: str | None | object = _UNSET,
    document_class: str | None | object = _UNSET,
    authority_state: Literal["draft", "reviewed", "canonical"] | None | object = _UNSET,
    visibility_state: Literal["internal", "player_safe"] | None | object = _UNSET,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    file_record = unswitched_workspace_record(root, document_id)
    if file_record is None:
        from application_state.content.service import get_content_optional
        from application_state.errors import ApplicationStateError

        try:
            existing = get_content_optional(document_id)
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        if existing.kind not in ("plan", "runbook"):
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        if target_relpath is not _UNSET and target_relpath != existing.target_relpath:
            raise WorkspaceDocumentRegistryError(
                "target_relpath cannot be changed via metadata update",
                status_code=422,
            )
        if document_class is not _UNSET or authority_state is not _UNSET or visibility_state is not _UNSET:
            raise WorkspaceDocumentRegistryError(
                "worldbuilding metadata is only valid for kind=worldbuilding_source",
                status_code=422,
            )
        from application_state.content.service import (
            update_plan_metadata,
            update_runbook_metadata,
        )

        update_fn = (
            update_plan_metadata if existing.kind == "plan" else update_runbook_metadata
        )
        try:
            updated = update_fn(
                document_id,
                title=None if title is _UNSET else str(title),
                target_session=None if target_session is _UNSET else target_session,  # type: ignore[arg-type]
                target_session_set=target_session is not _UNSET,
                expected_revision=expected_revision,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_work_object(updated)
    with workspace_document_mutation_lock(root, document_id):
        return _update_workspace_document_metadata_unlocked(
            root,
            document_id,
            title=title,
            target_session=target_session,
            target_relpath=target_relpath,
            document_class=document_class,
            authority_state=authority_state,
            visibility_state=visibility_state,
            expected_revision=expected_revision,
        )


def _update_workspace_document_metadata_unlocked(
    root: Path,
    document_id: str,
    *,
    title: str | object = _UNSET,
    target_session: int | None | object = _UNSET,
    target_relpath: str | None | object = _UNSET,
    document_class: str | None | object = _UNSET,
    authority_state: Literal["draft", "reviewed", "canonical"] | None | object = _UNSET,
    visibility_state: Literal["internal", "player_safe"] | None | object = _UNSET,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updates: dict[str, Any] = {}
        if title is not _UNSET:
            updates["title"] = _validate_title(str(title))
        if target_session is not _UNSET:
            updates["target_session"] = target_session
        if target_relpath is not _UNSET:
            if existing.kind == "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "target_relpath is registry-owned for worldbuilding_source",
                    status_code=422,
                )
            resolved_update_target: str | None
            if target_relpath is None:
                resolved_update_target = None
            elif isinstance(target_relpath, str):
                resolved_update_target = target_relpath
            else:
                raise WorkspaceDocumentRegistryError(
                    "target_relpath must be a string or null",
                    status_code=422,
                )
            if existing.kind == "plan" and resolved_update_target != existing.target_relpath:
                # Generic PATCH must not act as hidden workspace→canonical promotion.
                raise WorkspaceDocumentRegistryError(
                    "plan target_relpath cannot be changed via metadata update",
                    status_code=422,
                )
            _require_unique_target_relpath(
                document,
                resolved_update_target,
                exclude_document_id=existing.document_id,
            )
            updates["target_relpath"] = resolved_update_target
        if document_class is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "document_class is only valid for worldbuilding_source",
                    status_code=422,
                )
            cleaned_class = str(document_class or "").strip()
            if not cleaned_class:
                raise WorkspaceDocumentRegistryError(
                    "document_class must be non-empty",
                    status_code=422,
                )
            updates["document_class"] = cleaned_class
        if authority_state is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "authority_state is only valid for worldbuilding_source",
                    status_code=422,
                )
            if authority_state is None:
                raise WorkspaceDocumentRegistryError(
                    "authority_state is required for worldbuilding_source",
                    status_code=422,
                )
            updates["authority_state"] = authority_state
        if visibility_state is not _UNSET:
            if existing.kind != "worldbuilding_source":
                raise WorkspaceDocumentRegistryError(
                    "visibility_state is only valid for worldbuilding_source",
                    status_code=422,
                )
            if visibility_state is None:
                raise WorkspaceDocumentRegistryError(
                    "visibility_state is required for worldbuilding_source",
                    status_code=422,
                )
            updates["visibility_state"] = visibility_state
        if not updates:
            raise WorkspaceDocumentRegistryError(
                "at least one metadata field is required",
                status_code=422,
            )

        updated = existing.model_copy(
            update={
                **updates,
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated


def discard_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    file_record = unswitched_workspace_record(root, document_id)
    if file_record is None:
        from application_state.content.service import (
            get_content_optional,
            update_plan_metadata,
            update_runbook_metadata,
        )
        from application_state.errors import ApplicationStateError

        try:
            existing = get_content_optional(document_id)
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        if existing is None or existing.kind not in ("plan", "runbook"):
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        update_fn = (
            update_plan_metadata if existing.kind == "plan" else update_runbook_metadata
        )
        try:
            updated = update_fn(
                document_id,
                status="discarded",
                expected_revision=expected_revision,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_work_object(updated)
    with workspace_document_mutation_lock(root, document_id):
        return _set_workspace_document_status_unlocked(
            root,
            document_id,
            status="discarded",
            expected_revision=expected_revision,
        )


def restore_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    file_record = unswitched_workspace_record(root, document_id)
    if file_record is None:
        from application_state.content.service import (
            get_content_optional,
            update_plan_metadata,
            update_runbook_metadata,
        )
        from application_state.errors import ApplicationStateError

        try:
            existing = get_content_optional(document_id)
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        if existing is None or existing.kind not in ("plan", "runbook"):
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        update_fn = (
            update_plan_metadata if existing.kind == "plan" else update_runbook_metadata
        )
        try:
            updated = update_fn(
                document_id,
                status="active",
                expected_revision=expected_revision,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_work_object(updated)
    with workspace_document_mutation_lock(root, document_id):
        return _set_workspace_document_status_unlocked(
            root,
            document_id,
            status="active",
            expected_revision=expected_revision,
        )


def mark_workspace_document_committed_unlocked(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    """Mark committed without acquiring the per-document mutation lock.

    Callers that already hold ``workspace_document_mutation_lock`` (Markdown commit)
    must use this form to avoid deadlock. Still acquires the registry-file lock and CAS.
    Lock order: document lock (caller) → registry lock (here).
    """
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updated = existing.model_copy(
            update={
                "content_status": "committed",
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated


def mark_workspace_document_committed(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    with workspace_document_mutation_lock(root, document_id):
        return mark_workspace_document_committed_unlocked(
            root,
            document_id,
            expected_revision=expected_revision,
        )


def _set_workspace_document_status_unlocked(
    root: Path,
    document_id: str,
    *,
    status: Literal["active", "discarded"],
    expected_revision: int | None,
) -> WorkspaceDocumentRecord:
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = _find_record(document, document_id)
        if existing is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {_validate_document_id(document_id)}",
                status_code=404,
            )
        _check_expected_revision(existing, expected_revision)

        updated = existing.model_copy(
            update={
                "status": status,
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
            }
        )
        _replace_record(document, updated)
        _save_cas(root, document, expected_token=token)
        return updated


def find_duplicate_target_relpath_ownership(
    root: Path,
) -> list[tuple[str, list[WorkspaceDocumentRecord]]]:
    """Read-only scan: non-null target_relpath values owned by more than one record."""
    document = _load_registry_document(root)
    by_path: dict[str, list[WorkspaceDocumentRecord]] = {}
    for record in document.records:
        path = record.target_relpath
        if path is None or path == "":
            continue
        by_path.setdefault(path, []).append(record)
    return sorted(
        ((path, owners) for path, owners in by_path.items() if len(owners) > 1),
        key=lambda item: item[0],
    )


def reinstate_workspace_document_record(
    root: Path,
    record: WorkspaceDocumentRecord,
) -> WorkspaceDocumentRecord:
    """Re-insert a previously removed registry identity under the mutation lock.

    Fails closed when the document_id already exists or a non-null target_relpath
    collides with an existing owner. Used for bounded duplicate-repair restoration
    only — not a general create path.
    """
    cleaned_id = _validate_document_id(record.document_id)
    path = workspace_documents_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        if _find_record(document, cleaned_id) is not None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document already exists: {cleaned_id}",
                status_code=409,
            )
        _require_unique_target_relpath(document, record.target_relpath)
        document.records.append(record)
        _save_cas(root, document, expected_token=token)
        return record


def release_target_relpath_from_discarded_duplicate(
    root: Path,
    *,
    survivor_document_id: str,
    retire_document_id: str,
) -> WorkspaceDocumentRecord:
    """Bounded duplicate repair: keep both identities; only survivor retains the path.

    Preconditions (fail closed otherwise):
    - both records exist
    - they share the same non-null target_relpath
    - retiree is discarded (survivor may be active or discarded)

    Lock order matches ordinary document mutations: retiree document lock → registry lock.
    """
    survivor_id = _validate_document_id(survivor_document_id)
    retire_id = _validate_document_id(retire_document_id)
    if survivor_id == retire_id:
        raise WorkspaceDocumentRegistryError(
            "survivor and retire document ids must differ",
            status_code=422,
        )

    with workspace_document_mutation_lock(root, retire_id):
        path = workspace_documents_path(root)
        with registry_mutation_lock(path):
            document, token = _load_unlocked(root)
            survivor = _find_record(document, survivor_id)
            retire = _find_record(document, retire_id)
            if survivor is None:
                raise WorkspaceDocumentRegistryError(
                    f"workspace document not found: {survivor_id}",
                    status_code=404,
                )
            if retire is None:
                raise WorkspaceDocumentRegistryError(
                    f"workspace document not found: {retire_id}",
                    status_code=404,
                )
            if retire.status != "discarded":
                raise WorkspaceDocumentRegistryError(
                    "retire document must already be discarded before releasing target_relpath",
                    status_code=422,
                )
            shared = survivor.target_relpath
            if shared is None or shared == "":
                raise WorkspaceDocumentRegistryError(
                    "survivor must own a non-null target_relpath",
                    status_code=422,
                )
            if retire.target_relpath != shared:
                raise WorkspaceDocumentRegistryError(
                    "survivor and retire documents do not share the same target_relpath",
                    status_code=422,
                )

            updated = retire.model_copy(
                update={
                    "target_relpath": None,
                    "revision": retire.revision + 1,
                    "updated_at": _utc_now_iso(),
                }
            )
            _replace_record(document, updated)
            _save_cas(root, document, expected_token=token)
            return updated
