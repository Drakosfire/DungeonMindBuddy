from copy import deepcopy
import pytest
from dataclasses import replace
from src.graph_memory.extraction.source_sentence_evidence import (
    compile_source_sentence_packet as compile_packet,
    materialize_node_evidence,
    render_source_sentence_packet,
)


def materialize(p, source, parsed, *, expected_packet_id):
    return materialize_node_evidence(
        replace(p, source=source), parsed, expected_packet_id=expected_packet_id
    )


def render_packet(p, source):
    return render_source_sentence_packet(replace(p, source=source))


def packet(text):
    return compile_packet(
        text, [{"source_span_ref_id": "span:1", "line_start": 1, "text": text}]
    )


def response(p, ids):
    return {
        "observation_nodes": [
            {"node_id": "x", "evidence_refs": [{"source_quote_ids": ids}]}
        ]
    }


@pytest.mark.parametrize(
    "source",
    [
        "Dr. Ari did not open the gate. Bea did.",
        "“Do not enter!” Ari said. Unless Bea agrees.",
        "- Do not enter.\n- Wait for Bea.",
        "Ari waits; unless Bea returns, she will not leave.",
        "Ari carried 3.5 gold. Bea waited.",
    ],
)
def test_exact_offsets_and_qualifiers(source):
    p = packet(source)
    quotes = [source[u.start : u.end] for u in p.units]
    assert all(q and q in source for q in quotes)
    assert materialize(
        p,
        source,
        response(p, [u.unit_id for u in p.units]),
        expected_packet_id=p.packet_id,
    )["observation_nodes"][0]["evidence_refs"]
    if source.startswith("Dr."):
        assert quotes[0] == "Dr. Ari did not open the gate."
    if "unless" in source:
        assert any("unless" in q and "will not leave" in q for q in quotes)


def test_repeated_sentence_keeps_source_location():
    source = "Ari waits.\n\nAri waits."
    p = compile_packet(
        source,
        [
            {"source_span_ref_id": "a", "line_start": 1, "text": "Ari waits."},
            {"source_span_ref_id": "b", "line_start": 3, "text": "Ari waits."},
        ],
    )
    assert len(p.units) == 2 and p.units[0].unit_id != p.units[1].unit_id
    assert p.units[0].span_id != p.units[1].span_id


@pytest.mark.parametrize("damage", ["unknown", "duplicate", "revision", "packet"])
def test_invalid_binding_is_atomic(damage):
    source = "Ari waits. Bea returns."
    p = packet(source)
    raw = response(p, ["Q001"])
    expected = p.packet_id
    if damage == "unknown":
        raw["observation_nodes"][0]["evidence_refs"][0]["source_quote_ids"] = ["Q999"]
    if damage == "duplicate":
        raw["observation_nodes"][0]["evidence_refs"][0]["source_quote_ids"] = [
            "Q001",
            "Q001",
        ]
    if damage == "revision":
        source += " Changed."
    if damage == "packet":
        expected = "foreign"
    unchanged = deepcopy(raw)
    with pytest.raises(ValueError):
        materialize(p, source, raw, expected_packet_id=expected)
    assert raw == unchanged


def test_conflicting_span_and_offset_reject():
    with pytest.raises(ValueError, match="conflicting_span"):
        compile_packet(
            "Ari.\nBea.",
            [
                {"source_span_ref_id": "a", "line_start": 1, "text": "Ari."},
                {"source_span_ref_id": "a", "line_start": 2, "text": "Bea."},
            ],
        )
    with pytest.raises(ValueError, match="offsets"):
        compile_packet(
            "Ari.", [{"source_span_ref_id": "a", "line_start": 1, "text": "Bea."}]
        )


def test_pronoun_needs_multiple_units_without_claiming_entailment():
    source = "Ari stayed outside. She did not enter."
    p = packet(source)
    out = materialize(
        p, source, response(p, ["Q001", "Q002"]), expected_packet_id=p.packet_id
    )
    assert [
        r["anchor_quotes"][0] for r in out["observation_nodes"][0]["evidence_refs"]
    ] == ["Ari stayed outside.", "She did not enter."]
    assert "Q001" in render_packet(p, source)


def test_damaged_offsets_cannot_keep_old_packet_digest():
    p = packet('Ari waits. Bea returns.')
    bad = replace(p, units=(replace(p.units[0], end=len(p.source) + 1),))
    with pytest.raises(ValueError, match='source_revision_mismatch'):
        materialize_node_evidence(bad, response(p, ['Q001']), expected_packet_id=p.packet_id)


def test_node_dispositions_share_exact_handle_wire_and_preserve_empty_refs():
    from jsonschema import validate
    from src.graph_memory.extraction.source_sentence_evidence import node_wire_schema
    from src.graph_memory.extraction.category_candidate_graph_schema import category_node_pass_json_schema
    p = packet("It did have a job board. The town was hardly known.")
    base = category_node_pass_json_schema(include_dispositions=True)
    wire = node_wire_schema(base, p)
    node = {"node_id": "town", "label": "Town", "node_type": "location",
            "description": "The town was hardly known.", "importance": "high",
            "evidence_refs": [{"source_quote_ids": ["Q001", "Q002"]}]}
    disposition = {"item_id": "held", "label": "Unknown", "reason": "No claim",
                   "suggested_next_step": None, "evidence_refs": []}
    raw = {"observation_nodes": [node], "ignored_items": [disposition],
           "deferred_items": [{**disposition, "evidence_refs": [{"source_quote_ids": ["Q001"]}]}]}
    validate(raw, wire)
    normalized = materialize_node_evidence(p, raw, expected_packet_id=p.packet_id)
    validate(normalized, base)
    assert normalized["observation_nodes"][0]["evidence_refs"][0]["anchor_quotes"] == ["It did have a job board."]
    assert normalized["ignored_items"][0]["evidence_refs"] == []
    assert normalized["deferred_items"][0]["evidence_refs"][0]["anchor_quotes"] == ["It did have a job board."]
    assert raw["observation_nodes"][0]["evidence_refs"] == [{"source_quote_ids": ["Q001", "Q002"]}]


@pytest.mark.parametrize("collection", ["ignored_items", "deferred_items"])
def test_unknown_disposition_handle_rejects_without_partial_materialization(collection):
    p = packet("The gate stayed closed.")
    raw = {"observation_nodes": [], collection: [{"evidence_refs": [{"source_quote_ids": ["Q999"]}]}]}
    original = deepcopy(raw)
    with pytest.raises(ValueError, match="unknown_or_duplicate_unit"):
        materialize_node_evidence(p, raw, expected_packet_id=p.packet_id)
    assert raw == original
