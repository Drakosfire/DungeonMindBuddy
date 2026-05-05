"""Unit tests for the planner retrieval router (no LLM, no API)."""

from __future__ import annotations

from typing import Any

from src.agent.planner_retrieval_router import (
    DECISION_ANSWER_NOW,
    DECISION_NEED_MORE_CONTEXT,
    REASON_INSUFFICIENT_CONTEXT_DENSITY,
    REASON_INSUFFICIENT_HITS,
    REASON_INSUFFICIENT_MATCHED_RECORDS,
    REASON_LOW_TOP_HIT_STRENGTH,
    REASON_MISSING_ROUTE_ANCHOR,
    REASON_NO_MATCHED_RECORDS,
    ROUTER_DECISION_SCHEMA_V1,
    RetrievalDecisionResult,
    RetrievalEvidence,
    SufficiencyConfig,
    evaluate_sufficiency,
    run_retrieval_first_decision,
)


def _record(
    *,
    unit_id: str,
    routes: list[str],
    lexical: str,
    session_number: int = 20,
    campaign_id: str = "longmont-c2",
    line_start: int = 1,
    line_end: int = 1,
    source_recap_path: str = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
) -> dict[str, Any]:
    return {
        "schema": "dmb_session_memory_record_v1",
        "campaign_id": campaign_id,
        "session_number": session_number,
        "unit_id": unit_id,
        "lexical_plain": lexical,
        "line_start": line_start,
        "line_end": line_end,
        "source_recap_path": source_recap_path,
        "routes": [{"normalized_route": r} for r in routes],
    }


def _dense_records() -> list[dict[str, Any]]:
    """Index seeded with several records that lex-match a single query well."""
    return [
        _record(
            unit_id="r-tower-1",
            routes=["NPCs/captain_lysandra_ironveil/timeline"],
            lexical="The captain saw the tower drawing in dirt and tea was brewed.",
            line_start=10,
        ),
        _record(
            unit_id="r-tower-2",
            routes=["NPCs/captain_lysandra_ironveil/timeline"],
            lexical="Lysandra and the tower voices remained tied to a forest beat.",
            line_start=11,
        ),
        _record(
            unit_id="r-tower-3",
            routes=["NPCs/captain_lysandra_ironveil/dossier"],
            lexical="Captain Lysandra's tower drawing detail and dirt blueprint.",
            line_start=12,
        ),
        _record(
            unit_id="r-other",
            routes=["NPCs/sara_mirathorn_operator/timeline"],
            lexical="Sara relayed messages but no tower drawings were shared.",
            line_start=20,
        ),
    ]


def _sparse_records() -> list[dict[str, Any]]:
    """Index where a query produces zero or one weak hit."""
    return [
        _record(
            unit_id="r-other-1",
            routes=["Locations/mossford"],
            lexical="Bridge inspection chatter at Mossford with no tower mention.",
        ),
        _record(
            unit_id="r-other-2",
            routes=["Locations/mossford"],
            lexical="Caelynn watered horses near the wagon yard.",
        ),
    ]


def test_run_retrieval_first_decision_answers_now_on_dense_index():
    res = run_retrieval_first_decision(
        query="captain tower drawing tea",
        records=_dense_records(),
        campaign_id="longmont-c2",
        query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
    )
    assert isinstance(res, RetrievalDecisionResult)
    assert res.schema == ROUTER_DECISION_SCHEMA_V1
    assert res.decision == DECISION_ANSWER_NOW, res.failure_reasons
    assert res.escalation is None
    assert res.evidence.matched_records >= 2
    assert res.evidence.returned_hits >= 3
    assert res.evidence.top_hit_score >= 3
    assert res.failure_reasons == []


def test_run_retrieval_first_decision_escalates_with_no_matches():
    res = run_retrieval_first_decision(
        query="zeppelin antenna circuit board",
        records=_sparse_records(),
        campaign_id="longmont-c2",
        query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
    )
    assert res.decision == DECISION_NEED_MORE_CONTEXT
    assert res.escalation is not None
    assert REASON_NO_MATCHED_RECORDS in res.failure_reasons
    assert REASON_INSUFFICIENT_HITS in res.failure_reasons
    assert REASON_LOW_TOP_HIT_STRENGTH in res.failure_reasons


def test_run_retrieval_first_decision_escalates_when_route_anchor_missing():
    res = run_retrieval_first_decision(
        query="captain tower drawing tea",
        records=_dense_records(),
        campaign_id="longmont-c2",
        query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
        required_route_anchors=["NPCs/professor_tealeaf"],
    )
    assert res.decision == DECISION_NEED_MORE_CONTEXT
    assert REASON_MISSING_ROUTE_ANCHOR in res.failure_reasons
    assert res.escalation is not None
    missing = res.escalation.missing_signals.get("route_anchors") or {}
    assert "NPCs/professor_tealeaf" in (missing.get("missing") or [])


def test_run_retrieval_first_decision_decision_serializes_to_json_dict():
    res = run_retrieval_first_decision(
        query="captain tower drawing tea",
        records=_dense_records(),
        campaign_id="longmont-c2",
        query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
    )
    payload = res.as_json_dict()
    assert payload["schema"] == ROUTER_DECISION_SCHEMA_V1
    assert payload["decision"] in (DECISION_ANSWER_NOW, DECISION_NEED_MORE_CONTEXT)
    assert "evidence" in payload and "trace" in payload["evidence"]
    assert "confidence_features" in payload
    cf = payload["confidence_features"]
    assert "top_hit_score" in cf
    assert "context_density" in cf
    assert isinstance(cf["query_tokens"], list)


def test_evaluate_sufficiency_emits_each_reason_in_isolation():
    base_evidence = RetrievalEvidence(
        hits=[],
        trace={},
        top_hit_score=5,
        matched_records=10,
        returned_hits=8,
        route_anchor_recall=1.0,
        context_density=1.0,
        why_matched_tokens=["a"],
        expansion_fill_ratio=0.0,
    )

    cfg_strict_density = SufficiencyConfig(min_context_density=0.99)
    reasons, _ = evaluate_sufficiency(
        evidence=RetrievalEvidence(
            **{**base_evidence.__dict__, "context_density": 0.1}
        ),
        config=cfg_strict_density,
    )
    assert reasons == [REASON_INSUFFICIENT_CONTEXT_DENSITY]

    cfg = SufficiencyConfig()
    reasons, _ = evaluate_sufficiency(
        evidence=RetrievalEvidence(
            **{**base_evidence.__dict__, "matched_records": 1}
        ),
        config=cfg,
    )
    assert REASON_INSUFFICIENT_MATCHED_RECORDS in reasons

    reasons, _ = evaluate_sufficiency(
        evidence=RetrievalEvidence(
            **{**base_evidence.__dict__, "matched_records": 0}
        ),
        config=cfg,
    )
    assert REASON_NO_MATCHED_RECORDS in reasons
    assert REASON_INSUFFICIENT_MATCHED_RECORDS not in reasons


def test_evaluate_sufficiency_passes_with_all_signals_strong():
    cfg = SufficiencyConfig()
    evidence = RetrievalEvidence(
        hits=[{"routes": [{"normalized_route": "NPCs/captain_lysandra_ironveil"}]}],
        trace={"query_tokens": ["captain", "tower"]},
        top_hit_score=9,
        matched_records=5,
        returned_hits=6,
        route_anchor_recall=1.0,
        context_density=0.9,
        why_matched_tokens=["captain", "tower"],
        expansion_fill_ratio=0.0,
    )
    reasons, missing = evaluate_sufficiency(
        evidence=evidence,
        config=cfg,
        required_route_anchors=["NPCs/captain_lysandra_ironveil"],
        missing_route_anchors=[],
    )
    assert reasons == []
    assert missing == {}


def test_run_retrieval_first_decision_rejects_blank_query():
    try:
        run_retrieval_first_decision(
            query="   ",
            records=_dense_records(),
            campaign_id="longmont-c2",
        )
    except ValueError as exc:
        assert "query is required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("blank query did not raise ValueError")


def test_router_controller_answer_now_emits_planner_envelope_json():
    """Controller wraps a stub-synth answer into the strict planner envelope."""
    import json as _json

    from src.agent.planner import (
        RouterControlledTurnDetail,
        run_planning_turn_with_retrieval_router,
    )

    captured: dict[str, str] = {}

    def stub_synth(question: str, hit_context: str) -> tuple[str, float, dict[str, int]]:
        captured["question"] = question
        captured["hit_context"] = hit_context
        return ("Captain Lysandra drew the tower in dirt.", 0.0023, {"input_tokens": 10, "output_tokens": 5})

    out = run_planning_turn_with_retrieval_router(
        user_line="captain tower drawing tea",
        session_memory_records=_dense_records(),
        campaign_id="longmont-c2",
        query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
        answer_now_synth=stub_synth,
    )
    assert isinstance(out, RouterControlledTurnDetail)
    assert out.escalated is False
    assert out.planner_detail is None
    assert out.decision["decision"] == "answer_now"
    assert out.answer_now_cost_usd == 0.0023
    payload = _json.loads(out.final_text)
    assert payload["user_intent"] == "factual_lookup"
    assert payload["unsure_queue"] is None
    assert "tower" in payload["message"].lower()
    assert captured["question"] == "captain tower drawing tea"
    assert "tower" in captured["hit_context"].lower()
    tc = out.telemetry_cost
    assert tc["escalated"] is False
    assert tc["router_decision"] == "answer_now"
    assert abs(tc["scenario_estimated_cost_usd"] - 0.0023) < 1e-9


def test_router_controller_escalation_invokes_run_planning_turn_detailed():
    """When the router escalates, the controller forwards to run_planning_turn_detailed."""
    from src.agent import planner as planner_mod
    from src.agent.planner import (
        RouterControlledTurnDetail,
        run_planning_turn_with_retrieval_router,
    )

    forwarded: dict[str, Any] = {}

    class FakeDetail:
        def __init__(self) -> None:
            self.final_text = '{"user_intent": "factual_lookup", "message": "planner ran", "unsure_queue": null}'
            self.tool_trace: list[dict[str, Any]] = []
            self.telemetry_cost = {
                "planner_estimated_cost_usd": 0.0123,
                "statblock_tool_estimated_cost_usd": 0.0,
            }
            self.hit_tool_round_limit = False

    def fake_run_planning_turn_detailed(**kwargs: Any) -> Any:
        forwarded.update(kwargs)
        return FakeDetail()

    original = planner_mod.run_planning_turn_detailed
    planner_mod.run_planning_turn_detailed = fake_run_planning_turn_detailed  # type: ignore[assignment]
    try:
        out = run_planning_turn_with_retrieval_router(
            user_line="zeppelin antenna circuit board",
            session_memory_records=_sparse_records(),
            campaign_id="longmont-c2",
            query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
            escalate_kwargs={
                "client": object(),
                "model_id": "stub-model",
                "instructions": "stub-instructions",
                "tools": [],
                "corpus_path": __import__("pathlib").Path("/tmp/stub-corpus"),
                "previous_response_id": None,
                "dispatch_tool": (lambda name, raw: "{}"),
            },
        )
    finally:
        planner_mod.run_planning_turn_detailed = original  # type: ignore[assignment]

    assert isinstance(out, RouterControlledTurnDetail)
    assert out.escalated is True
    assert out.planner_detail is not None
    assert out.decision["decision"] == "need_more_context"
    assert "router_failure_reasons" in out.telemetry_cost
    assert out.telemetry_cost["escalated"] is True
    assert out.telemetry_cost["planner_estimated_cost_usd"] == 0.0123
    assert forwarded["user_line"] == "zeppelin antenna circuit board"
    assert forwarded["telemetry_context"]["router_decision"] == "need_more_context"
    assert forwarded["telemetry_context"]["router_failure_reasons"] == out.decision["failure_reasons"]


def test_router_controller_requires_synth_or_escalate_kwargs():
    from src.agent.planner import run_planning_turn_with_retrieval_router

    try:
        run_planning_turn_with_retrieval_router(
            user_line="captain tower drawing tea",
            session_memory_records=_dense_records(),
            campaign_id="longmont-c2",
            query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
        )
    except ValueError as exc:
        assert "answer_now_synth" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing answer_now_synth did not raise")

    try:
        run_planning_turn_with_retrieval_router(
            user_line="zeppelin antenna circuit board",
            session_memory_records=_sparse_records(),
            campaign_id="longmont-c2",
            query_spec={"max_hits": 6, "session_min": 20, "session_max": 20},
        )
    except ValueError as exc:
        assert "escalate_kwargs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing escalate_kwargs did not raise")
