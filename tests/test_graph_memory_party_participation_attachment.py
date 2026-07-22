from __future__ import annotations

from typing import Any, Mapping

from src.graph_memory import party_context as pc
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.session_graph_context import (
    PARTY_COLLECTIVE_NODE_ID,
    attach_party_participation_edges,
    merge_party_anchor_nodes,
    merge_party_collective,
)


def _span_index() -> dict[str, Any]:
    return {
        "source_artifact_id": "artifact:recap:longmont-c2:session-22:test",
        "source_ref_id": "artifact:recap:longmont-c2:session-22:test:text",
        "spans": [
            {
                "kind": "paragraph",
                "span_id": "spref:c1s22:001",
                "source_span_ref_id": "spref:c1s22:001",
                "line_start": 1,
                "line_end": 1,
                "text": "Glowkindle asked the party to clear rats from the cellar beneath the brewery.",
            },
            {
                "kind": "paragraph",
                "span_id": "spref:c1s22:002",
                "source_span_ref_id": "spref:c1s22:002",
                "line_start": 3,
                "line_end": 3,
                "text": "In the cellar, the party fought a swarm of rats and drove them back from the stores.",
            },
        ]
    }


def _encounter_nodes() -> dict[str, Any]:
    return {
        "observation_nodes": [
            {
                "node_id": "quest_clear_glowkindle_rats",
                "label": "Clear rats from Glowkindle's cellar",
                "node_type": "quest",
                "description": "Glowkindle asks the party to clear rats from the cellar.",
                "importance": "medium",
                "evidence_refs": [
                    {"source_span_ref_id": "spref:c1s22:001", "anchor_quotes": ["clear rats from the cellar"]}
                ],
            },
            {
                "node_id": "enc_glowkindle_cellar_rats",
                "label": "Glowkindle cellar rat fight",
                "node_type": "combat_encounter",
                "description": "The party fights a swarm of rats in the cellar.",
                "importance": "medium",
                "evidence_refs": [
                    {"source_span_ref_id": "spref:c1s22:002", "anchor_quotes": ["fought a swarm of rats"]}
                ],
            },
        ]
    }


def _base_outputs(*, encounter: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {
        "actor_pass": {"observation_nodes": []},
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {"observation_edges": []},
    }
    if encounter is not None:
        outputs["encounter_job_pass"] = dict(encounter)
    return outputs


def _run(*, encounter_enabled: bool = True, attachment_enabled: bool = True, encounter: Mapping[str, Any] | None = None):
    client = FixtureCategoryGraphPassClient(_base_outputs(encounter=_encounter_nodes() if encounter is None else encounter))
    return run_category_pipeline(
        client,
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="c1s22",
            session_number=22,
            source_span_index=_span_index(),
            model_id="gpt-5.4-mini",
            enable_encounter_job_pass=encounter_enabled,
            enable_party_participation_attachment=attachment_enabled,
        ),
    )


def _deterministic_edges(result) -> list[dict[str, Any]]:
    return [
        edge
        for edge in result.candidate_graph["edges"]
        if "deterministic_party_participation" in edge.get("warnings", [])
    ]


def test_default_behavior_does_not_attach_party_participation():
    result = _run(attachment_enabled=False)

    assert result.consolidation_diagnostics["party_participation_attachment"]["enabled"] is False
    assert _deterministic_edges(result) == []


def test_enabled_behavior_attaches_party_collective_to_quest_and_encounter():
    result = _run()

    by_target = {(edge["from_node_id"], edge["to_node_id"]): edge for edge in _deterministic_edges(result)}
    quest_edge = by_target[(PARTY_COLLECTIVE_NODE_ID, "quest_clear_glowkindle_rats")]
    encounter_edge = by_target[(PARTY_COLLECTIVE_NODE_ID, "enc_glowkindle_cellar_rats")]

    assert {edge["from_node_id"] for edge in _deterministic_edges(result)} == {PARTY_COLLECTIVE_NODE_ID}
    assert quest_edge["relationship_type"] == "pursues"
    assert quest_edge["predicate_family"] == "hook_relation"
    assert quest_edge["context_anchor"] is True
    assert encounter_edge["relationship_type"] == "participates_in"
    assert encounter_edge["predicate_family"] == "participation"
    assert encounter_edge["context_anchor"] is True

    diag = result.consolidation_diagnostics["party_participation_attachment"]
    assert diag["enabled"] is True
    assert diag["subject_node_ids"] == [PARTY_COLLECTIVE_NODE_ID]
    assert diag["combat_encounter_node_ids"] == ["enc_glowkindle_cellar_rats"]
    assert diag["quest_node_ids"] == ["quest_clear_glowkindle_rats"]
    assert diag["inserted_edge_count"] == 2
    assert diag["skipped_reason"] is None


def test_attachment_edges_survive_sanitization():
    result = _run()

    edge_ids = {edge["edge_id"] for edge in result.candidate_graph["edges"]}
    assert "edge:heroes-party-pursues-quest-clear-glowkindle-rats" in edge_ids
    assert "edge:heroes-party-participates-in-enc-glowkindle-cellar-rats" in edge_ids


def test_no_attachment_when_no_encounter_or_quest_nodes_exist():
    result = _run(encounter_enabled=False)

    assert _deterministic_edges(result) == []
    diag = result.consolidation_diagnostics["party_participation_attachment"]
    assert diag["enabled"] is True
    assert diag["skipped_reason"] == "no_encounter_or_quest_nodes"


def test_repeated_helper_application_does_not_duplicate_edges():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    nodes, _ = merge_party_anchor_nodes([], party_ctx, default_semantic_state={"status": "unknown"})
    nodes.extend(_encounter_nodes()["observation_nodes"])
    nodes, edges, _ = merge_party_collective(nodes, [], party_ctx, default_semantic_state={"status": "unknown"})

    once, _ = attach_party_participation_edges(nodes, edges, party_ctx, default_semantic_state={"status": "unknown"})
    twice, _ = attach_party_participation_edges(nodes, once, party_ctx, default_semantic_state={"status": "unknown"})

    target_id = "edge:heroes-party-pursues-quest-clear-glowkindle-rats"
    assert [edge["edge_id"] for edge in twice].count(target_id) == 1


def test_helper_ignores_non_target_node_types_and_member_edges_by_default():
    party_ctx = pc.build_party_context_for_campaign("longmont-c2", 22)
    nodes, _ = merge_party_anchor_nodes([], party_ctx, default_semantic_state={"status": "unknown"})
    nodes.extend(
        {
            "node_id": f"node_{node_type}",
            "label": node_type.title(),
            "node_type": node_type,
            "evidence_refs": [],
        }
        for node_type in ("character", "location", "item", "thread", "mystery", "warning", "event")
    )
    nodes, edges, _ = merge_party_collective(nodes, [], party_ctx, default_semantic_state={"status": "unknown"})

    merged_edges, diag = attach_party_participation_edges(nodes, edges, party_ctx, default_semantic_state={"status": "unknown"})

    assert diag["skipped_reason"] == "no_encounter_or_quest_nodes"
    participation_edges = [edge for edge in merged_edges if "deterministic_party_participation" in edge.get("warnings", [])]
    assert participation_edges == []
    assert diag["subject_node_ids"] == []
