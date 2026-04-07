from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.agent.scope_relevance import (
    build_entity_document_index,
    build_entity_evidence_index,
    build_evidence_document_index,
    compute_scope_relevance,
    normalize_scope_document_ids,
    scope_relevance_to_dict,
)


ACTIVE_TRUTH_STATES = {"OBSERVED", "CANON", "CANON_CANDIDATE", "PREP", "IDEA"}
REJECTED_TRUTH_STATES = {"OVERRIDDEN", "RETRACTED"}


@dataclass(frozen=True)
class FactWithLayer:
    fact: dict[str, Any]
    layer: str
    campaign_id: str | None
    source_class: str
    truth_state: str


def _fact_sort_key(
    fact: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[int, int, str]:
    session = fact.get("asserted_in_session")
    if session is None:
        session = 0
    seq = fact.get("sequence_index_within_session")
    if seq is None and evidence_by_id is not None:
        evidence_ids = fact.get("evidence_ids", [])
        orders = [
            int(evidence_by_id[eid]["source_order_index"])
            for eid in evidence_ids
            if eid in evidence_by_id
            and evidence_by_id[eid].get("source_order_index") is not None
        ]
        seq = max(orders) if orders else 0
    if seq is None:
        seq = 0
    return int(session), int(seq), str(fact["fact_id"])


def _terminal_observed_rank(label: str) -> int:
    lowered = label.lower()
    death_markers = (
        "killing blow",
        "dies",
        "dead",
        "decapitated",
    )
    if any(marker in lowered for marker in death_markers):
        return 3
    if "oily sheen in eyes fades" in lowered or "oily sheen fades" in lowered:
        return 2
    return 0


def _selection_priority(
    entry: FactWithLayer,
    *,
    campaign_id: str | None,
    contradiction_detected: bool,
    evidence_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[int, int, int, int, str]:
    session, seq, fid = _fact_sort_key(entry.fact, evidence_by_id=evidence_by_id)
    if not contradiction_detected:
        return session, seq, 0, 0, fid

    label = str(entry.fact.get("value", {}).get("label", ""))
    terminal_rank = _terminal_observed_rank(label)
    campaign_observed_rank = (
        1
        if campaign_id is not None
        and entry.layer == "campaign"
        and entry.campaign_id == campaign_id
        and entry.truth_state == "OBSERVED"
        else 0
    )
    truth_rank = 1 if entry.truth_state == "OBSERVED" else 0
    return session, seq, campaign_observed_rank, terminal_rank + truth_rank, fid


def _canonical_json_value(value: dict[str, Any]) -> tuple[str | None, str]:
    normalized = value.get("normalized")
    return normalized, str(value.get("label", ""))


def _pick_selected_fact(
    facts: list[FactWithLayer],
    selected_fact_ids: set[str],
    campaign_id: str | None,
    evidence_by_id: dict[str, dict[str, Any]] | None = None,
) -> FactWithLayer:
    selected = [fact for fact in facts if fact.fact["fact_id"] in selected_fact_ids]
    candidates = selected if selected else facts

    contradiction_detected = (
        len({_canonical_json_value(entry.fact["value"]) for entry in candidates}) > 1
    )
    return sorted(
        candidates,
        key=lambda entry: _selection_priority(
            entry,
            campaign_id=campaign_id,
            contradiction_detected=contradiction_detected,
            evidence_by_id=evidence_by_id,
        ),
    )[-1]


def _group_facts(facts: list[FactWithLayer]) -> dict[tuple[str, str], list[FactWithLayer]]:
    groups: dict[tuple[str, str], list[FactWithLayer]] = defaultdict(list)
    for fact in facts:
        key = (str(fact.fact["subject_entity_id"]), str(fact.fact["attribute"]))
        groups[key].append(fact)
    return groups


def _derive_conflicts(
    grouped_facts: dict[tuple[str, str], list[FactWithLayer]],
    provided_conflicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    conflicts_by_id: dict[str, dict[str, Any]] = {
        conflict["conflict_id"]: conflict for conflict in provided_conflicts
    }
    generated_idx = 0
    for (entity_id, attribute), facts in grouped_facts.items():
        distinct = {
            _canonical_json_value(entry.fact["value"]): entry.fact["fact_id"] for entry in facts
        }
        if len(distinct) <= 1:
            continue
        fact_ids = sorted(entry.fact["fact_id"] for entry in facts)
        generated_idx += 1
        conflict_id = f"auto_conflict_{generated_idx:03d}"
        conflicts_by_id[conflict_id] = {
            "conflict_id": conflict_id,
            "conflict_type": "source_conflict",
            "entity_id": entity_id,
            "attribute": attribute,
            "fact_ids": fact_ids,
            "conflict_status": "open",
            "blocking": False,
            "record_status": "active",
        }
    return [conflicts_by_id[key] for key in sorted(conflicts_by_id)]


def _fact_layers_by_evidence(
    evidence_by_id: dict[str, dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[FactWithLayer]:
    output: list[FactWithLayer] = []
    for fact in facts:
        evidence_ids = fact.get("evidence_ids", [])
        if not evidence_ids:
            raise ValueError(f"Fact {fact.get('fact_id')} has no evidence_ids")
        layers = {(evidence_by_id[evidence_id]["canon_layer"], evidence_by_id[evidence_id]["campaign_id"]) for evidence_id in evidence_ids}
        if len(layers) != 1:
            raise ValueError(
                f"Fact {fact.get('fact_id')} mixes evidence layers: {sorted(layers)}"
            )
        layer, campaign_id = next(iter(layers))
        output.append(
            FactWithLayer(
                fact=fact,
                layer=layer,
                campaign_id=campaign_id,
                source_class=str(evidence_by_id[evidence_ids[0]].get("source_class", "unknown")),
                truth_state=str(fact.get("truth_state", "CANON")),
            )
        )
    return output


def _applicable_fact(
    fact: FactWithLayer,
    campaign_id: str | None,
) -> bool:
    if fact.truth_state in REJECTED_TRUTH_STATES:
        return False
    if fact.truth_state not in ACTIVE_TRUTH_STATES:
        return False
    if fact.fact.get("record_status") != "active":
        return False
    if fact.layer == "world":
        return True
    if fact.layer == "campaign":
        return campaign_id is not None and fact.campaign_id == campaign_id
    return False


def _applicable_decision(decision: dict[str, Any], campaign_id: str | None) -> bool:
    decision_campaign_id = decision.get("campaign_id")
    if decision_campaign_id is None:
        return True
    if campaign_id is None:
        return False
    return decision_campaign_id == campaign_id


def project_entity_state(
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    canon_decisions: list[dict[str, Any]],
    campaign_id: str | None,
) -> dict[str, Any]:
    evidence_by_id = {entry["evidence_id"]: entry for entry in evidence_units}
    layered_facts = _fact_layers_by_evidence(evidence_by_id=evidence_by_id, facts=facts)
    active_facts = [fact for fact in layered_facts if _applicable_fact(fact=fact, campaign_id=campaign_id)]
    grouped = _group_facts(facts=active_facts)
    all_conflicts = _derive_conflicts(grouped_facts=grouped, provided_conflicts=conflicts)

    applicable_decisions = [
        decision
        for decision in canon_decisions
        if decision.get("record_status") == "active" and _applicable_decision(decision, campaign_id)
    ]
    selected_fact_ids: set[str] = set()
    resolved_conflict_ids: set[str] = set()
    for decision in applicable_decisions:
        effect = decision.get("effect", {})
        selected_fact_ids.update(effect.get("selected_fact_ids", []))
        resolved_conflict_ids.update(decision.get("resolves_conflict_ids", []))

    projection_entities: dict[str, dict[str, Any]] = {}
    for (entity_id, attribute), entries in sorted(grouped.items()):
        picked = _pick_selected_fact(
            facts=entries,
            selected_fact_ids=selected_fact_ids,
            campaign_id=campaign_id,
            evidence_by_id=evidence_by_id,
        )
        layer = picked.layer
        value = picked.fact["value"]
        if entity_id not in projection_entities:
            projection_entities[entity_id] = {"attributes": {}}
        observed_labels: list[str] = []
        canon_labels: list[str] = []
        seen_labels: set[str] = set()
        for entry in entries:
            label = str(entry.fact["value"].get("label", "")).strip()
            if not label or label in seen_labels:
                continue
            seen_labels.add(label)
            if entry.truth_state == "OBSERVED":
                observed_labels.append(label)
            else:
                canon_labels.append(label)
        all_labels = sorted(observed_labels) + sorted(canon_labels)
        projection_entities[entity_id]["attributes"][attribute] = {
            "selected_fact_id": picked.fact["fact_id"],
            "value_label": value.get("label"),
            "value_normalized": value.get("normalized"),
            "all_value_labels": all_labels,
            "source_layer": layer,
            "source_campaign_id": picked.campaign_id,
            "source_class": picked.source_class,
            "source_truth_state": picked.truth_state,
            "fact_ids": sorted(entry.fact["fact_id"] for entry in entries),
            "provenance_evidence_ids": sorted(
                {evidence_id for entry in entries for evidence_id in entry.fact["evidence_ids"]}
            ),
            "conflict_ids": sorted(
                conflict["conflict_id"]
                for conflict in all_conflicts
                if conflict.get("entity_id") == entity_id
                and conflict.get("attribute") == attribute
                and any(fact_id in conflict.get("fact_ids", []) for fact_id in [entry.fact["fact_id"] for entry in entries])
            ),
        }

    projection_conflicts = []
    open_conflicts = 0
    resolved_conflicts = 0
    for conflict in sorted(all_conflicts, key=lambda item: str(item["conflict_id"])):
        is_resolved = conflict["conflict_id"] in resolved_conflict_ids
        projection_conflicts.append(
            {
                "conflict_id": conflict["conflict_id"],
                "entity_id": conflict.get("entity_id"),
                "attribute": conflict.get("attribute"),
                "fact_ids": sorted(conflict.get("fact_ids", [])),
                "status": "resolved" if is_resolved else "open",
            }
        )
        if is_resolved:
            resolved_conflicts += 1
        else:
            open_conflicts += 1

    return {
        "campaign_id": campaign_id,
        "entities": projection_entities,
        "conflicts": projection_conflicts,
        "metrics": {
            "open_conflicts": open_conflicts,
            "resolved_conflicts": resolved_conflicts,
            "projected_entities": len(projection_entities),
        },
    }


def attach_scope_relevance_metadata(
    *,
    projection: dict[str, Any],
    evidence_units: list[dict[str, Any]],
    scope_document_ids: list[str] | set[str] | None,
    scope_confidence: float = 1.0,
    min_scope_confidence: float = 0.75,
    min_entity_evidence_count: int = 2,
    mentioned_entity_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Attach confidence-aware scope relevance metadata to projection entities."""
    projection_copy = deepcopy(projection)
    projection_entities = projection_copy.get("entities", {})
    if not isinstance(projection_entities, dict):
        return projection_copy

    scope_doc_ids = normalize_scope_document_ids(scope_document_ids)
    if not scope_doc_ids:
        return projection_copy

    evidence_document_by_id = build_evidence_document_index(evidence_units)
    entity_evidence_index = build_entity_evidence_index(projection_entities)
    entity_document_index = build_entity_document_index(entity_evidence_index, evidence_document_by_id)
    mentioned = mentioned_entity_ids or set()
    pruning_candidates: list[str] = []

    for entity_id, entity_payload in projection_entities.items():
        if not isinstance(entity_payload, dict):
            continue
        relevance = compute_scope_relevance(
            entity_document_ids=entity_document_index.get(entity_id, set()),
            entity_evidence_count=len(entity_evidence_index.get(entity_id, set())),
            scope_document_ids=scope_doc_ids,
            scope_confidence=scope_confidence,
            min_scope_confidence=min_scope_confidence,
            min_entity_evidence_count=min_entity_evidence_count,
            mentioned_in_question=entity_id in mentioned,
        )
        relevance_payload = scope_relevance_to_dict(relevance)
        entity_payload["scope_relevance"] = relevance_payload
        if relevance_payload.get("pruning_candidate"):
            pruning_candidates.append(entity_id)

    projection_copy["scope_relevance"] = {
        "scope_document_ids": sorted(scope_doc_ids),
        "scope_confidence": scope_confidence,
        "min_scope_confidence": min_scope_confidence,
        "min_entity_evidence_count": min_entity_evidence_count,
        "pruning_candidates": sorted(pruning_candidates),
    }
    return projection_copy

