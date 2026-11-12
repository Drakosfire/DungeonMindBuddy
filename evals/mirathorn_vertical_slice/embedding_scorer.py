"""Embedding-based semantic similarity scoring for QA evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.agent.retrieval_embeddings import (
    embed_texts as embed_texts,
    embedding_available as embedding_available,
    load_embedding_model as load_embedding_model,
)


def cosine_similarity_single(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalized vectors (dot product)."""
    return float(np.dot(a, b))


def score_batch(
    model: Any,
    expected_summaries: list[str],
    answers: list[str],
) -> list[float]:
    """Compute per-pair cosine similarity between expected summaries and answers.

    Both lists must have the same length.  Returns a list of similarity scores.
    """
    if len(expected_summaries) != len(answers):
        raise ValueError(
            f"Length mismatch: {len(expected_summaries)} expected vs {len(answers)} answers"
        )
    if not expected_summaries:
        return []

    expected_vecs = embed_texts(model, expected_summaries)
    answer_vecs = embed_texts(model, answers)
    return [
        cosine_similarity_single(expected_vecs[i], answer_vecs[i])
        for i in range(len(expected_summaries))
    ]
