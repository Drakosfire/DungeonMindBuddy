from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "over",
        "and",
        "or",
        "but",
        "not",
        "no",
        "nor",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "than",
        "too",
        "very",
        "just",
        "about",
    }
)
_WORD_RE = re.compile(r"[a-z][a-z']{2,}")
_SESSION_RE = re.compile(r"\bsession\s+(\d+)\b", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower())) - _STOPWORDS


def _normalize_phrase(value: str) -> str:
    phrase = re.sub(r"[^a-z0-9']+", " ", (value or "").strip().lower())
    return re.sub(r"\s+", " ", phrase).strip()


def _lexicon_maps(
    corpus_lexicon: dict[str, Any] | None,
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    if not corpus_lexicon:
        return {}, []
    alias_to_canonical_raw = corpus_lexicon.get("alias_to_canonical")
    alias_to_canonical: dict[str, str] = {}
    phrase_pairs: list[tuple[str, str]] = []
    if isinstance(alias_to_canonical_raw, dict):
        for alias, canonical in alias_to_canonical_raw.items():
            norm_alias = _normalize_phrase(str(alias))
            norm_canonical = _normalize_phrase(str(canonical))
            if not norm_alias or not norm_canonical:
                continue
            alias_to_canonical[norm_alias] = norm_canonical
            phrase_pairs.append((norm_alias, norm_canonical))
    return alias_to_canonical, phrase_pairs


def _expand_tokens(tokens: set[str], alias_to_canonical: dict[str, str]) -> set[str]:
    if not alias_to_canonical:
        return set(tokens)
    expanded = set(tokens)
    for token in tokens:
        canonical = alias_to_canonical.get(token)
        if not canonical:
            continue
        expanded.update(_tokenize(canonical))
        for part in canonical.split(" "):
            if len(part) >= 3 and part not in _STOPWORDS:
                expanded.add(part)
    return expanded


@dataclass(frozen=True)
class EvidenceHit:
    evidence_id: str
    score: float
    document_id: str
    source_order_index: int
    inferred_session: int | None


@dataclass(frozen=True)
class EvidenceRetrievalResult:
    selected_evidence_ids: list[str]
    seeded_evidence_ids: list[str]
    ranked_hits: list[EvidenceHit]
    selected_document_ids: list[str]
    debug: dict[str, Any]


def _question_session(question: str) -> int | None:
    match = _SESSION_RE.search(question)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _unit_allowed(unit: dict[str, Any], campaign_id: str | None) -> bool:
    layer = str(unit.get("canon_layer", "")).strip()
    if layer == "world":
        return True
    if campaign_id is None:
        return layer != "campaign"
    if layer != "campaign":
        return True
    return str(unit.get("campaign_id", "")).strip() == campaign_id


def _score_units(
    question: str,
    candidate_units: list[dict[str, Any]],
    *,
    scope_document_ids: set[str],
    corpus_lexicon: dict[str, Any] | None = None,
    enable_alias_normalization: bool = False,
    alias_match_weight: float = 0.0,
    lexicon_max_boost: float = 0.0,
    include_legacy_phrase_boost: bool = True,
) -> list[EvidenceHit]:
    alias_to_canonical, phrase_pairs = _lexicon_maps(corpus_lexicon)
    q_tokens = _tokenize(question)
    if enable_alias_normalization:
        q_tokens = _expand_tokens(q_tokens, alias_to_canonical)
    q_session = _question_session(question)
    if not q_tokens:
        return []

    doc_freq: Counter[str] = Counter()
    unit_tokens: list[set[str]] = []
    for unit in candidate_units:
        text = str(unit.get("text", ""))
        section = " ".join(str(p) for p in (unit.get("section_path") or []))
        tokens = _tokenize(f"{text} {section}")
        if enable_alias_normalization:
            tokens = _expand_tokens(tokens, alias_to_canonical)
        unit_tokens.append(tokens)
        for token in q_tokens:
            if token in tokens:
                doc_freq[token] += 1

    n_docs = len(candidate_units)
    if n_docs == 0:
        return []
    idf = {
        token: (
            math.log((n_docs - doc_freq.get(token, 0) + 0.5) / (doc_freq.get(token, 0) + 0.5) + 1.0)
            if doc_freq.get(token, 0) > 0
            else 0.0
        )
        for token in q_tokens
    }

    out: list[EvidenceHit] = []
    for unit, tokens in zip(candidate_units, unit_tokens, strict=False):
        evidence_id = str(unit.get("evidence_id", "")).strip()
        if not evidence_id:
            continue
        score = sum(idf.get(token, 0.0) for token in q_tokens if token in tokens)
        if score <= 0.0:
            continue

        document_id = str(unit.get("document_id", "")).strip()
        if scope_document_ids and document_id in scope_document_ids:
            score += 0.35

        if include_legacy_phrase_boost:
            section_text = " ".join(str(p).lower() for p in (unit.get("section_path") or []))
            phrase_boost = 0
            for phrase in ("trap", "alarm", "ward", "countdown", "consequence", "session"):
                if phrase in question.lower() and phrase in section_text:
                    phrase_boost += 1
            score += min(0.3, phrase_boost * 0.08)

        if phrase_pairs and lexicon_max_boost > 0 and alias_match_weight > 0:
            question_lower = _normalize_phrase(question)
            haystack = _normalize_phrase(
                f"{unit.get('text', '')} {' '.join(str(p) for p in (unit.get('section_path') or []))}"
            )
            lexicon_hits = 0
            for alias, canonical in phrase_pairs:
                if alias in question_lower and (canonical in haystack or alias in haystack):
                    lexicon_hits += 1
            if lexicon_hits > 0:
                score += min(lexicon_max_boost, lexicon_hits * alias_match_weight)

        inferred_session_raw = unit.get("inferred_session")
        inferred_session: int | None
        try:
            inferred_session = int(inferred_session_raw) if inferred_session_raw is not None else None
        except (TypeError, ValueError):
            inferred_session = None

        if q_session is not None and inferred_session is not None and q_session == inferred_session:
            score += 0.25

        try:
            source_order = int(unit.get("source_order_index", 0))
        except (TypeError, ValueError):
            source_order = 0

        out.append(
            EvidenceHit(
                evidence_id=evidence_id,
                score=score,
                document_id=document_id,
                source_order_index=source_order,
                inferred_session=inferred_session,
            )
        )

    out.sort(key=lambda hit: hit.score, reverse=True)
    return out


def _embedding_rerank_evidence_hits(
    question: str,
    ranked_hits: list[EvidenceHit],
    filtered_units: list[dict[str, Any]],
) -> list[EvidenceHit]:
    """Optionally fuse BM25 order with chunk–question cosine similarity (env-gated)."""
    if os.environ.get("DMB_EVIDENCE_EMBEDDING_RERANK", "").strip() != "1":
        return ranked_hits
    if not ranked_hits:
        return ranked_hits
    try:
        from evals.mirathorn_vertical_slice.embedding_scorer import (
            embed_texts,
            embedding_available,
            load_embedding_model,
        )
    except ImportError:
        return ranked_hits
    if not embedding_available():
        return ranked_hits
    try:
        top_n = int(os.environ.get("DMB_EVIDENCE_EMBEDDING_RERANK_TOP_N", "48"))
    except ValueError:
        top_n = 48
    top_n = max(8, min(top_n, len(ranked_hits)))
    try:
        weight = float(os.environ.get("DMB_EVIDENCE_EMBEDDING_RERANK_WEIGHT", "0.6"))
    except ValueError:
        weight = 0.6
    weight = max(0.0, min(1.0, weight))

    unit_by_eid = {
        str(u.get("evidence_id", "")).strip(): u
        for u in filtered_units
        if str(u.get("evidence_id", "")).strip()
    }
    pool = ranked_hits[:top_n]
    rest = ranked_hits[top_n:]
    texts: list[str] = []
    for h in pool:
        u = unit_by_eid.get(h.evidence_id, {})
        body = str(u.get("text", ""))[:800]
        sp = u.get("section_path") or []
        sec = " ".join(str(p) for p in (sp[:3] if isinstance(sp, list) else []))
        chunk = f"{sec}\n{body}".strip() or "(empty)"
        texts.append(chunk)
    try:
        model = load_embedding_model()
        qv = embed_texts(model, [question])[0]
        mv = embed_texts(model, texts)
        sem_scores = (mv @ qv).tolist()
    except Exception:
        return ranked_hits

    bm25_scores = [h.score for h in pool]
    bmax = max(bm25_scores) if bm25_scores else 1.0
    if bmax <= 0:
        bmax = 1.0

    fused_hits: list[EvidenceHit] = []
    for hit, sem, bm in zip(pool, sem_scores, bm25_scores, strict=True):
        bnorm = bm / bmax
        fuse = weight * float(sem) + (1.0 - weight) * bnorm
        fused_hits.append(
            EvidenceHit(
                evidence_id=hit.evidence_id,
                score=fuse,
                document_id=hit.document_id,
                source_order_index=hit.source_order_index,
                inferred_session=hit.inferred_session,
            )
        )
    fused_hits.sort(key=lambda h: h.score, reverse=True)
    return fused_hits + rest


def _resolve_effective_top_k(
    *,
    ranked_hits: list[EvidenceHit],
    top_k: int,
    adaptive_top_k: bool,
    adaptive_top_k_max: int,
    adaptive_density_threshold: float,
) -> int:
    if not ranked_hits:
        return max(1, top_k)
    base = max(1, min(int(top_k), len(ranked_hits)))
    if not adaptive_top_k:
        return base
    cap = max(base, min(int(adaptive_top_k_max), len(ranked_hits)))
    if cap <= base:
        return base
    threshold = max(0.01, min(1.0, float(adaptive_density_threshold)))
    max_score = ranked_hits[0].score
    if max_score <= 0:
        return base
    effective = base
    for hit in ranked_hits[base:cap]:
        if hit.score >= max_score * threshold:
            effective += 1
        else:
            break
    return max(base, min(effective, cap))


def collect_provenance_evidence_for_entities(
    projection: dict[str, Any],
    entity_ids: list[str],
) -> list[str]:
    """Return provenance evidence IDs for the given entities (stable public API for CLI two-pass)."""
    return _collect_entity_provenance_ids(projection, entity_ids)


def _collect_entity_provenance_ids(
    projection: dict[str, Any],
    entity_ids: list[str],
) -> list[str]:
    evidence_ids: list[str] = []
    seen: set[str] = set()
    entities = projection.get("entities") or {}
    for entity_id in entity_ids:
        attrs = ((entities.get(entity_id) or {}).get("attributes") or {})
        for payload in attrs.values():
            if not isinstance(payload, dict):
                continue
            for evidence_id in (payload.get("provenance_evidence_ids") or []):
                eid = str(evidence_id).strip()
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                evidence_ids.append(eid)
    return evidence_ids


def retrieve_relevant_evidence(
    question: str,
    evidence_units: list[dict[str, Any]],
    *,
    campaign_id: str | None,
    scope_document_ids: list[str] | set[str] | None = None,
    top_k: int = 24,
    neighbor_window: int = 1,
    max_neighbors: int = 24,
    corpus_lexicon: dict[str, Any] | None = None,
    enable_alias_normalization: bool = False,
    alias_match_weight: float = 0.06,
    lexicon_max_boost: float = 0.35,
    include_legacy_phrase_boost: bool = True,
    adaptive_top_k: bool = False,
    adaptive_top_k_max: int = 48,
    adaptive_density_threshold: float = 0.3,
    projection: dict[str, Any] | None = None,
    entity_awareness_enabled: bool = False,
    entity_quota: int = 10,
    entity_evidence_quota: int = 12,
) -> EvidenceRetrievalResult:
    scope_doc_ids = {str(doc).strip() for doc in (scope_document_ids or []) if str(doc).strip()}
    filtered = [unit for unit in evidence_units if _unit_allowed(unit, campaign_id)]
    if scope_doc_ids:
        in_scope = [u for u in filtered if str(u.get("document_id", "")).strip() in scope_doc_ids]
        if in_scope:
            filtered = in_scope

    ranked_hits = _score_units(
        question,
        filtered,
        scope_document_ids=scope_doc_ids,
        corpus_lexicon=corpus_lexicon,
        enable_alias_normalization=enable_alias_normalization,
        alias_match_weight=alias_match_weight,
        lexicon_max_boost=lexicon_max_boost,
        include_legacy_phrase_boost=include_legacy_phrase_boost,
    )
    ranked_hits = _embedding_rerank_evidence_hits(question, ranked_hits, filtered)
    effective_top_k = _resolve_effective_top_k(
        ranked_hits=ranked_hits,
        top_k=top_k,
        adaptive_top_k=adaptive_top_k,
        adaptive_top_k_max=adaptive_top_k_max,
        adaptive_density_threshold=adaptive_density_threshold,
    )
    seeded = ranked_hits[:effective_top_k]
    seeded_ids = [hit.evidence_id for hit in seeded]
    selected_ids = set(seeded_ids)

    by_doc: dict[str, list[tuple[int, str]]] = {}
    for unit in filtered:
        evidence_id = str(unit.get("evidence_id", "")).strip()
        document_id = str(unit.get("document_id", "")).strip()
        if not evidence_id or not document_id:
            continue
        try:
            source_order = int(unit.get("source_order_index", 0))
        except (TypeError, ValueError):
            source_order = 0
        by_doc.setdefault(document_id, []).append((source_order, evidence_id))
    for doc in by_doc:
        by_doc[doc].sort(key=lambda row: row[0])

    neighbor_budget = max(0, int(max_neighbors))
    expanded = 0
    per_seed_neighbors = os.environ.get("DMB_EVIDENCE_PER_SEED_NEIGHBORS", "").strip() == "1"
    if neighbor_window > 0 and neighbor_budget > 0:
        if per_seed_neighbors and seeded:
            per_seed_budget = max(1, neighbor_budget // max(1, len(seeded)))
            for seed in seeded:
                if expanded >= neighbor_budget:
                    break
                rows = by_doc.get(seed.document_id, [])
                if not rows:
                    continue
                seed_expanded = 0
                for source_order, evidence_id in rows:
                    if expanded >= neighbor_budget:
                        break
                    if evidence_id in selected_ids:
                        continue
                    if abs(source_order - seed.source_order_index) > neighbor_window:
                        continue
                    selected_ids.add(evidence_id)
                    expanded += 1
                    seed_expanded += 1
                    if seed_expanded >= per_seed_budget:
                        break
        else:
            for seed in seeded:
                rows = by_doc.get(seed.document_id, [])
                if not rows:
                    continue
                for source_order, evidence_id in rows:
                    if evidence_id in selected_ids:
                        continue
                    if abs(source_order - seed.source_order_index) > neighbor_window:
                        continue
                    selected_ids.add(evidence_id)
                    expanded += 1
                    if expanded >= neighbor_budget:
                        break
                if expanded >= neighbor_budget:
                    break

    entity_expanded = 0
    if (
        entity_awareness_enabled
        and projection is not None
        and entity_evidence_quota > 0
        and selected_ids
    ):
        overlap_scores = rank_entities_by_evidence_overlap(projection, set(selected_ids))
        prioritized_entities = sorted(
            overlap_scores,
            key=lambda entity_id: overlap_scores[entity_id],
            reverse=True,
        )
        if entity_quota > 0:
            prioritized_entities = prioritized_entities[:entity_quota]
        provenance_ids = _collect_entity_provenance_ids(projection, prioritized_entities)
        for evidence_id in provenance_ids:
            if evidence_id in selected_ids:
                continue
            selected_ids.add(evidence_id)
            entity_expanded += 1
            if entity_expanded >= int(entity_evidence_quota):
                break

    selected_ordered = [hit.evidence_id for hit in ranked_hits if hit.evidence_id in selected_ids]
    if expanded > 0:
        remaining = [eid for eid in selected_ids if eid not in set(selected_ordered)]
        selected_ordered.extend(sorted(remaining))

    try:
        doc_quota = int(os.environ.get("DMB_EVIDENCE_DOC_QUOTA", "0") or "0")
    except ValueError:
        doc_quota = 0
    if doc_quota > 0:
        evidence_doc_map: dict[str, str] = {}
        for unit in filtered:
            eid = str(unit.get("evidence_id", "")).strip()
            if eid:
                evidence_doc_map[eid] = str(unit.get("document_id", "")).strip()
        doc_counts: dict[str, int] = {}
        quota_filtered: list[str] = []
        for eid in selected_ordered:
            doc_id = evidence_doc_map.get(eid, "")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            if doc_counts[doc_id] <= doc_quota:
                quota_filtered.append(eid)
        selected_ordered = quota_filtered

    selected_docs = sorted(
        {
            str(unit.get("document_id", "")).strip()
            for unit in filtered
            if str(unit.get("evidence_id", "")).strip() in selected_ids
        }
    )
    return EvidenceRetrievalResult(
        selected_evidence_ids=selected_ordered,
        seeded_evidence_ids=seeded_ids,
        ranked_hits=ranked_hits,
        selected_document_ids=selected_docs,
        debug={
            "candidate_units": len(filtered),
            "ranked_hits": len(ranked_hits),
            "seeded": len(seeded_ids),
            "requested_top_k": int(top_k),
            "effective_top_k": int(effective_top_k),
            "adaptive_top_k_enabled": bool(adaptive_top_k),
            "adaptive_top_k_max": int(adaptive_top_k_max),
            "adaptive_density_threshold": float(adaptive_density_threshold),
            "expanded_neighbors": expanded,
            "expanded_entity_provenance": entity_expanded,
            "entity_awareness_enabled": bool(entity_awareness_enabled),
            "entity_quota": int(entity_quota),
            "entity_evidence_quota": int(entity_evidence_quota),
            "selected": len(selected_ordered),
            "scope_docs_applied": sorted(scope_doc_ids),
            "lexicon_enabled": bool(corpus_lexicon),
            "alias_normalization_enabled": bool(enable_alias_normalization),
            "lexicon_terms": len((corpus_lexicon or {}).get("terms") or []),
            "legacy_phrase_boost_enabled": bool(include_legacy_phrase_boost),
            "lexicon_alias_match_weight": float(alias_match_weight),
            "lexicon_max_boost": float(lexicon_max_boost),
            "score_stats": {
                "max": float(ranked_hits[0].score) if ranked_hits else 0.0,
                "min_seed": float(seeded[-1].score) if seeded else 0.0,
            },
        },
    )


def rank_entities_by_evidence_overlap(
    projection: dict[str, Any],
    evidence_ids: set[str],
) -> dict[str, float]:
    """Return per-entity overlap score in [0, 1] against selected evidence IDs."""
    if not evidence_ids:
        return {}
    scores: dict[str, float] = {}
    for entity_id, payload in (projection.get("entities") or {}).items():
        attrs = (payload or {}).get("attributes") or {}
        entity_evidence: set[str] = set()
        for attr_payload in attrs.values():
            if not isinstance(attr_payload, dict):
                continue
            entity_evidence.update(
                str(eid).strip()
                for eid in (attr_payload.get("provenance_evidence_ids") or [])
                if str(eid).strip()
            )
        if not entity_evidence:
            continue
        overlap = len(entity_evidence & evidence_ids)
        if overlap <= 0:
            continue
        scores[str(entity_id)] = min(1.0, overlap / max(1, min(5, len(entity_evidence))))
    return scores
