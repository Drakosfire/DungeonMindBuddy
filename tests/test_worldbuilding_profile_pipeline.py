"""Fixture-backed pipeline proof for the bounded worldbuilding profile."""

from __future__ import annotations

import json
from pathlib import Path

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    FixtureCategoryGraphPassClient,
)
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
    validate_worldbuilding_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_source_adapter import (
    WorldbuildingSourceAdapter,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "graph_memory_layer"
    / "fixtures"
    / "worldbuilding_profile_fixture.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _pass_outputs_for_span(fixture: dict, span_id: str) -> dict:
    outputs = json.loads(json.dumps(fixture["pass_outputs"]))
    for pass_payload in outputs.values():
        for key in ("observation_nodes", "observation_edges"):
            for row in pass_payload.get(key) or []:
                for ref in row.get("evidence_refs") or []:
                    if ref.get("source_span_ref_id") == "PLACEHOLDER_SPAN":
                        ref["source_span_ref_id"] = span_id
    return outputs


def test_fixture_pipeline_produces_reviewable_null_session_run(tmp_path: Path) -> None:
    fixture = _load_fixture()
    source = WorldbuildingSourceAdapter(
        source_artifact_id=fixture["source_artifact_id"],
        source_text=fixture["source_text"],
        campaign_id=fixture["campaign_id"],
        document_class=fixture["document_class"],
        source_uri="fixture://worldbuilding_profile",
    ).normalize()
    paragraph = next(
        span
        for span in source.source_span_index["spans"]
        if span.get("kind") == "paragraph"
    )
    span_id = paragraph["source_span_ref_id"]
    client = FixtureCategoryGraphPassClient(_pass_outputs_for_span(fixture, span_id))

    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            allow_llm=True,
            category_client=client,
            output_dir=tmp_path / "out" / "runs" / "wb-profile",
        )
    )

    assert result.failure_kind is None
    assert result.run.status.value == "reviewable"
    assert result.run.session_id is None
    assert result.run.profile_id == f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    assert result.candidate_graph is not None
    assert result.candidate_graph.get("session_id") in (None, "")
    assert validate_worldbuilding_candidate_bounds(result.candidate_graph) == []
    labels = {node["label"] for node in result.candidate_graph["nodes"]}
    assert "Commander Vell" in labels
    assert "Shepherd's Flock" in labels
    assert "Flockhouse" in labels
    for node in result.candidate_graph["nodes"]:
        assert node["evidence_refs"]
        assert all("source_span_ref_id" in ref for ref in node["evidence_refs"])


def test_fixture_pipeline_rejects_recap_profile_for_worldbuilding_source(
    tmp_path: Path,
) -> None:
    fixture = _load_fixture()
    source = WorldbuildingSourceAdapter(
        source_artifact_id=fixture["source_artifact_id"],
        source_text=fixture["source_text"],
        campaign_id=fixture["campaign_id"],
        document_class=fixture["document_class"],
    ).normalize()
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="recap_category_v1",
            profile_version="1.0",
            allow_llm=False,
            output_dir=tmp_path / "out" / "runs" / "bad-profile",
        )
    )
    assert result.failure_kind == "profile"
    assert result.run.status.value == "failed"
