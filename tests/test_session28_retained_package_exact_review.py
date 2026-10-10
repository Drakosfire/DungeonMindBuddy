from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest
from apps.live_control_server.services import (
    candidate_graph_admission,
    extract_promote,
    graph_run_registry,
)


def test_retained_style_review_uses_the_canonical_exact_run_projection(
    monkeypatch, tmp_path: Path
) -> None:
    run_id = "retained-import-synthetic"
    artifact_id = "artifact:recap:synthetic:session-28:abc"
    source_span_id = f"{artifact_id}:span:abc:1-1"
    source = tmp_path / "source.md"
    source.write_text("Mira found the silver key and returned to camp.\n", encoding="utf-8")
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps({"campaign_id": "synthetic", "session_id": "session-28"}))
    span_index_path = tmp_path / "span-index.json"
    span_index_path.write_text("{}\n", encoding="utf-8")

    evidence_ref = SimpleNamespace(
        source_artifact_id=artifact_id,
        source_span_ref_id=source_span_id,
        anchor_quotes=[
            "Mira found the silver key",
            "Mira returned with the silver key",
        ],
    )
    typed = SimpleNamespace(
        nodes=[SimpleNamespace(
            node_id="mira-found-key",
            label="Mira found the silver key",
            description="Mira found and returned with the key.",
            evidence_refs=[evidence_ref],
        )],
        edges=[],
    )
    resolved = SimpleNamespace(
        run_id=run_id,
        status="reviewable",
        normalized_recap_path=source,
        candidate_graph_path=candidate_path,
        source_span_index_path=span_index_path,
        source_artifact_id=artifact_id,
        source_revision_id="sha256:abc",
        campaign_id="synthetic",
        session_id="session-28",
        source_domain="recap",
        world_id="synthetic-world",
        sealed_source_uri="file:///synthetic/source.md",
        diagnostics=["resolved via canonical ExtractionRun registry"],
    )
    span_index = SimpleNamespace(spans=[SimpleNamespace(
        source_span_id=source_span_id,
        start_line=1,
        end_line=1,
    )])
    capability = SimpleNamespace(
        world_id="synthetic-world",
        world_state="uninitialized",
        eligible=True,
        reason=None,
    )
    monkeypatch.setattr(candidate_graph_admission, "validate_candidate_document_integrity", lambda _: typed)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_args, **_kwargs: resolved)
    monkeypatch.setattr(extract_promote, "_load_frozen_span_index_for_resolved_run", lambda _: span_index)
    monkeypatch.setattr(extract_promote, "resolve_first_world_capability", lambda **_kwargs: capability)
    monkeypatch.setattr(
        extract_promote,
        "_resolve_publication_target",
        lambda _world_id: SimpleNamespace(native_world_id="synthetic-world"),
    )
    monkeypatch.setattr(extract_promote, "_recap_semantic_assessment", lambda *_args: (None, None))
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    monkeypatch.setattr(
        graph_run_registry,
        "get_extraction_run",
        lambda *_args, **_kwargs: SimpleNamespace(lineage={}),
    )

    review = extract_promote.get_exact_run_review_package(run_id)

    assert review.run_id == run_id
    assert review.assertions[0].assertion_id == "mira-found-key"
    assert review.assertions[0].evidence[0].source_span_ref_id == source_span_id
    assert review.inspection_status == "invalid_evidence"
    assert review.invalid_evidence_count == 1
    assert review.assertions[0].evidence[0].invalid_anchor_quotes == [
        "Mira returned with the silver key"
    ]
    assert review.assertions[0].evidence[0].source_span_ref_id == source_span_id
    assert review.promotable is False
    assert review.first_world_publish_eligible is False
    assert "publication is blocked" in review.promotable_reason.lower()
    assert any("unresolved_quote_binding:" in item for item in review.diagnostics)

    with pytest.raises(extract_promote.ExtractPromoteError) as exc_info:
        extract_promote.prepare(
            ExtractPromotePrepareRequest(
                run_id=run_id,
                managed_world_id="synthetic-managed-world",
            )
        )

    error = exc_info.value
    assert error.code == "run_not_promotable"
    assert "anchor quote" in str(error).lower()
    assert "canonical span paragraph" in str(error).lower()
    assert any(item.code == "false_anchor_quote" for item in error.diagnostics)
    assert any(item.code == "span_ref" and item.message == source_span_id for item in error.diagnostics)
