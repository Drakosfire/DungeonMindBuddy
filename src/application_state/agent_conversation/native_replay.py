"""Compact replay metadata derived from the saved native execution ledger."""

import json

from pydantic import BaseModel

ASSERTION_READ_KINDS = frozenset({
    "native_plan_assertion_read_observed_v1",
    "native_plan_assertion_read_observed_v2",
})


class NativeReplayAssertionStep(BaseModel):
    sequence: int
    revision_id: str
    assertion_ids: list[str]
    subject_ids: list[str]
    unavailable_count: int
    writer_evidence: bool


def load_native_replay_read(*, world_id, turn_id, trace_id, sequence, assertion_id):
    """Read the exact saved authorization and assertion in one database snapshot."""
    from .context_trace_store import _load_trace
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_plan_assertions import (
        NativePlanQueryV2,
        NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadV1, NativePlanAssertionReadV2,
    )
    from .service import _ready_dsn
    from .types import PlanNativeContextReceiptV1, canonical_sha256
    from application_state.unit_of_work import unit_of_work

    with unit_of_work(_ready_dsn()) as conn:
        row = conn.execute(
            """SELECT t.conversation_id, t.answer_composition_kind,
                      t.graph_context_receipt, t.graph_context_execution,
                      capture.attempt, capture.payload,
                      (SELECT min((later.payload->>'execution_start_sequence')::integer)
                       FROM agent.turn_context_trace AS later
                       WHERE later.turn_id=t.turn_id AND later.attempt>capture.attempt)
               FROM agent.turn AS t
               JOIN agent.turn_context_trace AS capture ON capture.turn_id=t.turn_id
               WHERE t.world_id=%s AND t.turn_id=%s AND capture.trace_id=%s""",
            (world_id, turn_id, trace_id),
        ).fetchone()
    if row is None:
        raise ValueError("Saved replay attempt is unavailable")
    conversation_id, composition, receipt, execution, attempt, payload, stop = row
    trace = _load_trace(payload)
    if (trace.world_id, trace.turn_id, trace.conversation_id, trace.trace_id, trace.attempt) != (
        world_id, turn_id, conversation_id, trace_id, attempt,
    ):
        raise ValueError("Saved replay attempt binding differs")
    if sequence < trace.execution_start_sequence or (stop is not None and sequence >= stop):
        raise ValueError("Assertion read belongs to another attempt")
    if composition != "base":
        return None
    events = execution["events"]
    observed, = [event for event in events if event["sequence"] == sequence and event["kind"] in ASSERTION_READ_KINDS]
    grant_data, = [event for event in events if event["event_id"] == observed["authorization_event_id"]
                   and trace.execution_start_sequence <= event["sequence"] < sequence]
    saved_data, = [read for read in observed["reads"] if read["assertion"]["assertion_id"] == assertion_id]
    codecs = {codec.model_fields["schema_"].default: codec
              for codec in (SurfaceNativeContextReceiptV1, PlanNativeContextReceiptV1)}
    captured = codecs[receipt["schema"]].model_validate_json(json.dumps(receipt))
    query = captured.native_query
    if (not isinstance(query, NativePlanQueryV2)
            or execution["context_receipt_sha256"] != captured.context_receipt_sha256
            or execution["policy"]["native_query_sha256"] != canonical_sha256(query)):
        raise ValueError("Saved native execution differs from its query receipt")
    grant = NativePlanAssertionReadAuthorizedV1.model_validate_json(json.dumps(grant_data))
    codec = NativePlanAssertionReadV2 if observed["kind"].endswith("_v2") else NativePlanAssertionReadV1
    saved = codec.model_validate_json(json.dumps(saved_data))
    if (query.authority.managed_world_id != world_id or assertion_id not in grant.assertion_ids
            or grant.query_sha256 != query.sha256):
        raise ValueError("Saved assertion differs from its World or authorization")
    return query, grant, saved


def native_assertion_steps(execution, receipt, *, start: int, stop: int | None):
    """Keep ledger sequence and identify the completed writer's exact read events."""
    if not isinstance(execution, dict) or not isinstance(receipt, dict):
        return []
    revision = (receipt.get("native_query") or {}).get("authority", {}).get("revision_id")
    if not revision:
        return []
    events = [
        event for event in execution.get("events", [])
        if event["sequence"] >= start and (stop is None or event["sequence"] < stop)
    ]
    bindings = [event for event in events if event["kind"] == "completion_binding"]
    writers = [
        event for event in events
        if len(bindings) == 1
        and event["kind"] in {"native_writer_authorized_v1", "native_build_writer_authorized_v2",
                              "plan_native_writer_authorized_v2"}
        and event["provider_attempt_id"] == bindings[0]["provider_attempt_id"]
        and event["sequence"] < bindings[0]["sequence"]
    ]
    included = set()
    if len(writers) == 1:
        included.update(writers[0].get("native_read_event_ids", ()))
        included.update(writers[0].get("native_assertion_read_event_ids", ()))
    steps = []
    for event in events:
        if event["kind"] not in ASSERTION_READ_KINDS:
            continue
        assertions = [read["assertion"] for read in event["reads"]]
        steps.append(NativeReplayAssertionStep(
            sequence=event["sequence"],
            revision_id=revision,
            assertion_ids=[assertion["assertion_id"] for assertion in assertions],
            subject_ids=list(dict.fromkeys(assertion["subject_entity_id"] for assertion in assertions)),
            unavailable_count=len(event["unavailable_assertion_ids"]),
            writer_evidence=event["event_id"] in included,
        ))
    return steps
