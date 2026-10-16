import type { RecapIngestStatus } from "../api/types";

/** States that must follow live inspect graph_preview, never a stale draft. */
const GRAPH_PREVIEW_STATES = new Set([
  "preview_union_store_ready",
  "graph_preview_missing",
  "source_span_bundle_ready",
  "candidate_validation_ready",
  "graph_preview_failed",
]);

const GRAPH_STATE_PREFIXES = [
  "graph_",
  "preview_union_store_",
  "source_span_bundle_",
  "candidate_validation_",
];

function isGraphState(state: string): boolean {
  return GRAPH_PREVIEW_STATES.has(state) || GRAPH_STATE_PREFIXES.some((prefix) => state.startsWith(prefix));
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

  const draftReport = draftResult.ingest_report ?? {};
  const inspectedReport = inspected.ingest_report ?? {};
  const inspectHasGraphResult =
    Object.prototype.hasOwnProperty.call(inspectedReport, "graph_preview") ||
    inspected.states.some(isGraphState);
  const preservedDraftGraphStates = inspectHasGraphResult
    ? []
    : draftResult.states.filter(isGraphState);
  const inspectedGraphStates = graphStatesForInspect(inspected);
  const graphPreview = Object.prototype.hasOwnProperty.call(inspectedReport, "graph_preview")
    ? inspectedReport.graph_preview
    : draftReport.graph_preview;

  return {
    ...inspected,
    // `inspect_status` reports the current disk state. Local drafts may contain
    // older operation results, so only the independent graph-preview lane can
    // be carried forward when this inspection did not include one.
    states: [...new Set([...inspected.states, ...preservedDraftGraphStates, ...inspectedGraphStates])],
    // Keep unrelated graph/run details, but never restore old disk-derived
    // paths, corpus impact, readiness, warnings, or next actions.
    ingest_report: {
      ...draftReport,
      ...inspectedReport,
      ...(graphPreview === undefined ? {} : { graph_preview: graphPreview }),
    },
  };
}
