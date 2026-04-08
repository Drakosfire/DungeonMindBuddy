"""Question-aware entity retrieval for the QA synthesis pipeline.

Combines name matching, keyword search (BM25-style), and optional
embedding search to identify the most relevant entities for a given
question, then expands via relationship graph and shared evidence.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

_NOISE_ATTRIBUTES = frozenset({"source_comments", "unresolved_questions"})

_NOISE_LABEL_PREFIXES = (
    "not mentioned",
    "no direct assertion",
    "no assertion",
    "no asserted fact",
    "not asserted",
    "text does not mention",
    "no direct mention",
    "not directly mentioned",
    "mentioned in evidence unit",
    "presence in evidence",
    "evidence unit text content",
    "mentioned in evidence",
    "no assertions in provided text",
    "no direct assertions in provided",
    "the text does not",
    "not mentioned in the provided",
    "not mentioned in evidence",
    "no assertion about",
    "no assertion in",
)

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "over",
    "and", "or", "but", "not", "no", "nor",
    "that", "this", "these", "those", "it", "its",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "than", "too", "very", "just", "about",
})

_WORD_RE = re.compile(r"[a-z][a-z']{2,}")


def _tokenize(text: str) -> set[str]:
    """Extract lowercase alpha tokens, filtering stopwords and very short words."""
    return set(_WORD_RE.findall(text.lower())) - _STOPWORDS


def _is_noise_fact(attribute: str, label: str) -> bool:
    """Return True if a fact is noise that should be excluded from summaries."""
    if attribute in _NOISE_ATTRIBUTES:
        return True
    if not label or not label.strip():
        return True
    lowered = label.lower().strip()
    if len(lowered) < 5:
        return True
    return any(lowered.startswith(p) for p in _NOISE_LABEL_PREFIXES)


def build_entity_summary(
    meta: dict[str, Any],
    entity_data: dict[str, Any],
) -> str:
    """Build searchable text from entity metadata and projected attributes.

    Filters out noise facts to produce a cleaner signal for search.
    """
    parts: list[str] = []
    name = meta.get("display_name", "Unknown")
    cls = meta.get("entity_class", "")
    facets = meta.get("subtype_facets", []) or meta.get("semantic_facets", [])
    aliases = meta.get("aliases", [])

    header = name
    if cls:
        header += f" ({cls})"
    if facets:
        header += f" [{', '.join(str(f) for f in facets[:6])}]"
    parts.append(header)

    real_aliases = [a for a in aliases if a and a.lower() != name.lower()][:5]
    if real_aliases:
        parts.append(f"Also known as: {', '.join(real_aliases)}")

    attributes = entity_data.get("attributes", {})
    for attr in sorted(attributes):
        payload = attributes[attr]
        label = payload.get("value_label", "")
        if _is_noise_fact(attr, label):
            continue
        if len(label) > 300:
            label = label[:300] + "..."
        parts.append(f"{attr}: {label}")

    return "\n".join(parts)


def _embed_texts(model: Any, texts: list[str]) -> Any:
    """Embed texts using a SentenceTransformer-compatible model, L2-normalized."""
    import numpy as np

    raw = model.encode(texts, show_progress_bar=False)
    arr = np.asarray(raw, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return arr / norms


class EntityIndex:
    """In-memory index of entity summaries for multi-signal search."""

    def __init__(self) -> None:
        self.entity_ids: list[str] = []
        self.summaries: list[str] = []
        self.summary_tokens: list[set[str]] = []
        self.embeddings: Any = None
        self.name_to_ids: dict[str, list[str]] = {}
        self._built = False

    @property
    def size(self) -> int:
        return len(self.entity_ids)

    def build(
        self,
        projection: dict[str, Any],
        entities: list[dict[str, Any]],
    ) -> None:
        """Build index from a projection and entity metadata list."""
        meta_by_id: dict[str, dict[str, Any]] = {}
        for e in entities:
            eid = e.get("entity_id", "")
            if eid:
                meta_by_id[eid] = e

        proj_entities = projection.get("entities", {})
        for entity_id in sorted(proj_entities):
            entity_data = proj_entities[entity_id]
            meta = meta_by_id.get(entity_id, {})
            summary = build_entity_summary(meta, entity_data)

            self.entity_ids.append(entity_id)
            self.summaries.append(summary)
            self.summary_tokens.append(_tokenize(summary))

            names: list[str] = [meta.get("display_name", "")]
            names.extend(meta.get("aliases", []))
            for raw_name in names:
                if not raw_name or len(raw_name) < 2:
                    continue
                key = raw_name.lower().strip()
                if key not in self.name_to_ids:
                    self.name_to_ids[key] = []
                if entity_id not in self.name_to_ids[key]:
                    self.name_to_ids[key].append(entity_id)

        self._built = True
        logger.info(
            "EntityIndex built: %d entities, %d name entries",
            len(self.entity_ids),
            len(self.name_to_ids),
        )

    def search_by_name(self, question: str) -> dict[str, float]:
        """Find entities whose names/aliases appear in the question text.

        Returns {entity_id: score} where score is proportional to name length.
        """
        q_lower = question.lower()
        scores: dict[str, float] = {}
        for name, eids in self.name_to_ids.items():
            if len(name) < 3:
                continue
            if name in q_lower:
                name_score = len(name) / 50.0
                for eid in eids:
                    scores[eid] = max(scores.get(eid, 0.0), name_score)
        return scores

    def search_by_keyword(
        self, question: str, top_k: int = 50
    ) -> list[tuple[str, float]]:
        """BM25-style keyword search over entity summaries."""
        q_tokens = _tokenize(question)
        if not q_tokens:
            return []

        n_docs = len(self.entity_ids)
        if n_docs == 0:
            return []

        doc_freq: Counter[str] = Counter()
        for tokens in self.summary_tokens:
            for t in q_tokens:
                if t in tokens:
                    doc_freq[t] += 1

        idf: dict[str, float] = {}
        for t in q_tokens:
            df = doc_freq.get(t, 0)
            idf[t] = (
                math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0) if df > 0 else 0.0
            )

        results: list[tuple[str, float]] = []
        for i, tokens in enumerate(self.summary_tokens):
            score = sum(idf.get(t, 0.0) for t in q_tokens if t in tokens)
            if score > 0:
                results.append((self.entity_ids[i], score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def compute_embeddings(self, model: Any) -> None:
        """Pre-compute embeddings for all entity summaries."""
        if not self.summaries:
            return
        t0 = time.time()
        self.embeddings = _embed_texts(model, self.summaries)
        logger.info(
            "Embeddings computed: %d entities in %.1fs",
            len(self.summaries),
            time.time() - t0,
        )

    def search_by_embedding(
        self, model: Any, question: str, top_k: int = 50
    ) -> list[tuple[str, float]]:
        """Semantic search using embedding cosine similarity."""
        if self.embeddings is None:
            return []

        import numpy as np

        q_emb = _embed_texts(model, [question])
        sims = (q_emb @ self.embeddings.T).flatten()
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(self.entity_ids[int(i)], float(sims[i])) for i in top_indices]


def _expand_via_relationships(
    seed_ids: set[str],
    projection: dict[str, Any],
    index: EntityIndex,
) -> set[str]:
    """Expand seed set by following relationship_tags to connected entities."""
    expanded: set[str] = set()
    proj_entities = projection.get("entities", {})

    for eid in seed_ids:
        entity_data = proj_entities.get(eid, {})
        attrs = entity_data.get("attributes", {})

        for attr_name in ("relationship_tags", "role"):
            payload = attrs.get(attr_name, {})
            label = payload.get("value_label", "")
            if not label:
                continue
            label_lower = label.lower()
            for name, ref_ids in index.name_to_ids.items():
                if len(name) >= 4 and name in label_lower:
                    for ref_id in ref_ids:
                        if ref_id not in seed_ids:
                            expanded.add(ref_id)

    return expanded


def _expand_via_shared_evidence(
    seed_ids: set[str],
    projection: dict[str, Any],
    max_expansion: int = 10,
) -> set[str]:
    """Find entities that share evidence units with seed entities."""
    proj_entities = projection.get("entities", {})

    seed_evidence: set[str] = set()
    for eid in seed_ids:
        entity_data = proj_entities.get(eid, {})
        for attr_payload in entity_data.get("attributes", {}).values():
            seed_evidence.update(attr_payload.get("provenance_evidence_ids", []))

    if not seed_evidence:
        return set()

    expanded: set[str] = set()
    for eid, entity_data in proj_entities.items():
        if eid in seed_ids:
            continue
        for attr_payload in entity_data.get("attributes", {}).values():
            if any(
                evid in seed_evidence
                for evid in attr_payload.get("provenance_evidence_ids", [])
            ):
                expanded.add(eid)
                break
        if len(expanded) >= max_expansion:
            break

    return expanded


def retrieve_relevant_entities(
    question: str,
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    *,
    embedding_model: Any = None,
    top_k: int = 30,
    name_boost: float = 3.0,
    keyword_weight: float = 1.0,
    embedding_weight: float = 1.5,
    expand_relationships: bool = True,
    expand_evidence: bool = True,
    max_evidence_expansion: int = 10,
    min_score: float = 0.01,
    index: EntityIndex | None = None,
) -> tuple[list[tuple[str, float]], EntityIndex]:
    """Retrieve entity IDs relevant to a question, ranked by combined score.

    Returns ([(entity_id, combined_score), ...], index).
    The index is returned so callers can cache it across queries.
    """
    t0 = time.time()

    if index is None:
        index = EntityIndex()
        index.build(projection, entities)

    name_scores = index.search_by_name(question)

    keyword_results = index.search_by_keyword(question, top_k=top_k * 2)
    keyword_scores = dict(keyword_results)
    if keyword_scores:
        max_kw = max(keyword_scores.values())
        if max_kw > 0:
            keyword_scores = {k: v / max_kw for k, v in keyword_scores.items()}

    embedding_scores: dict[str, float] = {}
    if embedding_model is not None:
        if index.embeddings is None:
            index.compute_embeddings(embedding_model)
        emb_results = index.search_by_embedding(
            embedding_model, question, top_k=top_k * 2
        )
        embedding_scores = dict(emb_results)

    all_ids = set(name_scores) | set(keyword_scores) | set(embedding_scores)
    combined: list[tuple[str, float]] = []
    for eid in all_ids:
        score = 0.0
        if eid in name_scores:
            score += name_scores[eid] * name_boost
        if eid in keyword_scores:
            score += keyword_scores[eid] * keyword_weight
        if eid in embedding_scores:
            score += max(0.0, embedding_scores[eid]) * embedding_weight
        if score >= min_score:
            combined.append((eid, score))

    combined.sort(key=lambda x: x[1], reverse=True)

    selected = list(combined[:top_k])
    selected_ids = {eid for eid, _ in selected}

    expansion_count = 0
    if expand_relationships and selected_ids:
        rel_expanded = _expand_via_relationships(selected_ids, projection, index)
        for eid in rel_expanded:
            if eid not in selected_ids:
                selected_ids.add(eid)
                selected.append((eid, min_score * 0.5))
                expansion_count += 1

    if expand_evidence and selected_ids:
        ev_expanded = _expand_via_shared_evidence(
            selected_ids, projection, max_expansion=max_evidence_expansion
        )
        for eid in ev_expanded:
            if eid not in selected_ids:
                selected_ids.add(eid)
                selected.append((eid, min_score * 0.1))
                expansion_count += 1

    selected.sort(key=lambda x: x[1], reverse=True)

    elapsed = time.time() - t0
    logger.info(
        "Retrieval: %d entities from %d (%.2fs) "
        "[name=%d kw=%d emb=%d expanded=%d]",
        len(selected),
        index.size,
        elapsed,
        len(name_scores),
        len(keyword_scores),
        len(embedding_scores),
        expansion_count,
    )

    return selected, index


def filter_projection(
    projection: dict[str, Any],
    entity_ids: set[str],
) -> dict[str, Any]:
    """Return a copy of projection containing only the specified entity_ids."""
    filtered_entities = {
        eid: data
        for eid, data in projection.get("entities", {}).items()
        if eid in entity_ids
    }
    return {
        **projection,
        "entities": filtered_entities,
        "metrics": {
            **projection.get("metrics", {}),
            "projected_entities": len(filtered_entities),
            "retrieval_filtered": True,
            "pre_filter_count": len(projection.get("entities", {})),
        },
    }
