"""Owning tests for A7 Play current-moment SurfaceContext."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from apps.live_control_server.services.agent_play_surface_context import (
    PLAY_BEAT_BODY_MAX_CHARS,
    PLAY_MODEL_BLOCK_MAX_CHARS,
    PLAY_SCENE_BODY_MAX_CHARS,
    extract_v2_play_authored_slices,
    render_agent_play_surface_context,
    resolve_agent_play_surface_context,
)
from apps.live_control_server.services.agent_runtime import (
    AgentPlayCurrentElementContext,
    AgentPlayCurrentMomentContext,
    AgentSurfaceContext,
)
from apps.live_control_server.services.agent_surface_context import (
    SURFACE_CONTEXT_REQUEST_SCHEMA,
    SURFACE_SUMMARY_KEYS,
    AgentSurfaceContextRequest,
    render_agent_surface_context,
    resolve_agent_surface_context,
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
    WorkspaceDocumentRegistryError,
)
from tests.test_play_run_reference_manifest import C2S27_SHAPED_V2_MARKDOWN

RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DOC_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
SHA256 = "c" * 64
CAMPAIGN = "longmont-c2"
SECRET_BEAT_TITLE = "Hold the gate"
SECRET_SCENE_TITLE = "The gate line"
SECRET_BEAT_BODY = "Triage at the gate line while the refugee crush builds."
SECRET_SCENE_BODY = "Guards waver while Lysandro works the crowd."


def _play_request(**overrides: Any) -> AgentSurfaceContextRequest:
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
    return AgentSurfaceContextRequest.model_validate(payload)


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


def _manifest() -> Any:
    return derive_sealed_manifest(
        C2S27_SHAPED_V2_MARKDOWN,
        run_id=RUN_ID,
        playable_artifact_id=DOC_ID,
        playable_revision=1,
        playable_content_sha256=SHA256,
        sealed_at="2026-01-01T00:00:00Z",
    )


def _committed() -> WorkspaceCommittedRevision:
    return WorkspaceCommittedRevision(
        schema_version="dmb_workspace_committed_revision_v1",
        document_id=DOC_ID,
        kind="runbook",
        campaign_id=CAMPAIGN,
        title="Session 27 North Gate Runbook",
        status="active",
        object_revision=1,
        work_revision_id=str(uuid.uuid4()),
        revision_n=1,
        markdown=C2S27_SHAPED_V2_MARKDOWN,
        content_sha256=SHA256,
        has_divergent_working_copy=False,
        target_relpath="runbooks/session-27.md",
    )


def _assert_trace_privacy(summary: dict[str, Any], *secrets: str) -> None:
    blob = json.dumps(summary, sort_keys=True, default=str)
    for secret in secrets:
        assert secret not in blob
    assert set(summary) == SURFACE_SUMMARY_KEYS


def test_extract_v2_play_authored_slices_matches_c2s27_shape() -> None:
    slices = extract_v2_play_authored_slices(C2S27_SHAPED_V2_MARKDOWN)
    beat = slices["beat:hold-the-gate"]
    scene = slices["scene:gate-line"]
    assert beat.kind == "beat"
    assert beat.title == SECRET_BEAT_TITLE
    assert SECRET_BEAT_BODY in beat.body_text
    assert "Guards waver" not in beat.body_text
    assert scene.kind == "scene"
    assert scene.title == SECRET_SCENE_TITLE
    assert SECRET_SCENE_BODY in scene.body_text


def test_resolved_play_uses_server_metadata_not_client_prose(tmp_path: Path) -> None:
    record = _play_record()
    manifest = _manifest()
    committed = _committed()
    with (
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run",
            return_value=record,
        ) as mock_run,
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run_reference_manifest",
            return_value=manifest,
        ) as mock_manifest,
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            return_value=committed,
        ) as mock_revision,
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    mock_run.assert_called_once_with(tmp_path, RUN_ID)
    mock_manifest.assert_called_once_with(tmp_path, RUN_ID)
    mock_revision.assert_called_once_with(
        DOC_ID,
        revision_n=1,
        expected_sha256=SHA256,
        kind="runbook",
    )
    assert resolution.context is not None
    play = resolution.context.current_play
    assert play is not None
    assert play.run_id == RUN_ID
    assert play.current_beat.title == SECRET_BEAT_TITLE
    assert play.current_scene is not None
    assert play.current_scene.title == SECRET_SCENE_TITLE
    assert resolution.trace_summary["resolution_status"] == "resolved"
    rendered = render_agent_play_surface_context(resolution.context)
    assert rendered is not None
    assert SECRET_BEAT_TITLE in rendered
    assert SECRET_SCENE_TITLE in rendered
    assert SECRET_BEAT_BODY in rendered
    assert SECRET_SCENE_BODY in rendered
    assert RUN_ID not in rendered
    assert DOC_ID not in rendered
    assert "beat:hold-the-gate" not in rendered
    assert "scene:gate-line" not in rendered
    assert "Current phase of play (Beat)" in rendered
    assert "Current immediate table situation (Scene)" in rendered
    _assert_trace_privacy(dict(resolution.trace_summary), SECRET_BEAT_TITLE, RUN_ID)


def test_beat_only_render_omits_scene_line() -> None:
    context = AgentSurfaceContext(
        surface_id="play",
        current_play=AgentPlayCurrentMomentContext(
            run_id=RUN_ID,
            playable_artifact_id=DOC_ID,
            playable_revision=1,
            current_beat=AgentPlayCurrentElementContext(
                kind="beat",
                element_id="beat:hold-the-gate",
                title=SECRET_BEAT_TITLE,
                body_text=SECRET_BEAT_BODY,
            ),
            current_scene=None,
        ),
    )
    rendered = render_agent_play_surface_context(context)
    assert rendered is not None
    assert "Current immediate table situation" not in rendered
    assert SECRET_BEAT_TITLE in rendered


@pytest.mark.parametrize(
    ("overrides", "warning"),
    [
        ({"pointers": [{"kind": "playable_revision", "value": "1"}, {"kind": "current_beat", "value": "beat:hold-the-gate"}]}, "surface_context_rejected_surface"),
        ({"pointers": [{"kind": "play_run", "value": RUN_ID}, {"kind": "current_beat", "value": "beat:hold-the-gate"}]}, "surface_context_rejected_surface"),
        ({"pointers": [{"kind": "play_run", "value": RUN_ID}, {"kind": "playable_revision", "value": "1"}]}, "surface_context_rejected_surface"),
        (
            {
                "pointers": [
                    {"kind": "play_run", "value": RUN_ID},
                    {"kind": "playable_revision", "value": "1"},
                    {"kind": "current_beat", "value": "beat:hold-the-gate"},
                    {"kind": "current_beat", "value": "beat:other"},
                ]
            },
            "surface_context_rejected_surface",
        ),
        (
            {
                "pointers": [
                    {"kind": "play_run", "value": RUN_ID},
                    {"kind": "playable_revision", "value": "1"},
                    {"kind": "current_beat", "value": "beat:hold-the-gate"},
                    {"kind": "inspection", "value": "scene:other"},
                ]
            },
            "surface_context_rejected_surface",
        ),
        ({"pointers": [{"kind": "play_run", "value": "not-a-uuid"}, {"kind": "playable_revision", "value": "1"}, {"kind": "current_beat", "value": "beat:hold-the-gate"}]}, "surface_context_rejected_surface"),
        ({"pointers": [{"kind": "play_run", "value": RUN_ID}, {"kind": "playable_revision", "value": "0"}, {"kind": "current_beat", "value": "beat:hold-the-gate"}]}, "surface_context_rejected_surface"),
        ({"session_number": 27}, "surface_context_rejected_surface"),
    ],
)
def test_pointer_admission_rejects(tmp_path: Path, overrides: dict[str, Any], warning: str) -> None:
    resolution = resolve_agent_play_surface_context(
        _play_request(**overrides),
        root=tmp_path,
        outer_campaign_id=CAMPAIGN,
    )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_surface"
    assert warning in resolution.warning_codes


def test_stale_beat_witness_rejects_without_substitution(tmp_path: Path) -> None:
    record = _play_record(
        progress=PlayRunProgress(
            current_beat_id="beat:panic-breaks",
            current_scene_id=None,
            resolved_beat_ids=[],
            selections={},
            notes_by_element_id={},
        )
    )
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        return_value=record,
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(
                pointers=[
                    {"kind": "play_run", "value": RUN_ID},
                    {"kind": "playable_revision", "value": "1"},
                    {"kind": "current_beat", "value": "beat:hold-the-gate"},
                ],
                session_number=None,
            ),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert "surface_context_play_stale_beat" in resolution.warning_codes


def test_stale_scene_witness_rejects_when_authoritative_has_none(tmp_path: Path) -> None:
    record = _play_record(
        progress=PlayRunProgress(
            current_beat_id="beat:hold-the-gate",
            current_scene_id=None,
            resolved_beat_ids=[],
            selections={},
            notes_by_element_id={},
        )
    )
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        return_value=record,
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert "surface_context_play_stale_scene" in resolution.warning_codes


def test_stale_scene_witness_rejects_when_client_omits_but_run_has_scene(tmp_path: Path) -> None:
    record = _play_record()
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        return_value=record,
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(
                pointers=[
                    {"kind": "play_run", "value": RUN_ID},
                    {"kind": "playable_revision", "value": "1"},
                    {"kind": "current_beat", "value": "beat:hold-the-gate"},
                ]
            ),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert "surface_context_play_stale_scene" in resolution.warning_codes


def test_campaign_mismatch_rejects_scope(tmp_path: Path) -> None:
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        return_value=_play_record(campaign_id="other-campaign"),
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_scope"


def test_unavailable_when_run_missing(tmp_path: Path) -> None:
    with patch(
        "apps.live_control_server.services.agent_play_surface_context.get_play_run",
        side_effect=PlayRunRegistryError("missing", status_code=404),
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "unavailable"
    assert "surface_context_play_unavailable" in resolution.warning_codes


def test_unavailable_when_committed_revision_missing(tmp_path: Path) -> None:
    with (
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run",
            return_value=_play_record(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run_reference_manifest",
            return_value=_manifest(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            side_effect=WorkspaceDocumentRegistryError("missing", status_code=404),
        ),
    ):
        resolution = resolve_agent_play_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
        )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "unavailable"


def test_play_dispatch_through_generic_resolver(tmp_path: Path) -> None:
    with (
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run",
            return_value=_play_record(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_play_run_reference_manifest",
            return_value=_manifest(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            return_value=_committed(),
        ),
    ):
        resolution = resolve_agent_surface_context(
            _play_request(),
            root=tmp_path,
            outer_campaign_id=CAMPAIGN,
            outer_session=27,
        )
    assert resolution.trace_summary["resolution_status"] == "resolved"
    rendered = render_agent_surface_context(resolution.context)
    assert rendered is not None
    assert SECRET_BEAT_TITLE in rendered


def test_renderer_bounds_long_play_material() -> None:
    context = AgentSurfaceContext(
        surface_id="play",
        current_play=AgentPlayCurrentMomentContext(
            run_id=RUN_ID,
            playable_artifact_id=DOC_ID,
            playable_revision=1,
            current_beat=AgentPlayCurrentElementContext(
                kind="beat",
                element_id="beat:hold-the-gate",
                title="B" * 300,
                body_text="b" * 500,
            ),
            current_scene=AgentPlayCurrentElementContext(
                kind="scene",
                element_id="scene:gate-line",
                title="S" * 300,
                body_text="s" * 900,
            ),
        ),
    )
    rendered = render_agent_play_surface_context(context)
    assert rendered is not None
    assert len(rendered) <= PLAY_MODEL_BLOCK_MAX_CHARS
    assert "B" * 161 not in rendered
    assert "b" * (PLAY_BEAT_BODY_MAX_CHARS + 5) not in rendered
    assert "s" * (PLAY_SCENE_BODY_MAX_CHARS + 5) not in rendered
