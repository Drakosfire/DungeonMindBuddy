"""
Response-accuracy rig for planner live answers: citation grounding + concept coverage,
plus legacy substring ``keyword_coverage`` and optional embedding (weak diagnostic).

Manifest: ``benchmark/manifest.json`` with per-scenario ``exemplar``, ``critical_keywords``,
and optional ``concept_checks`` (weighted phrases). See ``EVAL_DEFINITION.md``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_MANIFEST_NAME = "manifest.json"

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "of",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "with",
        "as",
        "by",
        "it",
        "its",
        "we",
        "our",
        "you",
        "your",
        "they",
        "their",
        "this",
        "that",
        "these",
        "those",
        "from",
        "into",
        "onto",
    }
)

# Sliding token window and max gap between consecutive phrase tokens (inclusive of skips).
_CONCEPT_WINDOW = 44
_CONCEPT_MAX_GAP = 10
_PROXIMITY_BONUS = 0.25
_EXACT_PHRASE_BONUS = 0.15


def benchmark_root() -> Path:
    return Path(__file__).resolve().parent / "benchmark"


def manifest_path() -> Path:
    return benchmark_root() / _MANIFEST_NAME


def load_manifest() -> dict[str, Any] | None:
    p = manifest_path()
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def manifest_row(manifest: dict[str, Any], scenario_id: str) -> dict[str, Any] | None:
    for row in manifest.get("scenarios") or []:
        if str(row.get("scenario_id", "")) == scenario_id:
            return row
    return None


def load_exemplar_text(row: dict[str, Any]) -> str | None:
    rel = str(row.get("exemplar", "")).strip()
    if not rel or ".." in rel:
        return None
    path = (benchmark_root() / rel).resolve()
    root = benchmark_root().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def score_keyword_coverage(candidate: str, keywords: list[str]) -> dict[str, Any]:
    """Case-insensitive substring match per keyword (legacy diagnostic)."""
    hay = candidate.lower()
    present: list[str] = []
    missing: list[str] = []
    for raw in keywords:
        k = str(raw).strip()
        if not k:
            continue
        if k.lower() in hay:
            present.append(k)
        else:
            missing.append(k)
    n = len(present) + len(missing)
    frac = (len(present) / n) if n else 1.0
    return {
        "keyword_count": n,
        "present": present,
        "missing": missing,
        "fraction": round(frac, 4),
    }


def _tokenize_for_match(text: str) -> list[str]:
    t = text.lower()
    t = t.replace("/", " ")
    t = re.sub(r"[*_`#\[\]()]", " ", t)
    t = re.sub(r"[^a-z0-9\- ]+", " ", t)
    parts: list[str] = []
    for w in t.split():
        if len(w) < 2 or w in _STOPWORDS:
            continue
        parts.append(w)
    return parts


def _content_tokens(phrase: str) -> list[str]:
    return _tokenize_for_match(phrase)


def _subsequence_with_max_gap(hay: list[str], need: list[str], max_gap: int) -> bool:
    if not need:
        return True
    pos = -1
    for ntk in need:
        found_at: int | None = None
        start = pos + 1
        for j in range(start, len(hay)):
            if hay[j] != ntk:
                continue
            if pos < 0:
                found_at = j
                break
            if j - pos - 1 <= max_gap:
                found_at = j
                break
        if found_at is None:
            return False
        pos = found_at
    return True


def _proximity_match(hay: list[str], need: list[str], window: int, max_gap: int) -> bool:
    if not need:
        return True
    if len(need) == 1:
        return need[0] in hay
    w = max(window, len(need) + max_gap * (len(need) - 1))
    for s in range(len(hay)):
        chunk = hay[s : s + w]
        if _subsequence_with_max_gap(chunk, need, max_gap):
            return True
    return False


def score_single_phrase_concept(candidate: str, phrase: str) -> dict[str, Any]:
    """Bag token coverage + proximity window + exact substring; returns score in [0, 1]."""
    raw_phrase = str(phrase).strip()
    if not raw_phrase:
        return {
            "phrase": phrase,
            "score": 1.0,
            "bag_fraction": 1.0,
            "proximity_match": True,
            "exact_substring": True,
            "content_tokens": [],
        }
    content = _content_tokens(raw_phrase)
    if not content:
        return {
            "phrase": raw_phrase,
            "score": 1.0,
            "bag_fraction": 1.0,
            "proximity_match": True,
            "exact_substring": True,
            "content_tokens": [],
        }
    cand = _tokenize_for_match(candidate)
    cand_set = set(cand)
    hits = sum(1 for t in content if t in cand_set)
    bag_fraction = hits / len(content)
    prox = _proximity_match(cand, content, _CONCEPT_WINDOW, _CONCEPT_MAX_GAP)
    exact = raw_phrase.lower() in candidate.lower()
    score = min(
        1.0,
        bag_fraction
        + (_PROXIMITY_BONUS if prox else 0.0)
        + (_EXACT_PHRASE_BONUS if exact else 0.0),
    )
    return {
        "phrase": raw_phrase,
        "score": round(score, 4),
        "bag_fraction": round(bag_fraction, 4),
        "proximity_match": prox,
        "exact_substring": exact,
        "content_tokens": content,
    }


def score_concept_coverage(candidate: str, weighted_phrases: list[tuple[str, float]]) -> dict[str, Any]:
    """
    ``weighted_phrases`` is (phrase, weight). Weighted mean of per-phrase scores.
    """
    if not weighted_phrases:
        return {
            "weighted_score": 1.0,
            "phrase_count": 0,
            "total_weight": 0.0,
            "per_phrase": [],
        }
    per: list[dict[str, Any]] = []
    num = 0.0
    den = 0.0
    for ph, wt in weighted_phrases:
        w = max(float(wt), 0.0)
        if w <= 0:
            continue
        one = score_single_phrase_concept(candidate, ph)
        one["weight"] = w
        per.append(one)
        num += w * float(one["score"])
        den += w
    ws = (num / den) if den > 0 else 1.0
    return {
        "weighted_score": round(ws, 4),
        "phrase_count": len(per),
        "total_weight": round(den, 4),
        "per_phrase": per,
    }


def _weighted_phrases_from_row(row: dict[str, Any]) -> list[tuple[str, float]]:
    checks = row.get("concept_checks")
    if isinstance(checks, list) and checks:
        out: list[tuple[str, float]] = []
        for item in checks:
            if not isinstance(item, dict):
                continue
            ph = str(item.get("phrase", "")).strip()
            if not ph:
                continue
            try:
                w = float(item.get("weight", 1.0) or 1.0)
            except (TypeError, ValueError):
                w = 1.0
            out.append((ph, w))
        if out:
            return out
    kws = [str(x) for x in (row.get("critical_keywords") or []) if str(x).strip()]
    return [(k, 1.0) for k in kws]


def build_citation_grounding(final_text: str, tool_trace: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """
    Summarize reads vs citations (lazy-imports ``live_eval`` to avoid import cycles).
    """
    if tool_trace is None:
        return None
    from evals.planner_slice.live_eval import (
        cite_matches_any_read,
        dedupe_read_paths_preserve_order,
        extract_cited_markdown_paths_from_final,
        read_paths_from_tool_trace,
        reads_mentioned_in_final,
    )

    reads = dedupe_read_paths_preserve_order(read_paths_from_tool_trace(tool_trace))
    cites = extract_cited_markdown_paths_from_final(final_text)
    if reads:
        not_grounded = [c for c in cites if not cite_matches_any_read(c, reads)]
    else:
        not_grounded = list(cites)
    uncited = reads_mentioned_in_final(final_text, reads)
    return {
        "read_count": len(reads),
        "citation_count": len(cites),
        "reads": reads,
        "citations_in_final": cites,
        "citations_not_grounded": not_grounded,
        "reads_not_mentioned_in_final": uncited,
    }


def build_quality_summary(
    citation_grounding: dict[str, Any] | None,
    concept_coverage: dict[str, Any] | None,
    keyword_coverage: dict[str, Any] | None,
    embedding: dict[str, Any] | None,
    *,
    exemplar_loaded: bool,
) -> dict[str, Any]:
    """
    Roll up benchmark signals for **quality assessment** (tuning / dashboards).

    This is intentionally separate from live-eval **pass/fail**: fixtures own gates;
    ``quality_summary`` names dimensions and short heuristic notes so runs are comparable
    without treating any single scalar as "the score."
    """
    out: dict[str, Any] = {
        "purpose": "Compare runs on citation facts, exemplar-derived concepts, and weak diagnostics.",
        "exemplar_available_for_concepts": exemplar_loaded,
    }
    notes: list[str] = []

    if citation_grounding is not None:
        n_ng = len(citation_grounding.get("citations_not_grounded") or [])
        n_uc = len(citation_grounding.get("reads_not_mentioned_in_final") or [])
        n_reads = int(citation_grounding.get("read_count") or 0)
        # Grounding gate is hallucinated cites only; reads are listed in the report appendix.
        ok = n_ng == 0
        out["citation_alignment"] = {
            "telemetry_available": True,
            "read_count": n_reads,
            "citation_count": int(citation_grounding.get("citation_count") or 0),
            "citations_not_grounded_count": n_ng,
            "reads_not_echoed_in_prose_count": n_uc,
            "aligned": ok,
        }
        if n_ng > 0:
            notes.append(
                "Citation grounding: final text cites at least one `.md` path not opened with "
                "`read_corpus_file` this turn (hallucinated citation)."
            )
        elif n_uc > 0:
            notes.append(
                f"{n_uc} retrieved path(s) not echoed in assistant prose; see report "
                "`Corpus files retrieved` section for the authoritative list."
            )
        elif n_reads == 0:
            notes.append("Citation telemetry: no read_corpus_file rows in trace; alignment vacuous.")
    else:
        out["citation_alignment"] = {"telemetry_available": False}

    if exemplar_loaded and concept_coverage and concept_coverage.get("per_phrase"):
        per = [p for p in (concept_coverage.get("per_phrase") or []) if isinstance(p, dict)]
        scores = [float(p.get("score", 0) or 0) for p in per]
        below_05 = sum(1 for s in scores if s < 0.5)
        below_025 = sum(1 for s in scores if s < 0.25)
        mean_s = sum(scores) / len(scores) if scores else 0.0
        out["exemplar_concepts"] = {
            "weighted_score": concept_coverage.get("weighted_score"),
            "phrase_count": len(per),
            "mean_phrase_score": round(mean_s, 4),
            "phrases_scored_below_0_5": below_05,
            "phrases_scored_below_0_25": below_025,
        }
        if below_05 > max(2, len(per) // 4):
            notes.append(
                "Many manifest phrases score below 0.5; inspect per_phrase for misses vs token-collision "
                "(e.g. Mage + Hand appearing apart)."
            )
    elif not exemplar_loaded:
        out["exemplar_concepts"] = None
        notes.append("Exemplar file missing; concept coverage not computed for this row.")
    else:
        out["exemplar_concepts"] = None

    if keyword_coverage:
        out["legacy_substring_keywords"] = {
            "fraction": keyword_coverage.get("fraction"),
            "hit_count": len(keyword_coverage.get("present") or []),
            "miss_count": len(keyword_coverage.get("missing") or []),
        }
    else:
        out["legacy_substring_keywords"] = None

    if embedding and not embedding.get("skipped"):
        cos = embedding.get("cosine_similarity")
        out["embedding_diagnostic"] = {"cosine_similarity": cos}
        wc = None
        if exemplar_loaded and concept_coverage:
            wc = concept_coverage.get("weighted_score")
        try:
            if cos is not None and wc is not None and float(cos) > 0.85 and float(wc) < 0.65:
                notes.append(
                    "Embedding cosine is high while concept coverage is moderate; treat cosine as weak "
                    "signal for this task shape."
                )
        except (TypeError, ValueError):
            pass
    elif embedding and embedding.get("skipped"):
        out["embedding_diagnostic"] = {"skipped": True, "reason": embedding.get("reason")}
    else:
        out["embedding_diagnostic"] = {"available": False}

    if (
        exemplar_loaded
        and concept_coverage
        and keyword_coverage
        and concept_coverage.get("weighted_score") is not None
        and keyword_coverage.get("fraction") is not None
    ):
        try:
            delta = float(concept_coverage["weighted_score"]) - float(keyword_coverage["fraction"])
            if delta > 0.12:
                notes.append(
                    f"Weighted concept score exceeds legacy substring fraction by {delta:.2f}; "
                    "prefer concept_coverage when judging ritual/skill wording layout."
                )
        except (TypeError, ValueError):
            pass

    out["notes"] = notes
    return out


def _maybe_embed_cosine(exemplar: str, candidate: str, model_id: str | None) -> dict[str, Any] | None:
    if os.environ.get("PLANNER_BENCHMARK_EMBED", "").strip().lower() not in ("1", "true", "yes"):
        return None
    try:
        from evals.mirathorn_vertical_slice.embedding_scorer import (
            cosine_similarity_single,
            embed_texts,
            embedding_available,
            load_embedding_model,
        )
    except ImportError:
        return {"skipped": True, "reason": "embedding_scorer_import_failed"}
    if not embedding_available():
        return {"skipped": True, "reason": "sentence_transformers_unavailable"}
    mid = (model_id or "").strip() or "perplexity-ai/pplx-embed-v1-0.6B"
    try:
        model = load_embedding_model(mid)
    except Exception as exc:  # pragma: no cover - runtime env
        return {"skipped": True, "reason": f"load_failed:{exc!r}"}
    vecs = embed_texts(model, [exemplar, candidate])
    cos = cosine_similarity_single(vecs[0], vecs[1])
    return {"skipped": False, "embedding_model_id": mid, "cosine_similarity": round(float(cos), 4)}


def instrument_planner_answer(
    scenario_id: str,
    final_text: str,
    tool_trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Build a telemetry dict for ``scenario_id`` + model ``final_text``.

    Returns ``None`` if no manifest or no row for this scenario.
    Does **not** gate pass/fail — logging / report section only (until you wire thresholds).
    """
    manifest = load_manifest()
    if not manifest:
        return None
    row = manifest_row(manifest, scenario_id)
    if not row:
        return None

    citation = build_citation_grounding(final_text, tool_trace)

    exemplar = load_exemplar_text(row)
    if exemplar is None:
        err: dict[str, Any] = {
            "scenario_id": scenario_id,
            "error": "exemplar_missing_or_unreadable",
            "exemplar_relpath": row.get("exemplar"),
        }
        if citation is not None:
            err["citation_grounding"] = citation
        err["quality_summary"] = build_quality_summary(
            citation, None, None, None, exemplar_loaded=False
        )
        return err

    kws = [str(x) for x in (row.get("critical_keywords") or []) if str(x).strip()]
    kw = score_keyword_coverage(final_text, kws)
    wph = _weighted_phrases_from_row(row)
    concept = score_concept_coverage(final_text, wph)

    out: dict[str, Any] = {
        "scenario_id": scenario_id,
        "exemplar_relpath": row.get("exemplar"),
        "exemplar_chars": len(exemplar),
        "candidate_chars": len(final_text),
        "declared_min_keyword_fraction": row.get("min_keyword_fraction"),
        "declared_saturation_cosine": row.get("saturation_cosine"),
        "declared_saturation_keyword_fraction": row.get("saturation_keyword_fraction"),
        "declared_min_weighted_concept_score": row.get("min_weighted_concept_score"),
        "keyword_coverage": kw,
        "concept_coverage": concept,
    }
    if citation is not None:
        out["citation_grounding"] = citation
    emb = _maybe_embed_cosine(exemplar, final_text, str(manifest.get("embedding_model_id") or ""))
    if emb is not None:
        out["embedding"] = emb
    out["quality_summary"] = build_quality_summary(
        citation,
        out.get("concept_coverage"),
        out.get("keyword_coverage"),
        out.get("embedding"),
        exemplar_loaded=True,
    )
    return out
