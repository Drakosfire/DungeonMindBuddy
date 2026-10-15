"""Pinned private dispatcher integration uses real vendor budgets and call pairing."""

from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.live_control_server.services.hermes_graph_dispatch_adapter import (
    install_graph_serial_dispatch,
)
from apps.live_control_server.services.hermes_graph_agent import (
    hermes_import_namespace,
    import_hermes_aiagent,
)


def _call(i):
    return SimpleNamespace(
        id=f"call:{i}",
        type="function",
        function=SimpleNamespace(
            name="expand_graph_retrieval",
            arguments=json.dumps({"queryText": f"keeper {i}"}),
        ),
    )


def _agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cls = import_hermes_aiagent()
    with hermes_import_namespace(), patch("run_agent.OpenAI"):
        agent = cls(
            api_key="test-key-1234567890",
            provider="openai-api",
            model="gpt-6-luna",
            base_url="https://api.openai.com/v1",
            api_mode="chat_completions",
            quiet_mode=True,
            skip_memory=True,
            skip_context_files=True,
            enabled_toolsets=[],
            request_overrides={"parallel_tool_calls": False},
        )
    agent.tool_delay = 0
    agent.save_trajectories = False
    agent.compression_enabled = False
    return agent


def test_actual_dispatcher_multi_call_pairing_and_budget(tmp_path, monkeypatch):
    agent = _agent(tmp_path, monkeypatch)
    calls = []
    from apps.live_control_server.services.graph_tool_transport import (
        GraphToolPageCache,
        TransportScope,
    )

    raw = json.dumps(
        {
            "schema": "dmb_world_graph_source_anchor_read_v1",
            "content": "x" * 60000 + "Ω" * 20,
            "anchorId": "opaque:one",
            "sourceReadId": "read:one",
        },
        ensure_ascii=False,
    )
    content = GraphToolPageCache().present(
        "read_graph_source",
        {"anchorIds": ["opaque:one"]},
        TransportScope("session:one", "world:one", "rev:one"),
        raw,
    )
    assert len(content.encode()) <= 8000

    with hermes_import_namespace():
        import run_agent

        def execute(name, args, *positional, **kwargs):
            calls.append(args["queryText"])
            return content

        monkeypatch.setattr(run_agent, "handle_function_call", execute)
        install_graph_serial_dispatch(agent)
        batch = SimpleNamespace(tool_calls=[_call(i) for i in range(32)], content=None)
        original = deepcopy(batch)
        assistant = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in batch.tool_calls
            ],
        }
        messages = [assistant]
        agent._execute_tool_calls(batch, messages, "task:one", 7)
        assert batch == original
        assert messages[0] is assistant
        assert [m["tool_call_id"] for m in messages[1:]] == [
            tc.id for tc in batch.tool_calls
        ]
        assert len(calls) == 32
        from agent.transports.chat_completions import ChatCompletionsTransport

        next_request = ChatCompletionsTransport().build_kwargs(
            model="gpt-6-luna",
            messages=messages,
            request_overrides={"parallel_tool_calls": False},
        )
        assert next_request["messages"][0]["tool_calls"] == assistant["tool_calls"]
        assert [m["tool_call_id"] for m in next_request["messages"][1:]] == [
            tc.id for tc in batch.tool_calls
        ]
        assert sum(len(m["content"]) for m in messages[1:]) > 200000
        assert all(
            json.loads(m["content"])["schema"] == "dmb_graph_tool_page_v1"
            for m in messages[1:]
        )


def test_actual_dispatcher_interrupt_skips_subsequent_graph_io(tmp_path, monkeypatch):
    agent = _agent(tmp_path, monkeypatch)
    calls = []
    with hermes_import_namespace():
        import run_agent

        def execute(name, args, *positional, **kwargs):
            calls.append(name)
            agent._interrupt_requested = True
            return '{"ok":true}'

        monkeypatch.setattr(run_agent, "handle_function_call", execute)
        install_graph_serial_dispatch(agent)
        batch = SimpleNamespace(tool_calls=[_call(i) for i in range(3)], content=None)
        messages = []
        agent._execute_tool_calls(batch, messages, "task:one", 1)
        assert len(calls) == 1
        assert [m["tool_call_id"] for m in messages] == [
            tc.id for tc in batch.tool_calls
        ]
        assert all("cancel" in m["content"].lower() for m in messages[1:])


def test_unsupported_signature_fails_explicitly():
    with pytest.raises(ValueError, match="signature_unsupported"):
        install_graph_serial_dispatch(
            SimpleNamespace(_execute_tool_calls=lambda x: None)
        )


@pytest.mark.parametrize("kind", ["chat", "responses"])
def test_actual_transports_preserve_parallel_false(kind):
    with hermes_import_namespace():
        if kind == "chat":
            from agent.transports.chat_completions import ChatCompletionsTransport

            transport = ChatCompletionsTransport()
        else:
            from agent.transports.codex import ResponsesApiTransport

            transport = ResponsesApiTransport()
        kwargs = transport.build_kwargs(
            model="gpt-6-luna",
            messages=[{"role": "user", "content": "test"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "test",
                        "description": "test",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            request_overrides={"parallel_tool_calls": False},
        )
        assert kwargs["parallel_tool_calls"] is False


def test_actual_dispatcher_policy_denial_performs_no_io(tmp_path, monkeypatch):
    agent = _agent(tmp_path, monkeypatch)
    with hermes_import_namespace():
        import run_agent
        from hermes_cli import plugins

        monkeypatch.setattr(
            plugins,
            "resolve_pre_tool_block",
            lambda *a, **k: "Denied by current capability policy",
        )
        monkeypatch.setattr(
            run_agent,
            "handle_function_call",
            lambda *a, **k: pytest.fail("denied operation executed"),
        )
        install_graph_serial_dispatch(agent)
        batch = SimpleNamespace(tool_calls=[_call(i) for i in range(3)], content=None)
        messages = []
        agent._execute_tool_calls(batch, messages, "task:one", 1)
        assert [m["tool_call_id"] for m in messages] == [
            tc.id for tc in batch.tool_calls
        ]
        assert all(
            "Denied by current capability policy" in m["content"] for m in messages
        )
