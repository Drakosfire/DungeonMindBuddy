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
    ThreatDraftCandidateRefV1,
    ThreatDraftV1,
)
from apps.live_control_server.services.statblock_candidate_cache import (
    CandidateCacheError,
    read_candidate_payload,
    read_candidate_payload_or_none,
    store_candidate_payload,
)
from apps.live_control_server.services.statblock_generation_reconciliation import (
    GenerationReconciliationError,
    read_reconciliation,
    request_digest_for_body,
    validate_request_id,
    write_reconciliation,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    append_candidate_ref,
    get_threat_draft,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
        created_at=candidate.created_at,
        expires_at=candidate.expires_at,
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


def _persist_candidate_artifacts(
    root: Path,
    *,
    draft: ThreatDraftV1,
    candidate: GeneratedStatblockCandidateV1,
    request_id: str,
    request_digest: str,
) -> GenerateThreatDraftCandidateResponseV1:
    candidate_ref = _candidate_ref_from_payload(
        candidate, draft_version=draft.version
    )
    try:
        write_reconciliation(
            root,
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
            request_digest=request_digest,
            candidate_id=candidate.candidate_id,
        )
    except GenerationReconciliationError as exc:
        if exc.status_code == 409:
            raise ThreatDraftStoreError(str(exc), status_code=409) from None
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=draft.draft_id,
            generated_from_draft_version=draft.version,
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
            draft_id=draft.draft_id,
            expected_version=draft.version,
            candidate_ref=candidate_ref,
        )
    except ThreatDraftStoreError:
        cache_status = "partial_ref" if cache_status == "stored" else "partial_cache"

    return GenerateThreatDraftCandidateResponseV1(
        draft_id=draft.draft_id,
        generated_from_draft_version=draft.version,
        request_id=request_id,
        outcome="success",
        candidate_ref=candidate_ref,
        candidate=candidate,
        cache_status=cache_status,  # type: ignore[arg-type]
    )


def _replay_from_reconciliation(
    root: Path,
    *,
    draft: ThreatDraftV1,
    request_id: str,
    request_digest: str,
    client: StatblockV1Client | None,
) -> GenerateThreatDraftCandidateResponseV1:
    try:
        record = read_reconciliation(
            root,
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
        )
    except GenerationReconciliationError as exc:
        if exc.status_code == 422:
            raise ThreatDraftStoreError(str(exc), status_code=422) from None
        return _failure(
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
            category="integrity_failure",
            message=str(exc),
        )

    if record is None:
        return _failure(
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
            category="integrity_failure",
            message="missing generation reconciliation record",
        )
    if record.request_digest != request_digest:
        raise ThreatDraftStoreError(
            "generation request replay conflict",
            status_code=409,
        )

    candidate = read_candidate_payload_or_none(root, record.candidate_id)
    if candidate is None:
        active_client = client or DungeonMindStatblockV1Client()
        owns_client = client is None
        try:
            candidate = active_client.get_candidate(record.candidate_id)
        except StatblockIntegrationError as exc:
            return _failure(
                draft_id=draft.draft_id,
                draft_version=draft.version,
                request_id=request_id,
                category=exc.category,
                message=exc.message,
            )
        finally:
            if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
                active_client.close()

    return _persist_candidate_artifacts(
        root,
        draft=draft,
        candidate=candidate,
        request_id=request_id,
        request_digest=request_digest,
    )


def generate_candidate_from_draft(
    root: Path,
    *,
    draft_id: str,
    request: GenerateThreatDraftCandidateRequestV1,
    client: StatblockV1Client | None = None,
) -> GenerateThreatDraftCandidateResponseV1:
    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError as exc:
        if exc.status_code == 404:
            raise
        raise

    if draft.version != request.expected_draft_version:
        raise ThreatDraftStoreError("expected_version mismatch", status_code=409)

    if request.client_request_id is not None:
        try:
            request_id = validate_request_id(request.client_request_id)
        except GenerationReconciliationError as exc:
            raise ThreatDraftStoreError(str(exc), status_code=422) from None
    else:
        request_id = str(uuid.uuid4())

    body = map_draft_to_generate_request(draft, request_id=request_id)
    request_digest = request_digest_for_body(body)

    try:
        existing = read_reconciliation(
            root,
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
        )
    except GenerationReconciliationError as exc:
        if exc.status_code == 422:
            raise ThreatDraftStoreError(str(exc), status_code=422) from None
        return _failure(
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
            category="integrity_failure",
            message=str(exc),
        )

    if existing is not None:
        return _replay_from_reconciliation(
            root,
            draft=draft,
            request_id=request_id,
            request_digest=request_digest,
            client=client,
        )

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        candidate = active_client.generate_candidate(body)
    except StatblockIntegrationError as exc:
        return _failure(
            draft_id=draft.draft_id,
            draft_version=draft.version,
            request_id=request_id,
            category=exc.category,
            message=exc.message,
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()

    return _persist_candidate_artifacts(
        root,
        draft=draft,
        candidate=candidate,
        request_id=request_id,
        request_digest=request_digest,
    )


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
        expires_at = cached.expires_at
        if isinstance(expires_at, str) and expires_at < _utc_now_iso():
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
    return ReadStatblockCandidateResponseV1(
        candidate_id=candidate_id,
        status="active",
        candidate=payload,
    )
