"""Planner pricing helpers (no API)."""

from __future__ import annotations

from src.agent.planner_pricing import pricing_rates_for_model, usage_cost_usd


def test_pricing_longest_prefix_matches_chat_latest() -> None:
    r = pricing_rates_for_model("gpt-5.3-chat-latest")
    assert r["input"] == 1.75


def test_usage_cost_splits_cached_input() -> None:
    c = usage_cost_usd(
        model_id="gpt-5.3-chat-latest",
        input_tokens=10_000,
        output_tokens=500,
        cached_tokens=8000,
    )
    assert c["uncached_input_tokens"] == 2000
    assert c["total_usd"] > 0


def test_unknown_model_zero_rates() -> None:
    c = usage_cost_usd(model_id="unknown-model-xyz", input_tokens=1000, output_tokens=100, cached_tokens=0)
    assert c["pricing_table_matched"] is False
    assert c["total_usd"] == 0.0
