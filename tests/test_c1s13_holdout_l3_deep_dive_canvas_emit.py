from __future__ import annotations

from evals.sentence_routing_retrieval_falsification.c1s13_holdout_l3_deep_dive_canvas_emit import emit_payload


def test_emit_payload_has_promoted_and_legacy_labels() -> None:
    payload = emit_payload()
    assert payload["cohort_lane_labels"]["promoted_default"] == "Promoted Equivalence Default"
    assert payload["cohort_lane_labels"]["legacy_diagnostics"] == "Legacy Baseline (diagnostics)"


def test_emit_payload_retains_backcompat_baseline_equivalence_keys() -> None:
    payload = emit_payload()
    assert "baseline" in payload["backcompat"]
    assert "equivalence" in payload["backcompat"]
    assert "results" in payload["backcompat"]["baseline"]
    assert "results" in payload["backcompat"]["equivalence"]
