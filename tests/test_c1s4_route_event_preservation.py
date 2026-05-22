from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.admission_preservation import (
    _best_prior_route_event_candidate,
    _is_prior_route_event_candidate,
    apply_admission_preservation,
)
from evals.c1s4_preplanning_vertical_slice.context_admission import estimate_context_item_size
from evals.c1s4_preplanning_vertical_slice.query_lane_router import build_lane_plan


def test_prior_route_event_candidate_prefers_session_recap_with_mirathorn_week() -> None:
    question = "How far away is Mirathorn at this point?"
    recap = {
        "unit_id": "corpus:session_recap:s3",
        "source_kind": "session_recap",
        "snippet": "Mirathorn is about a week away on the road from Stone Bridge.",
        "title": "Session 3 recap",
    }
    hub = {
        "unit_id": "corpus:location:stone_bridge:hub",
        "source_kind": "location_hub",
        "snippet": "Stone Bridge sits near Mirathorn travel routes.",
        "title": "Stone Bridge hub",
    }
    candidates = [hub, recap]
    assert not _is_prior_route_event_candidate(hub, question)
    assert _is_prior_route_event_candidate(recap, question)
    pick = _best_prior_route_event_candidate(candidates, question_text=question, admitted_ranks=set())
    assert pick is not None
    assert pick[0] == 2


def test_route_event_preservation_selects_session_evidence_over_location_hub() -> None:
    question = "How far away is Mirathorn at this point?"
    lane_plan = build_lane_plan(question_text=question, retrieval_mode="prior_only", candidate_depth=10, total_budget_chars=8000)
    lane_state = {ln: {**cfg, "remaining": int(cfg.get("target_chars", 0))} for ln, cfg in (lane_plan.get("lanes") or {}).items()}
    candidates = [
        {
            "unit_id": "corpus:location:stone_bridge:canon-summary",
            "source_kind": "location_hub",
            "snippet": "Stone Bridge and Mirathorn are linked by old roads.",
            "title": "Stone Bridge",
        },
        {
            "unit_id": "corpus:session_recap:s3-travel",
            "source_kind": "session_recap",
            "snippet": "From Stone Bridge, Mirathorn is roughly a week on foot.",
            "title": "Travel notes",
        },
    ]
    preserved, diag = apply_admission_preservation(
        question_text=question,
        retrieval_mode="prior_only",
        candidates=candidates,
        lane_plan=lane_plan,
        lane_state=lane_state,
        total_budget_chars=8000,
        estimate_size=estimate_context_item_size,
    )
    preserved_ids = {p.get("unit_id") for p in preserved}
    assert "corpus:session_recap:s3-travel" in preserved_ids
    groups = [g.get("group_id") for g in (diag.get("preservation_plan") or {}).get("preserve_groups") or []]
    assert "prior_campaign_route_event" in groups
