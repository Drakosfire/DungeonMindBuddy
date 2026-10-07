"""HermesAgentRuntimeAdapter maps DMB invocation/result onto the existing host."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.live_control_server.services.agent_runtime import (
    CONVERSATION_ONLY_POLICY,
    HERMES_RUNTIME_DESCRIPTOR,
    UNSUPPORTED_CAPABILITY_POLICY,
    WORLD_GRAPH_READ_POLICY,
    AgentCapabilityPolicy,
    AgentContextPacket,
    AgentRetrievalSession,
    AgentRunOptions,
    AgentRuntimeInvocation,
    AgentWorldScope,
)
from apps.live_control_server.services.hermes_agent_runtime import (
    HermesAgentRuntimeAdapter,
    map_hermes_result_to_runtime_result,
    map_invocation_to_hermes_request,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    HermesGraphToolEvent,
)
from graph_memory.hermes_graph_plugin import (
    ORDERED_MODEL_VISIBLE_TOOL_NAMES,
    TOOLSET_NAME,
)


def test_guarded_adapter_passes_final_answer_limits_unchanged() -> None:
    budget = {
        "schema": "dmb_hermes_request_budget_policy_v1",
        "provider": "openai-api", "model": "gpt-6-luna", "apiMode": "codex_responses",
        "estimator": "utf8_json_bytes_plus_64_per_node_v1",
        "contextLimitTokens": 1_050_000, "outputReserveTokens": 2048,
        "maxProviderAttempts": 4, "maxToolCapableAttempts": 3,
        "maxGraphOperations": 8,
    }
    result = HermesGraphAgentTurnResult(
        status="error", error_code="provider_authorization_denied",
        final_response=None, messages=[], hermes_session_id="test",
        tool_events=[], answer_scope=None,
    )

    class CapturingHost(_FakeHost):
        def execute(self, request: HermesGraphAgentTurnRequest, **kwargs: Any) -> HermesGraphAgentTurnResult:
            self.calls.append(request)
            assert callable(kwargs["on_provider_authorization"])
            assert callable(kwargs["on_graph_operation"])
            return self.result

    host = CapturingHost(result)
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    adapter.run_with_provider_authorization(
        _invocation(), lambda _view: False, request_budget=budget,
        on_graph_operation=lambda _message: {},
    )
    assert len(host.calls) == 1
    assert host.calls[0].request_budget == budget
    assert host.calls[0].provider_authorization_required is True
    assert host.calls[0].parent_graph_broker_required is True


class _FakeHost:
    def __init__(self, result: HermesGraphAgentTurnResult) -> None:
        self.result = result
        self.calls: list[HermesGraphAgentTurnRequest] = []
        self.pid = 4242

    @property
    def worker_pid(self) -> int:
        return self.pid

    def execute(
        self,
        request: HermesGraphAgentTurnRequest,
        *,
        timeout_s: float | None = None,
        on_host_phase: Any = None,
    ) -> HermesGraphAgentTurnResult:
        del timeout_s
        self.calls.append(request)
        if on_host_phase is not None:
            on_host_phase(
                {
                    "span_id": "group:1",
                    "parent_span_id": None,
                    "kind": "phase",
                    "name": "host_worker_result_wait",
                    "status": "ok",
                    "started_at": "2026-10-02T00:00:00Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 1,
                    "attributes": {"host_phase_group_id": "group"},
                }
            )
        return self.result


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
                focus={
                    "kind": "session",
                    "session_id": "session-21",
                    "campaign_id": None,
                },
                admissibility="gm",
                revision_id="revision:resolved-server",
            ),
            retrieval_session=AgentRetrievalSession(
                session_id="retrieval-sess-1",
                packet={
                    "schema": "dmb_graph_retrieval_session_v1",
                    "id": "retrieval-sess-1",
                },
            ),
        ),
        "capability_policy": WORLD_GRAPH_READ_POLICY,
        "run_options": AgentRunOptions(
            runtime_session_id="runtime-continue",
            execution_root=Path("/tmp/graph-root"),
        ),
    }
    values.update(overrides)
    return AgentRuntimeInvocation(**values)


def _hermes_ok_result() -> HermesGraphAgentTurnResult:
    retry = {
        "schema": "dmb_agent_model_call_v1",
        "call_id": "call-1",
        "sequence": 1,
        "status": "error",
        "provider": "openai-api",
        "model": "gpt-5.4",
        "error_code": "rate_limited",
        "usage": {"status": "unavailable"},
        "cost": {"status": "unpriced", "usd": None, "currency": "USD"},
    }
    success = {
        "schema": "dmb_agent_model_call_v1",
        "call_id": "call-2",
        "sequence": 2,
        "status": "ok",
        "provider": "openai-api",
        "model": "gpt-5.4",
        "runtime_api_request_id": "api-req-2",
        "usage": {
            "status": "reported",
            "input_tokens": 18_000,
            "cached_tokens": 18_000,
            "output_tokens": 400,
            "total_tokens": 18_400,
        },
        "cost": {"status": "estimated", "usd": 0.0105, "currency": "USD"},
    }
    return HermesGraphAgentTurnResult(
        status="ok",
        final_response="Tripod stands at the North Gate.",
        messages=[{"role": "assistant", "content": "ignored"}],
        hermes_session_id="hermes-internal-s1",
        tool_events=[
            HermesGraphToolEvent(
                tool_name="expand_graph_retrieval",
                state="start",
                duration_ms=None,
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
            ),
            HermesGraphToolEvent(
                tool_name="expand_graph_retrieval",
                state="completion",
                duration_ms=12.0,
                world_id="world:eldyrwild",
                campaign_id="campaign:c1",
                focus={"kind": "session", "sessionId": "session-21"},
                admissibility="gm",
                revision_pin="revision:resolved-server",
                outcome="enough",
                matched_node_ids=["threat:tripod-null-calf"],
                source_anchor_ids=["anchor:a1"],
                diagnostic_codes=["ok"],
            ),
        ],
        process_isolation="process_exclusive",
        retrieval_session_id="retrieval-sess-1",
        retrieval_session={
            "schema": "dmb_graph_retrieval_session_v1",
            "id": "retrieval-sess-1",
        },
        answer_scope=None,
        model_calls=[retry, success],
        telemetry_warnings=["observer_retry"],
        observed_model_call_count=2,
    )


def test_adapter_maps_invocation_onto_existing_host(tmp_path: Path) -> None:
    host = _FakeHost(_hermes_ok_result())
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    invocation = _invocation(
        run_options=AgentRunOptions(
            runtime_session_id="runtime-continue",
            execution_root=tmp_path,
        )
    )
    result = adapter.run(invocation)
    assert adapter.descriptor == HERMES_RUNTIME_DESCRIPTOR
    assert len(host.calls) == 1
    request = host.calls[0]
    assert request.question == "Where is Tripod?"
    assert request.world_id == "world:eldyrwild"
    assert request.campaign_id == "campaign:c1"
    assert request.focus == {
        "kind": "session",
        "sessionId": "session-21",
        "campaignId": None,
    }
    assert request.admissibility == "gm"
    assert request.revision_pin == "revision:resolved-server"
    assert request.conversation_history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    assert request.session_id == "runtime-continue"
    assert request.root == tmp_path.resolve()
    assert request.retrieval_session_id == "retrieval-sess-1"
    assert request.retrieval_session == {
        "schema": "dmb_graph_retrieval_session_v1",
        "id": "retrieval-sess-1",
    }
    assert request.capability_policy is not None
    assert request.capability_policy.enabled_toolsets == (TOOLSET_NAME,)
    assert (
        request.capability_policy.enabled_tool_names == ORDERED_MODEL_VISIBLE_TOOL_NAMES
    )
    assert all(
        "write" not in rule.allowed_effects
        for rule in request.capability_policy.tool_rules
    )
    assert result.status == "ok"
    assert result.final_text == "Tripod stands at the North Gate."
    assert result.runtime_session_id == "hermes-internal-s1"
    assert result.runtime_metadata["worker_pid"] == 4242
    assert result.runtime_metadata["process_isolation"] == "process_exclusive"
    assert (
        result.runtime_metadata["host_phase_spans"][0]["name"]
        == "host_worker_result_wait"
    )


def test_unsupported_capability_fails_closed_before_host() -> None:
    host = _FakeHost(_hermes_ok_result())
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    result = adapter.run(
        _invocation(capability_policy=AgentCapabilityPolicy(policy_id="terminal_v1"))
    )
    assert result.status == "error"
    assert result.error_code == UNSUPPORTED_CAPABILITY_POLICY
    assert host.calls == []
    assert result.model_calls == []


def test_adapter_preserves_model_calls_without_recompute() -> None:
    hermes_result = _hermes_ok_result()
    mapped = map_hermes_result_to_runtime_result(hermes_result, worker_pid=7)
    assert mapped.model_calls is not hermes_result.model_calls
    assert mapped.model_calls == hermes_result.model_calls
    assert mapped.model_calls[0] is hermes_result.model_calls[0]
    assert mapped.model_calls[1]["cost"]["usd"] == 0.0105
    assert mapped.telemetry_warnings == ["observer_retry"]
    assert mapped.observed_model_call_count == 2
    assert mapped.context_updates["retrieval_session_id"] == "retrieval-sess-1"
    assert mapped.tool_events[0].state == "start"
    assert mapped.tool_events[1].attributes["matched_node_ids"] == [
        "threat:tripod-null-calf"
    ]
    assert mapped.tool_events[1].attributes["source_anchor_ids"] == ["anchor:a1"]
    assert mapped.runtime_session_id == "hermes-internal-s1"
    assert "hermes_session_id" not in mapped.__dataclass_fields__


def test_map_invocation_does_not_infer_missing_scope() -> None:
    invocation = _invocation()
    request = map_invocation_to_hermes_request(invocation)
    assert request.revision_pin == invocation.context_packet.world_scope.revision_id
    assert request.world_id == invocation.context_packet.world_scope.world_id
    assert request.capability_policy is not None
    assert (
        request.capability_policy.graph_scope.revision_pin == "revision:resolved-server"
    )


def test_adapter_preserves_managed_world_scope_without_campaign() -> None:
    scope = AgentWorldScope(
        world_id="of-conks-j1-fresh-rehearsal",
        campaign_id="",
        focus={"kind": "none"},
        admissibility="gm",
        revision_id="rev:22ef509825ee1048efc73a1a1aa4a60c",
        scope_mode="world",
    )
    invocation = _invocation(
        context_packet=AgentContextPacket(world_scope=scope, retrieval_session=None)
    )
    request = map_invocation_to_hermes_request(invocation)
    assert request.world_id == scope.world_id
    assert request.campaign_id == ""
    assert request.scope_mode == "world"
    assert request.revision_pin == scope.revision_id
    assert request.capability_policy is not None
    assert request.capability_policy.graph_scope.scope_mode == "world"
    assert request.capability_policy.graph_scope.campaign_id == ""


def test_no_scope_invocation_maps_to_explicit_toolless_conversation_turn() -> None:
    invocation = _invocation(
        context_packet=AgentContextPacket(world_scope=None, retrieval_session=None),
        capability_policy=CONVERSATION_ONLY_POLICY,
        run_options=AgentRunOptions(runtime_session_id="provider-session"),
        plan_continuity_turn=True,
    )
    request = map_invocation_to_hermes_request(invocation)
    assert request.plan_continuity_turn is True
    assert request.world_id is None
    assert request.campaign_id is None
    assert request.scope_mode is None
    assert request.focus is None
    assert request.revision_pin is None
    assert request.retrieval_session is None
    assert request.retrieval_session_id is None
    assert request.session_id == "provider-session"
    assert request.capability_policy is not None
    assert request.capability_policy.mode == "conversation_only"
    assert request.capability_policy.graph_scope is None
    assert request.capability_policy.enabled_toolsets == ()
    assert request.capability_policy.enabled_tool_names == ()

    result = HermesGraphAgentTurnResult(
        status="ok",
        final_response="Hello.",
        messages=[],
        hermes_session_id="provider-session-next",
        tool_events=[],
        answer_scope=None,
    )
    host = _FakeHost(result)
    adapted = HermesAgentRuntimeAdapter(host_factory=lambda: host).run(invocation)
    assert len(host.calls) == 1
    assert adapted.status == "ok"
    assert adapted.answer_scope is None
    assert adapted.tool_events == []


def test_error_host_result_keeps_partial_telemetry() -> None:
    call = {
        "schema": "dmb_agent_model_call_v1",
        "call_id": "call-1",
        "sequence": 1,
        "status": "ok",
        "provider": "openai-api",
        "model": "gpt-5.4",
        "usage": {
            "status": "reported",
            "input_tokens": 10,
            "output_tokens": 2,
            "total_tokens": 12,
        },
        "cost": {"status": "estimated", "usd": 0.0001, "currency": "USD"},
    }
    host = _FakeHost(
        HermesGraphAgentTurnResult(
            status="error",
            final_response=None,
            messages=[],
            hermes_session_id="",
            tool_events=[],
            error_code="hermes_worker_timeout",
            error_message="timed out",
            process_isolation="process_exclusive",
            model_calls=[call],
            telemetry_warnings=["streamed_before_timeout"],
            observed_model_call_count=1,
        )
    )
    adapter = HermesAgentRuntimeAdapter(host_factory=lambda: host)
    result = adapter.run(_invocation())
    assert result.status == "error"
    assert result.error_code == "hermes_worker_timeout"
    assert result.model_calls[0] is call
    assert result.telemetry_warnings == ["streamed_before_timeout"]
    assert result.observed_model_call_count == 1
    assert result.runtime_metadata["process_isolation"] == "process_exclusive"


def test_map_invocation_carries_surface_context_block_without_mutating_question() -> (
    None
):
    from apps.live_control_server.services.agent_runtime import (
        AgentCurrentWorkContext,
        AgentSurfaceContext,
    )
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
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
    with_surface = _invocation(
        message="What does Lysandra know about the swarm?",
        context_packet=AgentContextPacket(
            world_scope=base.context_packet.world_scope,
            retrieval_session=base.context_packet.retrieval_session,
            surface_context=surface,
        ),
    )
    without = map_invocation_to_hermes_request(
        _invocation(message="What does Lysandra know about the swarm?")
    )
    request = map_invocation_to_hermes_request(with_surface)
    expected = render_agent_surface_context(surface)
    assert request.surface_context_block == expected
    assert without.surface_context_block is None
    assert (
        request.question
        == without.question
        == "What does Lysandra know about the swarm?"
    )
    assert request.conversation_history == without.conversation_history
    assert "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" not in (
        request.surface_context_block or ""
    )
    assert "revision" not in (request.surface_context_block or "").lower()


def test_map_invocation_carries_play_surface_context_block_without_mutating_question() -> (
    None
):
    from apps.live_control_server.services.agent_runtime import (
        AgentPlayCurrentElementContext,
        AgentPlayCurrentMomentContext,
        AgentSurfaceContext,
    )
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
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
            current_scene=AgentPlayCurrentElementContext(
                kind="scene",
                element_id="scene:gate-line",
                title="The gate line",
                body_text="Guards waver while Lysandro works the crowd.",
            ),
        ),
    )
    base = _invocation()
    with_surface = _invocation(
        message="What happens if they collapse the tunnel?",
        context_packet=AgentContextPacket(
            world_scope=base.context_packet.world_scope,
            retrieval_session=base.context_packet.retrieval_session,
            surface_context=surface,
        ),
    )
    without = map_invocation_to_hermes_request(
        _invocation(message="What happens if they collapse the tunnel?")
    )
    request = map_invocation_to_hermes_request(with_surface)
    expected = render_agent_surface_context(surface)
    assert request.surface_context_block == expected
    assert without.surface_context_block is None
    assert (
        request.question
        == without.question
        == "What happens if they collapse the tunnel?"
    )
    assert "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" not in (
        request.surface_context_block or ""
    )
    assert "beat:hold-the-gate" not in (request.surface_context_block or "")
