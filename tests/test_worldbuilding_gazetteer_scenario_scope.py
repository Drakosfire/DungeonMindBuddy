from __future__ import annotations

from copy import deepcopy

import pytest

from src.graph_memory.extraction.worldbuilding_gazetteer_scenario_scope import (
    GAZETTEER_PREPARED_SCENARIO_PROFILE,
    compile_gazetteer_scenario_scope,
    prepared_scenario_sections,
    retain_durable_gazetteer_scope,
)
from src.graph_memory.extraction.worldbuilding_source_sections import (
    SourceSectionRetentionError,
)


def _rows(*texts: str) -> list[dict[str, object]]:
    return [
        {
            "source_span_ref_id": f"span:{line}",
            "line_start": line,
            "line_end": line,
            "text": text,
        }
        for line, text in enumerate(texts, 1)
    ]


def _ref(row: dict[str, object]) -> dict[str, object]:
    return {
        "source_span_ref_id": row["source_span_ref_id"],
        "anchor_quotes": [row["text"]],
    }


def _graph(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "nodes": [
            {
                "node_id": "thalia", "label": "Thalia Ashenvale",
                "node_type": "character", "description": "Commander of the Guard.",
                "evidence_refs": [_ref(rows[1])],
            },
            {
                "node_id": "guard", "label": "City Guard",
                "node_type": "organization",
                "description": "Durable command plus prepared gate-scene claims.",
                "aliases": ["gate guards"],
                "evidence_refs": [_ref(rows[1]), _ref(rows[7])],
            },
            {
                "node_id": "hook", "label": "Rescue Mission",
                "node_type": "event", "description": "An unplayed hook.",
                "evidence_refs": [_ref(rows[3])],
            },
            {
                "node_id": "fields", "label": "Agricultural Fields",
                "node_type": "location", "description": "Approach scenery.",
                "evidence_refs": [_ref(rows[9])],
            },
        ],
        "edges": [
            {
                "edge_id": "commands", "from_node_id": "thalia",
                "to_node_id": "guard", "label": "Thalia commands the Guard",
                "relationship_type": "commands",
                "evidence_refs": [_ref(rows[1])],
            },
            {
                "edge_id": "hook-at-fields", "from_node_id": "hook",
                "to_node_id": "fields", "label": "Hook at fields",
                "relationship_type": "occurs_at",
                "evidence_refs": [_ref(rows[9])],
            },
        ],
        "deferred_items": [],
    }


def test_scope_preserves_intervening_reaches_and_excludes_only_named_scene_sections():
    rows = _rows(
        "# The City of Mirathorn",
        "**Commander Thalia Ashenvale** – **Commander of the Guard**",
        "#### Plot Hooks and Encounters",
        "**Rescue Mission:** Freeing captives from a hideout.",
        "## Quirks of the Elderwyld",
        "### Unit Name: Reaches",
        "One Reach is equivalent to 8 kilometers.",
        "## Approach to Mirathorn",
        "### 1. Agricultural Landscape",
        "## Agricultural Fields:",
        "As the players approach, they see fields.",
    )
    sections = prepared_scenario_sections(rows)
    assert [item["heading"] for item in sections] == [
        "Plot Hooks and Encounters", "Approach to Mirathorn",
    ]
    assert sections[0]["source_span_ref_ids"] == ["span:3", "span:4"]
    assert sections[1]["source_span_ref_ids"] == [
        "span:8", "span:9", "span:10", "span:11",
    ]
    assert "span:6" not in {
        ref for item in sections for ref in item["source_span_ref_ids"]
    }


def test_scene_candidates_are_deferred_and_mixed_node_is_reduced_to_durable_identity():
    rows = _rows(
        "# The City of Mirathorn",
        "**Commander Thalia Ashenvale** – **Commander of the Guard**",
        "#### Plot Hooks and Encounters",
        "**Rescue Mission:** Freeing captives from a hideout.",
        "## Quirks of the Elderwyld",
        "### Unit Name: Reaches",
        "One Reach is equivalent to 8 kilometers.",
        "## Approach to Mirathorn",
        "### 1. Agricultural Landscape",
        "As the players approach, they see fields.",
        "The guards manage tolls at the gate.",
    )
    graph = _graph(rows)
    original = deepcopy(graph)
    result, diagnostics = retain_durable_gazetteer_scope(graph, rows)
    scope = diagnostics

    assert graph == original
    assert [node["node_id"] for node in result["nodes"]] == ["thalia", "guard"]
    guard = result["nodes"][1]
    assert guard["description"] == ""
    assert guard["aliases"] == []
    assert [ref["source_span_ref_id"] for ref in guard["evidence_refs"]] == ["span:2"]
    assert [edge["edge_id"] for edge in result["edges"]] == ["commands"]
    assert scope["deferred_node_ids"] == ["fields", "hook"]
    assert scope["sanitized_node_ids"] == ["guard"]
    assert scope["deferred_edge_ids"] == ["hook-at-fields"]
    assert len(scope["deferred_proposals"]) == 4
    suppressed = [
        item for item in scope["deferred_proposals"].values()
        if "decision" not in item
    ]
    sanitized = next(
        item for item in scope["deferred_proposals"].values()
        if item.get("decision") == "identity_retained_description_and_aliases_cleared"
    )
    assert len(suppressed) == 3
    assert all(
        ref.get("source_span_ref_id") in {"span:4", "span:10"}
        for proposal in suppressed
        for ref in proposal["proposal"].get("evidence_refs", [])
    )
    assert [
        ref["source_span_ref_id"]
        for ref in sanitized["proposal"]["evidence_refs"]
    ] == ["span:2", "span:8"]
    assert all(
        edge["from_node_id"] in {node["node_id"] for node in result["nodes"]}
        and edge["to_node_id"] in {node["node_id"] for node in result["nodes"]}
        for edge in result["edges"]
    )


def test_scenario_profile_composes_role_citations_then_applies_scope():
    rows = _rows(
        "# The City of Mirathorn",
        "**Commander Thalia Ashenvale** – **Commander of the Guard**",
        "#### Plot Hooks and Encounters",
        "**Rescue Mission:** Freeing captives from a hideout.",
        "## Quirks of the Elderwyld",
        "### Unit Name: Reaches",
        "One Reach is equivalent to 8 kilometers.",
        "## Approach to Mirathorn",
        "### 1. Agricultural Landscape",
        "As the players approach, they see fields.",
        "The guards manage tolls at the gate.",
    )
    graph = _graph(rows)
    _result, diagnostics = compile_gazetteer_scenario_scope(graph, rows)
    assert GAZETTEER_PREPARED_SCENARIO_PROFILE.profile_version == "1.8"
    assert diagnostics["role_line_citations"]["profile"] == "worldbuilding_gazetteer_v1@1.7"
    assert diagnostics["prepared_scenario_scope"]["profile"] == "worldbuilding_gazetteer_v1@1.8"


def test_duplicate_or_crossing_scene_section_boundaries_fail_closed():
    duplicate = _rows(
        "# City", "#### Plot Hooks and Encounters", "Hook", "## Next",
        "#### Plot Hooks and Encounters", "Hook again", "## End",
    )
    with pytest.raises(SourceSectionRetentionError):
        prepared_scenario_sections(duplicate)

    crossing = _rows(
        "# City", "#### Plot Hooks and Encounters", "## Quirks",
    )
    crossing[1]["line_end"] = 4
    with pytest.raises(SourceSectionRetentionError):
        prepared_scenario_sections(crossing)
