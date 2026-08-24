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
    EXECUTION_ERROR_ANSWER,
    HermesGraphQueryRequestError,
    UNAVAILABLE_ANSWER,
    build_hermes_graph_product_response,
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
    "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
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


_MISSING = object()


def _tool_event(
    *,
    outcome: str | None = "enough",
    source_anchor_ids: list[str] | None = None,
    revision_pin: Any = _MISSING,
    world_id: Any = _MISSING,
    campaign_id: Any = _MISSING,
    focus: Any = _MISSING,
    admissibility: Any = _MISSING,
    state: str = "completion",
    matched_node_ids: list[str] | None = None,
    relationship_ids: list[str] | None = None,
    diagnostic_codes: list[str] | None = None,
    retrieval_schema: str | None = "dmb_world_graph_retrieval_result_v1",
    tool_name: str = "expand_graph_retrieval",
) -> HermesGraphToolEvent:
    return HermesGraphToolEvent(
        tool_name=tool_name,
        state=state,  # type: ignore[arg-type]
        duration_ms=12.0,
        world_id="world:eldyrwild" if world_id is _MISSING else world_id,
        campaign_id="campaign:c1" if campaign_id is _MISSING else campaign_id,
        focus=(
            {"kind": "session", "sessionId": "session-21"}
            if focus is _MISSING
            else focus
        ),
        admissibility="gm" if admissibility is _MISSING else admissibility,
        revision_pin=(
            "revision:resolved-server" if revision_pin is _MISSING else revision_pin
        ),
        bounded_ids={},
        retrieval_schema=retrieval_schema,
        outcome=outcome,
        matched_node_ids=list(
            matched_node_ids
            if matched_node_ids is not None
            else ["threat:tripod-null-calf"]
        ),
        relationship_ids=list(relationship_ids or []),
        source_anchor_ids=list(source_anchor_ids or []),
        diagnostic_codes=list(diagnostic_codes or []),
    )


def _ok_result(
    *,
    final_response: str = "Tripod stands at the North Gate.",
    events: list[HermesGraphToolEvent] | None = None,
    messages: list[dict[str, Any]] | None = None,
    answer_scope: str | None = None,
    hermes_session_id: str = "hermes-sess-obs-only",
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
        hermes_session_id=hermes_session_id,
        tool_events=tool_events,
        error_code=None,
        error_message=None,
        process_isolation="process_exclusive",
        answer_scope=answer_scope,  # type: ignore[arg-type]
    )


def _declare_tool_event(*, state: str = "completion") -> HermesGraphToolEvent:
    return HermesGraphToolEvent(
        tool_name="declare_conversation_context",
        state=state,  # type: ignore[arg-type]
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
    monkeypatch.setattr(live_agent_loop, "run_context_lookup_turn", _raise_if_called)
    monkeypatch.setattr(live_agent_loop, "handle_live_turn", _raise_if_called)


def test_validate_rejects_missing_context_and_legacy_fields() -> None:
    with pytest.raises(Exception) as missing:
        validate_hermes_query_inputs(
            world_graph_context=None,
            request_manifest_path=None,
            hermes_session_id=None,
            outer_campaign_id="campaign:c1",
        )
    assert missing.value.code == "world_graph_context_required"  # type: ignore[attr-defined]

    # Campaign lens may differ from the outer live-packet campaign (C1-only on C2 Plan).
    validate_hermes_query_inputs(
        world_graph_context=SimpleNamespace(
            campaign_id="longmont-c1",
            scope_mode="campaign",
        ),
        request_manifest_path=None,
        hermes_session_id=None,
        outer_campaign_id="longmont-c2",
    )

    # World scope allows a same-world narrative anchor that differs from outer.
    validate_hermes_query_inputs(
        world_graph_context=SimpleNamespace(
            campaign_id="longmont-c1",
            scope_mode="world",
        ),
        request_manifest_path=None,
        hermes_session_id=None,
        outer_campaign_id="longmont-c2",
    )

    with pytest.raises(Exception) as bad_scope:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(
                campaign_id="longmont-c1",
                scope_mode="galaxy",
            ),
            request_manifest_path=None,
            hermes_session_id=None,
            outer_campaign_id="longmont-c2",
        )
    assert bad_scope.value.code == "invalid_request"  # type: ignore[attr-defined]

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

    with pytest.raises(Exception) as empty_pointer:
        validate_hermes_query_inputs(
            world_graph_context=SimpleNamespace(campaign_id="campaign:c1"),
            request_manifest_path=None,
            hermes_session_id=None,
            hermes_session_pointer="   ",
            outer_campaign_id="campaign:c1",
        )
    assert empty_pointer.value.code == "hermes_session_pointer_invalid"  # type: ignore[attr-defined]


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
    assert request.focus == {"kind": "session", "sessionId": "session-21", "campaignId": None}
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

    partial_state, _, warnings, _, _, _ = classify_hermes_graph_result(
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

    matched_without_anchors_state, matched_answer, *_ = classify_hermes_graph_result(
        _ok_result(
            events=[_tool_event(outcome="enough", source_anchor_ids=[])],
        ),
        scope=scope,
    )
    assert matched_without_anchors_state == "grounded"
    assert matched_answer.startswith("Tripod")

    no_evidence_state, *_ = classify_hermes_graph_result(
        _ok_result(
            events=[
                _tool_event(
                    outcome="enough",
                    source_anchor_ids=[],
                    matched_node_ids=[],
                    relationship_ids=[],
                )
            ],
        ),
        scope=scope,
    )
    assert no_evidence_state == "abstained"

    prose_only_state, *_ = classify_hermes_graph_result(
        _ok_result(events=[]),
        scope=scope,
    )
    assert prose_only_state == "abstained"

    mismatch_state, _, _, codes, error_code, _ = classify_hermes_graph_result(
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
        state, _, _, _, mapped, _ = classify_hermes_graph_result(
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
        session_base=tmp_path / "live-session",
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
    assert response["grounding"]["source_anchor_count"] == 0
    assert response["grounding"]["graph_reference_count"] == 0
    assert response["citations"] == [
        {
            "schema": "dmb_world_graph_anchor_citation_v1",
            "kind": "world_graph_anchor",
            "anchor_id": "anchor:a1",
            "world_id": "world:eldyrwild",
            "campaign_id": "campaign:c1",
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "revision_id": "revision:resolved-server",
        },
        {
            "schema": "dmb_world_graph_anchor_citation_v1",
            "kind": "world_graph_anchor",
            "anchor_id": "anchor:a2",
            "world_id": "world:eldyrwild",
            "campaign_id": "campaign:c1",
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "revision_id": "revision:resolved-server",
        },
    ]
    assert response["hermes_session"] is not None
    assert response["hermes_session"]["sessionId"].startswith("hptr-")
    assert response["hermes_session"]["runtime"] == "process_isolated"
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
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
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

    # Product path: Plan packet stays C2/session 22 while graph lens is C1-only.
    cross_campaign = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 22,
            "mode": "live",
            "query_backend": "hermes",
            "text": "Where is Tripod?",
            "world_graph_context": {
                **GRAPH_NESTED,
                "campaign_id": "longmont-c1",
                "scope_mode": "campaign",
                "focus": {"kind": "none", "session_id": None, "campaign_id": None},
            },
        },
    )
    assert cross_campaign.status_code == 200
    assert cross_campaign.json()["mode"] == "hermes_graph_agent"
    assert len(host.calls) == 1
    host.calls.clear()

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
    assert body["hermes_session"] is not None
    assert body["hermes_session"]["sessionId"].startswith("hptr-")
    assert len(body["citations"]) == 1
    assert body["citations"][0]["kind"] == "world_graph_anchor"
    assert body["citations"][0]["anchor_id"] == "anchor:a1"
    assert body["citations"][0]["revision_id"] == "revision:http"
    assert body["grounding"]["source_anchor_count"] == 0
    assert body["grounding"]["graph_reference_count"] == 0
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


def test_missing_scope_fields_never_ground() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    cases = [
        _tool_event(world_id=None, source_anchor_ids=["source-anchor:v1:a"]),
        _tool_event(campaign_id=None, source_anchor_ids=["source-anchor:v1:b"]),
        _tool_event(focus=None, source_anchor_ids=["source-anchor:v1:c"]),
        _tool_event(admissibility=None, source_anchor_ids=["source-anchor:v1:d"]),
        _tool_event(revision_pin=None, source_anchor_ids=["source-anchor:v1:e"]),
        HermesGraphToolEvent(
            tool_name="search_campaign_graph",
            state="completion",
            duration_ms=1.0,
            world_id=None,
            campaign_id=None,
            focus=None,
            admissibility=None,
            revision_pin=None,
            bounded_ids={},
            retrieval_schema="dmb_world_graph_retrieval_result_v1",
            outcome="enough",
            matched_node_ids=[],
            relationship_ids=[],
            source_anchor_ids=["source-anchor:v1:omitted"],
            diagnostic_codes=[],
        ),
        _tool_event(
            outcome="not-a-canonical-outcome",
            source_anchor_ids=["source-anchor:v1:bad-outcome"],
        ),
    ]
    for event in cases:
        state, *_ = classify_hermes_graph_result(
            _ok_result(events=[event]),
            scope=scope,
        )
        assert state != "grounded"
        assert state != "partial"


def test_graph_tool_error_events_are_typed_errors_not_abstention() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )

    alone_state, alone_answer, _, alone_codes, alone_error, _ = classify_hermes_graph_result(
        _ok_result(
            final_response="model prose after tool failure",
            events=[
                _tool_event(
                    state="error",
                    outcome=None,
                    source_anchor_ids=[],
                    diagnostic_codes=["invalid_arguments"],
                    retrieval_schema="dmb_world_graph_retrieval_error_v1",
                )
            ],
        ),
        scope=scope,
    )
    assert alone_state == "error"
    assert alone_answer == EXECUTION_ERROR_ANSWER
    assert alone_answer != ABSTENTION_ANSWER
    assert alone_error == "invalid_arguments"
    assert "invalid_arguments" in alone_codes

    no_completion_state, _, _, _, no_completion_error, _ = classify_hermes_graph_result(
        _ok_result(
            events=[
                _tool_event(
                    state="error",
                    outcome=None,
                    source_anchor_ids=[],
                    diagnostic_codes=["integrity_failure"],
                ),
                _tool_event(outcome="empty", source_anchor_ids=[]),
            ]
        ),
        scope=scope,
    )
    assert no_completion_state == "error"
    assert no_completion_error == "integrity_failure"

    recovered_state, recovered_answer, *_ = classify_hermes_graph_result(
        _ok_result(
            events=[
                _tool_event(
                    state="error",
                    outcome=None,
                    source_anchor_ids=[],
                    diagnostic_codes=["transient_failure"],
                ),
                _tool_event(source_anchor_ids=["anchor:recovered"]),
            ]
        ),
        scope=scope,
    )
    assert recovered_state == "grounded"
    assert recovered_answer.startswith("Tripod")


def test_scope_mismatch_events_are_redacted_from_serialized_response(
    tmp_path: Path,
) -> None:
    host = _FakeHost(
        _ok_result(
            events=[
                _tool_event(
                    campaign_id="campaign:FOREIGN-LEAK",
                    revision_pin="revision:FOREIGN-REV",
                    source_anchor_ids=["source-anchor:FOREIGN-ANCHOR"],
                    matched_node_ids=["node:FOREIGN-NODE"],
                    relationship_ids=["edge:FOREIGN-EDGE"],
                )
            ]
        )
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-redact",
        turn_id="agent-turn-redact",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] == "error"
    assert response["diagnostics"]["error_code"] == "hermes_grounding_contract_error"
    blob = json.dumps(response)
    assert "FOREIGN-LEAK" not in blob
    assert "FOREIGN-REV" not in blob
    assert "FOREIGN-ANCHOR" not in blob
    assert "FOREIGN-NODE" not in blob
    assert "FOREIGN-EDGE" not in blob
    assert response["agent_trace"]["tool_events"] == []
    assert "hermes_tool_event_scope_mismatch" in response["grounding"]["diagnostic_codes"]


def test_agent_trace_preserves_plan_shell_fields(tmp_path: Path) -> None:
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id=None,
        turn_id=None,
        root=tmp_path,
        host_factory=lambda: _FakeHost(_ok_result()),  # type: ignore[arg-type, return-value]
    )
    trace = response["agent_trace"]
    assert trace["usage"] == {
        "available": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    assert trace["steps"] == []
    assert trace["context_summary"] == {}
    assert trace["artifact_refs"] == []
    assert isinstance(trace["tool_events"], list)
    assert trace["tool_event_count"] >= 1
    assert trace["final_response_present"] is True


def test_malformed_tool_event_returns_typed_contract_error_not_500() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    malformed = _tool_event(source_anchor_ids=["anchor:MALFORMED-LEAK"])
    object.__setattr__(malformed, "bounded_ids", None)
    object.__setattr__(malformed, "source_anchor_ids", None)
    result = _ok_result(events=[malformed])

    response = build_hermes_graph_product_response(
        packet=PACKET,
        result=result,
        scope=scope,
        agent_thread_id="agent-thread-malformed",
        turn_id="agent-turn-malformed",
        started_at="2026-07-14T18:00:00Z",
        completed_at="2026-07-14T18:00:01Z",
        elapsed_ms=1,
        world_graph_context=READY_ENVELOPE,
    )
    assert response["status"] == "error"
    assert response["grounding"]["state"] == "error"
    assert response["diagnostics"]["error_code"] == "hermes_grounding_contract_error"
    assert response["agent_trace"]["tool_events"] == []
    blob = json.dumps(response)
    assert "MALFORMED-LEAK" not in blob
    assert '"bounded_ids": null' not in blob
    assert '"source_anchor_ids": null' not in blob


def test_http_world_graph_unavailable_is_typed_not_422(
    client: TestClient,
    isolated_session: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_fallback: None,
) -> None:
    host_calls: list[str] = []

    def boom() -> Any:
        host_calls.append("called")
        raise AssertionError("host must not be called when graph is unavailable")

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        lambda *args, **kwargs: {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "unavailable",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "revision_id": None,
            "head_revision_id": None,
            "is_head": None,
            "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
            "admissibility": "gm",
            "query_text": "Where is Tripod?",
            "matched_node_ids": [],
            "nodes": [],
            "relationships": [],
            "attributes": [],
            "projection_truncated": False,
            "diagnostics": [],
            "warning_codes": ["world_graph_unavailable"],
            "trust_boundary": {},
        },
    )
    monkeypatch.setattr(hermes_graph_query_mod, "get_hermes_graph_agent_host", boom)
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
    assert body["diagnostics"]["error_code"] == "world_graph_unavailable"
    assert body["answer"] == UNAVAILABLE_ANSWER
    assert "world_graph_context_invalid" not in json.dumps(body)
    assert body.get("schema") == "dmb_live_query_response_v1"
    assert host_calls == []
    assert response.status_code != 422

def _product_response_for_events(
    events: list[HermesGraphToolEvent],
    *,
    final_response: str = "Tripod stands at the North Gate.",
) -> dict[str, Any]:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    return build_hermes_graph_product_response(
        packet=PACKET,
        result=_ok_result(final_response=final_response, events=events),
        scope=scope,
        agent_thread_id="agent-thread-cite",
        turn_id="agent-turn-cite",
        started_at="2026-07-14T18:00:00Z",
        completed_at="2026-07-14T18:00:01Z",
        elapsed_ms=1,
        world_graph_context=READY_ENVELOPE,
    )


def test_graph_citations_shape_order_dedupe_and_scope() -> None:
    response = _product_response_for_events(
        [
            _tool_event(source_anchor_ids=["anchor:first", "anchor:second"]),
            _tool_event(source_anchor_ids=["anchor:second", "anchor:third"]),
        ]
    )
    assert response["grounding"]["state"] == "grounded"
    citations = response["citations"]
    assert [c["anchor_id"] for c in citations] == [
        "anchor:first",
        "anchor:second",
        "anchor:third",
    ]
    assert response["grounding"]["source_anchor_count"] == 0
    assert response["grounding"]["graph_reference_count"] == 0
    for citation in citations:
        assert citation["schema"] == "dmb_world_graph_anchor_citation_v1"
        assert citation["kind"] == "world_graph_anchor"
        assert citation["world_id"] == "world:eldyrwild"
        assert citation["campaign_id"] == "campaign:c1"
        assert citation["focus"] == {"kind": "session", "session_id": "session-21", "campaign_id": None}
        assert citation["admissibility"] == "gm"
        assert citation["revision_id"] == "revision:resolved-server"
        assert "path" not in citation
        assert "evidence_id" not in citation


def test_partial_emits_citations_abstained_and_error_do_not() -> None:
    partial = _product_response_for_events(
        [_tool_event(outcome="partial", source_anchor_ids=["anchor:partial"])],
    )
    assert partial["grounding"]["state"] == "partial"
    assert [c["anchor_id"] for c in partial["citations"]] == ["anchor:partial"]

    abstained = _product_response_for_events(
        [_tool_event(outcome="empty", source_anchor_ids=[])],
        final_response="discard me",
    )
    assert abstained["grounding"]["state"] == "abstained"
    assert abstained["citations"] == []

    errored = _product_response_for_events(
        [
            _tool_event(
                state="error",
                outcome=None,
                source_anchor_ids=[],
                diagnostic_codes=["adapter_error"],
            )
        ],
        final_response="discard me",
    )
    assert errored["grounding"]["state"] == "error"
    assert errored["citations"] == []


def test_ordered_event_citation_matrix() -> None:
    assert _product_response_for_events(
        [
            _tool_event(
                state="error",
                outcome=None,
                source_anchor_ids=[],
                diagnostic_codes=["adapter_error"],
            )
        ],
        final_response="x",
    )["citations"] == []

    assert _product_response_for_events(
        [
            _tool_event(
                state="error",
                outcome=None,
                source_anchor_ids=[],
                diagnostic_codes=["adapter_error"],
            ),
            _tool_event(outcome="empty", source_anchor_ids=[]),
        ],
        final_response="x",
    )["citations"] == []

    recovered = _product_response_for_events(
        [
            _tool_event(
                state="error",
                outcome=None,
                source_anchor_ids=["anchor:FROM_ERROR_ONLY"],
                diagnostic_codes=["adapter_error"],
            ),
            _tool_event(source_anchor_ids=["anchor:recovered"]),
        ]
    )
    assert recovered["grounding"]["state"] == "grounded"
    assert [c["anchor_id"] for c in recovered["citations"]] == ["anchor:recovered"]
    assert all(c["anchor_id"] != "anchor:FROM_ERROR_ONLY" for c in recovered["citations"])

    failed = _product_response_for_events(
        [
            _tool_event(source_anchor_ids=["anchor:EARLY_EVIDENCE"]),
            _tool_event(
                state="error",
                outcome=None,
                source_anchor_ids=[],
                diagnostic_codes=["adapter_error"],
            ),
        ]
    )
    assert failed["grounding"]["state"] == "error"
    assert failed["citations"] == []

    mismatched = _product_response_for_events(
        [
            _tool_event(
                campaign_id="FOREIGN_CAMPAIGN_ID",
                revision_pin="FOREIGN_REVISION_ID",
                source_anchor_ids=["FOREIGN_SOURCE_ANCHOR_ID"],
                matched_node_ids=["FOREIGN_WORLD_ID"],
            ),
            _tool_event(source_anchor_ids=["anchor:valid"]),
        ]
    )
    assert mismatched["grounding"]["state"] == "error"
    assert mismatched["citations"] == []
    leak_blob = json.dumps(mismatched)
    assert "FOREIGN_CAMPAIGN_ID" not in leak_blob
    assert "FOREIGN_REVISION_ID" not in leak_blob
    assert "FOREIGN_SOURCE_ANCHOR_ID" not in leak_blob
    assert "/foreign/absolute/path.md" not in leak_blob


def test_model_prose_never_creates_citations() -> None:
    response = _product_response_for_events(
        [],
        final_response=(
            "See source-anchor:v1:FROM_PROSE and /foreign/absolute/path.md "
            "RAW_PROMPT_SECRET RAW_TOOL_ARGUMENT_SECRET RAW_SOURCE_BODY_SECRET "
            "RAW_HERMES_MESSAGE_SECRET"
        ),
    )
    assert response["grounding"]["state"] == "abstained"
    assert response["citations"] == []
    blob = json.dumps(response)
    assert "FROM_PROSE" not in blob
    assert "/foreign/absolute/path.md" not in blob
    assert "RAW_PROMPT_SECRET" not in blob
    assert "RAW_TOOL_ARGUMENT_SECRET" not in blob
    assert "RAW_SOURCE_BODY_SECRET" not in blob
    assert "RAW_HERMES_MESSAGE_SECRET" not in blob


def test_malformed_mixed_with_valid_emits_no_citations() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    valid = _tool_event(source_anchor_ids=["anchor:valid-sibling"])
    malformed = _tool_event(source_anchor_ids=["anchor:MALFORMED-MIX"])
    object.__setattr__(malformed, "bounded_ids", None)
    response = build_hermes_graph_product_response(
        packet=PACKET,
        result=_ok_result(events=[valid, malformed]),
        scope=scope,
        agent_thread_id="agent-thread-mix",
        turn_id="agent-turn-mix",
        started_at="2026-07-14T18:00:00Z",
        completed_at="2026-07-14T18:00:01Z",
        elapsed_ms=1,
    )
    assert response["grounding"]["state"] == "error"
    assert response["citations"] == []
    blob = json.dumps(response)
    assert "MALFORMED-MIX" not in blob
    assert "anchor:valid-sibling" not in blob


VALID_HISTORY = [
    {"role": "user", "content": "What do we know about Tripod Null-Calf at the North Gate?"},
    {
        "role": "assistant",
        "content": "Tripod Null-Calf is a siege scout at revision FOREIGN_REVISION_A.",
    },
]


def test_normalize_rejects_malformed_history() -> None:
    from apps.live_control_server.services.hermes_graph_query import (
        normalize_hermes_conversation_history,
    )

    with pytest.raises(Exception) as odd:
        normalize_hermes_conversation_history([{"role": "user", "content": "only one"}])
    assert odd.value.code == "hermes_history_invalid"  # type: ignore[attr-defined]

    with pytest.raises(Exception) as bad_role:
        normalize_hermes_conversation_history(
            [
                {"role": "system", "content": "hidden"},
                {"role": "assistant", "content": "hi"},
            ]
        )
    assert bad_role.value.code == "hermes_history_invalid"  # type: ignore[attr-defined]


def test_follow_up_passes_exact_history_to_host(tmp_path: Path) -> None:
    host = _FakeHost(_ok_result())
    response = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-followup",
        turn_id="turn-2",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=VALID_HISTORY,
    )
    assert len(host.calls) == 1
    assert host.calls[0].conversation_history == VALID_HISTORY
    assert host.calls[0].session_id is None
    assert response["agent_trace"]["conversation_context"] == {
        "history_present": True,
        "message_count": 2,
        "pair_count": 1,
        "payload_shape": "role_content_only",
        "graph_metadata_in_history": False,
        "hermes_session_pointer_in_request": False,
        "hermes_session_pointer_status": "absent",
        "worker_pid_changed": False,
        "fresh_graph_revision_used": True,
    }


def test_revision_a_history_with_revision_b_dispatch_uses_only_b(tmp_path: Path) -> None:
    envelope_b = {
        **READY_ENVELOPE,
        "revision_id": "FOREIGN_REVISION_B",
        "head_revision_id": "FOREIGN_REVISION_B",
    }
    host = _FakeHost(
        _ok_result(
            events=[
                _tool_event(
                    revision_pin="FOREIGN_REVISION_B",
                    source_anchor_ids=["FOREIGN_SOURCE_ANCHOR_B"],
                )
            ]
        )
    )
    response = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=envelope_b,
        agent_thread_id="agent-thread-revision",
        turn_id="turn-revision-b",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=[
            {
                "role": "user",
                "content": "Tripod at FOREIGN_REVISION_A with FOREIGN_SOURCE_ANCHOR_A",
            },
            {
                "role": "assistant",
                "content": "Revision FOREIGN_REVISION_A prose only.",
            },
        ],
    )
    assert host.calls[0].revision_pin == "FOREIGN_REVISION_B"
    assert response["grounding"]["revision_id"] == "FOREIGN_REVISION_B"
    assert [c["anchor_id"] for c in response["citations"]] == ["FOREIGN_SOURCE_ANCHOR_B"]
    blob = json.dumps(response)
    assert "FOREIGN_REVISION_A" not in blob
    assert "FOREIGN_SOURCE_ANCHOR_A" not in blob


def test_contradictory_assistant_prose_does_not_create_authority(tmp_path: Path) -> None:
    contradictory_history = [
        {"role": "user", "content": "What do we know about Tripod Null-Calf?"},
        {
            "role": "assistant",
            "content": (
                "Tripod Null-Calf is allied with the Gate Wardens and has no "
                "relationship to the North Gate."
            ),
        },
    ]
    host = _FakeHost(
        _ok_result(
            final_response="Tripod threatens the North Gate per current graph evidence.",
            events=[
                _tool_event(
                    source_anchor_ids=["FOREIGN_SOURCE_ANCHOR_B"],
                )
            ],
        )
    )
    response = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-contradiction",
        turn_id="turn-contradiction",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=contradictory_history,
    )
    assert response["answer"] == "Tripod threatens the North Gate per current graph evidence."
    assert response["citations"][0]["anchor_id"] == "FOREIGN_SOURCE_ANCHOR_B"
    assert "Gate Wardens" not in json.dumps(response["citations"])


def test_valid_history_graph_gap_still_abstains(tmp_path: Path) -> None:
    host = _FakeHost(
        _ok_result(
            final_response="History prose should not answer this.",
            events=[_tool_event(outcome="empty", source_anchor_ids=[])],
        )
    )
    response = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-gap",
        turn_id="turn-gap",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=VALID_HISTORY,
    )
    assert response["grounding"]["state"] == "abstained"
    assert response["answer"] == ABSTENTION_ANSWER
    assert response["citations"] == []


class _EchoRetrievalSessionHost:
    """Echoes back retrieval_session_id/retrieval_session like the real Hermes runtime.

    ``_FakeHost``/``_ok_result`` do not echo these fields, so they always miss the
    server-side claim ledger and exercise the legacy no-session fallback path
    instead of ``validate_structured_answer``. Production Hermes turns always
    echo them (see ``run_hermes_graph_agent_turn``), so tests of the claim-ledger
    path need to reproduce that here.
    """

    def __init__(
        self,
        *,
        final_response: str | None,
        tool_events: list[HermesGraphToolEvent],
        answer_scope: str | None = None,
    ) -> None:
        self.final_response = final_response
        self.tool_events = tool_events
        self.answer_scope = answer_scope
        self.calls: list[HermesGraphAgentTurnRequest] = []

    def execute(self, request: HermesGraphAgentTurnRequest) -> HermesGraphAgentTurnResult:
        self.calls.append(request)
        return HermesGraphAgentTurnResult(
            status="ok",
            final_response=self.final_response,
            messages=[],
            hermes_session_id="hermes-sess-echo",
            tool_events=list(self.tool_events),
            retrieval_session_id=request.retrieval_session_id,
            retrieval_session=(
                dict(request.retrieval_session)
                if request.retrieval_session is not None
                else None
            ),
            process_isolation="process_exclusive",
            answer_scope=self.answer_scope,  # type: ignore[arg-type]
        )


# No matched_node_ids/nodes — an empty claim ledger, distinct from READY_ENVELOPE
# (whose matched_node_ids alone are enough to synthesize an identity claim; see
# claims_from_preflight_envelope's "matched durable IDs are authoritative" path).
EMPTY_CLAIM_ENVELOPE = {
    **READY_ENVELOPE,
    "status": "empty",
    "matched_node_ids": [],
    "nodes": [],
}


def test_zero_tool_calls_with_prose_still_abstains(tmp_path: Path) -> None:
    """Hermes must explicitly declare conversation context before prose is trusted."""
    host = _EchoRetrievalSessionHost(
        final_response="We covered Tripod Null-Calf's position and the siege timeline.",
        tool_events=[],
    )
    response = run_hermes_graph_query(
        text="What have we discussed so far?",
        packet=PACKET,
        graph_envelope=EMPTY_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-conversation",
        turn_id="turn-conversation",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=VALID_HISTORY,
    )
    assert response["grounding"]["state"] == "abstained"
    assert response["status"] == "partial"
    assert response["answer"] == ABSTENTION_ANSWER
    assert response["citations"] == []
    assert "conversation_context_no_tool_calls" not in response["grounding"]["reason_codes"]
    assert response["agent_trace"]["validator_path"] == "claim_ledger_validation"


def test_explicit_declare_conversation_context_turn(tmp_path: Path) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="We discussed siege prep and Tripod's position.",
        tool_events=[_declare_tool_event()],
        answer_scope="conversation_context",
    )
    response = run_hermes_graph_query(
        text="What have we discussed so far?",
        packet=PACKET,
        graph_envelope=EMPTY_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-declare",
        turn_id="turn-declare",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=VALID_HISTORY,
    )
    assert response["grounding"]["state"] == "conversation_context"
    assert response["answer"] == "We discussed siege prep and Tripod's position."
    assert "explicit_conversation_context" in response["grounding"]["reason_codes"]
    trace = response["agent_trace"]
    assert trace["answer_scope"] == "conversation_context"
    assert trace["tool_event_count"] == 1
    assert trace["evidence_event_count"] == 0
    assert trace["final_response_present"] is True
    assert trace["validator_path"] == "explicit_conversation_context"


def test_explicit_conversation_scope_ignores_preflight_claims(
    tmp_path: Path,
) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="We discussed Tripod's position and the siege prep question.",
        tool_events=[_declare_tool_event()],
        answer_scope="conversation_context",
    )
    response = run_hermes_graph_query(
        text="What have we discussed so far?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="agent-thread-conversation-preflight",
        turn_id="turn-conversation-preflight",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        conversation_history=VALID_HISTORY,
    )

    assert response["grounding"]["state"] == "conversation_context"
    assert response["grounding"]["answer_authority"] == "explicit_conversation_context"
    assert response["answer"] == (
        "We discussed Tripod's position and the siege prep question."
    )
    assert response["grounding"]["accepted_claim_ids"] == []
    assert response["graph_references"] == []
    assert response["agent_trace"]["validator_path"] == "explicit_conversation_context"


def test_graph_context_synthesis_keeps_natural_answer_and_ledger_support(
    tmp_path: Path,
) -> None:
    host = _EchoRetrievalSessionHost(
        final_response=(
            "Tripod is at the North Gate and controls the Shepherd's army."
        ),
        tool_events=[_tool_event()],
    )
    graph_envelope = {
        **READY_ENVELOPE,
        "nodes": [{"node_id": "threat:tripod", "label": "Tripod"}],
        "matched_node_ids": ["threat:tripod"],
        "attributes": [
            {
                "assertion_id": "assertion:loc",
                "subject_node_id": "threat:tripod",
                "predicate": "location",
                "text_value": "North Gate",
                "authority_class": "accepted_explicit_attribute",
            }
        ],
    }
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=graph_envelope,
        agent_thread_id="agent-thread-natural-answer",
        turn_id="turn-natural-answer",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )

    assert response["answer"] == (
        "Tripod is at the North Gate and controls the Shepherd's army."
    )
    assert response["agent_trace"]["validator_path"] == "graph_context_synthesis"
    assert response["grounding"]["answer_authority"] == "graph_context_synthesis"
    support_text = response["grounding"]["support_claim_ledger_text"]
    assert "Graph-grounded facts for this turn:" in support_text
    assert "location — North Gate" in support_text
    assert "controls the Shepherd's army" not in support_text
    assert "assertion:loc" in response["grounding"]["accepted_claim_ids"]


_FACTUAL_CLAIM_ENVELOPE = {
    **READY_ENVELOPE,
    "nodes": [{"node_id": "threat:tripod", "label": "Tripod"}],
    "matched_node_ids": ["threat:tripod"],
    "attributes": [
        {
            "assertion_id": "assertion:loc",
            "subject_node_id": "threat:tripod",
            "predicate": "location",
            "text_value": "North Gate",
            "authority_class": "accepted_explicit_attribute",
        }
    ],
}


def _cardinality_error_event(code: str) -> HermesGraphToolEvent:
    return _tool_event(
        state="error",
        outcome=None,
        source_anchor_ids=[],
        matched_node_ids=[],
        diagnostic_codes=[code],
        retrieval_schema="dmb_world_graph_retrieval_error_v1",
    )


def test_too_many_targets_after_claims_landed_proceeds_to_validation(
    tmp_path: Path,
) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="Tripod is at the North Gate.",
        tool_events=[
            _tool_event(source_anchor_ids=["anchor:prior"]),
            _cardinality_error_event("too_many_targets"),
        ],
    )
    response = run_hermes_graph_query(
        text="Where is Tripod relative to Pippa?",
        packet=PACKET,
        graph_envelope=_FACTUAL_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-cardinality-recover",
        turn_id="turn-cardinality-recover",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] != "error"
    assert response["grounding"]["acceptance_state"] != "execution_error"
    assert response["answer"] != EXECUTION_ERROR_ANSWER
    assert response["answer"] == "Tripod is at the North Gate."
    assert "too_many_targets" in response["grounding"]["diagnostic_codes"]
    assert any("too_many_targets" in w for w in response["warnings"])
    assert response["agent_trace"]["validator_path"] == "graph_context_synthesis"


def test_ambiguous_target_with_preflight_claims_non_fatal(tmp_path: Path) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="Tripod is at the North Gate.",
        tool_events=[_cardinality_error_event("ambiguous_target")],
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=_FACTUAL_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-ambiguous-recover",
        turn_id="turn-ambiguous-recover",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] != "error"
    assert response["grounding"]["acceptance_state"] != "execution_error"
    assert response["answer"] != EXECUTION_ERROR_ANSWER
    assert "ambiguous_target" in response["grounding"]["diagnostic_codes"]
    assert response["agent_trace"]["validator_path"] == "graph_context_synthesis"


def test_too_many_targets_without_claims_stays_execution_error(tmp_path: Path) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="Should not surface.",
        tool_events=[_cardinality_error_event("too_many_targets")],
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=EMPTY_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-cardinality-fatal",
        turn_id="turn-cardinality-fatal",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] == "error"
    assert response["grounding"]["acceptance_state"] == "execution_error"
    assert response["answer"] == EXECUTION_ERROR_ANSWER
    assert response["diagnostics"]["error_code"] == "too_many_targets"


def test_integrity_failure_still_fatal_with_claims(tmp_path: Path) -> None:
    host = _EchoRetrievalSessionHost(
        final_response="Should not surface.",
        tool_events=[
            _tool_event(source_anchor_ids=["anchor:prior"]),
            _cardinality_error_event("integrity_failure"),
        ],
    )
    response = run_hermes_graph_query(
        text="Where is Tripod?",
        packet=PACKET,
        graph_envelope=_FACTUAL_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-integrity-fatal",
        turn_id="turn-integrity-fatal",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] == "error"
    assert response["grounding"]["acceptance_state"] == "execution_error"
    assert response["answer"] == EXECUTION_ERROR_ANSWER
    assert response["diagnostics"]["error_code"] == "integrity_failure"


def test_cardinality_error_recovered_by_later_evidence_still_works() -> None:
    _, scope = build_hermes_graph_turn_request(
        question="q",
        graph_envelope=READY_ENVELOPE,
        root=Path("/tmp"),
    )
    recovered_state, recovered_answer, *_ = classify_hermes_graph_result(
        _ok_result(
            events=[
                _cardinality_error_event("too_many_targets"),
                _tool_event(source_anchor_ids=["anchor:recovered"]),
            ]
        ),
        scope=scope,
    )
    assert recovered_state == "grounded"
    assert recovered_answer.startswith("Tripod")


def test_expand_steer_mentions_neighborhood_for_multi_entity() -> None:
    from apps.live_control_server.services.hermes_graph_agent import _GRAPH_SYSTEM_POLICY
    from apps.live_control_server.services.hermes_graph_interaction_tools import (
        hermes_graph_interaction_tool_definitions,
    )

    assert "neighborhood" in _GRAPH_SYSTEM_POLICY
    assert "multi-entity" in _GRAPH_SYSTEM_POLICY
    assert "one node at a time" in _GRAPH_SYSTEM_POLICY
    expand = next(
        item
        for item in hermes_graph_interaction_tool_definitions()
        if item["function"]["name"] == "expand_graph_retrieval"
    )
    description = expand["function"]["description"]
    assert "prefer neighborhood" in description
    assert "separately for each single node" in description
    expand_schema = expand["function"]["parameters"]
    schema_desc = expand_schema.get("description") or ""
    if schema_desc:
        assert "neighborhood" in schema_desc


def test_zero_tool_calls_without_prose_still_abstains(tmp_path: Path) -> None:
    """Zero tool calls and an empty final_response — still nothing to answer with."""
    host = _EchoRetrievalSessionHost(final_response="", tool_events=[])
    response = run_hermes_graph_query(
        text="What have we discussed so far?",
        packet=PACKET,
        graph_envelope=EMPTY_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-conversation-empty",
        turn_id="turn-conversation-empty",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] == "abstained"
    assert response["answer"] == ABSTENTION_ANSWER


def test_nonzero_tool_calls_with_empty_evidence_still_abstains(tmp_path: Path) -> None:
    """Agent did query the graph this turn but got nothing back — real abstention."""
    host = _EchoRetrievalSessionHost(
        final_response="Prose after an empty graph query should still be discarded.",
        tool_events=[_tool_event(outcome="empty", source_anchor_ids=[])],
    )
    response = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=EMPTY_CLAIM_ENVELOPE,
        agent_thread_id="agent-thread-nonzero-empty",
        turn_id="turn-nonzero-empty",
        root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    assert response["grounding"]["state"] == "abstained"
    assert response["answer"] == ABSTENTION_ANSWER


def test_s1_empty_graph_with_latest_recap_is_partial_not_abstention(
    tmp_path: Path,
) -> None:
    recap_path = tmp_path / "Session 24 - Recap.md"
    recap_path.write_text(
        "The party held the North Gate while Tripod Null-Calf pressed the wall.\n",
        encoding="utf-8",
    )
    s1_envelope = {
        **READY_ENVELOPE,
        "status": "empty",
        "matched_node_ids": [],
        "nodes": [],
        "warning_codes": ["graph_context_empty"],
        "latest_recap_change": {
            "schema": "dmb_latest_recap_change_context_v1",
            "status": "ready",
            "campaign_id": "longmont-c2",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {
                "artifact_id": "longmont-c2/session-24",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_recap_path": "Session 24 - Recap.md",
            },
            "comparison_boundary": {
                "kind": "latest_admitted_recap_to_graph_head",
                "recap_session_id": "session-24",
                "graph_latest_session_id": "session-23",
                "graph_revision_id": "revision:resolved-server",
            },
            "diagnostic_codes": ["latest_recap_not_in_graph_head"],
        },
    }

    class _EchoSessionHost:
        def __init__(self) -> None:
            self.calls: list[HermesGraphAgentTurnRequest] = []

        def execute(
            self,
            request: HermesGraphAgentTurnRequest,
        ) -> HermesGraphAgentTurnResult:
            self.calls.append(request)
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response=(
                    "Session 24 keeps the siege at the North Gate under pressure; "
                    "graph memory still lags at session-23."
                ),
                messages=[],
                hermes_session_id="hermes-s1-empty",
                tool_events=[
                    _tool_event(
                        outcome="empty",
                        source_anchor_ids=[],
                        matched_node_ids=[],
                        relationship_ids=[],
                    )
                ],
                retrieval_session_id=request.retrieval_session_id,
                retrieval_session=(
                    dict(request.retrieval_session)
                    if request.retrieval_session is not None
                    else None
                ),
            )

    host = _EchoSessionHost()
    response = run_hermes_graph_query(
        text="What changed after the latest ingested recap?",
        packet=PACKET,
        graph_envelope=s1_envelope,
        agent_thread_id="agent-thread-s1",
        turn_id="turn-s1",
        root=tmp_path,
        corpus_root=tmp_path,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )

    assert host.calls
    assert host.calls[0].retrieval_session is not None
    assert host.calls[0].retrieval_session["latest_recap_change"]["outcome"] == "memory_lag"
    assert "admitted_recap_excerpt" in host.calls[0].retrieval_session["latest_recap_change"]
    assert response["grounding"]["state"] == "partial"
    assert response["grounding"]["acceptance_state"] == "partial_coverage"
    assert "no_admissible_claims" not in response["grounding"]["reason_codes"]
    assert "hermes_agent_answer" in response["grounding"]["reason_codes"]
    assert response["answer"].startswith("Session 24 keeps the siege")
    assert "From the admitted session-24 recap" not in response["answer"]
    assert "memory lag" not in response["answer"].lower()
    assert response["s1_support"]["lag_disclosure"]
    assert "memory lag" in response["s1_support"]["lag_disclosure"].lower()
    assert "North Gate" in response["s1_support"]["admitted_recap_excerpt"]
    assert response["latest_recap_change"]["outcome"] == "memory_lag"
    assert "lag_disclosure" in response["latest_recap_change"]


def test_s1_admitted_recap_read_uses_corpus_root_not_graph_store_root(
    tmp_path: Path,
) -> None:
    """Live path uses world_graph_root (out/) for graph and repo_root for corpus."""
    graph_root = tmp_path / "out"
    graph_root.mkdir()
    corpus_root = tmp_path / "repo"
    corpus_root.mkdir()
    (corpus_root / "Session 24 - Recap.md").write_text(
        "The party held the North Gate while Tripod Null-Calf pressed the wall.\n",
        encoding="utf-8",
    )
    s1_envelope = {
        **READY_ENVELOPE,
        "status": "empty",
        "matched_node_ids": [],
        "nodes": [],
        "warning_codes": ["graph_context_empty"],
        "latest_recap_change": {
            "schema": "dmb_latest_recap_change_context_v1",
            "status": "ready",
            "campaign_id": "longmont-c2",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {
                "artifact_id": "longmont-c2/session-24",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_recap_path": "Session 24 - Recap.md",
            },
            "comparison_boundary": {
                "kind": "latest_admitted_recap_to_graph_head",
                "recap_session_id": "session-24",
                "graph_latest_session_id": "session-23",
                "graph_revision_id": "revision:resolved-server",
            },
            "diagnostic_codes": ["latest_recap_not_in_graph_head"],
        },
    }

    class _EchoSessionHost:
        def execute(
            self,
            request: HermesGraphAgentTurnRequest,
        ) -> HermesGraphAgentTurnResult:
            return HermesGraphAgentTurnResult(
                status="ok",
                final_response=(
                    "Session 24 keeps the siege at the North Gate under pressure; "
                    "graph memory still lags at session-23."
                ),
                messages=[],
                hermes_session_id="hermes-s1-roots",
                tool_events=[
                    _tool_event(
                        outcome="empty",
                        source_anchor_ids=[],
                        matched_node_ids=[],
                        relationship_ids=[],
                    )
                ],
                retrieval_session_id=request.retrieval_session_id,
                retrieval_session=(
                    dict(request.retrieval_session)
                    if request.retrieval_session is not None
                    else None
                ),
            )

    captured: list[HermesGraphAgentTurnRequest] = []

    class _CaptureHost(_EchoSessionHost):
        def execute(self, request: HermesGraphAgentTurnRequest) -> HermesGraphAgentTurnResult:
            captured.append(request)
            return super().execute(request)

    # Wrong corpus root: agent answer still fronts; excerpt is not attached.
    wrong = run_hermes_graph_query(
        text="What changed after the latest ingested recap?",
        packet=PACKET,
        graph_envelope=s1_envelope,
        agent_thread_id="agent-thread-s1-wrong",
        turn_id="turn-s1-wrong",
        root=graph_root,
        corpus_root=graph_root,
        host_factory=lambda: _CaptureHost(),  # type: ignore[arg-type, return-value]
    )
    assert wrong["answer"].startswith("Session 24 keeps the siege")
    assert "hermes_agent_answer" in wrong["grounding"]["reason_codes"]
    assert not (
        captured[0].retrieval_session or {}
    ).get("latest_recap_change", {}).get("admitted_recap_excerpt")

    captured.clear()
    right = run_hermes_graph_query(
        text="What changed after the latest ingested recap?",
        packet=PACKET,
        graph_envelope=s1_envelope,
        agent_thread_id="agent-thread-s1-right",
        turn_id="turn-s1-right",
        root=graph_root,
        corpus_root=corpus_root,
        host_factory=lambda: _CaptureHost(),  # type: ignore[arg-type, return-value]
    )
    assert right["answer"].startswith("Session 24 keeps the siege")
    assert "hermes_agent_answer" in right["grounding"]["reason_codes"]
    assert "North Gate" in (
        captured[0].retrieval_session or {}
    ).get("latest_recap_change", {}).get("admitted_recap_excerpt", "")


def test_invalid_service_history_fails_before_host(tmp_path: Path) -> None:
    host = _FakeHost(_ok_result())
    with pytest.raises(Exception) as exc:
        run_hermes_graph_query(
            text="follow-up",
            packet=PACKET,
            graph_envelope=READY_ENVELOPE,
            agent_thread_id="agent-thread-invalid",
            turn_id="turn-invalid",
            root=tmp_path,
            host_factory=lambda: host,  # type: ignore[arg-type, return-value]
            conversation_history={"role": "user", "content": "not a list"},
        )
    assert exc.value.code == "hermes_history_invalid"  # type: ignore[attr-defined]
    assert host.calls == []


def test_invalid_history_with_unavailable_envelope_still_rejects(
    tmp_path: Path,
) -> None:
    host = _FakeHost(_ok_result())
    unavailable = {
        **READY_ENVELOPE,
        "status": "unavailable",
        "revision_id": "",
        "warning_codes": ["world_graph_unavailable"],
    }
    with pytest.raises(Exception) as exc:
        run_hermes_graph_query(
            text="follow-up",
            packet=PACKET,
            graph_envelope=unavailable,
            agent_thread_id="agent-thread-unavail-invalid",
            turn_id="turn-unavail-invalid",
            root=tmp_path,
            host_factory=lambda: host,  # type: ignore[arg-type, return-value]
            conversation_history=[{"role": "user", "content": "solo"}],
        )
    assert exc.value.code == "hermes_history_invalid"  # type: ignore[attr-defined]
    assert host.calls == []


def test_invalid_history_fails_before_graph_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services.agent_world_graph_query_context import (
        AgentWorldGraphQueryContextRequest,
    )
    from apps.live_control_server.services.hermes_graph_query import (
        HermesGraphQueryRequestError,
    )

    def _resolver_must_not_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("graph resolver must not run for malformed history")

    monkeypatch.setattr(
        live_agent_loop,
        "resolve_agent_world_graph_query_context",
        _resolver_must_not_run,
    )
    monkeypatch.setattr(live_agent_loop, "world_graph_root", lambda: tmp_path)
    monkeypatch.setattr(
        live_agent_loop,
        "load_session",
        lambda *_a, **_k: ({"campaign_id": "longmont-c2", "session": 22}, {}, [], []),
    )
    monkeypatch.setattr(live_agent_loop, "session_dir", lambda: tmp_path)

    with pytest.raises(HermesGraphQueryRequestError) as exc:
        live_agent_loop.process_live_query(
            "follow-up",
            base=tmp_path,
            query_backend="hermes",
            world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
                {
                    "schema": "dmb_agent_world_graph_query_context_request_v1",
                    "world_id": "eldyrwild",
                    "campaign_id": "longmont-c2",
                    "focus": {"kind": "session", "session_id": "session-21", "campaign_id": None},
                    "admissibility": "gm",
                }
            ),
            outer_campaign_id="longmont-c2",
            conversation_history=[{"role": "user", "content": "solo"}],
        )
    assert exc.value.code == "hermes_history_invalid"


def test_first_turn_issues_opaque_pointer_and_persists_binding(tmp_path: Path) -> None:
    session_base = tmp_path / "live-session"
    host = _FakeHost(_ok_result(hermes_session_id="hermes-internal-s1"))
    response = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = response["hermes_session"]["sessionId"]
    assert pointer.startswith("hptr-")
    assert host.calls[0].session_id is None
    assert response["agent_trace"]["conversation_context"]["hermes_session_pointer_status"] == "absent"

    from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore

    store = HermesSessionPointerStore(session_base)
    binding = store.get_for_thread(
        campaign_id=str(PACKET["campaign_id"]),
        agent_thread_id="thread-a",
    )
    assert binding is not None
    assert binding.pointer_id == pointer
    assert binding.hermes_session_id == "hermes-internal-s1"
    assert binding.campaign_id == PACKET["campaign_id"]


def test_pointer_survives_graph_lens_campaign_switch_same_thread(tmp_path: Path) -> None:
    """Same Plan packet + thread keeps continuity when the graph lens changes.

    Ask under C2 lens, then C1-only on the same thread with the same opaque
    pointer — must accept, not hermes_session_pointer_rejected.
    """
    session_base = tmp_path / "live-session"
    packet = {"campaign_id": "longmont-c2", "session": 22}
    c2_envelope = {
        **READY_ENVELOPE,
        "campaign_id": "longmont-c2",
        "world_id": "eldyrwild",
        "revision_id": "revision:c2",
        "head_revision_id": "revision:c2",
    }
    c1_envelope = {
        **READY_ENVELOPE,
        "campaign_id": "longmont-c1",
        "world_id": "eldyrwild",
        "revision_id": "revision:c1",
        "head_revision_id": "revision:c1",
    }
    host = _FakeHost(_ok_result(hermes_session_id="hermes-internal-s1"))
    first = run_hermes_graph_query(
        text="Who is in campaign 2?",
        packet=packet,
        graph_envelope=c2_envelope,
        agent_thread_id="thread-lens",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = first["hermes_session"]["sessionId"]
    assert pointer.startswith("hptr-")
    host.calls.clear()
    host.result = _ok_result(hermes_session_id="hermes-internal-s1")
    second = run_hermes_graph_query(
        text="Now only campaign 1 memory.",
        packet=packet,
        graph_envelope=c1_envelope,
        agent_thread_id="thread-lens",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer=pointer,
        conversation_history=VALID_HISTORY,
    )
    assert len(host.calls) == 1
    assert host.calls[0].session_id == "hermes-internal-s1"
    assert second["hermes_session"]["sessionId"] == pointer
    ctx = second["agent_trace"]["conversation_context"]
    assert ctx["hermes_session_pointer_status"] == "accepted"
    from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore

    store = HermesSessionPointerStore(session_base)
    binding = store.get_for_thread(
        campaign_id="longmont-c2",
        agent_thread_id="thread-lens",
    )
    assert binding is not None
    assert binding.pointer_id == pointer
    assert binding.campaign_id == "longmont-c2"
    # Lens campaign must not become a separate continuity key.
    assert (
        store.get_for_thread(campaign_id="longmont-c1", agent_thread_id="thread-lens")
        is None
    )


def test_follow_up_accepts_bound_pointer_and_passes_continuity_session(
    tmp_path: Path,
) -> None:
    session_base = tmp_path / "live-session"
    host = _FakeHost(_ok_result(hermes_session_id="hermes-internal-s1"))
    first = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = first["hermes_session"]["sessionId"]
    host.calls.clear()
    host.result = _ok_result(hermes_session_id="hermes-internal-s1")
    second = run_hermes_graph_query(
        text="What is it connected to?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer=pointer,
        conversation_history=VALID_HISTORY,
    )
    assert len(host.calls) == 1
    assert host.calls[0].session_id == "hermes-internal-s1"
    assert host.calls[0].revision_pin == "revision:resolved-server"
    assert second["hermes_session"]["sessionId"] == pointer
    ctx = second["agent_trace"]["conversation_context"]
    assert ctx["hermes_session_pointer_in_request"] is True
    assert ctx["hermes_session_pointer_status"] == "accepted"
    assert ctx["fresh_graph_revision_used"] is True


def test_cross_thread_pointer_is_rejected(tmp_path: Path) -> None:
    session_base = tmp_path / "live-session"
    host = _FakeHost(_ok_result(hermes_session_id="hermes-internal-s1"))
    first = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = first["hermes_session"]["sessionId"]
    with pytest.raises(HermesGraphQueryRequestError) as exc:
        run_hermes_graph_query(
            text="Follow up?",
            packet=PACKET,
            graph_envelope=READY_ENVELOPE,
            agent_thread_id="thread-b",
            turn_id="turn-2",
            root=tmp_path,
            session_base=session_base,
            host_factory=lambda: host,  # type: ignore[arg-type, return-value]
            hermes_session_pointer=pointer,
        )
    assert exc.value.code == "hermes_session_pointer_rejected"


def test_unknown_pointer_recovers_with_fresh_session(tmp_path: Path) -> None:
    session_base = tmp_path / "live-session"
    host = _FakeHost(_ok_result(hermes_session_id="hermes-recovered"))
    response = run_hermes_graph_query(
        text="Follow up?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer="hptr-deadbeefdeadbeefdeadbeef",
    )
    assert host.calls[0].session_id is None
    ctx = response["agent_trace"]["conversation_context"]
    assert ctx["hermes_session_pointer_status"] == "recovered"
    assert response["hermes_session"]["sessionId"].startswith("hptr-")


def test_pointer_survives_store_reload_after_server_restart(tmp_path: Path) -> None:
    session_base = tmp_path / "live-session"
    host = _FakeHost(_ok_result(hermes_session_id="hermes-durable"))
    first = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = first["hermes_session"]["sessionId"]
    host.calls.clear()
    second = run_hermes_graph_query(
        text="Follow up?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer=pointer,
    )
    assert host.calls[0].session_id == "hermes-durable"
    assert second["hermes_session"]["sessionId"] == pointer


def test_pointer_trace_reports_worker_pid_change(tmp_path: Path) -> None:
    class _PidHost(_FakeHost):
        def __init__(self, result: HermesGraphAgentTurnResult, pid: int) -> None:
            super().__init__(result)
            self.pid = pid

        @property
        def worker_pid(self) -> int:
            return self.pid

    session_base = tmp_path / "live-session"
    host = _PidHost(_ok_result(hermes_session_id="hermes-worker-session"), pid=101)
    first = run_hermes_graph_query(
        text="Who is Tripod?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-1",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
    )
    pointer = first["hermes_session"]["sessionId"]

    host.pid = 202
    second = run_hermes_graph_query(
        text="Follow up?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer=pointer,
    )

    assert second["agent_trace"]["conversation_context"]["worker_pid_changed"] is True


def test_expired_binding_recovers_without_cross_thread_reuse(tmp_path: Path) -> None:
    from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore

    session_base = tmp_path / "live-session"
    store = HermesSessionPointerStore(session_base)
    binding = store.upsert_after_turn(
        campaign_id=str(READY_ENVELOPE["campaign_id"]),
        agent_thread_id="thread-a",
        hermes_session_id="hermes-expired",
    )
    payload = store._load_store()
    key = f"{READY_ENVELOPE['campaign_id']}::thread-a"
    payload["bindings"][key]["status"] = "expired"
    store._save_store(payload)

    host = _FakeHost(_ok_result(hermes_session_id="hermes-fresh"))
    response = run_hermes_graph_query(
        text="Follow up?",
        packet=PACKET,
        graph_envelope=READY_ENVELOPE,
        agent_thread_id="thread-a",
        turn_id="turn-2",
        root=tmp_path,
        session_base=session_base,
        host_factory=lambda: host,  # type: ignore[arg-type, return-value]
        hermes_session_pointer=binding.pointer_id,
    )
    assert host.calls[0].session_id is None
    assert response["agent_trace"]["conversation_context"]["hermes_session_pointer_status"] == "recovered"
    assert response["hermes_session"]["sessionId"] != binding.pointer_id


# --- CUTOVER R.3: Hermes graph tools execute on the direct read path --------


def test_hermes_expansion_tool_executes_via_direct_dungeonmind_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Hermes ``expand_graph_retrieval`` tool path dispatches to DungeonMind.

    The interaction executor calls the retrieval *service* with the production
    root; in ``dungeonmind`` authority mode that dispatch executes natively in
    DungeonMind. Kernel/hydration explosion stubs prove the legacy graph read
    machinery never runs.
    """
    import graph_memory.kernel as kernel

    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from graph_memory.interaction.expansion_executor import (
        execute_expand_graph_retrieval,
    )
    from graph_memory.interaction.initial_resolve import create_session_from_preflight
    from graph_memory.world_supergraph import storage
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        CAMPAIGN_ONE,
        NOW,
        _FakeBundle,
        _payload,
        _receipt,
        _seed_sources,
    )
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        WORLD_ID as DIRECT_WORLD_ID,
    )

    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=DIRECT_WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:hermes-r3"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(DIRECT_WORLD_ID, published.revision_id),
    )
    services = direct.direct_services_from_bundle(bundle, DIRECT_WORLD_ID)

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()
    monkeypatch.setattr(
        direct, "direct_services_from_config", lambda world_id: services
    )

    def _explode(*_args, **_kwargs):
        raise AssertionError("legacy kernel must not run on the direct read path")

    monkeypatch.setattr(kernel, "search_campaign_graph", _explode)
    monkeypatch.setattr(kernel, "get_campaign_object", _explode)
    monkeypatch.setattr(kernel, "get_object_neighborhood", _explode)
    monkeypatch.setattr(kernel, "get_object_evidence", _explode)
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )

    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)

    session = create_session_from_preflight(
        {
            "schema": "dmb_agent_world_graph_query_context_v1",
            "status": "ready",
            "world_id": DIRECT_WORLD_ID,
            "campaign_id": CAMPAIGN_ONE,
            "revision_id": published.revision_id,
            "is_head": True,
            "focus": {"kind": "none"},
            "admissibility": "gm",
            "query_text": "Where is the tavern?",
            "matched_node_ids": [],
            "nodes": [],
            "warning_codes": [],
        },
        question="Where is the tavern?",
    )
    result = execute_expand_graph_retrieval(
        {
            "operation": "search",
            "queryText": "tavern",
            "targets": [],
            "retrievalSessionId": session.id,
        }
    )
    assert result["schema"] == "dmb_world_graph_retrieval_result_v1"
    labels = [node["label"] for node in result["nodes"]]
    assert "The Prancing Tavern" in labels
