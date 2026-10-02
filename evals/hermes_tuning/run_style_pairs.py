#!/usr/bin/env python3
"""Run one reproducible, synthetic matched cohort for Hermes co-GM prose."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
CASE_PATH = HERE / "style_cases.json"
STYLE_PATH = HERE / "scenario.json"
MODEL_EXPECTED = "gpt-6-luna"
PROVIDER_EXPECTED = "openai-api"
UNCERTAINTY = (
    "unknown",
    "unconfirmed",
    "unverified",
    "unclear",
    "not known",
    "not established",
    "not yet",
)
HEAD_RE = re.compile(r"^\s{0,3}(?:#{1,6}\s|[-*+]\s|\d+[.)]\s)")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cases() -> tuple[list[dict[str, Any]], str]:
    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    voice = json.loads(STYLE_PATH.read_text(encoding="utf-8"))["voice_variation"]
    cases = payload.get("cases")
    if (
        payload.get("schema") != "hermes_synthetic_style_cases_v1"
        or not isinstance(cases, list)
        or len(cases) != 12
    ):
        raise ValueError("expected exactly 12 cases in hermes_synthetic_style_cases_v1")
    ids = [c.get("case_id") for c in cases]
    if len(set(ids)) != 12:
        raise ValueError("case IDs must be unique")
    for case in cases:
        if not all(
            isinstance(case.get(k), str) and case[k].strip()
            for k in ("case_id", "question", "actionable_pressure")
        ):
            raise ValueError("case missing required nonempty string")
        if not isinstance(case.get("evidence"), list) or not case["evidence"]:
            raise ValueError("case evidence must be a nonempty list")
        if not isinstance(case.get("supported_facts"), list) or not case.get(
            "known_unknowns"
        ):
            raise ValueError("case must include supported_facts and known_unknowns")
    if not voice or "calm, practical co-GM" not in voice:
        raise ValueError("voice variation must be the fixed scenario sentence")
    return cases, voice


def build_prompts(case: dict[str, Any], voice: str) -> tuple[str, str]:
    base = (
        "Evidence packet (fully synthetic):\n"
        + "\n".join("- " + x for x in case["evidence"])
        + "\n\nRequest: "
        + case["question"]
    )
    challenger = base + "\n" + voice
    if challenger != base + "\n" + voice or not challenger.startswith(base):
        raise AssertionError("arm parity failed")
    return base, challenger


def hard_gates(
    answer: str | None, status: str, tool_count: int, call_count: int
) -> dict[str, Any]:
    text = answer or ""
    lines = text.splitlines()
    gates = {
        "turn_status_ok": status == "ok",
        "nonempty_answer": bool(text.strip()),
        "at_most_100_words": len(text.split()) <= 100,
        "no_heading_or_bullets": not any(HEAD_RE.match(line) for line in lines),
        "explicit_uncertainty": any(
            marker in text.casefold() for marker in UNCERTAINTY
        ),
        "exactly_one_model_call": call_count == 1,
        "no_tool_events": tool_count == 0,
    }
    gates["all_pass"] = all(gates.values())
    return {"word_count": len(text.split()), "gates": gates}


def _safe_call(call: dict[str, Any]) -> dict[str, Any]:
    usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
    allowed_usage = {
        k: usage.get(k)
        for k in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_input_tokens",
        )
        if usage.get(k) is not None
    }
    cost = call.get("cost") if isinstance(call.get("cost"), dict) else {}
    allowed_cost = {
        k: cost.get(k)
        for k in ("status", "usd", "currency", "pricing_table_matched")
        if k in cost
    }
    return {
        "status": call.get("status"),
        "provider": call.get("provider"),
        "requested_model": call.get("requested_model"),
        "response_model": call.get("response_model"),
        "duration_ms": call.get("duration_ms"),
        "usage": allowed_usage,
        "cost": allowed_cost,
    }


def _run_arm(
    question: str, policy: Any, model: str, case_id: str, arm: str
) -> dict[str, Any]:
    request = HermesGraphAgentTurnRequest(
        question=question,
        world_id=None,
        campaign_id=None,
        scope_mode=None,
        session_id=f"style-{case_id}-{arm}-{uuid.uuid4()}",
        root=Path("/tmp"),
        capability_policy=policy,
    )
    system = _build_ephemeral_system_prompt(
        policy, request, retrieval_session_packet=None
    )
    start = time.perf_counter()
    result = run_hermes_graph_agent_turn(request)
    wall = round((time.perf_counter() - start) * 1000, 1)
    calls = [_safe_call(dict(c)) for c in result.model_calls]
    estimated = (
        estimate_model_call_cost(
            model=model, usage={"status": "reported", **(calls[0].get("usage") or {})}
        )
        if calls
        else {"status": "unavailable", "usd": None}
    )
    answer = result.final_response
    return {
        "arm": arm,
        "status": result.status,
        "error_code": result.error_code,
        "answer": answer,
        "wall_ms": wall,
        "system_sha256": sha(system),
        "user_sha256": sha(question),
        "model_calls": calls,
        "estimated_cost": estimated,
        "tool_event_count": len(result.tool_events),
        "hard_gates": hard_gates(
            answer, str(result.status), len(result.tool_events), len(calls)
        ),
    }


def _new_record(seed: int, provider: str, model: str, base_url: str) -> dict[str, Any]:
    return {
        "schema": "hermes_synthetic_style_pairs_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cohort_id": str(uuid.uuid4()),
        "source": "fully synthetic; not derived from private or user corpus material",
        "provider": provider,
        "model": model,
        "api_base_url": base_url,
        "randomization_seed": seed,
        "arm_order": [],
        "cases": [],
        "limitations": [
            "Twelve pairs are exploratory and do not establish general or production quality improvement.",
            "Hard gates are deterministic screens, not complete factual-grounding proofs; evidence-keyed scoring remains a blinded human task.",
            "Non-streaming responses leave TTFT unknown.",
        ],
    }


def blinded_packet(
    record: dict[str, Any], cases: list[dict[str, Any]], blind_seed: int
) -> dict[str, Any]:
    rng = random.Random(blind_seed)
    case_map = {c["case_id"]: c for c in cases}
    items = []
    for entry in record["cases"]:
        case = case_map[entry["case_id"]]
        outputs = [entry["arms"]["control"]["answer"], entry["arms"]["voice"]["answer"]]
        rng.shuffle(outputs)
        items.append(
            {
                "case_id": entry["case_id"],
                "evidence": case["evidence"],
                "question": case["question"],
                "supported_facts": case["supported_facts"],
                "known_unknowns": case["known_unknowns"],
                "actionable_pressure": case["actionable_pressure"],
                "answer_A": outputs[0],
                "answer_B": outputs[1],
                "human_hard_gate_review": "pending",
                "scores": "pending blind reviewer",
            }
        )
    rng.shuffle(items)
    return {
        "schema": "hermes_blinded_style_review_v1",
        "source": "fully synthetic",
        "instructions": "Score each answer independently for grounding, uncertainty preservation, task fit, naturalness, clarity, and concision (anchored 1-5); then record A/B/tie preference. Do not infer experimental condition.",
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="raw cohort JSON; keep outside the repository until final",
    )
    parser.add_argument("--stop-after", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--blind-output", type=Path)
    parser.add_argument("--blind-seed", type=int, default=91731)
    args = parser.parse_args()
    if args.stop_after < 1 or args.stop_after > 12:
        parser.error("--stop-after must be 1..12")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required; its value is never emitted")
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    if (provider, model) != (PROVIDER_EXPECTED, MODEL_EXPECTED):
        parser.error(
            f"policy resolved {provider}/{model}; this cohort requires openai-api/gpt-6-luna"
        )
    cases, voice = load_cases()
    if args.resume:
        record = json.loads(args.output.read_text(encoding="utf-8"))
        if (
            record.get("schema") != "hermes_synthetic_style_pairs_v1"
            or record.get("randomization_seed") != args.seed
            or record.get("provider") != provider
            or record.get("model") != model
        ):
            parser.error(
                "resume metadata mismatch; refusing to create a different cohort"
            )
    else:
        record = _new_record(args.seed, provider, model, base_url)
    if len(record["cases"]) > args.stop_after:
        parser.error("cohort already exceeds --stop-after")
    rng = random.Random(args.seed)
    order = record["arm_order"]
    if not order:
        order.extend(rng.choice(["control_first", "voice_first"]) for _ in cases)
    elif len(order) != len(cases):
        parser.error("resume arm-order list is invalid")
    policy = default_conversation_only_capability_policy()
    done = {c["case_id"] for c in record["cases"]}
    for index, case in enumerate(cases):
        if case["case_id"] in done or len(record["cases"]) >= args.stop_after:
            continue
        control_q, voice_q = build_prompts(case, voice)
        control_request = HermesGraphAgentTurnRequest(
            question=control_q,
            world_id=None,
            campaign_id=None,
            scope_mode=None,
            capability_policy=policy,
        )
        voice_request = HermesGraphAgentTurnRequest(
            question=voice_q,
            world_id=None,
            campaign_id=None,
            scope_mode=None,
            capability_policy=policy,
        )
        sys_a = _build_ephemeral_system_prompt(
            policy, control_request, retrieval_session_packet=None
        )
        sys_b = _build_ephemeral_system_prompt(
            policy, voice_request, retrieval_session_packet=None
        )
        if sys_a != sys_b or voice_q != control_q + "\n" + voice:
            raise RuntimeError("prompt/system parity validation failed")
        arms: dict[str, Any] = {}
        sequence = (
            ["control", "voice"]
            if order[index] == "control_first"
            else ["voice", "control"]
        )
        for arm in sequence:
            arms[arm] = _run_arm(
                control_q if arm == "control" else voice_q,
                policy,
                model,
                case["case_id"],
                arm,
            )
        record["cases"].append(
            {
                "case_id": case["case_id"],
                "evidence": case["evidence"],
                "question": case["question"],
                "supported_facts": case["supported_facts"],
                "known_unknowns": case["known_unknowns"],
                "actionable_pressure": case["actionable_pressure"],
                "base_user_sha256": sha(control_q),
                "voice_user_sha256": sha(voice_q),
                "system_sha256": sha(sys_a),
                "arm_order": sequence,
                "arms": arms,
            }
        )
        record["cases"].sort(
            key=lambda c: next(
                i for i, item in enumerate(cases) if item["case_id"] == c["case_id"]
            )
        )
        # Keep the full randomized sequence, including cases not run yet.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        cost = sum(
            float((arms[a].get("estimated_cost") or {}).get("usd") or 0) for a in arms
        )
        print(
            json.dumps(
                {
                    "pair": len(record["cases"]),
                    "case_id": case["case_id"],
                    "arm_order": sequence,
                    "control_pass": arms["control"]["hard_gates"]["gates"]["all_pass"],
                    "voice_pass": arms["voice"]["hard_gates"]["gates"]["all_pass"],
                    "pair_estimated_cost_usd": round(cost, 7),
                    "pair_wall_ms": {a: arms[a]["wall_ms"] for a in arms},
                    "raw_output": str(args.output),
                }
            ),
            flush=True,
        )
    if len(record["cases"]) == 12 and args.blind_output:
        args.blind_output.parent.mkdir(parents=True, exist_ok=True)
        args.blind_output.write_text(
            json.dumps(
                blinded_packet(record, cases, args.blind_seed),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        record["blind_packet_sha256"] = sha(
            args.blind_output.read_text(encoding="utf-8")
        )
        record["blind_seed"] = args.blind_seed
        args.output.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps({"blind_packet": str(args.blind_output), "pairs": 12}),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
