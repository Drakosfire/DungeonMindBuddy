"""Workspace API projections over the Content database owner.

Legacy registry path/schema definitions remain for explicit historical Plan
continuity tools. Live Page/Plan/Runbook reads and writes use Content only.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from application_state.content.service import CurrentWorldPlanRead

DEFAULT_REGISTRY_REL = "out/registries/workspace_documents.json"
REGISTRY_SCHEMA = "dmb_workspace_document_registry_v1"
RECORD_SCHEMA = "dmb_workspace_document_record_v1"

_SAFE_WORLD_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")

_UNSET: Any = object()


def _iso_timestamp(value: object) -> str:
    if isinstance(value, str):
        return value

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
) -> WorkspaceDocumentRecordAny:
    current_revision_id = getattr(obj, "current_revision_id", None)
    if from_working_copy or current_revision_id is None:
        content_status: Literal["draft", "committed"] = "draft"
    else:
        content_status = "committed"
    values = dict(
        document_id=str(obj.work_object_id),
        title=obj.title,
        target_session=obj.target_session,
        kind=str(obj.kind),
        target_relpath=obj.target_relpath,
        status=obj.status,
        content_status=content_status,
        revision=int(obj.object_revision),
        created_at=_iso_timestamp(obj.created_at),
        updated_at=_iso_timestamp(obj.updated_at),
    )
    world_id = getattr(obj, "world_id", None)
    campaign_id = getattr(obj, "campaign_id", None)
    if obj.kind == "runbook" and world_id is not None:
        if campaign_id is not None or obj.target_session is not None:
            raise WorkspaceDocumentRegistryError(
                "World-owned Runbooks require an explicit World-only owner",
                status_code=500,
            )
        return WorldOwnedRunbookRecordV2(world_id=world_id, **values)
    if obj.kind == "plan" and world_id is not None and campaign_id is None:
        return WorldOwnedPlanRecordV2(world_id=world_id, **values)
    return WorkspaceDocumentRecord(
        campaign_id=campaign_id,
        world_id=world_id,
        **values,
    )


class WorkspaceDocumentRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkspaceDocumentRecord(BaseModel):
    schema_version: Literal["dmb_workspace_document_record_v1"] = RECORD_SCHEMA
    document_id: str
    title: str
    campaign_id: str | None
    world_id: str | None = None
    target_session: int | None = None
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    connected_page_operation_id: str | None = None
    revision: int = 1
    created_at: str
    updated_at: str
    # Worldbuilding-source metadata (null for plan/runbook).
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None

    @model_validator(mode="after")
    def exact_owner(self):
        if self.kind == "worldbuilding_source":
            if not self.world_id:
                raise ValueError("authored Page requires its World owner")
        elif not self.campaign_id:
            raise ValueError("campaign Plan/Runbook requires its campaign owner")
        return self


class WorldOwnedPlanRecordV2(BaseModel):
    schema_version: Literal["dmb_world_owned_plan_record_v2"] = (
        "dmb_world_owned_plan_record_v2"
    )
    scope_mode: Literal["world"] = "world"
    document_id: str
    title: str
    campaign_id: None = None
    world_id: str
    target_session: None = None
    kind: Literal["plan"] = "plan"
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    revision: int = 1
    created_at: str
    updated_at: str


class WorldOwnedRunbookRecordV2(BaseModel):
    schema_version: Literal["dmb_world_owned_runbook_record_v2"] = (
        "dmb_world_owned_runbook_record_v2"
    )
    scope_mode: Literal["world"] = "world"
    document_id: str
    title: str
    campaign_id: None = None
    world_id: str
    target_session: None = None
    kind: Literal["runbook"] = "runbook"
    target_relpath: str | None = None
    status: Literal["active", "discarded"] = "active"
    content_status: Literal["draft", "committed"] = "draft"
    revision: int = 1
    created_at: str
    updated_at: str


WorkspaceDocumentRecordAny = Annotated[
    Union[
        WorkspaceDocumentRecord,
        WorldOwnedPlanRecordV2,
        WorldOwnedRunbookRecordV2,
    ],
    Field(discriminator="schema_version"),
]


class WorkspaceDocumentRegistryDocument(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class WorkspaceDocumentsListResponse(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorkspaceDocumentRecord] = Field(default_factory=list)


class WorldOwnedPlansResponseV2(BaseModel):
    schema_version: Literal["dmb_workspace_document_registry_v2"] = (
        "dmb_workspace_document_registry_v2"
    )
    scope_mode: Literal["world"] = "world"
    world_id: str
    records: list[WorldOwnedPlanRecordV2] = Field(default_factory=list)


class WorldOwnedRunbooksResponseV2(BaseModel):
    schema_version: Literal["dmb_world_owned_runbooks_list_v2"] = (
        "dmb_world_owned_runbooks_list_v2"
    )
    scope_mode: Literal["world"] = "world"
    world_id: str
    records: list[WorldOwnedRunbookRecordV2] = Field(default_factory=list)


class CreateWorkspaceDocumentRequest(BaseModel):
    title: str
    campaign_id: str | None = None
    world_id: str | None = None
    kind: Literal["plan", "runbook", "worldbuilding_source"]
    target_session: int | None = None
    target_relpath: str | None = None
    source_domain: Literal["worldbuilding"] | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None


class CreateWorldOwnedPlanRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_workspace_document_create_v2"] = (
        "dmb_workspace_document_create_v2"
    )
    scope_mode: Literal["world"] = "world"
    world_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class CreateWorldOwnedRunbookRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_workspace_document_create_v2"] = (
        "dmb_workspace_document_create_v2"
    )
    scope_mode: Literal["world"] = "world"
    world_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


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
    committed_markdown: str | None = None
    committed_content_sha256: str | None = None
    markdown: str
    content_sha256: str
    file_fingerprint: str
    file_exists: bool
    loaded_revision: int


class WorldOwnedPlanSnapshotV2(BaseModel):
    schema_version: Literal["dmb_workspace_document_snapshot_v2"] = (
        "dmb_workspace_document_snapshot_v2"
    )
    record: WorldOwnedPlanRecordV2
    markdown: str
    content_sha256: str
    file_fingerprint: str
    file_exists: bool
    loaded_revision: int


class WorldOwnedRunbookSnapshotV2(BaseModel):
    schema_version: Literal["dmb_workspace_runbook_snapshot_v2"] = (
        "dmb_workspace_runbook_snapshot_v2"
    )
    record: WorldOwnedRunbookRecordV2
    markdown: str
    content_sha256: str
    file_fingerprint: str
    file_exists: bool
    loaded_revision: int


WorkspaceDocumentSnapshotAny = Annotated[
    Union[
        WorkspaceDocumentSnapshot,
        WorldOwnedPlanSnapshotV2,
        WorldOwnedRunbookSnapshotV2,
    ],
    Field(discriminator="schema_version"),
]


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


class WorldOwnedCommittedRevisionV2(BaseModel):
    schema_version: Literal["dmb_workspace_committed_revision_v2"] = (
        "dmb_workspace_committed_revision_v2"
    )
    scope_mode: Literal["world"] = "world"
    world_id: str
    document_id: str
    kind: Literal["plan", "runbook"]
    campaign_id: None = None
    title: str
    status: Literal["active", "discarded"]
    object_revision: int
    work_revision_id: str
    revision_n: int
    markdown: str
    content_sha256: str
    has_divergent_working_copy: bool = False
    target_relpath: str | None = None


WorkspaceCommittedRevisionAny = Annotated[
    Union[WorkspaceCommittedRevision, WorldOwnedCommittedRevisionV2],
    Field(discriminator="schema_version"),
]


def workspace_documents_path(root: Path) -> Path:
    from apps.live_control_server.config import (
        ArtifactDataRootError,
        artifact_data_root,
    )

    try:
        base = artifact_data_root(root)
    except ArtifactDataRootError as exc:
        raise WorkspaceDocumentRegistryError(str(exc), status_code=503) from exc
    path = (base / DEFAULT_REGISTRY_REL).resolve()
    if not path.is_relative_to(base):
        raise WorkspaceDocumentRegistryError(
            "workspace registry escapes artifact repository", status_code=422
        )
    return path


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


def list_workspace_documents(
    root: Path,
    *,
    world_id: str | None = None,
    campaign_id: str | None = None,
    kind: Literal["plan", "runbook", "worldbuilding_source"] | None = None,
    status: Literal["active", "discarded"] | None = "active",
) -> list[WorkspaceDocumentRecord]:
    from application_state.content import pages
    from application_state.content.service import list_plans, list_runbooks
    from application_state.errors import ApplicationStateError

    if world_id is not None and kind != "worldbuilding_source":
        raise WorkspaceDocumentRegistryError(
            "world_id inventory requires kind=worldbuilding_source", status_code=422
        )
    records = []
    try:
        if kind in (None, "worldbuilding_source"):
            records.extend(
                _record_from_page(state)
                for state in pages.page_inventory(
                    world_id=world_id, campaign_id=campaign_id, status=status
                )
            )
        if kind in (None, "plan"):
            records.extend(
                _record_from_work_object(obj)
                for obj in list_plans(campaign_id=campaign_id, status=status)
            )
        if kind in (None, "runbook"):
            records.extend(
                _record_from_work_object(obj)
                for obj in list_runbooks(campaign_id=campaign_id, status=status)
                if obj.world_id is None
            )
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    records.sort(key=lambda row: row.updated_at, reverse=True)
    return records


def _validate_world_id(world_id: str) -> str:
    cleaned = world_id.strip()
    if not cleaned or not _SAFE_WORLD_ID_RE.fullmatch(cleaned):
        raise WorkspaceDocumentRegistryError(
            "world_id must match ^[a-z][a-z0-9_-]{0,62}$",
            status_code=422,
        )
    return cleaned


def _plan_workspace_target_relpath(document_id: str) -> str:
    return f"out/workspace/plan/{document_id}.md"


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
    campaign_id: str | None,
    kind: Literal["plan", "runbook", "worldbuilding_source"],
    world_id: str | None = None,
    target_session: int | None = None,
    target_relpath: str | None = None,
    source_domain: Literal["worldbuilding"] | None = None,
    document_class: str | None = None,
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None,
    visibility_state: Literal["internal", "player_safe"] | None = None,
    _connected_reservation: tuple[str, str] | None = None,
) -> WorkspaceDocumentRecord:
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    cleaned_title = _validate_title(title)
    if kind == "worldbuilding_source":
        if target_relpath is not None or target_session is not None:
            raise WorkspaceDocumentRegistryError(
                "Page storage and session are not caller-assigned", status_code=422
            )
        if not world_id:
            raise WorkspaceDocumentRegistryError(
                "Page requires an explicit World owner", status_code=422
            )
        fields = _validate_worldbuilding_metadata(
            source_domain=source_domain,
            document_class=document_class,
            authority_state=authority_state,
            visibility_state=visibility_state,
        )
        if _connected_reservation is not None and campaign_id != world_id:
            raise WorkspaceDocumentRegistryError(
                "Connected reservation requires a World Build page", status_code=422
            )
        ident, operation_id = (
            _connected_reservation if _connected_reservation else (None, None)
        )
        try:
            state = pages.create_page(
                world_id=_validate_world_id(world_id),
                title=cleaned_title,
                campaign_id=campaign_id,
                document_id=ident,
                metadata=pages.PageMetadata(
                    document_class=fields["document_class"],
                    authority_state=fields["authority_state"],
                    visibility_state=fields["visibility_state"],
                    connected_page_operation_id=operation_id,
                ),
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_page(state)
    if _connected_reservation is not None:
        raise WorkspaceDocumentRegistryError(
            "Connected reservation requires a Page", status_code=422
        )
    if world_id is not None:
        raise WorkspaceDocumentRegistryError(
            "world_id is only valid for kind=worldbuilding_source", status_code=422
        )
    if any(
        value is not None
        for value in (source_domain, document_class, authority_state, visibility_state)
    ):
        raise WorkspaceDocumentRegistryError(
            "worldbuilding metadata is only valid for kind=worldbuilding_source",
            status_code=422,
        )
    cleaned_campaign = (campaign_id or "").strip()
    if not cleaned_campaign:
        raise WorkspaceDocumentRegistryError("campaign_id is required", status_code=422)
    document_id = str(uuid.uuid4())
    resolved_target = target_relpath
    if kind == "plan":
        if not target_relpath:
            resolved_target = _plan_workspace_target_relpath(document_id)
        else:
            from apps.live_control_server.services.tiptap_markdown_write import (
                require_legal_plan_target_relpath,
                TiptapMarkdownWriteError,
            )

            try:
                resolved_target = require_legal_plan_target_relpath(
                    document_id, target_relpath
                )
            except TiptapMarkdownWriteError as exc:
                raise WorkspaceDocumentRegistryError(str(exc), status_code=422) from exc
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


def create_world_owned_plan_v2(
    root: Path, *, world_id: str, title: str
) -> WorldOwnedPlanRecordV2:
    cleaned_world = _validate_world_id(world_id)
    cleaned_title = _validate_title(title)
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
        get_world_container,
    )
    from application_state.content.service import create_world_plan
    from application_state.errors import ApplicationStateError

    try:
        world = get_world_container(root, cleaned_world)
        if world.world_id != cleaned_world:
            raise WorkspaceDocumentRegistryError(
                "selected World identity does not match the managed World record",
                status_code=409,
            )
        document_id = str(uuid.uuid4())
        obj = create_world_plan(
            world_id=cleaned_world,
            title=cleaned_title,
            target_relpath=_plan_workspace_target_relpath(document_id),
            document_id=document_id,
        )
    except WorldContainerRegistryError as exc:
        raise WorkspaceDocumentRegistryError(
            str(exc), status_code=exc.status_code
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    record = _record_from_work_object(obj)
    if not isinstance(record, WorldOwnedPlanRecordV2):
        raise WorkspaceDocumentRegistryError(
            "World-owned Plan creation returned an incompatible Content scope",
            status_code=500,
        )
    return record


def list_world_owned_plans_v2(
    root: Path, *, world_id: str, status: str | None = "active"
) -> WorldOwnedPlansResponseV2:
    cleaned_world = _validate_world_id(world_id)
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
        get_world_container,
    )
    from application_state.content.service import list_plans
    from application_state.errors import ApplicationStateError

    try:
        world = get_world_container(root, cleaned_world)
        if world.world_id != cleaned_world:
            raise WorkspaceDocumentRegistryError(
                "selected World identity does not match the managed World record",
                status_code=409,
            )
        records = [
            _record_from_work_object(obj)
            for obj in list_plans(world_id=cleaned_world, status=status)
        ]
    except WorldContainerRegistryError as exc:
        raise WorkspaceDocumentRegistryError(
            str(exc), status_code=exc.status_code
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    if any(not isinstance(record, WorldOwnedPlanRecordV2) for record in records):
        raise WorkspaceDocumentRegistryError(
            "World Plan inventory returned a non-World-owned document",
            status_code=500,
        )
    return WorldOwnedPlansResponseV2(world_id=cleaned_world, records=records)


def create_world_owned_runbook_v2(
    root: Path, *, world_id: str, title: str
) -> WorldOwnedRunbookRecordV2:
    cleaned_world = _validate_world_id(world_id)
    cleaned_title = _validate_title(title)
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
        get_world_container,
    )
    from application_state.content.service import create_world_runbook
    from application_state.errors import ApplicationStateError

    try:
        world = get_world_container(root, cleaned_world)
        if world.world_id != cleaned_world:
            raise WorkspaceDocumentRegistryError(
                "selected World identity does not match the managed World record",
                status_code=409,
            )
        obj = create_world_runbook(title=cleaned_title, world_id=cleaned_world)
    except WorldContainerRegistryError as exc:
        raise WorkspaceDocumentRegistryError(
            str(exc), status_code=exc.status_code
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    record = _record_from_work_object(obj)
    if not isinstance(record, WorldOwnedRunbookRecordV2):
        raise WorkspaceDocumentRegistryError(
            "World-owned Runbook creation returned an incompatible Content scope",
            status_code=500,
        )
    return record


def list_world_owned_runbooks_v2(
    root: Path, *, world_id: str, status: str | None = "active"
) -> WorldOwnedRunbooksResponseV2:
    cleaned_world = _validate_world_id(world_id)
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
        get_world_container,
    )
    from application_state.cli import assert_at_head
    from application_state.config import load_runtime_dsn
    from application_state.content import repository as content_repository
    from application_state.errors import ApplicationStateError
    from application_state.unit_of_work import unit_of_work

    try:
        world = get_world_container(root, cleaned_world)
        if world.world_id != cleaned_world:
            raise WorkspaceDocumentRegistryError(
                "selected World identity does not match the managed World record",
                status_code=409,
            )
        # Content's V1 list_runbooks intentionally returns campaign-owned rows
        # only. Read this World scope through the same owning repository with an
        # explicit world_id predicate rather than broadening V1 inventory.
        dsn = load_runtime_dsn()
        assert_at_head(dsn=dsn)
        with unit_of_work(dsn) as conn:
            objects = content_repository.list_work_objects(
                conn,
                kind="runbook",
                world_id=cleaned_world,
                status=status,
            )
        records = [_record_from_work_object(obj) for obj in objects]
    except WorldContainerRegistryError as exc:
        raise WorkspaceDocumentRegistryError(
            str(exc), status_code=exc.status_code
        ) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    if any(not isinstance(record, WorldOwnedRunbookRecordV2) for record in records):
        raise WorkspaceDocumentRegistryError(
            "World Runbook inventory returned a non-World-owned document",
            status_code=500,
        )
    return WorldOwnedRunbooksResponseV2(world_id=cleaned_world, records=records)


def get_world_owned_runbook_v2(
    root: Path, *, world_id: str, document_id: str
) -> WorldOwnedRunbookRecordV2:
    cleaned_world = _validate_world_id(world_id)
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
        get_world_container,
    )

    try:
        world = get_world_container(root, cleaned_world)
        if world.world_id != cleaned_world:
            raise WorkspaceDocumentRegistryError(
                "selected World identity does not match the managed World record",
                status_code=409,
            )
    except WorldContainerRegistryError as exc:
        raise WorkspaceDocumentRegistryError(
            str(exc), status_code=exc.status_code
        ) from exc
    record = get_workspace_document(root, document_id)
    if not isinstance(record, WorldOwnedRunbookRecordV2):
        raise WorkspaceDocumentRegistryError(
            "Runbook is not owned by the selected World", status_code=404
        )
    if record.world_id != cleaned_world:
        raise WorkspaceDocumentRegistryError(
            "Runbook is not owned by the selected World", status_code=404
        )
    return record


def get_world_owned_runbook_snapshot_v2(
    root: Path, *, world_id: str, document_id: str
) -> WorldOwnedRunbookSnapshotV2:
    # Verify scope before reading Markdown bytes; the generic snapshot route has
    # no World authority and cannot serve World-owned Runbooks.
    get_world_owned_runbook_v2(root, world_id=world_id, document_id=document_id)
    snapshot = get_workspace_document_snapshot(root, document_id)
    if not isinstance(snapshot, WorldOwnedRunbookSnapshotV2):
        raise WorkspaceDocumentRegistryError(
            "Runbook snapshot is not World-owned", status_code=409
        )
    if snapshot.record.world_id != _validate_world_id(world_id):
        raise WorkspaceDocumentRegistryError(
            "Runbook is not owned by the selected World", status_code=404
        )
    return snapshot


def get_workspace_document(root: Path, document_id: str) -> WorkspaceDocumentRecordAny:
    from application_state.content import pages
    from application_state.content.service import snapshot_content
    from application_state.errors import ApplicationStateError

    try:
        page = pages.find_page(document_id)
        if page is not None:
            return _record_from_page(page)
        snap = snapshot_content(document_id)
        return _record_from_work_object(
            snap.work_object, from_working_copy=snap.from_working_copy
        )
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc


def get_workspace_document_snapshot(
    root: Path, document_id: str
) -> WorkspaceDocumentSnapshotAny:
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        snap = pages.workspace_page_snapshot(document_id)
        if snap is None:
            return _postgres_plan_snapshot(document_id)
        return WorkspaceDocumentSnapshot(
            record=_record_from_page(snap, from_working_copy=snap.from_working_copy),
            markdown=snap.markdown,
            content_sha256=snap.content_sha256,
            committed_markdown=snap.committed_revision.markdown
            if snap.committed_revision
            else None,
            committed_content_sha256=snap.committed_revision.content_sha256
            if snap.committed_revision
            else None,
            file_exists=False,
            file_fingerprint="postgres",
            loaded_revision=snap.page.object_revision,
        )
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc


def _postgres_plan_snapshot(document_id: str) -> WorkspaceDocumentSnapshotAny:
    from application_state.content.service import snapshot_content
    from application_state.errors import (
        ApplicationStateError,
        ApplicationStateNotFoundError,
    )

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
    snapshot_model = (
        WorldOwnedPlanSnapshotV2
        if isinstance(record, WorldOwnedPlanRecordV2)
        else (
            WorldOwnedRunbookSnapshotV2
            if isinstance(record, WorldOwnedRunbookRecordV2)
            else WorkspaceDocumentSnapshot
        )
    )
    return snapshot_model(
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
    expected_world_id: str | None = None,
) -> WorkspaceCommittedRevision | WorldOwnedCommittedRevisionV2:
    from application_state.content.service import (
        current_committed_revision,
        exact_committed_revision,
        get_content_optional,
    )
    from application_state.errors import (
        ApplicationStateError,
        ApplicationStateNotFoundError,
    )

    canonical_id = _validate_document_id(document_id)
    try:
        obj = get_content_optional(canonical_id)
        if obj is None:
            raise WorkspaceDocumentRegistryError(
                f"workspace document not found: {canonical_id}", status_code=404
            )
        is_world_content = obj.world_id is not None
        if is_world_content and (
            obj.kind not in ("plan", "runbook") or obj.campaign_id is not None
        ):
            raise WorkspaceDocumentRegistryError(
                "World-owned committed revisions require a World-owned Plan or Runbook",
                status_code=422,
            )
        if obj.kind == "runbook" and is_world_content:
            if expected_world_id is None or obj.world_id != _validate_world_id(
                expected_world_id
            ):
                raise WorkspaceDocumentRegistryError(
                    "World-owned Runbooks require the matching World-scoped V2 route",
                    status_code=404,
                )
        elif expected_world_id is not None and obj.world_id != _validate_world_id(
            expected_world_id
        ):
            raise WorkspaceDocumentRegistryError(
                "committed document is not owned by the selected World",
                status_code=404,
            )
        resolved_kind = obj.kind if is_world_content else kind
        if revision_n is None:
            committed = current_committed_revision(canonical_id, kind=resolved_kind)
        else:
            committed = exact_committed_revision(
                canonical_id,
                revision_n,
                kind=resolved_kind,
                expected_sha256=expected_sha256,
            )
    except ApplicationStateNotFoundError as exc:
        raise WorkspaceDocumentRegistryError(str(exc), status_code=404) from exc
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    obj = committed.work_object
    revision = committed.work_revision
    if expected_world_id is not None and obj.world_id != _validate_world_id(
        expected_world_id
    ):
        raise WorkspaceDocumentRegistryError(
            "committed revision is not owned by the selected World", status_code=404
        )
    if obj.world_id is not None and obj.campaign_id is not None:
        raise WorkspaceDocumentRegistryError(
            "World-owned committed revision also has a Campaign owner",
            status_code=409,
        )
    values = dict(
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
    if obj.world_id is not None:
        return WorldOwnedCommittedRevisionV2(
            scope_mode="world",
            world_id=obj.world_id,
            **values,
        )
    return WorkspaceCommittedRevision(**values)


def get_current_world_plan_revision(
    document_id: str,
    *,
    expected_world_id: str,
    expected_revision: int,
    expected_revision_n: int,
    expected_content_sha256: str,
) -> CurrentWorldPlanRead:
    """Read one exact, current World Plan revision through Content's atomic boundary."""
    from application_state.content.service import read_current_world_plan_revision
    from application_state.errors import ApplicationStateError

    canonical_id = _validate_document_id(document_id)
    try:
        return read_current_world_plan_revision(
            canonical_id,
            expected_world_id=expected_world_id,
            expected_revision=expected_revision,
            expected_revision_n=expected_revision_n,
            expected_content_sha256=expected_content_sha256,
        )
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc


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
) -> WorkspaceDocumentRecordAny:
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        state = pages.find_page(document_id)
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    if state is not None:
        if target_relpath is not _UNSET and target_relpath is not None:
            raise WorkspaceDocumentRegistryError(
                "Page has no file target", status_code=422
            )
        if target_session is not _UNSET and target_session is not None:
            raise WorkspaceDocumentRegistryError(
                "Page has no target session", status_code=422
            )
        changes = {
            key: value
            for key, value in {
                "document_class": document_class,
                "authority_state": authority_state,
                "visibility_state": visibility_state,
            }.items()
            if value is not _UNSET
        }
        metadata = pages.PageMetadata.model_validate(
            {**state.metadata.model_dump(), **changes}
        )
        kwargs = dict(title=None if title is _UNSET else str(title), metadata=metadata)
        try:
            updated = pages.update_page(
                document_id,
                world_id=state.page.world_id,
                expected_revision=expected_revision
                if expected_revision is not None
                else state.page.object_revision,
                **kwargs,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_page(updated)
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
    if (
        existing.world_id is not None
        and target_session is not _UNSET
        and target_session is not None
    ):
        raise WorkspaceDocumentRegistryError(
            "World-owned Plans cannot be assigned a target session",
            status_code=422,
        )
    if target_relpath is not _UNSET and target_relpath != existing.target_relpath:
        raise WorkspaceDocumentRegistryError(
            "target_relpath cannot be changed via metadata update",
            status_code=422,
        )
    if (
        document_class is not _UNSET
        or authority_state is not _UNSET
        or visibility_state is not _UNSET
    ):
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


def discard_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        state = pages.find_page(document_id)
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    if state is not None:
        kwargs = dict(status="discarded")
        try:
            updated = pages.update_page(
                document_id,
                world_id=state.page.world_id,
                expected_revision=expected_revision
                if expected_revision is not None
                else state.page.object_revision,
                **kwargs,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_page(updated)
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


def restore_workspace_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None = None,
) -> WorkspaceDocumentRecord:
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        state = pages.find_page(document_id)
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
    if state is not None:
        kwargs = dict(status="active")
        try:
            updated = pages.update_page(
                document_id,
                world_id=state.page.world_id,
                expected_revision=expected_revision
                if expected_revision is not None
                else state.page.object_revision,
                **kwargs,
            )
        except ApplicationStateError as exc:
            raise _map_application_state_error(exc) from exc
        return _record_from_page(updated)
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


def _record_from_page(
    state, *, from_working_copy: bool = False
) -> WorkspaceDocumentRecord:
    obj, meta = state.page, state.metadata
    return WorkspaceDocumentRecord(
        document_id=str(obj.work_object_id),
        title=obj.title,
        campaign_id=obj.campaign_id,
        world_id=obj.world_id,
        target_session=None,
        kind="worldbuilding_source",
        target_relpath=None,
        status=obj.status,
        content_status="draft"
        if from_working_copy or obj.current_revision_id is None
        else "committed",
        revision=obj.object_revision,
        created_at=_iso_timestamp(obj.created_at),
        updated_at=_iso_timestamp(obj.updated_at),
        source_domain="worldbuilding",
        **meta.model_dump(mode="json"),
    )


def get_committed_page_snapshot(
    root: Path, document_id: str
) -> WorkspaceDocumentSnapshot:
    from application_state.content import pages
    from application_state.content.types import sha256_utf8
    from application_state.errors import ApplicationStateError

    try:
        snap = pages.workspace_page_snapshot(document_id, committed=True)
        if snap is None:
            raise WorkspaceDocumentRegistryError(
                "authored Page not found", status_code=404
            )
        revision = snap.revision
        return WorkspaceDocumentSnapshot(
            record=_record_from_page(snap),
            markdown=revision.markdown if revision else "",
            content_sha256=revision.content_sha256 if revision else sha256_utf8(""),
            committed_markdown=revision.markdown if revision else None,
            committed_content_sha256=revision.content_sha256 if revision else None,
            file_exists=False,
            file_fingerprint="postgres",
            loaded_revision=snap.page.object_revision,
        )
    except ApplicationStateError as exc:
        raise _map_application_state_error(exc) from exc
