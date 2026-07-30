"""TL01C temporal prompt calibration runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    TemporalShadowExtractionError,
    compute_prompt_sha256,
    load_temporal_shadow_extraction_case,
    run_temporal_shadow_extraction,
)
from graph_memory.temporal_shadow_extraction_schema import (
    TEMPORAL_SHADOW_PROMPT_VERSION,
    CalibrationAssertionStabilityV1,
    CalibrationCohortAggregateV1,
    CalibrationDecision,
    CalibrationMetricDistributionV1,
    CalibrationRunRecordV1,
    TemporalPromptCalibrationAggregateV1,
    TemporalPromptCalibrationMetricsSliceV1,
)

PromptLane = Literal["baseline", "candidate"]
CohortName = Literal["development", "holdout", "adversarial"]

PROVIDER_FAILURE_CODES = frozenset(
    {"provider_refusal", "provider_incomplete", "provider_error"}
)
CONTRACT_FAILURE_CODES = frozenset(
    {"invalid_model_output", "overlay_assembly_failed", "unsupported_prompt_version"}
)
EVIDENCE_FAILURE_CODES = frozenset(
    {"evidence_unresolved", "digest_mismatch", "invalid_case", "invalid_gold_overlay"}
)
GROUNDING_FAILURE_CODE = "grounding_failure"

# Handoff READY thresholds (development + holdout).
READY_DEV_MEDIAN_EXACT_MATCHES = 4  # of 6 development gold rows
READY_DEV_RESOLVED_EXACT_MATCHES = 2  # of 3 resolved gold rows
READY_DEV_RESOLVED_EXACT_RUNS = 2  # at least two development runs
READY_MIN_HOLDOUT_STATUS_ACCURACY = 0.80
READY_MIN_NOT_APPLICABLE_ACCURACY = 1.0

INPUT_REP_MIN_WRONG_TEMPORAL_VALUE = 2


@dataclass(frozen=True)
class CalibrationRunSpec:
    prompt_lane: PromptLane
    cohort: CohortName
    case_path: Path
    repetition: int


@dataclass(frozen=True)
class RunOutcome:
    spec: CalibrationRunSpec
    run_dir: Path
    succeeded: bool
    failure_code: str | None = None
    comparison: dict[str, Any] | None = None
    run_manifest: dict[str, Any] | None = None
    failure_manifest: dict[str, Any] | None = None
    overlay: dict[str, Any] | None = None


@dataclass(frozen=True)
class CohortSealRecord:
    case_sha256: str
    base_sha256: str
    gold_sha256: str
    seal_commit_sha: str
    case_id: str
    verified_paths: tuple[str, ...]


class CohortSealError(ValueError):
    """Holdout/adversarial seal verification failed."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _normalize_temporal_value(value: Any) -> str:
    if value is None:
        return "null"
    return _canonical_json(value)


def _repository_sha(*, repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_stdout(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_ok(repo_root: Path, *args: str) -> bool:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _blob_sha256_at_commit(repo_root: Path, commit: str, rel_path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{rel_path}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError as exc:
        raise CohortSealError(f"path outside repository: {path}") from exc


def verify_cohort_seal(
    *,
    case_path: Path,
    seal_commit_sha: str,
    repo_root: Path,
    execution_commit_sha: str | None = None,
) -> CohortSealRecord:
    """Verify case/base/gold/evidence digests against a sealing commit."""
    if not seal_commit_sha or not seal_commit_sha.strip():
        raise CohortSealError("seal_commit_sha is required")
    seal = seal_commit_sha.strip()
    if not _git_ok(repo_root, "cat-file", "-e", f"{seal}^{{commit}}"):
        raise CohortSealError(f"seal commit does not exist: {seal}")

    execution = execution_commit_sha or _repository_sha(repo_root=repo_root)
    if execution == "unknown":
        raise CohortSealError("cannot resolve execution commit SHA")
    if not _git_ok(repo_root, "merge-base", "--is-ancestor", seal, execution):
        raise CohortSealError(
            f"seal commit {seal} is not an ancestor of execution commit {execution}"
        )

    case = load_temporal_shadow_extraction_case(case_path, repo_root=repo_root)
    case_rel = _repo_relative(case_path, repo_root=repo_root)
    base_rel = case.base_contribution_path
    gold_rel = case.gold_overlay_path
    base_path = repo_root / base_rel
    gold_path = repo_root / gold_rel

    case_sha = _file_sha256(case_path)
    base_sha = _file_sha256(base_path)
    gold_sha = _file_sha256(gold_path)

    if case.base_contribution_sha256 != base_sha:
        raise CohortSealError(
            "case.base_contribution_sha256 does not match executed base file "
            f"(declared={case.base_contribution_sha256} actual={base_sha})"
        )
    if case.gold_overlay_sha256 != gold_sha:
        raise CohortSealError(
            "case.gold_overlay_sha256 does not match executed gold file "
            f"(declared={case.gold_overlay_sha256} actual={gold_sha})"
        )

    verified: list[str] = [case_rel, base_rel, gold_rel]
    for entry in case.evidence_registry:
        verified.append(entry.source_artifact_path)

    for rel in verified:
        worktree_path = repo_root / rel
        if not worktree_path.is_file():
            raise CohortSealError(f"missing sealed fixture path: {rel}")
        worktree_sha = _file_sha256(worktree_path)
        try:
            sealed_sha = _blob_sha256_at_commit(repo_root, seal, rel)
        except subprocess.CalledProcessError as exc:
            raise CohortSealError(
                f"seal commit {seal} does not contain fixture path {rel}"
            ) from exc
        if worktree_sha != sealed_sha:
            raise CohortSealError(
                f"executed fixture {rel} does not match seal commit {seal} "
                f"(worktree={worktree_sha} sealed={sealed_sha})"
            )

    return CohortSealRecord(
        case_sha256=case_sha,
        base_sha256=base_sha,
        gold_sha256=gold_sha,
        seal_commit_sha=_git_stdout(repo_root, "rev-parse", seal),
        case_id=case.case_id,
        verified_paths=tuple(verified),
    )


def _distribution(values: list[float | int]) -> CalibrationMetricDistributionV1:
    if not values:
        return CalibrationMetricDistributionV1(min=0.0, median=0.0, max=0.0)
    floats = [float(v) for v in values]
    return CalibrationMetricDistributionV1(
        min=min(floats),
        median=float(statistics.median(floats)),
        max=max(floats),
    )


def _lane_run_dir(
    *,
    output_dir: Path,
    prompt_lane: PromptLane,
    cohort: CohortName,
    repetition: int,
) -> Path:
    return (
        output_dir
        / "calibration"
        / prompt_lane
        / cohort
        / f"run-{repetition:02d}"
    )


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_run_outcome(spec: CalibrationRunSpec, run_dir: Path) -> RunOutcome:
    comparison = _load_json_if_exists(run_dir / "comparison.json")
    run_manifest = _load_json_if_exists(run_dir / "run-manifest.json")
    failure_manifest = _load_json_if_exists(run_dir / "failure-manifest.json")
    overlay = _load_json_if_exists(run_dir / "overlay.json")
    succeeded = comparison is not None and run_manifest is not None
    failure_code = None
    if failure_manifest is not None:
        failure_code = str(failure_manifest.get("failure_code") or "")
    return RunOutcome(
        spec=spec,
        run_dir=run_dir,
        succeeded=succeeded,
        failure_code=failure_code,
        comparison=comparison,
        run_manifest=run_manifest,
        failure_manifest=failure_manifest,
        overlay=overlay,
    )


def _comparison_metrics(comparison: dict[str, Any] | None) -> dict[str, Any]:
    if comparison is None:
        return {}
    metrics = comparison.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _classification_counts(comparison: dict[str, Any] | None) -> Counter[str]:
    if comparison is None:
        return Counter()
    rows = comparison.get("rows")
    if not isinstance(rows, list):
        return Counter()
    counts: Counter[str] = Counter()
    for row in rows:
        if isinstance(row, dict):
            classification = row.get("classification")
            if isinstance(classification, str):
                counts[classification] += 1
    return counts


def _resolved_gold_count(comparison: dict[str, Any] | None) -> int:
    if comparison is None:
        return 0
    rows = comparison.get("rows")
    if not isinstance(rows, list):
        return 0
    return sum(
        1
        for row in rows
        if isinstance(row, dict) and row.get("gold_interpretation_status") == "resolved"
    )


def _overlay_temporal_norms(
    overlay: dict[str, Any] | None,
) -> dict[str, tuple[str, str]]:
    """Map assertion_id -> (occurrence_norm, valid_time_norm)."""
    if overlay is None:
        return {}
    annotations = overlay.get("annotations")
    if not isinstance(annotations, list):
        return {}
    out: dict[str, tuple[str, str]] = {}
    for item in annotations:
        if not isinstance(item, dict):
            continue
        assertion_id = item.get("base_assertion_id")
        if not isinstance(assertion_id, str):
            continue
        out[assertion_id] = (
            _normalize_temporal_value(item.get("occurrence_time")),
            _normalize_temporal_value(item.get("valid_time")),
        )
    return out


def _validate_manifest_consistency(
    *,
    outcomes: list[RunOutcome],
    expected_model_id: str | None = None,
    expected_prompt_version: str | None = None,
    expected_case_id: str | None = None,
    expected_repository_sha: str | None = None,
) -> tuple[bool, list[str], str | None]:
    diagnostics: list[str] = []
    case_ids: set[str] = set()
    model_ids: set[str] = set()
    prompt_versions: set[str] = set()
    repo_shas: set[str] = set()
    repetitions: list[int] = []

    for outcome in outcomes:
        repetitions.append(outcome.spec.repetition)
        manifest = outcome.run_manifest if outcome.succeeded else None
        failure = outcome.failure_manifest
        payload = manifest or failure or {}
        case_id = payload.get("case_id")
        model_id = payload.get("model_id")
        prompt_version = payload.get("prompt_version") or payload.get(
            "executed_prompt_version"
        )
        repository_sha = payload.get("repository_sha")
        if isinstance(case_id, str) and case_id:
            case_ids.add(case_id)
        if isinstance(model_id, str) and model_id:
            model_ids.add(model_id)
        if isinstance(prompt_version, str) and prompt_version:
            prompt_versions.add(prompt_version)
        if isinstance(repository_sha, str) and repository_sha:
            repo_shas.add(repository_sha)

    if len(set(repetitions)) != len(repetitions):
        diagnostics.append("duplicate_repetition_identity")
    if len(case_ids) > 1:
        diagnostics.append(f"inconsistent_case_ids={sorted(case_ids)}")
    if len(model_ids) > 1:
        diagnostics.append(f"inconsistent_model_ids={sorted(model_ids)}")
    if len(prompt_versions) > 1:
        diagnostics.append(f"inconsistent_prompt_versions={sorted(prompt_versions)}")
    if len(repo_shas) > 1:
        diagnostics.append(f"inconsistent_repository_shas={sorted(repo_shas)}")

    observed_case = next(iter(case_ids), None)
    if expected_case_id and observed_case and observed_case != expected_case_id:
        diagnostics.append(
            f"case_id_mismatch expected={expected_case_id} observed={observed_case}"
        )
    if expected_model_id and model_ids and expected_model_id not in model_ids:
        diagnostics.append(
            f"model_id_mismatch expected={expected_model_id} observed={sorted(model_ids)}"
        )
    if (
        expected_prompt_version
        and prompt_versions
        and expected_prompt_version not in prompt_versions
    ):
        diagnostics.append(
            "prompt_version_mismatch "
            f"expected={expected_prompt_version} observed={sorted(prompt_versions)}"
        )
    if (
        expected_repository_sha
        and repo_shas
        and expected_repository_sha not in repo_shas
    ):
        diagnostics.append(
            "repository_sha_mismatch "
            f"expected={expected_repository_sha} observed={sorted(repo_shas)}"
        )

    return (not diagnostics), diagnostics, observed_case


def aggregate_cohort_runs(
    *,
    prompt_lane: PromptLane,
    cohort: CohortName,
    outcomes: list[RunOutcome],
    expected_model_id: str | None = None,
    expected_prompt_version: str | None = None,
    expected_case_id: str | None = None,
    expected_repository_sha: str | None = None,
) -> CalibrationCohortAggregateV1:
    exact_values: list[int] = []
    resolved_exact_values: list[int] = []
    status_accuracies: list[float] = []
    not_applicable_accuracies: list[float] = []

    total_unsafe = 0
    total_source_occ = 0
    total_source_valid = 0
    total_evidence_mismatch = 0
    total_evidence_or_case_failures = 0
    total_provider_failures = 0
    total_grounding_failures = 0
    total_invalid_payloads = 0
    total_wrong_value = 0
    total_wrong_lane = 0
    total_status_mismatch = 0
    exact_match_ratios: list[float] = []
    resolved_exact_ratios: list[float] = []

    classification_by_assertion: dict[str, Counter[str]] = defaultdict(Counter)
    status_by_assertion: dict[str, Counter[str]] = defaultdict(Counter)
    occurrence_by_assertion: dict[str, Counter[str]] = defaultdict(Counter)
    valid_by_assertion: dict[str, Counter[str]] = defaultdict(Counter)
    failure_by_assertion: dict[str, Counter[str]] = defaultdict(Counter)

    # Collect assertion ids seen across successes so failures can be attributed.
    known_assertion_ids: set[str] = set()

    success_count = 0
    failure_count = 0
    run_records: list[CalibrationRunRecordV1] = []

    consistent, manifest_diagnostics, observed_case_id = _validate_manifest_consistency(
        outcomes=outcomes,
        expected_model_id=expected_model_id,
        expected_prompt_version=expected_prompt_version,
        expected_case_id=expected_case_id,
        expected_repository_sha=expected_repository_sha,
    )

    for outcome in outcomes:
        metrics = _comparison_metrics(outcome.comparison)
        manifest = outcome.run_manifest or {}
        failure = outcome.failure_manifest or {}
        payload = manifest if outcome.succeeded else failure
        record_diags: list[str] = []
        if not consistent:
            record_diags.extend(manifest_diagnostics)

        if outcome.succeeded:
            success_count += 1
            exact_values.append(int(metrics.get("exact_match_count") or 0))
            resolved_exact_values.append(
                int(metrics.get("resolved_exact_match_count") or 0)
            )
            status_accuracies.append(float(metrics.get("status_accuracy") or 0.0))
            not_applicable_accuracies.append(
                float(metrics.get("not_applicable_accuracy") or 0.0)
            )
            total_unsafe += int(metrics.get("unsafe_over_resolution_count") or 0)
            total_source_occ += int(
                metrics.get("source_to_occurrence_false_positives") or 0
            )
            total_source_valid += int(
                metrics.get("source_to_valid_time_false_positives") or 0
            )
            total_evidence_mismatch += int(
                metrics.get("evidence_selection_mismatch_count") or 0
            )
            total_invalid_payloads += int(metrics.get("invalid_temporal_payloads") or 0)
            total_gold = int(metrics.get("total_gold_annotations") or 0)
            resolved_gold = _resolved_gold_count(outcome.comparison)
            if total_gold > 0:
                exact_match_ratios.append(
                    int(metrics.get("exact_match_count") or 0) / total_gold
                )
            if resolved_gold > 0:
                resolved_exact_ratios.append(
                    int(metrics.get("resolved_exact_match_count") or 0) / resolved_gold
                )
            total_wrong_value += _classification_counts(outcome.comparison)[
                "wrong_temporal_value"
            ]
            total_wrong_lane += _classification_counts(outcome.comparison)[
                "wrong_temporal_lane"
            ]
            total_status_mismatch += int(metrics.get("status_mismatch_count") or 0)

            norms = _overlay_temporal_norms(outcome.overlay)
            rows = outcome.comparison.get("rows") if outcome.comparison else []
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    assertion_id = row.get("base_assertion_id")
                    classification = row.get("classification")
                    status = row.get("predicted_interpretation_status")
                    if isinstance(assertion_id, str):
                        known_assertion_ids.add(assertion_id)
                        if isinstance(classification, str):
                            classification_by_assertion[assertion_id][
                                classification
                            ] += 1
                        if isinstance(status, str):
                            status_by_assertion[assertion_id][status] += 1
                        if assertion_id in norms:
                            occ_norm, valid_norm = norms[assertion_id]
                            occurrence_by_assertion[assertion_id][occ_norm] += 1
                            valid_by_assertion[assertion_id][valid_norm] += 1

            run_records.append(
                CalibrationRunRecordV1(
                    prompt_lane=prompt_lane,
                    cohort=cohort,
                    repetition=outcome.spec.repetition,
                    succeeded=True,
                    case_id=str(payload.get("case_id") or "") or None,
                    model_id=str(payload.get("model_id") or "") or None,
                    prompt_version=str(
                        payload.get("prompt_version")
                        or payload.get("executed_prompt_version")
                        or ""
                    )
                    or None,
                    repository_sha=str(payload.get("repository_sha") or "") or None,
                    run_id=str(payload.get("run_id") or "") or None,
                    provider_response_id=str(payload.get("provider_response_id") or "")
                    or None,
                    exact_match_count=int(metrics.get("exact_match_count") or 0),
                    resolved_exact_match_count=int(
                        metrics.get("resolved_exact_match_count") or 0
                    ),
                    status_accuracy=float(metrics.get("status_accuracy") or 0.0),
                    not_applicable_accuracy=float(
                        metrics.get("not_applicable_accuracy") or 0.0
                    ),
                    unsafe_over_resolution_count=int(
                        metrics.get("unsafe_over_resolution_count") or 0
                    ),
                    source_to_occurrence_false_positives=int(
                        metrics.get("source_to_occurrence_false_positives") or 0
                    ),
                    source_to_valid_time_false_positives=int(
                        metrics.get("source_to_valid_time_false_positives") or 0
                    ),
                    evidence_selection_mismatch_count=int(
                        metrics.get("evidence_selection_mismatch_count") or 0
                    ),
                    manifest_consistent=consistent,
                    manifest_diagnostics=list(record_diags),
                )
            )
        else:
            failure_count += 1
            code = outcome.failure_code or "unknown_failure"
            if code in PROVIDER_FAILURE_CODES:
                total_provider_failures += 1
            elif code == GROUNDING_FAILURE_CODE:
                total_grounding_failures += 1
            elif code in CONTRACT_FAILURE_CODES:
                total_invalid_payloads += 1
            elif code in EVIDENCE_FAILURE_CODES:
                total_evidence_or_case_failures += 1

            # Attribute failures to known assertions once discovered.
            for assertion_id in sorted(known_assertion_ids):
                classification_by_assertion[assertion_id]["run_failed"] += 1
                failure_by_assertion[assertion_id][code] += 1

            run_records.append(
                CalibrationRunRecordV1(
                    prompt_lane=prompt_lane,
                    cohort=cohort,
                    repetition=outcome.spec.repetition,
                    succeeded=False,
                    case_id=str(payload.get("case_id") or "") or None,
                    model_id=str(payload.get("model_id") or "") or None,
                    prompt_version=str(
                        payload.get("prompt_version")
                        or payload.get("executed_prompt_version")
                        or ""
                    )
                    or None,
                    repository_sha=str(payload.get("repository_sha") or "") or None,
                    run_id=str(payload.get("run_id") or "") or None,
                    failure_code=code,
                    manifest_consistent=consistent,
                    manifest_diagnostics=list(record_diags),
                )
            )

    # Second pass: if failures came before successes, re-attribute using final known set.
    if failure_count and known_assertion_ids:
        # Rebuild failure attribution cleanly from outcomes order.
        classification_by_assertion = defaultdict(Counter)
        status_by_assertion = defaultdict(Counter)
        occurrence_by_assertion = defaultdict(Counter)
        valid_by_assertion = defaultdict(Counter)
        failure_by_assertion = defaultdict(Counter)
        for outcome in outcomes:
            if outcome.succeeded:
                norms = _overlay_temporal_norms(outcome.overlay)
                rows = outcome.comparison.get("rows") if outcome.comparison else []
                if isinstance(rows, list):
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        assertion_id = row.get("base_assertion_id")
                        classification = row.get("classification")
                        status = row.get("predicted_interpretation_status")
                        if isinstance(assertion_id, str):
                            if isinstance(classification, str):
                                classification_by_assertion[assertion_id][
                                    classification
                                ] += 1
                            if isinstance(status, str):
                                status_by_assertion[assertion_id][status] += 1
                            if assertion_id in norms:
                                occ_norm, valid_norm = norms[assertion_id]
                                occurrence_by_assertion[assertion_id][occ_norm] += 1
                                valid_by_assertion[assertion_id][valid_norm] += 1
            else:
                code = outcome.failure_code or "unknown_failure"
                for assertion_id in sorted(known_assertion_ids):
                    classification_by_assertion[assertion_id]["run_failed"] += 1
                    failure_by_assertion[assertion_id][code] += 1

    assertion_ids = sorted(
        set(classification_by_assertion)
        | set(status_by_assertion)
        | set(occurrence_by_assertion)
        | set(valid_by_assertion)
        | set(failure_by_assertion)
    )
    assertion_stability = [
        CalibrationAssertionStabilityV1(
            base_assertion_id=assertion_id,
            classification_counts=dict(
                sorted(classification_by_assertion[assertion_id].items())
            ),
            status_counts=dict(sorted(status_by_assertion[assertion_id].items())),
            occurrence_normalized_counts=dict(
                sorted(occurrence_by_assertion[assertion_id].items())
            ),
            valid_time_normalized_counts=dict(
                sorted(valid_by_assertion[assertion_id].items())
            ),
            failure_counts=dict(sorted(failure_by_assertion[assertion_id].items())),
        )
        for assertion_id in assertion_ids
    ]

    return CalibrationCohortAggregateV1(
        prompt_lane=prompt_lane,
        cohort=cohort,
        case_id=observed_case_id or expected_case_id,
        run_count=len(outcomes),
        success_count=success_count,
        failure_count=failure_count,
        exact_match=_distribution(exact_values),
        resolved_exact_match=_distribution(resolved_exact_values),
        min_status_accuracy=min(status_accuracies) if status_accuracies else 0.0,
        min_not_applicable_accuracy=(
            min(not_applicable_accuracies) if not_applicable_accuracies else 0.0
        ),
        total_unsafe_over_resolution=total_unsafe,
        total_source_to_occurrence_false_positives=total_source_occ,
        total_source_to_valid_time_false_positives=total_source_valid,
        total_source_leakage_false_positives=total_source_occ + total_source_valid,
        total_evidence_selection_mismatches=total_evidence_mismatch,
        total_evidence_or_case_failures=total_evidence_or_case_failures,
        total_provider_failures=total_provider_failures,
        total_grounding_failures=total_grounding_failures,
        total_invalid_payloads=total_invalid_payloads,
        total_wrong_temporal_value=total_wrong_value,
        total_wrong_temporal_lane=total_wrong_lane,
        total_status_mismatch=total_status_mismatch,
        min_exact_match_ratio=min(exact_match_ratios) if exact_match_ratios else 0.0,
        min_resolved_exact_ratio=(
            min(resolved_exact_ratios) if resolved_exact_ratios else 0.0
        ),
        assertion_stability=assertion_stability,
        run_records=sorted(run_records, key=lambda item: item.repetition),
        manifest_consistency_ok=consistent,
        manifest_diagnostics=manifest_diagnostics,
    )


def compute_calibration_decision(
    *,
    candidate_aggregates: list[CalibrationCohortAggregateV1],
    diagnostics: list[str] | None = None,
) -> tuple[CalibrationDecision, list[str]]:
    notes = list(diagnostics or [])
    candidate = [a for a in candidate_aggregates if a.prompt_lane == "candidate"]
    holdout = next((a for a in candidate if a.cohort == "holdout"), None)

    total_provider = sum(a.total_provider_failures for a in candidate)
    if total_provider > 0:
        notes.append(f"candidate_provider_failures={total_provider}")
        return "PROVIDER_FAILURE", notes

    total_contract = sum(a.total_invalid_payloads for a in candidate)
    if total_contract > 0:
        notes.append(f"candidate_invalid_payloads={total_contract}")
        return "BLOCKED_BY_CONTRACT", notes

    total_evidence_case = sum(a.total_evidence_or_case_failures for a in candidate)
    if total_evidence_case > 0:
        notes.append(f"candidate_evidence_or_case_failures={total_evidence_case}")
        return "BLOCKED_BY_EVIDENCE", notes

    # Safety findings before input-representation heuristic.
    total_unsafe = sum(a.total_unsafe_over_resolution for a in candidate)
    if total_unsafe > 0:
        notes.append(f"candidate_unsafe_over_resolution={total_unsafe}")
        return "ITERATE_PROMPT", notes

    total_source_leakage = sum(a.total_source_leakage_false_positives for a in candidate)
    if total_source_leakage > 0:
        notes.append(f"candidate_source_leakage={total_source_leakage}")
        return "ITERATE_PROMPT", notes

    total_grounding = sum(a.total_grounding_failures for a in candidate)
    if total_grounding > 0:
        # Phrase grounding misses are prompt/model quality unless spans are unusable
        # (those land in evidence_or_case_failures → BLOCKED_BY_EVIDENCE above).
        notes.append(f"candidate_grounding_failures={total_grounding}")
        return "ITERATE_PROMPT", notes

    total_wrong_value = sum(a.total_wrong_temporal_value for a in candidate)
    total_wrong_lane = sum(a.total_wrong_temporal_lane for a in candidate)
    total_status_mismatch = sum(a.total_status_mismatch for a in candidate)
    if (
        total_wrong_value >= INPUT_REP_MIN_WRONG_TEMPORAL_VALUE
        and total_wrong_lane == 0
        and total_status_mismatch == 0
    ):
        notes.append(
            "wrong_temporal_value_dominates_with_correct_status_and_lane="
            f"{total_wrong_value}"
        )
        return "BLOCKED_BY_INPUT_REPRESENTATION", notes

    development = next((a for a in candidate if a.cohort == "development"), None)
    if holdout is None:
        notes.append("missing_candidate_holdout_aggregate")
        return "ITERATE_PROMPT", notes
    if development is None:
        notes.append("missing_candidate_development_aggregate")
        return "ITERATE_PROMPT", notes

    if any(a.failure_count > 0 for a in candidate):
        notes.append("candidate_has_failed_runs")
        return "ITERATE_PROMPT", notes

    if any(not a.manifest_consistency_ok for a in candidate):
        notes.append("candidate_manifest_inconsistency")
        return "ITERATE_PROMPT", notes

    dev_exact = development.exact_match
    dev_resolved = development.resolved_exact_match
    median_exact = float(dev_exact.median) if dev_exact is not None else 0.0
    resolved_runs_ok = (
        development.success_count >= READY_DEV_RESOLVED_EXACT_RUNS
        and dev_resolved is not None
        and float(dev_resolved.min) >= READY_DEV_RESOLVED_EXACT_MATCHES
    )
    min_not_applicable = min(
        (a.min_not_applicable_accuracy for a in candidate if a.success_count),
        default=0.0,
    )
    holdout_status_ok = holdout.min_status_accuracy >= READY_MIN_HOLDOUT_STATUS_ACCURACY
    holdout_resolved = holdout.resolved_exact_match
    holdout_has_occurrence_and_valid = (
        holdout_resolved is not None and float(holdout_resolved.min) >= 2.0
    )

    ready = (
        median_exact >= READY_DEV_MEDIAN_EXACT_MATCHES
        and resolved_runs_ok
        and min_not_applicable >= READY_MIN_NOT_APPLICABLE_ACCURACY
        and holdout_status_ok
        and holdout_has_occurrence_and_valid
    )
    if ready:
        notes.append("candidate_metrics_met_ready_thresholds")
        return "PROMPT_READY_FOR_BROADER_SHADOW", notes

    notes.append(
        "candidate_quality_insufficient "
        f"(dev_median_exact={median_exact:.3f}, "
        f"dev_resolved_min="
        f"{(float(dev_resolved.min) if dev_resolved is not None else 0.0):.3f}, "
        f"min_not_applicable={min_not_applicable:.3f}, "
        f"holdout_status={holdout.min_status_accuracy:.3f}, "
        f"holdout_resolved_min="
        f"{(float(holdout_resolved.min) if holdout_resolved is not None else 0.0):.3f})"
    )
    return "ITERATE_PROMPT", notes


def _build_metrics_slice(
    *,
    prompt_lane: PromptLane,
    prompt_version: str,
    cohort_aggregates: list[CalibrationCohortAggregateV1],
) -> TemporalPromptCalibrationMetricsSliceV1:
    lane_aggregates = [a for a in cohort_aggregates if a.prompt_lane == prompt_lane]
    pass_count = 0
    partial_count = 0
    fail_count = 0
    blocked_count = 0
    case_ids: list[str] = []
    for aggregate in lane_aggregates:
        if aggregate.case_id and aggregate.case_id not in case_ids:
            case_ids.append(aggregate.case_id)
        for record in aggregate.run_records:
            if record.case_id and record.case_id not in case_ids:
                case_ids.append(record.case_id)
        # blocked_count = provider failures only (do not double-count failure_count)
        blocked_count += aggregate.total_provider_failures
        if aggregate.success_count == 0:
            fail_count += 1
        elif aggregate.total_unsafe_over_resolution > 0:
            fail_count += 1
        elif aggregate.min_status_accuracy >= READY_MIN_HOLDOUT_STATUS_ACCURACY:
            pass_count += 1
        else:
            partial_count += 1
    return TemporalPromptCalibrationMetricsSliceV1(
        prompt_lane=prompt_lane,
        prompt_version=prompt_version,
        prompt_sha256=compute_prompt_sha256(prompt_version),
        case_ids=case_ids,
        pass_count=pass_count,
        partial_count=partial_count,
        fail_count=fail_count,
        blocked_count=blocked_count,
        cohort_aggregates=lane_aggregates,
    )


def _trivial_fake_batch(case_path: Path, *, repo_root: Path) -> dict[str, Any]:
    case = load_temporal_shadow_extraction_case(case_path, repo_root=repo_root)
    annotations: list[dict[str, Any]] = []
    for assertion_id in case.selected_assertion_ids:
        owned = next(
            (
                entry.evidence_ref_id
                for entry in case.evidence_registry
                if entry.evidence_ref_id.startswith("evidence:")
            ),
            "evidence:placeholder",
        )
        annotations.append(
            {
                "base_assertion_id": assertion_id,
                "interpretation_status": "unresolved",
                "occurrence_time": None,
                "valid_time": None,
                "evidence_ref_ids": [owned],
                "source_phrase": None,
                "extraction_confidence": "unknown",
                "diagnostics": ["calibration fake placeholder"],
            }
        )
    return {"schema": "dmb_temporal_model_annotation_batch_v1", "annotations": annotations}


def _resolve_fake_client(
    *,
    spec: CalibrationRunSpec,
    fake_batches: dict[str, dict[str, Any]] | None,
    repo_root: Path,
) -> FakeTemporalShadowExtractionClient:
    lane_key = f"{spec.prompt_lane}:{spec.cohort}"
    if fake_batches and lane_key in fake_batches:
        return FakeTemporalShadowExtractionClient(fake_batches[lane_key])
    return FakeTemporalShadowExtractionClient(
        _trivial_fake_batch(spec.case_path, repo_root=repo_root)
    )


def run_calibration_repetition(
    spec: CalibrationRunSpec,
    *,
    output_dir: Path,
    model_id: str,
    repo_root: Path,
    fake: bool = False,
    fake_batches: dict[str, dict[str, Any]] | None = None,
) -> RunOutcome:
    run_dir = _lane_run_dir(
        output_dir=output_dir,
        prompt_lane=spec.prompt_lane,
        cohort=spec.cohort,
        repetition=spec.repetition,
    )
    client = (
        _resolve_fake_client(spec=spec, fake_batches=fake_batches, repo_root=repo_root)
        if fake
        else None
    )
    try:
        run_temporal_shadow_extraction(
            spec.case_path,
            run_dir,
            client=client,
            model_id=model_id,
            overwrite=True,
            repo_root=repo_root,
        )
    except TemporalShadowExtractionError:
        pass
    return load_run_outcome(spec, run_dir)


def run_prompt_calibration(
    *,
    development_case: Path,
    candidate_development_case: Path,
    holdout_case: Path,
    candidate_holdout_case: Path,
    adversarial_case: Path,
    output_dir: Path,
    model_id: str,
    repetitions: int,
    repo_root: Path | None = None,
    holdout_seal_commit_sha: str | None = None,
    adversarial_seal_commit_sha: str | None = None,
    skip_seal_verification: bool = False,
    fake: bool = False,
    fake_batches: dict[str, dict[str, Any]] | None = None,
) -> TemporalPromptCalibrationAggregateV1:
    root = repo_root or _repo_root()
    execution_sha = _repository_sha(repo_root=root)

    if skip_seal_verification:
        holdout_loaded = load_temporal_shadow_extraction_case(
            candidate_holdout_case, repo_root=root
        )
        holdout_seal = CohortSealRecord(
            case_sha256=_file_sha256(candidate_holdout_case),
            base_sha256=_file_sha256(root / holdout_loaded.base_contribution_path),
            gold_sha256=_file_sha256(root / holdout_loaded.gold_overlay_path),
            seal_commit_sha=holdout_seal_commit_sha or "unverified",
            case_id=holdout_loaded.case_id,
            verified_paths=(),
        )
        adv_loaded = load_temporal_shadow_extraction_case(
            adversarial_case, repo_root=root
        )
        adversarial_seal = CohortSealRecord(
            case_sha256=_file_sha256(adversarial_case),
            base_sha256=_file_sha256(root / adv_loaded.base_contribution_path),
            gold_sha256=_file_sha256(root / adv_loaded.gold_overlay_path),
            seal_commit_sha=adversarial_seal_commit_sha or "unverified",
            case_id=adv_loaded.case_id,
            verified_paths=(),
        )
    else:
        if not holdout_seal_commit_sha:
            raise CohortSealError(
                "--holdout-seal-commit is required unless seal verification is skipped"
            )
        if not adversarial_seal_commit_sha:
            raise CohortSealError(
                "--adversarial-seal-commit is required unless seal verification is skipped"
            )
        holdout_seal = verify_cohort_seal(
            case_path=candidate_holdout_case,
            seal_commit_sha=holdout_seal_commit_sha,
            repo_root=root,
            execution_commit_sha=execution_sha,
        )
        adversarial_seal = verify_cohort_seal(
            case_path=adversarial_case,
            seal_commit_sha=adversarial_seal_commit_sha,
            repo_root=root,
            execution_commit_sha=execution_sha,
        )

    run_specs: list[CalibrationRunSpec] = []
    for repetition in range(1, repetitions + 1):
        run_specs.extend(
            [
                CalibrationRunSpec("baseline", "development", development_case, repetition),
                CalibrationRunSpec("baseline", "holdout", holdout_case, repetition),
                CalibrationRunSpec(
                    "candidate", "development", candidate_development_case, repetition
                ),
                CalibrationRunSpec(
                    "candidate", "holdout", candidate_holdout_case, repetition
                ),
                CalibrationRunSpec(
                    "candidate", "adversarial", adversarial_case, repetition
                ),
            ]
        )

    outcomes: list[RunOutcome] = []
    for spec in run_specs:
        outcomes.append(
            run_calibration_repetition(
                spec,
                output_dir=output_dir,
                model_id=model_id,
                repo_root=root,
                fake=fake,
                fake_batches=fake_batches,
            )
        )

    expected_prompt = {
        ("baseline", "development"): TEMPORAL_SHADOW_PROMPT_VERSION,
        ("baseline", "holdout"): TEMPORAL_SHADOW_PROMPT_VERSION,
        ("candidate", "development"): "tl01c-v1",
        ("candidate", "holdout"): "tl01c-v1",
        ("candidate", "adversarial"): "tl01c-v1",
    }
    expected_case = {
        ("candidate", "holdout"): holdout_seal.case_id,
        ("candidate", "adversarial"): adversarial_seal.case_id,
    }

    cohort_groups: dict[tuple[PromptLane, CohortName], list[RunOutcome]] = defaultdict(
        list
    )
    for outcome in outcomes:
        cohort_groups[(outcome.spec.prompt_lane, outcome.spec.cohort)].append(outcome)

    cohort_aggregates = [
        aggregate_cohort_runs(
            prompt_lane=prompt_lane,
            cohort=cohort,
            outcomes=group_outcomes,
            expected_model_id=model_id,
            expected_prompt_version=expected_prompt.get((prompt_lane, cohort)),
            expected_case_id=expected_case.get((prompt_lane, cohort)),
            expected_repository_sha=None if fake else execution_sha,
        )
        for (prompt_lane, cohort), group_outcomes in sorted(cohort_groups.items())
    ]

    decision, diagnostics = compute_calibration_decision(
        candidate_aggregates=cohort_aggregates,
    )

    calibration_id_payload = {
        "candidate_prompt_sha256": compute_prompt_sha256("tl01c-v1"),
        "holdout_case_sha256": holdout_seal.case_sha256,
        "holdout_seal_commit_sha": holdout_seal.seal_commit_sha,
        "adversarial_case_sha256": adversarial_seal.case_sha256,
        "adversarial_seal_commit_sha": adversarial_seal.seal_commit_sha,
        "model_id": model_id,
        "repetitions": repetitions,
        "repository_sha": execution_sha,
    }
    calibration_id = hashlib.sha256(
        json.dumps(calibration_id_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    aggregate = TemporalPromptCalibrationAggregateV1(
        calibration_id=f"temporal-prompt-calibration:{calibration_id}",
        repository_sha=execution_sha,
        holdout_case_sha256=holdout_seal.case_sha256,
        holdout_base_sha256=holdout_seal.base_sha256,
        holdout_gold_sha256=holdout_seal.gold_sha256,
        holdout_seal_commit_sha=holdout_seal.seal_commit_sha,
        adversarial_case_sha256=adversarial_seal.case_sha256,
        adversarial_base_sha256=adversarial_seal.base_sha256,
        adversarial_gold_sha256=adversarial_seal.gold_sha256,
        adversarial_seal_commit_sha=adversarial_seal.seal_commit_sha,
        candidate_prompt_sha256=compute_prompt_sha256("tl01c-v1"),
        baseline_prompt_sha256=compute_prompt_sha256(TEMPORAL_SHADOW_PROMPT_VERSION),
        model_id=model_id,
        repetitions=repetitions,
        slices=[
            _build_metrics_slice(
                prompt_lane="baseline",
                prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
                cohort_aggregates=cohort_aggregates,
            ),
            _build_metrics_slice(
                prompt_lane="candidate",
                prompt_version="tl01c-v1",
                cohort_aggregates=cohort_aggregates,
            ),
        ],
        decision=decision,
        diagnostics=diagnostics,
    )

    aggregate_path = output_dir / "calibration" / "aggregate.json"
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)
    aggregate_path.write_text(
        json.dumps(aggregate.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return aggregate


def _load_fake_batches(path: Path | None) -> dict[str, dict[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fake batches JSON must be an object")
    return {str(key): value for key, value in payload.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TL01C temporal prompt calibration")
    parser.add_argument("--development-case", required=True)
    parser.add_argument("--candidate-development-case", required=True)
    parser.add_argument("--holdout-case", required=True)
    parser.add_argument("--candidate-holdout-case", required=True)
    parser.add_argument("--adversarial-case", required=True)
    parser.add_argument("--model-id", default="gpt-5.4-mini")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--output-dir",
        default="evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/",
    )
    parser.add_argument(
        "--holdout-seal-commit",
        default=None,
        help="Git commit SHA that sealed the holdout fixtures (required unless --fake)",
    )
    parser.add_argument(
        "--adversarial-seal-commit",
        default=None,
        help="Git commit SHA that sealed the adversarial fixtures (required unless --fake)",
    )
    parser.add_argument(
        "--skip-seal-verification",
        action="store_true",
        help="Skip seal verification (tests / --fake only)",
    )
    parser.add_argument("--fake", action="store_true")
    parser.add_argument(
        "--fake-batches-json",
        default=None,
        help="Optional JSON map of lane keys (baseline:development, etc.) to model batches",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    output_dir = Path(args.output_dir)
    fake_batches = _load_fake_batches(
        Path(args.fake_batches_json) if args.fake_batches_json else None
    )
    skip_seal = bool(args.skip_seal_verification or args.fake)

    aggregate = run_prompt_calibration(
        development_case=Path(args.development_case),
        candidate_development_case=Path(args.candidate_development_case),
        holdout_case=Path(args.holdout_case),
        candidate_holdout_case=Path(args.candidate_holdout_case),
        adversarial_case=Path(args.adversarial_case),
        output_dir=output_dir,
        model_id=args.model_id,
        repetitions=args.repetitions,
        repo_root=repo_root,
        holdout_seal_commit_sha=args.holdout_seal_commit,
        adversarial_seal_commit_sha=args.adversarial_seal_commit,
        skip_seal_verification=skip_seal,
        fake=args.fake,
        fake_batches=fake_batches,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "calibration_id": aggregate.calibration_id,
                "decision": aggregate.decision,
                "holdout_case_sha256": aggregate.holdout_case_sha256,
                "holdout_seal_commit_sha": aggregate.holdout_seal_commit_sha,
                "adversarial_case_sha256": aggregate.adversarial_case_sha256,
                "adversarial_seal_commit_sha": aggregate.adversarial_seal_commit_sha,
                "aggregate_path": str(output_dir / "calibration" / "aggregate.json"),
            }
        )
    )
    return 0 if aggregate.decision == "PROMPT_READY_FOR_BROADER_SHADOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
