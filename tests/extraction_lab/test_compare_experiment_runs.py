import json

from extraction_lab.compare_experiment_runs import (
    compare_experiment_runs,
    write_comparison,
)


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _run(
    tmp_path,
    name,
    *,
    corpus="corpus-a",
    gold="gold-a",
    model="baseline-model",
    entity_pass=True,
    entity_bucket=None,
    entity_count=10,
):
    run = tmp_path / name
    run.mkdir()
    benchmark = {
        "contract_version": 1,
        "surface": "core_extraction",
        "corpus": {
            "available": True,
            "fingerprint": corpus,
            "source_count": 1,
            "unavailable_reasons": [],
        },
        "gold": {
            "fingerprint": gold,
            "entity_fingerprint": "entities",
            "fact_fingerprint": "facts",
            "entity_anchor_count": 1,
            "fact_anchor_count": 1,
        },
    }
    _write_json(
        run / "run_manifest.json",
        {"run_id": name, "surface": "core_extraction", "benchmark_contract": benchmark},
    )
    _write_json(run / "benchmark_contract.json", benchmark)
    _write_json(
        run / "pipeline_contract.json",
        {"contract_version": 1, "entity_model": model, "entity_prompt_id": "prompt"},
    )
    _write_json(
        run / "aggregate_metrics.json",
        {
            "entity_anchor_recall": 1.0 if entity_pass else 0.0,
            "fact_anchor_recall": 1.0,
            "unresolved_core_anchors": 0 if entity_pass else 1,
            "total_entity_count": entity_count,
            "total_fact_count": 5,
        },
    )
    _write_json(
        run / "entity_results.json",
        [
            {
                "anchor_id": "brin",
                "passed": entity_pass,
                "fail_bucket": entity_bucket,
                "surface": "core_extraction",
            }
        ],
    )
    _write_json(
        run / "fact_results.json",
        [
            {
                "anchor_id": "orik_mayor",
                "passed": True,
                "fail_bucket": None,
                "surface": "core_extraction",
            }
        ],
    )
    return run


def test_cross_contract_runs_are_comparable_and_explain_transitions(tmp_path) -> None:
    baseline = _run(
        tmp_path, "baseline", entity_pass=False, entity_bucket="name_not_found"
    )
    candidate = _run(
        tmp_path,
        "candidate",
        model="candidate-model",
        entity_pass=True,
        entity_count=40,
    )
    result = compare_experiment_runs(baseline_dir=baseline, candidate_dir=candidate)
    assert result["comparable"] is True
    assert {row["field"] for row in result["pipeline_contract_differences"]} == {
        "entity_model"
    }
    assert result["metric_deltas"]["entity_anchor_recall"]["delta"] == 1.0
    assert result["metric_deltas"]["total_entity_count"]["delta"] == 30
    assert result["anchor_transitions"]["entity"][0] == {
        "anchor_id": "brin",
        "transition": "improved",
        "baseline_passed": False,
        "candidate_passed": True,
        "baseline_fail_bucket": "name_not_found",
        "candidate_fail_bucket": None,
    }
    assert "winner" not in result
    assert "READY" not in result


def test_benchmark_mismatch_fails_closed_without_quality_deltas(tmp_path) -> None:
    baseline = _run(tmp_path, "baseline")
    candidate = _run(tmp_path, "candidate", corpus="corpus-b", gold="gold-b")
    result = compare_experiment_runs(baseline_dir=baseline, candidate_dir=candidate)
    assert result["comparable"] is False
    assert result["non_comparable_reasons"] == [
        "benchmark_corpus_mismatch",
        "benchmark_gold_intent_mismatch",
    ]
    assert "metric_deltas" not in result
    assert "anchor_transitions" not in result


def test_legacy_run_requires_rerun(tmp_path) -> None:
    baseline = _run(tmp_path, "baseline")
    candidate = _run(tmp_path, "candidate")
    (baseline / "benchmark_contract.json").unlink()
    manifest = json.loads((baseline / "run_manifest.json").read_text(encoding="utf-8"))
    manifest.pop("benchmark_contract")
    _write_json(baseline / "run_manifest.json", manifest)
    result = compare_experiment_runs(baseline_dir=baseline, candidate_dir=candidate)
    assert result["comparable"] is False
    assert result["non_comparable_reasons"] == [
        "baseline_missing_benchmark_contract_rerun_required"
    ]


def test_invalid_benchmark_contract_fails_closed(tmp_path) -> None:
    baseline = _run(tmp_path, "baseline")
    candidate = _run(tmp_path, "candidate")
    benchmark = json.loads(
        (candidate / "benchmark_contract.json").read_text(encoding="utf-8")
    )
    benchmark["contract_version"] = 99
    _write_json(candidate / "benchmark_contract.json", benchmark)
    result = compare_experiment_runs(baseline_dir=baseline, candidate_dir=candidate)
    assert result["comparable"] is False
    assert (
        "candidate_benchmark_contract_version_unsupported"
        in result["non_comparable_reasons"]
    )
    assert (
        "candidate_benchmark_contract_stamp_mismatch"
        in result["non_comparable_reasons"]
    )


def test_report_contains_tradeoffs_without_ranking(tmp_path) -> None:
    baseline = _run(
        tmp_path, "baseline", entity_pass=False, entity_bucket="class_mismatch"
    )
    candidate = _run(tmp_path, "candidate", model="candidate-model", entity_count=100)
    out = tmp_path / "comparison"
    result = write_comparison(
        baseline_dir=baseline, candidate_dir=candidate, out_dir=out
    )
    report = (out / "report.md").read_text(encoding="utf-8")
    assert result["comparable"] is True
    assert "total_entity_count" in report
    assert "class_mismatch" in report
    assert "winner" not in report.lower()
    assert "promotion" not in report.lower()
