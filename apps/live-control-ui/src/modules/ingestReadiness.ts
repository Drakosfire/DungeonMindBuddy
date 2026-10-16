import type { RecapGraphPreviewReport, RecapIngestStatus } from "../api/types";

export type IngestLaneState = "ready" | "not_ready" | "blocked" | "idle";

export interface IngestReadinessLane {
  id: "memory" | "graph" | "attention";
  label: string;
  state: IngestLaneState;
  detail: string;
}

export interface IngestReadiness {
  memory: IngestReadinessLane;
  graph: IngestReadinessLane;
  attention: IngestReadinessLane;
  nextAction: string;
  memoryReady: boolean;
  graphReady: boolean;
  isComplete: boolean;
}

interface CandidateValidationSummary {
  state: "not_applicable" | "valid" | "warning" | "blocked" | "unavailable";
  error_count: number;
  warning_count: number;
  unresolved_evidence_reference_count: number;
}

type CandidateValidationPreview = RecapGraphPreviewReport & {
  candidate_validation?: CandidateValidationSummary;
};

function hasState(result: RecapIngestStatus | null | undefined, state: string): boolean {
  return Boolean(result?.states?.includes(state));
}

function graphPreviewFrom(result: RecapIngestStatus | null | undefined): RecapGraphPreviewReport | null {
  const raw = result?.ingest_report?.graph_preview;
  if (!raw || typeof raw !== "object") return null;
  return raw as RecapGraphPreviewReport;
}

function memoryReady(result: RecapIngestStatus | null | undefined): boolean {
  return (
    hasState(result, "session_memory_materialized") ||
    hasState(result, "ready_for_planning_activation") ||
    result?.status === "ready_for_planning_activation"
  );
}

function graphReady(preview: RecapGraphPreviewReport | null): boolean {
  return preview?.status === "preview_union_store_ready";
}

function candidateValidationSummary(
  preview: RecapGraphPreviewReport | null,
): CandidateValidationSummary | undefined {
  return (preview as CandidateValidationPreview | null)?.candidate_validation;
}

function candidateValidationState(preview: RecapGraphPreviewReport | null):
  | "not_applicable"
  | "valid"
  | "warning"
  | "blocked"
  | "unavailable"
  | null {
  if (!preview) return null;
  const summary = candidateValidationSummary(preview);
  if (summary) return summary.state;
  if (
    preview.candidate_graph_path ||
    preview.status === "candidate_validation_ready" ||
    preview.status === "preview_union_store_ready"
  ) {
    return "unavailable";
  }
  return "not_applicable";
}

function candidateValidationMessage(preview: RecapGraphPreviewReport | null): string | null {
  const summary = candidateValidationSummary(preview);
  const state = candidateValidationState(preview);
  if (!state || state === "not_applicable" || state === "valid") return null;
  if (state === "unavailable") {
    return "Candidate validation details are unavailable; inspect the run before treating it as ready.";
  }
  if (state === "blocked") {
    const reasons = [
      summary?.unresolved_evidence_reference_count
        ? `${summary.unresolved_evidence_reference_count} unresolved evidence reference${summary.unresolved_evidence_reference_count === 1 ? "" : "s"}`
        : null,
      summary?.error_count ? `${summary.error_count} validation error${summary.error_count === 1 ? "" : "s"}` : null,
    ].filter(Boolean);
    return reasons.length
      ? `Candidate validation is blocked by ${reasons.join(" and ")}.`
      : "Candidate validation is blocked; inspect the validation report before admission.";
  }
  const warningCount = summary?.warning_count ?? 0;
  return `${warningCount} candidate validation warning${warningCount === 1 ? "" : "s"} need review before admission.`;
}

function graphBlocked(preview: RecapGraphPreviewReport | null): boolean {
  if (!preview) return false;
  if (preview.extraction_mode === "llm_blocked") return true;
  if (["blocked", "unavailable"].includes(candidateValidationState(preview) ?? "")) return true;
  return Boolean(preview.blocked_reason && preview.status !== "preview_union_store_ready");
}

function attentionItems(result: RecapIngestStatus | null | undefined, preview: RecapGraphPreviewReport | null): string[] {
  const items: string[] = [];
  if (!result) return items;

  const candidates = result.ingest_report?.normalized_recap_candidates;
  if (Array.isArray(candidates) && candidates.length > 1) {
    items.push(`Resolve ${candidates.length} duplicate normalized recaps.`);
  }
  if (Array.isArray(result.entity_spelling_audit) && result.entity_spelling_audit.length > 0) {
    items.push("Review spelling / entity variants before treating names as canon.");
  }
  const validationMessage = candidateValidationMessage(preview);
  if (validationMessage) items.push(validationMessage);
  if (graphBlocked(preview)) {
    if (!validationMessage) items.push(preview?.blocked_reason?.trim() || "Graph extraction is blocked.");
  }
  if (result.errors.length > 0) {
    items.push(...result.errors.slice(0, 2));
  }
  return items;
}

function memoryDetail(result: RecapIngestStatus | null | undefined, ready: boolean): string {
  if (!result) return "Load or inspect a session to see recap memory status.";
  if (ready) return "Session memory is on disk and ready for planning.";
  if (hasState(result, "breadcrumb_found")) return "Breadcrumb exists; materialize session memory next.";
  if (hasState(result, "frontmatter_seed_found") || hasState(result, "frontmatter_seed_required")) {
    return "Frontmatter seed / breadcrumb still needed.";
  }
  if (
    hasState(result, "normalized_reused") ||
    hasState(result, "normalized_created") ||
    hasState(result, "recap_reused") ||
    hasState(result, "recap_applied")
  ) {
    return "Canonical/normalized recap present; finish seed → breadcrumb → memory.";
  }
  return "Recap memory pipeline has not completed yet.";
}

function formatGraphCounts(preview: RecapGraphPreviewReport): string | null {
  const candidateReady = preview.status === "candidate_validation_ready";
  const nodes = candidateReady ? preview.candidate_node_count ?? preview.node_count : preview.node_count;
  const edges = candidateReady ? preview.candidate_edge_count ?? preview.edge_count : preview.edge_count;
  if (typeof nodes !== "number" && typeof edges !== "number") return null;
  const nodePart = typeof nodes === "number" ? `${nodes} node${nodes === 1 ? "" : "s"}` : null;
  const edgePart = typeof edges === "number" ? `${edges} edge${edges === 1 ? "" : "s"}` : null;
  return [nodePart, edgePart].filter(Boolean).join(", ");
}

function graphDetail(preview: RecapGraphPreviewReport | null, ready: boolean, blocked: boolean): string {
  const validationState = candidateValidationState(preview);
  const validationMessage = candidateValidationMessage(preview);
  const counts = preview ? formatGraphCounts(preview) : null;
  if (blocked && validationMessage && validationState !== "not_applicable") {
    const hasCandidateArtifact = Boolean(
      preview?.candidate_graph_path ||
        preview?.candidate_node_count != null ||
        preview?.candidate_edge_count != null,
    );
    if (!hasCandidateArtifact) return validationMessage;
    const candidateLabel = counts ? `Candidate extracted (${counts})` : "Candidate extracted";
    return `${candidateLabel}, but ${validationMessage.charAt(0).toLowerCase()}${validationMessage.slice(1)}`;
  }
  if (ready) {
    const detail = counts
      ? `Preview union on disk (${counts}). Open Graph Review to judge coverage.`
      : "Preview union store is on disk. Open Graph Review to judge coverage.";
    return validationMessage ? `${detail} ${validationMessage}` : detail;
  }
  if (preview?.status === "candidate_validation_ready" && !blocked) {
    if (validationState === "warning") {
      const candidate = `Extracted candidate${counts ? ` (${counts})` : ""} is available for review. World Graph admission is pending.`;
      return validationMessage ? `${candidate} ${validationMessage}` : candidate;
    }
    const candidate = `Extracted candidate${counts ? ` (${counts})` : ""} is ready for review. World Graph admission is pending.`;
    return validationMessage ? `${candidate} ${validationMessage}` : candidate;
  }
  if (blocked) return preview?.blocked_reason?.trim() || "Graph extraction blocked.";
  if (!preview || preview.status === "missing" || preview.status === "graph_preview_missing") {
    return "No preview graph for this session yet.";
  }
  return counts ? `Graph status: ${preview.status} (${counts}).` : `Graph status: ${preview.status}.`;
}

function buildNextAction(options: {
  result: RecapIngestStatus | null | undefined;
  memoryIsReady: boolean;
  graphIsReady: boolean;
  blocked: boolean;
  preview: RecapGraphPreviewReport | null;
  attention: string[];
}): string {
  const { result, memoryIsReady, graphIsReady, blocked, preview, attention } = options;
  if (!result) return "Inspect or load a session to see the next ingest action.";
  if (result.status === "needs_reconciliation" || attention.some((item) => item.includes("duplicate"))) {
    return "Resolve duplicate normalized recaps, then re-inspect status.";
  }
  const validationState = candidateValidationState(preview);
  if (validationState === "blocked") {
    const unresolved = candidateValidationSummary(preview)?.unresolved_evidence_reference_count ?? 0;
    return unresolved > 0
      ? `Next: resolve or recover ${unresolved} unresolved evidence reference${unresolved === 1 ? "" : "s"} before admission.`
      : "Next: inspect and resolve candidate validation errors before admission.";
  }
  if (validationState === "unavailable") {
    return "Next: inspect the candidate run or rerun validation before treating it as ready.";
  }
  if (validationState === "warning") {
    return "Next: review candidate validation warnings before admission.";
  }
  if (blocked) {
    return `Graph projection blocked: ${preview?.blocked_reason?.trim() || "unknown reason"}.`;
  }
  if (preview?.status === "candidate_validation_ready" && !blocked) {
    return "Next: Review the extracted candidate. World Graph admission is pending.";
  }
  if (!memoryIsReady) {
    if (hasState(result, "breadcrumb_found")) return "Next: Materialize Session Memory.";
    if (hasState(result, "frontmatter_seed_found")) return "Next: Run Breadcrumb Ingest.";
    if (
      hasState(result, "normalized_reused") ||
      hasState(result, "normalized_created") ||
      hasState(result, "recap_reused") ||
      hasState(result, "recap_applied")
    ) {
      return "Next: Build Frontmatter Seed, then breadcrumb and session memory.";
    }
    return "Next: Prep for ingest to package the session recap.";
  }
  if (!graphIsReady) {
    return "Next: Run ingest to extract the graph.";
  }
  const counts = preview ? formatGraphCounts(preview) : null;
  const countHint = counts ? ` (${counts})` : "";
  return `Session packaged; graph on disk${countHint}. Review in workbench — check Replace existing graph to re-run ingest.`;
}

export function buildIngestReadiness(result: RecapIngestStatus | null | undefined): IngestReadiness {
  const preview = graphPreviewFrom(result);
  const memoryIsReady = memoryReady(result);
  const graphIsReady = graphReady(preview);
  const blocked = graphBlocked(preview);
  const attention = attentionItems(result, preview);
  const isComplete = memoryIsReady && graphIsReady && !blocked && attention.length === 0;

  return {
    memory: {
      id: "memory",
      label: "Recap memory",
      state: memoryIsReady ? "ready" : result ? "not_ready" : "idle",
      detail: memoryDetail(result, memoryIsReady),
    },
    graph: {
      id: "graph",
      label: "Graph preview",
      state: blocked ? "blocked" : graphIsReady ? "ready" : result ? "not_ready" : "idle",
      detail: graphDetail(preview, graphIsReady, blocked),
    },
    attention: {
      id: "attention",
      label: "Attention",
      state: attention.length > 0 ? (blocked || result?.errors.length ? "blocked" : "not_ready") : "ready",
      detail: attention.length > 0 ? attention.join(" ") : "No blocking review items.",
    },
    nextAction: buildNextAction({
      result,
      memoryIsReady,
      graphIsReady,
      blocked,
      preview,
      attention,
    }),
    memoryReady: memoryIsReady,
    graphReady: graphIsReady,
    isComplete,
  };
}
