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
    ApplicationStateIntegrityError,
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
    status: Literal["active", "archived", "trashed"]
    library_archived: bool
    turn_count: int
    created_at: datetime
    updated_at: datetime


# Starting or switching a chat changes its execution status without writing an
# Archive receipt. Only explicit Archive/Reopen choices affect the library.
_SELECT = """WITH library_choices AS (
    SELECT DISTINCT ON (conversation_id) conversation_id, command_kind
    FROM agent.command_receipt
    WHERE world_id=%s AND command_kind IN ('archive', 'reopen')
    ORDER BY conversation_id, result_pointer_revision DESC
)
    SELECT c.conversation_id,c.world_id,c.status,c.created_at,c.updated_at,
    COALESCE(l.command_kind='archive', false) AS library_archived,
    c.next_turn_sequence-1 AS turn_count,COALESCE(n.revision,0) AS name_revision,
    COALESCE(n.title,(SELECT left(regexp_replace(t.user_text,'[[:space:]]+',' ','g'),160)
        FROM agent.turn t
        WHERE t.world_id=c.world_id AND t.conversation_id=c.conversation_id
        ORDER BY sequence LIMIT 1),'') AS title
    FROM agent.conversation c
    LEFT JOIN agent.conversation_name n USING(conversation_id,world_id)
    LEFT JOIN library_choices l ON l.conversation_id=c.conversation_id"""


def _summary(row):
    if row["name_revision"] == 0:
        row["title"] = " ".join(row["title"].split())[:160] or "Untitled conversation"
    return ConversationSummary.model_validate(row)


def _one(conn, world, conversation):
    row = conn.execute(
        _SELECT + " WHERE c.world_id=%s AND c.conversation_id=%s", (world, world, conversation)
    ).fetchone()
    if row is None:
        raise ApplicationStateNotFoundError("Conversation not found in this World")
    return _summary(row)


def get_name(world: str, conversation: UUID):
    with unit_of_work(_ready_dsn()) as conn:
        conn.row_factory = dict_row
        return _one(conn, world, conversation)


def list_library(
    world: str, *, status: str = "all", limit: int = 25, before: str | UUID | None = None
):
    if status not in {"all", "recent", "archived", "explicitly_archived", "trashed"} or not 1 <= limit <= 50:
        raise ApplicationStateValidationError(
            "Invalid conversation library page selector"
        )
    with unit_of_work(_ready_dsn()) as conn:
        conn.row_factory = dict_row
        params = [world, world]
        clauses = ["c.world_id=%s"]
        order_column = "updated_at" if status == "recent" else "created_at"
        if status == "trashed":
            clauses.append("c.status='trashed'")
        else:
            clauses.append("c.status<>'trashed'")
            if status == "recent":
                clauses.append("l.command_kind IS DISTINCT FROM 'archive'")
            elif status == "explicitly_archived":
                clauses.append("l.command_kind='archive'")
            elif status == "archived":
                clauses.append("c.status='archived'")
        if before is not None:
            if status == "recent":
                try:
                    activity, cursor_id = str(before).split("|", 1)
                    cursor_id = UUID(cursor_id)
                    cursor_time = datetime.fromisoformat(activity)
                    if cursor_time.tzinfo is None:
                        raise ValueError
                except ValueError as exc:
                    raise ApplicationStateValidationError("Invalid Recent conversation cursor") from exc
            else:
                try:
                    cursor_id = UUID(str(before))
                except ValueError as exc:
                    raise ApplicationStateValidationError("Invalid conversation cursor") from exc
                cursor = conn.execute(
                    "SELECT created_at FROM agent.conversation WHERE world_id=%s AND conversation_id=%s",
                    (world, cursor_id),
                ).fetchone()
                if cursor is None:
                    raise ApplicationStateNotFoundError("Conversation cursor not found in this World")
                cursor_time = cursor["created_at"]
            clauses.append(f"(c.{order_column},c.conversation_id)<(%s,%s)")
            params.extend([cursor_time, cursor_id])
        params.append(limit + 1)
        rows = conn.execute(
            _SELECT
            + " WHERE "
            + " AND ".join(clauses)
            + f" ORDER BY c.{order_column} DESC,c.conversation_id DESC LIMIT %s",
            params,
        ).fetchall()
        items = [_summary(r) for r in rows[:limit]]
        next_before = None
        if len(rows) > limit:
            last = items[-1]
            next_before = str(last.conversation_id)
            if status == "recent":
                next_before = f"{last.updated_at.isoformat()}|{next_before}"
        return {
            "schema": "dmb_conversation_library_v1",
            "world_id": world,
            "status": status,
            "items": [r.model_dump(mode="json") for r in items],
            "next_before": next_before,
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
        saved_name = conn.execute(
            "SELECT title, revision FROM agent.conversation_name WHERE world_id=%s AND conversation_id=%s",
            (world, conversation),
        ).fetchone()
        revision = saved_name["revision"] if saved_name else 0
        if (
            saved_name is not None
            and revision == change.expected_revision + 1
            and saved_name["title"] == change.title
        ):
            current = _one(conn, world, conversation)
            if current.name_revision == revision and current.title == change.title:
                return current
        if revision != change.expected_revision:
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
    from .types import Turn
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
    if not isinstance(base, Turn) or base.status != "completed" or (base.world_id,base.conversation_id)!=(world,conversation):
        return None
    return _reply_object_projection(base.completion,base.provenance,world,conversation,base.turn_id)


def _reply_object_projection(completion, provenance, world, conversation, turn_id):
    """One display descriptor owner for full and lightweight saved messages."""
    from .types import BuildCollaborationCompletionV1, BuildGraphReferenceCompletionV1, BuildImageMoveCompletionV1, BuildIntentionalResponseCompletionV1
    from .native_completion import SurfaceNativeCompletionV1
    codecs=(BuildCollaborationCompletionV1,BuildIntentionalResponseCompletionV1,SurfaceNativeCompletionV1)
    work=provenance.primary_work
    surface=provenance.surface_id
    if isinstance(completion, (BuildGraphReferenceCompletionV1, BuildImageMoveCompletionV1)):
        if (surface != 'build' or provenance.surface_resolution != 'resolved' or provenance.world_id != world
                or work.resolution != 'resolved' or work.kind != 'build' or not work.object_id
                or completion.disposition != 'ready' or completion.action_id != turn_id):
            return None
        kind = 'build_image_move' if isinstance(completion, BuildImageMoveCompletionV1) else 'build_graph_reference'
        return {'kind': kind, 'placement_sha256': completion.placement_sha256,
                'source': {'world_id': world, 'conversation_id': str(conversation), 'turn_id': str(turn_id),
                           'document_id': work.object_id, 'surface_id': surface}}
    if (surface not in {'build','plan'} or provenance.surface_resolution!='resolved' or work.resolution!='resolved' or provenance.world_id!=world
            or work.kind!=surface or not work.object_id or not isinstance(completion,codecs)
            or isinstance(completion,SurfaceNativeCompletionV1) and completion.surface_id!=surface
            or not isinstance(completion,SurfaceNativeCompletionV1) and surface!='build'):
        return None
    obj=completion.collaboration
    if obj is None or surface=='plan' and (not isinstance(completion,SurfaceNativeCompletionV1) or obj.kind!='connected_page'):
        return None
    source={'world_id':world,'conversation_id':str(conversation),'turn_id':str(turn_id),
        'document_id':work.object_id,'surface_id':surface}
    if obj.kind=='questions':
        return {'kind':'questions','questions':[{'text':q.text} for q in obj.questions],'source':source}
    if obj.kind in {'plan','connected_page','relationship'}:
        return {'kind':'page_object','object_kind':obj.kind,'source':source}
    return None


def _message_reply_object(row, provenance, conversation):
    """Parse stored completion only; opening the review still reads its exact Turn."""
    if row['status']!='completed':return None
    from .types import BuildCollaborationCompletionV1, BuildGraphReferenceCompletionV1, BuildImageMoveCompletionV1, BuildIntentionalResponseCompletionV1
    from .native_completion import SurfaceNativeCompletionV1
    from pydantic import ValidationError
    raw=row['completion']
    codecs={cls.model_fields['schema_'].default:cls for cls in (
        BuildCollaborationCompletionV1,BuildIntentionalResponseCompletionV1,SurfaceNativeCompletionV1,
        BuildGraphReferenceCompletionV1, BuildImageMoveCompletionV1)}
    codec=codecs.get(raw.get('schema')) if isinstance(raw,dict) else None
    if codec is None:return None
    try:completion=codec.model_validate(raw)
    except (ValidationError,ValueError,TypeError):return None
    if isinstance(completion, (BuildGraphReferenceCompletionV1, BuildImageMoveCompletionV1)) and (
        row['answer_composition_kind'] != 'base' or row['assistant_text'] != completion.answer_segments[0].text
    ):
        return None
    try:
        from .rules_authority_reads import validate_base_composition_summary,read_completed_binding_summary
        if row['answer_composition_kind']=='base':
            validate_base_composition_summary(row['rules_summary'])
        elif row['answer_composition_kind']=='rules_mixed_v1':
            binding=read_completed_binding_summary(row['rules_summary'],world_id=row['world_id'],
                conversation_id=conversation,turn_id=row['turn_id'],attempt=row['attempt'],revision=row['revision'])
            if binding.base_disposition!='approved':return None
            binding.validate_text(row['assistant_text'],tuple(s.text for s in completion.answer_segments))
        else:return None
    except (ApplicationStateIntegrityError,ValueError,TypeError,KeyError):return None
    return _reply_object_projection(completion,provenance,row['world_id'],conversation,row['turn_id'])


_SAVED_STATBLOCK_PREVIEW_SELECT = """CASE WHEN surface_id='build' AND status='completed' THEN (
            SELECT jsonb_agg(jsonb_build_object(
                'name', event->'definition'->'identity'->'name',
                'world_id', event->'world_id', 'draft_id', event->'draft_id',
                'revision_id', event->'locator'->'revision_id',
                'pdf_sources', CASE WHEN jsonb_typeof(event->'pdf_support'->'support')='array'
                THEN jsonb_build_object('scope', event->'pdf_support'->'scope', 'support', (
                    SELECT COALESCE(jsonb_agg(item - 'text'), '[]'::jsonb)
                    FROM jsonb_array_elements(event->'pdf_support'->'support') AS item
                    WHERE EXISTS (
                        SELECT 1 FROM jsonb_array_elements(completion->'answer_segments') AS claim
                        WHERE claim->>'kind'='statblock_pdf_claim'
                            AND claim->'scope'=event->'pdf_support'->'scope'
                            AND claim->>'assertion_id'=item->>'assertion_id'
                            AND claim->>'evidence_ref_id'=item->>'evidence_ref_id')))
                ELSE NULL END))
            FROM jsonb_array_elements(graph_context_execution->'events') AS event
            WHERE event->>'kind'='build_saved_statblock_read_v1'
                AND event->>'world_id'=t.world_id
        ) END AS saved_statblocks"""


_VARIANT_APPROVAL_PREVIEW_SELECT = """(
    t.status = 'completed' AND t.surface_id = 'build' AND
    jsonb_path_exists(t.graph_context_execution, '$.events[*] ? (
        @.kind == "build_requested_work_resolved_v1" &&
        @.requested_work == "review_variant_approval"
    )')
) AS variant_approval_requested"""


def _message_page(conn, world, conversation, limit, before_sequence, *, metadata=False, retry_lineage=False):
    """Bounded message display; never load execution or a full context receipt."""
    from . import repository as repo
    from .authored_reference_preview import SELECT as reference_select, project as reference_preview
    from .conversation_drafts import CANONICAL_REVIEWED_DRAFT

    presentation = (""",failure_code,completion,
        CASE WHEN jsonb_typeof(completion->'saved_source_citations')='array'
            AND completion->'saved_source_citations'<>'[]'::jsonb
            THEN graph_context_receipt->'work_context'->'source_basis'
            ELSE NULL END AS citation_source_basis,
        """ + _SAVED_STATBLOCK_PREVIEW_SELECT + """,
        EXISTS (SELECT 1 FROM agent.conversation_draft_revision d
            WHERE d.turn_id=t.turn_id AND d.world_id=t.world_id
                AND d.conversation_id=t.conversation_id AND d.revision=1) AS draft_available,
        """ + _VARIANT_APPROVAL_PREVIEW_SELECT + """,
        (t.status='completed' AND t.surface_id='build' AND
        """ + CANONICAL_REVIEWED_DRAFT + """) AS variant_draft_reviewed,
        t.answer_composition_kind, """ + reference_select + ", " + repo._rules_summary_select("t")) if metadata else ""
    rows = conn.execute(
        f"""SELECT turn_id,sequence,status,user_text,assistant_text,idempotency_key,
            revision,world_id,surface_resolution,surface_id,surface_instance_id,attempt{presentation}
        FROM agent.turn t WHERE world_id=%s AND conversation_id=%s
            AND (%s::bigint IS NULL OR sequence<%s)
        ORDER BY sequence DESC LIMIT %s""",
        (world, conversation, before_sequence, before_sequence, limit + 1),
    ).fetchall()
    page = list(reversed(rows[:limit]))
    references = repo._turn_reference_page(conn, page) if metadata else {}
    lineage = {}
    if retry_lineage and page:
        lineage = {row["id"]: row for row in conn.execute(
            """SELECT page.id, i.root_id, i.predecessor_id, i.ordinal, o.successor_id
            FROM unnest(%s::uuid[]) AS page(id)
            LEFT JOIN agent.turn_retry i ON i.successor_id=page.id
                AND i.world_id=%s AND i.conversation_id=%s
            LEFT JOIN agent.turn_retry o ON o.predecessor_id=page.id
                AND o.world_id=%s AND o.conversation_id=%s""",
            ([row["turn_id"] for row in page], world, conversation, world, conversation),
        ).fetchall()}
    messages = []
    for row in page:
        message = {
            key: row[key]
            for key in ("sequence", "status", "user_text", "assistant_text")
        }
        message["turn_id"] = str(row["turn_id"])
        edge = lineage.get(row["turn_id"])
        if edge and (edge["root_id"] is not None or edge["successor_id"] is not None):
            message["retry_lineage"] = {
                "root_id": str(edge["root_id"] or row["turn_id"]),
                "predecessor_id": str(edge["predecessor_id"]) if edge["predecessor_id"] else None,
                "successor_id": str(edge["successor_id"]) if edge["successor_id"] else None,
                "ordinal": edge["ordinal"] if edge["ordinal"] is not None else 0,
            }
        if metadata:
            from .saved_citation_preview import project
            from .retry import author_interaction
            provenance=repo.turn_provenance(row,references[row["turn_id"]])
            if row["draft_available"]:
                message["conversation_draft_available"] = True
            if row["variant_draft_reviewed"]:
                message["variant_draft_reviewed"] = True
            if row["variant_approval_requested"]:
                message["variant_approval_requested"] = True
            if row["saved_statblocks"]:
                message["saved_statblocks"] = row["saved_statblocks"]
            message.update(
                reply_object=_message_reply_object(row,provenance,conversation),
                citation_preview=project(row),
                authored_references=reference_preview(row["authored_reference_inputs"], world),
                idempotency_key=str(row["idempotency_key"]),
                revision=row["revision"],
                provenance=provenance.model_dump(mode="json"),
            )
            interaction = author_interaction(
                provenance.surface_id, provenance.primary_work.kind, row["status"], row["failure_code"],
            )
            if interaction:
                message["author_interaction"] = interaction
        messages.append(message)
    return messages, page[0]["sequence"] if len(rows) > limit else None


def _message_selector(limit, before_sequence):
    if not 1 <= limit <= 100 or (before_sequence is not None and before_sequence < 1):
        raise ApplicationStateValidationError("Invalid message page selector")


def read_messages(
    world: str,
    conversation: UUID,
    *,
    limit: int = 50,
    before_sequence: int | None = None,
):
    """Stored text grants no evidence, retry or authoring authority."""
    _message_selector(limit, before_sequence)
    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.row_factory = dict_row
        owner = conn.execute(
            "SELECT 1 FROM agent.conversation WHERE world_id=%s AND conversation_id=%s",
            (world, conversation),
        ).fetchone()
        if owner is None:
            raise ApplicationStateNotFoundError("Conversation not found in this World")
        messages, cursor = _message_page(
            conn, world, conversation, limit, before_sequence
        )
    return {
        "schema": "dmb_conversation_messages_v1",
        "world_id": world,
        "conversation_id": str(conversation),
        "messages": messages,
        "next_before_sequence": cursor,
    }


def read_active_messages(
    world: str, *, limit: int = 50, before_sequence: int | None = None,
    retry_lineage: bool = False,
):
    """Pointer and message metadata share one APP snapshot, never a replay authority."""
    from . import repository as repo
    from application_state.errors import ApplicationStateIntegrityError

    _message_selector(limit, before_sequence)
    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.row_factory = dict_row
        pointer, active = repo.get_active_conversation_snapshot(conn, world)
        ident = pointer.active_conversation_id if pointer else None
        if (
            (active.conversation_id if active else None) != ident
            or active
            and active.status != "active"
        ):
            raise ApplicationStateIntegrityError(
                "Active conversation pointer has no matching owner"
            )
        messages, cursor = (
            _message_page(conn, world, ident, limit, before_sequence, metadata=True, retry_lineage=retry_lineage)
            if ident
            else ([], None)
        )
    return {
        "schema": "dmb_active_conversation_messages_v5" if retry_lineage else "dmb_active_conversation_messages_v4",
        "world_id": world,
        "conversation_state": "active" if ident else "absent",
        "conversation_id": str(ident) if ident else None,
        "active_conversation_id": str(ident) if ident else None,
        "pointer_revision": pointer.revision if pointer else 0,
        "messages": messages,
        "next_before_sequence": cursor,
    }


def _turn_row(turn, world, conversation):
    from .authored_graph_references import reference_input

    meta = getattr(turn, "envelope", turn)
    row = {
        "turn_id": str(meta.turn_id),
        "sequence": meta.sequence,
        "status": meta.status,
        "user_text": meta.user_text,
        "assistant_text": turn.assistant_text,
        "reply_object": _reply_object(turn, world, conversation),
    }
    captured = reference_input(turn)
    if captured is not None:
        row["authored_references"] = captured.model_dump(mode="json", by_alias=True)
    return row


def read_turns(
    world: str,
    conversation: UUID,
    *,
    limit: int = 50,
    before_sequence: int | None = None,
):
    service = AgentConversationService()
    from .retry import library_contexts

    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        turns, more = service.list_turn_page(
            world, conversation, limit=limit, before_sequence=before_sequence,
            connection=conn,
        )
        contexts = library_contexts(conn, world, conversation, turns)
    rows = [_turn_row(turn, world, conversation) for turn in turns]
    for row, retry_context in zip(rows, contexts, strict=True):
        row["retry_context"] = retry_context
    return {
        "schema": "dmb_conversation_library_turns_v3",
        "world_id": world,
        "conversation_id": str(conversation),
        "turns": rows,
        "next_before_sequence": min(r["sequence"] for r in rows)
        if more
        else None,
    }


def read_retry_attempts(
    world, conversation, turn_id, *, limit=50, before_sequence=None
):
    from . import repository as repo
    from .retry import library_contexts

    if not 1 <= limit <= 50 or before_sequence is not None and before_sequence < 1:
        raise ApplicationStateValidationError("Invalid retry history cursor")
    with unit_of_work(_ready_dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        anchor = repo.get_retry_history_anchor(conn, world, conversation, turn_id)
        if anchor is None:
            raise ApplicationStateNotFoundError(
                "Retry history unavailable in this conversation"
            )
        sequence, root = anchor
        before = sequence if before_sequence is None else before_sequence
        if before > sequence:
            raise ApplicationStateValidationError(
                "Retry history cursor follows its selected attempt"
            )
        turns, more = repo.list_retry_attempt_page(
            conn, world, conversation, root, before_sequence=before, limit=limit
        )
        rows = []
        contexts = library_contexts(conn, world, conversation, turns)
        for item, retry_context in zip(turns, contexts, strict=True):
            row = _turn_row(item, world, conversation)
            row["retry_context"] = retry_context
            rows.append(row)
        return {
            "schema": "dmb_conversation_library_turns_v3",
            "world_id": world,
            "conversation_id": str(conversation),
            "turns": rows,
            "next_before_sequence": rows[0]["sequence"] if more else None,
        }
