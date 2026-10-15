"""Private capture observes one actual dispatch without becoming authority."""

from dataclasses import replace
import json
import stat
from types import SimpleNamespace

import pytest

from apps.live_control_server.services import agent_runtime_evidence as evidence
from apps.live_control_server.services.agent_runtime import (
    AgentCapabilityPolicy,
    AgentContextPacket,
    AgentRunOptions,
    AgentRuntimeDescriptor,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
    AgentSurfaceContext,
    AgentWorldScope,
)


def invocation():
    return AgentRuntimeInvocation(
        thread_id="thread",
        turn_id="../../untrusted",
        message="What does the keeper believe?",
        conversation_history=None,
        context_packet=AgentContextPacket(
            world_scope=AgentWorldScope(
                "native-world", "", {}, "gm", "rev:one", "world"
            ),
            surface_context=AgentSurfaceContext("build", "document:one"),
        ),
        capability_policy=AgentCapabilityPolicy("world_graph_read_v1"),
        run_options=AgentRunOptions(),
    )


def runtime(result=None, error=None):
    calls = []

    def run(value):
        calls.append(value)
        if error is not None:
            raise error
        return result

    return SimpleNamespace(
        descriptor=AgentRuntimeDescriptor("fake", "test", "test", "graph"),
        run=run,
        calls=calls,
    )


def test_exact_returned_messages_receipts_scope_and_no_configuration_capture(
    tmp_path, monkeypatch
):
    directory = tmp_path / "private"
    monkeypatch.setenv(evidence.ENV, str(directory))
    monkeypatch.setenv("OPENAI_API_KEY", "configuration-must-not-leak")
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call:one",
                    "function": {
                        "name": "expand_graph_retrieval",
                        "arguments": '{"operation":"object","targets":[{"id":"keeper"}]}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call:one",
            "content": '{"text":"The keeper believes it may rain."}',
        },
    ]
    packet = {
        "id": "session:one",
        "source_reads": [
            {
                "source_read_id": "read:one",
                "anchor_id": "anchor:one",
                "content_sha256": "digest",
            }
        ],
    }
    result = AgentRuntimeResult(
        status="ok",
        final_text="The keeper expects rain.",
        messages=messages,
        context_updates={"retrieval_session": packet},
        runtime_metadata={"secret": "must-not-capture"},
    )
    adapter = runtime(result)
    sent = invocation()
    assert (
        evidence.run_with_private_evidence(
            adapter,
            sent,
            binding={
                "world_id": "managed-world",
                "turn_id": "durable-turn",
                "conversation_id": "conversation",
                "attempt": 2,
            },
        )
        is result
    )
    assert adapter.calls == [sent]
    (record_path,) = directory.glob("*-result.json")
    text = record_path.read_text()
    record = json.loads(text)
    assert record["result"]["messages"] == messages
    assert record["result"]["retrieval_session"] == packet
    assert (
        record["binding"]["turn_id"] == "durable-turn"
        and record["binding"]["attempt"] == 2
    )
    assert (
        record["invocation"]["context_packet"]["world_scope"]["revision_id"]
        == "rev:one"
    )
    assert record["input_kind"] == "runtime_invocation_not_provider_wire"
    assert all(record["implementation_sha256"].values())
    assert "configuration-must-not-leak" not in text and "must-not-capture" not in text
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in directory.iterdir())
    assert not (tmp_path / "untrusted").exists()


@pytest.mark.parametrize(
    "mode", ["disabled", "other_surface", "private_error", "too_large"]
)
def test_capture_failure_or_disabled_does_not_change_or_repeat_execution(
    tmp_path, monkeypatch, caplog, mode
):
    directory = tmp_path / "private"
    sent = invocation()
    if mode == "disabled":
        monkeypatch.delenv(evidence.ENV, raising=False)
    else:
        monkeypatch.setenv(evidence.ENV, str(directory))
    if mode == "other_surface":
        sent = replace(
            sent,
            context_packet=replace(
                sent.context_packet, surface_context=AgentSurfaceContext("plan")
            ),
        )
    if mode == "private_error":
        directory.mkdir(mode=0o755)
    if mode == "too_large":
        monkeypatch.setattr(evidence, "MAX_PAYLOAD_BYTES", 1)
    result = AgentRuntimeResult(status="ok", final_text="answer")
    adapter = runtime(result)
    assert evidence.run_with_private_evidence(adapter, sent, binding={}) is result
    assert len(adapter.calls) == 1
    if mode in {"disabled", "other_surface"}:
        assert not directory.exists()
    else:
        assert "input_capture_failed" in caplog.text


@pytest.mark.parametrize("exception", [False, True])
def test_failed_runtime_and_exception_preserve_available_evidence(
    tmp_path, monkeypatch, exception
):
    monkeypatch.setenv(evidence.ENV, str(tmp_path / "private"))
    result = AgentRuntimeResult(
        status="error",
        error_code="hermes_worker_timeout",
        messages=[{"role": "user", "content": "question"}],
    )
    failure = RuntimeError("secret exception detail") if exception else None
    adapter = runtime(result, failure)
    if exception:
        with pytest.raises(RuntimeError, match="secret exception detail"):
            evidence.run_with_private_evidence(
                adapter, invocation(), binding={"turn_id": "one"}
            )
    else:
        assert (
            evidence.run_with_private_evidence(
                adapter, invocation(), binding={"turn_id": "one"}
            )
            is result
        )
    (record_path,) = (tmp_path / "private").glob("*-result.json")
    text = record_path.read_text()
    record = json.loads(text)
    assert len(adapter.calls) == 1 and "secret exception detail" not in text
    if exception:
        assert record["result"] is None and record["exception_class"] == "RuntimeError"
        assert record["capture_completeness"] == "input_only_runtime_exception"
    else:
        assert record["result"]["error_code"] == "hermes_worker_timeout"


def test_private_publication_rejects_overwrite_symlink_and_escape(tmp_path):
    root = tmp_path / "private"
    evidence._publish(root, "one.json", {"value": "first"})
    with pytest.raises(FileExistsError):
        evidence._publish(root, "one.json", {"value": "second"})
    assert json.loads((root / "one.json").read_text()) == {"value": "first"}
    with pytest.raises(ValueError):
        evidence._publish(root, "../outside.json", {})
    alias = tmp_path / "alias"
    alias.symlink_to(root)
    with pytest.raises(ValueError):
        evidence._publish(alias, "two.json", {})
    assert not (tmp_path / "outside.json").exists()


def test_output_limit_records_explicit_incomplete_without_altering_result(
    tmp_path, monkeypatch
):
    directory = tmp_path / "private"
    monkeypatch.setenv(evidence.ENV, str(directory))
    monkeypatch.setattr(evidence, "MAX_PAYLOAD_BYTES", 10000)
    result = AgentRuntimeResult(status="ok", messages=[{"content": "x" * 20000}])
    adapter = runtime(result)
    assert (
        evidence.run_with_private_evidence(adapter, invocation(), binding={}) is result
    )
    (record_path,) = directory.glob("*-incomplete.json")
    assert json.loads(record_path.read_text())["reason"] == "capture_size_limit"
    assert not list(directory.glob("*-result.json"))
    assert len(adapter.calls) == 1


def test_directory_capacity_does_not_overwrite_existing_evidence(tmp_path, monkeypatch):
    root = tmp_path / "private"
    evidence._publish(root, "one.json", {"existing": "kept"})
    existing = (root / "one.json").read_bytes()
    monkeypatch.setattr(evidence, "MAX_DIRECTORY_BYTES", len(existing))
    with pytest.raises(OverflowError, match="capture_directory_limit"):
        evidence._publish(root, "two.json", {})
    assert (root / "one.json").read_bytes() == existing
    assert not (root / "two.json").exists()
