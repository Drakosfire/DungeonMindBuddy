import json

import pytest

from extraction_lab.repeat_experiment_qualification import qualify_repetitions, render_report


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _receipt(tmp_path, number, delta, transition, baseline_pass, candidate_pass):
    variants = {}
    for side, cost in (("baseline", 0.1), ("candidate", 0.2)):
        run = tmp_path / f"r{number}-{side}"
        _write(run / "benchmark_contract.json", {"corpus": {"fingerprint": "corpus"}, "gold": {"fingerprint": "gold"}})
        variants[side] = {
            "extraction_lab_run_path": str(run), "observed_models": {"entity_extraction": "m", "fact_extraction": "m"},
            "telemetry": {"cost_estimate": {"estimated_cost_usd": cost}, "run_window": {"elapsed_seconds": number},
                          "tokens": {"input_tokens": 10, "output_tokens": 5, "cached_tokens": 2}, "api_calls": {"total": 3}},
        }
    comparison = tmp_path / f"comparison-{number}.json"
    metrics = {}
    for field in ("entity_anchor_recall", "fact_anchor_recall", "unresolved_core_anchors", "total_entity_count", "total_fact_count"):
        metrics[field] = {"baseline": 1, "candidate": 1 + delta, "delta": delta}
    row = {"anchor_id": "brin", "transition": transition, "baseline_passed": baseline_pass,
           "candidate_passed": candidate_pass, "baseline_fail_bucket": None if baseline_pass else "missing",
           "candidate_fail_bucket": None if candidate_pass else "missing"}
    _write(comparison, {"metric_deltas": metrics, "anchor_transitions": {"entity": [row], "fact": [row]}})
    return {"manifest_sha256": "pair", "repository_sha": "a" * 40, "surface": "core_extraction",
            "sources": [{"locator": "one.md", "sha256": "source"}], "gold": {"entity": {"sha256": "e"}, "fact": {"sha256": "f"}},
            "model_policy_sha256": "policy", "variants": variants, "comparison": {"artifact_path": str(comparison)}}


def test_qualification_exposes_variability_anchor_stability_and_telemetry(tmp_path):
    receipts = [_receipt(tmp_path, 1, 1, "improved", False, True), _receipt(tmp_path, 2, -1, "regressed", True, False)]
    result = qualify_repetitions(receipts)
    delta = result["metrics"]["entity_anchor_recall"]["delta"]
    assert delta["values"] == [1, -1]
    assert delta["mean"] == 0
    assert delta["pstdev"] == 1
    assert delta["sign_counts"] == {"negative": 1, "zero": 0, "positive": 1}
    anchor = result["anchors"]["entity"][0]
    assert anchor["baseline"]["pass_rate"] == 0.5
    assert anchor["candidate"]["fail_buckets"] == {"missing": 1}
    assert anchor["transitions"] == {"improved": 1, "regressed": 1}
    assert result["telemetry"]["pair"]["cost_usd"]["total"] == pytest.approx(0.6)
    serialized = json.dumps(result).lower()
    assert '"winner"' not in serialized
    assert '"ready"' not in serialized
    assert '"promotion"' not in serialized
    report = render_report(result).lower()
    assert "descriptive variability only" in report
    assert "winner:" not in report
