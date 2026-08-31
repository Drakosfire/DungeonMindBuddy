"""A3 PydanticAI AgentRuntime challenger: deterministic loop, A0 telemetry, no production selection."""

from __future__ import annotations

import ast
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from apps.live_control_server.services.agent_runtime import (
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY,
    AgentCapabilityPolicy,
    AgentContextPacket,
    AgentRetrievalSession,
    AgentRunOptions,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentRuntimeToolEvent,
    AgentWorldScope,
)
from apps.live_control_server.services.agent_graph_policy import GRAPH_SYSTEM_POLICY
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    hermes_model_visible_tool_definitions,
)
from apps.live_control_server.services.hermes_graph_query import run_hermes_graph_query
from apps.live_control_server.services.live_agent_loop import process_live_query
from apps.live_control_server.services.pydantic_ai_agent_runtime import (
    CREDENTIALS_MISSING,
    PROVIDER_ERROR,
    PYDANTIC_AI_RUNTIME_DESCRIPTOR,
    PydanticAIAgentRuntimeAdapter,
    inject_authoritative_tool_args,
    map_conversation_history,
    map_pydantic_ai_usage,
    model_visible_json_schemas,
    model_visible_tool_names,
    pydantic_ai_agent_instructions,
)

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "apps/live_control_server/services"
ROUTES = ROOT / "apps/live_control_server/routes"

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

IN_SCOPE_EXPAND_JSON = json.dumps(
    {
        "schema": "dmb_world_graph_retrieval_result_v1",
        "outcome": "enough",
        "matchedNodeIds": ["threat:tripod-null-calf"],
        "sourceAnchors": [{"anchorId": "anchor:a1"}],
        "diagnostics": [],
    },
    separators=(",", ":"),
)

DECLARE_JSON = json.dumps(
    {"schema": "dmb_hermes_answer_scope_v1", "scope": "conversation_context"},
    separators=(",", ":"),
)

TOOL_ERROR_JSON = json.dumps(
    {
        "schema": "dmb_world_graph_retrieval_error_v1",
        "code": "integrity_failure",
        "message": "tool failed",
        "statusCode": 500,
        "diagnostics": [],
    },
    separators=(",", ":"),
)


class _RecordingExecutor:
    def __init__(self, payload_by_tool: dict[str, str] | None = None, default: str = IN_SCOPE_EXPAND_JSON) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.payload_by_tool = payload_by_tool or {}
        self.default = default

    def __call__(self, tool_name: str, arguments: Any, *, root: Any = None) -> str:
        del root
        captured = dict(arguments)
        self.calls.append((tool_name, captured))
        return self.payload_by_tool.get(tool_name, self.default)


def _invocation(**overrides: Any) -> AgentRuntimeInvocation:
    values: dict[str, Any] = {
        "thread_id": "agent-thread-1",
        "turn_id": "turn-1",
        "message": "Where is Tripod?",
        "conversation_history": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
        "context_packet": AgentContextPacket(
            world_scope=AgentWorldScope(
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
                focus={"kind": "session", "session_id": "session-21", "campaign_id": None},
                admissibility="gm",
                revision_id="revision:resolved-server",
            ),
            retrieval_session=AgentRetrievalSession(
                session_id="retrieval-sess-1",
                packet={"schema": "dmb_graph_retrieval_session_v1", "id": "retrieval-sess-1"},
            ),
        ),
        "capability_policy": WORLD_GRAPH_READ_POLICY,
        "run_options": AgentRunOptions(execution_root=Path("/tmp/graph-root")),
    }
    values.update(overrides)
    return AgentRuntimeInvocation(**values)


def _scripted_model(steps: list[ModelResponse | BaseException], *, model_name: str = "gpt-5.4-mini") -> tuple[FunctionModel, dict[str, Any]]:
    state = {"i": 0, "messages": []}

    def fn(messages, _info):
        state["messages"].append(messages)
        index = state["i"]
        state["i"] = index + 1
        if index >= len(steps):
            raise RuntimeError("scripted model exhausted")
        step = steps[index]
        if isinstance(step, BaseException):
            raise step
        return step

    fn.__name__ = "scripted_pydantic_ai_model"
    return FunctionModel(fn, model_name=model_name), state


def _adapter_for(steps: list[ModelResponse | BaseException], executor: _RecordingExecutor | None = None) -> tuple[PydanticAIAgentRuntimeAdapter, _RecordingExecutor, dict[str, Any]]:
    model, captured = _scripted_model(steps)
    recording = executor or _RecordingExecutor()
    adapter = PydanticAIAgentRuntimeAdapter(
        model_factory=lambda _model_id: model,
        tool_executor=recording,
        resolved_model_id="gpt-5.4-mini",
    )
    return adapter, recording, captured


def _expand_then_answer() -> list[ModelResponse]:
    return [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="expand_graph_retrieval",
                    args={
                        "retrievalSessionId": "foreign-session",
                        "target": {"kind": "object", "id": "threat:tripod-null-calf"},
                    },
                )
            ],
            usage=RequestUsage(input_tokens=80, output_tokens=10),
        ),
        ModelResponse(
            parts=[TextPart(content="Tripod stands at the North Gate.")],
            usage=RequestUsage(input_tokens=90, output_tokens=12),
        ),
    ]


def test_dependency_coexistence_pins() -> None:
    assert importlib.metadata.version("pydantic-ai-slim") == "1.66.0"
    assert importlib.metadata.version("openai") == "2.24.0"
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "openai"\nversion = "2.24.0"' in lock
    assert "pydantic-ai-slim" in lock and "1.66.0" in lock
    assert "861d69c7bba8d2ea6a1cd170e989c901c74d32d1" in lock
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "openai==2.24.0" in pyproject
    assert "pydantic-ai-slim[openai]==1.66.0" in pyproject


def test_exact_tool_surface_from_existing_dmb_schemas() -> None:
    names = model_visible_tool_names()
    assert names == ORDERED_MODEL_VISIBLE_TOOL_NAMES
    dmb = {
        str(item["function"]["name"]): dict(item["function"]["parameters"])
        for item in hermes_model_visible_tool_definitions()
    }
    assert model_visible_json_schemas() == dmb
    assert names == (
        "declare_conversation_context",
        "expand_graph_retrieval",
        "read_graph_source",
        "query_threat_mechanics_hydration",
    )


def test_agent_instructions_reuse_graph_system_policy_and_scope_packet() -> None:
    invocation = _invocation(
        context_packet=AgentContextPacket(
            world_scope=AgentWorldScope(
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
                focus={"kind": "session", "session_id": "session-21", "campaign_id": None},
                admissibility="gm",
                revision_id="revision:resolved-server",
            ),
            retrieval_session=AgentRetrievalSession(
                session_id="retrieval-sess-1",
                packet={
                    "schema": "dmb_graph_retrieval_session_v1",
                    "id": "retrieval-sess-1",
                    "candidates": [{"nodeId": "threat:tripod-null-calf"}],
                    "claim_ledger": [{"claimId": "claim:1"}],
                    "intent_hint": "where",
                    "available_expansions": ["neighborhood"],
                    "latest_recap_change": {
                        "boundary": "changed",
                        "admitted_recap_excerpt": "Tripod moved.",
                    },
                },
            ),
        )
    )
    expected = pydantic_ai_agent_instructions(invocation)
    assert expected.startswith(GRAPH_SYSTEM_POLICY)
    assert GRAPH_SYSTEM_POLICY in expected
    assert "call declare_conversation_context exactly once" in expected
    assert "latest-recap change question" in expected
    assert "name the campaign and session provenance" in expected
    assert "Use read_graph_source only for quotation" in expected
    assert "Do not use report scaffolding" in expected
    assert "Manifest, corpus, Markdown" in expected
    assert "DungeonBuddy World Graph Agent. Answer only from enabled graph tools" not in expected
    assert "enabledPluginIds" not in expected
    assert "enabledToolsets" not in expected
    assert '"worldId": "world:eldyrwild"' in expected
    assert '"retrievalSessionId": "retrieval-sess-1"' in expected
    assert '"processIsolation": "in_process"' in expected
    assert "This runtime is in-process PydanticAI" in expected
    assert '"admittedRecapExcerpt": "Tripod moved."' in expected
    adapter, _executor, captured = _adapter_for(_expand_then_answer())
    result = adapter.run(invocation)
    assert result.status == "ok"
    supplied: list[str] = []
    for messages in captured["messages"]:
        for message in messages:
            instructions = getattr(message, "instructions", None)
            if isinstance(instructions, str) and instructions.strip():
                supplied.append(instructions)
    blob = "\n".join(supplied)
    assert blob
    assert expected in blob
    assert GRAPH_SYSTEM_POLICY in blob
    assert '"retrievalSessionId": "retrieval-sess-1"' in blob


def test_unsupported_policy_fails_closed_before_model_or_tools() -> None:
    executor = _RecordingExecutor()
    called = {"factory": 0}

    def factory(_model_id: str) -> FunctionModel:
        called["factory"] += 1
        model, _ = _scripted_model(_expand_then_answer())
        return model

    adapter = PydanticAIAgentRuntimeAdapter(
        model_factory=factory,
        tool_executor=executor,
        resolved_model_id="gpt-5.4-mini",
    )
    result = adapter.run(
        _invocation(capability_policy=AgentCapabilityPolicy(policy_id="nope"))
    )
    assert result.status == "error"
    assert result.error_code == UNSUPPORTED_CAPABILITY_POLICY
    assert result.model_calls == []
    assert result.tool_events == []
    assert executor.calls == []
    assert called["factory"] == 0


def test_authoritative_args_overwrite_foreign_model_values() -> None:
    invocation = _invocation()
    injected = inject_authoritative_tool_args(
        "expand_graph_retrieval",
        {"retrievalSessionId": "foreign-session", "target": {"kind": "object", "id": "x"}},
        invocation,
    )
    assert injected["retrievalSessionId"] == "retrieval-sess-1"
    threat = inject_authoritative_tool_args(
        "query_threat_mechanics_hydration",
        {
            "worldId": "world:foreign",
            "campaignId": "campaign:other",
            "revisionPin": "revision:other",
            "queryText": "Tripod",
        },
        invocation,
    )
    assert threat["worldId"] == "world:eldyrwild"
    assert threat["campaignId"] == "campaign:c1"
    assert threat["revisionPin"] == "revision:resolved-server"
    assert threat["queryText"] == "Tripod"


def test_executor_receives_authoritative_session_not_model_supplied() -> None:
    adapter, executor, _captured = _adapter_for(_expand_then_answer())
    result = adapter.run(_invocation())
    assert result.status == "ok"
    assert executor.calls[0][0] == "expand_graph_retrieval"
    assert executor.calls[0][1]["retrievalSessionId"] == "retrieval-sess-1"
    assert executor.calls[0][1]["retrievalSessionId"] != "foreign-session"


def test_two_model_calls_and_one_tool_are_observed() -> None:
    adapter, executor, _captured = _adapter_for(_expand_then_answer())
    result = adapter.run(_invocation())
    assert result.status == "ok"
    assert result.final_text == "Tripod stands at the North Gate."
    assert result.runtime_session_id is None
    assert result.answer_scope == "graph"
    assert adapter.descriptor == PYDANTIC_AI_RUNTIME_DESCRIPTOR
    assert [call["sequence"] for call in result.model_calls] == [1, 2]
    assert [call["status"] for call in result.model_calls] == ["ok", "ok"]
    assert result.observed_model_call_count == 2
    assert result.model_calls[0]["provider"] == "function"
    assert result.model_calls[0]["requested_model"] == "gpt-5.4-mini"
    assert result.model_calls[0]["duration_ms"] is not None
    assert result.model_calls[0]["usage"]["status"] == "reported"
    completions = [event for event in result.tool_events if event.state == "completion"]
    assert len(completions) == 1
    assert completions[0].tool_name == "expand_graph_retrieval"
    assert completions[0].outcome == "enough"
    assert "args" not in completions[0].attributes
    assert "result" not in completions[0].attributes
    assert executor.calls[0][0] == "expand_graph_retrieval"


def test_product_path_uses_pydantic_ai_descriptor_and_grounds(tmp_path: Path) -> None:
    adapter, _executor, _captured = _adapter_for(_expand_then_answer())
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-pai",
        turn_id="turn-pai",
        root=tmp_path,
        agent_runtime=adapter,
    )
    trace = response["agent_trace"]
    assert trace["backend"] == "pydantic_ai"
    assert trace["runtime"] == "in_process"
    assert trace["mode"] == "pydantic_ai_graph_agent"
    assert trace["backend"] != "hermes"
    assert len(trace["model_calls"]) == 2
    assert response["grounding"]["state"] == "grounded"
    assert response["answer"].startswith("Tripod")
    assert trace["schema"] == "dmb_agent_turn_trace_v1"


def test_process_live_query_descriptor_is_not_hermes(tmp_path: Path, monkeypatch) -> None:
    adapter, _executor, _captured = _adapter_for(_expand_then_answer())
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
        agent_runtime=adapter,
        base=tmp_path,
        root=tmp_path,
    )
    trace = response["agent_trace"]
    assert trace["backend"] == "pydantic_ai"
    assert trace["mode"] == "pydantic_ai_graph_agent"
    assert trace["runtime"] == "in_process"


def test_conversation_context_journey() -> None:
    steps = [
        ModelResponse(
            parts=[ToolCallPart(tool_name="declare_conversation_context", args={})],
            usage=RequestUsage(input_tokens=40, output_tokens=5),
        ),
        ModelResponse(
            parts=[TextPart(content="We were discussing the previous question.")],
            usage=RequestUsage(input_tokens=50, output_tokens=8),
        ),
    ]
    adapter, executor, _ = _adapter_for(
        steps, executor=_RecordingExecutor(default=DECLARE_JSON)
    )
    result = adapter.run(_invocation(message="What did I just ask?"))
    assert result.status == "ok"
    assert result.answer_scope == "conversation_context"
    assert executor.calls[0][0] == "declare_conversation_context"


def test_conversation_context_product_classification(tmp_path: Path) -> None:
    steps = [
        ModelResponse(
            parts=[ToolCallPart(tool_name="declare_conversation_context", args={})],
            usage=RequestUsage(input_tokens=40, output_tokens=5),
        ),
        ModelResponse(
            parts=[TextPart(content="We were discussing the previous question.")],
            usage=RequestUsage(input_tokens=50, output_tokens=8),
        ),
    ]
    adapter, _executor, _ = _adapter_for(
        steps, executor=_RecordingExecutor(default=DECLARE_JSON)
    )
    response = run_hermes_graph_query(
        text="What did I just ask?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-ctx",
        turn_id="turn-ctx",
        root=tmp_path,
        agent_runtime=adapter,
    )
    assert response["grounding"]["state"] == "conversation_context"
    assert "campaign-fact" not in str(response.get("answer") or "").lower()


def test_foreign_scope_product_still_rejects(tmp_path: Path) -> None:
    class _ForeignRuntime:
        descriptor = PYDANTIC_AI_RUNTIME_DESCRIPTOR

        def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
            del invocation
            return AgentRuntimeResult(
                status="ok",
                final_text="foreign prose",
                tool_events=[
                    AgentRuntimeToolEvent(
                        tool_name="expand_graph_retrieval",
                        state="completion",
                        duration_ms=4.0,
                        attributes={
                            "world_id": "world:foreign",
                            "campaign_id": "campaign:other",
                            "focus": {"kind": "session", "session_id": "session-21"},
                            "admissibility": "gm",
                            "revision_pin": "revision:other",
                            "outcome": "enough",
                            "matched_node_ids": ["threat:tripod-null-calf"],
                            "source_anchor_ids": ["anchor:a1"],
                        },
                    )
                ],
            )

    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-foreign",
        turn_id="turn-foreign",
        root=tmp_path,
        agent_runtime=_ForeignRuntime(),
    )
    assert response["status"] == "error"
    assert "hermes_tool_event_scope_mismatch" in response["grounding"]["diagnostic_codes"]


def test_cache_semantics_do_not_double_count() -> None:
    usage = RequestUsage(
        input_tokens=1000,
        cache_read_tokens=600,
        cache_write_tokens=0,
        output_tokens=100,
    )
    mapped = map_pydantic_ai_usage(usage)
    assert mapped["input_tokens"] == 1000
    assert mapped["cached_input_tokens"] == 600
    assert mapped["uncached_input_tokens"] == 400
    assert mapped["output_tokens"] == 100
    assert mapped["total_tokens"] == 1100
    assert mapped["input_tokens"] != 1600


def test_error_after_partial_preserves_first_call() -> None:
    steps: list[ModelResponse | BaseException] = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="expand_graph_retrieval",
                    args={
                        "retrievalSessionId": "foreign-session",
                        "target": {"kind": "object", "id": "threat:tripod-null-calf"},
                    },
                )
            ],
            usage=RequestUsage(input_tokens=20, output_tokens=4),
        ),
        RuntimeError("provider exploded"),
    ]
    adapter, _executor, _ = _adapter_for(steps)
    result = adapter.run(_invocation())
    assert result.status == "error"
    assert result.error_code == PROVIDER_ERROR
    assert len(result.model_calls) == 2
    assert result.model_calls[0]["status"] == "ok"
    assert result.model_calls[0]["usage"]["status"] == "reported"
    assert result.model_calls[0]["cost"]["status"] in {"estimated", "unavailable"}
    assert result.model_calls[1]["status"] == "error"
    assert result.model_calls[1]["usage"]["status"] == "unavailable"
    assert result.model_calls[1]["cost"]["status"] == "unavailable"
    assert result.model_calls[1]["error_type"] == "RuntimeError"
    assert result.model_calls[1]["duration_ms"] is not None


def test_tool_error_records_safe_error_state() -> None:
    steps = [
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="expand_graph_retrieval",
                    args={"retrievalSessionId": "x", "target": {"kind": "object", "id": "n"}},
                )
            ],
            usage=RequestUsage(input_tokens=10, output_tokens=2),
        ),
        ModelResponse(
            parts=[TextPart(content="I could not complete retrieval.")],
            usage=RequestUsage(input_tokens=12, output_tokens=3),
        ),
    ]
    adapter, _executor, _ = _adapter_for(
        steps, executor=_RecordingExecutor(default=TOOL_ERROR_JSON)
    )
    result = adapter.run(_invocation())
    errors = [event for event in result.tool_events if event.state == "error"]
    assert errors
    assert errors[0].tool_name == "expand_graph_retrieval"
    assert "args" not in errors[0].attributes


def test_history_maps_role_content_once_without_world_metadata() -> None:
    mapped = map_conversation_history(
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    )
    assert len(mapped) == 2
    assert isinstance(mapped[0].parts[0], UserPromptPart)
    assert mapped[0].parts[0].content == "hi"
    adapter, _executor, captured = _adapter_for(_expand_then_answer())
    adapter.run(_invocation())
    first_messages = captured["messages"][0]
    user_parts = [
        part
        for message in first_messages
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]
    assert any(part.content == "hi" for part in user_parts)
    assert any(part.content == "Where is Tripod?" for part in user_parts)


def test_no_production_selection_imports() -> None:
    forbidden = "pydantic_ai_agent_runtime"
    for path in (
        SERVICES / "live_agent_loop.py",
        SERVICES / "hermes_graph_query.py",
        *ROUTES.glob("*.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module or "")
                for alias in node.names:
                    names.add(alias.name)
        assert forbidden not in names, f"{path} imported {forbidden}"
    live_py = (SERVICES / "live_agent_loop.py").read_text(encoding="utf-8")
    assert 'query_backend: str = "live"' in live_py or "LIVE_QUERY_BACKENDS" in live_py
    assert "pydantic_ai" not in live_py
    routes_live = (ROUTES / "live.py").read_text(encoding="utf-8")
    assert "pydantic_ai" not in routes_live


def test_descriptor_constant_is_truthful() -> None:
    assert PYDANTIC_AI_RUNTIME_DESCRIPTOR.runtime_id == "pydantic_ai"
    assert PYDANTIC_AI_RUNTIME_DESCRIPTOR.trace_backend == "pydantic_ai"
    assert PYDANTIC_AI_RUNTIME_DESCRIPTOR.trace_runtime == "in_process"
    assert PYDANTIC_AI_RUNTIME_DESCRIPTOR.trace_mode == "pydantic_ai_graph_agent"
    assert CREDENTIALS_MISSING.startswith("pydantic_ai_")


def test_surface_context_block_parity_with_hermes_renderer() -> None:
    from apps.live_control_server.services.agent_runtime import (
        AgentCurrentWorkContext,
        AgentSurfaceContext,
    )
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )

    surface = AgentSurfaceContext(
        surface_id="plan",
        current_work=AgentCurrentWorkContext(
            kind="plan",
            work_object_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            title="C2 Session 27 Prep",
            object_revision=4,
            target_session=27,
        ),
    )
    base = _invocation()
    invocation = _invocation(
        context_packet=AgentContextPacket(
            world_scope=base.context_packet.world_scope,
            retrieval_session=base.context_packet.retrieval_session,
            surface_context=surface,
        )
    )
    instructions = pydantic_ai_agent_instructions(invocation)
    block = render_agent_surface_context(surface)
    assert block is not None
    assert block in instructions
    assert instructions.startswith(GRAPH_SYSTEM_POLICY)
    assert "Turn capability policy" in instructions
    hermes_block = map_invocation_to_hermes_request(invocation).surface_context_block
    assert hermes_block == block
    bare = pydantic_ai_agent_instructions(_invocation())
    assert block not in bare
    assert bare.startswith(GRAPH_SYSTEM_POLICY)


def test_play_surface_context_block_parity_with_hermes_renderer() -> None:
    from apps.live_control_server.services.agent_runtime import (
        AgentPlayCurrentElementContext,
        AgentPlayCurrentMomentContext,
        AgentSurfaceContext,
    )
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )

    surface = AgentSurfaceContext(
        surface_id="play",
        current_play=AgentPlayCurrentMomentContext(
            run_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            playable_artifact_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            playable_revision=1,
            current_beat=AgentPlayCurrentElementContext(
                kind="beat",
                element_id="beat:hold-the-gate",
                title="Hold the gate",
                body_text="Triage at the gate line.",
            ),
            current_scene=None,
        ),
    )
    base = _invocation()
    invocation = _invocation(
        context_packet=AgentContextPacket(
            world_scope=base.context_packet.world_scope,
            retrieval_session=base.context_packet.retrieval_session,
            surface_context=surface,
        )
    )
    instructions = pydantic_ai_agent_instructions(invocation)
    block = render_agent_surface_context(surface)
    assert block is not None
    assert block in instructions
    hermes_block = map_invocation_to_hermes_request(invocation).surface_context_block
    assert hermes_block == block
