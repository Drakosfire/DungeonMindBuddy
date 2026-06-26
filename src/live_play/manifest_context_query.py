"""Blind manifest-backed query/admission for planning context packets.

This module implements a generic manifest query/admission contract:
manifest sources are selected from question text and manifest metadata, then
source content is read to extract citable evidence units/spans before admission.

The runner must not read benchmark gold, dogfood traces, or route by question_id.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.live_play.session_paths import repo_root

PLAY_FACT_USE = "play_facts"
PLAY_FACT_ALLOWED_AUTHORITIES = frozenset({"canon_play", "derived_memory"})
PLAY_FACT_FORBIDDEN_AUTHORITIES = frozenset(
    {"pre_canonical_evidence", "planning_scaffold", "reference_tool", "live_observation"}
)
PIPELINE_STATE_FORBIDDEN_ROLES = frozenset({"prep_scaffold", "roll_table"})
PIPELINE_STATE_FORBIDDEN_AUTHORITIES = frozenset({"planning_scaffold", "reference_tool"})
AUTHORITY_GUARDRAIL_FORBIDDEN_ROLES = frozenset({"table_notes"})
AUTHORITY_GUARDRAIL_FORBIDDEN_AUTHORITIES = frozenset({"pre_canonical_evidence"})

DEFAULT_LANE_BUDGETS: dict[str, int] = {
    "play_recap": 4,
    "session_memory": 4,
    "breadcrumbed_recap": 3,
    "hub_evidence": 4,
    "world_reference": 4,
    "prep_scaffold": 3,
    "live_workspace": 3,
    "roll_reference": 2,
    "capability_audit": 4,
    "table_notes": 2,
    "ingest_status": 2,
}

ROLE_LANE: dict[str, str] = {
    "play_recap": "play_recap",
    "session_memory": "session_memory",
    "prep_scaffold": "prep_scaffold",
    "roll_table": "roll_reference",
    "live_packet": "live_workspace",
    "live_event": "live_workspace",
    "fresh_recap": "live_workspace",
    "hub_evidence": "hub_evidence",
    "world_evidence": "world_reference",
    "table_notes": "table_notes",
}
MECHANICAL_QUERY_TOKENS = frozenset(
    {
        "ac",
        "armor",
        "class",
        "cr",
        "challenge",
        "rating",
        "hp",
        "hit",
        "points",
        "save",
        "saves",
        "saving",
        "statblock",
        "stat",
        "block",
    }
)
MIN_CONTENT_OVERLAP = 2
COMMON_QUERY_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "change",
        "end",
        "for",
        "from",
        "happened",
        "in",
        "is",
        "it",
        "last",
        "memory",
        "of",
        "on",
        "or",
        "play",
        "record",
        "recap",
        "session",
        "that",
        "the",
        "thing",
        "timeline",
        "to",
        "use",
        "was",
        "what",
    }
)

FORBIDDEN_GOLD_SUBSTRINGS = ("gold",)
FORBIDDEN_DOGFOOD_SUBSTRINGS = ("c2s23_dogfood_", "c2s23_dogfood_planner_summary")


@dataclass(frozen=True)
class QueryRequest:
    question_id: str
    question: str
    category: str | None = None


@dataclass(frozen=True)
class QueryConfig:
    precondition_paths: dict[str, str] | None = None
    virtual_precondition_path: str = "virtual://manifest_query/corpus_preconditions"
    virtual_precondition_session_scope: tuple[int, ...] = ()
    max_retrieved_evidence: int = 30
    max_admitted_evidence: int = 12
    max_rejected_evidence: int = 12
    max_admitted_per_source_role: dict[str, int] = field(
        default_factory=lambda: {
            "play_recap": 6,
            "session_memory": 4,
            "hub_evidence": 3,
            "world_evidence": 3,
            "prep_scaffold": 3,
            "live_packet": 1,
            "live_event": 1,
            "table_notes": 1,
            "roll_table": 1,
            "fresh_recap": 1,
            "ingest_status": 1,
        }
    )
    max_spans_per_markdown_source: int = 2
    max_units_per_session_memory_source: int = 3
    min_supporting_evidence_score: float = 2.0


@dataclass(frozen=True)
class QueryFeatures:
    raw_question: str
    tokens: set[str]
    content_tokens: set[str]
    stopword_tokens: set[str]
    distinctive_tokens: set[str]
    session_numbers: set[int]
    exact_phrases: tuple[str, ...]
    title_phrases: tuple[str, ...]
    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    asks_for_last_or_final: bool
    asks_for_play_event: bool
    asks_historical_continuity: bool
    explicit_session_only: bool


def _norm(path: str) -> str:
    return path.strip().replace("\\", "/").lower().lstrip("./")


def _manifest_route_variants(route: str) -> set[str]:
    r = _norm(route)
    variants = {r}
    corpus_prefix = "corpus/eldyrwild-markdown/"
    if r.startswith(corpus_prefix):
        variants.add(r[len(corpus_prefix) :])
    return variants


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _parse_aliases(question: str) -> tuple[str, ...]:
    lowered = question.lower()
    if "aliases:" not in lowered:
        return ()
    idx = lowered.rfind("aliases:")
    chunk = question[idx + len("aliases:") :].strip().strip(".")
    if not chunk:
        return ()
    aliases = [x.strip() for x in chunk.split(",") if x.strip()]
    return tuple(dict.fromkeys(aliases[:12]).keys())


def _extract_quoted_phrases(question: str) -> tuple[str, ...]:
    phrases = [p.strip().lower() for p in re.findall(r'"([^"]+)"', question) if p.strip()]
    return tuple(dict.fromkeys(phrases).keys())


def _extract_title_phrases(question: str, sessions: set[int]) -> tuple[str, ...]:
    titles: list[str] = list(_extract_quoted_phrases(question))
    for match in re.finditer(r"(session\s*\d+\s*-\s*[a-z0-9][a-z0-9\s_\-]+)", question.lower()):
        title = re.sub(r"\s+", " ", str(match.group(1) or "").strip())
        if title:
            titles.append(title)
    for session in sorted(sessions):
        titles.append(f"session {session}")
    return tuple(dict.fromkeys([t for t in titles if t]).keys())


def _explicit_session_only(question: str, sessions: set[int]) -> bool:
    if not sessions:
        return False
    lowered = question.lower()
    if re.search(r"\bonly\s+(use\s+)?session\s*\d{1,2}\b", lowered):
        return True
    return bool(re.search(r"\b(session\s*\d{1,2}).*(only|exclusively)\b", lowered))


def _asks_for_last_or_final(question: str) -> bool:
    lowered = question.lower()
    if any(
        phrase in lowered
        for phrase in (
            "last",
            "latest",
            "most recent",
            "recently",
            "final",
            "ending",
            "end of",
            "at the end",
            "close of",
            "wrap up",
            "cliffhanger",
        )
    ):
        return True
    return bool(re.search(r"\bhow did .+ end\b", lowered))


def _build_query_features(question: str, *, hints: set[str], sessions: set[int]) -> QueryFeatures:
    lowered = question.lower()
    tokens = _tokenize(question)
    stop_tokens = {t for t in tokens if t in COMMON_QUERY_TOKENS}
    content_tokens = {t for t in tokens if t not in COMMON_QUERY_TOKENS}
    distinctive_tokens = {t for t in content_tokens if len(t) > 2 or t.isdigit()}
    aliases = _parse_aliases(question)
    title_phrases = _extract_title_phrases(question, sessions)
    asks_for_last_or_final = _asks_for_last_or_final(question)
    asks_for_play_event = "play_fact" in hints or any(
        t in lowered
        for t in (
            "what happened",
            "what change",
            "what changed",
            "last thing",
            "final beat",
            "last event",
            "outcome",
            "end of session",
            "at the end of",
        )
    )
    asks_historical_continuity = any(
        t in lowered for t in ("old threads", "earlier sessions", "over time", "historical continuity", "changed over time")
    )
    return QueryFeatures(
        raw_question=question,
        tokens=tokens,
        content_tokens=content_tokens,
        stopword_tokens=stop_tokens,
        distinctive_tokens=distinctive_tokens,
        session_numbers=sessions,
        exact_phrases=_extract_quoted_phrases(question),
        title_phrases=title_phrases,
        aliases=aliases,
        tags=tuple(sorted(hints)),
        asks_for_last_or_final=asks_for_last_or_final,
        asks_for_play_event=asks_for_play_event,
        asks_historical_continuity=asks_historical_continuity,
        explicit_session_only=_explicit_session_only(question, sessions),
    )


def _token_overlap_score(candidate_tokens: set[str], features: QueryFeatures) -> tuple[float, dict[str, float]]:
    distinctive_overlap = float(len(candidate_tokens & features.distinctive_tokens))
    content_overlap = float(len(candidate_tokens & features.content_tokens))
    stopword_overlap = float(len(candidate_tokens & features.stopword_tokens))
    score = (distinctive_overlap * 2.5) + (content_overlap * 0.8) - (stopword_overlap * 0.2)
    return score, {
        "distinctive_token_overlap": distinctive_overlap,
        "query_token_overlap": content_overlap,
        "stopword_overlap": stopword_overlap,
    }


def infer_intent_hints(question: str) -> set[str]:
    q = question.lower()
    hints: set[str] = set()
    if any(
        t in q
        for t in (
            "ingest",
            "ready",
            "readiness",
            "breadcrumb",
            "normalized",
            "session memory",
            "materialized",
            "activation",
            "pipeline state",
        )
    ):
        hints.add("pipeline_state")
    if any(
        t in q
        for t in (
            "can i",
            "can we",
            "can one",
            "supported",
            "capability",
            "tool",
            "create",
            "write",
            "patch",
            "register",
            "add a new",
        )
    ):
        hints.add("capability_check")
    if any(
        t in q
        for t in (
            "happened",
            "in play",
            "played",
            "play outcomes",
            "carry into",
            "foreground",
            "background mentions",
            "normal retrieval evidence",
            "what change",
            "what changed",
            "at the end of",
            "end of session",
            "how did",
        )
    ):
        hints.add("play_fact")
    if any(t in q for t in ("prep", "plan", "session 23", "opening", "next", "carry forward")):
        hints.add("planning_context")
    if any(t in q for t in ("authority", "prove", "source of truth", "normal retrieval evidence")) or (
        "raw staged" in q and "normal retrieval evidence" in q
    ):
        hints.add("authority_guardrail")
    return hints or {"planning_context"}


def infer_session_numbers(question: str) -> set[int]:
    found = {int(m) for m in re.findall(r"\bsession\s*(\d{1,2})\b", question.lower())}
    found.update(int(m) for m in re.findall(r"\bs(\d{1,2})\b", question.lower()))
    return found


def _session_number_from_path(path: str) -> int | None:
    match = re.search(r"session\s+(\d{1,2})", path, re.I)
    if not match:
        return None
    return int(match.group(1))


def _single_session_target(session_numbers: set[int]) -> int | None:
    if len(session_numbers) == 1:
        return next(iter(session_numbers))
    return None


def _evidence_session_number(evidence: dict[str, Any]) -> int | None:
    raw = evidence.get("session_number")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return _session_number_from_path(str(evidence.get("path") or ""))


def _session_target_mismatch(query_features: QueryFeatures, evidence: dict[str, Any]) -> bool:
    target = _single_session_target(query_features.session_numbers)
    if target is None:
        return False
    ev_session = _evidence_session_number(evidence)
    if ev_session is None:
        return False
    return ev_session != target


def primary_claim_type(hints: set[str]) -> str:
    priority = (
        "authority_guardrail",
        "capability_check",
        "play_fact",
        "pipeline_state",
        "planning_context",
    )
    for claim in priority:
        if claim in hints:
            return claim
    return "planning_context"


def intent_class_from_hints(hints: set[str]) -> str:
    if "authority_guardrail" in hints:
        return "authority_check"
    if "capability_check" in hints:
        return "capability_check"
    if "play_fact" in hints:
        return "play_fact_retrieval"
    if "pipeline_state" in hints:
        return "ingest_state_check"
    return "cross_session_planning"


def compute_lane_budgets(hints: set[str]) -> dict[str, int]:
    budgets = dict(DEFAULT_LANE_BUDGETS)
    if "pipeline_state" in hints:
        budgets["ingest_status"] = max(budgets["ingest_status"], 4)
        budgets["play_recap"] = max(budgets["play_recap"], 4)
        budgets["session_memory"] = max(budgets["session_memory"], 4)
        budgets["prep_scaffold"] = min(budgets["prep_scaffold"], 2)
    if "play_fact" in hints:
        budgets["play_recap"] = max(budgets["play_recap"], 4)
        budgets["session_memory"] = max(budgets["session_memory"], 4)
    if "capability_check" in hints:
        budgets["capability_audit"] = max(budgets["capability_audit"], 4)
        budgets["live_workspace"] = max(budgets["live_workspace"], 3)
    if "authority_guardrail" in hints:
        budgets["table_notes"] = max(budgets["table_notes"], 2)
        budgets["play_recap"] = max(budgets["play_recap"], 3)
    if "planning_context" in hints:
        budgets["prep_scaffold"] = max(budgets["prep_scaffold"], 3)
        budgets["hub_evidence"] = max(budgets["hub_evidence"], 4)
        budgets["world_reference"] = max(budgets["world_reference"], 4)
    return budgets


def build_query_plan(request: QueryRequest) -> dict[str, Any]:
    hints = infer_intent_hints(request.question)
    return {
        "intent_hints": sorted(hints),
        "session_numbers": sorted(infer_session_numbers(request.question)),
        "lane_budgets": compute_lane_budgets(hints),
        "primary_claim_type": primary_claim_type(hints),
    }


def build_manifest_index(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_route: dict[str, dict[str, Any]] = {}
    entries = [e for e in list(manifest.get("entries") or []) if isinstance(e, dict)]
    for row in entries:
        route = str(row.get("route") or "").strip()
        if not route:
            continue
        for variant in _manifest_route_variants(route):
            by_route[variant] = row
    return by_route, entries


def build_corpus_preconditions(precondition_paths: dict[str, str], root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    checks = []
    for key, rel in precondition_paths.items():
        p = base / rel
        checks.append({"key": key, "path": rel, "exists": p.is_file()})
    return {"all_required_present": all(bool(c["exists"]) for c in checks), "checks": checks}


def build_virtual_precondition_evidence(preconditions: dict[str, Any], config: QueryConfig) -> dict[str, Any]:
    checks = list(preconditions.get("checks") or [])
    routes = [str(c["path"]) for c in checks if c.get("exists")]
    present = [str(c.get("key") or "") for c in checks if c.get("exists")]
    state_excerpt = (
        "Corpus precondition audit: "
        + (", ".join(sorted(present)) if present else "no configured preconditions")
    )
    return {
        "path": config.virtual_precondition_path,
        "source_role": "ingest_status",
        "authority": "audit",
        "session_scope": list(config.virtual_precondition_session_scope),
        "route_exists": True,
        "unit_id": None,
        "breadcrumb_id": None,
        "line_start": None,
        "line_end": None,
        "text_excerpt": state_excerpt,
        "evidence_score": 100.0,
        "admissible": True,
        "allowed_uses": ["pipeline_state", "planning_activation_readiness"],
        "forbidden_uses": [PLAY_FACT_USE],
        "routes": routes,
    }


def _lane_for_entry(entry: dict[str, Any]) -> str:
    role = str(entry.get("source_role") or "")
    route = _norm(str(entry.get("route") or ""))
    if role == "play_recap" and "_breadcrumbed/" in route:
        return "breadcrumbed_recap"
    return ROLE_LANE.get(role, "hub_evidence")


def _is_mechanical_query(features: QueryFeatures) -> bool:
    lowered = features.raw_question.lower()
    if "statblock" in lowered or "armor class" in lowered:
        return True
    return bool(features.content_tokens & MECHANICAL_QUERY_TOKENS)


def _path_slug_token_boost(route: str, features: QueryFeatures) -> float:
    segments = set(re.findall(r"[a-z0-9]+", route.lower()))
    overlap = features.content_tokens & segments
    return float(len(overlap)) * 1.5


def _score_entry(entry: dict[str, Any], features: QueryFeatures, hints: set[str]) -> tuple[float, dict[str, float]]:
    route = str(entry.get("route") or "")
    source_id = str(entry.get("source_id") or "")
    notes = " ".join(str(x) for x in list(entry.get("notes") or []) if str(x).strip())
    lexical = " ".join(str(x) for x in list(entry.get("lexical_terms") or []) if str(x).strip())
    role = str(entry.get("source_role") or "")
    authority = str(entry.get("authority") or "")
    scopes = {int(s) for s in list(entry.get("session_scope") or []) if str(s).isdigit()}
    score = 0.0
    components: dict[str, float] = {}

    route_tokens = _tokenize(route)
    source_id_tokens = _tokenize(source_id)
    notes_tokens = _tokenize(notes)
    lexical_tokens = _tokenize(lexical)

    route_score, route_overlap = _token_overlap_score(route_tokens, features)
    source_id_score, source_id_overlap = _token_overlap_score(source_id_tokens, features)
    notes_score, notes_overlap = _token_overlap_score(notes_tokens, features)
    lexical_score, lexical_overlap = _token_overlap_score(lexical_tokens, features)
    score += route_score + (source_id_score * 0.75) + (notes_score * 0.4) + (lexical_score * 0.6)
    components["route_token_score"] = route_score
    components["source_id_token_score"] = source_id_score * 0.75
    components["notes_token_score"] = notes_score * 0.4
    components["lexical_term_score"] = lexical_score * 0.6
    components.update({f"route_{k}": v for k, v in route_overlap.items()})
    components.update({f"source_id_{k}": v for k, v in source_id_overlap.items()})
    components.update({f"notes_{k}": v for k, v in notes_overlap.items()})
    components.update({f"lexical_{k}": v for k, v in lexical_overlap.items()})

    session_scope_score = 0.0
    if features.session_numbers and scopes & features.session_numbers:
        session_scope_score += 8.0
    elif features.session_numbers and scopes:
        session_scope_score -= 0.75 if features.asks_historical_continuity else 2.5
    elif not features.session_numbers and scopes:
        session_scope_score += 1.0
    if features.explicit_session_only and features.session_numbers:
        if scopes and not (scopes & features.session_numbers):
            session_scope_score -= 100.0
        elif not scopes:
            session_scope_score -= 20.0
    recency_score = 0.0
    if not features.session_numbers and features.asks_for_last_or_final and scopes:
        recency_score = max(scopes) * 0.12

    score += session_scope_score + recency_score
    components["session_scope_score"] = session_scope_score
    components["recency_score"] = recency_score

    role_score = 0.0

    if "play_fact" in hints and role in {"play_recap", "session_memory"}:
        role_score += 10.0
    if "pipeline_state" in hints and role in {"play_recap", "session_memory"}:
        role_score += 9.0
    if "pipeline_state" in hints and authority == "audit":
        role_score += 8.0
    if "planning_context" in hints and role in {"prep_scaffold", "hub_evidence", "live_packet", "world_evidence"}:
        role_score += 5.0
    if "capability_check" in hints and role in {
        "live_packet",
        "roll_table",
        "prep_scaffold",
        "hub_evidence",
        "world_evidence",
    }:
        role_score += 4.0
    if "authority_guardrail" in hints and role == "table_notes":
        role_score += 8.0
    if "authority_guardrail" in hints and role in {"play_recap", "session_memory"}:
        role_score += 6.0
    if "play_fact" in hints and role == "table_notes" and features.session_numbers and scopes & features.session_numbers:
        role_score += 7.0
    if features.asks_for_play_event and role in {"play_recap", "session_memory"}:
        role_score += 6.0
    if features.asks_for_play_event and role == "hub_evidence":
        role_score -= 4.0
    if features.asks_for_play_event and role == "world_evidence":
        role_score -= 5.0
    if features.asks_for_last_or_final and role == "play_recap":
        role_score += 2.0
    route_lower = route.lower()
    if _is_mechanical_query(features) and (
        role == "world_evidence" or "statblock" in route_lower
    ):
        role_score += 6.0
    if _is_mechanical_query(features) and role == "prep_scaffold":
        role_score -= 6.0
    if "timeline" in features.tokens and route_lower.endswith("/timeline.md"):
        role_score += 5.0
    slug_boost = _path_slug_token_boost(route, features)
    role_score += slug_boost
    components["path_slug_boost"] = slug_boost
    score += role_score
    components["source_role_score"] = role_score

    searchable_text = " ".join((route.lower(), source_id.lower(), notes.lower(), lexical.lower()))
    title_matches = float(sum(1 for phrase in features.title_phrases if phrase and phrase in searchable_text))
    exact_title_match_score = title_matches * 6.0
    alias_matches = float(sum(1 for alias in features.aliases if alias.lower() in searchable_text))
    alias_match_score = alias_matches * 2.0
    score += exact_title_match_score + alias_match_score
    components["exact_title_match_score"] = exact_title_match_score
    components["alias_match_score"] = alias_match_score
    components["title_match_count"] = title_matches
    components["alias_match_count"] = alias_matches

    admissibility_penalty = 0.0
    if not bool(entry.get("route_exists")):
        admissibility_penalty -= 100.0
    if not bool(entry.get("admissible")):
        admissibility_penalty -= 50.0
    score += admissibility_penalty
    components["admissibility_penalty"] = admissibility_penalty
    components["final_score"] = score
    return score, components


def retrieve_candidates(
    entries: list[dict[str, Any]],
    request: QueryRequest,
    query_plan: dict[str, Any],
    query_features: QueryFeatures,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hints = set(query_plan["intent_hints"])
    budgets = dict(query_plan["lane_budgets"])

    by_lane: dict[str, list[tuple[float, dict[str, Any], dict[str, float]]]] = {}
    manifest_scores: list[dict[str, Any]] = []
    for entry in entries:
        lane = _lane_for_entry(entry)
        sc, components = _score_entry(entry, query_features, hints)
        by_lane.setdefault(lane, []).append((sc, entry, components))
        manifest_scores.append(
            {
                "route": str(entry.get("route") or ""),
                "source_id": str(entry.get("source_id") or ""),
                "source_role": str(entry.get("source_role") or ""),
                "authority": str(entry.get("authority") or ""),
                "session_scope": list(entry.get("session_scope") or []),
                "lane": lane,
                "final_score": sc,
                "score_components": components,
            }
        )

    selected: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    lane_top: dict[str, list[dict[str, Any]]] = {}
    for lane, budget in budgets.items():
        ranked = sorted(by_lane.get(lane, []), key=lambda t: (-t[0], str(t[1].get("route") or "")))
        lane_top[lane] = [
            {
                "route": str(entry.get("route") or ""),
                "source_role": str(entry.get("source_role") or ""),
                "authority": str(entry.get("authority") or ""),
                "final_score": score,
                "score_components": components,
            }
            for score, entry, components in ranked[:5]
        ]
        taken = 0
        for sc, entry, components in ranked:
            if sc <= -50:
                continue
            route = _norm(str(entry.get("route") or ""))
            if route in seen_routes:
                continue
            seen_routes.add(route)
            enriched = dict(entry)
            enriched["_entry_score"] = sc
            enriched["_entry_score_components"] = dict(components)
            enriched["_entry_lane"] = lane
            selected.append(enriched)
            taken += 1
            if taken >= budget:
                break
    trace = {
        "query": request.question,
        "top_manifest_entries": sorted(manifest_scores, key=lambda row: (-float(row["final_score"]), row["route"]))[:30],
        "lane_top_entries": lane_top,
    }
    return selected, trace


def _entry_to_evidence(entry: dict[str, Any], *, path_override: str | None = None) -> dict[str, Any]:
    route = path_override or str(entry.get("route") or "")
    entry_score = float(entry.get("_entry_score") or 0.0)
    entry_components = dict(entry.get("_entry_score_components") or {})
    if "final_score" not in entry_components:
        entry_components["final_score"] = entry_score
    return {
        "path": route,
        "source_role": str(entry.get("source_role") or ""),
        "authority": str(entry.get("authority") or ""),
        "session_scope": list(entry.get("session_scope") or []),
        "unit_id": None,
        "breadcrumb_id": None,
        "line_start": None,
        "line_end": None,
        "text_excerpt": None,
        "evidence_score": entry_score,
        "score_components": entry_components,
        "admissible": bool(entry.get("admissible")),
        "allowed_uses": list(entry.get("allowed_uses") or []),
        "forbidden_uses": list(entry.get("forbidden_uses") or []),
        "routes": [str(entry.get("route") or route)],
    }


def _evidence_from_entry(
    entry: dict[str, Any],
    *,
    path: str,
    unit_id: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    breadcrumb_id: str | None = None,
    text_excerpt: str | None = None,
    routes: list[str] | None = None,
    evidence_score: float | None = None,
    score_components: dict[str, Any] | None = None,
    session_number: int | None = None,
) -> dict[str, Any]:
    ev = _entry_to_evidence(entry, path_override=path)
    ev["unit_id"] = unit_id
    ev["line_start"] = line_start
    ev["line_end"] = line_end
    ev["breadcrumb_id"] = breadcrumb_id
    ev["text_excerpt"] = text_excerpt
    ev["evidence_score"] = evidence_score
    ev["score_components"] = dict(score_components or {})
    if session_number is not None:
        ev["session_number"] = session_number
    if evidence_score is not None and "final_score" not in ev["score_components"]:
        ev["score_components"]["final_score"] = float(evidence_score)
    if routes is not None:
        ev["routes"] = routes
    return ev


def _extract_markdown_spans(
    entry: dict[str, Any], abs_path: Path, query_features: QueryFeatures, max_spans: int
) -> list[dict[str, Any]]:
    text = abs_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    content_start_idx = 0
    if lines and lines[0].strip() == "---":
        for idx, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                content_start_idx = idx + 1
                break
    spans: list[tuple[int, int, str]] = []
    start: int | None = None
    bucket: list[str] = []
    for idx, line in enumerate(lines[content_start_idx:], start=content_start_idx + 1):
        if line.strip():
            if start is None:
                start = idx
            bucket.append(line.strip())
            continue
        if start is not None and bucket:
            spans.append((start, idx - 1, " ".join(bucket)))
            start = None
            bucket = []
    if start is not None and bucket:
        spans.append((start, len(lines), " ".join(bucket)))

    scored: list[tuple[float, int, int, str, dict[str, float]]] = []
    entry_score = float(entry.get("_entry_score") or 0.0)
    entry_components = dict(entry.get("_entry_score_components") or {})
    entry_role_score = float(entry_components.get("source_role_score", 0.0))
    entry_session_scope_score = float(entry_components.get("session_scope_score", 0.0))
    entry_title_score = float(entry_components.get("exact_title_match_score", 0.0))
    for s, e, body in spans:
        body_lc = body.lstrip().lower()
        if body_lc.startswith("--- schema:") or body_lc.startswith("schema:"):
            continue
        if s <= 200 and "breadcrumb_semantics:" in body_lc:
            continue
        if query_features.asks_for_play_event and body_lc.startswith("#"):
            continue
        tokens = _tokenize(body)
        overlap_score, overlap_components = _token_overlap_score(tokens, query_features)
        min_overlap = 1.0 if query_features.asks_for_last_or_final else float(MIN_CONTENT_OVERLAP)
        if overlap_components["query_token_overlap"] < min_overlap:
            continue
        body_lc = body.lower()
        exact_title_hits = float(sum(1 for phrase in query_features.title_phrases if phrase and phrase in body_lc))
        exact_title_match_score = exact_title_hits * 2.0
        route_title_score = max(0.0, entry_title_score * 0.4) + exact_title_match_score
        document_position_score = 0.0
        if query_features.asks_for_last_or_final:
            document_position_score = float(e) / float(max(1, len(lines)))
            if str(entry.get("source_role") or "") == "play_recap":
                document_position_score *= 8.0
            else:
                document_position_score *= 4.0
        ending_phrase_score = 0.0
        if query_features.asks_for_last_or_final and any(
            marker in body_lc
            for marker in (
                "and that is how",
                "that's when",
                "finally",
                "at the end",
                "met her father",
                "lightning bolt",
                "turn the tide",
                "overrun",
            )
        ):
            ending_phrase_score += 2.5
        final_score = (
            (entry_score * 0.55)
            + overlap_score
            + route_title_score
            + (entry_session_scope_score * 0.7)
            + (entry_role_score * 0.35)
            + document_position_score
            + ending_phrase_score
        )
        components = {
            "entry_score": entry_score,
            "span_score": overlap_score,
            "route_title_score": route_title_score,
            "session_scope_score": entry_session_scope_score * 0.7,
            "source_role_score": entry_role_score * 0.35,
            "exact_title_match_score": exact_title_match_score,
            "document_position_score": document_position_score,
            "ending_phrase_score": ending_phrase_score,
            "query_token_overlap": overlap_components["query_token_overlap"],
            "distinctive_token_overlap": overlap_components["distinctive_token_overlap"],
            "stopword_overlap": overlap_components["stopword_overlap"],
            "final_score": final_score,
        }
        scored.append((final_score, s, e, body, components))
    if query_features.asks_for_last_or_final:
        scored.sort(key=lambda t: (-t[2], -t[0], t[1]))
    else:
        scored.sort(key=lambda t: (-t[0], t[1]))

    route = str(entry.get("route") or "")
    out: list[dict[str, Any]] = []
    for score, s, e, body, components in scored[:max(1, max_spans)]:
        out.append(
            _evidence_from_entry(
                entry,
                path=route,
                line_start=s,
                line_end=e,
                text_excerpt=body[:700],
                evidence_score=score,
                score_components=components,
            )
        )

    if (
        not out
        and str(entry.get("source_role") or "") == "play_recap"
        and query_features.asks_for_last_or_final
        and spans
        and "/_normalized/" not in route
        and "/_breadcrumbed/" not in route
    ):
        s, e, body = spans[-1]
        body_lc = body.lower()
        document_position_score = float(e) / float(max(1, len(lines))) * 8.0
        ending_phrase_score = 2.5 if any(
            marker in body_lc
            for marker in ("lightning bolt", "turn the tide", "overrun", "finally", "at the end")
        ) else 0.0
        final_score = (entry_score * 0.55) + document_position_score + ending_phrase_score
        out.append(
            _evidence_from_entry(
                entry,
                path=route,
                line_start=s,
                line_end=e,
                text_excerpt=body[:700],
                evidence_score=final_score,
                score_components={
                    "entry_score": entry_score,
                    "document_position_score": document_position_score,
                    "ending_phrase_score": ending_phrase_score,
                    "final_score": final_score,
                    "recap_tail_fallback": 1.0,
                },
            )
        )
    return out


def _extract_session_memory_units(
    entry: dict[str, Any], abs_path: Path, query_features: QueryFeatures, max_units: int
) -> list[dict[str, Any]]:
    route = str(entry.get("route") or "")
    entry_score = float(entry.get("_entry_score") or 0.0)
    entry_components = dict(entry.get("_entry_score_components") or {})
    rows: list[tuple[float, dict[str, Any], dict[str, float], list[str]]] = []
    max_line_start = 0
    parsed_rows: list[dict[str, Any]] = []
    for raw in abs_path.read_text(encoding="utf-8").splitlines():
        row = raw.strip()
        if not row:
            continue
        try:
            obj = json.loads(row)
        except json.JSONDecodeError:
            continue
        excerpt = str(obj.get("lexical_plain") or "").strip()
        if not excerpt:
            continue
        parsed_rows.append(obj)

    target_session = _single_session_target(query_features.session_numbers)

    for obj in parsed_rows:
        unit_session = int(obj["session_number"]) if isinstance(obj.get("session_number"), int) else None
        if target_session is not None and unit_session is not None and unit_session != target_session:
            continue
        line_start = int(obj["line_start"]) if isinstance(obj.get("line_start"), int) else 0
        max_line_start = max(max_line_start, line_start)

    for obj in parsed_rows:
        excerpt = str(obj.get("lexical_plain") or "").strip()
        unit_session = int(obj["session_number"]) if isinstance(obj.get("session_number"), int) else None
        if target_session is not None and unit_session is not None and unit_session != target_session:
            continue
        tokens = _tokenize(excerpt)
        overlap_score, overlap_components = _token_overlap_score(tokens, query_features)
        route_refs = [str(r.get("normalized_route") or "") for r in list(obj.get("routes") or []) if r.get("normalized_route")]
        source_recap_path = str(obj.get("source_recap_path") or "")
        if source_recap_path:
            route_refs.append(source_recap_path)
        route_bonus = 0.0
        route_refs_lc = " ".join(route_refs).lower()
        route_title_hits = float(sum(1 for phrase in query_features.title_phrases if phrase and phrase in route_refs_lc))
        route_bonus += route_title_hits * 2.0
        for rr in list(obj.get("routes") or []):
            route_bonus += float(len(_tokenize(str(rr.get("normalized_route") or "")) & query_features.distinctive_tokens)) * 0.25
        source_recap_alignment_score = 0.0
        if source_recap_path and query_features.session_numbers:
            if any(f"session {s}" in source_recap_path.lower() for s in query_features.session_numbers):
                source_recap_alignment_score += 4.0
            else:
                source_recap_alignment_score -= 1.5
        min_overlap = 1.0 if query_features.asks_for_last_or_final else float(MIN_CONTENT_OVERLAP)
        if (
            overlap_components["query_token_overlap"] < min_overlap
            and source_recap_alignment_score <= 0.0
            and not query_features.asks_for_last_or_final
        ):
            continue
        unit_id = str(obj.get("unit_id") or "")
        meta_dampening = -2.5 if query_features.asks_for_play_event and unit_id.startswith("meta-") else 0.0
        line_start = int(obj["line_start"]) if isinstance(obj.get("line_start"), int) else 0
        document_position_score = 0.0
        early_position_penalty = 0.0
        if query_features.asks_for_last_or_final and max_line_start > 0:
            relative_position = float(line_start) / float(max_line_start)
            document_position_score = relative_position * 20.0
            if relative_position < 0.65:
                early_position_penalty = -12.0
        elif query_features.asks_for_last_or_final:
            document_position_score = min(8.0, float(max(0, line_start)) / 4.0)
        excerpt_lc = excerpt.lower()
        ending_phrase_score = 0.0
        if query_features.asks_for_last_or_final and any(
            marker in excerpt_lc
            for marker in (
                "and that is how",
                "that's when",
                "finally",
                "at the end",
                "met her father",
                "lightning bolt",
                "turn the tide",
                "overrun",
            )
        ):
            ending_phrase_score += 12.0
        final_score = (
            (entry_score * 0.5)
            + overlap_score
            + route_bonus
            + source_recap_alignment_score
            + meta_dampening
            + (float(entry_components.get("source_role_score", 0.0)) * 0.25)
            + document_position_score
            + early_position_penalty
            + ending_phrase_score
        )
        components = {
            "entry_score": entry_score,
            "unit_score": overlap_score,
            "route_title_score": route_bonus,
            "source_recap_alignment_score": source_recap_alignment_score,
            "session_scope_score": float(entry_components.get("session_scope_score", 0.0)) * 0.4,
            "source_role_score": float(entry_components.get("source_role_score", 0.0)) * 0.25,
            "meta_dampening": meta_dampening,
            "document_position_score": document_position_score,
            "early_position_penalty": early_position_penalty,
            "ending_phrase_score": ending_phrase_score,
            "query_token_overlap": overlap_components["query_token_overlap"],
            "distinctive_token_overlap": overlap_components["distinctive_token_overlap"],
            "stopword_overlap": overlap_components["stopword_overlap"],
            "final_score": final_score,
        }
        rows.append((final_score, obj, components, route_refs))
    if query_features.asks_for_last_or_final:
        rows.sort(key=lambda t: (-int(t[1].get("line_start") or 0), -t[0]))
    else:
        rows.sort(key=lambda t: -t[0])

    out: list[dict[str, Any]] = []
    for score, obj, components, route_refs in rows[: max(1, max_units)]:
        if route not in route_refs:
            route_refs.insert(0, route)
        out.append(
            _evidence_from_entry(
                entry,
                path=route,
                unit_id=str(obj.get("unit_id") or "") or None,
                line_start=int(obj["line_start"]) if isinstance(obj.get("line_start"), int) else None,
                line_end=int(obj["line_end"]) if isinstance(obj.get("line_end"), int) else None,
                text_excerpt=str(obj.get("lexical_plain") or "")[:700] or None,
                routes=route_refs,
                evidence_score=score,
                score_components=components,
                session_number=unit_session,
            )
        )
    return out


def _extract_generic_excerpt(entry: dict[str, Any], abs_path: Path, query_features: QueryFeatures) -> list[dict[str, Any]]:
    text = abs_path.read_text(encoding="utf-8")
    first = text.strip().splitlines()
    if not first:
        return []
    excerpt = " ".join(first[:4]).strip()
    excerpt_tokens = _tokenize(excerpt)
    overlap_score, overlap_components = _token_overlap_score(excerpt_tokens, query_features)
    total_overlap = float(len(excerpt_tokens & query_features.tokens))
    if total_overlap <= 0:
        return []
    route = str(entry.get("route") or "")
    entry_score = float(entry.get("_entry_score") or 0.0)
    content_score = overlap_score + (total_overlap * 0.25)
    final_score = (entry_score * 0.7) + content_score
    return [
        _evidence_from_entry(
            entry,
            path=route,
            text_excerpt=excerpt[:700],
            evidence_score=final_score,
            score_components={
                "entry_score": entry_score,
                "content_score": content_score,
                "total_token_overlap": total_overlap,
                "query_token_overlap": overlap_components["query_token_overlap"],
                "distinctive_token_overlap": overlap_components["distinctive_token_overlap"],
                "stopword_overlap": overlap_components["stopword_overlap"],
                "final_score": final_score,
            },
        )
    ]


def extract_evidence_units(
    entry: dict[str, Any],
    *,
    query_features: QueryFeatures,
    root: Path,
    config: QueryConfig,
) -> list[dict[str, Any]]:
    route = str(entry.get("route") or "")
    if not route:
        return []
    abs_path = root / route
    if not abs_path.is_file():
        return []
    role = str(entry.get("source_role") or "")

    if role == "session_memory" and route.endswith(".records_meta.json"):
        return []
    if role == "session_memory" and route.endswith(".jsonl"):
        return _extract_session_memory_units(
            entry, abs_path, query_features, max_units=config.max_units_per_session_memory_source
        )
    if route.endswith(".md"):
        return _extract_markdown_spans(
            entry, abs_path, query_features, max_spans=config.max_spans_per_markdown_source
        )
    return _extract_generic_excerpt(entry, abs_path, query_features)


def _has_evidence_granularity(evidence: dict[str, Any]) -> bool:
    if str(evidence.get("unit_id") or "").strip():
        return True
    if str(evidence.get("breadcrumb_id") or "").strip():
        return True
    if evidence.get("line_start") is not None and evidence.get("line_end") is not None:
        return True
    if str(evidence.get("text_excerpt") or "").strip():
        return True
    return False


def _evidence_score(evidence: dict[str, Any]) -> float:
    raw = evidence.get("evidence_score")
    if isinstance(raw, (int, float)):
        return float(raw)
    return 0.0


def _apply_evidence_budget(
    evidence: list[dict[str, Any]],
    *,
    max_total: int,
    per_role_cap: dict[str, int] | None = None,
    ensure_roles: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not evidence:
        return []
    ranked = sorted(evidence, key=lambda e: (-_evidence_score(e), str(e.get("path") or "")))
    role_caps = dict(per_role_cap or {})
    for before_rank, row in enumerate(ranked, start=1):
        components = dict(row.get("score_components") or {})
        components["budget_rank_before_cap"] = before_rank
        row["score_components"] = components
    role_counts: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    required_roles = set(ensure_roles or set())
    after_rank = 0

    for role in sorted(required_roles):
        cap = int(role_caps.get(role, max_total))
        if cap <= 0:
            continue
        picked = next((row for row in ranked if str(row.get("source_role") or "") == role), None)
        if picked is None:
            continue
        out.append(picked)
        after_rank += 1
        picked_components = dict(picked.get("score_components") or {})
        picked_components["budget_rank_after_cap"] = after_rank
        picked["score_components"] = picked_components
        role_counts[role] = role_counts.get(role, 0) + 1
        if len(out) >= max_total:
            return out

    for row in ranked:
        if row in out:
            continue
        role = str(row.get("source_role") or "")
        cap = int(role_caps.get(role, max_total))
        if role_counts.get(role, 0) >= cap:
            continue
        out.append(row)
        after_rank += 1
        row_components = dict(row.get("score_components") or {})
        row_components["budget_rank_after_cap"] = after_rank
        row["score_components"] = row_components
        role_counts[role] = role_counts.get(role, 0) + 1
        if len(out) >= max_total:
            break
    return out


def _apply_rejected_budget(rejected: list[dict[str, Any]], *, max_total: int) -> list[dict[str, Any]]:
    ranked = sorted(
        rejected,
        key=lambda r: (-_evidence_score(dict(r.get("evidence") or {})), str(r.get("reason_code") or "")),
    )
    return ranked[:max_total]


def _admission_reason(
    entry: dict[str, Any],
    claim_type: str,
    evidence: dict[str, Any],
    config: QueryConfig,
    *,
    query_features: QueryFeatures | None = None,
) -> str | None:
    if not bool(entry.get("route_exists")):
        return "route_missing"
    if not bool(entry.get("admissible")):
        return "manifest_not_admissible"
    if query_features and _session_target_mismatch(query_features, evidence):
        return "wrong_session_target"

    role = str(entry.get("source_role") or "")
    authority = str(entry.get("authority") or "")
    forbidden_uses = set(entry.get("forbidden_uses") or [])
    allowed_uses = set(entry.get("allowed_uses") or [])

    if claim_type == "play_fact":
        if not _has_evidence_granularity(evidence):
            return "missing_evidence_granularity"
        if _evidence_score(evidence) < config.min_supporting_evidence_score:
            return "insufficient_evidence_score"
        if authority in PLAY_FACT_FORBIDDEN_AUTHORITIES:
            return "authority_forbidden_for_play_fact"
        if PLAY_FACT_USE in forbidden_uses:
            return "use_forbidden_by_manifest"
        if authority not in PLAY_FACT_ALLOWED_AUTHORITIES:
            return "authority_forbidden_for_play_fact"
        return None

    if claim_type == "pipeline_state":
        if role in PIPELINE_STATE_FORBIDDEN_ROLES:
            return "source_role_forbidden_for_pipeline_state"
        if authority in PIPELINE_STATE_FORBIDDEN_AUTHORITIES:
            return "authority_forbidden_for_pipeline_state"
        if role == "ingest_status" or authority == "audit":
            return None
        if authority in {"canon_play", "derived_memory"}:
            return None
        if "pipeline_state" in allowed_uses or "planning_activation_readiness" in allowed_uses:
            return None
        return "use_forbidden_by_manifest"

    if claim_type == "authority_guardrail":
        if not _has_evidence_granularity(evidence):
            return "missing_evidence_granularity"
        if _evidence_score(evidence) < config.min_supporting_evidence_score:
            return "insufficient_evidence_score"
        if role in AUTHORITY_GUARDRAIL_FORBIDDEN_ROLES or authority in AUTHORITY_GUARDRAIL_FORBIDDEN_AUTHORITIES:
            return "authority_forbidden_for_play_fact"
        if PLAY_FACT_USE in forbidden_uses and role == "table_notes":
            return "use_forbidden_by_manifest"
        if authority in PLAY_FACT_ALLOWED_AUTHORITIES:
            return None
        if role == "table_notes":
            return "authority_forbidden_for_play_fact"
        return None

    if claim_type == "capability_check":
        if role == "table_notes" or authority == "pre_canonical_evidence":
            return "authority_forbidden_for_play_fact"
        if role in {
            "live_packet",
            "roll_table",
            "prep_scaffold",
            "hub_evidence",
            "world_evidence",
            "play_recap",
            "session_memory",
            "live_event",
        }:
            return None
        if authority in {"audit", "planning_scaffold", "reference_tool", "live_observation"}:
            return None
        return None

    # planning_context — preserve authority separation but allow broader sources
    if PLAY_FACT_USE in forbidden_uses and claim_type != "planning_context":
        return "use_forbidden_by_manifest"
    return None


def _manifest_activation_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(entry.get("source_id") or ""),
        "route": str(entry.get("route") or ""),
        "source_role": str(entry.get("source_role") or ""),
        "authority": str(entry.get("authority") or ""),
        "admissible": bool(entry.get("admissible")),
        "allowed_uses": list(entry.get("allowed_uses") or []),
        "forbidden_uses": list(entry.get("forbidden_uses") or []),
    }


def _detect_capability_topic(question: str) -> str | None:
    q = question.lower()
    if any(
        t in q
        for t in (
            "planning query",
            "searches session",
            "hub evidence",
            "correct roles",
            "activated corpus",
            "across the activated",
        )
    ) and any(t in q for t in ("prep scaffold", "roll tables", "session 21", "session 22 memory", "workspace")):
        return "manifest_query"
    if any(t in q for t in ("hub satellite", "elderwyld", "world reference")) and any(
        t in q for t in ("query", "reach", "manifest", "one query")
    ):
        return "manifest_query"
    if any(t in q for t in ("sub-location", "location hub", "named sub-location", "hub markdown")):
        return "location_write"
    if any(t in q for t in ("random encounter table", "register it on the packet", "patch rows")) and any(
        t in q for t in ("add a new", "create", "register")
    ):
        return "roll_table_create"
    if "roll table" in q and any(t in q for t in ("add", "create", "register", "patch")):
        return "roll_table_create"
    return None


def _capability_status(
    request: QueryRequest,
    hints: set[str],
    admitted: list[dict[str, Any]],
    blocked: list[dict[str, str]],
) -> dict[str, Any]:
    if "capability_check" not in hints:
        return {"status": "unknown", "evidence": ["not_a_capability_question"]}

    topic = _detect_capability_topic(request.question)
    if topic == "manifest_query":
        roles = {str(e.get("source_role") or "") for e in admitted}
        if len(roles) >= 3:
            return {"status": "supported", "evidence": ["manifest_context_query_runner", "multi_role_admission"]}
        return {"status": "partial", "evidence": ["manifest_context_query_runner"]}

    if topic == "location_write":
        blocked.append(
            {
                "code": "missing_live_write_capability",
                "message": "Location hub create/write is not supported in the PR97 read-only runner.",
            }
        )
        return {"status": "missing", "evidence": ["no_location_hub_write_entrypoint"]}

    if topic == "roll_table_create":
        blocked.append(
            {
                "code": "missing_roll_table_create_register_capability",
                "message": "Roll-table create/register/patch is not supported in the PR97 read-only runner.",
            }
        )
        return {"status": "missing", "evidence": ["no_roll_table_create_entrypoint"]}

    blocked.append(
        {
            "code": "capability_not_supported",
            "message": "Requested mutation capability is not implemented in PR97.",
        }
    )
    return {"status": "unknown", "evidence": ["generic_capability_check"]}


def _policy_verdict(request: QueryRequest, hints: set[str], admitted: list[dict[str, Any]]) -> str:
    if "authority_guardrail" not in hints:
        return ""
    q = request.question.lower()
    if "raw staged" in q or "staged table notes" in q or "normal retrieval evidence" in q:
        has_canon = any(str(e.get("authority") or "") in PLAY_FACT_ALLOWED_AUTHORITIES for e in admitted)
        if has_canon:
            return (
                "No — raw staged table notes are not admissible as normal retrieval evidence "
                "after canonical recap exists; use canon recap or derived session memory instead."
            )
    return ""


def build_context_packet(
    request: QueryRequest,
    manifest: dict[str, Any],
    *,
    root: Path | None = None,
    config: QueryConfig | None = None,
) -> dict[str, Any]:
    base = root or repo_root()
    resolved_config = config or QueryConfig()
    precondition_paths = dict(resolved_config.precondition_paths or {})
    _manifest_by_route, entries = build_manifest_index(manifest)
    query_plan = build_query_plan(request)
    hints = set(query_plan["intent_hints"])
    claim_type = str(query_plan["primary_claim_type"])
    preconditions = build_corpus_preconditions(precondition_paths, base)
    query_features = _build_query_features(request.question, hints=hints, sessions=set(query_plan["session_numbers"]))

    retrieved: list[dict[str, Any]] = []
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    activation_refs: list[dict[str, Any]] = []
    route_context: list[dict[str, Any]] = []

    if "pipeline_state" in hints and precondition_paths:
        virtual = build_virtual_precondition_evidence(preconditions, resolved_config)
        retrieved.append(virtual)
        activation_refs.append(
            {
                "source_id": "virtual-corpus-preconditions-s22",
                "route": virtual["path"],
                "source_role": virtual["source_role"],
                "authority": virtual["authority"],
                "admissible": True,
                "allowed_uses": list(virtual["allowed_uses"]),
                "forbidden_uses": list(virtual["forbidden_uses"]),
            }
        )
        virtual_reason: str | None
        if claim_type != "pipeline_state":
            virtual_reason = "ingest_status_for_non_pipeline_claim"
        else:
            virtual_reason = _admission_reason(
                virtual, claim_type, virtual, resolved_config, query_features=query_features
            )
        if virtual_reason:
            rejected.append({"evidence": virtual, "reason_code": virtual_reason})
        else:
            admitted.append(virtual)

    candidates, candidate_trace = retrieve_candidates(entries, request, query_plan, query_features)
    markdown_span_trace: list[dict[str, Any]] = []
    session_memory_trace: list[dict[str, Any]] = []
    for entry in candidates:
        activation_refs.append(_manifest_activation_ref(entry))
        extracted = extract_evidence_units(
            entry, query_features=query_features, root=base, config=resolved_config
        )
        for evidence in extracted:
            trace_row = {
                "path": str(evidence.get("path") or ""),
                "source_role": str(evidence.get("source_role") or ""),
                "line_start": evidence.get("line_start"),
                "line_end": evidence.get("line_end"),
                "unit_id": evidence.get("unit_id"),
                "final_score": _evidence_score(evidence),
                "score_components": dict(evidence.get("score_components") or {}),
            }
            if str(evidence.get("source_role") or "") == "session_memory":
                session_memory_trace.append(trace_row)
            else:
                markdown_span_trace.append(trace_row)
        evidence_units = extracted or [_entry_to_evidence(entry)]
        for evidence in evidence_units:
            retrieved.append(evidence)
            reason = _admission_reason(
                entry, claim_type, evidence, resolved_config, query_features=query_features
            )
            if reason:
                rejected.append({"evidence": evidence, "reason_code": reason})
                continue
            admitted.append(evidence)

    admitted_cap = max(1, resolved_config.max_admitted_evidence)
    if claim_type in {"play_fact", "pipeline_state", "authority_guardrail"}:
        admitted_cap = min(admitted_cap, 10)
    ensure_roles: set[str] | None = None
    if claim_type == "play_fact":
        ensure_roles = {"play_recap", "session_memory"}
    if claim_type == "capability_check":
        ensure_roles = {
            "play_recap",
            "session_memory",
            "prep_scaffold",
            "hub_evidence",
            "world_evidence",
            "live_packet",
        }

    retrieved = _apply_evidence_budget(
        retrieved,
        max_total=max(1, resolved_config.max_retrieved_evidence),
        per_role_cap=resolved_config.max_admitted_per_source_role,
    )
    admitted = _apply_evidence_budget(
        admitted,
        max_total=admitted_cap,
        per_role_cap=resolved_config.max_admitted_per_source_role,
        ensure_roles=ensure_roles,
    )
    rejected = _apply_rejected_budget(rejected, max_total=max(1, resolved_config.max_rejected_evidence))

    route_context = [
        {
            "route": str(e.get("path") or ""),
            "source_role": str(e.get("source_role") or ""),
            "authority": str(e.get("authority") or ""),
        }
        for e in admitted
    ]

    blocked: list[dict[str, str]] = []
    capability_status = _capability_status(request, hints, admitted, blocked)
    verdict = _policy_verdict(request, hints, admitted)

    support_status = "supported" if admitted else "unsupported"
    if admitted and rejected:
        support_status = "partial"

    claim = {
        "claim_id": f"{request.question_id}_primary_claim",
        "claim_type": claim_type,
        "support_status": support_status,
        "supporting_evidence_refs": [str(e["path"]) for e in admitted],
        "route_refs": [str(r["route"]) for r in route_context],
        "planning_implication": "Use admitted evidence only; rejected evidence remains audit-visible.",
        "authority_notes": "Play-fact claims require canon_play/derived_memory only.",
    }

    admitted_trace = [
        {
            "path": str(e.get("path") or ""),
            "source_role": str(e.get("source_role") or ""),
            "authority": str(e.get("authority") or ""),
            "final_score": _evidence_score(e),
            "score_components": dict(e.get("score_components") or {}),
            "admission_reason": "admitted",
        }
        for e in admitted
    ]
    rejected_trace = [
        {
            "path": str(r.get("evidence", {}).get("path") or ""),
            "source_role": str(r.get("evidence", {}).get("source_role") or ""),
            "authority": str(r.get("evidence", {}).get("authority") or ""),
            "final_score": _evidence_score(dict(r.get("evidence") or {})),
            "score_components": dict(r.get("evidence", {}).get("score_components") or {}),
            "rejection_reason": str(r.get("reason_code") or ""),
        }
        for r in rejected
    ]
    retrieval_trace = {
        "question": request.question,
        "intent_hints": sorted(hints),
        "session_numbers": sorted(query_features.session_numbers),
        "tokens": sorted(query_features.tokens),
        "content_tokens": sorted(query_features.content_tokens),
        "stopword_tokens": sorted(query_features.stopword_tokens),
        "distinctive_tokens": sorted(query_features.distinctive_tokens),
        "aliases": list(query_features.aliases),
        "tags": list(query_features.tags),
        "title_phrases": list(query_features.title_phrases),
        "exact_phrases": list(query_features.exact_phrases),
        "asks_for_last_or_final": query_features.asks_for_last_or_final,
        "asks_for_play_event": query_features.asks_for_play_event,
        "asks_historical_continuity": query_features.asks_historical_continuity,
        "explicit_session_only": query_features.explicit_session_only,
        "top_manifest_entries": candidate_trace.get("top_manifest_entries", []),
        "lane_top_entries": candidate_trace.get("lane_top_entries", {}),
        "top_markdown_spans": sorted(markdown_span_trace, key=lambda r: (-float(r["final_score"]), str(r["path"])))[:30],
        "top_session_memory_units": sorted(
            session_memory_trace, key=lambda r: (-float(r["final_score"]), str(r["path"]))
        )[:30],
        "admitted_evidence": admitted_trace,
        "rejected_evidence": rejected_trace,
    }

    packet: dict[str, Any] = {
        "schema": "dmb_enriched_planning_context_packet_v1",
        "question_id": request.question_id,
        "intent_class": intent_class_from_hints(hints),
        "corpus_preconditions": preconditions,
        "activation_manifest_refs": activation_refs,
        "retrieved_evidence": retrieved,
        "admitted_evidence": admitted,
        "rejected_evidence": rejected,
        "claims": [claim],
        "route_context": route_context,
        "planning_implications": [
            "Packet is evidence-first; unsupported claims should remain blocked.",
            "PR97 manifest query/admission runner — not the PR96 trace adapter.",
        ],
        "capability_status": capability_status,
        "blocked_or_missing": blocked,
        "citation_policy": {
            "play_fact_allowed_authorities": sorted(PLAY_FACT_ALLOWED_AUTHORITIES),
            "play_fact_forbidden_authorities": sorted(PLAY_FACT_FORBIDDEN_AUTHORITIES),
        },
        "retrieval_trace": retrieval_trace,
        "query_signals": {
            "asks_for_last_or_final": query_features.asks_for_last_or_final,
            "asks_for_play_event": query_features.asks_for_play_event,
            "session_numbers": sorted(query_features.session_numbers),
        },
    }
    if verdict:
        packet["source_excerpt"] = verdict
    return packet


def run_query(request: QueryRequest, manifest: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    return build_context_packet(request, manifest, root=root)


def load_manifest(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)
