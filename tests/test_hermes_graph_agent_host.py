"""Owning proofs for PR353 process-isolated Hermes graph-agent host."""

from __future__ import annotations

import ast
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.services.hermes_graph_agent import (
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    deserialize_hermes_graph_agent_turn_request,
    deserialize_hermes_graph_agent_turn_result,
    run_hermes_graph_agent_turn,
    serialize_capability_policy,
    serialize_hermes_graph_agent_turn_request,
    serialize_hermes_graph_agent_turn_result,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    MAX_HISTORY_MESSAGES,
    MAX_POLICY_TOOLSETS,
    MAX_QUESTION_CHARS,
    MAX_TOOL_EVENTS,
    MAX_WIRE_BYTES,
    encode_json_wire,
    encode_turn_request_wire,
)
from apps.live_control_server.services.hermes_graph_agent_host import (
    HermesGraphAgentHost,
    get_hermes_graph_agent_host,
    hermes_graph_agent_worker_main,
    shutdown_hermes_graph_agent_host,
)
from graph_memory.hermes_graph_plugin import (
    HermesCapabilityPolicy,
    HermesGraphScope,
    HermesPluginActivation,
    HermesToolCapabilityRule,
    TOOLSET_NAME,
    default_graph_only_capability_policy,
)

HOST_MODULE = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "live_control_server"
    / "services"
    / "hermes_graph_agent_host.py"
)


def _scope() -> HermesGraphScope:
    return HermesGraphScope(
        world_id="world:eldyrwild",
        campaign_id="campaign:c1",
        focus={"kind": "none", "sessionId": None},
        admissibility="gm",
        revision_pin="revision:test",
    )


def _request(**overrides: Any) -> HermesGraphAgentTurnRequest:
    payload: dict[str, Any] = {
        "question": "What do we know about Tripod?",
        "world_id": "world:eldyrwild",
        "campaign_id": "campaign:c1",
        "focus": {"kind": "none", "sessionId": None},
        "admissibility": "gm",
        "revision_pin": "revision:test",
        "root": None,
        "capability_policy": default_graph_only_capability_policy(_scope()),
    }
    payload.update(overrides)
    return HermesGraphAgentTurnRequest(**payload)


def _ok_result(*, session_id: str = "sess-1") -> HermesGraphAgentTurnResult:
    return HermesGraphAgentTurnResult(
        status="ok",
        final_response="Tripod is near the North Gate.",
        messages=[{"role": "assistant", "content": "Tripod is near the North Gate."}],
        hermes_session_id=session_id,
        tool_events=[],
        process_isolation="process_exclusive",
    )


def _put_json(queue: Any, payload: dict[str, Any]) -> None:
    queue.put(encode_json_wire(payload))


def _stub_worker_main(request_queue: Any, response_queue: Any) -> None:
    """Picklable stub worker that never imports Rung 3 turn execution."""
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        payload = message.get("payload") or {}
        question = str(payload.get("question") or "")
        result = serialize_hermes_graph_agent_turn_result(
            HermesGraphAgentTurnResult(
                status="ok",
                final_response=f"echo:{question}",
                messages=[],
                hermes_session_id=f"worker-{os.getpid()}",
                tool_events=[],
                process_isolation="process_exclusive",
            )
        )
        _put_json(
            response_queue,
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": result,
            },
        )


def _slow_after_accept_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
    )

    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        time.sleep(60)


def _crash_after_accept_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
    )

    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    message = decode_json_wire(request_queue.get())
    if message.get("type") == "execute":
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        os._exit(1)


def _crash_once_then_ok_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    flag_path = Path(os.environ["DMB_HERMES_HOST_CRASH_FLAG"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    message = decode_json_wire(request_queue.get())
    if message.get("type") == "shutdown":
        return
    if message.get("type") != "execute":
        return
    request_id = str(message.get("requestId") or "")
    _put_json(
        response_queue,
        {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
    )
    # Let the parent drain `accepted` before exit; otherwise a lost accept looks
    # pre-accept and the host may retry into the success path.
    time.sleep(0.15)
    if not flag_path.exists():
        flag_path.write_text("crashed-once", encoding="utf-8")
        os._exit(1)
    _put_json(
        response_queue,
        {
            "type": "result",
            "requestId": request_id,
            "pid": os.getpid(),
            "payload": serialize_hermes_graph_agent_turn_result(_ok_result()),
        },
    )


def _die_before_accept_once_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    flag_path = Path(os.environ["DMB_HERMES_HOST_DIE_FLAG"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    message = decode_json_wire(request_queue.get())
    if message.get("type") == "shutdown":
        return
    if not flag_path.exists():
        flag_path.write_text("died-once", encoding="utf-8")
        os._exit(1)
    request_id = str(message.get("requestId") or "")
    _put_json(
        response_queue,
        {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
    )
    _put_json(
        response_queue,
        {
            "type": "result",
            "requestId": request_id,
            "pid": os.getpid(),
            "payload": serialize_hermes_graph_agent_turn_result(_ok_result()),
        },
    )


def _holding_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    started_path = Path(os.environ["DMB_HERMES_HOST_STARTED"])
    release_path = Path(os.environ["DMB_HERMES_HOST_RELEASE"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        started_path.write_text(request_id, encoding="utf-8")
        deadline = time.time() + 10
        while time.time() < deadline:
            if release_path.exists():
                break
            time.sleep(0.01)
        _put_json(
            response_queue,
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": serialize_hermes_graph_agent_turn_result(
                    HermesGraphAgentTurnResult(
                        status="ok",
                        final_response=request_id,
                        messages=[],
                        hermes_session_id=f"worker-{os.getpid()}",
                        tool_events=[],
                        process_isolation="process_exclusive",
                    )
                ),
            },
        )


def _accept_counting_slow_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
    )

    accept_path = Path(os.environ["DMB_HERMES_HOST_ACCEPT_COUNT"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        count = 0
        if accept_path.exists():
            count = int(accept_path.read_text(encoding="utf-8") or "0")
        accept_path.write_text(str(count + 1), encoding="utf-8")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        time.sleep(60)


def _never_ready_worker(request_queue: Any, response_queue: Any) -> None:
    """Starts but never emits ready — simulates hung Rung 3 import."""
    del request_queue, response_queue
    while True:
        time.sleep(60)


def _tool_using_aiagent_host_worker(request_queue: Any, response_queue: Any) -> None:
    """Real Rung 3 + AIAgent worker with only the external model mocked."""
    import json as json_mod
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from apps.live_control_server.services.hermes_graph_agent import (
        hermes_import_namespace,
        import_hermes_aiagent,
        run_hermes_graph_agent_turn,
    )
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        deserialize_hermes_graph_agent_turn_request,
        serialize_hermes_graph_agent_turn_result,
    )
    from graph_memory.retrieval.models import WorldGraphRetrievalResult

    def _mock_chat_response(
        *,
        content: str | None = "Hello",
        finish_reason: str = "stop",
        tool_calls: list[Any] | None = None,
    ) -> SimpleNamespace:
        msg = SimpleNamespace(
            content=content,
            tool_calls=tool_calls,
            reasoning_content=None,
            reasoning=None,
        )
        choice = SimpleNamespace(message=msg, finish_reason=finish_reason)
        return SimpleNamespace(choices=[choice], model="test/model", usage=None)

    AIAgent = import_hermes_aiagent()

    def _fake_execute(tool_name: str, arguments: Any, *, root: Any = None) -> str:
        del root
        return WorldGraphRetrievalResult(
            operation="search",
            outcome="enough",
            matched_node_ids=["threat:tripod-null-calf"],
        ).model_dump_json(by_alias=True)

    tool_args = {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": "world:SPOOF",
        "campaignId": "campaign:SPOOF",
        "queryText": "Tripod",
        "focus": {"kind": "session", "sessionId": "session:spoof"},
        "admissibility": "player",
        "revisionPin": "rev:spoof",
    }
    tc = SimpleNamespace(
        id="call-graph-1",
        type="function",
        function=SimpleNamespace(
            name="search_campaign_graph",
            arguments=json_mod.dumps(tool_args),
        ),
    )
    tool_resp = _mock_chat_response(
        content=None,
        finish_reason="tool_calls",
        tool_calls=[tc],
    )
    final_resp = _mock_chat_response(
        content="Tripod stands at the North Gate.",
        finish_reason="stop",
    )

    def _factory(**kwargs: Any) -> Any:
        with hermes_import_namespace():
            with patch("run_agent.OpenAI"):
                agent = AIAgent(
                    api_key="test-key-1234567890",
                    base_url="https://openrouter.ai/api/v1",
                    **kwargs,
                )
        agent.client = MagicMock()
        agent.client.chat.completions.create.side_effect = [tool_resp, final_resp]
        agent._cached_system_prompt = "test"
        agent._use_prompt_caching = False
        agent.tool_delay = 0
        agent.compression_enabled = False
        agent.save_trajectories = False
        return agent

    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        try:
            payload = message.get("payload")
            request = deserialize_hermes_graph_agent_turn_request(payload)
            with patch(
                "graph_memory.hermes_graph_plugin.execute_hermes_graph_read_tool_json",
                _fake_execute,
            ):
                result = run_hermes_graph_agent_turn(request, agent_factory=_factory)
            _put_json(
                response_queue,
                {
                    "type": "result",
                    "requestId": request_id,
                    "pid": os.getpid(),
                    "payload": serialize_hermes_graph_agent_turn_result(result),
                },
            )
        except Exception as exc:
            from apps.live_control_server.services.hermes_graph_agent_contract import (
                PROCESS_ISOLATION_MODE,
            )

            _put_json(
                response_queue,
                {
                    "type": "result",
                    "requestId": request_id,
                    "pid": os.getpid(),
                    "payload": serialize_hermes_graph_agent_turn_result(
                        HermesGraphAgentTurnResult(
                            status="error",
                            final_response=None,
                            messages=[],
                            hermes_session_id="",
                            tool_events=[],
                            error_code="hermes_worker_protocol_error",
                            error_message=f"{type(exc).__name__}: {exc}",
                            process_isolation=PROCESS_ISOLATION_MODE,
                        )
                    ),
                },
            )


def test_host_module_does_not_import_rung3_runtime_module() -> None:
    source = HOST_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.endswith("hermes_graph_agent"), (
                "host module must not import hermes_graph_agent at module level"
            )
    worker_src = source.split("def hermes_graph_agent_worker_main", 1)[1]
    assert "run_hermes_graph_agent_turn" in worker_src
    assert "run_hermes_graph_agent_turn(request)" in worker_src


def test_default_worker_source_calls_real_rung3_entry() -> None:
    source = HOST_MODULE.read_text(encoding="utf-8")
    worker_src = source.split("def hermes_graph_agent_worker_main", 1)[1]
    assert "run_hermes_graph_agent_turn" in worker_src
    assert "run_hermes_graph_agent_turn(request)" in worker_src


def test_request_result_round_trip_is_bounded_and_deterministic() -> None:
    policy = HermesCapabilityPolicy(
        enabled_toolsets=(TOOLSET_NAME,),
        enabled_tool_names=("search_campaign_graph",),
        graph_scope=_scope(),
        plugin_activations=(
            HermesPluginActivation(plugin_id=TOOLSET_NAME, toolsets=(TOOLSET_NAME,)),
        ),
        tool_rules=(
            HermesToolCapabilityRule(
                tool_name="search_campaign_graph",
                toolset=TOOLSET_NAME,
                require_graph_scope=True,
                allowed_effects=frozenset({"read"}),
            ),
        ),
    )
    request = _request(
        conversation_history=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
        capability_policy=policy,
        root=Path("/tmp/graph-root"),
    )
    wire = serialize_hermes_graph_agent_turn_request(request)
    assert "agentFactory" not in wire
    restored = deserialize_hermes_graph_agent_turn_request(wire)
    assert restored.question == request.question
    assert restored.world_id == request.world_id
    assert restored.root == Path("/tmp/graph-root")
    assert restored.capability_policy is not None
    assert restored.capability_policy.enabled_tool_names == ("search_campaign_graph",)
    assert serialize_capability_policy(restored.capability_policy) == (
        serialize_capability_policy(policy)
    )

    result = _ok_result()
    result_wire = serialize_hermes_graph_agent_turn_result(result)
    assert result_wire["messages"] == []
    restored_result = deserialize_hermes_graph_agent_turn_result(result_wire)
    assert restored_result.status == "ok"
    assert restored_result.final_response == result.final_response
    assert restored_result.hermes_session_id == result.hermes_session_id
    assert restored_result.messages == []


def test_encode_json_wire_round_trips_and_is_bytes() -> None:
    payload = {"type": "ready", "pid": 1234}
    raw = encode_json_wire(payload)
    assert isinstance(raw, bytes)
    assert json.loads(raw.decode("utf-8")) == payload


def test_oversized_question_rejected() -> None:
    with pytest.raises(ValueError, match="question"):
        serialize_hermes_graph_agent_turn_request(
            _request(question="x" * (MAX_QUESTION_CHARS + 1))
        )


def test_oversized_history_rejected() -> None:
    history = [{"role": "user", "content": "hi"} for _ in range(MAX_HISTORY_MESSAGES + 1)]
    with pytest.raises(ValueError, match="conversationHistory"):
        serialize_hermes_graph_agent_turn_request(_request(conversation_history=history))


def test_oversized_policy_collections_rejected() -> None:
    policy = HermesCapabilityPolicy(
        enabled_toolsets=tuple(f"toolset-{index}" for index in range(MAX_POLICY_TOOLSETS + 1)),
        enabled_tool_names=("search_campaign_graph",),
        graph_scope=_scope(),
        plugin_activations=(),
        tool_rules=(),
    )
    with pytest.raises(ValueError, match="enabledToolsets"):
        serialize_capability_policy(policy)


def test_unknown_request_keys_rejected() -> None:
    wire = serialize_hermes_graph_agent_turn_request(_request())
    wire["extraField"] = "nope"
    with pytest.raises(ValueError, match="unknown keys"):
        deserialize_hermes_graph_agent_turn_request(wire)


def test_non_json_serializable_nested_object_rejected() -> None:
    wire = serialize_hermes_graph_agent_turn_request(_request())
    wire["focus"] = {"kind": object()}
    with pytest.raises(ValueError, match="JSON-serializable|focus"):
        encode_json_wire(wire)


def test_relative_and_traversal_root_rejected() -> None:
    with pytest.raises(ValueError, match="absolute"):
        serialize_hermes_graph_agent_turn_request(_request(root=Path("foo")))
    with pytest.raises(ValueError, match="\\.\\."):
        deserialize_hermes_graph_agent_turn_request(
            {**serialize_hermes_graph_agent_turn_request(_request()), "root": "/tmp/../etc/passwd"}
        )


def test_malformed_result_structures_rejected() -> None:
    wire = serialize_hermes_graph_agent_turn_result(_ok_result())
    wire["status"] = "maybe"
    with pytest.raises(ValueError, match="status"):
        deserialize_hermes_graph_agent_turn_result(wire)
    wire = serialize_hermes_graph_agent_turn_result(_ok_result())
    wire["toolEvents"] = [{"toolName": "x", "state": "bogus"}]
    with pytest.raises(ValueError, match="state"):
        deserialize_hermes_graph_agent_turn_result(wire)


def test_host_result_wire_omits_hermes_transcript_with_tool_messages() -> None:
    """Tool-bearing Hermes messages must not break host result serialization."""
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphToolEvent,
    )

    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="Tripod stands at the North Gate.",
        messages=[
            {"role": "user", "content": "Where is Tripod?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-graph-1",
                        "type": "function",
                        "function": {
                            "name": "search_campaign_graph",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "name": "search_campaign_graph",
                "tool_call_id": "call-graph-1",
                "content": '{"outcome":"enough"}',
            },
            {"role": "assistant", "content": "Tripod stands at the North Gate."},
        ],
        hermes_session_id="sess-tool",
        tool_events=[
            HermesGraphToolEvent(tool_name="search_campaign_graph", state="start"),
            HermesGraphToolEvent(
                tool_name="search_campaign_graph",
                state="completion",
                outcome="enough",
                matched_node_ids=["threat:tripod-null-calf"],
            ),
        ],
        process_isolation="process_exclusive",
    )
    wire = serialize_hermes_graph_agent_turn_result(result)
    assert wire["messages"] == []
    assert wire["finalResponse"] == "Tripod stands at the North Gate."
    restored = deserialize_hermes_graph_agent_turn_result(wire)
    assert restored.status == "ok"
    assert restored.messages == []
    assert restored.final_response == "Tripod stands at the North Gate."
    assert [event.tool_name for event in restored.tool_events] == [
        "search_campaign_graph",
        "search_campaign_graph",
    ]


def test_oversized_tool_events_rejected() -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        HermesGraphToolEvent,
    )

    events = [
        HermesGraphToolEvent(tool_name=f"tool-{index}", state="start")
        for index in range(MAX_TOOL_EVENTS + 1)
    ]
    with pytest.raises(ValueError, match="toolEvents"):
        serialize_hermes_graph_agent_turn_result(
            HermesGraphAgentTurnResult(
                status="ok",
                final_response="ok",
                messages=[],
                hermes_session_id="sess",
                tool_events=events,
                process_isolation="process_exclusive",
            )
        )


def test_deserialize_rejects_forbidden_factory_fields() -> None:
    wire = serialize_hermes_graph_agent_turn_request(_request())
    wire["agentFactory"] = "evil"
    with pytest.raises(ValueError, match="forbidden"):
        deserialize_hermes_graph_agent_turn_request(wire)


def test_encode_turn_request_wire_respects_max_bytes() -> None:
    request = _request(question="x" * MAX_QUESTION_CHARS)
    raw = encode_turn_request_wire(request)
    assert len(raw) <= MAX_WIRE_BYTES


def test_host_uses_spawn_start_method() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    assert host.start_method == "spawn"
    host.shutdown()


def test_parent_execute_does_not_call_rung3_when_using_stub_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    def _boom(request: HermesGraphAgentTurnRequest, **kwargs: Any) -> Any:
        del request, kwargs
        calls.append(os.getpid())
        raise AssertionError("parent must not execute Rung 3")

    monkeypatch.setattr(
        "apps.live_control_server.services.hermes_graph_agent.run_hermes_graph_agent_turn",
        _boom,
    )
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    try:
        result = host.execute(_request(question="q1"))
        assert result.status == "ok"
        assert result.final_response == "echo:q1"
        assert calls == []
    finally:
        host.shutdown()


def test_real_worker_executes_rung3_entry_for_validation_error() -> None:
    host = HermesGraphAgentHost(
        worker_target=hermes_graph_agent_worker_main,
        turn_timeout_s=60.0,
        ready_timeout_s=60.0,
    )
    try:
        parent_pid = os.getpid()
        result = host.execute(
            HermesGraphAgentTurnRequest(
                question="",
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
            )
        )
        assert result.status == "error"
        assert result.error_code == "invalid_request"
        assert host.worker_pid is not None
        assert host.worker_pid != parent_pid
    finally:
        host.shutdown()


def test_worker_is_reused_across_sequential_requests() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    try:
        first = host.execute(_request(question="one"))
        pid_one = host.worker_pid
        second = host.execute(_request(question="two"))
        pid_two = host.worker_pid
        assert first.status == "ok"
        assert second.status == "ok"
        assert pid_one is not None and pid_one == pid_two
        assert first.hermes_session_id == f"worker-{pid_one}"
        assert second.hermes_session_id == f"worker-{pid_two}"
    finally:
        host.shutdown()


def test_concurrent_host_calls_are_serialized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = tmp_path / "started"
    release = tmp_path / "release"
    monkeypatch.setenv("DMB_HERMES_HOST_STARTED", str(started))
    monkeypatch.setenv("DMB_HERMES_HOST_RELEASE", str(release))
    host = HermesGraphAgentHost(worker_target=_holding_worker, turn_timeout_s=15.0)
    results: list[HermesGraphAgentTurnResult | None] = [None, None]

    def _run(index: int, question: str) -> None:
        results[index] = host.execute(_request(question=question))

    try:
        t1 = threading.Thread(target=_run, args=(0, "a"))
        t2 = threading.Thread(target=_run, args=(1, "b"))
        t1.start()
        deadline = time.time() + 5
        while time.time() < deadline and not started.exists():
            time.sleep(0.01)
        assert started.exists()
        first_id = started.read_text(encoding="utf-8")
        t2.start()
        time.sleep(0.1)
        assert started.read_text(encoding="utf-8") == first_id
        release.write_text("go", encoding="utf-8")
        t1.join(timeout=10)
        t2.join(timeout=10)
        assert results[0] is not None and results[0].status == "ok"
        assert results[1] is not None and results[1].status == "ok"
        assert results[0].final_response != results[1].final_response
    finally:
        release.write_text("go", encoding="utf-8")
        host.shutdown()


def test_pre_accept_failure_can_restart_without_duplicate_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flag = tmp_path / "died"
    monkeypatch.setenv("DMB_HERMES_HOST_DIE_FLAG", str(flag))
    host = HermesGraphAgentHost(
        worker_target=_die_before_accept_once_worker,
        accept_timeout_s=2.0,
    )
    try:
        result = host.execute(_request(question="recover"))
        assert result.status == "ok"
        assert flag.exists()
        assert result.final_response == "Tripod is near the North Gate."
    finally:
        host.shutdown()


def test_post_accept_crash_is_not_replayed() -> None:
    host = HermesGraphAgentHost(
        worker_target=_crash_after_accept_worker,
        accept_timeout_s=2.0,
        turn_timeout_s=2.0,
    )
    try:
        result = host.execute(_request(question="crash"))
        assert result.status == "error"
        assert result.error_code == "hermes_worker_lost"
    finally:
        host.shutdown()


def test_timeout_discards_worker_and_is_not_replayed() -> None:
    host = HermesGraphAgentHost(
        worker_target=_slow_after_accept_worker,
        accept_timeout_s=2.0,
        turn_timeout_s=0.2,
    )
    try:
        result = host.execute(_request(question="slow"))
        assert result.status == "error"
        assert result.error_code == "hermes_worker_timeout"
        assert host.worker_pid is None
    finally:
        host.shutdown()


def test_same_host_recovers_after_post_accept_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flag = tmp_path / "crashed"
    monkeypatch.setenv("DMB_HERMES_HOST_CRASH_FLAG", str(flag))
    host = HermesGraphAgentHost(
        worker_target=_crash_once_then_ok_worker,
        accept_timeout_s=2.0,
        turn_timeout_s=2.0,
    )
    try:
        host.start()
        first_pid = host.worker_pid
        assert first_pid is not None
        first = host.execute(_request(question="crash-once"))
        assert first.status == "error"
        assert first.error_code == "hermes_worker_lost"
        assert not Path(f"/proc/{first_pid}").exists()
        second = host.execute(_request(question="recover"))
        assert second.status == "ok"
        assert second.final_response == "Tripod is near the North Gate."
        assert host.worker_pid is not None
        assert host.worker_pid != first_pid
    finally:
        host.shutdown()


def test_shutdown_terminates_active_turn_promptly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accept_count = tmp_path / "accept_count"
    monkeypatch.setenv("DMB_HERMES_HOST_ACCEPT_COUNT", str(accept_count))
    host = HermesGraphAgentHost(
        worker_target=_accept_counting_slow_worker,
        turn_timeout_s=60.0,
        accept_timeout_s=2.0,
    )
    result_holder: list[HermesGraphAgentTurnResult | None] = [None]

    def _execute_turn() -> None:
        result_holder[0] = host.execute(_request(question="blocked"))

    try:
        host.start()
        worker_pid = None
        thread = threading.Thread(target=_execute_turn)
        thread.start()
        deadline = time.time() + 5
        while time.time() < deadline and not accept_count.exists():
            time.sleep(0.01)
        assert accept_count.exists()
        worker_pid = host.worker_pid
        assert worker_pid is not None
        shutdown_started = time.monotonic()
        shutdown_thread = threading.Thread(
            target=lambda: host.shutdown(timeout_s=2.0),
        )
        shutdown_thread.start()
        shutdown_thread.join(timeout=5.0)
        thread.join(timeout=5.0)
        assert shutdown_thread.is_alive() is False
        assert time.monotonic() - shutdown_started < 5.0
        assert result_holder[0] is not None
        assert result_holder[0].status == "error"
        assert result_holder[0].error_code in {
            "hermes_worker_lost",
            "hermes_worker_timeout",
        }
        assert accept_count.read_text(encoding="utf-8") == "1"
        assert host.worker_pid is None
        if worker_pid is not None:
            assert not Path(f"/proc/{worker_pid}").exists()
    finally:
        host.shutdown()


def test_execute_after_shutdown_returns_start_failed() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    host.shutdown()
    result = host.execute(_request(question="after-shutdown"))
    assert result.status == "error"
    assert result.error_code == "hermes_worker_start_failed"


def test_start_cleans_dead_worker_handles() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    try:
        host.start()
        first_pid = host.worker_pid
        assert first_pid is not None
        os.kill(first_pid, 9)
        deadline = time.time() + 2
        while time.time() < deadline and Path(f"/proc/{first_pid}").exists():
            time.sleep(0.01)
        host.start()
        second_pid = host.worker_pid
        assert second_pid is not None
        assert second_pid != first_pid
        result = host.execute(_request(question="after-death"))
        assert result.status == "ok"
    finally:
        host.shutdown()


def test_shutdown_leaves_no_live_worker() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    host.start()
    pid = host.worker_pid
    assert pid is not None
    host.shutdown()
    assert host.worker_pid is None
    assert not Path(f"/proc/{pid}").exists()


def test_repeated_start_stop_cycles() -> None:
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    for _ in range(3):
        host.start()
        result = host.execute(_request(question="cycle"))
        assert result.status == "ok"
        host.shutdown()
        assert host.worker_pid is None


def test_app_lifespan_shuts_down_global_host() -> None:
    shutdown_hermes_graph_agent_host()
    from apps.live_control_server.main import create_app

    application = create_app()
    with TestClient(application) as client:
        response = client.get("/health")
        assert response.status_code == 200
        host = get_hermes_graph_agent_host()
        host.shutdown()
        host._worker_target = _stub_worker_main  # noqa: SLF001
        host.start()
        pid = host.worker_pid
        assert pid is not None
    time.sleep(0.05)
    if pid is not None:
        assert not Path(f"/proc/{pid}").exists()


def test_shutdown_terminates_never_ready_worker_within_bound() -> None:
    host = HermesGraphAgentHost(
        worker_target=_never_ready_worker,
        ready_timeout_s=30.0,
    )
    start_error: list[BaseException | None] = [None]

    def _start() -> None:
        try:
            host.start()
        except BaseException as exc:  # noqa: BLE001 — capture for assertion
            start_error[0] = exc

    try:
        thread = threading.Thread(target=_start)
        thread.start()
        deadline = time.time() + 5
        worker_pid = None
        while time.time() < deadline:
            worker_pid = host.worker_pid
            if worker_pid is not None and Path(f"/proc/{worker_pid}").exists():
                break
            time.sleep(0.01)
        assert worker_pid is not None
        assert Path(f"/proc/{worker_pid}").exists()
        shutdown_started = time.monotonic()
        host.shutdown(timeout_s=2.0)
        shutdown_elapsed = time.monotonic() - shutdown_started
        thread.join(timeout=5.0)
        assert thread.is_alive() is False
        assert shutdown_elapsed < 5.0
        assert host.worker_pid is None
        assert not Path(f"/proc/{worker_pid}").exists()
        assert start_error[0] is not None
    finally:
        host.shutdown(timeout_s=1.0)


def test_stale_execute_does_not_kill_replacement_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accept_count = tmp_path / "accept_count"
    monkeypatch.setenv("DMB_HERMES_HOST_ACCEPT_COUNT", str(accept_count))
    host = HermesGraphAgentHost(
        worker_target=_accept_counting_slow_worker,
        turn_timeout_s=60.0,
        accept_timeout_s=2.0,
    )
    result_holder: list[HermesGraphAgentTurnResult | None] = [None]

    def _execute_turn() -> None:
        result_holder[0] = host.execute(_request(question="stale"))

    try:
        host.start()
        first_pid = host.worker_pid
        assert first_pid is not None
        thread = threading.Thread(target=_execute_turn)
        thread.start()
        deadline = time.time() + 5
        while time.time() < deadline and not accept_count.exists():
            time.sleep(0.01)
        assert accept_count.exists()

        host.shutdown(timeout_s=2.0)
        assert not Path(f"/proc/{first_pid}").exists()

        host._worker_target = _stub_worker_main  # noqa: SLF001
        host.start()
        replacement_pid = host.worker_pid
        assert replacement_pid is not None
        assert replacement_pid != first_pid
        assert Path(f"/proc/{replacement_pid}").exists()

        thread.join(timeout=5.0)
        assert thread.is_alive() is False
        assert result_holder[0] is not None
        assert result_holder[0].status == "error"
        assert result_holder[0].error_code in {
            "hermes_worker_lost",
            "hermes_worker_timeout",
        }
        assert host.worker_pid == replacement_pid
        assert Path(f"/proc/{replacement_pid}").exists()

        recovered = host.execute(_request(question="after-replace"))
        assert recovered.status == "ok"
        assert recovered.final_response == "echo:after-replace"
        assert host.worker_pid == replacement_pid
    finally:
        host.shutdown()


def test_host_executes_real_aiagent_tool_turn_through_wire(tmp_path: Path) -> None:
    """End-to-end: host wire must carry a completed tool-using Hermes turn."""
    host = HermesGraphAgentHost(
        worker_target=_tool_using_aiagent_host_worker,
        turn_timeout_s=120.0,
        ready_timeout_s=90.0,
        accept_timeout_s=30.0,
    )
    try:
        result = host.execute(
            HermesGraphAgentTurnRequest(
                question="Where is Tripod?",
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
                session_id="sess-host-tool",
                root=tmp_path / "graph",
            )
        )
        assert result.status == "ok", (result.error_code, result.error_message)
        assert result.final_response == "Tripod stands at the North Gate."
        assert result.messages == []
        assert [event.tool_name for event in result.tool_events] == [
            "search_campaign_graph",
            "search_campaign_graph",
        ]
        assert [event.state for event in result.tool_events] == ["start", "completion"]
        assert result.tool_events[1].matched_node_ids == ["threat:tripod-null-calf"]
        assert result.tool_events[1].outcome == "enough"
        assert result.process_isolation == "process_exclusive"
    finally:
        host.shutdown()


def test_rung3_suite_entry_still_importable() -> None:
    result = run_hermes_graph_agent_turn(
        HermesGraphAgentTurnRequest(
            question="",
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
        )
    )
    assert result.status == "error"
    assert result.error_code == "invalid_request"
