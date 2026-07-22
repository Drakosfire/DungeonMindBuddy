"""Tests for projection-load telemetry and contribution/projection caches."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from graph_memory.projection_load_telemetry import (
    current_projection_load_trace,
    projection_load_trace,
    timed_stage,
)
from graph_memory.world_projection_cache import (
    clear_projection_cache,
    get_cached_projection,
    make_projection_cache_key,
    projection_cache_stats,
    put_cached_projection,
)


def test_projection_load_trace_emits_structured_log_without_prose(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="dmb.graph_load")
    with projection_load_trace("unit_pipeline", world_id="eldyrwild", campaign_id="longmont-c1"):
        with timed_stage("example_stage", node_count=3):
            pass
        trace = current_projection_load_trace()
        assert trace is not None
        trace.bump("nodes", 3)

    records = [r for r in caplog.records if r.name == "dmb.graph_load"]
    assert records
    message = records[-1].getMessage()
    assert message.startswith("graph_load ")
    payload = json.loads(message.removeprefix("graph_load "))
    assert payload["pipeline"] == "unit_pipeline"
    assert payload["outcome"] == "ok"
    assert payload["counts"]["nodes"] == 3
    assert payload["stages"][0]["stage"] == "example_stage"
    blob = json.dumps(payload)
    assert "Glowkindle" not in blob
    assert "friendly merchant" not in blob


def test_nested_projection_load_trace_reuses_parent_contribution_cache() -> None:
    with projection_load_trace("parent", emit=False) as parent:
        parent.put_cached_contribution("w", "c1", {"ok": True}, load_ms=1.5)
        with projection_load_trace("child", emit=False) as child:
            assert child is parent
            hit = child.get_cached_contribution("w", "c1")
            assert hit == {"ok": True}
        assert parent.contribution_cache_hits == 1
        assert parent.contribution_cache_misses == 1


def test_projection_cache_hit_by_revision_key(tmp_path: Path) -> None:
    from graph_memory.projection.world_projection import (
        WorldGraphProjection,
        WorldGraphProjectionFocus,
        WorldGraphProjectionRequest,
        WorldGraphProjectionSnapshot,
        WorldGraphProjectionSummary,
        WorldGraphProjectionTrustBoundary,
    )

    clear_projection_cache()
    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id="eldyrwild",
        campaign_id="longmont-c1",
        focus=WorldGraphProjectionFocus(kind="session", session_id="session-1"),
        admissibility="gm",
        scope_mode="campaign",
    )
    key = make_projection_cache_key(
        tmp_path,
        request,
        revision_id="rev:abc",
        head_revision_id="rev:abc",
        ledger_fp="idx:missing|files:missing",
    )
    projection = WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=WorldGraphProjectionSnapshot(
            world_id="eldyrwild",
            campaign_id="longmont-c1",
            revision_id="rev:abc",
            head_revision_id="rev:abc",
            is_head=True,
            focus=request.focus,
            admissibility="gm",
            scope_mode="campaign",
        ),
        summary=WorldGraphProjectionSummary(
            node_count=0,
            relationship_count=0,
            attribute_count=0,
            evidence_count=0,
            source_artifact_count=0,
            projection_truncated=False,
        ),
        nodes=[],
        relationships=[],
        attributes=[],
        evidence=[],
        source_artifacts=[],
        trust_boundary=WorldGraphProjectionTrustBoundary(can_trust=[], cannot_trust=[]),
        diagnostics=[],
    )
    assert get_cached_projection(key) is None
    put_cached_projection(key, projection)
    assert get_cached_projection(key) is projection
    stats = projection_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    clear_projection_cache()
