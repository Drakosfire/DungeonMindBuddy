"""Tests for TL01C temporal prompt calibration runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from evals.graph_memory_layer import temporal_shadow_prompt_calibration as calibration
from graph_memory.temporal_shadow_extraction_schema import (
    CalibrationCohortAggregateV1,
    CalibrationMetricDistributionV1,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _comparison_payload(
    *,
    exact_match_count: int = 6,
    resolved_exact_match_count: int = 3,
    status_accuracy: float = 1.0,
    not_applicable_accuracy: float = 1.0,
    unsafe_over_resolution_count: int = 0,
    wrong_temporal_value: int = 0,
    wrong_temporal_lane: int = 0,
    status_mismatch_count: int = 0,
    total_gold: int = 6,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index in range(wrong_temporal_value):
        rows.append(
            {
                "base_assertion_id": f"assertion:wrong-value-{index}",
                "classification": "wrong_temporal_value",
                "gold_interpretation_status": "resolved",
                "predicted_interpretation_status": "resolved",
                "diagnostics": [],
            }
        )
    for index in range(unsafe_over_resolution_count):
        rows.append(
            {
                "base_assertion_id": f"assertion:unsafe-{index}",
                "classification": "unsafe_over_resolution",
                "gold_interpretation_status": "not_applicable",
                "predicted_interpretation_status": "resolved",
                "diagnostics": [],
            }
        )
    return {
        "schema": "dmb_temporal_shadow_comparison_v1",
        "verdict": "pass" if unsafe_over_resolution_count == 0 else "fail",
        "evaluation_verdict": "SAFE_FOR_NEXT_EXPERIMENT",
        "metrics": {
            "total_gold_annotations": total_gold,
            "exact_match_count": exact_match_count,
            "resolved_exact_match_count": resolved_exact_match_count,
            "status_accuracy": status_accuracy,
            "not_applicable_accuracy": not_applicable_accuracy,
            "unsafe_over_resolution_count": unsafe_over_resolution_count,
            "status_mismatch_count": status_mismatch_count,
            "wrong_temporal_lane_count": wrong_temporal_lane,
            "source_to_occurrence_false_positives": 0,
            "source_to_valid_time_false_positives": 0,
            "evidence_selection_mismatch_count": 0,
            "invalid_temporal_payloads": 0,
        },
        "rows": rows,
    }


def _write_success_run(
    run_dir: Path,
    *,
    comparison: dict[str, Any],
    case_id: str = "test-case",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run-manifest.json").write_text(
        json.dumps(
            {
                "schema": "dmb_temporal_shadow_extraction_run_v1",
                "run_id": "temporal-shadow-run:test",
                "case_id": case_id,
                "comparison_verdict": comparison["verdict"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_failure_run(run_dir: Path, *, failure_code: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "failure-manifest.json").write_text(
        json.dumps(
            {
                "schema": "dmb_temporal_shadow_extraction_failure_v1",
                "failure_code": failure_code,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _spec(lane: str, cohort: str, repetition: int) -> calibration.CalibrationRunSpec:
    return calibration.CalibrationRunSpec(
        prompt_lane=lane,  # type: ignore[arg-type]
        cohort=cohort,  # type: ignore[arg-type]
        case_path=Path("dummy.json"),
        repetition=repetition,
    )


def test_baseline_and_candidate_outputs_separated(tmp_path: Path) -> None:
    baseline_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="baseline",
        cohort="development",
        repetition=1,
    )
    candidate_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=1,
    )
    _write_success_run(baseline_dir, comparison=_comparison_payload(exact_match_count=1))
    _write_success_run(candidate_dir, comparison=_comparison_payload(exact_match_count=2))

    baseline_outcome = calibration.load_run_outcome(
        _spec("baseline", "development", 1), baseline_dir
    )
    candidate_outcome = calibration.load_run_outcome(
        _spec("candidate", "development", 1), candidate_dir
    )
    assert baseline_outcome.succeeded
    assert candidate_outcome.succeeded
    assert (
        baseline_outcome.comparison["metrics"]["exact_match_count"]  # type: ignore[index]
        != candidate_outcome.comparison["metrics"]["exact_match_count"]  # type: ignore[index]
    )


def test_independent_run_directories_per_repetition(tmp_path: Path) -> None:
    run1 = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="holdout",
        repetition=1,
    )
    run2 = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="holdout",
        repetition=2,
    )
    assert run1 != run2
    _write_success_run(run1, comparison=_comparison_payload(exact_match_count=1))
    _write_success_run(run2, comparison=_comparison_payload(exact_match_count=2))
    assert run1.is_dir() and run2.is_dir()


def test_failed_repetitions_remain_visible(tmp_path: Path) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=1,
    )
    _write_failure_run(run_dir, failure_code="provider_error")
    outcome = calibration.load_run_outcome(_spec("candidate", "development", 1), run_dir)
    assert not outcome.succeeded
    assert (run_dir / "failure-manifest.json").is_file()
    assert outcome.failure_code == "provider_error"


def test_aggregate_counts_match_underlying_manifests(tmp_path: Path) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=1,
    )
    comparison = _comparison_payload(
        unsafe_over_resolution_count=1,
        exact_match_count=4,
        status_accuracy=0.8,
    )
    _write_success_run(run_dir, comparison=comparison)
    outcome = calibration.load_run_outcome(_spec("candidate", "development", 1), run_dir)
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="candidate",
        cohort="development",
        outcomes=[outcome],
    )
    assert aggregate.total_unsafe_over_resolution == 1
    assert aggregate.exact_match == CalibrationMetricDistributionV1(
        min=4.0, median=4.0, max=4.0
    )
    assert aggregate.min_status_accuracy == pytest.approx(0.8)


def test_mixed_safe_unsafe_set_cannot_receive_ready_verdict() -> None:
    safe = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        success_count=1,
        exact_match=CalibrationMetricDistributionV1(min=6.0, median=6.0, max=6.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=3.0, median=3.0, max=3.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    unsafe = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="adversarial",
        run_count=1,
        success_count=1,
        total_unsafe_over_resolution=1,
        exact_match=CalibrationMetricDistributionV1(min=5.0, median=5.0, max=5.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=3.0, median=3.0, max=3.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    holdout = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="holdout",
        run_count=1,
        success_count=1,
        exact_match=CalibrationMetricDistributionV1(min=7.0, median=7.0, max=7.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=4.0, median=4.0, max=4.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    decision, _ = calibration.compute_calibration_decision(
        candidate_aggregates=[safe, unsafe, holdout],
    )
    assert decision == "ITERATE_PROMPT"


def test_one_correct_run_cannot_hide_unsafe_repetitions() -> None:
    good = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="holdout",
        run_count=1,
        success_count=1,
        exact_match=CalibrationMetricDistributionV1(min=7.0, median=7.0, max=7.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=4.0, median=4.0, max=4.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    bad = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="holdout",
        run_count=1,
        success_count=1,
        total_unsafe_over_resolution=2,
        exact_match=CalibrationMetricDistributionV1(min=7.0, median=7.0, max=7.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=4.0, median=4.0, max=4.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    decision, diagnostics = calibration.compute_calibration_decision(
        candidate_aggregates=[good, bad],
    )
    assert decision == "ITERATE_PROMPT"
    assert any("unsafe_over_resolution" in note for note in diagnostics)


def test_holdout_seal_sha_and_prompt_hash_recorded_in_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holdout_case = (
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case.json"
    )
    holdout_seal = "abc123deadbeef"

    def fake_repetition(spec: calibration.CalibrationRunSpec, **kwargs: Any) -> calibration.RunOutcome:
        run_dir = calibration._lane_run_dir(
            output_dir=kwargs["output_dir"],
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        if spec.prompt_lane == "candidate" and spec.cohort == "holdout":
            _write_success_run(
                run_dir,
                comparison=_comparison_payload(exact_match_count=7, total_gold=7),
                case_id="holdout",
            )
        else:
            _write_success_run(run_dir, comparison=_comparison_payload())
        return calibration.load_run_outcome(spec, run_dir)

    monkeypatch.setattr(calibration, "run_calibration_repetition", fake_repetition)

    aggregate = calibration.run_prompt_calibration(
        development_case=REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json",
        candidate_development_case=REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01c.json",
        holdout_case=REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01b.json",
        candidate_holdout_case=holdout_case,
        adversarial_case=REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_adversarial/temporal-case.json",
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=1,
        repo_root=REPO_ROOT,
        holdout_seal_sha256=holdout_seal,
        fake=True,
    )
    assert aggregate.holdout_seal_sha256 == holdout_seal
    assert len(aggregate.candidate_prompt_sha256) == 64
    assert len(aggregate.baseline_prompt_sha256) == 64
    assert (tmp_path / "calibration" / "aggregate.json").is_file()


def test_input_representation_blocked_when_wrong_value_dominates() -> None:
    dev = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        success_count=1,
        total_wrong_temporal_value=2,
        exact_match=CalibrationMetricDistributionV1(min=4.0, median=4.0, max=4.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=2.0, median=2.0, max=2.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    holdout = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="holdout",
        run_count=1,
        success_count=1,
        exact_match=CalibrationMetricDistributionV1(min=7.0, median=7.0, max=7.0),
        resolved_exact_match=CalibrationMetricDistributionV1(min=4.0, median=4.0, max=4.0),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
    )
    decision, _ = calibration.compute_calibration_decision(
        candidate_aggregates=[dev, holdout],
    )
    assert decision == "BLOCKED_BY_INPUT_REPRESENTATION"


def test_provider_failure_decision() -> None:
    aggregate = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        failure_count=1,
        total_provider_failures=1,
    )
    decision, _ = calibration.compute_calibration_decision(
        candidate_aggregates=[aggregate],
    )
    assert decision == "PROVIDER_FAILURE"


@patch.object(calibration, "run_calibration_repetition")
def test_run_prompt_calibration_writes_separate_lane_dirs(
    mock_repetition: Any, tmp_path: Path
) -> None:
    def side_effect(spec: calibration.CalibrationRunSpec, **kwargs: Any) -> calibration.RunOutcome:
        run_dir = calibration._lane_run_dir(
            output_dir=kwargs["output_dir"],
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        _write_success_run(run_dir, comparison=_comparison_payload())
        return calibration.load_run_outcome(spec, run_dir)

    mock_repetition.side_effect = side_effect
    calibration.run_prompt_calibration(
        development_case=Path("dev.json"),
        candidate_development_case=Path("cdev.json"),
        holdout_case=Path("hold.json"),
        candidate_holdout_case=Path("chold.json"),
        adversarial_case=Path("adv.json"),
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=2,
        repo_root=REPO_ROOT,
        holdout_seal_sha256="seal",
        fake=True,
    )
    assert mock_repetition.call_count == 10
    assert (
        tmp_path / "calibration" / "baseline" / "development" / "run-01"
    ).is_dir()
    assert (
        tmp_path / "calibration" / "candidate" / "adversarial" / "run-02"
    ).is_dir()
