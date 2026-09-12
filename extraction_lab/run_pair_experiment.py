from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from extraction_lab.compare_experiment_runs import write_comparison
from extraction_lab.pair_experiment_manifest import (
    NormalizedPairExperiment,
    load_pair_experiment_manifest,
)
from extraction_lab.run_extraction_lab import run_extraction_lab


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = "dmb_extraction_pair_receipt_v1"
BatchRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
RepositoryShaReader = Callable[[Path], str]
WorktreeCleanReader = Callable[[Path], bool]


class ExperimentFailure(RuntimeError):
    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def _default_batch_runner(
    argv: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def _repository_sha(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _worktree_clean(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=True,
    )
    return not result.stdout.strip()


def _load_model_policy(policy_path: Path) -> tuple[dict[str, Any], str, str]:
    if not policy_path.is_file():
        raise ExperimentFailure("preflight", "model_policy_missing")
    raw = policy_path.read_bytes()
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExperimentFailure("preflight", "model_policy_invalid") from exc
    action = policy.get("actions", {}).get("structured_generation")
    model = policy.get("models", {}).get(action)
    if not isinstance(action, str) or not isinstance(model, str) or not model.strip():
        raise ExperimentFailure("preflight", "structured_generation_model_unresolved")
    return policy, _sha256_bytes(raw), model.strip()


def _assert_policy_unchanged(
    policy_path: Path, expected_sha256: str, *, stage: str
) -> None:
    if not policy_path.is_file() or _file_sha256(policy_path) != expected_sha256:
        raise ExperimentFailure(stage, "model_policy_changed_during_experiment")


def _normalized_plan(
    pair: NormalizedPairExperiment, *, model_policy_sha256: str, model_id: str
) -> dict[str, Any]:
    manifest = pair.manifest
    return {
        "schema": manifest.schema_name,
        "experiment_id": manifest.experiment_id,
        "repository_sha": manifest.repository_sha,
        "surface": manifest.surface,
        "corpus_root": str(pair.corpus_root),
        "sources": list(pair.source_locators),
        "entity_anchors": str(pair.entity_anchor_path),
        "fact_anchors": str(pair.fact_anchor_path),
        "execution": manifest.execution.model_dump(),
        "variants": manifest.variants.model_dump(),
        "model_policy_sha256": model_policy_sha256,
        "resolved_structured_generation_model": model_id,
        "will_execute": False,
    }


def _observed_models(model_calls_path: Path) -> tuple[str, str]:
    if not model_calls_path.is_file():
        raise ExperimentFailure("observed_models", "model_calls_log_missing")
    rows = _read_jsonl(model_calls_path)
    observed: dict[str, set[str]] = {
        "entity_extraction": set(),
        "fact_extraction": set(),
    }
    for row in rows:
        stage = row.get("stage")
        if stage not in observed:
            continue
        model_name = str(row.get("model_name", "")).strip()
        if model_name:
            observed[stage].add(model_name)
    for stage, models in observed.items():
        if not models:
            raise ExperimentFailure("observed_models", f"{stage}_model_missing")
        if len(models) != 1:
            raise ExperimentFailure("observed_models", f"{stage}_model_ambiguous")
    return next(iter(observed["entity_extraction"])), next(
        iter(observed["fact_extraction"])
    )


def _batch_telemetry(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: report.get(key)
        for key in (
            "run_window",
            "files",
            "api_calls",
            "tokens",
            "cost_estimate",
            "local_cache",
            "timing",
        )
    }


def _initial_receipt(
    pair: NormalizedPairExperiment, *, policy_path: Path, policy_sha256: str
) -> dict[str, Any]:
    manifest = pair.manifest
    return {
        "schema": RECEIPT_SCHEMA,
        "experiment_id": manifest.experiment_id,
        "manifest_sha256": pair.manifest_sha256,
        "status": "running",
        "started_at": _utc_now_iso(),
        "completed_at": None,
        "repository_sha": manifest.repository_sha,
        "worktree_clean_at_start": True,
        "corpus_root": str(pair.corpus_root),
        "sources": [
            {"locator": locator, "sha256": _file_sha256(path)}
            for locator, path in zip(
                pair.source_locators, pair.source_paths, strict=True
            )
        ],
        "surface": manifest.surface,
        "gold": {
            "entity": {
                "path": str(pair.entity_anchor_path),
                "sha256": _file_sha256(pair.entity_anchor_path),
            },
            "fact": {
                "path": str(pair.fact_anchor_path),
                "sha256": _file_sha256(pair.fact_anchor_path),
            },
        },
        "model_policy_path": str(policy_path),
        "model_policy_sha256": policy_sha256,
        "cache_policy": manifest.execution.cache_policy,
        "execution_mode": manifest.execution.mode,
        "variants": {
            "baseline": {
                "status": "not_started",
                "batch_size": manifest.variants.baseline.batch_size,
            },
            "candidate": {
                "status": "not_started",
                "batch_size": manifest.variants.candidate.batch_size,
            },
        },
        "comparison": {"status": "not_started"},
        "failure": None,
    }


def _validate_batch_report(report: dict[str, Any], source_count: int) -> None:
    files = report.get("files", {})
    if (
        files.get("succeeded") != source_count
        or files.get("failed") != 0
        or files.get("skipped") != 0
    ):
        raise ExperimentFailure("batch_execution", "batch_report_not_fully_successful")


def _execute_variant(
    *,
    pair: NormalizedPairExperiment,
    experiment_root: Path,
    variant: str,
    batch_size: int,
    batch_runner: BatchRunner,
) -> dict[str, Any]:
    variant_root = experiment_root / variant
    store_path = variant_root / "store"
    lab_root = variant_root / "extraction_lab"
    paths_file = variant_root / "source_paths.txt"
    variant_root.mkdir(parents=True, exist_ok=False)
    paths_file.write_text(
        "".join(f"{locator}\n" for locator in pair.source_locators), encoding="utf-8"
    )
    stdout_path = variant_root / "stdout.log"
    argv = [
        sys.executable,
        str(pair.repo_root / "tools" / "batch_ingest_corpus.py"),
        "--store",
        str(store_path),
        "--corpus-root",
        str(pair.corpus_root),
        "--paths-file",
        str(paths_file),
        "--batch-size",
        str(batch_size),
    ]
    result = batch_runner(argv, pair.repo_root)
    stdout_path.write_text(
        result.stdout + (f"\n[stderr]\n{result.stderr}" if result.stderr else ""),
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise ExperimentFailure(
            f"{variant}_batch_execution", f"batch_subprocess_exit_{result.returncode}"
        )

    summary_path = store_path / "logs" / "batch_ingest_summary.json"
    report_path = store_path / "logs" / "batch_report.json"
    if not summary_path.is_file() or not report_path.is_file():
        raise ExperimentFailure(f"{variant}_batch_execution", "batch_artifacts_missing")
    report = _read_json(report_path)
    _validate_batch_report(report, len(pair.source_paths))
    entity_model, fact_model = _observed_models(
        store_path / "logs" / "model_calls.jsonl"
    )

    run_dir = run_extraction_lab(
        store_path=store_path,
        surface=pair.manifest.surface,
        out_dir=lab_root,
        run_id=variant,
        entity_anchor_path=pair.entity_anchor_path,
        fact_anchor_path=pair.fact_anchor_path,
        entity_model=entity_model,
        fact_model=fact_model,
        batch_size=batch_size,
        pipeline_code_sha=pair.manifest.repository_sha,
        corpus_source_root=pair.corpus_root,
    )
    benchmark_contract = _read_json(run_dir / "benchmark_contract.json")
    if not benchmark_contract.get("corpus", {}).get("available"):
        raise ExperimentFailure(
            f"{variant}_scoring", "benchmark_corpus_identity_unqualified"
        )
    return {
        "status": "completed",
        "batch_size": batch_size,
        "store_path": str(store_path),
        "cache_path": str(store_path / ".cache"),
        "paths_file": str(paths_file),
        "stdout_path": str(stdout_path),
        "ingest_summary_path": str(summary_path),
        "batch_report_path": str(report_path),
        "observed_models": {
            "entity_extraction": entity_model,
            "fact_extraction": fact_model,
        },
        "telemetry": _batch_telemetry(report),
        "extraction_lab_run_path": str(run_dir),
        "benchmark_fingerprint": benchmark_contract["corpus"]["fingerprint"],
        "pipeline_contract": _read_json(run_dir / "pipeline_contract.json"),
    }


def run_pair_experiment(
    *,
    manifest_path: Path,
    out_dir: Path,
    execute: bool = False,
    repo_root: Path = ROOT,
    batch_runner: BatchRunner = _default_batch_runner,
    repository_sha_reader: RepositoryShaReader = _repository_sha,
    worktree_clean_reader: WorktreeCleanReader = _worktree_clean,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    pair = load_pair_experiment_manifest(manifest_path, repo_root=repo_root)
    current_sha = repository_sha_reader(pair.repo_root)
    if current_sha != pair.manifest.repository_sha:
        raise ExperimentFailure("preflight", "repository_sha_mismatch")
    if out_dir.exists():
        raise ExperimentFailure("preflight", "output_root_already_exists")
    policy_path = pair.repo_root / "MODEL_POLICY.json"
    _, policy_sha256, structured_model = _load_model_policy(policy_path)
    plan = _normalized_plan(
        pair, model_policy_sha256=policy_sha256, model_id=structured_model
    )
    if not execute:
        return {"mode": "dry_run", "plan": plan}

    if not worktree_clean_reader(pair.repo_root):
        raise ExperimentFailure("preflight", "worktree_not_clean")
    active_environ = os.environ if environ is None else environ
    if not active_environ.get("OPENAI_API_KEY"):
        raise ExperimentFailure("preflight", "openai_api_key_missing")
    _assert_policy_unchanged(policy_path, policy_sha256, stage="preflight")

    experiment_root = out_dir.resolve()
    experiment_root.mkdir(parents=True, exist_ok=False)
    receipt_path = experiment_root / "experiment_receipt.json"
    receipt = _initial_receipt(
        pair, policy_path=policy_path, policy_sha256=policy_sha256
    )
    _write_json_atomic(receipt_path, receipt)

    current_stage = "baseline"
    try:
        for variant in ("baseline", "candidate"):
            current_stage = variant
            variant_config = getattr(pair.manifest.variants, variant)
            receipt["variants"][variant]["status"] = "running"
            _write_json_atomic(receipt_path, receipt)
            variant_receipt = _execute_variant(
                pair=pair,
                experiment_root=experiment_root,
                variant=variant,
                batch_size=variant_config.batch_size,
                batch_runner=batch_runner,
            )
            receipt["variants"][variant] = variant_receipt
            _write_json_atomic(receipt_path, receipt)
            _assert_policy_unchanged(
                policy_path, policy_sha256, stage=f"after_{variant}"
            )

        current_stage = "comparison"
        comparison_dir = experiment_root / "comparison"
        comparison = write_comparison(
            baseline_dir=Path(
                receipt["variants"]["baseline"]["extraction_lab_run_path"]
            ),
            candidate_dir=Path(
                receipt["variants"]["candidate"]["extraction_lab_run_path"]
            ),
            out_dir=comparison_dir,
        )
        receipt["comparison"] = {
            "status": "completed" if comparison.get("comparable") else "failed",
            "artifact_path": str(comparison_dir / "comparison.json"),
            "report_path": str(comparison_dir / "report.md"),
            "comparable": bool(comparison.get("comparable")),
            "non_comparable_reasons": comparison.get("non_comparable_reasons", []),
        }
        if not comparison.get("comparable"):
            raise ExperimentFailure("comparison", "comparison_not_comparable")
        receipt["status"] = "completed"
        receipt["completed_at"] = _utc_now_iso()
        _write_json_atomic(receipt_path, receipt)
        return receipt
    except Exception as exc:
        failure = (
            exc
            if isinstance(exc, ExperimentFailure)
            else ExperimentFailure(current_stage, type(exc).__name__)
        )
        if receipt["variants"].get(current_stage, {}).get("status") == "running":
            receipt["variants"][current_stage]["status"] = "failed"
            receipt["variants"][current_stage]["failure_reason"] = failure.reason
        receipt["status"] = "failed"
        receipt["completed_at"] = _utc_now_iso()
        receipt["failure"] = {"stage": failure.stage, "reason": failure.reason}
        _write_json_atomic(receipt_path, receipt)
        raise failure from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one bounded isolated extraction experiment pair."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--execute", action="store_true", help="Authorize paid realtime model execution"
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        result = run_pair_experiment(
            manifest_path=args.manifest, out_dir=args.out_dir, execute=args.execute
        )
    except (ExperimentFailure, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
