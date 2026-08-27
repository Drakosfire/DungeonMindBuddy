"""A2 AgentRuntime boundary: product consumes the port, not Hermes host types."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from apps.live_control_server.services.agent_runtime import (
    HERMES_RUNTIME_DESCRIPTOR,
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY,
    WORLD_GRAPH_READ_POLICY_ID,
    AgentCapabilityPolicy,
    AgentContextPacket,
    AgentRetrievalSession,
    AgentRunOptions,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
    AgentWorldScope,
)
from apps.live_control_server.services.hermes_graph_query import (
    build_hermes_graph_product_response,
    build_hermes_graph_turn_request,
    run_hermes_graph_query,
)
from apps.live_control_server.services.live_agent_loop import process_live_query

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "apps/live_control_server/services"

READY_ENVELOPE = {
    "schema": "dmb_agent_world_graph_query_context_v1",
    "status": "ready",
    "world_id": "world:eldyrwild",
    "campaign_id": "campaign:c1",
    "revision_id": "revision:resolved-server",
    "head_revision_id": "revision:resolved-server",
    "is_head": True,
    "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
    "admissibility": "gm",
    "query_text": "Where is Tripod?",
    "matched_node_ids": ["threat:tripod-null-calf"],
    "nodes": [],
    "relationships": [],
    "attributes": [],
    "projection_truncated": False,
    "diagnostics": [],
    "warning_codes": [],
    "trust_boundary": {
        "graph_role": "structured_campaign_memory_and_navigation",
        "citation_authority": "corpus_source_evidence",
        "graph_citations_permitted": False,
    },
}

PACKET = {"campaign_id": "campaign:c1", "session": 22}

_FORBIDDEN_HERMES_NAMES = frozenset(
    {
        "hermes_graph_agent_contract",
        "hermes_graph_agent_host",
        "hermes_graph_agent",
        "hermes_graph_plugin",
        "HermesGraphAgentHost",
        "HermesGraphAgentTurnRequest",
        "HermesGraphAgentTurnResult",
        "HermesGraphToolEvent",
        "NousResearch",
    }
)


class _FakeRuntime:
    descriptor = HERMES_RUNTIME_DESCRIPTOR

    def __init__(self, result: AgentRuntimeResult) -> None:
        self.result = result
        self.calls: list[AgentRuntimeInvocation] = []

    def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
        self.calls.append(invocation)
        return self.result


def _in_scope_event(**overrides: Any) -> AgentRuntimeToolEvent:
    attributes = {
        "world_id": "world:eldyrwild",
        "campaign_id": "campaign:c1",
        "focus": {"kind": "session", "sessionId": "session-21"},
        "admissibility": "gm",
        "revision_pin": "revision:resolved-server",
        "bounded_ids": {},
        "retrieval_schema": "dmb_world_graph_retrieval_result_v1",
        "outcome": "enough",
        "matched_node_ids": ["threat:tripod-null-calf"],
        "relationship_ids": [],
        "source_anchor_ids": ["anchor:a1"],
        "diagnostic_codes": [],
        **overrides,
    }
    return AgentRuntimeToolEvent(
        tool_name="expand_graph_retrieval",
        state="completion",
        duration_ms=12.0,
        attributes=attributes,
    )


def _priced_model_call(*, request_id: str, sequence: int) -> dict[str, Any]:
    return {
        "schema": "dmb_agent_model_call_v1",
        "call_id": f"call-{sequence}",
        "sequence": sequence,
        "status": "ok",
        "provider": "openai-api",
        "requested_model": "gpt-5.4-mini",
        "response_model": "gpt-5.4-mini",
        "runtime_api_request_id": request_id,
        "started_at": "2026-08-26T18:00:00Z",
        "completed_at": "2026-08-26T18:00:01Z",
        "duration_ms": 400,
        "usage": {
            "status": "reported",
            "input_tokens": 80,
            "output_tokens": 10,
            "total_tokens": 90,
        },
        "cost": {"status": "estimated", "usd": 0.0004, "currency": "USD"},
    }


def _ok_result(**kwargs: Any) -> AgentRuntimeResult:
    model_calls = kwargs.pop("model_calls", [_priced_model_call(request_id="api-req-1", sequence=1)])
    tool_events = kwargs.pop("tool_events", [_in_scope_event()])
    runtime_session_id = kwargs.pop("runtime_session_id", "runtime-sess-1")
    return AgentRuntimeResult(
        status="ok",
        final_text="Tripod stands at the North Gate.",
        runtime_session_id=runtime_session_id,
        tool_events=tool_events,
        model_calls=list(model_calls),
        runtime_metadata={"process_isolation": "process_exclusive", "worker_pid": 4242},
        **kwargs,
    )


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            names.add(module.split(".")[-1] if module else "")
            for alias in node.names:
                names.add(alias.name)
    return names


def test_agent_runtime_module_imports_no_hermes() -> None:
    names = _imported_names(SERVICES / "agent_runtime.py")
    assert not (names & _FORBIDDEN_HERMES_NAMES)


def test_product_modules_import_no_hermes_host_or_wire_types() -> None:
    for filename in ("hermes_graph_query.py", "live_agent_loop.py"):
        names = _imported_names(SERVICES / filename)
        leaked = names & {
            "hermes_graph_agent_contract",
            "hermes_graph_agent_host",
            "HermesGraphAgentHost",
            "HermesGraphAgentTurnRequest",
            "HermesGraphAgentTurnResult",
            "HermesGraphToolEvent",
        }
        assert not leaked, f"{filename} imported {sorted(leaked)}"


def test_fake_runtime_drives_product_grounding_without_hermes_host(tmp_path: Path) -> None:
    runtime = _FakeRuntime(_ok_result())
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-fake",
        turn_id="turn-fake",
        root=tmp_path,
        agent_runtime=runtime,
    )
    assert len(runtime.calls) == 1
    invocation = runtime.calls[0]
    assert invocation.message == "Where is Tripod?"
    assert invocation.capability_policy.policy_id == WORLD_GRAPH_READ_POLICY_ID
    assert invocation.context_packet.world_scope.revision_id == "revision:resolved-server"
    assert "hermes_session_id" not in invocation.__dataclass_fields__
    assert response["status"] == "ok"
    assert response["grounding"]["state"] == "grounded"
    assert response["answer"].startswith("Tripod")
    assert response["agent_trace"]["schema"] == "dmb_agent_turn_trace_v1"
    assert response["agent_trace"]["backend"] == "hermes"
    assert response["agent_trace"]["runtime"] == "process_isolated"
    assert response["agent_trace"]["mode"] == "hermes_graph_agent"


def test_foreign_scope_fake_runtime_is_rejected(tmp_path: Path) -> None:
    runtime = _FakeRuntime(
        _ok_result(
            tool_events=[
                _in_scope_event(
                    world_id="world:foreign",
                    campaign_id="campaign:other",
                    revision_pin="revision:other",
                )
            ]
        )
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-foreign",
        turn_id="turn-foreign",
        root=tmp_path,
        agent_runtime=runtime,
    )
    assert len(runtime.calls) == 1
    assert response["status"] == "error"
    assert response["grounding"]["state"] == "error"
    assert "hermes_tool_event_scope_mismatch" in response["grounding"]["diagnostic_codes"]
    assert response["agent_trace"]["tool_events"] == []


def test_error_result_preserves_partial_model_telemetry(tmp_path: Path) -> None:
    call = _priced_model_call(request_id="api-req-partial", sequence=1)
    runtime = _FakeRuntime(
        AgentRuntimeResult(
            status="error",
            error_code="hermes_worker_timeout",
            error_message="worker timed out",
            tool_events=[],
            model_calls=[call],
            telemetry_warnings=["observer_stream_incomplete"],
            observed_model_call_count=1,
            runtime_metadata={"process_isolation": "process_exclusive", "worker_pid": 99},
        )
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-partial",
        turn_id="turn-partial",
        root=tmp_path,
        agent_runtime=runtime,
    )
    trace = response["agent_trace"]
    assert response["status"] == "error"
    assert trace["model_calls"][0]["runtime_api_request_id"] == "api-req-partial"
    assert trace["model_calls"][0]["cost"]["usd"] == call["cost"]["usd"]
    assert "observer_stream_incomplete" in trace["warnings"]
    assert trace["usage"]["model_call_count"] == 1
    assert trace["cost"]["usd"] != 0


def test_trace_compatibility_for_fixed_runtime_result(tmp_path: Path) -> None:
    call = _priced_model_call(request_id="api-req-compat", sequence=1)
    result = _ok_result(model_calls=[call])
    _, scope = build_hermes_graph_turn_request(
        question="Where is Tripod?",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
    )
    response = build_hermes_graph_product_response(
        packet=PACKET,
        result=result,
        scope=scope,
        agent_thread_id="agent-thread-compat",
        turn_id="turn-compat",
        started_at="2026-08-26T18:00:00Z",
        completed_at="2026-08-26T18:00:02Z",
        elapsed_ms=2000,
        world_graph_context=READY_ENVELOPE,
    )
    trace = response["agent_trace"]
    assert trace["schema"] == "dmb_agent_turn_trace_v1"
    assert trace["backend"] == "hermes"
    assert trace["runtime"] == "process_isolated"
    assert trace["mode"] == "hermes_graph_agent"
    assert trace["provider"] == "openai-api"
    assert trace["model"] == "gpt-5.4-mini"
    assert [item["runtime_api_request_id"] for item in trace["model_calls"]] == ["api-req-compat"]
    assert trace["usage"]["input_tokens"] == 80
    assert trace["usage"]["output_tokens"] == 10
    assert trace["cost"]["usd"] == call["cost"]["usd"]
    assert trace["agent_thread_id"] == "agent-thread-compat"
    assert trace["turn_id"] == "turn-compat"
    assert trace["tool_events"][0]["tool_name"] == "expand_graph_retrieval"


def test_continuity_uses_runtime_session_id_not_generic_hermes_field(tmp_path: Path) -> None:
    first_runtime = _FakeRuntime(_ok_result(runtime_session_id="runtime-internal-s1"))
    first = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=tmp_path / "live-session",
        agent_runtime=first_runtime,
    )
    pointer = first["hermes_session"]["sessionId"]
    assert first_runtime.calls[0].run_options.runtime_session_id is None
    assert hasattr(first_runtime.calls[0], "runtime_session_id") is False

    second_runtime = _FakeRuntime(_ok_result(runtime_session_id="runtime-internal-s1"))
    second = run_hermes_graph_query(
        text="Follow up?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=tmp_path / "live-session",
        hermes_session_pointer=pointer,
        agent_runtime=second_runtime,
    )
    assert second_runtime.calls[0].run_options.runtime_session_id == "runtime-internal-s1"
    assert "hermes_session_id" not in second_runtime.calls[0].run_options.__dataclass_fields__
    assert second["hermes_session"]["sessionId"] == pointer


def test_process_live_query_injects_runtime_once(tmp_path: Path, monkeypatch) -> None:
    runtime = _FakeRuntime(_ok_result())
    monkeypatch.setattr(
        "apps.live_control_server.services.live_agent_loop.resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: READY_ENVELOPE,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.live_agent_loop.load_session",
        lambda *_args, **_kwargs: (PACKET, None, [], []),
    )
    response = process_live_query(
        "Where is Tripod?",
        query_backend="hermes",
        world_graph_context=READY_ENVELOPE,  # type: ignore[arg-type]
        outer_campaign_id="campaign:c1",
        agent_runtime=runtime,
        base=tmp_path,
        root=tmp_path,
    )
    assert len(runtime.calls) == 1
    assert response["grounding"]["state"] == "grounded"


def test_world_graph_read_policy_identity_is_stable() -> None:
    assert WORLD_GRAPH_READ_POLICY.policy_id == "world_graph_read_v1"
    assert AgentCapabilityPolicy(policy_id="nope").policy_id != WORLD_GRAPH_READ_POLICY_ID
    assert UNSUPPORTED_CAPABILITY_POLICY == "unsupported_capability_policy"


def test_context_packet_is_world_scope_plus_retrieval_session() -> None:
    packet = AgentContextPacket(
        world_scope=AgentWorldScope(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            focus={"kind": "none"},
            admissibility="gm",
            revision_id="revision:1",
        ),
        retrieval_session=AgentRetrievalSession(session_id="sess", packet={"k": "v"}),
    )
    invocation = AgentRuntimeInvocation(
        thread_id="t",
        turn_id="u",
        message="q",
        conversation_history=None,
        context_packet=packet,
        capability_policy=WORLD_GRAPH_READ_POLICY,
        run_options=AgentRunOptions(),
    )
    assert invocation.context_packet.world_scope.world_id == "world:eldyrwild"
    assert invocation.context_packet.retrieval_session is not None
    assert invocation.context_packet.retrieval_session.session_id == "sess"
