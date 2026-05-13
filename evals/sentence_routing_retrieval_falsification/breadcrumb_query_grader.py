"""Deterministic grading helpers for session-memory query recall (no LLM)."""

from __future__ import annotations

import json
import re
from collections import Counter
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
from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (
    build_campaign_lexicon,
    effective_semantic_equivalences_for_question,
    merged_route_token_stopwords,
)
from src.agent.session_memory_query import CandidateQueryResult, query_session_memory_candidate
from src.token_resolution.contracts import LexiconArtifact

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


def hits_cover_expected_routes(
    hits: list[dict[str, Any]],
    expected_route_substrings: list[str],
    *,
    location_hierarchy_equivalences: dict[str, list[str]] | None = None,
) -> bool:
    """Each expected substring must appear in some hit route's ``normalized_route``."""
    routes: list[str] = []
    for h in hits:
        for r in h.get("routes") or []:
            routes.append(str(r.get("normalized_route", "")).lower())
    blob = "\n".join(routes)
    hierarchy = {
        str(parent).lower(): [str(child).lower() for child in (children or [])]
        for parent, children in (location_hierarchy_equivalences or {}).items()
    }
    for sub in expected_route_substrings:
        sub_l = sub.lower()
        if sub_l in blob:
            continue
        # Deterministic contract: query-time hierarchy expansion may satisfy a
        # parent-location expectation via explicit sublocation route hits.
        children = hierarchy.get(sub_l, [])
        if children and any(child in blob for child in children):
            continue
        return False
    return True


def location_entity_summary_routes_blob(summary: dict[str, Any] | None) -> str:
    """Lowercased newline-joined entity ``normalized_route`` values from a location summary."""
    if not isinstance(summary, dict):
        return ""
    parts: list[str] = []
    for ent in summary.get("entities") or []:
        if isinstance(ent, dict):
            parts.append(str(ent.get("normalized_route", "")).lower())
    return "\n".join(parts)


def grade_location_entity_trace(
    *,
    trace: dict[str, Any],
    expect_location_entity_route_substrings: list[str],
    forbid_location_entity_route_substrings: list[str],
    expect_query_mode: str | None,
) -> list[str]:
    """Violations for deterministic location-entity aggregation (``trace['location_entity_summary']``)."""
    violations: list[str] = []
    if expect_query_mode is not None and str(trace.get("query_mode", "")) != str(expect_query_mode):
        violations.append("query_mode_mismatch")
    need_blob = bool(expect_location_entity_route_substrings or forbid_location_entity_route_substrings)
    summ = trace.get("location_entity_summary")
    blob = location_entity_summary_routes_blob(summ if isinstance(summ, dict) else None)
    if need_blob and not isinstance(summ, dict):
        violations.append("missing_location_entity_summary")
        return violations
    for sub in expect_location_entity_route_substrings:
        if sub.lower() not in blob:
            violations.append(f"missing_expected_location_entity_route:{sub}")
    for sub in forbid_location_entity_route_substrings:
        if sub.lower() in blob:
            violations.append(f"forbidden_location_entity_route_present:{sub}")
    return violations


def resolve_context_evidence_top_k(
    scenario: dict[str, Any],
    *,
    trace: dict[str, Any] | None = None,
) -> int:
    """Lexical-first band size used for expansion / prompt budgeting (usually ``expand_first_pass_cap``)."""
    qspec = scenario.get("query_spec") or {}
    for key in ("expand_first_pass_cap", "expand_seed_hits"):
        raw = qspec.get(key)
        if raw is not None and raw != "":
            return max(1, int(raw))
    tr = trace or {}
    for key in ("expand_first_pass_cap", "expand_seed_hits"):
        raw = tr.get(key)
        if raw is not None and raw != "":
            return max(1, int(raw))
    return 9


def compute_context_evidence_metrics(
    *,
    hits: list[dict[str, Any]],
    scenario: dict[str, Any],
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expected route/unit substring recall restricted to the top-*K* retrieval slice (lexical seed band)."""
    k = resolve_context_evidence_top_k(scenario, trace=trace)
    top_slice = hits[:k]
    exp_units = [str(x) for x in (scenario.get("expect_unit_id_substrings") or [])]
    exp_routes = [str(x) for x in (scenario.get("expect_route_substrings") or [])]
    hierarchy_map = scenario.get("location_hierarchy_equivalences")
    hierarchy_equivalences = (
        {
            str(parent).lower(): [str(child).lower() for child in (children or [])]
            for parent, children in hierarchy_map.items()
        }
        if isinstance(hierarchy_map, dict)
        else {}
    )

    uids_top = [str(h.get("unit_id") or "") for h in top_slice]
    units_missing = [u for u in exp_units if not any(u in uid for uid in uids_top)]
    unit_hit_count = len(exp_units) - len(units_missing)

    routes_top: list[str] = []
    for h in top_slice:
        for r in h.get("routes") or []:
            routes_top.append(str(r.get("normalized_route", "")).lower())
    blob_top = "\n".join(routes_top)
    routes_missing: list[str] = []
    for s in exp_routes:
        s_l = s.lower()
        if s_l in blob_top:
            continue
        children = hierarchy_equivalences.get(s_l, [])
        if children and any(child in blob_top for child in children):
            continue
        routes_missing.append(s)
    route_hit_count = len(exp_routes) - len(routes_missing)

    full_units_ok = hits_cover_expected_units(hits, exp_units) if exp_units else True
    hierarchy_map = scenario.get("location_hierarchy_equivalences")
    hierarchy_equivalences = hierarchy_map if isinstance(hierarchy_map, dict) else None
    full_routes_ok = (
        hits_cover_expected_routes(
            hits,
            exp_routes,
            location_hierarchy_equivalences=hierarchy_equivalences,
        )
        if exp_routes
        else True
    )

    return {
        "context_evidence_top_k": k,
        "hits_considered": len(top_slice),
        "expected_unit_substring_count": len(exp_units),
        "expected_route_substring_count": len(exp_routes),
        "unit_substrings_matched_in_top_k": unit_hit_count,
        "route_substrings_matched_in_top_k": route_hit_count,
        "unit_recall_in_top_k": (unit_hit_count / len(exp_units)) if exp_units else None,
        "route_recall_in_top_k": (route_hit_count / len(exp_routes)) if exp_routes else None,
        "unit_substrings_missing_in_top_k": units_missing,
        "route_substrings_missing_in_top_k": routes_missing,
        "top_k_unit_coverage_ok": not units_missing if exp_units else True,
        "top_k_route_coverage_ok": not routes_missing if exp_routes else True,
        "full_list_unit_coverage_ok": full_units_ok if exp_units else None,
        "full_list_route_coverage_ok": full_routes_ok if exp_routes else None,
    }


def aggregate_context_evidence_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Macro recall weighted by gold expected substring counts across rows."""
    unit_num = 0
    unit_den = 0
    route_num = 0
    route_den = 0
    rows_with_unit_expectation = 0
    rows_with_route_expectation = 0
    k_ref: int | None = None
    for r in results:
        m = r.get("context_evidence_metrics")
        if not isinstance(m, dict):
            continue
        if k_ref is None and m.get("context_evidence_top_k") is not None:
            k_ref = int(m["context_evidence_top_k"])
        eu = int(m.get("expected_unit_substring_count") or 0)
        er = int(m.get("expected_route_substring_count") or 0)
        if eu:
            rows_with_unit_expectation += 1
            unit_den += eu
            unit_num += int(m.get("unit_substrings_matched_in_top_k") or 0)
        if er:
            rows_with_route_expectation += 1
            route_den += er
            route_num += int(m.get("route_substrings_matched_in_top_k") or 0)
    return {
        "context_evidence_top_k_reference": k_ref,
        "executable_rows": len(results),
        "rows_with_unit_expectations": rows_with_unit_expectation,
        "rows_with_route_expectations": rows_with_route_expectation,
        "macro_unit_recall_in_top_k": (unit_num / unit_den) if unit_den else None,
        "macro_route_recall_in_top_k": (route_num / route_den) if route_den else None,
        "macro_unit_matched_in_top_k": unit_num,
        "macro_unit_expected_substrings": unit_den,
        "macro_route_matched_in_top_k": route_num,
        "macro_route_expected_substrings": route_den,
    }


def merge_natural_scenario_from_gold(scenario: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Match ``breadcrumb_query_run`` merged ``query_spec`` for metric recomputation from artifacts."""
    default_campaign = str(gold.get("campaign_id") or "")
    default_spec = gold.get("default_query_spec") or {}
    scen = dict(scenario)
    scen["campaign_id"] = str(scen.get("campaign_id") or default_campaign)
    merged_spec = {**default_spec, **(scen.get("query_spec") or {})}
    merged_spec["query"] = str(scen.get("question") or "")
    scen["query_spec"] = merged_spec
    return scen


# Back-compat alias (older harnesses import this name).
merge_natural_benchmark_scenario = merge_natural_scenario_from_gold


def enrich_natural_report_with_context_evidence_metrics(
    report: dict[str, Any],
    gold: dict[str, Any],
) -> dict[str, Any]:
    """Attach ``context_evidence_metrics`` per row and ``context_evidence_aggregate`` (mutates a copy)."""
    scenarios_by_id = {str(s.get("id") or ""): s for s in (gold.get("scenarios") or [])}
    new_results: list[dict[str, Any]] = []
    for row in report.get("results") or []:
        sid = str(row.get("scenario_id") or "")
        template = scenarios_by_id.get(sid)
        out_row = dict(row)
        if template:
            scen = merge_natural_scenario_from_gold(template, gold)
            hits = list((out_row.get("full_result") or {}).get("hits") or [])
            trace = (out_row.get("full_result") or {}).get("trace") or {}
            out_row["context_evidence_metrics"] = compute_context_evidence_metrics(
                hits=hits,
                scenario=scen,
                trace=trace if isinstance(trace, dict) else {},
            )
        new_results.append(out_row)
    out = dict(report)
    out["results"] = new_results
    out["context_evidence_aggregate"] = aggregate_context_evidence_metrics(new_results)
    return out


def _int_from_spec(qspec: dict[str, Any], key: str, default: int) -> int:
    raw = qspec.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


_EXPANSION_TOKEN_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "and",
        "campaign",
        "captain",
        "character",
        "connects",
        "currently",
        "episode",
        "happened",
        "line",
        "nearby",
        "party",
        "question",
        "recap",
        "relevant",
        "session",
        "situation",
        "team",
        "the",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
)

_GLOBAL_QUERY_ALIAS_MAP: dict[str, list[str]] = {
    # These are task-language aliases, not scenario facts. They are allowed to
    # map intent words to retrieval vocabulary, but not to inject expected
    # campaign entities such as Tealeaf, Mossford, or a specific storm.
    "communication": ["relay", "operator", "transfer", "contact"],
    "communications": ["relay", "operator", "transfer", "contact"],
    "learn": ["clue", "fact", "signal"],
    "learned": ["clue", "fact", "signal"],
    "locations": ["place", "site", "town", "city", "camp"],
    "loops": ["unresolved", "followup", "follow-up", "lead", "thread"],
    "open": ["unresolved", "followup", "follow-up", "lead", "thread"],
    "prep": ["preparation", "shelter", "supplies"],
    "regroups": ["camp", "returns", "finds"],
    "supplies": ["provisions", "crates"],
}


def _tokenize_expansion_text(text: str) -> list[str]:
    out: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9_'-]+", text.lower()):
        token = raw.strip("_-'")
        if len(token) < 3 or token in _EXPANSION_TOKEN_STOPWORDS:
            continue
        out.append(token)
    return out


def _route_expansion_tokens(route: str, *, route_stopwords: frozenset[str]) -> list[str]:
    route_bits = re.split(r"[/_\-\s.]+", route.lower())
    out: list[str] = []
    for bit in route_bits:
        token = bit.strip()
        if len(token) < 3 or token in route_stopwords:
            continue
        out.append(token)
    return out


def _records_by_unit_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("unit_id") or ""): r for r in records}


def _global_query_alias_terms(question: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in _tokenize_expansion_text(question):
        for alias in _GLOBAL_QUERY_ALIAS_MAP.get(token, []):
            norm = alias.lower().strip()
            if norm and norm not in seen:
                terms.append(norm)
                seen.add(norm)
    return terms


def build_query_expansion(
    *,
    question: str,
    records: list[dict[str, Any]],
    first_pass_result: CandidateQueryResult,
    max_terms: int = 24,
    breadcrumb_artifact_text: str = "",
    lexicon: LexiconArtifact | None = None,
    route_token_stopwords: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build production-valid query expansion terms without reading scenario gold.

    Inputs are restricted to the natural question, a small global query-language
    alias dictionary, and the raw first-pass hits. This intentionally excludes
    expected answers, must-hit tokens, expected unit IDs, and expected routes.
    """
    question_terms = _global_query_alias_terms(question)
    by_unit = _records_by_unit_id(records)
    counts: Counter[str] = Counter()
    route_sw = (
        merged_route_token_stopwords(
            records=records,
            breadcrumb_artifact_text=breadcrumb_artifact_text,
            lexicon=lexicon,
        )
        if route_token_stopwords is None
        else route_token_stopwords
    )

    for h in first_pass_result.hits:
        uid = str(h.get("unit_id") or "")
        rec = by_unit.get(uid) or {}
        for r in h.get("routes") or []:
            for token in _route_expansion_tokens(
                str(r.get("normalized_route") or ""),
                route_stopwords=route_sw,
            ):
                counts[token] += 4
        for token in _tokenize_expansion_text(str(rec.get("lexical_plain") or "")):
            counts[token] += 1

    seen: set[str] = set()
    expanded_terms: list[str] = []
    for term in question_terms:
        if term not in seen:
            expanded_terms.append(term)
            seen.add(term)
    for term, _count in counts.most_common():
        if term in seen:
            continue
        expanded_terms.append(term)
        seen.add(term)
        if len(expanded_terms) >= max_terms:
            break

    if first_pass_result.hits:
        source = "first_pass"
    elif question_terms:
        source = "query_only"
    else:
        source = "query_only"
    return {
        "raw_question": question,
        "expanded_terms": expanded_terms[:max_terms],
        "expansion_source": source,
        "first_pass_hit_count": len(first_pass_result.hits),
    }


def _clean_natural_qspec(qspec: dict[str, Any]) -> dict[str, Any]:
    out = dict(qspec)
    # Gold-authored aliases are oracle-prone; expansion is now a measured stage.
    out.pop("query_token_aliases", None)
    return out


def _scenario_with_qspec(scenario: dict[str, Any], qspec: dict[str, Any]) -> dict[str, Any]:
    out = dict(scenario)
    out["query_spec"] = qspec
    return out


def _grade_natural_with_qspec(
    *,
    records: list[dict[str, Any]],
    scenario: dict[str, Any],
    qspec: dict[str, Any],
    breadcrumb_artifact_text: str = "",
    lexicon: LexiconArtifact | None = None,
) -> dict[str, Any]:
    return grade_natural_scenario(
        records=records,
        scenario=_scenario_with_qspec(scenario, qspec),
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        lexicon=lexicon,
    )


def grade_natural_scenario_lanes(
    *,
    records: list[dict[str, Any]],
    scenario: dict[str, Any],
    wide_max_hits: int = 34,
    breadcrumb_artifact_text: str = "",
    lexicon: LexiconArtifact | None = None,
) -> dict[str, Any]:
    """Grade raw, expanded, and wide-recall retrieval lanes for one natural scenario."""
    base_qspec = _clean_natural_qspec(scenario.get("query_spec") or {})
    question = str(base_qspec.get("query") or scenario.get("question") or "")

    raw_qspec = dict(base_qspec)
    raw_qspec["query"] = question
    raw_qspec["expand_context"] = False
    raw_row = _grade_natural_with_qspec(
        records=records,
        scenario=scenario,
        qspec=raw_qspec,
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        lexicon=lexicon,
    )
    first_pass_result = query_session_memory_for_scenario(
        records=records,
        scenario=_scenario_with_qspec(scenario, raw_qspec),
    )

    expansion = build_query_expansion(
        question=question,
        records=records,
        first_pass_result=first_pass_result,
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        lexicon=lexicon,
    )
    expanded_qspec = dict(base_qspec)
    expanded_qspec["query"] = question
    if expansion["expanded_terms"]:
        expanded_qspec["query_token_aliases"] = [" ".join(expansion["expanded_terms"])]
    expanded_row = _grade_natural_with_qspec(
        records=records,
        scenario=scenario,
        qspec=expanded_qspec,
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        lexicon=lexicon,
    )
    expanded_row["raw_question"] = question
    expanded_row["expanded_terms"] = list(expansion["expanded_terms"])
    expanded_row["expansion_source"] = expansion["expansion_source"]
    expanded_row["first_pass_result"] = first_pass_result.as_json_dict()
    expanded_row["expanded_result"] = expanded_row.get("full_result")

    wide_qspec = dict(expanded_qspec)
    wide_qspec["max_hits"] = max(int(wide_qspec.get("max_hits") or 12), int(wide_max_hits))
    wide_row = _grade_natural_with_qspec(
        records=records,
        scenario=scenario,
        qspec=wide_qspec,
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        lexicon=lexicon,
    )

    return {
        "scenario_id": scenario.get("id"),
        "raw_question": question,
        "expansion": expansion,
        "raw_natural": raw_row,
        "expanded_retrieval": expanded_row,
        "wide_recall": wide_row,
    }


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
        expand_same_beat_limit=_int_from_spec(qspec, "expand_same_beat_limit", 0),
        scene_beat_packet_mode=bool(qspec.get("scene_beat_packet_mode", False)),
        scene_beat_packet_threshold=_int_from_spec(qspec, "scene_beat_packet_threshold", 16),
        scene_beat_packet_top_k=_int_from_spec(qspec, "scene_beat_packet_top_k", 3),
        scene_beat_packet_unit_limit=_int_from_spec(qspec, "scene_beat_packet_unit_limit", 8),
        scene_beat_packet_max_packets=_int_from_spec(qspec, "scene_beat_packet_max_packets", 2),
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
    hierarchy_map = scenario.get("location_hierarchy_equivalences")
    hierarchy_equivalences = hierarchy_map if isinstance(hierarchy_map, dict) else None
    if exp_routes and not hits_cover_expected_routes(
        hits,
        [str(x) for x in exp_routes],
        location_hierarchy_equivalences=hierarchy_equivalences,
    ):
        violations.append("missing_expected_route_hit")

    tr_gate = result.trace if isinstance(result.trace, dict) else {}
    exp_loc = [str(x) for x in (scenario.get("expect_location_entity_route_substrings") or [])]
    forbid_loc = [str(x) for x in (scenario.get("forbid_location_entity_route_substrings") or [])]
    raw_mode = scenario.get("expect_query_mode")
    expect_mode = str(raw_mode) if raw_mode is not None and str(raw_mode).strip() != "" else None
    if exp_loc or forbid_loc or expect_mode is not None:
        violations.extend(
            grade_location_entity_trace(
                trace=tr_gate,
                expect_location_entity_route_substrings=exp_loc,
                forbid_location_entity_route_substrings=forbid_loc,
                expect_query_mode=expect_mode,
            )
        )

    min_score = scenario.get("min_top_hit_score")
    if min_score is not None and hits:
        if int(hits[0].get("score", 0)) < int(min_score):
            violations.append("top_hit_score_below_threshold")

    ok = not violations
    full_json = result.as_json_dict()
    trace_obj = full_json.get("trace") if isinstance(full_json.get("trace"), dict) else {}
    return {
        "scenario_id": scenario.get("id"),
        "ok": ok,
        "violations": violations,
        "hit_count": len(hits),
        "top_hit": hits[0] if hits else None,
        "context_evidence_metrics": compute_context_evidence_metrics(
            hits=hits,
            scenario=scenario,
            trace=trace_obj,
        ),
        "full_result": full_json,
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
    breadcrumb_artifact_text: str = "",
    lexicon: LexiconArtifact | None = None,
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
    hierarchy_map = scenario.get("location_hierarchy_equivalences")
    hierarchy_equivalences = hierarchy_map if isinstance(hierarchy_map, dict) else None
    if exp_routes and not hits_cover_expected_routes(
        hits,
        [str(x) for x in exp_routes],
        location_hierarchy_equivalences=hierarchy_equivalences,
    ):
        violations.append("missing_expected_route_hit")

    tr_gate = result.trace if isinstance(result.trace, dict) else {}
    exp_loc = [str(x) for x in (scenario.get("expect_location_entity_route_substrings") or [])]
    forbid_loc = [str(x) for x in (scenario.get("forbid_location_entity_route_substrings") or [])]
    raw_mode = scenario.get("expect_query_mode")
    expect_mode = str(raw_mode) if raw_mode is not None and str(raw_mode).strip() != "" else None
    if exp_loc or forbid_loc or expect_mode is not None:
        violations.extend(
            grade_location_entity_trace(
                trace=tr_gate,
                expect_location_entity_route_substrings=exp_loc,
                forbid_location_entity_route_substrings=forbid_loc,
                expect_query_mode=expect_mode,
            )
        )

    must_tokens = [str(x) for x in (scenario.get("must_hit_tokens") or [])]
    stale_tokens = [str(x) for x in (scenario.get("stale_tokens") or [])]
    resolved_lexicon = lexicon or build_campaign_lexicon(
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        records=records,
        campaign_id=str(scenario.get("campaign_id") or ""),
    )
    question_text = str((scenario.get("query_spec") or {}).get("query") or scenario.get("question") or "")
    question_equivalences = effective_semantic_equivalences_for_question(
        question=question_text,
        scenario=scenario,
        lexicon=resolved_lexicon,
    )
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
    full_json = result.as_json_dict()
    trace_obj = full_json.get("trace") if isinstance(full_json.get("trace"), dict) else {}
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
        "context_evidence_metrics": compute_context_evidence_metrics(
            hits=hits,
            scenario=scenario,
            trace=trace_obj,
        ),
        "full_result": full_json,
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
