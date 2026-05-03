"""Harness-only LLM synthesis over retrieved breadcrumb hit context (not planner-facing)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_SYSTEM = (
    "You are assisting a tabletop RPG GM. Answer the question using ONLY the evidence in the "
    "retrieved excerpts and corpus route lines below. If the excerpts do not support a confident "
    "answer, say what is missing. Stay concise (roughly 3–8 sentences). Do not invent specifics "
    "that are not grounded in the excerpts."
)


def _policy_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [here.parents[2] / "MODEL_POLICY.json", here.parents[3] / "MODEL_POLICY.json"]


def resolve_breadcrumb_query_llm_model() -> str:
    """Model id: env ``DMB_BREADCRUMB_QUERY_LLM_MODEL``, else ``ruleslawyer_response_synthesis`` role."""
    raw = os.environ.get("DMB_BREADCRUMB_QUERY_LLM_MODEL", "").strip()
    if raw:
        return raw
    for p in _policy_paths():
        if not p.is_file():
            continue
        policy = json.loads(p.read_text(encoding="utf-8"))
        actions = policy.get("actions") or {}
        models = policy.get("models") or {}
        role = actions.get("ruleslawyer_response_synthesis")
        if isinstance(role, str) and role in models:
            mid = models.get(role)
            if isinstance(mid, str) and mid.strip():
                return mid.strip()
    return "gpt-5.4-mini"


def _usage_tokens(usage: Any) -> tuple[int, int, int]:
    if usage is None:
        return 0, 0, 0
    inp = int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0)
    out = int(getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0)
    details = getattr(usage, "prompt_tokens_details", None) or getattr(usage, "input_tokens_details", None)
    cached = 0
    if details is not None:
        cached = int(getattr(details, "cached_tokens", None) or 0)
    return inp, out, cached


def synthesize_answer_from_hit_context(
    *,
    question: str,
    hit_context: str,
    model: str,
) -> tuple[str, float, dict[str, int]]:
    """Return (assistant_plaintext, estimated_usd, token_usage)."""
    from openai import OpenAI

    from src.agent.planner_pricing import usage_cost_usd

    client = OpenAI()
    user_block = (
        f"Question:\n{question.strip()}\n\n"
        f"### Retrieved excerpts and routes (only source you may use)\n"
        f"{hit_context.strip()}\n"
    )
    resp = client.chat.completions.create(
        model=model.strip(),
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_block},
        ],
        max_completion_tokens=700,
    )
    text = (resp.choices[0].message.content or "").strip()
    inp_t, out_t, cached_t = _usage_tokens(resp.usage)
    pricing = usage_cost_usd(
        model_id=model.strip(),
        input_tokens=inp_t,
        output_tokens=out_t,
        cached_tokens=cached_t,
    )
    cost_usd = float(pricing.get("total_usd") or 0.0)
    return text, cost_usd, {
        "input_tokens": inp_t,
        "output_tokens": out_t,
        "cached_input_tokens": cached_t,
        "total_tokens": inp_t + out_t,
    }
