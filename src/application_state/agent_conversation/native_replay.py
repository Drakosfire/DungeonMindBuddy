"""Compact replay metadata derived from the saved native execution ledger."""

import json

from pydantic import BaseModel, Field

from .neighborhood_replay import NeighborhoodReplayHop

ASSERTION_READ_KINDS = frozenset({
    "native_plan_assertion_read_observed_v1",
    "native_plan_assertion_read_observed_v2",
})


class NativeReplayAssertionStep(BaseModel):
    sequence: int
    revision_id: str
    assertion_ids: list[str]
    subject_ids: list[str]
    assertion_ids_by_subject: dict[str, list[str]] = Field(default_factory=dict)
    subject_labels: dict[str, str] = Field(default_factory=dict)
    subject_kinds: dict[str, str] = Field(default_factory=dict)
    related_labels: dict[str, str] = Field(default_factory=dict)
    unavailable_count: int
    writer_evidence: bool



class NativeDiscoveryReplay(BaseModel):
    revision_id: str
    seed_ids: list[str]
    labels: dict[str, str]
    hops: list[NeighborhoodReplayHop]


def _replay_query(receipt, execution, *, stop=None):
    query = receipt.get("native_query") if isinstance(receipt, dict) else None
    if not isinstance(query, dict) or query.get("schema") != "dmb_native_build_query_pending_v1":
        return query
    from .native_context import NativeBuildQueryPendingV1, SurfaceNativeContextReceiptV1
    from .native_execution import SurfaceNativeExecutionV1, _join_context_binding, effective_native_query

    context = SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(receipt))
    ledger = SurfaceNativeExecutionV1.model_validate_json(json.dumps(
        execution | {"events": execution["events"][:stop]},
    ))
    _join_context_binding(context, ledger)
    query = effective_native_query(context, ledger)
    return None if isinstance(query, NativeBuildQueryPendingV1) else query.model_dump(mode="json", by_alias=True)


def native_discovery_replay(receipt, execution=None, *, stop=None):
    query = _replay_query(receipt, execution, stop=stop)
    if not isinstance(query, dict) or not query.get("discovery_hops"):
        return None
    hops = [NeighborhoodReplayHop.model_validate(hop) for hop in query["discovery_hops"]]
    sources = {hop.from_node_id for hop in hops}
    destinations = {hop.to_node_id for hop in hops}
    labels = {item["entity_id"]: item["label"][:256] for item in query["object_matches"]
              if item["entity_id"] in sources}
    labels.update({item["statement_id"]: item["label"][:256] for item in query["matches"]
                   if item["statement_id"] in destinations})
    for item in query.get("assertion_matches", []):
        identity = item["subject_entity_id"]
        if identity in destinations:
            labels.setdefault(identity, item["label"].rsplit(" · ", 1)[0][:256])
    return NativeDiscoveryReplay(
        revision_id=query["authority"]["revision_id"],
        seed_ids=[item["entity_id"] for item in query["object_matches"] if item["entity_id"] in sources],
        labels=labels, hops=hops,
    )


def load_native_replay_read(*, world_id, turn_id, trace_id, sequence, assertion_id):
    """Read the exact saved authorization and assertion in one database snapshot."""
    from .repository import plan_checkpoint_projection
    from .plan_execution_checkpoints import restore_snapshot_execution
    from .context_trace_store import _load_trace
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_execution import SurfaceNativeExecutionV1, _join_context_binding
    from .native_plan_assertions import (
        NativePlanQueryV2,
        NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadV1, NativePlanAssertionReadV2,
    )
    from .service import _ready_dsn
    from .native_reads import validate_execution_binding
    from .types import PlanNativeContextReceiptV1, PlanNativeExecutionV1
    from application_state.unit_of_work import unit_of_work

    with unit_of_work(_ready_dsn()) as conn:
        row = conn.execute(
            f"""SELECT t.conversation_id, t.answer_composition_kind,
                      t.graph_context_receipt, t.graph_context_execution,
                      capture.attempt, capture.payload,
                      (SELECT min((later.payload->>'execution_start_sequence')::integer)
                       FROM agent.turn_context_trace AS later
                       WHERE later.turn_id=t.turn_id AND later.attempt>capture.attempt),
                      t.attempt, t.revision, {plan_checkpoint_projection('t')}
               FROM agent.turn AS t
               JOIN agent.turn_context_trace AS capture ON capture.turn_id=t.turn_id
               WHERE t.world_id=%s AND t.turn_id=%s AND capture.trace_id=%s""",
            (world_id, turn_id, trace_id),
        ).fetchone()
    if row is None:
        raise ValueError("Saved replay attempt is unavailable")
    conversation_id, composition, receipt, execution, attempt, payload, stop, current_attempt, revision, stored = row
    execution = restore_snapshot_execution(execution, turn_id, current_attempt, revision, stored)
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
    if isinstance(captured, SurfaceNativeContextReceiptV1):
        ledger = SurfaceNativeExecutionV1.model_validate_json(json.dumps(execution))
        _join_context_binding(captured, ledger)
    else:
        ledger = PlanNativeExecutionV1.model_validate_json(json.dumps(execution))
        validate_execution_binding(captured, ledger)
    from .native_execution import effective_native_query
    query = effective_native_query(captured, ledger)
    if not isinstance(query, NativePlanQueryV2):
        raise ValueError("Saved query does not admit native assertions")
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
    query = _replay_query(receipt, execution, stop=stop) or {}
    revision = query.get("authority", {}).get("revision_id")
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
    labels = {item["entity_id"]: item["label"] for item in query.get("object_matches", ())}
    steps = []
    for event in events:
        if event["kind"] not in ASSERTION_READ_KINDS:
            continue
        assertions = [read["assertion"] for read in event["reads"]]
        subjects = list(dict.fromkeys(assertion["subject_entity_id"] for assertion in assertions))
        classifications: dict[str, set[str]] = {}
        assertion_ids_by_subject: dict[str, list[str]] = {}
        for assertion in assertions:
            assertion_ids_by_subject.setdefault(assertion["subject_entity_id"], []).append(assertion["assertion_id"])
            value = assertion.get("value", {})
            if assertion.get("predicate") == "dnd5e:classification" and value.get("kind") == "term_ref":
                term = value.get("term")
                if isinstance(term, str) and term.startswith("dnd5e:"):
                    classifications.setdefault(assertion["subject_entity_id"], set()).add(term.removeprefix("dnd5e:"))
        related_labels = {
            target: labels[target]
            for assertion in assertions
            if assertion.get("value", {}).get("kind") == "entity_ref"
            and (target := assertion["value"].get("entity_id")) in labels
        }
        summary_order = {
            assertion["assertion_id"]: (
                0 if assertion.get("predicate") == "dungeonbuddy:summary"
                else 1 if assertion.get("value", {}).get("kind") == "entity_ref"
                and assertion["value"].get("entity_id") in related_labels
                else 2 if assertion.get("value", {}).get("kind") == "entity_ref"
                else 3
            )
            for assertion in assertions
        }
        for ids in assertion_ids_by_subject.values():
            ids.sort(key=summary_order.__getitem__)
        steps.append(NativeReplayAssertionStep(
            sequence=event["sequence"],
            revision_id=revision,
            assertion_ids=[assertion["assertion_id"] for assertion in assertions],
            subject_ids=subjects,
            assertion_ids_by_subject=assertion_ids_by_subject,
            subject_labels={identity: labels[identity] for identity in subjects if identity in labels},
            subject_kinds={identity: next(iter(kinds)) for identity, kinds in classifications.items() if len(kinds) == 1},
            related_labels=related_labels,
            unavailable_count=len(event["unavailable_assertion_ids"]),
            writer_evidence=event["event_id"] in included,
        ))
    return steps
