from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

GRAPH_INGEST_RUN_MANIFEST_SCHEMA = "dmb_graph_ingest_run_manifest_v0"
GRAPH_INGEST_RUN_MANIFEST_VERSION = "0.1"


class GraphIngestRunStatus(StrEnum):
    NOT_STARTED = "not_started"
    SOURCE_READY = "source_ready"
    SOURCE_SPAN_BUNDLE_READY = "source_span_bundle_ready"
    CANDIDATE_EXTRACTION_READY = "candidate_extraction_ready"
    CANDIDATE_VALIDATION_READY = "candidate_validation_ready"
    PREVIEW_UNION_STORE_READY = "preview_union_store_ready"
    READY_FOR_PROJECTION = "ready_for_projection"
    FAILED = "failed"


class GraphIngestStepState(StrEnum):
    LOCKED = "locked"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class GraphIngestArtifactKind(StrEnum):
    NORMALIZED_RECAP = "normalized_recap"
    SOURCE_SPAN_BUNDLE = "source_span_bundle"
    SOURCE_SPAN_INDEX = "source_span_index"
    PROVENANCE_INDEX = "provenance_index"
    CANDIDATE_GRAPH = "candidate_graph"
    REGISTRY_CONTEXT_GRAPH = "registry_context_graph"
    CANDIDATE_VALIDATION_REPORT = "candidate_validation_report"
    PASS_TELEMETRY = "pass_telemetry"
    KNOWN_ENTITY_MENTIONS = "known_entity_mentions"
    PREVIEW_UNION_STORE = "preview_union_store"
    PREVIEW_UNION_VALIDATION_REPORT = "preview_union_validation_report"
    PROJECTION_PAYLOAD = "projection_payload"


class _GraphIngestModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class GraphIngestArtifactRef(_GraphIngestModel):
    kind: GraphIngestArtifactKind
    uri: str
    schema_: str | None = Field(
        default=None, validation_alias="schema", serialization_alias="schema"
    )
    sha256: str | None = None
    exists: bool = False
    preview_only: bool = True

    @property
    def schema(self) -> str | None:
        return self.schema_


class GraphIngestSource(_GraphIngestModel):
    source_artifact_id: str | None = None
    source_domain: str = "recap"
    input_path_record: str | None = None
    normalized_recap_path: str | None = None
    normalized_recap_sha256: str | None = None
    source_label: str | None = None
    source_span_bundle_uri: str | None = None
    source_span_index_uri: str | None = None
    provenance_index_uri: str | None = None


class GraphIngestStepStatus(_GraphIngestModel):
    id: str
    label: str
    state: GraphIngestStepState
    started_at: str | None = None
    completed_at: str | None = None
    summary: str | None = None
    artifact_refs: list[GraphIngestArtifactRef] = Field(default_factory=list)


class GraphIngestHealth(_GraphIngestModel):
    candidate_graph_valid: bool | None = None
    preview_union_store_valid: bool | None = None
    node_count: int = 0
    edge_count: int = 0
    beat_count: int = 0
    ignored_count: int = 0
    deferred_count: int = 0
    evidence_ref_count: int = 0
    resolvable_evidence_ref_count: int = 0
    openable_evidence_ref_count: int = 0
    highlightable_evidence_ref_count: int = 0
    model_id: str | None = None
    estimated_cost_usd: float | None = None


class GraphIngestDiagnostics(_GraphIngestModel):
    preview_only: bool = True
    candidate_extraction: bool = False
    preview_import: bool = False
    canon_promotion: bool = False
    approved_memory_write: bool = False
    corpus_mutation: bool = False
    production_retrieval: bool = False
    agent_interaction_connected: bool = False
    runtime_projection_connected: bool = False


class GraphIngestProjectionLocator(_GraphIngestModel):
    projection_ready: bool = False
    projection_endpoint: str | None = None
    query: dict[str, Any] = Field(default_factory=dict)


class GraphIngestRunManifest(_GraphIngestModel):
    schema_: str = Field(
        default=GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        validation_alias="schema",
        serialization_alias="schema",
    )
    version: str = GRAPH_INGEST_RUN_MANIFEST_VERSION
    run_id: str
    campaign_id: str
    session_id: str
    status: GraphIngestRunStatus = GraphIngestRunStatus.NOT_STARTED
    created_at: str | None = None
    updated_at: str | None = None
    source: GraphIngestSource = Field(default_factory=GraphIngestSource)
    steps: list[GraphIngestStepStatus] = Field(default_factory=list)
    artifacts: dict[str, GraphIngestArtifactRef] = Field(default_factory=dict)
    health: GraphIngestHealth = Field(default_factory=GraphIngestHealth)
    diagnostics: GraphIngestDiagnostics = Field(default_factory=GraphIngestDiagnostics)
    projection: GraphIngestProjectionLocator | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @property
    def schema(self) -> str:
        return self.schema_


# ---------------------------------------------------------------------------
# Legacy recap manifest adapter → canonical ExtractionRun
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[GraphIngestRunStatus, str] = {
    GraphIngestRunStatus.NOT_STARTED: "draft",
    GraphIngestRunStatus.SOURCE_READY: "prepared",
    GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY: "prepared",
    GraphIngestRunStatus.CANDIDATE_EXTRACTION_READY: "extracted",
    GraphIngestRunStatus.CANDIDATE_VALIDATION_READY: "validated",
    GraphIngestRunStatus.PREVIEW_UNION_STORE_READY: "validated",
    GraphIngestRunStatus.READY_FOR_PROJECTION: "reviewable",
    GraphIngestRunStatus.FAILED: "failed",
}


def adapt_recap_manifest_to_extraction_run(manifest: GraphIngestRunManifest):
    """Map a recap/preview manifest into the canonical ExtractionRun contract.

    This module remains the recap/legacy loader surface; ExtractionRun is the
    canonical exact-run authority for new consumers.
    """
    from graph_memory.ingestion.extraction_run import (
        ExtractionRun,
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunDiagnostics,
        ExtractionRunStatus,
    )

    if not manifest.run_id or not manifest.run_id.strip():
        raise ValueError("recap manifest run_id is required")
    if not manifest.campaign_id or not manifest.session_id:
        raise ValueError("recap manifest requires campaign_id and session_id")

    source_artifact_id = manifest.source.source_artifact_id
    if not source_artifact_id:
        raise ValueError("recap manifest source.source_artifact_id is required for adaptation")

    components: dict[str, ExtractionRunComponentRef] = {}
    kind_map = {
        GraphIngestArtifactKind.SOURCE_SPAN_INDEX: ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
        GraphIngestArtifactKind.CANDIDATE_GRAPH: ExtractionRunComponentKind.CANDIDATE_GRAPH,
        GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT: ExtractionRunComponentKind.VALIDATION_REPORT,
        GraphIngestArtifactKind.PASS_TELEMETRY: ExtractionRunComponentKind.PASS_TELEMETRY,
        GraphIngestArtifactKind.PROVENANCE_INDEX: ExtractionRunComponentKind.PROVENANCE_INDEX,
    }
    for key, artifact in manifest.artifacts.items():
        mapped = kind_map.get(artifact.kind)
        if mapped is None:
            continue
        components[key] = ExtractionRunComponentRef(
            kind=mapped,
            uri=artifact.uri,
            sha256=artifact.sha256,
            exists=artifact.exists,
        )
    components["source_artifact"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
        uri=manifest.source.input_path_record or manifest.source.normalized_recap_path or "",
        sha256=manifest.source.normalized_recap_sha256,
        exists=bool(source_artifact_id),
    )

    status_value = _STATUS_MAP.get(manifest.status, "incomplete")
    status = ExtractionRunStatus(status_value)
    diagnostics = ExtractionRunDiagnostics(
        messages=list(manifest.warnings),
        errors=list(manifest.errors),
    )
    # Build non-reviewable first so incomplete REVIEWABLE mappings fail closed
    # without violating the ExtractionRun model validator.
    construct_status = (
        ExtractionRunStatus.INCOMPLETE
        if status == ExtractionRunStatus.REVIEWABLE
        else status
    )
    run = ExtractionRun(
        run_id=manifest.run_id,
        source_artifact_id=source_artifact_id,
        source_domain=manifest.source.source_domain or "recap",
        status=construct_status,
        campaign_id=manifest.campaign_id,
        session_id=manifest.session_id,
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        components=components,
        diagnostics=diagnostics,
        lineage={
            "adapter": "graph_ingest_run_manifest_v0",
            "legacy_status": manifest.status.value,
        },
    )
    if status == ExtractionRunStatus.REVIEWABLE and run.has_required_review_components():
        run = run.model_copy(update={"status": ExtractionRunStatus.REVIEWABLE})
    return run

