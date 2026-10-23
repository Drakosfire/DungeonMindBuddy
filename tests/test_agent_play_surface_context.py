"""Owning tests for A7 Play current-moment SurfaceContext."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from apps.live_control_server.services.agent_play_surface_context import (
    PLAY_BEAT_BODY_MAX_CHARS,
    PLAY_MODEL_BLOCK_MAX_CHARS,
    PLAY_SCENE_BODY_MAX_CHARS,
    WorldPlaySurfaceContextError,
    extract_v2_play_authored_slices,
    render_agent_play_surface_context,
    resolve_agent_play_world_surface_context_v2,
    resolve_agent_play_surface_context,
    validate_agent_play_world_surface_context_v2,
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
    AgentWorldPlaySurfaceContextRequestV2,
    render_agent_surface_context,
    resolve_agent_surface_context,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    PlayRunRecord,
    PlayRunRegistryError,
    WorldPlayRunRecord,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    derive_sealed_manifest,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceCommittedRevision,
    WorkspaceDocumentRegistryError,
    WorldOwnedCommittedRevisionV2,
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


def _world_play_request(**overrides: Any) -> AgentWorldPlaySurfaceContextRequestV2:
    payload: dict[str, Any] = {
        "schema": "dmb_agent_world_play_surface_context_request_v2",
        "surface_id": "play",
        "world_id": "world-a",
        "run_id": RUN_ID,
        "run_revision": 7,
    }
    payload.update(overrides)
    return AgentWorldPlaySurfaceContextRequestV2.model_validate(payload)


def _world_play_record(**overrides: Any) -> WorldPlayRunRecord:
    payload: dict[str, Any] = {
        "schema_version": "dmb_world_play_run_record_v2",
        "run_id": RUN_ID,
        "world_id": "world-a",
        "playable_artifact_id": DOC_ID,
        "playable_revision": 1,
        "playable_work_revision_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "playable_content_sha256": SHA256,
        "run_revision": 7,
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
    return WorldPlayRunRecord.model_validate(payload)


def _world_committed(**overrides: Any) -> WorldOwnedCommittedRevisionV2:
    payload: dict[str, Any] = {
        "schema_version": "dmb_workspace_committed_revision_v2",
        "scope_mode": "world",
        "world_id": "world-a",
        "document_id": DOC_ID,
        "kind": "runbook",
        "campaign_id": None,
        "title": "World Play Runbook",
        "status": "active",
        "object_revision": 2,
        "work_revision_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "revision_n": 1,
        "markdown": C2S27_SHAPED_V2_MARKDOWN,
        "content_sha256": SHA256,
        "has_divergent_working_copy": False,
        "target_relpath": None,
    }
    payload.update(overrides)
    return WorldOwnedCommittedRevisionV2.model_validate(payload)


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


def test_extract_ends_beat_body_at_ordinary_unmarked_root_h2() -> None:
    """Parity with client slicePlayableBodies: unmarked root H2 must not bleed backward."""
    markdown = "\n".join(
        [
            "<!-- dmb-playable-element:v2 kind=beat id=beat:breach beat_kind=spine -->",
            "## Hold the Breach",
            "",
            "Beat-specific prose",
            "",
            "### GM Note",
            "",
            "Keep this unmarked H3 inside the Beat.",
            "",
            "## Open questions",
            "",
            "- Does Tealeaf answer?",
            "- How much wall falls?",
            "",
        ]
    )
    slices = extract_v2_play_authored_slices(markdown)
    beat = slices["beat:breach"]
    assert beat.title == "Hold the Breach"
    assert "Beat-specific prose" in beat.body_text
    assert "Keep this unmarked H3 inside the Beat." in beat.body_text
    assert "Open questions" not in beat.body_text
    assert "Does Tealeaf answer" not in beat.body_text
    assert "open-questions" not in slices


def test_extract_ends_scene_body_at_ordinary_unmarked_root_h1() -> None:
    markdown = "\n".join(
        [
            "<!-- dmb-playable-element:v2 kind=beat id=beat:breach beat_kind=spine -->",
            "## Hold the Breach",
            "",
            "Beat intro.",
            "",
            "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
            "### North Gate",
            "",
            "Scene-specific prose.",
            "",
            "# Appendix",
            "",
            "Later runbook appendix must not enter Scene body.",
            "",
        ]
    )
    slices = extract_v2_play_authored_slices(markdown)
    scene = slices["scene:north-gate"]
    assert "Scene-specific prose." in scene.body_text
    assert "Appendix" not in scene.body_text
    assert "Later runbook appendix" not in scene.body_text
    beat = slices["beat:breach"]
    assert "Scene-specific prose." not in beat.body_text
    assert "Appendix" not in beat.body_text


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


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_world_play_context_v2_resolves_exact_world_run_revision_and_pin(
    tmp_path: Path, kind: str,
) -> None:
    record = _world_play_record()
    committed = _world_committed(kind=kind)
    with (
        patch(
            "apps.live_control_server.services.world_container_registry.get_world_container",
            return_value=SimpleNamespace(world_id="world-a", name="World A"),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run",
            return_value=record,
        ) as get_run,
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            return_value=committed,
        ) as get_revision,
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run_reference_manifest",
            return_value=_manifest(),
        ),
    ):
        resolution = resolve_agent_play_world_surface_context_v2(
            _world_play_request(),
            root=tmp_path,
            outer_world_id="world-a",
        )

    assert resolution.context is not None
    assert resolution.trace_summary["resolution_status"] == "resolved"
    assert resolution.context.current_owner is not None
    assert resolution.context.current_owner.owner_id == "world-a"
    assert resolution.context.current_play is not None
    assert resolution.context.current_play.run_id == RUN_ID
    assert resolution.context.current_play.current_beat.element_id == "beat:hold-the-gate"
    assert resolution.context.current_play.current_scene is not None
    assert resolution.context.current_play.current_scene.element_id == "scene:gate-line"
    rendered = render_agent_surface_context(resolution.context)
    assert rendered is not None and "Current World: \"World A\"" in rendered
    get_run.assert_called_once_with(tmp_path, world_id="world-a", run_id=RUN_ID)
    get_revision.assert_called_once_with(
        DOC_ID,
        revision_n=1,
        expected_sha256=SHA256,
        kind=None,
        expected_world_id="world-a",
    )


def test_world_play_context_v2_rejects_stale_run_revision_and_pin_mismatch(
    tmp_path: Path,
) -> None:
    with (
        patch(
            "apps.live_control_server.services.world_container_registry.get_world_container",
            return_value=SimpleNamespace(world_id="world-a", name="World A"),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run",
            return_value=_world_play_record(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            return_value=_world_committed(
                work_revision_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd"
            ),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run_reference_manifest",
            return_value=_manifest(),
        ),
    ):
        with pytest.raises(WorldPlaySurfaceContextError, match="run_revision is stale"):
            validate_agent_play_world_surface_context_v2(
                _world_play_request(run_revision=6),
                root=tmp_path,
                outer_world_id="world-a",
            )

        resolution = resolve_agent_play_world_surface_context_v2(
            _world_play_request(),
            root=tmp_path,
            outer_world_id="world-a",
        )

    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_surface"


@pytest.mark.parametrize(
    "committed_overrides",
    [
        {"document_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd"},
        {"revision_n": 2},
        {"content_sha256": "f" * 64},
        {"work_revision_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd"},
        {"world_id": "world-b"},
    ],
    ids=("artifact", "revision", "sha", "work_revision", "world"),
)
def test_world_play_context_v2_rejects_each_committed_pin_mismatch(
    tmp_path: Path,
    committed_overrides: dict[str, Any],
) -> None:
    with (
        patch(
            "apps.live_control_server.services.world_container_registry.get_world_container",
            return_value=SimpleNamespace(world_id="world-a", name="World A"),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run",
            return_value=_world_play_record(),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision",
            return_value=_world_committed(**committed_overrides),
        ),
    ):
        with pytest.raises(WorldPlaySurfaceContextError, match="exact pin"):
            validate_agent_play_world_surface_context_v2(
                _world_play_request(), root=tmp_path, outer_world_id="world-a"
            )


def test_world_play_context_v2_rejects_campaign_run_even_when_ids_match(
    tmp_path: Path,
) -> None:
    with (
        patch(
            "apps.live_control_server.services.world_container_registry.get_world_container",
            return_value=SimpleNamespace(world_id="world-a", name="World A"),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run",
            side_effect=PlayRunRegistryError("World Play Run not found", status_code=404),
        ) as get_run,
    ):
        with pytest.raises(WorldPlaySurfaceContextError):
            validate_agent_play_world_surface_context_v2(
                _world_play_request(), root=tmp_path, outer_world_id="world-a"
            )
    get_run.assert_called_once_with(tmp_path, world_id="world-a", run_id=RUN_ID)


def _create_real_world_play_context(root: Path, *, kind: str = "plan", historical_session=False):
    """Use real Content/Run producers; no mocked pin or manifest."""
    from application_state.content.service import (
        commit_plan, commit_runbook, create_world_plan, create_world_runbook,
    )
    from apps.live_control_server.services.world_container_registry import create_world_container
    from apps.live_control_server.services.play_run_registry import (
        create_or_replay_world_play_run, replace_world_play_run_progress,
    )

    world = create_world_container(root, name="Agent pin test")
    create = create_world_plan if kind == "plan" else create_world_runbook
    commit = commit_plan if kind == "plan" else commit_runbook
    obj = create(title="Pinned opening", world_id=world.world_id)
    obj, revision = commit(str(obj.work_object_id), C2S27_SHAPED_V2_MARKDOWN,
                           expected_revision=obj.object_revision)
    from tests.application_state.session_encounter_helpers import session_request
    from apps.live_control_server.services.play_run_registry import WorldPlayRunRecord
    if historical_session:
        from tests.application_state.session_encounter_helpers import historical_world_run
        from apps.live_control_server.services.play_run_registry import _world_record_from_aggregate
        run=_world_record_from_aggregate(historical_world_run(world_id=world.world_id,run_id=str(uuid.uuid4()),playable_artifact_id=obj.work_object_id,expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256))
    else:
        created = create_or_replay_world_play_run(
            root, world_id=world.world_id, run_id=str(uuid.uuid4()),
            request=session_request(world_id=world.world_id,playable_artifact_id=obj.work_object_id,
                expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256),
        )
        run=WorldPlayRunRecord.model_validate(created['run'])
    run = replace_world_play_run_progress(
        root, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision,
        progress=PlayRunProgress(current_beat_id="beat:hold-the-gate",
                                 current_scene_id="scene:gate-line",
                                 resolved_beat_ids=[], selections={}, notes_by_element_id={}),
    )
    return world, obj, revision, run


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_real_world_play_pin_survives_plan_edits_and_run_progress(
    tmp_path: Path, application_state_dsn: str, kind: str,
) -> None:
    from application_state.content.service import (
        commit_plan, commit_runbook, update_plan_metadata, update_runbook_metadata,
    )
    from apps.live_control_server.services.agent_play_surface_context import (
        resolve_world_play_turn_snapshot, resolve_historical_world_play_turn_snapshot,
    )
    from apps.live_control_server.services.play_run_registry import replace_world_play_run_progress

    assert application_state_dsn
    world, obj, revision, run = _create_real_world_play_context(tmp_path, kind=kind)
    args = dict(root=tmp_path, world_id=world.world_id, run_id=run.run_id,
                run_revision=run.run_revision)
    original, receipt = resolve_world_play_turn_snapshot(**args)
    request = _world_play_request(world_id=world.world_id, run_id=run.run_id,
                                  run_revision=run.run_revision)
    assert resolve_agent_play_world_surface_context_v2(
        request, root=tmp_path, outer_world_id=world.world_id,
    ).context == original
    assert receipt.runbook_work_revision_id == revision.work_revision_id
    frozen = receipt.model_dump(mode="json")
    metadata = update_plan_metadata if kind == "plan" else update_runbook_metadata
    commit = commit_plan if kind == "plan" else commit_runbook
    obj = metadata(str(obj.work_object_id), title="Later title", expected_revision=obj.object_revision)
    assert resolve_historical_world_play_turn_snapshot(
        root=tmp_path, world_id=world.world_id, receipt=receipt,
    ) == original
    obj, _ = commit(str(obj.work_object_id), C2S27_SHAPED_V2_MARKDOWN + "\nLATER BODY MARKER\n",
                    expected_revision=obj.object_revision)
    current, new_receipt = resolve_world_play_turn_snapshot(**args)
    assert current.current_play == original.current_play
    assert new_receipt.runbook_work_revision_id == receipt.runbook_work_revision_id
    assert new_receipt.runbook_content_sha256 == receipt.runbook_content_sha256
    assert new_receipt.runbook_object_revision > receipt.runbook_object_revision
    replace_world_play_run_progress(
        tmp_path, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision,
        progress=run.progress.model_copy(update={"current_scene_id": None}),
    )
    with pytest.raises(WorldPlaySurfaceContextError, match="run_revision is stale"):
        resolve_world_play_turn_snapshot(**args)
    historical = resolve_historical_world_play_turn_snapshot(
        root=tmp_path, world_id=world.world_id, receipt=receipt,
    )
    assert historical == original
    assert "LATER BODY MARKER" not in render_agent_surface_context(historical)
    assert receipt.model_dump(mode="json") == frozen
    from apps.live_control_server.services.world_container_registry import WorldContainerRegistryError
    with pytest.raises((WorldPlaySurfaceContextError, WorldContainerRegistryError)):
        resolve_historical_world_play_turn_snapshot(
            root=tmp_path, world_id="foreign-world", receipt=receipt,
        )
    for key, value in (("runbook_work_revision_id", uuid.uuid4()),
                       ("runbook_content_sha256", "f" * 64),
                       ("runbook_revision_n", 999)):
        with pytest.raises((WorldPlaySurfaceContextError, WorkspaceDocumentRegistryError)):
            resolve_historical_world_play_turn_snapshot(
                root=tmp_path, world_id=world.world_id,
                receipt=receipt.model_copy(update={key: value}),
            )


def test_saved_session_turn_admits_exact_edition_and_scene_note_then_reconstructs_history(
    tmp_path: Path, application_state_dsn: str,
) -> None:
    from application_state.agent_conversation.types import PlayContentBasis
    from application_state.play.edition_service import commit_content, read_content
    from application_state.play.edition_types import ContentCommit
    from apps.live_control_server.services.agent_play_surface_context import (
        resolve_world_play_session_turn_snapshot,
        resolve_historical_world_play_turn_snapshot,
    )
    from apps.live_control_server.services.play_run_registry import replace_world_play_run_progress

    assert application_state_dsn
    world, _obj, _revision, run = _create_real_world_play_context(tmp_path)
    with_note = run.progress.model_copy(update={
        "notes_by_element_id": {"scene:gate-line": "The eastern lantern is dark."},
    })
    run = replace_world_play_run_progress(
        tmp_path, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision, progress=with_note,
    )
    current = read_content(run_id=run.run_id, world_id=world.world_id)
    edited_markdown = current.markdown.replace(
        "Guards waver while Lysandro works the crowd.",
        "Guards waver while Lysandro works the crowd.\n\n![Gate lantern](media:gate-lantern.png)\n\n```text\nKeep this fenced clue.\n```",
    )
    accepted = commit_content(
        run_id=run.run_id, world_id=world.world_id, command_id=str(uuid.uuid4()),
        request=ContentCommit(
            schema_version="dmb_world_play_run_content_commit_v1",
            expected_origin=current.origin,
            expected_edition_revision=current.edition_revision,
            expected_content_sha256=current.content_sha256,
            markdown=edited_markdown,
        ),
    )
    basis = PlayContentBasis(
        edition_revision=accepted.accepted_edition_revision,
        edition_revision_id=accepted.accepted_edition_revision_id,
        content_sha256=accepted.accepted_content_sha256,
    )
    with pytest.raises(WorldPlaySurfaceContextError, match="Run revision is stale"):
        resolve_world_play_session_turn_snapshot(
            root=tmp_path, world_id=world.world_id, run_id=run.run_id,
            run_revision=run.run_revision + 1, content_basis=basis,
        )
    context, receipt = resolve_world_play_session_turn_snapshot(
        root=tmp_path, world_id=world.world_id, run_id=run.run_id,
        run_revision=run.run_revision, content_basis=basis,
    )
    rendered = render_agent_play_surface_context(context)
    assert rendered is not None
    assert "![Gate lantern](media:gate-lantern.png)" in rendered
    assert "Keep this fenced clue." in rendered
    assert "The eastern lantern is dark." in rendered
    assert receipt.scene_note == "The eastern lantern is dark."
    provider_context = render_agent_surface_context(context)
    assert "Who gets through first?" in provider_context
    assert "Prioritize the cure line" in provider_context
    assert "Keep families together" in provider_context
    assert "choice:who-gets-through" in provider_context
    assert "The line surges against the wagons." not in provider_context

    latest = read_content(run_id=run.run_id, world_id=world.world_id)
    revised = commit_content(
        run_id=run.run_id, world_id=world.world_id, command_id=str(uuid.uuid4()),
        request=ContentCommit(
            schema_version="dmb_world_play_run_content_commit_v1",
            expected_origin=latest.origin,
            expected_edition_revision=latest.edition_revision,
            expected_content_sha256=latest.content_sha256,
            markdown=latest.markdown.replace("Keep this fenced clue.", "Changed clue."),
        ),
    )
    with pytest.raises(WorldPlaySurfaceContextError, match="session copy changed"):
        resolve_world_play_session_turn_snapshot(
            root=tmp_path, world_id=world.world_id, run_id=run.run_id,
            run_revision=run.run_revision, content_basis=basis,
        )
    changed = replace_world_play_run_progress(
        tmp_path, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision,
        progress=run.progress.model_copy(update={
            "notes_by_element_id": {"scene:gate-line": "A later note."},
        }),
    )
    historical = resolve_historical_world_play_turn_snapshot(
        root=tmp_path, world_id=world.world_id, receipt=receipt,
    )
    historical_render = render_agent_play_surface_context(historical)
    assert historical_render is not None
    assert "Keep this fenced clue." in historical_render
    assert "Changed clue." not in historical_render
    assert "The eastern lantern is dark." in historical_render
    assert "A later note." not in historical_render
    assert changed.run_revision > run.run_revision
    assert revised.accepted_edition_revision > receipt.edition_revision


def test_session_context_utf8_budget_rejects_instead_of_clipping() -> None:
    from apps.live_control_server.services.agent_play_surface_context import (
        WorldPlaySurfaceContextError,
    )

    context = AgentSurfaceContext(
        surface_id="play",
        current_play=AgentPlayCurrentMomentContext(
            run_id=RUN_ID,
            playable_artifact_id=DOC_ID,
            playable_revision=1,
            current_beat=AgentPlayCurrentElementContext(
                kind="beat", element_id="beat:hold-the-gate", title="Gate",
                body_text="", body_markdown="🧙" * 17_000,
            ),
            edition_revision=1,
        ),
    )
    with pytest.raises(WorldPlaySurfaceContextError, match="64 KiB UTF8"):
        render_agent_play_surface_context(context)


def test_revision_zero_history_uses_original_pin_after_run_rebase(
    tmp_path: Path, application_state_dsn: str,
) -> None:
    from application_state.agent_conversation.types import PlayContentBasis
    from application_state.content.service import commit_runbook
    from application_state.play.edition_service import read_content
    from apps.live_control_server.services.agent_play_surface_context import (
        resolve_world_play_session_turn_snapshot,
        resolve_historical_world_play_turn_snapshot,
    )
    from apps.live_control_server.services.play_run_registry import replace_world_play_run_progress
    from apps.live_control_server.services.play_run_rebase import rebase_or_replay_world_play_run

    assert application_state_dsn
    world, obj, _revision, run = _create_real_world_play_context(tmp_path, kind="runbook", historical_session=True)
    run = replace_world_play_run_progress(
        tmp_path, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision,
        progress=run.progress.model_copy(update={
            "notes_by_element_id": {"scene:gate-line": "Note before the first edit."},
        }),
    )
    pinned = read_content(run_id=run.run_id, world_id=world.world_id)
    context, receipt = resolve_world_play_session_turn_snapshot(
        root=tmp_path, world_id=world.world_id, run_id=run.run_id,
        run_revision=run.run_revision,
        content_basis=PlayContentBasis(
            edition_revision=0, edition_revision_id=None,
            content_sha256=pinned.content_sha256,
        ),
    )
    assert context.current_play is not None

    _updated, revision = commit_runbook(
        str(obj.work_object_id),
        C2S27_SHAPED_V2_MARKDOWN.replace(
            "Guards waver while Lysandro works the crowd.",
            "The newly committed Plan has different guard details.",
        ),
        expected_revision=obj.object_revision,
    )
    rebased = rebase_or_replay_world_play_run(
        tmp_path, world_id=world.world_id, run_id=run.run_id,
        expected_run_revision=run.run_revision,
        target_playable_revision=revision.revision_n,
        target_playable_content_sha256=revision.content_sha256,
    )
    assert rebased.run_revision > run.run_revision
    with (
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run",
            side_effect=AssertionError("revision-zero history must not read current Run"),
        ),
        patch(
            "apps.live_control_server.services.agent_play_surface_context.get_world_play_run_reference_manifest",
            side_effect=AssertionError("revision-zero history must not read current manifest"),
        ),
    ):
        historical = resolve_historical_world_play_turn_snapshot(
            root=tmp_path, world_id=world.world_id, receipt=receipt,
        )
    rendered = render_agent_play_surface_context(historical)
    assert rendered is not None
    assert "Guards waver while Lysandro works the crowd." in rendered
    assert "newly committed Plan" not in rendered
    assert "Note before the first edit." in rendered


@pytest.mark.parametrize("failure", ["kind", "manifest", "scene_parent"])
def test_world_play_context_rejects_unsupported_kind_or_broken_membership(tmp_path, failure):
    committed = _world_committed().model_copy(update={"kind": "worldbuilding_source"}) if failure == "kind" else _world_committed()
    record = _world_play_record()
    if failure == "scene_parent":
        record = record.model_copy(update={"progress": record.progress.model_copy(
            update={"current_scene_id": "scene:not-in-this-beat"})})
    with (
        patch("apps.live_control_server.services.world_container_registry.get_world_container",
              return_value=SimpleNamespace(world_id="world-a", name="World A")),
        patch("apps.live_control_server.services.agent_play_surface_context.get_world_play_run", return_value=record),
        patch("apps.live_control_server.services.agent_play_surface_context.get_committed_playable_revision", return_value=committed),
        patch("apps.live_control_server.services.agent_play_surface_context.get_world_play_run_reference_manifest",
              return_value=None if failure == "manifest" else _manifest()),
    ):
        with pytest.raises(WorldPlaySurfaceContextError):
            validate_agent_play_world_surface_context_v2(
                _world_play_request(), root=tmp_path, outer_world_id="world-a",
            )
