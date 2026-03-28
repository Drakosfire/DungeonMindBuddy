from __future__ import annotations

from typing import Any

MAX_ENTITIES = 200
MAX_VALUES_PER_ATTRIBUTE = 5


def _entity_meta_by_id(entities: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for entity in entities:
        entity_id = str(entity.get("entity_id", "")).strip()
        if not entity_id:
            continue
        lookup[entity_id] = {
            "display_name": str(entity.get("display_name", entity_id)).strip() or entity_id,
            "entity_type": str(entity.get("entity_type", "other")).strip() or "other",
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
) -> str:
    """Render projection as structured text for the synthesis LLM."""
    projection_entities = projection.get("entities", {})
    if not projection_entities:
        return "No projected entities are available for this campaign scope."

    meta_by_id = _entity_meta_by_id(entities)
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

    for entity_id, entity_payload in ordered:
        metadata = meta_by_id.get(
            entity_id,
            {"display_name": entity_id, "entity_type": "other"},
        )
        display_name = metadata["display_name"]
        entity_type = metadata["entity_type"]
        lines.append(f"== Entity: {display_name} ({entity_type}) ==")

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
