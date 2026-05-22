from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_classification import is_admittable_planner_evidence
from evals.c1s4_preplanning_vertical_slice.query_alias_expansion import MERGE_POLICY_DEFAULTS
from src.agent.session_memory_query import query_session_memory_candidate

SUPPORT_KIND = "support_knowledge_card"

C1S4_NPC_FAMILY_ORDER: tuple[str, ...] = ("pippa", "bubbles", "grishna")

_CORPUS_FIELDS_FOR_ENRICHMENT = (
    "source_path",
    "source_kind",
    "source_layer",
    "subject_class",
    "subject_id",
    "section_heading",
    "evidence_role",
    "presentation_lane",
    "planner_lane_hint",
    "title",
    "subject_doc_kind",
    "source_recap_path",
    "source_reference",
)


def records_for_query_variant(records: list[dict[str, Any]], variant: dict[str, Any]) -> list[dict[str, Any]]:
    role = str(variant.get("variant_role") or "")
    if role in {"support_alias", "planner_affordance"}:
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


def _channels_for_variant(role: str) -> dict[str, bool]:
    return {
        "title_summary": role == "literal_question",
        "retrieval_terms": role == "support_alias",
        "planner_affordances": role == "planner_affordance",
        "support_alias": role == "support_alias",
    }


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
    hits = _query_hits(
        records=records_for_query_variant(records, variant),
        query=str(variant["query"]),
        campaign_id=campaign_id,
        session_min=session_min,
        session_max=session_max,
        max_hits=depth,
    )
    if role != "literal_question":
        channels = _channels_for_variant(role)
        out = []
        for hit in hits:
            marked = dict(hit)
            marked["merge_source_variant_role"] = role
            marked["merge_source_query"] = str(variant.get("query") or "")
            marked["support_match_channels"] = channels
            marked["query_affordances"] = list(variant.get("query_affordances") or [])
            out.append(marked)
        return out
    out = []
    channels = _channels_for_variant(role)
    for hit in hits:
        if str(hit.get("source_kind") or "") == SUPPORT_KIND or str(hit.get("unit_id") or "").startswith("support:"):
            marked = dict(hit)
            marked["support_match_channels"] = channels
            out.append(marked)
        else:
            out.append(hit)
    return out


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


def _enrich_hit_with_record(hit: dict[str, Any], records_by_unit_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    record = records_by_unit_id.get(_hit_unit_id(hit), {})
    enriched = dict(hit)
    for field in _CORPUS_FIELDS_FOR_ENRICHMENT:
        if record.get(field) is not None and enriched.get(field) is None:
            enriched[field] = record[field]
    return enriched


def family_key_for_candidate(hit: dict[str, Any]) -> str | None:
    text = " ".join(
        str(hit.get(k) or "")
        for k in ("unit_id", "source_path", "source_recap_path", "source_reference", "title", "snippet")
    ).lower()
    if "/npcs/pippa/" in text or "corpus:npc:pippa:" in text:
        return "pippa"
    if "/npcs/bubbles_the_float_goat/" in text or "corpus:npc:bubbles_the_float_goat:" in text:
        return "bubbles"
    if "/npcs/grishna/" in text or "corpus:npc:grishna:" in text:
        return "grishna"
    return None


def _family_hit_priority(family: str, hit: dict[str, Any]) -> tuple[int, int]:
    unit_id = str(hit.get("unit_id") or "").lower()
    source_kind = str(hit.get("source_kind") or "").lower()
    source_path = str(hit.get("source_path") or hit.get("source_recap_path") or "").lower()
    if unit_id == f"corpus:npc:{family}:summary":
        return (0, 0)
    if unit_id.endswith(":summary") and family in unit_id:
        return (1, 0)
    if source_kind == "npc_dossier" and f"/npcs/{family}/" in source_path:
        return (2, 0)
    if source_kind == "npc_dossier":
        return (3, 0)
    if source_kind == "npc_hub":
        return (4, 0)
    if source_kind in {"session_memory", "session_recap"}:
        return (5, 0)
    return (6, 0)


def _is_family_coverage_eligible(hit: dict[str, Any]) -> bool:
    if not is_admittable_planner_evidence(hit):
        return False
    if str(hit.get("presentation_lane") or "").lower() == "navigation":
        return False
    if family_key_for_candidate(hit) is None:
        return False
    source_kind = str(hit.get("source_kind") or "").lower()
    if source_kind == "location_hub":
        return False
    return True


def select_required_family_alias_hits(
    *,
    alias_hits_by_variant: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    literal_head_unit_ids: set[str],
    records_by_unit_id: dict[str, dict[str, Any]],
    max_required_family_hits: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates_by_family: dict[str, list[tuple[tuple[int, int], int, dict[str, Any], dict[str, Any], str]]] = {
        family: [] for family in C1S4_NPC_FAMILY_ORDER
    }

    for variant_dict, hits in alias_hits_by_variant:
        role = str(variant_dict.get("variant_role") or "")
        if role != "npc_target_alias":
            continue
        query = str(variant_dict.get("query") or "")
        for alias_rank, hit in enumerate(hits):
            uid = _hit_unit_id(hit)
            if not uid or uid in literal_head_unit_ids:
                continue
            enriched = _enrich_hit_with_record(hit, records_by_unit_id)
            if not _is_family_coverage_eligible(enriched):
                continue
            family = family_key_for_candidate(enriched)
            if family is None:
                continue
            priority = _family_hit_priority(family, enriched)
            candidates_by_family[family].append((priority, alias_rank, hit, variant_dict, query))

    selected: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for family in C1S4_NPC_FAMILY_ORDER:
        if len(selected) >= max_required_family_hits:
            break
        family_candidates = candidates_by_family.get(family) or []
        if not family_candidates:
            continue
        priority, alias_rank, hit, variant_dict, query = min(
            family_candidates,
            key=lambda row: (row[0], row[1]),
        )
        marked = dict(hit)
        marked["merge_reason"] = "required_npc_family_coverage"
        marked["merge_family"] = family
        marked["merge_source_variant_role"] = str(variant_dict.get("variant_role") or "npc_target_alias")
        marked["merge_source_query"] = query
        selected.append(marked)
        enriched = _enrich_hit_with_record(hit, records_by_unit_id)
        diagnostics.append(
            {
                "family": family,
                "unit_id": _hit_unit_id(hit),
                "source_path": enriched.get("source_path"),
                "selected_from_variant_role": marked["merge_source_variant_role"],
                "selected_from_query": query,
                "alias_rank": alias_rank,
                "reason": "required_npc_family_coverage",
            }
        )

    return selected, diagnostics


def merge_variant_hits(
    *,
    literal_hits: list[dict[str, Any]],
    alias_hits: list[dict[str, Any]],
    literal_keep_n: int,
    alias_slot_n: int,
    candidate_depth: int,
    alias_hits_by_variant: list[tuple[dict[str, Any], list[dict[str, Any]]]] | None = None,
    records_by_unit_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    literal_head = literal_hits[:literal_keep_n]
    literal_tail = literal_hits[literal_keep_n:]
    literal_uids = {_hit_unit_id(h) for h in literal_head if _hit_unit_id(h)}

    required_family_hits: list[dict[str, Any]] = []
    family_diagnostics: list[dict[str, Any]] = []
    if alias_hits_by_variant and records_by_unit_id is not None:
        required_family_hits, family_diagnostics = select_required_family_alias_hits(
            alias_hits_by_variant=alias_hits_by_variant,
            literal_head_unit_ids=literal_uids,
            records_by_unit_id=records_by_unit_id,
        )

    required_uids = {_hit_unit_id(h) for h in required_family_hits if _hit_unit_id(h)}
    remaining_slots = max(0, alias_slot_n - len(required_family_hits))

    alias_slot = list(required_family_hits)
    for hit in stable_dedupe_hits(alias_hits):
        uid = _hit_unit_id(hit)
        if not uid or uid in literal_uids or uid in required_uids:
            continue
        alias_slot.append(hit)
        literal_uids.add(uid)
        if len(alias_slot) >= alias_slot_n:
            break

    merged = stable_dedupe_hits(literal_head + alias_slot + literal_tail)[:candidate_depth]
    merge_allocation_diagnostics = {
        "schema": "dmb_query_variant_merge_allocation_v1",
        "family_required_hits": family_diagnostics,
        "alias_slot_n": alias_slot_n,
        "required_family_slots_used": len(required_family_hits),
        "remaining_alias_slots": remaining_slots,
        "literal_keep_n": literal_keep_n,
        "candidate_depth": candidate_depth,
    }
    return merged, merge_allocation_diagnostics


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
    alias_hits_by_variant: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    variant_hit_counts: list[dict[str, Any]] = []
    literal_hits: list[dict[str, Any]] = []
    records_by_unit_id = {str(r.get("unit_id")): r for r in records if r.get("unit_id")}
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
                "query_affordances": variant.get("query_affordances") or [],
                "record_scope": role if role != "literal_question" else "full_universe",
                "scoped_record_count": len(scoped_records),
                "hit_count": len(hits),
                "top_unit_ids": [_hit_unit_id(h) for h in hits[:5] if _hit_unit_id(h)],
                "hits": hits,
            }
        )
        if role != "literal_question":
            alias_hits.extend(hits)
            alias_hits_by_variant.append((variant, hits))

    merged, merge_allocation_diagnostics = merge_variant_hits(
        literal_hits=literal_hits,
        alias_hits=alias_hits,
        literal_keep_n=literal_keep_n,
        alias_slot_n=alias_slot_n,
        candidate_depth=candidate_depth,
        alias_hits_by_variant=alias_hits_by_variant,
        records_by_unit_id=records_by_unit_id,
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
        "merge_allocation_diagnostics": merge_allocation_diagnostics,
    }
    return merged, diagnostics
