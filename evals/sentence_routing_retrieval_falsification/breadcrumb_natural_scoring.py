"""Scoring helpers mirrored from ``run_council_room_question_set.py`` (retrieval context grading).

Keeps breadcrumb benchmarks independent of ``DungeonBuddyCLI`` / fact-store imports.
"""

from __future__ import annotations

import re
from typing import Any

GLOBAL_STALE_PATTERNS = (
    "nothing changed",
    "no changes",
    "no observed or prep",
    "no observed updates",
    "no observed facts",
    "architecturally unchanged",
)

UPDATE_SIGNAL_TOKENS = (
    "observed",
    "disheveled",
    "activated",
    "fireball",
    "killing blow",
    "decapitated",
    "dead",
    "fades",
)

# Subset of council-room globals useful for Longmont recap prose.
SEMANTIC_EQUIVALENCES: dict[str, list[str]] = {
    "captain": ["lysandra", "captain lysandra", "ironveil"],
    "forest": ["migrating forest", "the forest"],
    "tower": ["voices tower", "tower drawing", "drawing"],
    "voices": ["voice", "tower"],
}


def _normalize_text(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _token_negated_by_cooccurrence(
    *,
    token: str,
    answer_lower: str,
    must_not_cooccur: dict[str, list[str]] | None,
) -> bool:
    if not must_not_cooccur:
        return False
    normalized_token = _normalize_text(token).lower()
    for key, negations in must_not_cooccur.items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for phrase in negations:
            if _normalize_text(phrase).lower() in answer_lower:
                return True
    return False


def classify_answer(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if _normalize_text(token).lower() not in lower_answer:
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    if update_signal_tokens is None:
        effective_update_tokens = list(UPDATE_SIGNAL_TOKENS)
    else:
        effective_update_tokens = update_signal_tokens
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif len(must_hits) >= max(1, len(must_tokens) - 1) and not stale_state:
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def _semantic_token_present(
    token: str,
    answer_lower: str,
    question_equivalences: dict[str, list[str]] | None = None,
) -> bool:
    normalized_token = _normalize_text(token).lower()
    if normalized_token in answer_lower:
        return True
    for key, values in (question_equivalences or {}).items():
        if _normalize_text(key).lower() != normalized_token:
            continue
        for equiv in values:
            if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
                return True
    for equiv in SEMANTIC_EQUIVALENCES.get(normalized_token, []):
        if re.search(_normalize_text(equiv), answer_lower, re.IGNORECASE):
            return True
    return False


def classify_answer_semantic(
    *,
    must_tokens: list[str],
    stale_tokens: list[str],
    answer: str,
    has_error: bool,
    question_equivalences: dict[str, list[str]] | None = None,
    update_signal_tokens: list[str] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[str, list[str], list[str], list[str]]:
    lower_answer = _normalize_text(answer).lower()
    must_hits: list[str] = []
    for token in must_tokens:
        if not _semantic_token_present(token, lower_answer, question_equivalences):
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_answer,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        must_hits.append(token)
    stale_hits = [
        token for token in stale_tokens if _normalize_text(token).lower() in lower_answer
    ]
    global_stale_hits = [
        pattern
        for pattern in GLOBAL_STALE_PATTERNS
        if _normalize_text(pattern).lower() in lower_answer
    ]
    if update_signal_tokens is None:
        effective_update_tokens = list(UPDATE_SIGNAL_TOKENS)
    else:
        effective_update_tokens = update_signal_tokens
    update_signal_hits = [
        token
        for token in effective_update_tokens
        if _normalize_text(token).lower() in lower_answer
    ]

    stale_state = bool(global_stale_hits) or (
        bool(stale_hits) and not must_hits and not update_signal_hits
    )
    if has_error:
        verdict = "fail_error"
    elif len(must_hits) >= max(1, len(must_tokens) - 1) and not stale_state:
        verdict = "pass_updated"
    elif stale_state:
        verdict = "fail_stale"
    else:
        verdict = "fail_incomplete"

    return verdict, must_hits, stale_hits, global_stale_hits


def score_context_support(
    *,
    must_tokens: list[str],
    context: str,
    question_equivalences: dict[str, list[str]] | None = None,
    must_not_cooccur: dict[str, list[str]] | None = None,
) -> tuple[list[str], float]:
    lower_context = _normalize_text(context).lower()
    if not must_tokens:
        return [], 1.0
    hits: list[str] = []
    for token in must_tokens:
        if not _semantic_token_present(token, lower_context, question_equivalences):
            continue
        if _token_negated_by_cooccurrence(
            token=token,
            answer_lower=lower_context,
            must_not_cooccur=must_not_cooccur,
        ):
            continue
        hits.append(token)
    return hits, len(hits) / max(1, len(must_tokens))


def classify_failure_surface(
    *,
    semantic_verdict: str,
    context_support_ratio: float,
) -> str:
    if semantic_verdict == "pass_updated":
        return "pass"
    if context_support_ratio < 0.5:
        return "retrieval_gap"
    return "synthesis_gap"


def index_records_by_unit_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("unit_id", "")): r for r in records if r.get("unit_id")}


def build_hit_context_text(
    hits: list[dict[str, Any]],
    by_unit: dict[str, dict[str, Any]],
) -> str:
    parts: list[str] = []
    for h in hits:
        uid = str(h.get("unit_id", "") or "")
        rec = by_unit.get(uid)
        if not rec:
            continue
        lp = str(rec.get("lexical_plain", "") or "").strip()
        if lp:
            parts.append(lp)
        for rt in rec.get("routes") or []:
            nr = str(rt.get("normalized_route", "") or "").strip()
            if nr:
                parts.append(nr)
    return "\n".join(parts)
