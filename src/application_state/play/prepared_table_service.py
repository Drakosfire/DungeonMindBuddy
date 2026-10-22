"""Run-owned table reads and atomic, replayable physical-roll receipts."""
from datetime import UTC, datetime
import hashlib
import json
import re
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content.playable_admission import resolve_pinned_playable_revision
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play import repository as repo
from application_state.play.prepared_tables import read_prepared_tables
from application_state.play.service import _as_uuid, _require_world_id, require_persisted_aggregate_integrity
from application_state.play.session_review import _head as review_head
from application_state.unit_of_work import unit_of_work


class TableRollCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_run_revision: StrictInt = Field(gt=0)
    playable_artifact_id: str
    playable_revision: StrictInt = Field(gt=0)
    playable_work_revision_id: str
    playable_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    table_id: str = Field(pattern=r"^table:[a-z0-9][a-z0-9._-]{0,127}$")
    table_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_value: StrictInt


def _owner(conn, run_id, world_id):
    run = repo.lock_run(conn, run_id, allow_trashed=True)
    if run is None or run.world_id != world_id or run.campaign_id is not None:
        raise ApplicationStateNotFoundError("Play Run not found in this World")
    return run


def _pin(run):
    return dict(playable_artifact_id=str(run.playable_work_object_id), playable_revision=run.playable_revision_n,
                playable_work_revision_id=str(run.playable_work_revision_id), playable_content_sha256=run.playable_content_sha256)


def _source(conn, run, world_id):
    # One exact source resolution per fresh command/read. No edition/history scan.
    require_persisted_aggregate_integrity(run, repo.get_manifest(conn, run.run_id))
    source = resolve_pinned_playable_revision(conn, run.playable_work_object_id, run.playable_revision_n,
                                             run.playable_work_revision_id, run.playable_content_sha256,
                                             expected_world_id=world_id)
    try:
        tables = read_prepared_tables(source.markdown)
    except ValueError as exc:
        raise ApplicationStateValidationError(f"Saved preparation contains an invalid table: {exc}") from exc
    title = re.search(r"^# +(.+)$", source.markdown, re.MULTILINE)
    return tables, title.group(1).strip() if title else "Saved preparation"


def _record(run, world_id):
    from apps.live_control_server.services.play_run_registry import _world_record_from_aggregate
    from types import SimpleNamespace
    return _world_record_from_aggregate(SimpleNamespace(run=run, world_id=world_id)).model_dump(mode="json")


def inventory(*, world_id: str, run_id: str):
    world_id = _require_world_id(world_id)
    run_id = _as_uuid(run_id, field_name="run_id")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = _owner(conn, run_id, world_id)
        tables, title = _source(conn, run, world_id)
        review = review_head(conn, run_id)
        return dict(run=_record(run, world_id), source_title=title, source=_pin(run),
                    can_record=run.lifecycle_status == "active" and not (review and review["status"] == "ended"),
                    tables=[dict(**table.model_dump(), table_sha256=table.content_sha256) for table in tables])


def record_roll(*, world_id: str, run_id: str, command_id: str, request: TableRollCommand):
    world_id = _require_world_id(world_id)
    run_id = _as_uuid(run_id, field_name="run_id")
    command_id = _as_uuid(command_id, field_name="command_id")
    for field in ("playable_artifact_id", "playable_work_revision_id"):
        _as_uuid(getattr(request, field), field_name=field)
    digest = hashlib.sha256(json.dumps(dict(world_id=world_id, run_id=str(run_id), **request.model_dump()),
                                       sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = _owner(conn, run_id, world_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT request_sha256,payload FROM play.prepared_table_receipt WHERE run_id=%s AND command_id=%s", (run_id, command_id))
            prior = cur.fetchone()
        if prior:
            if prior["request_sha256"] != digest:
                raise ApplicationStateConflictError("Roll command already has different submitted values")
            return dict(receipt=prior["payload"], run=_record(run, world_id), replayed=True)
        review = review_head(conn, run_id)
        if run.lifecycle_status != "active" or (review and review["status"] == "ended"):
            raise ApplicationStateConflictError("Reopen this session before recording another roll")
        if run.run_revision != request.expected_run_revision or any(getattr(request, key) != value for key, value in _pin(run).items()):
            raise ApplicationStateConflictError("Saved session or preparation changed. Refresh before submitting a new roll")
        tables, title = _source(conn, run, world_id)
        table = next((table for table in tables if table.table_id == request.table_id), None)
        if table is None or table.content_sha256 != request.table_sha256:
            raise ApplicationStateConflictError("Table is not part of this exact saved preparation")
        try:
            row = table.resolve(request.physical_value)
        except ValueError as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
        now = datetime.now(UTC)
        updated = repo.cas_replace_progress(conn, run_id=run_id, expected_run_revision=request.expected_run_revision,
                                            progress=run.progress, updated_at=now)
        if updated is None:
            raise ApplicationStateConflictError("Session changed before recording the roll")
        payload = dict(schema_version="dmb_prepared_table_receipt_v1", world_id=world_id, run_id=str(run_id),
                       command_id=str(command_id), request_sha256=digest, expected_run_revision=run.run_revision,
                       resulting_run_revision=updated.run_revision, source=_pin(run), source_title=title,
                       table_id=table.table_id, table_sha256=table.content_sha256, table_title=table.title,
                       die_sides=table.die_sides, physical_value=request.physical_value, row_id=row.row_id,
                       outcome=row.outcome, recorded_at=now.isoformat())
        conn.execute("INSERT INTO play.prepared_table_receipt(run_id,resulting_run_revision,command_id,request_sha256,payload) VALUES (%s,%s,%s,%s,%s)",
                     (run_id, updated.run_revision, command_id, digest, Jsonb(payload)))
        return dict(receipt=payload, run=_record(updated, world_id), replayed=False)


def receipts(*, world_id: str, run_id: str, before: int | None = None, limit: int = 20):
    world_id = _require_world_id(world_id)
    run_id = _as_uuid(run_id, field_name="run_id")
    if type(limit) is not int or not 1 <= limit <= 100 or (before is not None and (type(before) is not int or before < 1)):
        raise ApplicationStateValidationError("Invalid history page")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        _owner(conn, run_id, world_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT resulting_run_revision,payload FROM play.prepared_table_receipt WHERE run_id=%s AND (%s::bigint IS NULL OR resulting_run_revision<%s) ORDER BY resulting_run_revision DESC LIMIT %s", (run_id, before, before, limit + 1))
            rows = cur.fetchall()
        return dict(receipts=[row["payload"] for row in rows[:limit]],
                    next_before=rows[limit-1]["resulting_run_revision"] if len(rows) > limit else None)
