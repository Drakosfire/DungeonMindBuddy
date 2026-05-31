import type { RecapIngestStatus } from "../api/types";

export const SESSION_22_CANONICAL_SLUG = "Mireward Road and Lysandro";
export const SESSION_22_CANONICAL_TITLE = "Session 22 - Mireward Road and Lysandro";

export interface CorpusPipelineStep {
  id: string;
  label: string;
  matchStates: string[];
  pathKey: keyof RecapIngestStatus["paths"];
}

export const CORPUS_PIPELINE_STEPS: CorpusPipelineStep[] = [
  {
    id: "staged",
    label: "Staged raw notes",
    matchStates: ["staged_raw_notes_created", "staged_raw_notes_reused"],
    pathKey: "staged_raw_notes",
  },
  {
    id: "canonical",
    label: "Canonical recap",
    matchStates: ["recap_applied", "recap_reused"],
    pathKey: "canonical_recap",
  },
  {
    id: "normalized",
    label: "Normalized recap",
    matchStates: ["normalized_created", "normalized_reused"],
    pathKey: "normalized_recap",
  },
  {
    id: "breadcrumb",
    label: "Breadcrumb routing",
    matchStates: ["breadcrumb_found"],
    pathKey: "breadcrumbed_recap",
  },
  {
    id: "session_memory",
    label: "Session memory",
    matchStates: ["session_memory_materialized"],
    pathKey: "session_memory_jsonl",
  },
];

export function recapSourceSession(liveSession: number): number {
  return Math.max(1, liveSession - 1);
}

export function inspectHintsForRecapSession(recapSession: number): {
  slug?: string;
  title?: string;
} {
  if (recapSession === 22) {
    return { slug: SESSION_22_CANONICAL_SLUG, title: SESSION_22_CANONICAL_TITLE };
  }
  return {};
}

export function stepComplete(result: RecapIngestStatus, step: CorpusPipelineStep): boolean {
  return step.matchStates.some((state) => result.states.includes(state));
}

export function corpusReadyForPlanning(result: RecapIngestStatus | null): boolean {
  return result?.states.includes("ready_for_planning_activation") ?? false;
}

export function corpusStatusHeadline(result: RecapIngestStatus | null): string {
  if (!result) {
    return "Checking corpus…";
  }
  if (result.errors.length > 0) {
    return "Corpus ingest error";
  }
  if (corpusReadyForPlanning(result)) {
    return "Corpus loaded for planning";
  }
  if (result.status === "breadcrumb_required") {
    return "Breadcrumb artifact missing";
  }
  const completed = CORPUS_PIPELINE_STEPS.filter((step) => stepComplete(result, step)).length;
  return `Corpus ingest ${completed}/${CORPUS_PIPELINE_STEPS.length} complete`;
}

export function corpusStatusTone(
  result: RecapIngestStatus | null,
): "ready" | "progress" | "error" | "loading" {
  if (!result) {
    return "loading";
  }
  if (result.errors.length > 0) {
    return "error";
  }
  if (corpusReadyForPlanning(result)) {
    return "ready";
  }
  return "progress";
}
