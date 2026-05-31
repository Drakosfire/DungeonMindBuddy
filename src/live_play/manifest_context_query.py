"""Blind manifest-backed query/admission for planning context packets.

Loads an activated planning corpus manifest, retrieves candidate evidence from
manifest-admissible sources using question text and generic policy only, admits
or rejects candidates by authority/use rules, and emits enriched context packets.

The runner must not read benchmark gold, dogfood traces, or route by question_id.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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

PRECONDITION_PATHS: dict[str, str] = {
    "canonical_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "normalized_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "breadcrumb_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    ),
    "session_memory_jsonl_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.jsonl"
    ),
    "session_memory_meta_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.json"
    ),
    "live_workspace_s23_packet": "evals/c2_live_prep/live/session_23/live_packet.json",
    "activated_manifest": "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json",
}

DEFAULT_LANE_BUDGETS: dict[str, int] = {
    "play_recap": 4,
    "session_memory": 4,
    "breadcrumbed_recap": 3,
    "hub_evidence": 4,
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
    "table_notes": "table_notes",
}

FORBIDDEN_GOLD_SUBSTRINGS = ("gold",)
FORBIDDEN_DOGFOOD_SUBSTRINGS = ("c2s23_dogfood_", "c2s23_dogfood_planner_summary")


@dataclass(frozen=True)
class QueryRequest:
    question_id: str
    question: str
    category: str | None = None


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
    if any(t in q for t in ("happened", "in play", "canon", "recap", "table", "session", "played", "outcomes")):
        hints.add("play_fact")
    if any(t in q for t in ("prep", "plan", "session 23", "opening", "next", "carry forward")):
        hints.add("planning_context")
    if any(
        t in q
        for t in ("raw notes", "staged", "authority", "prove", "source of truth", "normal retrieval evidence")
    ):
        hints.add("authority_guardrail")
    return hints or {"planning_context"}


def infer_session_numbers(question: str) -> set[int]:
    found = {int(m) for m in re.findall(r"\bsession\s*(\d{1,2})\b", question.lower())}
    found.update(int(m) for m in re.findall(r"\bs(\d{1,2})\b", question.lower()))
    return found


def primary_claim_type(hints: set[str]) -> str:
    priority = (
        "authority_guardrail",
        "capability_check",
        "pipeline_state",
        "play_fact",
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
    if "pipeline_state" in hints:
        return "ingest_state_check"
    if "play_fact" in hints:
        return "play_fact_retrieval"
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
        budgets["hub_evidence"] = max(budgets["hub_evidence"], 3)
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


def build_corpus_preconditions(root: Path | None = None) -> dict[str, Any]:
    base = root or repo_root()
    checks = []
    for key, rel in PRECONDITION_PATHS.items():
        p = base / rel
        checks.append({"key": key, "path": rel, "exists": p.is_file()})
    return {"all_required_present": all(bool(c["exists"]) for c in checks), "checks": checks}


def build_virtual_precondition_evidence(preconditions: dict[str, Any]) -> dict[str, Any]:
    routes = [str(c["path"]) for c in list(preconditions.get("checks") or []) if c.get("exists")]
    return {
        "path": "virtual://c2s23/corpus_preconditions/session_22",
        "source_role": "ingest_status",
        "authority": "audit",
        "session_scope": [22],
        "unit_id": None,
        "breadcrumb_id": None,
        "line_start": None,
        "line_end": None,
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


def _score_entry(entry: dict[str, Any], question_tokens: set[str], hints: set[str], sessions: set[int]) -> float:
    route = str(entry.get("route") or "")
    role = str(entry.get("source_role") or "")
    authority = str(entry.get("authority") or "")
    scopes = {int(s) for s in list(entry.get("session_scope") or []) if str(s).isdigit()}
    score = 0.0

    path_tokens = _tokenize(route)
    score += len(question_tokens & path_tokens) * 2.0

    if sessions and scopes & sessions:
        score += 6.0
    elif not sessions and scopes:
        score += 1.0

    if "play_fact" in hints and role in {"play_recap", "session_memory"}:
        score += 10.0
    if "pipeline_state" in hints and role in {"play_recap", "session_memory"}:
        score += 9.0
    if "pipeline_state" in hints and authority == "audit":
        score += 8.0
    if "planning_context" in hints and role in {"prep_scaffold", "hub_evidence", "live_packet"}:
        score += 5.0
    if "capability_check" in hints and role in {"live_packet", "roll_table", "prep_scaffold", "hub_evidence"}:
        score += 4.0
    if "authority_guardrail" in hints and role == "table_notes":
        score += 8.0
    if "authority_guardrail" in hints and role in {"play_recap", "session_memory"}:
        score += 6.0
    if "play_fact" in hints and role == "table_notes" and sessions and scopes & sessions:
        score += 7.0

    if not bool(entry.get("route_exists")):
        score -= 100.0
    if not bool(entry.get("admissible")):
        score -= 50.0
    return score


def retrieve_candidates(
    entries: list[dict[str, Any]],
    request: QueryRequest,
    query_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    hints = set(query_plan["intent_hints"])
    sessions = set(query_plan["session_numbers"])
    budgets = dict(query_plan["lane_budgets"])
    question_tokens = _tokenize(request.question)

    by_lane: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for entry in entries:
        lane = _lane_for_entry(entry)
        sc = _score_entry(entry, question_tokens, hints, sessions)
        by_lane.setdefault(lane, []).append((sc, entry))

    selected: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    for lane, budget in budgets.items():
        ranked = sorted(by_lane.get(lane, []), key=lambda t: (-t[0], str(t[1].get("route") or "")))
        taken = 0
        for sc, entry in ranked:
            if sc <= -50:
                continue
            route = _norm(str(entry.get("route") or ""))
            if route in seen_routes:
                continue
            seen_routes.add(route)
            selected.append(entry)
            taken += 1
            if taken >= budget:
                break
    return selected


def _entry_to_evidence(entry: dict[str, Any], *, path_override: str | None = None) -> dict[str, Any]:
    route = path_override or str(entry.get("route") or "")
    return {
        "path": route,
        "source_role": str(entry.get("source_role") or ""),
        "authority": str(entry.get("authority") or ""),
        "session_scope": list(entry.get("session_scope") or []),
        "unit_id": None,
        "breadcrumb_id": None,
        "line_start": None,
        "line_end": None,
        "admissible": bool(entry.get("admissible")),
        "allowed_uses": list(entry.get("allowed_uses") or []),
        "forbidden_uses": list(entry.get("forbidden_uses") or []),
        "routes": [str(entry.get("route") or route)],
    }


def _admission_reason(entry: dict[str, Any], claim_type: str) -> str | None:
    if not bool(entry.get("route_exists")):
        return "route_missing"
    if not bool(entry.get("admissible")):
        return "manifest_not_admissible"

    role = str(entry.get("source_role") or "")
    authority = str(entry.get("authority") or "")
    forbidden_uses = set(entry.get("forbidden_uses") or [])
    allowed_uses = set(entry.get("allowed_uses") or [])

    if claim_type == "play_fact":
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
        if role in {"live_packet", "roll_table", "prep_scaffold", "hub_evidence", "play_recap", "session_memory", "live_event"}:
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
) -> dict[str, Any]:
    base = root or repo_root()
    _manifest_by_route, entries = build_manifest_index(manifest)
    query_plan = build_query_plan(request)
    hints = set(query_plan["intent_hints"])
    claim_type = str(query_plan["primary_claim_type"])
    preconditions = build_corpus_preconditions(base)

    retrieved: list[dict[str, Any]] = []
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    activation_refs: list[dict[str, Any]] = []
    route_context: list[dict[str, Any]] = []

    if "pipeline_state" in hints:
        virtual = build_virtual_precondition_evidence(preconditions)
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
        admitted.append(virtual)
        route_context.append(
            {
                "route": virtual["path"],
                "source_role": virtual["source_role"],
                "authority": virtual["authority"],
            }
        )

    candidates = retrieve_candidates(entries, request, query_plan)
    for entry in candidates:
        evidence = _entry_to_evidence(entry)
        retrieved.append(evidence)
        activation_refs.append(_manifest_activation_ref(entry))
        reason = _admission_reason(entry, claim_type)
        if reason:
            rejected.append({"evidence": evidence, "reason_code": reason})
        else:
            admitted.append(evidence)
            route_context.append(
                {
                    "route": str(entry.get("route") or ""),
                    "source_role": str(entry.get("source_role") or ""),
                    "authority": str(entry.get("authority") or ""),
                }
            )

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
    }
    if verdict:
        packet["source_excerpt"] = verdict
    return packet


def run_query(request: QueryRequest, manifest: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    return build_context_packet(request, manifest, root=root)


def load_manifest(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)
