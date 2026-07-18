"""Category assemble must stamp promote-eligible EvidenceRef IR from span stubs."""

from __future__ import annotations

from src.graph_memory.candidate_graph_preview import evidence_ref_from_dict
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    DEFAULT_SEMANTIC_STATE,
    assemble_envelope,
    materialize_promote_evidence_ref,
    stamp_graph_evidence_refs,
)


ARTIFACT = "artifact:recap:longmont-c2:session-24"
SPAN = "session-24:recap:paragraph:002"


def test_materialize_promote_evidence_ref_expands_stub() -> None:
    stub = {"source_span_ref_id": SPAN, "anchor_quotes": ["quote"]}
    out = materialize_promote_evidence_ref(stub, source_artifact_id=ARTIFACT)
    assert out == {
        "source_ref_id": f"source-ref:{ARTIFACT}",
        "source_artifact_id": ARTIFACT,
        "source_anchor_id": f"anchor:{SPAN}",
        "label": SPAN,
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": SPAN,
        "anchor_quotes": ["quote"],
    }


def test_materialize_promote_evidence_ref_passthrough_full() -> None:
    full = {
        "source_ref_id": "source-ref:custom",
        "source_artifact_id": ARTIFACT,
        "source_span_ref_id": SPAN,
        "can_open_source": True,
        "can_highlight_span": True,
        "extra": "kept",
    }
    assert materialize_promote_evidence_ref(full, source_artifact_id=ARTIFACT) == full


def test_materialize_promote_evidence_ref_drops_missing_span() -> None:
    assert (
        materialize_promote_evidence_ref({"anchor_quotes": ["x"]}, source_artifact_id=ARTIFACT)
        is None
    )


def test_assemble_envelope_stamps_evidence_refs() -> None:
    consolidated = {
        "nodes": [
            {
                "node_id": "npc:karsemine",
                "label": "Karsemine",
                "node_type": "npc",
                "description": "PC",
                "importance": "high",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [
                    {"source_span_ref_id": SPAN, "anchor_quotes": ["Firebolt"]}
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "consolidation_diagnostics": {"merged_nodes": []},
    }
    envelope = assemble_envelope(
        consolidated,
        campaign_id="longmont-c2",
        session_id="session-24",
        source_artifact_id=ARTIFACT,
        model_id="test-model",
    )
    graph = envelope["candidate_graph"]
    ref = graph["nodes"][0]["evidence_refs"][0]
    assert ref["source_ref_id"] == f"source-ref:{ARTIFACT}"
    assert ref["source_artifact_id"] == ARTIFACT
    assert ref["can_open_source"] is True
    assert ref["can_highlight_span"] is True
    assert ref["source_span_ref_id"] == SPAN
    assert ref["anchor_quotes"] == ["Firebolt"]
    # Typed EvidenceRef parse must succeed for the stamped row.
    typed = evidence_ref_from_dict(ref)
    assert typed.source_ref_id == f"source-ref:{ARTIFACT}"
    assert typed.can_open_source is True
    assert typed.can_highlight_span is True


def test_stamp_graph_evidence_refs_walks_all_collections() -> None:
    stub = {"source_span_ref_id": SPAN}
    graph = {
        "nodes": [{"evidence_refs": [stub]}],
        "edges": [{"evidence_refs": [dict(stub)]}],
        "beats": [{"evidence_refs": [dict(stub)]}],
        "proposed_writes": [{"evidence_refs": [dict(stub)]}],
        "ignored_items": [{"evidence_refs": [dict(stub)]}],
        "deferred_items": [{"evidence_refs": [dict(stub)]}],
    }
    stamp_graph_evidence_refs(graph, source_artifact_id=ARTIFACT)
    for key in (
        "nodes",
        "edges",
        "beats",
        "proposed_writes",
        "ignored_items",
        "deferred_items",
    ):
        ref = graph[key][0]["evidence_refs"][0]
        assert ref["source_ref_id"] == f"source-ref:{ARTIFACT}"
        assert ref["source_artifact_id"] == ARTIFACT
