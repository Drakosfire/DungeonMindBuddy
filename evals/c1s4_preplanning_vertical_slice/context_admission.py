from __future__ import annotations

import math
import re
from typing import Any

SUPPORT_KIND = "support_knowledge_card"
STOPWORDS = {
    "the","and","for","with","from","that","this","what","when","where","which","into","onto","your","their","have","been","were","about","would","could","should","there","after","before","while","during","than","then","them","they","are","was","did","does","how","why","who","our","you","his","her","its","not","can","may","might","had","has","was","were"
}


def _jsonish(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    import json
    return json.dumps(value, sort_keys=True)


def render_context_item_for_budget(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ["title", "snippet", "text", "body", "content", "source_reference", "source_kind", "source_layer"]:
        value = _jsonish(item.get(key))
        if value:
            parts.append(value)
    return "\n".join(parts)


def estimate_context_item_size(item: dict[str, Any]) -> tuple[int, int]:
    chars = len(render_context_item_for_budget(item))
    return chars, math.ceil(chars / 4)


def _normalize_terms(text: str) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))
    return {t for t in toks if len(t) >= 3 and t not in STOPWORDS}


def extract_query_terms(question_text: str) -> set[str]:
    return _normalize_terms(question_text)


def support_candidate_is_relevant(question_text: str, item: dict[str, Any]) -> bool:
    q_terms = extract_query_terms(question_text)
    if not q_terms:
        return False
    item_terms = _normalize_terms(render_context_item_for_budget(item))
    overlap = q_terms & item_terms
    return len(overlap) >= 2 or any(t in item_terms for t in q_terms)


def classify_presentation_lane(item: dict[str, Any]) -> str:
    source_kind = str(item.get("source_kind") or "")
    source_layer = str(item.get("source_layer") or "")
    txt = render_context_item_for_budget(item).lower()
    if source_kind == "support_knowledge_card":
        return "support_knowledge"
    if source_kind == "session_memory":
        return "prior_campaign_memory"
    if "known gap" in txt or source_kind == "support_gap":
        return "known_gap"
    if "oracle" in txt or "forbidden" in txt or "safety" in txt or source_layer == "safety":
        return "safety_constraint"
    return "unknown"


def build_budgeted_admission(*, question_text: str, retrieval_mode: str, candidates: list[dict[str, Any]], candidate_depth: int = 50, total_budget_chars: int = 8000) -> dict[str, Any]:
    candidate_context = candidates[:candidate_depth]
    support_mode = retrieval_mode != "prior_only"
    support_budget = 2000 if support_mode else 0
    general_budget = total_budget_chars - support_budget

    support_candidates: list[tuple[int, dict[str, Any], int, int]] = []
    general_candidates: list[tuple[int, dict[str, Any], int, int]] = []
    counts: dict[str, int] = {}

    for idx, item in enumerate(candidate_context, start=1):
        kind = str(item.get("source_kind") or "session_memory")
        counts[kind] = counts.get(kind, 0) + 1
        chars, tokens = estimate_context_item_size(item)
        if kind == SUPPORT_KIND and support_mode and support_candidate_is_relevant(question_text, item):
            support_candidates.append((idx, item, chars, tokens))
        elif kind != SUPPORT_KIND:
            general_candidates.append((idx, item, chars, tokens))

    admitted_raw: list[dict[str, Any]] = []
    for idx, item, chars, tokens in general_candidates:
        if chars <= general_budget:
            general_budget -= chars
            out = dict(item)
            out.update({"candidate_rank": idx, "admission_policy": "budgeted_v1", "admission_reason": "general_budget_candidate", "presentation_lane": classify_presentation_lane(item), "estimated_chars": chars, "estimated_tokens": tokens})
            admitted_raw.append(out)
    for idx, item, chars, tokens in support_candidates:
        if chars <= support_budget:
            support_budget -= chars
            out = dict(item)
            out.update({"candidate_rank": idx, "admission_policy": "budgeted_v1", "admission_reason": "support_budget_relevant_candidate", "presentation_lane": classify_presentation_lane(item), "estimated_chars": chars, "estimated_tokens": tokens})
            admitted_raw.append(out)

    admitted_sorted = sorted(admitted_raw, key=lambda x: int(x["candidate_rank"]))
    for i, item in enumerate(admitted_sorted, start=1):
        item["admitted_rank"] = i

    admitted_chars = sum(int(i["estimated_chars"]) for i in admitted_sorted)
    return {
        "admission_policy": "budgeted_v1",
        "admission_budget": {
            "candidate_depth": candidate_depth,
            "total_budget_chars": total_budget_chars,
            "general_budget_chars": total_budget_chars - (2000 if support_mode else 0),
            "support_budget_chars": 2000 if support_mode else 0,
            "estimated_tokens": math.ceil(admitted_chars / 4),
        },
        "candidate_context_diagnostics": {"candidate_count": len(candidate_context), "source_kind_counts": counts},
        "admitted_context": admitted_sorted,
    }
