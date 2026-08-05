"""SBW09a: durable no-write Threat publication-operation orchestration.

Storage:
    out/threat_publication_operations/<draft_id>/ledger.json
    out/threat_publication_operations/<draft_id>/.publication.lock

Lock order (never acquire in the reverse direction):

    publication ledger lock -> ThreatDraft store read -> trusted World Graph head read

No path in this module acquires the publication lock while already holding
the ThreatDraft store lock. ``get_threat_draft`` acquires and releases its own
store lock internally; this module always calls it only while already holding
the publication lock for the same draft, never the other way around.

This module never mutates ThreatDraft, accepted mechanics, DungeonMind, or the
World Graph. The only durable write this module performs is an atomic replace
of one draft-scoped ``ThreatPublicationLedgerV1``.
"""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Literal

import graph_memory.kernel as kernel

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.models.threat_publication import (
    LEDGER_SCHEMA,
    MAX_PUBLICATION_OPERATIONS_PER_DRAFT,
    BeginThreatPublicationOperationRequestV1,
    CancelThreatPublicationOperationRequestV1,
    RetryThreatPublicationOperationRequestV1,
    ThreatPublicationLedgerV1,
    ThreatPublicationOperationResponseV1,
    ThreatPublicationOperationV1,
    ThreatPublicationResultLabel,
    begin_request_digest,
    build_source_snapshot,
    retry_request_digest,
    source_digest_for_snapshot,
    validate_publication_operation_id,
)
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    get_threat_draft,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_PUBLICATION_REL = "out/threat_publication_operations"
LEDGER_NAME = "ledger.json"
LOCK_NAME = ".publication.lock"


@dataclass(frozen=True)
class PublicationOperationOutcome:
    """Result of a service call plus whether it minted a brand-new operation.

    ``created`` is only ever true for begin/retry paths that appended a new
    ``ready`` operation to the ledger; it drives the 201-vs-200 HTTP mapping
    at the route layer (handoff §9.9). It is never true for read/refresh/cancel.
    """

    response: ThreatPublicationOperationResponseV1
    created: bool = False


class ThreatPublicationStorageError(Exception):
    """Internal signal for storage unavailability vs. corrupt/impossible state."""

    def __init__(self, message: str, *, kind: Literal["unavailable", "integrity"]) -> None:
        super().__init__(message)
        self.kind = kind


class GraphHeadUnavailable(Exception):
    """Trusted World Graph head could not be read."""


_STATE_LABELS: dict[str, ThreatPublicationResultLabel] = {
    "ready": "publication_ready",
    "stale": "publication_stale",
    "cancelled": "publication_cancelled",
    "superseded": "publication_superseded",
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def publication_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_PUBLICATION_REL


def _storage_unavailable() -> ThreatPublicationStorageError:
    return ThreatPublicationStorageError(
        "publication ledger storage unavailable", kind="unavailable"
    )


def _integrity_failure(message: str) -> ThreatPublicationStorageError:
    return ThreatPublicationStorageError(message, kind="integrity")


def _draft_directory(root: Path, draft_id: str) -> Path:
    safe = require_draft_id(draft_id)
    store_root = publication_root(root).resolve()
    directory = (store_root / safe).resolve()
    if directory.parent != store_root:
        raise _integrity_failure("publication path escape")
    return directory


def _ledger_path(root: Path, draft_id: str) -> Path:
    return _draft_directory(root, draft_id) / LEDGER_NAME


@contextmanager
def _publication_lock(root: Path, draft_id: str) -> Iterator[None]:
    """Draft-scoped exclusive lock. Acquire before any ThreatDraft/graph read."""
    directory = _draft_directory(root, draft_id)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / LOCK_NAME
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


def _empty_ledger(draft_id: str) -> ThreatPublicationLedgerV1:
    return ThreatPublicationLedgerV1(draft_id=draft_id, active_operation_id=None, operations=[])


def _load_ledger_unlocked(root: Path, draft_id: str) -> ThreatPublicationLedgerV1:
    safe = require_draft_id(draft_id)
    path = _ledger_path(root, safe)
    if not path.is_file():
        return _empty_ledger(safe)
    try:
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        raise _integrity_failure("corrupt publication ledger") from None
    if payload.get("schema") != LEDGER_SCHEMA:
        raise _integrity_failure("corrupt publication ledger")
    try:
        ledger = ThreatPublicationLedgerV1.model_validate(payload)
    except Exception:
        raise _integrity_failure("corrupt publication ledger") from None
    if ledger.draft_id != safe:
        raise _integrity_failure("publication ledger identity mismatch")
    return ledger


def _save_ledger_unlocked(root: Path, ledger: ThreatPublicationLedgerV1) -> None:
    path = _ledger_path(root, ledger.draft_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, ledger.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None


def _revalidate_operation(op: ThreatPublicationOperationV1) -> ThreatPublicationOperationV1:
    return ThreatPublicationOperationV1.model_validate(op.model_dump(mode="json", by_alias=True))


def _revalidate_ledger(ledger: ThreatPublicationLedgerV1) -> ThreatPublicationLedgerV1:
    return ThreatPublicationLedgerV1.model_validate(ledger.model_dump(mode="json", by_alias=True))


def _find_operation(
    ledger: ThreatPublicationLedgerV1, operation_id: str
) -> ThreatPublicationOperationV1 | None:
    for op in ledger.operations:
        if op.operation_id == operation_id:
            return op
    return None


def _replace_operation(
    ledger: ThreatPublicationLedgerV1, updated: ThreatPublicationOperationV1
) -> list[ThreatPublicationOperationV1]:
    return [updated if op.operation_id == updated.operation_id else op for op in ledger.operations]


def _state_to_label(op: ThreatPublicationOperationV1) -> ThreatPublicationResultLabel:
    return _STATE_LABELS[op.state]


def _response(
    draft_id: str,
    result_label: ThreatPublicationResultLabel,
    *,
    operation: ThreatPublicationOperationV1 | None = None,
    message: str | None = None,
) -> ThreatPublicationOperationResponseV1:
    return ThreatPublicationOperationResponseV1(
        draft_id=draft_id,
        result_label=result_label,
        operation=operation,
        message=message,
    )


def _outcome_from_storage_error(
    draft_id: str, exc: ThreatPublicationStorageError
) -> PublicationOperationOutcome:
    label: ThreatPublicationResultLabel = (
        "publication_integrity_failure" if exc.kind == "integrity" else "publication_storage_unavailable"
    )
    return PublicationOperationOutcome(_response(draft_id, label, message=str(exc)), created=False)


def _read_graph_head(root: Path, world_id: str) -> str:
    """Trusted current World Graph head for ``world_id``; never a fallback parent."""
    try:
        head = kernel.open_world_graph_head(world_graph_root(), world_id)
    except kernel.WorldGraphNotFoundError as exc:
        raise GraphHeadUnavailable(str(exc)) from exc
    except OSError as exc:
        raise GraphHeadUnavailable(str(exc)) from exc
    except Exception as exc:
        # The canonical loader owns JSON decoding and WorldGraphHead validation.
        # Convert every parser/model failure into the dependency failure contract;
        # never let corrupt head bytes escape the typed publication response.
        raise GraphHeadUnavailable(str(exc)) from exc
    return head.head_revision_id


def _draft_outcome_from_store_error(
    draft_id: str, exc: ThreatDraftStoreError
) -> PublicationOperationOutcome:
    if exc.status_code == 404:
        return PublicationOperationOutcome(
            _response(draft_id, "publication_not_found", message=str(exc)), created=False
        )
    return PublicationOperationOutcome(
        _response(draft_id, "publication_draft_unavailable", message=str(exc)), created=False
    )


def _eligible_draft_or_response(
    root: Path, draft_id: str, expected_draft_version: int
) -> tuple[object, PublicationOperationOutcome | None]:
    """Load the committed draft and validate begin/retry source eligibility.

    Returns ``(draft, None)`` on success or ``(None, outcome)`` carrying the
    typed rejection response. No ledger mutation happens on rejection.
    """
    try:
        draft = get_threat_draft(root, draft_id)
    except ThreatDraftStoreError as exc:
        return None, _draft_outcome_from_store_error(draft_id, exc)

    if draft.version != expected_draft_version:
        return None, PublicationOperationOutcome(
            _response(
                draft_id,
                "publication_source_mismatch",
                message="expected_draft_version does not match the committed draft",
            ),
            created=False,
        )
    if draft.workflow_state != "mechanics_saved" or draft.accepted_mechanics_ref is None:
        return None, PublicationOperationOutcome(
            _response(
                draft_id,
                "publication_source_mismatch",
                message="draft is not mechanics_saved with an accepted mechanics ref",
            ),
            created=False,
        )
    try:
        draft.accepted_mechanics_ref.to_mechanics_locator()
    except Exception:
        return None, PublicationOperationOutcome(
            _response(
                draft_id,
                "publication_source_mismatch",
                message="accepted_mechanics_ref does not validate to an exact locator",
            ),
            created=False,
        )
    return draft, None


def begin_publication_operation(
    root: Path,
    draft_id: str,
    request: BeginThreatPublicationOperationRequestV1,
) -> PublicationOperationOutcome:
    """Handoff §10 Begin. Exact replay is checked before any draft/graph read."""
    safe_draft = require_draft_id(draft_id)
    computed_digest = begin_request_digest(safe_draft, request)

    with _publication_lock(root, safe_draft):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        existing = _find_operation(ledger, request.operation_id)
        if existing is not None:
            if existing.request_digest == computed_digest:
                return PublicationOperationOutcome(
                    _response(safe_draft, _state_to_label(existing), operation=existing),
                    created=False,
                )
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_input_conflict",
                    message="operation_id reused with a changed request",
                ),
                created=False,
            )

        if ledger.active_operation_id is not None:
            active = _find_operation(ledger, ledger.active_operation_id)
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_busy",
                    operation=active,
                    message="another publication operation is active for this draft",
                ),
                created=False,
            )

        if len(ledger.operations) >= MAX_PUBLICATION_OPERATIONS_PER_DRAFT:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_history_full",
                    message="publication operation history bound reached",
                ),
                created=False,
            )

        draft, rejection = _eligible_draft_or_response(
            root, safe_draft, request.expected_draft_version
        )
        if rejection is not None:
            return rejection
        assert draft is not None

        try:
            observed_head = _read_graph_head(root, draft.world_id)
        except GraphHeadUnavailable as exc:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_graph_unavailable", message=str(exc)),
                created=False,
            )

        if observed_head != request.expected_parent_revision_id:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_parent_mismatch",
                    message="expected_parent_revision_id does not match the observed World Graph head",
                ),
                created=False,
            )

        snapshot = build_source_snapshot(draft)
        digest = source_digest_for_snapshot(snapshot)
        now = _utc_now_iso()
        new_op = ThreatPublicationOperationV1(
            operation_id=request.operation_id,
            request_digest=computed_digest,
            source_snapshot=snapshot,
            source_digest=digest,
            expected_parent_revision_id=request.expected_parent_revision_id,
            state="ready",
            stale_reasons=[],
            operator_note=request.operator_note,
            created_by=request.actor,
            created_at=now,
            updated_at=now,
        )
        new_ledger = _revalidate_ledger(
            ledger.model_copy(
                update={
                    "active_operation_id": new_op.operation_id,
                    "operations": [*ledger.operations, new_op],
                }
            )
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        return PublicationOperationOutcome(
            _response(safe_draft, "publication_ready", operation=new_op), created=True
        )


def read_publication_operation(
    root: Path, draft_id: str, operation_id: str
) -> PublicationOperationOutcome:
    """Handoff §10 Read. No draft or graph read; no freshness transition."""
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)

    with _publication_lock(root, safe_draft):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        existing = _find_operation(ledger, safe_op)
        if existing is None:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_not_found", message="publication operation not found"),
                created=False,
            )
        return PublicationOperationOutcome(
            _response(safe_draft, _state_to_label(existing), operation=existing), created=False
        )


def refresh_publication_operation(
    root: Path, draft_id: str, operation_id: str
) -> PublicationOperationOutcome:
    """Handoff §10 Refresh. Only a ``ready`` operation is re-checked."""
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)

    with _publication_lock(root, safe_draft):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        existing = _find_operation(ledger, safe_op)
        if existing is None:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_not_found", message="publication operation not found"),
                created=False,
            )
        if existing.state != "ready":
            return PublicationOperationOutcome(
                _response(safe_draft, _state_to_label(existing), operation=existing), created=False
            )

        try:
            draft = get_threat_draft(root, safe_draft)
        except ThreatDraftStoreError as exc:
            return _draft_outcome_from_store_error(safe_draft, exc)

        try:
            observed_head = _read_graph_head(root, draft.world_id)
        except GraphHeadUnavailable as exc:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_graph_unavailable", message=str(exc)),
                created=False,
            )

        reasons: list[str] = []
        if draft.version != existing.source_snapshot.draft_version:
            reasons.append("draft_version_changed")
        if draft.world_id != existing.source_snapshot.world_id or (
            draft.campaign_id != existing.source_snapshot.campaign_id
        ):
            reasons.append("world_or_campaign_changed")
        if (
            draft.accepted_mechanics_ref is None
            or draft.accepted_mechanics_ref.model_dump(mode="json")
            != existing.source_snapshot.accepted_mechanics_ref.model_dump(mode="json")
        ):
            reasons.append("accepted_mechanics_changed")

        current_digest: str | None = None
        if draft.workflow_state == "mechanics_saved" and draft.accepted_mechanics_ref is not None:
            try:
                current_snapshot = build_source_snapshot(draft)
                current_digest = source_digest_for_snapshot(current_snapshot)
            except Exception:
                current_digest = None
        if current_digest is None or current_digest != existing.source_digest:
            if "source_digest_changed" not in reasons:
                reasons.append("source_digest_changed")

        if observed_head != existing.expected_parent_revision_id:
            reasons.append("graph_parent_changed")

        if not reasons:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_ready", operation=existing), created=False
            )

        updated_op = _revalidate_operation(
            existing.model_copy(
                update={
                    "state": "stale",
                    "stale_reasons": reasons,
                    "updated_at": _utc_now_iso(),
                }
            )
        )
        new_ledger = _revalidate_ledger(
            ledger.model_copy(update={"operations": _replace_operation(ledger, updated_op)})
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        return PublicationOperationOutcome(
            _response(safe_draft, "publication_stale", operation=updated_op), created=False
        )


def cancel_publication_operation(
    root: Path,
    draft_id: str,
    operation_id: str,
    request: CancelThreatPublicationOperationRequestV1,
) -> PublicationOperationOutcome:
    """Handoff §10 Cancel. Terminal and idempotent; no external dependency read."""
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)

    with _publication_lock(root, safe_draft):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        existing = _find_operation(ledger, safe_op)
        if existing is None:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_not_found", message="publication operation not found"),
                created=False,
            )

        if existing.state == "cancelled":
            same_request = (
                existing.cancelled_by == request.actor
                and (existing.cancellation_note or None) == (request.note or None)
            )
            if same_request:
                return PublicationOperationOutcome(
                    _response(safe_draft, "publication_cancelled", operation=existing), created=False
                )
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_input_conflict",
                    message="cancel request does not match the existing cancellation",
                ),
                created=False,
            )

        if existing.state == "superseded":
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_invalid_state",
                    message="operation is already superseded",
                ),
                created=False,
            )

        updated_op = _revalidate_operation(
            existing.model_copy(
                update={
                    "state": "cancelled",
                    "cancelled_by": request.actor,
                    "cancellation_note": request.note,
                    "updated_at": _utc_now_iso(),
                }
            )
        )
        new_active = ledger.active_operation_id
        if new_active == safe_op:
            new_active = None
        new_ledger = _revalidate_ledger(
            ledger.model_copy(
                update={
                    "active_operation_id": new_active,
                    "operations": _replace_operation(ledger, updated_op),
                }
            )
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        return PublicationOperationOutcome(
            _response(safe_draft, "publication_cancelled", operation=updated_op), created=False
        )


def retry_publication_operation(
    root: Path,
    draft_id: str,
    operation_id: str,
    request: RetryThreatPublicationOperationRequestV1,
) -> PublicationOperationOutcome:
    """Handoff §10 Retry. Only the current stale active operation may retry."""
    safe_draft = require_draft_id(draft_id)
    safe_old_op = validate_publication_operation_id(operation_id)
    computed_digest = retry_request_digest(safe_draft, safe_old_op, request)

    with _publication_lock(root, safe_draft):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        old = _find_operation(ledger, safe_old_op)
        if old is None:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_not_found", message="publication operation not found"),
                created=False,
            )

        existing_new = _find_operation(ledger, request.new_operation_id)
        if existing_new is not None:
            if (
                existing_new.request_digest == computed_digest
                and existing_new.supersedes_operation_id == safe_old_op
            ):
                return PublicationOperationOutcome(
                    _response(safe_draft, _state_to_label(existing_new), operation=existing_new),
                    created=False,
                )
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_input_conflict",
                    message="new_operation_id reused with a changed request",
                ),
                created=False,
            )

        if request.new_operation_id == safe_old_op:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_invalid_state",
                    message="new_operation_id must differ from operation_id",
                ),
                created=False,
            )

        if old.state != "stale" or ledger.active_operation_id != safe_old_op:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_invalid_state",
                    message="only the current stale active operation may retry",
                ),
                created=False,
            )

        if len(ledger.operations) >= MAX_PUBLICATION_OPERATIONS_PER_DRAFT:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_history_full",
                    message="publication operation history bound reached",
                ),
                created=False,
            )

        try:
            draft = get_threat_draft(root, safe_draft)
        except ThreatDraftStoreError as exc:
            return _draft_outcome_from_store_error(safe_draft, exc)

        if draft.workflow_state != "mechanics_saved" or draft.accepted_mechanics_ref is None:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_source_mismatch",
                    message="source has drifted; begin a new publication intent",
                ),
                created=False,
            )
        try:
            current_snapshot = build_source_snapshot(draft)
            current_digest = source_digest_for_snapshot(current_snapshot)
        except Exception:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_source_mismatch",
                    message="source has drifted; begin a new publication intent",
                ),
                created=False,
            )
        if current_digest != old.source_digest:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_source_mismatch",
                    message="source has drifted since staleness; begin a new publication intent",
                ),
                created=False,
            )

        try:
            observed_head = _read_graph_head(root, draft.world_id)
        except GraphHeadUnavailable as exc:
            return PublicationOperationOutcome(
                _response(safe_draft, "publication_graph_unavailable", message=str(exc)),
                created=False,
            )
        if observed_head != request.expected_parent_revision_id:
            return PublicationOperationOutcome(
                _response(
                    safe_draft,
                    "publication_parent_mismatch",
                    message="expected_parent_revision_id does not match the observed World Graph head",
                ),
                created=False,
            )

        now = _utc_now_iso()
        new_op = ThreatPublicationOperationV1(
            operation_id=request.new_operation_id,
            request_digest=computed_digest,
            source_snapshot=old.source_snapshot,
            source_digest=old.source_digest,
            expected_parent_revision_id=request.expected_parent_revision_id,
            state="ready",
            stale_reasons=[],
            supersedes_operation_id=safe_old_op,
            operator_note=request.operator_note,
            created_by=request.actor,
            created_at=now,
            updated_at=now,
        )
        superseded_old = _revalidate_operation(
            old.model_copy(
                update={
                    "state": "superseded",
                    "superseded_by_operation_id": new_op.operation_id,
                    "updated_at": now,
                }
            )
        )
        new_ops = _replace_operation(ledger, superseded_old)
        new_ops.append(new_op)
        new_ledger = _revalidate_ledger(
            ledger.model_copy(
                update={"active_operation_id": new_op.operation_id, "operations": new_ops}
            )
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationStorageError as exc:
            return _outcome_from_storage_error(safe_draft, exc)

        return PublicationOperationOutcome(
            _response(safe_draft, "publication_ready", operation=new_op), created=True
        )
