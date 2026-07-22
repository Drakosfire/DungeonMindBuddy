"""Tests for category graph extraction JSON schemas."""
from __future__ import annotations

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