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

_PATH_LIKE_LEXICAL_RE = re.compile(r"^[A-Za-z0-9 _.'()&-]+(?:/[A-Za-z0-9 _.'()&-]+)+/?$")
_QUERY_SIGNAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "while",
    "with",
}

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


def _is_path_like_lexical_unit(text: str) -> bool:
    s = str(text or "").strip()
    if not s:
        return False
    return bool(_PATH_LIKE_LEXICAL_RE.fullmatch(s))


def _signal_query_tokens(query_tokens: list[str] | None) -> list[str]:
    out: list[str] = []
    for token in (query_tokens or []):
        t = _normalize_text(str(token)).lower().strip()
        if not t or t in _QUERY_SIGNAL_STOPWORDS or len(t) < 3:
            continue
        out.append(t)
    return out


def _lexical_token_hits_count(text_lower: str, query_tokens: list[str]) -> int:
    hits = 0
    for token in query_tokens:
        if re.search(rf"\b{re.escape(token)}\b", text_lower):
            hits += 1
    return hits


def _ranked_row_key(row: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    return (
        int(row.get("query_token_hits") or 0),
        int(row.get("why_lexical") or 0),
        int(row.get("score") or 0),
        -int(row.get("why_route") or 0),
        -int(row.get("why_expanded") or 0),
        -int(row.get("idx") or 0),
    )


def _unit_suffix(unit_id: str) -> int:
    """Sentence index from a ``u-L<line>-<sentence>`` unit_id; 0 when absent.

    Mirrors ``_unit_numeric_suffix`` in ``src/agent/session_memory_query.py`` so
    ``build_hit_context_text`` can break ``source_order`` ties on shared
    ``line_start`` by the recap's actual sentence order rather than retrieval rank.
    """
    parts = str(unit_id or "").split("-")
    if len(parts) >= 3 and parts[-1].isdigit():
        return int(parts[-1])
    return 0


def build_hit_context_text(
    hits: list[dict[str, Any]],
    by_unit: dict[str, dict[str, Any]],
    *,
    include_normalized_route_lines: bool = True,
    exclude_path_like_lexical_units: bool = False,
    query_tokens: list[str] | None = None,
    max_lexical_units: int | None = None,
    max_chars: int | None = None,
    order_mode: str = "ranked",
) -> str:
    parts: list[str] = []
    lexical_count = 0
    signal_tokens = _signal_query_tokens(query_tokens)
    rows: list[dict[str, Any]] = []

    for h in hits:
        uid = str(h.get("unit_id", "") or "")
        rec = by_unit.get(uid)
        if not rec:
            continue
        lp = str(rec.get("lexical_plain", "") or "").strip()
        if exclude_path_like_lexical_units and lp and _is_path_like_lexical_unit(lp):
            lp = ""
        route_lines: list[str] = []
        if include_normalized_route_lines:
            for rt in rec.get("routes") or []:
                nr = str(rt.get("normalized_route", "") or "").strip()
                if nr:
                    route_lines.append(nr)
        why = [str(x) for x in (h.get("why_matched") or [])]
        lp_lower = _normalize_text(lp).lower()
        rows.append(
            {
                "lp": lp,
                "routes": route_lines,
                "score": int(h.get("score") or 0),
                "idx": len(rows),
                "line_start": int(rec.get("line_start") or 0),
                "line_end": int(rec.get("line_end") or 0),
                "unit_suffix": _unit_suffix(uid),
                "why_lexical": sum(1 for w in why if w.startswith("lexical_token:")),
                "why_route": sum(1 for w in why if w.startswith("route_token:")),
                "why_expanded": sum(1 for w in why if w.startswith("expanded_")),
                "query_token_hits": _lexical_token_hits_count(lp_lower, signal_tokens) if lp else 0,
            }
        )

    mode = str(order_mode or "ranked").strip().lower()
    if mode == "source_order":
        if signal_tokens:
            ranked_rows = sorted(rows, key=_ranked_row_key, reverse=True)
            keep_n = max_lexical_units if max_lexical_units is not None else len(ranked_rows)
            seeded = ranked_rows[:keep_n]
            rows = list(seeded)
        rows.sort(
            key=lambda row: (
                int(row.get("line_start") or 0),
                int(row.get("line_end") or 0),
                int(row.get("unit_suffix") or 0),
                int(row.get("idx") or 0),
            )
        )
    elif signal_tokens:
        rows.sort(key=_ranked_row_key, reverse=True)

    def _append_with_cap(s: str) -> bool:
        if not s:
            return True
        if max_chars is None:
            parts.append(s)
            return True
        current_len = len("\n".join(parts))
        needed = len(s) + (1 if parts else 0)
        if current_len + needed > max_chars:
            return False
        parts.append(s)
        return True

    for row in rows:
        lp = str(row.get("lp") or "")
        if lp:
            if max_lexical_units is not None and lexical_count >= max_lexical_units:
                break
            if not _append_with_cap(lp):
                break
            lexical_count += 1
        for route_line in row.get("routes") or []:
            if not _append_with_cap(str(route_line)):
                return "\n".join(parts)

    return "\n".join(parts)
