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
    GenerationReconciliationError,
    claim_generation_request,
    finalize_generation_request,
    load_received_candidate,
    read_reconciliation,
    record_generation_received,
    request_digest_for_body,
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


def _candidate_ref_from_payload(
    candidate: GeneratedStatblockCandidateV1,
    *,
    draft_version: int,
    request_id: str,
) -> ThreatDraftCandidateRefV1:
    receipt_request_id = (
        candidate.generation_receipt.request_id
        if candidate.generation_receipt is not None
        else request_id
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
) -> GenerateThreatDraftCandidateResponseV1:
    candidate_ref = _candidate_ref_from_payload(
        candidate, draft_version=draft_version, request_id=request_id
    )
    try:
        # Durably bind locator before any disposable cache/ref write.
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

    failures: list[PersistenceFailureV1] = []
    try:
        store_candidate_payload(root, candidate)
    except CandidateCacheError as exc:
        failures.append(
            PersistenceFailureV1(
                component="cache",
                category="cache_failure",
                message=str(exc),
            )
        )

    try:
        append_candidate_ref(
            root,
            draft_id=draft_id,
            expected_version=draft_version,
            candidate_ref=candidate_ref,
        )
    except ThreatDraftStoreError as exc:
        failures.append(
            PersistenceFailureV1(
                component="candidate_ref",
                category="ref_failure",
                message=str(exc),
            )
        )

    try:
        finalize_generation_request(
            root,
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            request_digest=request_digest,
            candidate_id=candidate.candidate_id,
        )
    except GenerationReconciliationError as exc:
        # Locator already durable in received form; do not mislabel as ref failure.
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
        return load_received_candidate(record)
    except GenerationReconciliationError:
        pass

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
        return cached

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        return active_client.get_candidate(record.candidate_id)
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


def _replay_from_record(
    root: Path,
    *,
    record,
    request_digest: str,
    client: StatblockV1Client | None,
) -> GenerateThreatDraftCandidateResponseV1:
    if record.request_digest != request_digest:
        raise ThreatDraftStoreError(
            "generation request replay conflict",
            status_code=409,
        )
    candidate_or_failure = _candidate_from_record_or_client(
        root, record=record, client=client
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
) -> str:
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

    # Replay/recovery before version gates so received/completed lineage survives
    # draft advance.
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

    if existing is not None and existing.status in {"received", "completed"}:
        request_digest = _digest_for_source_version(
            root,
            draft_id=draft_id,
            source_version=source_version,
            request_id=request_id,
            existing_digest=existing.request_digest,
        )
        return _replay_from_record(
            root,
            record=existing,
            request_digest=request_digest,
            client=client,
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

    try:
        claim_status, claim = claim_generation_request(
            root,
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            request_digest=request_digest,
            ref_candidate_ids=ref_candidate_ids,
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

    if claim_status in {"completed", "received"}:
        return _replay_from_record(
            root,
            record=claim,
            request_digest=request_digest,
            client=client,
        )

    if claim_status == "pending":
        return _failure(
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            category="generation_incomplete",
            message="generation request is already claimed without a durable candidate",
        )

    if claim_status == "abandoned":
        # Expired pending is terminal: the provider is non-idempotent and may
        # already have succeeded without a durable locator binding.
        return _failure(
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            category="generation_incomplete",
            message=(
                "generation request expired without a durable candidate; "
                "request_id is not retryable"
            ),
        )

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        candidate = active_client.generate_candidate(body)
    except StatblockIntegrationError as exc:
        # Pending claim stays until TTL; expiry abandons without provider retry.
        return _failure(
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            category=exc.category,
            message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()

    # Immediate durable locator bind — before cache/ref — so crash recovery works.
    return _persist_candidate_artifacts(
        root,
        draft_id=draft.draft_id,
        draft_version=source_version,
        candidate=candidate,
        request_id=request_id,
        request_digest=request_digest,
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
