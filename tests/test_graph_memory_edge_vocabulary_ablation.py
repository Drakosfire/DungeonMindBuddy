from __future__ import annotations

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    build_edge_pass_prompt,
    edge_vocabulary_ablation_diagnostics,
    render_category_pass_prompts,
)
from src.graph_memory.extraction.staged_edge_extraction import (
    EdgeVocabularyAblationOptions,
    build_graph_context_packet,
    render_relation_observation_prompt,
)
from src.graph_memory.party_context import PartyContext
from src.graph_memory.vocabulary import (
    ContextVocabularyPacket,
    ExtractedVocabularyEdge,
    ExtractedVocabularyNode,
    diagnose_vocabulary_extraction_baseline,
)


def _packet() -> ContextVocabularyPacket:
    return ContextVocabularyPacket(
        packet_id="packet:vocab:edge-ablation",
        scope="campaign",
        known_names=["Mireward", "North Gate Defense"],
        type_hints={"Mireward": "place", "North Gate Defense": "combat_encounter"},
        combat_encounter_hints=["North Gate Defense"],
        predicate_hints={"North Gate Defense": ["occurred_at", "involved"]},
    )


def _options(**kwargs) -> CategoryGraphExtractionOptions:
    base = {
        "campaign_id": "campaign:mireward",
        "session_id": "session:23",
        "session_number": 23,
        "source_span_index": {"spans": []},
    }
    base.update(kwargs)
    return CategoryGraphExtractionOptions(**base)


def _edge_template() -> str:
    prompts = render_category_pass_prompts(
        [
            {
                "source_span_ref_id": "spref:1",
                "source_unit_id": "u1",
                "line_start": 1,
                "line_end": 1,
                "text": "North Gate Defense at Mireward.",
            }
        ],
        party_ctx=PartyContext(
            campaign_id="campaign:mireward", session="23", party_names=(), members=()
        ),
    )
    return prompts["edge_pass.md"]


def test_default_edge_extraction_context_omits_vocabulary_context():
    prompt, diagnostics = build_edge_pass_prompt(_edge_template(), [], options=_options())

    assert "Vocabulary context for edge extraction" not in prompt
    assert diagnostics == {"enabled": False}


def test_packet_ignored_unless_enabled():
    prompt, diagnostics = build_edge_pass_prompt(
        _edge_template(), [], options=_options(edge_vocabulary_packet=_packet())
    )

    assert "Vocabulary context for edge extraction" not in prompt
    assert diagnostics == {"enabled": False}


def test_packet_included_when_enabled():
    prompt, diagnostics = build_edge_pass_prompt(
        _edge_template(),
        [],
        options=_options(enable_edge_vocabulary_packet=True, edge_vocabulary_packet=_packet()),
    )

    assert "Vocabulary context for edge extraction" in prompt
    assert "North Gate Defense" in prompt
    assert "occurred_at" in prompt
    assert diagnostics["enabled"] is True
    assert diagnostics["packet_id"] == "packet:vocab:edge-ablation"


def test_node_pass_and_staged_default_context_are_not_modified():
    prompts = render_category_pass_prompts(
        [],
        party_ctx=PartyContext(
            campaign_id="campaign:mireward", session="23", party_names=(), members=()
        ),
    )
    assert "Vocabulary context for edge extraction" not in prompts["actor_pass.md"]

    default_context = build_graph_context_packet(source_rows=[], nodes=[], beats=[])
    assert "Vocabulary context for edge extraction" not in default_context

    disabled_prompt = render_relation_observation_prompt(
        [],
        nodes=[],
        beats=[],
        edge_vocabulary_options=EdgeVocabularyAblationOptions(vocabulary_packet=_packet()),
    )
    assert "Vocabulary context for edge extraction" not in disabled_prompt


def test_staged_edge_context_can_opt_in_to_packet():
    context = build_graph_context_packet(
        source_rows=[],
        nodes=[],
        beats=[],
        edge_vocabulary_options=EdgeVocabularyAblationOptions(
            enable_edge_vocabulary_packet=True,
            vocabulary_packet=_packet(),
        ),
    )

    assert "Vocabulary context for edge extraction" in context
    assert "North Gate Defense" in context


def test_edge_ablation_diagnostics_are_exposed():
    disabled = edge_vocabulary_ablation_diagnostics(_options(edge_vocabulary_packet=_packet()))
    enabled = edge_vocabulary_ablation_diagnostics(
        _options(enable_edge_vocabulary_packet=True, edge_vocabulary_packet=_packet())
    )

    assert disabled == {"enabled": False}
    assert enabled["enabled"] is True
    assert enabled["packet_id"] == "packet:vocab:edge-ablation"
    assert enabled["context_line_count"] > 0
    assert enabled["known_name_count"] == 2
    assert enabled["predicate_hint_count"] == 2
    assert enabled["combat_encounter_hint_count"] == 1


def test_passive_diagnostics_compare_synthetic_baseline_and_packet_assisted_output():
    packet = _packet()
    baseline = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[ExtractedVocabularyNode("node:mireward", "Mireward", "place")],
        extracted_edges=[],
    ).diagnostics
    assisted = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=[
            ExtractedVocabularyNode("node:mireward", "Mireward", "place"),
            ExtractedVocabularyNode("node:north-gate-defense", "North Gate Defense", "combat_encounter"),
        ],
        extracted_edges=[
            ExtractedVocabularyEdge("edge:1", "North Gate Defense", "occurred_at", "Mireward"),
            ExtractedVocabularyEdge("edge:2", "North Gate Defense", "involved", "Mireward Guard"),
        ],
    ).diagnostics

    assert assisted["known_name_pickup"]["pickup_rate"] > baseline["known_name_pickup"]["pickup_rate"]
    assert len(assisted["predicate_hint_pickup"]["matched"]) > len(
        baseline["predicate_hint_pickup"]["matched"]
    )
    assert assisted["combat_encounter_pickup"]["matched"] == ["North Gate Defense"]
