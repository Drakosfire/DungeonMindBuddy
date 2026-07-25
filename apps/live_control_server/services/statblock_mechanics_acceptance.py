"""SBW07b: validation gate, idempotent create orchestration, Phase 1/2 repair."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
    is_changed_body_idempotency_conflict,
    is_fixture_proven_terminal_non_begin,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    CreateStatblockRequestV1,
    ValidationReceiptV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    ValidationSeverity,
    ValidationStatus,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    same_mechanics_locator,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptThreatDraftMechanicsRequestV1,
    AcceptThreatDraftMechanicsResponseV1,
    AcceptedMechanicsRefV1,
    AcceptanceOperationV1,
    AcceptanceResultLabel,
    ReadAcceptanceOperationResponseV1,
    idempotency_key_for_operation,
)
from apps.live_control_server.services.statblock_acceptance_reconciliation import (
    AcceptanceReconciliationError,
    claim_acceptance_operation,
    create_request_digest_for_body,
    get_acceptance_operation,
    reconcile_acceptance_operation,
    record_draft_ref_conflicted,
    record_draft_ref_failed,
    record_server_committed,
    record_terminal_failure,
)
from apps.live_control_server.services.statblock_definition_validation import (
    ValidateDefinitionBuddyResponseV1,
    validate_definition,
)
from apps.live_control_server.services.threat_draft_store import (
    AcceptedMechanicsRefConflictError,
    ThreatDraftStoreError,
    attach_accepted_mechanics_ref,
    get_threat_draft,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _blocked(
    *,
    draft_id: str,
    operation_id: str,
    message: str,
) -> AcceptThreatDraftMechanicsResponseV1:
    return AcceptThreatDraftMechanicsResponseV1(
        draft_id=draft_id,
        operation_id=operation_id,
        result_label="acceptance_blocked",
        message=message,
    )


def _validation_receipt_eligible(receipt: ValidationReceiptV1) -> bool:
    if receipt.status == ValidationStatus.invalid:
        return False
    for issue in receipt.issues or []:
        if issue.severity == ValidationSeverity.error:
            return False
    return True


def _client_receipt_matches(receipt: ValidationReceiptV1, expected_digest: str) -> bool:
    if receipt.definition_digest != expected_digest:
        return False
    return _validation_receipt_eligible(receipt)


def _run_validation_gate(
    request: AcceptThreatDraftMechanicsRequestV1,
    *,
    client: StatblockV1Client | None,
) -> tuple[bool, str | None, ValidateDefinitionBuddyResponseV1 | None]:
    if not _client_receipt_matches(
        request.validation_receipt, request.validation_definition_digest
    ):
        return False, "client validation receipt not eligible or digest mismatch", None

    response = validate_definition(definition=request.definition, client=client)
    if response.outcome != "success":
        return False, response.failure_message or "validation failed", response
    assert response.definition_digest is not None
    assert response.validation_receipt is not None
    if response.definition_digest != request.validation_definition_digest:
        return False, "validation definition digest mismatch", response
    if response.validation_receipt.definition_digest != request.validation_definition_digest:
        return False, "validation receipt digest mismatch", response
    if not _validation_receipt_eligible(response.validation_receipt):
        return False, "validation receipt contains blocking errors", response
    return True, None, response


def _build_create_body(request: AcceptThreatDraftMechanicsRequestV1) -> dict[str, Any]:
    create = CreateStatblockRequestV1(
        idempotency_key=idempotency_key_for_operation(request.operation_id),
        definition=request.definition,
        candidate_id=request.source_candidate_id,
        change_summary=request.change_summary,
        actor=request.actor,
        accepted_through=request.accepted_through,
    )
    return json.loads(create.model_dump_json())


def _result_label_for_operation(
    op: AcceptanceOperationV1,
    *,
    draft_workflow: str | None,
    draft_ref: AcceptedMechanicsRefV1 | None,
) -> AcceptanceResultLabel:
    if op.authority_state == "terminal_failure":
        return "terminal_failure"
    product_saved = (
        draft_workflow == "mechanics_saved"
        and draft_ref is not None
        and op.locator is not None
        and same_mechanics_locator(draft_ref.to_mechanics_locator(), op.locator)
    )
    if op.authority_state == "reconciled":
        if product_saved:
            return "mechanics_saved"
        if draft_workflow is None and draft_ref is None:
            return "acceptance_draft_unavailable"
        if draft_ref is not None and op.locator is not None and not same_mechanics_locator(
            draft_ref.to_mechanics_locator(), op.locator
        ):
            return "accepted_ref_conflict"
        return "acceptance_draft_unavailable"
    if op.authority_state == "server_committed":
        if op.materialization.draft_ref == "conflicted":
            return "accepted_ref_conflict"
        if product_saved:
            return "mechanics_saved"
        if draft_workflow is None and draft_ref is None:
            return "acceptance_draft_unavailable"
        return "server_committed_reference_pending"
    return "dispatched_unknown"


def _response_from_operation(
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
    draft_workflow: str | None = None,
    draft_accepted: AcceptedMechanicsRefV1 | None = None,
    message: str | None = None,
    result_label: AcceptanceResultLabel | None = None,
) -> AcceptThreatDraftMechanicsResponseV1:
    label = result_label or _result_label_for_operation(
        op,
        draft_workflow=draft_workflow,
        draft_ref=draft_accepted,
    )
    return AcceptThreatDraftMechanicsResponseV1(
        draft_id=draft_id,
        operation_id=op.operation_id,
        result_label=label,
        authority_state=op.authority_state,
        draft_ref=op.materialization.draft_ref,
        workflow_state=draft_workflow,  # type: ignore[arg-type]
        locator=op.locator,
        terminal_code=op.terminal_code,
        failure_category=op.failure_category,
        http_status=op.http_status,
        message=message,
    )


def _dispatch_create_if_needed(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
    client: StatblockV1Client,
) -> AcceptanceOperationV1:
    if op.authority_state != "dispatched_unknown":
        return op
    body = op.request_body
    try:
        result = client.create_statblock(body)
    except StatblockIntegrationError as exc:
        if is_changed_body_idempotency_conflict(exc):
            return op
        if is_fixture_proven_terminal_non_begin(exc):
            try:
                return record_terminal_failure(
                    root,
                    draft_id=draft_id,
                    operation_id=op.operation_id,
                    create_request_digest=op.create_request_digest,
                    terminal_code=exc.error_code or "terminal",
                    failure_category=exc.category,
                    http_status=exc.status_code or 500,
                    terminal_details=dict(exc.details) if exc.details else None,
                )
            except AcceptanceReconciliationError:
                return op
        return op
    locator = result.locator
    try:
        return record_server_committed(
            root,
            draft_id=draft_id,
            operation_id=op.operation_id,
            create_request_digest=op.create_request_digest,
            locator=locator,
        )
    except AcceptanceReconciliationError:
        return op


def _build_accepted_ref(
    locator: MechanicsLocatorV1,
    *,
    accepted_from_draft_version: int,
    accepted_from_candidate_id: str | None,
    accepted_at: str,
) -> AcceptedMechanicsRefV1:
    return AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_draft_version=accepted_from_draft_version,
        accepted_from_candidate_id=accepted_from_candidate_id,
        accepted_at=accepted_at,
    )


def _phase1_attach(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
    max_cas_attempts: int = 3,
) -> AcceptanceOperationV1:
    if op.authority_state != "server_committed" or op.locator is None:
        return op
    if op.materialization.draft_ref == "conflicted":
        return op

    accepted_at = _utc_now_iso()
    ref = _build_accepted_ref(
        op.locator,
        accepted_from_draft_version=op.source_draft_version,
        accepted_from_candidate_id=op.source_candidate_id,
        accepted_at=accepted_at,
    )

    for _ in range(max_cas_attempts):
        try:
            draft = get_threat_draft(root, draft_id)
        except ThreatDraftStoreError:
            try:
                return record_draft_ref_failed(
                    root,
                    draft_id=draft_id,
                    operation_id=op.operation_id,
                    create_request_digest=op.create_request_digest,
                )
            except AcceptanceReconciliationError:
                return op
        # Always call attach: matching locator still repairs workflow_state and
        # preserves accepted_at / provenance inside attach_accepted_mechanics_ref.
        try:
            attach_accepted_mechanics_ref(
                root,
                draft_id=draft_id,
                expected_version=draft.version,
                locator=ref,
            )
            break
        except AcceptedMechanicsRefConflictError:
            try:
                return record_draft_ref_conflicted(
                    root,
                    draft_id=draft_id,
                    operation_id=op.operation_id,
                    create_request_digest=op.create_request_digest,
                )
            except AcceptanceReconciliationError:
                return op
        except ThreatDraftStoreError as exc:
            if exc.status_code == 409:
                continue
            try:
                return record_draft_ref_failed(
                    root,
                    draft_id=draft_id,
                    operation_id=op.operation_id,
                    create_request_digest=op.create_request_digest,
                )
            except AcceptanceReconciliationError:
                return op
        except OSError:
            try:
                return record_draft_ref_failed(
                    root,
                    draft_id=draft_id,
                    operation_id=op.operation_id,
                    create_request_digest=op.create_request_digest,
                )
            except AcceptanceReconciliationError:
                return op
    else:
        return op

    reloaded = get_acceptance_operation(
        root, draft_id=draft_id, operation_id=op.operation_id
    )
    return reloaded or op


def _phase2_reconcile(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
) -> AcceptanceOperationV1:
    if op.authority_state != "server_committed" or op.locator is None:
        return op
    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError:
        return op
    if draft.accepted_mechanics_ref is None:
        return op
    if not same_mechanics_locator(
        draft.accepted_mechanics_ref.to_mechanics_locator(), op.locator
    ):
        return op
    if draft.workflow_state != "mechanics_saved":
        return op
    try:
        return reconcile_acceptance_operation(
            root,
            draft_id=draft_id,
            operation_id=op.operation_id,
            create_request_digest=op.create_request_digest,
        )
    except AcceptanceReconciliationError:
        return op


def _drive_phases(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
) -> AcceptanceOperationV1:
    op = _phase1_attach(root, draft_id=draft_id, op=op)
    op = _phase2_reconcile(root, draft_id=draft_id, op=op)
    return op


def _conflict_response(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
) -> AcceptThreatDraftMechanicsResponseV1:
    draft_workflow = None
    draft_accepted = None
    try:
        draft_now = get_threat_draft(root, draft_id)
        draft_workflow = draft_now.workflow_state
        draft_accepted = draft_now.accepted_mechanics_ref
    except ThreatDraftStoreError:
        pass
    return _response_from_operation(
        draft_id=draft_id,
        op=op,
        draft_workflow=draft_workflow,
        draft_accepted=draft_accepted,
        result_label="acceptance_input_conflict",
        message="operation_id reused with different request body",
    )


def _finish_acceptance(
    root: Path,
    *,
    draft_id: str,
    op: AcceptanceOperationV1,
    client: StatblockV1Client | None,
) -> AcceptThreatDraftMechanicsResponseV1:
    if op.authority_state == "dispatched_unknown":
        owns_client = False
        active = client
        if active is None:
            active = DungeonMindStatblockV1Client()
            owns_client = True
        try:
            op = _dispatch_create_if_needed(
                root, draft_id=draft_id, op=op, client=active
            )
        finally:
            if owns_client and hasattr(active, "close"):
                active.close()

    op = _drive_phases(root, draft_id=draft_id, op=op)

    try:
        draft_after = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError:
        return _response_from_operation(
            draft_id=draft_id,
            op=op,
            draft_workflow=None,
            draft_accepted=None,
            message="threat draft unavailable; journal authority retained",
        )
    return _response_from_operation(
        draft_id=draft_id,
        op=op,
        draft_workflow=draft_after.workflow_state,
        draft_accepted=draft_after.accepted_mechanics_ref,
    )


def begin_or_resume_acceptance(
    root: Path,
    *,
    draft_id: str,
    request: AcceptThreatDraftMechanicsRequestV1,
    client: StatblockV1Client | None = None,
) -> AcceptThreatDraftMechanicsResponseV1:
    # Build the canonical create body before deciding whether validation is required.
    # Existing-operation conflict/resume must be local — zero validation / create calls.
    request_body = _build_create_body(request)
    digest = create_request_digest_for_body(request_body)

    try:
        existing = get_acceptance_operation(
            root, draft_id=draft_id, operation_id=request.operation_id
        )
    except AcceptanceReconciliationError as exc:
        return _blocked(
            draft_id=draft_id,
            operation_id=request.operation_id,
            message=str(exc),
        )

    if existing is not None:
        if (
            existing.create_request_digest != digest
            or existing.request_body != request_body
        ):
            return _conflict_response(root, draft_id=draft_id, op=existing)
        # Exact-body resume from durable authority — no outbound validation.
        outcome, op = claim_acceptance_operation(
            root,
            draft_id=draft_id,
            expected_draft_version=request.expected_draft_version,
            operation_id=request.operation_id,
            create_request_digest=digest,
            request_body=request_body,
            validation_receipt_digest=request.validation_definition_digest,
            source_candidate_id=request.source_candidate_id,
        )
        if outcome == "input_conflict":
            assert op is not None
            return _conflict_response(root, draft_id=draft_id, op=op)
        assert outcome == "resume" and op is not None
        return _finish_acceptance(root, draft_id=draft_id, op=op, client=client)

    # Genuinely new operation: authoritative validation before claim or create.
    ok, gate_message, _ = _run_validation_gate(request, client=client)
    if not ok:
        return _blocked(
            draft_id=draft_id,
            operation_id=request.operation_id,
            message=gate_message or "acceptance blocked",
        )

    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError as exc:
        return _blocked(
            draft_id=draft_id,
            operation_id=request.operation_id,
            message=str(exc),
        )

    if request.source_candidate_id is not None:
        if not any(
            ref.candidate_id == request.source_candidate_id
            for ref in draft.candidate_refs
        ):
            return _blocked(
                draft_id=draft_id,
                operation_id=request.operation_id,
                message="source_candidate_id not on draft",
            )

    outcome, op = claim_acceptance_operation(
        root,
        draft_id=draft_id,
        expected_draft_version=request.expected_draft_version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=request_body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=request.source_candidate_id,
    )

    if outcome == "acceptance_history_full":
        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_id,
            operation_id=request.operation_id,
            result_label="acceptance_history_full",
            message="acceptance history bound reached",
        )
    if outcome == "acceptance_busy":
        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_id,
            operation_id=request.operation_id,
            result_label="acceptance_busy",
            message="another acceptance operation occupies the active slot",
        )
    if outcome == "version_mismatch":
        return _blocked(
            draft_id=draft_id,
            operation_id=request.operation_id,
            message="expected draft version mismatch",
        )
    if outcome == "input_conflict":
        assert op is not None
        return _conflict_response(root, draft_id=draft_id, op=op)
    assert op is not None
    return _finish_acceptance(root, draft_id=draft_id, op=op, client=client)


def recover_acceptance_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
    client: StatblockV1Client | None = None,
) -> AcceptThreatDraftMechanicsResponseV1:
    try:
        op = get_acceptance_operation(root, draft_id=draft_id, operation_id=operation_id)
    except AcceptanceReconciliationError as exc:
        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_id,
            operation_id=operation_id,
            result_label="acceptance_blocked",
            message=str(exc),
        )
    if op is None:
        return AcceptThreatDraftMechanicsResponseV1(
            draft_id=draft_id,
            operation_id=operation_id,
            result_label="acceptance_blocked",
            message="acceptance operation not found",
        )

    return _finish_acceptance(root, draft_id=draft_id, op=op, client=client)


def read_acceptance_operation(
    root: Path,
    *,
    draft_id: str,
    operation_id: str,
) -> ReadAcceptanceOperationResponseV1:
    op = get_acceptance_operation(root, draft_id=draft_id, operation_id=operation_id)
    if op is None:
        return ReadAcceptanceOperationResponseV1(
            draft_id=draft_id,
            operation=None,
            result_label=None,
        )
    try:
        draft = get_threat_draft(root, draft_id)
        label = _result_label_for_operation(
            op,
            draft_workflow=draft.workflow_state,
            draft_ref=draft.accepted_mechanics_ref,
        )
    except ThreatDraftStoreError:
        label = _result_label_for_operation(op, draft_workflow=None, draft_ref=None)
    return ReadAcceptanceOperationResponseV1(
        draft_id=draft_id,
        operation=op,
        result_label=label,
    )
