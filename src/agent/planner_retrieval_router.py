"""Retrieval-first planner router.

Decides whether deterministic retrieval over the session-memory index supplies
enough evidence to answer a query directly (``answer_now``) or whether the
caller should escalate to a full corpus-grounded planner turn
(``need_more_context``). The router is intentionally a thin, model-agnostic
controller around :func:`src.agent.session_memory_query.query_session_memory_candidate`
so its decisions are deterministic and falsifiable in unit tests.

This module is **read-only with respect to existing planner state**:

* It never instantiates an OpenAI client.
* It never mutates the planner cache, telemetry sinks, or tool dispatchers.
* Callers compose it with ``run_planning_turn_detailed`` separately.

The decision contract is:

* ``answer_now`` — retrieval evidence is dense enough that the harness can
  synthesize a grounded answer directly from the retrieved hit context. The
  caller still needs an LLM (or a deterministic policy) to render prose; the
  router only signals sufficiency.
* ``need_more_context`` — escalate to corpus reads. The router emits machine
  readable ``failure_reasons`` plus an optional ordered ``suggested_read_paths``
  hint that callers may log in telemetry/artifacts but **must not** inject into
  user-facing prompt text (per ``llm-context-discovery.mdc``).

All thresholds live in :class:`SufficiencyConfig` so cohorts can A/B them
without touching the policy implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agent.session_memory_query import (
    CandidateQueryResult,
    query_session_memory_candidate,
)

#: Schema string baked into router result payloads so artifacts are versioned.
ROUTER_DECISION_SCHEMA_V1 = "dmb_planner_retrieval_router_decision_v1"

#: Canonical decision labels.
DECISION_ANSWER_NOW = "answer_now"
DECISION_NEED_MORE_CONTEXT = "need_more_context"

_VALID_DECISIONS = frozenset({DECISION_ANSWER_NOW, DECISION_NEED_MORE_CONTEXT})

#: Stable machine codes for sufficiency-gate failures (one per checked condition).
REASON_NO_MATCHED_RECORDS = "no_matched_records"
REASON_INSUFFICIENT_MATCHED_RECORDS = "insufficient_matched_records"
REASON_LOW_TOP_HIT_STRENGTH = "low_top_hit_strength"
REASON_INSUFFICIENT_HITS = "insufficient_hits"
REASON_MISSING_ROUTE_ANCHOR = "missing_route_anchor"
REASON_INSUFFICIENT_CONTEXT_DENSITY = "insufficient_context_density"
REASON_EXPANSION_SATURATED = "expansion_saturated"


@dataclass(frozen=True)
class SufficiencyConfig:
    """Tunable thresholds for the deterministic sufficiency gate.

    Each threshold contributes one explainable reason code on failure. The
    defaults are calibrated for the breadcrumb-query benchmark (Session 20)
    and intentionally conservative — escalating in doubt — so cohorts trade
    cost against escalation rate, not silent answer-now failures.
    """

    #: Minimum matched-record count from the deterministic scorer. Below this,
    #: the lexical surface is so sparse the answer is almost certainly not
    #: in the index (``REASON_INSUFFICIENT_MATCHED_RECORDS``).
    min_matched_records: int = 2

    #: Minimum number of returned hits (post-expansion). Below this, the
    #: caller cannot reasonably synthesize without escalating
    #: (``REASON_INSUFFICIENT_HITS``).
    min_hits: int = 3

    #: Minimum lexical+route score for the top hit. The scorer awards 1 point
    #: per lexical token match and 3 per route token match (see
    #: ``_score_record``); a top hit ≥3 means at least one route or three
    #: lexical tokens fired (``REASON_LOW_TOP_HIT_STRENGTH``).
    min_top_hit_score: int = 3

    #: Minimum fraction of the ``required_route_anchors`` that must appear in
    #: at least one hit's normalized routes (``REASON_MISSING_ROUTE_ANCHOR``).
    #: When the caller does not provide any anchors, this check is skipped.
    min_route_anchor_recall: float = 1.0

    #: Minimum fraction of distinct query tokens that appear in the hit
    #: ``why_matched`` evidence aggregated across the top hits
    #: (``REASON_INSUFFICIENT_CONTEXT_DENSITY``).
    min_context_density: float = 0.5

    #: Maximum fraction of expansion slots that may be filled before treating
    #: the result as expansion-saturated and untrustworthy
    #: (``REASON_EXPANSION_SATURATED``). Use 1.0 (default) to disable.
    max_expansion_fill_ratio: float = 1.0


@dataclass(frozen=True)
class RetrievalEvidence:
    """Structured retrieval evidence pulled from a :class:`CandidateQueryResult`.

    The ``trace`` mirrors the underlying retrieval trace verbatim so downstream
    artifacts can still be reconstructed without re-running retrieval.
    """

    hits: list[dict[str, Any]]
    trace: dict[str, Any]
    top_hit_score: int
    matched_records: int
    returned_hits: int
    route_anchor_recall: float | None
    context_density: float
    why_matched_tokens: list[str]
    expansion_fill_ratio: float


@dataclass(frozen=True)
class EscalationRequest:
    """Hint payload for ``need_more_context`` decisions.

    ``suggested_read_paths`` is **strictly optional** and must never be merged
    into the user-facing prompt (see ``llm-context-discovery.mdc``). It exists
    so escalation callers can log "we expected the planner would still need
    these files" alongside the resulting trace for offline review.
    """

    failure_reasons: list[str]
    missing_signals: dict[str, Any]
    suggested_read_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalDecisionResult:
    """End-to-end router output, JSON-serializable."""

    schema: str
    decision: str
    query: str
    campaign_id: str
    config: dict[str, Any]
    evidence: RetrievalEvidence
    escalation: EscalationRequest | None
    failure_reasons: list[str]
    confidence_features: dict[str, Any]

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "decision": self.decision,
            "query": self.query,
            "campaign_id": self.campaign_id,
            "config": dict(self.config),
            "evidence": {
                "hits": list(self.evidence.hits),
                "trace": dict(self.evidence.trace),
                "top_hit_score": int(self.evidence.top_hit_score),
                "matched_records": int(self.evidence.matched_records),
                "returned_hits": int(self.evidence.returned_hits),
                "route_anchor_recall": self.evidence.route_anchor_recall,
                "context_density": float(self.evidence.context_density),
                "why_matched_tokens": list(self.evidence.why_matched_tokens),
                "expansion_fill_ratio": float(self.evidence.expansion_fill_ratio),
            },
            "escalation": (
                None
                if self.escalation is None
                else {
                    "failure_reasons": list(self.escalation.failure_reasons),
                    "missing_signals": dict(self.escalation.missing_signals),
                    "suggested_read_paths": list(self.escalation.suggested_read_paths),
                }
            ),
            "failure_reasons": list(self.failure_reasons),
            "confidence_features": dict(self.confidence_features),
        }


def _config_as_dict(config: SufficiencyConfig) -> dict[str, Any]:
    return {
        "min_matched_records": int(config.min_matched_records),
        "min_hits": int(config.min_hits),
        "min_top_hit_score": int(config.min_top_hit_score),
        "min_route_anchor_recall": float(config.min_route_anchor_recall),
        "min_context_density": float(config.min_context_density),
        "max_expansion_fill_ratio": float(config.max_expansion_fill_ratio),
    }


def _query_tokens_from_trace(trace: dict[str, Any]) -> list[str]:
    raw = trace.get("query_tokens")
    if not isinstance(raw, list):
        return []
    return [str(t) for t in raw if str(t).strip()]


def _why_matched_tokens(hits: list[dict[str, Any]]) -> list[str]:
    """Distinct tokens appearing in any hit's ``why_matched`` (order preserved)."""
    out: list[str] = []
    seen: set[str] = set()
    for h in hits:
        for entry in h.get("why_matched") or []:
            s = str(entry)
            # ``_score_record`` emits ``lexical_token:<t>`` and ``route_token:<t>``
            # plus expansion tags such as ``expanded_adjacent:<uid>``. Only the
            # token reasons measure context density.
            for prefix in ("lexical_token:", "route_token:"):
                if s.startswith(prefix):
                    tok = s[len(prefix):]
                    if tok and tok not in seen:
                        seen.add(tok)
                        out.append(tok)
                    break
    return out


def _route_anchor_recall(
    hits: list[dict[str, Any]],
    anchors: list[str],
) -> tuple[float | None, list[str]]:
    """Return (recall, missing_anchors) for required normalized-route substrings."""
    if not anchors:
        return None, []
    blob_parts: list[str] = []
    for h in hits:
        for r in h.get("routes") or []:
            if isinstance(r, dict):
                blob_parts.append(str(r.get("normalized_route") or "").lower())
            else:
                blob_parts.append(str(r).lower())
    blob = "\n".join(blob_parts)
    missing: list[str] = []
    matched = 0
    for needle in anchors:
        n = str(needle).strip().lower()
        if not n:
            continue
        if n in blob:
            matched += 1
        else:
            missing.append(needle)
    denom = sum(1 for n in anchors if str(n).strip())
    if denom == 0:
        return None, []
    return matched / denom, missing


def _expansion_fill_ratio(trace: dict[str, Any], returned: int) -> float:
    """Fraction of returned hits emitted by expansion (not first-pass)."""
    if returned <= 0:
        return 0.0
    expansion = trace.get("expansion") or {}
    if not isinstance(expansion, dict):
        return 0.0
    added = 0
    for k in ("added_adjacent", "added_shared_route", "added_route_family"):
        try:
            added += int(expansion.get(k) or 0)
        except (TypeError, ValueError):
            continue
    return added / max(returned, 1)


def _build_evidence(
    *,
    result: CandidateQueryResult,
    required_route_anchors: list[str],
) -> tuple[RetrievalEvidence, list[str]]:
    """Project a :class:`CandidateQueryResult` into router-shaped evidence."""
    hits = list(result.hits)
    trace = dict(result.trace or {})
    top_score = int(hits[0].get("score", 0)) if hits else 0
    matched = int(trace.get("matched_records") or 0)
    returned = int(trace.get("returned_hits") or len(hits))
    route_recall, missing = _route_anchor_recall(hits, required_route_anchors)
    why_tokens = _why_matched_tokens(hits)
    query_tokens = _query_tokens_from_trace(trace)
    if query_tokens:
        density = len(why_tokens) / len(query_tokens)
    else:
        density = 1.0 if why_tokens else 0.0
    expansion_fill = _expansion_fill_ratio(trace, returned)
    return (
        RetrievalEvidence(
            hits=hits,
            trace=trace,
            top_hit_score=top_score,
            matched_records=matched,
            returned_hits=returned,
            route_anchor_recall=route_recall,
            context_density=density,
            why_matched_tokens=why_tokens,
            expansion_fill_ratio=expansion_fill,
        ),
        missing,
    )


def _suggested_paths_from_hits(hits: list[dict[str, Any]], limit: int = 6) -> list[str]:
    """Distinct ``source_recap_path`` values from the top hits (order preserved)."""
    out: list[str] = []
    seen: set[str] = set()
    for h in hits:
        p = str(h.get("source_recap_path") or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= limit:
            break
    return out


def evaluate_sufficiency(
    *,
    evidence: RetrievalEvidence,
    config: SufficiencyConfig,
    required_route_anchors: list[str] | None = None,
    missing_route_anchors: list[str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Apply the deterministic sufficiency gate.

    Returns ``(failure_reasons, missing_signals)``. Reasons are emitted in
    declaration order so cohort reports group consistently.
    """
    reasons: list[str] = []
    missing: dict[str, Any] = {}

    if evidence.matched_records <= 0:
        reasons.append(REASON_NO_MATCHED_RECORDS)
        missing["matched_records"] = evidence.matched_records
    elif evidence.matched_records < config.min_matched_records:
        reasons.append(REASON_INSUFFICIENT_MATCHED_RECORDS)
        missing["matched_records"] = {
            "actual": evidence.matched_records,
            "required": int(config.min_matched_records),
        }

    if evidence.returned_hits < config.min_hits:
        reasons.append(REASON_INSUFFICIENT_HITS)
        missing["returned_hits"] = {
            "actual": evidence.returned_hits,
            "required": int(config.min_hits),
        }

    if evidence.top_hit_score < config.min_top_hit_score:
        reasons.append(REASON_LOW_TOP_HIT_STRENGTH)
        missing["top_hit_score"] = {
            "actual": evidence.top_hit_score,
            "required": int(config.min_top_hit_score),
        }

    if required_route_anchors:
        recall = evidence.route_anchor_recall
        if recall is None or recall + 1e-9 < config.min_route_anchor_recall:
            reasons.append(REASON_MISSING_ROUTE_ANCHOR)
            missing["route_anchors"] = {
                "required": list(required_route_anchors),
                "missing": list(missing_route_anchors or []),
                "recall": recall,
                "required_recall": float(config.min_route_anchor_recall),
            }

    if evidence.context_density + 1e-9 < config.min_context_density:
        reasons.append(REASON_INSUFFICIENT_CONTEXT_DENSITY)
        missing["context_density"] = {
            "actual": float(evidence.context_density),
            "required": float(config.min_context_density),
        }

    if (
        config.max_expansion_fill_ratio < 1.0
        and evidence.expansion_fill_ratio > config.max_expansion_fill_ratio + 1e-9
    ):
        reasons.append(REASON_EXPANSION_SATURATED)
        missing["expansion_fill_ratio"] = {
            "actual": float(evidence.expansion_fill_ratio),
            "max": float(config.max_expansion_fill_ratio),
        }

    return reasons, missing


def run_retrieval_first_decision(
    *,
    query: str,
    records: list[dict[str, Any]],
    campaign_id: str,
    query_spec: dict[str, Any] | None = None,
    config: SufficiencyConfig | None = None,
    required_route_anchors: list[str] | None = None,
) -> RetrievalDecisionResult:
    """Run retrieval over ``records`` and return a sufficiency-gated decision.

    ``query_spec`` mirrors the shape used by ``breadcrumb_query_run`` /
    ``natural_retrieval_bundle`` so router cohorts and benchmark cohorts share
    the same retrieval call. When omitted, the router falls back to defaults
    that match :func:`query_session_memory_candidate` (no expansion, default
    tokenizer, etc.).

    The router itself does not call any LLM and does not mutate ``records``.
    """
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required for run_retrieval_first_decision")
    cfg = config or SufficiencyConfig()
    spec = dict(query_spec or {})

    def _opt_int(key: str, default: int | None = None) -> int | None:
        if key not in spec or spec[key] is None or spec[key] == "":
            return default
        return int(spec[key])

    result = query_session_memory_candidate(
        records=records,
        query=q,
        campaign_id=str(campaign_id or "").strip(),
        subject_route=spec.get("subject_route"),
        session_min=_opt_int("session_min"),
        session_max=_opt_int("session_max"),
        subject_types=spec.get("subject_types") if isinstance(spec.get("subject_types"), list) else None,
        proposed_only=bool(spec.get("proposed_only", False)),
        max_hits=_opt_int("max_hits", 12) or 12,
        expand_context=bool(spec.get("expand_context", False)),
        expand_seed_hits=_opt_int("expand_seed_hits", 5) or 5,
        expand_adjacent_window=_opt_int("expand_adjacent_window", 2) or 0,
        expand_shared_route_limit=_opt_int("expand_shared_route_limit", 3) or 0,
        expand_route_family_limit=_opt_int("expand_route_family_limit", 3) or 0,
        expand_first_pass_cap=_opt_int("expand_first_pass_cap"),
        expansion_allocation_mode=str(spec.get("expansion_allocation_mode", "round_robin")),
        tokenizer_mode=str(spec.get("tokenizer_mode", "default")),
        query_token_aliases=(
            [str(x) for x in spec.get("query_token_aliases", [])]
            if isinstance(spec.get("query_token_aliases"), list)
            else None
        ),
    )

    anchors = list(required_route_anchors or [])
    evidence, missing_anchors = _build_evidence(
        result=result,
        required_route_anchors=anchors,
    )
    reasons, missing_signals = evaluate_sufficiency(
        evidence=evidence,
        config=cfg,
        required_route_anchors=anchors,
        missing_route_anchors=missing_anchors,
    )

    if reasons:
        decision = DECISION_NEED_MORE_CONTEXT
        escalation: EscalationRequest | None = EscalationRequest(
            failure_reasons=list(reasons),
            missing_signals=dict(missing_signals),
            suggested_read_paths=_suggested_paths_from_hits(evidence.hits),
        )
    else:
        decision = DECISION_ANSWER_NOW
        escalation = None

    if decision not in _VALID_DECISIONS:  # pragma: no cover - defensive
        raise ValueError(f"router emitted invalid decision {decision!r}")

    confidence_features = {
        "matched_records": evidence.matched_records,
        "returned_hits": evidence.returned_hits,
        "top_hit_score": evidence.top_hit_score,
        "route_anchor_recall": evidence.route_anchor_recall,
        "context_density": float(evidence.context_density),
        "expansion_fill_ratio": float(evidence.expansion_fill_ratio),
        "query_tokens": _query_tokens_from_trace(evidence.trace),
    }

    return RetrievalDecisionResult(
        schema=ROUTER_DECISION_SCHEMA_V1,
        decision=decision,
        query=q,
        campaign_id=str(campaign_id or "").strip(),
        config=_config_as_dict(cfg),
        evidence=evidence,
        escalation=escalation,
        failure_reasons=list(reasons),
        confidence_features=confidence_features,
    )
