"""Owning tests for A6 SurfaceContext resolver and renderer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.agent_runtime import (
    AgentCurrentWorkContext,
    AgentSurfaceContext,
)
from apps.live_control_server.services.agent_surface_context import (
    MODEL_BLOCK_MAX_CHARS,
    SURFACE_CONTEXT_REQUEST_SCHEMA,
    SURFACE_CONTEXT_SUMMARY_SCHEMA,
    SURFACE_SUMMARY_KEYS,
    TITLE_MODEL_MAX_CHARS,
    AgentSurfaceContextRequest,
    render_agent_surface_context,
    resolve_agent_surface_context,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
)

SECRET_TITLE = "SECRET-PLAN-TITLE-a6-privacy-9f3c"
SECRET_DOC_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SECRET_CAMPAIGN = "secret-campaign-a6"


def _request(**overrides: Any) -> AgentSurfaceContextRequest:
    payload: dict[str, Any] = {
        "schema": SURFACE_CONTEXT_REQUEST_SCHEMA,
        "surface_id": "plan",
        "campaign_id": "longmont-c2",
        "document_id": SECRET_DOC_ID,
        "session_number": 27,
        "pointers": [],
    }
    payload.update(overrides)
    return AgentSurfaceContextRequest.model_validate(payload)


def _plan_record(**overrides: Any) -> WorkspaceDocumentRecord:
    payload: dict[str, Any] = {
        "document_id": SECRET_DOC_ID,
        "title": SECRET_TITLE,
        "campaign_id": "longmont-c2",
        "kind": "plan",
        "status": "active",
        "revision": 3,
        "target_session": 27,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return WorkspaceDocumentRecord.model_validate(payload)


def _assert_trace_privacy(summary: dict[str, Any], *secrets: str) -> None:
    blob = json.dumps(summary, sort_keys=True, default=str)
    for secret in secrets:
        assert secret not in blob
    assert set(summary) == SURFACE_SUMMARY_KEYS
    assert summary["surface_context_schema"] == SURFACE_CONTEXT_SUMMARY_SCHEMA
    for value in summary.values():
        assert value is None or isinstance(value, (str, int, bool))


def test_absent_request_emits_no_model_block(tmp_path: Path) -> None:
    resolution = resolve_agent_surface_context(
        None,
        root=tmp_path,
        outer_campaign_id="longmont-c2",
        outer_session=27,
    )
    assert resolution.context is None
    assert resolution.warning_codes == ()
    assert resolution.trace_summary["resolution_status"] == "absent"
    assert resolution.trace_summary["request_present"] is False
    assert render_agent_surface_context(resolution.context) is None
    _assert_trace_privacy(dict(resolution.trace_summary), SECRET_TITLE, SECRET_DOC_ID)


def test_resolved_plan_uses_server_metadata_not_client_prose(tmp_path: Path) -> None:
    record = _plan_record(title=SECRET_TITLE, target_session=27, revision=9)
    with patch(
        "apps.live_control_server.services.agent_surface_context.get_workspace_document",
        return_value=record,
    ) as mock_get:
        resolution = resolve_agent_surface_context(
            _request(),
            root=tmp_path,
            outer_campaign_id="longmont-c2",
            outer_session=27,
        )
    mock_get.assert_called_once_with(tmp_path, SECRET_DOC_ID)
    assert resolution.context is not None
    assert resolution.context.surface_id == "plan"
    work = resolution.context.current_work
    assert work is not None
    assert work.kind == "plan"
    assert work.work_object_id == SECRET_DOC_ID
    assert work.title == SECRET_TITLE
    assert work.object_revision == 9
    assert work.target_session == 27
    assert resolution.trace_summary["resolution_status"] == "resolved"
    assert resolution.warning_codes == ()
    rendered = render_agent_surface_context(resolution.context)
    assert rendered is not None
    assert SECRET_TITLE in rendered
    assert SECRET_DOC_ID not in rendered
    assert "object_revision" not in rendered
    assert "revision" not in rendered.lower()
    assert 'work_object_id' not in rendered
    assert 'The GM is working in Plan on the planning document "SECRET-PLAN-TITLE-a6-privacy-9f3c" for session 27.' in rendered
    assert resolution.trace_summary["model_context_char_count"] == len(rendered)
    _assert_trace_privacy(dict(resolution.trace_summary), SECRET_TITLE, SECRET_DOC_ID)


def test_surface_only_when_document_id_absent(tmp_path: Path) -> None:
    resolution = resolve_agent_surface_context(
        _request(document_id=None),
        root=tmp_path,
        outer_campaign_id="longmont-c2",
        outer_session=27,
    )
    assert resolution.context == AgentSurfaceContext(surface_id="plan", current_work=None)
    assert resolution.trace_summary["resolution_status"] == "surface_only"
    rendered = render_agent_surface_context(resolution.context)
    assert rendered is not None
    assert "The GM is working in DungeonBuddy Plan." in rendered
    assert resolution.trace_summary["model_context_char_count"] == len(rendered)


def test_rejected_scope_continues_without_enrichment(tmp_path: Path) -> None:
    resolution = resolve_agent_surface_context(
        _request(campaign_id="other-campaign", session_number=99),
        root=tmp_path,
        outer_campaign_id="longmont-c2",
        outer_session=27,
    )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_scope"
    assert "surface_context_rejected_scope" in resolution.warning_codes
    assert render_agent_surface_context(resolution.context) is None


def test_non_empty_plan_pointers_reject_surface(tmp_path: Path) -> None:
    resolution = resolve_agent_surface_context(
        _request(pointers=[{"kind": "selection", "value": "beat-1"}]),
        root=tmp_path,
        outer_campaign_id="longmont-c2",
        outer_session=27,
    )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_surface"
    assert "surface_context_rejected_pointers" in resolution.warning_codes


def test_unsupported_surface_rejects(tmp_path: Path) -> None:
    resolution = resolve_agent_surface_context(
        _request(surface_id="play"),
        root=tmp_path,
        outer_campaign_id="longmont-c2",
        outer_session=27,
    )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "rejected_surface"
    assert resolution.trace_summary["surface_id"] == "play"


def test_unavailable_registry_lookup(tmp_path: Path) -> None:
    with patch(
        "apps.live_control_server.services.agent_surface_context.get_workspace_document",
        side_effect=WorkspaceDocumentRegistryError("missing", status_code=404),
    ):
        resolution = resolve_agent_surface_context(
            _request(),
            root=tmp_path,
            outer_campaign_id="longmont-c2",
            outer_session=27,
        )
    assert resolution.context is None
    assert resolution.trace_summary["resolution_status"] == "unavailable"
    assert "surface_context_unavailable" in resolution.warning_codes


def test_wrong_kind_or_status_rejects_surface(tmp_path: Path) -> None:
    with patch(
        "apps.live_control_server.services.agent_surface_context.get_workspace_document",
        return_value=_plan_record(kind="runbook"),
    ):
        bad_kind = resolve_agent_surface_context(
            _request(),
            root=tmp_path,
            outer_campaign_id="longmont-c2",
            outer_session=27,
        )
    assert bad_kind.trace_summary["resolution_status"] == "rejected_surface"

    with patch(
        "apps.live_control_server.services.agent_surface_context.get_workspace_document",
        return_value=_plan_record(status="discarded"),
    ):
        discarded = resolve_agent_surface_context(
            _request(),
            root=tmp_path,
            outer_campaign_id="longmont-c2",
            outer_session=27,
        )
    assert discarded.trace_summary["resolution_status"] == "rejected_surface"


def test_render_null_target_session_omits_session_clause() -> None:
    context = AgentSurfaceContext(
        surface_id="plan",
        current_work=AgentCurrentWorkContext(
            kind="plan",
            work_object_id=SECRET_DOC_ID,
            title="Campaign planning notes",
            object_revision=1,
            target_session=None,
        ),
    )
    rendered = render_agent_surface_context(context)
    assert rendered is not None
    assert 'planning document "Campaign planning notes".' in rendered
    assert "for session" not in rendered
    assert SECRET_DOC_ID not in rendered


def test_render_escapes_quotes_and_bounds_title() -> None:
    title = 'Prep "quoted"\nline ' + ("X" * (TITLE_MODEL_MAX_CHARS + 40))
    context = AgentSurfaceContext(
        surface_id="plan",
        current_work=AgentCurrentWorkContext(
            kind="plan",
            work_object_id=SECRET_DOC_ID,
            title=title,
            object_revision=2,
            target_session=3,
        ),
    )
    rendered = render_agent_surface_context(context)
    assert rendered is not None
    assert len(rendered) <= MODEL_BLOCK_MAX_CHARS
    assert "\\n" in rendered or "quoted" in rendered
    assert SECRET_DOC_ID not in rendered


def test_wire_rejects_label_and_ambient_fields() -> None:
    with pytest.raises(ValidationError):
        AgentSurfaceContextRequest.model_validate(
            {
                "schema": SURFACE_CONTEXT_REQUEST_SCHEMA,
                "surface_id": "plan",
                "campaign_id": "longmont-c2",
                "document_id": None,
                "session_number": 22,
                "pointers": [],
                "label": "must not be on wire",
            }
        )
    with pytest.raises(ValidationError):
        AgentSurfaceContextRequest.model_validate(
            {
                "schema": SURFACE_CONTEXT_REQUEST_SCHEMA,
                "surface_id": "plan",
                "campaign_id": "longmont-c2",
                "document_id": None,
                "session_number": 22,
                "pointers": [],
                "ambientSummary": "must not be on wire",
            }
        )


def test_wire_requires_versioned_fields_and_rejects_internal_schema_name() -> None:
    complete = {
        "schema": SURFACE_CONTEXT_REQUEST_SCHEMA,
        "surface_id": "plan",
        "campaign_id": "longmont-c2",
        "document_id": None,
        "session_number": 22,
        "pointers": [],
    }
    assert AgentSurfaceContextRequest.model_validate(complete).surface_id == "plan"

    for missing in ("schema", "surface_id", "campaign_id", "document_id", "session_number", "pointers"):
        payload = dict(complete)
        del payload[missing]
        with pytest.raises(ValidationError):
            AgentSurfaceContextRequest.model_validate(payload)

    with pytest.raises(ValidationError):
        AgentSurfaceContextRequest.model_validate(
            {
                "schema_": SURFACE_CONTEXT_REQUEST_SCHEMA,
                "surface_id": "plan",
                "campaign_id": "longmont-c2",
                "document_id": None,
                "session_number": 22,
                "pointers": [],
            }
        )

    with pytest.raises(ValidationError):
        AgentSurfaceContextRequest.model_validate(
            {
                "schema": "dmb_agent_surface_context_request_v0",
                "surface_id": "plan",
                "campaign_id": "longmont-c2",
                "document_id": None,
                "session_number": 22,
                "pointers": [],
            }
        )
