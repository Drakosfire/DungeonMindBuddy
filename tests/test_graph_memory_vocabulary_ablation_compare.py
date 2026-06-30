from __future__ import annotations

import json

import pytest

from src.graph_memory.vocabulary import (
    ContextVocabularyPacket,
    ExtractedVocabularyEdge,
    ExtractedVocabularyNode,
    VocabularyAblationVariant,
    compare_vocabulary_ablation_variants,
    diagnose_vocabulary_extraction_baseline,
    render_vocabulary_ablation_comparison_markdown,
    vocabulary_ablation_comparison_to_payload,
)


def _packet() -> ContextVocabularyPacket:
    return ContextVocabularyPacket(
        packet_id="packet:vocab:mireward",
        scope="campaign",
        known_names=["Mireward", "North Gate Defense"],
        type_hints={"Mireward": "place", "North Gate Defense": "combat_encounter"},
        predicate_hints={"North Gate Defense": ["occurred_at"]},
        combat_encounter_hints=["North Gate Defense"],
    )


def _diagnostics(packet: ContextVocabularyPacket, nodes, edges=()):
    return diagnose_vocabulary_extraction_baseline(packet=packet, extracted_nodes=nodes, extracted_edges=edges).diagnostics


def _variant(name: str, diagnostics: dict, nodes=None, edges=None, run=None) -> VocabularyAblationVariant:
    return VocabularyAblationVariant(
        variant_name=name,
        extraction_diagnostics=diagnostics,
        extracted_nodes=nodes if nodes is not None else [],
        extracted_edges=edges if edges is not None else [],
        extraction_run_diagnostics=run if run is not None else {},
    )


def test_synthetic_compares_baseline_and_edge_variant_metrics():
    packet = _packet()
    baseline_nodes = [ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place")]
    edge_nodes = [
        ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place"),
        ExtractedVocabularyNode(node_id="n2", label="North Gate Defense", entity_kind="combat_encounter"),
    ]
    edge_edges = [
        ExtractedVocabularyEdge(
            edge_id="e1",
            source_label="North Gate Defense",
            predicate="occurred_at",
            target_label="Mireward",
        )
    ]

    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[
            _variant("baseline", _diagnostics(packet, baseline_nodes), baseline_nodes, []),
            _variant("edge_packet", _diagnostics(packet, edge_nodes, edge_edges), edge_nodes, edge_edges),
        ],
    ).to_dict()

    baseline = result["metrics_by_variant"]["baseline"]
    edge = result["metrics_by_variant"]["edge_packet"]
    delta = result["deltas_vs_baseline"]["edge_packet"]
    assert edge["known_name_pickup_rate"] > baseline["known_name_pickup_rate"]
    assert edge["combat_encounter_match_count"] > baseline["combat_encounter_match_count"]
    assert edge["predicate_hint_match_count"] > baseline["predicate_hint_match_count"]
    assert delta["known_name_match_count_delta"] == 1
    assert delta["combat_encounter_match_count_delta"] == 1
    assert delta["predicate_hint_match_count_delta"] == 1


def test_requires_baseline_variant():
    packet = _packet()
    with pytest.raises(ValueError, match="baseline"):
        compare_vocabulary_ablation_variants(
            packet=packet,
            variants=[_variant("edge_packet", _diagnostics(packet, []))],
        )


def test_reports_warnings_for_missing_expected_variants():
    packet = _packet()
    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[_variant("baseline", _diagnostics(packet, [])), _variant("edge_packet", _diagnostics(packet, []))],
    ).to_dict()

    warning_text = "\n".join(result["warnings"])
    assert "node_packet" in warning_text
    assert "edge_and_node_packet" in warning_text


def test_reports_collision_regression_honestly():
    packet = _packet()
    baseline = _diagnostics(packet, [ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place")])
    node_diag = _diagnostics(
        packet,
        [
            ExtractedVocabularyNode(node_id="n1", label="Mireward", entity_kind="place"),
            ExtractedVocabularyNode(node_id="n2", label="mireward", entity_kind="collective"),
        ],
    )

    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[_variant("baseline", baseline), _variant("node_packet", node_diag)],
    ).to_dict()

    metrics = result["metrics_by_variant"]["node_packet"]
    delta = result["deltas_vs_baseline"]["node_packet"]
    assert metrics["duplicate_label_collision_count"] == 1
    assert metrics["conflicting_kind_collision_count"] == 1
    assert delta["duplicate_label_collision_count_delta"] == 1
    assert delta["conflicting_kind_collision_count_delta"] == 1
    assert any("collision regression" in warning for warning in result["warnings"])


def test_parses_extraction_run_diagnostics():
    packet = _packet()
    run = {
        "consolidation_diagnostics": {
            "dropped_edges_missing_endpoints": [{"edge_id": "e1"}],
            "edge_predicate_issues": [{"edge_id": "e2"}],
            "cross_class_merged_nodes": [{"label": "Mireward"}],
            "cross_class_blocked_nodes": [{"label": "Shepherd", "reason": "unsafe_cross_class_exact_label"}],
        }
    }

    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[_variant("baseline", _diagnostics(packet, [])), _variant("edge_packet", _diagnostics(packet, []), run=run)],
    ).to_dict()

    metrics = result["metrics_by_variant"]["edge_packet"]
    assert metrics["edge_drop_count"] == 1
    assert metrics["edge_predicate_issue_count"] == 1
    assert metrics["cross_class_merged_count"] == 1
    assert metrics["cross_class_blocked_count"] == 1
    assert metrics["unsafe_cross_class_blocked_count"] == 1


def test_best_variant_is_deterministic_with_tie_breaks():
    packet = _packet()
    baseline_diag = _diagnostics(packet, [])
    combat_diag = _diagnostics(packet, [ExtractedVocabularyNode(node_id="n1", label="North Gate Defense", entity_kind="combat_encounter")])
    known_diag = _diagnostics(packet, [ExtractedVocabularyNode(node_id="n2", label="Mireward", entity_kind="place")])

    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[
            _variant("baseline", baseline_diag),
            _variant("edge_packet", combat_diag),
            _variant("node_packet", known_diag),
        ],
    ).to_dict()

    assert result["best_variant"] == "edge_packet"


def test_diagnostics_are_json_serializable_and_quote_free():
    packet = _packet()
    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[_variant("baseline", _diagnostics(packet, [])), _variant("edge_packet", _diagnostics(packet, []))],
    )

    serialized = json.dumps(result.to_dict(), sort_keys=True)
    restored = json.loads(serialized)
    assert "quote" not in serialized
    assert "prompt" not in serialized
    assert "source_text" not in serialized
    assert "comparison_method" in restored
    assert "metrics_by_variant" in restored
    assert "summary" in restored


def test_markdown_summary_renders_compact_table():
    packet = _packet()
    result = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[_variant("baseline", _diagnostics(packet, [])), _variant("edge_packet", _diagnostics(packet, []))],
    )

    markdown = render_vocabulary_ablation_comparison_markdown(result)
    assert "packet:vocab:mireward" in markdown
    assert result.to_dict()["best_variant"] in markdown
    assert "| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |" in markdown
    assert "Heuristic review score; not benchmark truth." in markdown
    assert "metrics_by_variant" not in markdown


def test_payload_helper_returns_dict_identity():
    packet = _packet()
    result = compare_vocabulary_ablation_variants(packet=packet, variants=[_variant("baseline", _diagnostics(packet, []))])

    payload = vocabulary_ablation_comparison_to_payload(result)

    assert payload == result.to_dict()
