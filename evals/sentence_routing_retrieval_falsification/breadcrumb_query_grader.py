"""Deterministic grading helpers for session-memory query recall (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import (
    build_hit_context_text,
    classify_answer,
    classify_answer_semantic,
    classify_failure_surface,
    index_records_by_unit_id,
    score_context_support,
)
from src.agent.session_memory_query import CandidateQueryResult, query_session_memory_candidate

_GOLD_SCHEMAS = frozenset(
    {
        "dmb_breadcrumb_query_gold_v1",
        "dmb_breadcrumb_query_natural_gold_v1",
    }
)


def load_gold(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sch = str(data.get("schema", ""))
    if sch not in _GOLD_SCHEMAS:
        raise ValueError(f"unexpected gold schema {sch!r} in {path}; expected one of {_GOLD_SCHEMAS}")
    return data


def hits_cover_expected_units(hits: list[dict[str, Any]], expected_substrings: list[str]) -> bool:
    """Every expected substring must appear in at least one hit's ``unit_id``."""
    uids = [str(h.get("unit_id", "")) for h in hits]
    for sub in expected_substrings:
        if not any(sub in uid for uid in uids):
            return False
    return True


def hits_cover_expected_routes(hits: list[dict[str, Any]], expected_route_substrings: list[str]) -> bool:
    """Each expected substring must appear in some hit route's ``normalized_route``."""
    routes: list[str] = []
    for h in hits:
        for r in h.get("routes") or []:
            routes.append(str(r.get("normalized_route", "")).lower())
    blob = "\n".join(routes)
    for sub in expected_route_substrings:
        if sub.lower() not in blob:
            return False
    return True


def _int_from_spec(qspec: dict[str, Any], key: str, default: int) -> int:
    raw = qspec.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def query_session_memory_for_scenario(
    *, records: list[dict[str, Any]], scenario: dict[str, Any]
) -> CandidateQueryResult:
    """Run ``query_session_memory_candidate`` using merged ``scenario['query_spec']``."""
    qspec = scenario.get("query_spec") or {}
    return query_session_memory_candidate(
        records=records,
        query=str(qspec.get("query", "")),
        campaign_id=str(scenario.get("campaign_id", "")),
        subject_route=qspec.get("subject_route"),
        session_min=qspec.get("session_min"),
        session_max=qspec.get("session_max"),
        subject_types=qspec.get("subject_types"),
        proposed_only=bool(qspec.get("proposed_only", False)),
        max_hits=_int_from_spec(qspec, "max_hits", 12),
        expand_context=bool(qspec.get("expand_context", False)),
        expand_seed_hits=_int_from_spec(qspec, "expand_seed_hits", 5),
        expand_adjacent_window=_int_from_spec(qspec, "expand_adjacent_window", 2),
        expand_shared_route_limit=_int_from_spec(qspec, "expand_shared_route_limit", 3),
        expand_route_family_limit=_int_from_spec(qspec, "expand_route_family_limit", 3),
        expand_first_pass_cap=(
            int(qspec["expand_first_pass_cap"])
            if ("expand_first_pass_cap" in qspec and qspec["expand_first_pass_cap"] is not None)
            else None
        ),
        expansion_allocation_mode=str(qspec.get("expansion_allocation_mode", "round_robin")),
        tokenizer_mode=str(qspec.get("tokenizer_mode", "default")),
        query_token_aliases=(
            [str(x) for x in qspec.get("query_token_aliases", [])]
            if isinstance(qspec.get("query_token_aliases"), list)
            else None
        ),
    )


def grade_scenario(*, records: list[dict[str, Any]], scenario: dict[str, Any]) -> dict[str, Any]:
    """Run the scenario's query args and return pass/fail + evidence."""
    result = query_session_memory_for_scenario(records=records, scenario=scenario)
    hits = result.hits
    violations: list[str] = []

    exp_units = scenario.get("expect_unit_id_substrings") or []
    if exp_units and not hits_cover_expected_units(hits, [str(x) for x in exp_units]):
        violations.append("missing_expected_unit_id_hit")

    exp_routes = scenario.get("expect_route_substrings") or []
    if exp_routes and not hits_cover_expected_routes(hits, [str(x) for x in exp_routes]):
        violations.append("missing_expected_route_hit")

    min_score = scenario.get("min_top_hit_score")
    if min_score is not None and hits:
        if int(hits[0].get("score", 0)) < int(min_score):
            violations.append("top_hit_score_below_threshold")

    ok = not violations
    return {
        "scenario_id": scenario.get("id"),
        "ok": ok,
        "violations": violations,
        "hit_count": len(hits),
        "top_hit": hits[0] if hits else None,
        "full_result": result.as_json_dict(),
    }


def natural_retrieval_bundle(
    *, records: list[dict[str, Any]], scenario: dict[str, Any]
) -> tuple[CandidateQueryResult, str]:
    """Run session-memory query for a prepared scenario and return hits + harness-only hit context text."""
    result = query_session_memory_for_scenario(records=records, scenario=scenario)
    by_unit = index_records_by_unit_id(records)
    hit_context = build_hit_context_text(result.hits, by_unit)
    return result, hit_context


def grade_natural_scenario(
    *,
    records: list[dict[str, Any]],
    scenario: dict[str, Any],
    llm_answer: str | None = None,
    cached_retrieval: tuple[CandidateQueryResult, str] | None = None,
) -> dict[str, Any]:
    """Council-room-style gates over retrieval + optional LLM synthesis.

    * ``llm_answer is None``: requires semantic pass on **hit context** (deterministic-only path).
    * ``llm_answer`` set: skips that requirement; requires ``classify_answer_semantic`` pass on the **LLM answer**
      instead (retrieval still gated via routes + ``context_support_ratio``).
    """
    if cached_retrieval is not None:
        result, hit_context = cached_retrieval
    else:
        result, hit_context = natural_retrieval_bundle(records=records, scenario=scenario)
    hits = result.hits

    violations: list[str] = []
    exp_units = scenario.get("expect_unit_id_substrings") or []
    if exp_units and not hits_cover_expected_units(hits, [str(x) for x in exp_units]):
        violations.append("missing_expected_unit_id_hit")

    exp_routes = scenario.get("expect_route_substrings") or []
    if exp_routes and not hits_cover_expected_routes(hits, [str(x) for x in exp_routes]):
        violations.append("missing_expected_route_hit")

    must_tokens = [str(x) for x in (scenario.get("must_hit_tokens") or [])]
    stale_tokens = [str(x) for x in (scenario.get("stale_tokens") or [])]
    equiv = scenario.get("semantic_equivalences")
    question_equivalences: dict[str, list[str]] | None = None
    if isinstance(equiv, dict):
        question_equivalences = {}
        for k, vals in equiv.items():
            if isinstance(vals, list):
                question_equivalences[str(k)] = [str(v) for v in vals]
            else:
                question_equivalences[str(k)] = [str(vals)]
    must_not = scenario.get("must_not_cooccur")
    must_not_cooccur = must_not if isinstance(must_not, dict) else None
    if "update_signal_tokens" in scenario:
        upd_raw = scenario.get("update_signal_tokens")
        update_signal_tokens = [str(x) for x in upd_raw] if isinstance(upd_raw, list) else []
    else:
        update_signal_tokens = []

    strict_verdict, strict_must_hits, strict_stale_hits, strict_global_stale = classify_answer(
        must_tokens=must_tokens,
        stale_tokens=stale_tokens,
        answer=hit_context,
        has_error=False,
        update_signal_tokens=update_signal_tokens,
        must_not_cooccur=must_not_cooccur,
    )
    semantic_verdict, sem_must_hits, sem_stale_hits, sem_global_stale = classify_answer_semantic(
        must_tokens=must_tokens,
        stale_tokens=stale_tokens,
        answer=hit_context,
        has_error=False,
        question_equivalences=question_equivalences,
        update_signal_tokens=update_signal_tokens,
        must_not_cooccur=must_not_cooccur,
    )
    ctx_must_hits, ctx_ratio = score_context_support(
        must_tokens=must_tokens,
        context=hit_context,
        question_equivalences=question_equivalences,
        must_not_cooccur=must_not_cooccur,
    )
    retrieval_failure_surface = classify_failure_surface(
        semantic_verdict=semantic_verdict,
        context_support_ratio=ctx_ratio,
    )

    llm_semantic_verdict: str | None = None
    llm_semantic_must_hits: list[str] | None = None
    llm_semantic_stale_hits: list[str] | None = None
    llm_semantic_global_stale_hits: list[str] | None = None
    llm_context_must_hits: list[str] | None = None
    llm_context_support_ratio: float | None = None
    llm_failure_surface: str | None = None

    min_score = scenario.get("min_top_hit_score")
    if min_score is not None and hits:
        if int(hits[0].get("score", 0)) < int(min_score):
            violations.append("top_hit_score_below_threshold")

    min_ctx = float(scenario.get("min_context_support_ratio", 0.67))
    if must_tokens and ctx_ratio + 1e-9 < min_ctx:
        violations.append("context_support_below_threshold")

    if llm_answer is None:
        if semantic_verdict != "pass_updated":
            violations.append(f"semantic_verdict:{semantic_verdict}")
    else:
        llm_semantic_verdict, llm_sem_must, llm_sem_stale, llm_sem_global = classify_answer_semantic(
            must_tokens=must_tokens,
            stale_tokens=stale_tokens,
            answer=llm_answer,
            has_error=False,
            question_equivalences=question_equivalences,
            update_signal_tokens=update_signal_tokens,
            must_not_cooccur=must_not_cooccur,
        )
        llm_semantic_must_hits = llm_sem_must
        llm_semantic_stale_hits = llm_sem_stale
        llm_semantic_global_stale_hits = llm_sem_global
        llm_ctx_must, llm_ctx_ratio = score_context_support(
            must_tokens=must_tokens,
            context=llm_answer,
            question_equivalences=question_equivalences,
            must_not_cooccur=must_not_cooccur,
        )
        llm_context_must_hits = llm_ctx_must
        llm_context_support_ratio = llm_ctx_ratio
        llm_failure_surface = classify_failure_surface(
            semantic_verdict=llm_semantic_verdict,
            context_support_ratio=llm_ctx_ratio,
        )
        if llm_semantic_verdict != "pass_updated":
            violations.append(f"llm_semantic_verdict:{llm_semantic_verdict}")
        if must_tokens and llm_ctx_ratio + 1e-9 < min_ctx:
            violations.append("llm_context_support_below_threshold")

    ok = not violations
    preview_len = int(scenario.get("hit_context_preview_chars", 600))
    grading_mode = "natural_retrieval_context+llm" if llm_answer is not None else "natural_retrieval_context"
    out: dict[str, Any] = {
        "scenario_id": scenario.get("id"),
        "grading_mode": grading_mode,
        "ok": ok,
        "violations": violations,
        "hit_count": len(hits),
        "top_hit": hits[0] if hits else None,
        "strict_verdict": strict_verdict,
        "strict_must_hits": strict_must_hits,
        "strict_stale_hits": strict_stale_hits,
        "strict_global_stale_hits": strict_global_stale,
        "semantic_verdict": semantic_verdict,
        "semantic_must_hits": sem_must_hits,
        "semantic_stale_hits": sem_stale_hits,
        "semantic_global_stale_hits": sem_global_stale,
        "context_must_hits": ctx_must_hits,
        "context_support_ratio": ctx_ratio,
        "failure_surface": retrieval_failure_surface,
        "hit_context_preview": hit_context[:preview_len],
        "full_result": result.as_json_dict(),
    }
    if llm_answer is not None:
        out["llm_semantic_verdict"] = llm_semantic_verdict
        out["llm_semantic_must_hits"] = llm_semantic_must_hits
        out["llm_semantic_stale_hits"] = llm_semantic_stale_hits
        out["llm_semantic_global_stale_hits"] = llm_semantic_global_stale_hits
        out["llm_context_must_hits"] = llm_context_must_hits
        out["llm_context_support_ratio"] = llm_context_support_ratio
        out["llm_failure_surface"] = llm_failure_surface
    return out
