"""Prepare/apply durable identity merge materialization for Graph Review."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root
from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphMergeObjectsAssertion,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    overlay_file_token,
    stable_json_digest,
    validate_authoring_campaign_scope,
)
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    _resolve_repo_contained_path,
)
from graph_memory.union_supergraph.load import load_union_supergraph_store
from graph_memory.union_supergraph.merge_reconciliation import (
    MergeAssertionPlan,
    ReconciliationDiagnostic,
    UnionSupergraphMergePlan,
    plan_authored_merge_reconciliation,
)
from graph_memory.union_supergraph.merge_reconciliation_apply import (
    UnionSupergraphApplyResult,
    applied_identity_merge_assertion_ids,
    apply_union_supergraph_merge_plan_to_file,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore

CONFIRM_TOKEN_KIND = "graph_merge_reconciliation_apply_confirmation_v1"


class GraphMergeReconciliationMaterializeError(ValueError):
    status_code = 422

    def __init__(self, message: str, *, code: str = "invalid_request", status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class GraphMergeReconciliationDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: Literal["error", "warning", "info"] = "info"
    assertion_id: str | None = None
    node_id: str | None = None


class GraphMergeReconciliationPlanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_assertion_count: int
    applicable_assertion_count: int
    already_materialized_assertion_count: int
    skipped_assertion_count: int
    redirect_count: int
    edge_rewire_count: int
    edge_dedupe_count: int


class GraphMergeReconciliationApplySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    redirects_added: int
    merge_records_added: int
    survivor_nodes_created: int
    survivor_nodes_updated: int
    merged_away_nodes_marked: int
    edges_rewired: int
    edges_deduped: int


class GraphMergeReconciliationPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    campaign_id: str = Field(alias="campaignId")
    campaign_rel: str | None = Field(default=None, alias="campaignRel")
    session_id: str | None = Field(default=None, alias="sessionId")
    preview_union_store_path: str = Field(alias="previewUnionStorePath")
    materialization_pass_id: str | None = Field(default=None, alias="materializationPassId")


class GraphMergeReconciliationApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    campaign_id: str = Field(alias="campaignId")
    campaign_rel: str | None = Field(default=None, alias="campaignRel")
    session_id: str | None = Field(default=None, alias="sessionId")
    preview_union_store_path: str = Field(alias="previewUnionStorePath")
    materialization_pass_id: str = Field(alias="materializationPassId")
    confirm_token: str = Field(alias="confirmToken")
    overlay_token: str = Field(alias="overlayToken")
    union_store_token: str = Field(alias="unionStoreToken")


class GraphMergeReconciliationPrepareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prepared: bool
    campaign_id: str
    session_id: str | None
    overlay_path: str
    union_store_path: str
    materialization_pass_id: str
    overlay_token: str
    union_store_token: str
    plan_digest: str
    confirm_token: str
    summary: GraphMergeReconciliationPlanSummary
    diagnostics: list[GraphMergeReconciliationDiagnostic]
    no_mutation_guarantees: list[str]


class GraphMergeReconciliationApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applied: bool
    campaign_id: str
    session_id: str | None
    overlay_path: str
    union_store_path: str
    backup_path: str | None
    materialization_pass_id: str
    applied_assertion_ids: list[str]
    skipped_assertion_ids: list[str]
    summary: GraphMergeReconciliationApplySummary
    diagnostics: list[GraphMergeReconciliationDiagnostic]
    no_mutation_guarantees: list[str]


def _no_mutation_guarantees() -> list[str]:
    return [
        "Prepare wrote nothing to disk.",
        "Source recap markdown was not mutated.",
        "Extracted graph run artifacts were not mutated.",
        "Candidate graph gold was not mutated.",
        "Apply writes only the selected union graph store (with backup).",
    ]


def union_store_file_token(path: Path, *, campaign_id: str) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return stable_json_digest({"missing_union_store": campaign_id})


def resolve_repo_path(root: Path, value: str) -> Path:
    try:
        return _resolve_repo_contained_path(Path(value), root)
    except ValueError as exc:
        raise GraphMergeReconciliationMaterializeError(
            str(exc),
            code="unsafe_union_store_path",
        ) from exc
    except FileNotFoundError as exc:
        raise GraphMergeReconciliationMaterializeError(
            str(exc),
            code="union_store_not_found",
            status_code=404,
        ) from exc


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def _to_api_diagnostic(item: ReconciliationDiagnostic) -> GraphMergeReconciliationDiagnostic:
    return GraphMergeReconciliationDiagnostic(
        code=item.code,
        message=item.message,
        severity=item.severity,
        assertion_id=item.assertion_id,
        node_id=item.node_id,
    )


def merge_plan_digest_payload(plan: UnionSupergraphMergePlan) -> dict[str, object]:
    return {
        "campaign_id": plan.campaign_id,
        "materialization_pass_id": plan.materialization_pass_id,
        "plans": [
            {
                "assertion_id": assertion_plan.assertion_id,
                "survivor_node_id": assertion_plan.survivor_node_id,
                "merged_away_node_ids": list(assertion_plan.merged_away_node_ids),
                "redirects": [
                    {
                        "from_node_id": redirect.from_node_id,
                        "to_node_id": redirect.to_node_id,
                        "redirect_id": redirect.redirect_id,
                    }
                    for redirect in assertion_plan.redirects
                ],
                "edges_to_rewire": [
                    {
                        "edge_id": edge.edge_id,
                        "planned_source_node_id": edge.planned_source_node_id,
                        "planned_target_node_id": edge.planned_target_node_id,
                    }
                    for edge in assertion_plan.edges_to_rewire
                ],
            }
            for assertion_plan in plan.plans
        ],
    }


def merge_plan_digest(plan: UnionSupergraphMergePlan) -> str:
    return stable_json_digest(merge_plan_digest_payload(plan))


def actionable_assertion_plans(
    plan: UnionSupergraphMergePlan,
    union_store: UnionSupergraphStore,
) -> tuple[MergeAssertionPlan, ...]:
    applied_ids = applied_identity_merge_assertion_ids(union_store)
    return tuple(
        assertion_plan
        for assertion_plan in plan.plans
        if assertion_plan.assertion_id not in applied_ids
    )


def actionable_merge_plan(
    plan: UnionSupergraphMergePlan,
    union_store: UnionSupergraphStore,
) -> UnionSupergraphMergePlan:
    actionable_plans = actionable_assertion_plans(plan, union_store)
    return UnionSupergraphMergePlan(
        campaign_id=plan.campaign_id,
        materialization_pass_id=plan.materialization_pass_id,
        plans=actionable_plans,
        diagnostics=plan.diagnostics,
    )


def derive_materialization_pass_id(
    *,
    campaign_id: str,
    session_id: str | None,
    plan_digest: str,
    requested: str | None,
) -> str:
    if requested and requested.strip():
        return requested.strip()
    session_part = session_id or "no-session"
    digest_part = plan_digest[:16]
    raw = f"materialize:{campaign_id}:{session_part}:{digest_part}"
    return raw.replace("/", "_").replace(" ", "_")


def build_merge_reconciliation_confirm_token(
    *,
    campaign_id: str,
    session_id: str | None,
    overlay_path: str,
    overlay_token: str,
    union_store_path: str,
    union_store_token: str,
    materialization_pass_id: str,
    plan_digest: str,
) -> str:
    return stable_json_digest(
        {
            "kind": CONFIRM_TOKEN_KIND,
            "campaign_id": campaign_id,
            "session_id": session_id,
            "overlay_path": overlay_path,
            "overlay_token": overlay_token,
            "union_store_path": union_store_path,
            "union_store_token": union_store_token,
            "materialization_pass_id": materialization_pass_id,
            "plan_digest": plan_digest,
        }
    )


def _count_merge_assertions(overlay) -> int:
    return sum(
        1
        for assertion in overlay.assertions
        if isinstance(assertion, AuthoredGraphMergeObjectsAssertion)
    )


def _plan_summary(
    plan: UnionSupergraphMergePlan,
    merge_assertion_count: int,
    union_store: UnionSupergraphStore,
) -> GraphMergeReconciliationPlanSummary:
    applied_ids = applied_identity_merge_assertion_ids(union_store)
    actionable = actionable_assertion_plans(plan, union_store)
    already_materialized = sum(
        1 for assertion_plan in plan.plans if assertion_plan.assertion_id in applied_ids
    )
    redirect_count = sum(len(item.redirects) for item in actionable)
    edge_rewire_count = sum(len(item.edges_to_rewire) for item in actionable)
    return GraphMergeReconciliationPlanSummary(
        merge_assertion_count=merge_assertion_count,
        applicable_assertion_count=len(actionable),
        already_materialized_assertion_count=already_materialized,
        skipped_assertion_count=max(0, merge_assertion_count - len(plan.plans)),
        redirect_count=redirect_count,
        edge_rewire_count=edge_rewire_count,
        edge_dedupe_count=0,
    )


def _apply_summary(result: UnionSupergraphApplyResult) -> GraphMergeReconciliationApplySummary:
    return GraphMergeReconciliationApplySummary(
        redirects_added=result.redirects_added,
        merge_records_added=result.merge_records_added,
        survivor_nodes_created=result.survivor_nodes_created,
        survivor_nodes_updated=result.survivor_nodes_updated,
        merged_away_nodes_marked=result.merged_away_nodes_marked,
        edges_rewired=result.edges_rewired,
        edges_deduped=result.edges_deduped,
    )


def _resolve_materialization_paths(
    request: GraphMergeReconciliationPrepareRequest | GraphMergeReconciliationApplyRequest,
    *,
    corpus_root: Path | None,
    repo_root_override: Path | None = None,
) -> tuple[GraphAuthoringOverlayStore, Path, Path, str, str]:
    validate_authoring_campaign_scope(request.campaign_id, request.campaign_rel)

    root = (repo_root_override or repo_root()).resolve()
    union_store_path = resolve_repo_path(root, request.preview_union_store_path)

    store = _resolve_store(corpus_root)
    overlay_path = store.overlay_path(request.campaign_id, campaign_rel=request.campaign_rel)
    overlay_token = overlay_file_token(overlay_path, campaign_id=request.campaign_id)
    union_store_token = union_store_file_token(union_store_path, campaign_id=request.campaign_id)
    return store, overlay_path, union_store_path, overlay_token, union_store_token


def _plan_materialization(
    request: GraphMergeReconciliationPrepareRequest | GraphMergeReconciliationApplyRequest,
    *,
    corpus_root: Path | None,
    repo_root_override: Path | None = None,
    overlay_path: Path | None = None,
    union_store_path: Path | None = None,
) -> tuple[
    GraphAuthoringOverlayStore,
    Path,
    Path,
    str,
    str,
    UnionSupergraphStore,
    UnionSupergraphMergePlan,
    str,
    str,
    list[GraphMergeReconciliationDiagnostic],
]:
    validate_authoring_campaign_scope(request.campaign_id, request.campaign_rel)

    root = (repo_root_override or repo_root()).resolve()
    if union_store_path is None:
        union_store_path = resolve_repo_path(root, request.preview_union_store_path)

    store = _resolve_store(corpus_root)
    if overlay_path is None:
        overlay_path = store.overlay_path(request.campaign_id, campaign_rel=request.campaign_rel)
    overlay = store.load_overlay(request.campaign_id, campaign_rel=request.campaign_rel)
    union_store = load_union_supergraph_store(union_store_path)

    overlay_token = overlay_file_token(overlay_path, campaign_id=request.campaign_id)
    union_store_token = union_store_file_token(union_store_path, campaign_id=request.campaign_id)

    provisional_pass_id = getattr(request, "materialization_pass_id", None) or "provisional"
    plan = plan_authored_merge_reconciliation(
        campaign_id=request.campaign_id,
        overlay=overlay,
        union_store=union_store,
        materialization_pass_id=provisional_pass_id,
    )
    plan_digest = merge_plan_digest(plan)
    materialization_pass_id = derive_materialization_pass_id(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        plan_digest=plan_digest,
        requested=getattr(request, "materialization_pass_id", None),
    )
    if materialization_pass_id != provisional_pass_id:
        plan = plan_authored_merge_reconciliation(
            campaign_id=request.campaign_id,
            overlay=overlay,
            union_store=union_store,
            materialization_pass_id=materialization_pass_id,
        )
        plan_digest = merge_plan_digest(plan)

    diagnostics = [_to_api_diagnostic(item) for item in plan.diagnostics]
    return (
        store,
        overlay_path,
        union_store_path,
        overlay_token,
        union_store_token,
        union_store,
        plan,
        plan_digest,
        materialization_pass_id,
        diagnostics,
    )


def prepare_graph_merge_reconciliation_materialization(
    request: GraphMergeReconciliationPrepareRequest,
    *,
    corpus_root: Path | None = None,
    repo_root_override: Path | None = None,
) -> GraphMergeReconciliationPrepareResponse:
    (
        _store,
        overlay_path,
        union_store_path,
        overlay_token,
        union_store_token,
        union_store,
        plan,
        _plan_digest,
        materialization_pass_id,
        diagnostics,
    ) = _plan_materialization(
        request,
        corpus_root=corpus_root,
        repo_root_override=repo_root_override,
    )

    merge_assertion_count = _count_merge_assertions(
        _store.load_overlay(request.campaign_id, campaign_rel=request.campaign_rel)
    )
    actionable_plan = actionable_merge_plan(plan, union_store)
    plan_digest = merge_plan_digest(actionable_plan)
    summary = _plan_summary(plan, merge_assertion_count, union_store)
    if summary.already_materialized_assertion_count:
        diagnostics.append(
            GraphMergeReconciliationDiagnostic(
                code="merge_assertion_already_materialized",
                message=(
                    f"{summary.already_materialized_assertion_count} committed identity merge(s) "
                    "are already durable in the union store."
                ),
                severity="info",
            )
        )
    confirm_token = build_merge_reconciliation_confirm_token(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        overlay_path=str(overlay_path),
        overlay_token=overlay_token,
        union_store_path=str(union_store_path),
        union_store_token=union_store_token,
        materialization_pass_id=materialization_pass_id,
        plan_digest=plan_digest,
    )

    return GraphMergeReconciliationPrepareResponse(
        prepared=True,
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        overlay_path=str(overlay_path),
        union_store_path=str(union_store_path),
        materialization_pass_id=materialization_pass_id,
        overlay_token=overlay_token,
        union_store_token=union_store_token,
        plan_digest=plan_digest,
        confirm_token=confirm_token,
        summary=summary,
        diagnostics=diagnostics,
        no_mutation_guarantees=_no_mutation_guarantees(),
    )


def apply_graph_merge_reconciliation_materialization(
    request: GraphMergeReconciliationApplyRequest,
    *,
    corpus_root: Path | None = None,
    repo_root_override: Path | None = None,
) -> GraphMergeReconciliationApplyResponse:
    store, overlay_path, union_store_path, overlay_token, union_store_token = _resolve_materialization_paths(
        request,
        corpus_root=corpus_root,
        repo_root_override=repo_root_override,
    )

    if overlay_token != request.overlay_token:
        raise GraphMergeReconciliationMaterializeError(
            "The authored graph overlay changed since this preview was prepared. Prepare again before applying.",
            code="stale_overlay",
            status_code=409,
        )
    if union_store_token != request.union_store_token:
        raise GraphMergeReconciliationMaterializeError(
            "The union graph store changed since this preview was prepared. Prepare again before applying.",
            code="stale_union_store",
            status_code=409,
        )

    (
        _store,
        overlay_path,
        union_store_path,
        overlay_token,
        union_store_token,
        union_store,
        plan,
        _plan_digest,
        materialization_pass_id,
        diagnostics,
    ) = _plan_materialization(
        request,
        corpus_root=corpus_root,
        repo_root_override=repo_root_override,
        overlay_path=overlay_path,
        union_store_path=union_store_path,
    )

    actionable_plan = actionable_merge_plan(plan, union_store)
    plan_digest = merge_plan_digest(actionable_plan)

    if materialization_pass_id != request.materialization_pass_id:
        raise GraphMergeReconciliationMaterializeError(
            "Materialization pass id no longer matches the prepared preview. Prepare again before applying.",
            code="stale_materialization_pass",
            status_code=409,
        )

    expected_confirm = build_merge_reconciliation_confirm_token(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        overlay_path=str(overlay_path),
        overlay_token=overlay_token,
        union_store_path=str(union_store_path),
        union_store_token=union_store_token,
        materialization_pass_id=materialization_pass_id,
        plan_digest=plan_digest,
    )
    if expected_confirm != request.confirm_token:
        raise GraphMergeReconciliationMaterializeError(
            "Confirm token does not match the prepared preview. Prepare again before applying.",
            code="confirm_token_mismatch",
            status_code=409,
        )

    if not actionable_plan.plans:
        raise GraphMergeReconciliationMaterializeError(
            "No committed identity merges need materialization for the current overlay and union store.",
            code="no_applicable_plans",
        )

    applied_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    backup_dir = union_store_path.parent / "backups"
    apply_result = apply_union_supergraph_merge_plan_to_file(
        union_store_path=union_store_path,
        plan=plan,
        applied_at=applied_at,
        backup_dir=backup_dir,
    )
    diagnostics.extend(_to_api_diagnostic(item) for item in apply_result.diagnostics)

    return GraphMergeReconciliationApplyResponse(
        applied=True,
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        overlay_path=str(overlay_path),
        union_store_path=str(union_store_path),
        backup_path=apply_result.backup_path,
        materialization_pass_id=materialization_pass_id,
        applied_assertion_ids=list(apply_result.applied_assertion_ids),
        skipped_assertion_ids=list(apply_result.skipped_assertion_ids),
        summary=_apply_summary(apply_result),
        diagnostics=diagnostics,
        no_mutation_guarantees=_no_mutation_guarantees(),
    )
