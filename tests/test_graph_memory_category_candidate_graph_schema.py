"""Tests for category graph extraction JSON schemas."""
from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator, ValidationError

from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format,
    schema_for_pass,
)


def test_category_pass_text_format_uses_strict_json_schema() -> None:
    for pass_name in (
        "actor_pass",
        "location_pass",
        "collective_pass",
        "object_pass",
        "thread_pass",
        "beat_pass",
        "edge_pass",
    ):
        fmt = category_pass_text_format(pass_name)
        assert fmt["format"]["type"] == "json_schema"
        assert fmt["format"]["strict"] is True
        assert fmt["format"]["name"] == f"category_graph_{pass_name}"
        schema = schema_for_pass(pass_name)
        assert "required" in schema
        if pass_name == "thread_pass":
            assert "ignored_items" in schema["required"]
            assert "deferred_items" in schema["required"]
        if pass_name == "edge_pass":
            edge_items = schema["properties"]["observation_edges"]["items"]
            assert "predicate_family" in edge_items["required"]
            assert "relationship_type" in edge_items["properties"]
            assert "enum" in edge_items["properties"]["relationship_type"]
            assert "parent_of" in edge_items["properties"]["relationship_type"]["enum"]


def test_schema_for_pass_spec_uses_kind_not_literal_id() -> None:
    from src.graph_memory.extraction.category_candidate_graph_schema import (
        category_pass_text_format_for_spec,
        schema_for_pass_spec,
    )
    from src.graph_memory.extraction.extraction_profile import ExtractionPassSpec

    custom_node = ExtractionPassSpec(
        pass_id="lore_actor_pass",
        default_node_type="character",
        instruction="custom",
        progress_label="custom",
        kind="node",
    )
    custom_edge = ExtractionPassSpec(
        pass_id="lore_edge_pass",
        default_node_type=None,
        instruction="custom",
        progress_label="custom",
        kind="edge",
    )
    node_schema = schema_for_pass_spec(custom_node)
    edge_schema = schema_for_pass_spec(custom_edge)
    assert "observation_nodes" in node_schema["required"]
    assert "observation_edges" in edge_schema["required"]
    fmt = category_pass_text_format_for_spec(custom_node)
    assert fmt["format"]["type"] == "json_schema"
    assert fmt["format"]["strict"] is True
    assert fmt["format"]["name"] == "category_graph_lore_actor_pass"


def test_thread_disposition_schema_allows_only_optional_string_node_type() -> None:
    payload = {
        "observation_nodes": [],
        "ignored_items": [
            {
                "item_id": "ignored:noise",
                "label": "Background chatter",
                "reason": "not durable",
                "node_type": "mystery",
                "evidence_refs": [],
                "suggested_next_step": None,
            }
        ],
        "deferred_items": [
            {
                "item_id": "deferred:followup",
                "label": "Follow the current",
                "reason": "needs later pass",
                "node_type": "thread",
                "evidence_refs": [],
                "suggested_next_step": "revisit after session 25",
            }
        ],
    }
    validator = Draft202012Validator(schema_for_pass("thread_pass"))
    validator.validate(payload)

    without_node_type = deepcopy(payload)
    del without_node_type["ignored_items"][0]["node_type"]
    del without_node_type["deferred_items"][0]["node_type"]
    validator.validate(without_node_type)

    for section in ("ignored_items", "deferred_items"):
        for invalid_type in (None, True, {}, []):
            invalid = deepcopy(payload)
            invalid[section][0]["node_type"] = invalid_type
            with pytest.raises(ValidationError):
                validator.validate(invalid)

        invalid = deepcopy(payload)
        invalid[section][0]["unrecognized_model_field"] = "reject"
        with pytest.raises(ValidationError):
            validator.validate(invalid)

    # The narrow tolerance does not loosen the positive-node schema.
    actor_payload = {
        "observation_nodes": [
            {
                "node_id": "node:actor",
                "label": "Actor",
                "node_type": "character",
                "description": "A character.",
                "importance": "low",
                "evidence_refs": [],
                "unrecognized_model_field": "reject",
            }
        ]
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(schema_for_pass("actor_pass")).validate(actor_payload)

    # Nor does it extend the separate positive-edge schema.
    edge_item_schema = schema_for_pass("edge_pass")["properties"][
        "observation_edges"
    ]["items"]
    edge_payload = {
        "observation_edges": [
            {
                "edge_id": "edge:actor-place",
                "from_node_id": "node:actor",
                "to_node_id": "node:place",
                "label": "works at",
                "relationship_type": edge_item_schema["properties"][
                    "relationship_type"
                ]["enum"][0],
                "predicate_family": edge_item_schema["properties"][
                    "predicate_family"
                ]["enum"][0],
                "evidence_refs": [],
            }
        ]
    }
    edge_validator = Draft202012Validator(schema_for_pass("edge_pass"))
    edge_validator.validate(edge_payload)
    edge_payload["observation_edges"][0]["node_type"] = "thread"
    with pytest.raises(ValidationError):
        edge_validator.validate(edge_payload)
