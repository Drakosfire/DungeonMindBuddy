"""OpenAI Batch API runner for planner live evals (shared cached instructions per corpus)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI

from evals.planner_slice.live_eval import (
    LiveEvalResult,
    evaluate_scenario_detail,
    resolve_planner_user_message,
)
from src.agent.planner import (
    PlanningModelStepRecord,
    PlanningTurnDetail,
    _MAX_TOOL_ROUNDS_PER_USER_TURN,
    _planner_tools_responses,
    make_tool_dispatcher,
)
from src.agent.planner_cache import load_or_build_planner_instructions
from src.ingestion.openai_batch_pipeline import (
    build_jsonl_request_line,
    extract_response_body_from_batch_line,
    run_batch_job,
)


def function_calls_from_response_body(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse ``function_call`` items from a serialized Responses ``body`` dict."""
    out: list[dict[str, Any]] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        raw = item.get("arguments")
        if isinstance(raw, str):
            try:
                args_obj = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                args_obj = {"_raw": raw}
        elif isinstance(raw, dict):
            args_obj = raw
        else:
            args_obj = {}
        out.append(
            {
                "name": str(item.get("name", "")),
                "arguments": args_obj,
                "_call_id": str(item.get("call_id", "")),
            }
        )
    return out


def output_text_from_response_body(body: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text":
                t = part.get("text")
                if isinstance(t, str):
                    parts.append(t)
    return "".join(parts).strip()


def _function_calls_for_dispatch(body: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        raw = item.get("arguments")
        args_str = raw if isinstance(raw, str) else json.dumps(raw or {})
        out.append(
            {
                "name": str(item.get("name", "")),
                "arguments_str": args_str or "{}",
                "call_id": str(item.get("call_id", "")),
            }
        )
    return out


def _planner_request_body(
    *,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
    user_message: str | None,
    previous_response_id: str | None,
    tool_inputs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "tools": tools,
        "tool_choice": "auto",
        "truncation": "auto",
    }
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
        body["input"] = tool_inputs or []
    else:
        body["input"] = [
            {"type": "message", "role": "user", "content": user_message or ""},
        ]
    return body


@dataclass
class _BatchEvalState:
    scenario: dict[str, Any]
    user_message: str
    completed: bool = False
    hit_tool_round_limit: bool = False
    last_response_id: str | None = None
    steps: list[PlanningModelStepRecord] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    response_count: int = 0
    final_text: str = ""
    violations: list[str] = field(default_factory=list)
    pending_tool_inputs: list[dict[str, Any]] | None = None


def run_batched_planner_eval(
    *,
    corpus_dir: Path,
    client: OpenAI,
    model_id: str,
    scenarios: list[dict[str, Any]],
    work_dir: Path,
    cache_root: Path | None = None,
    file_prefix: str = "planner_eval_batch",
    poll_interval_sec: float = 30.0,
) -> tuple[list[LiveEvalResult], dict[str, Any]]:
    """
    Run scenarios via OpenAI Batch (one job per model round).

    Reuses **cached** ``instructions`` (corpus manifest + system template) per corpus
    fingerprint via ``load_or_build_planner_instructions``. Tool execution is local.
    """
    corpus_path = corpus_dir.resolve()
    instructions, corpus_fp = load_or_build_planner_instructions(corpus_path, cache_root=cache_root)
    tools = _planner_tools_responses()
    dispatch = make_tool_dispatcher(corpus_path, client, model_id, statblock_stub=None)

    states: dict[str, _BatchEvalState] = {}
    for sc in scenarios:
        sid = str(sc.get("id", "unknown"))
        um, input_viol = resolve_planner_user_message(sc, corpus_path)
        states[sid] = _BatchEvalState(scenario=sc, user_message=um)
        states[sid].violations.extend(input_viol)

    meta_all: dict[str, Any] = {"corpus_fingerprint": corpus_fp, "rounds": []}
    round_idx = 0

    while True:
        lines: list[dict[str, Any]] = []
        for sid, st in states.items():
            if st.violations or st.completed or st.hit_tool_round_limit:
                continue
            if st.response_count >= _MAX_TOOL_ROUNDS_PER_USER_TURN:
                st.hit_tool_round_limit = True
                continue

            if st.last_response_id is None:
                body = _planner_request_body(
                    model=model_id,
                    instructions=instructions,
                    tools=tools,
                    user_message=st.user_message,
                    previous_response_id=None,
                    tool_inputs=None,
                )
            else:
                if not st.pending_tool_inputs:
                    st.completed = True
                    continue
                body = _planner_request_body(
                    model=model_id,
                    instructions=instructions,
                    tools=tools,
                    user_message=None,
                    previous_response_id=st.last_response_id,
                    tool_inputs=st.pending_tool_inputs,
                )
                st.pending_tool_inputs = None

            lines.append(build_jsonl_request_line(custom_id=sid, body=body))

        if not lines:
            break

        out_rows, err_rows, meta = run_batch_job(
            client,
            lines=lines,
            work_dir=work_dir,
            file_prefix=f"{file_prefix}_r{round_idx}",
            poll_interval_sec=poll_interval_sec,
            print_status=True,
        )
        meta_all["rounds"].append({"meta": meta, "errors": len(err_rows), "lines": len(lines)})
        round_idx += 1

        for row in err_rows:
            cid = str(row.get("custom_id", "") or "")
            if cid in states:
                states[cid].violations.append(f"batch_error_row: {row!r}")

        for row in out_rows:
            cid = str(row.get("custom_id", "") or "")
            st = states.get(cid)
            if st is None:
                continue
            body = extract_response_body_from_batch_line(row)
            if body is None:
                st.violations.append(f"batch_line_no_body: {row!r}")
                continue

            st.response_count += 1
            rid = str(body.get("id", "") or "")
            fc = function_calls_from_response_body(body)
            assistant_text = output_text_from_response_body(body)
            st.steps.append(
                PlanningModelStepRecord(
                    step_index=len(st.steps),
                    response_id=rid,
                    function_calls=list(fc),
                    assistant_text=assistant_text,
                )
            )
            st.last_response_id = rid or st.last_response_id

            raw_calls = _function_calls_for_dispatch(body)
            if not raw_calls:
                st.final_text = assistant_text
                st.completed = True
                continue

            if st.response_count >= _MAX_TOOL_ROUNDS_PER_USER_TURN:
                st.hit_tool_round_limit = True
                continue

            tool_inputs: list[dict[str, Any]] = []
            for call in raw_calls:
                name = call["name"]
                raw_args = call["arguments_str"]
                try:
                    args_obj = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args_obj = {"_raw": raw_args}
                out = dispatch(name, raw_args)
                st.tool_trace.append(
                    {
                        "tool": name,
                        "arguments": args_obj,
                        "output_chars": len(out),
                        "output_excerpt": out[:800],
                    }
                )
                tool_inputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": out,
                    }
                )
            st.pending_tool_inputs = tool_inputs

    results: list[LiveEvalResult] = []
    for sid, st in states.items():
        if st.violations:
            results.append(
                LiveEvalResult(
                    scenario_id=sid,
                    passed=False,
                    violations={"batch": st.violations},
                )
            )
            continue
        detail = PlanningTurnDetail(
            final_text=st.final_text,
            last_response_id=st.last_response_id or "",
            tool_trace=st.tool_trace,
            steps=st.steps,
            hit_tool_round_limit=st.hit_tool_round_limit,
        )
        results.append(evaluate_scenario_detail(st.scenario, detail))
    return results, meta_all
