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

from extraction_lab.campaign_memory_baseline_manifest import load_baseline_manifest
from extraction_lab.campaign_memory_baseline_qualification import (
    qualify_baseline,
    render_report,
)
from extraction_lab.run_extraction_lab import run_extraction_lab
from extraction_lab.run_pair_experiment import (
    ExperimentFailure,
    _batch_telemetry,
    _load_model_policy,
    _observed_models,
    _repository_sha,
    _validate_batch_report,
    _worktree_clean,
)

ROOT = Path(__file__).resolve().parents[1]
BatchRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _runner(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def run_campaign_memory_baseline(
    *,
    manifest_path: Path,
    out_dir: Path,
    execute: bool = False,
    repo_root: Path = ROOT,
    batch_runner: BatchRunner = _runner,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    baseline = load_baseline_manifest(manifest_path, repo_root=repo_root)
    policy_path = baseline.repo_root / "MODEL_POLICY.json"
    _, policy_sha, planned_model = _load_model_policy(policy_path)
    pins = {
        "manifest": baseline.manifest_sha256,
        "benchmark": _sha(baseline.benchmark_path),
        "temporal": _sha(baseline.temporal_path),
        "entity_gold": _sha(baseline.entity_anchor_path),
        "fact_gold": _sha(baseline.fact_anchor_path),
        "policy": policy_sha,
        "sources": [_sha(p) for p in baseline.source_paths],
    }
    plan = {
        "experiment_id": baseline.manifest.experiment_id,
        "repository_sha": baseline.manifest.repository_sha,
        "repetitions": 3,
        "source_ingestions": 21,
        "sources": baseline.source_locators,
        "batch_size": 5,
        "resolved_structured_generation_model": planned_model,
        "will_execute": execute,
    }
    if out_dir.exists():
        raise ExperimentFailure("preflight", "output_root_already_exists")
    if not execute:
        return {"mode": "dry_run", "plan": plan}
    if not (environ or os.environ).get("OPENAI_API_KEY"):
        raise ExperimentFailure("preflight", "openai_api_key_missing")

    def assert_state(stage: str) -> None:
        if _repository_sha(baseline.repo_root) != baseline.manifest.repository_sha:
            raise ExperimentFailure(stage, "repository_sha_drift")
        if not _worktree_clean(baseline.repo_root):
            raise ExperimentFailure(stage, "worktree_drift")
        current = {
            "manifest": _sha(baseline.manifest_path),
            "benchmark": _sha(baseline.benchmark_path),
            "temporal": _sha(baseline.temporal_path),
            "entity_gold": _sha(baseline.entity_anchor_path),
            "fact_gold": _sha(baseline.fact_anchor_path),
            "policy": _sha(policy_path),
            "sources": [_sha(p) for p in baseline.source_paths],
        }
        if current != pins:
            raise ExperimentFailure(stage, "pinned_input_drift")

    assert_state("preflight")
    out_dir.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema": "dmb_campaign_memory_baseline_receipt_v1",
        "status": "running",
        "started_at": _now(),
        "completed_at": None,
        "manifest_sha256": baseline.manifest_sha256,
        "repository_sha": baseline.manifest.repository_sha,
        "pins": baseline.manifest.pins.model_dump(),
        "repetitions": [],
    }
    receipt_path = out_dir / "characterization_receipt.json"
    _write(receipt_path, receipt)
    expected_models: tuple[str, str] | None = None
    try:
        for index in range(1, 4):
            assert_state(f"rep_{index}_before")
            root = out_dir / f"rep-{index:03d}"
            root.mkdir()
            paths = root / "source_paths.txt"
            paths.write_text(
                "".join(f"{x}\n" for x in baseline.source_locators), encoding="utf-8"
            )
            store = root / "store"
            argv = [
                sys.executable,
                str(baseline.repo_root / "tools/batch_ingest_corpus.py"),
                "--store",
                str(store),
                "--corpus-root",
                str(baseline.corpus_root),
                "--paths-file",
                str(paths),
                "--batch-size",
                "5",
            ]
            result = batch_runner(argv, baseline.repo_root)
            (root / "stdout.log").write_text(
                result.stdout
                + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
                encoding="utf-8",
            )
            if result.returncode:
                raise ExperimentFailure(
                    f"rep_{index}_batch", f"batch_subprocess_exit_{result.returncode}"
                )
            report = _read(store / "logs" / "batch_report.json")
            _validate_batch_report(report, 7)
            entity_model, fact_model = _observed_models(
                store / "logs" / "model_calls.jsonl"
            )
            observed_models = (entity_model, fact_model)
            if expected_models is None:
                expected_models = observed_models
            elif observed_models != expected_models:
                raise ExperimentFailure(
                    f"rep_{index}_models", "observed_model_identity_drift"
                )
            assert_state(f"rep_{index}_before_scoring")
            lab = run_extraction_lab(
                store_path=store,
                surface="campaign_memory_development",
                out_dir=root / "extraction_lab",
                run_id=f"rep-{index:03d}",
                entity_anchor_path=baseline.entity_anchor_path,
                fact_anchor_path=baseline.fact_anchor_path,
                entity_model=entity_model,
                fact_model=fact_model,
                batch_size=5,
                pipeline_code_sha=baseline.manifest.repository_sha,
                corpus_source_root=baseline.corpus_root,
            )
            contract = _read(lab / "benchmark_contract.json")
            if (
                contract["corpus"]["fingerprint"]
                != baseline.manifest.pins.corpus_fingerprint
                or contract["gold"]["fingerprint"]
                != baseline.manifest.pins.gold_fingerprint
            ):
                raise ExperimentFailure(
                    f"rep_{index}_scoring", "benchmark_identity_mismatch"
                )
            telemetry = _batch_telemetry(report)
            tokens = telemetry.get("tokens") or {}
            cost = telemetry.get("cost_estimate") or {}
            window = telemetry.get("run_window") or {}
            calls = telemetry.get("api_calls") or {}
            input_tokens = tokens.get("input_tokens", 0)
            output_tokens = tokens.get("output_tokens", 0)
            row = {
                "index": index,
                "status": "completed",
                "store_path": str(store),
                "lab_run_path": str(lab),
                "observed_models": {"entity": entity_model, "fact": fact_model},
                "telemetry": {
                    "runtime_seconds": window.get("elapsed_seconds", 0),
                    "api_calls": calls.get("total", 0),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": cost.get("estimated_cost_usd", 0),
                },
            }
            receipt["repetitions"].append(row)
            _write(receipt_path, receipt)
            assert_state(f"rep_{index}_after")
        assert_state("before_qualification")
        qualification, witness = qualify_baseline(
            repetitions=receipt["repetitions"],
            benchmark_path=baseline.benchmark_path,
            temporal_path=baseline.temporal_path,
        )
        _write(out_dir / "qualification.json", qualification)
        _write(out_dir / "witness_index.json", witness)
        (out_dir / "report.md").write_text(
            render_report(qualification), encoding="utf-8"
        )
        receipt.update(
            {
                "status": "completed",
                "completed_at": _now(),
                "qualification_path": str(out_dir / "qualification.json"),
                "witness_index_path": str(out_dir / "witness_index.json"),
                "report_path": str(out_dir / "report.md"),
            }
        )
        _write(receipt_path, receipt)
        return receipt
    except Exception as exc:
        failure = (
            exc
            if isinstance(exc, ExperimentFailure)
            else ExperimentFailure("execution", type(exc).__name__)
        )
        receipt.update(
            {
                "status": "failed",
                "completed_at": _now(),
                "failure": {"stage": failure.stage, "reason": failure.reason},
            }
        )
        _write(receipt_path, receipt)
        raise failure from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        result = run_campaign_memory_baseline(
            manifest_path=args.manifest, out_dir=args.out_dir, execute=args.execute
        )
    except (ValueError, OSError, json.JSONDecodeError, ExperimentFailure) as exc:
        print(f"Characterization failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
