from __future__ import annotations

import json

import pytest

from src.graph_memory.extraction.preview_candidate_graph_extractor import (
    FixtureCandidateGraphModelClient,
    PreviewCandidateGraphExtractionOptions,
    enforce_preview_only_candidate_graph,
    extract_preview_candidate_graph,
)


def test_sanitizes_preview_only_diagnostics_and_arrays() -> None:
    graph = enforce_preview_only_candidate_graph(
        {
            "candidate_nodes": [{"id": "node:bonogo", "label": "Bonogo", "evidence_refs": ["ev:1"]}, "bad"],
            "candidate_edges": None,
            "session_beats": [{"summary": "A beat", "evidence_refs": ["ev:1"]}],
            "evidence_refs": [{"id": "ev:1", "span_id": "session-22:recap:full_text"}, {"id": "bad"}],
            "diagnostics": {
                "preview_only": False,
                "canon_promotion": True,
                "approved_memory_write": True,
                "corpus_mutation": True,
                "production_retrieval": True,
            },
        }
    )

    assert graph["diagnostics"]["preview_only"] is True
    assert graph["diagnostics"]["canon_promotion"] is False
    assert graph["diagnostics"]["approved_memory_write"] is False
    assert graph["diagnostics"]["corpus_mutation"] is False
    assert graph["diagnostics"]["production_retrieval"] is False
    assert len(graph["candidate_nodes"]) == 1
    assert graph["candidate_edges"] == []
    assert len(graph["evidence_refs"]) == 1


def test_rejects_malformed_non_object_model_output() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        enforce_preview_only_candidate_graph([])  # type: ignore[arg-type]


def test_extract_preview_candidate_graph_uses_fixture_client() -> None:
    raw = json.dumps(
        {
            "candidate_nodes": [],
            "candidate_edges": [],
            "session_beats": [],
            "ignored_or_deferred_candidates": [{"summary": "uncertain spelling"}],
            "source_artifacts": [],
            "evidence_refs": [],
        }
    )
    result = extract_preview_candidate_graph(
        PreviewCandidateGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            recap_markdown="Bonogo found a clue.",
            source_span_id="session-22:recap:full_text",
        ),
        client=FixtureCandidateGraphModelClient(raw),
    )

    assert result.raw_model_response == raw
    assert result.candidate_graph["ignored_or_deferred_candidates"] == [{"summary": "uncertain spelling"}]
    assert result.candidate_graph["diagnostics"]["preview_only"] is True
