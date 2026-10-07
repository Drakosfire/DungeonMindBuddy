"""Additive universal Agent route, mounted below the established /api/live router."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Mapping
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import ConversationCommand, TurnProvenance
from application_state.errors import ApplicationStateError

from apps.live_control_server.config import (
    ManagedWorldDataRootError,
    managed_world_data_root,
    repo_root,
    session_dir,
    world_graph_root,
)
from apps.live_control_server.models.agent_turn import (
    AgentConversationHistoryResponse,
    AgentConversationHistoryResponseV2,
    AgentConversationHistoryResponseV3,
    AgentConversationHistoryPlanTurnV3,
    AgentConversationHistoryTurn,
    AgentConversationHistoryTurnV2,
    AgentConversationHistoryTurnV3,
    AgentNewConversationRequest,
    AgentNewConversationResponse,
    AgentTurnContentBasis,
    AgentTurnRequest,
)
from apps.live_control_server.services.agent_runtime import (
    AgentCurrentWorkContext,
    AgentSurfaceContext,
)
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
from apps.live_control_server.services.agent_turn_service import (
    AgentPlanWorldGraphBootstrap,
    AgentTurnResolvedWork,
    AgentTurnServiceError,
    build_existing_graph_context,
    execute_agent_turn,
    project_plan_turn_context,
)
from apps.live_control_server.services.hermes_session_store import (
    HermesSessionPointerStore,
)
from apps.live_control_server.services.recap_artifacts import normalize_session_id
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_committed_playable_revision,
    get_current_world_plan_revision,
    get_workspace_document,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)


router = APIRouter(prefix="/agent", tags=["agent-turn"])


def _finalize_unlogged_agent_trace(
    trace: AgentTurnTraceBuilder, *, status: str,
) -> None:
    if not trace.logged:
        trace.finalize_and_log(status=status, model_calls=0)


def _managed_world_root():
    try:
        return managed_world_data_root(repo_root())
    except ManagedWorldDataRootError as exc:
        raise WorldContainerRegistryError(
            "Managed World storage is unavailable.", status_code=503,
        ) from exc

_PLAN_PREDISPATCH_FAILURES = {
    "managed_world_unresolved": ("managed_world_unresolved", 404),
    "world_owner_unavailable": ("managed_world_unresolved", 404),
    "native_binding_invalid": ("native_binding_invalid", 409),
    "native_graph_binding_unavailable": ("native_binding_invalid", 409),
    "native_graph_binding_changed": ("native_binding_invalid", 409),
    "graph_revision_unavailable": ("graph_revision_unavailable", 409),
    "graph_unavailable": ("graph_read_failed", 503),
    "graph_evidence_invalid": ("graph_evidence_invalid", 502),
    "provider_envelope_over_budget": ("provider_envelope_over_budget", 413),
    "receipt_freeze_failed": ("receipt_freeze_failed", 503),
}


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
        record = get_world_container(_managed_world_root(), owner.world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code=("graph_unavailable" if exc.status_code == 503 else "world_owner_unavailable"),
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
    if body.surface.surface_id == "plan":
        if owner is None or owner.get("kind") != "world" or not owner.get("id"):
            raise AgentTurnServiceError(
                "A saved Plan question requires a verified managed World.",
                code="plan_owner_required",
                status_code=422,
            )
        if (
            locator.expected_revision_n is None
            or locator.expected_content_sha256 is None
        ):
            raise AgentTurnServiceError(
                "A saved Plan question requires an exact committed revision pin.",
                code="plan_content_pin_required",
                status_code=422,
            )
        try:
            committed = get_current_world_plan_revision(
                locator.object_id,
                expected_world_id=str(owner["id"]),
                expected_revision=locator.expected_revision,
                expected_revision_n=locator.expected_revision_n,
                expected_content_sha256=locator.expected_content_sha256,
            )
        except WorkspaceDocumentRegistryError as exc:
            code = (
                "plan_revision_changed"
                if exc.status_code == 409
                else "work_unavailable"
            )
            raise AgentTurnServiceError(
                str(exc),
                code=code,
                status_code=exc.status_code,
            ) from exc

        content_basis = AgentTurnContentBasis(
            world_id=committed.world_id,
            document_id=str(committed.document_id),
            object_revision=committed.object_revision,
            work_revision_id=str(committed.work_revision_id),
            revision_n=committed.revision_n,
            content_sha256=committed.content_sha256,
            committed_status=committed.committed_status,
            has_divergent_working_copy=committed.has_divergent_working_copy,
        )
        return AgentTurnResolvedWork(
            kind="plan",
            object_id=str(committed.document_id),
            revision=committed.object_revision,
            changed_since_expected=False,
            owner_kind="world",
            owner_id=committed.world_id,
            surface_context=AgentSurfaceContext(
                surface_id=body.surface.surface_id,
                current_work=AgentCurrentWorkContext(
                    kind="plan",
                    work_object_id=str(committed.document_id),
                    title="Saved Plan",
                    object_revision=committed.object_revision,
                ),
            ),
            world_id=committed.world_id,
            content_basis=content_basis,
            plan_markdown=committed.markdown,
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
    if (
        record.kind != "plan"
        or record.status != "active"
        or committed.status != "active"
    ):
        raise AgentTurnServiceError(
            "The requested saved Plan is not active.",
            code="work_removed",
            status_code=404,
        )
    record_world_id = getattr(record, "world_id", None)
    record_campaign_id = getattr(record, "campaign_id", None)
    if owner is not None and (
        owner.get("kind") != "world"
        or record_world_id is None
        or owner.get("id") != record_world_id
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
        owner_kind="world"
        if record_world_id
        else ("campaign" if record_campaign_id else None),
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


def _historical_work_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    provenance: TurnProvenance,
) -> AgentTurnResolvedWork | None:
    """Load retry content from its frozen WorkRevision, never today's pointer."""
    reference = provenance.primary_work
    if reference.resolution == "absent":
        return None
    locator = body.primary_work
    if (
        reference.resolution != "resolved"
        or reference.kind != "plan"
        or locator is None
        or locator.kind != "plan"
        or locator.object_id != reference.object_id
        or reference.object_revision is None
        or reference.revision_n is None
        or reference.content_sha256 is None
        or reference.work_revision_id is None
        or locator.expected_revision != reference.object_revision
        or locator.expected_revision_n != reference.revision_n
        or locator.expected_content_sha256 != reference.content_sha256
    ):
        raise AgentTurnServiceError(
            "The retry intent does not match a complete frozen Plan reference.",
            code="turn_receipt_unverifiable",
            status_code=409,
        )
    if owner is None or owner.get("kind") != "world" or not owner.get("id"):
        raise AgentTurnServiceError(
            "A historical World Plan requires a verified World owner.",
            code="world_owner_unverified",
            status_code=403,
        )
    try:
        committed = get_committed_playable_revision(
            reference.object_id,
            revision_n=reference.revision_n,
            expected_sha256=reference.content_sha256,
            kind="plan",
            expected_world_id=str(owner["id"]),
        )
    except WorkspaceDocumentRegistryError as exc:
        raise AgentTurnServiceError(
            "The pinned historical Plan revision could not be verified.",
            code="historical_work_unavailable",
            status_code=503 if exc.status_code >= 500 else exc.status_code,
        ) from exc
    if (
        committed.document_id != reference.object_id
        or committed.work_revision_id != str(reference.work_revision_id)
        or committed.revision_n != reference.revision_n
        or committed.content_sha256 != reference.content_sha256
        or getattr(committed, "world_id", None) != owner.get("id")
    ):
        raise AgentTurnServiceError(
            "The pinned historical Plan identity does not match the stored receipt.",
            code="turn_receipt_unverifiable",
            status_code=409,
        )
    target_session = getattr(committed, "target_session", None)
    return AgentTurnResolvedWork(
        kind="plan",
        object_id=reference.object_id,
        revision=reference.object_revision,
        changed_since_expected=False,
        owner_kind="world",
        owner_id=str(owner["id"]),
        surface_context=AgentSurfaceContext(
            surface_id=body.surface.surface_id,
            current_work=AgentCurrentWorkContext(
                kind="plan",
                work_object_id=reference.object_id,
                title="Saved Plan",
                object_revision=reference.object_revision,
                target_session=target_session,
            ),
        ),
        campaign_id=getattr(committed, "campaign_id", None),
        target_session=target_session,
        session_id=(
            None if target_session is None else normalize_session_id(target_session)
        ),
        world_id=str(owner["id"]),
        # The historical reference does not store editor divergence. The
        # immutable pin is sufficient to reconstruct runtime input, not that
        # transient response boolean.
        content_basis=None,
        plan_markdown=committed.markdown,
    )


def _graph_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    work: AgentTurnResolvedWork | None,
) -> tuple[dict[str, Any], Any]:
    graph = body.graph_request
    if graph.mode == "none":
        raise AgentTurnServiceError(
            "Graph was not requested.", code="graph_not_requested"
        )
    if graph.mode == "world":
        requested_world_id = graph.world_id
        if owner is not None and (
            owner.get("kind") != "world" or owner.get("id") != requested_world_id
        ):
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
            get_world_container(_managed_world_root(), requested_world_id)
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
        if (
            graph.focus.kind == "session"
            and graph.focus.campaign_id != graph.campaign_id
        ):
            raise AgentTurnServiceError(
                "Campaign graph focus must match the exact campaign scope.",
                code="graph_focus_rejected",
                status_code=422,
            )
    try:
        return build_existing_graph_context(
            body,
            root=world_graph_root(),
            world_id=requested_world_id,
        )
    except Exception as exc:
        raise AgentTurnServiceError(
            "The requested graph projection could not be resolved.",
            code="graph_unavailable",
            status_code=503,
        ) from exc


def _source_session_handles(
    managed_world_id: str, turn_id: str, graph_revision: str,
) -> tuple[str, str]:
    identity = f"{managed_world_id}:{turn_id}:{graph_revision}"
    return (
        f"grs:{uuid5(NAMESPACE_URL, f'dmb-plan-source-session:{identity}').hex[:16]}",
        f"op:{uuid5(NAMESPACE_URL, f'dmb-plan-source-search:{identity}').hex[:12]}",
    )


def _store_plan_retrieval_session(session: Any, *, reusable_source_session: bool) -> Any:
    from graph_memory.interaction.session_store import create_session, get_session

    existing = get_session(session.id) if reusable_source_session else None
    if existing is not None:
        if existing.snapshot != session.snapshot or existing.question != session.question:
            raise AgentTurnServiceError(
                "The source session identity conflicts with its pinned Graph retrieval.",
                code="turn_receipt_unverifiable", status_code=409,
                provider_dispatched=False,
            )
        return existing
    return create_session(session)


def _plan_context_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    work: AgentTurnResolvedWork | None,
    frozen_receipt: Any | None,
    *,
    trace: AgentTurnTraceBuilder | None = None,
    parent_span_id: str | None = None,
) -> AgentPlanWorldGraphBootstrap:
    """Resolve one source-free, revision-pinned DungeonMind retrieval packet."""
    from graph_memory.interaction.authority_classifier import (
        claims_from_retrieval_result,
    )
    from graph_memory.interaction.session import (
        CoverageState,
        GraphReferent,
        GraphRetrievalSession,
        RetrievalOperationEvent,
        SessionSnapshot,
        SourceAnchorState,
    )
    from graph_memory.retrieval.models import WorldGraphObjectRequest, WorldGraphSearchRequest

    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        direct_services_from_config,
        get_object_direct,
        search_world_graph_direct_v2,
    )
    from apps.live_control_server.services.agent_plan_playable_target import (
        AgentPlanPlayableTargetError,
        selected_plan_graph_seed_candidates,
    )
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
        world_source_root_relpath,
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope

    managed_world_id = str(owner.get("id")) if owner is not None else ""
    if (
        owner is None
        or owner.get("kind") != "world"
        or not managed_world_id
        or work is None
        or work.kind != "plan"
        or work.world_id != managed_world_id
    ):
        raise AgentTurnServiceError(
            "auto_plan_world requires a saved Plan owned by the verified World.",
            code="plan_context_scope_rejected",
            status_code=403,
        )
    try:
        registry_root = _managed_world_root()
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            "Managed World storage is unavailable.",
            code="graph_unavailable", status_code=503,
            provider_dispatched=False,
        ) from exc
    expected_root = world_source_root_relpath(managed_world_id)
    try:
        initial = get_world_container(registry_root, managed_world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code="world_owner_unavailable",
            status_code=exc.status_code,
            provider_dispatched=False,
        ) from exc
    binding = initial.native_graph_binding
    try:
        source_root = (registry_root / expected_root).resolve(strict=True)
        source_root_present = source_root.is_relative_to(registry_root.resolve()) and source_root.is_dir()
    except (OSError, RuntimeError):
        source_root_present = False
    if (
        initial.source_root_relpath != expected_root
        or not source_root_present
        or binding is None
        or binding.status != "active"
        or binding.binding_version <= 0
    ):
        raise AgentTurnServiceError(
            "The managed World has no verified active native Graph binding.",
            code="native_graph_binding_unavailable",
            status_code=409,
            provider_dispatched=False,
        )
    native_world_id = binding.native_world_id
    if frozen_receipt is not None and (
        frozen_receipt.graph_authority.managed_world_id != managed_world_id
        or frozen_receipt.graph_authority.native_world_id != native_world_id
        or frozen_receipt.graph_authority.binding_version != binding.binding_version
    ):
        raise AgentTurnServiceError(
            "The stored Graph authority no longer matches the managed World binding.",
            code="native_binding_invalid",
            status_code=409,
            provider_dispatched=False,
        )
    try:
        with (
            trace.phase(
                "plan_graph_seed_selection", parent_span_id=parent_span_id,
            ) if trace else nullcontext()
        ):
            candidates = selected_plan_graph_seed_candidates(
                body.playable_target, work.plan_markdown or ""
            )
    except AgentPlanPlayableTargetError as exc:
        raise AgentTurnServiceError(
            str(exc), code="plan_playable_target_unavailable", status_code=422,
            provider_dispatched=False,
        ) from exc
    lookup_count = 0
    lookup_status = "ok"
    lookup_span = (
        trace.start_phase(
            "plan_graph_seed_object_lookups",
            parent_span_id=parent_span_id,
            attributes={"candidate_count": len(candidates)},
        )
        if trace else None
    )
    try:
        services = direct_services_from_config(native_world_id)
        revision_pin = (
            None if frozen_receipt is None
            else frozen_receipt.graph_authority.graph_revision
        )
        valid_seeds: list[str] = []
        for candidate in candidates:
            lookup_count += 1
            lookup = get_object_direct(
                services,
                WorldGraphObjectRequest.model_validate({
                    "schema": "dmb_world_graph_object_request_v1",
                    "worldId": native_world_id,
                    "campaignId": "",
                    "focus": {"kind": "none", "sessionId": None, "campaignId": None},
                    "admissibility": "gm",
                    "revisionPin": revision_pin,
                    "scopeMode": "world",
                    "nodeId": candidate,
                    "bounds": {
                        "maxNodes": 1, "maxRelationships": 1,
                        "maxAttributes": 1, "maxSourceAnchors": 1,
                    },
                }),
            )
            if lookup.snapshot is None or lookup.snapshot.world_id != native_world_id:
                raise ValueError("Graph seed lookup did not return the bound World snapshot")
            if revision_pin is None:
                revision_pin = lookup.snapshot.revision_id
            elif lookup.snapshot.revision_id != revision_pin:
                raise ValueError("Graph seed lookup changed revision")
            if lookup.resolved_node_id == candidate:
                valid_seeds.append(candidate)
    except Exception as exc:
        lookup_status = "error"
        raise AgentTurnServiceError(
            "The pinned DungeonMind Graph retrieval could not be resolved.",
            code="graph_unavailable",
            status_code=503,
            provider_dispatched=False,
        ) from exc
    finally:
        if trace is not None and lookup_span is not None:
            trace.complete_phase(
                lookup_span,
                status=lookup_status,
                attributes={"lookup_count": lookup_count},
            )
    try:
        request = WorldGraphSearchRequest.model_validate(
            {
                "schema": "dmb_world_graph_search_request_v1",
                "worldId": native_world_id,
                "campaignId": "",
                "focus": {"kind": "none", "sessionId": None, "campaignId": None},
                "admissibility": "gm",
                "revisionPin": revision_pin,
                "scopeMode": "world",
                "queryText": body.message,
                "seedNodeIds": valid_seeds,
                "bounds": {
                    "maxNodes": 8,
                    "maxRelationships": 16,
                    "maxAttributes": 24,
                    "maxSourceAnchors": 24,
                },
            }
        )
        with (
            trace.phase(
                "plan_graph_search",
                parent_span_id=parent_span_id,
                attributes={"seed_count": len(valid_seeds)},
            ) if trace else nullcontext()
        ):
            resolved_search = search_world_graph_direct_v2(services, request)
            result = resolved_search.result
    except Exception as exc:
        raise AgentTurnServiceError(
            "The pinned DungeonMind Graph retrieval could not be resolved.",
            code="graph_unavailable",
            status_code=503,
            provider_dispatched=False,
        ) from exc
    projection_span = (
        trace.start_phase("plan_graph_projection", parent_span_id=parent_span_id)
        if trace else None
    )
    try:
        current = get_world_container(registry_root, managed_world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval.",
            code="native_graph_binding_changed",
            status_code=409,
            provider_dispatched=False,
        ) from exc
    current_binding = current.native_graph_binding
    if (
        current.source_root_relpath != initial.source_root_relpath
        or current_binding is None
        or current_binding.status != "active"
        or current_binding.native_world_id != native_world_id
        or current_binding.binding_version != binding.binding_version
    ):
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval; retry the turn.",
            code="native_graph_binding_changed",
            status_code=409,
        )
    if result.snapshot is None or result.snapshot.world_id != native_world_id:
        raise AgentTurnServiceError(
            "DungeonMind returned no exact Graph snapshot for the active binding.",
            code="graph_revision_unavailable",
            status_code=503,
            provider_dispatched=False,
        )
    if (
        frozen_receipt is not None
        and result.snapshot.revision_id
        != frozen_receipt.graph_authority.graph_revision
    ):
        raise AgentTurnServiceError(
            "DungeonMind did not return the stored Graph revision.",
            code="graph_revision_unavailable",
            status_code=409,
            provider_dispatched=False,
        )
    packet = result.model_dump(mode="python", by_alias=False)
    revision_id = result.snapshot.revision_id
    matched = list(result.matched_node_ids)
    claims = claims_from_retrieval_result(packet, revision_id=revision_id)
    evidence_by_anchor = {
        anchor.anchor_id: anchor.evidence_ref_id
        for anchor in result.source_anchors
        if anchor.anchor_id and anchor.evidence_ref_id
    }
    source_scope_anchors: list[dict[str, str]] = []
    try:
        by_id = {anchor.anchor_id: anchor for anchor in result.source_anchors}
        for pin in resolved_search.source_pins:
            anchor = by_id.get(pin.anchor_id)
            if (
                anchor is None
                or not anchor.readable
                or pin.graph_revision != revision_id
                or pin.evidence_ref_id != anchor.evidence_ref_id
                or pin.source_artifact_id != anchor.source_artifact_id
            ):
                raise ValueError("source anchor metadata differs from the admitted Graph result")
            source_scope_anchors.append({
                "anchor_id": pin.anchor_id,
                "evidence_ref_id": pin.evidence_ref_id,
                "source_artifact_id": pin.source_artifact_id,
                "source_revision_id": pin.source_revision_id,
            })
    except Exception as exc:
        raise AgentTurnServiceError(
            "The pinned source-anchor metadata could not be resolved.",
            code="graph_evidence_invalid", status_code=502,
            provider_dispatched=False,
        ) from exc
    # A safely reclaimed V2 turn must reconstruct the same initial provider
    # envelope after process restart; both handles appear in that envelope.
    source_session_id, initial_operation_id = (
        _source_session_handles(managed_world_id, body.turn_id, revision_id)
        if source_scope_anchors else (None, f"op:{uuid4().hex[:12]}")
    )
    session = GraphRetrievalSession(
        **({"id": source_session_id} if source_session_id is not None else {}),
        snapshot=SessionSnapshot(
            world_id=native_world_id,
            campaign_id="",
            focus={"kind": "none", "session_id": None, "campaign_id": None},
            admissibility="gm",
            revision_id=revision_id,
            is_head=result.snapshot.is_head,
            scope_mode="world",
        ),
        question=body.message,
        referents=[
            GraphReferent(
                kind="node",
                id=node.node_id,
                label=node.label,
                origin="deterministic_match",
                match_reasons=list(result.match_reasons.get(node.node_id, [])),
                selected=(len(matched) == 1 and node.node_id == matched[0]),
            )
            for node in result.nodes
        ],
        claims=claims,
        source_anchors=[
            SourceAnchorState(
                anchor_id=anchor.anchor_id,
                readable=anchor.readable,
                opened=False,
                locator_kind=anchor.locator_kind,
            )
            for anchor in result.source_anchors
        ],
        preflight_candidate_ids=matched,
        coverage=CoverageState(
            state=("ready" if result.outcome == "enough" else "empty" if result.outcome == "empty" else "partial_coverage"),
            known=[claim.predicate or claim.claim_kind for claim in claims if claim.may_state_as_campaign_fact()],
            missing=[] if result.outcome == "enough" else ["complete Graph coverage"],
            gap_codes=[diagnostic.code for diagnostic in result.diagnostics],
        ),
        diagnostics=[diagnostic.code for diagnostic in result.diagnostics],
    )
    session.operations.append(
        RetrievalOperationEvent(
            operation_id=initial_operation_id,
            requested_by="server_initial",
            operation="search",
            inputs={"result_limit": 32},
            status="completed" if result.outcome == "enough" else "partial",
            added_claim_ids=[claim.claim_id for claim in claims],
            diagnostic_codes=[diagnostic.code for diagnostic in result.diagnostics],
        )
    )
    session = _store_plan_retrieval_session(
        session, reusable_source_session=source_session_id is not None,
    )
    bootstrap = AgentPlanWorldGraphBootstrap(
        graph_envelope={
            "world_id": native_world_id,
            "campaign_id": "",
            "revision_id": revision_id,
            "head_revision_id": result.snapshot.head_revision_id,
            "is_head": result.snapshot.is_head,
            "scope_mode": "world",
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            "admissibility": "gm",
            "matched_node_ids": matched,
            "nodes": [item.model_dump(mode="python") for item in result.nodes],
            "relationships": [item.model_dump(mode="python") for item in result.relationships],
            "attributes": [item.model_dump(mode="python") for item in result.attributes],
            "source_anchors": [item.model_dump(mode="python") for item in result.source_anchors],
            "warning_codes": [diagnostic.code for diagnostic in result.diagnostics],
        },
        world_scope=AgentWorldScope(
            world_id=native_world_id,
            campaign_id="",
            focus={"kind": "none", "session_id": None},
            admissibility="gm",
            revision_id=revision_id,
            scope_mode="world",
        ),
        retrieval_session=session,
        binding_version=binding.binding_version,
        source_root_relpath=initial.source_root_relpath,
        candidate_assertion_ids=tuple(sorted({item.assertion_id for item in result.attributes})),
        candidate_relationship_ids=tuple(sorted({item.edge_id for item in result.relationships})),
        candidate_evidence_ref_ids=tuple(sorted({item.evidence_ref_id for item in result.source_anchors})),
        evidence_by_anchor_id=evidence_by_anchor,
        source_scope_anchors=tuple(source_scope_anchors),
    )
    if trace is not None and projection_span is not None:
        trace.complete_phase(
            projection_span,
            attributes={
                "node_count": len(result.nodes),
                "relationship_count": len(result.relationships),
                "source_anchor_count": len(result.source_anchors),
            },
        )
    return bootstrap


def _conversation_service(request: Request) -> AgentConversationService:
    configured = getattr(request.app.state, "agent_conversation_service", None)
    return configured if configured is not None else AgentConversationService()


def _verified_world_id(world_id: str) -> str:
    try:
        return get_world_container(_managed_world_root(), world_id).world_id
    except WorldContainerRegistryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": "world_owner_unavailable", "message": str(exc)},
        ) from exc


@router.get(
    "/worlds/{world_id}/conversation",
    # The response is selected per snapshot when it contains a policy turn.
    # A fixed v1 model would reject the additive plan_context payload.
    response_model=(
        AgentConversationHistoryResponse
        | AgentConversationHistoryResponseV2
        | AgentConversationHistoryResponseV3
    ),
)
def get_world_conversation_history(
    world_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    before_sequence: int | None = Query(default=None, gt=0),
    include_turn_correlation: bool = False,
) -> (
    AgentConversationHistoryResponse
    | AgentConversationHistoryResponseV2
    | AgentConversationHistoryResponseV3
):
    # Authenticate before managed World lookup and every APP-STATE read.
    enforce_native_graph_gm(request)
    verified_world_id = _verified_world_id(world_id)
    service = _conversation_service(request)
    try:
        # The pointer and active record are separate APP-STATE reads. Verify
        # they agree across the history read so callers can use the revision
        # for a subsequent New Conversation CAS.
        snapshot = None
        for _attempt in range(3):
            before = service.get_world_pointer(verified_world_id)
            conversation = service.get_active_conversation(verified_world_id)
            turns = (
                []
                if conversation is None
                else service.list_turns(
                    verified_world_id,
                    conversation.conversation_id,
                    limit=limit,
                    before_sequence=before_sequence,
                )
            )
            after = service.get_world_pointer(verified_world_id)
            active_id = None if conversation is None else conversation.conversation_id
            if (
                before.revision == after.revision
                and before.active_conversation_id == after.active_conversation_id
                and before.active_conversation_id == active_id
            ):
                snapshot = (after, conversation, turns)
                break
        if snapshot is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "conversation_changed",
                    "message": "The World conversation changed while history was being read.",
                },
            )
    except ApplicationStateError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": "conversation_unavailable", "message": str(exc)},
        ) from exc
    pointer, conversation, turns = snapshot
    if conversation is None:
        absent_model = (
            AgentConversationHistoryResponseV3
            if include_turn_correlation else AgentConversationHistoryResponse
        )
        return absent_model(
            world_id=verified_world_id,
            conversation_state="absent",
            conversation_id=None,
            active_conversation_id=None,
            pointer_revision=pointer.revision,
            turns=[],
        )
    contains_plan_context = any(
        turn.graph_context_receipt is not None for turn in turns
    )
    history_turns = []
    for turn in turns:
        values = {
            "turn_id": turn.turn_id,
            "sequence": turn.sequence,
            "lifecycle_status": turn.status,
            "user_text": turn.user_text,
            "assistant_text": turn.assistant_text,
            "provenance": turn.provenance,
        }
        if include_turn_correlation:
            persisted_key = getattr(turn, "idempotency_key", None)
            if not isinstance(persisted_key, UUID):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "turn_correlation_unavailable",
                        "message": "A historical turn has no persisted correlation key.",
                    },
                )
            values["idempotency_key"] = persisted_key
        if turn.graph_context_receipt is not None:
            history_turns.append(
                (
                    AgentConversationHistoryPlanTurnV3
                    if include_turn_correlation else AgentConversationHistoryTurnV2
                )(
                    **values,
                    plan_context=project_plan_turn_context(
                        turn, delivery_replay=False
                    ),
                )
            )
        else:
            turn_model = (
                AgentConversationHistoryTurnV3
                if include_turn_correlation else AgentConversationHistoryTurn
            )
            history_turns.append(turn_model(**values))
    if include_turn_correlation:
        response_model = AgentConversationHistoryResponseV3
    elif contains_plan_context:
        response_model = AgentConversationHistoryResponseV2
    else:
        response_model = AgentConversationHistoryResponse
    return response_model(
        world_id=verified_world_id,
        conversation_state="active",
        conversation_id=conversation.conversation_id,
        active_conversation_id=pointer.active_conversation_id,
        pointer_revision=pointer.revision,
        turns=history_turns,
        # before_sequence is exclusive; using the first visible sequence gives
        # the caller the next older page without exposing repository ordering.
        next_before_sequence=(
            turns[0].sequence if len(turns) == limit and turns else None
        ),
    )


@router.post(
    "/worlds/{world_id}/conversation/new",
    response_model=AgentNewConversationResponse,
)
def post_new_world_conversation(
    world_id: str,
    body: AgentNewConversationRequest,
    request: Request,
) -> AgentNewConversationResponse:
    enforce_native_graph_gm(request)
    verified_world_id = _verified_world_id(world_id)
    service = _conversation_service(request)
    try:
        receipt = service.new_conversation(
            ConversationCommand(
                world_id=verified_world_id,
                command_id=body.command_id,
                expected_pointer_revision=body.expected_pointer_revision,
                expected_active_conversation_id=body.expected_active_conversation_id,
            )
        )
    except ApplicationStateError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": "conversation_command_rejected", "message": str(exc)},
        ) from exc
    return AgentNewConversationResponse(
        world_id=verified_world_id,
        conversation_id=receipt.conversation_id,
        active_conversation_id=receipt.active_conversation_id,
        pointer_revision=receipt.pointer_revision,
    )


@router.post("/turn", response_model=None)
def post_agent_turn(body: AgentTurnRequest, request: Request) -> dict[str, Any]:
    # Authorization is a prerequisite for every turn, including Graph none.
    # It runs before World/receipt/DB resolution and before runtime lookup.
    trace = AgentTurnTraceBuilder(
        agent_thread_id=None,
        turn_id=body.turn_id,
        runtime="unresolved",
        backend="unresolved",
        mode="unresolved",
    )
    auth_span = trace.start_phase("route_auth")
    try:
        try:
            enforce_native_graph_gm(request)
        except Exception:
            trace.complete_phase(auth_span, status="error")
            raise
        trace.complete_phase(auth_span)

        result = execute_agent_turn(
            body,
            root=repo_root(),
            pointer_store=HermesSessionPointerStore(session_dir()),
            owner_resolver=_owner_resolver,
            work_resolver=_work_resolver,
            historical_work_resolver=_historical_work_resolver,
            graph_resolver=_graph_resolver,
            plan_graph_resolver=lambda turn, owner, work, receipt, parent_span_id: _plan_context_resolver(
                turn, owner, work, receipt, trace=trace,
                parent_span_id=parent_span_id,
            ),
            runtime_factory=lambda: getattr(
                request.app.state, "agent_turn_runtime", None
            ),
            conversation_service=_conversation_service(request),
            trace_builder=trace,
        )
        _finalize_unlogged_agent_trace(trace, status="ok")
        return result.model_dump(mode="json", by_alias=True)
    except AgentTurnServiceError as exc:
        _finalize_unlogged_agent_trace(trace, status="error")
        if body.plan_context_policy is not None and exc.provider_dispatched is False:
            mapping = _PLAN_PREDISPATCH_FAILURES.get(exc.code)
            if mapping is not None:
                failure_code, status_code = mapping
                raise HTTPException(
                    status_code=status_code,
                    detail={
                        "code": failure_code,
                        "message": str(exc),
                        "plan_context_failure": {
                            "schema": "dmb_plan_world_graph_context_failure_v1",
                            "status": "pre_dispatch_failed",
                            "failure_code": failure_code,
                            "provider_dispatched": False,
                            "automatic_downgrade": False,
                        },
                    },
                ) from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValidationError as exc:
        _finalize_unlogged_agent_trace(trace, status="error")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ApplicationStateError as exc:
        _finalize_unlogged_agent_trace(trace, status="error")
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": "conversation_unavailable", "message": str(exc)},
        ) from exc
    except HTTPException:
        _finalize_unlogged_agent_trace(trace, status="error")
        raise
    except Exception:
        _finalize_unlogged_agent_trace(trace, status="error")
        raise
