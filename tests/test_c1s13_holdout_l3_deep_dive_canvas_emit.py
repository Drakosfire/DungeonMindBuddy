from __future__ import annotations

from evals.sentence_routing_retrieval_falsification.c1s13_holdout_l3_deep_dive_canvas_emit import emit_payload


def test_emit_payload_default_lane_label() -> None:
    payload = emit_payload()
    assert payload["cohort_lane_labels"]["promoted_default"] == "Default (equivalence-augmented ranking)"


def test_emit_payload_comparison_is_default_lane_only() -> None:
    payload = emit_payload()
    assert set(payload["comparison"].keys()) == {"promoted_default"}
    assert "results" in payload["comparison"]["promoted_default"]
    assert "legacy_diagnostics" not in payload["comparison"]
    assert "backcompat" not in payload
