"""Atomic durable ThreatDraft repository with optimistic concurrency."""
from __future__ import annotations

import fcntl
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Literal

from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.models.threat_draft import (
    DEFAULT_LIST_LIMIT,
    MAX_CANDIDATE_REFS,
    MAX_LIST_LIMIT,
    CreateThreatDraftRequest,
    RequestedSourceStatusTransitionV1,
    ThreatDraftCandidateRefV1,
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


def _storage_unavailable() -> ThreatDraftStoreError:
    return ThreatDraftStoreError(
        "threat draft storage unavailable",
        status_code=500,
    )


@contextmanager
def _store_lock(root: Path) -> Iterator[None]:
    """Exclusive lock covering index and draft mutation for one store root.

    Lock orders involving this lock:
    - Acceptance: acceptance journal lock → this lock.
    - New generation admission: this lock → generation reconciliation lock.

    Do not acquire the acceptance journal lock while holding this lock.
    Callers may nest the generation reconciliation lock while holding this lock
    only for brand-new generation admission (claim must complete before release).
    """
    try:
        store_root = threat_drafts_root(root)
        store_root.mkdir(parents=True, exist_ok=True)
        lock_path = store_root / LOCK_NAME
        lock_file = open(lock_path, "a+", encoding="utf-8")
    except OSError:
        raise _storage_unavailable() from None

    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except OSError:
            raise _storage_unavailable() from None
        try:
            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        lock_file.close()


def _validated_draft_id(draft_id: str) -> str:
    try:
        return require_draft_id(draft_id)
    except ValueError:
        raise ThreatDraftStoreError("invalid draft_id", status_code=422) from None


def _draft_path(root: Path, draft_id: str) -> Path:
    """Resolve a draft path that is always under the store directory."""
    cleaned = _validated_draft_id(draft_id)
    try:
        store_root = threat_drafts_root(root).resolve()
        path = (store_root / f"{cleaned}.json").resolve()
    except OSError:
        raise _storage_unavailable() from None
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
    try:
        if not path.is_file():
            return ThreatDraftIndexV1()
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    try:
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, index.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None


def _require_committed_draft_id(root: Path, draft_id: str) -> str:
    """Index membership is the commit authority for durable reads/updates."""
    cleaned = _validated_draft_id(draft_id)
    index = _load_index(root)
    if cleaned not in index.draft_ids:
        raise ThreatDraftStoreError("threat draft not found", status_code=404)
    return cleaned


def _load_draft_unlocked(root: Path, draft_id: str) -> ThreatDraftV1:
    """Load one draft file and require embedded identity to match the requested ID."""
    cleaned = _validated_draft_id(draft_id)
    path = _draft_path(root, cleaned)
    try:
        if not path.is_file():
            raise ThreatDraftStoreError("threat draft not found", status_code=404)
        payload = load_json(path)
    except ThreatDraftStoreError:
        raise
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        # JSONDecodeError / TypeError / other parse failures must fail closed
        # as a typed store error so recovery can retain journal authority.
        raise ThreatDraftStoreError(
            "corrupt threat draft record",
            status_code=500,
        ) from None
    try:
        draft = ThreatDraftV1.model_validate(payload)
    except ThreatDraftStoreError:
        raise
    except Exception:
        raise ThreatDraftStoreError(
            "corrupt threat draft record",
            status_code=500,
        ) from None
    if draft.draft_id != cleaned:
        raise ThreatDraftStoreError(
            "threat draft identity mismatch",
            status_code=500,
        )
    return draft


def _save_draft_unlocked(root: Path, draft: ThreatDraftV1, *, as_draft_id: str) -> None:
    """Persist a draft only under the requested/committed ID path."""
    cleaned = _validated_draft_id(as_draft_id)
    if draft.draft_id != cleaned:
        raise ThreatDraftStoreError(
            "threat draft identity mismatch",
            status_code=500,
        )
    path = _draft_path(root, cleaned)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, draft.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None


def _remove_draft_file(root: Path, draft_id: str) -> None:
    path = _draft_path(root, draft_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        raise _storage_unavailable() from None


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
        index = _load_index(root)
        if draft.draft_id in index.draft_ids:
            raise ThreatDraftStoreError(
                "draft_id collision",
                status_code=500,
            )
        draft_written = False
        try:
            _save_draft_unlocked(root, draft, as_draft_id=draft.draft_id)
            draft_written = True
            index.draft_ids.append(draft.draft_id)
            _save_index(root, index)
        except ThreatDraftStoreError:
            if draft_written:
                try:
                    _remove_draft_file(root, draft.draft_id)
                except ThreatDraftStoreError:
                    pass
            raise
    return draft


def get_threat_draft(root: Path, draft_id: str) -> ThreatDraftV1:
    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        return _load_draft_unlocked(root, committed_id)


def find_threat_draft_for_candidate(
    root: Path,
    candidate_id: str,
) -> tuple[ThreatDraftV1, ThreatDraftCandidateRefV1] | None:
    """Reverse-lookup the ThreatDraft that lists this candidate in candidate_refs."""
    cleaned = (candidate_id or "").strip()
    if not cleaned:
        return None
    with _store_lock(root):
        index = _load_index(root)
        for draft_id in index.draft_ids:
            try:
                draft = _load_draft_unlocked(root, draft_id)
            except ThreatDraftStoreError:
                continue
            for ref in draft.candidate_refs:
                if ref.candidate_id == cleaned:
                    return draft, ref
    return None


def read_committed_draft_version(root: Path, draft_id: str) -> int:
    """Read a committed draft's version under the ThreatDraft store lock.

    Callers that already hold the acceptance journal lock may nest this call
    (lock order: acceptance journal → ThreatDraft store). Do not call this
    while holding the generation reconciliation lock.
    """
    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        return _load_draft_unlocked(root, committed_id).version


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
    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        current = _load_draft_unlocked(root, committed_id)
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
        _save_draft_unlocked(root, updated, as_draft_id=committed_id)
        return updated


def append_candidate_ref(
    root: Path,
    *,
    draft_id: str,
    expected_version: int,
    candidate_ref: ThreatDraftCandidateRefV1,
    workflow_state: Literal["drafting", "candidate_ready"] | None = "candidate_ready",
) -> ThreatDraftV1:
    """Append candidate workflow evidence for a committed draft version.

    Authored concept fields and draft version are unchanged; only candidate_refs,
    optional workflow_state, and updated_at may change.

    Historical lineage is preserved: a ref generated from an earlier draft version
    may still be attached after the draft advances.
    """
    if candidate_ref.generated_from_draft_version != expected_version:
        raise ThreatDraftStoreError(
            "candidate ref source version mismatch",
            status_code=422,
        )

    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        current = _load_draft_unlocked(root, committed_id)
        if expected_version > current.version:
            raise ThreatDraftStoreError(
                "expected_version mismatch",
                status_code=409,
            )

        refs = list(current.candidate_refs)
        existing = next(
            (ref for ref in refs if ref.candidate_id == candidate_ref.candidate_id),
            None,
        )
        if existing is not None:
            if existing.model_dump(mode="json") != candidate_ref.model_dump(mode="json"):
                raise ThreatDraftStoreError(
                    "candidate ref identity conflict",
                    status_code=409,
                )
            return current

        if len(refs) >= MAX_CANDIDATE_REFS:
            raise ThreatDraftStoreError(
                "candidate_refs limit exceeded",
                status_code=422,
            )
        refs.append(candidate_ref)
        updates: dict = {
            "candidate_refs": refs,
            "updated_at": _utc_now_iso(),
        }
        # Saved mechanics are monotonic in SBW07: never regress workflow_state
        # from mechanics_saved back to candidate_ready/drafting.
        if current.workflow_state == "mechanics_saved":
            updates["workflow_state"] = "mechanics_saved"
        elif workflow_state is not None:
            updates["workflow_state"] = workflow_state
        # Validate the full record before write so an over-limit or invalid
        # payload cannot be persisted and fail on reload.
        updated = ThreatDraftV1.model_validate(
            current.model_copy(update=updates).model_dump(mode="json", by_alias=True)
        )
        _save_draft_unlocked(root, updated, as_draft_id=committed_id)
        return updated


_TERMINAL_CANDIDATE_REF_STATUS = frozenset(
    {"superseded", "rejected", "expired", "accepted_source"}
)


def _ref_json(ref: ThreatDraftCandidateRefV1) -> dict:
    return ref.model_dump(mode="json")


def _validate_source_status_transition(
    draft: ThreatDraftV1,
    refs: list[ThreatDraftCandidateRefV1],
    transition: RequestedSourceStatusTransitionV1,
) -> None:
    source = next(
        (ref for ref in refs if ref.candidate_id == transition.source_candidate_id),
        None,
    )
    if source is None:
        raise ThreatDraftStoreError(
            "source candidate ref not found",
            status_code=409,
        )
    current_status = source.status
    target = transition.to_status
    if current_status == target:
        return
    if current_status in _TERMINAL_CANDIDATE_REF_STATUS:
        raise ThreatDraftStoreError(
            "source candidate status transition forbidden",
            status_code=409,
        )
    if current_status != "active":
        raise ThreatDraftStoreError(
            "source candidate status transition forbidden",
            status_code=409,
        )
    if target == "expired" and not transition.expiry_proven:
        raise ThreatDraftStoreError(
            "expired transition requires expiry proof",
            status_code=409,
        )
    if target == "accepted_source":
        accepted = draft.accepted_mechanics_ref
        if accepted is None or accepted.accepted_from_candidate_id != transition.source_candidate_id:
            raise ThreatDraftStoreError(
                "accepted_source transition requires accepted mechanics proof",
                status_code=409,
            )


def _apply_source_status_transition(
    refs: list[ThreatDraftCandidateRefV1],
    transition: RequestedSourceStatusTransitionV1,
) -> tuple[list[ThreatDraftCandidateRefV1], bool]:
    """Return updated refs and whether any status changed."""
    updated_refs: list[ThreatDraftCandidateRefV1] = []
    changed = False
    for ref in refs:
        if ref.candidate_id != transition.source_candidate_id:
            updated_refs.append(ref)
            continue
        if ref.status == transition.to_status:
            updated_refs.append(ref)
            continue
        updated_refs.append(ref.model_copy(update={"status": transition.to_status}))
        changed = True
    return updated_refs, changed


def _source_transition_satisfied(
    refs: list[ThreatDraftCandidateRefV1],
    transition: RequestedSourceStatusTransitionV1 | None,
) -> bool:
    if transition is None:
        return True
    source = next(
        (ref for ref in refs if ref.candidate_id == transition.source_candidate_id),
        None,
    )
    if source is None:
        return False
    return source.status == transition.to_status


def reconcile_revise_candidate_ref(
    root: Path,
    *,
    draft_id: str,
    expected_version: int,
    candidate_ref: ThreatDraftCandidateRefV1,
    requested_source_transition: RequestedSourceStatusTransitionV1 | None = None,
) -> ThreatDraftV1:
    """Atomic revise ref attach with required lineage and optional source transition."""
    if candidate_ref.lineage is None:
        raise ThreatDraftStoreError(
            "revise candidate ref requires lineage",
            status_code=422,
        )
    if candidate_ref.request_id != candidate_ref.lineage.revise_request_id:
        raise ThreatDraftStoreError(
            "candidate ref request_id must match lineage.revise_request_id",
            status_code=422,
        )

    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        current = _load_draft_unlocked(root, committed_id)
        if current.version != expected_version:
            raise ThreatDraftStoreError(
                "expected_version mismatch",
                status_code=409,
            )

        refs = list(current.candidate_refs)
        incoming_json = _ref_json(candidate_ref)
        existing_by_cid = next(
            (ref for ref in refs if ref.candidate_id == candidate_ref.candidate_id),
            None,
        )
        existing_by_rid = next(
            (ref for ref in refs if ref.request_id == candidate_ref.request_id),
            None,
        )

        if existing_by_cid is not None:
            if existing_by_cid.request_id != candidate_ref.request_id:
                raise ThreatDraftStoreError(
                    "candidate ref identity conflict",
                    status_code=409,
                )
            if _ref_json(existing_by_cid) != incoming_json:
                raise ThreatDraftStoreError(
                    "candidate ref identity conflict",
                    status_code=409,
                )
        if existing_by_rid is not None:
            if existing_by_rid.candidate_id != candidate_ref.candidate_id:
                raise ThreatDraftStoreError(
                    "candidate ref identity conflict",
                    status_code=409,
                )

        idempotent_ref_present = existing_by_cid is not None and _ref_json(
            existing_by_cid
        ) == incoming_json

        working_refs = refs
        if requested_source_transition is not None:
            _validate_source_status_transition(
                current, working_refs, requested_source_transition
            )

        transition_needed = (
            requested_source_transition is not None
            and not _source_transition_satisfied(working_refs, requested_source_transition)
        )

        if idempotent_ref_present:
            if not transition_needed:
                return current
            working_refs, _ = _apply_source_status_transition(
                working_refs, requested_source_transition
            )
            updates: dict = {
                "candidate_refs": working_refs,
                "version": current.version + 1,
                "updated_at": _utc_now_iso(),
            }
            updated = ThreatDraftV1.model_validate(
                current.model_copy(update=updates).model_dump(mode="json", by_alias=True)
            )
            _save_draft_unlocked(root, updated, as_draft_id=committed_id)
            return updated

        if len(refs) >= MAX_CANDIDATE_REFS:
            raise ThreatDraftStoreError(
                "candidate_refs limit exceeded",
                status_code=422,
            )

        working_refs = list(refs)
        working_refs.append(candidate_ref)
        if requested_source_transition is not None:
            working_refs, _ = _apply_source_status_transition(
                working_refs, requested_source_transition
            )

        updates = {
            "candidate_refs": working_refs,
            "version": current.version + 1,
            "updated_at": _utc_now_iso(),
        }
        if current.workflow_state == "mechanics_saved":
            updates["workflow_state"] = "mechanics_saved"
        elif current.workflow_state == "drafting":
            updates["workflow_state"] = "candidate_ready"

        updated = ThreatDraftV1.model_validate(
            current.model_copy(update=updates).model_dump(mode="json", by_alias=True)
        )
        _save_draft_unlocked(root, updated, as_draft_id=committed_id)
        return updated


class AcceptedMechanicsRefConflictError(ThreatDraftStoreError):
    """Draft already holds a different accepted mechanics locator."""

    def __init__(self) -> None:
        super().__init__(
            "accepted mechanics ref conflict",
            status_code=409,
        )


def attach_accepted_mechanics_ref(
    root: Path,
    *,
    draft_id: str,
    expected_version: int,
    locator: AcceptedMechanicsRefV1,
) -> ThreatDraftV1:
    """Phase 1 ThreatDraft attach under store lock + version CAS.

    Does not mutate the acceptance journal.
    """
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        same_mechanics_locator,
    )

    with _store_lock(root):
        committed_id = _require_committed_draft_id(root, draft_id)
        current = _load_draft_unlocked(root, committed_id)
        if current.version != expected_version:
            raise ThreatDraftStoreError("expected_version mismatch", status_code=409)

        existing = current.accepted_mechanics_ref
        if existing is None:
            updated = current.model_copy(
                update={
                    "version": current.version + 1,
                    "accepted_mechanics_ref": locator,
                    "workflow_state": "mechanics_saved",
                    "updated_at": _utc_now_iso(),
                }
            )
            _save_draft_unlocked(root, updated, as_draft_id=committed_id)
            return updated

        if same_mechanics_locator(
            existing.to_mechanics_locator(), locator.to_mechanics_locator()
        ):
            if current.workflow_state == "mechanics_saved":
                return current
            updated = current.model_copy(
                update={
                    "version": current.version + 1,
                    "workflow_state": "mechanics_saved",
                    "updated_at": _utc_now_iso(),
                }
            )
            _save_draft_unlocked(root, updated, as_draft_id=committed_id)
            return updated

        raise AcceptedMechanicsRefConflictError()
