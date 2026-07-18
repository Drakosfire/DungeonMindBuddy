"""Category extractor defaults must emit typed CandidateGraphPreview SemanticState."""

from __future__ import annotations

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    DEFAULT_SEMANTIC_STATE,
)


def test_default_semantic_state_is_typed_promote_eligible() -> None:
    assert DEFAULT_SEMANTIC_STATE == {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }
    assert "canon_status" not in DEFAULT_SEMANTIC_STATE
    assert "lifecycle" not in DEFAULT_SEMANTIC_STATE
    assert "memory_status" not in DEFAULT_SEMANTIC_STATE
