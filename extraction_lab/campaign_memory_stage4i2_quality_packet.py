"""Deterministic Stage 4I.2 quality packet and identity/composition diagnostics.

Analysis-only: never mutates the compared store. Makes no evaluator/model calls.
"""

from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any


WITNESSES: list[dict[str, Any]] = [
    {"id": "brin_holloway", "label": "Brin Holloway", "needles": ["brin", "holloway"]},
    {"id": "orik_oric_tane", "label": "Orik / Orric Tane", "needles": ["orik", "oric", "orric", "tane"]},
    {"id": "karsemine", "label": "Karsemine", "needles": ["karsemine"]},
    {"id": "mireward", "label": "Mireward / Mireward Reach", "needles": ["mireward"]},
    {"id": "hesta_bramblewood", "label": "Hesta Bramblewood", "needles": ["hesta", "bramblewood"]},
    {"id": "thrin", "label": "Thrin", "needles": ["thrin"]},
    {"id": "tripod_s23", "label": "Tripod creatures / S23 tactical target", "needles": ["tripod"]},
    {"id": "s25_hybrid", "label": "S25 hybrid/threat", "needles": ["hybrid", "s25"]},
]

CONTINUITY_ATTRIBUTES = {
    "species",
    "role",
    "rank_or_title",
    "faction",
    "relationship_tags",
    "loyalty_or_alignment_context",
    "current_location",
}

HIGH_SIGNAL_ATTRIBUTES = {
    "event_outcome",
    "event_progression",
    "operational_status",
    "physical_condition",
    "mental_state",
    "portrayal_notes",
    *CONTINUITY_ATTRIBUTES,
}

_TOKEN = re.compile(r"[a-z0-9]+")


def _norm(value: Any) -> str:
    return " ".join(_TOKEN.findall(str(value or "").casefold()))


def _names_for_entity(entity: dict[str, Any]) -> list[str]:
    names = [str(entity.get("display_name") or "")]
    aliases = entity.get("aliases") or []
    if isinstance(aliases, list):
        names.extend(str(item) for item in aliases)
    names.append(str(entity.get("entity_id") or ""))
    return [item for item in names if item.strip()]


def _entity_matches(entity: dict[str, Any], needles: list[str]) -> bool:
    blob = " ".join(_names_for_entity(entity)).casefold()
    return any(needle in blob for needle in needles)


def _fact_matches(
    fact: dict[str, Any],
    *,
    needles: list[str],
    entity_ids: set[str],
) -> bool:
    subject = str(fact.get("subject_entity_id") or "").casefold()
    if subject and subject in {item.casefold() for item in entity_ids}:
        return True
    blob = " ".join(
        [
            str(fact.get("subject_entity_id") or ""),
            str((fact.get("value") or {}).get("label") or ""),
            str(fact.get("attribute") or ""),
        ]
    ).casefold()
    return any(needle in blob for needle in needles)


def _fact_label(fact: dict[str, Any]) -> str:
    value = fact.get("value") or {}
    if isinstance(value, dict):
        return str(value.get("label") or "")
    return str(value or "")


def _witness_packet(
    *,
    witness: dict[str, Any],
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    matched_entities = [row for row in entities if _entity_matches(row, witness["needles"])]
    entity_ids = {str(row.get("entity_id") or "") for row in matched_entities if row.get("entity_id")}
    matched_facts = [
        row for row in facts if _fact_matches(row, needles=witness["needles"], entity_ids=entity_ids)
    ]
    high = [row for row in matched_facts if str(row.get("attribute") or "") in HIGH_SIGNAL_ATTRIBUTES]
    low = [row for row in matched_facts if row not in high]
    return {
        "witness_id": witness["id"],
        "label": witness["label"],
        "entity_ids": sorted(entity_ids),
        "aliases": sorted(
            {
                name
                for entity in matched_entities
                for name in _names_for_entity(entity)
            }
        ),
        "entity_count": len(matched_entities),
        "fact_count": len(matched_facts),
        "high_signal_facts": [
            {
                "fact_id": row.get("fact_id"),
                "subject_entity_id": row.get("subject_entity_id"),
                "attribute": row.get("attribute"),
                "label": _fact_label(row),
                "source_authority": row.get("source_authority"),
                "truth_state": row.get("truth_state"),
            }
            for row in high[:40]
        ],
        "low_signal_facts": [
            {
                "fact_id": row.get("fact_id"),
                "subject_entity_id": row.get("subject_entity_id"),
                "attribute": row.get("attribute"),
                "label": _fact_label(row),
            }
            for row in low[:20]
        ],
        "human_ratings": {
            "IDENTITY_COHERENCE": "NOT_EVALUATED",
            "FACTUAL_COMPLETENESS": "NOT_EVALUATED",
            "SPECIFICITY": "NOT_EVALUATED",
            "ATOMICITY": "NOT_EVALUATED",
            "PROSE_QUALITY": "NOT_EVALUATED",
            "GM_USEFULNESS": "NOT_EVALUATED",
            "CONTINUITY_PROTECTION": "NOT_EVALUATED",
            "AUTHORITY_CORRECTNESS": "NOT_EVALUATED",
            "TEMPORAL_SHAPE": "NOT_EVALUATED",
            "NOISE": "NOT_EVALUATED",
        },
    }


def _identity_candidates(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    indexed = [
        (idx, entity, {_norm(name) for name in _names_for_entity(entity) if _norm(name)})
        for idx, entity in enumerate(entities)
    ]
    for left_idx, left, left_names in indexed:
        for right_idx, right, right_names in indexed:
            if right_idx <= left_idx:
                continue
            shared = sorted(name for name in left_names & right_names if name)
            best = 0.0
            relation = "none"
            if shared:
                best = 1.0
                relation = "exact_alias_or_name"
            else:
                for left_name in left_names:
                    for right_name in right_names:
                        score = SequenceMatcher(None, left_name, right_name).ratio()
                        if score > best:
                            best = score
                if best >= 0.82:
                    relation = "fuzzy_name"
            if relation == "none":
                continue
            candidates.append(
                {
                    "left_entity_id": left.get("entity_id"),
                    "right_entity_id": right.get("entity_id"),
                    "left_display_name": left.get("display_name"),
                    "right_display_name": right.get("display_name"),
                    "relation": relation,
                    "score": round(best, 3),
                    "shared_normalized_names": shared,
                    "classification": "POSSIBLE_LOCAL_RECONCILIATION",
                }
            )
    return candidates


def _composition_candidates(
    *, entities: list[dict[str, Any]], facts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    karsemine_ids = {
        str(row.get("entity_id") or "")
        for row in entities
        if _entity_matches(row, ["karsemine"]) and row.get("entity_id")
    }
    tripod_ids = {
        str(row.get("entity_id") or "")
        for row in entities
        if _entity_matches(row, ["tripod"]) and row.get("entity_id")
    }
    weakness = [
        row
        for row in facts
        if _fact_matches(row, needles=["weak", "resist", "poison", "fire"], entity_ids=karsemine_ids | tripod_ids)
    ]
    return [
        {
            "id": "karsemine_tripod_defense_composition",
            "karsemine_entity_ids": sorted(karsemine_ids),
            "tripod_entity_ids": sorted(tripod_ids),
            "related_fact_count": len(weakness),
            "preserves_source_linked_structure": bool(karsemine_ids and tripod_ids and weakness),
            "sample_labels": [_fact_label(row) for row in weakness[:8]],
        }
    ]


def _continuity_salience(facts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        attribute = str(fact.get("attribute") or "")
        label = _fact_label(fact).casefold()
        item = {
            "fact_id": fact.get("fact_id"),
            "subject_entity_id": fact.get("subject_entity_id"),
            "attribute": attribute,
            "label": _fact_label(fact),
        }
        if attribute in CONTINUITY_ATTRIBUTES:
            buckets["continuity_constraint"].append(item)
        if any(token in label for token in ("siege", "pressure", "hunt", "threat", "war")):
            buckets["active_pressure"].append(item)
        if attribute in {"portrayal_notes", "relationship_tags"}:
            buckets["portrayal_anchor"].append(item)
        if attribute in {"species", "rank_or_title", "role"}:
            buckets["texture"].append(item)
        if "learn" in label or attribute == "event_outcome":
            buckets["callback_hook"].append(item)
    return {key: value[:25] for key, value in buckets.items()}


def build_quality_packet(
    *,
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    arm: dict[str, Any],
) -> dict[str, Any]:
    witnesses = [
        _witness_packet(witness=witness, entities=entities, facts=facts) for witness in WITNESSES
    ]
    return {
        "schema": "dmb_campaign_memory_stage4i2_quality_packet_v1",
        "evaluator_llm": False,
        "store_mutated": False,
        "arm_id": arm.get("arm_id"),
        "model": arm.get("model"),
        "provider": arm.get("provider"),
        "service_tier": arm.get("service_tier"),
        "reasoning_effort": arm.get("reasoning_effort"),
        "raw_model_identity": {
            "entity_count": len(entities),
            "fact_count": len(facts),
        },
        "witnesses": witnesses,
        "diagnostics": {
            "identity_candidates": _identity_candidates(entities),
            "composition_candidates": _composition_candidates(entities=entities, facts=facts),
            "continuity_salience": _continuity_salience(facts),
        },
        "human_review_required": True,
    }
