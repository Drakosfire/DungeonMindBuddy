"""SBW06a: exact edited source_definition revise orchestration (no ThreatDraft attach)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
    build_statblock_v1_client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.create_terminal_inventory import (
    is_changed_body_idempotency_conflict,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.statblock_candidate_revision import (
    ReviseCandidateFromEditedDefinitionRequestV1,
    ReviseCandidateFromEditedDefinitionResponseV1,
    ReviseOperationV1,
    instruction_options_digest,
    map_edited_definition_to_revise_server_body,
    normalize_revision_instructions,
    revise_request_digest_for_server_body,
    source_definition_digest_from_body,
)
from apps.live_control_server.models.threat_draft import (
    CandidateLineageV1,
    EditedWorkingCopyLineageV1,
    ThreatDraftCandidateRefV1,
)
from apps.live_control_server.services.statblock_candidate_cache import (
    CandidateCacheError,
    read_candidate_payload_or_none,
    store_candidate_payload,
)
from apps.live_control_server.services.statblock_revise_reconciliation import (
    ReviseReconciliationError,
    claim_revise_operation,
    get_revise_operation,
    mark_cache_failed,
    mark_cache_stored_ref_pending,
    mark_idempotency_authority_conflict,
    mark_revise_reconciled,
    prove_revise_ref_attached,
    record_candidate_received,
    write_ahead_dispatched_unknown,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    get_threat_draft,
    reconcile_revise_candidate_ref,
)


class ReviseCandidateRevisionError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response_from_operation(
    operation: ReviseOperationV1,
    *,
    result: Literal[
        "revise_claimed",
        "dispatched_unknown",
        "candidate_received",
        "cache_stored_ref_pending",
        "reconciled",
        "revise_busy",
        "revise_history_full",
        "revise_input_conflict",
        "revise_integrity_conflict",
        "revise_blocked",
        "revise_draft_unavailable",
        "terminal_failure",
    ],
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    return ReviseCandidateFromEditedDefinitionResponseV1(
        result=result,
        request_id=operation.request_id,
        operation_status=operation.status,
        candidate_id=operation.candidate_id,
        request_digest=operation.request_digest,
        source_definition_digest=operation.source_definition_digest,
        instruction_options_digest=operation.instruction_options_digest,
    )


def _receipt_digest_str(receipt_digest: object) -> str | None:
    if receipt_digest is None:
        return None
    if hasattr(receipt_digest, "root"):
        return str(receipt_digest.root)
    return str(receipt_digest)


def _build_lineage_from_operation(operation: ReviseOperationV1) -> CandidateLineageV1:
    return CandidateLineageV1(
        revise_request_id=operation.request_id,
        source_origin_kind="edited_working_copy",
        instruction_options_digest=operation.instruction_options_digest,
        created_at=operation.created_at,
        edited_working_copy=EditedWorkingCopyLineageV1(
            draft_id=operation.draft_id,
            source_draft_version=operation.source_draft_version,
            editor_state_revision=operation.editor_state_revision,
            source_definition_digest=operation.source_definition_digest,
        ),
    )


def _build_revise_candidate_ref(
    operation: ReviseOperationV1,
    lineage: CandidateLineageV1,
) -> ThreatDraftCandidateRefV1:
    if operation.candidate_id is None:
        raise ReviseCandidateRevisionError(
            "reconcile requires candidate_id",
            status_code=500,
        )
    return ThreatDraftCandidateRefV1(
        candidate_id=operation.candidate_id,
        generated_from_draft_version=operation.source_draft_version,
        request_id=operation.request_id,
        created_at=operation.created_at,
        status="active",
        lineage=lineage,
    )


def _mark_reconciled_or_recover(
    root: Path,
    operation: ReviseOperationV1,
    *,
    lineage: CandidateLineageV1,
) -> ReviseOperationV1:
    assert operation.candidate_id is not None
    try:
        return mark_revise_reconciled(
            root,
            draft_id=operation.draft_id,
            request_id=operation.request_id,
            request_digest=operation.request_digest,
            candidate_id=operation.candidate_id,
            source_status="none",
        )
    except ReviseReconciliationError:
        draft = get_threat_draft(root, operation.draft_id)
        if prove_revise_ref_attached(
            draft,
            operation,
            expected_lineage=lineage,
            expected_source_status="none",
        ):
            return mark_revise_reconciled(
                root,
                draft_id=operation.draft_id,
                request_id=operation.request_id,
                request_digest=operation.request_digest,
                candidate_id=operation.candidate_id,
                source_status="none",
            )
        raise


def _reconcile_draft_and_journal(
    root: Path,
    operation: ReviseOperationV1,
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    if operation.status == "reconciled":
        return _response_from_operation(operation, result="reconciled")
    if operation.status != "cache_stored_ref_pending":
        return _response_from_operation(operation, result="cache_stored_ref_pending")

    lineage = _build_lineage_from_operation(operation)
    candidate_ref = _build_revise_candidate_ref(operation, lineage)
    draft = get_threat_draft(root, operation.draft_id)

    if prove_revise_ref_attached(
        draft,
        operation,
        expected_lineage=lineage,
        expected_source_status="none",
    ):
        try:
            operation = _mark_reconciled_or_recover(root, operation, lineage=lineage)
        except ReviseReconciliationError:
            return _response_from_operation(
                operation, result="cache_stored_ref_pending"
            )
        return _response_from_operation(operation, result="reconciled")

    try:
        reconcile_revise_candidate_ref(
            root,
            draft_id=operation.draft_id,
            expected_version=draft.version,
            candidate_ref=candidate_ref,
            requested_source_transition=None,
        )
    except ThreatDraftStoreError as exc:
        if exc.status_code == 409 and "identity conflict" in str(exc):
            return _response_from_operation(
                operation, result="revise_integrity_conflict"
            )
        return _response_from_operation(operation, result="cache_stored_ref_pending")

    try:
        operation = _mark_reconciled_or_recover(root, operation, lineage=lineage)
    except ReviseReconciliationError:
        return _response_from_operation(operation, result="cache_stored_ref_pending")

    return _response_from_operation(operation, result="reconciled")


def bind_candidate_to_revise_operation(
    candidate: GeneratedStatblockCandidateV1,
    operation: ReviseOperationV1,
) -> None:
    """Require candidate identity + Server receipt to match the revise journal.

    Covers POST responses, cache reads, and exact GET responses before any
    transition to ``cache_stored_ref_pending``.
    """
    if (
        operation.candidate_id is not None
        and candidate.candidate_id != operation.candidate_id
    ):
        raise ReviseCandidateRevisionError(
            "candidate.candidate_id does not match revise operation",
            status_code=409,
        )
    receipt = candidate.generation_receipt
    if receipt is None:
        raise ReviseCandidateRevisionError(
            "candidate missing generation_receipt",
            status_code=500,
        )
    if receipt.request_id != operation.request_id:
        raise ReviseCandidateRevisionError(
            "candidate generation_receipt.request_id does not match revise operation",
            status_code=409,
        )
    observed = _receipt_digest_str(receipt.source_definition_digest)
    if observed is None:
        raise ReviseCandidateRevisionError(
            "candidate generation_receipt missing source_definition_digest",
            status_code=500,
        )
    if observed != operation.source_definition_digest:
        raise ReviseCandidateRevisionError(
            "candidate generation_receipt.source_definition_digest does not match "
            "revise operation",
            status_code=409,
        )


def _ensure_write_ahead(
    root: Path,
    operation: ReviseOperationV1,
) -> ReviseOperationV1:
    if operation.status == "claimed":
        return write_ahead_dispatched_unknown(
            root,
            draft_id=operation.draft_id,
            request_id=operation.request_id,
            request_digest=operation.request_digest,
        )
    return operation


def _dispatch_revise_post(
    client: StatblockV1Client,
    body: dict,
) -> GeneratedStatblockCandidateV1:
    return client.revise_candidate(body)


def _materialize_through_cache(
    root: Path,
    operation: ReviseOperationV1,
    candidate: GeneratedStatblockCandidateV1,
) -> ReviseOperationV1:
    bind_candidate_to_revise_operation(candidate, operation)
    store_candidate_payload(root, candidate)
    return mark_cache_stored_ref_pending(
        root,
        draft_id=operation.draft_id,
        request_id=operation.request_id,
        request_digest=operation.request_digest,
        candidate_id=candidate.candidate_id,
    )


def _demote_cache_failed(
    root: Path,
    operation: ReviseOperationV1,
    *,
    candidate_id: str,
) -> ReviseOperationV1:
    return mark_cache_failed(
        root,
        draft_id=operation.draft_id,
        request_id=operation.request_id,
        request_digest=operation.request_digest,
        candidate_id=candidate_id,
    )


def _repair_or_demote_known_candidate(
    root: Path,
    *,
    operation: ReviseOperationV1,
    resolve_client: Callable[[], StatblockV1Client],
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    """Verify/repair cache for a journal that already records candidate_id.

    ``cache_stored_ref_pending`` is only returned when a bound payload is
    present in cache (or successfully repaired into cache).
    """
    assert operation.candidate_id is not None

    try:
        cached = read_candidate_payload_or_none(root, operation.candidate_id)
    except CandidateCacheError:
        cached = None

    if cached is not None:
        try:
            bind_candidate_to_revise_operation(cached, operation)
        except ReviseCandidateRevisionError:
            cached = None
        else:
            if operation.status != "cache_stored_ref_pending":
                try:
                    operation = _materialize_through_cache(root, operation, cached)
                except CandidateCacheError:
                    failed = _demote_cache_failed(
                        root, operation, candidate_id=operation.candidate_id
                    )
                    return _response_from_operation(failed, result="candidate_received")
            return _reconcile_draft_and_journal(root, operation)

    try:
        candidate = resolve_client().get_candidate(operation.candidate_id)
        bind_candidate_to_revise_operation(candidate, operation)
    except (StatblockIntegrationError, ReviseCandidateRevisionError):
        failed = _demote_cache_failed(
            root, operation, candidate_id=operation.candidate_id
        )
        return _response_from_operation(failed, result="candidate_received")

    if operation.status == "dispatched_unknown":
        operation = record_candidate_received(
            root,
            draft_id=operation.draft_id,
            request_id=operation.request_id,
            request_digest=operation.request_digest,
            candidate_id=candidate.candidate_id,
        )

    try:
        operation = _materialize_through_cache(root, operation, candidate)
    except CandidateCacheError:
        failed = _demote_cache_failed(
            root, operation, candidate_id=candidate.candidate_id
        )
        return _response_from_operation(failed, result="candidate_received")
    return _reconcile_draft_and_journal(root, operation)


def _client_factory(
    client: StatblockV1Client | None,
) -> tuple[Callable[[], StatblockV1Client], list[DungeonMindStatblockV1Client]]:
    """Lazy client construction; only builds when POST/GET is required."""
    owned: list[DungeonMindStatblockV1Client] = []

    def resolve() -> StatblockV1Client:
        if client is not None:
            return client
        built = build_statblock_v1_client()
        if isinstance(built, DungeonMindStatblockV1Client):
            owned.append(built)
        return built

    return resolve, owned


def _advance_after_claim(
    root: Path,
    *,
    draft_id: str,
    operation: ReviseOperationV1,
    resolve_client: Callable[[], StatblockV1Client],
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    if operation.status == "reconciled":
        return _response_from_operation(operation, result="reconciled")

    # Known candidate: always verify cache before claiming cache_stored_ref_pending.
    if operation.candidate_id is not None:
        return _repair_or_demote_known_candidate(
            root,
            operation=operation,
            resolve_client=resolve_client,
        )

    if (
        operation.status == "dispatched_unknown"
        and operation.recovery_classification == "idempotency_authority_conflict"
    ):
        return _response_from_operation(operation, result="revise_integrity_conflict")

    operation = _ensure_write_ahead(root, operation)

    if operation.status != "dispatched_unknown":
        return _response_from_operation(operation, result="dispatched_unknown")

    try:
        candidate = _dispatch_revise_post(resolve_client(), operation.request_body)
    except StatblockIntegrationError as exc:
        if is_changed_body_idempotency_conflict(exc):
            marked = mark_idempotency_authority_conflict(
                root,
                draft_id=operation.draft_id,
                request_id=operation.request_id,
                request_digest=operation.request_digest,
                details={
                    "server_error_code": exc.error_code,
                    "http_status": exc.status_code,
                    "message": exc.message,
                },
            )
            return _response_from_operation(
                marked, result="revise_integrity_conflict"
            )
        refreshed = get_revise_operation(
            root,
            draft_id=draft_id,
            request_id=operation.request_id,
        )
        if refreshed is not None:
            if refreshed.recovery_classification == "idempotency_authority_conflict":
                return _response_from_operation(
                    refreshed, result="revise_integrity_conflict"
                )
            return _response_from_operation(
                refreshed, result="dispatched_unknown"
            )
        raise

    bind_candidate_to_revise_operation(candidate, operation)
    operation = record_candidate_received(
        root,
        draft_id=operation.draft_id,
        request_id=operation.request_id,
        request_digest=operation.request_digest,
        candidate_id=candidate.candidate_id,
    )
    try:
        operation = _materialize_through_cache(root, operation, candidate)
    except CandidateCacheError:
        failed = _demote_cache_failed(
            root, operation, candidate_id=candidate.candidate_id
        )
        return _response_from_operation(failed, result="candidate_received")
    return _reconcile_draft_and_journal(root, operation)


def revise_candidate_from_edited_definition(
    root: Path,
    *,
    draft_id: str,
    request: ReviseCandidateFromEditedDefinitionRequestV1,
    client: StatblockV1Client | None = None,
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    """Exact edited definition revise adapter through reconciled product success.

    Existing journal authority is classified before draft/version/capacity
    checks and before Server client construction. The client is built lazily
    only when a revise POST or candidate GET is required.

    New claims read draft membership, version, and candidate refs under the
    ThreatDraft store lock through the shared capacity decision (store →
    capacity → revise journal).
    """
    resolve_client, owned_clients = _client_factory(client)

    try:
        try:
            normalized = normalize_revision_instructions(request.revision_instructions)
        except ValueError as exc:
            raise ReviseCandidateRevisionError(str(exc), status_code=422) from exc

        body = map_edited_definition_to_revise_server_body(request)
        request_digest = revise_request_digest_for_server_body(body)
        src_digest = source_definition_digest_from_body(body["source_definition"])
        instr_digest = instruction_options_digest(
            normalized, request.preserve_element_keys
        )

        # Durable journal authority before draft I/O or client construction.
        existing = get_revise_operation(
            root,
            draft_id=draft_id,
            request_id=request.request_id,
        )
        if existing is not None:
            if (
                existing.request_digest != request_digest
                or existing.request_body != body
            ):
                return _response_from_operation(
                    existing, result="revise_input_conflict"
                )
            return _advance_after_claim(
                root,
                draft_id=draft_id,
                operation=existing,
                resolve_client=resolve_client,
            )

        claim_outcome, operation = claim_revise_operation(
            root,
            draft_id=draft_id,
            expected_draft_version=request.expected_draft_version,
            request_id=request.request_id,
            request_digest=request_digest,
            request_body=body,
            editor_state_revision=request.editor_state_revision,
            source_definition_digest=src_digest,
            instruction_options_digest=instr_digest,
        )

        if claim_outcome == "version_mismatch":
            raise ReviseCandidateRevisionError(
                "expected_version mismatch",
                status_code=409,
            )
        if claim_outcome == "revise_busy":
            return ReviseCandidateFromEditedDefinitionResponseV1(
                result="revise_busy",
                request_id=request.request_id,
                operation_status=None,
                candidate_id=None,
                request_digest=request_digest,
                source_definition_digest=src_digest,
                instruction_options_digest=instr_digest,
            )
        if claim_outcome == "revise_history_full":
            return ReviseCandidateFromEditedDefinitionResponseV1(
                result="revise_history_full",
                request_id=request.request_id,
                operation_status=None,
                candidate_id=None,
                request_digest=request_digest,
                source_definition_digest=src_digest,
                instruction_options_digest=instr_digest,
            )
        if claim_outcome == "revise_input_conflict":
            assert operation is not None
            return _response_from_operation(operation, result="revise_input_conflict")

        assert operation is not None
        return _advance_after_claim(
            root,
            draft_id=draft_id,
            operation=operation,
            resolve_client=resolve_client,
        )
    finally:
        for owned in owned_clients:
            owned.close()
