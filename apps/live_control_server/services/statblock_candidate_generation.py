"""Exact ThreatDraft version → DungeonMind candidate generation orchestration."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.statblock_candidate_workflow import (
    GenerateThreatDraftCandidateRequestV1,
    GenerateThreatDraftCandidateResponseV1,
    PersistenceFailureV1,
    ReadStatblockCandidateResponseV1,
)
from apps.live_control_server.models.threat_draft import (
    ThreatDraftCandidateRefV1,
    ThreatDraftV1,
)
from apps.live_control_server.services.statblock_candidate_cache import (
    CandidateCacheError,
    read_candidate_payload_or_none,
    store_candidate_payload,
)
from apps.live_control_server.services.statblock_generation_reconciliation import (
    GenerationOperationV2,
    GenerationReconciliationError,
    GenerationTombstoneV1,
    claim_generation_request,
    finalize_generation_request,
    load_received_candidate,
    read_reconciliation,
    record_generation_received,
    record_terminal_expired,
    record_terminal_failure,
    request_digest_for_body,
    update_materialization,
    validate_request_id,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    append_candidate_ref,
    get_threat_draft,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def map_draft_to_generate_request(
    draft: ThreatDraftV1,
    *,
    request_id: str,
) -> dict[str, Any]:
    intent = draft.generation_intent
    context = draft.encounter_context
    return {
        "request_id": request_id,
        "ruleset": intent.ruleset.model_dump(mode="json"),
        "source": {
            "name_hint": draft.name,
            "description": draft.description,
        },
        "intent": {
            "target_cr": intent.target_cr,
            "roles": list(draft.intended_roles),
            "complexity": intent.complexity,
            "must_include": list(intent.must_include),
            "must_avoid": list(intent.must_avoid),
        },
        "context": {
            "party_level": context.party_level,
            "party_size": context.party_size,
            "terrain_notes": list(context.terrain_notes),
        },
        "asset_options": {
            "include_generation_brief": True,
            "generate_images": False,
        },
        "actor": draft.created_by,
    }


def _bound_request_id_from_candidate(
    candidate: GeneratedStatblockCandidateV1,
    *,
    request_id: str,
) -> str:
    """Require generation_receipt.request_id to match the local request lineage.

    Never fabricate lineage by substituting the local request_id when the receipt
    is absent or mismatched — fail closed instead.
    """
    receipt = candidate.generation_receipt
    if receipt is None or not receipt.request_id:
        raise GenerationReconciliationError(
            "candidate generation_receipt.request_id missing",
            status_code=500,
        )
    if receipt.request_id != request_id:
        raise GenerationReconciliationError(
            "candidate generation_receipt.request_id mismatch",
            status_code=409,
        )
    return receipt.request_id


def _candidate_ref_from_payload(
    candidate: GeneratedStatblockCandidateV1,
    *,
    draft_version: int,
    request_id: str,
) -> ThreatDraftCandidateRefV1:
    receipt_request_id = _bound_request_id_from_candidate(
        candidate, request_id=request_id
    )
    return ThreatDraftCandidateRefV1(
        candidate_id=candidate.candidate_id,
        generated_from_draft_version=draft_version,
        request_id=receipt_request_id,
        created_at=_iso_z(candidate.created_at),
        expires_at=_iso_z(candidate.expires_at),
        status="active",
    )


def _failure(
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    category: str,
    message: str,
) -> GenerateThreatDraftCandidateResponseV1:
    return GenerateThreatDraftCandidateResponseV1(
        draft_id=draft_id,
        generated_from_draft_version=draft_version,
        request_id=request_id,
        outcome="failure",
        failure_category=category,
        failure_message=message,
        cache_status="missing",
    )


def _map_reconciliation_error(exc: GenerationReconciliationError) -> ThreatDraftStoreError | None:
    if exc.status_code in {409, 422}:
        return ThreatDraftStoreError(str(exc), status_code=exc.status_code)
    return None


def _cache_status_from_failures(
    failures: list[PersistenceFailureV1],
) -> Literal[
    "stored",
    "partial_cache",
    "partial_ref",
    "partial_reconciliation",
    "partial_both",
]:
    if not failures:
        return "stored"
    components = {item.component for item in failures}
    if components == {"cache"}:
        return "partial_cache"
    if components == {"candidate_ref"}:
        return "partial_ref"
    if components == {"reconciliation"}:
        return "partial_reconciliation"
    return "partial_both"


def _persist_candidate_artifacts(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    candidate: GeneratedStatblockCandidateV1,
    request_id: str,
    request_digest: str,
    ref_candidate_ids: set[str] | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    del ref_candidate_ids
    try:
        candidate_ref = _candidate_ref_from_payload(
            candidate, draft_version=draft_version, request_id=request_id
        )
    except GenerationReconciliationError as exc:
        mapped = _map_reconciliation_error(exc)
        if mapped is not None:
            raise mapped from None
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=draft_id,
            generated_from_draft_version=draft_version,
            request_id=request_id,
            outcome="failure",
            failure_category="integrity_failure",
            failure_message=str(exc),
            cache_status="missing",
        )

    failures: list[PersistenceFailureV1] = []
    try:
        # Authority first: candidate_received before disposable cache/ref writes.
        record_generation_received(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            request_digest=request_digest,
            candidate=candidate,
        )
    except GenerationReconciliationError as exc:
        mapped = _map_reconciliation_error(exc)
        if mapped is not None:
            raise mapped from None
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=draft_id,
            generated_from_draft_version=draft_version,
            request_id=request_id,
            outcome="failure",
            candidate_ref=candidate_ref,
            candidate=candidate,
            failure_category="integrity_failure",
            failure_message=str(exc),
            cache_status="missing",
        )

    cache_state: Literal["stored", "failed"] = "stored"
    try:
        store_candidate_payload(root, candidate)
    except CandidateCacheError as exc:
        cache_state = "failed"
        failures.append(
            PersistenceFailureV1(
                component="cache",
                category="cache_failure",
                message=str(exc),
            )
        )

    ref_attached = False
    try:
        append_candidate_ref(
            root,
            draft_id=draft_id,
            expected_version=draft_version,
            candidate_ref=candidate_ref,
        )
        ref_attached = True
    except ThreatDraftStoreError as exc:
        failures.append(
            PersistenceFailureV1(
                component="candidate_ref",
                category="ref_failure",
                message=str(exc),
            )
        )

    try:
        if ref_attached:
            update_materialization(
                root,
                draft_id=draft_id,
                draft_version=draft_version,
                request_id=request_id,
                request_digest=request_digest,
                cache=cache_state,
                draft_ref="attached",
                ref_entries=[(candidate.candidate_id, request_id)],
                compact_if_eligible=True,
            )
        else:
            update_materialization(
                root,
                draft_id=draft_id,
                draft_version=draft_version,
                request_id=request_id,
                request_digest=request_digest,
                cache=cache_state,
                draft_ref="failed",
                compact_if_eligible=False,
            )
    except GenerationReconciliationError as exc:
        failures.append(
            PersistenceFailureV1(
                component="reconciliation",
                category="integrity_failure",
                message=str(exc),
            )
        )

    cache_status = _cache_status_from_failures(failures)

    return GenerateThreatDraftCandidateResponseV1(
        draft_id=draft_id,
        generated_from_draft_version=draft_version,
        request_id=request_id,
        outcome="success",
        candidate_ref=candidate_ref,
        candidate=candidate,
        cache_status=cache_status,
        persistence_failures=failures,
        failure_category=failures[0].category if failures else None,
        failure_message=(
            "; ".join(f"{item.component}:{item.message}" for item in failures)
            if failures
            else None
        ),
    )


def _candidate_from_record_or_client(
    root: Path,
    *,
    record,
    client: StatblockV1Client | None,
) -> GeneratedStatblockCandidateV1 | GenerateThreatDraftCandidateResponseV1:
    try:
        candidate = load_received_candidate(record)
        return candidate
    except GenerationReconciliationError as exc:
        message = str(exc)
        # Corrupt stored payload may still be recoverable from cache/Server.
        # Receipt/lineage failures must fail closed — never fabricate request_id.
        if "corrupt generation reconciliation candidate payload" in message:
            pass
        else:
            return _failure(
                draft_id=record.draft_id,
                draft_version=record.draft_version,
                request_id=record.request_id,
                category="integrity_failure",
                message=message,
            )

    assert record.candidate_id is not None
    try:
        cached = read_candidate_payload_or_none(root, record.candidate_id)
    except CandidateCacheError as exc:
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category="integrity_failure",
            message=str(exc),
        )
    if cached is not None:
        try:
            _bound_request_id_from_candidate(cached, request_id=record.request_id)
        except GenerationReconciliationError as exc:
            return _failure(
                draft_id=record.draft_id,
                draft_version=record.draft_version,
                request_id=record.request_id,
                category="integrity_failure",
                message=str(exc),
            )
        return cached

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        payload = active_client.get_candidate(record.candidate_id)
        _bound_request_id_from_candidate(payload, request_id=record.request_id)
        return payload
    except GenerationReconciliationError as exc:
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category="integrity_failure",
            message=str(exc),
        )
    except StatblockIntegrationError as exc:
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category=exc.category,
            message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()


def _call_server_generate(
    *,
    body: dict[str, Any],
    draft_id: str,
    draft_version: int,
    request_id: str,
    client: StatblockV1Client | None,
    root: Path | None = None,
    request_digest: str | None = None,
) -> GeneratedStatblockCandidateV1 | GenerateThreatDraftCandidateResponseV1:
    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        return active_client.generate_candidate(body)
    except StatblockIntegrationError as exc:
        if exc.error_code == "generation_in_progress":
            return _failure(
                draft_id=draft_id,
                draft_version=draft_version,
                request_id=request_id,
                category="generation_incomplete",
                message=exc.message
                or "generation request is already in progress downstream",
            )
        if exc.error_code == "idempotency_conflict":
            if root is not None and request_digest is not None:
                try:
                    record_terminal_failure(
                        root,
                        draft_id=draft_id,
                        draft_version=draft_version,
                        request_id=request_id,
                        request_digest=request_digest,
                        terminal_code="idempotency_conflict",
                        terminal_message=exc.message or "generation idempotency conflict",
                    )
                except GenerationReconciliationError:
                    pass
            raise ThreatDraftStoreError(
                exc.message or "generation idempotency conflict",
                status_code=409,
            ) from None
        # Definitive downstream validation / auth refusals become terminal.
        if exc.category in {
            "downstream_validation_failed",
            "downstream_unauthorized",
            "downstream_forbidden",
        }:
            if root is not None and request_digest is not None:
                try:
                    record_terminal_failure(
                        root,
                        draft_id=draft_id,
                        draft_version=draft_version,
                        request_id=request_id,
                        request_digest=request_digest,
                        terminal_code=exc.error_code or exc.category,
                        terminal_message=exc.message or exc.category,
                    )
                except GenerationReconciliationError:
                    pass
        if exc.category == "downstream_gone" or exc.error_code in {
            "candidate_expired",
            "generation_expired",
        }:
            if root is not None and request_digest is not None:
                try:
                    record_terminal_expired(
                        root,
                        draft_id=draft_id,
                        draft_version=draft_version,
                        request_id=request_id,
                        request_digest=request_digest,
                        terminal_code=exc.error_code or "candidate_expired",
                        terminal_message=exc.message or "candidate expired",
                    )
                except GenerationReconciliationError:
                    pass
        return _failure(
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            category=exc.category,
            message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()


def _recover_uncertain_with_stored_body(
    root: Path,
    *,
    record: GenerationOperationV2,
    client: StatblockV1Client | None,
    ref_candidate_ids: set[str] | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    """Recover dispatched_unknown using the durable request body."""
    if record.request_body is None:
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category="integrity_failure",
            message="generation request body missing from reconciliation record",
        )
    request_digest = request_digest_for_body(record.request_body)
    if request_digest != record.request_digest:
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category="integrity_failure",
            message="generation request body digest mismatch",
        )

    refs = ref_candidate_ids or set()
    # Refresh claim / observe durable outcomes without inventing terminality.
    try:
        claim_status, claim = claim_generation_request(
            root,
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            request_digest=request_digest,
            request_body=record.request_body,
            ref_candidate_ids=refs,
        )
    except GenerationReconciliationError as exc:
        mapped = _map_reconciliation_error(exc)
        if mapped is not None:
            raise mapped from None
        return _failure(
            draft_id=record.draft_id,
            draft_version=record.draft_version,
            request_id=record.request_id,
            category="integrity_failure",
            message=str(exc),
        )

    if claim_status in {
        "candidate_received",
        "reconciled",
        "tombstone_reconciled",
    }:
        return _replay_from_authority(
            root,
            entry=claim,
            request_digest=request_digest,
            client=client,
            ref_candidate_ids=refs,
        )
    if claim_status in {
        "terminal_failure",
        "terminal_expired",
        "tombstone_terminal_failure",
        "tombstone_terminal_expired",
    }:
        return _terminal_response(entry=claim, request_digest=request_digest)

    body = (
        claim.request_body
        if isinstance(claim, GenerationOperationV2) and claim.request_body is not None
        else record.request_body
    )
    candidate_or_failure = _call_server_generate(
        body=body,
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        request_id=record.request_id,
        client=client,
        root=root,
        request_digest=request_digest,
    )
    if isinstance(candidate_or_failure, GenerateThreatDraftCandidateResponseV1):
        return candidate_or_failure
    return _persist_candidate_artifacts(
        root,
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        candidate=candidate_or_failure,
        request_id=record.request_id,
        request_digest=request_digest,
        ref_candidate_ids=refs,
    )


def _terminal_response(
    *,
    entry: GenerationOperationV2 | GenerationTombstoneV1,
    request_digest: str,
) -> GenerateThreatDraftCandidateResponseV1:
    if entry.request_digest != request_digest:
        raise ThreatDraftStoreError(
            "generation request replay conflict",
            status_code=409,
        )
    if isinstance(entry, GenerationTombstoneV1):
        code = entry.terminal_code or entry.outcome
        message = entry.terminal_message or entry.outcome
        category = (
            "downstream_gone"
            if entry.outcome == "terminal_expired"
            else "downstream_validation_failed"
        )
    else:
        code = entry.terminal_code or entry.status
        message = entry.terminal_message or entry.status
        category = (
            "downstream_gone"
            if entry.status == "terminal_expired"
            else "downstream_validation_failed"
        )
    return _failure(
        draft_id=entry.draft_id,
        draft_version=entry.draft_version,
        request_id=entry.request_id,
        category=category,
        message=f"{code}: {message}",
    )


def _candidate_from_tombstone(
    root: Path,
    *,
    tombstone: GenerationTombstoneV1,
    client: StatblockV1Client | None,
) -> GeneratedStatblockCandidateV1 | GenerateThreatDraftCandidateResponseV1:
    if not tombstone.candidate_id:
        return _failure(
            draft_id=tombstone.draft_id,
            draft_version=tombstone.draft_version,
            request_id=tombstone.request_id,
            category="integrity_failure",
            message="tombstone missing candidate_id",
        )
    try:
        cached = read_candidate_payload_or_none(root, tombstone.candidate_id)
    except CandidateCacheError as exc:
        return _failure(
            draft_id=tombstone.draft_id,
            draft_version=tombstone.draft_version,
            request_id=tombstone.request_id,
            category="integrity_failure",
            message=str(exc),
        )
    if cached is not None:
        try:
            _bound_request_id_from_candidate(cached, request_id=tombstone.request_id)
        except GenerationReconciliationError as exc:
            return _failure(
                draft_id=tombstone.draft_id,
                draft_version=tombstone.draft_version,
                request_id=tombstone.request_id,
                category="integrity_failure",
                message=str(exc),
            )
        return cached

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        payload = active_client.get_candidate(tombstone.candidate_id)
        _bound_request_id_from_candidate(payload, request_id=tombstone.request_id)
        return payload
    except GenerationReconciliationError as exc:
        return _failure(
            draft_id=tombstone.draft_id,
            draft_version=tombstone.draft_version,
            request_id=tombstone.request_id,
            category="integrity_failure",
            message=str(exc),
        )
    except StatblockIntegrationError as exc:
        return _failure(
            draft_id=tombstone.draft_id,
            draft_version=tombstone.draft_version,
            request_id=tombstone.request_id,
            category=exc.category,
            message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()


def _replay_from_authority(
    root: Path,
    *,
    entry: GenerationOperationV2 | GenerationTombstoneV1,
    request_digest: str,
    client: StatblockV1Client | None,
    ref_candidate_ids: set[str] | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    if entry.request_digest != request_digest:
        raise ThreatDraftStoreError(
            "generation request replay conflict",
            status_code=409,
        )
    if isinstance(entry, GenerationTombstoneV1):
        if entry.outcome in {"terminal_failure", "terminal_expired"}:
            return _terminal_response(entry=entry, request_digest=request_digest)
        candidate_or_failure = _candidate_from_tombstone(
            root, tombstone=entry, client=client
        )
        if isinstance(candidate_or_failure, GenerateThreatDraftCandidateResponseV1):
            return candidate_or_failure
        # Tombstone already reconciled — return success without regenerating.
        candidate_ref = _candidate_ref_from_payload(
            candidate_or_failure,
            draft_version=entry.draft_version,
            request_id=entry.request_id,
        )
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=entry.draft_id,
            generated_from_draft_version=entry.draft_version,
            request_id=entry.request_id,
            outcome="success",
            candidate_ref=candidate_ref,
            candidate=candidate_or_failure,
            cache_status="stored",
        )

    if entry.status in {"terminal_failure", "terminal_expired"}:
        return _terminal_response(entry=entry, request_digest=request_digest)

    candidate_or_failure = _candidate_from_record_or_client(
        root, record=entry, client=client
    )
    if isinstance(candidate_or_failure, GenerateThreatDraftCandidateResponseV1):
        return candidate_or_failure
    return _persist_candidate_artifacts(
        root,
        draft_id=entry.draft_id,
        draft_version=entry.draft_version,
        candidate=candidate_or_failure,
        request_id=entry.request_id,
        request_digest=request_digest,
        ref_candidate_ids=ref_candidate_ids,
    )


def _replay_from_record(
    root: Path,
    *,
    record,
    request_digest: str,
    client: StatblockV1Client | None,
    ref_candidate_ids: set[str] | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    return _replay_from_authority(
        root,
        entry=record,
        request_digest=request_digest,
        client=client,
        ref_candidate_ids=ref_candidate_ids,
    )


def _resolve_request_id(request: GenerateThreatDraftCandidateRequestV1) -> str:
    if request.client_request_id is not None:
        try:
            return validate_request_id(request.client_request_id)
        except GenerationReconciliationError as exc:
            raise ThreatDraftStoreError(str(exc), status_code=422) from None
    return str(uuid.uuid4())


def _digest_for_source_version(
    root: Path,
    *,
    draft_id: str,
    source_version: int,
    request_id: str,
    existing_digest: str,
    existing_body: dict[str, Any] | None = None,
) -> str:
    if existing_body is not None:
        digest = request_digest_for_body(existing_body)
        if digest != existing_digest:
            raise ThreatDraftStoreError(
                "generation request replay conflict",
                status_code=409,
            )
        return digest
    draft = get_threat_draft(root, draft_id)
    if draft.version == source_version:
        body = map_draft_to_generate_request(draft, request_id=request_id)
        digest = request_digest_for_body(body)
        if digest != existing_digest:
            raise ThreatDraftStoreError(
                "generation request replay conflict",
                status_code=409,
            )
        return digest
    return existing_digest


def generate_candidate_from_draft(
    root: Path,
    *,
    draft_id: str,
    request: GenerateThreatDraftCandidateRequestV1,
    client: StatblockV1Client | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    request_id = _resolve_request_id(request)
    source_version = request.expected_draft_version

    # Replay/recovery before version gates — full records and tombstones.
    try:
        existing = read_reconciliation(
            root,
            draft_id=draft_id,
            draft_version=source_version,
            request_id=request_id,
        )
    except GenerationReconciliationError as exc:
        mapped = _map_reconciliation_error(exc)
        if mapped is not None:
            raise mapped from None
        return _failure(
            draft_id=draft_id,
            draft_version=source_version,
            request_id=request_id,
            category="integrity_failure",
            message=str(exc),
        )

    ref_ids: set[str] = set()
    try:
        current = get_threat_draft(root, draft_id)
        ref_ids = {ref.candidate_id for ref in current.candidate_refs}
    except ThreatDraftStoreError:
        ref_ids = set()

    if isinstance(existing, GenerationTombstoneV1):
        # Same-key body conflict: when the source draft version is still current,
        # recompute the body digest and compare to the tombstone digest.
        request_digest = _digest_for_source_version(
            root,
            draft_id=draft_id,
            source_version=source_version,
            request_id=request_id,
            existing_digest=existing.request_digest,
            existing_body=None,
        )
        return _replay_from_authority(
            root,
            entry=existing,
            request_digest=request_digest,
            client=client,
            ref_candidate_ids=ref_ids,
        )

    if existing is not None and existing.status in {
        "candidate_received",
        "reconciled",
    }:
        request_digest = _digest_for_source_version(
            root,
            draft_id=draft_id,
            source_version=source_version,
            request_id=request_id,
            existing_digest=existing.request_digest,
            existing_body=existing.request_body,
        )
        return _replay_from_authority(
            root,
            entry=existing,
            request_digest=request_digest,
            client=client,
            ref_candidate_ids=ref_ids,
        )

    if existing is not None and existing.status in {
        "terminal_failure",
        "terminal_expired",
    }:
        return _terminal_response(
            entry=existing, request_digest=existing.request_digest
        )

    if existing is not None and existing.status == "dispatched_unknown":
        return _recover_uncertain_with_stored_body(
            root,
            record=existing,
            client=client,
            ref_candidate_ids=ref_ids,
        )

    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError as exc:
        if exc.status_code == 404:
            raise
        raise

    if draft.version != source_version:
        raise ThreatDraftStoreError("expected_version mismatch", status_code=409)

    body = map_draft_to_generate_request(draft, request_id=request_id)
    request_digest = request_digest_for_body(body)
    ref_candidate_ids = {ref.candidate_id for ref in draft.candidate_refs}
    ref_entries = [(ref.candidate_id, ref.request_id) for ref in draft.candidate_refs]

    try:
        claim_status, claim = claim_generation_request(
            root,
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            request_digest=request_digest,
            request_body=body,
            ref_candidate_ids=ref_candidate_ids,
            ref_entries=ref_entries,
        )
    except GenerationReconciliationError as exc:
        mapped = _map_reconciliation_error(exc)
        if mapped is not None:
            raise mapped from None
        return _failure(
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            category="integrity_failure",
            message=str(exc),
        )

    if claim_status in {
        "candidate_received",
        "reconciled",
        "tombstone_reconciled",
    }:
        return _replay_from_authority(
            root,
            entry=claim,
            request_digest=request_digest,
            client=client,
            ref_candidate_ids=ref_candidate_ids,
        )
    if claim_status in {
        "terminal_failure",
        "terminal_expired",
        "tombstone_terminal_failure",
        "tombstone_terminal_expired",
    }:
        return _terminal_response(entry=claim, request_digest=request_digest)

    # claimed / dispatched_retry: call Server. PR23 makes generate idempotent.
    candidate_or_failure = _call_server_generate(
        body=body,
        draft_id=draft.draft_id,
        draft_version=source_version,
        request_id=request_id,
        client=client,
        root=root,
        request_digest=request_digest,
    )
    if isinstance(candidate_or_failure, GenerateThreatDraftCandidateResponseV1):
        return candidate_or_failure

    return _persist_candidate_artifacts(
        root,
        draft_id=draft.draft_id,
        draft_version=source_version,
        candidate=candidate_or_failure,
        request_id=request_id,
        request_digest=request_digest,
        ref_candidate_ids=ref_candidate_ids,
    )


def _candidate_is_expired(candidate: GeneratedStatblockCandidateV1) -> bool:
    expires_at = candidate.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= _utc_now()


def read_candidate(
    root: Path,
    *,
    candidate_id: str,
    client: StatblockV1Client | None = None,
) -> ReadStatblockCandidateResponseV1:
    try:
        cached = read_candidate_payload_or_none(root, candidate_id)
    except CandidateCacheError as exc:
        return ReadStatblockCandidateResponseV1(
            candidate_id=candidate_id,
            status="unavailable",
            failure_category="integrity_failure",
            failure_message=str(exc),
        )

    if cached is not None:
        if _candidate_is_expired(cached):
            return ReadStatblockCandidateResponseV1(
                candidate_id=candidate_id,
                status="expired",
                candidate=cached,
            )
        return ReadStatblockCandidateResponseV1(
            candidate_id=candidate_id,
            status="active",
            candidate=cached,
        )

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        payload = active_client.get_candidate(candidate_id)
    except StatblockIntegrationError as exc:
        if exc.category == "downstream_expired":
            status = "expired"
        elif exc.category == "downstream_not_found":
            status = "missing"
        else:
            status = "unavailable"
        return ReadStatblockCandidateResponseV1(
            candidate_id=candidate_id,
            status=status,  # type: ignore[arg-type]
            failure_category=exc.category,
            failure_message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()

    try:
        store_candidate_payload(root, payload)
    except CandidateCacheError:
        pass
    if _candidate_is_expired(payload):
        return ReadStatblockCandidateResponseV1(
            candidate_id=candidate_id,
            status="expired",
            candidate=payload,
        )
    return ReadStatblockCandidateResponseV1(
        candidate_id=candidate_id,
        status="active",
        candidate=payload,
    )
