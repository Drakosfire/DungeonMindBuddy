"""Named buddy_files first-world initialization adapter (CUTOVER D.2C2 / D.3 owner).

Wraps the legacy Kernel reviewed-world initializer and filesystem classification
until D.3. Not a production fallback.
"""

from __future__ import annotations

from pathlib import Path

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationError,
    WorldGraphInitializationReceipt,
    WorldGraphInitializationRequest,
    WorldGraphInitializationState,
)
from apps.live_control_server.services.first_world_graph import classify_world_graph_state
from graph_memory.kernel.contributions import compute_contribution_payload_sha256
from graph_memory.kernel.reviewed_world_initialization import (
    REVIEWED_PLAN_SCHEMA,
    SESSIONLESS_FOCUS_SESSION_ID,
    ReviewedWorldInitializationAttestation,
    ReviewedWorldInitializationError,
    ReviewedWorldInitializationPlan,
    initialize_reviewed_world,
)


def _graph_root(world_root: Path | None) -> Path:
    return (world_root if world_root is not None else world_graph_root()).resolve()


def _kernel_plan(request: WorldGraphInitializationRequest) -> ReviewedWorldInitializationPlan:
    contribution = request.reviewed_contribution
    payload_hex = compute_contribution_payload_sha256(contribution).removeprefix("sha256:")
    decision_hex = (request.decision_digest or "").removeprefix("sha256:")
    if len(decision_hex) != 64:
        raise WorldGraphInitializationError(
            "buddy_files first-world initialize requires a 64-hex decision digest",
            code="inexpressible",
            details={"decision_digest": request.decision_digest},
        )
    run_id = request.run_id or ""
    workspace_document_id = request.workspace_document_id or ""
    workspace_document_revision = request.workspace_document_revision or ""
    artifact = request.source_artifact
    return ReviewedWorldInitializationPlan(
        schema=REVIEWED_PLAN_SCHEMA,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus_session_id=SESSIONLESS_FOCUS_SESSION_ID,
        plan_id=request.source_plan_id,
        contribution_id=contribution.contribution_id,
        contribution_payload_sha256=payload_hex,
        approval_attestation=ReviewedWorldInitializationAttestation(
            run_id=run_id,
            source_artifact_id=getattr(artifact, "source_artifact_id", ""),
            source_revision_id=request.source_revision_token,
            workspace_document_id=workspace_document_id,
            workspace_document_revision=str(workspace_document_revision),
            decision_digest=decision_hex,
        ),
    )


class BuddyFilesWorldGraphInitializationAdapter:
    """Legacy filesystem/Kernel first-world initializer (D.3 deletion owner)."""

    def __init__(self, world_root: Path | None = None) -> None:
        self._world_root = world_root

    def probe(self, world_id: str) -> WorldGraphInitializationState:
        state = classify_world_graph_state(_graph_root(self._world_root), world_id)
        if state == "unreadable":
            return WorldGraphInitializationState(world_id=world_id, state="unreadable")
        if state == "initialized":
            return WorldGraphInitializationState(world_id=world_id, state="initialized")
        return WorldGraphInitializationState(world_id=world_id, state="uninitialized")

    def initialize(
        self,
        request: WorldGraphInitializationRequest,
    ) -> WorldGraphInitializationReceipt:
        try:
            result = initialize_reviewed_world(
                _graph_root(self._world_root),
                plan=_kernel_plan(request),
                contribution=request.reviewed_contribution,
                actor=request.actor,
            )
        except ReviewedWorldInitializationError as exc:
            if exc.state == "blocked":
                raise WorldGraphInitializationError(
                    str(exc),
                    code="already_initialized",
                    details={"diagnostics": list(exc.diagnostics)},
                ) from exc
            raise WorldGraphInitializationError(
                str(exc),
                code="initialization_failed",
                details={"diagnostics": list(exc.diagnostics), "state": exc.state},
            ) from exc
        receipt = result.receipt
        published = (
            receipt.initial_head_revision_id
            if receipt is not None
            else result.initial_head_revision_id
        )
        baseline = (
            receipt.baseline_revision_id
            if receipt is not None
            else result.baseline_revision_id
        )
        if not published:
            raise WorldGraphInitializationError(
                "legacy first-world initialization did not publish a head",
                code="initialization_failed",
                details={"outcome": result.outcome},
            )
        outcome = (
            "already_initialized"
            if result.outcome == "already_initialized"
            else "initialized"
        )
        accepted = tuple(
            item.assertion_id
            for item in request.reviewed_contribution.accepted_assertions
        )
        return WorldGraphInitializationReceipt(
            world_id=request.world_id,
            initialization_id=request.initialization_id,
            published_revision_id=published,
            reviewed_contribution_id=request.reviewed_contribution.contribution_id,
            reviewed_contribution_sha256=compute_contribution_payload_sha256(
                request.reviewed_contribution
            ),
            accepted_assertion_ids=accepted,
            outcome=outcome,
            baseline_revision_id=baseline,
        )
