"""Read frozen display labels without loading source prose or granting evidence."""
from uuid import UUID


def read_source_names(conn, world_id: str, conversation_id: UUID, turn_ids: list[UUID]) -> list[dict]:
    if not turn_ids:
        return []
    # The existing turn page is already bounded. Match the trace to its current
    # owner/attempt and return only display/identity fields, never text or prompts.
    rows = conn.execute("""
        SELECT t.turn_id, jsonb_build_object(
            'source_read_event_id', observation.value->'source_read_event_id',
            'source_read_id', observation.value->'source_read_id',
            'source_artifact_id', observation.value->'source_artifact_id',
            'source_revision_id', observation.value->'source_revision_id',
            'anchor_id', observation.value->'anchor_id',
            'evidence_ref_id', observation.value->'evidence_ref_id',
            'graph_revision', observation.value->'graph_revision',
            'content_sha256', observation.value->'content_sha256',
            'source_name', observation.value->'source_name'
        ) AS label
        FROM agent.turn t
        JOIN agent.turn_context_trace trace ON trace.turn_id=t.turn_id AND trace.attempt=t.attempt
        CROSS JOIN LATERAL jsonb_array_elements(trace.payload->'observations') observation(value)
        WHERE t.world_id=%s AND t.conversation_id=%s AND t.turn_id=ANY(%s)
          AND trace.payload->>'world_id'=t.world_id
          AND trace.payload->>'conversation_id'=t.conversation_id::text
          AND trace.payload->>'turn_id'=t.turn_id::text
          AND trace.payload->>'trace_id'=trace.trace_id::text
          AND trace.payload->'attempt'=to_jsonb(t.attempt)
          AND observation.value->>'world_id'=t.world_id
          AND observation.value->>'kind'='source_passage'
          AND jsonb_typeof(observation.value->'source_name')='string'
    """, (world_id, conversation_id, turn_ids)).fetchall()
    return [{"turn_id": str(row[0]), **row[1]} for row in rows]
