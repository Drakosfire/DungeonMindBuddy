"""Deterministic session-memory retrieval over normalized breadcrumb records (candidate mode).

The planner tool ``query_session_memory`` returns **anchors and routes only** — no recap prose
in candidate mode — so benchmarks can grade recall without leaking answer text into tool traces.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import blake3

RECORD_SCHEMA_V1 = "dmb_session_memory_record_v1"
QUERY_CONTRACT_CANDIDATE_V1 = "candidate_mode_v1"
QUERY_TRACE_SCHEMA_V1 = "dmb_query_session_memory_trace_v1"
# When expanding, leave this many hit slots to fill via adjacency / shared-route / route-family passes.
_EXPAND_DEFAULT_POST_FIRST_PASS_SLOTS = 3
_TOKENIZER_MODE_DEFAULT = "default"
_TOKENIZER_MODE_RESTRAINED = "restrained"
_TOKENIZER_MODES = frozenset({_TOKENIZER_MODE_DEFAULT, _TOKENIZER_MODE_RESTRAINED})
_EXPANSION_ALLOCATION_GREEDY = "greedy"
_EXPANSION_ALLOCATION_ROUND_ROBIN = "round_robin"
_EXPANSION_ALLOCATION_MODES = frozenset(
    {_EXPANSION_ALLOCATION_GREEDY, _EXPANSION_ALLOCATION_ROUND_ROBIN}
)
_RESTRAINED_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "him",
        "his",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "she",
        "that",
        "the",
        "their",
        "them",
        "they",
        "this",
        "to",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        # Meta tokens from natural GM questions — rank poorly for recap retrieval.
        "actionable",
        "next",
        "recap",
        "session",
    }
)


def load_session_memory_records_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL records; skips blank lines; validates ``schema`` when present."""
    out: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        sch = row.get("schema")
        if sch is not None and sch != RECORD_SCHEMA_V1:
            raise ValueError(f"unexpected record schema {sch!r} in {path}")
        out.append(row)
    return out


def _tokens(query: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", query.lower())


def _tokenize_query(
    query: str,
    *,
    tokenizer_mode: str,
    query_token_aliases: list[str] | None,
) -> list[str]:
    mode = tokenizer_mode.strip().lower()
    if mode not in _TOKENIZER_MODES:
        raise ValueError(
            f"unsupported tokenizer_mode {tokenizer_mode!r}; expected one of {sorted(_TOKENIZER_MODES)}"
        )
    raw = _tokens(query)
    if mode == _TOKENIZER_MODE_RESTRAINED:
        # Keep domain-bearing query terms while dropping high-frequency function words.
        toks = [t for t in raw if len(t) >= 3 and t not in _RESTRAINED_QUERY_STOPWORDS]
    else:
        toks = list(raw)
    out: list[str] = []
    seen: set[str] = set()
    for t in toks:
        if t not in seen:
            out.append(t)
            seen.add(t)
    for alias in query_token_aliases or []:
        for t in _tokens(str(alias)):
            if mode == _TOKENIZER_MODE_RESTRAINED and (len(t) < 3 or t in _RESTRAINED_QUERY_STOPWORDS):
                continue
            if t not in seen:
                out.append(t)
                seen.add(t)
    return out


def _subject_classes(record: dict[str, Any]) -> set[str]:
    s: set[str] = set()
    for r in record.get("routes") or []:
        sc = str(r.get("subject_class", "") or "").strip()
        if sc:
            s.add(sc)
    return s


def _record_passes_filters(
    record: dict[str, Any],
    *,
    campaign_id: str,
    session_min: int | None,
    session_max: int | None,
    subject_types: set[str] | None,
    subject_route_substr: str | None,
    proposed_only: bool,
) -> bool:
    if str(record.get("campaign_id", "")).strip() != campaign_id.strip():
        return False
    try:
        sn = int(record.get("session_number"))
    except (TypeError, ValueError):
        return False
    if session_min is not None and sn < session_min:
        return False
    if session_max is not None and sn > session_max:
        return False
    routes = record.get("routes") or []
    if proposed_only:
        if not any(bool(r.get("proposed")) for r in routes):
            return False
    if subject_types is not None and subject_types:
        classes = _subject_classes(record)
        if not (classes & subject_types):
            return False
    if subject_route_substr:
        needle = subject_route_substr.strip().lower()
        if not any(needle in str(r.get("normalized_route", "")).lower() for r in routes):
            return False
    return True


def _score_record(record: dict[str, Any], tokens: list[str]) -> tuple[int, list[str]]:
    why: list[str] = []
    if not tokens:
        return 0, why
    lex = str(record.get("lexical_plain", "") or "").lower()
    score = 0
    seen_why: set[str] = set()
    route_blob_parts: list[str] = []
    for r in record.get("routes") or []:
        nr = str(r.get("normalized_route", "") or "")
        route_blob_parts.append(nr.lower())
    route_blob = " ".join(route_blob_parts)
    for t in tokens:
        if t in lex:
            score += 1
            key = f"lexical_token:{t}"
            if key not in seen_why:
                why.append(key)
                seen_why.add(key)
        if t in route_blob:
            score += 3
            key = f"route_token:{t}"
            if key not in seen_why:
                why.append(key)
                seen_why.add(key)
    return score, why


def _hit_id(record: dict[str, Any]) -> str:
    raw = f"{record.get('campaign_id')}:{record.get('session_number')}:{record.get('unit_id')}"
    return blake3.blake3(raw.encode("utf-8")).hexdigest()[:20]


def _norm_route_path(nr: str) -> str:
    return str(nr or "").strip().lower().rstrip("/")


def _record_route_norms(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for r in record.get("routes") or []:
        n = _norm_route_path(str(r.get("normalized_route", "")))
        if n:
            out.append(n)
    return out


LOCATION_ENTITY_SUMMARY_SCHEMA_V1 = "dmb_location_entity_summary_v1"
QUERY_MODE_LEXICAL_ROUTE_OVERLAP = "lexical_route_overlap"
QUERY_MODE_LOCATION_ENTITY_LIST = "location_entity_list"
_RELATION_CONFIDENCE_CO_TAGGED = "co_tagged_with_location"
_LOCATION_ENTITY_SUBJECT_CLASSES = frozenset({"NPC", "NewHubCandidate"})


def _query_compact_alnum(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(query or "").lower())


def _is_location_entity_list_question(query: str) -> bool:
    """Heuristic: GM is asking for a roster of people/NPCs tied to a place name."""
    ql = str(query or "").lower()
    if re.search(r"\b(npcs?|characters|people|residents?|townsfolk)\b", ql):
        return True
    if re.search(r"\blist of\b", ql) and re.search(
        r"\b(npcs?|people|characters|residents?)\b", ql
    ):
        return True
    if re.search(r"\ball\b", ql) and re.search(r"\b(npcs?|characters|people)\b", ql):
        return True
    if re.search(r"\bwho\b", ql) and re.search(r"\b(npcs?|characters|people)\b", ql):
        return True
    if re.search(r"\bwho\b", ql) and re.search(
        r"\b(live|lives|living|reside|residing|residents?|staying)\b", ql
    ):
        return True
    return False


def _location_slug_from_normalized_route(norm_route: str) -> str:
    s = _norm_route_path(norm_route)
    if not s:
        return ""
    return s.rsplit("/", 1)[-1]


def _collect_unique_location_routes(records: list[dict[str, Any]]) -> list[str]:
    """Distinct Location hub routes (normalized, lowercased) under .../Locations/."""
    seen: set[str] = set()
    out: list[str] = []
    for rec in records:
        for r in rec.get("routes") or []:
            if str(r.get("subject_class", "") or "").strip() != "Location":
                continue
            nr = _norm_route_path(str(r.get("normalized_route", "")))
            if not nr or "/locations/" not in nr:
                continue
            if nr not in seen:
                seen.add(nr)
                out.append(nr)
    out.sort()
    return out


def _resolve_location_route_from_query(
    query: str, location_routes: list[str]
) -> tuple[str | None, str | None]:
    """Pick the Location route whose folder slug is mentioned in the query text."""
    if not location_routes:
        return None, "no_location_routes_in_filtered_records"
    qc = _query_compact_alnum(query)
    if not qc:
        return None, "empty_query"
    best: tuple[int, str] | None = None
    for nr in location_routes:
        slug = _location_slug_from_normalized_route(nr)
        key = slug.replace("_", "")
        if not key or key not in qc:
            continue
        cand: tuple[int, str] = (len(key), nr)
        if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
            best = cand
    if best is None:
        return None, "location_slug_not_found_in_query"
    return best[1], None


def _record_includes_normalized_route(record: dict[str, Any], route_norm: str) -> bool:
    return route_norm in _record_route_norms(record)


def _build_location_entity_summary(
    filtered_records: list[dict[str, Any]],
    *,
    location_route_norm: str,
    resolution_note: str | None,
) -> dict[str, Any]:
    """Aggregate NPC + NewHubCandidate routes co-tagged on units that carry ``location_route_norm``."""
    loc_norm = _norm_route_path(location_route_norm)
    matching_recs: list[dict[str, Any]] = [
        rec for rec in filtered_records if _record_includes_normalized_route(rec, loc_norm)
    ]
    # Preserve casing from first occurrence of the location route string.
    display_loc = loc_norm
    for rec in matching_recs:
        for r in rec.get("routes") or []:
            raw = str(r.get("normalized_route", "")).strip()
            if _norm_route_path(raw) == loc_norm:
                display_loc = raw if raw.endswith("/") else f"{raw}/"
                break
        else:
            continue
        break

    entities_work: dict[str, dict[str, Any]] = {}
    for rec in matching_recs:
        uid = str(rec.get("unit_id", "") or "")
        lex = str(rec.get("lexical_plain", "") or "").strip()
        snippet = lex[:240] + ("…" if len(lex) > 240 else "")
        for r in rec.get("routes") or []:
            sc = str(r.get("subject_class", "") or "").strip()
            if sc not in _LOCATION_ENTITY_SUBJECT_CLASSES:
                continue
            raw_nr = str(r.get("normalized_route", "")).strip()
            nn = _norm_route_path(raw_nr)
            if not nn:
                continue
            disp = raw_nr if raw_nr.endswith("/") else f"{raw_nr}/"
            if nn not in entities_work:
                entities_work[nn] = {
                    "normalized_route": disp,
                    "subject_class": sc,
                    "proposed": bool(r.get("proposed")),
                    "evidence_unit_ids": [],
                    "evidence_lexical_snippets": [],
                }
            ent = entities_work[nn]
            if sc == "NPC":
                ent["subject_class"] = "NPC"
            elif str(ent.get("subject_class", "")) != "NPC":
                ent["subject_class"] = sc
            ent["proposed"] = ent["proposed"] or bool(r.get("proposed"))
            if uid and uid not in ent["evidence_unit_ids"]:
                ent["evidence_unit_ids"].append(uid)
            if snippet and snippet not in ent["evidence_lexical_snippets"]:
                ent["evidence_lexical_snippets"].append(snippet)
            if len(ent["evidence_lexical_snippets"]) > 3:
                ent["evidence_lexical_snippets"] = ent["evidence_lexical_snippets"][:3]

    entities = sorted(entities_work.values(), key=lambda e: str(e["normalized_route"]).lower())
    caveat = (
        "Entities are co-tagged with this location on the same recap sentence units — "
        "not confirmed residency unless corpus/ingestion adds an explicit home_base / lives_in relation."
    )
    return {
        "summary_schema": LOCATION_ENTITY_SUMMARY_SCHEMA_V1,
        "relation_confidence": _RELATION_CONFIDENCE_CO_TAGGED,
        "caveat": caveat,
        "location_route": display_loc,
        "location_route_norm": loc_norm,
        "resolution_note": resolution_note,
        "record_count_for_location": len(matching_recs),
        "entities": entities,
    }


def _strict_prefix_path(parent: str, child: str) -> bool:
    p, c = parent.rstrip("/"), child.rstrip("/")
    if not p or not c or p == c:
        return False
    return c.startswith(p + "/")


def _routes_prefix_related(a: str, b: str) -> bool:
    a_n, b_n = _norm_route_path(a), _norm_route_path(b)
    if not a_n or not b_n or a_n == b_n:
        return False
    return _strict_prefix_path(a_n, b_n) or _strict_prefix_path(b_n, a_n)


def _route_parent_prefix(nr: str) -> str | None:
    s = _norm_route_path(nr)
    if "/" not in s:
        return None
    return s.rsplit("/", 1)[0]


def _routes_sibling(a: str, b: str) -> bool:
    """Same parent folder, not a prefix/child relationship."""
    a_n, b_n = _norm_route_path(a), _norm_route_path(b)
    if not a_n or not b_n or a_n == b_n or _routes_prefix_related(a_n, b_n):
        return False
    pa, pb = _route_parent_prefix(a_n), _route_parent_prefix(b_n)
    if pa is None or pb is None or pa != pb:
        return False
    return True


def _routes_family(a: str, b: str) -> bool:
    """Prefix/child in the same hub tree, or sibling under the same parent path."""
    return _routes_prefix_related(a, b) or _routes_sibling(a, b)


def _line_sort_key(rec: dict[str, Any]) -> tuple[int, str]:
    try:
        ls = int(rec.get("line_start") or 0)
    except (TypeError, ValueError):
        ls = 0
    return (ls, str(rec.get("unit_id") or ""))


def _unit_numeric_suffix(unit_id: str) -> int:
    parts = str(unit_id or "").split("-")
    if len(parts) >= 3 and parts[-1].isdigit():
        return int(parts[-1])
    return 0


def _median_suffix_on_line(records: list[dict[str, Any]], line: int) -> int:
    suf: list[int] = []
    for rec in records:
        try:
            ls = int(rec.get("line_start") or 0)
        except (TypeError, ValueError):
            continue
        if ls != line:
            continue
        suf.append(_unit_numeric_suffix(str(rec.get("unit_id") or "")))
    if not suf:
        return 0
    suf.sort()
    return suf[len(suf) // 2]


def _first_pass_anchor_line(first_pass_records: list[dict[str, Any]]) -> int:
    """Line number farthest down-recap among first-pass hits (stable narrative anchor).

    Session-memory first-pass lists are sorted by score then ``unit_id``. Early-low-line
    hits can share the same score as later beats; taking **max line_start** biases
    expansion toward the chronologically forward cluster the query matched, so
    adjacent/shared/family slots fill timeline neighbors (e.g. Lysandra wagon camp)
    instead of unrelated earlier paragraphs.
    """
    best = 0
    for rec in first_pass_records:
        try:
            ls = int(rec.get("line_start") or 0)
        except (TypeError, ValueError):
            continue
        if ls > best:
            best = ls
    return best


def _expansion_shared_family_sort_key(rec: dict[str, Any]) -> tuple[int, str]:
    """Prefer lower recap lines first for shared-route / route-family expansion only.

    Adjacent expansion stays anchored to the first-pass narrative cluster; shared and
    family bridges can legitimately land on earlier setting beats (e.g. Mossford hub
    routes) that share a route family with a later hit.
    """
    try:
        ls = int(rec.get("line_start") or 0)
    except (TypeError, ValueError):
        ls = 0
    return (ls, str(rec.get("unit_id") or ""))


def _expansion_shared_family_emit_sort_key(
    rec: dict[str, Any],
    expansion_tokens: list[str] | None,
) -> tuple[int, int, str]:
    """Order shared/family expansion emissions: lexical+route score first, then recap line.

    Line-only ordering pulled low-line weak matches ahead of high-scoring later beats
    (e.g. tainted meat / storm) that share seed routes. When ``expansion_tokens`` is
    empty, degrades to line-then-id (legacy behavior).
    """
    if expansion_tokens:
        sc, _ = _score_record(rec, expansion_tokens)
    else:
        sc = 0
    try:
        ls = int(rec.get("line_start") or 0)
    except (TypeError, ValueError):
        ls = 0
    return (-sc, ls, str(rec.get("unit_id") or ""))


def _expansion_proximity_sort_key(
    rec: dict[str, Any],
    anchor_line: int,
    *,
    median_suffix_on_anchor: int,
) -> tuple[int, int, int, str]:
    """Prefer recap lines near the anchor line, then sentence-order proximity on that line.

    Within the anchor line (the deepest first-pass line), rank by distance from the
    median sentence-unit suffix among **expansion seeds** on that line — so expansion
    hugs the matched narrative beat (e.g. Lysandra wagon camp) instead of earlier
    sentences on the same recap line consuming the expansion budget.
    """
    try:
        ls = int(rec.get("line_start") or 0)
    except (TypeError, ValueError):
        ls = 0
    uid = str(rec.get("unit_id") or "")
    suf = _unit_numeric_suffix(uid)
    if anchor_line <= 0:
        return (0, 0, -ls, uid)
    line_dist = abs(ls - anchor_line)
    if line_dist != 0 or median_suffix_on_anchor <= 0:
        return (line_dist, 0, -ls, uid)
    return (line_dist, abs(suf - median_suffix_on_anchor), -suf, uid)


def _group_key_recap_session(rec: dict[str, Any]) -> tuple[str, int]:
    path = str(rec.get("source_recap_path") or "")
    try:
        sn = int(rec.get("session_number"))
    except (TypeError, ValueError):
        sn = -1
    return (path, sn)


def _build_adjacency_groups(filtered: list[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for rec in filtered:
        key = _group_key_recap_session(rec)
        groups.setdefault(key, []).append(rec)
    for key in groups:
        groups[key].sort(key=_line_sort_key)
    return groups


def _expand_hits(
    *,
    filtered: list[dict[str, Any]],
    first_pass_hits: list[dict[str, Any]],
    first_pass_records: list[dict[str, Any]],
    max_hits: int,
    expand_seed_hits: int,
    expand_adjacent_window: int,
    expand_shared_route_limit: int,
    expand_route_family_limit: int,
    expand_same_beat_limit: int,
    expansion_allocation_mode: str,
    expansion_tokens: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Append expansion rows after first-pass hits until ``max_hits`` (deterministic)."""
    stats = {
        "anchor_line": 0,
        "added_adjacent": 0,
        "added_shared_route": 0,
        "added_route_family": 0,
        "added_same_beat": 0,
    }
    if not first_pass_hits or max_hits <= len(first_pass_hits):
        return first_pass_hits, stats

    first_uids = {str(h.get("unit_id") or "") for h in first_pass_hits}
    seen: set[str] = set(first_uids)

    n_seed = max(0, min(expand_seed_hits, len(first_pass_records)))
    seeds = first_pass_records[:n_seed]
    anchor_line = _first_pass_anchor_line(first_pass_records)
    stats["anchor_line"] = anchor_line
    median_suffix_on_anchor = _median_suffix_on_line(seeds, anchor_line)
    stats["median_suffix_on_anchor_line"] = median_suffix_on_anchor

    # --- Adjacent (same recap + session, line / unit order)
    adj_pairs: dict[str, tuple[dict[str, Any], list[str]]] = {}
    groups = _build_adjacency_groups(filtered)
    for seed in seeds:
        gkey = _group_key_recap_session(seed)
        lst = groups.get(gkey)
        if not lst:
            continue
        suid = str(seed.get("unit_id") or "")
        idx = next((i for i, r in enumerate(lst) if str(r.get("unit_id") or "") == suid), None)
        if idx is None:
            continue
        lo = max(0, idx - expand_adjacent_window)
        hi = min(len(lst), idx + expand_adjacent_window + 1)
        for j in range(lo, hi):
            if j == idx:
                continue
            nb = lst[j]
            uid = str(nb.get("unit_id") or "")
            if uid in first_uids:
                continue
            tag = f"expanded_adjacent:{uid}"
            if uid not in adj_pairs:
                adj_pairs[uid] = (nb, [tag])
            elif tag not in adj_pairs[uid][1]:
                adj_pairs[uid][1].append(tag)

    adj_batch = sorted(
        adj_pairs.values(),
        key=lambda it: _expansion_proximity_sort_key(
            it[0], anchor_line, median_suffix_on_anchor=median_suffix_on_anchor
        ),
    )

    # --- Shared exact route (from seed records)
    seed_routes: set[str] = set()
    for seed in seeds:
        seed_routes.update(_record_route_norms(seed))
    shared_pairs: dict[str, tuple[dict[str, Any], list[str]]] = {}
    for R in sorted(seed_routes):
        added = 0
        route_candidates: list[tuple[int, dict[str, Any]]] = []
        for rec in filtered:
            uid = str(rec.get("unit_id") or "")
            if uid in first_uids:
                continue
            norms = set(_record_route_norms(rec))
            if R not in norms:
                continue
            sc, _ = _score_record(rec, expansion_tokens) if expansion_tokens else (0, [])
            route_candidates.append((sc, rec))
        route_candidates.sort(key=lambda x: (-x[0], str(x[1].get("unit_id") or "")))
        for _sc, rec in route_candidates:
            if added >= expand_shared_route_limit:
                break
            uid = str(rec.get("unit_id") or "")
            tag = f"expanded_shared_route:{R}"
            if uid not in shared_pairs:
                shared_pairs[uid] = (rec, [tag])
                added += 1
            elif tag not in shared_pairs[uid][1]:
                shared_pairs[uid][1].append(tag)

    shared_batch = sorted(
        shared_pairs.values(),
        key=lambda it: _expansion_shared_family_emit_sort_key(it[0], expansion_tokens),
    )

    # --- Route family (prefix / sibling), same session as seed
    family_pairs: dict[str, tuple[dict[str, Any], list[str]]] = {}
    for seed in seeds:
        try:
            sn = int(seed.get("session_number"))
        except (TypeError, ValueError):
            continue
        for R in sorted(set(_record_route_norms(seed))):
            added = 0
            fam_candidates: list[tuple[int, dict[str, Any]]] = []
            for rec in filtered:
                try:
                    rsn = int(rec.get("session_number"))
                except (TypeError, ValueError):
                    continue
                if rsn != sn:
                    continue
                uid = str(rec.get("unit_id") or "")
                if uid in first_uids:
                    continue
                hit = any(_routes_family(R, S) for S in _record_route_norms(rec))
                if not hit:
                    continue
                sc, _ = _score_record(rec, expansion_tokens) if expansion_tokens else (0, [])
                fam_candidates.append((sc, rec))
            fam_candidates.sort(key=lambda x: (-x[0], str(x[1].get("unit_id") or "")))
            for _sc, rec in fam_candidates:
                if added >= expand_route_family_limit:
                    break
                uid = str(rec.get("unit_id") or "")
                tag = f"expanded_route_family:{R}"
                if uid not in family_pairs:
                    family_pairs[uid] = (rec, [tag])
                    added += 1
                elif tag not in family_pairs[uid][1]:
                    family_pairs[uid][1].append(tag)

    family_batch = sorted(
        family_pairs.values(),
        key=lambda it: _expansion_shared_family_emit_sort_key(it[0], expansion_tokens),
    )

    same_beat_pairs: dict[str, tuple[dict[str, Any], list[str]]] = {}
    if expand_same_beat_limit > 0:
        by_beat: dict[str, list[dict[str, Any]]] = {}
        for rec in filtered:
            bid = str(rec.get("beat_id") or "").strip()
            if bid:
                by_beat.setdefault(bid, []).append(rec)
        for seed in seeds:
            bid = str(seed.get("beat_id") or "").strip()
            if not bid:
                continue
            added = 0
            for rec in sorted(by_beat.get(bid, []), key=lambda r: (int(r.get("line_start") or 0), str(r.get("unit_id") or ""))):
                if added >= expand_same_beat_limit:
                    break
                uid = str(rec.get("unit_id") or "")
                if uid in first_uids:
                    continue
                tag = f"expanded_same_beat:{bid}"
                if uid not in same_beat_pairs:
                    same_beat_pairs[uid] = (rec, [tag])
                    added += 1

    same_beat_batch = sorted(
        same_beat_pairs.values(),
        key=lambda it: (int(it[0].get("line_start") or 0), str(it[0].get("unit_id") or "")),
    )

    hits_out = list(first_pass_hits)

    def _emit_batch(batch: list[tuple[dict[str, Any], list[str]]], stat_key: str) -> None:
        nonlocal hits_out
        for rec, why in batch:
            if len(hits_out) >= max_hits:
                return
            uid = str(rec.get("unit_id") or "")
            if uid in seen:
                continue
            seen.add(uid)
            hits_out.append(
                {
                    "hit_id": _hit_id(rec),
                    "score": 0,
                    "source_recap_path": rec.get("source_recap_path"),
                    "unit_id": rec.get("unit_id"),
                    "line_start": rec.get("line_start"),
                    "line_end": rec.get("line_end"),
                    "routes": rec.get("routes") or [],
                    "why_matched": sorted(why),
                }
            )
            stats[stat_key] += 1

    mode = expansion_allocation_mode.strip().lower()
    if mode not in _EXPANSION_ALLOCATION_MODES:
        raise ValueError(
            "unsupported expansion_allocation_mode "
            f"{expansion_allocation_mode!r}; expected one of {sorted(_EXPANSION_ALLOCATION_MODES)}"
        )

    if mode == _EXPANSION_ALLOCATION_GREEDY:
        _emit_batch(adj_batch, "added_adjacent")
        if len(hits_out) < max_hits:
            _emit_batch(same_beat_batch, "added_same_beat")
        if len(hits_out) < max_hits:
            _emit_batch(shared_batch, "added_shared_route")
        if len(hits_out) < max_hits:
            _emit_batch(family_batch, "added_route_family")
        return hits_out, stats

    # Round-robin allocation ensures each expansion source can contribute before one source exhausts slots.
    batches: dict[str, list[tuple[dict[str, Any], list[str]]]] = {
        "added_adjacent": adj_batch,
        "added_shared_route": shared_batch,
        "added_route_family": family_batch,
        "added_same_beat": same_beat_batch,
    }
    cursors: dict[str, int] = {k: 0 for k in batches}
    order = ["added_adjacent", "added_same_beat", "added_shared_route", "added_route_family"]
    while len(hits_out) < max_hits:
        emitted_any = False
        for key in order:
            batch = batches[key]
            i = cursors[key]
            while i < len(batch):
                rec, why = batch[i]
                i += 1
                uid = str(rec.get("unit_id") or "")
                if uid in seen:
                    continue
                seen.add(uid)
                hits_out.append(
                    {
                        "hit_id": _hit_id(rec),
                        "score": 0,
                        "source_recap_path": rec.get("source_recap_path"),
                        "unit_id": rec.get("unit_id"),
                        "line_start": rec.get("line_start"),
                        "line_end": rec.get("line_end"),
                        "routes": rec.get("routes") or [],
                        "why_matched": sorted(why),
                    }
                )
                stats[key] += 1
                emitted_any = True
                break
            cursors[key] = i
            if len(hits_out) >= max_hits:
                break
        if not emitted_any:
            break

    return hits_out, stats


@dataclass(frozen=True)
class CandidateQueryResult:
    """Structured query result (also JSON-serializable)."""

    schema: str
    contract: str
    campaign_id: str
    query: str
    hits: list[dict[str, Any]]
    trace: dict[str, Any]

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract": self.contract,
            "campaign_id": self.campaign_id,
            "query": self.query,
            "hits": self.hits,
            "trace": self.trace,
        }




def _compute_scene_beat_packets(*,
    candidates: list[tuple[int, dict[str, Any], list[str]]],
    filtered: list[dict[str, Any]],
    threshold: int,
    top_k: int,
    unit_limit: int,
    max_packets: int,
) -> list[dict[str, Any]]:
    by_beat: dict[str, dict[str, Any]] = {}
    for score, rec, why in candidates:
        beat_id = str(rec.get("beat_id") or "").strip()
        if not beat_id:
            continue
        row = by_beat.setdefault(beat_id, {"scores": [], "first_pass_records": [], "token_set": set()})
        row["scores"].append(int(score))
        row["first_pass_records"].append(rec)
        for marker in why:
            row["token_set"].add(str(marker))
    packets=[]
    for beat_id, row in by_beat.items():
        scores=sorted(row["scores"], reverse=True)[:max(1, top_k)]
        diversity_bonus=min(6, len(row["token_set"]))
        scene_score=max(scores)+sum(scores)+(4*min(len(scores), max(1, top_k)))+diversity_bonus+8
        if scene_score < threshold:
            continue
        first_pass = sorted(row["first_pass_records"], key=lambda r:(int(r.get("line_start") or 0), str(r.get("unit_id") or "")))
        siblings = sorted((r for r in filtered if str(r.get("beat_id") or "").strip()==beat_id), key=lambda r:(int(r.get("line_start") or 0), str(r.get("unit_id") or "")))
        ordered=[]
        seen=set()
        for rec in [*first_pass,*siblings]:
            uid=str(rec.get("unit_id") or "")
            if not uid or uid in seen:
                continue
            seen.add(uid); ordered.append(rec)
            if len(ordered)>=max(1,unit_limit):
                break
        packets.append({"beat_id":beat_id,"score":scene_score,"records":ordered,"first_pass_unit_ids":[str(r.get("unit_id") or "") for r in first_pass],"packet_unit_ids":[str(r.get("unit_id") or "") for r in ordered]})
    packets.sort(key=lambda p:(-int(p["score"]), p["beat_id"]))
    return packets[:max(0,max_packets)]
def query_session_memory_candidate(
    *,
    records: list[dict[str, Any]],
    query: str,
    campaign_id: str,
    subject_route: str | None = None,
    session_min: int | None = None,
    session_max: int | None = None,
    subject_types: list[str] | None = None,
    proposed_only: bool = False,
    max_hits: int = 12,
    expand_context: bool = False,
    expand_seed_hits: int = 5,
    expand_adjacent_window: int = 2,
    expand_shared_route_limit: int = 3,
    expand_route_family_limit: int = 3,
    expand_first_pass_cap: int | None = None,
    expansion_allocation_mode: str = _EXPANSION_ALLOCATION_ROUND_ROBIN,
    tokenizer_mode: str = _TOKENIZER_MODE_DEFAULT,
    query_token_aliases: list[str] | None = None,
    expand_same_beat_limit: int = 0,
    scene_beat_packet_mode: bool = False,
    scene_beat_packet_threshold: int = 16,
    scene_beat_packet_top_k: int = 3,
    scene_beat_packet_unit_limit: int = 8,
    scene_beat_packet_max_packets: int = 2,
) -> CandidateQueryResult:
    """Rank records by deterministic lexical + route token overlap; return candidate hits only."""
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    if max_hits < 1:
        raise ValueError("max_hits must be >= 1")
    if expand_seed_hits < 1:
        raise ValueError("expand_seed_hits must be >= 1")
    if expand_adjacent_window < 0:
        raise ValueError("expand_adjacent_window must be >= 0")
    if expand_shared_route_limit < 0 or expand_route_family_limit < 0 or expand_same_beat_limit < 0:
        raise ValueError("expand_* limits must be >= 0")
    first_pass_cap = max_hits
    if expand_context:
        if expand_first_pass_cap is not None:
            first_pass_cap = max(1, min(int(expand_first_pass_cap), max_hits))
        else:
            first_pass_cap = max(1, max_hits - _EXPAND_DEFAULT_POST_FIRST_PASS_SLOTS)
    st_set: set[str] | None = None
    if subject_types is not None:
        st_set = {str(s).strip() for s in subject_types if str(s).strip()}

    tokens = _tokenize_query(q, tokenizer_mode=tokenizer_mode, query_token_aliases=query_token_aliases)
    candidates: list[tuple[int, dict[str, Any], list[str]]] = []
    filtered: list[dict[str, Any]] = []
    examined = 0
    for rec in records:
        examined += 1
        if not _record_passes_filters(
            rec,
            campaign_id=campaign_id,
            session_min=session_min,
            session_max=session_max,
            subject_types=st_set,
            subject_route_substr=subject_route,
            proposed_only=proposed_only,
        ):
            continue
        filtered.append(rec)
        sc, why = _score_record(rec, tokens)
        if sc <= 0:
            continue
        candidates.append((sc, rec, why))

    query_mode = QUERY_MODE_LEXICAL_ROUTE_OVERLAP
    location_entity_summary: dict[str, Any] | None = None
    if _is_location_entity_list_question(q):
        loc_opts = _collect_unique_location_routes(filtered)
        picked, res_note = _resolve_location_route_from_query(q, loc_opts)
        if picked:
            location_entity_summary = _build_location_entity_summary(
                filtered,
                location_route_norm=picked,
                resolution_note=res_note,
            )
            query_mode = QUERY_MODE_LOCATION_ENTITY_LIST

    candidates.sort(
        key=lambda item: (-item[0], str(item[1].get("unit_id", "")), str(item[1].get("source_recap_path", "")))
    )

    hits_out: list[dict[str, Any]] = []
    first_pass_records: list[dict[str, Any]] = []
    for sc, rec, why in candidates[:first_pass_cap]:
        first_pass_records.append(rec)
        hits_out.append(
            {
                "hit_id": _hit_id(rec),
                "score": sc,
                "source_recap_path": rec.get("source_recap_path"),
                "unit_id": rec.get("unit_id"),
                "line_start": rec.get("line_start"),
                "line_end": rec.get("line_end"),
                "routes": rec.get("routes") or [],
                "why_matched": why,
            }
        )

    scene_packets_trace = {
        "enabled": bool(scene_beat_packet_mode),
        "threshold": int(scene_beat_packet_threshold),
        "top_k": int(scene_beat_packet_top_k),
        "unit_limit": int(scene_beat_packet_unit_limit),
        "max_packets": int(scene_beat_packet_max_packets),
        "qualified_count": 0,
        "units_added": 0,
        "packets": [],
    }
    if scene_beat_packet_mode and filtered and hits_out:
        packets = _compute_scene_beat_packets(
            candidates=candidates,
            filtered=filtered,
            threshold=scene_beat_packet_threshold,
            top_k=scene_beat_packet_top_k,
            unit_limit=scene_beat_packet_unit_limit,
            max_packets=scene_beat_packet_max_packets,
        )
        seen_units = {str(h.get("unit_id") or "") for h in hits_out}
        packet_slots = max(0, scene_beat_packet_unit_limit * max(0, scene_beat_packet_max_packets))
        packet_added = 0
        for packet in packets:
            packet_payload = {
                "beat_id": packet["beat_id"],
                "score": packet["score"],
                "first_pass_unit_ids": packet["first_pass_unit_ids"],
                "packet_unit_ids": packet["packet_unit_ids"],
            }
            scene_packets_trace["packets"].append(packet_payload)
            scene_packets_trace["qualified_count"] += 1
            for rec in packet["records"]:
                if packet_added >= packet_slots:
                    break
                uid = str(rec.get("unit_id") or "")
                if uid in seen_units:
                    continue
                seen_units.add(uid)
                packet_added += 1
                scene_packets_trace["units_added"] += 1
                hits_out.append({
                    "hit_id": _hit_id(rec),
                    "score": 0,
                    "source_recap_path": rec.get("source_recap_path"),
                    "unit_id": rec.get("unit_id"),
                    "line_start": rec.get("line_start"),
                    "line_end": rec.get("line_end"),
                    "routes": rec.get("routes") or [],
                    "why_matched": [f"scene_beat_packet:{packet['beat_id']}", f"scene_beat_packet_score:{packet['score']}"] ,
                })
    expansion_stats: dict[str, Any] | None = None
    if expand_context and filtered and hits_out and first_pass_cap < max_hits:
        hits_out, expansion_stats = _expand_hits(
            filtered=filtered,
            first_pass_hits=hits_out,
            first_pass_records=first_pass_records,
            max_hits=max_hits,
            expand_seed_hits=expand_seed_hits,
            expand_adjacent_window=expand_adjacent_window,
            expand_shared_route_limit=expand_shared_route_limit,
            expand_route_family_limit=expand_route_family_limit,
            expand_same_beat_limit=expand_same_beat_limit,
            expansion_allocation_mode=expansion_allocation_mode,
            expansion_tokens=tokens,
        )

    trace: dict[str, Any] = {
        "trace_schema": QUERY_TRACE_SCHEMA_V1,
        "examined_records": examined,
        "matched_records": len(candidates),
        "returned_hits": len(hits_out),
        "effective_context_size": len(hits_out),
        "session_window": [session_min, session_max],
        "subject_route_substr": subject_route,
        "subject_types": sorted(st_set) if st_set is not None else None,
        "proposed_only": proposed_only,
        "max_hits": max_hits,
    }
    trace["scene_beat_packets"] = scene_packets_trace
    if expand_context:
        trace["filtered_records"] = len(filtered)
        trace["expand_context"] = True
        trace["expand_seed_hits"] = expand_seed_hits
        trace["expand_adjacent_window"] = expand_adjacent_window
        trace["expand_shared_route_limit"] = expand_shared_route_limit
        trace["expand_route_family_limit"] = expand_route_family_limit
        trace["expand_same_beat_limit"] = expand_same_beat_limit
        trace["expand_first_pass_cap"] = first_pass_cap
        trace["expansion_allocation_mode"] = expansion_allocation_mode
        trace["expansion"] = expansion_stats or {
            "added_adjacent": 0,
            "added_shared_route": 0,
            "added_route_family": 0,
        }
    trace["tokenizer_mode"] = tokenizer_mode
    if query_token_aliases:
        trace["query_token_aliases"] = [str(x) for x in query_token_aliases]
    trace["query_tokens"] = tokens
    trace["query_mode"] = query_mode
    if location_entity_summary is not None:
        trace["location_entity_summary"] = location_entity_summary
    trace["scene_beat_packets"] = scene_packets_trace
    return CandidateQueryResult(
        schema="dmb_query_session_memory_result_v1",
        contract=QUERY_CONTRACT_CANDIDATE_V1,
        campaign_id=campaign_id.strip(),
        query=q,
        hits=hits_out,
        trace=trace,
    )


def dispatch_query_session_memory_json(
    raw_args: str | dict[str, Any],
    *,
    records: list[dict[str, Any]],
) -> str:
    """Planner dispatcher helper: parse JSON args and return a JSON string payload."""
    args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")
    mode = str(args.get("mode") or "candidate").strip().lower()
    if mode != "candidate":
        return json.dumps({"ok": False, "error": f"unsupported mode {mode!r} (only candidate is enabled)"})
    q = str(args.get("query", "")).strip()
    cid = str(args.get("campaign_id", "")).strip()
    if not cid:
        return json.dumps({"ok": False, "error": "campaign_id is required"})
    try:
        max_hits = int(args.get("max_hits", 12))
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "max_hits must be an integer"})
    sr = args.get("subject_route")
    subject_route = str(sr).strip() if sr is not None and str(sr).strip() else None
    smin = args.get("session_min")
    smax = args.get("session_max")
    session_min = int(smin) if smin is not None and str(smin).strip() else None
    session_max = int(smax) if smax is not None and str(smax).strip() else None
    st = args.get("subject_types")
    subject_types = [str(x) for x in st] if isinstance(st, list) else None
    proposed_only = bool(args.get("proposed_only", False))
    expand_context = bool(args.get("expand_context", False))
    try:
        expand_seed_hits = int(args.get("expand_seed_hits", 5))
        expand_adjacent_window = int(args.get("expand_adjacent_window", 2))
        expand_shared_route_limit = int(args.get("expand_shared_route_limit", 3))
        expand_route_family_limit = int(args.get("expand_route_family_limit", 3))
        expand_same_beat_limit = int(args.get("expand_same_beat_limit", 0))
        scene_beat_packet_threshold = int(args.get("scene_beat_packet_threshold", 16))
        scene_beat_packet_top_k = int(args.get("scene_beat_packet_top_k", 3))
        scene_beat_packet_unit_limit = int(args.get("scene_beat_packet_unit_limit", 8))
        scene_beat_packet_max_packets = int(args.get("scene_beat_packet_max_packets", 2))
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "expand_* parameters must be integers"})
    efcap_raw = args.get("expand_first_pass_cap")
    expand_first_pass_cap: int | None
    if efcap_raw is None:
        expand_first_pass_cap = None
    else:
        try:
            expand_first_pass_cap = int(efcap_raw)
        except (TypeError, ValueError):
            return json.dumps({"ok": False, "error": "expand_first_pass_cap must be an integer"})
    expansion_allocation_mode = str(
        args.get("expansion_allocation_mode", _EXPANSION_ALLOCATION_ROUND_ROBIN)
    ).strip()
    tokenizer_mode = str(args.get("tokenizer_mode", _TOKENIZER_MODE_DEFAULT)).strip()
    qta = args.get("query_token_aliases")
    query_token_aliases = [str(x) for x in qta] if isinstance(qta, list) else None

    try:
        result = query_session_memory_candidate(
            records=records,
            query=q,
            campaign_id=cid,
            subject_route=subject_route,
            session_min=session_min,
            session_max=session_max,
            subject_types=subject_types,
            proposed_only=proposed_only,
            max_hits=max_hits,
            expand_context=expand_context,
            expand_seed_hits=expand_seed_hits,
            expand_adjacent_window=expand_adjacent_window,
            expand_shared_route_limit=expand_shared_route_limit,
            expand_route_family_limit=expand_route_family_limit,
            expand_first_pass_cap=expand_first_pass_cap,
            expansion_allocation_mode=expansion_allocation_mode,
            tokenizer_mode=tokenizer_mode,
            expand_same_beat_limit=expand_same_beat_limit,
            query_token_aliases=query_token_aliases,
            scene_beat_packet_mode=bool(args.get("scene_beat_packet_mode", False)),
            scene_beat_packet_threshold=scene_beat_packet_threshold,
            scene_beat_packet_top_k=scene_beat_packet_top_k,
            scene_beat_packet_unit_limit=scene_beat_packet_unit_limit,
            scene_beat_packet_max_packets=scene_beat_packet_max_packets,
        )
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    payload = result.as_json_dict()
    payload["ok"] = True
    return json.dumps(payload, ensure_ascii=False)


def env_session_memory_records_path() -> Path | None:
    raw = os.environ.get("DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL", "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def load_session_memory_records_from_env() -> list[dict[str, Any]] | None:
    path = env_session_memory_records_path()
    if path is None:
        return None
    return load_session_memory_records_jsonl(path)
