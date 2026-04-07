from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ScopeRelevance:
    classification: str
    scope_overlap: float
    in_scope_document_ids: list[str]
    all_document_ids: list[str]
    in_scope_document_count: int
    total_evidence_count: int
    pruning_candidate: bool
    decision_reason: str
    mentioned_in_question: bool


def normalize_scope_document_ids(scope_document_ids: list[str] | set[str] | None) -> set[str]:
    if not scope_document_ids:
        return set()
    return {str(doc_id).strip() for doc_id in scope_document_ids if str(doc_id).strip()}


def build_evidence_document_index(evidence_units: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(unit.get("evidence_id", "")).strip(): str(unit.get("document_id", "")).strip()
        for unit in evidence_units
        if str(unit.get("evidence_id", "")).strip() and str(unit.get("document_id", "")).strip()
    }


def entity_evidence_ids_from_projection_entity(entity_payload: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    attributes = entity_payload.get("attributes", {})
    if not isinstance(attributes, dict):
        return evidence_ids
    for attribute_payload in attributes.values():
        if not isinstance(attribute_payload, dict):
            continue
        provenance = attribute_payload.get("provenance_evidence_ids", [])
        if isinstance(provenance, list):
            evidence_ids.update(str(eid).strip() for eid in provenance if str(eid).strip())
    return evidence_ids


def build_entity_evidence_index(
    projection_entities: dict[str, dict[str, Any]]
) -> dict[str, set[str]]:
    return {
        entity_id: entity_evidence_ids_from_projection_entity(entity_payload)
        for entity_id, entity_payload in projection_entities.items()
    }


def build_entity_document_index(
    entity_evidence_ids: dict[str, set[str]], evidence_document_by_id: dict[str, str]
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for entity_id, evidence_ids in entity_evidence_ids.items():
        index[entity_id] = {
            evidence_document_by_id[eid]
            for eid in evidence_ids
            if eid in evidence_document_by_id and evidence_document_by_id[eid]
        }
    return index


def question_mentioned_entity_ids(
    question: str | None, entities: list[dict[str, Any]]
) -> set[str]:
    if not question:
        return set()
    lowered = question.lower()
    mentioned: set[str] = set()
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        names = [str(entity.get("display_name", "")).strip()]
        aliases = entity.get("aliases", [])
        if isinstance(aliases, list):
            names.extend(str(alias).strip() for alias in aliases)
        if any(name and name.lower() in lowered for name in names):
            mentioned.add(entity_id)
    return mentioned


def compute_scope_relevance(
    *,
    entity_document_ids: set[str],
    entity_evidence_count: int,
    scope_document_ids: set[str],
    scope_confidence: float,
    min_scope_confidence: float,
    min_entity_evidence_count: int,
    mentioned_in_question: bool,
) -> ScopeRelevance:
    in_scope_document_ids = sorted(entity_document_ids & scope_document_ids)
    all_document_ids = sorted(entity_document_ids)
    overlap = (
        len(in_scope_document_ids) / len(all_document_ids)
        if all_document_ids
        else 0.0
    )

    if in_scope_document_ids:
        classification = "in_scope"
        reason = "has_in_scope_document_overlap"
    elif not all_document_ids:
        classification = "unknown_insufficient_signal"
        reason = "no_document_provenance"
    elif mentioned_in_question:
        classification = "unknown_insufficient_signal"
        reason = "entity_mentioned_in_question"
    elif scope_confidence < min_scope_confidence:
        classification = "unknown_insufficient_signal"
        reason = "scope_confidence_below_threshold"
    elif entity_evidence_count < min_entity_evidence_count:
        classification = "unknown_insufficient_signal"
        reason = "entity_evidence_below_threshold"
    else:
        classification = "out_of_scope_confident"
        reason = "no_scope_overlap_with_confident_signal"

    return ScopeRelevance(
        classification=classification,
        scope_overlap=round(overlap, 6),
        in_scope_document_ids=in_scope_document_ids,
        all_document_ids=all_document_ids,
        in_scope_document_count=len(in_scope_document_ids),
        total_evidence_count=entity_evidence_count,
        pruning_candidate=(classification == "out_of_scope_confident"),
        decision_reason=reason,
        mentioned_in_question=mentioned_in_question,
    )


def scope_relevance_to_dict(value: ScopeRelevance) -> dict[str, Any]:
    payload = asdict(value)
    # Backward-compat alias for older consumers; value is document-count granularity.
    payload["in_scope_evidence_count"] = payload["in_scope_document_count"]
    return payload
