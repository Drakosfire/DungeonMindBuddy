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

from extraction_lab.campaign_memory_corpus_census import census_corpus
from extraction_lab.campaign_memory_exploratory_screen_manifest import (
    argv_leaks_evaluator_authority,
    load_screen_manifest,
    sha,
)
from extraction_lab.campaign_memory_output_contract_audit import build_output_contract_audit
from extraction_lab.campaign_memory_stage4i2_quality_packet import build_quality_packet
from extraction_lab.run_extraction_lab import run_extraction_lab
from extraction_lab.run_pair_experiment import (
    ExperimentFailure,
    _load_model_policy,
    _observed_models,
    _repository_sha,
    _validate_batch_report,
    _worktree_clean,
)
from src.llm.experiment_provider import (
    DEEPSEEK_FLASH_SLUG,
    ensure_experiment_secrets,
    openai_key_present,
    openrouter_key_present,
)

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
CensusFn = Callable[..., dict[str, Any]]
LabFn = Callable[..., Path]
ShaReader = Callable[[Path], str]
CleanReader = Callable[[Path], bool]

DEEPSEEK_EFFORTS = ("none", "low", "high", "max")
LUNA_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")
LUNA_MODEL = "gpt-5.6-luna"
OPERATOR_BUDGET_WAIVED = True
BUDGET_CEILING_USD = 1000.0
REASONING_CONTRACT = {
    "luna_efforts": list(LUNA_EFFORTS),
    "deepseek_efforts": list(DEEPSEEK_EFFORTS),
    "deepseek_cannot_honor_medium": True,
    "deepseek_catalog_default_effort": "high",
    "openrouter_none_means_reasoning_disabled": True,
    "non_equivalence": "DeepSeek OpenRouter efforts are none/low/high/max; Luna uses none/low/medium/high/xhigh/max.",
}


def stage4i2_arms() -> list[dict[str, str]]:
    arms: list[dict[str, str]] = []
    for effort in DEEPSEEK_EFFORTS:
        arms.append(
            {
                "arm_id": f"deepseek-{effort}",
                "model": DEEPSEEK_FLASH_SLUG,
                "provider": "openrouter",
                "service_tier": "standard",
                "reasoning_effort": effort,
                "openrouter_provider_pin": "DeepSeek",
            }
        )
    for effort in LUNA_EFFORTS:
        arms.append(
            {
                "arm_id": f"luna-standard-{effort}",
                "model": LUNA_MODEL,
                "provider": "openai",
                "service_tier": "standard",
                "reasoning_effort": effort,
                "openrouter_provider_pin": "",
            }
        )
    for effort in LUNA_EFFORTS:
        arms.append(
            {
                "arm_id": f"luna-flex-{effort}",
                "model": LUNA_MODEL,
                "provider": "openai",
                "service_tier": "flex",
                "reasoning_effort": effort,
                "openrouter_provider_pin": "",
            }
        )
    return arms


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _runner(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)


def arm_ingest_argv(
    *,
    repo_root: Path,
    store: Path,
    corpus_root: Path,
    paths_file: Path,
    arm: dict[str, str],
) -> list[str]:
    argv = [
        sys.executable,
        str(repo_root / "tools/batch_ingest_corpus.py"),
        "--store",
        str(store),
        "--corpus-root",
        str(corpus_root),
        "--paths-file",
        str(paths_file),
        "--batch-size",
        "5",
        "--structured-generation-model",
        arm["model"],
        "--openai-service-tier",
        arm["service_tier"],
        "--normalize-legacy-frontmatter",
        "--fact-contract",
        "payload_lean_v1",
        "--reasoning-effort",
        arm["reasoning_effort"],
        "--extraction-context-mode",
        "whole_document",
        "--extraction-provider",
        arm["provider"],
        "--extraction-transport",
        "chat_completions" if arm["provider"] == "openrouter" else "responses",
    ]
    if arm["provider"] == "openrouter":
        argv.extend(["--openrouter-provider-pin", arm["openrouter_provider_pin"] or "DeepSeek"])
    return argv


def _throughput(value: float | None, seconds: float) -> float | None:
    if value is None or seconds <= 0:
        return None
    return value / seconds


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
    wall = float(report["run_window"]["elapsed_seconds"] or 0)
    timing = report.get("timing") or {}
    request_seconds = None
    samples = timing.get("request_elapsed_count")
    p50 = timing.get("request_elapsed_p50_ms")
    if p50 is not None and samples:
        request_seconds = (float(p50) / 1000.0)
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
        "calculator_cost_usd": report["cost_estimate"].get("calculator_cost_usd"),
        "provider_measured_cost_usd": report["cost_estimate"].get("provider_measured_cost_usd"),
        "wall_time_seconds": wall,
        "entity_stage_seconds": (timing.get("entity_extraction_ms") or 0) / 1000.0,
        "fact_stage_seconds": (timing.get("fact_extraction_ms") or 0) / 1000.0,
        "request_elapsed_p50_ms": timing.get("request_elapsed_p50_ms"),
        "request_elapsed_p95_ms": timing.get("request_elapsed_p95_ms"),
        "request_elapsed_max_ms": timing.get("request_elapsed_max_ms"),
        "observed_providers": report["cost_estimate"].get("observed_providers") or [],
        "observed_models": report["cost_estimate"].get("observed_models") or [],
        "pipeline_effective_throughput": {
            "label": "PIPELINE EFFECTIVE THROUGHPUT — cumulative tokens or rows / wall second, not decode speed",
            "input_tokens_per_wall_second": _throughput(float(token.get("input_tokens") or 0), wall),
            "output_tokens_per_wall_second": _throughput(float(output), wall),
            "visible_output_tokens_per_wall_second": _throughput(
                float(visible) if visible is not None else None, wall
            ),
            "persisted_rows_per_wall_second": _throughput(float(persisted), wall),
        },
        "request_effective_rate": {
            "label": "REQUEST EFFECTIVE RATE — output tokens / request elapsed second using p50; not pipeline throughput",
            "output_tokens_per_request_p50_second": (
                (output / report["api_calls"]["total"] / request_seconds)
                if request_seconds and report["api_calls"]["total"]
                else None
            ),
        },
        "json_object_parse": timing.get("json_object_parse") or {},
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
    budget_ceiling_usd: float = BUDGET_CEILING_USD,
    arms: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    selected_arms = list(arms or stage4i2_arms())
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
        "arm_count": len(selected_arms),
        "run_order": [row["arm_id"] for row in selected_arms],
        "repetitions_per_arm": 1,
        "repository_sha": manifest.repository_sha,
        "source_count": 7,
        "batch_size": 5,
        "extraction_context_mode": "whole_document",
        "cache_policy": "isolated",
        "fact_contract": "payload_lean_v1",
        "transport": "responses_for_openai_chat_json_object_for_openrouter",
        "transport_by_provider": {
            "openai": "responses",
            "openrouter": "chat_completions",
        },
        "openrouter_response_format": {"type": "json_object"},
        "openrouter_schema_enforcement": "local_pydantic_after_json_object",
        "json_object_max_attempts": 5,
        "json_object_retry": "same_request_resend_on_invalid_json_or_schema; not semantic repair",
        "provider_json_schema": "unavailable_on_official_deepseek_openrouter_pin",
        "reasoning_contract": REASONING_CONTRACT,
        "budget_ceiling_usd": budget_ceiling_usd,
        "operator_budget_waived": OPERATOR_BUDGET_WAIVED,
        "production_policy_model": policy_model,
        "pins": pins,
        "will_execute": execute,
        "resume": False,
        "batch_api": False,
        "auto_escalation": False,
        "topology_frozen_request_count": 84,
        "unique_corpus_size_is_not_cumulative_api_traffic": True,
    }
    if out_dir.exists():
        raise ExperimentFailure("preflight", "output_root_already_exists")
    if not execute:
        return {"mode": "dry_run", "plan": plan, "api_calls": 0}

    env = dict(environ if environ is not None else os.environ)
    ensure_experiment_secrets(repo_root, env)
    if any(row["provider"] == "openai" for row in selected_arms) and not openai_key_present(env):
        raise ExperimentFailure("preflight", "openai_api_key_missing")
    if any(row["provider"] == "openrouter" for row in selected_arms) and not openrouter_key_present(env):
        raise ExperimentFailure("preflight", "openrouter_key_missing")

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
        "schema": "dmb_campaign_memory_stage4i2_screen_receipt_v1",
        "status": "running",
        "started_at": _now(),
        "repository_sha": manifest.repository_sha,
        "manifest_sha256": pins["manifest"],
        "pins": pins,
        "plan": plan,
        "arms": [],
        "census_path": str(out_dir / "corpus_census.json"),
        "seven_source_census_path": str(out_dir / "seven_source_census.json"),
        "total_cost_usd": 0.0,
        "failed_or_partial_attempts_included_in_spend": True,
    }
    receipt_path = out_dir / "receipt.json"
    _write(receipt_path, receipt)
    try:
        for arm in selected_arms:
            arm_id = arm["arm_id"]
            assert_state(f"{arm_id}_before")
            if float(receipt["total_cost_usd"]) >= budget_ceiling_usd:
                raise ExperimentFailure(arm_id, "budget_guard_would_exceed_ceiling")
            arm_root = out_dir / arm_id
            arm_root.mkdir()
            paths_file = arm_root / "source_paths.txt"
            paths_file.write_text(
                "".join(f"{item}\n" for item in ctx["source_locators"]), encoding="utf-8"
            )
            store = arm_root / "store"
            row = {
                "index": len(receipt["arms"]) + 1,
                "arm_id": arm_id,
                "model": arm["model"],
                "provider": arm["provider"],
                "service_tier": arm["service_tier"],
                "reasoning_effort": arm["reasoning_effort"],
                "status": "running",
                "started_at": _now(),
                "store_path": str(store),
            }
            receipt["arms"].append(row)
            _write(receipt_path, receipt)
            argv = arm_ingest_argv(
                repo_root=repo_root,
                store=store,
                corpus_root=ctx["corpus_root"],
                paths_file=paths_file,
                arm=arm,
            )
            leaks = argv_leaks_evaluator_authority(argv)
            if leaks:
                raise ExperimentFailure(arm_id, f"evaluator_authority_leak:{','.join(leaks)}")
            if "--resume" in argv or "--use-batch-api" in argv or "--auto-escalate" in argv:
                raise ExperimentFailure(arm_id, "forbidden_batch_flag")
            result = runner(argv, repo_root)
            (arm_root / "stdout.log").write_text(
                result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else ""),
                encoding="utf-8",
            )
            if result.returncode:
                raise ExperimentFailure(arm_id, f"batch_subprocess_exit_{result.returncode}")
            report = _read(store / "logs" / "batch_report.json")
            _validate_batch_report(report, 7)
            observed = _observed_models(store / "logs" / "model_calls.jsonl")
            if observed != (arm["model"], arm["model"]):
                raise ExperimentFailure(arm_id, "observed_model_mismatch")
            assert_state(f"{arm_id}_before_scoring")
            lab = lab_fn(
                store_path=store,
                surface="campaign_memory_development",
                out_dir=arm_root / "extraction_lab",
                run_id=arm_id,
                entity_anchor_path=ctx["entity_gold"],
                fact_anchor_path=ctx["fact_gold"],
                entity_model=arm["model"],
                fact_model=arm["model"],
                batch_size=5,
                pipeline_code_sha=manifest.repository_sha,
                corpus_source_root=ctx["corpus_root"],
            )
            entities = _read(store / "entities.json")
            facts = _read(store / "facts.json")
            counts = {"entities": len(entities), "facts": len(facts)}
            packet = build_quality_packet(entities=entities, facts=facts, arm=arm)
            packet_path = arm_root / "quality_packet.json"
            _write(packet_path, packet)
            telemetry = _arm_telemetry(report, counts)
            row.update(
                {
                    "status": "completed",
                    "completed_at": _now(),
                    "batch_report": str(store / "logs/batch_report.json"),
                    "lab_run_path": str(lab),
                    "quality_packet_path": str(packet_path),
                    "observed_models": observed,
                    "counts": counts,
                    "telemetry": telemetry,
                    "context_mode": "whole_document",
                }
            )
            receipt["total_cost_usd"] = round(
                float(receipt["total_cost_usd"]) + float(telemetry["cost_usd"] or 0), 4
            )
            _write(receipt_path, receipt)
            assert_state(f"{arm_id}_after")

        receipt.update(
            {
                "status": "completed",
                "completed_at": _now(),
                "duration_seconds": time.perf_counter() - started,
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
        print(f"Stage 4I.2 screen failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
