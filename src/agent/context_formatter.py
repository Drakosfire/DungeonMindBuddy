from __future__ import annotations

from typing import Any

from src.agent.scope_relevance import (
    build_entity_document_index,
    build_entity_evidence_index,
    build_evidence_document_index,
    compute_scope_relevance,
    normalize_scope_document_ids,
    question_mentioned_entity_ids,
    scope_relevance_to_dict,
)

MAX_ENTITIES = 200
MAX_VALUES_PER_ATTRIBUTE = 5
DEFAULT_MIN_SCOPE_CONFIDENCE = 0.75
DEFAULT_MIN_ENTITY_EVIDENCE_COUNT = 2
DEFAULT_UNKNOWN_EXPLORATION_QUOTA = 10


def _entity_meta_by_id(entities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        tags = entity.get("entity_tags")
        tag_list = [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else []
        lookup[entity_id] = {
            "display_name": str(entity.get("display_name", entity_id)).strip() or entity_id,
            "entity_class": str(entity.get("entity_class", entity.get("entity_type", "concept"))).strip()
            or "concept",
            "entity_tags": tag_list,
            "subtype_facets": [
                str(t).strip()
                for t in (entity.get("subtype_facets") or entity.get("semantic_facets") or [])
                if str(t).strip()
            ],
            "aliases": [
                str(alias).strip() for alias in (entity.get("aliases") or []) if str(alias).strip()
            ],
        }
    return lookup


def _truth_state_from_payload(attribute_payload: dict[str, Any]) -> str:
    explicit = str(attribute_payload.get("source_truth_state", "")).strip()
    if explicit:
        return explicit
    source_layer = str(attribute_payload.get("source_layer", "unknown"))
    if source_layer == "world":
        return "CANON"
    if source_layer == "campaign":
        return "CAMPAIGN"
    return "UNKNOWN"


def _entity_fact_count(entity_payload: dict[str, Any]) -> int:
    attributes = entity_payload.get("attributes", {})
    count = 0
    for attribute_payload in attributes.values():
        fact_ids = attribute_payload.get("fact_ids", [])
        count += len(fact_ids) if isinstance(fact_ids, list) else 1
    return count


def format_projection_context(
    projection: dict[str, Any],
    entities: list[dict[str, Any]],
    question: str | None = None,
    *,
    evidence_units: list[dict[str, Any]] | None = None,
    scope_document_ids: list[str] | set[str] | None = None,
    scope_confidence: float = 1.0,
    min_scope_confidence: float = DEFAULT_MIN_SCOPE_CONFIDENCE,
    min_entity_evidence_count: int = DEFAULT_MIN_ENTITY_EVIDENCE_COUNT,
    hard_exclude_out_of_scope: bool = False,
    unknown_exploration_quota: int = DEFAULT_UNKNOWN_EXPLORATION_QUOTA,
    include_scope_annotations: bool = False,
) -> str:
    """Render projection as structured text for the synthesis LLM."""
    projection_entities = projection.get("entities", {})
    if not projection_entities:
        return "No projected entities are available for this campaign scope."

    meta_by_id = _entity_meta_by_id(entities)
    scope_doc_ids = normalize_scope_document_ids(scope_document_ids)
    scope_enabled = bool(scope_doc_ids and evidence_units)
    mentioned_entity_ids = question_mentioned_entity_ids(question, entities) if scope_enabled else set()
    scope_relevance_by_entity: dict[str, dict[str, Any]] = {}
    if scope_enabled:
        evidence_document_by_id = build_evidence_document_index(evidence_units or [])
        entity_evidence_index = build_entity_evidence_index(projection_entities)
        entity_document_index = build_entity_document_index(entity_evidence_index, evidence_document_by_id)
        for entity_id, entity_payload in projection_entities.items():
            relevance = compute_scope_relevance(
                entity_document_ids=entity_document_index.get(entity_id, set()),
                entity_evidence_count=len(entity_evidence_index.get(entity_id, set())),
                scope_document_ids=scope_doc_ids,
                scope_confidence=scope_confidence,
                min_scope_confidence=min_scope_confidence,
                min_entity_evidence_count=min_entity_evidence_count,
                mentioned_in_question=entity_id in mentioned_entity_ids,
            )
            scope_relevance_by_entity[entity_id] = scope_relevance_to_dict(relevance)

    if scope_enabled:
        in_scope: list[tuple[str, dict[str, Any]]] = []
        unknown: list[tuple[str, dict[str, Any]]] = []
        out_of_scope_confident: list[tuple[str, dict[str, Any]]] = []
        for item in projection_entities.items():
            entity_id = item[0]
            classification = scope_relevance_by_entity[entity_id]["classification"]
            if classification == "in_scope":
                in_scope.append(item)
            elif classification == "out_of_scope_confident":
                out_of_scope_confident.append(item)
            else:
                unknown.append(item)
        in_scope.sort(key=lambda item: _entity_fact_count(item[1]), reverse=True)
        unknown.sort(key=lambda item: _entity_fact_count(item[1]), reverse=True)
        out_of_scope_confident.sort(key=lambda item: _entity_fact_count(item[1]), reverse=True)

        unknown_quota = max(0, int(unknown_exploration_quota))
        if unknown_quota and unknown:
            unknown_reserved = min(unknown_quota, len(unknown))
            in_scope_budget = max(0, MAX_ENTITIES - unknown_reserved)
            pre_truncation_ordered = (
                in_scope[:in_scope_budget]
                + unknown[:unknown_reserved]
                + in_scope[in_scope_budget:]
                + unknown[unknown_reserved:]
            )
        else:
            pre_truncation_ordered = in_scope + unknown
        if not hard_exclude_out_of_scope:
            pre_truncation_ordered.extend(out_of_scope_confident)
        ordered = pre_truncation_ordered
    else:
        ordered = sorted(
            projection_entities.items(),
            key=lambda item: _entity_fact_count(item[1]),
            reverse=True,
        )

    truncated = len(ordered) > MAX_ENTITIES
    if truncated:
        ordered = ordered[:MAX_ENTITIES]

    lines: list[str] = []
    if question:
        lines.append(f"Question: {question}")
        lines.append("")
    if scope_enabled:
        lines.append(
            "Scope policy: confidence-aware relevance "
            f"(scope_docs={len(scope_doc_ids)}, scope_confidence={scope_confidence:.2f}, "
            f"min_scope_confidence={min_scope_confidence:.2f}, "
            f"min_entity_evidence_count={min_entity_evidence_count}, "
            f"hard_exclude_out_of_scope={hard_exclude_out_of_scope}, "
            f"unknown_exploration_quota={max(0, int(unknown_exploration_quota))})"
        )
        lines.append("")

    for entity_id, entity_payload in ordered:
        metadata = meta_by_id.get(
            entity_id,
            {
                "display_name": entity_id,
                "entity_class": "concept",
                "entity_tags": [],
                "subtype_facets": [],
                "aliases": [],
            },
        )
        display_name = metadata["display_name"]
        entity_class = metadata["entity_class"]
        tag_list = metadata.get("entity_tags") or []
        facet_list = metadata.get("subtype_facets") or []
        if tag_list:
            tag_suffix = " [" + ", ".join(tag_list) + "]"
        else:
            tag_suffix = ""
        if facet_list:
            facet_suffix = " {" + ", ".join(facet_list) + "}"
        else:
            facet_suffix = ""
        lines.append(f"== Entity: {display_name} ({entity_class}){tag_suffix}{facet_suffix} ==")
        if scope_enabled and include_scope_annotations:
            relevance = scope_relevance_by_entity.get(entity_id, {})
            lines.append(
                "  [scope_relevance: "
                f"classification={relevance.get('classification', 'unknown')}, "
                f"overlap={relevance.get('scope_overlap', 0.0)}, "
                f"reason={relevance.get('decision_reason', 'n/a')}, "
                f"pruning_candidate={relevance.get('pruning_candidate', False)}]"
            )

        attributes = entity_payload.get("attributes", {})
        if not attributes:
            lines.append("  (no projected attributes)")
            lines.append("")
            continue

        conflict_lines: list[str] = []
        for attribute, attribute_payload in sorted(attributes.items()):
            all_labels = attribute_payload.get("all_value_labels")
            value_label = str(attribute_payload.get("value_label", "")).strip() or "(no value)"
            source_layer = str(attribute_payload.get("source_layer", "unknown"))
            truth_state = _truth_state_from_payload(attribute_payload)
            selected_fact_id = str(attribute_payload.get("selected_fact_id", ""))
            source_campaign_id = attribute_payload.get("source_campaign_id")
            source_class = str(attribute_payload.get("source_class", "")).strip()
            source_summary = f"layer={source_layer}"
            if source_campaign_id:
                source_summary += f", campaign={source_campaign_id}"
            if source_class:
                source_summary += f", source_class={source_class}"
            if selected_fact_id:
                source_summary += f", fact={selected_fact_id}"

            if all_labels and len(all_labels) > 1:
                shown = all_labels[:MAX_VALUES_PER_ATTRIBUTE]
                display_value = "; ".join(shown)
                if len(all_labels) > MAX_VALUES_PER_ATTRIBUTE:
                    display_value += f" (+{len(all_labels) - MAX_VALUES_PER_ATTRIBUTE} more)"
            else:
                display_value = value_label
            lines.append(f"  {attribute}: {display_value}")
            lines.append(f"    [{truth_state}, from: {source_summary}]")

            conflict_ids = attribute_payload.get("conflict_ids", [])
            if isinstance(conflict_ids, list) and conflict_ids:
                conflict_lines.append(
                    f"    {attribute}: {len(conflict_ids)} competing facts ({', '.join(conflict_ids)})"
                )

        if conflict_lines:
            lines.append("  CONFLICTS:")
            lines.extend(conflict_lines)

        lines.append("")

    if truncated:
        remaining = len(projection_entities) - MAX_ENTITIES
        lines.append(
            f"[Context truncated to top {MAX_ENTITIES} entities by fact count; {remaining} more entities omitted.]"
        )

    return "\n".join(lines).strip()
