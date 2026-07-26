"""SBW06a: exact edited source_definition revise orchestration (no ThreatDraft attach)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
    build_statblock_v1_client,
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
from apps.live_control_server.services.statblock_candidate_cache import (
    CandidateCacheError,
    read_candidate_payload_or_none,
    store_candidate_payload,
)
from apps.live_control_server.services.statblock_revise_reconciliation import (
    claim_revise_operation,
    get_revise_operation,
    mark_cache_failed,
    mark_cache_stored_ref_pending,
    record_candidate_received,
    write_ahead_dispatched_unknown,
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
        "revise_busy",
        "revise_history_full",
        "revise_input_conflict",
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
    store_candidate_payload(root, candidate)
    return mark_cache_stored_ref_pending(
        root,
        draft_id=operation.draft_id,
        request_id=operation.request_id,
        request_digest=operation.request_digest,
        candidate_id=candidate.candidate_id,
    )


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
    if operation.status == "cache_stored_ref_pending":
        return _response_from_operation(operation, result="cache_stored_ref_pending")

    operation = _ensure_write_ahead(root, operation)

    candidate: GeneratedStatblockCandidateV1 | None = None
    if operation.candidate_id is not None:
        cached = read_candidate_payload_or_none(root, operation.candidate_id)
        if cached is not None:
            candidate = cached
        else:
            candidate = resolve_client().get_candidate(operation.candidate_id)
    elif operation.status == "dispatched_unknown":
        try:
            candidate = _dispatch_revise_post(
                resolve_client(), operation.request_body
            )
        except StatblockIntegrationError:
            refreshed = get_revise_operation(
                root,
                draft_id=draft_id,
                request_id=operation.request_id,
            )
            if refreshed is not None:
                return _response_from_operation(
                    refreshed, result="dispatched_unknown"
                )
            raise
        operation = record_candidate_received(
            root,
            draft_id=operation.draft_id,
            request_id=operation.request_id,
            request_digest=operation.request_digest,
            candidate_id=candidate.candidate_id,
        )

    if candidate is not None:
        try:
            operation = _materialize_through_cache(root, operation, candidate)
        except CandidateCacheError:
            failed = mark_cache_failed(
                root,
                draft_id=operation.draft_id,
                request_id=operation.request_id,
                request_digest=operation.request_digest,
                candidate_id=candidate.candidate_id,
            )
            return _response_from_operation(failed, result="candidate_received")
        return _response_from_operation(
            operation, result="cache_stored_ref_pending"
        )

    return _response_from_operation(operation, result="dispatched_unknown")


def revise_candidate_from_edited_definition(
    root: Path,
    *,
    draft_id: str,
    request: ReviseCandidateFromEditedDefinitionRequestV1,
    client: StatblockV1Client | None = None,
) -> ReviseCandidateFromEditedDefinitionResponseV1:
    """Exact edited definition revise adapter; ends at cache_stored_ref_pending.

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
