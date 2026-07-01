"""Strict JSON schemas for category-decomposed graph extraction passes."""
from __future__ import annotations

from typing import Any, Literal, Sequence

from src.graph_memory.predicate_catalog import exact_predicate_ids, predicate_family_ids

PASS_NAMES = (
    "actor_pass",
    "location_pass",
    "collective_pass",
    "object_pass",
    "thread_pass",
    "beat_pass",
    "encounter_job_pass",
    "edge_pass",
)

ImportanceLiteral = Literal["high", "medium", "low"]


def _evidence_ref_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_span_ref_id": {"type": "string"},
            "anchor_quotes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["source_span_ref_id", "anchor_quotes"],
    }


def _observation_node_schema(
    *,
    allowed_node_types: Sequence[str] | None = None,
) -> dict[str, Any]:
    node_type_schema: dict[str, Any] = {"type": "string"}
    if allowed_node_types is not None:
        node_type_schema["enum"] = list(allowed_node_types)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "node_id": {"type": "string"},
            "label": {"type": "string"},
            "node_type": node_type_schema,
            "description": {"type": ["string", "null"]},
            "importance": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "evidence_refs": {
                "type": "array",
                "items": _evidence_ref_schema(),
            },
        },
        "required": [
            "node_id",
            "label",
            "node_type",
            "description",
            "importance",
            "evidence_refs",
        ],
    }


def _disposition_item_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "item_id": {"type": "string"},
            "label": {"type": "string"},
            "reason": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": _evidence_ref_schema(),
            },
            "suggested_next_step": {"type": ["string", "null"]},
        },
        "required": ["item_id", "label", "reason", "evidence_refs", "suggested_next_step"],
    }


def category_node_pass_json_schema(
    *,
    include_dispositions: bool = False,
    allowed_node_types: Sequence[str] | None = None,
) -> dict[str, Any]:
    props: dict[str, Any] = {
        "observation_nodes": {
            "type": "array",
            "items": _observation_node_schema(allowed_node_types=allowed_node_types),
        },
    }
    required = ["observation_nodes"]
    if include_dispositions:
        props["ignored_items"] = {"type": "array", "items": _disposition_item_schema()}
        props["deferred_items"] = {"type": "array", "items": _disposition_item_schema()}
        required.extend(["ignored_items", "deferred_items"])
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": props,
        "required": required,
    }


def category_beat_pass_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "observation_beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "beat_id": {"type": "string"},
                        "order": {"type": "integer"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "involved_node_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "evidence_refs": {
                            "type": "array",
                            "items": _evidence_ref_schema(),
                        },
                    },
                    "required": [
                        "beat_id",
                        "order",
                        "title",
                        "summary",
                        "involved_node_ids",
                        "evidence_refs",
                    ],
                },
            },
        },
        "required": ["observation_beats"],
    }


def category_edge_pass_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "observation_edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "edge_id": {"type": "string"},
                        "from_node_id": {"type": "string"},
                        "to_node_id": {"type": "string"},
                        "label": {"type": "string"},
                        "relationship_type": {
                            "type": "string",
                            "enum": list(exact_predicate_ids()),
                        },
                        "predicate_family": {
                            "type": "string",
                            "enum": list(predicate_family_ids()),
                        },
                        "evidence_refs": {
                            "type": "array",
                            "items": _evidence_ref_schema(),
                        },
                    },
                    "required": [
                        "edge_id",
                        "from_node_id",
                        "to_node_id",
                        "label",
                        "relationship_type",
                        "predicate_family",
                        "evidence_refs",
                    ],
                },
            },
        },
        "required": ["observation_edges"],
    }


def schema_for_pass(pass_name: str) -> dict[str, Any]:
    if pass_name == "thread_pass":
        return category_node_pass_json_schema(include_dispositions=True)
    if pass_name == "beat_pass":
        return category_beat_pass_json_schema()
    if pass_name == "edge_pass":
        return category_edge_pass_json_schema()
    if pass_name == "encounter_job_pass":
        return category_node_pass_json_schema(
            include_dispositions=False,
            allowed_node_types=("combat_encounter", "quest"),
        )
    if pass_name in {"actor_pass", "location_pass", "collective_pass", "object_pass"}:
        return category_node_pass_json_schema(include_dispositions=False)
    raise ValueError(f"unknown category pass: {pass_name}")


def category_pass_text_format(pass_name: str, *, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": f"category_graph_{pass_name}",
            "strict": strict,
            "schema": schema_for_pass(pass_name),
        }
    }
