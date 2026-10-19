"""Durable reservation and immutable terminal receipt for Play scene edits."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from psycopg.types.json import Jsonb

from application_state.agent_conversation.service import _ready_dsn
from application_state.agent_conversation.types import PlayRunTurnContextReceiptV2
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play_scene_edit.types import MAX_CONTEXT_BYTES, SceneEditProposalRecord, canonical_json_bytes, validate_failure_code, validate_result
from application_state.unit_of_work import unit_of_work


def _world(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 128:
        raise ApplicationStateValidationError("world_id must be non-empty and canonical")
    return value


def _load(row) -> SceneEditProposalRecord:
    return SceneEditProposalRecord.model_validate({
        "world_id": row[0], "run_id": row[1], "proposal_id": row[2],
        "request_sha256": row[3], "request": row[4], "context_receipt": row[5],
        "status": row[6], "result": row[7], "failure_code": row[8],
        "created_at": row[9], "updated_at": row[10],
    })


_SELECT_COLUMNS = "world_id,run_id,proposal_id,request_sha256,request,context_receipt,status,result,failure_code,created_at,updated_at"


def _fingerprint(request: dict, receipt: PlayRunTurnContextReceiptV2) -> str:
    try:
        raw_request = canonical_json_bytes(request)
        raw_receipt = canonical_json_bytes(receipt.model_dump(mode="json", by_alias=True))
        payload = canonical_json_bytes({"request": request, "context_receipt": receipt.model_dump(mode="json", by_alias=True)})
    except (TypeError, ValueError) as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    if len(raw_request) > MAX_CONTEXT_BYTES or len(raw_receipt) > MAX_CONTEXT_BYTES:
        raise ApplicationStateValidationError("proposal request or context receipt exceeds 256 KiB")
    return hashlib.sha256(payload).hexdigest()


class PlaySceneEditProposalService:
    def reserve(self, *, world_id: str, run_id: UUID, proposal_id: UUID, request: dict,
                context_receipt: PlayRunTurnContextReceiptV2) -> tuple[SceneEditProposalRecord, bool]:
        world = _world(world_id)
        if context_receipt.world_id != world or context_receipt.run_id != str(run_id):
            raise ApplicationStateValidationError("context receipt World/Run does not match reservation")
        fingerprint = _fingerprint(request, context_receipt)
        now = datetime.now(UTC)
        try:
            candidate = SceneEditProposalRecord(world_id=world, run_id=run_id, proposal_id=proposal_id,
                request_sha256=fingerprint, request=request, context_receipt=context_receipt,
                status="pending", created_at=now, updated_at=now)
        except (TypeError, ValueError) as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
        with unit_of_work(_ready_dsn()) as conn:
            run = conn.execute("SELECT world_id, run_revision, playable_work_object_id, playable_revision_n, playable_work_revision_id, playable_content_sha256 FROM play.run WHERE run_id=%s FOR UPDATE", (run_id,)).fetchone()
            if run is None or run[0] != world:
                raise ApplicationStateNotFoundError("Play Run is unavailable in this World")
            existing = conn.execute(f"SELECT {_SELECT_COLUMNS} FROM play.scene_edit_proposal WHERE world_id=%s AND run_id=%s AND proposal_id=%s FOR UPDATE", (world, run_id, proposal_id)).fetchone()
            if existing:
                record = _load(existing)
                if record.request_sha256 != fingerprint:
                    raise ApplicationStateConflictError("proposal ID has a different frozen request")
                return record, False
            if run[1] != request.get("run_revision"):
                raise ApplicationStateConflictError("Play Run changed before proposal reservation")
            if (context_receipt.runbook_object_id != str(run[2])
                    or context_receipt.runbook_revision_n != run[3]
                    or context_receipt.runbook_work_revision_id != run[4]
                    or context_receipt.runbook_content_sha256 != run[5]):
                raise ApplicationStateConflictError("Play Run origin pin changed before proposal reservation")
            edition = conn.execute("""
                SELECT e.origin_artifact_id,e.origin_revision_n,e.origin_work_revision_id,
                       e.origin_content_sha256,e.head_revision,r.revision_id,r.content_sha256
                FROM play.run_edition e
                JOIN play.run_edition_revision r
                  ON r.run_id=e.run_id AND r.revision_n=e.head_revision
                WHERE e.run_id=%s
            """, (run_id,)).fetchone()
            if edition is None:
                matches_edition = (
                    context_receipt.edition_revision == 0
                    and context_receipt.edition_revision_id is None
                    and context_receipt.content_sha256 == run[5]
                )
            else:
                matches_edition = (
                    edition[0] == run[2]
                    and edition[1] == run[3]
                    and edition[2] == run[4]
                    and edition[3] == run[5]
                    and context_receipt.edition_revision == edition[4]
                    and context_receipt.edition_revision_id == edition[5]
                    and context_receipt.content_sha256 == edition[6]
                )
            if not matches_edition:
                raise ApplicationStateConflictError("saved Play edition changed before proposal reservation")
            conn.execute("INSERT INTO play.scene_edit_proposal(world_id,run_id,proposal_id,request_sha256,request,context_receipt,status,result,failure_code,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,'pending',NULL,NULL,%s,%s)",
                (world, run_id, proposal_id, fingerprint, Jsonb(request), Jsonb(context_receipt.model_dump(mode="json", by_alias=True)), now, now))
            return candidate, True

    def finish(self, *, world_id: str, run_id: UUID, proposal_id: UUID, result: dict | None,
               failure_code: str | None) -> SceneEditProposalRecord:
        world = _world(world_id)
        if (result is None) == (failure_code is None):
            raise ApplicationStateValidationError("provide exactly one result or failure_code")
        if result is not None:
            try:
                validate_result(result)
            except (TypeError, ValueError) as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
            status = "ready"
        else:
            try:
                validate_failure_code(failure_code)
            except ValueError as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
            status = "failed"
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(f"SELECT {_SELECT_COLUMNS} FROM play.scene_edit_proposal WHERE world_id=%s AND run_id=%s AND proposal_id=%s FOR UPDATE", (world, run_id, proposal_id)).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Play scene edit proposal not found")
            previous = _load(row)
            if previous.status != "pending":
                if previous.status == status and previous.result == result and previous.failure_code == failure_code:
                    return previous
                raise ApplicationStateConflictError("Play scene edit proposal is already terminal")
            updated = SceneEditProposalRecord.model_validate(previous.model_dump(mode="json", by_alias=True) | {
                "status": status, "result": result, "failure_code": failure_code,
                "updated_at": datetime.now(UTC),
            })
            changed = conn.execute("UPDATE play.scene_edit_proposal SET status=%s,result=%s,failure_code=%s,updated_at=%s WHERE world_id=%s AND run_id=%s AND proposal_id=%s AND status='pending'",
                (status, Jsonb(result) if result is not None else None, failure_code, updated.updated_at, world, run_id, proposal_id))
            if changed.rowcount != 1:
                raise ApplicationStateConflictError("Play scene edit proposal changed concurrently")
            return updated

    def get(self, *, world_id: str, run_id: UUID, proposal_id: UUID) -> SceneEditProposalRecord:
        world = _world(world_id)
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(f"SELECT {_SELECT_COLUMNS} FROM play.scene_edit_proposal WHERE world_id=%s AND run_id=%s AND proposal_id=%s", (world, run_id, proposal_id)).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Play scene edit proposal not found")
        return _load(row)

    def list_records(self, *, world_id: str, run_id: UUID, limit: int = 20) -> list[SceneEditProposalRecord]:
        world = _world(world_id)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise ApplicationStateValidationError("limit must be between 1 and 20")
        with unit_of_work(_ready_dsn()) as conn:
            rows = conn.execute(f"SELECT {_SELECT_COLUMNS} FROM play.scene_edit_proposal WHERE world_id=%s AND run_id=%s ORDER BY created_at DESC,proposal_id DESC LIMIT %s", (world, run_id, limit)).fetchall()
        return [_load(row) for row in rows]
