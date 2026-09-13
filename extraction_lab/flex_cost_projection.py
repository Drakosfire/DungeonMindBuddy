from __future__ import annotations

from typing import Any


PRICING_AS_OF = "2026-09-12"
PRICING_SOURCE = "OpenAI pricing page supplied with Stage 4H"
FLEX_SHORT_CONTEXT_PER_MILLION_USD = {
    "gpt-5.6-luna": {"input": 0.10, "cached_input": 0.01, "output": 0.60},
    "gpt-5.6-terra": {"input": 1.00, "cached_input": 0.10, "output": 6.00},
    "gpt-5.6-sol": {"input": 2.00, "cached_input": 0.20, "output": 10.00},
    "gpt-5.4": {"input": 1.25, "cached_input": 0.13, "output": 7.50},
    "gpt-5.4-mini": {"input": 0.375, "cached_input": 0.0375, "output": 2.25},
    "gpt-5.4-nano": {"input": 0.10, "cached_input": 0.01, "output": 0.625},
}


def project_flex_costs(
    *,
    input_tokens: float,
    cached_tokens: float,
    output_tokens: float,
    measured_source_count: int,
    target_source_count: int,
) -> dict[str, Any]:
    scale = target_source_count / measured_source_count
    uncached = max(0.0, input_tokens - cached_tokens)
    projections = {}
    for model, rates in FLEX_SHORT_CONTEXT_PER_MILLION_USD.items():
        measured = (
            uncached * rates["input"]
            + cached_tokens * rates["cached_input"]
            + output_tokens * rates["output"]
        ) / 1_000_000
        projections[model] = {
            "measured_workload_usd": measured,
            "target_linear_projection_usd": measured * scale,
        }
    return {
        "service_tier": "flex",
        "context_band": "short",
        "pricing_as_of": PRICING_AS_OF,
        "pricing_source": PRICING_SOURCE,
        "measured_source_count": measured_source_count,
        "target_source_count": target_source_count,
        "linear_scale_factor": scale,
        "assumption": "Linear token-per-source extrapolation; excludes cache-write charges because current usage logs do not expose cache-write tokens.",
        "models": projections,
    }
