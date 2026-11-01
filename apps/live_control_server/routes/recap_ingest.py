from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from application_state.errors import ApplicationStateError
from apps.live_control_server.config import repo_root
from apps.live_control_server.models.session_evidence import SessionEvidenceRef
from apps.live_control_server.services.ingest_run_catalog import IngestRunCatalogError
from apps.live_control_server.services.recap_graph_preview_ingest import extract_recap
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
)
from graph_memory.ingestion.native_recap_source import (
    Resume as NativeRecapResume,
)
from graph_memory.ingestion.native_recap_source import (
    SourceSelection,
)
from graph_memory.ingestion.native_recap_source import (
    Status as NativeRecapSourceStatus,
)

router = APIRouter(prefix="/api/live", tags=["live"])

RecapIngestOperation = Literal[
    "generate_recap_memory", "build_graph_preview_bundle", "inspect_status"
]


class RecapIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_recap_source: SourceSelection | None = None
    native_recap_run_id: UUID | None = None
    native_recap_resume: NativeRecapResume | None = None
    session_evidence: list[SessionEvidenceRef] = Field(
        default_factory=list, max_length=3
    )
    operation: RecapIngestOperation
    campaign_id: str = Field(min_length=1, pattern=r"^\S(?:.*\S)?$")
    managed_world_id: str | None = None
    session: Annotated[int, Field(ge=1, strict=True)]
    raw_text: str | None = None
    force_graph_run: bool = False
    graph_model_id: str | None = None
    include_graph_extraction: bool = True

    @model_validator(mode="after")
    def native_selector_scope(self):
        if self.native_recap_run_id is not None and (
            self.operation != "inspect_status"
            or not self.managed_world_id
            or self.native_recap_resume is not None
            or self.raw_text is not None
            or self.session_evidence
        ):
            raise ValueError(
                "Exact native source status requires inspect_status and its selected World"
            )
        if self.native_recap_source is not None and (
            not _source_only(self)
            or self.native_recap_run_id is not None
            or self.native_recap_resume is not None
        ):
            raise ValueError(
                "Exact source selection requires fresh source-only admission"
            )
        if self.native_recap_resume is not None and not _source_only(self):
            raise ValueError(
                "Explicit native resume requires the exact source-only operation"
            )
        return self


class RecapIngestStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    native_recap_source: NativeRecapSourceStatus | None = None
    schema_: Literal["dmb_raw_recap_ingest_status_v1"] = Field(alias="schema")
    campaign_id: str
    session: int
    status: str
    states: list[str]
    paths: dict[str, str | None]
    authority: dict[str, str]
    warnings: list[str]
    errors: list[str]
    next_actions: list[str]
    ingest_report: dict[str, Any]
    entity_spelling_audit: list[dict[str, Any]]


def _request_recap_context(body: RecapIngestRequest):
    if not body.managed_world_id:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "managed_world_context_required",
                "message": "Select a managed World before creating a campaign recap graph run.",
            },
        )
    from apps.live_control_server.services.recap_ingest_context import (
        resolve_recap_source_scope,
    )

    try:
        return resolve_recap_source_scope(
            managed_world_id=body.managed_world_id,
            campaign_id=body.campaign_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 503),
            detail={
                "code": getattr(exc, "code", "ingest_context_unavailable"),
                "message": str(exc),
            },
        ) from exc


def _source_only(body):
    return (
        body.operation == "build_graph_preview_bundle"
        and not body.include_graph_extraction
        and not body.force_graph_run
        and not body.session_evidence
        and body.raw_text is None
        and body.graph_model_id is None
    )


def _native_source_envelope(body, native):
    state = (
        "native_source_admitted"
        if native.state == "admitted"
        else "native_source_pending"
    )
    return {
        "schema": "dmb_raw_recap_ingest_status_v1",
        "campaign_id": body.campaign_id,
        "session": body.session,
        "status": state,
        "states": ["immutable_app_source_prepared", state],
        "paths": {},
        "authority": {"source": "immutable_app_recap_v1"},
        "warnings": [],
        "errors": [native.failure_code] if native.failure_code else [],
        "next_actions": [],
        "ingest_report": {},
        "entity_spelling_audit": [],
        "native_recap_source": native.model_dump(mode="json"),
    }


async def resolve_native_recap_hosted_world(request: Request) -> str:
    """Authorize only this capability's strict forms through the hosted boundary."""
    from apps.live_control_server import config
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
    )
    from graph_memory.ingestion.native_recap_source import StatusBody

    payload = await request.json()
    if isinstance(payload, dict) and payload.get("native_recap_run_id") is not None:
        body = StatusBody.model_validate(payload)
    else:
        body = RecapIngestRequest.model_validate(payload)
        if not _source_only(body) or not body.managed_world_id:
            raise ValueError("Hosted recap operation is outside source admission")
    world = get_world_container(
        config.managed_world_data_root(repo_root()), body.managed_world_id
    )
    return world.world_id


def _native_source_actor(body, request):
    from apps.live_control_server import config
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.world_container_registry import (
        WorldAccessDenied,
        WorldContainerRegistryError,
        WorldPermission,
        get_world_container,
        require_world_permission,
    )

    if request is None:
        raise HTTPException(status_code=403, detail={"code": "graph_gm_required"})
    environment, mode = hosted_auth.deployment_environment(), hosted_auth.auth_mode()
    if environment in hosted_auth.LOCAL_ENVIRONMENTS and mode == hosted_auth.LOCAL_MODE:
        principal = enforce_native_graph_gm(request)
        if not principal.subject.strip():
            raise HTTPException(status_code=403, detail={"code": "graph_gm_required"})
        return principal.subject, "local_gm"
    if (
        environment != hosted_auth.PRODUCTION_ENVIRONMENT
        or mode != hosted_auth.HOSTED_MODE
    ):
        raise HTTPException(status_code=503, detail={"code": "hosted_auth_unavailable"})
    principal = getattr(request.state, "dms_principal", None)
    if principal is None or not principal.subject.strip():
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    hosted_auth.require_hosted_write_origin(request)
    try:
        world = get_world_container(
            config.managed_world_data_root(repo_root()), body.managed_world_id
        )
        require_world_permission(
            world, subject=principal.subject, permission=WorldPermission.MANAGE
        )
    except (WorldAccessDenied, WorldContainerRegistryError) as exc:
        raise HTTPException(
            status_code=403, detail={"code": "native_recap_world_manage_required"}
        ) from exc
    return principal.subject, "world_manage"


def _native_source_request(body, request):
    from apps.live_control_server.services import (
        native_recap_source_admission as native,
    )

    actor, authority_basis = _native_source_actor(body, request)
    try:
        if body.native_recap_run_id is not None:
            return _native_source_envelope(
                body,
                native.inspect(
                    repo_root(),
                    body.native_recap_run_id,
                    body.managed_world_id,
                    body.campaign_id,
                    body.session,
                ),
            )
        if body.native_recap_resume is not None:
            return _native_source_envelope(
                body,
                native.resume_admission(
                    repo_root(),
                    resume=body.native_recap_resume,
                    world=body.managed_world_id,
                    campaign=body.campaign_id,
                    session=body.session,
                    actor=actor,
                    authority_basis=authority_basis,
                ),
            )
        if body.native_recap_source is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "native_recap_source_selection_required"},
            )
        if not body.managed_world_id:
            raise HTTPException(
                status_code=422, detail={"code": "managed_world_context_required"}
            )
        from apps.live_control_server import config
        from apps.live_control_server.services.managed_world_graph_projection import (
            resolve_managed_source_identity,
        )
        from graph_memory.ingestion.native_recap_source import SourceScope

        binding = resolve_managed_source_identity(
            body.managed_world_id, root=config.managed_world_data_root(repo_root())
        )
        context = SourceScope(
            managed_world_id=binding.managed_world_id,
            native_world_id=binding.native_world_id,
            binding_version=binding.binding_version,
            campaign_id=body.campaign_id,
        )
        return _native_source_envelope(
            body,
            native.admit(
                repo_root(),
                context=context,
                selection=body.native_recap_source,
                session=body.session,
                actor=actor,
                authority_basis=authority_basis,
            ),
        )
    except HTTPException:
        raise
    except native.NativeRecapError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code}
        ) from exc
    except Exception as exc:
        # Never reflect stored commands, source bytes or validation input to a public error.
        import logging

        logging.getLogger(__name__).exception("Native recap source request failed")
        raise HTTPException(
            status_code=409, detail={"code": "native_recap_source_unavailable"}
        ) from exc


@router.post("/recap-ingest", response_model=RecapIngestStatusResponse)
def post_recap_ingest(
    body: RecapIngestRequest, request: Request = None
) -> dict[str, Any]:
    if body.native_recap_run_id is not None or _source_only(body):
        return _native_source_request(body, request)
    if body.operation != "generate_recap_memory":
        raise HTTPException(
            status_code=422,
            detail="Select exact saved extraction work or an exact native source operation.",
        )
    if not body.include_graph_extraction or not (body.raw_text or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Process requires submitted recap text and extraction.",
        )
    # The hosted boundary admits source-only forms. This command retains its
    # local-only authority and authenticates before source creation or dispatch.
    from apps.live_control_server.services import hosted_auth

    if (
        hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS
        or hosted_auth.auth_mode() != hosted_auth.LOCAL_MODE
    ):
        raise HTTPException(status_code=403, detail="Raw recap Process is local-only.")
    _native_source_actor(body, request)
    context = _request_recap_context(body)
    try:
        supplemental_evidence = None
        if body.session_evidence:
            from apps.live_control_server.services.session_evidence import (
                resolve_evidence_refs,
            )

            supplemental_evidence = resolve_evidence_refs(
                body.managed_world_id,
                [ref.model_dump() for ref in body.session_evidence],
            )
        graph = extract_recap(
            repo_root=repo_root(),
            campaign_id=body.campaign_id,
            session=body.session,
            recap_text=body.raw_text,
            graph_model_id=body.graph_model_id,
            force_graph_run=body.force_graph_run,
            ingest_context=context,
            supplemental_evidence=supplemental_evidence,
        )
        failed = graph.get("status") == "failed"
        return {
            "schema": "dmb_raw_recap_ingest_status_v1",
            "campaign_id": body.campaign_id,
            "session": body.session,
            "status": "error" if failed else graph["status"],
            "states": [
                "immutable_app_source_prepared",
                *(
                    ["graph_preview_failed"]
                    if failed
                    else ["graph_candidate_ready"]
                    if graph.get("status") == "candidate_validation_ready"
                    else []
                ),
            ],
            "paths": {},
            "authority": {"source": "immutable_app_recap_v1"},
            "warnings": [],
            "errors": [graph["blocked_reason"]] if failed else [],
            "next_actions": graph.get("next_actions", []),
            "ingest_report": {"graph_preview": graph},
            "entity_spelling_audit": [],
        }
    except (
        ApplicationStateError,
        IngestRunCatalogError,
        SourceArtifactRegistryError,
    ) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": getattr(exc, "code", "recap_input_unavailable"),
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
