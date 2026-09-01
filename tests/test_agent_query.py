"""A8: shared Agent query service and POST /api/agent/query."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.live_control_server.main import create_app
from apps.live_control_server.services.agent_play_surface_context import (
    resolve_agent_play_query_scope,
)
from apps.live_control_server.services.agent_query import (
    AGENT_QUERY_REQUEST_SCHEMA,
    AgentQueryRequest,
    AgentQueryRequestError,
    process_agent_query,
)
from apps.live_control_server.services.agent_runtime import (
    HERMES_RUNTIME_DESCRIPTOR,
    AgentRuntimeInvocation,
    AgentRuntimeResult,
)
from apps.live_control_server.services.agent_surface_context import (
    SURFACE_CONTEXT_REQUEST_SCHEMA,
    AgentSurfaceContextRequest,
)
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRecord,
    PlayRunRegistryError,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    derive_sealed_manifest,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceCommittedRevision,
)
from tests.test_live_query_hermes_graph import (
    READY_ENVELOPE,
    _ok_result,
)
from tests.test_play_run_reference_manifest import C2S27_SHAPED_V2_MARKDOWN

RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DOC_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
SHA256 = "c" * 64
CAMPAIGN = "longmont-c2"
QUESTION = "What does Lysandra know about the swarm?"


def _play_surface(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": SURFACE_CONTEXT_REQUEST_SCHEMA,
        "surface_id": "play",
        "campaign_id": CAMPAIGN,
        "document_id": DOC_ID,
        "session_number": None,
        "pointers": [
            {"kind": "play_run", "value": RUN_ID},
            {"kind": "playable_revision", "value": "1"},
            {"kind": "current_beat", "value": "beat:hold-the-gate"},
            {"kind": "current_scene", "value": "scene:gate-line"},
        ],
    }
    payload.update(overrides)
    return payload


def _world_context(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": "dmb_agent_world_graph_query_context_request_v1",
        "world_id": "eldyrwild",
        "campaign_id": CAMPAIGN,
        "scope_mode": "campaign",
        "focus": {"kind": "none", "session_id": None, "campaign_id": None},
        "admissibility": "gm",
        "revision_pin": None,
    }
    payload.update(overrides)
    return payload


def _agent_request(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": AGENT_QUERY_REQUEST_SCHEMA,
        "text": QUESTION,
        "agent_thread_id": "agent-thread-test",
        "hermes_session_pointer": None,
        "trace_requested": True,
        "world_graph_context": _world_context(),
        "conversation_history": None,
        "surface_context": _play_surface(),
    }
    payload.update(overrides)
    return payload


def _play_record(**overrides: Any) -> PlayRunRecord:
    payload: dict[str, Any] = {
        "schema_version": "dmb_play_run_record_v1",
        "run_id": RUN_ID,
        "campaign_id": CAMPAIGN,
        "playable_artifact_id": DOC_ID,
        "playable_revision": 1,
        "playable_content_sha256": SHA256,
        "run_revision": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "progress": PlayRunProgress(
            current_beat_id="beat:hold-the-gate",
            current_scene_id="scene:gate-line",
            resolved_beat_ids=[],
            selections={},
            notes_by_element_id={},
        ),
        "rebased_from_run_revision": None,
    }
    payload.update(overrides)
    return PlayRunRecord.model_validate(payload)


def _install_play_fixtures(monkeypatch: pytest.MonkeyPatch) -> None:
    record = _play_record()
    manifest = derive_sealed_manifest(
        C2S27_SHAPED_V2_MARKDOWN,
        run_id=RUN_ID,
        playable_artifact_id=DOC_ID,
        playable_revision=1,
        playable_content_sha256=SHA256,
        sealed_at="2026-01-01T00:00:00Z",
    )
    committed = WorkspaceCommittedRevision(
        schema_version="dmb_workspace_committed_revision_v1",
        document_id=DOC_ID,
        kind="runbook",
        campaign_id=CAMPAIGN,
        title="Session 27 North Gate Runbook",
        status="active",
        object_revision=1,
        work_revision_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        revision_n=1,
        markdown=C2S27_SHAPED_V2_MARKDOWN,
        content_sha256=SHA256,
        has_divergent_working_copy=False,
        target_relpath="runbooks/session-27.md",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        lambda *_a, **_k: record,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run_reference_manifest",
        lambda *_a, **_k: manifest,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
        lambda *_a, **_k: committed,
    )


def test_agent_query_request_rejects_missing_schema() -> None:
    with pytest.raises(ValidationError):
        AgentQueryRequest.model_validate({"text": QUESTION})


def test_agent_query_request_rejects_forbidden_top_level_fields() -> None:
    payload = _agent_request()
    payload["campaign_id"] = CAMPAIGN
    with pytest.raises(ValidationError):
        AgentQueryRequest.model_validate(payload)


def test_agent_query_request_rejects_non_play_surface() -> None:
    with pytest.raises(AgentQueryRequestError) as exc:
        process_agent_query(
            QUESTION,
            world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
                _world_context()
            ),
            surface_context=AgentSurfaceContextRequest.model_validate(
                _play_surface(surface_id="plan", session_number=22, pointers=[])
            ),
        )
    assert exc.value.code == "agent_query_surface_not_supported"


def test_resolve_play_query_scope_rejects_missing_play_run(tmp_path: Path) -> None:
    request = AgentSurfaceContextRequest.model_validate(
        _play_surface(
            pointers=[
                {"kind": "playable_revision", "value": "1"},
                {"kind": "current_beat", "value": "beat:hold-the-gate"},
            ]
        )
    )
    with pytest.raises(Exception) as exc:
        resolve_agent_play_query_scope(request, root=tmp_path)
    assert "play_run" in str(exc.value).lower()


def test_resolve_play_query_scope_rejects_malformed_run_id(tmp_path: Path) -> None:
    request = AgentSurfaceContextRequest.model_validate(
        _play_surface(
            pointers=[
                {"kind": "play_run", "value": "not-a-uuid"},
                {"kind": "playable_revision", "value": "1"},
                {"kind": "current_beat", "value": "beat:hold-the-gate"},
            ]
        )
    )
    with pytest.raises(Exception):
        resolve_agent_play_query_scope(request, root=tmp_path)


def test_resolve_play_query_scope_rejects_unavailable_run(tmp_path: Path) -> None:
    request = AgentSurfaceContextRequest.model_validate(_play_surface())
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        side_effect=PlayRunRegistryError("missing"),
    ):
        with pytest.raises(Exception) as exc:
            resolve_agent_play_query_scope(request, root=tmp_path)
    assert "unavailable" in str(exc.value).lower()


def test_resolve_play_query_scope_derives_campaign_from_run(tmp_path: Path) -> None:
    request = AgentSurfaceContextRequest.model_validate(_play_surface())
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        return_value=_play_record(),
    ):
        scope = resolve_agent_play_query_scope(request, root=tmp_path)
    assert scope.run_id == RUN_ID
    assert scope.campaign_id == CAMPAIGN


def test_agent_query_rejects_world_campaign_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_play_fixtures(monkeypatch)
    with pytest.raises(AgentQueryRequestError) as exc:
        process_agent_query(
            QUESTION,
            root=tmp_path,
            world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
                _world_context(campaign_id="other-campaign")
            ),
            surface_context=AgentSurfaceContextRequest.model_validate(_play_surface()),
        )
    assert exc.value.code == "agent_query_world_campaign_mismatch"


def test_agent_query_stale_surface_still_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_play_fixtures(monkeypatch)
    captured: list[AgentRuntimeInvocation] = []

    def fake_resolve(*_a: Any, **kwargs: Any) -> dict[str, Any]:
        return {**READY_ENVELOPE, "query_text": kwargs["outer_text"]}

    class _CaptureRuntime:
        descriptor = HERMES_RUNTIME_DESCRIPTOR

        def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
            captured.append(invocation)
            return _ok_result()

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.resolve_agent_world_graph_query_context",
        fake_resolve,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.world_graph_root",
        lambda: tmp_path,
    )

    stale_surface = AgentSurfaceContextRequest.model_validate(
        _play_surface(
            pointers=[
                {"kind": "play_run", "value": RUN_ID},
                {"kind": "playable_revision", "value": "1"},
                {"kind": "current_beat", "value": "beat:hold-the-gate"},
                {"kind": "current_scene", "value": "scene:the-crush"},
            ]
        )
    )
    response = process_agent_query(
        QUESTION,
        root=tmp_path,
        world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
            _world_context()
        ),
        surface_context=stale_surface,
        agent_runtime=_CaptureRuntime(),  # type: ignore[arg-type]
    )
    assert captured
    assert response["status"] == "ok"
    assert response["events_written"] == []
    assert response["jobs_queued"] == []
    assert response["mutations"] == []
    assert "session" not in response
    trace = response["agent_trace"]
    surface_span = next(
        span for span in trace["spans"] if span["name"] == "surface_context_resolution"
    )
    assert surface_span["attributes"]["resolution_status"] == "rejected_surface"


def test_agent_query_query_primacy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_play_fixtures(monkeypatch)
    captured_outer: list[str] = []
    captured_invocations: list[AgentRuntimeInvocation] = []

    def fake_resolve(*_a: Any, **kwargs: Any) -> dict[str, Any]:
        captured_outer.append(kwargs["outer_text"])
        return {**READY_ENVELOPE, "query_text": kwargs["outer_text"]}

    class _CaptureRuntime:
        descriptor = HERMES_RUNTIME_DESCRIPTOR

        def run(self, invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
            captured_invocations.append(invocation)
            return _ok_result()

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.resolve_agent_world_graph_query_context",
        fake_resolve,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.world_graph_root",
        lambda: tmp_path,
    )

    process_agent_query(
        QUESTION,
        root=tmp_path,
        world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
            _world_context()
        ),
        surface_context=AgentSurfaceContextRequest.model_validate(_play_surface()),
        agent_runtime=_CaptureRuntime(),  # type: ignore[arg-type]
    )

    assert captured_outer == [QUESTION]
    assert len(captured_invocations) == 1
    invocation = captured_invocations[0]
    assert invocation.message == QUESTION
    retrieval = invocation.context_packet.retrieval_session
    assert retrieval is not None
    assert retrieval.packet["question"] == QUESTION


def test_agent_query_response_omits_session_and_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_play_fixtures(monkeypatch)

    class _CaptureRuntime:
        descriptor = HERMES_RUNTIME_DESCRIPTOR

        def run(self, _invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
            return _ok_result()

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.resolve_agent_world_graph_query_context",
        lambda *_a, **kwargs: {
            **READY_ENVELOPE,
            "query_text": kwargs["outer_text"],
        },
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.world_graph_root",
        lambda: tmp_path,
    )

    response = process_agent_query(
        QUESTION,
        root=tmp_path,
        world_graph_context=AgentWorldGraphQueryContextRequest.model_validate(
            _world_context()
        ),
        surface_context=AgentSurfaceContextRequest.model_validate(_play_surface()),
        agent_runtime=_CaptureRuntime(),  # type: ignore[arg-type]
    )
    assert "session" not in response
    assert response["events_written"] == []
    assert response["jobs_queued"] == []
    assert response["mutations"] == []


def test_post_agent_query_http_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_play_fixtures(monkeypatch)

    class _CaptureRuntime:
        descriptor = HERMES_RUNTIME_DESCRIPTOR

        def run(self, _invocation: AgentRuntimeInvocation) -> AgentRuntimeResult:
            return _ok_result()

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.resolve_agent_world_graph_query_context",
        lambda *_a, **kwargs: {
            **READY_ENVELOPE,
            "query_text": kwargs["outer_text"],
        },
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_query.world_graph_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.hermes_agent_runtime.default_hermes_agent_runtime",
        lambda: _CaptureRuntime(),
    )

    client = TestClient(create_app())
    response = client.post("/api/agent/query", json=_agent_request())
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hermes_graph_agent"
    assert "session" not in body
    assert body["events_written"] == []
    assert body["jobs_queued"] == []
    assert body["mutations"] == []
