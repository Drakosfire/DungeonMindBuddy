"""SBW09a: begin/resume, reconcile-stale, read, and cancel orchestration."""
from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.threat_draft import ThreatDraftV1
from apps.live_control_server.models.threat_statblock_publication import (
    BeginThreatStatblockPublicationRequestV1,
    CancelThreatStatblockPublicationRequestV1,
    PublicationResultLabel,
    ReconcileThreatStatblockPublicationRequestV1,
    ThreatPublicationSourceSnapshotV1,
    ThreatStatblockPublicationDiagnosticV1,
    ThreatStatblockPublicationErrorV1,
    ThreatStatblockPublicationOperationResponseV1,
    ThreatStatblockPublicationOperationV1,
    claim_request_digest_for_begin,
    validate_publication_operation_id,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    get_threat_draft,
)
from apps.live_control_server.services.threat_statblock_publication_store import (
    ThreatStatblockPublicationStoreError,
    build_new_publication_operation,
    cas_transition_publication_cancelled,
    cas_transition_publication_stale,
    claim_publication_operation,
    get_publication_operation,
)
from apps.live_control_server.models.threat_draft import require_draft_id


class ThreatStatblockPublicationError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[ThreatStatblockPublicationDiagnosticV1] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = diagnostics or [
            ThreatStatblockPublicationDiagnosticV1(code=code, message=message)
        ]

    def response(self) -> ThreatStatblockPublicationErrorV1:
        return ThreatStatblockPublicationErrorV1(
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            diagnostics=self.diagnostics,
        )


def _validate_route_draft_id(draft_id: str) -> str:
    try:
        return require_draft_id(draft_id)
    except ValueError as exc:
        raise ThreatStatblockPublicationError(
            str(exc),
            code="invalid_request",
            status_code=422,
        ) from exc


def _validate_route_operation_id(operation_id: str) -> str:
    try:
        return validate_publication_operation_id(operation_id)
    except ValueError as exc:
        raise ThreatStatblockPublicationError(
            str(exc),
            code="invalid_request",
            status_code=422,
        ) from exc


def map_store_error(exc: ThreatStatblockPublicationStoreError) -> ThreatStatblockPublicationError:
    message = str(exc)
    if exc.status_code == 422:
        return ThreatStatblockPublicationError(
            message,
            code="invalid_request",
            status_code=422,
        )
    if exc.status_code == 404:
        return ThreatStatblockPublicationError(
            "Publication operation not found.",
            code="operation_not_found",
            status_code=404,
        )
    if exc.status_code == 409:
        lowered = message.lower()
        if "version mismatch" in lowered:
            return ThreatStatblockPublicationError(
                "Publication operation version mismatch.",
                code="operation_version_mismatch",
                status_code=409,
            )
        if "not cancellable" in lowered:
            return ThreatStatblockPublicationError(
                "Publication operation cannot be cancelled after graph side effects.",
                code="publication_not_cancellable",
                status_code=409,
            )
        if "not stale-transitionable" in lowered:
            return ThreatStatblockPublicationError(
                "Publication operation state is not supported in this slice.",
                code="unsupported_publication_state",
                status_code=409,
            )
        return ThreatStatblockPublicationError(
            message,
            code="operation_input_conflict",
            status_code=409,
        )
    if exc.status_code == 500 and "corrupt" in message.lower():
        return ThreatStatblockPublicationError(
            message,
            code="corrupt_publication_operation",
            status_code=500,
        )
    return ThreatStatblockPublicationError(
        message,
        code="publication_storage_unavailable",
        status_code=500,
    )


def _result_label_for_state(state: str) -> PublicationResultLabel:
    if state == "cancelled":
        return "publication_cancelled"
    if state == "stale":
        return "publication_stale"
    return "publication_resumed"


def _read_graph_head(
    graph_root: Path,
    world_id: str,
) -> str:
    try:
        head = kernel.open_world_graph_head(graph_root, world_id)
    except WorldGraphNotFoundError as exc:
        raise ThreatStatblockPublicationError(
            "The World Graph is not initialized.",
            code="world_not_initialized",
            status_code=409,
        ) from exc
    except (OSError, ValueError) as exc:
        raise ThreatStatblockPublicationError(
            "The World Graph could not be read.",
            code="world_graph_unreadable",
            status_code=500,
        ) from exc
    return head.head_revision_id


def _source_snapshot_from_draft(draft: ThreatDraftV1) -> ThreatPublicationSourceSnapshotV1:
    if draft.workflow_state != "mechanics_saved" or draft.accepted_mechanics_ref is None:
        raise ThreatStatblockPublicationError(
            "ThreatDraft mechanics are not saved.",
            code="mechanics_not_saved",
            status_code=409,
        )
    return ThreatPublicationSourceSnapshotV1(
        source_draft_id=draft.draft_id,
        source_draft_version=draft.version,
        world_id=draft.world_id,
        campaign_id=draft.campaign_id,
        name=draft.name,
        description=draft.description,
        threat_kind=draft.threat_kind,
        intended_roles=list(draft.intended_roles),
        tags=list(draft.tags),
        graph_context_snapshot=draft.graph_context_snapshot,
        accepted_mechanics_ref=draft.accepted_mechanics_ref,
    )


def _maybe_mark_stale_on_head_drift(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    operation,
    current_head: str,
) -> tuple[object, PublicationResultLabel]:
    if (
        operation.authority_state == "awaiting_identity_resolution"
        and current_head != operation.expected_parent_revision_id
    ):
        try:
            updated = cas_transition_publication_stale(
                root,
                draft_id=draft_id,
                operation_id=operation_id,
                expected_operation_version=operation.operation_version,
                last_observed_head_revision_id=current_head,
            )
        except ThreatStatblockPublicationStoreError as exc:
            raise map_store_error(exc) from exc
        return updated, "publication_stale"
    return operation, _result_label_for_state(operation.authority_state)


def _response(
    operation,
    *,
    result_label: PublicationResultLabel,
    warnings: list[str] | None = None,
) -> ThreatStatblockPublicationOperationResponseV1:
    return ThreatStatblockPublicationOperationResponseV1(
        result_label=result_label,
        operation=operation,
        warnings=warnings or [],
    )


def begin_or_resume_publication_operation(
    root: Path,
    *,
    draft_id: str,
    request: BeginThreatStatblockPublicationRequestV1,
    graph_root: Path | None = None,
) -> ThreatStatblockPublicationOperationResponseV1:
    safe_draft = _validate_route_draft_id(draft_id)
    graph_root = graph_root or world_graph_root()
    claim_digest = claim_request_digest_for_begin(
        draft_id=safe_draft,
        operation_id=request.operation_id,
        expected_draft_version=request.expected_draft_version,
        expected_parent_revision_id=request.expected_parent_revision_id,
    )

    try:
        existing = get_publication_operation(
            root, draft_id=safe_draft, operation_id=request.operation_id
        )
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc
    if existing is not None:
        if existing.claim_request_digest != claim_digest:
            raise ThreatStatblockPublicationError(
                "Publication operation input conflict.",
                code="operation_input_conflict",
                status_code=409,
            )
        current_head = _read_graph_head(graph_root, existing.world_id)
        operation, label = _maybe_mark_stale_on_head_drift(
            root,
            draft_id=safe_draft,
            operation_id=request.operation_id,
            operation=existing,
            current_head=current_head,
        )
        if label == "publication_stale":
            return _response(operation, result_label=label)
        return _response(operation, result_label="publication_resumed")

    def _build_new_record() -> ThreatStatblockPublicationOperationV1:
        try:
            draft = get_threat_draft(root, safe_draft)
        except ThreatDraftStoreError as exc:
            if exc.status_code == 404:
                raise ThreatStatblockPublicationError(
                    "ThreatDraft not found.",
                    code="draft_not_found",
                    status_code=404,
                ) from exc
            raise ThreatStatblockPublicationError(
                str(exc),
                code="publication_storage_unavailable",
                status_code=exc.status_code,
            ) from exc

        if draft.version != request.expected_draft_version:
            raise ThreatStatblockPublicationError(
                "ThreatDraft version mismatch.",
                code="draft_version_mismatch",
                status_code=409,
            )

        snapshot = _source_snapshot_from_draft(draft)
        current_head = _read_graph_head(graph_root, draft.world_id)
        if current_head != request.expected_parent_revision_id:
            raise ThreatStatblockPublicationError(
                "Expected parent revision is not the current World Graph head.",
                code="stale_parent_revision",
                status_code=409,
            )

        return build_new_publication_operation(
            operation_id=request.operation_id,
            claim_request_digest=claim_digest,
            source_snapshot=snapshot,
            expected_parent_revision_id=request.expected_parent_revision_id,
            last_observed_head_revision_id=current_head,
        )

    try:
        outcome, written = claim_publication_operation(
            root,
            draft_id=safe_draft,
            operation_id=request.operation_id,
            claim_request_digest=claim_digest,
            build_new_record=_build_new_record,
        )
    except ThreatStatblockPublicationError:
        raise
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc
    if outcome == "input_conflict":
        assert written is not None
        raise ThreatStatblockPublicationError(
            "Publication operation input conflict.",
            code="operation_input_conflict",
            status_code=409,
        )
    if outcome == "resume":
        assert written is not None
        current_head = _read_graph_head(graph_root, written.world_id)
        operation, label = _maybe_mark_stale_on_head_drift(
            root,
            draft_id=safe_draft,
            operation_id=request.operation_id,
            operation=written,
            current_head=current_head,
        )
        return _response(
            operation,
            result_label=label if label == "publication_stale" else "publication_resumed",
        )
    if outcome == "publication_busy":
        raise ThreatStatblockPublicationError(
            "Another active publication operation exists for this draft.",
            code="publication_busy",
            status_code=409,
        )
    if outcome == "publication_history_full":
        raise ThreatStatblockPublicationError(
            "Publication operation history is full for this draft.",
            code="publication_history_full",
            status_code=409,
        )
    assert outcome == "claimed" and written is not None
    return _response(written, result_label="publication_claimed")


def read_publication_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
) -> ThreatStatblockPublicationOperationResponseV1:
    safe_draft = _validate_route_draft_id(draft_id)
    safe_operation_id = _validate_route_operation_id(operation_id)
    try:
        operation = get_publication_operation(
            root, draft_id=safe_draft, operation_id=safe_operation_id
        )
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc
    if operation is None:
        raise ThreatStatblockPublicationError(
            "Publication operation not found.",
            code="operation_not_found",
            status_code=404,
        )
    return _response(operation, result_label=_result_label_for_state(operation.authority_state))


def reconcile_publication_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    request: ReconcileThreatStatblockPublicationRequestV1,
    graph_root: Path | None = None,
) -> ThreatStatblockPublicationOperationResponseV1:
    safe_draft = _validate_route_draft_id(draft_id)
    safe_operation_id = _validate_route_operation_id(operation_id)
    graph_root = graph_root or world_graph_root()
    try:
        operation = get_publication_operation(
            root, draft_id=safe_draft, operation_id=safe_operation_id
        )
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc
    if operation is None:
        raise ThreatStatblockPublicationError(
            "Publication operation not found.",
            code="operation_not_found",
            status_code=404,
        )

    reserved_active = {
        "identity_resolved",
        "prepared",
        "confirming",
        "committed_unverified",
        "verified",
        "failed",
    }
    if operation.authority_state in reserved_active:
        raise ThreatStatblockPublicationError(
            "Publication operation state is not supported in this slice.",
            code="unsupported_publication_state",
            status_code=409,
        )

    if operation.authority_state == "cancelled":
        return _response(operation, result_label="publication_cancelled")
    if operation.authority_state == "stale":
        return _response(operation, result_label="publication_stale")

    if operation.operation_version != request.expected_operation_version:
        raise ThreatStatblockPublicationError(
            "Publication operation version mismatch.",
            code="operation_version_mismatch",
            status_code=409,
        )

    current_head = _read_graph_head(graph_root, operation.world_id)
    if (
        operation.authority_state == "awaiting_identity_resolution"
        and current_head != operation.expected_parent_revision_id
    ):
        try:
            updated = cas_transition_publication_stale(
                root,
                draft_id=safe_draft,
                operation_id=safe_operation_id,
                expected_operation_version=request.expected_operation_version,
                last_observed_head_revision_id=current_head,
            )
        except ThreatStatblockPublicationStoreError as exc:
            raise map_store_error(exc) from exc
        return _response(updated, result_label="publication_stale")

    return _response(operation, result_label="publication_resumed")


def cancel_publication_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    request: CancelThreatStatblockPublicationRequestV1,
) -> ThreatStatblockPublicationOperationResponseV1:
    safe_draft = _validate_route_draft_id(draft_id)
    safe_operation_id = _validate_route_operation_id(operation_id)
    try:
        existing = get_publication_operation(
            root, draft_id=safe_draft, operation_id=safe_operation_id
        )
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc
    if existing is None:
        raise ThreatStatblockPublicationError(
            "Publication operation not found.",
            code="operation_not_found",
            status_code=404,
        )

    if existing.authority_state == "cancelled":
        return _response(existing, result_label="publication_cancelled")
    if existing.authority_state == "stale":
        return _response(existing, result_label="publication_stale")

    post_commit_states = {
        "identity_resolved",
        "prepared",
        "confirming",
        "committed_unverified",
        "verified",
    }
    if existing.authority_state in post_commit_states:
        raise ThreatStatblockPublicationError(
            "Publication operation cannot be cancelled after graph side effects.",
            code="publication_not_cancellable",
            status_code=409,
        )

    try:
        updated = cas_transition_publication_cancelled(
            root,
            draft_id=safe_draft,
            operation_id=safe_operation_id,
            expected_operation_version=request.expected_operation_version,
        )
    except ThreatStatblockPublicationStoreError as exc:
        raise map_store_error(exc) from exc

    label = _result_label_for_state(updated.authority_state)
    return _response(updated, result_label=label)


def publication_repo_root() -> Path:
    return repo_root()
