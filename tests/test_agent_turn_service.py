from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from apps.live_control_server.models.agent_turn import (
    AgentTurnContentBasis,
    AgentTurnRequest,
)
from apps.live_control_server.services.agent_runtime import (
    CONVERSATION_ONLY_POLICY_ID,
    AgentRuntimeDescriptor,
    AgentRuntimeResult,
)
from apps.live_control_server.services.agent_turn_service import (
    AgentTurnResolvedWork,
    AgentTurnServiceError,
    execute_agent_turn,
)
from apps.live_control_server.services.hermes_session_store import (
    HermesSessionPointerStore,
)


def _request(**updates: Any) -> AgentTurnRequest:
    payload: dict[str, Any] = {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "thread-1",
        "turn_id": "turn-1",
        "surface": {"surface_id": "index", "instance_id": "index-main"},
        "owner_scope": None,
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "message": "Hello there",
    }
    payload.update(updates)
    return AgentTurnRequest.model_validate(payload)


class FakeRuntime:
    descriptor = AgentRuntimeDescriptor(
        runtime_id="fake",
        trace_backend="fake",
        trace_runtime="test",
        trace_mode="conversation",
    )

    def __init__(self) -> None:
        self.invocations = []
        self.result: AgentRuntimeResult | None = None

    def run(self, invocation: Any) -> AgentRuntimeResult:
        self.invocations.append(invocation)
        if self.result is not None:
            return self.result
        return AgentRuntimeResult(
            status="ok",
            final_text="Hello.",
            runtime_session_id="runtime-session-1",
        )


def _plan_work(_request: Any, _owner: Any) -> AgentTurnResolvedWork:
    return AgentTurnResolvedWork(
        kind="plan",
        object_id="plan:one",
        revision=3,
        changed_since_expected=False,
        owner_kind=None,
        owner_id=None,
    )


def _plan_request() -> AgentTurnRequest:
    return _request(surface={"surface_id": "plan", "instance_id": "plan-main"})


def _pinned_plan_request() -> AgentTurnRequest:
    return _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        primary_work={
            "kind": "plan",
            "object_id": "plan:one",
            "expected_revision": 7,
            "expected_revision_n": 4,
            "expected_content_sha256": "b" * 64,
        },
        client_work_state="saved_dirty",
        message="What is beneath the black arch?",
    )


def _pinned_plan_work(markdown: str) -> AgentTurnResolvedWork:
    return AgentTurnResolvedWork(
        kind="plan",
        object_id="plan:one",
        revision=7,
        changed_since_expected=False,
        owner_kind="world",
        owner_id="world:one",
        world_id="world:one",
        content_basis=AgentTurnContentBasis(
            world_id="world:one",
            document_id="plan:one",
            object_revision=7,
            work_revision_id="work-revision-4",
            revision_n=4,
            content_sha256="b" * 64,
            committed_status="committed",
            has_divergent_working_copy=True,
        ),
        plan_markdown=markdown,
    )


def test_plan_turn_sends_exact_committed_markdown_and_returns_source_free_basis(
    tmp_path: Path,
) -> None:
    markdown = "# Saved Plan\n\nThe keeper waits below the black arch.\n"
    runtime = FakeRuntime()
    response = execute_agent_turn(
        _pinned_plan_request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: _pinned_plan_work(markdown),
        graph_resolver=lambda *_args: pytest.fail(
            "Plan content turn must not resolve graph"
        ),
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    prefix, payload = runtime.invocations[0].message.split("\n", maxsplit=1)
    assert prefix.startswith("Answer the user's question using the committed Plan")
    assert json.loads(payload) == {
        "committed_plan_markdown": markdown,
        "user_question": "What is beneath the black arch?",
    }
    assert response.graph.status == "not_requested"
    assert (
        response.primary_work.content_basis == _pinned_plan_work(markdown).content_basis
    )
    assert markdown not in response.model_dump_json(by_alias=True)
    assert response.answer.trace.get("context_summary", {}).get("content_basis") is None


def test_over_budget_committed_plan_stops_before_pointer_or_runtime_dispatch(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()
    pointer_dir = tmp_path / "pointers"

    with pytest.raises(AgentTurnServiceError) as exc_info:
        execute_agent_turn(
            _pinned_plan_request(),
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(pointer_dir),
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": "world:one",
                "name": "The Glass Orchard",
            },
            work_resolver=lambda _request, _owner: _pinned_plan_work("x" * 8_000),
            graph_resolver=lambda *_args: pytest.fail(
                "Plan content turn must not resolve graph"
            ),
            runtime=runtime,
        )

    assert exc_info.value.code == "plan_content_over_budget"
    assert exc_info.value.status_code == 413
    assert runtime.invocations == []
    assert not (pointer_dir / "hermes_thread_pointers.json").exists()


def test_no_graph_turn_uses_no_scope_runtime_and_only_structured_pointer_store(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()

    def unexpected_graph(*_args: Any) -> Any:
        raise AssertionError("no-graph turn must not resolve graph authority")

    response = execute_agent_turn(
        _request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointer-only"),
        owner_resolver=lambda _request: None,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=unexpected_graph,
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    invocation = runtime.invocations[0]
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    assert invocation.capability_policy.policy_id == CONVERSATION_ONLY_POLICY_ID
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_id
    pointer_path = tmp_path / "pointer-only" / "hermes_thread_pointers.json"
    assert pointer_path.is_file()


@pytest.mark.parametrize(
    ("surface_id", "label"),
    [
        ("index", "Index"),
        ("plan", "Plan"),
        ("play", "Play"),
        ("build", "Build"),
        ("ingest", "Ingest"),
        ("combat", "Combat Tracker"),
    ],
)
def test_no_work_turn_carries_surface_and_verified_world_through_real_adapters(
    tmp_path: Path, surface_id: str, label: str
) -> None:
    from apps.live_control_server.services.agent_surface_context import (
        render_agent_surface_context,
    )
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )
    from apps.live_control_server.services.pydantic_ai_agent_runtime import (
        pydantic_ai_agent_instructions,
    )

    runtime = FakeRuntime()
    request = _request(
        surface={"surface_id": surface_id, "instance_id": f"{surface_id}-pane-1"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        },
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail(
            "no-graph turn resolved graph authority"
        ),
        runtime=runtime,
    )

    invocation = runtime.invocations[0]
    assert invocation.plan_continuity_turn is False
    context = invocation.context_packet.surface_context
    assert context is not None
    assert context.surface_id == surface_id
    assert context.surface_instance_id == f"{surface_id}-pane-1"
    assert context.current_owner is not None
    assert context.current_owner.owner_id == "world:one"
    assert invocation.context_packet.world_scope is None
    assert invocation.context_packet.retrieval_session is None
    rendered = render_agent_surface_context(context)
    assert rendered is not None
    assert label in rendered
    assert 'Current World: "The Glass Orchard"' in rendered
    assert "world:one" not in rendered

    hermes_request = map_invocation_to_hermes_request(invocation)
    assert hermes_request.world_id is None
    assert hermes_request.campaign_id is None
    assert hermes_request.retrieval_session is None
    assert hermes_request.capability_policy.mode == "conversation_only"
    assert hermes_request.capability_policy.graph_scope is None
    assert hermes_request.capability_policy.enabled_toolsets == ()
    assert hermes_request.plan_continuity_turn is False
    hermes_prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert label in hermes_prompt
    assert 'Current World: "The Glass Orchard"' in hermes_prompt
    pydantic_prompt = pydantic_ai_agent_instructions(invocation)
    assert label in pydantic_prompt
    assert 'Current World: "The Glass Orchard"' in pydantic_prompt
    assert "No graph retrieval is performed on this turn" in pydantic_prompt


def test_server_resolves_saved_plan_continuity_flag_before_runtime_dispatch(
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime()
    execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert len(runtime.invocations) == 1
    assert runtime.invocations[0].plan_continuity_turn is True


def test_graphless_followup_reuses_same_binding_without_current_graph_authority(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.agent_runtime import AgentWorldScope
    from apps.live_control_server.services.hermes_agent_runtime import (
        map_invocation_to_hermes_request,
    )
    from apps.live_control_server.services.hermes_graph_agent import (
        _build_ephemeral_system_prompt,
    )

    runtime = FakeRuntime()
    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")

    def owner(_request):
        return {
            "kind": "world",
            "id": "world:one",
            "name": "The Glass Orchard",
        }

    def graph(_request, _owner, _work):
        return (
            {
                "status": "ready",
                "world_id": "world:one",
                "campaign_id": "",
                "scope_mode": "world",
                "revision_id": "revision-one",
                "head_revision_id": "revision-one",
                "is_head": True,
                "focus": {"kind": "none"},
                "matched_node_ids": ["node:one"],
                "nodes": [{"node_id": "node:one", "label": "The Glass Orchard"}],
            },
            AgentWorldScope(
                world_id="world:one",
                campaign_id="",
                focus={"kind": "none"},
                admissibility="gm",
                revision_id="revision-one",
                scope_mode="world",
            ),
        )

    first = _request(
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
        graph_request={
            "mode": "world",
            "world_id": "world:one",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        },
    )
    execute_agent_turn(
        first,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=graph,
        runtime=runtime,
    )
    second = _request(
        turn_id="turn-2",
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:one"},
    )
    response = execute_agent_turn(
        second,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=owner,
        work_resolver=lambda _request, _owner: None,
        graph_resolver=lambda *_args: pytest.fail(
            "graphless follow-up must not retrieve"
        ),
        runtime=runtime,
    )

    assert runtime.invocations[1].run_options.runtime_session_id == "runtime-session-1"
    assert runtime.invocations[1].context_packet.world_scope is None
    assert runtime.invocations[1].context_packet.retrieval_session is None
    assert response.graph.status == "not_requested"
    assert response.answer.graph_grounded is False
    assert response.conversation.pointer_status == "reused"
    hermes_request = map_invocation_to_hermes_request(runtime.invocations[1])
    prompt = _build_ephemeral_system_prompt(
        hermes_request.capability_policy,
        hermes_request,
        retrieval_session_packet=None,
    )
    assert "No graph retrieval is performed on this turn" in prompt
    assert "historical graph-derived statements" in prompt
    assert "not revalidated as current graph evidence" in prompt
    assert "request an explicit graph-retrieval turn" in prompt


def test_expired_structured_binding_stops_before_runtime_and_removes_profile(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="expired-session",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.status_code == 409
    assert error.value.code == "hermes_continuity_unavailable"
    assert not runtime.invocations
    assert not profile.exists()
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["structured_bindings"][key]["status"] == "expired"


def test_rejected_plan_pointer_does_not_change_other_agent_surface_behavior(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="expired-session",
    )
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=8)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()
    request = _request(surface={"surface_id": "build", "instance_id": "plan-main"})

    response = execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "ok"
    assert len(runtime.invocations) == 1
    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["structured_bindings"][key]["status"] == "expired"


def test_native_continuity_failure_revokes_binding_without_returning_answer(
    tmp_path: Path,
) -> None:
    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="session-original",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="error",
        runtime_session_id="session-original",
        error_code="hermes_continuity_unavailable",
        error_message="missing native history",
    )

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.status_code == 409
    assert error.value.code == "hermes_continuity_unavailable"
    assert len(runtime.invocations) == 1
    assert not profile.exists()
    payload = json.loads((pointer_base / "hermes_thread_pointers.json").read_text())
    stored = next(iter(payload["structured_bindings"].values()))
    assert stored["status"] == "invalid"


def test_changed_hermes_session_identity_revokes_saved_plan_binding(
    tmp_path: Path,
) -> None:
    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    binding = pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="session-original",
    )
    profile = pointer_store.structured_profile_home(binding.hermes_session_id)
    profile.mkdir(parents=True)
    (profile / "state.db").write_text("native state", encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="This answer must not be shown.",
        runtime_session_id="session-different",
    )

    with pytest.raises(AgentTurnServiceError) as error:
        execute_agent_turn(
            _plan_request(),
            root=tmp_path,
            pointer_store=pointer_store,
            owner_resolver=lambda _request: None,
            work_resolver=_plan_work,
            graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
            runtime=runtime,
        )

    assert error.value.code == "hermes_continuity_unavailable"
    assert "This answer must not be shown." not in str(error.value)
    assert not profile.exists()
    payload = json.loads((pointer_base / "hermes_thread_pointers.json").read_text())
    stored = next(iter(payload["structured_bindings"].values()))
    assert stored["status"] == "invalid"


def test_runtime_error_does_not_create_or_renew_structured_pointer(
    tmp_path: Path,
) -> None:
    pointer_store = HermesSessionPointerStore(tmp_path / "pointers")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="error",
        runtime_session_id="unpersisted-session",
        error_code="provider_unavailable",
        error_message="provider failed",
    )

    response = execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "error"
    assert not (tmp_path / "pointers" / "hermes_thread_pointers.json").exists()


def test_successful_persisted_plan_turn_refreshes_sliding_idle_ttl(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    pointer_base = tmp_path / "pointers"
    pointer_store = HermesSessionPointerStore(pointer_base)
    pointer_store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="plan-session",
    )
    store_path = pointer_base / "hermes_thread_pointers.json"
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(days=6)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="Plan reply.",
        runtime_session_id="plan-session",
    )

    response = execute_agent_turn(
        _plan_request(),
        root=tmp_path,
        pointer_store=pointer_store,
        owner_resolver=lambda _request: None,
        work_resolver=_plan_work,
        graph_resolver=lambda *_args: pytest.fail("no graph turn expected"),
        runtime=runtime,
    )

    assert response.answer.status == "ok"
    refreshed = json.loads(store_path.read_text(encoding="utf-8"))
    binding = refreshed["structured_bindings"][key]
    updated_at = datetime.fromisoformat(binding["updated_at"].replace("Z", "+00:00"))
    assert updated_at > datetime.now(timezone.utc) - timedelta(minutes=1)
    assert binding["hermes_session_id"] == "plan-session"


def test_unresolvable_requested_graph_fails_before_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    request = _request(
        graph_request={
            "mode": "world",
            "world_id": "world-1",
            "campaign_id": None,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        }
    )

    def reject_graph(*_args: Any) -> Any:
        raise AgentTurnServiceError(
            "foreign graph", code="graph_scope_rejected", status_code=403
        )

    with pytest.raises(AgentTurnServiceError, match="foreign graph"):
        execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: None,
            work_resolver=lambda _request, _owner: None,
            graph_resolver=reject_graph,
            runtime=runtime,
        )
    assert runtime.invocations == []


def test_successful_plan_turn_returns_one_sanitized_trace_event(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    prompt_secret = "plan-prompt-secret-6d3b"
    runtime = FakeRuntime()
    runtime.result = AgentRuntimeResult(
        status="ok",
        final_text="ANSWER_SENTINEL synthetic answer",
        runtime_metadata={
            "host_phase_spans": [
                {
                    "span_id": "0123456789abcdef0123456789abcdef:1",
                    "parent_span_id": None,
                    "kind": "phase",
                    "name": "host_worker_result_wait",
                    "status": "ok",
                    "started_at": "2026-10-01T23:59:59.991Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {
                        "host_phase_group_id": "0123456789abcdef0123456789abcdef",
                        "request_summary": "TRACE_LEAK_SENTINEL from innocuous field",
                    },
                    "extra_context": "TRACE_LEAK_SENTINEL from arbitrary field",
                },
                {
                    "span_id": "0123456789abcdef0123456789abcdef:2",
                    "name": "host_worker_result_wait",
                    "status": "ok",
                    "started_at": "2026-10-02T00:00:00Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": -1,
                    "attributes": {
                        "host_phase_group_id": "0123456789abcdef0123456789abcdef"
                    },
                },
                {
                    "span_id": "abcdef0123456789abcdef0123456789:1",
                    "name": "rung3_bootstrap_logger_home_setup",
                    "status": "ok",
                    "started_at": "2026-10-01T23:59:59.991Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {
                        "host_phase_group_id": "abcdef0123456789abcdef0123456789"
                    },
                },
                {
                    "span_id": "TRACE_LEAK_SENTINEL",
                    "name": "unapproved_phase_name",
                    "status": "ok",
                    "started_at": "2026-10-02T00:00:00Z",
                    "completed_at": "2026-10-02T00:00:00Z",
                    "duration_ms": 9,
                    "attributes": {},
                },
            ]
        },
    )
    request = _request(
        message=prompt_secret,
        surface={"surface_id": "plan", "instance_id": "plan-main"},
        owner_scope={"kind": "world", "world_id": "world:plan"},
    )

    with caplog.at_level(logging.INFO, logger="dmb.agent.turn_trace"):
        response = execute_agent_turn(
            request,
            root=tmp_path,
            pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
            owner_resolver=lambda _request: {
                "kind": "world",
                "id": "world:plan",
                "name": "Trace Test World",
            },
            work_resolver=lambda _request, _owner: None,
            graph_resolver=lambda *_args: pytest.fail(
                "graphless Plan turn must not resolve graph authority"
            ),
            runtime=runtime,
        )

    trace = response.answer.trace
    trace_events = [
        record.getMessage()
        for record in caplog.records
        if record.name == "dmb.agent.turn_trace"
        and record.getMessage().startswith("dmb_agent_turn_trace ")
    ]

    assert response.answer.status == "ok"
    assert trace["status"] == "ok"
    assert len(trace_events) == 1
    logged_trace = json.loads(trace_events[0].removeprefix("dmb_agent_turn_trace "))
    assert logged_trace["trace_id"] == trace["trace_id"]
    runtime_span = next(
        span for span in trace["spans"] if span["name"] == "runtime_dispatch"
    )
    host_span = next(
        span for span in trace["spans"] if span["name"] == "host_worker_result_wait"
    )
    worker_span = next(
        span
        for span in trace["spans"]
        if span["name"] == "rung3_bootstrap_logger_home_setup"
    )
    assert sum(span.get("name", "").startswith("host_") for span in trace["spans"]) == 1
    assert sum(span.get("name", "").startswith("rung3_") for span in trace["spans"]) == 1
    assert host_span["parent_span_id"] == runtime_span["span_id"]
    assert worker_span["parent_span_id"] == runtime_span["span_id"]
    assert prompt_secret not in json.dumps(trace["spans"])
    assert "ANSWER_SENTINEL" not in json.dumps(trace)
    assert "TRACE_LEAK_SENTINEL" not in json.dumps(trace)
    assert prompt_secret not in trace_events[0]
    assert "ANSWER_SENTINEL" not in trace_events[0]
    assert "TRACE_LEAK_SENTINEL" not in trace_events[0]
