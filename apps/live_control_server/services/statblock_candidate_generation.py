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
    store_candidate_payload,
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

    request_id = (request.client_request_id or "").strip() or str(uuid.uuid4())
    body = map_draft_to_generate_request(draft, request_id=request_id)

    active_client = client or DungeonMindStatblockV1Client()
    owns_client = client is None
    try:
        candidate_payload = active_client.generate_candidate(body)
    except StatblockIntegrationError as exc:
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=draft.draft_id,
            generated_from_draft_version=draft.version,
            request_id=request_id,
            outcome="failure",
            failure_category=exc.category,
            failure_message=exc.message,
            cache_status="missing",
        )
    finally:
        if owns_client and isinstance(active_client, DungeonMindStatblockV1Client):
            active_client.close()

    candidate_id = str(candidate_payload.get("candidate_id") or "").strip()
    if not candidate_id:
        return GenerateThreatDraftCandidateResponseV1(
            draft_id=draft.draft_id,
            generated_from_draft_version=draft.version,
            request_id=request_id,
            outcome="failure",
            failure_category="downstream_unexpected",
            failure_message="candidate response missing candidate_id",
            cache_status="missing",
        )

    candidate_ref = ThreatDraftCandidateRefV1(
        candidate_id=candidate_id,
        generated_from_draft_version=draft.version,
        request_id=request_id,
        created_at=str(candidate_payload.get("created_at") or _utc_now_iso()),
        expires_at=(
            str(candidate_payload["expires_at"])
            if candidate_payload.get("expires_at") is not None
            else None
        ),
        status="active",
    )

    cache_status: str = "stored"
    try:
        store_candidate_payload(root, candidate_id, candidate_payload)
    except Exception:
        cache_status = "partial"

    try:
        append_candidate_ref(
            root,
            draft_id=draft.draft_id,
            expected_version=draft.version,
            candidate_ref=candidate_ref,
        )
    except ThreatDraftStoreError:
        cache_status = "partial"

    return GenerateThreatDraftCandidateResponseV1(
        draft_id=draft.draft_id,
        generated_from_draft_version=draft.version,
        request_id=request_id,
        outcome="success",
        candidate_ref=candidate_ref,
        candidate=candidate_payload,
        cache_status=cache_status,  # type: ignore[arg-type]
    )


def read_candidate(
    root: Path,
    *,
    candidate_id: str,
    client: StatblockV1Client | None = None,
) -> ReadStatblockCandidateResponseV1:
    try:
        cached = read_candidate_payload(root, candidate_id)
    except CandidateCacheError as exc:
        return ReadStatblockCandidateResponseV1(
            candidate_id=candidate_id,
            status="unavailable",
            failure_category="integrity_failure",
            failure_message=str(exc),
        )

    if cached is not None:
        expires_at = cached.get("expires_at")
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
        status = "expired" if exc.category == "downstream_not_found" else "unavailable"
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
        store_candidate_payload(root, candidate_id, payload)
    except Exception:
        pass
    return ReadStatblockCandidateResponseV1(
        candidate_id=candidate_id,
        status="active",
        candidate=payload,
    )
