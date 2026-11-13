"""Already-mapped actor kinds survive preview validation without role coercion."""

import pytest

from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
    map_candidate_node_to_assertion,
)


def fixture(kind):
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "synthetic:actor-kinds",
        "campaign_id": "synthetic",
        "session_id": "session-1",
        "source_artifact_ids": ["artifact:synthetic"],
        "status": "preview",
        "nodes": [{
            "node_id": "actor:synthetic", "label": "Iria", "node_type": kind,
            "description": "Synthetic declared actor kind", "importance": "medium",
            "semantic_state": {
                "canon_state": "played_canon", "lifecycle_state": "candidate",
                "evidence_role": "source_evidence", "authority_state": "system_derived",
                "visibility_state": "gm_private",
            },
            "evidence_refs": [{
                "source_ref_id": "source:synthetic", "source_artifact_id": "artifact:synthetic",
                "source_anchor_id": "anchor:synthetic", "source_span_ref_id": "span:synthetic",
                "label": "Synthetic passage", "evidence_role": "source_evidence",
                "can_open_source": True, "can_highlight_span": True,
                "anchor_quotes": ["Iria accompanies the Lanterns."],
            }],
            "proposed_action": "create", "confidence": "medium", "warnings": [],
        }],
        "edges": [], "beats": [], "proposed_writes": [],
        "ignored_items": [], "deferred_items": [], "diagnostics": {
            "preview_only": True, "extraction_performed": False, "llm_used": False,
            "runtime_connected": False, "plan_connected": False,
            "agent_interaction_connected": False, "corpus_scanned": False,
            "corpus_mutated": False, "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0, "warning_count": 0,
        },
    }


@pytest.mark.parametrize("kind,expected", [
    ("pc", "pc"), ("party", "party"), ("group", "group"), ("character", "npc"),
])
def test_explicit_kind_survives_typed_preview_and_contribution_mapping(kind, expected):
    preview = load_typed_candidate_graph(fixture(kind))
    assertion = map_candidate_node_to_assertion(
        preview.nodes[0], source_revision_id="sha256:synthetic",
        verified_source_artifact_id="artifact:synthetic", campaign_scope="synthetic",
    )
    assert assertion.value["kind"] == expected
    assert assertion.value["role"] == expected
    assert assertion.acceptance_state == "candidate"
    assert assertion.identity_resolution_outcome == "unresolved"


def test_unknown_kind_is_still_rejected():
    with pytest.raises(CandidateGraphMappingError, match="invalid node_type"):
        load_typed_candidate_graph(fixture("unverified_actor_kind"))
