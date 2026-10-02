#!/usr/bin/env python3
"""Same-model direct API versus Buddy's embedded Hermes on synthetic evidence only."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
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
from apps.live_control_server.services.agent_turn_trace import estimate_model_call_cost  # noqa: E402
from apps.live_control_server.services.hermes_graph_agent import (  # noqa: E402
    _build_ephemeral_system_prompt,
    run_hermes_graph_agent_turn,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (  # noqa: E402
    HermesGraphAgentTurnRequest,
)
from graph_memory.hermes_graph_plugin import default_conversation_only_capability_policy  # noqa: E402

HERE = Path(__file__).resolve().parent


def one_run(
    client: OpenAI, model: str, system: str, question: str, variant: str
) -> dict[str, Any]:
    direct_start = time.perf_counter()
    response = client.responses.create(model=model, instructions=system, input=question)
    direct_ms = (time.perf_counter() - direct_start) * 1000
    direct_usage = response.usage.model_dump(mode="json") if response.usage else None
    direct_normalized = (
        {
            "status": "reported",
            "input_tokens": direct_usage.get("input_tokens"),
            "output_tokens": direct_usage.get("output_tokens"),
            "total_tokens": direct_usage.get("total_tokens"),
        }
        if direct_usage
        else {}
    )
    if (
        direct_usage
        and direct_usage.get("input_tokens_details", {}).get("cached_tokens")
        is not None
    ):
        direct_normalized["cached_input_tokens"] = direct_usage["input_tokens_details"][
            "cached_tokens"
        ]
    direct_cost = estimate_model_call_cost(model=model, usage=direct_normalized)
    request = HermesGraphAgentTurnRequest(
        question=question,
        world_id=None,
        campaign_id=None,
        scope_mode=None,
        session_id=f"synthetic-{variant}-{uuid.uuid4()}",
        root=Path("/tmp"),
        capability_policy=default_conversation_only_capability_policy(),
    )
    model_calls = []
    hermes_start = time.perf_counter()
    result = run_hermes_graph_agent_turn(
        request, on_model_call=lambda call: model_calls.append(dict(call))
    )
    hermes_ms = (time.perf_counter() - hermes_start) * 1000
    return {
        "variant": variant,
        "direct": {
            "elapsed_ms": round(direct_ms, 1),
            "response_id": response.id,
            "usage": direct_usage,
            "estimated_cost": direct_cost,
            "answer": response.output_text,
        },
        "hermes": {
            "status": result.status,
            "elapsed_ms": round(hermes_ms, 1),
            "error_code": result.error_code,
            "error_message": result.error_message,
            "model_calls": model_calls,
            "tool_event_count": len(result.tool_events),
            "answer": result.final_response,
        },
        "timing_limits": {
            "direct_ttft_ms": None,
            "hermes_ttft_ms": None,
            "hermes_initialization_ms": None,
            "hermes_plugin_discovery_ms": None,
            "hermes_projection_ms": None,
            "note": "non-streaming calls; adapter does not expose these component spans",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("control", "voice"), default="control")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required; its value is never emitted")
    scenario = json.loads((HERE / "scenario.json").read_text(encoding="utf-8"))
    policy = default_conversation_only_capability_policy()
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    question = (
        "Evidence packet (fully synthetic):\n"
        + "\n".join("- " + line for line in scenario["evidence"])
        + "\n\nRequest: "
        + scenario["question"]
    )
    if args.variant == "voice":
        question += "\n" + scenario["voice_variation"]
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
    record = {
        "schema": "hermes_tuning_synthetic_pair_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "fully synthetic; no private or user corpus data",
        "scenario_id": scenario["scenario_id"],
        "variant": args.variant,
        "provider": provider,
        "model": model,
        "api_base_url": base_url,
        "input_sha256": hashlib.sha256((system + "\n" + question).encode()).hexdigest(),
        "effective_question": question,
        "system_instruction": system,
        "pair": one_run(client, model, system, question, args.variant),
    }
    output = args.output or HERE / "artifacts" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + args.variant
        + ".json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "model": model,
                "provider": provider,
                "variant": args.variant,
                "input_sha256": record["input_sha256"],
                "direct_elapsed_ms": record["pair"]["direct"]["elapsed_ms"],
                "hermes_elapsed_ms": record["pair"]["hermes"]["elapsed_ms"],
                "hermes_model_call_count": len(record["pair"]["hermes"]["model_calls"]),
                "hermes_tool_event_count": record["pair"]["hermes"]["tool_event_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
