from __future__ import annotations

import math
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
) -> list[EvidenceHit]:
    q_tokens = _tokenize(question)
    q_session = _question_session(question)
    if not q_tokens:
        return []

    doc_freq: Counter[str] = Counter()
    unit_tokens: list[set[str]] = []
    for unit in candidate_units:
        text = str(unit.get("text", ""))
        section = " ".join(str(p) for p in (unit.get("section_path") or []))
        tokens = _tokenize(f"{text} {section}")
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

        section_text = " ".join(str(p).lower() for p in (unit.get("section_path") or []))
        phrase_boost = 0
        for phrase in ("trap", "alarm", "ward", "countdown", "consequence", "session"):
            if phrase in question.lower() and phrase in section_text:
                phrase_boost += 1
        score += min(0.3, phrase_boost * 0.08)

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


def retrieve_relevant_evidence(
    question: str,
    evidence_units: list[dict[str, Any]],
    *,
    campaign_id: str | None,
    scope_document_ids: list[str] | set[str] | None = None,
    top_k: int = 24,
    neighbor_window: int = 1,
    max_neighbors: int = 24,
) -> EvidenceRetrievalResult:
    scope_doc_ids = {str(doc).strip() for doc in (scope_document_ids or []) if str(doc).strip()}
    filtered = [unit for unit in evidence_units if _unit_allowed(unit, campaign_id)]
    if scope_doc_ids:
        in_scope = [u for u in filtered if str(u.get("document_id", "")).strip() in scope_doc_ids]
        if in_scope:
            filtered = in_scope

    ranked_hits = _score_units(question, filtered, scope_document_ids=scope_doc_ids)
    seeded = ranked_hits[: max(1, top_k)]
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
    if neighbor_window > 0 and neighbor_budget > 0:
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

    selected_ordered = [hit.evidence_id for hit in ranked_hits if hit.evidence_id in selected_ids]
    if expanded > 0:
        remaining = [eid for eid in selected_ids if eid not in set(selected_ordered)]
        selected_ordered.extend(sorted(remaining))

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
        ranked_hits=seeded,
        selected_document_ids=selected_docs,
        debug={
            "candidate_units": len(filtered),
            "ranked_hits": len(ranked_hits),
            "seeded": len(seeded_ids),
            "expanded_neighbors": expanded,
            "selected": len(selected_ordered),
            "scope_docs_applied": sorted(scope_doc_ids),
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
