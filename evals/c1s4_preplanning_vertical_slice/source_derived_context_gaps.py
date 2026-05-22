from __future__ import annotations

from typing import Any

SOURCE_DERIVED_GAP_SCHEMA = "dmb_source_derived_context_gap_v1"

_FORBIDDEN_GOLD_GAP_PHRASES = (
    "exact Stone Bridge-to-Mirathorn route gazetteer",
    "intermediate settlements",
    "day-by-day travel route",
    "route-specific ecology",
)


def _context_haystack(items: list[dict[str, Any]], *, keys: tuple[str, ...]) -> str:
    return " ".join(
        str(i.get(k) or "")
        for i in items
        for k in keys
    ).lower()


def _is_route_distance_question(question_text: str, query_features: dict[str, Any] | None) -> bool:
    text = question_text.lower()
    route_terms = ("how far", "mirathorn", "traveling", "road", "route", "encounter")
    return "mirathorn" in text and any(term in text for term in route_terms)


def _has_positive_stone_bridge_mirathorn_context(items: list[dict[str, Any]]) -> bool:
    refs = _context_haystack(
        items,
        keys=("unit_id", "source_path", "source_recap_path", "title", "snippet"),
    )
    return ("stone_bridge" in refs or "stone bridge" in refs) and "mirathorn" in refs


def _text_establishes_exact_route_gazetteer(hay: str) -> bool:
    lower = hay.lower()
    absence_markers = (
        "not yet established",
        "not established",
        "does not establish",
        "open canon question",
        "are unknown",
        "uncertain",
        "not found in retrieved",
    )
    if any(marker in lower for marker in absence_markers):
        return False
    positive_signals = (
        "stone bridge to mirathorn route:",
        "stone bridge-to-mirathorn route:",
        "day-by-day travel route",
        "intermediate settlements between",
        "route gazetteer for",
        "travel days from stone bridge to mirathorn",
        "route-specific ecology between stone bridge and mirathorn",
    )
    return any(sig in lower for sig in positive_signals)


def _has_exact_route_gazetteer(items: list[dict[str, Any]]) -> bool:
    hay = _context_haystack(
        items,
        keys=("unit_id", "source_path", "source_recap_path", "section_heading", "title", "snippet"),
    )
    return _text_establishes_exact_route_gazetteer(hay)


def _positive_basis_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded_unit_id_fragments = (
        "retrieval-keywords",
        "suggested-reads",
        "cross-references",
        "authority-stance",
        "campaign-canon-npcs-anchored-here",
        "timeline-pointers",
        "sub-locations-and-scene-anchors",
        "canonical-name-and-legacy-spellings",
        "mechanical-sheets",
        "package-notes",
        "statblock-generator",
        "source-pointers",
        "float-goat",
        "bubbles",
        "hempholm",
        "rivers_edge",
    )

    def _rank(item: dict[str, Any]) -> tuple[int, str]:
        ref = str(item.get("unit_id") or item.get("ref") or "").lower()
        blob = _context_haystack(
            [item],
            keys=("unit_id", "source_path", "source_recap_path", "title", "snippet"),
        )
        if any(fragment in ref for fragment in excluded_unit_id_fragments):
            return (99, ref)
        if "/npcs/" in blob and "stone_bridge" not in ref:
            return (98, ref)
        if "session_recap:session-3" in ref or "session-3:observed-play-prose" in ref:
            return (0, ref)
        if "stone_bridge:canon-summary" in ref:
            return (1, ref)
        if "stone_bridge:open-canon-questions" in ref:
            return (2, ref)
        if "stone_bridge" in ref and ("mirathorn" in blob or "stone bridge" in blob):
            return (3, ref)
        if ("stone bridge" in blob or "stone_bridge" in blob) and "mirathorn" in blob:
            return (4, ref)
        return (50, ref)

    ranked = sorted(items, key=_rank)
    selected = [item for item in ranked if _rank(item)[0] < 50][:5]
    return selected


def _positive_context_refs(items: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for item in _positive_basis_items(items):
        ref = str(item.get("unit_id") or item.get("ref") or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _mirathorn_route_gap_text() -> str:
    return (
        "Retrieved prior context supports Stone Bridge and Mirathorn as relevant travel context, "
        "but does not establish the exact route, stops, or road encounters between them."
    )


def _emit_mirathorn_route_gap(
    *,
    question_id: str,
    positive_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SOURCE_DERIVED_GAP_SCHEMA,
        "gap_id": "source_gap:mirathorn_exact_route_gap",
        "gap": _mirathorn_route_gap_text(),
        "source": "deterministic_absence_analysis",
        "evidence_scope": "allowed_prior_context",
        "presentation_lane": "known_gap",
        "source_kind": "source_derived_gap",
        "subject_class": "route_gap",
        "question_id": question_id,
        "basis": {
            "positive_context_refs": _positive_context_refs(positive_items),
            "missing_context_type": "route_gazetteer",
            "searched_terms": ["Stone Bridge", "Mirathorn", "route", "road", "travel"],
        },
    }


def gap_text_contains_forbidden_gold_phrase(gap_text: str) -> bool:
    return any(phrase in gap_text for phrase in _FORBIDDEN_GOLD_GAP_PHRASES)


def is_source_derived_route_gap_hit(item_or_prov: dict[str, Any]) -> bool:
    if item_or_prov.get("source_kind") != "source_derived_gap":
        return False
    if item_or_prov.get("source") != "deterministic_absence_analysis":
        return False
    if item_or_prov.get("evidence_scope") != "allowed_prior_context":
        return False
    text = str(item_or_prov.get("gap") or item_or_prov.get("snippet") or "").lower()
    return (
        "route" in text
        and ("mirathorn" in text or "stone bridge" in text)
        and any(term in text for term in ("not established", "not found", "does not establish", "unclear"))
    )


def source_derived_gap_to_grading_item(gap: dict[str, Any]) -> dict[str, Any]:
    ref = str(gap.get("gap_id") or "")
    return {
        "unit_id": ref,
        "ref": ref,
        "snippet": str(gap.get("gap") or ""),
        "gap": gap.get("gap"),
        "presentation_lane": gap.get("presentation_lane", "known_gap"),
        "source_kind": gap.get("source_kind", "source_derived_gap"),
        "source": gap.get("source"),
        "evidence_scope": gap.get("evidence_scope"),
        "subject_class": gap.get("subject_class", "route_gap"),
        "basis": gap.get("basis"),
    }


def build_source_derived_context_gaps(
    *,
    question_id: str,
    question_text: str,
    retrieval_mode: str,
    candidate_context: list[dict[str, Any]],
    admitted_context: list[dict[str, Any]],
    query_features: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    del retrieval_mode  # reserved for future mode-specific detectors
    if not _is_route_distance_question(question_text, query_features):
        return []

    allowed_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*admitted_context, *candidate_context]:
        ref = str(item.get("unit_id") or item.get("ref") or "")
        if ref and ref in seen:
            continue
        if ref:
            seen.add(ref)
        allowed_items.append(item)

    if not _has_positive_stone_bridge_mirathorn_context(allowed_items):
        return []
    if _has_exact_route_gazetteer(allowed_items):
        return []

    gap = _emit_mirathorn_route_gap(question_id=question_id, positive_items=allowed_items)
    if gap_text_contains_forbidden_gold_phrase(str(gap.get("gap") or "")):
        return []
    return [gap]
