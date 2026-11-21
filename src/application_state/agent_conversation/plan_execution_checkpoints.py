"""Reconstruct an open Plan execution from its committed event groups."""

from dataclasses import dataclass
import json
from uuid import UUID

from pydantic import ValidationError

from application_state.errors import ApplicationStateIntegrityError
from . import types as t
from .native_execution import SurfaceNativeExecutionV1


@dataclass(frozen=True)
class EventCheckpoint:
    turn_id: UUID
    attempt: int
    base_revision: int
    revision: int
    first_sequence: int
    next_sequence: int
    prefix_sha256: str


@dataclass(frozen=True)
class EventCheckpointGroup:
    append_revision: int
    first_sequence: int
    after_sequence: int
    events: list[dict]
    events_sha256: str


def recover_execution(*, turn_id, attempt, revision, prefix, checkpoint, groups):
    """Validate the exact committed suffix selected under the root snapshot."""
    if (
        (turn_id, attempt) != (checkpoint.turn_id, checkpoint.attempt)
        or not 0 < checkpoint.base_revision <= checkpoint.revision <= revision
        or type(prefix) is not SurfaceNativeExecutionV1
        or len(prefix.events) != checkpoint.first_sequence
    ):
        raise ApplicationStateIntegrityError("Plan checkpoint differs from its locked Turn")
    payload = prefix.model_dump(mode="json", by_alias=True)
    if t.canonical_sha256(payload) != checkpoint.prefix_sha256:
        raise ApplicationStateIntegrityError("Plan checkpoint opening execution changed")
    events = payload["events"]
    previous_revision = checkpoint.base_revision
    for group in groups:
        if (
            not previous_revision < group.append_revision <= checkpoint.revision
            or group.first_sequence != len(events)
            or not group.first_sequence < group.after_sequence <= checkpoint.next_sequence
            or group.after_sequence - group.first_sequence != len(group.events)
            or any(type(event) is not dict or type(event.get("sequence")) is not int
                   or event["sequence"] != ordinal
                   for ordinal, event in enumerate(group.events, group.first_sequence))
            or t.canonical_sha256(group.events) != group.events_sha256
        ):
            raise ApplicationStateIntegrityError("Plan checkpoint event group changed or is out of order")
        events.extend(group.events)
        previous_revision = group.append_revision
    if len(events) != checkpoint.next_sequence or previous_revision != checkpoint.revision:
        raise ApplicationStateIntegrityError("Plan checkpoint suffix is incomplete")
    try:
        return SurfaceNativeExecutionV1.model_validate_json(json.dumps(payload))
    except ValidationError as exc:
        raise ApplicationStateIntegrityError("Plan checkpoint does not reconstruct a valid execution") from exc


def start_checkpoint(conn, *, world_id, turn_id, attempt, revision, prefix):
    """Bind the already-locked root execution to a new checkpoint suffix."""
    event_count = len(prefix.events)
    digest = t.canonical_sha256(prefix.model_dump(mode="json", by_alias=True))
    row = conn.execute("""
        INSERT INTO agent.plan_execution_checkpoint
            (turn_id, attempt, base_revision, revision, first_sequence, next_sequence, prefix_sha256)
        SELECT turn_id, attempt, revision, revision, %s, %s, %s
        FROM agent.turn
        WHERE world_id=%s AND turn_id=%s AND attempt=%s AND revision=%s
          AND status='running' AND claim_expires_at>clock_timestamp()
        ON CONFLICT (turn_id) DO NOTHING
        RETURNING turn_id
        """, (event_count, event_count, digest, world_id, turn_id, attempt, revision)).fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("Plan checkpoint cannot open for this claim")
    return EventCheckpoint(turn_id, attempt, revision, revision, event_count, event_count, digest)


def append_group(conn, *, world_id, root_revision, checkpoint, events):
    """Commit the next typed group and root revision at the same database boundary."""
    from psycopg.types.json import Jsonb

    first = checkpoint.next_sequence
    after = first + len(events)
    if not events or any(event.sequence != ordinal for ordinal, event in enumerate(events, first)):
        raise ApplicationStateIntegrityError("Plan checkpoint append is not contiguous")
    payload = [event.model_dump(mode="json", by_alias=True) for event in events]
    row = conn.execute("""
        WITH root AS (
            UPDATE agent.turn AS turn
            SET revision=turn.revision+1, updated_at=clock_timestamp()
            FROM agent.plan_execution_checkpoint AS head
            WHERE turn.turn_id=head.turn_id AND turn.world_id=%s AND turn.turn_id=%s
              AND turn.status='running' AND turn.claim_expires_at>clock_timestamp()
              AND turn.attempt=%s AND turn.revision=%s
              AND head.attempt=turn.attempt AND head.revision=%s AND head.next_sequence=%s
            RETURNING turn.turn_id, turn.attempt, turn.revision
        ), checkpoint AS (
            UPDATE agent.plan_execution_checkpoint AS head
            SET next_sequence=%s, revision=root.revision
            FROM root WHERE head.turn_id=root.turn_id AND head.attempt=root.attempt
            RETURNING head.turn_id, head.attempt, head.revision
        )
        INSERT INTO agent.plan_execution_checkpoint_group
            (turn_id, attempt, first_sequence, after_sequence, append_revision, events, events_sha256)
        SELECT turn_id, attempt, %s, %s, revision, %s, %s FROM checkpoint
        RETURNING append_revision
        """, (world_id, checkpoint.turn_id, checkpoint.attempt, root_revision, checkpoint.revision,
              first, after, first, after, Jsonb(payload), t.canonical_sha256(payload))).fetchone()
    if row is None:
        return None
    stored = conn.execute("""
        SELECT after_sequence, append_revision, events, events_sha256
        FROM agent.plan_execution_checkpoint_group
        WHERE turn_id=%s AND attempt=%s AND first_sequence=%s
        FOR SHARE
        """, (checkpoint.turn_id, checkpoint.attempt, first)).fetchone()
    if stored != (after, row[0], payload, t.canonical_sha256(payload)):
        raise ApplicationStateIntegrityError("Plan checkpoint append changed its stored event group")
    return row[0]


def load_checkpoint_head(conn, turn_id):
    row = conn.execute("""
        SELECT turn_id, attempt, base_revision, revision, first_sequence, next_sequence, prefix_sha256
        FROM agent.plan_execution_checkpoint WHERE turn_id=%s
        """, (turn_id,)).fetchone()
    return None if row is None else EventCheckpoint(*row)


def load_checkpoint(conn, turn_id):
    """Read a checkpoint and its ordered groups while the caller holds the root lock."""
    rows = conn.execute("""
        SELECT head.turn_id, head.attempt, head.base_revision, head.revision,
               head.first_sequence, head.next_sequence, head.prefix_sha256,
               grouped.append_revision, grouped.first_sequence, grouped.after_sequence,
               grouped.events, grouped.events_sha256
        FROM agent.plan_execution_checkpoint AS head
        LEFT JOIN agent.plan_execution_checkpoint_group AS grouped
            ON grouped.turn_id=head.turn_id AND grouped.attempt=head.attempt
        WHERE head.turn_id=%s
        ORDER BY grouped.first_sequence
        """, (turn_id,)).fetchall()
    if not rows:
        return None
    return EventCheckpoint(*rows[0][:7]), [
        EventCheckpointGroup(*row[7:]) for row in rows if row[7] is not None
    ]



def trace_checkpoint_execution(conn, turn_id, attempt, execution, *, revision, selector):
    """Select trace witnesses under the already-locked Turn claim."""
    head = load_checkpoint_head(conn, turn_id)
    if head is None:
        return execution
    if head.attempt != attempt or head.revision > revision:
        raise ApplicationStateIntegrityError("Plan trace checkpoint belongs to another claim")
    if selector is None:
        from pydantic_core import to_json

        checkpoint, groups = load_checkpoint(conn, turn_id)
        prefix = SurfaceNativeExecutionV1.model_validate_json(to_json(execution))
        return recover_execution(turn_id=turn_id, attempt=attempt, revision=head.revision,
            prefix=prefix, checkpoint=checkpoint, groups=groups).model_dump(mode="json", by_alias=True)
    field, value = selector
    suffix = conn.execute("""
        SELECT event FROM agent.plan_execution_checkpoint_group
        CROSS JOIN LATERAL jsonb_array_elements(events) AS event
        WHERE turn_id=%s AND attempt=%s AND event->>%s=%s
        """, (turn_id, attempt, field, value)).fetchall()
    return execution | {"events": [
        *(event for event in execution["events"] if event.get(field) == value),
        *(event for (event,) in suffix),
    ]}
