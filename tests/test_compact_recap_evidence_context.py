from copy import deepcopy
import hashlib
import pytest
from src.graph_memory.extraction.compact_evidence_context import CompactEvidenceContext

TEXT = "Bonogo says it is in the warehouse. Thrin points elsewhere."


def context():
    return CompactEvidenceContext([
        {"source_span_ref_id": "artifact:p:1", "text": TEXT, "line_start": 1, "line_end": 1},
        {"source_span_ref_id": "artifact:p:2", "text": TEXT, "line_start": 3, "line_end": 3},
    ], source_sha256=hashlib.sha256(TEXT.encode()).hexdigest())


def test_dictionary_preserves_distinct_paragraphs_and_exact_text():
    ctx = context()
    assert [e["handle"] for e in ctx.record()["entries"]] == ["E1", "E2"]
    assert ctx.prompt_rows()[0]["text"] == TEXT
    assert ctx.record()["entries"][1]["source_span_ref_id"] == "artifact:p:2"
    assert ctx.record()["entries"][0]["text_sha256"] == hashlib.sha256(TEXT.encode()).hexdigest()
    changed = ctx.record(); changed["entries"].clear()
    assert len(ctx.record()["entries"]) == 2


def test_inventory_deduplicates_only_packaging_and_preserves_attribution():
    node = {"node_id": "n1", "node_type": "clue", "label": "Bonogo's claim",
            "description": "Bonogo believes it is in the warehouse; Thrin points elsewhere.",
            "evidence_refs": [{"source_span_ref_id": "artifact:p:1", "anchor_quotes": [TEXT]}] * 4}
    original = deepcopy(node)
    result = context().inventory([node], descriptions=True)[0]
    assert result["description"] == node["description"]
    assert result["evidence_ids"] == ["E1"]
    assert "evidence_refs" not in result
    assert node == original


@pytest.mark.parametrize("ref", ["E3", "E01", "E1 suffix", None, []])
def test_unknown_or_malformed_handles_fail_closed(ref):
    with pytest.raises(ValueError):
        context().expand({"evidence_refs": [{"source_span_ref_id": ref, "anchor_quotes": [TEXT]}]})


def test_expansion_changes_only_reference_fields_not_quotes_labels_or_original():
    raw = {"label": "E1", "evidence_refs": [{"source_span_ref_id": "E2", "anchor_quotes": ["E1 is NOT a quote"]}]}
    normalized = context().expand(raw)
    assert normalized["evidence_refs"][0] == {"source_span_ref_id": "artifact:p:2", "anchor_quotes": ["E1 is NOT a quote"]}
    assert normalized["label"] == raw["label"]
    assert raw["evidence_refs"][0]["source_span_ref_id"] == "E2"
    assert context().expand({"source_span_ref_id": "artifact:p:1"}) == {"source_span_ref_id": "artifact:p:1"}


def test_duplicate_span_ids_are_rejected_even_with_identical_text():
    rows = context().prompt_rows()
    rows[1]["source_span_ref_id"] = rows[0]["source_span_ref_id"]
    with pytest.raises(ValueError):
        CompactEvidenceContext(rows, source_sha256="a" * 64)


def test_context_anchor_and_canonical_validation_boundary_are_preserved():
    ctx = context()
    assert ctx.inventory([{"node_id": "n", "context_anchor": True}], descriptions=True)[0]["context_anchor"] is True
    # Host quote/span checks retain ownership of canonical IDs; no fuzzy repair.
    foreign = {"source_span_ref_id": "supplement:foreign", "anchor_quotes": ["wrong"]}
    assert ctx.expand(foreign) == foreign


def test_context_is_sealed_before_dispatch_and_wrong_source_is_refused():
    from src.graph_memory.extraction.bounded_recap_execution import BoundedRecapPassClient, RecapExecutionLimits
    client = BoundedRecapPassClient(RecapExecutionLimits())
    ctx = context()
    client.execution_binding = {"run_id": "run", "prepared_revision": 2, "source_sha256": ctx.source_sha256}
    captures = []
    client._persist_capture = lambda kind, record: captures.append((kind, record))
    client.retain_compact_evidence_context(ctx.record())
    assert captures[0][0] == "pass_telemetry"
    assert captures[0][1]["context"] == ctx.record()
    assert captures[0][1]["execution_binding"] == client.execution_binding
    bad = ctx.record(); bad["source_sha256"] = "f" * 64
    with pytest.raises(ValueError): client.retain_compact_evidence_context(bad)
    client.calls.append({})
    with pytest.raises(ValueError): client.retain_compact_evidence_context(ctx.record())


def test_expanded_quotes_still_fail_the_owning_literal_validator():
    from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict
    from src.graph_memory.extraction.recap_quote_integrity import validate_and_defer_nonliteral_recap_items
    source = "Bonogo says it is in the warehouse."
    digest = hashlib.sha256(source.encode()).hexdigest()
    index = source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id="artifact:test", content_sha256=digest, text=source))
    from src.graph_memory.extraction.category_candidate_graph_extractor import source_packet_rows_from_span_index
    rows = source_packet_rows_from_span_index(index, source_text=source)
    ctx = CompactEvidenceContext(rows, source_sha256=digest)
    for quote, retained in [(source, True), ("The warehouse is confirmed.", False)]:
        node = {"node_id": "claim", "node_type": "clue", "label": "Bonogo's reported belief",
                "description": "Bonogo says it is there, not an established location.",
                "evidence_refs": [{"source_span_ref_id": "E1", "anchor_quotes": [quote]}]}
        graph = {"source_artifact_ids": ["artifact:test"], "nodes": [node], "edges": [], "beats": [], "proposed_writes": [], "deferred_items": []}
        expanded = ctx.expand(graph)
        from src.graph_memory.extraction.category_candidate_graph_extractor import stamp_graph_evidence_refs
        stamp_graph_evidence_refs(expanded, source_artifact_id="artifact:test", source_ref_id="artifact:test:text")
        cleaned, _ = validate_and_defer_nonliteral_recap_items(expanded, source_text=source,
            source_artifact_id="artifact:test", source_sha256=digest, source_span_index=index)
        assert bool(cleaned["nodes"]) is retained
        if retained:
            assert cleaned["nodes"][0]["description"] == node["description"]
            assert cleaned["nodes"][0]["evidence_refs"][0]["anchor_quotes"] == [quote]
