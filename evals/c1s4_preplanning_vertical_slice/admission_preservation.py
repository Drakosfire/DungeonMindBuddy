from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_classification import (
    infer_context_subject_class,
    infer_planner_lane,
    is_admittable_planner_evidence,
)

C1S4_NPC_FAMILY_BUCKETS: tuple[tuple[str, str], ...] = (
    ("pippa", "pippa"),
    ("bubbles", "bubbles"),
    ("grishna", "grishna"),
)

PRESERVATION_MAX_CHARS_PER_FAMILY = 600
PRESERVATION_MAX_CHARS_LOCATION = 800
PRESERVATION_MAX_TOTAL_CHARS = 1800


def _presentation_lane_for_item(item: dict[str, Any]) -> str:
    from evals.c1s4_preplanning_vertical_slice.context_admission import classify_presentation_lane

    return str(item.get("presentation_lane") or classify_presentation_lane(item))


def _item_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(k) or "")
        for k in ("unit_id", "source_path", "source_recap_path", "source_reference", "title", "snippet", "text")
    ).lower()


def _npc_path_family(item: dict[str, Any]) -> str | None:
    path = str(item.get("source_path") or item.get("source_recap_path") or "").lower()
    unit_id = str(item.get("unit_id") or "").lower()
    for bucket, needle in C1S4_NPC_FAMILY_BUCKETS:
        if f"/npcs/{needle}/" in path or unit_id.startswith(f"corpus:npc:{needle}:"):
            return bucket
    return None


def _npc_family_bucket(item: dict[str, Any]) -> str | None:
    path_family = _npc_path_family(item)
    if path_family:
        return path_family
    text = _item_text(item)
    for bucket, needle in C1S4_NPC_FAMILY_BUCKETS:
        if needle in text:
            return bucket
    return None


def _is_npc_family_candidate(item: dict[str, Any]) -> bool:
    if infer_context_subject_class(item) not in {"npc", "pc"}:
        return False
    if infer_planner_lane(item) not in {"character_party_behavior", "prior_campaign_memory"}:
        return False
    presentation = _presentation_lane_for_item(item)
    if presentation in {"navigation", "known_gap", "safety_constraint"}:
        return False
    source_kind = str(item.get("source_kind") or "")
    if source_kind in {"npc_hub", "npc_dossier", "session_recap", "session_memory"}:
        return True
    if "/npcs/" in _item_text(item) or "/pcs/" in _item_text(item):
        return True
    return bool(_npc_family_bucket(item))


def _is_location_worldbuilding_candidate(item: dict[str, Any]) -> bool:
    if infer_context_subject_class(item) != "location":
        return False
    if infer_planner_lane(item) not in {"location_worldbuilding", "prior_campaign_memory"}:
        return False
    presentation = _presentation_lane_for_item(item)
    if presentation in {"navigation", "known_gap", "safety_constraint"}:
        return False
    return str(item.get("source_kind") or "") in {"location_hub", "session_recap", "session_memory"} or "/locations/" in _item_text(item)


def _is_prior_route_event_candidate(item: dict[str, Any], question_text: str) -> bool:
    if not is_admittable_planner_evidence(item):
        return False
    if str(item.get("source_kind") or "") not in {"session_recap", "session_memory"}:
        return False
    lane = infer_planner_lane(item)
    if lane not in {"prior_campaign_memory", "location_worldbuilding", "unknown"}:
        return False
    text = _item_text(item)
    q = question_text.lower()
    if "mirathorn" in q and "mirathorn" not in text:
        return False
    if "stone bridge" in q and "stone bridge" not in text and "stonebridge" not in text:
        return False
    route_tokens = ("week", "travel", "road", "on foot", "journey", "days")
    if not any(tok in text for tok in route_tokens):
        return False
    return True


def _prior_route_event_score(item: dict[str, Any], *, candidate_rank: int) -> tuple[int, int, int, int]:
    text = _item_text(item)
    source_kind = str(item.get("source_kind") or "")
    kind_bonus = 2 if source_kind == "session_recap" else 1 if source_kind == "session_memory" else 0
    mirathorn_week = int("mirathorn" in text and "week" in text)
    stone_bridge = int("stone bridge" in text or "stonebridge" in text)
    return (mirathorn_week, stone_bridge, kind_bonus, -candidate_rank)


def _best_prior_route_event_candidate(
    candidates: list[dict[str, Any]],
    *,
    question_text: str,
    admitted_ranks: set[int],
) -> tuple[int, dict[str, Any]] | None:
    scored: list[tuple[tuple[int, int, int], int, dict[str, Any]]] = []
    for idx, item in enumerate(candidates, start=1):
        if idx in admitted_ranks:
            continue
        if not _is_prior_route_event_candidate(item, question_text):
            continue
        scored.append((_prior_route_event_score(item, candidate_rank=idx), idx, item))
    if not scored:
        return None
    scored.sort(key=lambda row: row[0], reverse=True)
    _, idx, item = scored[0]
    return idx, item


def build_admission_preservation_plan(
    *,
    question_text: str,
    retrieval_mode: str,
    lane_plan: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    qf = lane_plan.get("query_features") or {}
    signals = qf.get("intent_signals") or {}
    preserve_groups: list[dict[str, Any]] = []

    if signals.get("asks_prior_npc_context"):
        visible_families = sorted(
            {bucket for item in candidates if (bucket := _npc_family_bucket(item))}
        )
        preserve_groups.append(
            {
                "group_id": "character_party_behavior_npc",
                "required_when": "asks_prior_npc_context",
                "visible_npc_families": visible_families,
                "min_items_per_family": 1,
                "max_chars_per_family": PRESERVATION_MAX_CHARS_PER_FAMILY,
                "max_chars_total": PRESERVATION_MAX_TOTAL_CHARS,
                "priority": 0,
            }
        )

    asks_route = bool(signals.get("asks_route_or_distance"))
    has_location_candidates = any(_is_location_worldbuilding_candidate(c) and is_admittable_planner_evidence(c) for c in candidates)
    if asks_route:
        preserve_groups.append(
            {
                "group_id": "prior_campaign_route_event",
                "required_when": "asks_route_or_distance",
                "min_items": 1,
                "max_chars_total": 900,
                "priority": 0,
            }
        )
    if asks_route or has_location_candidates:
        preserve_groups.append(
            {
                "group_id": "location_worldbuilding",
                "required_when": "asks_route_or_distance_or_location_candidates_visible",
                "min_items": 1,
                "max_chars_total": PRESERVATION_MAX_CHARS_LOCATION,
                "priority": 1,
            }
        )

    return {
        "schema": "dmb_admission_preservation_plan_v1",
        "retrieval_mode": retrieval_mode,
        "preserve_groups": preserve_groups,
    }


def _best_candidate_for_family(
    candidates: list[dict[str, Any]],
    *,
    family: str,
    admitted_ranks: set[int],
) -> tuple[int, dict[str, Any]] | None:
    path_scoped: tuple[int, dict[str, Any]] | None = None
    lexical: tuple[int, dict[str, Any]] | None = None
    for idx, item in enumerate(candidates, start=1):
        if idx in admitted_ranks:
            continue
        if not is_admittable_planner_evidence(item) or not _is_npc_family_candidate(item):
            continue
        if _npc_path_family(item) == family:
            if path_scoped is None or idx < path_scoped[0]:
                path_scoped = (idx, item)
            continue
        if _npc_family_bucket(item) == family:
            if lexical is None or idx < lexical[0]:
                lexical = (idx, item)
    return path_scoped or lexical


def _best_location_candidate(
    candidates: list[dict[str, Any]],
    *,
    admitted_ranks: set[int],
) -> tuple[int, dict[str, Any]] | None:
    best: tuple[int, dict[str, Any]] | None = None
    for idx, item in enumerate(candidates, start=1):
        if idx in admitted_ranks:
            continue
        if not is_admittable_planner_evidence(item) or not _is_location_worldbuilding_candidate(item):
            continue
        if best is None or idx < best[0]:
            best = (idx, item)
    return best


def apply_admission_preservation(
    *,
    question_text: str,
    retrieval_mode: str,
    candidates: list[dict[str, Any]],
    lane_plan: dict[str, Any],
    lane_state: dict[str, dict[str, Any]],
    total_budget_chars: int,
    estimate_size,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return preserved admitted items (unsorted) and diagnostics."""
    plan = build_admission_preservation_plan(
        question_text=question_text,
        retrieval_mode=retrieval_mode,
        lane_plan=lane_plan,
        candidates=candidates,
    )
    preserved: list[dict[str, Any]] = []
    preserved_items_diag: list[dict[str, Any]] = []
    deferred_visible: list[dict[str, Any]] = []
    admitted_ranks: set[int] = set()
    preserved_chars = 0

    def _try_preserve(idx: int, item: dict[str, Any], *, group_id: str, reason: str, max_chars: int) -> bool:
        nonlocal preserved_chars
        if retrieval_mode == "prior_only" and str(item.get("source_kind")) == "support_knowledge_card":
            return False
        if idx in admitted_ranks:
            return True
        chars, tokens = estimate_size(item)
        if chars > max_chars:
            return False
        if preserved_chars + chars > PRESERVATION_MAX_TOTAL_CHARS:
            return False
        budget_lane = _infer_budget_lane(item)
        state = lane_state.get(budget_lane)
        if not state or chars > int(state.get("remaining", 0)):
            return False
        if sum(int(i["estimated_chars"]) for i in preserved) + chars > total_budget_chars:
            return False
        state["remaining"] -= chars
        presentation_lane = _presentation_lane_for_item(item)
        out = dict(item)
        out.update(
            {
                "candidate_rank": idx,
                "admission_policy": "lane_budgeted_v1",
                "admission_reason": reason,
                "presentation_lane": presentation_lane,
                "admission_budget_lane": budget_lane,
                "estimated_chars": chars,
                "estimated_tokens": tokens,
            }
        )
        preserved.append(out)
        preserved_items_diag.append(
            {
                "unit_id": item.get("unit_id"),
                "candidate_rank": idx,
                "group_id": group_id,
                "reason": reason,
                "estimated_chars": chars,
                "presentation_lane": presentation_lane,
                "admission_budget_lane": budget_lane,
            }
        )
        admitted_ranks.add(idx)
        preserved_chars += chars
        return True

    for group in plan.get("preserve_groups") or []:
        group_id = str(group.get("group_id") or "")
        if group_id == "character_party_behavior_npc":
            per_family_cap = int(group.get("max_chars_per_family") or PRESERVATION_MAX_CHARS_PER_FAMILY)
            for family in group.get("visible_npc_families") or []:
                pick = _best_candidate_for_family(candidates, family=str(family), admitted_ranks=admitted_ranks)
                if pick is None:
                    deferred_visible.append({"group_id": group_id, "npc_family": family, "reason": "no_admittable_candidate_visible"})
                    continue
                idx, item = pick
                _try_preserve(
                    idx,
                    item,
                    group_id=group_id,
                    reason=f"preserved_character_party_behavior_npc_{family}",
                    max_chars=per_family_cap,
                )
        elif group_id == "prior_campaign_route_event":
            pick = _best_prior_route_event_candidate(candidates, question_text=question_text, admitted_ranks=admitted_ranks)
            if pick is None:
                deferred_visible.append({"group_id": group_id, "reason": "no_admittable_prior_route_event_visible"})
            else:
                idx, item = pick
                _try_preserve(
                    idx,
                    item,
                    group_id=group_id,
                    reason="preserved_prior_campaign_route_event",
                    max_chars=int(group.get("max_chars_total") or 900),
                )
        elif group_id == "location_worldbuilding":
            pick = _best_location_candidate(candidates, admitted_ranks=admitted_ranks)
            if pick is None:
                deferred_visible.append({"group_id": group_id, "reason": "no_admittable_location_candidate_visible"})
            else:
                idx, item = pick
                _try_preserve(
                    idx,
                    item,
                    group_id=group_id,
                    reason="preserved_location_worldbuilding",
                    max_chars=int(group.get("max_chars_total") or PRESERVATION_MAX_CHARS_LOCATION),
                )

    diagnostics = {
        "schema": "dmb_admission_preservation_diagnostics_v1",
        "preservation_plan": plan,
        "preserved_items": preserved_items_diag,
        "deferred_visible_targets": deferred_visible,
        "budget_impact": {
            "preserved_chars": preserved_chars,
            "remaining_total_budget_chars": max(0, total_budget_chars - preserved_chars),
        },
    }
    return preserved, diagnostics


def _infer_budget_lane(item: dict[str, Any]) -> str:
    from evals.c1s4_preplanning_vertical_slice.context_admission import _infer_lane

    return _infer_lane(item)
