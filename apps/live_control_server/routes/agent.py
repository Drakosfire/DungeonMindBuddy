"""Additive universal Agent route, mounted below the established /api/live router."""

from __future__ import annotations

from apps.live_control_server.services.session_evidence import playing_session_evidence

from contextlib import nullcontext
from hashlib import sha256
from typing import Any, Literal, Mapping
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptPdfStatblockReviewRequestV1,
)
from apps.live_control_server.models.statblock_saved_revision import AppendPdfStatblockReviewRequest
from apps.live_control_server.services.conversation_variant_save import CorrectConversationVariant
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application_state.agent_conversation.lore_page_confirmation import LorePageConfirmation
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.services.rules_answer_presentation import project_rules_answer_context
from application_state.agent_conversation.types import BuildGraphContextReceiptV1, PlayWorldGraphContextReceiptV1, ConversationCommand, CommandResolutionRequestV1, PlayGraphBindingReceiptV1, PlayRunTurnContextReceiptV2, TurnProvenance, decode_play_run_turn_context_references, request_fingerprint
from application_state.plan_action_dialogue.authoring_review import (
    PlanAuthoringReviewV1, PlanReviewSnapshotV1, PlanReviewCommand,
)
from application_state.errors import ApplicationStateError

from apps.live_control_server.config import (
    ManagedWorldDataRootError,
    managed_world_data_root,
    repo_root,
    session_dir,
    world_graph_root,
)
from apps.live_control_server.services.build_pdf_ocr import read_crop_png, read_grounded_artwork
from apps.live_control_server.models.build_document_proposal import BuildDocumentProposalRequest
from apps.live_control_server.models.agent_turn import (
    AgentConversationHistoryResponse,
    AgentConversationHistoryBuildTurnV2,
    AgentConversationHistoryBuildTurnV3,
    AgentConversationHistoryResponseV2,
    AgentConversationHistoryResponseV3,
    AgentConversationHistoryResponseV4,
    AgentConversationHistoryMixedTurnV1,
    AgentConversationHistoryPlayRulesTurnV1, AgentConversationHistoryPlaySourceTurnV1,
    AgentConversationHistoryPlanTurnV3,
    AgentConversationHistoryPlayTurnV2,
    AgentConversationHistoryPlayTurnV3,
    AgentConversationHistoryTurn,
    AgentConversationHistoryTurnV2,
    AgentConversationHistoryTurnV3,
    AgentNewConversationRequest,
    AgentNewConversationResponse,
    AgentNewConversationStatusV1,
    AgentNewConversationReceiptV1,
    AgentCommandResolutionResponseV1,
    AgentTurnContentBasis,
    AgentTurnRequest,
    AgentTurnContextTraceResponseV1,
    AgentHistoricalSourcePassageResponseV1,
)
from apps.live_control_server.services.agent_runtime import (
    AgentCurrentWorkContext,
    AgentSurfaceContext,
)
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services.agent_play_surface_context import (
    WorldPlaySurfaceContextError,
    resolve_historical_world_play_turn_snapshot,
    resolve_world_play_session_turn_snapshot,
)
from apps.live_control_server.services.agent_turn_trace import AgentTurnTraceBuilder
from apps.live_control_server.services.agent_turn_service import (
    AgentPlanWorldGraphBootstrap,
    BuildSavedSourceBasis,
    BuildGraphBinding,
    validate_build_source_reference,
    AgentTurnResolvedWork,
    AgentTurnServiceError,
    build_existing_graph_context,
    execute_agent_turn,
    project_plan_turn_context,
    project_play_turn_context,
)
from apps.live_control_server.services.agent_runtime import AgentWorldScope
from apps.live_control_server.services.agent_world_graph_query_context import (
    adapt_projection_to_agent_envelope,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    ManagedWorldGraphProjectionRequest,
    project_managed_world_graph,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
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
    get_committed_page_snapshot,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)


router = APIRouter(prefix="/agent", tags=["agent-turn"])


@router.get("/readiness")
def get_agent_readiness(request: Request, surface: Literal["build", "plan", "play"],
                        world_graph: bool = True, world_id: str | None = None):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id or "", authorize_local=enforce_native_graph_gm)
    from apps.live_control_server.services.agent_readiness import agent_readiness
    return agent_readiness(surface=surface, world_graph=world_graph,
                           build_runtime=getattr(request.app.state, "build_jev_runtime_factory", None))


def _finalize_unlogged_agent_trace(
    trace: AgentTurnTraceBuilder, *, status: str,
) -> None:
    if not trace.logged:
        trace.finalize_and_log(status=status)


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
        _managed_world_root()
        record = get_world_container(owner.world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code=("graph_unavailable" if exc.status_code == 503 else "world_owner_unavailable"),
            status_code=exc.status_code,
        ) from exc
    return {"kind": "world", "id": record.world_id, "name": record.name}


def _build_work_resolver(body: AgentTurnRequest, owner: Mapping[str, Any] | None) -> AgentTurnResolvedWork:
    locator = body.primary_work
    if (locator is None or locator.kind != "build" or body.surface.surface_id != "build"
        or owner is None or owner.get("kind") != "world" or not owner.get("id")):
        raise AgentTurnServiceError("Build requires a verified World source", code="build_source_unavailable", status_code=403)
    try:
        snapshot = get_committed_page_snapshot(_managed_world_root(), locator.object_id)
    except WorkspaceDocumentRegistryError as exc:
        raise AgentTurnServiceError("The saved source is unavailable", code="build_source_unavailable", status_code=exc.status_code) from exc
    record = snapshot.record
    digest = sha256(snapshot.markdown.encode("utf-8")).hexdigest()
    if (record.kind != "worldbuilding_source" or record.status != "active"
        or record.content_status != "committed" or record.world_id != owner["id"]
        or record.document_id != locator.object_id or record.revision != locator.expected_revision
        or snapshot.loaded_revision != record.revision
        or digest != snapshot.content_sha256 or digest != locator.expected_content_sha256
        or record.source_domain != "worldbuilding" or not record.document_class
        or record.authority_state not in {"draft", "reviewed", "canonical"}
        or record.visibility_state not in {"internal", "player_safe"}):
        raise AgentTurnServiceError("The saved Build source changed or is not available in this World", code="build_source_unavailable", status_code=409)
    basis = BuildSavedSourceBasis(record.document_id, str(owner["id"]), record.revision, digest,
        record.title, record.source_domain, record.document_class, record.authority_state,
        record.visibility_state, snapshot.markdown)
    return AgentTurnResolvedWork(kind="build", object_id=record.document_id, revision=record.revision,
        changed_since_expected=False, owner_kind="world", owner_id=str(owner["id"]),
        world_id=str(owner["id"]), build_source=basis,
        surface_context=AgentSurfaceContext(surface_id="build", current_work=AgentCurrentWorkContext(
            kind="build", work_object_id=record.document_id, title=record.title,
            object_revision=record.revision, target_session=None)))


def _planning_session_evidence(body,owner,provenance=None):
    if body.surface.surface_id!="plan" or not owner or owner.get("kind")!="world":return None
    from apps.live_control_server.services.session_evidence import planning_session_evidence
    return planning_session_evidence(str(owner["id"]),provenance)


def _work_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
) -> AgentTurnResolvedWork | None:
    locator = body.primary_work
    if locator is None:
        return None
    if locator.kind == "build":
        return _build_work_resolver(body, owner)
    if locator.kind == "run" and body.surface.surface_id == "play":
        if owner is None or owner.get("kind") != "world" or not owner.get("id"):
            raise AgentTurnServiceError("A Play Run requires a verified World.", code="world_owner_unverified", status_code=403)
        try:
            if locator.play_content_basis is None:
                raise WorldPlaySurfaceContextError("Refresh Play to bind the saved session content before asking Buddy")
            context, receipt = resolve_world_play_session_turn_snapshot(
                root=_managed_world_root(), world_id=str(owner["id"]),
                run_id=locator.object_id, run_revision=locator.expected_revision,
                content_basis=locator.play_content_basis,
            )
        except (WorldPlaySurfaceContextError, WorkspaceDocumentRegistryError, WorldContainerRegistryError, ValueError) as exc:
            detail = str(exc) if isinstance(exc, WorldPlaySurfaceContextError) else "The exact saved Play session is unavailable"
            raise AgentTurnServiceError(f"{detail}. Reopen Play to refresh the saved session context.", code="play_context_unavailable", status_code=409, provider_dispatched=False) from exc
        return AgentTurnResolvedWork(
            kind="run", object_id=receipt.run_id, revision=receipt.run_revision,
            changed_since_expected=False, owner_kind="world", owner_id=str(owner["id"]),
            world_id=str(owner["id"]), surface_context=context,
            play_context_receipt=receipt,
            session_evidence=playing_session_evidence(str(owner["id"]),receipt),
        )
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
            session_evidence=_planning_session_evidence(body,owner),
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
    *, play_context_receipt: PlayRunTurnContextReceiptV2 | None = None,
) -> AgentTurnResolvedWork | None:
    """Load retry content from its frozen WorkRevision, never today's pointer."""
    reference = provenance.primary_work
    if reference.resolution == "absent":
        return None
    locator = body.primary_work
    if reference.kind == "build":
        try:
            document_id, revision, digest, visibility = validate_build_source_reference(provenance)
        except ValueError as exc:
            raise AgentTurnServiceError(str(exc), code="turn_receipt_unverifiable", status_code=409) from exc
        if (locator is None or locator.kind != "build" or locator.object_id != document_id
            or locator.expected_revision != revision or locator.expected_content_sha256 != digest
            or owner is None or owner.get("id") != provenance.world_id):
            raise AgentTurnServiceError("Build retry does not match its frozen source", code="turn_receipt_unverifiable", status_code=409)
        work = _build_work_resolver(body, owner)
        if work.build_source is None or work.build_source.visibility_state != visibility:
            raise AgentTurnServiceError("Build source visibility changed", code="historical_work_unavailable", status_code=409)
        return work
    if locator is not None and locator.kind == "run" and body.surface.surface_id == "play":
        try:
            receipt = decode_play_run_turn_context_references(reference, provenance.supporting_work)
        except ValueError as exc:
            raise AgentTurnServiceError("The historical Play receipt is malformed.", code="turn_receipt_unverifiable", status_code=409) from exc
        if (
            receipt is None or owner is None or owner.get("kind") != "world"
            or owner.get("id") != provenance.world_id
            or receipt.run_id != locator.object_id
            or receipt.run_revision != locator.expected_revision
        ):
            raise AgentTurnServiceError("The historical Play receipt does not match its World or Run.", code="turn_receipt_unverifiable", status_code=409)
        if play_context_receipt is not None:
            receipt = play_context_receipt
            if receipt.world_id != provenance.world_id:
                raise AgentTurnServiceError("Historical session context World differs", code="turn_receipt_unverifiable", status_code=409)
        try:
            context = resolve_historical_world_play_turn_snapshot(
                root=_managed_world_root(), world_id=provenance.world_id, receipt=receipt,
            )
        except (WorldPlaySurfaceContextError, WorkspaceDocumentRegistryError, WorldContainerRegistryError) as exc:
            raise AgentTurnServiceError("The historical Play Runbook is unavailable.", code="historical_work_unavailable", status_code=409) from exc
        return AgentTurnResolvedWork(
            kind="run", object_id=receipt.run_id, revision=receipt.run_revision,
            changed_since_expected=False, owner_kind="world", owner_id=provenance.world_id,
            world_id=provenance.world_id, surface_context=context,
            play_context_receipt=receipt,
            session_evidence=playing_session_evidence(provenance.world_id,receipt,provenance),
        )
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
        session_evidence=_planning_session_evidence(body,owner,provenance),
    )


def _graph_resolver(
    body: AgentTurnRequest,
    owner: Mapping[str, Any] | None,
    work: AgentTurnResolvedWork | None,
    *,
    expected_play_binding: PlayGraphBindingReceiptV1 | BuildGraphBinding | None = None,
) -> tuple[dict[str, Any], Any]:
    graph = body.graph_request
    if graph.mode == "none":
        raise AgentTurnServiceError(
            "Graph was not requested.", code="graph_not_requested"
        )
    if body.surface.surface_id in {"play", "build"} and body.primary_work is not None:
        if (
            graph.mode != "world" or owner is None
            or owner.get("kind") != "world" or owner.get("id") != graph.world_id
            or work is None or work.kind != ("build" if body.surface.surface_id == "build" else "run") or work.world_id != graph.world_id
            or graph.campaign_id is not None or graph.focus.kind != "none"
            or body.graph_selection is not None
        ):
            raise AgentTurnServiceError(
                "Play Graph requires the exact resolved Run and owner World.",
                code="graph_scope_rejected", status_code=403,
            )
        try:
            current_binding = None
            if expected_play_binding is not None:
                current_binding = resolve_managed_world_binding(
                    graph.world_id, root=_managed_world_root(),
                )
                if (
                    current_binding.managed_world_id != expected_play_binding.managed_world_id
                    or current_binding.native_world_id != expected_play_binding.native_world_id
                    or current_binding.binding_version != expected_play_binding.binding_version
                ):
                    raise AgentTurnServiceError(
                        "The native World Graph binding changed after turn acceptance.",
                        code="turn_receipt_unverifiable", status_code=409,
                    )
            bound = project_managed_world_graph(
                ManagedWorldGraphProjectionRequest(
                    schema_="dmb_managed_world_graph_projection_request_v1",
                    managed_world_id=graph.world_id,
                    revision_pin=graph.revision_pin,
                    query_text=body.message,
                ),
                root=_managed_world_root(),
                expected_binding=current_binding,
            )
        except WorldGraphProjectionServiceError as exc:
            raise AgentTurnServiceError(
                "The managed World Graph binding or revision is unavailable.",
                code="graph_unavailable", status_code=(
                    exc.status_code if exc.status_code in {404, 409, 503} else 503
                ),
            ) from exc
        envelope = adapt_projection_to_agent_envelope(
            bound.projection, query_text=body.message,
        )
        if (
            bound.managed_world_id != graph.world_id
            or envelope.get("world_id") != bound.native_world_id
            or envelope.get("scope_mode") != "world"
            or envelope.get("admissibility") != "gm"
        ):
            raise AgentTurnServiceError(
                "The native Graph projection does not match its verified binding.",
                code="graph_scope_rejected", status_code=409,
            )
        envelope["managed_world_id"] = bound.managed_world_id
        envelope["binding_version"] = bound.binding_version
        return envelope, AgentWorldScope(
            world_id=bound.native_world_id,
            campaign_id="", focus=envelope["focus"], admissibility="gm",
            revision_id=str(envelope.get("revision_id") or ""), scope_mode="world",
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
            _managed_world_root()
            get_world_container(requested_world_id)
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
    managed_world_id: str, turn_id: str, graph_revision: str, request_digest: str,
) -> tuple[str, str]:
    identity = f"{managed_world_id}:{turn_id}:{graph_revision}:{request_digest}"
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
    frozen_source_scope: Any | None = None,
    native_source_context=None, native_query_mode=False, native_principal=None,
) -> AgentPlanWorldGraphBootstrap:
    """Resolve one source-free, revision-pinned DungeonMind retrieval packet."""
    if native_query_mode:
        from apps.live_control_server.services.native_graph_reads import prepare_query
        if owner is None or owner.get('kind') != 'world' or work is None or work.world_id != owner.get('id') or body.surface.surface_id not in {'plan', 'build', 'play'}:
            raise AgentTurnServiceError('Native query scope differs from saved work.', code='plan_context_scope_rejected', status_code=403)
        from application_state.agent_conversation.native_plan_statements import NativePlanQueryV1
        frozen_query = getattr(frozen_receipt, 'native_query', None)
        try:
            context, query = prepare_query(work.world_id, body.message, native_principal,
                source_context=native_source_context,
                authored_references=body.build_authored_references if body.surface.surface_id == 'build' else body.authored_references,
                revision_id=frozen_query.authority.revision_id if isinstance(frozen_query, NativePlanQueryV1) else None)
        except ValueError as exc:
            raise AgentTurnServiceError('The selected native Graph scope or reference could not be verified.',
                code='native_graph_query_rejected',status_code=409,provider_dispatched=False) from exc
        if type(frozen_query) is NativePlanQueryV1 and isinstance(query, NativePlanQueryV1):
            from dataclasses import replace
            query = NativePlanQueryV1.model_validate(query.model_dump(mode='json', by_alias=True, exclude={'assertion_matches','authored_targets','object_matches','discovery_hops'}) | {'schema': 'dmb_native_plan_query_v1'})
            context = replace(context, query=query)
        elif hasattr(query, 'discovery_hops') and isinstance(frozen_query, NativePlanQueryV1):
            from dataclasses import replace
            # Retry reopens the original retrieval rather than recording a new discovery.
            query = query.model_copy(update={'discovery_hops': getattr(frozen_query, 'discovery_hops', ())})
            context = replace(context, query=query)
        return context, query

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
        list_source_anchor_index_direct_v2,
        list_selected_source_anchor_index_direct_v1,
        search_world_graph_direct_v2,
    )
    from apps.live_control_server.services.agent_plan_playable_target import (
        AgentPlanPlayableTargetError,
        selected_plan_graph_seed_candidates,
    )
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
    )
    from apps.live_control_server.services.agent_runtime import AgentWorldScope

    managed_world_id = str(owner.get("id")) if owner is not None else ""
    if (
        owner is None
        or owner.get("kind") != "world"
        or not managed_world_id
        or work is None
        or work.kind not in {"plan", "build", "run"}
        or (work.kind == "build" and work.build_source is None)
        or (work.kind == "run" and (
            body.surface.surface_id != "play"
            or body.play_target is None
            or work.play_context_receipt is None
        ))
        or work.world_id != managed_world_id
    ):
        raise AgentTurnServiceError(
            "The governed Graph turn requires saved work owned by the verified World.",
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
    try:
        initial = get_world_container(managed_world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            str(exc),
            code="world_owner_unavailable",
            status_code=exc.status_code,
            provider_dispatched=False,
        ) from exc
    binding = initial.native_graph_binding
    if (
        binding is None
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
            candidates = (
                ()
                if work.kind == "run"
                else selected_plan_graph_seed_candidates(
                    body.playable_target, work.plan_markdown or ""
                )
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
        current = get_world_container(managed_world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval.",
            code="native_graph_binding_changed",
            status_code=409,
            provider_dispatched=False,
        ) from exc
    current_binding = current.native_graph_binding
    if (
        current_binding is None
        or current_binding.status != "active"
        or current_binding.native_world_id != native_world_id
        or current_binding.binding_version != binding.binding_version
    ):
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval; retry the turn.",
            code="native_graph_binding_changed",
            status_code=409,
            provider_dispatched=False,
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
    assembler_version = (
        "agent_harness_final_request_v2" if frozen_receipt is None
        else frozen_receipt.assembled_input.assembler_version
    )
    if assembler_version not in {
        "agent_harness_final_request_v1", "agent_harness_final_request_v2",
    }:
        raise AgentTurnServiceError(
            "The stored initial claim assembler version is unsupported.",
            code="turn_receipt_unverifiable", status_code=409,
            provider_dispatched=False,
        )
    claims = claims_from_retrieval_result(
        packet, revision_id=revision_id,
        include_attribute_evidence_refs=(assembler_version == "agent_harness_final_request_v2"),
    )
    evidence_by_anchor = {
        anchor.anchor_id: anchor.evidence_ref_id
        for anchor in result.source_anchors
        if anchor.anchor_id and anchor.evidence_ref_id
    }
    stored_selection_policy = (
        None if frozen_receipt is None
        else frozen_receipt.graph_packet.selection_policy_version
    )
    if stored_selection_policy not in {
        None,
        "parent_initial_retrieval_v1",
        "parent_initial_retrieval_with_bounded_source_index_v1",
        "parent_initial_retrieval_with_selected_source_index_v1",
    }:
        raise AgentTurnServiceError(
            "The stored Graph selection policy cannot be safely reconstructed.",
            code="turn_receipt_unverifiable", status_code=409,
            provider_dispatched=False,
        )
    use_bounded_index = stored_selection_policy == "parent_initial_retrieval_with_bounded_source_index_v1"
    # Run work was already admitted with its Play surface/target above. Plan
    # Action search intents intentionally carry no conversational surface.
    native_play_scope = work.kind == "run"
    if native_play_scope and stored_selection_policy == "parent_initial_retrieval_with_selected_source_index_v1":
        raise AgentTurnServiceError(
            "The stored Play source scope uses an unsupported selected-index policy.",
            code="turn_receipt_unverifiable", status_code=409,
            provider_dispatched=False,
        )
    use_selected_index = not native_play_scope and (
        stored_selection_policy == "parent_initial_retrieval_with_selected_source_index_v1" or (
            stored_selection_policy is None and bool(resolved_search.native_targets)
        )
    )
    source_scope_anchors: list[dict[str, str]] = []
    source_index_commitment: dict[str, Any] | None = None
    try:
        if use_selected_index:
            from dungeonmind.application.world_graph_retrieval import EvidenceTarget
            from application_state.agent_conversation.types import GraphSelectedSourceReadScopeV2
            targets = resolved_search.native_targets
            if stored_selection_policy is not None:
                if not isinstance(frozen_source_scope, GraphSelectedSourceReadScopeV2):
                    raise AgentTurnServiceError("The stored selected source scope is unavailable.", code="turn_receipt_unverifiable", status_code=409, provider_dispatched=False)
                targets = tuple(EvidenceTarget(kind=target.kind, target_id=target.target_id)
                    for target in frozen_source_scope.selected_index_commitment.requested_targets)
            index = list_selected_source_anchor_index_direct_v1(services, request, revision_id=revision_id, targets=targets)
            if index.status == "overflow":
                raise AgentTurnServiceError("The selected source scope exceeds 512 anchors.", code="graph_evidence_invalid", status_code=502, provider_dispatched=False)
            source_index_commitment = dict(index.commitment)
            if frozen_source_scope is not None and source_index_commitment != frozen_source_scope.selected_index_commitment.model_dump(mode="json", by_alias=True):
                raise AgentTurnServiceError("The selected index differs from its frozen commitment.", code="turn_receipt_unverifiable", status_code=409, provider_dispatched=False)
            indexed = {pin.anchor_id: pin for pin in index.source_pins}
            for pin in resolved_search.source_pins:
                if pin.anchor_id in indexed and indexed[pin.anchor_id] != pin:
                    raise ValueError("selected source pin differs from initial read")
            source_pins = index.source_pins
        elif use_bounded_index:
            index = list_source_anchor_index_direct_v2(
                services, request, revision_id=revision_id,
            )
            if index.status != "complete":
                raise AgentTurnServiceError(
                    "The pinned source-anchor index exceeds the 512-anchor limit.",
                    code="graph_evidence_invalid", status_code=502,
                    provider_dispatched=False,
                )
            index_by_id = {pin.anchor_id: pin for pin in index.source_pins}
            for pin in resolved_search.source_pins:
                if index_by_id.get(pin.anchor_id) != pin:
                    raise ValueError("initial search source pin differs from the complete native index")
            source_pins = index.source_pins
        else:
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
            source_pins = resolved_search.source_pins if stored_selection_policy is not None else ()
        for pin in source_pins:
            source_scope_anchors.append({
                "anchor_id": pin.anchor_id,
                "evidence_ref_id": pin.evidence_ref_id,
                "source_artifact_id": pin.source_artifact_id,
                "source_revision_id": pin.source_revision_id,
            })
        if use_bounded_index and source_scope_anchors:
            source_index_commitment = {
                "schema": "dmb_bounded_source_anchor_index_commitment_v1",
                "world_id": native_world_id,
                "graph_revision": revision_id,
                "status": index.status,
                "max_entries": 512,
                "eligible_count": index.eligible_count,
                "source_pins": [dict(pin) for pin in source_scope_anchors],
            }
    except AgentTurnServiceError:
        raise
    except Exception as exc:
        raise AgentTurnServiceError(
            "The pinned source-anchor metadata could not be resolved.",
            code="graph_evidence_invalid", status_code=502,
            provider_dispatched=False,
        ) from exc
    # A safely reclaimed V2 turn must reconstruct the same initial provider
    # envelope after process restart; both handles appear in that envelope.
    request_identity = body.model_dump_json(by_alias=True).encode("utf-8")
    native_play = native_play_scope
    if use_bounded_index or use_selected_index or native_play:
        request_identity += b"\x00" + (
            (work.plan_markdown or "").encode("utf-8")
            if work.kind != "run"
            else work.play_context_receipt.model_dump_json(by_alias=True).encode("utf-8")
        )
    source_session_id, initial_operation_id = (
        _source_session_handles(
            managed_world_id, body.turn_id, revision_id,
            sha256(request_identity).hexdigest(),
        )
        if source_scope_anchors or native_play else (None, f"op:{uuid4().hex[:12]}")
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
    build_discovery = None
    if work.build_source is not None:
        from apps.live_control_server.services.build_source_discovery import discover_build_source
        try:
            build_discovery = discover_build_source(services, work.build_source,
                native_world_id=native_world_id, graph_revision=revision_id)
        except Exception as exc:
            raise AgentTurnServiceError("The exact saved source discovery could not be resolved.",
                code="graph_unavailable", status_code=503, provider_dispatched=False) from exc
    # Source-index construction can outlive the earlier binding check. Reject
    # a retargeted World before creating a durable retrieval session.
    try:
        final_world = get_world_container(managed_world_id)
    except WorldContainerRegistryError as exc:
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval.",
            code="native_graph_binding_changed", status_code=409,
            provider_dispatched=False,
        ) from exc
    final_binding = final_world.native_graph_binding
    if (
        final_world.world_id != managed_world_id
        or final_binding is None
        or final_binding.status != "active"
        or final_binding.native_world_id != native_world_id
        or final_binding.binding_version != binding.binding_version
    ):
        raise AgentTurnServiceError(
            "Managed World binding changed during Graph retrieval; retry the turn.",
            code="native_graph_binding_changed", status_code=409,
            provider_dispatched=False,
        )
    session = _store_plan_retrieval_session(
        session, reusable_source_session=source_session_id is not None,
    )
    bootstrap = AgentPlanWorldGraphBootstrap(
        completed_discovery_query=body.message if not valid_seeds else None,
        build_source_discovery=build_discovery,
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
        candidate_assertion_ids=tuple(sorted({item.assertion_id for item in result.attributes})),
        candidate_relationship_ids=tuple(sorted({item.edge_id for item in result.relationships})),
        candidate_evidence_ref_ids=tuple(sorted({
            item["evidence_ref_id"] for item in source_scope_anchors
        } | {
            item.evidence_ref_id for item in result.source_anchors
        })),
        evidence_by_anchor_id=evidence_by_anchor,
        assembler_version=assembler_version,
        source_scope_anchors=tuple(source_scope_anchors),
        source_index_commitment=source_index_commitment,
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
        _managed_world_root()
        return get_world_container(world_id).world_id
    except WorldContainerRegistryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": "world_owner_unavailable", "message": str(exc)},
        ) from exc


@router.get("/worlds/{world_id}/plan-proposals/{action_id}/review",
    response_model=PlanReviewSnapshotV1)
def get_plan_authoring_review(world_id: str, action_id: UUID, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    if request.query_params:
        raise HTTPException(status_code=422, detail="Plan proposal does not accept query selectors")
    verified = _verified_world_id(world_id)
    from application_state.plan_action_dialogue.authoring_review import read_review
    try:
        result = read_review(verified, action_id)
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
        return result
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,
            detail={"code": "plan_authoring_review_unavailable", "message": str(exc)}) from exc


@router.post("/worlds/{world_id}/plan-proposals/{action_id}/review",
    response_model=PlanAuthoringReviewV1)
def post_plan_authoring_review(
    world_id: str, action_id: UUID, command: PlanReviewCommand, request: Request,
):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    if request.query_params:
        raise HTTPException(status_code=422, detail="Plan proposal does not accept query selectors")
    verified = _verified_world_id(world_id)
    from application_state.plan_action_dialogue.authoring_review import execute_review_command
    try:
        from functools import partial

        authorize_world = partial(
            require_conversation_access, request, world_id, authorize_local=enforce_native_graph_gm,
        )
        result = execute_review_command(verified, action_id, command, authorize_world=authorize_world)
        authorize_world()
        return result
    except ApplicationStateError as exc:
        code = ("plan_authoring_review_conflict" if exc.status_code == 409
            else "plan_authoring_review_unavailable")
        raise HTTPException(status_code=exc.status_code,
            detail={"code": code, "message": str(exc)}) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={
            "code": "plan_authoring_review_invalid",
            "message": "The complete Plan working copy is invalid; retain it for correction.",
        }) from exc


@router.get(
    "/worlds/{world_id}/conversation",
    # The response is selected per snapshot when it contains a policy turn.
    # A fixed v1 model would reject the additive plan_context payload.
    response_model=(
        AgentConversationHistoryResponse
        | AgentConversationHistoryResponseV2
        | AgentConversationHistoryResponseV3
        | AgentConversationHistoryResponseV4
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
    | AgentConversationHistoryResponseV4
):
    # Authenticate before managed World lookup and every APP-STATE read.
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
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
    from apps.live_control_server.services.play_source_presentation import project_play_source_context
    def source_only_play(turn):
        meta = turn.envelope if isinstance(turn,MixedCompletedTurnV1) else turn
        return (meta.provenance.surface_id == "play" and meta.play_context_receipt is not None
            and (turn.base_projection.kind == "absent" if isinstance(turn,MixedCompletedTurnV1) else turn.graph_context_receipt is None))
    contains_play_source = any(source_only_play(turn) for turn in turns)
    contains_mixed = any(isinstance(turn, MixedCompletedTurnV1) for turn in turns)
    from application_state.agent_conversation.native_statement_input import NativeStatementContextReceiptV1
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1, BuildWorkContextV1, PlayWorkContextV1
    def has_play_context(turn):
        receipt = turn.graph_context_receipt
        return isinstance(receipt, PlayWorldGraphContextReceiptV1) or (
            isinstance(receipt, SurfaceNativeContextReceiptV1)
            and isinstance(receipt.work_context, PlayWorkContextV1)
        )
    contains_play_context = any(
        not isinstance(turn, MixedCompletedTurnV1) and has_play_context(turn)
        for turn in turns
    )
    from apps.live_control_server.models.agent_turn import AgentConversationHistoryNativeStatementTurnV1
    contains_native_statement = any(not isinstance(turn, MixedCompletedTurnV1)
        and isinstance(turn.graph_context_receipt, NativeStatementContextReceiptV1) for turn in turns)
    contains_plan_context = any(
        not isinstance(turn, MixedCompletedTurnV1)
        and turn.graph_context_receipt is not None
        and not has_play_context(turn)
        for turn in turns
    )
    from apps.live_control_server.services.agent_source_names import source_names_for_turns
    source_names = source_names_for_turns(turns)
    from apps.live_control_server.services.agent_turn_service import project_plan_authoring_proposal
    from application_state.agent_conversation.authored_graph_references import reference_input
    def plan_operation_for_turn(turn):
        from application_state.agent_conversation.native_execution import NativePlanActionV1
        actual = getattr(turn.base_projection, 'turn', None) if isinstance(turn, MixedCompletedTurnV1) else turn
        execution = getattr(actual, 'graph_context_execution', None)
        action = getattr(getattr(execution, 'policy', None), 'action', None)
        return action.intent.plan_requested_operation if isinstance(action, NativePlanActionV1) and hasattr(action.intent, 'plan_requested_operation') else None

    completed_build_turn_ids = [
        turn.turn_id for turn in turns
        if not isinstance(turn, MixedCompletedTurnV1)
        and turn.status == "completed"
        and turn.provenance.surface_id == "build"
    ]
    draft_turn_ids = service.conversation_draft_turn_ids(
        verified_world_id, conversation.conversation_id, completed_build_turn_ids,
    ) if completed_build_turn_ids else set()
    reviewed_variant_ids = service.reviewed_variant_turn_ids(
        verified_world_id, conversation.conversation_id, completed_build_turn_ids,
    ) if completed_build_turn_ids else set()
    from application_state.agent_conversation.conversation_variant_save import requested_approval

    history_turns = []
    for turn in turns:
        if isinstance(turn, MixedCompletedTurnV1):
            envelope = turn.envelope
            mixed_model = AgentConversationHistoryPlayRulesTurnV1 if source_only_play(turn) else AgentConversationHistoryMixedTurnV1
            history_turns.append(mixed_model(
                variant_approval_requested=True if requested_approval(turn) else None,
                turn_id=envelope.turn_id, sequence=envelope.sequence,
                lifecycle_status=envelope.status, user_text=envelope.user_text,
                assistant_text=turn.assistant_text, provenance=envelope.provenance,
                idempotency_key=envelope.idempotency_key,
                plan_proposal=project_plan_authoring_proposal(turn, service=service),
                rules_context=project_rules_answer_context(turn, delivery_replay=True, source_names=source_names),
                authored_references=reference_input(turn),
                plan_requested_operation=plan_operation_for_turn(turn),
                **({"play_source_context":project_play_source_context(turn,delivery_replay=True)} if source_only_play(turn) else {})))
            continue
        values = {
            "authored_references": reference_input(turn),
            "plan_requested_operation": plan_operation_for_turn(turn),
            "plan_proposal": project_plan_authoring_proposal(turn, service=service),
            "turn_id": turn.turn_id,
            "sequence": turn.sequence,
            "lifecycle_status": turn.status,
            "user_text": turn.user_text,
            "assistant_text": turn.assistant_text,
            "provenance": turn.provenance,
        }
        if include_turn_correlation or source_only_play(turn) or isinstance(turn.graph_context_receipt, NativeStatementContextReceiptV1):
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
        if isinstance(turn.graph_context_receipt, NativeStatementContextReceiptV1):
            history_turns.append(AgentConversationHistoryNativeStatementTurnV1(**values,
                native_statement_context={"receipt": turn.graph_context_receipt,
                    "completion": turn.completion, "delivery_replay": True}))
        elif source_only_play(turn):
            history_turns.append(AgentConversationHistoryPlaySourceTurnV1(**values,
                play_source_context=project_play_source_context(turn,delivery_replay=True)))
        elif isinstance(turn.graph_context_receipt, BuildGraphContextReceiptV1) or (
            isinstance(turn.graph_context_receipt, SurfaceNativeContextReceiptV1)
            and isinstance(turn.graph_context_receipt.work_context, BuildWorkContextV1)
        ):
            build_model = AgentConversationHistoryBuildTurnV3 if include_turn_correlation else AgentConversationHistoryBuildTurnV2
            history_turns.append(build_model(**values,
                conversation_draft_available=True if turn.turn_id in draft_turn_ids else None,
                variant_draft_reviewed=True if turn.turn_id in reviewed_variant_ids else None,
                variant_approval_requested=True if requested_approval(turn) else None,
                knowledge_context=project_plan_turn_context(turn, delivery_replay=True, source_names=source_names)))
        elif has_play_context(turn):
            play_model = (
                AgentConversationHistoryPlayTurnV3
                if include_turn_correlation
                else AgentConversationHistoryPlayTurnV2
            )
            history_turns.append(
                play_model(
                    **values,
                    play_context=project_play_turn_context(
                        turn, delivery_replay=True
                    ),
                )
            )
        elif turn.graph_context_receipt is not None:
            history_turns.append(
                (
                    AgentConversationHistoryPlanTurnV3
                    if include_turn_correlation else AgentConversationHistoryTurnV2
                )(
                    **values,
                    plan_context=project_plan_turn_context(
                        turn, delivery_replay=True, source_names=source_names
                    ),
                )
            )
        else:
            turn_model = (
                AgentConversationHistoryTurnV3
                if include_turn_correlation else AgentConversationHistoryTurn
            )
            history_turns.append(turn_model(**values))
    if contains_mixed or contains_play_source or contains_native_statement:
        response_model = AgentConversationHistoryResponseV4
    elif include_turn_correlation:
        response_model = AgentConversationHistoryResponseV3
    elif contains_plan_context or contains_play_context:
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
            (turns[0].envelope.sequence if isinstance(turns[0], MixedCompletedTurnV1) else turns[0].sequence)
            if len(turns) == limit and turns else None
        ),
    )


class ConversationDraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(gt=0)
    markdown: str


_CONVERSATION_DRAFT_PATH = "/worlds/{world_id}/conversations/{conversation_id}/drafts/{turn_id}"


def _conversation_draft_access(request: Request, world_id: str) -> str:
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return _verified_world_id(world_id)


@router.get("/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/variant-approval")
def get_conversation_variant_approval(world_id: str, conversation_id: UUID, turn_id: UUID, request: Request):
    verified = _conversation_draft_access(request, world_id)
    try:
        return _conversation_service(request).conversation_variant_approval(verified, conversation_id, turn_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(_CONVERSATION_DRAFT_PATH)
def get_conversation_draft(world_id: str, conversation_id: UUID, turn_id: UUID, request: Request):
    verified = _conversation_draft_access(request, world_id)
    try:
        return _conversation_service(request).open_conversation_draft(verified, conversation_id, turn_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put(_CONVERSATION_DRAFT_PATH)
def put_conversation_draft(
    world_id: str, conversation_id: UUID, turn_id: UUID, body: ConversationDraftEdit, request: Request,
):
    verified = _conversation_draft_access(request, world_id)
    try:
        return _conversation_service(request).edit_conversation_draft(
            verified, conversation_id, turn_id,
            expected_revision=body.expected_revision, markdown=body.markdown,
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(_CONVERSATION_DRAFT_PATH + "/variant-reviews/{review_id}")
def get_conversation_variant_review(
    world_id: str, conversation_id: UUID, turn_id: UUID, review_id: UUID, request: Request,
):
    verified = _conversation_draft_access(request, world_id)
    try:
        return _conversation_service(request).open_conversation_variant_review(
            verified, conversation_id, turn_id, review_id=review_id,
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.put(_CONVERSATION_DRAFT_PATH + "/variant-reviews/{review_id}")
def correct_conversation_variant_review(
    world_id: str, conversation_id: UUID, turn_id: UUID, review_id: UUID,
    body: CorrectConversationVariant, request: Request,
):
    from apps.live_control_server.services.conversation_variant_save import correct_variant

    verified = _conversation_draft_access(request, world_id)
    try:
        return correct_variant(_conversation_service(request), verified, conversation_id, turn_id, review_id, body)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(_CONVERSATION_DRAFT_PATH + "/variant-reviews/{review_id}/saved")
def get_saved_conversation_variant(
    world_id: str, conversation_id: UUID, turn_id: UUID, review_id: UUID, request: Request,
):
    from apps.live_control_server.services.conversation_variant_save import open_saved_variant

    verified = _conversation_draft_access(request, world_id)
    try:
        return open_saved_variant(
            _conversation_service(request), verified, conversation_id, turn_id, review_id=review_id,
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(_CONVERSATION_DRAFT_PATH + "/variant-reviews/{review_id}/confirm")
def confirm_conversation_variant_review(
    world_id: str, conversation_id: UUID, turn_id: UUID, review_id: UUID, request: Request,
):
    from apps.live_control_server.services.conversation_variant_save import (
        ConfirmConversationVariant, save_variant,
    )

    verified = _conversation_draft_access(request, world_id)
    try:
        return save_variant(
            _conversation_service(request), verified, conversation_id, turn_id,
            ConfirmConversationVariant(review_id=review_id),
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/worlds/{world_id}/conversation/lore-pages/review")
def prepare_world_lore_save_review(world_id: str, body: LorePageConfirmation, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    if principal.role != "gm":
        raise HTTPException(status_code=403, detail={"code": "lore_confirmation_forbidden"})
    try:
        _conversation_service(request).prepare_lore_save_review(
            world_id=_verified_world_id(world_id), principal_subject=principal.subject, confirmation=body,
        )
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"review_sha256": body.review_sha256}


@router.post("/worlds/{world_id}/conversation/lore-pages/confirm")
def confirm_world_lore_page(world_id: str, body: LorePageConfirmation, request: Request):
    from apps.live_control_server.services.agent_native_source_sections import open_native_body_excerpt
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    world = _verified_world_id(world_id)
    service = _conversation_service(request)
    if principal.role != "gm":
        raise HTTPException(status_code=403, detail={"code": "lore_confirmation_forbidden"})

    def verify_source(turn_id, ordinal):
        return open_native_body_excerpt(
            world_id=world, turn_id=turn_id, citation_index=ordinal,
            principal=principal, service=service,
        )

    try:
        return service.confirm_lore_page(
            world_id=world, principal_subject=principal.subject, confirmation=body,
            verify_source=verify_source,
        )
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/connected-page-origin")
def get_world_turn_connected_page_origin(world_id: str, turn_id: UUID, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail={"code":"connected_page_origin_selector_invalid"})
    from apps.live_control_server.services.agent_connected_page_origin import open_origin
    from apps.live_control_server.services import hosted_auth
    try:
        result = open_origin(_conversation_service(request),verified,turn_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code":"connected_page_origin_unavailable"}) from exc
    except (ValueError,ValidationError,KeyError) as exc:
        raise HTTPException(status_code=409, detail={"code":"connected_page_origin_binding_invalid"}) from exc
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return result


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/related-pages/{read_id}")
def get_world_turn_related_page(world_id: str, turn_id: UUID, read_id: UUID, request: Request):
    """Read the immutable authored page captured for this completed answer."""
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified=_verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422,detail={"code":"related_page_selector_invalid"})
    from apps.live_control_server.services.build_related_pages import open_page
    try:
        result = open_page(_conversation_service(request),verified,turn_id,read_id)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,detail={"code":"related_page_turn_unavailable"}) from exc
    except (ValueError,ValidationError,KeyError) as exc:
        raise HTTPException(status_code=409,detail={"code":"related_page_binding_invalid"}) from exc
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return result


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/saved-sections/{segment_index}/{section_event_id}")
def get_world_turn_saved_section(world_id: str, turn_id: UUID, segment_index: int,
        section_event_id: UUID, request: Request):
    """Open persisted authored evidence; never substitute a current source."""
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params or not 0 <= segment_index <= 127:
        raise HTTPException(status_code=422, detail={"code": "saved_section_selector_invalid"})
    from apps.live_control_server.services.agent_saved_sections import open_saved_section
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    try:
        result = open_saved_section(world_id=verified, turn_id=turn_id,
            segment_index=segment_index, section_event_id=section_event_id,
            service=_conversation_service(request)).model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "saved_section_turn_unavailable"}) from exc
    except (ValidationError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail={"code": "saved_section_binding_invalid"}) from exc
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return result


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/native-source-clauses/{citation_index}")
def get_world_turn_native_source_clause(world_id: str, turn_id: UUID, citation_index: int, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world = _verified_world_id(world_id)
    if request.query_params or citation_index < 0:
        raise HTTPException(status_code=422, detail={"code": "native_clause_selector_invalid"})
    from apps.live_control_server.services.native_statement_clause_reads import open_clause
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    try:
        return open_clause(world_id=verified_world, turn_id=turn_id, citation_index=citation_index,
            principal=principal, service=_conversation_service(request)).model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "native_clause_turn_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/native-assertion-sources/{citation_index}")
def get_world_turn_native_assertion_source(world_id: str, turn_id: UUID, citation_index: int, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    world = _verified_world_id(world_id)
    if request.query_params or citation_index < 0:
        raise HTTPException(status_code=422, detail={"code": "native_assertion_selector_invalid"})
    from apps.live_control_server.services.native_statement_clause_reads import open_assertion_source
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    try:
        return open_assertion_source(world_id=world, turn_id=turn_id, citation_index=citation_index,
            principal=principal, service=_conversation_service(request)).model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "native_assertion_turn_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/native-body-excerpts/{citation_index}")
def get_world_turn_native_body_excerpt(world_id: str, turn_id: UUID, citation_index: int, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    world = _verified_world_id(world_id)
    if request.query_params or not 0 <= citation_index <= 16383:
        raise HTTPException(status_code=422, detail={"code": "native_body_selector_invalid"})
    from apps.live_control_server.services.agent_native_source_sections import open_native_body_excerpt
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    try:
        return open_native_body_excerpt(world_id=world, turn_id=turn_id, citation_index=citation_index,
            principal=principal, service=_conversation_service(request)).model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "native_body_turn_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/native-source-sections/{citation_index}")
def get_world_turn_native_source_section(world_id: str, turn_id: UUID, citation_index: int,request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    if request.query_params or not 0 <= citation_index <= 16383:
        raise HTTPException(status_code=422,detail={"code":"source_section_selector_invalid"})
    from apps.live_control_server.services.agent_native_source_sections import open_native_source_section
    from apps.live_control_server.services.agent_source_passages import SourcePassageOpenError
    try:
        return open_native_source_section(world_id=verified_world_id,turn_id=turn_id,
            citation_index=citation_index,service=_conversation_service(request)).model_dump(mode="json",by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code,detail={"code":exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,detail={"code":"source_section_turn_unavailable"}) from exc
    except (ValidationError,ValueError,KeyError,StopIteration) as exc:
        raise HTTPException(status_code=409,detail={"code":"source_section_binding_invalid"}) from exc


@router.get("/worlds/{world_id}/plan-proposals/{action_id}/graph-evidence")
def get_saved_plan_action_graph_evidence(world_id: str, action_id: UUID, request: Request):
    from apps.live_control_server.services.agent_source_passages import (
        SourcePassageOpenError, open_saved_plan_action_graph_evidence,
    )
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    selectors = request.query_params.multi_items()
    claim_id = request.query_params.get("claim_id")
    anchor_id = request.query_params.get("anchor_id")
    if (len(selectors) != 2 or {key for key, _ in selectors} != {"claim_id", "anchor_id"}
            or not claim_id or not anchor_id or max(len(claim_id), len(anchor_id)) > 256):
        raise HTTPException(status_code=422, detail={"code": "source_passage_selector_invalid"})
    try:
        result = open_saved_plan_action_graph_evidence(
            world_id=_verified_world_id(world_id), action_id=action_id, claim_id=claim_id, anchor_id=anchor_id,
        )
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
        return result.model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "source_passage_action_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/graph-evidence")
def get_saved_turn_graph_evidence(world_id: str, turn_id: UUID, request: Request):
    """Open an evidence anchor admitted by a saved turn at its recorded pin."""
    from apps.live_control_server.services.agent_source_passages import (
        SourcePassageOpenError, open_saved_turn_graph_evidence, open_saved_turn_related_recap,
    )
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    selectors = request.query_params.multi_items()
    claim_id = request.query_params.get("claim_id")
    anchor_id = request.query_params.get("anchor_id")
    related = bool(anchor_id and anchor_id.startswith("dm-context-anchor:v2:"))
    expected = {"claim_id", "anchor_id"}
    continuation = request.query_params.get("continuation")
    if related and continuation is not None:
        expected.add("continuation")
    if (
        len(selectors) != len(expected) or {key for key, _ in selectors} != expected
        or (continuation is not None and not 1 <= len(continuation) <= 256)
        or not claim_id or not anchor_id or max(len(claim_id), len(anchor_id)) > 256
    ):
        raise HTTPException(status_code=422, detail={"code": "source_passage_selector_invalid"})
    try:
        coordinates = dict(
            world_id=_verified_world_id(world_id), turn_id=turn_id, claim_id=claim_id,
            anchor_id=anchor_id, service=_conversation_service(request),
        )
        result = (open_saved_turn_related_recap(**coordinates, continuation=continuation)
                  if related else open_saved_turn_graph_evidence(**coordinates))
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
        return result.model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "source_passage_turn_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/source-passages/{citation_index}")
def get_world_turn_source_passage(world_id: str, turn_id: UUID, citation_index: int,
        request: Request):
    """Explicit authenticated historical source read, separate from Graph claims."""
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    if request.query_params or not 0 <= citation_index <= 16383:
        raise HTTPException(status_code=422, detail={"code": "source_passage_selector_invalid"})
    from apps.live_control_server.services.agent_source_passages import (
        open_source_passage, SourcePassageOpenError,
    )
    try:
        result = open_source_passage(world_id=verified_world_id, turn_id=turn_id,
            citation_index=citation_index, service=_conversation_service(request))
        return result.model_dump(mode="json", by_alias=True)
    except SourcePassageOpenError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,
            detail={"code": "source_passage_turn_unavailable"}) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"code": "source_passage_binding_invalid"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/source-passages/{source_read_event_id}")
def get_world_historical_source_passage(world_id: str, turn_id: str, trace_id: str,
        source_read_event_id: str, request: Request):
    """One exact historical capture, independent of current-turn citation authority."""
    from fastapi.responses import Response
    from apps.live_control_server.services import hosted_auth
    from application_state.agent_conversation.context_trace import TraceHistoricalSourceReferenceV1

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    selectors = list(request.query_params.multi_items())
    expected = {"conversation_id", "attempt", "source_read_id", "content_sha256"}
    try:
        if len(selectors) != len(expected) or {key for key, _ in selectors} != expected:
            raise ValueError("invalid selectors")
        query = dict(selectors)
        uuid_values = [turn_id, trace_id, source_read_event_id, query["conversation_id"]]
        if any(str(UUID(value)) != value for value in uuid_values):
            raise ValueError("noncanonical identifier")
        attempt = int(query["attempt"])
        if str(attempt) != query["attempt"] or not 1 <= attempt <= 2147483647:
            raise ValueError("invalid attempt")
        reference = TraceHistoricalSourceReferenceV1(world_id=verified, turn_id=UUID(turn_id),
            conversation_id=UUID(query["conversation_id"]), trace_id=UUID(trace_id),
            source_read_event_id=UUID(source_read_event_id), attempt=attempt,
            source_read_id=query["source_read_id"], content_sha256=query["content_sha256"])
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "historical_passage_selector_invalid"}) from exc
    try:
        passage = _conversation_service(request).read_historical_source_passage(reference)
        result = AgentHistoricalSourcePassageResponseV1(reference=reference, passage=passage)
        response = Response(content=result.model_dump_json(by_alias=True), media_type="application/json",
                        headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "historical_passage_unavailable"}) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"code": "historical_passage_binding_invalid"}) from exc
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return response


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/rules-passages/{support_id}")
def get_world_historical_rules_passage(world_id: str, turn_id: str, support_id: str,
        request: Request):
    """One persisted cited capsule; historical identity never resolves current rules."""
    from fastapi.responses import Response
    from apps.live_control_server.services import hosted_auth
    from application_state.agent_conversation.rules_authority_passages import (
        RulesHistoricalPassageRequestV1, RulesHistoricalPassageV1,
    )
    from application_state.agent_conversation.rules_authority_types import canonical_bytes

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    try:
        selectors = list(request.query_params.multi_items())
        keys = {"conversation_id", "attempt", "support_sha256"}
        if len(selectors) != len(keys) or {key for key, _ in selectors} != keys:
            raise ValueError("Rules passage requires exact selectors")
        query = dict(selectors)
        if any(str(UUID(value)) != value for value in (turn_id, support_id, query["conversation_id"])):
            raise ValueError("Rules passage requires canonical identifiers")
        attempt = int(query["attempt"])
        if str(attempt) != query["attempt"] or not 1 <= attempt <= 2147483647:
            raise ValueError("Rules passage attempt is invalid")
        reference = RulesHistoricalPassageRequestV1(world_id=verified,
            conversation_id=UUID(query["conversation_id"]), turn_id=UUID(turn_id),
            attempt=attempt, support_id=UUID(support_id), support_sha256=query["support_sha256"])
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "rules_passage_selector_invalid"}) from exc
    try:
        stored = _conversation_service(request).inspect_rules_passage(reference)
        # Revalidate the outward boundary, including injected service implementations.
        passage = RulesHistoricalPassageV1.model_validate_json(stored.model_dump_json(by_alias=True))
        if (passage.world_id, passage.conversation_id, passage.turn_id,
            passage.accepted_attempt, passage.support.support_id, passage.support_sha256) != (
            reference.world_id, reference.conversation_id, reference.turn_id,
            reference.attempt, reference.support_id, reference.support_sha256):
            raise ValueError("Rules passage differs from requested accepted identity")
        response = Response(content=canonical_bytes(passage), media_type="application/json",
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "rules_passage_unavailable"}) from exc
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"code": "rules_passage_binding_invalid"}) from exc
    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return response


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace", response_model=AgentTurnContextTraceResponseV1)
def get_world_turn_context_trace(world_id: str, turn_id: UUID, request: Request) -> AgentTurnContextTraceResponseV1:
    """Explicit authenticated read; normal history never includes passage bytes."""
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail="context trace read does not accept query selectors")
    try:
        attempts = _conversation_service(request).list_context_trace_attempts(
            world_id=verified_world_id, turn_id=turn_id,
        )
        return AgentTurnContextTraceResponseV1(world_id=verified_world_id, turn_id=turn_id, attempts=attempts)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code,
                            detail={"code": "context_trace_unavailable", "message": str(exc)}) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail={"code": "context_trace_binding_invalid"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/identities")
def get_world_replay_identities(world_id: str, turn_id: UUID, trace_id: UUID, request: Request):
    from fastapi.responses import JSONResponse
    from apps.live_control_server.services.agent_replay_identities import replay_identities
    from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable

    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal, require_explorer_access

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    world = _verified_world_id(world_id)
    selectors = list(request.query_params.multi_items())
    offset_text = request.query_params.get("offset", "0")
    if (selectors and (len(selectors) != 1 or selectors[0][0] != "offset")
            or not offset_text.isascii() or not offset_text.isdecimal()
            or len(offset_text) > 8 or str(int(offset_text)) != offset_text):
        raise HTTPException(status_code=422, detail={"code": "replay_identity_selector_invalid"})
    try:
        result = replay_identities(service=_conversation_service(request), principal=principal,
                                   world_id=world, turn_id=turn_id, trace_id=trace_id, offset=int(offset_text))
        response = JSONResponse(result, headers={"Cache-Control": "no-store"})
        require_explorer_access(principal, world_id)
        return response
    except InspectionUnavailable as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "replay_identities_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/steps/{sequence}/assertion")
def get_world_replay_assertion(world_id: str, turn_id: UUID, trace_id: UUID, sequence: int, request: Request):
    from apps.live_control_server.services.agent_replay_assertion import open_replay_assertion

    return _read_replay_assertion(world_id, turn_id, trace_id, sequence, request, open_replay_assertion)


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/native-steps/{sequence}/assertion")
def get_world_native_replay_assertion(world_id: str, turn_id: UUID, trace_id: UUID, sequence: int, request: Request):
    from apps.live_control_server.services.agent_replay_assertion import open_native_replay_assertion

    return _read_replay_assertion(world_id, turn_id, trace_id, sequence, request, open_native_replay_assertion)


def _read_replay_assertion(world_id, turn_id, trace_id, sequence, request, opener):
    from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable
    from fastapi.responses import JSONResponse

    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal, require_explorer_access

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    world = _verified_world_id(world_id)
    selectors = list(request.query_params.multi_items())
    if not 0 <= sequence < 2048 or len(selectors) != 1 or selectors[0][0] != "assertion_id" or not 0 < len(selectors[0][1].strip()) <= 256:
        raise HTTPException(status_code=422, detail={"code": "replay_assertion_selector_invalid"})
    try:
        result = opener(service=_conversation_service(request), principal=principal,
            world_id=world, turn_id=turn_id, trace_id=trace_id, sequence=sequence, assertion_id=selectors[0][1])
        response = JSONResponse(result, headers={"Cache-Control": "no-store"})
        require_explorer_access(principal, world_id)
        return response
    except InspectionUnavailable as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "replay_assertion_unavailable"}) from exc


@router.get("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/{trace_id}/prompt/{provider_attempt_id}")
def get_world_turn_prompt(world_id: str, turn_id: UUID, trace_id: UUID, provider_attempt_id: UUID, request: Request):
    """Explicit developer evidence read, under the same GM/World scope as traces."""
    from fastapi.responses import JSONResponse
    from application_state.agent_conversation.context_trace import TracePromptReference
    from apps.live_control_server.services.agent_prompt_evidence import PromptEvidenceError, read_prompt

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail="prompt read does not accept query selectors")
    try:
        attempts = _conversation_service(request).list_context_trace_attempts(world_id=verified, turn_id=turn_id)
        matches = [(trace, item) for trace in attempts if trace.trace_id == trace_id
            and trace.world_id == verified and trace.turn_id == turn_id
            for item in trace.observations if isinstance(item, TracePromptReference)
            and item.provider_attempt_id == provider_attempt_id]
        if len(matches) != 1:
            raise HTTPException(status_code=404, detail={"code": "prompt_not_captured"})
        trace, reference = matches[0]
        text = read_prompt(reference)
        return JSONResponse({"schema": "dmb_agent_prompt_evidence_v1", "world_id": verified,
            "conversation_id": str(trace.conversation_id), "turn_id": str(turn_id), "trace_id": str(trace_id),
            "attempt": trace.attempt, "reference": reference.model_dump(mode="json"), "payload_json": text},
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "prompt_evidence_unavailable"}) from exc
    except PromptEvidenceError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc


class PromptEvidenceSelector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: UUID
    provider_attempt_id: UUID


class PromptEvidenceBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompts: list[PromptEvidenceSelector] = Field(min_length=1, max_length=8)


@router.post("/worlds/{world_id}/conversation/turns/{turn_id}/context-trace/prompts")
def get_world_turn_prompts(
    world_id: str, turn_id: UUID, request: Request, body: PromptEvidenceBatch,
):
    from fastapi.responses import JSONResponse
    from application_state.agent_conversation.context_trace import TracePromptReference
    from apps.live_control_server.services.agent_prompt_evidence import MAX_PROMPT_BYTES, PromptEvidenceError, read_prompt

    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail="prompt read does not accept query selectors")
    try:
        attempts = _conversation_service(request).list_context_trace_attempts(
            world_id=verified, turn_id=turn_id,
        )
    except ApplicationStateError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": "prompt_evidence_unavailable"},
        ) from exc

    results = []
    remaining_bytes = MAX_PROMPT_BYTES
    for selector in body.prompts:
        matches = [
            (trace, item)
            for trace in attempts
            if trace.trace_id == selector.trace_id and trace.world_id == verified and trace.turn_id == turn_id
            for item in trace.observations
            if isinstance(item, TracePromptReference) and item.provider_attempt_id == selector.provider_attempt_id
        ]
        if len(matches) != 1:
            results.append({"unavailable": "prompt_not_captured"})
            continue
        trace, reference = matches[0]
        if reference.payload_utf8_bytes > remaining_bytes:
            results.append({"unavailable": "prompt_batch_byte_limit"})
            continue
        try:
            payload = read_prompt(reference)
        except PromptEvidenceError as exc:
            results.append({"unavailable": str(exc)})
            continue
        remaining_bytes -= reference.payload_utf8_bytes
        results.append({
            "schema": "dmb_agent_prompt_evidence_v1", "world_id": verified,
            "conversation_id": str(trace.conversation_id), "turn_id": str(turn_id),
            "trace_id": str(trace.trace_id), "attempt": trace.attempt,
            "reference": reference.model_dump(mode="json"), "payload_json": payload,
        })
    return JSONResponse(
        {"schema": "dmb_agent_prompt_evidence_batch_v1", "results": results},
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.get("/worlds/{world_id}/conversation/commands/{command_id}", response_model=AgentNewConversationStatusV1)
def get_new_world_conversation_status(
    world_id: str, command_id: UUID, request: Request,
    expected_pointer_revision: int = Query(ge=0),
    expected_active_conversation_id: str = Query(),
) -> AgentNewConversationStatusV1:
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    allowed = {"expected_pointer_revision", "expected_active_conversation_id"}
    if set(request.query_params) != allowed or any(len(request.query_params.getlist(key)) != 1 for key in allowed):
        raise HTTPException(status_code=422, detail="exact original command selectors are required")
    try:
        command = ConversationCommand(world_id=verified_world_id, command_id=command_id,
            expected_pointer_revision=expected_pointer_revision,
            expected_active_conversation_id=None if expected_active_conversation_id == "null" else UUID(expected_active_conversation_id))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="invalid original command binding") from exc
    try:
        receipt = _conversation_service(request).get_new_conversation_receipt(command)
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "conversation_status_rejected", "message": str(exc)}) from exc
    return AgentNewConversationStatusV1(world_id=verified_world_id, command_id=command_id,
        expected_pointer_revision=command.expected_pointer_revision,
        expected_active_conversation_id=command.expected_active_conversation_id,
        request_fingerprint=request_fingerprint(command), status="confirmed" if receipt else "absent",
        receipt=None if receipt is None else AgentNewConversationReceiptV1(
            conversation_id=receipt.conversation_id, active_conversation_id=receipt.active_conversation_id,
            pointer_revision=receipt.pointer_revision, recorded_at=receipt.recorded_at.isoformat()))


def _resolution_error(exc: ApplicationStateError) -> HTTPException:
    code = "use_original_resolution_record" if str(exc) == "use_original_resolution_record" else "command_resolution_nonterminal"
    return HTTPException(status_code=exc.status_code, detail={"code": code, "message": str(exc)})


@router.post("/worlds/{world_id}/conversation/commands/{command_id}/resolve", response_model=AgentCommandResolutionResponseV1)
def post_world_command_resolution(world_id: str, command_id: UUID, body: CommandResolutionRequestV1, request: Request) -> AgentCommandResolutionResponseV1:
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    if body.original_command.world_id != verified_world_id or body.original_command.command_id != command_id or request.query_params:
        raise HTTPException(status_code=422, detail="resolution path and original command must match")
    try:
        if principal.auth_method == "hosted_owner":
            from functools import partial
            from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

            authorize_world = partial(
                require_conversation_access, request, world_id, authorize_local=enforce_native_graph_gm,
            )
            record = _conversation_service(request).resolve_new_conversation(
                body, actor=principal.subject, authorize_world=authorize_world,
            )
            authorize_world()
        else:
            record = _conversation_service(request).resolve_new_conversation(body, actor=principal.subject)
    except ApplicationStateError as exc:
        raise _resolution_error(exc) from exc
    return AgentCommandResolutionResponseV1(status="terminal", record=record)


@router.get("/worlds/{world_id}/conversation/commands/{command_id}/resolutions/{operation_id}", response_model=AgentCommandResolutionResponseV1)
def get_world_command_resolution(world_id: str, command_id: UUID, operation_id: UUID, request: Request,
    original_pointer_revision: int = Query(ge=0), original_active_conversation_id: str = Query(),
    current_pointer_revision: int = Query(ge=0), current_active_conversation_id: str = Query(),
) -> AgentCommandResolutionResponseV1:
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified_world_id = _verified_world_id(world_id)
    allowed = {"original_pointer_revision", "original_active_conversation_id", "current_pointer_revision", "current_active_conversation_id"}
    if set(request.query_params) != allowed or any(len(request.query_params.getlist(key)) != 1 for key in allowed):
        raise HTTPException(status_code=422, detail="exact resolution selectors required")
    try:
        original = ConversationCommand(world_id=verified_world_id, command_id=command_id,
            expected_pointer_revision=original_pointer_revision,
            expected_active_conversation_id=None if original_active_conversation_id == "null" else UUID(original_active_conversation_id))
        body = CommandResolutionRequestV1(resolution_operation_id=operation_id, original_command=original,
            expected_current_pointer_revision=current_pointer_revision,
            expected_current_active_conversation_id=None if current_active_conversation_id == "null" else UUID(current_active_conversation_id))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="invalid resolution binding") from exc
    try:
        record = _conversation_service(request).get_command_resolution(body)
    except ApplicationStateError as exc:
        raise _resolution_error(exc) from exc
    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    return AgentCommandResolutionResponseV1(status="terminal" if record else "absent", record=record)


@router.post(
    "/worlds/{world_id}/conversation/new",
    response_model=AgentNewConversationResponse,
)
def post_new_world_conversation(
    world_id: str,
    body: AgentNewConversationRequest,
    request: Request,
) -> AgentNewConversationResponse:
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
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
            detail={"code": "new_conversation_request_retired" if str(exc) == "new_conversation_request_retired" else "conversation_command_rejected", "message": str(exc)},
        ) from exc
    return AgentNewConversationResponse(
        world_id=verified_world_id,
        conversation_id=receipt.conversation_id,
        active_conversation_id=receipt.active_conversation_id,
        pointer_revision=receipt.pointer_revision,
    )


@router.post("/turn", response_model=None)
def post_agent_turn(body: AgentTurnRequest, request: Request):
    if request.headers.get("accept") == "text/event-stream":
        _chat_turn_principal(body, request)
        if getattr(body.primary_work, "kind", None) != "build":
            raise HTTPException(422, detail="Construction streaming requires Build work")
        from apps.live_control_server.services.build_construction_stream import turn_stream
        return turn_stream(lambda: _execute_agent_turn(body, request), body.turn_id)
    return _execute_agent_turn(body, request)


def _chat_turn_principal(body: AgentTurnRequest, request: Request):
    from apps.live_control_server.services.hosted_native_graph_access import conversation_graph_principal

    owner = body.owner_scope
    world_id = owner.world_id if owner is not None and owner.kind == "world" else ""
    return conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)


def _execute_agent_turn(body: AgentTurnRequest, request: Request) -> dict[str, Any]:
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
            principal = _chat_turn_principal(body, request)
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
            plan_graph_resolver=lambda turn, owner, work, receipt, parent_span_id, frozen_source_scope=None: _plan_context_resolver(
                turn, owner, work, receipt, trace=trace,
                parent_span_id=parent_span_id, frozen_source_scope=frozen_source_scope,
            ),
            native_graph_query_resolver=lambda turn, owner, work, receipt, source_context: _plan_context_resolver(
                turn, owner, work, receipt, trace=trace, native_query_mode=True,
                native_source_context=source_context, native_principal=principal),
            runtime_factory=lambda: getattr(
                request.app.state, "agent_turn_runtime", None
            ),
            conversation_service=_conversation_service(request),
            build_runtime_factory=getattr(getattr(request.app, "state", None), "build_jev_runtime_factory", None),
            trace_builder=trace,
            operator_subject=principal.subject,
            native_principal=principal,
            native_statement_transport=getattr(request.app.state, "native_statement_writer_transport", None),
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


class BuildSourceWithdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["pdf", "text"]
    revision_id: str = Field(min_length=1, max_length=256)


@router.post("/worlds/{world_id}/build-source-withdrawals", status_code=204)
def withdraw_build_source(world_id: str, body: BuildSourceWithdrawal, request: Request):
    from fastapi.responses import Response
    from dungeonmind.domain.errors import DungeonMindError

    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError, _repository, _source_world_binding,
    )
    from apps.live_control_server.models.native_graph_inspection import InspectionScope
    from apps.live_control_server.services.native_source_inspection import catalog

    from apps.live_control_server.services.hosted_native_graph_access import (
        conversation_graph_principal, require_conversation_access,
    )

    principal = conversation_graph_principal(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    try:
        binding = _source_world_binding(None, verified)
        repository = _repository()
        if body.kind == "pdf":
            record = repository.get_native_pdf_source(binding.native_world_id, body.revision_id)
            artifact_id = record[0].source_artifact_id if (
                record and record[0].status == "active" and record[0].visibility.kind == "public"
            ) else None
        else:
            result = catalog(InspectionScope(managed_world_id=verified, scope_mode="world", campaign_id=None), principal)
            if result["scope"]["native_world_id"] != binding.native_world_id:
                raise ValueError("World binding changed")
            artifact_id = next((
                item["source_artifact"]["source_artifact_id"]
                for item in result["catalogue"]["sources"]
                if item["source_revision"]["source_revision_id"] == body.revision_id
            ), None)
        if not artifact_id:
            raise HTTPException(status_code=404, detail="The document is unavailable.")
        if _source_world_binding(None, verified) != binding:
            raise ValueError("World binding changed")
        require_conversation_access(request, verified, authorize_local=enforce_native_graph_gm)
        repository.withdraw_native_source(
            space_id=binding.native_world_id, source_artifact_id=artifact_id,
            source_revision_id=body.revision_id,
        )
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail="Document storage is unavailable.") from exc
    except (ValueError, DungeonMindError) as exc:
        raise HTTPException(status_code=409, detail="The document could not be deleted. Refresh and retry.") from exc
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/worlds/{world_id}/build-pdf-sources")
def get_build_pdf_sources(world_id: str, request: Request, after: str = ""):
    from fastapi.responses import JSONResponse

    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError, _repository, _source_world_binding,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    verified = _verified_world_id(world_id)
    try:
        binding = _source_world_binding(None, verified)
        revisions = _repository().list_public_native_pdf_revisions(
            binding.native_world_id, after_revision_id=after,
        )
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    require_build_pdf_access(request, world_id)
    return JSONResponse({
        "documents": [{
            "source_revision_id": revision.source_revision_id,
            "content_sha256": revision.content_sha256,
            "created_at": revision.created_at.isoformat(),
        } for revision in revisions],
        "next": revisions[-1].source_revision_id if len(revisions) == 100 else None,
    }, headers={"Cache-Control": "no-store"})


@router.post("/worlds/{world_id}/build-pdf-sources")
async def post_build_pdf_source(world_id: str, admission_id: UUID, request: Request):
    from dungeonmind.application.vnext.native_source_admission import validate_native_pdf_body
    from datetime import datetime
    from hashlib import sha256

    from starlette.concurrency import run_in_threadpool

    from dungeonmind.contracts.vnext.pdf_region import NativePdfSourceAdmissionV1
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError, _source_world_binding, retain_pdf_in_bound_world,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    encodings = request.headers.getlist("content-encoding")
    if encodings and encodings != ["identity"]:
        raise HTTPException(status_code=415, detail={"code": "pdf_content_encoding_unsupported"})
    verified = _verified_world_id(world_id)
    if request.headers.getlist("content-type") != ["application/pdf"]:
        raise HTTPException(status_code=415, detail={"code": "pdf_required"})
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 32 * 1024 * 1024:
            raise HTTPException(status_code=413, detail={"code": "pdf_too_large"})
        body.extend(chunk)
    raw = bytes(body)
    try:
        binding = _source_world_binding(None, verified)
        command = NativePdfSourceAdmissionV1.model_validate({
            "space_id": binding.native_world_id,
            "admission_id": str(admission_id),
            "created_at": datetime.fromisoformat(request.headers.get("x-pdf-created-at", "")),
            "content_sha256": sha256(raw).hexdigest(),
            "source_classification": "dungeonbuddy.source:worldbuilding",
            "authority": "primary",
            "visibility": {"kind": "public"},
        })
        require_build_pdf_access(request, world_id)
        await run_in_threadpool(validate_native_pdf_body, raw)
        revision = await run_in_threadpool(retain_pdf_in_bound_world, verified, binding, command, raw)
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_pdf_source"}) from exc
    return {"source_revision_id": revision.source_revision_id,
            "content_sha256": revision.content_sha256}


def _authorized_build_pdf_region(world_id: str, body: dict, request: Request, *, hosted_read: bool = False):
    from dungeonmind.application.vnext.native_pdf_access import open_native_pdf_region
    from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError, _repository, _source_world_binding,
    )

    if hosted_read:
        from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

        require_build_pdf_access(request, world_id)
    else:
        enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    try:
        binding = _source_world_binding(None, verified)
        region = NativePdfRegionV1.model_validate(body)
        pdf = open_native_pdf_region(
            region,
            authorized_space_id=binding.native_world_id,
            audience=frozenset(),
            declared_labels=frozenset(),
            load=_repository().get_native_pdf_source,
        )
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_pdf_region"}) from exc
    if pdf is None:
        raise HTTPException(status_code=404, detail={"code": "pdf_source_unavailable"})
    return pdf, region


def _render_build_pdf_region(pdf, region, **kwargs):
    from apps.live_control_server.services.build_pdf_region_render import render_region

    try:
        return render_region(pdf, region, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": "pdf_region_render_unavailable"}) from exc


@router.post("/worlds/{world_id}/build-pdf-sources/ocr")
def post_read_build_pdf_region(world_id: str, body: dict, request: Request):

    pdf, region = _authorized_build_pdf_region(world_id, body, request)
    png = _render_build_pdf_region(pdf, region)
    return read_crop_png(png)


@router.post("/worlds/{world_id}/build-pdf-sources/review")
def post_review_build_pdf_region(world_id: str, body: dict, request: Request):
    from generationengine import GenerationEngineError
    from generationengine.providers.errors import ProviderError
    from apps.live_control_server.services.build_pdf_capture_review import review_capture
    from llm.generation_sync import run_awaitable_sync

    instruction = body.get("instruction", "")
    region_body = body.get("region")
    if not isinstance(instruction, str) or not isinstance(region_body, dict):
        raise HTTPException(status_code=422, detail={"code": "invalid_pdf_review_request"})
    pdf, region = _authorized_build_pdf_region(world_id, region_body, request)
    png = _render_build_pdf_region(pdf, region)
    try:
        text = run_awaitable_sync(lambda: review_capture(png, instruction))
    except (GenerationEngineError, ProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Buddy could not review this capture. Check provider configuration and retry.",
        ) from exc
    return {"text": text, "region": region.model_dump(mode="json")}


@router.post("/worlds/{world_id}/build-pdf-sources/statblock:validate")
def post_validate_build_pdf_statblock(world_id: str, body: dict, request: Request):
    candidate, regions = _authorized_pdf_statblock(world_id, body, request)
    from apps.live_control_server.services.statblock_definition_validation import validate_definition

    validation = validate_definition(definition=candidate)
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    return {"validation": validation.model_dump(mode="json", by_alias=True), "regions": regions}


def _authorized_pdf_statblock(world_id: str, body: dict, request: Request, *, allow_unresolved: bool = False):
    from apps.live_control_server.services.statblock_definition_validation import (
        ValidateDefinitionBuddyRequestV1,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    regions = body.get("regions")
    if (
        set(body) != {"definition", "regions"}
        or not isinstance(regions, list)
        or not regions
        or any(not isinstance(region, dict) for region in regions)
    ):
        raise HTTPException(status_code=422, detail={"code": "invalid_pdf_statblock_request"})
    try:
        definition = body["definition"]
        if allow_unresolved:
            from apps.live_control_server.services.build_pdf_statblock_extraction import PdfStatblockDraftDefinition

            candidate = PdfStatblockDraftDefinition.model_validate(definition)
        else:
            candidate = ValidateDefinitionBuddyRequestV1.model_validate({"definition": definition}).definition
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_statblock_definition"}) from exc

    authorized_regions = []
    for locator in regions:
        _, region = _authorized_build_pdf_region(world_id, locator, request, hosted_read=True)
        authorized_regions.append(region.model_dump(mode="json"))
    return candidate, authorized_regions


@router.put("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}")
def put_pdf_statblock_review(world_id: str, review_id: UUID, body: dict, request: Request):
    from application_state.errors import ApplicationStateConflictError
    from application_state.pdf_statblock_review import save_review

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    expected_revision = body.get("expected_revision")
    if type(expected_revision) is not int or expected_revision < 0:
        raise HTTPException(status_code=422, detail={"code": "invalid_review_revision"})
    world_id = _verified_world_id(world_id)
    candidate, regions = _authorized_pdf_statblock(
        world_id, {key: value for key, value in body.items() if key not in {"expected_revision"}}, request,
        allow_unresolved=True,
    )
    try:
        require_build_pdf_access(request, world_id)
        saved = save_review(
            world_id=_verified_world_id(world_id), review_id=review_id, expected_revision=expected_revision,
            definition=candidate.model_dump(mode="json", by_alias=True), regions=regions,
        )
        require_build_pdf_access(request, world_id)
        return saved
    except ApplicationStateConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"}) from exc


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/from-regions")
def post_extract_pdf_statblock_review(world_id: str, review_id: UUID, body: dict, request: Request):
    """OCR exact retained regions, draft a complete definition, and open review only."""
    from application_state.errors import ApplicationStateConflictError
    from application_state.pdf_statblock_review import read_review, save_review
    from apps.live_control_server.services.statblock_definition_validation import ValidateDefinitionBuddyRequestV1
    from apps.live_control_server.services.build_pdf_statblock_extraction import (
        StatblockExtractionError, extract_statblock,
    )
    from llm.generation_sync import run_awaitable_sync
    from apps.live_control_server.services.build_pdf_region_render import read_region_text, request_page_renderer

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    instruction = body.get("instruction", "")
    regions_body = body.get("regions")
    edition = body.get("edition")
    whole_pdf = body.get("whole_pdf", False)
    if (set(body) - {"regions", "instruction", "edition", "whole_pdf"}
            or not isinstance(whole_pdf, bool)
            or edition not in (None, "2014", "2024") or not isinstance(instruction, str)
            or not isinstance(regions_body, list) or not regions_body
            or any(not isinstance(region, dict) for region in regions_body)):
        raise HTTPException(status_code=422, detail={"code": "invalid_pdf_statblock_extraction_request"})

    verified_world = _verified_world_id(world_id)
    existing = read_review(world_id=verified_world, review_id=review_id)
    if existing is not None:
        authorized_regions = [
            _authorized_build_pdf_region(world_id, locator, request, hosted_read=True)[1].model_dump(mode="json")
            for locator in regions_body
        ]
        if authorized_regions == existing["regions"] and (
            edition is None or existing["definition"]["ruleset"]["edition"] == edition
        ):
            require_build_pdf_access(request, world_id)
            return existing
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"})

    artwork = None
    transcriptions = []
    embedded_texts = []
    authorized_regions = []
    render_page = request_page_renderer()
    for locator in regions_body:
        pdf, region = _authorized_build_pdf_region(world_id, locator, request, hosted_read=True)
        png = _render_build_pdf_region(pdf, region, render_page=render_page)
        transcription = read_crop_png(png, allow_empty=True) if whole_pdf else read_crop_png(png)
        text = transcription.get("text") if isinstance(transcription, dict) else None
        authorized_regions.append(region.model_dump(mode="json"))
        if whole_pdf and isinstance(text, str) and not text.strip():
            continue
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=503, detail={"code": "pdf_statblock_ocr_unavailable"})
        if artwork is None and "<|ref|>image<|/ref|>" in text:
            crop = read_grounded_artwork(png, text)
            if crop is not None:
                artwork = {**crop, "region_index": len(authorized_regions) - 1}
        transcriptions.append(text)
        embedded_texts.append(read_region_text(pdf, region) or None)
    if not transcriptions:
        raise HTTPException(status_code=422, detail={"code": "pdf_statblock_extraction_incomplete"})

    try:
        options = {}
        if edition:
            options["edition"] = edition
        if any(embedded_texts):
            options["embedded_texts"] = embedded_texts
        extracted = run_awaitable_sync(lambda: extract_statblock(transcriptions, instruction, **options))
    except StatblockExtractionError as exc:
        status_code = 502 if exc.code == "pdf_statblock_output_invalid" else 503
        raise HTTPException(status_code=status_code, detail={"code": exc.code}) from exc
    if extracted.status == "incomplete":
        raise HTTPException(status_code=422, detail={
            "code": "pdf_statblock_extraction_incomplete",
            "missing_details": extracted.missing_details,
        })
    if edition is not None and extracted.definition.ruleset.edition != edition:
        raise HTTPException(status_code=422, detail={"code": "pdf_statblock_output_invalid"})
    try:
        definition = extracted.definition.model_dump(mode="json", by_alias=True)
        if (extracted.definition.movement is not None
                and extracted.definition.challenge.proficiency_bonus is not None):
            candidate = ValidateDefinitionBuddyRequestV1.model_validate({"definition": definition})
            definition = candidate.definition.model_dump(mode="json", by_alias=True)
        require_build_pdf_access(request, world_id)
        saved = save_review(
            world_id=verified_world, review_id=review_id, expected_revision=0,
            definition=definition, regions=authorized_regions,
            **({"artwork": artwork} if artwork is not None else {}),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "pdf_statblock_output_invalid"}) from exc
    except ApplicationStateConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"}) from exc
    require_build_pdf_access(request, world_id)
    return saved


@router.get("/worlds/{world_id}/build-pdf-sources/statblock-reviews")
def list_pdf_statblock_reviews(world_id: str, request: Request):
    from fastapi.responses import JSONResponse
    from application_state.pdf_statblock_review import list_reviews
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import (
        NativeWorldSourceAdmissionError, _repository, _source_world_binding,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    world_id = _verified_world_id(world_id)
    try:
        binding = _source_world_binding(None, world_id)
        repository = _repository()
        retained = {}
        after = ""
        while True:
            page = repository.list_public_native_pdf_revisions(binding.native_world_id, after_revision_id=after)
            retained.update((entry.source_revision_id, entry.content_sha256) for entry in page)
            if len(page) < 100:
                break
            after = page[-1].source_revision_id
        reviews = [
            {"review_id": str(review_id), "name": name, "draft_id": str(_pdf_review_creature_draft_id(world_id, review_id))}
            for review_id, name, regions in list_reviews(world_id=world_id)
            if name and regions and all(
                retained.get(region["source_revision_id"]) == region["content_sha256"] for region in regions
            )
        ]
        if _source_world_binding(None, world_id) != binding:
            raise HTTPException(status_code=409, detail="The World changed. Open the picker again.")
    except NativeWorldSourceAdmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    require_build_pdf_access(request, world_id)
    return JSONResponse({"reviews": reviews}, headers={"Cache-Control": "no-store"})


@router.get("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}")
def get_pdf_statblock_review(world_id: str, review_id: UUID, request: Request):
    from application_state.pdf_statblock_review import read_review

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    review = read_review(world_id=_verified_world_id(world_id), review_id=review_id)
    if review is None:
        raise HTTPException(status_code=404, detail={"code": "pdf_statblock_review_not_found"})
    for locator in review["regions"]:
        _authorized_build_pdf_region(world_id, locator, request, hosted_read=True)
    require_build_pdf_access(request, world_id)
    return review


def _pdf_review_creature_draft_id(world_id: str, review_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"dungeonbuddy:pdf-review:{world_id}:{review_id}")


@router.get("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/publication")
def get_pdf_statblock_publication(world_id: str, review_id: UUID, request: Request):
    from application_state.world_mechanics.service import list_current
    from apps.live_control_server.services import native_threat_creation as creature

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    get_pdf_statblock_review(world_id, review_id, request)
    world_id = _verified_world_id(world_id)
    draft_id = _pdf_review_creature_draft_id(world_id, review_id)
    bound = creature.native.binding(world_id)
    prior = creature.existing(creature.native.read_repository(), bound, draft_id)
    if prior is None:
        require_build_pdf_access(request, world_id)
        return None
    published = creature.published(bound, draft_id, prior, replayed=True)
    associations = [
        association for association in list_current(world_id=world_id)
        if str(association.request.draft_id) == str(draft_id)
        and association.request.target.campaign_scope is None
        and association.request.target.node_id == published["node_id"]
        and association.request.target.native_world_id == published["native_world_id"]
        and association.request.target.binding_version == published["binding_version"]
    ]
    require_build_pdf_access(request, world_id)
    if len(associations) != 1 or creature.native.binding(world_id) != bound:
        return None
    return {"draft_id": draft_id, "revision_id": associations[0].proof.locator.revision_id}


@router.get("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/publication/statblock")
def get_published_pdf_statblock(
    world_id: str, review_id: UUID, draft_id: UUID, revision_id: str, request: Request,
):
    from apps.live_control_server.routes.statblock_candidates import open_saved_revision
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    if draft_id != _pdf_review_creature_draft_id(world_id, review_id):
        raise HTTPException(status_code=404, detail="Published statblock not found")
    publication = get_pdf_statblock_publication(world_id, review_id, request)
    if publication != {"draft_id": draft_id, "revision_id": revision_id}:
        raise HTTPException(status_code=404, detail="Published statblock not found")
    packet = open_saved_revision(str(draft_id), revision_id, world_id, request)
    require_build_pdf_access(request, world_id)
    return packet


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/publication")
def post_pdf_statblock_publication(
    world_id: str, review_id: UUID, request: Request, expected_revision: int = Query(ge=1),
):
    from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
    from application_state.world_mechanics.types import AssociateWorldMechanicsRequest, MechanicsLocator
    from apps.live_control_server.models.native_threat_creation import ConfirmNativeThreat, PrepareNativeThreat
    from apps.live_control_server.routes.native_threat_creation import call
    from apps.live_control_server.routes.world_mechanics_associations import (
        _associate_for_principal, list_associations,
    )
    from apps.live_control_server.services import native_threat_creation as creature, world_creature_selection
    from apps.live_control_server.services.hosted_native_graph_access import build_pdf_publication_principal

    principal = build_pdf_publication_principal(request, world_id)
    review = get_pdf_statblock_review(world_id, review_id, request)
    if review["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail="The PDF review changed before publication")
    def recheck_review():
        current = get_pdf_statblock_review(world_id, review_id, request)
        if current["revision"] != expected_revision or current["regions"] != review["regions"]:
            raise HTTPException(status_code=409, detail="The PDF review changed before publication")
        return build_pdf_publication_principal(request, world_id)

    draft_id = _pdf_review_creature_draft_id(world_id, review_id)
    draft = call(creature.owned_draft, draft_id, world_id)
    if draft.accepted_mechanics_ref is None:
        raise HTTPException(status_code=409, detail="Save mechanics before publishing")
    locator = MechanicsLocator.model_validate(draft.accepted_mechanics_ref.to_mechanics_locator().model_dump())

    def verify_source(root):
        verified, _, acceptance_id, revision_operation, exact = creature.resolve_saved_source(
            root, world_id=world_id, draft_id=str(draft_id), locator=locator,
        )
        provenance = ((exact.provenance or {}).get("accepted_through") or {}).get(PDF_REVIEW_PROVENANCE)
        operation = creature.get_acceptance_operation(root, draft_id=str(draft_id), operation_id=acceptance_id)
        recorded = (operation.request_body.get("accepted_through") or {}) if operation else {}
        creature.require(verified == draft and revision_operation is None
                         and recorded.get(PDF_REVIEW_PROVENANCE) == provenance and provenance == {
            "world_id": world_id, "review_id": str(review_id),
            "revision": expected_revision, "regions": review["regions"],
        }, "Saved mechanics do not belong to this PDF review revision")

    call(verify_source)
    principal = recheck_review()
    result = call(creature.status, draft_id, world_id, principal, authorize_write=recheck_review)
    if result is None:
        principal = recheck_review()
        prepared = call(creature.prepare, draft_id, PrepareNativeThreat(
            world_id=world_id, expected_draft_version=draft.version, mechanics_locator=locator,
        ), principal, authorize_write=recheck_review)
        if prepared["state"] == "published":
            result = prepared
        else:
            principal = recheck_review()
            result = call(creature.confirm, draft_id, ConfirmNativeThreat(
                review=prepared["review"], prepared=prepared["prepared"], token=prepared["token"],
            ), principal, authorize_write=recheck_review)
    prior = [
        entry for entry in list_associations(world_id, principal)
        if entry.request.target.node_id == result["node_id"] and entry.request.target.campaign_scope is None
    ]
    if prior:
        if len(prior) != 1 or prior[0].request.draft_id != draft_id or prior[0].proof.locator != locator:
            raise HTTPException(status_code=409, detail="This creature already has different saved mechanics")
    else:
        catalog = call(lambda _root: world_creature_selection.catalog(world_id))
        target = next((item for item in catalog.targets
                       if item.node_id == result["node_id"] and item.campaign_scope is None
                       and item.native_world_id == result["native_world_id"]
                       and item.binding_version == result["binding_version"]), None)
        if target is None:
            raise HTTPException(status_code=409, detail="Retry Publish when the creature is available for association")
        principal = recheck_review()
        _associate_for_principal(AssociateWorldMechanicsRequest(
            request_id=uuid4(), draft_id=draft_id, expected_draft_version=draft.version,
            target=target, expected_version=0, locator=locator,
        ), principal, authorize=recheck_review)
    recheck_review()
    return {"draft_id": draft_id, "revision_id": locator.revision_id}


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/creature-draft")
def post_pdf_statblock_creature_draft(
    world_id: str, review_id: UUID, request: Request,
    expected_revision: int = Query(ge=1),
):
    from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest
    from apps.live_control_server.routes.statblock_storage import statblock_data_root
    from apps.live_control_server.services.threat_draft_store import (
        ThreatDraftStoreError, create_threat_draft,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    review = get_pdf_statblock_review(world_id, review_id, request)
    world_id = _verified_world_id(world_id)
    if review["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"})
    definition = review["definition"]
    name = definition["identity"]["name"]
    draft_request = CreateWorldThreatDraftRequest(
        scope_mode="world", world_id=world_id, campaign_id=None,
        name=name, description=name, threat_kind="creature",
        generation_intent={"ruleset": definition["ruleset"]},
        graph_context_snapshot={"graph_revision_id": None},
        created_by="gm",
    )
    draft_id = _pdf_review_creature_draft_id(world_id, review_id)
    require_build_pdf_access(request, world_id)
    try:
        draft = create_threat_draft(statblock_data_root(repo_root()), draft_request, stable_id=draft_id)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    require_build_pdf_access(request, world_id)
    return {"draft_id": draft.draft_id, "version": draft.version}


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/validate")
def post_validate_pdf_statblock_review(
    world_id: str, review_id: UUID, request: Request,
    expected_revision: int = Query(ge=1),
):
    from apps.live_control_server.services.statblock_definition_validation import (
        ValidateDefinitionBuddyRequestV1, validate_definition,
    )

    review = get_pdf_statblock_review(world_id, review_id, request)
    if review["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"})
    candidate = ValidateDefinitionBuddyRequestV1.model_validate({"definition": review["definition"]})
    validation = validate_definition(definition=candidate.definition)
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    return {
        "revision": review["revision"],
        "regions": review["regions"],
        "validation": validation.model_dump(mode="json", by_alias=True),
    }


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/accept/{draft_id}")
def post_accept_pdf_statblock_review(
    world_id: str, review_id: UUID, draft_id: UUID,
    body: AcceptPdfStatblockReviewRequestV1, request: Request,
):
    from apps.live_control_server.routes.statblock_storage import statblock_data_root
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptThreatDraftMechanicsRequestV1,
    )
    from apps.live_control_server.services.statblock_mechanics_acceptance import (
        PDF_REVIEW_PROVENANCE, begin_or_resume_acceptance, recover_acceptance_operation,
    )
    from apps.live_control_server.services.statblock_acceptance_reconciliation import (
        get_acceptance_operation, list_acceptance_operations_for_draft,
    )
    from apps.live_control_server.services.threat_draft_store import (
        ThreatDraftStoreError, get_threat_draft,
    )

    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    require_build_pdf_access(request, world_id)
    world_id = _verified_world_id(world_id)
    if (
        getattr(request.state, "hosted_build_pdf_world", None) is not None
        and draft_id != _pdf_review_creature_draft_id(world_id, review_id)
    ):
        raise HTTPException(status_code=404, detail={"code": "threat_draft_not_found"})
    root = statblock_data_root(repo_root())
    draft_key = str(draft_id)
    try:
        draft = get_threat_draft(root, draft_key)
    except ThreatDraftStoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if draft.world_id != world_id:
        raise HTTPException(status_code=404, detail={"code": "threat_draft_not_found"})

    def recover(operation_id):
        require_build_pdf_access(request, world_id)
        if getattr(request.state, "hosted_build_pdf_world", None) is not None:
            get_pdf_statblock_review(world_id, review_id, request)
        result = recover_acceptance_operation(root, draft_id=draft_key, operation_id=operation_id)
        require_build_pdf_access(request, world_id)
        return result

    identity = {"world_id": world_id, "review_id": str(review_id), "revision": body.expected_revision}
    existing = get_acceptance_operation(root, draft_id=draft_key, operation_id=body.operation_id)
    if existing is not None:
        recorded = (existing.request_body.get("accepted_through") or {}).get(PDF_REVIEW_PROVENANCE, {})
        if (
            any(recorded.get(key) != value for key, value in identity.items())
            or existing.source_draft_version != body.expected_draft_version
            or existing.validation_receipt_digest != body.validation_definition_digest
        ):
            raise HTTPException(status_code=409, detail={"code": "pdf_statblock_acceptance_conflict"})
        return recover(body.operation_id)

    if draft.version != body.expected_draft_version:
        from apps.live_control_server.models.statblock_mechanics_acceptance import (
            AcceptThreatDraftMechanicsResponseV1,
        )
        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_key, operation_id=body.operation_id,
            result_label="acceptance_blocked", message="expected draft version mismatch",
        )
    locator = draft.accepted_mechanics_ref.to_mechanics_locator() if draft.accepted_mechanics_ref else None
    matches = []
    for operation in list_acceptance_operations_for_draft(root, draft_id=draft_key):
        provenance = (operation.request_body.get("accepted_through") or {}).get(PDF_REVIEW_PROVENANCE, {})
        recoverable = (
            operation.locator == locator and operation.authority_state in {"server_committed", "reconciled"}
            if locator is not None else
            operation.source_draft_version == draft.version
            and operation.authority_state in {"dispatched_unknown", "server_committed"}
        )
        if (
            recoverable
            and operation.validation_receipt_digest == body.validation_definition_digest
            and all(provenance.get(key) == value for key, value in identity.items())
        ):
            matches.append(operation)
    if len(matches) == 1:
        return recover(matches[0].operation_id)
    if matches or locator is not None:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_acceptance_conflict" if matches else "pdf_statblock_draft_already_has_mechanics"})

    review = get_pdf_statblock_review(world_id, review_id, request)
    if review["revision"] != body.expected_revision:
        raise HTTPException(status_code=409, detail={"code": "pdf_statblock_review_conflict"})
    result = begin_or_resume_acceptance(
        root,
        draft_id=draft_key,
        request=AcceptThreatDraftMechanicsRequestV1(
            operation_id=body.operation_id,
            expected_draft_version=body.expected_draft_version,
            definition=review["definition"],
            validation_receipt=body.validation_receipt,
            validation_definition_digest=body.validation_definition_digest,
            change_summary="Accept saved PDF statblock review",
        ),
        pdf_review={**identity, "regions": review["regions"]},
    )
    require_build_pdf_access(request, world_id)
    return result


@router.post("/worlds/{world_id}/build-pdf-sources/statblock-reviews/{review_id}/append/{draft_id}")
def post_append_pdf_statblock_review(
    world_id: str, review_id: UUID, draft_id: UUID,
    body: AppendPdfStatblockReviewRequest, request: Request,
):
    from apps.live_control_server.routes.statblock_candidates import _revision_call
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access
    from apps.live_control_server.services.statblock_saved_revision import append_pdf_review

    require_build_pdf_access(request, world_id)
    world_id = _verified_world_id(world_id)
    result = _revision_call(
        append_pdf_review, draft_id=str(draft_id), world_id=world_id, review_id=review_id,
        request=body, load_review=lambda: get_pdf_statblock_review(world_id, review_id, request),
        authorize=lambda: require_build_pdf_access(request, world_id),
    )
    require_build_pdf_access(request, world_id)
    return result


@router.post("/worlds/{world_id}/build-pdf-sources/region:validate", status_code=204)
def post_validate_build_pdf_region(world_id: str, body: dict, request: Request):
    from fastapi.responses import Response
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    _authorized_build_pdf_region(world_id, body, request, hosted_read=True)
    require_build_pdf_access(request, world_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/worlds/{world_id}/build-pdf-sources/open")
def post_open_build_pdf_source(world_id: str, body: dict, request: Request, render: bool = False):
    from fastapi.responses import Response
    from apps.live_control_server.services.hosted_native_graph_access import require_build_pdf_access

    pdf, region = _authorized_build_pdf_region(world_id, body, request, hosted_read=True)
    if render:
        pdf = _render_build_pdf_region(pdf, region)
    require_build_pdf_access(request, world_id)
    return Response(
        pdf,
        media_type="image/png" if render else "application/pdf",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/worlds/{world_id}/build-proposals")
def post_build_document_proposal(world_id: str, body: BuildDocumentProposalRequest, request: Request):
    """Creative authoring proposal only; workspace Save remains a separate owner."""
    from apps.live_control_server.services.build_document_proposal import compose, _public
    from llm.generation_sync import run_awaitable_sync
    enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    if request.query_params or body.basis.world_id != verified or body.origin is not None:
        raise HTTPException(status_code=422, detail={"code": "build_compose_scope_mismatch"})
    try:
        return {"schema": "dmb_build_proposal_response_v1", "record": _public(run_awaitable_sync(lambda: compose(body)))}
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "build_compose_state_unavailable"}) from exc
    except Exception as exc:
        raise HTTPException(status_code=getattr(exc, "status_code", 503), detail={"code": "build_compose_failed", "action_id": str(body.idempotency_key)}) from exc


@router.get("/worlds/{world_id}/build-proposals")
def list_build_document_proposals(world_id: str, conversation_id: UUID, request: Request):
    from application_state.build_proposal.service import BuildProposalService
    from apps.live_control_server.services.build_document_proposal import _public
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id, authorize_local=enforce_native_graph_gm)
    verified = _verified_world_id(world_id)
    if set(request.query_params) != {"conversation_id"} or len(request.query_params.getlist("conversation_id")) != 1:
        raise HTTPException(status_code=422, detail="one exact conversation selector is required")
    try:
        return {"schema": "dmb_build_proposal_list_v1", "world_id": verified, "conversation_id": str(conversation_id),
            "records": [_public(record) for record in BuildProposalService().list(verified, conversation_id)]}
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "build_proposal_unavailable"}) from exc


@router.get("/worlds/{world_id}/build-proposals/{action_id}")
def get_build_document_proposal(world_id: str, action_id: UUID, request: Request):
    from application_state.build_proposal.service import BuildProposalService
    from apps.live_control_server.services.build_document_proposal import _public
    enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail="Build proposal does not accept query selectors")
    try:
        return {"schema": "dmb_build_proposal_response_v1", "record": _public(BuildProposalService().get(verified, action_id))}
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "build_proposal_unavailable"}) from exc


@router.get("/worlds/{world_id}/build-proposals/{action_id}/prompt")
def get_build_document_proposal_prompt(world_id: str, action_id: UUID, request: Request):
    from fastapi.responses import JSONResponse
    from apps.live_control_server.services.build_document_proposal import read_prompt
    enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    if request.query_params:
        raise HTTPException(status_code=422, detail="Build prompt does not accept query selectors")
    try:
        return JSONResponse(read_prompt(verified, action_id), headers={"Cache-Control": "no-store"})
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "build_prompt_unavailable"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "build_prompt_unavailable"}) from exc


@router.post("/worlds/{world_id}/build-proposals/{action_id}/inserted")
def report_build_document_proposal_inserted(world_id: str, action_id: UUID, request: Request, expected_revision: int = Query(ge=1)):
    from application_state.build_proposal.service import BuildProposalService
    from apps.live_control_server.services.build_document_proposal import _public
    enforce_native_graph_gm(request)
    verified = _verified_world_id(world_id)
    if set(request.query_params) != {"expected_revision"} or len(request.query_params.getlist("expected_revision")) != 1:
        raise HTTPException(status_code=422, detail="one exact revision selector is required")
    try:
        return {"schema": "dmb_build_proposal_response_v1", "record": _public(BuildProposalService().report_inserted(verified, action_id, expected_revision=expected_revision))}
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": "build_proposal_insert_status_unavailable"}) from exc

# Review is a separate owner from immutable generated proposal/provider evidence.
from .build_proposal_reviews import router as build_proposal_review_router
router.include_router(build_proposal_review_router)
