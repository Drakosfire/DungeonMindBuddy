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
