"""Commit prepared authored graph overlay writes."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_authoring_event_log import (
    GraphAuthoringEventLogError,
    append_graph_authoring_events,
    build_graph_authoring_events,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
    GraphAuthoringOverlayStoreError,
)
from apps.live_control_server.services.graph_merge_reconciliation_materialize import (
    actionable_merge_plan,
    derive_materialization_pass_id,
    merge_plan_digest,
    resolve_repo_path,
)
from apps.live_control_server.services.graph_object_authoring_merge_guard import (
    detect_merge_assertion_conflicts,
    find_superseded_merge_assertion_pairs,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    authored_object_node_id,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphAuthoringDiagnostic,
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringCommitResponse,
    GraphObjectAuthoringError,
    GraphObjectAuthoringUnionStoreMaterializationSummary,
    authoring_prepare_request_from_write,
    _blocking_assertion_diagnostics,
    build_assertions_from_proposals,
    build_confirm_token,
    commit_no_mutation_guarantees,
    overlay_file_token,
    stable_json_digest,
    validate_authoring_campaign_scope,
)
from graph_memory.union_supergraph.load import load_union_supergraph_store
from graph_memory.union_supergraph.merge_reconciliation import (
    plan_authored_merge_reconciliation,
)
from graph_memory.union_supergraph.merge_reconciliation_apply import (
    apply_union_supergraph_merge_plan_to_file,
)


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


def _created_node_ids_for_assertions(
    assertions: list,
    local_proposal_id_by_assertion_id: dict[str, str],
) -> dict[str, str]:
    created: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "object":
            continue
        local_proposal_id = local_proposal_id_by_assertion_id.get(assertion.assertion_id)
        if not local_proposal_id:
            continue
        created[local_proposal_id] = authored_object_node_id(assertion.assertion_id)
    return created


def _backup_overlay(
    store: GraphAuthoringOverlayStore,
    *,
    campaign_id: str,
    campaign_rel: str | None,
    overlay_token: str,
) -> Path | None:
    overlay_path = store.overlay_path(campaign_id, campaign_rel=campaign_rel)
    if not overlay_path.is_file():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"authored_graph_overlay.{stamp}.{overlay_token[:12]}.json"
    backup_path = store.backups_dir(campaign_id, campaign_rel=campaign_rel) / backup_name
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(overlay_path, backup_path)
    return backup_path


def _materialize_union_store_merges(
    request: GraphObjectAuthoringCommitRequest,
    *,
    store: GraphAuthoringOverlayStore,
    repo_root_override: Path | None = None,
) -> GraphObjectAuthoringUnionStoreMaterializationSummary:
    if not request.preview_union_store_path:
        return GraphObjectAuthoringUnionStoreMaterializationSummary(
            attempted=False,
            applied=False,
            reason="no_preview_union_store_selected",
        )

    root = (repo_root_override or repo_root()).resolve()
    try:
        union_store_path = resolve_repo_path(root, request.preview_union_store_path)
        overlay = store.load_overlay(request.campaign_id, campaign_rel=request.campaign_rel)
        union_store = load_union_supergraph_store(union_store_path)

        provisional_pass_id = "commit-materialize-provisional"
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
            requested=None,
        )
        if materialization_pass_id != provisional_pass_id:
            plan = plan_authored_merge_reconciliation(
                campaign_id=request.campaign_id,
                overlay=overlay,
                union_store=union_store,
                materialization_pass_id=materialization_pass_id,
            )

        actionable_plan = actionable_merge_plan(plan, union_store)
        if not actionable_plan.plans:
            return GraphObjectAuthoringUnionStoreMaterializationSummary(
                attempted=True,
                applied=False,
                reason="no_actionable_merge_assertions",
                union_store_path=str(union_store_path),
            )

        applied_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        backup_dir = union_store_path.parent / "backups"
        apply_result = apply_union_supergraph_merge_plan_to_file(
            union_store_path=union_store_path,
            plan=actionable_plan,
            applied_at=applied_at,
            backup_dir=backup_dir,
        )
        diagnostics = [
            GraphAuthoringDiagnostic(
                code=item.code,
                message=item.message,
                severity=item.severity,
            )
            for item in apply_result.diagnostics
        ]
        return GraphObjectAuthoringUnionStoreMaterializationSummary(
            attempted=True,
            applied=True,
            reason="materialized",
            union_store_path=str(union_store_path),
            backup_path=apply_result.backup_path,
            applied_assertion_ids=list(apply_result.applied_assertion_ids),
            redirects_added=apply_result.redirects_added,
            edges_rewired=apply_result.edges_rewired,
            survivor_nodes_updated=apply_result.survivor_nodes_updated,
            diagnostics=diagnostics,
        )
    except Exception as exc:
        return GraphObjectAuthoringUnionStoreMaterializationSummary(
            attempted=True,
            applied=False,
            reason="materialization_failed",
            union_store_path=request.preview_union_store_path,
            diagnostics=[
                GraphAuthoringDiagnostic(
                    code="union_store_materialization_failed",
                    message=str(exc),
                    severity="error",
                )
            ],
        )


def commit_graph_object_authoring_write(
    request: GraphObjectAuthoringCommitRequest,
    *,
    corpus_root: Path | None = None,
    repo_root_override: Path | None = None,
) -> GraphObjectAuthoringCommitResponse:
    if not request.proposals:
        raise GraphObjectAuthoringError(
            "At least one staged proposal is required to commit.",
            code="empty_proposals",
        )

    validate_authoring_campaign_scope(request.campaign_id, request.campaign_rel)

    try:
        store = _resolve_store(corpus_root)
        overlay_path = store.overlay_path(request.campaign_id, campaign_rel=request.campaign_rel)
        events_path = store.events_path(request.campaign_id, campaign_rel=request.campaign_rel)
    except GraphAuthoringOverlayStoreError as exc:
        raise GraphObjectAuthoringError(str(exc), code="invalid_campaign_scope") from exc
    current_token = overlay_file_token(overlay_path, campaign_id=request.campaign_id)

    if current_token != request.current_overlay_token:
        raise GraphObjectAuthoringError(
            "The authored graph changed since this preview was prepared. Prepare again before committing.",
            code="stale_overlay",
            status_code=409,
        )

    prepare_request = authoring_prepare_request_from_write(request)
    existing_overlay = store.load_overlay(request.campaign_id, campaign_rel=request.campaign_rel)
    assertions, assertion_diagnostics = build_assertions_from_proposals(prepare_request)
    local_proposal_ids = {
        assertion.assertion_id: proposal.local_proposal_id
        for assertion, proposal in zip(assertions, request.proposals, strict=False)
    }
    merge_conflicts = detect_merge_assertion_conflicts(
        assertions,
        existing_assertions=existing_overlay.assertions,
        local_proposal_id_by_assertion_id=local_proposal_ids,
    )
    blocking = _blocking_assertion_diagnostics([*assertion_diagnostics, *merge_conflicts])
    if blocking:
        raise GraphObjectAuthoringError(blocking[0].message, code=blocking[0].code)

    expected_confirm = build_confirm_token(
        campaign_id=request.campaign_id,
        overlay_path=str(overlay_path),
        current_overlay_token=current_token,
        assertions=assertions,
    )
    if expected_confirm != request.confirm_token:
        raise GraphObjectAuthoringError(
            "Confirm token does not match the prepared preview. Prepare again before committing.",
            code="confirm_token_mismatch",
            status_code=409,
        )

    token_before = current_token
    backup_path = _backup_overlay(
        store,
        campaign_id=request.campaign_id,
        campaign_rel=request.campaign_rel,
        overlay_token=token_before,
    )

    try:
        supersession_pairs = find_superseded_merge_assertion_pairs(
            assertions,
            existing_assertions=existing_overlay.assertions,
        )
        if supersession_pairs:
            store.supersede_assertions(
                request.campaign_id,
                {superseded_assertion_id for superseded_assertion_id, _ in supersession_pairs},
                campaign_rel=request.campaign_rel,
            )
        store.append_assertions(
            request.campaign_id,
            assertions,
            campaign_rel=request.campaign_rel,
        )
    except Exception as exc:
        raise GraphObjectAuthoringError(
            f"Failed to write authored graph overlay: {exc}",
            code="overlay_write_failed",
        ) from exc

    token_after = overlay_file_token(overlay_path, campaign_id=request.campaign_id)
    batch_event_id = stable_json_digest(
        {
            "batch": request.confirm_token,
            "assertion_ids": [assertion.assertion_id for assertion in assertions],
        }
    )[:24]
    events = build_graph_authoring_events(
        campaign_id=request.campaign_id,
        session_id=request.session_id,
        overlay_path=str(overlay_path),
        overlay_token_before=token_before,
        overlay_token_after=token_after,
        assertions=assertions,
        local_proposal_ids=[proposal.local_proposal_id for proposal in request.proposals],
        source_run_id=prepare_request.source_run_id,
        source_graph_id=prepare_request.source_graph_id,
        source_projection_id=prepare_request.source_projection_id,
        batch_event_id=f"evt-{batch_event_id}",
        supersessions=supersession_pairs,
    )

    try:
        append_graph_authoring_events(events_path, events)
    except GraphAuthoringEventLogError as exc:
        return GraphObjectAuthoringCommitResponse(
            committed=False,
            campaign_id=request.campaign_id,
            overlay_path=str(overlay_path),
            event_log_path=str(events_path),
            backup_path=str(backup_path) if backup_path else None,
            assertion_count=len(assertions),
            event_count=0,
            new_overlay_token=token_after,
            diagnostics=[
                GraphAuthoringDiagnostic(
                    code="event_log_write_failed",
                    message=str(exc),
                    severity="error",
                )
            ],
            no_mutation_guarantees=commit_no_mutation_guarantees(
                overlay_written=True,
                event_log_written=False,
                union_store_materialized=False,
            ),
            union_store_materialization=GraphObjectAuthoringUnionStoreMaterializationSummary(
                attempted=False,
                applied=False,
                reason="event_log_failed",
            ),
            created_node_ids={},
        )

    materialization = _materialize_union_store_merges(
        request,
        store=store,
        repo_root_override=repo_root_override,
    )

    return GraphObjectAuthoringCommitResponse(
        committed=True,
        campaign_id=request.campaign_id,
        overlay_path=str(overlay_path),
        event_log_path=str(events_path),
        backup_path=str(backup_path) if backup_path else None,
        assertion_count=len(assertions),
        event_count=len(events),
        new_overlay_token=token_after,
        diagnostics=[],
        no_mutation_guarantees=commit_no_mutation_guarantees(
            overlay_written=True,
            event_log_written=True,
            union_store_materialized=materialization.applied,
        ),
        union_store_materialization=materialization,
        created_node_ids=_created_node_ids_for_assertions(assertions, local_proposal_ids),
    )
