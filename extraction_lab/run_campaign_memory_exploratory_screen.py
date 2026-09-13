from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from dotenv import load_dotenv

from extraction_lab.campaign_memory_corpus_census import census_corpus
from extraction_lab.campaign_memory_exploratory_qualification import qualify_screen
from extraction_lab.campaign_memory_exploratory_screen_manifest import (
    MODELS,
    argv_leaks_evaluator_authority,
    load_screen_manifest,
    sha,
)
from extraction_lab.campaign_memory_output_contract_audit import build_output_contract_audit
from extraction_lab.run_extraction_lab import run_extraction_lab
from extraction_lab.run_pair_experiment import (
    ExperimentFailure,
    _load_model_policy,
    _observed_models,
    _repository_sha,
    _validate_batch_report,
    _worktree_clean,
)
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
CensusFn = Callable[..., dict[str, Any]]
LabFn = Callable[..., Path]
ShaReader = Callable[[Path], str]
CleanReader = Callable[[Path], bool]
PLANNED_COST = {"gpt-5.6-luna": 0.20, "gpt-5.6-terra": 1.70, "gpt-5.6-sol": 2.90}
BUDGET_CEILING_USD = 8.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _runner(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def _ensure_api_key(repo_root: Path, environ: dict[str, str]) -> None:
    if environ.get("OPENAI_API_KEY", "").strip():
        return
    load_dungeonmindbuddy_dotenv()
    if os.environ.get("OPENAI_API_KEY", "").strip():
        environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        return
    common = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
        text=True,
        capture_output=True,
        check=False,
    )
    if common.returncode != 0:
        return
    git_common = Path(common.stdout.strip())
    if not git_common.is_absolute():
        git_common = (repo_root / git_common).resolve()
    env_path = git_common.parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        if os.environ.get("OPENAI_API_KEY", "").strip():
            environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]


def _arm_telemetry(report: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    token = report["tokens"]
    cached = int(token.get("cached_input_tokens", token.get("cached_tokens", 0)) or 0)
    uncached = token.get("uncached_input_tokens")
    if uncached is None:
        uncached = max(0, int(token.get("input_tokens", 0) or 0) - cached)
    reasoning = token.get("reasoning_tokens")
    output = int(token.get("output_tokens", 0) or 0)
    visible = token.get("visible_output_tokens")
    persisted = counts["entities"] + counts["facts"]
    return {
        "input_tokens": token.get("input_tokens", 0),
        "cached_input_tokens": cached,
        "uncached_input_tokens": uncached,
        "output_tokens": output,
        "reasoning_tokens": reasoning,
        "visible_output_tokens": visible,
        "parsed_structured_output_bytes": token.get("parsed_output_bytes"),
        "api_calls": report["api_calls"]["total"],
        "persisted_entity_count": counts["entities"],
        "persisted_fact_count": counts["facts"],
        "visible_output_tokens_per_persisted_row": (
            visible / persisted if visible is not None and persisted else None
        ),
        "total_output_tokens_per_persisted_row": (
            output / persisted if persisted else None
        ),
        "reasoning_fraction_of_output": (
            reasoning / output if reasoning is not None and output else None
        ),
        "cache_hit_fraction": token.get("cache_rate"),
        "cost_usd": report["cost_estimate"]["estimated_cost_usd"],
        "wall_time_seconds": report["run_window"]["elapsed_seconds"],
    }


def run_screen(
    *,
    manifest_path: Path,
    out_dir: Path,
    repo_root: Path,
    execute: bool = False,
    runner: Runner = _runner,
    environ: dict[str, str] | None = None,
    repository_sha_reader: ShaReader = _repository_sha,
    worktree_clean_reader: CleanReader = _worktree_clean,
    census_fn: CensusFn = census_corpus,
    lab_fn: LabFn = run_extraction_lab,
    planned_costs: dict[str, float] | None = None,
    budget_ceiling_usd: float = BUDGET_CEILING_USD,
) -> dict[str, Any]:
    manifest, ctx = load_screen_manifest(manifest_path, repo_root=repo_root)
    audit = build_output_contract_audit()
    policy_path = repo_root / "MODEL_POLICY.json"
    _, policy_sha, policy_model = _load_model_policy(policy_path)
    pins = {
        "manifest": sha(manifest_path),
        "benchmark": sha(ctx["benchmark_path"]),
        "temporal": sha(ctx["temporal_path"]),
        "entity_gold": sha(ctx["entity_gold"]),
        "fact_gold": sha(ctx["fact_gold"]),
        "policy": policy_sha,
        "sources": [sha(path) for path in ctx["sources"]],
        "prompt": audit["prompt_sha256"],
        "schema": audit["structured_output_schema_sha256"],
    }
    plan = {
        "models": list(MODELS),
        "run_order": list(MODELS),
        "repetitions_per_model": 1,
        "repository_sha": manifest.repository_sha,
        "source_count": 7,
        "batch_size": 5,
        "service_tier": "flex",
        "cache_policy": "isolated",
        "reasoning_effort": "medium",
        "fact_contract": "payload_lean_v1",
        "production_policy_model": policy_model,
        "pins": pins,
        "will_execute": execute,
        "resume": False,
        "batch_api": False,
        "auto_escalation": False,
    }
    if out_dir.exists():
        raise ExperimentFailure("preflight", "output_root_already_exists")
    if not execute:
        return {"mode": "dry_run", "plan": plan, "api_calls": 0}

    env = dict(environ if environ is not None else os.environ)
    _ensure_api_key(repo_root, env)
    if not env.get("OPENAI_API_KEY"):
        raise ExperimentFailure("preflight", "openai_api_key_missing")

    def assert_state(stage: str) -> None:
        if repository_sha_reader(repo_root) != manifest.repository_sha:
            raise ExperimentFailure(stage, "repository_state_drift")
        if not worktree_clean_reader(repo_root):
            raise ExperimentFailure(stage, "repository_state_drift")
        current = {
            "manifest": sha(manifest_path),
            "benchmark": sha(ctx["benchmark_path"]),
            "temporal": sha(ctx["temporal_path"]),
            "entity_gold": sha(ctx["entity_gold"]),
            "fact_gold": sha(ctx["fact_gold"]),
            "policy": sha(policy_path),
            "sources": [sha(path) for path in ctx["sources"]],
            "prompt": build_output_contract_audit()["prompt_sha256"],
            "schema": build_output_contract_audit()["structured_output_schema_sha256"],
        }
        if current != pins:
            raise ExperimentFailure(stage, "pinned_input_drift")

    assert_state("preflight")
    started = time.perf_counter()
    out_dir.mkdir(parents=True)
    _write(out_dir / "output_contract_audit.json", audit)
    seven_census = census_fn(ctx["corpus_root"], batch_size=5, paths=ctx["sources"])
    full_census = census_fn(ctx["corpus_root"], batch_size=5)
    _write(out_dir / "seven_source_census.json", seven_census)
    _write(out_dir / "corpus_census.json", full_census)
    receipt: dict[str, Any] = {
        "schema": "dmb_campaign_memory_exploratory_screen_receipt_v1",
        "status": "running",
        "started_at": _now(),
        "repository_sha": manifest.repository_sha,
        "manifest_sha256": pins["manifest"],
        "pins": pins,
        "arms": [],
        "census_path": str(out_dir / "corpus_census.json"),
        "seven_source_census_path": str(out_dir / "seven_source_census.json"),
        "total_cost_usd": 0.0,
    }
    receipt_path = out_dir / "receipt.json"
    _write(receipt_path, receipt)
    costs = planned_costs or PLANNED_COST
    try:
        for model in MODELS:
            assert_state(f"{model}_before")
            projected_next = float(receipt["total_cost_usd"]) + float(costs[model])
            if projected_next > budget_ceiling_usd:
                raise ExperimentFailure(model, "budget_guard_would_exceed_8_usd")
            arm_root = out_dir / model
            arm_root.mkdir()
            paths_file = arm_root / "source_paths.txt"
            paths_file.write_text(
                "".join(f"{item}\n" for item in ctx["source_locators"]), encoding="utf-8"
            )
            store = arm_root / "store"
            row = {
                "index": 1,
                "model": model,
                "status": "running",
                "started_at": _now(),
                "store_path": str(store),
            }
            receipt["arms"].append(row)
            _write(receipt_path, receipt)
            argv = [
                sys.executable,
                str(repo_root / "tools/batch_ingest_corpus.py"),
                "--store",
                str(store),
                "--corpus-root",
                str(ctx["corpus_root"]),
                "--paths-file",
                str(paths_file),
                "--batch-size",
                "5",
                "--structured-generation-model",
                model,
                "--openai-service-tier",
                "flex",
                "--normalize-legacy-frontmatter",
                "--fact-contract",
                "payload_lean_v1",
                "--reasoning-effort",
                "medium",
            ]
            leaks = argv_leaks_evaluator_authority(argv)
            if leaks:
                raise ExperimentFailure(model, f"evaluator_authority_leak:{','.join(leaks)}")
            if "--resume" in argv or "--use-batch-api" in argv or "--auto-escalate" in argv:
                raise ExperimentFailure(model, "forbidden_batch_flag")
            result = runner(argv, repo_root)
            (arm_root / "stdout.log").write_text(
                result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
                encoding="utf-8",
            )
            if result.returncode:
                raise ExperimentFailure(model, f"batch_subprocess_exit_{result.returncode}")
            report = _read(store / "logs" / "batch_report.json")
            _validate_batch_report(report, 7)
            observed = _observed_models(store / "logs" / "model_calls.jsonl")
            if observed != (model, model):
                raise ExperimentFailure(model, "observed_model_mismatch")
            assert_state(f"{model}_before_scoring")
            lab = lab_fn(
                store_path=store,
                surface="campaign_memory_development",
                out_dir=arm_root / "extraction_lab",
                run_id=model,
                entity_anchor_path=ctx["entity_gold"],
                fact_anchor_path=ctx["fact_gold"],
                entity_model=model,
                fact_model=model,
                batch_size=5,
                pipeline_code_sha=manifest.repository_sha,
                corpus_source_root=ctx["corpus_root"],
            )
            counts = {
                "entities": len(_read(store / "entities.json")),
                "facts": len(_read(store / "facts.json")),
            }
            telemetry = _arm_telemetry(report, counts)
            row.update(
                {
                    "status": "completed",
                    "completed_at": _now(),
                    "batch_report": str(store / "logs/batch_report.json"),
                    "lab_run_path": str(lab),
                    "observed_models": observed,
                    "counts": counts,
                    "telemetry": telemetry,
                }
            )
            receipt["total_cost_usd"] = round(
                float(receipt["total_cost_usd"]) + float(telemetry["cost_usd"]), 4
            )
            _write(receipt_path, receipt)
            assert_state(f"{model}_after")

        qualification = qualify_screen(
            receipt,
            seven_source_census=seven_census,
            full_corpus_census=full_census,
        )
        _write(out_dir / "qualification.json", qualification)
        receipt.update(
            {
                "status": "completed",
                "completed_at": _now(),
                "duration_seconds": time.perf_counter() - started,
                "qualification_path": str(out_dir / "qualification.json"),
            }
        )
        _write(receipt_path, receipt)
        return receipt
    except Exception as exc:
        failure = (
            exc if isinstance(exc, ExperimentFailure) else ExperimentFailure("execution", type(exc).__name__)
        )
        if receipt["arms"] and receipt["arms"][-1]["status"] == "running":
            receipt["arms"][-1]["status"] = "failed"
        receipt.update(
            {
                "status": "failed",
                "completed_at": _now(),
                "duration_seconds": time.perf_counter() - started,
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
        result = run_screen(
            manifest_path=args.manifest,
            out_dir=args.out_dir,
            repo_root=Path.cwd(),
            execute=args.execute,
        )
    except Exception as exc:
        print(f"Screen failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
