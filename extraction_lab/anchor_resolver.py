from __future__ import annotations

import re
from typing import Any

from extraction_lab.anchor_schema import EntityGoldAnchor, FactGoldAnchor


def _normalize(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip(".,;:!?()[]{}\"'")


def _entity_names(entity: dict[str, Any]) -> set[str]:
    names = {_normalize(str(entity.get("display_name", "")))}
    names.update(_normalize(str(alias)) for alias in entity.get("aliases", []))
    return {name for name in names if name}


def resolve_entity_anchor(
    anchor: EntityGoldAnchor,
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_names = {_normalize(name) for name in anchor.expected_names if _normalize(name)}
    if not entities:
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "missing_entity",
        }

    name_matches: list[dict[str, Any]] = []
    for entity in entities:
        if expected_names and _entity_names(entity).intersection(expected_names):
            name_matches.append(entity)

    if not name_matches:
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "name_not_found",
        }

    class_matches = [
        entity
        for entity in name_matches
        if str(entity.get("entity_class", "")).strip().lower() == anchor.expected_class
    ]
    if not class_matches:
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "class_mismatch",
        }

    matched_entity = class_matches[0]
    if anchor.min_fact_count is not None:
        subject_id = str(matched_entity.get("entity_id", "")).strip()
        fact_count = sum(1 for fact in facts if str(fact.get("subject_entity_id", "")).strip() == subject_id)
        if fact_count < anchor.min_fact_count:
            return {
                "anchor_id": anchor.anchor_id,
                "surface": anchor.surface,
                "passed": False,
                "fail_bucket": "fact_count_below_min",
                "resolved_entity_id": subject_id,
                "fact_count": fact_count,
                "min_fact_count": anchor.min_fact_count,
            }

    return {
        "anchor_id": anchor.anchor_id,
        "surface": anchor.surface,
        "passed": True,
        "fail_bucket": None,
        "resolved_entity_id": matched_entity.get("entity_id"),
        "resolved_display_name": matched_entity.get("display_name"),
        "resolved_entity_class": matched_entity.get("entity_class"),
    }


def resolve_fact_anchor(
    anchor: FactGoldAnchor,
    resolved_entities: dict[str, dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    subject_resolution = resolved_entities.get(anchor.subject_anchor)
    if not subject_resolution or not subject_resolution.get("passed"):
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "subject_unresolved",
        }

    subject_entity_id = str(subject_resolution.get("resolved_entity_id", "")).strip()
    subject_facts = [fact for fact in facts if str(fact.get("subject_entity_id", "")).strip() == subject_entity_id]
    if not subject_facts:
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "missing_fact",
            "subject_entity_id": subject_entity_id,
        }

    allowed_attributes = {anchor.expected_attribute, *anchor.alternative_attributes}
    attr_matches = [fact for fact in subject_facts if str(fact.get("attribute", "")).strip() in allowed_attributes]
    if not attr_matches:
        return {
            "anchor_id": anchor.anchor_id,
            "surface": anchor.surface,
            "passed": False,
            "fail_bucket": "attribute_mismatch",
            "subject_entity_id": subject_entity_id,
        }

    normalized_keywords = [_normalize(keyword) for keyword in anchor.match_keywords if _normalize(keyword)]
    for fact in attr_matches:
        value = fact.get("value", {}) if isinstance(fact.get("value"), dict) else {}
        text_parts = [str(value.get("label", "")), str(value.get("normalized", ""))]
        text_parts.extend(str(item) for item in value.get("values", []) if item is not None)
        haystack = _normalize(" ".join(text_parts))
        if not normalized_keywords or any(keyword in haystack for keyword in normalized_keywords):
            return {
                "anchor_id": anchor.anchor_id,
                "surface": anchor.surface,
                "passed": True,
                "fail_bucket": None,
                "subject_entity_id": subject_entity_id,
                "matched_fact_id": fact.get("fact_id"),
                "matched_attribute": fact.get("attribute"),
            }

    return {
        "anchor_id": anchor.anchor_id,
        "surface": anchor.surface,
        "passed": False,
        "fail_bucket": "keyword_mismatch",
        "subject_entity_id": subject_entity_id,
    }


def resolve_entity_anchors(
    anchors: list[EntityGoldAnchor],
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [resolve_entity_anchor(anchor, entities, facts) for anchor in anchors]


def resolve_fact_anchors(
    anchors: list[FactGoldAnchor],
    resolved_entities: dict[str, dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [resolve_fact_anchor(anchor, resolved_entities, facts) for anchor in anchors]
