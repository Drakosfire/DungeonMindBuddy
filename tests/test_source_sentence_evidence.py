from copy import deepcopy
import pytest
from dataclasses import replace
from src.graph_memory.extraction.source_sentence_evidence import (
    compile_source_sentence_packet as compile_packet,
    materialize_actor_evidence,
    render_source_sentence_packet,
)


def materialize(p, source, parsed, *, expected_packet_id):
    return materialize_actor_evidence(
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
        materialize_actor_evidence(bad, response(p, ['Q001']), expected_packet_id=p.packet_id)
