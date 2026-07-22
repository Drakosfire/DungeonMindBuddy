"""Atomic durable ThreatDraft repository with optimistic concurrency."""
from __future__ import annotations

import fcntl
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from apps.live_control_server.models.threat_draft import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    CreateThreatDraftRequest,
    ThreatDraftIndexV1,
    ThreatDraftSummaryV1,
    ThreatDraftV1,
    UpdateThreatDraftRequest,
    require_draft_id,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_STORE_REL = "out/threat_drafts"
INDEX_NAME = "index.json"
LOCK_NAME = ".store.lock"


class ThreatDraftStoreError(ValueError):
    status_code: int = 422

    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def threat_drafts_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_STORE_REL


@contextmanager
def _store_lock(root: Path) -> Iterator[None]:
    """Exclusive lock covering index and draft mutation for one store root."""
    store_root = threat_drafts_root(root)
    store_root.mkdir(parents=True, exist_ok=True)
    lock_path = store_root / LOCK_NAME
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _validated_draft_id(draft_id: str) -> str:
    try:
        return require_draft_id(draft_id)
    except ValueError as exc:
        raise ThreatDraftStoreError("invalid draft_id", status_code=422) from None


def _draft_path(root: Path, draft_id: str) -> Path:
    """Resolve a draft path that is always under the store directory."""
    cleaned = _validated_draft_id(draft_id)
    store_root = threat_drafts_root(root).resolve()
    path = (store_root / f"{cleaned}.json").resolve()
    if path.parent != store_root:
        raise ThreatDraftStoreError(
            "corrupt threat draft index",
            status_code=500,
        )
    return path


def _index_path(root: Path) -> Path:
    return threat_drafts_root(root) / INDEX_NAME


def _load_index(root: Path) -> ThreatDraftIndexV1:
    path = _index_path(root)
    if not path.is_file():
        return ThreatDraftIndexV1()
    try:
        payload = load_json(path)
        return ThreatDraftIndexV1.model_validate(payload)
    except ThreatDraftStoreError:
        raise
    except Exception:
        raise ThreatDraftStoreError(
            "corrupt threat draft index",
            status_code=500,
        ) from None


def _save_index(root: Path, index: ThreatDraftIndexV1) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, index.model_dump(mode="json", by_alias=True))


def _load_draft_unlocked(root: Path, draft_id: str) -> ThreatDraftV1:
    path = _draft_path(root, draft_id)
    if not path.is_file():
        raise ThreatDraftStoreError("threat draft not found", status_code=404)
    try:
        payload = load_json(path)
        return ThreatDraftV1.model_validate(payload)
    except ThreatDraftStoreError:
        raise
    except Exception:
        raise ThreatDraftStoreError(
            "corrupt threat draft record",
            status_code=500,
        ) from None


def _save_draft_unlocked(root: Path, draft: ThreatDraftV1) -> None:
    path = _draft_path(root, draft.draft_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, draft.model_dump(mode="json", by_alias=True))


def _remove_draft_file(root: Path, draft_id: str) -> None:
    path = _draft_path(root, draft_id)
    path.unlink(missing_ok=True)


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
    with _store_lock(root):
        draft_written = False
        try:
            _save_draft_unlocked(root, draft)
            draft_written = True
            index = _load_index(root)
            if draft.draft_id in index.draft_ids:
                raise ThreatDraftStoreError(
                    "draft_id collision",
                    status_code=500,
                )
            index.draft_ids.append(draft.draft_id)
            _save_index(root, index)
        except Exception:
            if draft_written:
                _remove_draft_file(root, draft.draft_id)
            raise
    return draft


def get_threat_draft(root: Path, draft_id: str) -> ThreatDraftV1:
    cleaned = _validated_draft_id(draft_id)
    with _store_lock(root):
        return _load_draft_unlocked(root, cleaned)


def list_threat_drafts(
    root: Path,
    *,
    campaign_id: str | None = None,
    world_id: str | None = None,
    limit: int = DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> tuple[list[ThreatDraftSummaryV1], int]:
    if limit < 1 or limit > MAX_LIST_LIMIT:
        raise ThreatDraftStoreError(
            f"limit must be between 1 and {MAX_LIST_LIMIT}",
            status_code=422,
        )
    if offset < 0:
        raise ThreatDraftStoreError("offset must be >= 0", status_code=422)

    with _store_lock(root):
        index = _load_index(root)
        summaries: list[ThreatDraftSummaryV1] = []
        for draft_id in index.draft_ids:
            try:
                draft = _load_draft_unlocked(root, draft_id)
            except ThreatDraftStoreError as exc:
                if exc.status_code == 404:
                    raise ThreatDraftStoreError(
                        "threat draft index integrity failure",
                        status_code=500,
                    ) from None
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
        total = len(summaries)
        page = summaries[offset : offset + limit]
        return page, total


def update_threat_draft(
    root: Path,
    draft_id: str,
    request: UpdateThreatDraftRequest,
) -> ThreatDraftV1:
    cleaned = _validated_draft_id(draft_id)
    with _store_lock(root):
        current = _load_draft_unlocked(root, cleaned)
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
        _save_draft_unlocked(root, updated)
        return updated
