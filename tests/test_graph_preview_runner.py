from __future__ import annotations

from typing import Any

import pytest

from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)
from src.graph_memory.extraction.recap_source_adapter import RecapSourceAdapter
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION,
)
from src.graph_memory.extraction.worldbuilding_source_adapter import WorldbuildingSourceAdapter
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)


class FixtureClient:
    def __init__(self, *, mode: str = "ok") -> None:
        self.mode = mode

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
    ) -> dict[str, Any]:
        if self.mode == "refusal":
            raise CategoryGraphExtractionError(f"model refused {pass_name}: policy")
        if self.mode == "incomplete":
            raise CategoryGraphExtractionError(f"model response incomplete for {pass_name}")
        if self.mode == "schema":
            raise CategoryGraphExtractionError(f"schema failure for {pass_name}")
        if pass_name == "edge_pass":
            return {
                "parsed": {"observation_edges": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "edge",
            }
        if pass_name == "beat_pass":
            return {
                "parsed": {"observation_beats": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "beat",
            }
        node = {
            "node_id": f"{pass_name}-1",
            "label": "Mirathorn",
            "node_type": "location",
            "description": "fixture",
            "importance": "medium",
            "evidence_refs": [
                {"source_span_ref_id": "span-1", "anchor_quotes": ["Mirathorn"]}
            ],
        }
        if self.mode == "missing_evidence":
            node["evidence_refs"] = []
        return {
            "parsed": {"observation_nodes": [node]},
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": pass_name,
        }


def test_unknown_profile_persists_failed_run(tmp_path) -> None:
    source = RecapSourceAdapter(
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_text="Mirathorn stands.\n",
    ).normalize()
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="missing",
            profile_version="0.0",
            allow_llm=True,
            category_client=FixtureClient(),
        )
    )
    assert result.failure_kind == "profile"
    assert result.run.status == ExtractionRunStatus.FAILED


def test_recap_fixture_extracts_reviewable_run(tmp_path) -> None:
    source = RecapSourceAdapter(
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_text="Mirathorn is a river city.\n\nGuards watch the gate.\n",
    ).normalize()
    # Rewrite span ids used by fixture client.
    spans = list(source.source_span_index["spans"])
    for span in spans:
        if span.get("kind") == "paragraph":
            span["span_id"] = "span-1"
            span["source_span_ref_id"] = "span-1"
    source = source.__class__(
        **{
            **source.__dict__,
            "source_span_index": {**source.source_span_index, "spans": spans},
        }
    )
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(),
            output_dir=tmp_path / "run",
        )
    )
    assert result.failure_kind is None
    assert result.run.status == ExtractionRunStatus.REVIEWABLE
    assert result.run.session_id == "session-24"
    assert result.run.profile_id == f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}"
    assert result.candidate_graph is not None


def test_worldbuilding_null_session_extracts(tmp_path) -> None:
    source = WorldbuildingSourceAdapter(
        source_artifact_id="artifact:worldbuilding:eldyrwild:doc-1",
        source_text="Mirathorn is a river city.\n",
        campaign_id="eldyrwild",
    ).normalize()
    spans = list(source.source_span_index["spans"])
    for span in spans:
        if span.get("kind") == "paragraph":
            span["span_id"] = "span-1"
            span["source_span_ref_id"] = "span-1"
    source = source.__class__(
        **{
            **source.__dict__,
            "source_span_index": {**source.source_span_index, "spans": spans},
        }
    )
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
            profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(),
            output_dir=tmp_path / "wb-run",
        )
    )
    assert result.run.session_id is None
    assert result.run.status == ExtractionRunStatus.REVIEWABLE


@pytest.mark.parametrize("mode,kind", [("refusal", "refusal"), ("incomplete", "incomplete"), ("schema", "schema")])
def test_failure_modes_persist(tmp_path, mode: str, kind: str) -> None:
    source = RecapSourceAdapter(
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_text="Mirathorn.\n",
    ).normalize()
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(mode=mode),
        )
    )
    assert result.failure_kind == kind
    assert result.run.status == ExtractionRunStatus.FAILED
