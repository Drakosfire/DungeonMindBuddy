import type { RecapIngestStatus } from "../api/types";

/** States that must follow live inspect graph_preview, never a stale draft. */
const GRAPH_PREVIEW_STATES = new Set([
  "preview_union_store_ready",
  "graph_preview_missing",
  "source_span_bundle_ready",
  "candidate_validation_ready",
  "graph_preview_failed",
]);

function progressRank(status: string): number {
  switch (status) {
    case "ready_for_planning_activation":
      return 5;
    case "breadcrumb_required":
      return 4;
    case "recap_applied":
      return 3;
    case "recap_preview_created":
      return 2;
    default:
      return 1;
  }
}

function graphStatesForInspect(inspected: RecapIngestStatus): string[] {
  const fromInspect = inspected.states.filter((state) => GRAPH_PREVIEW_STATES.has(state));
  // ingest_report is an untyped report bag; graph_preview.status is read defensively.
  const graphPreview = inspected.ingest_report?.graph_preview as { status?: unknown } | undefined;
  const previewStatus = graphPreview?.status;
  if (previewStatus === "preview_union_store_ready") {
    return [...new Set([...fromInspect, "preview_union_store_ready"])];
  }
  if (previewStatus === "missing" || previewStatus === "graph_preview_missing") {
    return [...new Set([...fromInspect.filter((s) => s !== "preview_union_store_ready"), "graph_preview_missing"])];
  }
  return fromInspect.filter((state) => state !== "preview_union_store_ready");
}

/**
 * Merge a localStorage draft with a fresh inspect payload.
 * Inspect wins for graph_preview and graph-related states so draft cannot claim
 * "preview union materialized" after inspect reports missing (or the reverse).
 */
export function mergeInspectResult(
  draftResult: RecapIngestStatus | null,
  inspected: RecapIngestStatus,
): RecapIngestStatus {
  if (!draftResult) {
    return inspected;
  }

  const nonGraphDraft = draftResult.states.filter((state) => !GRAPH_PREVIEW_STATES.has(state));
  const nonGraphInspected = inspected.states.filter((state) => !GRAPH_PREVIEW_STATES.has(state));
  const mergedStates = [
    ...new Set([...nonGraphDraft, ...nonGraphInspected, ...graphStatesForInspect(inspected)]),
  ];

  const status =
    progressRank(draftResult.status) >= progressRank(inspected.status)
      ? draftResult.status
      : inspected.status;

  const draftReport = draftResult.ingest_report ?? {};
  const inspectedReport = inspected.ingest_report ?? {};

  return {
    ...inspected,
    status,
    states: mergedStates,
    paths: { ...inspected.paths, ...draftResult.paths },
    warnings: [...new Set([...draftResult.warnings, ...inspected.warnings])],
    next_actions:
      draftResult.next_actions.length > 0 ? draftResult.next_actions : inspected.next_actions,
    // Inspect wins on report keys (especially graph_preview). Draft only fills gaps.
    ingest_report: {
      ...draftReport,
      ...inspectedReport,
      graph_preview: inspectedReport.graph_preview ?? draftReport.graph_preview,
    },
    entity_spelling_audit:
      draftResult.entity_spelling_audit.length > 0
        ? draftResult.entity_spelling_audit
        : inspected.entity_spelling_audit,
  };
}
