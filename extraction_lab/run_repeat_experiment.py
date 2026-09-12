from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from extraction_lab.repeat_experiment_manifest import load_repeat_experiment_manifest
from extraction_lab.repeat_experiment_qualification import (
    execution_identity,
    identity_mismatch_reason,
    qualify_repetitions,
    render_report,
)
from extraction_lab.run_pair_experiment import ROOT, ExperimentFailure, run_pair_experiment


REPEAT_RECEIPT_SCHEMA = "dmb_extraction_repeat_receipt_v1"
PairRunner = Callable[..., dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _pair_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_pair_manifest_pinned(*, path: Path, expected: str, stage: str) -> None:
    if _pair_sha(path) != expected:
        raise ExperimentFailure(stage, "pair_manifest_drift")


def run_repeat_experiment(
    *,
    manifest_path: Path,
    out_dir: Path,
    execute: bool = False,
    repo_root: Path = ROOT,
    pair_runner: PairRunner = run_pair_experiment,
) -> dict[str, Any]:
    repeat = load_repeat_experiment_manifest(manifest_path, repo_root=repo_root)
    if out_dir.exists():
        raise ExperimentFailure("preflight", "output_root_already_exists")
    dry = pair_runner(
        manifest_path=repeat.pair_manifest_path,
        out_dir=out_dir / "preflight",
        execute=False,
        repo_root=repo_root,
    )
    plan = {
        "experiment_id": repeat.manifest.experiment_id,
        "will_execute": execute,
        "repetitions": repeat.manifest.repetitions,
        "variant_runs": repeat.manifest.repetitions * 2,
        "source_ingestions": repeat.manifest.repetitions * 2 * len(repeat.pair.source_paths),
        "pair_manifest": str(repeat.pair_manifest_path),
        "pair_manifest_sha256": repeat.pair_manifest_sha256,
        "isolated_output_roots": True,
        "pair_preflight": dry.get("plan", dry),
    }
    if not execute:
        return {"mode": "dry_run", "plan": plan}

    out_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = out_dir / "repeat_receipt.json"
    receipt: dict[str, Any] = {
        "schema": REPEAT_RECEIPT_SCHEMA,
        "experiment_id": repeat.manifest.experiment_id,
        "status": "running",
        "started_at": _utc_now(),
        "completed_at": None,
        "manifest_sha256": repeat.manifest_sha256,
        "pair_manifest_path": str(repeat.pair_manifest_path),
        "pair_manifest_sha256": repeat.pair_manifest_sha256,
        "requested_repetitions": repeat.manifest.repetitions,
        "completed_repetitions": 0,
        "repository_sha": repeat.pair.manifest.repository_sha,
        "sources": [
            {"locator": locator, "sha256": _pair_sha(path)}
            for locator, path in zip(
                repeat.pair.source_locators, repeat.pair.source_paths, strict=True
            )
        ],
        "gold": {
            "entity": {
                "path": str(repeat.pair.entity_anchor_path),
                "sha256": _pair_sha(repeat.pair.entity_anchor_path),
            },
            "fact": {
                "path": str(repeat.pair.fact_anchor_path),
                "sha256": _pair_sha(repeat.pair.fact_anchor_path),
            },
        },
        "model_policy_sha256": _pair_sha(repo_root / "MODEL_POLICY.json"),
        "fixed_execution_order": "repetition ascending; baseline then candidate",
        "repetitions": [],
        "qualification_path": None,
        "report_path": None,
    }
    _write_json(receipt_path, receipt)
    successful: list[dict[str, Any]] = []
    expected_identity: dict[str, Any] | None = None
    try:
        for index in range(1, repeat.manifest.repetitions + 1):
            stage = f"rep-{index:03d}"
            _assert_pair_manifest_pinned(
                path=repeat.pair_manifest_path,
                expected=repeat.pair_manifest_sha256,
                stage=stage,
            )
            child_root = out_dir / f"rep-{index:03d}"
            row = {
                "index": index,
                "status": "running",
                "child_root": str(child_root),
                "child_receipt_path": str(child_root / "experiment_receipt.json"),
                "child_receipt_sha256": None,
                "comparable": None,
                "failure": None,
            }
            receipt["repetitions"].append(row)
            _write_json(receipt_path, receipt)
            try:
                child = pair_runner(
                    manifest_path=repeat.pair_manifest_path,
                    out_dir=child_root,
                    execute=True,
                    repo_root=repo_root,
                )
            except Exception as exc:
                row["status"] = "failed"
                row["failure"] = {
                    "type": type(exc).__name__,
                    "detail": str(exc),
                }
                raise
            if child.get("status") != "completed":
                raise ExperimentFailure(stage, "child_not_completed")
            if child.get("schema") != "dmb_extraction_pair_receipt_v1":
                raise ExperimentFailure(stage, "child_receipt_schema_invalid")
            if child.get("manifest_sha256") != repeat.pair_manifest_sha256:
                raise ExperimentFailure(stage, "child_pair_manifest_sha_mismatch")
            _assert_pair_manifest_pinned(
                path=repeat.pair_manifest_path,
                expected=repeat.pair_manifest_sha256,
                stage=stage,
            )
            comparison = child.get("comparison", {})
            if comparison.get("status") != "completed" or comparison.get("comparable") is not True:
                raise ExperimentFailure(stage, "child_not_comparable")
            identity = execution_identity(child)
            if expected_identity is None:
                expected_identity = identity
            else:
                mismatch = identity_mismatch_reason(expected_identity, identity)
                if mismatch:
                    raise ExperimentFailure(stage, mismatch)
            successful.append(child)
            child_receipt_path = child_root / "experiment_receipt.json"
            child_bytes = (
                child_receipt_path.read_bytes()
                if child_receipt_path.is_file()
                else json.dumps(child, sort_keys=True).encode("utf-8")
            )
            row.update(
                {
                    "status": "completed",
                    "child_receipt_sha256": hashlib.sha256(child_bytes).hexdigest(),
                    "comparable": True,
                }
            )
            receipt["completed_repetitions"] = len(successful)
            _write_json(receipt_path, receipt)

        _assert_pair_manifest_pinned(
            path=repeat.pair_manifest_path,
            expected=repeat.pair_manifest_sha256,
            stage="qualification",
        )
        qualification = qualify_repetitions(successful)
        qualification_path = out_dir / "qualification.json"
        report_path = out_dir / "report.md"
        _write_json(qualification_path, qualification)
        report_path.write_text(render_report(qualification), encoding="utf-8")
        receipt.update(
            {
                "status": "completed",
                "completed_at": _utc_now(),
                "qualification_path": str(qualification_path),
                "report_path": str(report_path),
            }
        )
        _write_json(receipt_path, receipt)
        return receipt
    except Exception as exc:
        failure = exc if isinstance(exc, ExperimentFailure) else ExperimentFailure("repeat", type(exc).__name__)
        if receipt["repetitions"] and receipt["repetitions"][-1]["status"] == "running":
            receipt["repetitions"][-1]["status"] = "failed"
            receipt["repetitions"][-1]["failure"] = {
                "stage": failure.stage,
                "reason": failure.reason,
            }
        receipt["status"] = "failed"
        receipt["completed_at"] = _utc_now()
        receipt["failure"] = {"stage": failure.stage, "reason": failure.reason}
        _write_json(receipt_path, receipt)
        raise failure from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Repeat one bounded extraction pair experiment.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Authorize paid realtime model execution")
    args = parser.parse_args()
    try:
        result = run_repeat_experiment(manifest_path=args.manifest, out_dir=args.out_dir, execute=args.execute)
    except (ExperimentFailure, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Repeat experiment failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
