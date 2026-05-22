from __future__ import annotations

from typing import Any, Callable

from evals.c1s4_preplanning_vertical_slice.context_admission import render_context_item_for_budget
from evals.c1s4_preplanning_vertical_slice.context_classification import (
    NON_ADMITTABLE_EVIDENCE_ROLES,
    infer_context_subject_class,
    is_admittable_planner_evidence,
    is_navigation_only_context,
)
from evals.c1s4_preplanning_vertical_slice.context_renderer import render_context_packet
from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    RETRIEVAL_MODES,
    context_item_satisfies_lane_aware_group,
    grade_question_packet,
    load_expected_context_gold,
    match_context_item,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.visibility_provenance import is_planner_visible_for_c1s4_preplanning

ROW_SCHEMA = "dmb_pr67_required_group_admission_row_v2"
DIAGNOSTICS_SCHEMA = "dmb_pr67_required_group_admission_diagnostics_v2"

Q3_DISTANCE_MATCH = {"text_contains_all": ["mirathorn", "week"]}
Q3_DISTANCE_GROUP_ID = "mirathorn_distance_estimate_from_play"
TIER_A_QUESTIONS = frozenset({1, 3, 5})

Q3_DISTANCE_GOLD_GROUP: dict[str, Any] = {
    "group_id": Q3_DISTANCE_GROUP_ID,
    "min_hits": 1,
    "required_lane": "prior_campaign_memory",
    "expected_rendered_section": "prior_campaign_memory",
    "allowed_subject_classes": ["session_memory"],
    "disallowed_evidence_roles": ["navigation_only"],
    "requires_evidence_compatible": True,
    "match": Q3_DISTANCE_MATCH,
}


def _norm(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _context_item_ref(item: dict[str, Any]) -> str:
    return str(item.get("unit_id") or item.get("source_path") or item.get("source_recap_path") or "unknown")


def _rendered_section_for_ref(rendered: dict[str, Any], ref: str) -> str | None:
    for section in rendered.get("sections") or []:
        if not isinstance(section, dict):
            continue
        refs = [str(r) for r in (section.get("refs") or [])]
        if ref in refs:
            return str(section.get("section_id") or section.get("title") or "")
    return None


def _admission_rejection_for_rank(
    *,
    candidate_rank: int | None,
    admission_decision_diagnostics: dict[str, Any] | None,
    visibility_excluded: bool,
) -> str:
    if visibility_excluded:
        return "visibility_excluded"
    if candidate_rank is None:
        return "not_matched"
    if not admission_decision_diagnostics:
        return "not_admittable"
    for attempt in admission_decision_diagnostics.get("attempts") or []:
        if int(attempt.get("candidate_rank") or -1) != candidate_rank:
            continue
        if attempt.get("admitted"):
            return "admitted"
        return str(attempt.get("reason") or "not_admitted")
    return "outside_candidate_depth"


def _lane_rejection_for_item(
    *,
    item: dict[str, Any],
    group: dict[str, Any],
    rendered_packet: dict[str, Any],
) -> str | None:
    ok, diag = context_item_satisfies_lane_aware_group(
        item,
        group=group,
        rendered_context_packet=rendered_packet,
    )
    if ok:
        return None
    return str(diag.get("reason") or "lane_rejected")


def _candidate_rank_for_item(*, enumerate_rank: int, item: dict[str, Any]) -> int:
    stored = item.get("candidate_rank")
    if stored is not None:
        return int(stored)
    return enumerate_rank


def _build_match_surface(
    *,
    rank: int | None,
    item: dict[str, Any] | None,
    admission_diag: dict[str, Any] | None = None,
    lane_rejection: str | None = None,
    rendered_section: str | None = None,
) -> dict[str, Any] | None:
    if item is None or rank is None:
        return None
    candidate_rank = _candidate_rank_for_item(enumerate_rank=rank, item=item)
    visibility_excluded = not is_planner_visible_for_c1s4_preplanning(item)
    return {
        "candidate_rank": candidate_rank,
        "admitted_rank": rank if item.get("candidate_rank") is not None else None,
        "ref": _context_item_ref(item),
        "source_kind": item.get("source_kind"),
        "subject_class": infer_context_subject_class(item),
        "presentation_lane": item.get("presentation_lane"),
        "evidence_role": item.get("evidence_role"),
        "admittable": is_admittable_planner_evidence(item),
        "visibility_excluded": visibility_excluded,
        "admission_reason": _admission_rejection_for_rank(
            candidate_rank=candidate_rank,
            admission_decision_diagnostics=admission_diag,
            visibility_excluded=visibility_excluded,
        ),
        "lane_rejection_reason": lane_rejection,
        "rendered_section": rendered_section,
    }


def _first_matching_surface(
    items: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    *,
    admission_diag: dict[str, Any] | None = None,
    group: dict[str, Any] | None = None,
    rendered_packet: dict[str, Any] | None = None,
    require_rendered: bool = False,
) -> dict[str, Any] | None:
    for idx, item in enumerate(items, start=1):
        if not predicate(item):
            continue
        lane_rejection = None
        if group is not None and rendered_packet is not None:
            lane_rejection = _lane_rejection_for_item(item=item, group=group, rendered_packet=rendered_packet)
        rendered_section = None
        if rendered_packet is not None:
            rendered_section = _rendered_section_for_ref(rendered_packet, _context_item_ref(item))
        if require_rendered and rendered_section is None:
            continue
        return _build_match_surface(
            rank=idx,
            item=item,
            admission_diag=admission_diag,
            lane_rejection=lane_rejection,
            rendered_section=rendered_section,
        )
    return None


def _is_navigation_alias_or_keyword_record(item: dict[str, Any]) -> bool:
    ref = _context_item_ref(item).lower()
    if any(token in ref for token in ("retrieval-keywords", "retrieval_keywords", ":alias:", "cross_reference")):
        return True
    role = str(item.get("evidence_role") or "").lower()
    if role in NON_ADMITTABLE_EVIDENCE_ROLES:
        return True
    return is_navigation_only_context(item)


def _is_session_recap_or_memory(item: dict[str, Any]) -> bool:
    source_kind = str(item.get("source_kind") or "").lower()
    subject_class = infer_context_subject_class(item)
    if source_kind in {"session_recap", "session_memory"}:
        return True
    return subject_class == "session_memory"


def _lane_accepted_surface(
    *,
    accepted_matches: list[dict[str, Any]],
    items: list[dict[str, Any]],
    admission_diag: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not accepted_matches:
        return None
    accepted_ref = str(accepted_matches[0].get("ref") or "")
    if not accepted_ref:
        return None
    for idx, item in enumerate(items, start=1):
        if _context_item_ref(item) != accepted_ref:
            continue
        return _build_match_surface(
            rank=idx,
            item=item,
            admission_diag=admission_diag,
            lane_rejection=None,
            rendered_section=str(accepted_matches[0].get("rendered_section") or "") or None,
        )
    return {
        "candidate_rank": None,
        "ref": accepted_ref,
        "source_kind": accepted_matches[0].get("source_kind"),
        "subject_class": accepted_matches[0].get("subject_class"),
        "presentation_lane": None,
        "evidence_role": None,
        "admittable": True,
        "visibility_excluded": False,
        "admission_reason": "lane_accepted",
        "lane_rejection_reason": None,
        "rendered_section": accepted_matches[0].get("rendered_section"),
    }


def _miss_root_cause_from_lineage(
    *,
    lineage: dict[str, Any | None],
    lane_aware_accepted: bool,
    legacy_match: bool,
) -> str:
    raw = lineage.get("first_raw_match")
    admittable = lineage.get("first_admittable_match")
    admitted = lineage.get("first_admitted_match")
    rendered = lineage.get("first_rendered_match")
    lane_accepted = lineage.get("first_lane_accepted_match")

    if raw and raw.get("visibility_excluded"):
        return "visibility_exclusion"
    if raw is None:
        return "retrieval_rank"
    if admittable is None:
        reason = str(raw.get("admission_reason") or "")
        if reason in {"not_admittable_planner_evidence", "prior_only_support_suppressed"}:
            return "source_kind_mismatch"
        if _is_navigation_alias_or_keyword_record({"unit_id": raw.get("ref"), "evidence_role": raw.get("evidence_role")}):
            return "source_kind_mismatch"
        return "retrieval_rank"
    if admitted is None:
        reason = str(admittable.get("admission_reason") or "")
        if reason in {"lane_remaining_too_small", "lane_max_exhausted", "total_spillover_exhausted", "no_lane_state"}:
            return "lane_budget"
        if reason in {"not_admittable_planner_evidence", "prior_only_support_suppressed"}:
            return "source_kind_mismatch"
        return "admission_budget"
    if rendered is None:
        return "render"
    if not lane_aware_accepted or lane_accepted is None:
        return "strict_gold_lane_mismatch"
    if not legacy_match:
        return "strict_gold_lane_mismatch"
    return "ok"


def build_required_group_row(
    *,
    packet: dict[str, Any],
    gold_question: dict[str, Any],
    mode: str,
    group: dict[str, Any],
) -> dict[str, Any]:
    qn = int(packet.get("question_number") or 0)
    group_id = str(group.get("group_id") or "")
    match_spec = group.get("match") or {}
    candidates = packet.get("candidate_context") or []
    admitted = packet.get("admitted_context") or []
    admission_diag = packet.get("admission_decision_diagnostics") or {}

    rendered_packet = render_context_packet(packet)
    grade = grade_question_packet(packet=packet, gold_question=gold_question, retrieval_mode=mode, top_k=9)  # type: ignore[arg-type]
    lane_results = (grade.get("lane_aware_diagnostics") or {}).get("required_group_results") or []
    lane_row = next((r for r in lane_results if r.get("group_id") == group_id), {})
    lane_aware_accepted = bool(lane_row.get("ok"))
    accepted_matches = list(lane_row.get("accepted_matches") or [])
    rejected_matches = list(lane_row.get("rejected_matches") or [])

    def matches_group(item: dict[str, Any]) -> bool:
        return match_context_item(item, match_spec)

    def admittable_match(item: dict[str, Any]) -> bool:
        return matches_group(item) and is_admittable_planner_evidence(item)

    def lane_compatible_match(item: dict[str, Any]) -> bool:
        if not matches_group(item):
            return False
        ok, _ = context_item_satisfies_lane_aware_group(
            item,
            group=group,
            rendered_context_packet=rendered_packet,
        )
        return ok

    cand_matches = [item for item in candidates if matches_group(item)]

    first_raw = _first_matching_surface(candidates, matches_group, admission_diag=admission_diag)
    first_admittable = _first_matching_surface(candidates, admittable_match, admission_diag=admission_diag)
    first_lane_compatible = _first_matching_surface(
        candidates,
        lane_compatible_match,
        admission_diag=admission_diag,
        group=group,
        rendered_packet=rendered_packet,
    )
    first_admitted = _first_matching_surface(admitted, matches_group, admission_diag=admission_diag)
    first_rendered = _first_matching_surface(
        admitted,
        matches_group,
        admission_diag=admission_diag,
        group=group,
        rendered_packet=rendered_packet,
        require_rendered=True,
    )
    first_lane_accepted = _lane_accepted_surface(
        accepted_matches=accepted_matches,
        items=admitted,
        admission_diag=admission_diag,
    )

    admitted_flag = first_admitted is not None
    admission_reason = None
    if first_admitted is not None:
        admission_reason = str(first_admitted.get("admission_reason") or "")
    elif first_admittable is not None:
        admission_reason = str(first_admittable.get("admission_reason") or "not_admitted")
    elif first_raw is not None:
        admission_reason = str(first_raw.get("admission_reason") or "not_matched")

    lane_rejection = None
    if not lane_aware_accepted:
        for rejected in rejected_matches:
            lane_rejection = str(rejected.get("reason") or "")
            if lane_rejection:
                break
        if lane_rejection is None and first_lane_compatible is None and first_admittable is not None:
            lane_rejection = str(first_admittable.get("lane_rejection_reason") or "")

    legacy_matches = [m for m in (grade.get("matched_groups") or []) if m.get("group_id") == group_id]
    legacy_match = bool(legacy_matches and legacy_matches[0].get("ok"))

    lineage = {
        "first_raw_match": first_raw,
        "first_admittable_match": first_admittable,
        "first_lane_compatible_match": first_lane_compatible,
        "first_admitted_match": first_admitted,
        "first_rendered_match": first_rendered,
        "first_lane_accepted_match": first_lane_accepted,
    }

    rendered_section = None
    if first_rendered is not None:
        rendered_section = first_rendered.get("rendered_section")

    return {
        "schema": ROW_SCHEMA,
        "question_number": qn,
        "question_id": packet.get("question_id"),
        "mode": mode,
        "group_id": group_id,
        "required_lane": group.get("required_lane"),
        "expected_rendered_section": group.get("expected_rendered_section"),
        "lineage": lineage,
        "match_surface": {
            "candidate_match_count": len(cand_matches),
            "first_raw_rank": (first_raw or {}).get("candidate_rank"),
            "first_raw_ref": (first_raw or {}).get("ref"),
            "first_raw_source_kind": (first_raw or {}).get("source_kind"),
            "visibility_excluded": bool((first_raw or {}).get("visibility_excluded")),
        },
        "admission_surface": {
            "admitted": admitted_flag,
            "first_admitted_rank": (first_admitted or {}).get("candidate_rank"),
            "first_admitted_ref": (first_admitted or {}).get("ref"),
            "admission_rejection_reason": admission_reason,
            "admission_policy": packet.get("admission_policy"),
        },
        "render_surface": {
            "rendered": first_rendered is not None,
            "rendered_section": rendered_section,
            "first_rendered_ref": (first_rendered or {}).get("ref"),
        },
        "grading_surface": {
            "legacy_match": legacy_match,
            "lane_aware_accepted": lane_aware_accepted,
            "lane_aware_rejection_reason": lane_rejection if not lane_aware_accepted else None,
            "grading_context_kind": grade.get("grading_context_kind"),
            "effective_grading_surface": grade.get("grading_surface_labels", {}).get("effective_grading_surface"),
        },
        "miss_root_cause": _miss_root_cause_from_lineage(
            lineage=lineage,
            lane_aware_accepted=lane_aware_accepted,
            legacy_match=legacy_match,
        ),
    }


def _variant_first_text_match(
    *,
    query_variant_diagnostics: dict[str, Any] | None,
    variant_roles: set[str],
) -> dict[str, Any] | None:
    if not query_variant_diagnostics:
        return None
    best: tuple[int, dict[str, Any], dict[str, Any]] | None = None
    for entry in query_variant_diagnostics.get("variant_hit_counts") or []:
        role = str(entry.get("variant_role") or "")
        if role not in variant_roles:
            continue
        for idx, hit in enumerate(entry.get("hits") or [], start=1):
            if not match_context_item(hit, Q3_DISTANCE_MATCH):
                continue
            if best is None or idx < best[0]:
                best = (idx, hit, entry)
    if best is None:
        return None
    rank, hit, entry = best
    return {
        "variant_rank": rank,
        "variant_role": entry.get("variant_role"),
        "query": entry.get("query"),
        "ref": _context_item_ref(hit),
        "source_kind": hit.get("source_kind"),
        "subject_class": infer_context_subject_class(hit),
    }


def _q3_failure_stage(*, lineage: dict[str, Any | None]) -> str:
    session_evidence = lineage.get("first_session_memory_or_recap_match")
    admitted_lane = lineage.get("first_admitted_required_lane_match")
    rendered_lane = lineage.get("first_rendered_required_lane_match")
    lane_accepted = lineage.get("first_lane_accepted_match")

    if session_evidence is None:
        if lineage.get("first_raw_text_match") is None:
            return "retrieval"
        return "no_session_evidence"
    if admitted_lane is None:
        return "admission"
    if rendered_lane is None:
        return "render"
    if lane_accepted is None:
        return "grading"
    return "ok"


def build_q3_prior_distance_probe(*, packet: dict[str, Any], query_variant_diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    candidates = packet.get("candidate_context") or []
    admitted = packet.get("admitted_context") or []
    admission_diag = packet.get("admission_decision_diagnostics") or {}
    rendered_packet = render_context_packet(packet)
    group = Q3_DISTANCE_GOLD_GROUP

    grade = grade_question_packet(
        packet=packet,
        gold_question={"expectations_by_mode": {str(packet.get("retrieval_mode")): {"required_context_groups": [group]}}},
        retrieval_mode=str(packet.get("retrieval_mode")),  # type: ignore[arg-type]
        top_k=9,
    )
    lane_results = (grade.get("lane_aware_diagnostics") or {}).get("required_group_results") or []
    lane_row = next((r for r in lane_results if r.get("group_id") == Q3_DISTANCE_GROUP_ID), {})

    def text_match(item: dict[str, Any]) -> bool:
        return match_context_item(item, Q3_DISTANCE_MATCH)

    def admittable_text_match(item: dict[str, Any]) -> bool:
        return text_match(item) and is_admittable_planner_evidence(item) and not _is_navigation_alias_or_keyword_record(item)

    def session_memory_text_match(item: dict[str, Any]) -> bool:
        return admittable_text_match(item) and _is_session_recap_or_memory(item)

    def required_lane_match(item: dict[str, Any]) -> bool:
        if not session_memory_text_match(item):
            return False
        ok, _ = context_item_satisfies_lane_aware_group(item, group=group, rendered_context_packet=rendered_packet)
        return ok

    lineage = {
        "first_raw_text_match": _first_matching_surface(candidates, text_match, admission_diag=admission_diag),
        "first_admittable_text_match": _first_matching_surface(candidates, admittable_text_match, admission_diag=admission_diag),
        "first_session_memory_or_recap_match": _first_matching_surface(
            candidates,
            session_memory_text_match,
            admission_diag=admission_diag,
            group=group,
            rendered_packet=rendered_packet,
        ),
        "first_required_lane_compatible_match": _first_matching_surface(
            candidates,
            required_lane_match,
            admission_diag=admission_diag,
            group=group,
            rendered_packet=rendered_packet,
        ),
        "first_admitted_required_lane_match": _first_matching_surface(
            admitted,
            required_lane_match,
            admission_diag=admission_diag,
            group=group,
            rendered_packet=rendered_packet,
        ),
        "first_rendered_required_lane_match": _first_matching_surface(
            admitted,
            required_lane_match,
            admission_diag=admission_diag,
            group=group,
            rendered_packet=rendered_packet,
            require_rendered=True,
        ),
        "first_lane_accepted_match": _lane_accepted_surface(
            accepted_matches=list(lane_row.get("accepted_matches") or []),
            items=admitted,
            admission_diag=admission_diag,
        ),
    }

    literal_match = _variant_first_text_match(
        query_variant_diagnostics=query_variant_diagnostics,
        variant_roles={"literal_question"},
    )
    alias_match = _variant_first_text_match(
        query_variant_diagnostics=query_variant_diagnostics,
        variant_roles={"route_distance_alias", "npc_target_alias", "support_alias", "planner_affordance"},
    )

    meaningful = lineage.get("first_session_memory_or_recap_match") or lineage.get("first_admitted_required_lane_match")
    snippet_item = None
    if meaningful and isinstance(meaningful, dict):
        ref = str(meaningful.get("ref") or "")
        for item in admitted + candidates:
            if _context_item_ref(item) == ref:
                snippet_item = item
                break

    failure_stage = _q3_failure_stage(lineage=lineage)

    return {
        "schema": "dmb_pr67_q3_prior_distance_probe_v2",
        "lineage": lineage,
        "variant_literal_first_match": literal_match,
        "variant_route_alias_first_match": alias_match,
        "failure_stage": failure_stage,
        "first_meaningful_ref": (meaningful or {}).get("ref") if meaningful else None,
        "first_meaningful_snippet": render_context_item_for_budget(snippet_item)[:240] if snippet_item else None,
    }


def build_pr67_required_group_diagnostics(*, max_hits: int = 50) -> dict[str, Any]:
    gold = load_expected_context_gold()
    gold_by_q = {int(q["question_number"]): q for q in gold.get("questions", []) if q.get("question_number") is not None}
    rows: list[dict[str, Any]] = []
    q3_probes: dict[str, Any] = {}

    for mode in RETRIEVAL_MODES:
        summary = build_summary(mode=mode, max_hits=max_hits)  # type: ignore[arg-type]
        for packet in summary.get("packets") or []:
            qn = int(packet.get("question_number") or 0)
            gold_q = gold_by_q.get(qn)
            if gold_q is None:
                continue
            exp = (gold_q.get("expectations_by_mode") or {}).get(mode) or {}
            for group in exp.get("required_context_groups") or []:
                rows.append(build_required_group_row(packet=packet, gold_question=gold_q, mode=mode, group=group))
            if qn == 3:
                q3_probes[mode] = build_q3_prior_distance_probe(
                    packet=packet,
                    query_variant_diagnostics=packet.get("query_variant_diagnostics"),
                )

    tier_a_rows = [r for r in rows if int(r.get("question_number") or 0) in TIER_A_QUESTIONS]
    miss_causes: dict[str, int] = {}
    for row in tier_a_rows:
        if row.get("grading_surface", {}).get("lane_aware_accepted"):
            continue
        cause = str(row.get("miss_root_cause") or "unknown")
        miss_causes[cause] = miss_causes.get(cause, 0) + 1

    return {
        "schema": DIAGNOSTICS_SCHEMA,
        "tier_a_questions": sorted(TIER_A_QUESTIONS),
        "row_count": len(rows),
        "tier_a_row_count": len(tier_a_rows),
        "tier_a_miss_root_causes": miss_causes,
        "q3_prior_distance_probe_by_mode": q3_probes,
        "rows": rows,
    }
