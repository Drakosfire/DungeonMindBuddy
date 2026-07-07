"""Commit prepared authored graph overlay writes."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from apps.live_control_server.services.graph_authoring_event_log import (
    GraphAuthoringEventLogError,
    append_graph_authoring_events,
    build_graph_authoring_events,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    GraphAuthoringOverlayStore,
    GraphAuthoringOverlayStoreError,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphAuthoringDiagnostic,
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringCommitResponse,
    GraphObjectAuthoringError,
    authoring_prepare_request_from_write,
    _blocking_assertion_diagnostics,
    build_assertions_from_proposals,
    build_confirm_token,
    commit_no_mutation_guarantees,
    overlay_file_token,
    stable_json_digest,
    validate_authoring_campaign_scope,
)


def _resolve_store(corpus_root: Path | None) -> GraphAuthoringOverlayStore:
    if corpus_root is None:
        from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

        return GraphAuthoringOverlayStore(default_corpus_root())
    return GraphAuthoringOverlayStore(corpus_root)


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


def commit_graph_object_authoring_write(
    request: GraphObjectAuthoringCommitRequest,
    *,
    corpus_root: Path | None = None,
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
    assertions, assertion_diagnostics = build_assertions_from_proposals(prepare_request)
    blocking = _blocking_assertion_diagnostics(assertion_diagnostics)
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
    )

    try:
        append_graph_authoring_events(events_path, events)
    except GraphAuthoringEventLogError as exc:
        # Overlay was written but event log append failed. Not transactional in A5.
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
            ),
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
        ),
    )
