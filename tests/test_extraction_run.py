from __future__ import annotations

import pytest
from pydantic import ValidationError

from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
    assert_allowed_extraction_run_transition,
    assert_run_not_reviewable_when_incomplete,
    validate_extraction_run_lineage,
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
    with pytest.raises(ValidationError, match="incomplete"):
        ExtractionRun(
            run_id="run-1",
            source_artifact_id="artifact:x",
            source_domain="worldbuilding",
            status=ExtractionRunStatus.REVIEWABLE,
            components={},
        )


def test_reviewable_requires_core_components_with_digests() -> None:
    run = ExtractionRun(
        run_id="run-1",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.REVIEWABLE,
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://x.md",
                sha256="a" * 64,
            ),
            "source_span_index": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri="repo://spans.json",
                sha256="b" * 64,
            ),
            "candidate_graph": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri="repo://graph.json",
                sha256="c" * 64,
            ),
        },
    )
    assert run.is_reviewable() is True
    assert_run_not_reviewable_when_incomplete(run)


def test_exists_flag_alone_is_not_sufficient_for_reviewable_shape() -> None:
    run = ExtractionRun(
        run_id="run-1",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.DRAFT,
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://x.md",
                exists=True,
            ),
            "source_span_index": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri="repo://spans.json",
                exists=True,
            ),
            "candidate_graph": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri="repo://graph.json",
                exists=True,
            ),
        },
    )
    assert run.has_required_review_components() is False


def test_duplicate_component_kinds_are_rejected() -> None:
    with pytest.raises(ValidationError, match="component key must equal kind|duplicate component kind"):
        ExtractionRun(
            run_id="run-1",
            source_artifact_id="artifact:x",
            source_domain="worldbuilding",
            status=ExtractionRunStatus.DRAFT,
            components={
                "verified_graph": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    uri="repo://verified.json",
                    sha256="a" * 64,
                ),
                "candidate_graph": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    uri="repo://unverified.json",
                    sha256="b" * 64,
                ),
            },
        )


def test_non_canonical_component_keys_are_rejected() -> None:
    with pytest.raises(ValidationError, match="component key must equal kind"):
        ExtractionRun(
            run_id="run-1",
            source_artifact_id="artifact:x",
            source_domain="worldbuilding",
            status=ExtractionRunStatus.DRAFT,
            components={
                "graph": ExtractionRunComponentRef(
                    kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    uri="repo://graph.json",
                    sha256="a" * 64,
                ),
            },
        )


def test_terminal_transitions_are_rejected() -> None:
    with pytest.raises(ValueError, match="invalid extraction run transition"):
        assert_allowed_extraction_run_transition(
            ExtractionRunStatus.PROMOTED,
            ExtractionRunStatus.DRAFT,
        )
    with pytest.raises(ValueError, match="invalid extraction run transition"):
        assert_allowed_extraction_run_transition(
            ExtractionRunStatus.SUPERSEDED,
            ExtractionRunStatus.REVIEWABLE,
        )


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
            normalized_recap_sha256="a" * 64,
        ),
        artifacts={
            "source_span_index": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
                uri="runs/spans.json",
                sha256="b" * 64,
                exists=True,
            ),
            "candidate_graph": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
                uri="runs/graph.json",
                sha256="c" * 64,
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


def test_adapt_recap_manifest_preserves_llm_multi_telemetry_roles() -> None:
    """LLM graph-ingest manifests emit three PASS_TELEMETRY artifacts under distinct roles."""
    manifest = GraphIngestRunManifest(
        run_id="run-recap-llm-1",
        campaign_id="longmont-c2",
        session_id="session-22",
        status=GraphIngestRunStatus.CANDIDATE_VALIDATION_READY,
        source=GraphIngestSource(
            source_artifact_id="artifact:recap:longmont-c2:session-22",
            source_domain="recap",
            input_path_record="corpus/recap.md",
            normalized_recap_sha256="a" * 64,
        ),
        artifacts={
            "source_span_index": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
                uri="runs/source_span_index.json",
                sha256="b" * 64,
                exists=True,
            ),
            "candidate_graph": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
                uri="runs/candidate_graph.json",
                sha256="c" * 64,
                exists=True,
            ),
            "candidate_validation_report": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT,
                uri="runs/candidate_validation_report.json",
                sha256="d" * 64,
                exists=True,
            ),
            "pass_outputs": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.PASS_TELEMETRY,
                uri="runs/pass_outputs.json",
                sha256="e" * 64,
                exists=True,
            ),
            "pass_telemetry": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.PASS_TELEMETRY,
                uri="runs/pass_telemetry.json",
                sha256="f" * 64,
                exists=True,
            ),
            "consolidation_diagnostics": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.PASS_TELEMETRY,
                uri="runs/consolidation_diagnostics.json",
                sha256="1" * 64,
                exists=True,
            ),
        },
    )
    run = adapt_recap_manifest_to_extraction_run(manifest)
    assert run.components["pass_outputs"].uri.endswith("pass_outputs.json")
    assert run.components["pass_telemetry"].uri.endswith("pass_telemetry.json")
    assert run.components["consolidation_diagnostics"].uri.endswith(
        "consolidation_diagnostics.json"
    )
    assert run.components["pass_outputs"].sha256 == "e" * 64
    assert run.components["pass_telemetry"].sha256 == "f" * 64
    assert run.components["consolidation_diagnostics"].sha256 == "1" * 64
    assert run.components["pass_outputs"].kind == ExtractionRunComponentKind.PASS_OUTPUTS
    assert run.components["pass_telemetry"].kind == ExtractionRunComponentKind.PASS_TELEMETRY
    assert (
        run.components["consolidation_diagnostics"].kind
        == ExtractionRunComponentKind.CONSOLIDATION_DIAGNOSTICS
    )


def test_validate_extraction_run_lineage_requires_reciprocal_links() -> None:
    predecessor = ExtractionRun(
        run_id="run-a",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.SUPERSEDED,
        superseded_by_run_id="run-b",
    )
    successor = ExtractionRun(
        run_id="run-b",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.DRAFT,
        supersedes_run_id="run-a",
    )
    validate_extraction_run_lineage([predecessor, successor])

    one_sided = predecessor.model_copy(update={"superseded_by_run_id": "run-missing"})
    with pytest.raises(ValueError, match="missing successor"):
        validate_extraction_run_lineage([one_sided])

    non_reciprocal = successor.model_copy(update={"supersedes_run_id": None})
    with pytest.raises(ValueError, match="non-reciprocal"):
        validate_extraction_run_lineage([predecessor, non_reciprocal])


def test_validate_extraction_run_lineage_rejects_cycles() -> None:
    run_a = ExtractionRun(
        run_id="run-a",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.SUPERSEDED,
        superseded_by_run_id="run-b",
        supersedes_run_id="run-b",
    )
    run_b = ExtractionRun(
        run_id="run-b",
        source_artifact_id="artifact:x",
        source_domain="worldbuilding",
        status=ExtractionRunStatus.SUPERSEDED,
        superseded_by_run_id="run-a",
        supersedes_run_id="run-a",
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_extraction_run_lineage([run_a, run_b])
