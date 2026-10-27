"""APP-owned per-attempt trace storage and claim fencing."""

from __future__ import annotations

from datetime import datetime
import json
from uuid import UUID

from psycopg.types.json import Jsonb

from application_state.agent_conversation.context_trace import (
    ContextTraceObservation,
    CONTEXT_TRACE_TERMINAL_RESERVE_BYTES,
    MAX_CONTEXT_TRACE_BYTES,
    MAX_SOURCE_PASSAGE_CHARS_PER_TURN,
    TraceContextSnapshot,
    TraceHistoricalSourceReferenceV1,
    TraceGraphTool,
    TraceAuthoredGraphReferenceV1,
    TraceSourcePassage,
    TracePromptReference,
    TurnContextTraceV1,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work


def _load_trace(payload: object) -> TurnContextTraceV1:
    try:
        return TurnContextTraceV1.model_validate(payload)
    except Exception as exc:
        raise ApplicationStateValidationError("stored context trace is invalid") from exc


def _trace_row(conn, turn_id: UUID, attempt: int):
    return conn.execute(
        "SELECT trace_id, payload FROM agent.turn_context_trace "
        "WHERE turn_id=%s AND attempt=%s FOR UPDATE",
        (turn_id, attempt),
    ).fetchone()


def _save_trace(conn, trace: TurnContextTraceV1) -> None:
    payload = Jsonb(trace.model_dump(mode="json", by_alias=True))
    reserve = 0 if trace.closed_at is not None else (
        CONTEXT_TRACE_TERMINAL_RESERVE_BYTES if trace.capture_status == "recording"
        else CONTEXT_TRACE_TERMINAL_RESERVE_BYTES // 2
    )
    actual_bytes = conn.execute(
        "SELECT octet_length(%s::jsonb::text)", (payload,),
    ).fetchone()[0]
    if actual_bytes > MAX_CONTEXT_TRACE_BYTES - reserve:
        raise ApplicationStateValidationError("trace exceeds the explicit 1 MiB per-attempt ceiling")
    conn.execute(
        "UPDATE agent.turn_context_trace SET payload=%s "
        "WHERE turn_id=%s AND attempt=%s AND trace_id=%s",
        (
            payload,
            trace.turn_id,
            trace.attempt,
            trace.trace_id,
        ),
    )


def append_source_passages_locked(
    conn,
    *,
    world_id: str,
    turn_id: UUID,
    attempt: int,
    event_id: UUID,
    passages: list[TraceSourcePassage],
) -> TurnContextTraceV1 | None:
    """Append source bytes in the same transaction as their ledger receipt."""
    row = _trace_row(conn, turn_id, attempt)
    if row is None:
        return None
    trace = _load_trace(row[1])
    if trace.world_id != world_id:
        raise ApplicationStateValidationError("source passage trace belongs to a different World")
    if trace.closed_at is not None:
        raise ApplicationStateConflictError("context trace is already closed")
    candidates = [item for item in passages if item.source_read_event_id == event_id]
    if len(candidates) != len(passages):
        raise ApplicationStateValidationError("source passage refers to a different ledger event")
    existing = [
        item for item in trace.observations
        if isinstance(item, TraceSourcePassage) and item.source_read_event_id == event_id
    ]
    if existing:
        retry = [
            item.model_copy(update={"sequence": saved.sequence})
            for item, saved in zip(candidates, existing, strict=True)
        ]
        if existing == retry:
            return trace
        raise ApplicationStateConflictError("source-read passage observation changed")
    if len(candidates) != len({item.source_read_id for item in candidates}):
        raise ApplicationStateValidationError("source-read passage IDs must be unique")
    all_attempt_rows = conn.execute(
        "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s",
        (turn_id,),
    ).fetchall()
    observed_chars = sum(item.returned_chars for item in candidates)
    for attempt_row in all_attempt_rows:
        other = _load_trace(attempt_row[0])
        prior_passages = [
            item for item in other.observations
            if isinstance(item, TraceSourcePassage)
            and item.source_read_event_id != event_id
        ]
        observed_chars += sum(item.returned_chars for item in prior_passages)
    if observed_chars > MAX_SOURCE_PASSAGE_CHARS_PER_TURN:
        raise ApplicationStateValidationError("captured source passages exceed the 96,000 character turn ceiling")
    sequence = len(trace.observations)
    # The source read has already been validated by the authoritative graph
    # execution model. These observations only preserve the returned bytes.
    additions = [
        item.model_copy(update={"sequence": sequence + index})
        for index, item in enumerate(candidates)
    ]
    try:
        updated = TurnContextTraceV1.model_validate({
            **trace.model_dump(mode="python"),
            "observations": [*trace.observations, *additions],
        })
    except ValueError as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    _save_trace(conn, updated)
    return updated


def close_context_trace_locked(
    conn,
    *,
    world_id: str,
    turn_id: UUID,
    attempt: int,
    status: str,
    closed_at: datetime,
) -> None:
    row = _trace_row(conn, turn_id, attempt)
    if row is None:
        return
    trace = _load_trace(row[1])
    if trace.world_id != world_id:
        raise ApplicationStateValidationError("context trace World differs from its turn")
    if trace.closed_at is not None:
        if trace.closed_at == closed_at and trace.terminal_status == status:
            return
        raise ApplicationStateConflictError("context trace is already closed")
    execution_row = conn.execute(
        "SELECT graph_context_execution FROM agent.turn WHERE world_id=%s AND turn_id=%s",
        (world_id, turn_id),
    ).fetchone()
    execution = execution_row[0] if execution_row is not None else None
    observations = [
        item for item in trace.observations if isinstance(item, TraceSourcePassage)
    ]
    observed = {
        (str(item.source_read_event_id), item.source_read_id)
        for item in observations
    }
    missing_passage = False
    trace_graph_event_ids = {
        str(item.execution_event_id)
        for item in trace.observations if isinstance(item, TraceGraphTool)
    }
    missing_graph_projection = False
    if isinstance(execution, dict):
        for event in execution.get("events", []):
            if (
                event.get("kind") in {"validated_graph_operation", "validated_graph_operation_v3"}
                and int(event.get("sequence", -1)) >= trace.execution_start_sequence
                and str(event.get("event_id")) not in trace_graph_event_ids
            ):
                missing_graph_projection = True
            if (
                event.get("kind") not in {"validated_source_read_v2", "source_passage_reused_v1"}
                or int(event.get("sequence", -1)) < trace.execution_start_sequence
            ):
                continue
            for receipt in event.get("receipts", []):
                if receipt.get("content_sha256") is not None and (
                    event.get("event_id"), receipt.get("source_read_id")
                ) not in observed:
                    missing_passage = True
                    break
            if missing_passage:
                break
    capture_status = trace.capture_status
    capture_failure_code = trace.capture_failure_code
    if (missing_passage or missing_graph_projection) and capture_status == "recording":
        capture_status = "incomplete"
        capture_failure_code = (
            "source_passage_snapshot_missing" if missing_passage
            else "graph_result_projection_missing"
        )
    try:
        closed = TurnContextTraceV1.model_validate({
            **trace.model_dump(mode="python"),
            "closed_at": closed_at,
            "terminal_status": status,
            "capture_status": "complete" if capture_status == "recording" else capture_status,
            "capture_failure_code": capture_failure_code,
        })
    except ValueError as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    _save_trace(conn, closed)


class TurnContextTraceStore:
    def begin(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID, started_at: datetime,
    ) -> TurnContextTraceV1:
        from application_state.agent_conversation.service import _ready_dsn

        with unit_of_work(_ready_dsn()) as conn:
            turn = conn.execute(
                "SELECT conversation_id, status, revision, attempt, claim_expires_at, "
                "clock_timestamp() AS now, graph_context_execution FROM agent.turn "
                "WHERE world_id=%s AND turn_id=%s FOR UPDATE",
                (world_id, turn_id),
            ).fetchone()
            if turn is None or turn[0] != conversation_id:
                raise ApplicationStateNotFoundError("trace turn is unavailable in this World conversation")
            if (
                turn[1] != "running" or turn[2] != expected_revision
                or turn[3] != attempt or turn[4] is None or turn[4] <= turn[5]
            ):
                raise ApplicationStateConflictError("trace start is fenced by the current turn claim")
            existing = _trace_row(conn, turn_id, attempt)
            if existing is not None:
                trace = _load_trace(existing[1])
                if trace.trace_id != trace_id or trace.started_at != started_at:
                    raise ApplicationStateConflictError("context trace attempt identity changed")
                return trace
            trace = TurnContextTraceV1(
                trace_id=trace_id, world_id=world_id, conversation_id=conversation_id,
                turn_id=turn_id, attempt=attempt, started_at=started_at,
                execution_start_sequence=(
                    len(turn[6].get("events", [])) if isinstance(turn[6], dict) else 0
                ),
                observations=[],
            )
            conn.execute(
                "INSERT INTO agent.turn_context_trace(turn_id,attempt,trace_id,payload) "
                "VALUES (%s,%s,%s,%s)",
                (turn_id, attempt, trace_id, Jsonb(trace.model_dump(mode="json", by_alias=True))),
            )
            return trace

    def append(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID,
        observation: ContextTraceObservation,
    ) -> TurnContextTraceV1:
        from application_state.agent_conversation.service import _ready_dsn

        with unit_of_work(_ready_dsn()) as conn:
            turn = conn.execute(
                "SELECT conversation_id, status, revision, attempt, claim_expires_at, "
                "clock_timestamp() AS now, graph_context_execution, sequence "
                "FROM agent.turn "
                "WHERE world_id=%s AND turn_id=%s FOR UPDATE",
                (world_id, turn_id),
            ).fetchone()
            if turn is None or turn[0] != conversation_id:
                raise ApplicationStateNotFoundError("trace turn is unavailable in this World conversation")
            if (
                turn[1] != "running" or turn[2] != expected_revision
                or turn[3] != attempt or turn[4] is None or turn[4] <= turn[5]
            ):
                raise ApplicationStateConflictError("trace append is fenced by a stale or expired claim")
            row = _trace_row(conn, turn_id, attempt)
            if row is None:
                raise ApplicationStateNotFoundError("context trace was not started")
            trace = _load_trace(row[1])
            if trace.trace_id != trace_id or trace.world_id != world_id or trace.conversation_id != conversation_id or trace.turn_id != turn_id or trace.attempt != attempt:
                raise ApplicationStateConflictError("context trace identity changed")
            if trace.closed_at is not None:
                raise ApplicationStateConflictError("context trace is already closed")
            if isinstance(observation, TraceAuthoredGraphReferenceV1):
                validate_authored_reference_observation(observation, turn[6], trace)
            if observation.sequence < len(trace.observations):
                if trace.observations[observation.sequence] == observation:
                    return trace
                raise ApplicationStateConflictError("trace observation differs from the recorded event")
            if observation.sequence != len(trace.observations):
                raise ApplicationStateConflictError("trace observation sequence is stale")
            if isinstance(observation, TraceSourcePassage):
                raise ApplicationStateValidationError(
                    "source passage observations must be committed with their validated source-read event"
                )
            if isinstance(observation, TracePromptReference):
                validate_prompt_authorization(observation, turn[6], trace.execution_start_sequence)
                if any(isinstance(item, TracePromptReference) and item.provider_attempt_id == observation.provider_attempt_id
                       for item in trace.observations):
                    raise ApplicationStateValidationError("provider request already has a prompt reference")
            if isinstance(observation, TraceGraphTool):
                _validate_graph_tool_observation(observation, turn[6])
            if isinstance(observation, TraceContextSnapshot):
                if not _historical_sources_available(conn, trace, observation, turn[7], turn[6]):
                    incomplete = TurnContextTraceV1.model_validate({
                        **trace.model_dump(mode="python"),
                        "capture_status": "incomplete",
                        "capture_failure_code": trace.capture_failure_code or "historical_source_unavailable",
                    })
                    _save_trace(conn, incomplete)
                    return incomplete
            try:
                updated = TurnContextTraceV1.model_validate({
                    **trace.model_dump(mode="python"),
                    "observations": [*trace.observations, observation],
                })
                _save_trace(conn, updated)
            except (ValueError, ApplicationStateValidationError) as exc:
                if "1 MiB per-attempt ceiling" in str(exc):
                    incomplete = TurnContextTraceV1.model_validate({
                        **trace.model_dump(mode="python"),
                        "capture_status": "incomplete",
                        "capture_failure_code": trace.capture_failure_code or "trace_size_limit",
                    })
                    _save_trace(conn, incomplete)
                    return incomplete
                raise ApplicationStateValidationError(str(exc)) from exc
            return updated

    def mark_incomplete(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID, failure_code: str,
    ) -> TurnContextTraceV1:
        from application_state.agent_conversation.service import _ready_dsn

        with unit_of_work(_ready_dsn()) as conn:
            turn = conn.execute(
                "SELECT conversation_id, status, revision, attempt, claim_expires_at, "
                "clock_timestamp() AS now FROM agent.turn "
                "WHERE world_id=%s AND turn_id=%s FOR UPDATE",
                (world_id, turn_id),
            ).fetchone()
            if turn is None or turn[0] != conversation_id:
                raise ApplicationStateNotFoundError("trace turn is unavailable in this World conversation")
            if (
                turn[1] != "running" or turn[2] != expected_revision
                or turn[3] != attempt or turn[4] is None or turn[4] <= turn[5]
            ):
                raise ApplicationStateConflictError("trace failure marker is fenced by a stale claim")
            row = _trace_row(conn, turn_id, attempt)
            if row is None:
                raise ApplicationStateNotFoundError("context trace was not started")
            trace = _load_trace(row[1])
            if trace.trace_id != trace_id:
                raise ApplicationStateConflictError("context trace identity changed")
            if trace.capture_status == "incomplete":
                if trace.capture_failure_code == failure_code:
                    return trace
                raise ApplicationStateConflictError("context trace already has a different capture failure")
            incomplete = TurnContextTraceV1.model_validate({
                **trace.model_dump(mode="python"),
                "capture_status": "incomplete", "capture_failure_code": failure_code,
            })
            _save_trace(conn, incomplete)
            return incomplete

    def read_historical_passage(self, reference: TraceHistoricalSourceReferenceV1) -> TraceSourcePassage:
        """Read one bounded exact capture, never all attempts or current Graph evidence."""
        from application_state.agent_conversation.service import _ready_dsn

        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(
                "SELECT CASE WHEN octet_length(capture.payload::text) <= %s "
                "THEN capture.payload ELSE NULL END "
                "FROM agent.turn source JOIN agent.turn_context_trace capture "
                "ON capture.turn_id=source.turn_id "
                "WHERE source.world_id=%s AND source.conversation_id=%s AND source.turn_id=%s "
                "AND capture.attempt=%s AND capture.trace_id=%s",
                (MAX_CONTEXT_TRACE_BYTES, reference.world_id, reference.conversation_id,
                 reference.turn_id, reference.attempt, reference.trace_id),
            ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("historical passage is unavailable")
        if row[0] is None:
            raise ApplicationStateValidationError("historical trace exceeds its capture bound")
        trace = _load_trace(row[0])
        if (trace.world_id != reference.world_id or trace.conversation_id != reference.conversation_id
                or trace.turn_id != reference.turn_id or trace.trace_id != reference.trace_id
                or trace.attempt != reference.attempt):
            raise ApplicationStateValidationError("historical trace binding is invalid")
        matches = [item for item in trace.observations if isinstance(item, TraceSourcePassage)
                   and item.world_id == reference.world_id
                   and item.source_read_event_id == reference.source_read_event_id
                   and item.source_read_id == reference.source_read_id
                   and item.content_sha256 == reference.content_sha256]
        if len(matches) != 1:
            raise ApplicationStateNotFoundError("historical passage is unavailable")
        # _load_trace validates the actual UTF8 digest and exact character count.
        return matches[0]

    def list_attempts(
        self, *, world_id: str, turn_id: UUID,
    ) -> list[TurnContextTraceV1]:
        from application_state.agent_conversation.service import _ready_dsn

        with unit_of_work(_ready_dsn()) as conn:
            turn = conn.execute(
                "SELECT graph_context_execution, conversation_id FROM agent.turn WHERE world_id=%s AND turn_id=%s",
                (world_id, turn_id),
            ).fetchone()
            if turn is None:
                raise ApplicationStateNotFoundError("trace turn is unavailable in this World")
            rows = conn.execute(
                "SELECT payload, attempt FROM agent.turn_context_trace "
                "WHERE turn_id=%s ORDER BY attempt",
                (turn_id,),
            ).fetchall()
        traces = [_load_trace(row[0]) for row in rows]
        for trace, row in zip(traces, rows, strict=True):
            if trace.attempt != row[1]:
                raise ApplicationStateValidationError("stored trace attempt differs from its row")
            if trace.world_id != world_id or trace.turn_id != turn_id or trace.conversation_id != turn[1]:
                raise ApplicationStateValidationError("stored trace binding differs from its turn")
            for observation in trace.observations:
                if isinstance(observation, TraceAuthoredGraphReferenceV1):
                    validate_authored_reference_observation(observation, turn[0], trace)
                if isinstance(observation, TracePromptReference):
                    validate_prompt_authorization(observation, turn[0], trace.execution_start_sequence)
        return traces


def _historical_sources_available(conn, trace: TurnContextTraceV1,
                                  snapshot: TraceContextSnapshot, current_sequence: int, execution=None) -> bool:
    """Validate observational references without creating Graph/read authority."""
    for material in snapshot.materials:
        matched_passages = []
        for ref in material.historical_source_reads:
            if ref.world_id != trace.world_id or ref.conversation_id != trace.conversation_id:
                return False
            same_turn = False
            input_reference = snapshot.snapshot_kind == 'provider_input' or (
                snapshot.snapshot_kind == 'validated_answer' and any(ref == prior_ref
                    for prior in trace.observations if isinstance(prior,TraceContextSnapshot)
                    and prior.stage == 'before' and prior.snapshot_kind == 'provider_input'
                    for item in prior.materials for prior_ref in item.historical_source_reads))
            if isinstance(execution,dict) and input_reference:
                from .authored_graph_references import POLICY
                policy=execution.get('policy',{})
                events=execution.get('events',[])
                writer=policy.get('provider_roles',{}).get('writer',{})
                current_providers={e.get('provider_attempt_id'):e for e in events
                    if e.get('kind')=='provider_attempt_authorized_v3' and e.get('sequence',-1)>=trace.execution_start_sequence
                    and all(e.get(k)==writer.get(k) for k in ('provider','model','api_mode'))}
                same_turn=(policy.get('authored_graph_reference_policy')==POLICY and ref.turn_id==trace.turn_id
                    and ref.attempt<trace.attempt and any(e.get('kind')=='build_authored_provider_inclusion_v1'
                        and str(ref.source_read_event_id) in e.get('source_read_event_ids',[])
                        and e.get('provider_attempt_id') in current_providers
                        and e.get('envelope_sha256')==current_providers[e['provider_attempt_id']].get('envelope_sha256')
                        for e in events))
            row = conn.execute(
                "SELECT historical.payload FROM agent.turn source "
                "JOIN agent.turn_context_trace historical ON historical.turn_id=source.turn_id "
                "WHERE source.world_id=%s AND source.conversation_id=%s "
                "AND source.turn_id=%s AND (source.sequence < %s OR "
                "(source.turn_id=%s AND historical.attempt < %s AND %s)) "
                "AND historical.attempt=%s AND historical.trace_id=%s",
                (trace.world_id, trace.conversation_id, ref.turn_id, current_sequence,
                 trace.turn_id,trace.attempt,same_turn,ref.attempt,ref.trace_id),
            ).fetchone()
            if row is None:
                return False
            try:
                source_trace = _load_trace(row[0])
            except ApplicationStateValidationError:
                return False
            if (source_trace.world_id != ref.world_id or source_trace.conversation_id != ref.conversation_id
                    or source_trace.turn_id != ref.turn_id or source_trace.attempt != ref.attempt
                    or source_trace.trace_id != ref.trace_id):
                return False
            passages = [
                item for item in source_trace.observations
                if isinstance(item, TraceSourcePassage)
                and item.source_read_event_id == ref.source_read_event_id
                and item.source_read_id == ref.source_read_id
                and item.content_sha256 == ref.content_sha256
            ]
            if len(passages) != 1:
                return False
            matched_passages.extend(passages)
        if material.historical_source_reads and material.route is not None and not any(
            all(getattr(material.route, key) in (None, getattr(passage, key))
                for key in ("world_id", "graph_revision", "anchor_id", "evidence_ref_id",
                            "source_artifact_id", "source_revision_id", "content_sha256"))
            for passage in matched_passages
        ):
            return False
    return True


def _validate_graph_tool_observation(observation: TraceGraphTool, execution: object) -> None:
    """Tie the bounded summary to the authoritative graph execution ledger."""
    events = execution.get("events", []) if isinstance(execution, dict) else []
    matching = [
        event for event in events
        if isinstance(event, dict)
        and event.get("kind") in {"validated_graph_operation", "validated_graph_operation_v3"}
        and event.get("event_id") == str(observation.execution_event_id)
    ]
    if len(matching) != 1:
        raise ApplicationStateValidationError(
            "graph trace observation must reference one recorded validated operation"
        )
    event = matching[0]
    if event.get("operation") != "expand_graph_retrieval":
        raise ApplicationStateValidationError("graph trace tool does not match its execution event")
    if (
        event.get("request_arguments_sha256") != observation.request_arguments_sha256
        or event.get("result_packet_sha256") != observation.result_packet_sha256
    ):
        raise ApplicationStateValidationError(
            "graph trace request or result digest differs from its execution receipt"
        )
    result = observation.result
    if (
        event.get("graph_revision") != result.graph_revision
        or event.get("coverage_status") != result.coverage_status
        or event.get("truncated") is True and result.coverage_status != "incomplete"
    ):
        raise ApplicationStateValidationError(
            "graph trace result scope or coverage differs from its execution receipt"
        )
    for field, event_field in (
        ("claim_ids", "assertion_ids"),
        ("relationship_ids", "relationship_ids"),
        ("evidence_ref_ids", "evidence_ref_ids"),
    ):
        recorded = event.get(event_field, [])
        projected = getattr(result, field)
        if (
            result.total_counts.model_dump()[
                "claims" if field == "claim_ids" else
                "relationships" if field == "relationship_ids" else "evidence_refs"
            ] != len(recorded)
            or not set(projected).issubset(set(recorded))
        ):
            raise ApplicationStateValidationError(
                "graph trace result IDs differ from the authoritative execution receipt"
            )


def validate_prompt_authorization(observation: TracePromptReference, execution: object, start_sequence: int) -> None:
    events = execution.get("events", []) if isinstance(execution, dict) else []
    matches = [event for event in events if isinstance(event, dict)
        and event.get("kind") in {"provider_attempt_authorized", "provider_attempt_authorized_v2", "provider_attempt_authorized_v3", "provider_attempt_authorized_v4", "plan_jev_provider_authorized_v1", "plan_requested_work_authorized_v1", "plan_requested_work_authorized_v2", "plan_jev_writer_authorized_v1", "plan_jev_writer_authorized_v2"}
        and event.get("provider_attempt_id") == str(observation.provider_attempt_id)
        and event.get("sequence", -1) >= start_sequence]
    if len(matches) != 1 or any(matches[0].get(key) != expected for key, expected in {
        "provider": observation.provider, "model": observation.model,
        "api_mode": observation.api_mode, "serializer_version": observation.serializer_version,
        "envelope_sha256": observation.payload_sha256,
    }.items()):
        raise ApplicationStateValidationError("prompt reference differs from this attempt's durable provider authorization")


def validate_authored_reference_observation(observation: TraceAuthoredGraphReferenceV1, execution: object, trace: TurnContextTraceV1) -> None:
    """An observation must name the complete immutable event in this exact turn."""
    event = observation.execution_event.model_dump(mode='json', by_alias=True)
    events = execution.get('events', []) if isinstance(execution, dict) else []
    matching = [item for item in events if isinstance(item, dict) and item.get('event_id') == event['event_id']]
    if len(matching) != 1 or json.dumps(matching[0], sort_keys=True, separators=(',', ':'), allow_nan=False) != json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False):
        raise ApplicationStateValidationError('authored reference observation differs from its exact turn ledger event')
    from .types import BuildAuthoredReferencesCapturedV1
    captured = observation.execution_event
    if isinstance(captured, BuildAuthoredReferencesCapturedV1) and (
        captured.turn_id != trace.turn_id or captured.conversation_id != trace.conversation_id
        or any(ref.managed_world_id != trace.world_id for ref in captured.references.references)
    ):
        raise ApplicationStateValidationError('authored reference capture belongs to another trace owner')
    if not isinstance(captured, BuildAuthoredReferencesCapturedV1) and captured.sequence < trace.execution_start_sequence:
        raise ApplicationStateValidationError('authored reference observation predates this physical attempt')
    if any(isinstance(old, TraceAuthoredGraphReferenceV1)
        and old.execution_event.event_id == captured.event_id and old.sequence != observation.sequence
        for old in trace.observations):
        raise ApplicationStateValidationError('authored reference event already has an observation in this attempt')
