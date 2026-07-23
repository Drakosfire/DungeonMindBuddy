from __future__ import annotations

from typing import Any, Mapping

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.session_graph_context import PARTY_COLLECTIVE_NODE_ID


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


def _node(node_id: str, label: str, node_type: str, quote: str, spref: str = "spref:c1s22:001") -> dict[str, Any]:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": label,
        "importance": "medium",
        "evidence_refs": [{"source_span_ref_id": spref, "anchor_quotes": [quote]}],
    }


def _encounter_nodes() -> dict[str, Any]:
    return {
        "observation_nodes": [
            _node(
                "quest_clear_glowkindle_rats",
                "Clear rats from Glowkindle's cellar",
                "quest",
                "clear rats from the cellar",
            ),
            _node(
                "enc_glowkindle_cellar_rats",
                "Glowkindle cellar rat fight",
                "combat_encounter",
                "fought a swarm of rats",
                "spref:c1s22:002",
            ),
        ]
    }


def _edge(edge_id: str, from_node_id: str, to_node_id: str, relationship_type: str, predicate_family: str, quote: str, spref: str) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "label": edge_id,
        "relationship_type": relationship_type,
        "predicate_family": predicate_family,
        "evidence_refs": [{"source_span_ref_id": spref, "anchor_quotes": [quote]}],
    }


def _valid_edges() -> list[dict[str, Any]]:
    return [
        _edge(
            "edge:enc-rats-located-in-cellar",
            "enc_glowkindle_cellar_rats",
            "loc_glowkindle_cellar",
            "located_in",
            "location_hierarchy",
            "In the cellar",
            "spref:c1s22:002",
        ),
        _edge(
            "edge:rats-participate-in-fight",
            "creature_rat_swarm",
            "enc_glowkindle_cellar_rats",
            "participates_in",
            "participation",
            "fought a swarm of rats",
            "spref:c1s22:002",
        ),
        _edge(
            "edge:quest-targets-rats",
            "quest_clear_glowkindle_rats",
            "creature_rat_swarm",
            "mission_targets",
            "hook_relation",
            "clear rats",
            "spref:c1s22:001",
        ),
        _edge(
            "edge:quest-focus-cellar",
            "quest_clear_glowkindle_rats",
            "loc_glowkindle_cellar",
            "mission_focus",
            "hook_relation",
            "from the cellar",
            "spref:c1s22:001",
        ),
    ]


def _base_outputs(*, encounter: Mapping[str, Any] | None = None, edges: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {
        "actor_pass": {
            "observation_nodes": [
                _node("npc_glowkindle", "Glowkindle", "character", "Glowkindle asked"),
                _node("creature_rat_swarm", "Rat swarm", "character", "swarm of rats", "spref:c1s22:002"),
            ]
        },
        "location_pass": {
            "observation_nodes": [
                _node("loc_glowkindle_cellar", "Glowkindle cellar", "location", "the cellar")
            ]
        },
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {"observation_edges": edges or []},
    }
    if encounter is not None:
        outputs["encounter_job_pass"] = dict(encounter)
    return outputs


class RecordingFixtureClient(FixtureCategoryGraphPassClient):
    def __init__(self, pass_outputs: Mapping[str, Mapping[str, Any]]):
        super().__init__(pass_outputs)
        self.user_content: dict[str, str] = {}

    def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str, pass_spec=None) -> dict[str, Any]:
        self.user_content[pass_name] = user_content
        return super().run_pass(pass_name, model_id=model_id, instructions=instructions, user_content=user_content)


def _run(*, encounter_enabled: bool = True, guidance_enabled: bool = False, attachment_enabled: bool = False, encounter: Mapping[str, Any] | None = None, edges: list[dict[str, Any]] | None = None):
    client = RecordingFixtureClient(
        _base_outputs(encounter=_encounter_nodes() if encounter is None else encounter, edges=edges)
    )
    result = run_category_pipeline(
        client,
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="c1s22",
            session_number=22,
            source_span_index=_span_index(),
            model_id="gpt-5.4-mini",
            enable_encounter_job_pass=encounter_enabled,
            enable_party_participation_attachment=attachment_enabled,
            enable_encounter_job_edge_guidance=guidance_enabled,
        ),
    )
    return result, client


def test_default_behavior_does_not_add_encounter_job_edge_guidance():
    result, client = _run(encounter_enabled=True, guidance_enabled=False)

    prompt = client.user_content["edge_pass"]
    assert "Encounter/job edge guidance" not in prompt
    assert "Encounter/job nodes available for edge binding" not in prompt
    assert "Do not emit generic `node:heroes-party -> quest`" not in prompt
    assert "combat_encounter -> location" not in prompt
    assert result.diagnostics["encounter_job_edge_guidance"]["enabled"] is False
    assert result.diagnostics["encounter_job_edge_guidance"]["reason"] == "option_disabled"


def test_enabled_guidance_appears_when_targets_exist():
    result, client = _run(encounter_enabled=True, guidance_enabled=True)

    prompt = client.user_content["edge_pass"]
    for expected in (
        "Encounter/job edge guidance",
        "quest_clear_glowkindle_rats",
        "enc_glowkindle_cellar_rats",
        "mission_targets",
        "mission_focus",
        "located_in",
        "participates_in",
        "results_in",
        "Do not emit generic `node:heroes-party -> quest`",
    ):
        assert expected in prompt
    diag = result.diagnostics["encounter_job_edge_guidance"]
    assert diag["guidance_added"] is True
    assert diag["quest_node_ids"] == ["quest_clear_glowkindle_rats"]
    assert diag["combat_encounter_node_ids"] == ["enc_glowkindle_cellar_rats"]


def test_enabled_guidance_with_no_targets_is_quiet():
    result, client = _run(encounter_enabled=False, guidance_enabled=True, encounter=None)

    assert "Encounter/job edge guidance" not in client.user_content["edge_pass"]
    diag = result.diagnostics["encounter_job_edge_guidance"]
    assert diag["enabled"] is True
    assert diag["guidance_added"] is False
    assert diag["reason"] == "no_encounter_or_quest_nodes"


def test_edge_pass_can_emit_encounter_job_edges_with_existing_predicates():
    result, _client = _run(encounter_enabled=True, guidance_enabled=True, edges=_valid_edges())

    edges = {edge["edge_id"]: edge for edge in result.candidate_graph["edges"]}
    for edge_id in (
        "edge:enc-rats-located-in-cellar",
        "edge:rats-participate-in-fight",
        "edge:quest-targets-rats",
        "edge:quest-focus-cellar",
    ):
        assert edge_id in edges
        assert not [w for w in edges[edge_id].get("warnings", []) if str(w).startswith("predicate_validation:")]


def test_unknown_invented_predicates_remain_flagged():
    bad_edge = _edge(
        "edge:bad-assigned-by",
        "npc_glowkindle",
        "quest_clear_glowkindle_rats",
        "assigned_by",
        "hook_relation",
        "Glowkindle asked",
        "spref:c1s22:001",
    )
    result, _client = _run(encounter_enabled=True, guidance_enabled=True, edges=[bad_edge])

    edge = next((e for e in result.candidate_graph["edges"] if e["edge_id"] == "edge:bad-assigned-by"), None)
    issues = result.consolidation_diagnostics["edge_predicate_issues"]
    assert (edge and "predicate_validation:unknown_relationship_type" in edge.get("warnings", [])) or any(
        issue["edge_id"] == "edge:bad-assigned-by"
        and "unknown_relationship_type" in issue["issues"]
        for issue in issues
    )


def test_guidance_does_not_require_party_participation_attachment():
    result, client = _run(encounter_enabled=True, guidance_enabled=True, attachment_enabled=False)

    assert "Encounter/job edge guidance" in client.user_content["edge_pass"]
    assert not [e for e in result.candidate_graph["edges"] if e["from_node_id"] == PARTY_COLLECTIVE_NODE_ID]


def test_guidance_coexists_with_party_participation_attachment():
    result, client = _run(
        encounter_enabled=True,
        guidance_enabled=True,
        attachment_enabled=True,
        edges=_valid_edges(),
    )

    by_pair = {(e["from_node_id"], e["to_node_id"]): e for e in result.candidate_graph["edges"]}
    assert (PARTY_COLLECTIVE_NODE_ID, "quest_clear_glowkindle_rats") in by_pair
    assert (PARTY_COLLECTIVE_NODE_ID, "enc_glowkindle_cellar_rats") in by_pair
    assert "Do not emit generic `node:heroes-party -> quest`" in client.user_content["edge_pass"]
    assert "edge:rats-participate-in-fight" in {e["edge_id"] for e in result.candidate_graph["edges"]}
