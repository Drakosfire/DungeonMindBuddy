"""PR354: Hermes live-query cutover through the PR353 host."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.services.hermes_graph_agent_contract import (
    HermesGraphAgentTurnRequest,
    HermesGraphAgentTurnResult,
    HermesGraphToolEvent,
)
from apps.live_control_server.services.hermes_graph_query import (
    ABSTENTION_ANSWER,
    build_hermes_graph_turn_request,
    classify_hermes_graph_result,
    run_hermes_graph_query,
    validate_hermes_query_inputs,
)
from apps.live_control_server.services import hermes_graph_query as hermes_graph_query_mod
from apps.live_control_server.services import live_agent_loop
from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

GRAPH_NESTED = {
    "schema": "dmb_agent_world_graph_query_context_request_v1",
    "world_id": "eldyrwild",
    "campaign_id": "longmont-c2",
    "focus": {"kind": "session", "session_id": "session-21"},
    "admissibility": "gm",
    "revision_pin": "rev:client-repeated",
}

READY_ENVELOPE = {
    "schema": "dmb_agent_world_graph_query_context_v1",
    "status": "ready",
    "world_id": "world:eldyrwild",
    "campaign_id": "campaign:c1",
    "revision_id": "revision:resolved-server",
    "head_revision_id": "revision:resolved-server",
    "is_head": True,
    "focus": {"kind": "session", "session_id": "session-21"},
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

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import shutil

    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def _tool_event(
    *,
    outcome: str = "enough",
    source_anchor_ids: list[str] | None = None,
    revision_pin: str = "revision:resolved-server",
    world_id: str = "world:eldyrwild",
    campaign_id: str = "campaign:c1",
    state: str = "completion",
) -> HermesGraphToolEvent:
    return HermesGraphToolEvent(
        tool_name="search_campaign_graph",
        state=state,  # type: ignore[arg-type]
        duration_ms=12.0,
        world_id=world_id,
        campaign_id=campaign_id,
        focus={"kind": "session", "sessionId": "session-21"},
        admissibility="gm",
        revision_pin=revision_pin,
        bounded_ids={},
        retrieval_schema="dmb_world_graph_retrieval_result_v1",
        outcome=outcome,
        matched_node_ids=["threat:tripod-null-calf"],
        relationship_ids=[],
        source_anchor_ids=list(source_anchor_ids or []),
        diagnostic_codes=[],
    )


def _ok_result(
    *,
    final_response: str = "Tripod stands at the North Gate.",
    events: list[HermesGraphToolEvent] | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> HermesGraphAgentTurnResult:
    tool_events = (
        [_tool_event(source_anchor_ids=["anchor:a1"])]
        if events is None
        else list(events)
    )
    return HermesGraphAgentTurnResult(
        status="ok",
        final_response=final_response,
        messages=list(messages or []),
        hermes_session_id="hermes-sess-obs-only",
        tool_events=tool_events,
        error_code=None,
        error_message=None,
        process_isolation="process_exclusive",
    )


def _error_result(error_code: str) -> HermesGraphAgentTurnResult:
    return HermesGraphAgentTurnResult(
        status="error",
        final_response=None,
        messages=[],
        hermes_session_id="",
        tool_events=[],
        error_code=error_code,
        error_message="safe host error",
        process_isolation="process_exclusive",
    )


class _FakeHost:
    def __init__(self, result: HermesGraphAgentTurnResult) -> None:
        self.result = result
        self.calls: list[HermesGraphAgentTurnRequest] = []

    def execute(
        self,
        request: HermesGraphAgentTurnRequest,
        *,
        timeout_s: float | None = None,
    ) -> HermesGraphAgentTurnResult:
        self.calls.append(request)
        return self.result


def _raise_if_called(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("forbidden legacy path invoked")


@pytest.fixture
def no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live_agent_loop, "run_hermes_conversation", _raise_if_called)
    monkeypatch.setattr(live_agent_loop, "_process_hermes_context_query", _raise_if_called)
    monkeypatch.setattr(live_agent_loop, "_process_hermes_cli_query", _raise_if_called)
    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", _raise_if_called)
    monkeypatch.setattr(live_agent_loop, "handle_live_turn", _raise_if_called)
    monkeypatch.setattr(live_agent_loop.subprocess, "run", _raise_if_called)


def test_validate_rejects_missing_context_and_legacy_fields() -> None:
    with pytest.raises(Exception) as missing:
        validate_hermes_query_inputs(
            world_graph_context=None,
            request_manifest_path=None,
            hermes_session_id=None,
            outer_campaign_id="campaign:c1",
        )
    assert missing.value.code == "world_graph_context_required"  # type: ignore[attr-defined]

    with pytest.raises(Exception) as mismatch:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(campaign_id="other"),
            request_manifest_path=None,
            hermes_session_id=None,
            outer_campaign_id="campaign:c1",
        )
    assert mismatch.value.code == "campaign_scope_mismatch"  # type: ignore[attr-defined]

    with pytest.raises(Exception) as manifest:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(campaign_id="campaign:c1"),
            request_manifest_path="/tmp/manifest.json",
            hermes_session_id=None,
            outer_campaign_id="campaign:c1",
        )
    assert manifest.value.code == "legacy_manifest_not_supported"  # type: ignore[attr-defined]

    with pytest.raises(Exception) as continuity:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(campaign_id="campaign:c1"),
            request_manifest_path=None,
            hermes_session_id="sess-1",
            outer_campaign_id="campaign:c1",
        )
    assert continuity.value.code == "hermes_continuity_not_supported"  # type: ignore[attr-defined]


def test_turn_request_uses_resolved_revision_server_root_and_no_continuity(
    tmp_path: Path,
) -> None:
    request, scope = build_hermes_graph_turn_request(
        question="Where is Tripod?",
        graph_envelope=READY_ENVELOPE,
        root=tmp_path,
    )
    assert request.revision_pin == "revision:resolved-server"
    assert request.revision_pin != "rev:client-repeated"
    assert request.root == tmp_path.resolve()
    assert request.conversation_history is None
    assert request.session_id is None
    assert request.capability_policy is None
    assert request.focus == {"kind": "session", "sessionId": "session-21"}
    assert scope.revision_id == "revision:resolved-server"


def test_grounded_partial_abstention_and_error_classification() -> None:
    request, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    _ = request

    grounded_state, grounded_answer, *_ = classify_hermes_graph_result(
        _ok_result(),
        scope=scope,
    )
    assert grounded_state == "grounded"
    assert grounded_answer.startswith("Tripod")

    partial_state, _, warnings, _, _ = classify_hermes_graph_result(
        _ok_result(
            events=[
                _tool_event(outcome="partial", source_anchor_ids=["anchor:p1"]),
            ]
        ),
        scope=scope,
    )
    assert partial_state == "partial"
    assert warnings

    empty_state, empty_answer, *_ = classify_hermes_graph_result(
        _ok_result(
            final_response="model prose should be discarded",
            events=[_tool_event(outcome="empty", source_anchor_ids=[])],
        ),
        scope=scope,
    )
    assert empty_state == "abstained"
    assert empty_answer == ABSTENTION_ANSWER

    denied_state, denied_answer, *_ = classify_hermes_graph_result(
        _ok_result(
            final_response="denied prose",
            events=[_tool_event(outcome="denied", source_anchor_ids=[])],
        ),
        scope=scope,
    )
    assert denied_state == "abstained"
    assert denied_answer == ABSTENTION_ANSWER

    no_anchor_state, *_ = classify_hermes_graph_result(
        _ok_result(
            events=[_tool_event(outcome="enough", source_anchor_ids=[])],
        ),
        scope=scope,
    )
    assert no_anchor_state == "abstained"

    prose_only_state, *_ = classify_hermes_graph_result(
        _ok_result(events=[]),
        scope=scope,
    )
    assert prose_only_state == "abstained"

    mismatch_state, _, _, codes, error_code = classify_hermes_graph_result(
        _ok_result(
            events=[
                _tool_event(
                    outcome="enough",
                    source_anchor_ids=["anchor:x"],
                    revision_pin="revision:other",
                )
            ]
        ),
        scope=scope,
    )
    assert mismatch_state == "error"
    assert error_code == "hermes_grounding_contract_error"
    assert "hermes_tool_event_scope_mismatch" in codes

    for code in (
        "hermes_worker_lost",
        "hermes_worker_timeout",
        "hermes_worker_start_failed",
        "hermes_worker_protocol_error",
        "hermes_turn_error",
    ):
        state, _, _, _, mapped = classify_hermes_graph_result(
            _error_result(code),
            scope=scope,
        )
        assert state == "error"
        assert mapped == code


def test_messages_ignored_even_when_present() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    state, answer, *_ = classify_hermes_graph_result(
        _ok_result(
            messages=[
                {"role": "assistant", "content": "do not trust transcript"},
                {"role": "tool", "content": "tool body"},
            ]
        ),
        scope=scope,
    )
    assert state == "grounded"
    assert answer == "Tripod stands at the North Gate."


def test_run_hermes_graph_query_preserves_tool_events_and_uses_fake_host(
    tmp_path: Path,
    no_fallback: None,
) -> None:
    host = _FakeHost(
        _ok_result(
            events=[
                _tool_event(state="start", source_anchor_ids=[]),
                _tool_event(source_anchor_ids=["anchor:a1", "anchor:a2"]),
            ],
            messages=[{"role": "assistant", "content": "ignored"}],
        )
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-abc",
        turn_id="agent-turn-1",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert len(host.calls) == 1
    assert host.calls[0].revision_pin == "revision:resolved-server"
    assert host.calls[0].conversation_history is None
    assert host.calls[0].session_id is None
    assert host.calls[0].capability_policy is None
    assert response["mode"] == "hermes_graph_agent"
    assert response["status"] == "ok"
    assert response["grounding"]["state"] == "grounded"
    assert response["grounding"]["source_anchor_count"] == 2
    assert response["citations"] == []
    assert response["hermes_session"] is None
    assert response["agent_thread_id"] == "agent-thread-abc"
    assert response["agent_trace"]["hermes_session_id"] == "hermes-sess-obs-only"
    events = response["agent_trace"]["tool_events"]
    assert len(events) == 2
    assert events[1]["source_anchor_ids"] == ["anchor:a1", "anchor:a2"]
    assert events[1]["outcome"] == "enough"
    blob = json.dumps(response)
    assert "ignored" not in blob
    assert "/tmp" not in blob or str(tmp_path) not in blob
    assert "OPENAI" not in blob
    assert "prompt" not in response["agent_trace"]


def test_production_adapter_resolves_global_host_accessor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    host = _FakeHost(_ok_result())
    called = {"n": 0}

    def fake_get() -> _FakeHost:
        called["n"] += 1
        return host

    monkeypatch.setattr(hermes_graph_query_mod, "get_hermes_graph_agent_host", fake_get)
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id=None,
        turn_id=None,
        root=tmp_path,
    )
    assert called["n"] == 1
    assert response["grounding"]["state"] == "grounded"


def test_second_request_same_thread_is_independent(tmp_path: Path) -> None:
    host = _FakeHost(_ok_result())
    first = run_hermes_graph_query(
        text="first",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-same",
        turn_id="turn-1",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    second = run_hermes_graph_query(
        text="second",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-same",
        turn_id="turn-2",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert len(host.calls) == 2
    assert host.calls[0].conversation_history is None
    assert host.calls[1].conversation_history is None
    assert host.calls[0].session_id is None
    assert host.calls[1].session_id is None
    assert first["agent_thread_id"] == second["agent_thread_id"]
    assert first["turn_id"] != second["turn_id"]


def test_http_hermes_grounded_and_validation(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_fallback: None,
) -> None:
    host = _FakeHost(
        _ok_result(
            events=[
                _tool_event(
                    world_id="eldyrwild",
                    campaign_id="longmont-c2",
                    revision_pin="revision:http",
                    source_anchor_ids=["anchor:a1"],
                )
            ]
        )
    )

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            **READY_ENVELOPE,
            "campaign_id": "longmont-c2",
            "world_id": "eldyrwild",
            "revision_id": "revision:http",
            "focus": {"kind": "session", "session_id": "session-21"},
        },
    )
    monkeypatch.setattr(
        hermes_graph_query_mod,
        "get_hermes_graph_agent_host",
        lambda: host,
    )
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)

    missing = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
        },
    )
    assert missing.status_code == 422
    assert missing.json()["code"] == "world_graph_context_required"

    manifest = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "manifest_path": "some/manifest.json",
            "world_graph_context": GRAPH_NESTED,
        },
    )
    assert manifest.status_code == 422
    assert manifest.json()["code"] == "legacy_manifest_not_supported"

    continuity = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "hermes_session_id": "sess-x",
            "world_graph_context": GRAPH_NESTED,
        },
    )
    assert continuity.status_code == 422
    assert continuity.json()["code"] == "hermes_continuity_not_supported"

    mismatch = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "world_graph_context": {**GRAPH_NESTED, "campaign_id": "other-campaign"},
        },
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["code"] == "campaign_scope_mismatch"

    ok = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "agent_thread_id": "agent-thread-ui",
            "world_graph_context": GRAPH_NESTED,
        },
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["mode"] == "hermes_graph_agent"
    assert body["status"] == "ok"
    assert body["grounding"]["state"] == "grounded"
    assert body["grounding"]["revision_id"] == "revision:http"
    assert body["agent_thread_id"] == "agent-thread-ui"
    assert body["hermes_session"] is None
    assert body["citations"] == []
    assert host.calls[0].revision_pin == "revision:http"
    assert host.calls[0].root == tmp_path.resolve()
    assert len(host.calls) == 1


def test_live_sibling_never_invokes_host(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host_calls: list[str] = []

    def boom() -> Any:
        host_calls.append("called")
        raise AssertionError("host must not be called for live backend")

    monkeypatch.setattr(hermes_graph_query_mod, "get_hermes_graph_agent_host", boom)

    def fake_context_lookup_turn(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            response={
                "schema": "dmb_live_query_response_v1",
                "query_id": "live-sibling",
                "session": 22,
                "mode": "context_lookup",
                "status": "ok",
                "answer": "live answer",
                "classification": {
                    "latency_mode": "context_lookup",
                    "event_type": "context_question",
                },
                "events_written": [],
                "jobs_queued": [],
                "next_suggestions": [],
                "diagnostics": [],
                "provenance": {},
                "citations": [],
                "context_packet": {"admitted_evidence": [], "rejected_evidence": []},
                "warnings": [],
                "mutations": [],
            },
            events_to_write=[],
            jobs_to_queue=[],
        )

    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", fake_context_lookup_turn)
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "live",
            "text": "What happened at the end of session 22?",
            "manifest_path": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "context_lookup"
    assert host_calls == []


def test_http_host_error_no_fallback(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_fallback: None,
) -> None:
    host = _FakeHost(_error_result("hermes_worker_timeout"))
    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            **READY_ENVELOPE,
            "campaign_id": "longmont-c2",
            "world_id": "eldyrwild",
            "revision_id": "revision:http",
        },
    )
    monkeypatch.setattr(hermes_graph_query_mod, "get_hermes_graph_agent_host", lambda: host)
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "world_graph_context": GRAPH_NESTED,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["grounding"]["state"] == "error"
    assert body["diagnostics"]["error_code"] == "hermes_worker_timeout"
    assert body["mode"] == "hermes_graph_agent"
