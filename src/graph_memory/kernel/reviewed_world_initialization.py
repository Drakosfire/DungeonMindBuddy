"""Reviewed-source world initialization (CON-READY CR02A / first-world publish).

Separate authority from legacy certified-bundle bootstrap. Shares the Kernel
staging / merge / verify / atomic-rename transaction with
``world_initialization.py``; does not fabricate Git/bundle attestation fields.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.contributions import (
    canonical_payload_sha256,
    compute_contribution_payload_sha256,
)
from graph_memory.kernel.world_graph import (
    load_current_world_graph,
    open_world_graph_head,
)
from graph_memory.kernel.world_initialization import (
    WorldInitializationError,
    atomic_write_json,
    classify_head_relative_to_initialization,
    cleanup_world_initialization_staging,
    promote_staged_world_initialization,
    stage_and_verify_world_initialization,
)
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.storage import try_open_world_graph_head

REVIEWED_PLAN_SCHEMA = "dmb_reviewed_world_initialization_plan_v1"
REVIEWED_RECEIPT_SCHEMA = "dmb_reviewed_world_initialization_receipt_v1"

# Technical no-focus: sessionless / world-level graphs. Never invent session-*.
SESSIONLESS_FOCUS_SESSION_ID = ""

ReviewedWorldInitializationOutcome = Literal[
    "published",
    "already_initialized",
    "blocked",
    "error",
]

ReviewedWorldInitializationState = Literal[
    "ready",
    "already_initialized",
    "active_head_advanced",
    "blocked",
    "inconsistent_lineage",
    "error",
]


class _ReviewedInitModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReviewedWorldInitializationAttestation(_ReviewedInitModel):
    """Truthful reviewed-source authority (run / source / decision).

    Distinct from ``WorldInitializationApprovalAttestation`` — no bundle or
    Git merge SHA fields.
    """

    run_id: str
    source_artifact_id: str
    source_revision_id: str
    workspace_document_id: str
    workspace_document_revision: str
    decision_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ReviewedWorldInitializationPlan(_ReviewedInitModel):
    """Sealed plan for first-world publish from one reviewed contribution."""

    schema_: Literal["dmb_reviewed_world_initialization_plan_v1"] = Field(
        alias="schema"
    )
    world_id: str
    campaign_id: str
    focus_session_id: str = SESSIONLESS_FOCUS_SESSION_ID
    plan_id: str
    contribution_id: str
    contribution_payload_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_attestation: ReviewedWorldInitializationAttestation

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    @field_validator("focus_session_id")
    @classmethod
    def _require_sessionless_focus(cls, value: str) -> str:
        if value != SESSIONLESS_FOCUS_SESSION_ID:
            raise ValueError(
                "reviewed world initialization requires focus_session_id='' "
                "(sessionless technical no-focus); do not invent session-*"
            )
        return value


class ReviewedWorldInitializationReceipt(_ReviewedInitModel):
    """Durable proof that an exact reviewed plan initialized W."""

    schema_: Literal["dmb_reviewed_world_initialization_receipt_v1"] = Field(
        alias="schema"
    )
    world_id: str
    campaign_id: str
    focus_session_id: str
    run_id: str
    source_artifact_id: str
    source_revision_id: str
    workspace_document_id: str
    workspace_document_revision: str
    plan_id: str
    plan_digest: str
    decision_digest: str
    contribution_id: str
    contribution_payload_sha256: str
    baseline_revision_id: str
    initial_head_revision_id: str
    actor: str
    created_at: str

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class ReviewedWorldInitializationResult(_ReviewedInitModel):
    published: bool
    outcome: ReviewedWorldInitializationOutcome
    state: ReviewedWorldInitializationState
    baseline_revision_id: str | None
    initial_head_revision_id: str | None
    current_head_revision_id: str | None
    receipt: ReviewedWorldInitializationReceipt | None
    diagnostics: list[str] = Field(default_factory=list)


class ReviewedWorldInitializationError(RuntimeError):
    """Fail-closed reviewed initialization error."""

    def __init__(
        self,
        message: str,
        *,
        state: ReviewedWorldInitializationState = "error",
        outcome: ReviewedWorldInitializationOutcome = "error",
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.state = state
        self.outcome = outcome
        self.diagnostics = list(diagnostics or [])


def compute_reviewed_initialization_plan_digest(
    plan: ReviewedWorldInitializationPlan,
) -> str:
    """Hash the complete canonical reviewed initialization plan payload."""
    return canonical_payload_sha256(plan.model_dump(mode="json", by_alias=True))


def compute_reviewed_initialization_attestation_digest(
    attestation: ReviewedWorldInitializationAttestation,
) -> str:
    """Hash the complete canonical reviewed attestation payload."""
    return canonical_payload_sha256(attestation.model_dump(mode="json", by_alias=True))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _baseline_operation_id(world_id: str, plan_id: str) -> str:
    return f"reviewed-world-init:{world_id}:{plan_id}:empty-baseline"


def read_reviewed_initialization_receipt(
    root: Path,
    world_id: str,
) -> ReviewedWorldInitializationReceipt | None:
    """Load the reviewed-source initialization receipt for a world, if present."""
    path = world_paths.reviewed_initialization_receipt_path(root, world_id)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ReviewedWorldInitializationReceipt.model_validate(payload)


def _receipt_matches_plan(
    receipt: ReviewedWorldInitializationReceipt,
    *,
    plan: ReviewedWorldInitializationPlan,
    plan_digest: str,
) -> bool:
    attestation = plan.approval_attestation
    return (
        receipt.world_id == plan.world_id
        and receipt.campaign_id == plan.campaign_id
        and receipt.focus_session_id == plan.focus_session_id
        and receipt.plan_id == plan.plan_id
        and receipt.plan_digest == plan_digest
        and receipt.decision_digest == attestation.decision_digest
        and receipt.contribution_id == plan.contribution_id
        and receipt.contribution_payload_sha256 == plan.contribution_payload_sha256
        and receipt.run_id == attestation.run_id
        and receipt.source_artifact_id == attestation.source_artifact_id
        and receipt.source_revision_id == attestation.source_revision_id
        and receipt.workspace_document_id == attestation.workspace_document_id
        and receipt.workspace_document_revision
        == attestation.workspace_document_revision
    )


def inspect_reviewed_world_initialization_state(
    root: Path,
    *,
    world_id: str,
    plan: ReviewedWorldInitializationPlan,
    plan_digest: str | None = None,
) -> ReviewedWorldInitializationState:
    """Classify whether reviewed initialization may proceed for the plan."""
    if world_id != plan.world_id:
        return "blocked"
    world_dir = world_paths.world_dir(root, world_id)
    if not world_dir.exists():
        return "ready"

    receipt = read_reviewed_initialization_receipt(root, world_id)
    if receipt is None:
        return "blocked"
    plan_digest = plan_digest or compute_reviewed_initialization_plan_digest(plan)
    if not _receipt_matches_plan(receipt, plan=plan, plan_digest=plan_digest):
        return "blocked"

    head = try_open_world_graph_head(root, world_id)
    if head is None:
        return "blocked"
    try:
        legacy_state = classify_head_relative_to_initialization(
            root,
            world_id,
            initial_head_revision_id=receipt.initial_head_revision_id,
            current_head_revision_id=head.head_revision_id,
        )
    except WorldInitializationError as exc:
        if exc.state == "inconsistent_lineage":
            return "inconsistent_lineage"
        raise

    if legacy_state == "active":
        return "already_initialized"
    if legacy_state == "active_head_advanced":
        return "active_head_advanced"
    return "inconsistent_lineage"


def _bind_single_contribution(
    plan: ReviewedWorldInitializationPlan,
    contribution: GraphContribution,
    *,
    diagnostics: list[str],
) -> str:
    if plan.focus_session_id != SESSIONLESS_FOCUS_SESSION_ID:
        raise ReviewedWorldInitializationError(
            "reviewed initialization requires sessionless focus_session_id=''",
            state="error",
            outcome="error",
            diagnostics=diagnostics,
        )
    if contribution.contribution_id != plan.contribution_id:
        raise ReviewedWorldInitializationError(
            "contribution is not bound to plan.contribution_id",
            state="error",
            outcome="error",
            diagnostics=[
                *diagnostics,
                f"expected_id={plan.contribution_id}",
                f"actual_id={contribution.contribution_id}",
            ],
        )
    if contribution.world_id != plan.world_id:
        raise ReviewedWorldInitializationError(
            "contribution world_id does not match plan.world_id: "
            f"{contribution.contribution_id}",
            state="error",
            outcome="error",
            diagnostics=diagnostics,
        )
    if contribution.identity_decision_ids:
        raise ReviewedWorldInitializationError(
            "identity decision references are unsupported for reviewed init: "
            f"{contribution.contribution_id}",
            state="error",
            outcome="error",
            diagnostics=diagnostics,
        )
    actual_digest = compute_contribution_payload_sha256(contribution)
    if actual_digest != plan.contribution_payload_sha256:
        raise ReviewedWorldInitializationError(
            "contribution payload digest does not match reviewed plan: "
            f"{contribution.contribution_id}",
            state="error",
            outcome="error",
            diagnostics=[
                *diagnostics,
                f"expected_payload_sha256={plan.contribution_payload_sha256}",
                f"actual_payload_sha256={actual_digest}",
            ],
        )
    return compute_reviewed_initialization_plan_digest(plan)


def _build_reviewed_receipt(
    root: Path,
    *,
    plan: ReviewedWorldInitializationPlan,
    actor: str,
    baseline_revision_id: str,
    plan_digest: str,
) -> ReviewedWorldInitializationReceipt:
    head, _revision, _store = load_current_world_graph(root, plan.world_id)
    attestation = plan.approval_attestation
    return ReviewedWorldInitializationReceipt(
        schema=REVIEWED_RECEIPT_SCHEMA,
        world_id=plan.world_id,
        campaign_id=plan.campaign_id,
        focus_session_id=plan.focus_session_id,
        run_id=attestation.run_id,
        source_artifact_id=attestation.source_artifact_id,
        source_revision_id=attestation.source_revision_id,
        workspace_document_id=attestation.workspace_document_id,
        workspace_document_revision=attestation.workspace_document_revision,
        plan_id=plan.plan_id,
        plan_digest=plan_digest,
        decision_digest=attestation.decision_digest,
        contribution_id=plan.contribution_id,
        contribution_payload_sha256=plan.contribution_payload_sha256,
        baseline_revision_id=baseline_revision_id,
        initial_head_revision_id=head.head_revision_id,
        actor=actor,
        created_at=_utc_now_iso(),
    )


def _write_reviewed_receipt(
    root: Path,
    *,
    world_id: str,
    receipt: ReviewedWorldInitializationReceipt,
) -> None:
    path = world_paths.reviewed_initialization_receipt_path(root, world_id)
    atomic_write_json(path, receipt.model_dump(mode="json", by_alias=True))


def _already_initialized_result(
    root: Path,
    *,
    world_id: str,
    state: ReviewedWorldInitializationState,
    diagnostics: list[str],
) -> ReviewedWorldInitializationResult:
    receipt = read_reviewed_initialization_receipt(root, world_id)
    head = open_world_graph_head(root, world_id)
    return ReviewedWorldInitializationResult(
        published=False,
        outcome="already_initialized",
        state=state,
        baseline_revision_id=receipt.baseline_revision_id if receipt else None,
        initial_head_revision_id=(
            receipt.initial_head_revision_id if receipt else None
        ),
        current_head_revision_id=head.head_revision_id,
        receipt=receipt,
        diagnostics=diagnostics,
    )


def initialize_reviewed_world(
    root: Path,
    *,
    plan: ReviewedWorldInitializationPlan,
    contribution: GraphContribution,
    actor: str,
) -> ReviewedWorldInitializationResult:
    """Initialize a world from one reviewed contribution with atomic promotion.

    Uses the shared Kernel staging/merge/verify/rename transaction. Writes a
    ``dmb_reviewed_world_initialization_receipt_v1`` — never a legacy bundle
    receipt or fabricated ``approved_bundle_merge_sha``.
    """
    diagnostics: list[str] = []
    world_paths.assert_safe_world_id(plan.world_id)
    plan_digest = _bind_single_contribution(
        plan, contribution, diagnostics=diagnostics
    )

    existing_state = inspect_reviewed_world_initialization_state(
        root,
        world_id=plan.world_id,
        plan=plan,
        plan_digest=plan_digest,
    )
    if existing_state == "already_initialized":
        diagnostics.append("idempotent_noop:reviewed_world_already_initialized")
        return _already_initialized_result(
            root,
            world_id=plan.world_id,
            state="already_initialized",
            diagnostics=diagnostics,
        )
    if existing_state == "active_head_advanced":
        diagnostics.append("idempotent_noop:head_advanced_past_initial")
        return _already_initialized_result(
            root,
            world_id=plan.world_id,
            state="active_head_advanced",
            diagnostics=diagnostics,
        )
    if existing_state == "inconsistent_lineage":
        raise ReviewedWorldInitializationError(
            f"world {plan.world_id!r} head is not a descendant of the initialized head",
            state="inconsistent_lineage",
            outcome="blocked",
            diagnostics=diagnostics,
        )
    if existing_state == "blocked":
        raise ReviewedWorldInitializationError(
            f"world {plan.world_id!r} exists without a matching reviewed "
            "initialization receipt",
            state="blocked",
            outcome="blocked",
            diagnostics=diagnostics,
        )

    attestation_digest = compute_reviewed_initialization_attestation_digest(
        plan.approval_attestation
    )
    staging_root: Path | None = None
    try:
        staging_root, staged_world, baseline_revision_id = (
            stage_and_verify_world_initialization(
                root,
                world_id=plan.world_id,
                campaign_id=plan.campaign_id,
                focus_session_id=SESSIONLESS_FOCUS_SESSION_ID,
                contributions=[contribution],
                ordered_contribution_ids=[plan.contribution_id],
                ordered_payload_sha256s=[plan.contribution_payload_sha256],
                initialization_plan_digest=plan_digest,
                initialization_attestation_digest=attestation_digest,
                baseline_operation_id=_baseline_operation_id(
                    plan.world_id, plan.plan_id
                ),
                diagnostics=diagnostics,
            )
        )

        receipt = _build_reviewed_receipt(
            staging_root,
            plan=plan,
            actor=actor,
            baseline_revision_id=baseline_revision_id,
            plan_digest=plan_digest,
        )
        _write_reviewed_receipt(
            staging_root, world_id=plan.world_id, receipt=receipt
        )

        promote_staged_world_initialization(
            root,
            world_id=plan.world_id,
            staged_world=staged_world,
            diagnostics=diagnostics,
        )
    except ReviewedWorldInitializationError:
        if staging_root is not None:
            cleanup_world_initialization_staging(staging_root)
        raise
    except WorldInitializationError as exc:
        if staging_root is not None:
            cleanup_world_initialization_staging(staging_root)
        outcome: ReviewedWorldInitializationOutcome = (
            "blocked" if exc.state == "blocked_existing_world" else "error"
        )
        state: ReviewedWorldInitializationState = (
            "blocked" if exc.state == "blocked_existing_world" else "error"
        )
        if exc.state == "inconsistent_lineage":
            state = "inconsistent_lineage"
            outcome = "blocked"
        raise ReviewedWorldInitializationError(
            str(exc),
            state=state,
            outcome=outcome,
            diagnostics=[*diagnostics, *exc.diagnostics],
        ) from exc
    except Exception as exc:
        if staging_root is not None:
            cleanup_world_initialization_staging(staging_root)
        raise ReviewedWorldInitializationError(
            f"reviewed world initialization failed: {exc}",
            state="error",
            outcome="error",
            diagnostics=diagnostics,
        ) from exc

    # os.rename above is the irreversible commit point.
    try:
        cleanup_world_initialization_staging(staging_root)
    except Exception as exc:
        try:
            diagnostics.append(
                f"post_promotion_cleanup_failed:{type(exc).__name__}:{exc}"
            )
        except Exception:
            pass
    try:
        diagnostics.append("reviewed_initialization_complete")
    except Exception:
        pass

    return ReviewedWorldInitializationResult(
        published=True,
        outcome="published",
        state="already_initialized",
        baseline_revision_id=baseline_revision_id,
        initial_head_revision_id=receipt.initial_head_revision_id,
        current_head_revision_id=receipt.initial_head_revision_id,
        receipt=receipt,
        diagnostics=diagnostics,
    )
