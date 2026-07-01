from __future__ import annotations

from typing import Any, Mapping

from src.graph_memory.candidate_graph_preview import (
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass


def _span_index() -> dict[str, Any]:
    return {
        "spans": [
            {
                "kind": "paragraph",
                "span_id": "spref:c1s1:001",
                "source_span_ref_id": "spref:c1s1:001",
                "line_start": 1,
                "line_end": 1,
                "text": "Glowkindle asked the party to clear rats from the cellar beneath the brewery.",
            },
            {
                "kind": "paragraph",
                "span_id": "spref:c1s1:002",
                "source_span_ref_id": "spref:c1s1:002",
                "line_start": 3,
                "line_end": 3,
                "text": "In the cellar, the party fought a swarm of rats and drove them back from the stores.",
            },
        ]
    }


def _base_outputs(*, encounter: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {
        "actor_pass": {
            "observation_nodes": [
                {
                    "node_id": "npc_glowkindle",
                    "label": "Glowkindle",
                    "node_type": "character",
                    "description": "Glowkindle asks the party for help.",
                    "importance": "medium",
                    "evidence_refs": [
                        {"source_span_ref_id": "spref:c1s1:001", "anchor_quotes": ["Glowkindle asked"]}
                    ],
                }
            ]
        },
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {
            "observation_beats": [
                {
                    "beat_id": "beat_offer",
                    "order": 1,
                    "title": "Glowkindle asks for cellar help",
                    "summary": "Glowkindle asks the party to clear rats from the brewery cellar.",
                    "involved_node_ids": ["npc_glowkindle"],
                    "evidence_refs": [
                        {"source_span_ref_id": "spref:c1s1:001", "anchor_quotes": ["clear rats from the cellar"]}
                    ],
                },
                {
                    "beat_id": "beat_fight",
                    "order": 2,
                    "title": "Cellar rat fight",
                    "summary": "The party fights a swarm of rats in the cellar.",
                    "involved_node_ids": [],
                    "evidence_refs": [
                        {"source_span_ref_id": "spref:c1s1:002", "anchor_quotes": ["fought a swarm of rats"]}
                    ],
                },
            ]
        },
        "edge_pass": {"observation_edges": []},
    }
    if encounter is not None:
        outputs["encounter_job_pass"] = dict(encounter)
    return outputs


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
                    {"source_span_ref_id": "spref:c1s1:001", "anchor_quotes": ["clear rats from the cellar"]}
                ],
            },
            {
                "node_id": "enc_glowkindle_cellar_rats",
                "label": "Glowkindle cellar rat fight",
                "node_type": "combat_encounter",
                "description": "The party fights a swarm of rats in the cellar.",
                "importance": "medium",
                "evidence_refs": [
                    {"source_span_ref_id": "spref:c1s1:002", "anchor_quotes": ["fought a swarm of rats"]}
                ],
            },
        ]
    }


class RecordingFixtureClient(FixtureCategoryGraphPassClient):
    def __init__(self, pass_outputs: Mapping[str, Mapping[str, Any]]):
        super().__init__(pass_outputs)
        self.calls: list[str] = []
        self.user_content: dict[str, str] = {}

    def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str) -> dict[str, Any]:
        self.calls.append(pass_name)
        self.user_content[pass_name] = user_content
        return super().run_pass(
            pass_name,
            model_id=model_id,
            instructions=instructions,
            user_content=user_content,
        )


def _options(*, enabled: bool) -> CategoryGraphExtractionOptions:
    return CategoryGraphExtractionOptions(
        campaign_id="longmont-c2",
        session_id="c1s1",
        session_number=1,
        source_span_index=_span_index(),
        model_id="gpt-5.4-mini",
        enable_encounter_job_pass=enabled,
    )


def test_default_pipeline_does_not_run_encounter_pass():
    client = RecordingFixtureClient(_base_outputs(encounter=_encounter_nodes()))

    result = run_category_pipeline(client, _options(enabled=False))

    assert "encounter_job_pass" not in client.calls
    assert "encounter_job_pass" not in result.pass_outputs
    assert result.consolidation_diagnostics["encounter_job_pass"]["enabled"] is False


def test_enabled_pipeline_runs_encounter_pass_after_beat_and_before_edge():
    client = RecordingFixtureClient(_base_outputs(encounter=_encounter_nodes()))

    run_category_pipeline(client, _options(enabled=True))

    assert client.calls.index("beat_pass") < client.calls.index("encounter_job_pass") < client.calls.index("edge_pass")


def test_encounter_job_pass_nodes_appear_in_candidate_graph_and_edge_prompt():
    client = RecordingFixtureClient(_base_outputs(encounter=_encounter_nodes()))

    result = run_category_pipeline(client, _options(enabled=True))

    node_ids = {n["node_id"] for n in result.candidate_graph["nodes"]}
    node_types = {n["node_type"] for n in result.candidate_graph["nodes"]}
    assert {"quest_clear_glowkindle_rats", "enc_glowkindle_cellar_rats"} <= node_ids
    assert {"quest", "combat_encounter"} <= node_types
    assert "quest_clear_glowkindle_rats" in client.user_content["edge_pass"]
    assert "enc_glowkindle_cellar_rats" in client.user_content["edge_pass"]

    try:
        preview = candidate_graph_preview_from_dict(result.candidate_graph)
    except TypeError:
        # The runtime extractor still emits legacy semantic_state keys; keep this
        # prototype focused on proving the new node types are not invalid.
        assert node_types <= {"character", "quest", "combat_encounter"}
    else:
        report = validate_candidate_graph_preview(preview)
        assert not [issue for issue in report.issues if issue.field == "node_type"]


def test_invalid_encounter_job_node_types_are_dropped_and_diagnosed():
    invalid = {
        "observation_nodes": [
            {
                "node_id": f"bad_{node_type}",
                "label": f"Bad {node_type}",
                "node_type": node_type,
                "description": "Should be dropped.",
                "importance": "medium",
                "evidence_refs": [{"source_span_ref_id": "spref:c1s1:001", "anchor_quotes": ["clear rats"]}],
            }
            for node_type in ("job", "adversary", "monster", "location", "item")
        ]
    }
    client = RecordingFixtureClient(_base_outputs(encounter=invalid))

    result = run_category_pipeline(client, _options(enabled=True))

    node_ids = {n["node_id"] for n in result.candidate_graph["nodes"]}
    assert not ({"bad_job", "bad_adversary", "bad_monster", "bad_location", "bad_item"} & node_ids)
    assert result.consolidation_diagnostics["encounter_job_pass"]["dropped_invalid_node_type_ids"] == [
        "bad_job",
        "bad_adversary",
        "bad_monster",
        "bad_location",
        "bad_item",
    ]


def test_missing_encounter_job_node_type_defaults_to_quest():
    encounter = {
        "observation_nodes": [
            {
                "node_id": "quest_missing_type",
                "label": "Clear rats from Glowkindle's cellar",
                "description": "Glowkindle asks the party to clear rats from the cellar.",
                "importance": "medium",
                "evidence_refs": [{"source_span_ref_id": "spref:c1s1:001", "anchor_quotes": ["clear rats from the cellar"]}],
            }
        ]
    }
    client = RecordingFixtureClient(_base_outputs(encounter=encounter))

    result = run_category_pipeline(client, _options(enabled=True))

    nodes = {n["node_id"]: n for n in result.candidate_graph["nodes"]}
    assert nodes["quest_missing_type"]["node_type"] == "quest"


def test_encounter_prompt_includes_context_and_avoids_edges():
    client = RecordingFixtureClient(_base_outputs(encounter=_encounter_nodes()))

    run_category_pipeline(client, _options(enabled=True))

    prompt = client.user_content["encounter_job_pass"]
    for expected in (
        "Existing consolidated nodes",
        "Source-local beats",
        "combat_encounter",
        "quest",
        "Do not recreate actors",
        "Do not recreate locations",
        "Do not use `job`",
        "Return JSON with key `observation_nodes` only",
        "Glowkindle asked the party",
    ):
        assert expected in prompt
    assert "observation_edges" not in prompt
    assert "relationship_type" not in prompt


def test_schema_for_encounter_job_pass_restricts_node_types():
    schema = schema_for_pass("encounter_job_pass")

    node_type = schema["properties"]["observation_nodes"]["items"]["properties"]["node_type"]
    assert node_type["enum"] == ["combat_encounter", "quest"]
