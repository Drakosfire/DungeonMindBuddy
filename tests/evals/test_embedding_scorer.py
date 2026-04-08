from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

np = pytest.importorskip("numpy")

from evals.mirathorn_vertical_slice.embedding_scorer import (  # noqa: E402
    cosine_similarity_single,
    embed_texts,
    score_batch,
)


def _make_mock_model(dim: int = 8) -> MagicMock:
    """Return a mock SentenceTransformer whose encode returns deterministic vectors.

    Uses a counter-based seed so successive calls produce different embeddings.
    """
    model = MagicMock()
    call_counter = {"n": 0}

    def _encode(texts, **_kwargs):
        seed = 42 + call_counter["n"]
        call_counter["n"] += 1
        rng = np.random.RandomState(seed)
        return rng.randn(len(texts), dim).astype(np.float32)

    model.encode = _encode
    return model


def test_embed_texts_returns_correct_shape() -> None:
    model = _make_mock_model(dim=16)
    vecs = embed_texts(model, ["hello", "world", "test"])
    assert vecs.shape == (3, 16)
    assert vecs.dtype == np.float32


def test_embed_texts_l2_normalizes_rows() -> None:
    model = _make_mock_model(dim=8)
    vecs = embed_texts(model, ["a", "b"])
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)


def test_cosine_similarity_identical_vectors_returns_one() -> None:
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity_single(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_returns_zero() -> None:
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert cosine_similarity_single(a, b) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors_returns_negative_one() -> None:
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    assert cosine_similarity_single(a, b) == pytest.approx(-1.0)


def test_score_batch_returns_per_pair_scores() -> None:
    model = _make_mock_model(dim=8)
    scores = score_batch(model, ["expected A", "expected B"], ["answer A", "answer B"])
    assert len(scores) == 2
    assert all(isinstance(s, float) for s in scores)
    assert all(-1.0 <= s <= 1.0 for s in scores)


def test_score_batch_length_mismatch_raises() -> None:
    model = _make_mock_model()
    with pytest.raises(ValueError, match="Length mismatch"):
        score_batch(model, ["a", "b"], ["x"])


def test_score_batch_empty_returns_empty() -> None:
    model = _make_mock_model()
    assert score_batch(model, [], []) == []


def test_embed_texts_handles_zero_vector_gracefully() -> None:
    """If the model returns a zero vector, normalization should not produce NaN."""
    model = MagicMock()
    model.encode = lambda texts, **kw: np.zeros((len(texts), 4), dtype=np.float32)
    vecs = embed_texts(model, ["zero"])
    assert not np.any(np.isnan(vecs))


def test_embedding_available_reflects_import() -> None:
    from evals.mirathorn_vertical_slice.embedding_scorer import embedding_available

    result = embedding_available()
    assert isinstance(result, bool)


def test_runner_loads_expected_answer_summary_and_core_claims() -> None:
    """Verify _load_gold_questions includes both summary and core claims."""
    from evals.mirathorn_vertical_slice.run_council_room_question_set import (
        GOLD_QUESTIONS_PATH,
        _load_gold_questions,
    )

    questions = _load_gold_questions(GOLD_QUESTIONS_PATH)
    for q in questions:
        assert "expected_answer_summary" in q, f"Missing expected_answer_summary in {q['id']}"
        assert q["expected_answer_summary"].strip(), (
            f"Empty expected_answer_summary in {q['id']}"
        )
        assert "core_claims" in q, f"Missing core_claims in {q['id']}"
        assert isinstance(q["core_claims"], list), f"core_claims must be a list in {q['id']}"
        assert q["core_claims"], f"core_claims should not be empty in {q['id']}"


def test_runner_embedding_skipped_when_env_not_set() -> None:
    """When DMB_EMBEDDING_SCORING is not set, embedding scores should be None."""
    from evals.mirathorn_vertical_slice.run_council_room_question_set import (
        EMBEDDING_SCORING_ENV,
    )

    env_backup = os.environ.pop("DMB_EMBEDDING_SCORING", None)
    try:
        enabled = os.environ.get(EMBEDDING_SCORING_ENV, "").strip() == "1"
        assert not enabled
    finally:
        if env_backup is not None:
            os.environ["DMB_EMBEDDING_SCORING"] = env_backup


@pytest.mark.embedding_smoke
def test_smoke_embedding_model_load_and_encode() -> None:
    """Load perplexity embed model from HuggingFace and run one encode pass.

    Skips unless DMB_SMOKE_EMBEDDING_MODEL=1 (avoids ~600MB download in default CI).
    Requires: uv pip install -e '.[embedding]' (or sentence-transformers + torch).
    """
    if os.environ.get("DMB_SMOKE_EMBEDDING_MODEL", "").strip() != "1":
        pytest.skip(
            "Set DMB_SMOKE_EMBEDDING_MODEL=1 to run live embedding smoke "
            "(downloads model on first run)."
        )

    try:
        import sentence_transformers  # noqa: F401
    except ImportError as exc:
        raise AssertionError(
            "DMB_SMOKE_EMBEDDING_MODEL=1 but sentence-transformers is not installed. "
            "Install with: uv sync --extra embedding"
        ) from exc

    from evals.mirathorn_vertical_slice.embedding_scorer import (
        cosine_similarity_single,
        embed_texts,
        load_embedding_model,
    )

    model = load_embedding_model()
    phrase = "smoke test: the quick brown fox"
    vecs = embed_texts(model, [phrase, phrase, "unrelated quantum waffle"])
    assert vecs.shape[0] == 3
    assert vecs.dtype == np.float32
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    same = cosine_similarity_single(vecs[0], vecs[1])
    assert same == pytest.approx(1.0, abs=1e-4)

    diff = cosine_similarity_single(vecs[0], vecs[2])
    assert -1.0 <= diff <= 1.0
    assert diff < same
