"""Category assemble must stamp promote-eligible EvidenceRef IR from span stubs."""

from __future__ import annotations

from src.graph_memory.candidate_graph_preview import evidence_ref_from_dict
from src.graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    DEFAULT_SEMANTIC_STATE,
    PROMOTE_SAFE_PREVIEW_DIAGNOSTICS,
    assemble_envelope,
    materialize_promote_evidence_ref,
    project_candidate_graph_for_promote,
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
    assert graph["diagnostics"] == {
        **PROMOTE_SAFE_PREVIEW_DIAGNOSTICS,
        "warning_count": 0,
    }
    assert envelope["review_sidecar"]["extraction_mode"] == "category_decomposed"
    assert envelope["review_sidecar"]["model_id"] == "test-model"


def test_project_candidate_graph_for_promote_strips_edge_family_and_safe_diag() -> None:
    graph = {
        "nodes": [
            {
                "node_id": "n1",
                "context_anchor": True,
                "evidence_refs": [],
            },
            {
                "node_id": "n2",
                "evidence_refs": [
                    {
                        "source_ref_id": "source-ref:a",
                        "source_artifact_id": "a",
                        "source_domain": "recap",
                        "evidence_role": "supports",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": "span:1",
                        "anchor_quotes": ["x"],
                    }
                ],
            },
        ],
        "edges": [
            {
                "edge_id": "e_empty",
                "from_node_id": "n1",
                "to_node_id": "n2",
                "predicate_family": "spatial",
                "relationship_type": "located_at",
                "evidence_refs": [],
            },
            {
                "edge_id": "e_ok",
                "from_node_id": "n2",
                "to_node_id": "n2",
                "predicate_family": "spatial",
                "relationship_type": "located_at",
                "evidence_refs": [
                    {
                        "source_ref_id": "source-ref:a",
                        "source_artifact_id": "a",
                        "source_domain": "recap",
                        "evidence_role": "supports",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": "span:1",
                        "anchor_quotes": ["x"],
                    }
                ],
            },
        ],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": True,
            "llm_used": True,
            "runtime_connected": True,
            "canon_promotion": False,
            "extraction_mode": "category_decomposed",
            "model_id": "x",
            "warning_count": 3,
        },
    }
    project_candidate_graph_for_promote(graph, warning_count=3)
    # Empty-evidence context anchors are dropped (standing partition is out of scope).
    assert [n["node_id"] for n in graph["nodes"]] == ["n2"]
    assert "context_anchor" not in graph["nodes"][0]
    assert [e["edge_id"] for e in graph["edges"]] == ["e_ok"]
    assert "predicate_family" not in graph["edges"][0]
    assert graph["diagnostics"] == {
        **PROMOTE_SAFE_PREVIEW_DIAGNOSTICS,
        "warning_count": 3,
    }
    assert graph["diagnostics"]["extraction_performed"] is False
    assert graph["diagnostics"]["llm_used"] is False


def test_project_candidate_graph_for_promote_party_anchors_do_not_block_typed_load() -> None:
    """Fresh extract with party context must remain typed-promotable without standing partition."""
    from graph_memory.candidate_graph_preview import (
        candidate_graph_preview_from_dict,
        validate_candidate_graph_preview,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CANDIDATE_GRAPH_SCHEMA,
        CANDIDATE_GRAPH_VERSION,
    )

    graph = {
        "schema": CANDIDATE_GRAPH_SCHEMA,
        "version": CANDIDATE_GRAPH_VERSION,
        "preview_id": "candidate-preview:test:party",
        "campaign_id": "longmont-c2",
        "session_id": "session-24",
        "source_artifact_ids": [ARTIFACT],
        "status": "preview",
        "nodes": [
            {
                "node_id": "node:heroes-party",
                "label": "The Heroes",
                "node_type": "group",
                "description": None,
                "importance": "high",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [],
                "proposed_action": "anchor",
                "confidence": "high",
                "warnings": ["context_anchor_no_session_evidence"],
                "context_anchor": True,
            },
            {
                "node_id": "npc:session",
                "label": "Session NPC",
                "node_type": "character",
                "description": None,
                "importance": "medium",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [
                    {"source_span_ref_id": SPAN, "anchor_quotes": ["NPC"]}
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "edge:member",
                "from_node_id": "pc:caelynn",
                "to_node_id": "node:heroes-party",
                "relationship_type": "member_of",
                "label": "member of",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [],
                "proposed_action": "create",
                "confidence": "high",
                "warnings": ["context_anchor_no_session_evidence"],
                "context_anchor": True,
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": dict(PROMOTE_SAFE_PREVIEW_DIAGNOSTICS),
    }
    stamp_graph_evidence_refs(graph, source_artifact_id=ARTIFACT)
    project_candidate_graph_for_promote(graph, warning_count=0)
    assert [n["node_id"] for n in graph["nodes"]] == ["npc:session"]
    assert graph["edges"] == []
    preview = candidate_graph_preview_from_dict(graph)
    report = validate_candidate_graph_preview(preview)
    assert report.issues == ()


def test_assemble_envelope_edges_are_typed_loadable() -> None:
    consolidated = {
        "nodes": [
            {
                "node_id": "npc:a",
                "label": "A",
                "node_type": "character",
                "description": None,
                "importance": "medium",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [
                    {"source_span_ref_id": SPAN, "anchor_quotes": ["A"]}
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
            {
                "node_id": "loc:b",
                "label": "B",
                "node_type": "location",
                "description": None,
                "importance": "medium",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [
                    {"source_span_ref_id": SPAN, "anchor_quotes": ["B"]}
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            },
        ],
        "edges": [
            {
                "edge_id": "edge:a:located_at:b",
                "from_node_id": "npc:a",
                "to_node_id": "loc:b",
                "relationship_type": "located_at",
                "label": "located at",
                "predicate_family": "spatial",
                "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
                "evidence_refs": [
                    {"source_span_ref_id": SPAN, "anchor_quotes": ["at"]}
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
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
    assert "predicate_family" not in graph["edges"][0]
    preview = load_typed_candidate_graph(graph)
    assert len(preview.nodes) == 2
    assert len(preview.edges) == 1


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
