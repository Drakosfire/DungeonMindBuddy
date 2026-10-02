#!/usr/bin/env python3
"""Measure host phase durations for cold and reused synthetic Hermes turns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.live_control_server.services.agent_graph_policy import (  # noqa: E402
    resolve_agent_graph_openai_inference,
)
from apps.live_control_server.services.agent_turn_trace import (  # noqa: E402
    estimate_model_call_cost,
)
from apps.live_control_server.services.hermes_graph_agent import (  # noqa: E402
    _build_ephemeral_system_prompt,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (  # noqa: E402
    HermesGraphAgentTurnRequest,
)
from apps.live_control_server.services.hermes_graph_agent_host import (  # noqa: E402
    HermesGraphAgentHost,
)
from graph_memory.hermes_graph_plugin import (  # noqa: E402
    default_conversation_only_capability_policy,
)

HERE = Path(__file__).resolve().parent
SAMPLE_COUNT = 5


def _usage_summary(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    return usage.model_dump(mode="json")


def _estimate_cost(model: str, usage: dict[str, Any] | None) -> dict[str, Any]:
    if not usage:
        return {"status": "unavailable", "usd": None}
    normalized = {
        "status": "reported",
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }
    details = usage.get("input_tokens_details") or {}
    if details.get("cached_tokens") is not None:
        normalized["cached_input_tokens"] = details["cached_tokens"]
    return estimate_model_call_cost(model=model, usage=normalized)


def _hard_gates(answer: str | None, status: str) -> dict[str, Any]:
    text = answer or ""
    folded = text.casefold()
    words = text.split()
    uncertainty_markers = (
        "unknown",
        "unconfirmed",
        "unverified",
        "not confirmed",
        "nobody has followed",
        "remains unclear",
        "remains unknown",
    )
    gates = {
        "turn_status_ok": status == "ok",
        "nonempty_answer": bool(text.strip()),
        "at_most_100_words": len(words) <= 100,
        "mentions_actionable_bridge_pressure": "bridge" in folded and "dusk" in folded,
        "mentions_nera_missing": "nera" in folded
        and any(marker in folded for marker in ("missing", "disappeared", "vanished")),
        "signals_unresolved_fact": any(
            marker in folded for marker in uncertainty_markers
        ),
    }
    gates["all_pass"] = all(gates.values())
    return {"word_count": len(words), "gates": gates}


def _model_call_summary(call: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": call.get("status"),
        "provider": call.get("provider"),
        "requested_model": call.get("requested_model"),
        "response_model": call.get("response_model"),
        "duration_ms": call.get("duration_ms"),
        "request_summary": call.get("request_summary"),
        "usage": call.get("usage"),
        "cost": call.get("cost"),
    }


def _write_artifact(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=SAMPLE_COUNT)
    args = parser.parse_args()
    if args.samples < 5:
        parser.error("at least five host turns are required (one cold plus four warm)")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required; its value is never emitted")

    scenario = json.loads((HERE / "scenario.json").read_text(encoding="utf-8"))
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    policy = default_conversation_only_capability_policy()
    question = (
        "Evidence packet (fully synthetic):\n"
        + "\n".join("- " + line for line in scenario["evidence"])
        + "\n\nRequest: "
        + scenario["question"]
    )
    template = HermesGraphAgentTurnRequest(
        question=question,
        world_id=None,
        campaign_id=None,
        scope_mode=None,
        capability_policy=policy,
    )
    system = _build_ephemeral_system_prompt(
        policy, template, retrieval_session_packet=None
    )
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=base_url)
    host = HermesGraphAgentHost()
    artifact_path = args.output or HERE / "artifacts" / (
        "host-phases-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    record: dict[str, Any] = {
        "schema": "hermes_tuning_host_phases_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "fully synthetic evidence; no private corpus or Graph reads",
        "scenario_id": scenario["scenario_id"],
        "provider": provider,
        "model": model,
        "api_base_url": base_url,
        "sample_count_requested": args.samples,
        "parent_pid": os.getpid(),
        "input_sha256": hashlib.sha256((system + "\n" + question).encode()).hexdigest(),
        "effective_question": question,
        "system_instruction": system,
        "answer_gate_rule": {
            "version": "synthetic-co-gm-screen-v2",
            "checks": [
                "turn status is ok and answer is nonempty",
                "at most 100 whitespace-delimited words",
                "mentions the bridge and dusk",
                "mentions Nera with missing, disappeared, or vanished",
                "contains an explicit unresolved-fact marker",
            ],
            "post_run_gate_fields_recomputed": False,
        },
        "host_start_ready_ms": None,
        "worker_start_pid": None,
        "host_start_method": host.start_method,
        "samples": [],
        "limits": [
            "Five turns are descriptive evidence, not a stable latency distribution or production speedup.",
            "Host-owned serialization, worker acquisition/readiness, queue/acceptance, result wait, and result decoding are timed. Time inside worker execution remains residual after observed model-call duration.",
            "Responses are non-streaming through this host API; first useful visible text and TTFT are unknown.",
            "The direct route is a same-process Responses API control; it does not measure host startup or IPC.",
            "The answer checks are deterministic heuristics for status, length, key facts, and an uncertainty marker; they do not prove full grounding.",
        ],
    }
    previous_worker_pid: int | None = None

    def save_and_report_pair(sample: dict[str, Any]) -> None:
        record["samples"].append(sample)
        _write_artifact(artifact_path, record)
        if len(record["samples"]) == 2:
            cold, warm = record["samples"]
            print(
                "FIRST_COLD_WARM_PAIR="
                + json.dumps(
                    {
                        "output": str(artifact_path),
                        "model": model,
                        "provider": provider,
                        "host_start_ready_ms": record["host_start_ready_ms"],
                        "cold": {
                            "direct_wall_ms": cold["direct_control"]["wall_ms"],
                            "host_wall_ms": cold["host"]["wall_ms"],
                            "model_call_ms": cold["host"]["sum_observed_model_call_ms"],
                            "residual_ms": cold["host"]["unallocated_residual_ms"],
                            "phases": cold["host"]["phase_spans"],
                            "worker_pid": cold["host"]["worker_pid_after"],
                            "hard_gates_pass": cold["host"]["hard_gate_check"]["gates"][
                                "all_pass"
                            ],
                        },
                        "warm": {
                            "direct_wall_ms": warm["direct_control"]["wall_ms"],
                            "host_wall_ms": warm["host"]["wall_ms"],
                            "model_call_ms": warm["host"]["sum_observed_model_call_ms"],
                            "residual_ms": warm["host"]["unallocated_residual_ms"],
                            "phases": warm["host"]["phase_spans"],
                            "worker_pid": warm["host"]["worker_pid_after"],
                            "worker_reused": warm["host"][
                                "worker_reused_from_previous_sample"
                            ],
                            "hard_gates_pass": warm["host"]["hard_gate_check"]["gates"][
                                "all_pass"
                            ],
                        },
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        elif len(record["samples"]) > 2:
            print(
                "SAMPLE_COMPLETE="
                + json.dumps(
                    {
                        "index": len(record["samples"]),
                        "host_wall_ms": sample["host"]["wall_ms"],
                        "residual_ms": sample["host"]["unallocated_residual_ms"],
                        "worker_pid": sample["host"]["worker_pid_after"],
                    }
                ),
                flush=True,
            )

    try:
        for index in range(args.samples):
            sample_id = f"sample-{index + 1}"
            direct_start = time.perf_counter()
            direct_response = client.responses.create(
                model=model,
                instructions=system,
                input=question,
            )
            direct_wall_ms = (time.perf_counter() - direct_start) * 1000
            direct_usage = _usage_summary(direct_response.usage)
            direct_answer = direct_response.output_text
            direct_sample = {
                "status": "ok",
                "wall_ms": round(direct_wall_ms, 1),
                "response_id": direct_response.id,
                "usage": direct_usage,
                "cost": _estimate_cost(model, direct_usage),
                "answer": direct_answer,
                "hard_gate_check": _hard_gates(direct_answer, "ok"),
            }

            host_start_pid = host.worker_pid
            request = HermesGraphAgentTurnRequest(
                question=question,
                world_id=None,
                campaign_id=None,
                scope_mode=None,
                session_id=f"synthetic-host-latency-{uuid.uuid4()}",
                root=Path("/tmp"),
                capability_policy=policy,
            )
            host_start = time.perf_counter()
            host_phases: list[dict[str, Any]] = []
            result = host.execute(request, on_host_phase=host_phases.append)
            host_wall_ms = (time.perf_counter() - host_start) * 1000
            host_worker_pid = host.worker_pid
            if index == 0:
                record["worker_start_pid"] = host_worker_pid
            model_calls = [
                _model_call_summary(dict(call)) for call in result.model_calls
            ]
            observed_model_ms = [
                float(call["duration_ms"])
                for call in model_calls
                if isinstance(call.get("duration_ms"), (int, float))
            ]
            summed_model_ms = sum(observed_model_ms) if observed_model_ms else None
            host_sample = {
                "status": result.status,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "wall_ms": round(host_wall_ms, 1),
                "phase_spans": host_phases[:24],
                "model_calls": model_calls,
                "model_call_count": len(model_calls),
                "sum_observed_model_call_ms": (
                    round(summed_model_ms, 1) if summed_model_ms is not None else None
                ),
                "unallocated_residual_ms": (
                    round(host_wall_ms - summed_model_ms, 1)
                    if summed_model_ms is not None
                    else None
                ),
                "tool_event_count": len(result.tool_events),
                "tool_call_count": sum(
                    1 for event in result.tool_events if event.state == "completion"
                ),
                "process_isolation": result.process_isolation,
                "worker_pid_before": host_start_pid,
                "worker_pid_after": host_worker_pid,
                "worker_pid_matches_cold_worker": host_worker_pid
                == record["worker_start_pid"],
                "worker_reused_from_previous_sample": index > 0
                and host_worker_pid == previous_worker_pid,
                "answer": result.final_response,
                "hard_gate_check": _hard_gates(result.final_response, result.status),
            }
            save_and_report_pair(
                {
                    "sample_id": sample_id,
                    "phase": "cold_worker_turn"
                    if index == 0
                    else "warm_reused_worker_turn",
                    "direct_control": direct_sample,
                    "host": host_sample,
                }
            )
            previous_worker_pid = host_worker_pid
    except Exception as exc:
        record["failure"] = {
            "exception_type": type(exc).__name__,
            "message": re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", str(exc))[:1000],
            "completed_samples": len(record["samples"]),
        }
        _write_artifact(artifact_path, record)
        raise
    finally:
        shutdown_start = time.perf_counter()
        record["host_shutdown"] = {
            "confirmed": host.shutdown(),
            "elapsed_ms": round((time.perf_counter() - shutdown_start) * 1000, 1),
        }
        _write_artifact(artifact_path, record)

    print(
        "RUN_COMPLETE="
        + json.dumps(
            {
                "output": str(artifact_path),
                "sample_count": len(record["samples"]),
                "host_start_ready_ms": record["host_start_ready_ms"],
                "worker_start_pid": record["worker_start_pid"],
                "host_shutdown": record["host_shutdown"],
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
