from __future__ import annotations

from typing import Any, Mapping

import pytest

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)
from src.graph_memory.vocabulary.dynamic_selection import (
    DynamicVocabularySelectionPolicy,
    build_dynamic_context_vocabulary_packet,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from src.graph_memory.vocabulary.node_context import render_node_vocabulary_context


def _nodes() -> tuple[dict[str, Any], ...]:
    return (
        {"node_id": "npc_glowkindle", "label": "Glowkindle", "node_type": "character"},
        {"node_id": "loc_glowkindle_cellar", "label": "Glowkindle cellar", "node_type": "location"},
        {"node_id": "quest_clear_rats", "label": "Clear rats from Glowkindle's cellar", "node_type": "quest"},
        {"node_id": "enc_cellar_rats", "label": "Glowkindle cellar rat fight", "node_type": "combat_encounter"},
    )


def test_builds_packet_from_supplied_nodes():
    result = build_dynamic_context_vocabulary_packet(nodes=_nodes(), campaign_id="longmont-c2")

    assert set(result.packet.known_names) == {
        "Glowkindle",
        "Glowkindle cellar",
        "Clear rats from Glowkindle's cellar",
        "Glowkindle cellar rat fight",
    }
    assert result.packet.type_hints["Glowkindle"] == "actor"
    assert result.packet.type_hints["Glowkindle cellar"] == "place"
    assert result.packet.type_hints["Clear rats from Glowkindle's cellar"] == "thread"
    assert result.packet.type_hints["Glowkindle cellar rat fight"] == "combat_encounter"
    assert result.diagnostics["selected_entry_count"] == 4
    assert result.diagnostics["packet_id"] == result.packet.packet_id


def test_dedupes_same_label_kind_deterministically_preferring_anchor_or_source_ref():
    result = build_dynamic_context_vocabulary_packet(
        nodes=(
            {"node_id": "npc_plain", "label": "Glowkindle", "node_type": "character"},
            {
                "node_id": "npc_anchor",
                "label": "Glowkindle",
                "node_type": "npc",
                "context_anchor": True,
                "corpus_ref": "corpus/npcs/glowkindle.md",
            },
        ),
        campaign_id="longmont-c2",
    )

    assert result.diagnostics["selected_node_ids"] == ["npc_anchor"]
    assert result.diagnostics["skipped_nodes"] == [{"node_id": "npc_plain", "reason": "duplicate_label_kind"}]
    assert result.packet.known_names == ["Glowkindle"]


def test_trims_by_policy_max_entries():
    result = build_dynamic_context_vocabulary_packet(
        nodes=_nodes(),
        campaign_id="longmont-c2",
        policy=DynamicVocabularySelectionPolicy(max_entries=2),
    )

    assert result.diagnostics["selected_entry_count"] == 2
    assert result.diagnostics["trimmed_entry_count"] == 2
    assert result.diagnostics["skipped_node_count"] == 2


def test_does_not_include_source_quotes_as_aliases_or_names():
    quote = "Glowkindle asked the party to clear rats"
    result = build_dynamic_context_vocabulary_packet(
        nodes=(
            {
                "node_id": "npc_glowkindle",
                "label": "Glowkindle",
                "node_type": "character",
                "evidence_refs": [{"source_span_ref_id": "spref:1", "anchor_quotes": [quote]}],
            },
        ),
        campaign_id="longmont-c2",
    )

    assert quote not in result.packet.known_names
    assert all(quote not in aliases for aliases in result.packet.entry_aliases.values())
    assert all(quote not in aliases for aliases in result.packet.candidate_entry_aliases.values())


def test_encounter_job_pass_renders_targeted_context_and_excludes_objects():
    result = build_dynamic_context_vocabulary_packet(
        nodes=(*_nodes(), {"node_id": "item_mug", "label": "Glowkindle mug", "node_type": "item"}),
        campaign_id="longmont-c2",
    )

    rendered = render_node_vocabulary_context(result.packet, pass_name="encounter_job_pass")

    assert "Vocabulary context for node extraction — encounter_job_pass" in rendered.context_text
    assert "Known scoped names for this pass" in rendered.context_text
    assert "Combat encounter names" in rendered.context_text
    assert "Do-not-merge cautions" in rendered.context_text
    assert "Containment hints" in rendered.context_text
    assert "Glowkindle [actor]" in rendered.context_text
    assert "Glowkindle cellar [place]" in rendered.context_text
    assert "Clear rats from Glowkindle's cellar [thread]" in rendered.context_text
    assert "Glowkindle cellar rat fight [combat_encounter]" in rendered.context_text
    assert "Glowkindle mug" not in rendered.context_text
    assert rendered.diagnostics["target_entity_kinds"] == ["combat_encounter", "thread", "actor", "place"]


def test_unknown_pass_behavior_remains_strict():
    result = build_dynamic_context_vocabulary_packet(nodes=_nodes(), campaign_id="longmont-c2")

    with pytest.raises(ValueError):
        render_node_vocabulary_context(result.packet, pass_name="not_a_pass")


def _span_index() -> dict[str, Any]:
    return {
        "spans": [
            {
                "kind": "paragraph",
                "span_id": "spref:1",
                "source_span_ref_id": "spref:1",
                "line_start": 1,
                "line_end": 1,
                "text": "Glowkindle asked the party to clear rats from the cellar.",
            }
        ]
    }


class RecordingFixtureClient(FixtureCategoryGraphPassClient):
    def __init__(self, pass_outputs: Mapping[str, Mapping[str, Any]]):
        super().__init__(pass_outputs)
        self.user_content: dict[str, str] = {}

    def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str) -> dict[str, Any]:
        self.user_content[pass_name] = user_content
        return super().run_pass(pass_name, model_id=model_id, instructions=instructions, user_content=user_content)


def _outputs() -> dict[str, dict[str, Any]]:
    return {
        "actor_pass": {"observation_nodes": []},
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "encounter_job_pass": {"observation_nodes": []},
        "edge_pass": {"observation_edges": []},
    }


def _options(**kwargs: Any) -> CategoryGraphExtractionOptions:
    values = dict(
        campaign_id="longmont-c2",
        session_id="c1s1",
        session_number=1,
        source_span_index=_span_index(),
        model_id="gpt-5.4-mini",
    )
    values.update(kwargs)
    return CategoryGraphExtractionOptions(**values)


def test_extractor_uses_dynamic_packet_when_enabled_including_encounter_job_pass():
    client = RecordingFixtureClient(_outputs())

    run_category_pipeline(
        client,
        _options(
            enable_dynamic_node_vocabulary_packet=True,
            dynamic_node_vocabulary_nodes=_nodes(),
            enable_encounter_job_pass=True,
        ),
    )

    assert "Vocabulary context for node extraction" in client.user_content["actor_pass"]
    assert "Glowkindle" in client.user_content["actor_pass"]
    assert "Vocabulary context for node extraction — encounter_job_pass" in client.user_content["encounter_job_pass"]
    assert "Glowkindle cellar rat fight" in client.user_content["encounter_job_pass"]
    assert "Clear rats from Glowkindle's cellar" in client.user_content["encounter_job_pass"]


def test_dynamic_packet_disabled_by_default_even_with_nodes():
    client = RecordingFixtureClient(_outputs())

    result = run_category_pipeline(client, _options(dynamic_node_vocabulary_nodes=_nodes()))

    assert "Vocabulary context for node extraction" not in client.user_content["actor_pass"]
    assert result.diagnostics["dynamic_node_vocabulary_packet"] == {"enabled": False}


def test_explicit_packet_wins_over_dynamic_packet():
    explicit_packet = ContextVocabularyPacket(
        packet_id="packet:explicit",
        scope="campaign",
        known_names=["Explicit NPC"],
        type_hints={"Explicit NPC": "actor"},
    )
    client = RecordingFixtureClient(_outputs())

    result = run_category_pipeline(
        client,
        _options(
            enable_node_vocabulary_packet=True,
            node_vocabulary_packet=explicit_packet,
            enable_dynamic_node_vocabulary_packet=True,
            dynamic_node_vocabulary_nodes=(
                {"node_id": "npc_dynamic_only", "label": "Dynamic Only", "node_type": "character"},
            ),
        ),
    )

    assert "Explicit NPC" in client.user_content["actor_pass"]
    assert "Dynamic Only" not in client.user_content["actor_pass"]
    diag = result.diagnostics["dynamic_node_vocabulary_packet"]
    assert diag["source"] == "explicit_node_vocabulary_packet"
    assert diag["dynamic_nodes_ignored"] is True
