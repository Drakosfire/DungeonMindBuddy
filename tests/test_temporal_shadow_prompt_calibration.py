"""Tests for TL01C temporal prompt calibration runner."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from evals.graph_memory_layer import temporal_shadow_prompt_calibration as calibration
from graph_memory.temporal_shadow_extraction_schema import (
    CalibrationCohortAggregateV1,
    CalibrationMetricDistributionV1,
    CalibrationRunRecordV1,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

HEX64 = re.compile(r"^[0-9a-f]{64}$")
KNOWN_HOLDOUT_SEAL_COMMIT = "2c3be373fdaf6a713c4cae9c5ab75f9ffad5bc1d"

DEVELOPMENT_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json"
)
CANDIDATE_DEVELOPMENT_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01c.json"
)
HOLDOUT_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case-tl01b.json"
)
CANDIDATE_HOLDOUT_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case.json"
)
ADVERSARIAL_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_adversarial_v2/temporal-case.json"
)


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
    source_to_occurrence_false_positives: int = 0,
    source_to_valid_time_false_positives: int = 0,
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
            "source_to_occurrence_false_positives": source_to_occurrence_false_positives,
            "source_to_valid_time_false_positives": source_to_valid_time_false_positives,
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
    manifest_extra: dict[str, Any] | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest: dict[str, Any] = {
        "schema": "dmb_temporal_shadow_extraction_run_v1",
        "run_id": "temporal-shadow-run:test",
        "case_id": case_id,
        "comparison_verdict": comparison["verdict"],
    }
    if manifest_extra is not None:
        manifest.update(manifest_extra)
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _dev_run_record(*, repetition: int, resolved_exact: int) -> CalibrationRunRecordV1:
    return CalibrationRunRecordV1(
        prompt_lane="candidate",
        cohort="development",
        repetition=repetition,
        succeeded=True,
        resolved_exact_match_count=resolved_exact,
    )


def _ready_development_aggregate(
    *,
    run_resolved_counts: list[int] | None = None,
) -> CalibrationCohortAggregateV1:
    resolved_counts = run_resolved_counts or [3, 3, 3]
    run_records = [
        _dev_run_record(repetition=index + 1, resolved_exact=count)
        for index, count in enumerate(resolved_counts)
    ]
    return CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=len(run_records),
        success_count=len(run_records),
        exact_match=CalibrationMetricDistributionV1(min=4.0, median=5.0, max=6.0),
        resolved_exact_match=CalibrationMetricDistributionV1(
            min=float(min(resolved_counts)),
            median=float(sorted(resolved_counts)[len(resolved_counts) // 2]),
            max=float(max(resolved_counts)),
        ),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
        manifest_consistency_ok=True,
        run_records=run_records,
    )


def _ready_holdout_aggregate(
    *,
    occurrence_min: float = 2.0,
    occurrence_max: float | None = None,
    valid_min: float = 2.0,
    valid_max: float | None = None,
) -> CalibrationCohortAggregateV1:
    occ_max = occurrence_min if occurrence_max is None else occurrence_max
    val_max = valid_min if valid_max is None else valid_max
    return CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="holdout",
        run_count=3,
        success_count=3,
        exact_match=CalibrationMetricDistributionV1(min=7.0, median=7.0, max=7.0),
        resolved_exact_match=CalibrationMetricDistributionV1(
            min=2.0, median=2.0, max=2.0
        ),
        exact_occurrence_match=CalibrationMetricDistributionV1(
            min=occurrence_min, median=max(occurrence_min, occ_max), max=occ_max
        ),
        exact_valid_time_match=CalibrationMetricDistributionV1(
            min=valid_min, median=max(valid_min, val_max), max=val_max
        ),
        min_status_accuracy=1.0,
        min_not_applicable_accuracy=1.0,
        manifest_consistency_ok=True,
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


def _case_copy_with_prompt_version(
    source: Path,
    dest: Path,
    *,
    prompt_version: str,
    case_id: str | None = None,
) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["prompt_version"] = prompt_version
    if case_id is not None:
        payload["case_id"] = case_id
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def _baseline_adversarial_mirror(tmp_path: Path) -> Path:
    """TL01B-prompt mirror of adversarial V2 (same base/gold/evidence)."""
    return _case_copy_with_prompt_version(
        ADVERSARIAL_CASE,
        tmp_path / "temporal-case-tl01b-adversarial.json",
        prompt_version="tl01b-v1",
        case_id="tl01b-temporal-shadow-adversarial-v2-baseline",
    )


def _run_fake_calibration(
    tmp_path: Path,
    *,
    repetitions: int = 1,
    development_case: Path = DEVELOPMENT_CASE,
    holdout_case: Path = HOLDOUT_CASE,
    candidate_development_case: Path = CANDIDATE_DEVELOPMENT_CASE,
    candidate_holdout_case: Path = CANDIDATE_HOLDOUT_CASE,
    adversarial_case: Path = ADVERSARIAL_CASE,
    baseline_adversarial_case: Path | None = None,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> Any:
    def fake_repetition(
        spec: calibration.CalibrationRunSpec, **kwargs: Any
    ) -> calibration.RunOutcome:
        run_dir = calibration._lane_run_dir(
            output_dir=kwargs["output_dir"],
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        _write_success_run(run_dir, comparison=_comparison_payload())
        return calibration.load_run_outcome(spec, run_dir)

    if monkeypatch is not None:
        monkeypatch.setattr(calibration, "run_calibration_repetition", fake_repetition)

    kwargs: dict[str, Any] = dict(
        development_case=development_case,
        candidate_development_case=candidate_development_case,
        holdout_case=holdout_case,
        candidate_holdout_case=candidate_holdout_case,
        adversarial_case=adversarial_case,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=repetitions,
        repo_root=REPO_ROOT,
        skip_seal_verification=True,
        fake=True,
    )
    if baseline_adversarial_case is not None:
        kwargs["baseline_adversarial_case"] = baseline_adversarial_case

    if monkeypatch is not None:
        return calibration.run_prompt_calibration(**kwargs)

    with patch.object(calibration, "run_calibration_repetition", fake_repetition):
        return calibration.run_prompt_calibration(**kwargs)


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
        cohort_aggregates=[safe, unsafe, holdout],
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
        cohort_aggregates=[good, bad],
    )
    assert decision == "ITERATE_PROMPT"
    assert any("unsafe_over_resolution" in note for note in diagnostics)


def test_holdout_seal_fields_recorded_in_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holdout_seal_commit = "abc123deadbeef"

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
        development_case=DEVELOPMENT_CASE,
        candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
        holdout_case=HOLDOUT_CASE,
        candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
        adversarial_case=ADVERSARIAL_CASE,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=1,
        repo_root=REPO_ROOT,
        holdout_seal_commit_sha=holdout_seal_commit,
        skip_seal_verification=True,
        fake=True,
    )
    assert HEX64.match(aggregate.holdout_case_sha256)
    assert HEX64.match(aggregate.holdout_base_sha256)
    assert HEX64.match(aggregate.holdout_gold_sha256)
    assert aggregate.holdout_seal_commit_sha == holdout_seal_commit
    assert HEX64.match(aggregate.adversarial_case_sha256 or "")
    assert HEX64.match(aggregate.adversarial_base_sha256 or "")
    assert HEX64.match(aggregate.adversarial_gold_sha256 or "")
    assert len(aggregate.candidate_prompt_sha256) == 64
    assert len(aggregate.baseline_prompt_sha256) == 64
    assert (tmp_path / "calibration" / "aggregate.json").is_file()


def test_verify_cohort_seal_rejects_unknown_commit() -> None:
    with pytest.raises(calibration.CohortSealError, match="does not exist"):
        calibration.verify_cohort_seal(
            case_path=CANDIDATE_HOLDOUT_CASE,
            seal_commit_sha="0" * 40,
            repo_root=REPO_ROOT,
        )


def test_verify_cohort_seal_accepts_known_holdout_seal() -> None:
    record = calibration.verify_cohort_seal(
        case_path=CANDIDATE_HOLDOUT_CASE,
        seal_commit_sha=KNOWN_HOLDOUT_SEAL_COMMIT,
        repo_root=REPO_ROOT,
    )
    assert HEX64.match(record.case_sha256)
    assert HEX64.match(record.base_sha256)
    assert HEX64.match(record.gold_sha256)
    assert record.seal_commit_sha == KNOWN_HOLDOUT_SEAL_COMMIT
    assert record.case_id == "tl01c-temporal-shadow-holdout-v1"


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
        cohort_aggregates=[dev, holdout],
    )
    assert decision == "BLOCKED_BY_INPUT_REPRESENTATION"


def test_unsafe_blocks_before_input_representation() -> None:
    dev = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        success_count=1,
        total_unsafe_over_resolution=1,
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
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[dev, holdout],
    )
    assert decision == "ITERATE_PROMPT"
    assert not any("wrong_temporal_value_dominates" in note for note in diagnostics)


def test_evidence_case_failure_is_blocked_by_evidence() -> None:
    aggregate = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        failure_count=1,
        total_evidence_or_case_failures=1,
    )
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[aggregate],
    )
    assert decision == "BLOCKED_BY_EVIDENCE"
    assert any("evidence_or_case_failures" in note for note in diagnostics)


def test_provider_failure_decision() -> None:
    aggregate = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        failure_count=1,
        total_provider_failures=1,
    )
    decision, _ = calibration.compute_calibration_decision(
        cohort_aggregates=[aggregate],
    )
    assert decision == "PROVIDER_FAILURE"


def test_aggregate_splits_occurrence_and_valid_leakage(tmp_path: Path) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="holdout",
        repetition=1,
    )
    comparison = _comparison_payload(
        source_to_occurrence_false_positives=1,
        source_to_valid_time_false_positives=2,
    )
    _write_success_run(run_dir, comparison=comparison)
    outcome = calibration.load_run_outcome(_spec("candidate", "holdout", 1), run_dir)
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="candidate",
        cohort="holdout",
        outcomes=[outcome],
    )
    assert aggregate.total_source_to_occurrence_false_positives == 1
    assert aggregate.total_source_to_valid_time_false_positives == 2
    assert aggregate.total_source_leakage_false_positives == 3


def test_failed_repetition_appears_in_assertion_stability(tmp_path: Path) -> None:
    success_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=1,
    )
    failure_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=2,
    )
    comparison = _comparison_payload(
        exact_match_count=1,
        resolved_exact_match_count=1,
        total_gold=1,
    )
    comparison["rows"] = [
        {
            "base_assertion_id": "assertion:stability-target",
            "classification": "exact_match",
            "gold_interpretation_status": "resolved",
            "predicted_interpretation_status": "resolved",
            "diagnostics": [],
        }
    ]
    _write_success_run(success_dir, comparison=comparison)
    _write_failure_run(failure_dir, failure_code="provider_error")
    success = calibration.load_run_outcome(_spec("candidate", "development", 1), success_dir)
    failure = calibration.load_run_outcome(_spec("candidate", "development", 2), failure_dir)
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="candidate",
        cohort="development",
        outcomes=[success, failure],
    )
    assert aggregate.failure_count == 1
    assert aggregate.total_provider_failures == 1
    assert aggregate.assertion_stability
    assert any(
        entry.classification_counts.get("run_failed", 0) > 0
        for entry in aggregate.assertion_stability
    )


def test_case_ids_populated_in_metrics_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_repetition(spec: calibration.CalibrationRunSpec, **kwargs: Any) -> calibration.RunOutcome:
        run_dir = calibration._lane_run_dir(
            output_dir=kwargs["output_dir"],
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        case_id = f"{spec.prompt_lane}-{spec.cohort}"
        _write_success_run(
            run_dir,
            comparison=_comparison_payload(),
            case_id=case_id,
        )
        return calibration.load_run_outcome(spec, run_dir)

    monkeypatch.setattr(calibration, "run_calibration_repetition", fake_repetition)

    aggregate = calibration.run_prompt_calibration(
        development_case=DEVELOPMENT_CASE,
        candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
        holdout_case=HOLDOUT_CASE,
        candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
        adversarial_case=ADVERSARIAL_CASE,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=1,
        repo_root=REPO_ROOT,
        skip_seal_verification=True,
        fake=True,
    )
    candidate_slice = next(
        slice_ for slice_ in aggregate.slices if slice_.prompt_lane == "candidate"
    )
    assert candidate_slice.case_ids


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
        development_case=DEVELOPMENT_CASE,
        candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
        holdout_case=HOLDOUT_CASE,
        candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
        adversarial_case=ADVERSARIAL_CASE,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=2,
        repo_root=REPO_ROOT,
        skip_seal_verification=True,
        fake=True,
    )
    assert mock_repetition.call_count == 10
    assert (
        tmp_path / "calibration" / "baseline" / "development" / "run-01"
    ).is_dir()
    assert (
        tmp_path / "calibration" / "candidate" / "adversarial" / "run-02"
    ).is_dir()


def test_skip_seal_verification_requires_fake(tmp_path: Path) -> None:
    with pytest.raises(calibration.CohortSealError, match="skip_seal_verification requires fake=True"):
        calibration.run_prompt_calibration(
            development_case=DEVELOPMENT_CASE,
            candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
            holdout_case=HOLDOUT_CASE,
            candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
            adversarial_case=ADVERSARIAL_CASE,
            output_dir=tmp_path,
            model_id="fake-model",
            repetitions=1,
            repo_root=REPO_ROOT,
            skip_seal_verification=True,
            fake=False,
        )


def test_ready_requires_seals_verified() -> None:
    development = _ready_development_aggregate()
    holdout = _ready_holdout_aggregate()

    decision_unverified, diagnostics_unverified = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout],
        seals_verified=False,
    )
    assert decision_unverified == "ITERATE_PROMPT"
    assert any("seals_not_verified" in note for note in diagnostics_unverified)

    decision_verified, diagnostics_verified = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout],
        seals_verified=True,
    )
    assert decision_verified == "PROMPT_READY_FOR_BROADER_SHADOW"
    assert not any("seals_not_verified" in note for note in diagnostics_verified)


def test_manifest_missing_identity_fields_fail_closed(tmp_path: Path) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="development",
        repetition=1,
    )
    _write_success_run(
        run_dir,
        comparison=_comparison_payload(),
        case_id="",
        manifest_extra={"case_id": ""},
    )
    outcome = calibration.load_run_outcome(_spec("candidate", "development", 1), run_dir)
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="candidate",
        cohort="development",
        outcomes=[outcome],
        expected_model_id="fake-model",
        expected_prompt_version="tl01c-v1",
        expected_case_id="expected-case",
        expected_repository_sha="abc123",
    )
    assert not aggregate.manifest_consistency_ok
    joined = "\n".join(aggregate.manifest_diagnostics)
    assert "missing_case_id" in joined
    assert "missing_model_id" in joined
    assert "missing_prompt_version" in joined
    assert "missing_repository_sha" in joined


def test_paired_case_equivalence_accepts_real_dev_and_holdout_pairs() -> None:
    calibration.validate_paired_case_equivalence(
        baseline_case_path=DEVELOPMENT_CASE,
        candidate_case_path=CANDIDATE_DEVELOPMENT_CASE,
        repo_root=REPO_ROOT,
        pair_name="development",
    )
    calibration.validate_paired_case_equivalence(
        baseline_case_path=HOLDOUT_CASE,
        candidate_case_path=CANDIDATE_HOLDOUT_CASE,
        repo_root=REPO_ROOT,
        pair_name="holdout",
    )


def test_holdout_ready_requires_both_temporal_lanes() -> None:
    development = _ready_development_aggregate()
    holdout_missing_valid = _ready_holdout_aggregate(
        occurrence_min=2.0, valid_min=0.0
    )

    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout_missing_valid],
        seals_verified=True,
    )
    assert decision == "ITERATE_PROMPT"
    assert any(
        "holdout_exact_valid_min=0.000" in note or "candidate_quality_insufficient" in note
        for note in diagnostics
    )

    holdout_both_lanes = _ready_holdout_aggregate(occurrence_min=2.0, valid_min=1.0)
    decision_ready, diagnostics_ready = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout_both_lanes],
        seals_verified=True,
    )
    assert decision_ready == "PROMPT_READY_FOR_BROADER_SHADOW"
    assert any("candidate_metrics_met_ready_thresholds" in note for note in diagnostics_ready)


def test_holdout_ready_requires_lane_min_not_max() -> None:
    """One successful repetition must not hide lane failures in the others."""
    development = _ready_development_aggregate()
    holdout_occ_unstable = _ready_holdout_aggregate(
        occurrence_min=0.0,
        occurrence_max=2.0,
        valid_min=1.0,
        valid_max=1.0,
    )
    decision_occ, diagnostics_occ = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout_occ_unstable],
        seals_verified=True,
    )
    assert decision_occ == "ITERATE_PROMPT"
    assert any("holdout_exact_occurrence_min=0.000" in note for note in diagnostics_occ)

    holdout_valid_unstable = _ready_holdout_aggregate(
        occurrence_min=1.0,
        occurrence_max=1.0,
        valid_min=0.0,
        valid_max=2.0,
    )
    decision_valid, diagnostics_valid = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout_valid_unstable],
        seals_verified=True,
    )
    assert decision_valid == "ITERATE_PROMPT"
    assert any("holdout_exact_valid_min=0.000" in note for note in diagnostics_valid)

    holdout_stable = _ready_holdout_aggregate(
        occurrence_min=1.0,
        occurrence_max=2.0,
        valid_min=1.0,
        valid_max=2.0,
    )
    decision_ready, _ = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout_stable],
        seals_verified=True,
    )
    assert decision_ready == "PROMPT_READY_FOR_BROADER_SHADOW"


def test_dev_resolved_qualifying_runs_not_min_proxy() -> None:
    development_two_qualifying = _ready_development_aggregate(
        run_resolved_counts=[3, 1, 3],
    )
    holdout = _ready_holdout_aggregate()
    decision_ok, _ = calibration.compute_calibration_decision(
        cohort_aggregates=[development_two_qualifying, holdout],
        seals_verified=True,
    )
    assert decision_ok == "PROMPT_READY_FOR_BROADER_SHADOW"

    development_one_qualifying = _ready_development_aggregate(
        run_resolved_counts=[3, 1, 1],
    )
    decision_fail, diagnostics_fail = calibration.compute_calibration_decision(
        cohort_aggregates=[development_one_qualifying, holdout],
        seals_verified=True,
    )
    assert decision_fail == "ITERATE_PROMPT"
    assert any(
        "dev_qualifying_resolved_runs=1" in note for note in diagnostics_fail
    )


def test_live_rejects_dirty_worktree(tmp_path: Path) -> None:
    with patch.object(
        calibration,
        "_git_stdout",
        return_value=" M src/graph_memory/temporal_shadow_extraction.py\n",
    ):
        with pytest.raises(calibration.DirtyWorktreeError, match="clean git worktree"):
            calibration.run_prompt_calibration(
                development_case=DEVELOPMENT_CASE,
                candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
                holdout_case=HOLDOUT_CASE,
                candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
                adversarial_case=ADVERSARIAL_CASE,
                output_dir=tmp_path,
                model_id="fake-model",
                repetitions=1,
                repo_root=REPO_ROOT,
                holdout_seal_commit_sha=KNOWN_HOLDOUT_SEAL_COMMIT,
                adversarial_seal_commit_sha=KNOWN_HOLDOUT_SEAL_COMMIT,
                skip_seal_verification=False,
                fake=False,
            )


def test_live_rejects_untracked_nonignored_file() -> None:
    """Non-ignored untracked files must block live execution (no ``-uno``)."""
    probe = REPO_ROOT / ".tl01c_untracked_dirty_check_probe.py"
    assert not probe.exists()
    try:
        probe.write_text("# untracked non-ignored probe\n", encoding="utf-8")
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(probe)],
            cwd=REPO_ROOT,
            check=False,
        )
        assert ignored.returncode == 1  # not ignored
        with pytest.raises(
            calibration.DirtyWorktreeError,
            match="non-ignored untracked",
        ):
            calibration._assert_clean_worktree_for_live(
                repo_root=REPO_ROOT, fake=False
            )
    finally:
        probe.unlink(missing_ok=True)


def test_development_and_baseline_fixtures_tracked_at_head() -> None:
    execution_sha = calibration._repository_sha(repo_root=REPO_ROOT).split("+", 1)[0]
    for case_path in (
        DEVELOPMENT_CASE,
        CANDIDATE_DEVELOPMENT_CASE,
        HOLDOUT_CASE,
    ):
        record = calibration.verify_fixtures_tracked_at_commit(
            case_path=case_path,
            commit_sha=execution_sha,
            repo_root=REPO_ROOT,
        )
        assert record.case_sha256
        assert record.verified_paths
        assert case_path.name in "/".join(record.verified_paths) or any(
            Path(path).name == case_path.name for path in record.verified_paths
        )


def test_expected_case_id_mismatch_fail_closed(tmp_path: Path) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="baseline",
        cohort="development",
        repetition=1,
    )
    _write_success_run(
        run_dir,
        comparison=_comparison_payload(),
        case_id="wrong-case-id",
        manifest_extra={
            "model_id": "fake-model",
            "prompt_version": "tl01b-v1",
            "repository_sha": "abc123",
        },
    )
    outcome = calibration.load_run_outcome(_spec("baseline", "development", 1), run_dir)
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="baseline",
        cohort="development",
        outcomes=[outcome],
        expected_model_id="fake-model",
        expected_prompt_version="tl01b-v1",
        expected_case_id="tl01b-temporal-shadow-cohort-v1",
        expected_repository_sha="abc123",
    )
    assert not aggregate.manifest_consistency_ok
    assert any("case_id_mismatch" in item for item in aggregate.manifest_diagnostics)


def test_baseline_manifest_inconsistency_blocks_ready() -> None:
    development = _ready_development_aggregate()
    holdout = _ready_holdout_aggregate()
    baseline_bad = CalibrationCohortAggregateV1(
        prompt_lane="baseline",
        cohort="development",
        run_count=1,
        success_count=1,
        manifest_consistency_ok=False,
        manifest_diagnostics=["missing_repository_sha repetition=3"],
    )
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[baseline_bad, development, holdout],
        seals_verified=True,
    )
    assert decision == "ITERATE_PROMPT"
    assert any("manifest_inconsistency" in note for note in diagnostics)


def test_provider_revision_mismatch_blocks_ready() -> None:
    development = _ready_development_aggregate()
    holdout = _ready_holdout_aggregate()
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[development, holdout],
        seals_verified=True,
        aggregate_build_sha="aaa111",
        provider_run_repository_shas=["bbb222", "ccc333"],
    )
    assert decision == "ITERATE_PROMPT"
    assert any("provider_run_revision_mismatch" in note for note in diagnostics)


def test_fake_run_records_aggregate_build_and_provider_shas(tmp_path: Path) -> None:
    aggregate = calibration.run_prompt_calibration(
        development_case=DEVELOPMENT_CASE,
        candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
        holdout_case=HOLDOUT_CASE,
        candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
        adversarial_case=ADVERSARIAL_CASE,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=1,
        repo_root=REPO_ROOT,
        skip_seal_verification=True,
        fake=True,
    )
    assert aggregate.aggregate_build_sha
    assert aggregate.repository_sha == aggregate.aggregate_build_sha
    assert aggregate.provider_run_repository_shas == [aggregate.aggregate_build_sha]
    # Every cohort must validate against its exact expected case id.
    expected = {
        ("baseline", "development"): "tl01b-temporal-shadow-cohort-v1",
        ("baseline", "holdout"): "tl01c-temporal-shadow-holdout-v1-baseline",
        ("candidate", "development"): "tl01c-temporal-shadow-cohort-v1",
        ("candidate", "holdout"): "tl01c-temporal-shadow-holdout-v1",
        ("candidate", "adversarial"): "tl01c-temporal-shadow-adversarial-v2",
    }
    for slice_ in aggregate.slices:
        for cohort_agg in slice_.cohort_aggregates:
            key = (cohort_agg.prompt_lane, cohort_agg.cohort)
            assert cohort_agg.case_id == expected[key]
            assert cohort_agg.manifest_consistency_ok, cohort_agg.manifest_diagnostics


def test_ensure_identity_failure_manifest_when_run_dir_empty(tmp_path: Path) -> None:
    spec = calibration.CalibrationRunSpec(
        "candidate",
        "holdout",
        CANDIDATE_HOLDOUT_CASE,
        1,
    )
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="holdout",
        repetition=1,
    )
    calibration._ensure_identity_failure_manifest(
        run_dir=run_dir,
        spec=spec,
        model_id="fake-model",
        repo_root=REPO_ROOT,
        error=None,
    )
    failure = json.loads((run_dir / "failure-manifest.json").read_text(encoding="utf-8"))
    assert failure["case_id"] == "tl01c-temporal-shadow-holdout-v1"
    assert failure["model_id"] == "fake-model"
    assert failure["executed_prompt_version"] == "tl01c-v1"
    assert failure["repository_sha"]
    assert failure["failure_code"] == "unknown_failure"


def test_invalid_model_output_routes_to_iterate_prompt_not_contract() -> None:
    """Ambiguous+extents is model noncompliance; contract already represents the answer."""
    aggregate = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="adversarial",
        run_count=1,
        failure_count=1,
        total_model_output_failures=1,
    )
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[aggregate],
    )
    assert decision == "ITERATE_PROMPT"
    assert any("model_output_failures" in note for note in diagnostics)
    assert decision != "BLOCKED_BY_CONTRACT"


def test_true_contract_gap_still_blocked_by_contract() -> None:
    aggregate = CalibrationCohortAggregateV1(
        prompt_lane="candidate",
        cohort="development",
        run_count=1,
        failure_count=1,
        total_invalid_payloads=1,
    )
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[aggregate],
    )
    assert decision == "BLOCKED_BY_CONTRACT"
    assert any("invalid_payloads" in note for note in diagnostics)


def test_aggregate_counts_invalid_model_output_as_model_output_failure(
    tmp_path: Path,
) -> None:
    run_dir = calibration._lane_run_dir(
        output_dir=tmp_path,
        prompt_lane="candidate",
        cohort="adversarial",
        repetition=1,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "failure-manifest.json").write_text(
        json.dumps(
            {
                "schema": "dmb_temporal_shadow_extraction_failure_v1",
                "case_id": "tl01c-temporal-shadow-adversarial-v2",
                "case_digest": "a" * 64,
                "model_id": "fake-model",
                "executed_prompt_version": "tl01c-v1",
                "prompt_version": "tl01c-v1",
                "failure_code": "invalid_model_output",
                "diagnostics": ["ambiguous must not include occurrence_time"],
                "repository_sha": "deadbeef",
                "provider_response_id": "resp_preserved_123",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = calibration.load_run_outcome(
        _spec("candidate", "adversarial", 1), run_dir
    )
    aggregate = calibration.aggregate_cohort_runs(
        prompt_lane="candidate",
        cohort="adversarial",
        outcomes=[outcome],
        expected_case_id="tl01c-temporal-shadow-adversarial-v2",
        expected_model_id="fake-model",
        expected_prompt_version="tl01c-v1",
        expected_repository_sha="deadbeef",
    )
    assert aggregate.total_model_output_failures == 1
    assert aggregate.total_invalid_payloads == 0
    assert aggregate.run_records[0].provider_response_id == "resp_preserved_123"
    decision, diagnostics = calibration.compute_calibration_decision(
        cohort_aggregates=[aggregate],
    )
    assert decision == "ITERATE_PROMPT"
    assert any("model_output_failures" in note for note in diagnostics)


def test_historical_tl01c_fake_run_derives_tl01c_candidate_version(
    tmp_path: Path,
) -> None:
    aggregate = _run_fake_calibration(tmp_path)
    assert aggregate.baseline_prompt_version == "tl01b-v1"
    assert aggregate.candidate_prompt_version == "tl01c-v1"
    candidate_slice = next(
        slice_ for slice_ in aggregate.slices if slice_.prompt_lane == "candidate"
    )
    assert candidate_slice.prompt_version == "tl01c-v1"


def test_mixed_candidate_prompt_versions_fail_before_provider(
    tmp_path: Path,
) -> None:
    mixed_holdout = _case_copy_with_prompt_version(
        CANDIDATE_HOLDOUT_CASE,
        tmp_path / "candidate-holdout-tl01d.json",
        prompt_version="tl01d-v1",
        case_id="tl01d-temporal-shadow-holdout-v1",
    )
    with patch.object(calibration, "run_calibration_repetition") as mock_run:
        with pytest.raises(
            calibration.PromptVersionMismatchError,
            match="candidate cases must share one prompt_version",
        ):
            calibration.run_prompt_calibration(
                development_case=DEVELOPMENT_CASE,
                candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
                holdout_case=HOLDOUT_CASE,
                candidate_holdout_case=mixed_holdout,
                adversarial_case=ADVERSARIAL_CASE,
                output_dir=tmp_path,
                model_id="fake-model",
                repetitions=1,
                repo_root=REPO_ROOT,
                skip_seal_verification=True,
                fake=True,
            )
        mock_run.assert_not_called()


def test_mixed_control_prompt_versions_fail_before_provider(
    tmp_path: Path,
) -> None:
    mixed_holdout = _case_copy_with_prompt_version(
        HOLDOUT_CASE,
        tmp_path / "holdout-tl01c-control.json",
        prompt_version="tl01c-v1",
    )
    with patch.object(calibration, "run_calibration_repetition") as mock_run:
        with pytest.raises(
            calibration.PromptVersionMismatchError,
            match="control cases must share one prompt_version",
        ):
            calibration.run_prompt_calibration(
                development_case=DEVELOPMENT_CASE,
                candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
                holdout_case=mixed_holdout,
                candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
                adversarial_case=ADVERSARIAL_CASE,
                output_dir=tmp_path,
                model_id="fake-model",
                repetitions=1,
                repo_root=REPO_ROOT,
                skip_seal_verification=True,
                fake=True,
            )
        mock_run.assert_not_called()


@patch.object(calibration, "run_calibration_repetition")
def test_baseline_adversarial_adds_sixth_lane(
    mock_repetition: Any, tmp_path: Path
) -> None:
    baseline_adv = _baseline_adversarial_mirror(tmp_path)

    def side_effect(
        spec: calibration.CalibrationRunSpec, **kwargs: Any
    ) -> calibration.RunOutcome:
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
        development_case=DEVELOPMENT_CASE,
        candidate_development_case=CANDIDATE_DEVELOPMENT_CASE,
        holdout_case=HOLDOUT_CASE,
        candidate_holdout_case=CANDIDATE_HOLDOUT_CASE,
        adversarial_case=ADVERSARIAL_CASE,
        baseline_adversarial_case=baseline_adv,
        output_dir=tmp_path,
        model_id="fake-model",
        repetitions=2,
        repo_root=REPO_ROOT,
        skip_seal_verification=True,
        fake=True,
    )
    assert mock_repetition.call_count == 12
    assert (
        tmp_path / "calibration" / "baseline" / "adversarial" / "run-01"
    ).is_dir()


def test_aggregate_records_derived_prompt_versions(tmp_path: Path) -> None:
    aggregate = _run_fake_calibration(tmp_path)
    assert aggregate.baseline_prompt_version == "tl01b-v1"
    assert aggregate.candidate_prompt_version == "tl01c-v1"
    baseline_slice = next(
        slice_ for slice_ in aggregate.slices if slice_.prompt_lane == "baseline"
    )
    assert baseline_slice.prompt_version == "tl01b-v1"


def test_calibration_id_changes_when_candidate_prompt_version_changes(
    tmp_path: Path,
) -> None:
    tl01d_dev = _case_copy_with_prompt_version(
        CANDIDATE_DEVELOPMENT_CASE,
        tmp_path / "dev-tl01d.json",
        prompt_version="tl01d-v1",
        case_id="tl01d-temporal-shadow-cohort-v1",
    )
    tl01d_holdout = _case_copy_with_prompt_version(
        CANDIDATE_HOLDOUT_CASE,
        tmp_path / "holdout-tl01d.json",
        prompt_version="tl01d-v1",
        case_id="tl01d-temporal-shadow-holdout-v1",
    )
    tl01d_adv = _case_copy_with_prompt_version(
        ADVERSARIAL_CASE,
        tmp_path / "adv-tl01d.json",
        prompt_version="tl01d-v1",
    )
    tl01c_control_holdout = _case_copy_with_prompt_version(
        HOLDOUT_CASE,
        tmp_path / "holdout-tl01c-control.json",
        prompt_version="tl01c-v1",
        case_id="tl01c-temporal-shadow-holdout-v1-baseline",
    )
    aggregate_tl01c = _run_fake_calibration(tmp_path / "tl01c")
    aggregate_tl01d = _run_fake_calibration(
        tmp_path / "tl01d",
        candidate_development_case=tl01d_dev,
        candidate_holdout_case=tl01d_holdout,
        adversarial_case=tl01d_adv,
    )

    tl01c_control_dev = _case_copy_with_prompt_version(
        CANDIDATE_DEVELOPMENT_CASE,
        tmp_path / "dev-tl01c-control.json",
        prompt_version="tl01c-v1",
        case_id="tl01c-temporal-shadow-cohort-v1",
    )

    def side_effect(
        spec: calibration.CalibrationRunSpec, **kwargs: Any
    ) -> calibration.RunOutcome:
        run_dir = calibration._lane_run_dir(
            output_dir=kwargs["output_dir"],
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        _write_success_run(run_dir, comparison=_comparison_payload())
        return calibration.load_run_outcome(spec, run_dir)

    with patch.object(calibration, "run_calibration_repetition", side_effect=side_effect):
        aggregate_tl01d_control = calibration.run_prompt_calibration(
            development_case=tl01c_control_dev,
            candidate_development_case=tl01d_dev,
            holdout_case=tl01c_control_holdout,
            candidate_holdout_case=tl01d_holdout,
            adversarial_case=tl01d_adv,
            output_dir=tmp_path / "tl01d-control",
            model_id="fake-model",
            repetitions=1,
            repo_root=REPO_ROOT,
            skip_seal_verification=True,
            fake=True,
        )
    assert aggregate_tl01c.calibration_id != aggregate_tl01d.calibration_id
    assert aggregate_tl01d.calibration_id != aggregate_tl01d_control.calibration_id
    assert aggregate_tl01d.candidate_prompt_version == "tl01d-v1"
    assert aggregate_tl01d_control.baseline_prompt_version == "tl01c-v1"

