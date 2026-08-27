"""DungeonBuddy-owned AgentRuntime execution port.

Product orchestration builds ``AgentRuntimeInvocation`` and consumes
``AgentRuntimeResult``. Harness adapters (Hermes in A2) live outside this
module and must not leak host/wire types into it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

WORLD_GRAPH_READ_POLICY_ID = "world_graph_read_v1"

AgentRuntimeStatus = Literal["ok", "error"]
AgentRuntimeToolEventState = Literal["start", "completion", "error"]


@dataclass(frozen=True, slots=True)
class AgentRuntimeDescriptor:
    runtime_id: str
    trace_backend: str
    trace_runtime: str
    trace_mode: str


@dataclass(frozen=True, slots=True)
class AgentCapabilityPolicy:
    policy_id: str


@dataclass(frozen=True, slots=True)
class AgentRunOptions:
    runtime_session_id: str | None = None
    execution_root: Path | None = None


@dataclass(frozen=True, slots=True)
class AgentWorldScope:
    world_id: str
    campaign_id: str
    focus: Mapping[str, Any]
    admissibility: str
    revision_id: str


@dataclass(frozen=True, slots=True)
class AgentRetrievalSession:
    session_id: str
    packet: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AgentContextPacket:
    world_scope: AgentWorldScope
    retrieval_session: AgentRetrievalSession | None = None


@dataclass(frozen=True, slots=True)
class AgentRuntimeInvocation:
    thread_id: str | None
    turn_id: str | None
    message: str
    conversation_history: Sequence[Mapping[str, str]] | None
    context_packet: AgentContextPacket
    capability_policy: AgentCapabilityPolicy
    run_options: AgentRunOptions


@dataclass(frozen=True, slots=True)
class AgentRuntimeToolEvent:
    """Harness-neutral tool observation.

    Capability metadata lives in ``attributes`` only. No raw tool args or
    raw tool results belong here.
    """

    tool_name: str
    state: AgentRuntimeToolEventState
    duration_ms: float | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def _attr(self, key: str, default: Any = None) -> Any:
        if key in self.attributes:
            return self.attributes[key]
        return default

    @property
    def world_id(self) -> str | None:
        value = self._attr("world_id")
        return None if value is None else str(value)

    @property
    def campaign_id(self) -> str | None:
        value = self._attr("campaign_id")
        return None if value is None else str(value)

    @property
    def focus(self) -> Mapping[str, Any] | None:
        value = self._attr("focus")
        return value if isinstance(value, Mapping) else None

    @property
    def admissibility(self) -> str | None:
        value = self._attr("admissibility")
        return None if value is None else str(value)

    @property
    def revision_pin(self) -> str | None:
        value = self._attr("revision_pin")
        return None if value is None else str(value)

    @property
    def bounded_ids(self) -> Any:
        return self._attr("bounded_ids", {})

    @property
    def retrieval_schema(self) -> str | None:
        value = self._attr("retrieval_schema")
        return None if value is None else str(value)

    @property
    def outcome(self) -> str | None:
        value = self._attr("outcome")
        return None if value is None else str(value)

    @property
    def matched_node_ids(self) -> Any:
        return self._attr("matched_node_ids", [])

    @property
    def relationship_ids(self) -> Any:
        return self._attr("relationship_ids", [])

    @property
    def source_anchor_ids(self) -> Any:
        return self._attr("source_anchor_ids", [])

    @property
    def diagnostic_codes(self) -> Any:
        return self._attr("diagnostic_codes", [])


@dataclass(frozen=True, slots=True)
class AgentRuntimeResult:
    status: AgentRuntimeStatus
    final_text: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    runtime_session_id: str | None = None
    answer_scope: str | None = None
    tool_events: list[AgentRuntimeToolEvent] = field(default_factory=list)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    telemetry_warnings: list[str] = field(default_factory=list)
    observed_model_call_count: int | None = None
    context_updates: dict[str, Any] = field(default_factory=dict)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class AgentRuntime(Protocol):
    descriptor: AgentRuntimeDescriptor

    def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
        """Execute one Agent turn. Honest synchronous v1 — no handle facade."""


HERMES_RUNTIME_DESCRIPTOR = AgentRuntimeDescriptor(
    runtime_id="hermes",
    trace_backend="hermes",
    trace_runtime="process_isolated",
    trace_mode="hermes_graph_agent",
)

WORLD_GRAPH_READ_POLICY = AgentCapabilityPolicy(policy_id=WORLD_GRAPH_READ_POLICY_ID)

UNSUPPORTED_CAPABILITY_POLICY = "unsupported_capability_policy"
