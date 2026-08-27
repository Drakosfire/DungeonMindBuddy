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
import apps.live_control_server.services.hermes_graph_agent_host as hermes_host_mod
from apps.live_control_server.services.hermes_graph_agent_host import (
    HermesGraphAgentHost,
    _WorkerHandles,
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
from graph_memory.interaction.schema_constants import EXPAND_GRAPH_RETRIEVAL_SCHEMA

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


def _await_proceed_or_shutdown(request_queue: Any, request_id: str) -> str:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
    )

    while True:
        message = decode_json_wire(request_queue.get())
        msg_type = message.get("type")
        if msg_type == "shutdown":
            return "shutdown"
        if msg_type == "proceed" and str(message.get("requestId") or "") == request_id:
            return "proceed"


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
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
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
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
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
        time.sleep(0.15)
        os._exit(1)


def _crash_once_then_ok_worker(request_queue: Any, response_queue: Any) -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    flag_path = Path(os.environ["DMB_HERMES_HOST_CRASH_FLAG"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        # Crash after accept is observed by parent, before/without completing proceed.
        time.sleep(0.15)
        if not flag_path.exists():
            flag_path.write_text("crashed-once", encoding="utf-8")
            os._exit(1)
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
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
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        if not flag_path.exists():
            flag_path.write_text("died-once", encoding="utf-8")
            os._exit(1)
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
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
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
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
        if message.get("type") == "proceed":
            continue
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
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
        time.sleep(60)


def _never_ready_worker(request_queue: Any, response_queue: Any) -> None:
    """Starts but never emits ready — simulates hung Rung 3 import."""
    del request_queue, response_queue
    while True:
        time.sleep(60)


def _side_effect_counting_worker(request_queue: Any, response_queue: Any) -> None:
    """Increments a counter only after proceed — proves Rung-3-equivalent work."""
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    counter_path = Path(os.environ["DMB_HERMES_HOST_SIDE_EFFECT_COUNT"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
        count = 0
        if counter_path.exists():
            count = int(counter_path.read_text(encoding="utf-8") or "0")
        counter_path.write_text(str(count + 1), encoding="utf-8")
        payload = message.get("payload") or {}
        question = str(payload.get("question") or "")
        _put_json(
            response_queue,
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": serialize_hermes_graph_agent_turn_result(
                    HermesGraphAgentTurnResult(
                        status="ok",
                        final_response=f"effect:{question}",
                        messages=[],
                        hermes_session_id=f"worker-{os.getpid()}",
                        tool_events=[],
                        process_isolation="process_exclusive",
                    )
                ),
            },
        )


def _accept_then_drop_worker(request_queue: Any, response_queue: Any) -> None:
    """Emits accepted then waits for proceed; used with parent accept-loss simulation."""
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    counter_path = Path(os.environ["DMB_HERMES_HOST_SIDE_EFFECT_COUNT"])
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
        count = 0
        if counter_path.exists():
            count = int(counter_path.read_text(encoding="utf-8") or "0")
        counter_path.write_text(str(count + 1), encoding="utf-8")
        _put_json(
            response_queue,
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": serialize_hermes_graph_agent_turn_result(_ok_result()),
            },
        )


def _term_resistant_worker(request_queue: Any, response_queue: Any) -> None:
    """Ignores graceful shutdown and SIGTERM; only SIGKILL stops it."""
    import signal

    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
    )

    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        try:
            message = decode_json_wire(request_queue.get(timeout=0.5))
        except Exception:
            continue
        if message.get("type") == "shutdown":
            # Ignore graceful shutdown requests.
            continue
        if message.get("type") == "execute":
            request_id = str(message.get("requestId") or "")
            _put_json(
                response_queue,
                {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
            )
            _await_proceed_or_shutdown(request_queue, request_id)
            time.sleep(60)


def _slow_ready_worker(request_queue: Any, response_queue: Any) -> None:
    """Delays ready so overlapping start/execute can be scheduled."""
    from apps.live_control_server.services.hermes_graph_agent_contract import (
        decode_json_wire,
        serialize_hermes_graph_agent_turn_result,
    )

    counter_path = Path(os.environ["DMB_HERMES_HOST_SIDE_EFFECT_COUNT"])
    ready_gate = Path(os.environ["DMB_HERMES_HOST_READY_GATE"])
    deadline = time.time() + 10
    while time.time() < deadline and not ready_gate.exists():
        time.sleep(0.01)
    _put_json(response_queue, {"type": "ready", "pid": os.getpid()})
    while True:
        message = decode_json_wire(request_queue.get())
        if message.get("type") == "shutdown":
            return
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            return
        count = 0
        if counter_path.exists():
            count = int(counter_path.read_text(encoding="utf-8") or "0")
        counter_path.write_text(str(count + 1), encoding="utf-8")
        payload = message.get("payload") or {}
        question = str(payload.get("question") or "")
        _put_json(
            response_queue,
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": serialize_hermes_graph_agent_turn_result(
                    HermesGraphAgentTurnResult(
                        status="ok",
                        final_response=f"effect:{question}",
                        messages=[],
                        hermes_session_id=f"worker-{os.getpid()}",
                        tool_events=[],
                        process_isolation="process_exclusive",
                    )
                ),
            },
        )


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
        "schema": EXPAND_GRAPH_RETRIEVAL_SCHEMA,
        "retrievalSessionId": "sess:SPOOF",
        "operation": "search",
        "queryText": "Tripod",
    }
    tc = SimpleNamespace(
        id="call-graph-1",
        type="function",
        function=SimpleNamespace(
            name="expand_graph_retrieval",
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
        if message.get("type") == "proceed":
            continue
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        _put_json(
            response_queue,
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()},
        )
        if _await_proceed_or_shutdown(request_queue, request_id) == "shutdown":
            _put_json(response_queue, {"type": "shutdown_ack", "pid": os.getpid()})
            return
        try:
            payload = message.get("payload")
            request = deserialize_hermes_graph_agent_turn_request(payload)
            with patch(
                "graph_memory.hermes_graph_plugin.execute_hermes_graph_interaction_tool_json",
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
        enabled_tool_names=("expand_graph_retrieval",),
        graph_scope=_scope(),
        plugin_activations=(
            HermesPluginActivation(plugin_id=TOOLSET_NAME, toolsets=(TOOLSET_NAME,)),
        ),
        tool_rules=(
            HermesToolCapabilityRule(
                tool_name="expand_graph_retrieval",
                toolset=TOOLSET_NAME,
                require_graph_scope=False,
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
    assert restored.capability_policy.enabled_tool_names == ("expand_graph_retrieval",)
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


def test_history_rejects_unknown_keys_and_non_alternating_pairs() -> None:
    with pytest.raises(ValueError, match="unknown keys"):
        serialize_hermes_graph_agent_turn_request(
            _request(
                conversation_history=[
                    {"role": "user", "content": "hi", "trace": "RAW_TRACE_SECRET"},
                    {"role": "assistant", "content": "there"},
                ]
            )
        )
    with pytest.raises(ValueError, match="alternate"):
        serialize_hermes_graph_agent_turn_request(
            _request(
                conversation_history=[
                    {"role": "assistant", "content": "wrong"},
                    {"role": "user", "content": "order"},
                ]
            )
        )
    with pytest.raises(ValueError, match="user or assistant"):
        serialize_hermes_graph_agent_turn_request(
            _request(
                conversation_history=[
                    {"role": "system", "content": "hidden"},
                    {"role": "assistant", "content": "there"},
                ]
            )
        )


def test_history_round_trip_preserves_chronological_pairs() -> None:
    request = _request(
        conversation_history=[
            {"role": "user", "content": "Turn 1 question"},
            {"role": "assistant", "content": "Turn 1 answer"},
            {"role": "user", "content": "Turn 2 question"},
            {"role": "assistant", "content": "Turn 2 answer"},
        ]
    )
    wire = serialize_hermes_graph_agent_turn_request(request)
    restored = deserialize_hermes_graph_agent_turn_request(wire)
    assert restored.conversation_history == request.conversation_history


def test_oversized_policy_collections_rejected() -> None:
    policy = HermesCapabilityPolicy(
        enabled_toolsets=tuple(f"toolset-{index}" for index in range(MAX_POLICY_TOOLSETS + 1)),
        enabled_tool_names=("expand_graph_retrieval",),
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
                            "name": "expand_graph_retrieval",
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "name": "expand_graph_retrieval",
                "tool_call_id": "call-graph-1",
                "content": '{"outcome":"enough"}',
            },
            {"role": "assistant", "content": "Tripod stands at the North Gate."},
        ],
        hermes_session_id="sess-tool",
        tool_events=[
            HermesGraphToolEvent(tool_name="expand_graph_retrieval", state="start"),
            HermesGraphToolEvent(
                tool_name="expand_graph_retrieval",
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
        "expand_graph_retrieval",
        "expand_graph_retrieval",
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
        assert time.monotonic() - shutdown_started < 2.5
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
        assert shutdown_elapsed < 2.5
        assert host.worker_pid is None
        assert not Path(f"/proc/{worker_pid}").exists()
        assert start_error[0] is not None
    finally:
        host.shutdown(timeout_s=1.0)


def test_overlapping_start_and_execute_run_each_request_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter = tmp_path / "side_effects"
    ready_gate = tmp_path / "ready_gate"
    monkeypatch.setenv("DMB_HERMES_HOST_SIDE_EFFECT_COUNT", str(counter))
    monkeypatch.setenv("DMB_HERMES_HOST_READY_GATE", str(ready_gate))
    host = HermesGraphAgentHost(
        worker_target=_slow_ready_worker,
        ready_timeout_s=10.0,
        turn_timeout_s=15.0,
    )
    start_error: list[BaseException | None] = [None]
    result_holder: list[HermesGraphAgentTurnResult | None] = [None]

    def _start() -> None:
        try:
            host.start()
        except BaseException as exc:  # noqa: BLE001
            start_error[0] = exc

    def _execute() -> None:
        result_holder[0] = host.execute(_request(question="once"))

    try:
        start_thread = threading.Thread(target=_start)
        exec_thread = threading.Thread(target=_execute)
        start_thread.start()
        time.sleep(0.05)
        exec_thread.start()
        time.sleep(0.05)
        ready_gate.write_text("go", encoding="utf-8")
        start_thread.join(timeout=15.0)
        exec_thread.join(timeout=15.0)
        assert start_thread.is_alive() is False
        assert exec_thread.is_alive() is False
        assert start_error[0] is None
        assert result_holder[0] is not None
        assert result_holder[0].status == "ok"
        assert result_holder[0].final_response == "effect:once"
        assert counter.exists()
        assert counter.read_text(encoding="utf-8") == "1"
    finally:
        ready_gate.write_text("go", encoding="utf-8")
        host.shutdown()


def test_lost_accept_does_not_replay_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If accepted is emitted but parent fails to observe it, no proceed → no duplicate work."""
    counter = tmp_path / "side_effects"
    monkeypatch.setenv("DMB_HERMES_HOST_SIDE_EFFECT_COUNT", str(counter))
    host = HermesGraphAgentHost(
        worker_target=_accept_then_drop_worker,
        accept_timeout_s=2.0,
        turn_timeout_s=10.0,
    )
    original_recv = HermesGraphAgentHost._recv_until
    lost_once = {"done": False}

    def _lose_first_accept(
        self: HermesGraphAgentHost,
        response_queue: Any,
        process: Any,
        *,
        expected_types: set[str],
        request_id: str | None,
        timeout_s: float,
    ) -> dict[str, Any] | None:
        message = original_recv(
            self,
            response_queue,
            process,
            expected_types=expected_types,
            request_id=request_id,
            timeout_s=timeout_s,
        )
        if (
            not lost_once["done"]
            and message is not None
            and "accepted" in expected_types
            and message.get("type") == "accepted"
        ):
            lost_once["done"] = True
            # Parent failed to observe acceptance; worker still waits for proceed.
            return None
        return message

    monkeypatch.setattr(HermesGraphAgentHost, "_recv_until", _lose_first_accept)
    try:
        result = host.execute(_request(question="lost-accept"))
        assert result.status == "ok"
        assert lost_once["done"] is True
        assert counter.exists()
        assert counter.read_text(encoding="utf-8") == "1"
    finally:
        host.shutdown()


def test_shutdown_deadline_kills_term_resistant_worker() -> None:
    host = HermesGraphAgentHost(
        worker_target=_term_resistant_worker,
        ready_timeout_s=10.0,
    )
    try:
        host.start()
        pid = host.worker_pid
        assert pid is not None
        assert Path(f"/proc/{pid}").exists()
        started = time.monotonic()
        host.shutdown(timeout_s=2.0)
        elapsed = time.monotonic() - started
        assert elapsed < 2.5
        assert host.worker_pid is None
        assert not Path(f"/proc/{pid}").exists()
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
                retrieval_session_id="sess-host-tool",
                root=tmp_path / "graph",
            )
        )
        assert result.status == "ok", (result.error_code, result.error_message)
        assert result.final_response == "Tripod stands at the North Gate."
        assert result.messages == []
        assert [event.tool_name for event in result.tool_events] == [
            "expand_graph_retrieval",
            "expand_graph_retrieval",
        ]
        assert [event.state for event in result.tool_events] == ["start", "completion"]
        assert result.tool_events[1].matched_node_ids == ["threat:tripod-null-calf"]
        assert result.tool_events[1].outcome == "enough"
        assert result.process_isolation == "process_exclusive"
    finally:
        host.shutdown()


class _ImmortalProcess:
    """Deterministic fake whose is_alive() stays True after terminate/kill."""

    def __init__(self, pid: int = 424242) -> None:
        self.pid = pid
        self.terminate_calls = 0
        self.kill_calls = 0

    def is_alive(self) -> bool:
        return True

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1

    def join(self, timeout: float | None = None) -> None:
        return None


class _FakeQueue:
    def put(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def close(self) -> None:
        return None

    def get(self, timeout: float | None = None) -> bytes:
        raise TimeoutError("fake queue empty")


def test_immortal_worker_stays_tracked_blocks_spawn_and_retains_global_host() -> None:
    """A process that survives kill must stay tracked; no second worker allowed."""
    immortal = _ImmortalProcess(pid=424242)
    fake_handles = _WorkerHandles(
        process=immortal,  # type: ignore[arg-type]
        request_queue=_FakeQueue(),  # type: ignore[arg-type]
        response_queue=_FakeQueue(),  # type: ignore[arg-type]
        pid=424242,
    )
    host = HermesGraphAgentHost(worker_target=_stub_worker_main)
    with host._worker_lock:  # noqa: SLF001
        host._worker = fake_handles  # noqa: SLF001
        host._worker_ready = False  # noqa: SLF001 — force spawn/stop path
        host._started = True  # noqa: SLF001
        host._closed = False  # noqa: SLF001

    shutdown_hermes_graph_agent_host(timeout_s=0.1)
    with hermes_host_mod._HOST_LOCK:  # noqa: SLF001
        hermes_host_mod._GLOBAL_HOST = host  # noqa: SLF001

    try:
        with pytest.raises(RuntimeError, match="still alive"):
            host._spawn_worker()  # noqa: SLF001
        assert host._worker is fake_handles  # noqa: SLF001
        assert host.worker_pid == 424242

        stopped = host.shutdown(timeout_s=0.5)
        assert stopped is False
        assert host._worker is fake_handles  # noqa: SLF001
        assert host.worker_pid == 424242
        assert immortal.terminate_calls >= 1
        assert immortal.kill_calls >= 1

        cleared = shutdown_hermes_graph_agent_host(timeout_s=0.5)
        assert cleared is False
        assert hermes_host_mod._GLOBAL_HOST is host  # noqa: SLF001
        assert get_hermes_graph_agent_host() is host
        assert host.worker_pid == 424242
    finally:
        with host._worker_lock:  # noqa: SLF001
            host._worker = None  # noqa: SLF001
            host._worker_ready = False  # noqa: SLF001
            host._closed = True  # noqa: SLF001
        with hermes_host_mod._HOST_LOCK:  # noqa: SLF001
            if hermes_host_mod._GLOBAL_HOST is host:  # noqa: SLF001
                hermes_host_mod._GLOBAL_HOST = None  # noqa: SLF001


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


def test_model_call_fields_survive_host_wire_round_trip() -> None:
    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="Tripod is near the North Gate.",
        messages=[],
        hermes_session_id="sess-trace",
        tool_events=[],
        process_isolation="process_exclusive",
        model_calls=[
            {
                "call_id": "model-call-1",
                "runtime_api_request_id": "api-req-1",
                "runtime_turn_id": "hermes-turn-1",
                "sequence": 1,
                "status": "ok",
                "provider": "openai-api",
                "requested_model": "gpt-5.4-mini",
                "response_model": "gpt-5.4-mini",
                "api_mode": "chat_completions",
                "started_at": "2026-08-26T00:00:00.000000Z",
                "completed_at": "2026-08-26T00:00:00.250000Z",
                "duration_ms": 250,
                "request_summary": {
                    "api_call_count": 1,
                    "message_count": 4,
                    "tool_count": 2,
                    "approx_input_tokens": 100,
                    "request_char_count": 400,
                    "max_tokens": 2048,
                },
                "usage": {
                    "status": "reported",
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "cached_input_tokens": 0,
                    "reasoning_tokens": 12,
                },
                "cost": {
                    "status": "estimated",
                    "usd": 0.001,
                    "currency": "USD",
                    "pricing_table_matched": True,
                    "rates_per_1m_usd": {"input": 0.75, "cached_input": 0.075, "output": 4.5},
                },
                "finish_reason": "stop",
            }
        ],
        telemetry_warnings=["observer_payload_malformed"],
    )
    wire = serialize_hermes_graph_agent_turn_result(result)
    assert all("request" not in call and "response" not in call for call in wire["modelCalls"])
    restored = deserialize_hermes_graph_agent_turn_result(wire)
    assert restored.model_calls[0]["runtime_api_request_id"] == "api-req-1"
    assert restored.model_calls[0]["usage"]["input_tokens"] == 100
    assert restored.model_calls[0]["usage"]["reasoning_tokens"] == 12
    assert restored.telemetry_warnings == ["observer_payload_malformed"]


def test_model_call_forbidden_bodies_rejected_on_wire() -> None:
    result = _ok_result()
    object.__setattr__(
        result,
        "model_calls",
        [
            {
                "call_id": "model-call-leak",
                "sequence": 1,
                "status": "ok",
                "request": {"body": "RAW_PROMPT"},
                "usage": {"status": "unavailable"},
                "cost": {"status": "unavailable"},
                "request_summary": {},
            }
        ],
    )
    with pytest.raises(ValueError, match="forbidden keys"):
        serialize_hermes_graph_agent_turn_result(result)


def test_oversized_model_calls_rejected() -> None:
    from apps.live_control_server.services.hermes_graph_agent_contract import MAX_MODEL_CALLS

    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="ok",
        messages=[],
        hermes_session_id="sess-too-many",
        tool_events=[],
        process_isolation="process_exclusive",
        model_calls=[
            {
                "call_id": f"model-call-{index}",
                "sequence": index + 1,
                "status": "ok",
                "usage": {"status": "unavailable"},
                "cost": {"status": "unavailable"},
                "request_summary": {},
            }
            for index in range(MAX_MODEL_CALLS + 1)
        ],
    )
    with pytest.raises(ValueError, match="modelCalls"):
        serialize_hermes_graph_agent_turn_result(result)
