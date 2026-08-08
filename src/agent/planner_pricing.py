"""Approximate OpenAI USD cost from Responses usage (sync with ``tools/batch_ingest_corpus.py`` tiers)."""

from __future__ import annotations

from typing import Any

# Per-1M-token USD — keep aligned with ``tools/batch_ingest_corpus._PRICING_PER_1M`` when pricing changes.
# Short-context list rates. Longer prefixes must win over shorter ones (e.g. gpt-5.6-luna
# must not fall through to gpt-5).
_PRICING_PER_1M: dict[str, dict[str, float]] = {
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-sol": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5.4-pro": {"input": 30.00, "cached_input": 30.00, "output": 180.00},
    "gpt-5.4": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
    "gpt-5.3-codex": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.3-chat": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.2": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.1": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-4.1-nano": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "cached_input": 0.50, "output": 8.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "o4-mini": {"input": 1.10, "cached_input": 0.275, "output": 4.40},
    "o3-mini": {"input": 1.10, "cached_input": 0.55, "output": 4.40},
    "o3": {"input": 2.00, "cached_input": 0.50, "output": 8.00},
}


def pricing_rates_for_model(model_name: str) -> dict[str, float]:
    """Longest-prefix match on ``model_name`` (lowercased)."""
    if not model_name or not str(model_name).strip():
        return {"input": 0.0, "cached_input": 0.0, "output": 0.0}
    mn = str(model_name).lower().strip()
    best: dict[str, float] | None = None
    best_len = 0
    for prefix, rates in _PRICING_PER_1M.items():
        if mn.startswith(prefix.lower()) and len(prefix) > best_len:
            best = dict(rates)
            best_len = len(prefix)
    return best if best is not None else {"input": 0.0, "cached_input": 0.0, "output": 0.0}


def usage_cost_usd(
    *,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
) -> dict[str, Any]:
    """
    Bill **uncached** input at list input rate and **cached** input at cached_input rate.

    OpenAI reports ``input_tokens`` including cached portion; ``cached_tokens`` is the
    cache hit subset when present.
    """
    rates = pricing_rates_for_model(model_id)
    inp = int(input_tokens)
    out_t = int(output_tokens)
    cached = int(cached_tokens)
    uncached = max(0, inp - cached)
    c_in = uncached / 1_000_000.0 * rates["input"]
    c_cached = cached / 1_000_000.0 * rates["cached_input"]
    c_out = out_t / 1_000_000.0 * rates["output"]
    total = c_in + c_cached + c_out
    matched = rates["input"] > 0.0 or rates["cached_input"] > 0.0 or rates["output"] > 0.0
    return {
        "total_usd": total,
        "uncached_input_tokens": uncached,
        "cached_tokens": cached,
        "output_tokens": out_t,
        "input_tokens_reported": inp,
        "input_usd": c_in,
        "cached_input_usd": c_cached,
        "output_usd": c_out,
        "rates_per_1m_usd": rates,
        "pricing_table_matched": matched,
    }
