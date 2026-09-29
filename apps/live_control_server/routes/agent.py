"""Additive universal Agent route, mounted below the established /api/live router."""

from __future__ import annotations

from typing import Any, Mapping

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from apps.live_control_server.config import repo_root, session_dir
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.agent_runtime import (
    AgentCurrentWorkContext,
    AgentSurfaceContext,
)
from apps.live_control_server.services.agent_turn_service import (
    AgentTurnResolvedWork,
    AgentTurnServiceError,
    build_existing_graph_context,
    execute_agent_turn,
)
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from apps.live_control_server.services.recap_artifacts import normalize_session_id
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_committed_playable_revision,
    get_workspace_document,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)


router = APIRouter(prefix="/agent", tags=["agent-turn"])


def _owner_resolver(body: AgentTurnRequest) -> Mapping[str, Any] | None:
    owner = body.owner_scope
    if owner is None:
        return None
    if owner.kind == "campaign":
        # Buddy has no current campaign→World authority API. Do not treat the
        # campaign locator as a World ID or infer from graph contents.
        raise AgentTurnServiceError(
            "Campaign ownership cannot currently be resolved to a World.",
            code="campaign_owner_unresolved",
            status_code=422,
        )
    try:
        record = get_world_container(repo_root(), owner.world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code="world_owner_unavailable",
            status_code=exc.status_code,
        ) from exc
    return {"kind": "world", "id": record.world_id, "name": record.name}


def _work_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
) -> AgentTurnResolvedWork | None:
    locator = body.primary_work
    if locator is None:
        return None
    if locator.kind != "plan":
        raise AgentTurnServiceError(
            f"Saved work kind {locator.kind!r} has no accepted resolver yet.",
            code="work_kind_unresolved",
            status_code=422,
        )
    try:
        record = get_workspace_document(repo_root(), locator.object_id)
        committed = get_committed_playable_revision(
            locator.object_id,
            kind="plan",
        )
    except WorkspaceDocumentRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code="work_unavailable",
            status_code=exc.status_code,
        ) from exc
    if record.kind != "plan" or record.status != "active" or committed.status != "active":
        raise AgentTurnServiceError(
            "The requested saved Plan is not active.",
            code="work_removed",
            status_code=404,
        )
    record_world_id = getattr(record, "world_id", None)
    record_campaign_id = getattr(record, "campaign_id", None)
    effective_owner_id = record_world_id or record_campaign_id
    if owner is not None and (
        owner.get("kind") != "world" or owner.get("id") != effective_owner_id
    ):
        raise AgentTurnServiceError(
            "The saved Plan does not belong to the requested owner scope.",
            code="work_foreign",
            status_code=403,
        )
    expected_revision = locator.expected_revision
    record_world_id = getattr(record, "world_id", None)
    surface_context = AgentSurfaceContext(
        surface_id=body.surface.surface_id,
        current_work=AgentCurrentWorkContext(
            kind="plan",
            work_object_id=committed.document_id,
            title=committed.title,
            object_revision=committed.object_revision,
            target_session=getattr(record, "target_session", None),
        ),
    )
    return AgentTurnResolvedWork(
        kind="plan",
        object_id=committed.document_id,
        revision=committed.object_revision,
        changed_since_expected=(committed.object_revision != expected_revision),
        owner_kind="world" if record_world_id else ("campaign" if record_campaign_id else None),
        owner_id=record_world_id or record_campaign_id,
        surface_context=surface_context,
        campaign_id=record_campaign_id,
        target_session=getattr(record, "target_session", None),
        session_id=(
            None
            if getattr(record, "target_session", None) is None
            else normalize_session_id(record.target_session)
        ),
        world_id=record_world_id,
    )


def _graph_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    work: AgentTurnResolvedWork | None,
) -> tuple[dict[str, Any], Any]:
    graph = body.graph_request
    if graph.mode == "none":
        raise AgentTurnServiceError("Graph was not requested.", code="graph_not_requested")
    if graph.mode == "world":
        requested_world_id = graph.world_id
        if owner is not None and (owner.get("kind") != "world" or owner.get("id") != requested_world_id):
            raise AgentTurnServiceError(
                "The requested World graph is outside the resolved owner scope.",
                code="graph_scope_rejected",
                status_code=403,
            )
        if owner is None and (work is None or work.world_id != requested_world_id):
            raise AgentTurnServiceError(
                "A World graph requires an independently resolved matching owner or saved work.",
                code="graph_scope_unproven",
                status_code=422,
            )
        if work is None and (
            graph.campaign_id is not None or graph.focus.kind != "none"
        ):
            raise AgentTurnServiceError(
                "A campaign anchor or temporal focus requires matching saved work.",
                code="graph_focus_unproven",
                status_code=422,
            )
        if work is not None:
            if work.world_id != requested_world_id:
                raise AgentTurnServiceError(
                    "The saved Plan does not belong to the requested World.",
                    code="graph_scope_rejected",
                    status_code=403,
                )
            if graph.campaign_id != work.campaign_id:
                raise AgentTurnServiceError(
                    "The requested narrative campaign does not match saved work.",
                    code="graph_campaign_rejected",
                    status_code=422,
                )
            if work.target_session is None and graph.focus.kind != "none":
                raise AgentTurnServiceError(
                    "Saved work does not authorize a session focus.",
                    code="graph_focus_rejected",
                    status_code=422,
                )
            if work.target_session is not None and (
                graph.focus.kind != "session"
                or graph.focus.session_id != work.session_id
                or graph.focus.campaign_id != work.campaign_id
            ):
                raise AgentTurnServiceError(
                    "The graph focus must match the exact saved Plan session.",
                    code="graph_focus_rejected",
                    status_code=422,
                )
        try:
            get_world_container(repo_root(), requested_world_id)
        except WorldContainerRegistryError as exc:
            raise AgentTurnServiceError(
                str(exc), code="world_owner_unavailable", status_code=exc.status_code
            ) from exc
    else:
        if owner is None or owner.get("kind") != "world":
            raise AgentTurnServiceError(
                "A campaign graph requires its verified parent World scope.",
                code="campaign_owner_unresolved",
                status_code=422,
            )
        if work is None or work.world_id != owner.get("id"):
            raise AgentTurnServiceError(
                "A campaign graph requires saved work that proves its parent World.",
                code="campaign_owner_unresolved",
                status_code=422,
            )
        requested_world_id = str(owner["id"])
        if work.campaign_id != graph.campaign_id:
            raise AgentTurnServiceError(
                "The requested campaign does not match the saved Plan.",
                code="graph_campaign_rejected",
                status_code=422,
            )
        if work.target_session is None and graph.focus.kind != "none":
            raise AgentTurnServiceError(
                "Saved work does not authorize a session focus.",
                code="graph_focus_rejected",
                status_code=422,
            )
        if work.target_session is not None and (
            graph.focus.kind != "session"
            or graph.focus.session_id != work.session_id
            or graph.focus.campaign_id != work.campaign_id
        ):
            raise AgentTurnServiceError(
                "The exact saved Plan session focus is required.",
                code="graph_focus_rejected",
                status_code=422,
            )
        if graph.focus.kind == "session" and graph.focus.campaign_id != graph.campaign_id:
            raise AgentTurnServiceError(
                "Campaign graph focus must match the exact campaign scope.",
                code="graph_focus_rejected",
                status_code=422,
            )
    try:
        return build_existing_graph_context(
            body,
            root=repo_root(),
            world_id=requested_world_id,
        )
    except Exception as exc:
        raise AgentTurnServiceError(
            "The requested graph projection could not be resolved.",
            code="graph_unavailable",
            status_code=503,
        ) from exc


@router.post("/turn", response_model=None)
def post_agent_turn(body: AgentTurnRequest, request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "agent_turn_runtime", None)
    try:
        result = execute_agent_turn(
            body,
            root=repo_root(),
            pointer_store=HermesSessionPointerStore(session_dir()),
            owner_resolver=_owner_resolver,
            work_resolver=_work_resolver,
            graph_resolver=_graph_resolver,
            runtime=runtime,
        )
        return result.model_dump(mode="json", by_alias=True)
    except AgentTurnServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
