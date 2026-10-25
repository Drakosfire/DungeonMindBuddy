"""Bounded, non-authoritative observations of one Agent turn attempt."""

from __future__ import annotations

from application_state.agent_conversation.identifier_limits import (
    GRAPH_EVIDENCE_REF_ID_MAX_CHARS,
)

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

MAX_CONTEXT_TRACE_BYTES = 1_048_576
CONTEXT_TRACE_TERMINAL_RESERVE_BYTES = 4096
MAX_SOURCE_PASSAGE_CHARS_PER_TURN = 96_000
MAX_SOURCE_PASSAGE_CHARS_PER_READ = 12_000
SafeTraceCode = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class TraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TraceRoute(TraceModel):
    route_id: str = Field(min_length=1, max_length=256)
    world_id: str = Field(min_length=1, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    node_id: str | None = Field(default=None, max_length=256)
    anchor_id: str | None = Field(default=None, max_length=256)
    evidence_ref_id: str | None = Field(default=None, max_length=GRAPH_EVIDENCE_REF_ID_MAX_CHARS)
    source_artifact_id: str | None = Field(default=None, max_length=256)
    source_revision_id: str | None = Field(default=None, max_length=256)
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class TraceEvent(TraceModel):
    sequence: int = Field(strict=True, ge=0, le=2047)
    elapsed_ms: float = Field(ge=0)


class TraceCapturedSourceReference(TraceModel):
    source_read_id: str = Field(min_length=1, max_length=128)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class TraceHistoricalSourceReferenceV1(TraceModel):
    """Exact earlier passage provenance; never current-turn read authority."""

    schema_version: Literal["dmb_trace_historical_source_ref_v1"] = Field(
        default="dmb_trace_historical_source_ref_v1", alias="schema",
    )
    world_id: str = Field(min_length=1, max_length=256)
    conversation_id: UUID
    turn_id: UUID
    attempt: int = Field(strict=True, ge=1)
    trace_id: UUID
    source_read_event_id: UUID
    source_read_id: str = Field(min_length=1, max_length=128)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class TraceContextMaterial(TraceModel):
    item_id: str = Field(min_length=1, max_length=256)
    state: Literal["model_context", "retrieval_route"]
    role: Literal["user", "assistant", "source", "fact"]
    text: str | None = None
    route: TraceRoute | None = None
    source_read_event_id: UUID | None = None
    source_reads: list[TraceCapturedSourceReference] = Field(default_factory=list, max_length=8)
    historical_source_reads: list[TraceHistoricalSourceReferenceV1] = Field(default_factory=list, max_length=2048)

    @model_serializer(mode="wrap")
    def serialize_material(self, handler):
        payload = handler(self)
        if not self.historical_source_reads:
            payload.pop("historical_source_reads", None)
        return payload

    @model_validator(mode="after")
    def validate_representation(self) -> TraceContextMaterial:
        if self.state == "retrieval_route":
            if (self.route is None or self.text is not None or self.source_read_event_id is not None
                    or self.source_reads or self.historical_source_reads):
                raise ValueError("retrieval route must carry a route handle, not present prose")
        elif self.role == "source":
            current = self.source_read_event_id is not None and bool(self.source_reads)
            historical = bool(self.historical_source_reads)
            if (self.text is not None or current == historical or
                    historical and (self.source_read_event_id is not None or self.source_reads)):
                raise ValueError("present source material must reference its captured source read")
            if len({ref.source_read_id for ref in self.source_reads}) != len(self.source_reads):
                raise ValueError("present source read references must be unique")
            identities = [
                (ref.turn_id, ref.attempt, ref.trace_id, ref.source_read_event_id, ref.source_read_id)
                for ref in self.historical_source_reads
            ]
            if len(identities) != len(set(identities)):
                raise ValueError("historical source references must be unique")
        elif (self.text is None or self.route is not None or self.source_read_event_id is not None
              or self.source_reads or self.historical_source_reads):
            raise ValueError("visible context material must carry only its visible text")
        return self


class TraceContextSnapshot(TraceEvent):
    kind: Literal["context_snapshot"] = "context_snapshot"
    stage: Literal["before", "after"]
    materials: list[TraceContextMaterial] = Field(max_length=512)


class TraceContextDecision(TraceEvent):
    kind: Literal["context_decision"] = "context_decision"
    action: Literal["retrieved", "retained", "expanded", "compacted", "pruned"]
    item_ids: list[str] = Field(max_length=512)
    reason_code: Literal[
        "question_relevance", "followup_detail_needed", "coverage_gap",
        "context_budget", "duplicate", "superseded", "route_preserved",
        "retrieval_sufficient", "unavailable",
    ]
    policy_version: str = Field(min_length=1, max_length=128)


class TraceGraphSearchRequest(TraceModel):
    operation: Literal["search"]
    query_text: str = Field(min_length=1, max_length=512)
    seed_node_ids: list[str] = Field(max_length=8)
    max_nodes: int | None = Field(default=None, strict=True, ge=1, le=12)
    max_relationships: int | None = Field(default=None, strict=True, ge=1, le=24)
    max_claims: int | None = Field(default=None, strict=True, ge=1, le=32)
    max_source_anchors: int | None = Field(default=None, strict=True, ge=1, le=32)


class TraceGraphObjectRequest(TraceModel):
    operation: Literal["object"]
    target_node_id: str = Field(min_length=1, max_length=256)
    max_nodes: int | None = Field(default=None, strict=True, ge=1, le=12)
    max_relationships: int | None = Field(default=None, strict=True, ge=1, le=24)
    max_claims: int | None = Field(default=None, strict=True, ge=1, le=32)
    max_source_anchors: int | None = Field(default=None, strict=True, ge=1, le=32)


class TraceGraphNeighborhoodRequest(TraceModel):
    operation: Literal["neighborhood"]
    seed_node_ids: list[str] = Field(min_length=1, max_length=8)
    depth: Literal[1, 2]
    max_nodes: int | None = Field(default=None, strict=True, ge=1, le=12)
    max_relationships: int | None = Field(default=None, strict=True, ge=1, le=24)
    max_claims: int | None = Field(default=None, strict=True, ge=1, le=32)
    max_source_anchors: int | None = Field(default=None, strict=True, ge=1, le=32)


class TraceGraphSupportRequest(TraceModel):
    operation: Literal["support"]
    target_node_id: str = Field(min_length=1, max_length=256)
    max_source_anchors: int | None = Field(default=None, strict=True, ge=1, le=32)


class TraceGraphObservationsRequest(TraceModel):
    operation: Literal["observations"]
    observation_ids: list[str] = Field(min_length=1, max_length=8)
    max_bytes: int = Field(strict=True, ge=256, le=262144)


TraceGraphOperationRequest = Annotated[
    TraceGraphSearchRequest | TraceGraphObjectRequest
    | TraceGraphNeighborhoodRequest | TraceGraphSupportRequest | TraceGraphObservationsRequest,
    Field(discriminator="operation"),
]


class TraceGraphNode(TraceModel):
    node_id: str = Field(min_length=1, max_length=256)
    label: str = Field(min_length=1, max_length=512)
    kind: str = Field(min_length=1, max_length=128)


class TraceGraphResultCounts(TraceModel):
    nodes: int = Field(strict=True, ge=0)
    relationships: int = Field(strict=True, ge=0)
    claims: int = Field(strict=True, ge=0)
    evidence_refs: int = Field(strict=True, ge=0)


class TraceGraphResultProjection(TraceModel):
    """Bounded result metadata; source passage text is stored separately."""

    outcome: Literal["enough", "partial", "truncated", "empty", "denied", "unavailable"]
    graph_revision: str = Field(min_length=1, max_length=256)
    coverage_status: Literal["complete", "incomplete"]
    projection_status: Literal["complete", "limited"]
    nodes: list[TraceGraphNode] = Field(max_length=64)
    relationship_ids: list[str] = Field(max_length=128)
    claim_ids: list[str] = Field(max_length=128)
    evidence_ref_ids: list[str] = Field(max_length=128)
    returned_counts: TraceGraphResultCounts
    total_counts: TraceGraphResultCounts
    omission_codes: list[SafeTraceCode] = Field(max_length=16)

    @model_validator(mode="after")
    def validate_projection_completeness(self) -> TraceGraphResultProjection:
        returned = {
            "nodes": len(self.nodes),
            "relationships": len(self.relationship_ids),
            "claims": len(self.claim_ids),
            "evidence_refs": len(self.evidence_ref_ids),
        }
        for field, count in returned.items():
            if getattr(self.returned_counts, field) != count:
                raise ValueError(f"returned {field} count does not match its bounded projection")
            if getattr(self.total_counts, field) < count:
                raise ValueError(f"total {field} count is below the returned count")
        limited = any(
            getattr(self.total_counts, field) > count
            for field, count in returned.items()
        )
        if (self.projection_status == "limited") != limited:
            raise ValueError("limited projection status must describe omitted result rows")
        if self.projection_status == "limited" and not self.omission_codes:
            raise ValueError("limited projection requires a safe omission code")
        if self.projection_status == "complete" and self.omission_codes:
            raise ValueError("complete projection cannot carry omission codes")
        for field in ("relationship_ids", "claim_ids", "evidence_ref_ids", "omission_codes"):
            values = getattr(self, field)
            if any(not value.strip() for value in values) or len(values) != len(set(values)):
                raise ValueError(f"{field} must contain unique nonblank values")
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node projection IDs must be unique")
        if self.outcome in {"partial", "truncated"} and self.coverage_status != "incomplete":
            raise ValueError("partial retrieval outcome requires incomplete coverage")
        return self


class TraceGraphTool(TraceEvent):
    """A bounded, non-authoritative view onto a validated graph operation."""

    kind: Literal["graph_tool"] = "graph_tool"
    tool_name: Literal["expand_graph_retrieval"]
    execution_event_id: UUID
    request_arguments_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope_mode: Literal["campaign", "world"]
    campaign_id: str | None = Field(default=None, max_length=256)
    revision_pin: str = Field(min_length=1, max_length=256)
    request: TraceGraphOperationRequest
    result: TraceGraphResultProjection
    duration_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_graph_revision(self) -> TraceGraphTool:
        if self.revision_pin != self.result.graph_revision:
            raise ValueError("graph result revision differs from its request pin")
        if (self.scope_mode == "campaign") != (self.campaign_id is not None):
            raise ValueError("campaign ID must match the recorded graph scope")
        return self


class TraceSourcePassage(TraceEvent):
    """Exact validated text returned by one admitted source read."""

    kind: Literal["source_passage"] = "source_passage"
    source_read_event_id: UUID
    read_call_id: UUID
    world_id: str = Field(min_length=1, max_length=256)
    graph_revision: str = Field(min_length=1, max_length=256)
    source_read_id: str = Field(min_length=1, max_length=128)
    anchor_id: str = Field(min_length=1, max_length=256)
    evidence_ref_id: str = Field(min_length=1, max_length=GRAPH_EVIDENCE_REF_ID_MAX_CHARS)
    source_artifact_id: str = Field(min_length=1, max_length=256)
    source_name: str | None = None  # Display metadata, never source/evidence authority.
    source_revision_id: str = Field(min_length=1, max_length=256)
    line_start: int | None = Field(default=None, strict=True, ge=1)
    line_end: int | None = Field(default=None, strict=True, ge=1)
    outcome: Literal["enough", "partial", "truncated"]
    returned_chars: int = Field(strict=True, ge=1, le=MAX_SOURCE_PASSAGE_CHARS_PER_READ)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1, max_length=MAX_SOURCE_PASSAGE_CHARS_PER_READ)

    @model_validator(mode="after")
    def validate_exact_passage(self) -> TraceSourcePassage:
        if len(self.text) != self.returned_chars:
            raise ValueError("captured passage character count differs from the validated read")
        if hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("captured passage digest differs from the validated read")
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("captured passage line bounds must be supplied together")
        if self.line_start is not None and self.line_end < self.line_start:
            raise ValueError("captured passage line range is reversed")
        return self


class TraceSourceReuse(TraceSourcePassage):
    """Current included bytes reused from a completed original producer."""
    kind: Literal["source_passage_reuse"] = "source_passage_reuse"
    origin_turn_id: UUID
    origin_attempt: int = Field(strict=True, ge=1)
    origin_read_event_id: UUID
    origin_provider_attempt_id: UUID


class TraceProviderCall(TraceEvent):
    kind: Literal["provider_call"] = "provider_call"
    provider_attempt_id: UUID | None = None
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    outcome: Literal["authorized", "response_received", "denied", "failed", "unknown"]
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    input_upper_bound: int | None = Field(default=None, ge=0)
    input_estimator: Literal["utf8_json_bytes_plus_64_per_node_v1"] | None = None
    duration_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_input_accounting(self) -> TraceProviderCall:
        if (self.input_upper_bound is None) != (self.input_estimator is None):
            raise ValueError("input estimate requires both bound and estimator")
        return self


class TracePromptReference(TraceEvent):
    """Private blob handle, validated against the durable dispatch authorization."""
    kind: Literal["prompt_reference"] = "prompt_reference"
    evidence_id: UUID
    provider_attempt_id: UUID
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    api_mode: str = Field(min_length=1, max_length=128)
    serializer_version: str = Field(min_length=1, max_length=128)
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    payload_utf8_bytes: int = Field(gt=0, le=16 * 1024 * 1024)


class TraceFailure(TraceEvent):
    diagnostic_id: UUID | None = None
    diagnostic_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    exception_type: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
    cause_type: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
    stage: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["failure"] = "failure"
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    phase: Literal[
        "graph_retrieval", "source_read", "context_build", "provider",
        "projection", "delivery", "trace_capture",
    ]

    @model_validator(mode="after")
    def diagnostic_bundle(self):
        fields = (self.diagnostic_id, self.diagnostic_sha256, self.exception_type, self.cause_type, self.stage)
        if any(value is not None for value in fields) and not all(value is not None for value in fields):
            raise ValueError("Failure diagnostic requires its exact complete reference")
        return self


ContextTraceObservation = Annotated[
    TraceContextSnapshot | TraceContextDecision | TraceGraphTool
    | TraceSourcePassage | TraceSourceReuse | TraceProviderCall | TracePromptReference | TraceFailure,
    Field(discriminator="kind"),
]


class TurnContextTraceV1(TraceModel):
    schema_version: Literal["dmb_turn_context_trace_v1"] = Field(
        default="dmb_turn_context_trace_v1", alias="schema"
    )
    trace_id: UUID
    world_id: str = Field(min_length=1, max_length=256)
    conversation_id: UUID
    turn_id: UUID
    attempt: int = Field(strict=True, ge=1)
    execution_start_sequence: int = Field(strict=True, ge=0, le=2048)
    started_at: datetime
    closed_at: datetime | None = None
    terminal_status: Literal["completed", "failed", "interrupted"] | None = None
    capture_status: Literal["recording", "complete", "incomplete"] = "recording"
    capture_failure_code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    observations: list[ContextTraceObservation] = Field(max_length=2048)

    @model_validator(mode="after")
    def validate_order_scope_and_size(self) -> TurnContextTraceV1:
        if [item.sequence for item in self.observations] != list(range(len(self.observations))):
            raise ValueError("trace observations must have contiguous ordered sequences")
        if any(a.elapsed_ms > b.elapsed_ms for a, b in zip(self.observations, self.observations[1:])):
            raise ValueError("trace elapsed times must be monotonic")
        if (self.closed_at is None) != (self.terminal_status is None):
            raise ValueError("trace terminal status and closure time must be set together")
        if self.closed_at is not None and self.closed_at < self.started_at:
            raise ValueError("trace cannot close before it starts")
        if (self.capture_status == "incomplete") != (self.capture_failure_code is not None):
            raise ValueError("incomplete capture requires one explicit safe failure code")
        passages = [item for item in self.observations if isinstance(item, TraceSourcePassage)]
        if sum(item.returned_chars for item in passages) > MAX_SOURCE_PASSAGE_CHARS_PER_TURN:
            raise ValueError("captured source passages exceed the per-turn character ceiling")
        captured: dict[UUID, list[TraceSourcePassage]] = {}
        for item in self.observations:
            if isinstance(item, TraceSourcePassage) and item.world_id != self.world_id:
                raise ValueError("source passage must belong to the trace World")
            if isinstance(item, TraceSourcePassage):
                captured.setdefault(item.source_read_event_id, []).append(item)
            if isinstance(item, TraceContextSnapshot):
                if any(
                    material.route is not None and material.route.world_id != self.world_id
                    for material in item.materials
                ):
                    raise ValueError("context route must belong to the trace World")
                for material in item.materials:
                    if material.state != "model_context" or material.role != "source":
                        continue
                    if material.historical_source_reads:
                        if any(ref.world_id != self.world_id or ref.conversation_id != self.conversation_id
                               for ref in material.historical_source_reads):
                            raise ValueError("historical source reference must belong to the trace World conversation")
                        # Exact passage and earlier-turn validation belongs to the
                        # APP write boundary; historical reads are not new admission.
                        continue
                    passages = captured.get(material.source_read_event_id, [])
                    if not passages:
                        raise ValueError("present source context requires an earlier captured same-turn source read")
                    passage_by_id = {passage.source_read_id: passage for passage in passages}
                    if any(ref.source_read_id not in passage_by_id or
                           passage_by_id[ref.source_read_id].content_sha256 != ref.content_sha256
                           for ref in material.source_reads):
                        raise ValueError("present source context must identify captured passage IDs and digests")
                    passages = [passage_by_id[ref.source_read_id] for ref in material.source_reads]
                    if material.route is not None and not any(
                        all(getattr(material.route, key) in (None, getattr(passage, key))
                            for key in ("world_id", "graph_revision", "anchor_id", "evidence_ref_id",
                                        "source_artifact_id", "source_revision_id", "content_sha256"))
                        for passage in passages
                    ):
                        raise ValueError("present source context route differs from its captured source scope")
        encoded = json.dumps(
            self.model_dump(mode="json", by_alias=True), ensure_ascii=True,
            sort_keys=True, allow_nan=False,
        ).encode("utf-8")
        ceiling = MAX_CONTEXT_TRACE_BYTES - (
            (CONTEXT_TRACE_TERMINAL_RESERVE_BYTES if self.capture_status == "recording"
             else CONTEXT_TRACE_TERMINAL_RESERVE_BYTES // 2)
            if self.closed_at is None else 0
        )
        if len(encoded) > ceiling:
            raise ValueError("trace exceeds the explicit 1 MiB per-attempt ceiling")
        return self
