from __future__ import annotations

import pytest

from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
    assert_run_not_reviewable_when_incomplete,
)
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestSource,
    adapt_recap_manifest_to_extraction_run,
)


def test_incomplete_run_cannot_be_reviewable() -> None:
    run = ExtractionRun(
        run_id="run-1",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.REVIEWABLE,
        components={},
    )
    assert run.is_reviewable() is False
    with pytest.raises(ValueError, match="incomplete"):
        assert_run_not_reviewable_when_incomplete(run)


def test_reviewable_requires_core_components() -> None:
    run = ExtractionRun(
        run_id="run-1",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.REVIEWABLE,
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://x.md",
                exists=True,
            ),
            "spans": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri="repo://spans.json",
                exists=True,
            ),
            "graph": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri="repo://graph.json",
                exists=True,
            ),
        },
    )
    assert run.is_reviewable() is True
    assert_run_not_reviewable_when_incomplete(run)


def test_adapt_recap_manifest_preserves_scope_and_ids() -> None:
    manifest = GraphIngestRunManifest(
        run_id="run-recap-1",
        campaign_id="longmont-c2",
        session_id="session-22",
        status=GraphIngestRunStatus.READY_FOR_PROJECTION,
        source=GraphIngestSource(
            source_artifact_id="artifact:recap:longmont-c2:session-22",
            source_domain="recap",
            input_path_record="corpus/recap.md",
            normalized_recap_sha256="abc",
        ),
        artifacts={
            "source_span_index": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
                uri="runs/spans.json",
                exists=True,
            ),
            "candidate_graph": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
                uri="runs/graph.json",
                exists=True,
            ),
        },
    )
    run = adapt_recap_manifest_to_extraction_run(manifest)
    assert run.run_id == "run-recap-1"
    assert run.campaign_id == "longmont-c2"
    assert run.session_id == "session-22"
    assert run.source_artifact_id == "artifact:recap:longmont-c2:session-22"
    assert run.source_domain == "recap"
    assert run.status == ExtractionRunStatus.REVIEWABLE
    assert run.lineage["adapter"] == "graph_ingest_run_manifest_v0"


def test_adapt_recap_manifest_rejects_missing_source_artifact() -> None:
    manifest = GraphIngestRunManifest(
        run_id="run-recap-1",
        campaign_id="longmont-c2",
        session_id="session-22",
        source=GraphIngestSource(source_domain="recap"),
    )
    with pytest.raises(ValueError, match="source_artifact_id"):
        adapt_recap_manifest_to_extraction_run(manifest)
