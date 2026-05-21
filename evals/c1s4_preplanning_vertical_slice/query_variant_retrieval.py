from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import MERGE_POLICY_DEFAULTS
from src.agent.session_memory_query import query_session_memory_candidate

SUPPORT_KIND = "support_knowledge_card"


def records_for_query_variant(records: list[dict[str, Any]], variant: dict[str, Any]) -> list[dict[str, Any]]:
    role = str(variant.get("variant_role") or "")
    if role == "support_alias":
        return [r for r in records if str(r.get("source_kind") or "") == SUPPORT_KIND]
    if role == "npc_target_alias":
        scoped: list[dict[str, Any]] = []
        for record in records:
            source_kind = str(record.get("source_kind") or "")
            subject_class = str(record.get("subject_class") or "")
            unit_id = str(record.get("unit_id") or "")
            source_path = str(record.get("source_path") or record.get("source_recap_path") or "").lower()
            if source_kind == "npc_hub" or subject_class == "npc" or unit_id.startswith("corpus:npc:"):
                scoped.append(record)
                continue
            if source_kind == "session_memory" and "/npcs/" in source_path:
                scoped.append(record)
        return scoped or records
    if role == "route_distance_alias":
        scoped = []
        for record in records:
            source_kind = str(record.get("source_kind") or "")
            unit_id = str(record.get("unit_id") or "").lower()
            source_path = str(record.get("source_path") or record.get("source_recap_path") or "").lower()
            if source_kind in {"location_hub", "session_recap"}:
                scoped.append(record)
                continue
            if source_kind == "session_memory" and any(token in unit_id or token in source_path for token in ("mirathorn", "stone_bridge", "stone bridge")):
                scoped.append(record)
        return scoped or records
    return records


def _hit_unit_id(hit: dict[str, Any]) -> str:
    return str(hit.get("unit_id") or "")


def _query_hits(
    *,
    records: list[dict[str, Any]],
    query: str,
    campaign_id: str,
    session_min: int,
    session_max: int,
    max_hits: int,
) -> list[dict[str, Any]]:
    result = query_session_memory_candidate(
        records=records,
        query=query,
        campaign_id=campaign_id,
        session_min=session_min,
        session_max=session_max,
        max_hits=max_hits,
    )
    return list(getattr(result, "hits", []) or [])


def query_hits_for_variant(
    *,
    records: list[dict[str, Any]],
    variant: dict[str, Any],
    campaign_id: str,
    session_min: int,
    session_max: int,
    candidate_depth: int = 50,
    alias_depth_per_variant: int = MERGE_POLICY_DEFAULTS["alias_depth_per_variant"],
) -> list[dict[str, Any]]:
    role = str(variant.get("variant_role") or "")
    depth = candidate_depth if role == "literal_question" else alias_depth_per_variant
    return _query_hits(
        records=records_for_query_variant(records, variant),
        query=str(variant["query"]),
        campaign_id=campaign_id,
        session_min=session_min,
        session_max=session_max,
        max_hits=depth,
    )


def stable_dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for hit in hits:
        uid = _hit_unit_id(hit)
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(hit)
    return out


def merge_variant_hits(
    *,
    literal_hits: list[dict[str, Any]],
    alias_hits: list[dict[str, Any]],
    literal_keep_n: int,
    alias_slot_n: int,
    candidate_depth: int,
) -> list[dict[str, Any]]:
    literal_head = literal_hits[:literal_keep_n]
    literal_tail = literal_hits[literal_keep_n:]
    literal_uids = {_hit_unit_id(h) for h in literal_head if _hit_unit_id(h)}

    alias_slot: list[dict[str, Any]] = []
    for hit in stable_dedupe_hits(alias_hits):
        uid = _hit_unit_id(hit)
        if not uid or uid in literal_uids:
            continue
        alias_slot.append(hit)
        literal_uids.add(uid)
        if len(alias_slot) >= alias_slot_n:
            break

    return stable_dedupe_hits(literal_head + alias_slot + literal_tail)[:candidate_depth]


def retrieve_query_variants(
    *,
    records: list[dict[str, Any]],
    query_variants: list[dict[str, Any]],
    campaign_id: str,
    session_min: int,
    session_max: int,
    candidate_depth: int = 50,
    literal_keep_n: int = MERGE_POLICY_DEFAULTS["literal_keep_n"],
    alias_slot_n: int = MERGE_POLICY_DEFAULTS["alias_slot_n"],
    alias_depth_per_variant: int = MERGE_POLICY_DEFAULTS["alias_depth_per_variant"],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not query_variants:
        return [], {
            "variant_count": 0,
            "variants": [],
            "retrieval_merge_policy": {
                "literal_keep_n": literal_keep_n,
                "alias_slot_n": alias_slot_n,
                "alias_depth_per_variant": alias_depth_per_variant,
                "candidate_depth": candidate_depth,
            },
            "variant_hit_counts": [],
        }

    alias_hits: list[dict[str, Any]] = []
    variant_hit_counts: list[dict[str, Any]] = []
    literal_hits: list[dict[str, Any]] = []
    for variant in query_variants:
        role = str(variant.get("variant_role") or "")
        scoped_records = records_for_query_variant(records, variant)
        hits = query_hits_for_variant(
            records=records,
            variant=variant,
            campaign_id=campaign_id,
            session_min=session_min,
            session_max=session_max,
            candidate_depth=candidate_depth,
            alias_depth_per_variant=alias_depth_per_variant,
        )
        if role == "literal_question":
            literal_hits = hits
        variant_hit_counts.append(
            {
                "variant_role": role,
                "query": variant.get("query"),
                "target_lane": variant.get("target_lane"),
                "reason": variant.get("reason"),
                "source": variant.get("source"),
                "record_scope": role if role != "literal_question" else "full_universe",
                "scoped_record_count": len(scoped_records),
                "hit_count": len(hits),
                "top_unit_ids": [_hit_unit_id(h) for h in hits[:5] if _hit_unit_id(h)],
            }
        )
        if role != "literal_question":
            alias_hits.extend(hits)

    merged = merge_variant_hits(
        literal_hits=literal_hits,
        alias_hits=alias_hits,
        literal_keep_n=literal_keep_n,
        alias_slot_n=alias_slot_n,
        candidate_depth=candidate_depth,
    )

    diagnostics = {
        "variant_count": len(query_variants),
        "variants": query_variants,
        "retrieval_merge_policy": {
            "literal_keep_n": literal_keep_n,
            "alias_slot_n": alias_slot_n,
            "alias_depth_per_variant": alias_depth_per_variant,
            "candidate_depth": candidate_depth,
        },
        "variant_hit_counts": variant_hit_counts,
        "merged_hit_count": len(merged),
        "merged_top_unit_ids": [_hit_unit_id(h) for h in merged[:10] if _hit_unit_id(h)],
    }
    return merged, diagnostics
