"""Embedding similarity for benchmark expected-answer vs synthesized-answer checks."""

from __future__ import annotations

import math
from typing import Any

EMBEDDING_MODEL_DEFAULT = "text-embedding-3-large"

# OpenAI list price for text-embedding-3-large input tokens, USD per 1M tokens.
_EMBEDDING_INPUT_USD_PER_1M: dict[str, float] = {
    "text-embedding-3-large": 0.13,
}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity, or 0.0 when either vector is empty/zero."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _embedding_usage_tokens(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", None) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", None) or 0),
    }


def embedding_cost_usd(*, model: str, total_tokens: int) -> float:
    rate = _EMBEDDING_INPUT_USD_PER_1M.get(model.strip(), 0.0)
    return total_tokens / 1_000_000.0 * rate


def compare_expected_to_output_with_embeddings(
    *,
    expected_answer: str,
    output_answer: str,
    model: str = EMBEDDING_MODEL_DEFAULT,
) -> dict[str, Any]:
    """Embed expected/output answers and return similarity plus usage/cost telemetry."""
    from openai import OpenAI

    client = OpenAI()
    resp = client.embeddings.create(
        model=model.strip(),
        input=[expected_answer.strip(), output_answer.strip()],
    )
    vectors = [list(item.embedding) for item in resp.data]
    usage = _embedding_usage_tokens(resp.usage)
    total_tokens = int(usage.get("total_tokens", 0))
    return {
        "model": model.strip(),
        "cosine_similarity": cosine_similarity(vectors[0], vectors[1]) if len(vectors) == 2 else 0.0,
        "usage": usage,
        "cost_usd": embedding_cost_usd(model=model.strip(), total_tokens=total_tokens),
    }
