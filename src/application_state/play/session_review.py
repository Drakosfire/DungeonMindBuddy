"""Session review is an append-only companion to the Play aggregate, never Plan truth."""
from datetime import UTC, datetime
from typing import Literal
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.play.edition_service import _coordinates, _locked_state, _content
from application_state.unit_of_work import unit_of_work

class ReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["end", "save", "reopen"]
    expected_revision: int = Field(ge=0)
    expected_run_revision: int = Field(gt=0)
    expected_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    draft_markdown: str = ""

    @field_validator("draft_markdown")
    @classmethod
    def bounded(cls, value):
        if len(value.encode("utf-8")) > 1048576:
            raise ValueError("Recap draft exceeds 1 MiB")
        return value


def _head(conn, run_id):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT payload FROM play.session_review_revision WHERE run_id=%s ORDER BY revision_n DESC LIMIT 1", (run_id,))
        row = cur.fetchone()
        return row["payload"] if row else None


def read_review(*, run_id: str, world_id: str):
    run_id, world_id = _coordinates(run_id, world_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        state = _locked_state(conn, run_id, world_id)
        content = _content(state, world_id)
        head = _head(conn, run_id)
        return {"world_id": world_id, "run_id": str(run_id), "review": head,
                "source_changed": bool(head and (head["checkpoint"]["run_revision"] != state[0].run_revision or head["checkpoint"]["content"]["content_sha256"] != content.content_sha256))}


def commit_review(*, run_id: str, world_id: str, command_id: str, request: ReviewCommand):
    from application_state.play.service import _as_uuid
    run_id, world_id = _coordinates(run_id, world_id)
    command_id = _as_uuid(command_id, field_name="command_id")
    digest = hashlib.sha256(json.dumps({"world_id": world_id, **request.model_dump()}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        state = _locked_state(conn, run_id, world_id)
        run = state[0]
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT request_sha256,payload FROM play.session_review_revision WHERE run_id=%s AND command_id=%s", (run_id, command_id))
            prior = cur.fetchone()
        if prior:
            if prior["request_sha256"] != digest:
                raise ApplicationStateConflictError("Review command identity already has different bytes")
            return prior["payload"]
        head = _head(conn, run_id)
        if request.expected_revision != (head["revision"] if head else 0):
            raise ApplicationStateConflictError("Session review changed. Your draft is retained; reload the saved review before retrying.")
        content = _content(state, world_id)
        now = datetime.now(UTC).isoformat()
        if request.action == "end":
            if run.run_revision != request.expected_run_revision or content.content_sha256 != request.expected_content_sha256:
                raise ApplicationStateConflictError("Saved session changed. Reload it before ending play.")
            if head and head["status"] == "ended":
                raise ApplicationStateConflictError("Session is already ended. Open its review.")
            checkpoint = {"run_revision": run.run_revision, "progress": run.progress,
                          "content": content.model_dump(mode="json"), "captured_at": now}
            notes = run.progress.get("notes_by_element_id", {})
            draft = head["draft_markdown"] if head else "# Session recap — draft\n\nReview these saved notes and write what happened. Prepared scenes are not played events.\n\n" + "\n\n".join(f"## {key}\n\n{text}" for key, text in notes.items() if text.strip())
            status = "ended"
        else:
            if not head:
                raise ApplicationStateValidationError("End the session before reviewing it")
            if request.action == "save" and head["status"] != "ended":
                raise ApplicationStateConflictError("Session is open for play. End it before editing the recap.")
            checkpoint = head["checkpoint"]
            draft = request.draft_markdown if request.action == "save" else head["draft_markdown"]
            status = "playing" if request.action == "reopen" else "ended"
        payload = {"schema_version": "dmb_session_review_v1", "world_id": world_id, "run_id": str(run_id),
                   "revision": request.expected_revision + 1, "status": status, "updated_at": now,
                   "checkpoint": checkpoint, "draft_markdown": draft}
        conn.execute("INSERT INTO play.session_review_revision(run_id,revision_n,command_id,request_sha256,payload) VALUES (%s,%s,%s,%s,%s)",
                     (run_id, payload["revision"], command_id, digest, Jsonb(payload)))
        return payload
