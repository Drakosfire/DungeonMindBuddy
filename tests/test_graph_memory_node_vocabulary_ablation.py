from __future__ import annotations

from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    build_edge_pass_prompt,
    build_node_pass_prompt,
    render_category_pass_prompts,
    run_category_pipeline,
)
from src.graph_memory.party_context import PartyContext
from src.graph_memory.vocabulary import (
    ContextVocabularyPacket,
    ExtractedVocabularyNode,
    diagnose_vocabulary_extraction_baseline,
)


def _packet(packet_id: str = "packet:vocab:node-ablation") -> ContextVocabularyPacket:
    return ContextVocabularyPacket(
        packet_id=packet_id,
        scope="campaign",
        known_names=["Mireward", "Mireward Council", "North Gate Defense"],
        type_hints={
            "Mireward": "place",
            "Mireward Council": "collective",
            "North Gate Defense": "combat_encounter",
        },
        combat_encounter_hints=["North Gate Defense"],
        predicate_hints={"North Gate Defense": ["occurred_at", "involved"]},
    )


def _options(**kwargs: Any) -> CategoryGraphExtractionOptions:
    base = {
        "campaign_id": "longmont-c2",
        "session_id": "session:23",
        "session_number": 23,
        "source_span_index": {"spans": []},
    }
    base.update(kwargs)
    return CategoryGraphExtractionOptions(**base)


def _prompts() -> dict[str, str]:
    return render_category_pass_prompts(
        [
            {
                "source_span_ref_id": "spref:1",
                "source_unit_id": "u1",
                "line_start": 1,
                "line_end": 1,
                "text": "North Gate Defense at Mireward.",
            }
        ],
        party_ctx=PartyContext(campaign_id="campaign:mireward", session="23", party_names=(), members=()),
    )


def test_default_node_prompts_unchanged():
    prompt, diagnostics = build_node_pass_prompt("location_pass", _prompts()["location_pass.md"], options=_options())

    assert "Vocabulary context for node extraction" not in prompt
    assert diagnostics == {"enabled": False}


def test_packet_ignored_unless_enabled():
    prompt, diagnostics = build_node_pass_prompt(
        "location_pass", _prompts()["location_pass.md"], options=_options(node_vocabulary_packet=_packet())
    )

    assert "Vocabulary context for node extraction" not in prompt
    assert diagnostics == {"enabled": False}


def test_packet_included_when_enabled():
    prompt, diagnostics = build_node_pass_prompt(
        "location_pass",
        _prompts()["location_pass.md"],
        options=_options(enable_node_vocabulary_packet=True, node_vocabulary_packet=_packet()),
    )

    assert "Vocabulary context for node extraction" in prompt
    assert "Mireward [place]" in prompt
    assert "Mireward Council [collective]" not in prompt
    assert diagnostics["packet_id"] == "packet:vocab:node-ablation"


def test_targeting_differs_by_pass():
    options = _options(enable_node_vocabulary_packet=True, node_vocabulary_packet=_packet())
    prompts = _prompts()

    location_prompt, _ = build_node_pass_prompt("location_pass", prompts["location_pass.md"], options=options)
    collective_prompt, _ = build_node_pass_prompt("collective_pass", prompts["collective_pass.md"], options=options)
    thread_prompt, _ = build_node_pass_prompt("thread_pass", prompts["thread_pass.md"], options=options)

    assert "Mireward [place]" in location_prompt
    assert "Mireward Council [collective]" not in location_prompt
    assert "Mireward Council [collective]" in collective_prompt
    assert "Mireward [place]" not in collective_prompt
    assert "North Gate Defense [combat_encounter]" in thread_prompt


def test_beat_pass_is_not_modified():
    assert "Vocabulary context for node extraction" not in _prompts()["beat_pass.md"]


def test_edge_pass_is_not_modified_by_node_flag():
    edge_prompt, diagnostics, encounter_job_edge_diag = build_edge_pass_prompt(
        _prompts()["edge_pass.md"],
        [],
        options=_options(enable_node_vocabulary_packet=True, node_vocabulary_packet=_packet()),
    )

    assert "Vocabulary context for node extraction" not in edge_prompt
    assert "Vocabulary context for edge extraction" not in edge_prompt
    assert diagnostics == {"enabled": False}
    assert encounter_job_edge_diag["enabled"] is False


def test_node_and_edge_flags_are_independent():
    node_packet = _packet("packet:vocab:node")
    edge_packet = _packet("packet:vocab:edge")
    options = _options(
        enable_node_vocabulary_packet=True,
        node_vocabulary_packet=node_packet,
        enable_edge_vocabulary_packet=True,
        edge_vocabulary_packet=edge_packet,
    )

    node_prompt, node_diag = build_node_pass_prompt("location_pass", _prompts()["location_pass.md"], options=options)
    edge_prompt, edge_diag, _ = build_edge_pass_prompt(_prompts()["edge_pass.md"], [], options=options)

    assert "Vocabulary context for node extraction" in node_prompt
    assert "Vocabulary context for edge extraction" in edge_prompt
    assert node_diag["packet_id"] == "packet:vocab:node"
    assert edge_diag["packet_id"] == "packet:vocab:edge"


def test_pipeline_diagnostics_expose_node_ablation_state():
    result = run_category_pipeline(
        FixtureCategoryGraphPassClient({}),
        _options(enable_node_vocabulary_packet=True, node_vocabulary_packet=_packet()),
    )

    assert result.diagnostics["node_vocabulary_ablation"]["enabled"] is True
    assert result.diagnostics["node_vocabulary_ablation"]["passes"]["location_pass"]["enabled"] is True
    assert result.diagnostics["edge_vocabulary_ablation"] == {"enabled": False}


def test_synthetic_passive_diagnostics_comparison_shape():
    packet = _packet()
    baseline = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[ExtractedVocabularyNode("node:mireward", "Mireward", "place")],
    ).diagnostics
    assisted = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[
            ExtractedVocabularyNode("node:mireward", "Mireward", "place"),
            ExtractedVocabularyNode("node:north-gate-defense", "North Gate Defense", "combat_encounter"),
        ],
    ).diagnostics

    assert assisted["known_name_pickup"]["pickup_rate"] > baseline["known_name_pickup"]["pickup_rate"]
    assert baseline["combat_encounter_pickup"]["missed"] == ["North Gate Defense"]
    assert assisted["combat_encounter_pickup"]["matched"] == ["North Gate Defense"]
