"""Smoke tests for C1S3 statblock benchmark canvas payload builder."""

from __future__ import annotations

from evals.planner_slice.c1s3_statblock_benchmark_canvas_emit import (
    build_c1s3_statblock_benchmark_payload,
    build_statblock_canvas_block,
)


def test_build_payload_includes_three_c1s3_statblock_fixtures() -> None:
    p = build_c1s3_statblock_benchmark_payload()
    assert p["canvasBasename"] == "c1s3-statblock-benchmark-scenarios.canvas.tsx"
    assert len(p["scenarios"]) == 3
    ids = {str(s["id"]) for s in p["scenarios"]}
    assert "c1s3_pippa_statblock_context_scripted" in ids
    assert "c1s3_bubbles_statblock_context_scripted" in ids
    assert "c1s3_kirfan_missing_context_scripted" in ids
    kirfan = next(s for s in p["scenarios"] if "kirfan" in str(s["id"]))
    assert kirfan["noGenerateStatblock"] is True


def test_build_canvas_block_contains_markers_and_json() -> None:
    block = build_statblock_canvas_block()
    assert "// BEGIN GENERATED C1S3_STATBLOCK_SCENARIO_CANVAS" in block
    assert "// END GENERATED C1S3_STATBLOCK_SCENARIO_CANVAS" in block
    assert "c1s3StatblockHarnessGenerated" in block
    assert "scenario_c1s3_pippa_statblock_context.json" in block
