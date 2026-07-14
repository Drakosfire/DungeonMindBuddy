"""Owning proofs for PR353 process-isolated Hermes graph-agent host."""

from __future__ import annotations

import ast
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


def _stub_worker_main(request_queue: Any, response_queue: Any) -> None:
    """Picklable stub worker that never imports Rung 3 turn execution."""
    response_queue.put({"type": "ready", "pid": os.getpid()})
    while True:
        message = request_queue.get()
        if message.get("type") == "shutdown":
            response_queue.put({"type": "shutdown_ack", "pid": os.getpid()})
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        response_queue.put(
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()}
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
        response_queue.put(
            {
                "type": "result",
                "requestId": request_id,
                "pid": os.getpid(),
                "payload": result,
            }
        )


def _slow_after_accept_worker(request_queue: Any, response_queue: Any) -> None:
    response_queue.put({"type": "ready", "pid": os.getpid()})
    while True:
        message = request_queue.get()
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        response_queue.put(
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()}
        )
        time.sleep(60)


def _crash_after_accept_worker(request_queue: Any, response_queue: Any) -> None:
    response_queue.put({"type": "ready", "pid": os.getpid()})
    message = request_queue.get()
    if message.get("type") == "execute":
        request_id = str(message.get("requestId") or "")
        response_queue.put(
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()}
        )
        os._exit(1)


def _die_before_accept_once_worker(request_queue: Any, response_queue: Any) -> None:
    """Module-level worker using env flag for one pre-accept death."""
    flag_path = Path(os.environ["DMB_HERMES_HOST_DIE_FLAG"])
    response_queue.put({"type": "ready", "pid": os.getpid()})
    message = request_queue.get()
    if message.get("type") == "shutdown":
        return
    if not flag_path.exists():
        flag_path.write_text("died-once", encoding="utf-8")
        os._exit(1)
    request_id = str(message.get("requestId") or "")
    response_queue.put({"type": "accepted", "requestId": request_id, "pid": os.getpid()})
    response_queue.put(
        {
            "type": "result",
            "requestId": request_id,
            "pid": os.getpid(),
            "payload": serialize_hermes_graph_agent_turn_result(_ok_result()),
        }
    )


def _holding_worker(request_queue: Any, response_queue: Any) -> None:
    started_path = Path(os.environ["DMB_HERMES_HOST_STARTED"])
    release_path = Path(os.environ["DMB_HERMES_HOST_RELEASE"])
    response_queue.put({"type": "ready", "pid": os.getpid()})
    while True:
        message = request_queue.get()
        if message.get("type") == "shutdown":
            return
        if message.get("type") != "execute":
            continue
        request_id = str(message.get("requestId") or "")
        response_queue.put(
            {"type": "accepted", "requestId": request_id, "pid": os.getpid()}
        )
        started_path.write_text(request_id, encoding="utf-8")
        deadline = time.time() + 10
        while time.time() < deadline:
            if release_path.exists():
                break
            time.sleep(0.01)
        response_queue.put(
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
            }
        )


def test_host_module_does_not_call_rung3_at_import() -> None:
    source = HOST_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_level_imported_run = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(
            "hermes_graph_agent"
        ):
            for alias in node.names:
                if alias.name == "run_hermes_graph_agent_turn":
                    module_level_imported_run = True
    assert module_level_imported_run is False
    preamble = source.split("def hermes_graph_agent_worker_main", 1)[0]
    assert "run_hermes_graph_agent_turn(" not in preamble


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
    restored_result = deserialize_hermes_graph_agent_turn_result(result_wire)
    assert restored_result.status == "ok"
    assert restored_result.final_response == result.final_response
    assert restored_result.hermes_session_id == result.hermes_session_id


def test_deserialize_rejects_forbidden_factory_fields() -> None:
    wire = serialize_hermes_graph_agent_turn_request(_request())
    wire["agentFactory"] = "evil"
    with pytest.raises(ValueError, match="forbidden"):
        deserialize_hermes_graph_agent_turn_request(wire)


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


def test_subsequent_request_can_use_fresh_worker_after_loss() -> None:
    host = HermesGraphAgentHost(
        worker_target=_crash_after_accept_worker,
        accept_timeout_s=2.0,
        turn_timeout_s=2.0,
    )
    try:
        lost = host.execute(_request(question="crash"))
        assert lost.error_code == "hermes_worker_lost"
    finally:
        host.shutdown()

    host2 = HermesGraphAgentHost(worker_target=_stub_worker_main)
    try:
        ok = host2.execute(_request(question="after"))
        assert ok.status == "ok"
        assert ok.final_response == "echo:after"
    finally:
        host2.shutdown()


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
    # Lifespan finally calls shutdown_hermes_graph_agent_host().
    time.sleep(0.05)
    if pid is not None:
        assert not Path(f"/proc/{pid}").exists()


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
