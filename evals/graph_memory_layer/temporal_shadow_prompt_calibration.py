"""Temporal prompt calibration runner (TL01C+)."""

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
    CalibrationAssertionStabilityV1,
    CalibrationCohortAggregateV1,
    CalibrationDecision,
    CalibrationExperimentRole,
    CalibrationMetricDistributionV1,
    CalibrationRunMatrixEntryV1,
    CalibrationRunRecordV1,
    TemporalPromptCalibrationAggregateV1,
    TemporalPromptCalibrationMetricsSliceV1,
)

PromptLane = Literal["baseline", "candidate"]
CohortName = Literal["development", "holdout", "adversarial"]
ExperimentRole = CalibrationExperimentRole

PROVIDER_FAILURE_CODES = frozenset(
    {"provider_refusal", "provider_incomplete", "provider_error"}
)
# True contract gaps: frozen schema/prompt registry cannot represent the needed answer.
CONTRACT_FAILURE_CODES = frozenset(
    {"overlay_assembly_failed", "unsupported_prompt_version"}
)
# Model/prompt noncompliance against a representable contract (e.g. ambiguous+extents).
MODEL_OUTPUT_FAILURE_CODES = frozenset(
    {"invalid_model_output", "target_set_mismatch"}
)
EVIDENCE_FAILURE_CODES = frozenset(
    {"evidence_unresolved", "digest_mismatch", "invalid_case", "invalid_gold_overlay"}
)
GROUNDING_FAILURE_CODE = "grounding_failure"

# Handoff READY thresholds (development + holdout).
READY_DEV_MEDIAN_EXACT_MATCHES = 4  # of 6 development gold rows
READY_DEV_RESOLVED_EXACT_MATCHES = 2  # of 3 resolved gold rows
READY_DEV_RESOLVED_EXACT_RUNS = 2  # at least two qualifying development runs
READY_MIN_HOLDOUT_STATUS_ACCURACY = 0.80
READY_MIN_NOT_APPLICABLE_ACCURACY = 1.0
READY_MIN_HOLDOUT_EXACT_OCCURRENCE = 1
READY_MIN_HOLDOUT_EXACT_VALID_TIME = 1

INPUT_REP_MIN_WRONG_TEMPORAL_VALUE = 2

REQUIRED_MANIFEST_IDENTITY_FIELDS = (
    "case_id",
    "model_id",
    "prompt_version",
    "repository_sha",
)


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


class PairedCaseError(ValueError):
    """Baseline/candidate paired cases are not equivalent fixtures."""


class PromptVersionMismatchError(ValueError):
    """Control or candidate cases disagree on prompt_version."""


class DirtyWorktreeError(ValueError):
    """Live calibration refused because the git worktree is dirty."""


class ReaggregateError(ValueError):
    """Reaggregate refused due to missing/ambiguous artifacts or provenance mismatch.

    Covers absent manifests, both success and failure manifests present, inconsistent
    provider execution SHAs, case_digest mismatches against the executed case file,
    and other fail-closed provenance checks before rewriting aggregate.json.
    """


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


_CLEAN_WORKTREE_PATHSPECS = (
    ".",
    ":(exclude)node_modules",
    ":(exclude)node_modules/**",
    ":(exclude)evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration",
    ":(exclude)evals/graph_memory_layer/artifacts/temporal_shadow_prompt_calibration/**",
)


def _repository_sha(*, repo_root: Path) -> str:
    """Match extraction provenance: HEAD, or HEAD+dirty when the worktree is dirty.

    Untracked non-ignored files count as dirty (``git status --porcelain`` without
    ``-uno``). Ignored/generated calibration artifacts remain excluded via pathspec.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = completed.stdout.strip() or "unknown"
        dirty = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                *_CLEAN_WORKTREE_PATHSPECS,
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if dirty.stdout.strip():
        return f"{sha}+dirty"
    return sha


def _git_commit_sha(value: str) -> str:
    """Strip provenance suffixes (e.g. +dirty) before git ancestry/object checks."""
    return value.split("+", 1)[0]


def _assert_clean_worktree_for_live(*, repo_root: Path, fake: bool) -> None:
    """Refuse real provider runs when uncommitted or untracked changes could skew provenance."""
    if fake:
        return
    try:
        porcelain = _git_stdout(
            repo_root,
            "status",
            "--porcelain",
            "--",
            *_CLEAN_WORKTREE_PATHSPECS,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DirtyWorktreeError(
            "unable to determine git worktree cleanliness for live calibration"
        ) from exc
    if porcelain.strip():
        raise DirtyWorktreeError(
            "live calibration requires a clean git worktree "
            "(tracked modifications and non-ignored untracked files block execution); "
            "commit or stash changes before running, or use --fake"
        )


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
    execution_commit = _git_commit_sha(execution)
    if not _git_ok(repo_root, "merge-base", "--is-ancestor", seal, execution_commit):
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


def verify_fixtures_tracked_at_commit(
    *,
    case_path: Path,
    commit_sha: str,
    repo_root: Path,
) -> CohortSealRecord:
    """Require case/base/gold/evidence blobs at ``commit_sha`` match the worktree.

    Used for development and baseline-mirror inputs that are not sealed to an
    earlier cohort commit: they must still be Git-tracked at the execution commit.
    """
    commit = _git_commit_sha(commit_sha.strip())
    if not commit or commit == "unknown":
        raise CohortSealError("commit_sha is required to verify tracked fixtures")
    return verify_cohort_seal(
        case_path=case_path,
        seal_commit_sha=commit,
        repo_root=repo_root,
        execution_commit_sha=commit,
    )


def derive_prompt_versions_from_cases(
    *,
    control_case_paths: list[Path],
    candidate_case_paths: list[Path],
    repo_root: Path,
) -> tuple[str, str]:
    """Require uniform control/candidate prompt_version and control != candidate."""
    control_versions: set[str] = set()
    candidate_versions: set[str] = set()

    for path in control_case_paths:
        case = load_temporal_shadow_extraction_case(path, repo_root=repo_root)
        control_versions.add(case.prompt_version)

    for path in candidate_case_paths:
        case = load_temporal_shadow_extraction_case(path, repo_root=repo_root)
        candidate_versions.add(case.prompt_version)

    if len(control_versions) != 1:
        raise PromptVersionMismatchError(
            "control cases must share one prompt_version "
            f"(observed={sorted(control_versions)})"
        )
    if len(candidate_versions) != 1:
        raise PromptVersionMismatchError(
            "candidate cases must share one prompt_version "
            f"(observed={sorted(candidate_versions)})"
        )

    baseline_prompt_version = next(iter(control_versions))
    candidate_prompt_version = next(iter(candidate_versions))
    if baseline_prompt_version == candidate_prompt_version:
        raise PromptVersionMismatchError(
            "control and candidate prompt_version must differ "
            f"(both={baseline_prompt_version!r})"
        )
    return baseline_prompt_version, candidate_prompt_version


def validate_paired_case_equivalence(
    *,
    baseline_case_path: Path,
    candidate_case_path: Path,
    repo_root: Path,
    pair_name: str,
) -> None:
    """Require baseline/candidate pairs share contribution, gold, assertions, evidence.

    Only ``prompt_version`` (and case_id / case path) may differ.
    """
    baseline = load_temporal_shadow_extraction_case(baseline_case_path, repo_root=repo_root)
    candidate = load_temporal_shadow_extraction_case(
        candidate_case_path, repo_root=repo_root
    )
    errors: list[str] = []
    if baseline.base_contribution_path != candidate.base_contribution_path:
        errors.append("base_contribution_path mismatch")
    if baseline.base_contribution_sha256 != candidate.base_contribution_sha256:
        errors.append("base_contribution_sha256 mismatch")
    if baseline.gold_overlay_path != candidate.gold_overlay_path:
        errors.append("gold_overlay_path mismatch")
    if baseline.gold_overlay_sha256 != candidate.gold_overlay_sha256:
        errors.append("gold_overlay_sha256 mismatch")
    if list(baseline.selected_assertion_ids) != list(candidate.selected_assertion_ids):
        errors.append("selected_assertion_ids mismatch")
    if baseline.snippet_max_chars != candidate.snippet_max_chars:
        errors.append("snippet_max_chars mismatch")

    def _evidence_key(entry: Any) -> tuple[Any, ...]:
        return (
            entry.evidence_ref_id,
            entry.source_artifact_id,
            entry.source_artifact_path,
            entry.content_sha256,
            entry.source_ref_id,
            entry.start_line,
            entry.end_line,
            entry.label,
        )

    baseline_evidence = [_evidence_key(entry) for entry in baseline.evidence_registry]
    candidate_evidence = [_evidence_key(entry) for entry in candidate.evidence_registry]
    if baseline_evidence != candidate_evidence:
        errors.append("evidence_registry mismatch")

    if baseline.prompt_version == candidate.prompt_version:
        errors.append(
            "prompt_version must differ between baseline and candidate "
            f"(both={baseline.prompt_version!r})"
        )
    if errors:
        raise PairedCaseError(
            f"paired case equivalence failed for {pair_name}: " + "; ".join(errors)
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
        if not payload:
            diagnostics.append(
                f"missing_manifest repetition={outcome.spec.repetition}"
            )
            continue

        case_id = payload.get("case_id")
        model_id = payload.get("model_id")
        prompt_version = payload.get("prompt_version") or payload.get(
            "executed_prompt_version"
        )
        repository_sha = payload.get("repository_sha")

        identity = {
            "case_id": case_id if isinstance(case_id, str) and case_id else None,
            "model_id": model_id if isinstance(model_id, str) and model_id else None,
            "prompt_version": (
                prompt_version if isinstance(prompt_version, str) and prompt_version else None
            ),
            "repository_sha": (
                repository_sha
                if isinstance(repository_sha, str) and repository_sha
                else None
            ),
        }
        for field in REQUIRED_MANIFEST_IDENTITY_FIELDS:
            if identity[field] is None:
                diagnostics.append(
                    f"missing_{field} repetition={outcome.spec.repetition}"
                )

        if identity["case_id"] is not None:
            case_ids.add(identity["case_id"])
        if identity["model_id"] is not None:
            model_ids.add(identity["model_id"])
        if identity["prompt_version"] is not None:
            prompt_versions.add(identity["prompt_version"])
        if identity["repository_sha"] is not None:
            repo_shas.add(identity["repository_sha"])

        if expected_case_id and identity["case_id"] is not None:
            if identity["case_id"] != expected_case_id:
                diagnostics.append(
                    f"case_id_mismatch repetition={outcome.spec.repetition} "
                    f"expected={expected_case_id} observed={identity['case_id']}"
                )
        if expected_model_id and identity["model_id"] is not None:
            if identity["model_id"] != expected_model_id:
                diagnostics.append(
                    f"model_id_mismatch repetition={outcome.spec.repetition} "
                    f"expected={expected_model_id} observed={identity['model_id']}"
                )
        if expected_prompt_version and identity["prompt_version"] is not None:
            if identity["prompt_version"] != expected_prompt_version:
                diagnostics.append(
                    f"prompt_version_mismatch repetition={outcome.spec.repetition} "
                    f"expected={expected_prompt_version} "
                    f"observed={identity['prompt_version']}"
                )
        if expected_repository_sha and identity["repository_sha"] is not None:
            if identity["repository_sha"] != expected_repository_sha:
                diagnostics.append(
                    f"repository_sha_mismatch repetition={outcome.spec.repetition} "
                    f"expected={expected_repository_sha} "
                    f"observed={identity['repository_sha']}"
                )

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

    # Fail closed when expected identity exists but no run supplied that field.
    if expected_case_id and not case_ids:
        diagnostics.append(f"missing_all_case_ids expected={expected_case_id}")
    if expected_model_id and not model_ids:
        diagnostics.append(f"missing_all_model_ids expected={expected_model_id}")
    if expected_prompt_version and not prompt_versions:
        diagnostics.append(
            f"missing_all_prompt_versions expected={expected_prompt_version}"
        )
    if expected_repository_sha and not repo_shas:
        diagnostics.append(
            f"missing_all_repository_shas expected={expected_repository_sha}"
        )

    observed_case = next(iter(case_ids), None)
    return (not diagnostics), diagnostics, observed_case


def _count_exact_matches_by_lane(
    *,
    comparison: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
) -> tuple[int, int]:
    """Count exact-match rows that carry occurrence vs valid-time payloads."""
    if comparison is None or overlay is None:
        return 0, 0
    rows = comparison.get("rows")
    annotations = overlay.get("annotations")
    if not isinstance(rows, list) or not isinstance(annotations, list):
        return 0, 0
    by_id = {
        item.get("base_assertion_id"): item
        for item in annotations
        if isinstance(item, dict) and isinstance(item.get("base_assertion_id"), str)
    }
    occurrence = 0
    valid_time = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("classification") != "exact_match":
            continue
        assertion_id = row.get("base_assertion_id")
        if not isinstance(assertion_id, str):
            continue
        annotation = by_id.get(assertion_id)
        if not isinstance(annotation, dict):
            continue
        if annotation.get("occurrence_time") is not None:
            occurrence += 1
        if annotation.get("valid_time") is not None:
            valid_time += 1
    return occurrence, valid_time


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
    occurrence_exact_values: list[int] = []
    valid_exact_values: list[int] = []
    status_accuracies: list[float] = []
    not_applicable_accuracies: list[float] = []

    total_unsafe = 0
    total_source_occ = 0
    total_source_valid = 0
    total_evidence_mismatch = 0
    total_evidence_or_case_failures = 0
    total_provider_failures = 0
    total_grounding_failures = 0
    total_model_output_failures = 0
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
            occ_exact, valid_exact = _count_exact_matches_by_lane(
                comparison=outcome.comparison,
                overlay=outcome.overlay,
            )
            occurrence_exact_values.append(occ_exact)
            valid_exact_values.append(valid_exact)
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
                    exact_occurrence_match_count=occ_exact,
                    exact_valid_time_match_count=valid_exact,
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
            elif code in MODEL_OUTPUT_FAILURE_CODES:
                total_model_output_failures += 1
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
                    provider_response_id=str(payload.get("provider_response_id") or "")
                    or None,
                    failure_code=code,
                    affected_assertion_id=(
                        failure.get("affected_assertion_id")
                        if isinstance(failure.get("affected_assertion_id"), str)
                        else None
                    ),
                    failure_diagnostics=list(failure.get("diagnostics") or []),
                    foreign_evidence_attempts=(
                        int(failure["foreign_evidence_attempts"])
                        if failure.get("foreign_evidence_attempts") is not None
                        else None
                    ),
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
        exact_occurrence_match=_distribution(occurrence_exact_values),
        exact_valid_time_match=_distribution(valid_exact_values),
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
        total_model_output_failures=total_model_output_failures,
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
    cohort_aggregates: list[CalibrationCohortAggregateV1],
    diagnostics: list[str] | None = None,
    seals_verified: bool = False,
    aggregate_build_sha: str | None = None,
    provider_run_repository_shas: list[str] | None = None,
) -> tuple[CalibrationDecision, list[str]]:
    notes = list(diagnostics or [])
    candidate = [a for a in cohort_aggregates if a.prompt_lane == "candidate"]
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
        if sum(a.success_count for a in candidate) == 0:
            notes.append("candidate_comparison_metrics_unobserved")
        return "ITERATE_PROMPT", notes

    total_model_output = sum(a.total_model_output_failures for a in candidate)
    if total_model_output > 0:
        # Schema-invalid / target-set noncompliance against a representable contract.
        notes.append(f"candidate_model_output_failures={total_model_output}")
        if sum(a.success_count for a in candidate) == 0:
            notes.append("candidate_comparison_metrics_unobserved")
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
        if sum(a.success_count for a in candidate) == 0:
            notes.append("candidate_comparison_metrics_unobserved")
        return "ITERATE_PROMPT", notes

    if sum(a.success_count for a in candidate) == 0:
        notes.append("candidate_comparison_metrics_unobserved")
        return "ITERATE_PROMPT", notes

    if any(not a.manifest_consistency_ok for a in cohort_aggregates):
        notes.append("manifest_inconsistency")
        return "ITERATE_PROMPT", notes

    provider_shas = list(provider_run_repository_shas or [])
    if aggregate_build_sha:
        if not provider_shas:
            notes.append("missing_provider_run_repository_shas")
            return "ITERATE_PROMPT", notes
        if provider_shas != [aggregate_build_sha]:
            notes.append(
                "provider_run_revision_mismatch "
                f"aggregate_build_sha={aggregate_build_sha} "
                f"provider_run_repository_shas={provider_shas}"
            )
            return "ITERATE_PROMPT", notes

    if not seals_verified:
        notes.append("seals_not_verified")
        return "ITERATE_PROMPT", notes

    dev_exact = development.exact_match
    median_exact = float(dev_exact.median) if dev_exact is not None else 0.0
    qualifying_resolved_runs = sum(
        1
        for record in development.run_records
        if record.succeeded
        and int(record.resolved_exact_match_count or 0)
        >= READY_DEV_RESOLVED_EXACT_MATCHES
    )
    resolved_runs_ok = qualifying_resolved_runs >= READY_DEV_RESOLVED_EXACT_RUNS
    min_not_applicable = min(
        (a.min_not_applicable_accuracy for a in candidate if a.success_count),
        default=0.0,
    )
    holdout_status_ok = holdout.min_status_accuracy >= READY_MIN_HOLDOUT_STATUS_ACCURACY
    holdout_occurrence = holdout.exact_occurrence_match
    holdout_valid = holdout.exact_valid_time_match
    holdout_has_occurrence = (
        holdout_occurrence is not None
        and float(holdout_occurrence.min) >= READY_MIN_HOLDOUT_EXACT_OCCURRENCE
    )
    holdout_has_valid = (
        holdout_valid is not None
        and float(holdout_valid.min) >= READY_MIN_HOLDOUT_EXACT_VALID_TIME
    )

    ready = (
        median_exact >= READY_DEV_MEDIAN_EXACT_MATCHES
        and resolved_runs_ok
        and min_not_applicable >= READY_MIN_NOT_APPLICABLE_ACCURACY
        and holdout_status_ok
        and holdout_has_occurrence
        and holdout_has_valid
    )
    if ready:
        notes.append("candidate_metrics_met_ready_thresholds")
        return "PROMPT_READY_FOR_BROADER_SHADOW", notes

    notes.append(
        "candidate_quality_insufficient "
        f"(dev_median_exact={median_exact:.3f}, "
        f"dev_qualifying_resolved_runs={qualifying_resolved_runs}, "
        f"min_not_applicable={min_not_applicable:.3f}, "
        f"holdout_status={holdout.min_status_accuracy:.3f}, "
        f"holdout_exact_occurrence_min="
        f"{(float(holdout_occurrence.min) if holdout_occurrence is not None else 0.0):.3f}, "
        f"holdout_exact_valid_min="
        f"{(float(holdout_valid.min) if holdout_valid is not None else 0.0):.3f})"
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


def _build_calibration_run_specs(
    *,
    development_case: Path,
    candidate_development_case: Path,
    holdout_case: Path,
    candidate_holdout_case: Path,
    adversarial_case: Path,
    repetitions: int,
    baseline_adversarial_case: Path | None = None,
) -> list[CalibrationRunSpec]:
    run_specs: list[CalibrationRunSpec] = []
    for repetition in range(1, repetitions + 1):
        lane_specs = [
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
        if baseline_adversarial_case is not None:
            lane_specs.insert(
                2,
                CalibrationRunSpec(
                    "baseline",
                    "adversarial",
                    baseline_adversarial_case,
                    repetition,
                ),
            )
        run_specs.extend(lane_specs)
    return run_specs


def _manifest_case_digest(manifest: dict[str, Any] | None) -> str | None:
    if manifest is None:
        return None
    digest = manifest.get("case_digest")
    return digest if isinstance(digest, str) and digest else None


def _require_single_provider_execution_sha(outcomes: list[RunOutcome]) -> str:
    """Collect one non-empty repository_sha from published run/failure manifests."""
    shas: set[str] = set()
    for outcome in outcomes:
        manifest = outcome.run_manifest if outcome.succeeded else outcome.failure_manifest
        if manifest is None:
            manifest = outcome.failure_manifest or outcome.run_manifest
        if manifest is None:
            raise ReaggregateError(
                f"missing published manifest for {outcome.spec.prompt_lane}/"
                f"{outcome.spec.cohort}/run-{outcome.spec.repetition:02d}"
            )
        repository_sha = manifest.get("repository_sha")
        if not isinstance(repository_sha, str) or not repository_sha.strip():
            raise ReaggregateError(
                f"missing repository_sha in published manifest for "
                f"{outcome.spec.prompt_lane}/{outcome.spec.cohort}/"
                f"run-{outcome.spec.repetition:02d}"
            )
        shas.add(_git_commit_sha(repository_sha.strip()))
    if len(shas) != 1:
        raise ReaggregateError(
            f"inconsistent provider execution SHAs across matrix: {sorted(shas)}"
        )
    provider_sha = next(iter(shas))
    if not provider_sha or provider_sha == "unknown":
        raise ReaggregateError("provider execution SHA is empty or unknown")
    return provider_sha


def load_calibration_outcomes_from_disk(
    *,
    output_dir: Path,
    run_specs: list[CalibrationRunSpec],
) -> list[RunOutcome]:
    """Load published run outcomes without invoking the provider."""
    outcomes: list[RunOutcome] = []
    for spec in run_specs:
        run_dir = _lane_run_dir(
            output_dir=output_dir,
            prompt_lane=spec.prompt_lane,
            cohort=spec.cohort,
            repetition=spec.repetition,
        )
        has_run = (run_dir / "run-manifest.json").is_file()
        has_failure = (run_dir / "failure-manifest.json").is_file()
        if has_run and has_failure:
            raise ReaggregateError(
                f"ambiguous run outcome for {spec.prompt_lane}/{spec.cohort}/"
                f"run-{spec.repetition:02d}: both run-manifest.json and "
                f"failure-manifest.json found under {run_dir}"
            )
        if not has_run and not has_failure:
            raise ReaggregateError(
                f"missing run artifacts for {spec.prompt_lane}/{spec.cohort}/"
                f"run-{spec.repetition:02d}: neither run-manifest.json nor "
                f"failure-manifest.json found under {run_dir}"
            )
        outcome = load_run_outcome(spec, run_dir)
        published = (
            outcome.run_manifest if outcome.succeeded else outcome.failure_manifest
        )
        expected_digest = _file_sha256(spec.case_path)
        actual_digest = _manifest_case_digest(published)
        if actual_digest is None:
            raise ReaggregateError(
                f"missing case_digest in published manifest for "
                f"{spec.prompt_lane}/{spec.cohort}/run-{spec.repetition:02d} "
                f"case_path={spec.case_path} expected={expected_digest}"
            )
        if actual_digest != expected_digest:
            raise ReaggregateError(
                f"case_digest mismatch for {spec.prompt_lane}/{spec.cohort}/"
                f"run-{spec.repetition:02d} case_path={spec.case_path} "
                f"expected={expected_digest} actual={actual_digest}"
            )
        outcomes.append(outcome)
    return outcomes


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
    caught: TemporalShadowExtractionError | None = None
    try:
        run_temporal_shadow_extraction(
            spec.case_path,
            run_dir,
            client=client,
            model_id=model_id,
            overwrite=True,
            repo_root=repo_root,
        )
    except TemporalShadowExtractionError as exc:
        caught = exc
    _ensure_identity_failure_manifest(
        run_dir=run_dir,
        spec=spec,
        model_id=model_id,
        repo_root=repo_root,
        error=caught,
    )
    return load_run_outcome(spec, run_dir)


def _ensure_identity_failure_manifest(
    *,
    run_dir: Path,
    spec: CalibrationRunSpec,
    model_id: str,
    repo_root: Path,
    error: TemporalShadowExtractionError | None,
) -> None:
    """Guarantee every repetition leaves a manifest with identity fields."""
    if (run_dir / "run-manifest.json").is_file():
        return
    if (run_dir / "failure-manifest.json").is_file():
        return
    run_dir.mkdir(parents=True, exist_ok=True)
    case = load_temporal_shadow_extraction_case(spec.case_path, repo_root=repo_root)
    failure_code = error.code if error is not None else "unknown_failure"
    diagnostics = list(error.diagnostics) if error is not None else [
        f"missing_published_run_directory path={run_dir}"
    ]
    if error is not None:
        diagnostics = _bounded_or_plain(diagnostics)
    payload = {
        "schema": "dmb_temporal_shadow_extraction_failure_v1",
        "case_id": case.case_id,
        "case_digest": _file_sha256(spec.case_path),
        "model_id": model_id,
        "executed_prompt_version": case.prompt_version,
        "prompt_version": case.prompt_version,
        "failure_code": failure_code,
        "diagnostics": diagnostics[:8],
        "repository_sha": _repository_sha(repo_root=repo_root),
        "provider_response_id": (
            error.provider_response_id if error is not None else None
        ),
        "affected_assertion_id": (
            error.affected_assertion_id if error is not None else None
        ),
    }
    (run_dir / "failure-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _bounded_or_plain(diagnostics: list[str]) -> list[str]:
    bounded: list[str] = []
    for item in diagnostics[:8]:
        text = item if len(item) <= 500 else item[:497] + "..."
        bounded.append(text)
    return bounded


def build_calibration_run_matrix(
    *,
    expected_case: dict[tuple[PromptLane, CohortName], str],
) -> list[CalibrationRunMatrixEntryV1]:
    """Normalize lane/cohort/case identities for aggregate + calibration_id."""
    entries = [
        CalibrationRunMatrixEntryV1(
            prompt_lane=prompt_lane,
            cohort=cohort,
            case_id=case_id,
        )
        for (prompt_lane, cohort), case_id in expected_case.items()
    ]
    return sorted(
        entries,
        key=lambda item: (item.prompt_lane, item.cohort, item.case_id),
    )


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
    experiment_role: ExperimentRole,
    repo_root: Path | None = None,
    holdout_seal_commit_sha: str | None = None,
    adversarial_seal_commit_sha: str | None = None,
    baseline_adversarial_case: Path | None = None,
    skip_seal_verification: bool = False,
    fake: bool = False,
    fake_batches: dict[str, dict[str, Any]] | None = None,
) -> TemporalPromptCalibrationAggregateV1:
    root = repo_root or _repo_root()

    if skip_seal_verification and not fake:
        raise CohortSealError(
            "skip_seal_verification requires fake=True; real provider runs must verify seals"
        )

    _assert_clean_worktree_for_live(repo_root=root, fake=fake)
    execution_sha = _repository_sha(repo_root=root)

    control_case_paths = [development_case, holdout_case]
    candidate_case_paths = [
        candidate_development_case,
        candidate_holdout_case,
        adversarial_case,
    ]
    if baseline_adversarial_case is not None:
        control_case_paths.append(baseline_adversarial_case)

    baseline_prompt_version, candidate_prompt_version = derive_prompt_versions_from_cases(
        control_case_paths=control_case_paths,
        candidate_case_paths=candidate_case_paths,
        repo_root=root,
    )

    seals_verified = False
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
        # Development and baseline-mirror inputs are not sealed to an earlier cohort
        # commit; require their case/base/gold/evidence blobs match the execution commit.
        verify_fixtures_tracked_at_commit(
            case_path=development_case,
            commit_sha=execution_sha,
            repo_root=root,
        )
        verify_fixtures_tracked_at_commit(
            case_path=candidate_development_case,
            commit_sha=execution_sha,
            repo_root=root,
        )
        verify_fixtures_tracked_at_commit(
            case_path=holdout_case,
            commit_sha=execution_sha,
            repo_root=root,
        )
        if baseline_adversarial_case is not None:
            verify_fixtures_tracked_at_commit(
                case_path=baseline_adversarial_case,
                commit_sha=execution_sha,
                repo_root=root,
            )
        seals_verified = True

    # Paired baseline/candidate fixtures must share contribution/gold/assertions/evidence
    # before any provider call.
    validate_paired_case_equivalence(
        baseline_case_path=development_case,
        candidate_case_path=candidate_development_case,
        repo_root=root,
        pair_name="development",
    )
    validate_paired_case_equivalence(
        baseline_case_path=holdout_case,
        candidate_case_path=candidate_holdout_case,
        repo_root=root,
        pair_name="holdout",
    )
    if baseline_adversarial_case is not None:
        validate_paired_case_equivalence(
            baseline_case_path=baseline_adversarial_case,
            candidate_case_path=adversarial_case,
            repo_root=root,
            pair_name="adversarial",
        )

    baseline_development = load_temporal_shadow_extraction_case(
        development_case, repo_root=root
    )
    candidate_development = load_temporal_shadow_extraction_case(
        candidate_development_case, repo_root=root
    )
    baseline_holdout = load_temporal_shadow_extraction_case(
        holdout_case, repo_root=root
    )
    baseline_adversarial = (
        load_temporal_shadow_extraction_case(baseline_adversarial_case, repo_root=root)
        if baseline_adversarial_case is not None
        else None
    )

    run_specs = _build_calibration_run_specs(
        development_case=development_case,
        candidate_development_case=candidate_development_case,
        holdout_case=holdout_case,
        candidate_holdout_case=candidate_holdout_case,
        adversarial_case=adversarial_case,
        repetitions=repetitions,
        baseline_adversarial_case=baseline_adversarial_case,
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

    expected_prompt: dict[tuple[PromptLane, CohortName], str] = {
        ("baseline", "development"): baseline_prompt_version,
        ("baseline", "holdout"): baseline_prompt_version,
        ("candidate", "development"): candidate_prompt_version,
        ("candidate", "holdout"): candidate_prompt_version,
        ("candidate", "adversarial"): candidate_prompt_version,
    }
    expected_case: dict[tuple[PromptLane, CohortName], str] = {
        ("baseline", "development"): baseline_development.case_id,
        ("baseline", "holdout"): baseline_holdout.case_id,
        ("candidate", "development"): candidate_development.case_id,
        ("candidate", "holdout"): holdout_seal.case_id,
        ("candidate", "adversarial"): adversarial_seal.case_id,
    }
    if baseline_adversarial is not None:
        expected_prompt[("baseline", "adversarial")] = baseline_prompt_version
        expected_case[("baseline", "adversarial")] = baseline_adversarial.case_id

    run_matrix = build_calibration_run_matrix(expected_case=expected_case)
    control_adversarial_enabled = baseline_adversarial_case is not None
    control_adversarial_case_id = (
        baseline_adversarial.case_id if baseline_adversarial is not None else None
    )

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
            expected_case_id=expected_case[(prompt_lane, cohort)],
            expected_repository_sha=None if fake else execution_sha,
        )
        for (prompt_lane, cohort), group_outcomes in sorted(cohort_groups.items())
    ]

    provider_run_repository_shas = sorted(
        {
            record.repository_sha
            for aggregate in cohort_aggregates
            for record in aggregate.run_records
            if isinstance(record.repository_sha, str) and record.repository_sha
        }
    )

    decision, diagnostics = compute_calibration_decision(
        cohort_aggregates=cohort_aggregates,
        seals_verified=seals_verified,
        aggregate_build_sha=None if fake else execution_sha,
        provider_run_repository_shas=(
            None if fake else provider_run_repository_shas
        ),
    )

    calibration_id_payload = {
        "baseline_prompt_version": baseline_prompt_version,
        "candidate_prompt_version": candidate_prompt_version,
        "baseline_prompt_sha256": compute_prompt_sha256(baseline_prompt_version),
        "candidate_prompt_sha256": compute_prompt_sha256(candidate_prompt_version),
        "holdout_case_sha256": holdout_seal.case_sha256,
        "holdout_seal_commit_sha": holdout_seal.seal_commit_sha,
        "adversarial_case_sha256": adversarial_seal.case_sha256,
        "adversarial_seal_commit_sha": adversarial_seal.seal_commit_sha,
        "model_id": model_id,
        "repetitions": repetitions,
        "repository_sha": execution_sha,
        "aggregate_build_sha": execution_sha,
        "provider_run_repository_shas": provider_run_repository_shas,
        "experiment_role": experiment_role,
        "control_adversarial_enabled": control_adversarial_enabled,
        "control_adversarial_case_id": control_adversarial_case_id,
        "run_matrix": [
            {
                "prompt_lane": entry.prompt_lane,
                "cohort": entry.cohort,
                "case_id": entry.case_id,
            }
            for entry in run_matrix
        ],
    }
    calibration_id = hashlib.sha256(
        json.dumps(calibration_id_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    aggregate = TemporalPromptCalibrationAggregateV1(
        calibration_id=f"temporal-prompt-calibration:{calibration_id}",
        repository_sha=execution_sha,
        aggregate_build_sha=execution_sha,
        provider_run_repository_shas=provider_run_repository_shas,
        holdout_case_sha256=holdout_seal.case_sha256,
        holdout_base_sha256=holdout_seal.base_sha256,
        holdout_gold_sha256=holdout_seal.gold_sha256,
        holdout_seal_commit_sha=holdout_seal.seal_commit_sha,
        adversarial_case_sha256=adversarial_seal.case_sha256,
        adversarial_base_sha256=adversarial_seal.base_sha256,
        adversarial_gold_sha256=adversarial_seal.gold_sha256,
        adversarial_seal_commit_sha=adversarial_seal.seal_commit_sha,
        seals_verified=seals_verified,
        baseline_prompt_version=baseline_prompt_version,
        candidate_prompt_version=candidate_prompt_version,
        candidate_prompt_sha256=compute_prompt_sha256(candidate_prompt_version),
        baseline_prompt_sha256=compute_prompt_sha256(baseline_prompt_version),
        model_id=model_id,
        repetitions=repetitions,
        experiment_role=experiment_role,
        run_matrix=run_matrix,
        control_adversarial_enabled=control_adversarial_enabled,
        control_adversarial_case_id=control_adversarial_case_id,
        slices=[
            _build_metrics_slice(
                prompt_lane="baseline",
                prompt_version=baseline_prompt_version,
                cohort_aggregates=cohort_aggregates,
            ),
            _build_metrics_slice(
                prompt_lane="candidate",
                prompt_version=candidate_prompt_version,
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


def reaggregate_existing_calibration_runs(
    *,
    development_case: Path,
    candidate_development_case: Path,
    holdout_case: Path,
    candidate_holdout_case: Path,
    adversarial_case: Path,
    output_dir: Path,
    model_id: str,
    repetitions: int,
    experiment_role: ExperimentRole,
    repo_root: Path | None = None,
    holdout_seal_commit_sha: str | None = None,
    adversarial_seal_commit_sha: str | None = None,
    baseline_adversarial_case: Path | None = None,
) -> TemporalPromptCalibrationAggregateV1:
    """Rebuild aggregate.json from on-disk run manifests without provider calls."""
    root = repo_root or _repo_root()
    build_sha = _repository_sha(repo_root=root)

    _assert_clean_worktree_for_live(repo_root=root, fake=False)

    if not holdout_seal_commit_sha:
        raise CohortSealError(
            "--holdout-seal-commit is required for --reaggregate-only"
        )
    if not adversarial_seal_commit_sha:
        raise CohortSealError(
            "--adversarial-seal-commit is required for --reaggregate-only"
        )

    baseline_prompt_version, candidate_prompt_version = derive_prompt_versions_from_cases(
        control_case_paths=[
            development_case,
            holdout_case,
            *([baseline_adversarial_case] if baseline_adversarial_case else []),
        ],
        candidate_case_paths=[
            candidate_development_case,
            candidate_holdout_case,
            adversarial_case,
        ],
        repo_root=root,
    )

    baseline_development = load_temporal_shadow_extraction_case(
        development_case, repo_root=root
    )
    candidate_development = load_temporal_shadow_extraction_case(
        candidate_development_case, repo_root=root
    )
    baseline_holdout = load_temporal_shadow_extraction_case(
        holdout_case, repo_root=root
    )
    baseline_adversarial = (
        load_temporal_shadow_extraction_case(baseline_adversarial_case, repo_root=root)
        if baseline_adversarial_case is not None
        else None
    )

    run_specs = _build_calibration_run_specs(
        development_case=development_case,
        candidate_development_case=candidate_development_case,
        holdout_case=holdout_case,
        candidate_holdout_case=candidate_holdout_case,
        adversarial_case=adversarial_case,
        repetitions=repetitions,
        baseline_adversarial_case=baseline_adversarial_case,
    )
    outcomes = load_calibration_outcomes_from_disk(
        output_dir=output_dir,
        run_specs=run_specs,
    )
    provider_execution_sha = _require_single_provider_execution_sha(outcomes)

    holdout_seal = verify_cohort_seal(
        case_path=candidate_holdout_case,
        seal_commit_sha=holdout_seal_commit_sha,
        repo_root=root,
        execution_commit_sha=provider_execution_sha,
    )
    adversarial_seal = verify_cohort_seal(
        case_path=adversarial_case,
        seal_commit_sha=adversarial_seal_commit_sha,
        repo_root=root,
        execution_commit_sha=provider_execution_sha,
    )
    verify_fixtures_tracked_at_commit(
        case_path=development_case,
        commit_sha=provider_execution_sha,
        repo_root=root,
    )
    verify_fixtures_tracked_at_commit(
        case_path=candidate_development_case,
        commit_sha=provider_execution_sha,
        repo_root=root,
    )
    verify_fixtures_tracked_at_commit(
        case_path=holdout_case,
        commit_sha=provider_execution_sha,
        repo_root=root,
    )
    if baseline_adversarial_case is not None:
        verify_fixtures_tracked_at_commit(
            case_path=baseline_adversarial_case,
            commit_sha=provider_execution_sha,
            repo_root=root,
        )

    validate_paired_case_equivalence(
        baseline_case_path=development_case,
        candidate_case_path=candidate_development_case,
        repo_root=root,
        pair_name="development",
    )
    validate_paired_case_equivalence(
        baseline_case_path=holdout_case,
        candidate_case_path=candidate_holdout_case,
        repo_root=root,
        pair_name="holdout",
    )
    if baseline_adversarial_case is not None:
        validate_paired_case_equivalence(
            baseline_case_path=baseline_adversarial_case,
            candidate_case_path=adversarial_case,
            repo_root=root,
            pair_name="adversarial",
        )

    expected_prompt: dict[tuple[PromptLane, CohortName], str] = {
        ("baseline", "development"): baseline_prompt_version,
        ("baseline", "holdout"): baseline_prompt_version,
        ("candidate", "development"): candidate_prompt_version,
        ("candidate", "holdout"): candidate_prompt_version,
        ("candidate", "adversarial"): candidate_prompt_version,
    }
    expected_case: dict[tuple[PromptLane, CohortName], str] = {
        ("baseline", "development"): baseline_development.case_id,
        ("baseline", "holdout"): baseline_holdout.case_id,
        ("candidate", "development"): candidate_development.case_id,
        ("candidate", "holdout"): holdout_seal.case_id,
        ("candidate", "adversarial"): adversarial_seal.case_id,
    }
    if baseline_adversarial is not None:
        expected_prompt[("baseline", "adversarial")] = baseline_prompt_version
        expected_case[("baseline", "adversarial")] = baseline_adversarial.case_id

    run_matrix = build_calibration_run_matrix(expected_case=expected_case)
    control_adversarial_enabled = baseline_adversarial_case is not None
    control_adversarial_case_id = (
        baseline_adversarial.case_id if baseline_adversarial is not None else None
    )

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
            expected_case_id=expected_case[(prompt_lane, cohort)],
            expected_repository_sha=provider_execution_sha,
        )
        for (prompt_lane, cohort), group_outcomes in sorted(cohort_groups.items())
    ]

    provider_run_repository_shas = [provider_execution_sha]

    decision, diagnostics = compute_calibration_decision(
        cohort_aggregates=cohort_aggregates,
        seals_verified=True,
        aggregate_build_sha=build_sha,
        provider_run_repository_shas=provider_run_repository_shas,
    )

    calibration_id_payload = {
        "baseline_prompt_version": baseline_prompt_version,
        "candidate_prompt_version": candidate_prompt_version,
        "baseline_prompt_sha256": compute_prompt_sha256(baseline_prompt_version),
        "candidate_prompt_sha256": compute_prompt_sha256(candidate_prompt_version),
        "holdout_case_sha256": holdout_seal.case_sha256,
        "holdout_seal_commit_sha": holdout_seal.seal_commit_sha,
        "adversarial_case_sha256": adversarial_seal.case_sha256,
        "adversarial_seal_commit_sha": adversarial_seal.seal_commit_sha,
        "model_id": model_id,
        "repetitions": repetitions,
        "repository_sha": build_sha,
        "aggregate_build_sha": build_sha,
        "provider_run_repository_shas": provider_run_repository_shas,
        "experiment_role": experiment_role,
        "control_adversarial_enabled": control_adversarial_enabled,
        "control_adversarial_case_id": control_adversarial_case_id,
        "run_matrix": [
            {
                "prompt_lane": entry.prompt_lane,
                "cohort": entry.cohort,
                "case_id": entry.case_id,
            }
            for entry in run_matrix
        ],
    }
    calibration_id = hashlib.sha256(
        json.dumps(calibration_id_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    aggregate = TemporalPromptCalibrationAggregateV1(
        calibration_id=f"temporal-prompt-calibration:{calibration_id}",
        repository_sha=build_sha,
        aggregate_build_sha=build_sha,
        provider_run_repository_shas=provider_run_repository_shas,
        holdout_case_sha256=holdout_seal.case_sha256,
        holdout_base_sha256=holdout_seal.base_sha256,
        holdout_gold_sha256=holdout_seal.gold_sha256,
        holdout_seal_commit_sha=holdout_seal.seal_commit_sha,
        adversarial_case_sha256=adversarial_seal.case_sha256,
        adversarial_base_sha256=adversarial_seal.base_sha256,
        adversarial_gold_sha256=adversarial_seal.gold_sha256,
        adversarial_seal_commit_sha=adversarial_seal.seal_commit_sha,
        seals_verified=True,
        baseline_prompt_version=baseline_prompt_version,
        candidate_prompt_version=candidate_prompt_version,
        candidate_prompt_sha256=compute_prompt_sha256(candidate_prompt_version),
        baseline_prompt_sha256=compute_prompt_sha256(baseline_prompt_version),
        model_id=model_id,
        repetitions=repetitions,
        experiment_role=experiment_role,
        run_matrix=run_matrix,
        control_adversarial_enabled=control_adversarial_enabled,
        control_adversarial_case_id=control_adversarial_case_id,
        slices=[
            _build_metrics_slice(
                prompt_lane="baseline",
                prompt_version=baseline_prompt_version,
                cohort_aggregates=cohort_aggregates,
            ),
            _build_metrics_slice(
                prompt_lane="candidate",
                prompt_version=candidate_prompt_version,
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
    parser = argparse.ArgumentParser(
        description="Run temporal prompt calibration (baseline vs candidate)"
    )
    parser.add_argument("--development-case", required=True)
    parser.add_argument("--candidate-development-case", required=True)
    parser.add_argument("--holdout-case", required=True)
    parser.add_argument("--candidate-holdout-case", required=True)
    parser.add_argument("--adversarial-case", required=True)
    parser.add_argument(
        "--baseline-adversarial-case",
        default=None,
        help="Optional baseline mirror of the adversarial cohort (adds baseline/adversarial lane)",
    )
    parser.add_argument("--model-id", default="gpt-5.4-mini")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--experiment-role",
        required=True,
        choices=["observed_regression", "promotion"],
        help="Aggregate role; participates in calibration_id",
    )
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
        help="Skip seal verification (requires --fake; never allowed for real provider runs)",
    )
    parser.add_argument("--fake", action="store_true")
    parser.add_argument(
        "--fake-batches-json",
        default=None,
        help="Optional JSON map of lane keys (baseline:development, etc.) to model batches",
    )
    parser.add_argument(
        "--reaggregate-only",
        action="store_true",
        help="Rebuild aggregate.json from on-disk run manifests (no provider calls)",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    output_dir = Path(args.output_dir)
    fake_batches = _load_fake_batches(
        Path(args.fake_batches_json) if args.fake_batches_json else None
    )
    # --fake implies skip; --skip-seal-verification alone is rejected unless fake=True.
    skip_seal = bool(args.skip_seal_verification or args.fake)

    if args.reaggregate_only:
        if args.fake or args.skip_seal_verification:
            raise SystemExit(
                "--reaggregate-only cannot be combined with --fake or "
                "--skip-seal-verification"
            )
        aggregate = reaggregate_existing_calibration_runs(
            development_case=Path(args.development_case),
            candidate_development_case=Path(args.candidate_development_case),
            holdout_case=Path(args.holdout_case),
            candidate_holdout_case=Path(args.candidate_holdout_case),
            adversarial_case=Path(args.adversarial_case),
            output_dir=output_dir,
            model_id=args.model_id,
            repetitions=args.repetitions,
            experiment_role=args.experiment_role,
            repo_root=repo_root,
            holdout_seal_commit_sha=args.holdout_seal_commit,
            adversarial_seal_commit_sha=args.adversarial_seal_commit,
            baseline_adversarial_case=(
                Path(args.baseline_adversarial_case)
                if args.baseline_adversarial_case
                else None
            ),
        )
    else:
        aggregate = run_prompt_calibration(
            development_case=Path(args.development_case),
            candidate_development_case=Path(args.candidate_development_case),
            holdout_case=Path(args.holdout_case),
            candidate_holdout_case=Path(args.candidate_holdout_case),
            adversarial_case=Path(args.adversarial_case),
            output_dir=output_dir,
            model_id=args.model_id,
            repetitions=args.repetitions,
            experiment_role=args.experiment_role,
            repo_root=repo_root,
            holdout_seal_commit_sha=args.holdout_seal_commit,
            adversarial_seal_commit_sha=args.adversarial_seal_commit,
            baseline_adversarial_case=(
                Path(args.baseline_adversarial_case)
                if args.baseline_adversarial_case
                else None
            ),
            skip_seal_verification=skip_seal,
            fake=args.fake,
            fake_batches=fake_batches,
        )
    print(
        json.dumps(
            {
                "ok": True,
                "calibration_id": aggregate.calibration_id,
                "experiment_role": aggregate.experiment_role,
                "control_adversarial_enabled": aggregate.control_adversarial_enabled,
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
