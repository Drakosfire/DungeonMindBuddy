"""Names and bounded inspection; never activates or changes conversation history."""

from datetime import datetime
from typing import Literal
from uuid import UUID
import unicodedata
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator
from application_state.agent_conversation.service import (
    AgentConversationService,
    _ready_dsn,
)
from application_state.unit_of_work import unit_of_work
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)


class NameChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=160)
    expected_revision: int = Field(ge=0)

    @field_validator("title")
    @classmethod
    def title_is_one_line(cls, value):
        value = value.strip()
        if not value or any(unicodedata.category(c) == "Cc" for c in value):
            raise ValueError("Use a nonempty single-line conversation name")
        return value


class ConversationSummary(BaseModel):
    conversation_id: UUID
    world_id: str
    title: str
    name_revision: int
    status: Literal["active", "archived"]
    turn_count: int
    created_at: datetime
    updated_at: datetime


_SELECT = """SELECT c.conversation_id,c.world_id,c.status,c.created_at,c.updated_at,
    c.next_turn_sequence-1 AS turn_count,COALESCE(n.revision,0) AS name_revision,
    COALESCE(n.title,left(regexp_replace(first_turn.user_text,'[[:space:]]+',' ','g'),160),'') AS title
    FROM agent.conversation c
    LEFT JOIN agent.conversation_name n USING(conversation_id,world_id)
    LEFT JOIN LATERAL (SELECT user_text FROM agent.turn t
        WHERE t.world_id=c.world_id AND t.conversation_id=c.conversation_id
        ORDER BY sequence LIMIT 1) first_turn ON TRUE"""


def _summary(row):
    if row["name_revision"] == 0:
        row["title"] = " ".join(row["title"].split())[:160] or "Untitled conversation"
    return ConversationSummary.model_validate(row)


def _one(conn, world, conversation):
    row = conn.execute(
        _SELECT + " WHERE c.world_id=%s AND c.conversation_id=%s", (world, conversation)
    ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation not found in this World")
    return _summary(row)


def get_name(world: str, conversation: UUID):
    with unit_of_work(_ready_dsn()) as conn:
        conn.row_factory = dict_row
        return _one(conn, world, conversation)


def list_library(
    world: str, *, status: str = "all", limit: int = 25, before: UUID | None = None
):
    if status not in {"all", "archived"} or not 1 <= limit <= 50:
        raise ApplicationStateValidationError(
            "Invalid conversation library page selector"
        )
    with unit_of_work(_ready_dsn()) as conn:
        conn.row_factory = dict_row
        params = [world]
        clauses = ["c.world_id=%s"]
        if status == "archived":
            clauses.append("c.status='archived'")
        if before is not None:
            cursor = conn.execute(
                "SELECT created_at FROM agent.conversation WHERE world_id=%s AND conversation_id=%s",
                (world, before),
            ).fetchone()
            if cursor is None:
                raise ApplicationStateNotFoundError(
                    "Conversation cursor not found in this World"
                )
            clauses.append("(c.created_at,c.conversation_id)<(%s,%s)")
            params.extend([cursor["created_at"], before])
        params.append(limit + 1)
        rows = conn.execute(
            _SELECT
            + " WHERE "
            + " AND ".join(clauses)
            + " ORDER BY c.created_at DESC,c.conversation_id DESC LIMIT %s",
            params,
        ).fetchall()
        items = [_summary(r) for r in rows[:limit]]
        return {
            "schema": "dmb_conversation_library_v1",
            "world_id": world,
            "status": status,
            "items": [r.model_dump(mode="json") for r in items],
            "next_before": str(items[-1].conversation_id)
            if len(rows) > limit
            else None,
        }


def rename(world: str, conversation: UUID, change: NameChange):
    with unit_of_work(_ready_dsn()) as conn:
        conn.row_factory = dict_row
        parent = conn.execute(
            "SELECT 1 FROM agent.conversation WHERE world_id=%s AND conversation_id=%s FOR KEY SHARE",
            (world, conversation),
        ).fetchone()
        if parent is None:
            raise ApplicationStateNotFoundError("Conversation not found in this World")
        current = _one(conn, world, conversation)
        if (
            current.name_revision == change.expected_revision + 1
            and current.title == change.title
        ):
            return current
        if current.name_revision != change.expected_revision:
            raise ApplicationStateConflictError(
                "Conversation name changed. Reload its name before replacing it."
            )
        row = conn.execute(
            """INSERT INTO agent.conversation_name(conversation_id,world_id,title,revision,updated_at)
            VALUES(%s,%s,%s,1,clock_timestamp()) ON CONFLICT(conversation_id,world_id) DO UPDATE
            SET title=EXCLUDED.title,revision=agent.conversation_name.revision+1,updated_at=clock_timestamp()
            WHERE agent.conversation_name.revision=%s RETURNING revision""",
            (conversation, world, change.title, change.expected_revision),
        ).fetchone()
        if row is None:
            raise ApplicationStateConflictError(
                "Conversation name changed. Your edit was not substituted."
            )
        return _one(conn, world, conversation)


def _reply_object(turn, world, conversation):
    """Project validated historical objects without supplying action authority."""
    from .types import Turn, BuildCollaborationCompletionV1, BuildIntentionalResponseCompletionV1
    from .rules_authority_reads import MixedCompletedTurnV1, RulesApprovedBaseV1

    meta = getattr(turn, "envelope", turn)
    base = turn
    if isinstance(turn, MixedCompletedTurnV1):
        if not isinstance(turn.base_projection, RulesApprovedBaseV1):
            return None
        base = turn.base_projection.turn
        if (base.world_id, base.conversation_id, base.turn_id, base.provenance.primary_work) != (
            meta.world_id, meta.conversation_id, meta.turn_id, meta.provenance.primary_work
        ):
            return None
    if not isinstance(base, Turn) or base.status != "completed" or (
        base.world_id != world or base.conversation_id != conversation
        or base.provenance.surface_id != "build"
        or base.provenance.primary_work.kind != "build"
        or not base.provenance.primary_work.object_id
        or not isinstance(base.completion, (BuildCollaborationCompletionV1, BuildIntentionalResponseCompletionV1))
    ):
        return None
    obj = base.completion.collaboration
    if obj is None:
        return None
    source = {"world_id": world, "conversation_id": str(conversation),
              "turn_id": str(base.turn_id), "document_id": base.provenance.primary_work.object_id,
              "surface_id": "build"}
    if obj.kind == "questions":
        return {"kind": "questions", "questions": [{"text": q.text} for q in obj.questions], "source": source}
    if obj.kind in {"plan", "connected_page", "relationship"}:
        return {"kind": "page_object", "object_kind": obj.kind, "source": source}
    return None


def read_turns(
    world: str,
    conversation: UUID,
    *,
    limit: int = 50,
    before_sequence: int | None = None,
):
    service = AgentConversationService()
    service.get_conversation(world, conversation)
    turns = service.list_turns(
        world, conversation, limit=limit, before_sequence=before_sequence
    )
    rows = []
    for turn in turns:
        meta = getattr(turn, "envelope", turn)
        rows.append(
            {
                "turn_id": str(meta.turn_id),
                "sequence": meta.sequence,
                "status": meta.status,
                "user_text": meta.user_text,
                "assistant_text": turn.assistant_text,
                "reply_object": _reply_object(turn, world, conversation),
            }
        )
    from .retry import context

    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        for row, turn in zip(rows, turns, strict=True):
            row["retry_context"] = context(conn, turn, active=False)
    return {
        "schema": "dmb_conversation_library_turns_v3",
        "world_id": world,
        "conversation_id": str(conversation),
        "turns": rows,
        "next_before_sequence": min(r["sequence"] for r in rows)
        if len(rows) == limit
        else None,
    }


def read_retry_attempts(
    world, conversation, turn_id, *, limit=50, before_sequence=None
):
    from . import repository as repo
    from .retry import context, _edges

    if not 1 <= limit <= 50 or before_sequence is not None and before_sequence < 1:
        raise ApplicationStateValidationError("Invalid retry history cursor")
    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        owner = repo.get_conversation(conn, world, conversation)
        turn = repo.get_turn(conn, world, turn_id)
        meta = getattr(turn, "envelope", turn)
        if owner is None or turn is None or meta.conversation_id != conversation:
            raise ApplicationStateNotFoundError(
                "Retry history unavailable in this conversation"
            )
        incoming, _ = _edges(conn, meta)
        root = incoming[0] if incoming else turn_id
        before = meta.sequence if before_sequence is None else before_sequence
        if before > meta.sequence:
            raise ApplicationStateValidationError(
                "Retry history cursor follows its selected attempt"
            )
        ids = conn.execute(
            """SELECT t.turn_id FROM agent.turn t LEFT JOIN agent.turn_retry r ON r.successor_id=t.turn_id
            WHERE t.world_id=%s AND t.conversation_id=%s AND (t.turn_id=%s OR r.root_id=%s)
            AND t.sequence<%s ORDER BY t.sequence DESC LIMIT %s""",
            (world, conversation, root, root, before, limit + 1),
        ).fetchall()
        more = len(ids) > limit
        turns = [repo.get_turn(conn, world, row[0]) for row in reversed(ids[:limit])]
        active = False  # Library inspection never grants a retry control.
        rows = []
        for item in turns:
            m = getattr(item, "envelope", item)
            rows.append(
                {
                    "turn_id": str(m.turn_id),
                    "sequence": m.sequence,
                    "status": m.status,
                    "user_text": m.user_text,
                    "assistant_text": item.assistant_text,
                    "reply_object": _reply_object(item, world, conversation),
                    "retry_context": context(conn, item, active=active),
                }
            )
        return {
            "schema": "dmb_conversation_library_turns_v3",
            "world_id": world,
            "conversation_id": str(conversation),
            "turns": rows,
            "next_before_sequence": rows[0]["sequence"] if more else None,
        }
