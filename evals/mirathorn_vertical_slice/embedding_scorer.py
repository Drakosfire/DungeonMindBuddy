"""Embedding-based semantic similarity scoring for QA/synthesis evaluation.

Uses perplexity-ai/pplx-embed-v1-0.6B loaded locally via SentenceTransformers.
Gracefully degrades when sentence-transformers is not installed.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

_MODEL_HF_ID = "perplexity-ai/pplx-embed-v1-0.6B"
_TRUST_REMOTE_CODE = True


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _hf_home_is_usable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".dmb_hf_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _ensure_hf_runtime_caches() -> None:
    """Pin Hugging Face caches under the repo when defaults are missing or broken.

    Dotenv often sets ``HF_HOME`` to a removable disk; transformers and the HF
    xet backend still write logs and blobs under that tree.  If ``HF_HOME`` is
    not writable, redirect it (and unset hub/module caches) to ``.cache/embedding_hf/``.
    """
    root = _project_root() / ".cache" / "embedding_hf"
    root.mkdir(parents=True, exist_ok=True)
    home = root / "home"
    mod = root / "modules"
    hub = root / "hub"
    for p in (home, mod, hub):
        p.mkdir(parents=True, exist_ok=True)

    existing_hf_home = os.environ.get("HF_HOME", "").strip()
    if existing_hf_home and not _hf_home_is_usable(Path(existing_hf_home)):
        os.environ["HF_HOME"] = str(home)

    os.environ.setdefault("HF_MODULES_CACHE", str(mod))
    os.environ.setdefault("HF_HUB_CACHE", str(hub))


def _resolve_cache_folder() -> str | None:
    """Pick a writable SentenceTransformer snapshot cache.

    ``HF_HOME`` from dotenv may point at an offline mount; skip candidates that
    cannot be created and fall back under ``.cache/embedding_hf/``.
    """
    candidates = [
        os.getenv("EMBEDDING_MODEL_PATH"),
        os.getenv("SENTENCE_TRANSFORMERS_HOME"),
        os.getenv("HUGGINGFACE_HUB_CACHE"),
        os.getenv("HF_HOME"),
    ]
    for raw in candidates:
        if not (raw or "").strip():
            continue
        path = Path(raw.strip())
        try:
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        except OSError:
            continue
    fallback = _project_root() / ".cache" / "embedding_hf" / "sentence_transformers"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)
    except OSError:
        return None


def embedding_available() -> bool:
    """Return True if sentence-transformers is importable."""
    _ensure_hf_runtime_caches()
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def load_embedding_model(model_id: str = _MODEL_HF_ID) -> Any:
    """Load a SentenceTransformer model for embedding.

    Raises ImportError if sentence-transformers is not installed.
    """
    _ensure_hf_runtime_caches()
    from sentence_transformers import SentenceTransformer  # type: ignore
    import torch  # type: ignore

    cache_folder = _resolve_cache_folder()
    device = (os.getenv("EMBEDDING_DEVICE") or "").strip()
    if not device:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    kwargs: dict[str, Any] = {
        "model_name_or_path": model_id,
        "device": device,
        "trust_remote_code": _TRUST_REMOTE_CODE,
    }
    if cache_folder:
        kwargs["cache_folder"] = cache_folder

    model = SentenceTransformer(**kwargs)
    print(
        f"INFO: [embedding] model={model_id!r} device={device!r} "
        f"cache_folder={cache_folder!r}",
        file=sys.stderr,
        flush=True,
    )
    return model


def embed_texts(model: Any, texts: Sequence[str], batch_size: int = 16) -> np.ndarray:
    """Encode texts into L2-normalized float32 embeddings.

    PPLX emits unnormalized int8 vectors per model card, so we encode with
    normalize_embeddings=False and L2-normalize in numpy afterward.
    """
    t0 = time.perf_counter()
    raw = model.encode(
        list(texts),
        batch_size=batch_size,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    mat = np.array(raw, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    out = mat / norms
    elapsed = time.perf_counter() - t0
    dim = int(out.shape[1]) if out.ndim == 2 else 0
    print(
        f"INFO: [embedding] encoded n={len(texts)} dim={dim} in {elapsed:.2f}s",
        file=sys.stderr,
        flush=True,
    )
    return out


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
