"""Tests for graph authoring event log writer."""

from __future__ import annotations

import json
from pathlib import Path

from apps.live_control_server.services.graph_authoring_event_log import (
    append_graph_authoring_events,
    build_graph_authoring_events,
)
from tests.test_graph_authoring_overlay_models import object_assertion


def test_build_graph_authoring_events_includes_batch_and_per_assertion() -> None:
    assertion = object_assertion()
    events = build_graph_authoring_events(
        campaign_id="longmont-c1",
        session_id="session-2",
        overlay_path="/tmp/overlay.json",
        overlay_token_before="before",
        overlay_token_after="after",
        assertions=[assertion],
        local_proposal_ids=["local-1"],
        batch_event_id="evt-batch-1",
    )
    assert len(events) == 2
    assert events[0].event_kind == "authored_graph_assertions_committed"
    assert events[1].event_kind == "authored_graph_object_committed"
    assert events[1].local_proposal_id == "local-1"


def test_append_graph_authoring_events_writes_jsonl(tmp_path: Path) -> None:
    assertion = object_assertion()
    events = build_graph_authoring_events(
        campaign_id="longmont-c1",
        session_id="session-2",
        overlay_path="/tmp/overlay.json",
        overlay_token_before="before",
        overlay_token_after="after",
        assertions=[assertion],
        local_proposal_ids=["local-1"],
        batch_event_id="evt-batch-1",
    )
    events_path = tmp_path / "graph_authoring_events.jsonl"
    append_graph_authoring_events(events_path, events)
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["schema_version"] == "dmb.graph_authoring_event.v1"
