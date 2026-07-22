"""Exact ThreatDraft version → DungeonMind candidate generation orchestration."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    ReadStatblockCandidateResponseV1,
)
from apps.live_control_server.models.threat_draft import (
    MAX_CANDIDATE_REFS,
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
    read_reconciliation,
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
) -> ThreatDraftCandidateRefV1:
    return ThreatDraftCandidateRefV1(
        candidate_id=candidate.candidate_id,
        generated_from_draft_version=draft_version,
        request_id=candidate.generation_receipt.request_id,
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
        candidate, draft_version=draft_version
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

    cache_status: str = "stored"
    try:
        store_candidate_payload(root, candidate)
    except CandidateCacheError:
        cache_status = "partial_cache"

    try:
        append_candidate_ref(
            root,
            draft_id=draft_id,
            expected_version=draft_version,
            candidate_ref=candidate_ref,
        )
    except ThreatDraftStoreError:
        cache_status = "partial_ref" if cache_status == "stored" else "partial_cache"

    return GenerateThreatDraftCandidateResponseV1(
        draft_id=draft_id,
        generated_from_draft_version=draft_version,
        request_id=request_id,
        outcome="success",
        candidate_ref=candidate_ref,
        candidate=candidate,
        cache_status=cache_status,  # type: ignore[arg-type]
    )


def _replay_from_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate_id: str,
    client: StatblockV1Client | None,
) -> GenerateThreatDraftCandidateResponseV1:
    try:
        candidate = read_candidate_payload_or_none(root, candidate_id)
    except CandidateCacheError as exc:
        return _failure(
            draft_id=draft_id,
            draft_version=draft_version,
            request_id=request_id,
            category="integrity_failure",
            message=str(exc),
        )

    if candidate is None:
        active_client = client or DungeonMindStatblockV1Client()
        owns_client = client is None
        try:
            candidate = active_client.get_candidate(candidate_id)
        except StatblockIntegrationError as exc:
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

    return _persist_candidate_artifacts(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        candidate=candidate,
        request_id=request_id,
        request_digest=request_digest,
    )


def _resolve_request_id(request: GenerateThreatDraftCandidateRequestV1) -> str:
    if request.client_request_id is not None:
        try:
            return validate_request_id(request.client_request_id)
        except GenerationReconciliationError as exc:
            raise ThreatDraftStoreError(str(exc), status_code=422) from None
    return str(uuid.uuid4())


def generate_candidate_from_draft(
    root: Path,
    *,
    draft_id: str,
    request: GenerateThreatDraftCandidateRequestV1,
    client: StatblockV1Client | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    request_id = _resolve_request_id(request)
    source_version = request.expected_draft_version

    # Replay must be examined before version/capacity gates so a completed
    # generation retains lineage after the draft advances or refs fill up.
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

    if existing is not None and existing.status == "completed":
        assert existing.candidate_id is not None
        # Digest check uses the body from the current draft snapshot when still
        # at the source version; when the draft advanced, trust the stored
        # digest and only verify request identity via claim path.
        try:
            draft = get_threat_draft(root, draft_id)
        except ThreatDraftStoreError as exc:
            if exc.status_code == 404:
                raise
            raise
        if draft.version == source_version:
            body = map_draft_to_generate_request(draft, request_id=request_id)
            request_digest = request_digest_for_body(body)
            if existing.request_digest != request_digest:
                raise ThreatDraftStoreError(
                    "generation request replay conflict",
                    status_code=409,
                )
        else:
            request_digest = existing.request_digest
        return _replay_from_reconciliation(
            root,
            draft_id=draft_id,
            draft_version=source_version,
            request_id=request_id,
            request_digest=request_digest,
            candidate_id=existing.candidate_id,
            client=client,
        )

    if existing is not None and existing.status == "pending":
        try:
            draft_for_pending = get_threat_draft(root, draft_id)
        except ThreatDraftStoreError as exc:
            if exc.status_code == 404:
                raise
            raise
        if draft_for_pending.version == source_version:
            pending_digest = request_digest_for_body(
                map_draft_to_generate_request(
                    draft_for_pending, request_id=request_id
                )
            )
            if existing.request_digest != pending_digest:
                raise ThreatDraftStoreError(
                    "generation request replay conflict",
                    status_code=409,
                )
        return _failure(
            draft_id=draft_id,
            draft_version=source_version,
            request_id=request_id,
            category="generation_incomplete",
            message="generation request is already claimed without a durable candidate",
        )

    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError as exc:
        if exc.status_code == 404:
            raise
        raise

    if draft.version != source_version:
        raise ThreatDraftStoreError("expected_version mismatch", status_code=409)

    if len(draft.candidate_refs) >= MAX_CANDIDATE_REFS:
        raise ThreatDraftStoreError(
            "candidate_refs limit exceeded",
            status_code=422,
        )

    body = map_draft_to_generate_request(draft, request_id=request_id)
    request_digest = request_digest_for_body(body)

    try:
        claim_status, claim = claim_generation_request(
            root,
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            request_digest=request_digest,
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

    if claim_status == "completed":
        assert claim.candidate_id is not None
        return _replay_from_reconciliation(
            root,
            draft_id=draft.draft_id,
            draft_version=source_version,
            request_id=request_id,
            request_digest=request_digest,
            candidate_id=claim.candidate_id,
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

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        candidate = active_client.generate_candidate(body)
    except StatblockIntegrationError as exc:
        # Claim remains pending so retries do not spawn another provider call.
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
