"""Exact source-bound batch adaptation; Graph admission stays in DungeonMind."""
from dungeonmind.application.world_graph_retrieval import ReviewedObservationSelectionRequest
from graph_memory.retrieval.models import WorldGraphRetrievalNode, WorldGraphRetrievalResult
from . import world_graph_reads as reads


def select_observations_direct(services, request):
    try:
        projection = reads._map_retrieval_context(request, services.binding)
        native = services.retrieval.select_reviewed_source_observations(
            ReviewedObservationSelectionRequest(projection, request.source_artifact_id,
                request.source_revision_id, tuple(request.observation_ids), request.max_bytes))
        if native.status != "complete":
            raise reads.DirectWorldGraphReadError(
                "Exact source observation selection is unavailable" if native.status == "unavailable"
                else "Complete observation selection exceeds the result byte budget",
                code="selected_observation_unavailable" if native.status == "unavailable"
                else "observation_selection_overflow", status_code=422 if native.status == "unavailable" else 413,
            )
        if (native.source_artifact_id != request.source_artifact_id
                or native.source_revision_id != request.source_revision_id
                or set(row.assertion_id for row in native.observations) != set(request.observation_ids)):
            raise ValueError("Native selected observation identity differs from request")
        public = WorldGraphRetrievalResult(operation="observations", outcome="enough",
            snapshot=reads._retrieval_snapshot_view(native.snapshot, focus=request.focus.to_projection_focus()),
            request_summary={"observation_ids": list(request.observation_ids)},
            matched_node_ids=[row.subject_object_id for row in native.subjects],
            nodes=[WorldGraphRetrievalNode(node_id=row.subject_object_id, label=row.subject_label,
                kind=reads._wire_term(row.subject_kind), role=reads._wire_term(row.subject_kind))
                for row in native.subjects],
            source_anchors=reads._source_anchor_views(native.anchors, revision_id=native.snapshot.revision_id),
            coverage=reads._coverage_view(native.coverage))
        resolved = reads._resolved_operation_v3(native, public)
        return reads.ResolvedWorldGraphReviewedObjectV3(public, resolved.source_pins,
            tuple(reads._reviewed_source_observation_view(row) for row in native.observations),
            native.coverage.gap_codes, native.coverage.missing_ids)
    except Exception as exc:
        raise reads._map_direct_error(exc) from exc
