"""Atomic durable ThreatDraft repository with optimistic concurrency."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    ThreatDraftCandidateRefV1,
    ThreatDraftSummaryV1,
    ThreatDraftV1,
    UpdateThreatDraftRequest,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_STORE_REL = "out/threat_drafts"
INDEX_NAME = "index.json"


class ThreatDraftStoreError(ValueError):
    status_code: int = 422

    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def threat_drafts_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_STORE_REL


def _draft_path(root: Path, draft_id: str) -> Path:
    return threat_drafts_root(root) / f"{draft_id}.json"


def _index_path(root: Path) -> Path:
    return threat_drafts_root(root) / INDEX_NAME


def _load_index(root: Path) -> list[str]:
    path = _index_path(root)
    if not path.is_file():
        return []
    payload = load_json(path)
    drafts = payload.get("draft_ids")
    if not isinstance(drafts, list):
        raise ThreatDraftStoreError("corrupt threat draft index", status_code=500)
    return [str(item) for item in drafts]


def _save_index(root: Path, draft_ids: list[str]) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {"schema": "dmb_threat_draft_index_v1", "draft_ids": draft_ids})


def _load_draft(root: Path, draft_id: str) -> ThreatDraftV1:
    path = _draft_path(root, draft_id)
    if not path.is_file():
        raise ThreatDraftStoreError("threat draft not found", status_code=404)
    try:
        payload = load_json(path)
        return ThreatDraftV1.model_validate(payload)
    except ThreatDraftStoreError:
        raise
    except Exception as exc:
        raise ThreatDraftStoreError(
            "corrupt threat draft record",
            status_code=500,
        ) from exc


def _save_draft(root: Path, draft: ThreatDraftV1) -> None:
    path = _draft_path(root, draft.draft_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, draft.model_dump(mode="json", by_alias=True))


def create_threat_draft(root: Path, request: CreateThreatDraftRequest) -> ThreatDraftV1:
    now = _utc_now_iso()
    draft = ThreatDraftV1(
        draft_id=str(uuid.uuid4()),
        version=1,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        focus=request.focus,
        name=request.name,
        slug_hint=request.slug_hint,
        description=request.description,
        threat_kind=request.threat_kind,
        intended_roles=list(request.intended_roles),
        tags=list(request.tags),
        generation_intent=request.generation_intent,
        encounter_context=request.encounter_context,
        graph_context_snapshot=request.graph_context_snapshot,
        candidate_refs=[],
        accepted_mechanics_ref=None,
        workflow_state="drafting",
        created_by=request.created_by,
        created_at=now,
        updated_at=now,
    )
    _save_draft(root, draft)
    index = _load_index(root)
    if draft.draft_id not in index:
        index.append(draft.draft_id)
        _save_index(root, index)
    return draft


def get_threat_draft(root: Path, draft_id: str) -> ThreatDraftV1:
    return _load_draft(root, draft_id.strip())


def list_threat_drafts(
    root: Path,
    *,
    campaign_id: str | None = None,
    world_id: str | None = None,
) -> list[ThreatDraftSummaryV1]:
    summaries: list[ThreatDraftSummaryV1] = []
    for draft_id in _load_index(root):
        try:
            draft = _load_draft(root, draft_id)
        except ThreatDraftStoreError as exc:
            if exc.status_code == 404:
                continue
            raise
        if campaign_id and draft.campaign_id != campaign_id:
            continue
        if world_id and draft.world_id != world_id:
            continue
        summaries.append(
            ThreatDraftSummaryV1(
                draft_id=draft.draft_id,
                version=draft.version,
                world_id=draft.world_id,
                campaign_id=draft.campaign_id,
                name=draft.name,
                threat_kind=draft.threat_kind,
                workflow_state=draft.workflow_state,
                updated_at=draft.updated_at,
            )
        )
    summaries.sort(key=lambda item: (item.updated_at, item.draft_id), reverse=True)
    return summaries


def update_threat_draft(
    root: Path,
    draft_id: str,
    request: UpdateThreatDraftRequest,
) -> ThreatDraftV1:
    current = _load_draft(root, draft_id.strip())
    if current.version != request.expected_version:
        raise ThreatDraftStoreError(
            "expected_version mismatch",
            status_code=409,
        )
    updated = current.model_copy(
        update={
            "version": current.version + 1,
            "focus": request.focus,
            "name": request.name,
            "slug_hint": request.slug_hint,
            "description": request.description,
            "threat_kind": request.threat_kind,
            "intended_roles": list(request.intended_roles),
            "tags": list(request.tags),
            "generation_intent": request.generation_intent,
            "encounter_context": request.encounter_context,
            "graph_context_snapshot": request.graph_context_snapshot,
            "updated_at": _utc_now_iso(),
        }
    )
    _save_draft(root, updated)
    return updated


def append_candidate_ref(
    root: Path,
    *,
    draft_id: str,
    expected_version: int,
    candidate_ref: ThreatDraftCandidateRefV1,
    workflow_state: str | None = "candidate_ready",
) -> ThreatDraftV1:
    """Append a candidate ref without mutating authored concept fields.

    Version is unchanged because authored concept identity is preserved; the
    candidate_refs list is workflow evidence owned by the same record.
    """
    current = _load_draft(root, draft_id.strip())
    if current.version != expected_version:
        raise ThreatDraftStoreError("expected_version mismatch", status_code=409)
    existing_ids = {ref.candidate_id for ref in current.candidate_refs}
    refs = list(current.candidate_refs)
    if candidate_ref.candidate_id not in existing_ids:
        refs.append(candidate_ref)
    updates: dict = {
        "candidate_refs": refs,
        "updated_at": _utc_now_iso(),
    }
    if workflow_state is not None:
        updates["workflow_state"] = workflow_state
    updated = current.model_copy(update=updates)
    _save_draft(root, updated)
    return updated
