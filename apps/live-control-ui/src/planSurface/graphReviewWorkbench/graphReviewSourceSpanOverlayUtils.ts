import type { RecapProjectionSourceSpan } from "../../api/types";
import type { GraphReviewContextualDelta } from "./graphReviewDeltaTypes";

export type GraphReviewSourceSpanDeltaStatus =
  | "matched"
  | "live_only"
  | "comparator_uncertain"
  | "mixed"
  | "unclassified";

export interface GraphReviewSourceSpanDeltaPresentation {
  sourceSpanRefId: string;
  status: GraphReviewSourceSpanDeltaStatus;
  sourceSpan?: RecapProjectionSourceSpan | null;
  deltas: GraphReviewContextualDelta[];
  primaryDelta?: GraphReviewContextualDelta | null;
  label: string;
  sourceSpanText?: string | null;
  evidenceRefIds: string[];
  liveNodeIds: string[];
  comparatorReasons: string[];
}

export interface GraphReviewSourceSpanDeltaIndex {
  spansById: Record<string, GraphReviewSourceSpanDeltaPresentation>;
  orderedSpans: GraphReviewSourceSpanDeltaPresentation[];
  countsByStatus: Record<GraphReviewSourceSpanDeltaStatus, number>;
}

const SOURCE_SPAN_STATUSES: GraphReviewSourceSpanDeltaStatus[] = [
  "matched",
  "live_only",
  "comparator_uncertain",
  "mixed",
  "unclassified",
];

function emptyCounts(): Record<GraphReviewSourceSpanDeltaStatus, number> {
  return Object.fromEntries(SOURCE_SPAN_STATUSES.map((status) => [status, 0])) as Record<GraphReviewSourceSpanDeltaStatus, number>;
}

function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value && value.trim())))).sort();
}

function statusForDeltas(deltas: GraphReviewContextualDelta[]): GraphReviewSourceSpanDeltaStatus {
  if (!deltas.length) return "unclassified";
  const statuses = new Set(deltas.map((delta) => delta.status));
  if (statuses.has("comparator_uncertain")) return "comparator_uncertain";
  if (statuses.has("matched") && statuses.has("live_only")) return "mixed";
  if (statuses.has("live_only")) return "live_only";
  if (deltas.every((delta) => delta.status === "matched")) return "matched";
  return "mixed";
}

function primaryDeltaFor(deltas: GraphReviewContextualDelta[]): GraphReviewContextualDelta | null {
  const priority = ["comparator_uncertain", "live_only", "matched"] as const;
  for (const status of priority) {
    const found = deltas.find((delta) => delta.status === status);
    if (found) return found;
  }
  return deltas[0] ?? null;
}

function compareSourceSpans(a: GraphReviewSourceSpanDeltaPresentation, b: GraphReviewSourceSpanDeltaPresentation): number {
  const aOrdinal = a.sourceSpan?.ordinal ?? Number.POSITIVE_INFINITY;
  const bOrdinal = b.sourceSpan?.ordinal ?? Number.POSITIVE_INFINITY;
  if (aOrdinal !== bOrdinal) return aOrdinal - bOrdinal;
  return a.sourceSpanRefId.localeCompare(b.sourceSpanRefId);
}

export function statusLabelForSourceSpan(status: GraphReviewSourceSpanDeltaStatus): string {
  switch (status) {
    case "matched":
      return "Matched";
    case "live_only":
      return "Live-only";
    case "comparator_uncertain":
      return "Uncertain";
    case "mixed":
      return "Mixed";
    case "unclassified":
      return "Unclassified";
  }
}

export function buildSourceSpanDeltaIndex(input: {
  sourceSpans: RecapProjectionSourceSpan[];
  deltas: GraphReviewContextualDelta[];
}): GraphReviewSourceSpanDeltaIndex {
  const deltasBySpanId = new Map<string, GraphReviewContextualDelta[]>();
  const knownSpanIds = new Set(input.sourceSpans.map((span) => span.span_id));

  for (const delta of input.deltas) {
    for (const spanId of delta.sourceSpanRefIds) {
      if (!knownSpanIds.has(spanId)) continue;
      const current = deltasBySpanId.get(spanId) ?? [];
      current.push(delta);
      deltasBySpanId.set(spanId, current);
    }
  }

  const countsByStatus = emptyCounts();
  const spansById: Record<string, GraphReviewSourceSpanDeltaPresentation> = {};

  for (const sourceSpan of input.sourceSpans) {
    const deltas = [...(deltasBySpanId.get(sourceSpan.span_id) ?? [])].sort((a, b) => a.deltaId.localeCompare(b.deltaId));
    const status = statusForDeltas(deltas);
    const primaryDelta = primaryDeltaFor(deltas);
    const presentation: GraphReviewSourceSpanDeltaPresentation = {
      sourceSpanRefId: sourceSpan.span_id,
      status,
      sourceSpan,
      deltas,
      primaryDelta,
      label: statusLabelForSourceSpan(status),
      sourceSpanText: sourceSpan.text_excerpt ?? null,
      evidenceRefIds: uniqueSorted(deltas.flatMap((delta) => delta.evidenceRefIds)),
      liveNodeIds: uniqueSorted(
        deltas.flatMap((delta) =>
          delta.laneObjectRefs
            .filter((ref) => ref.laneRole === "live" && ref.objectKind === "node")
            .map((ref) => ref.objectId),
        ),
      ),
      comparatorReasons: uniqueSorted(deltas.map((delta) => delta.comparatorReason)),
    };
    spansById[sourceSpan.span_id] = presentation;
    countsByStatus[status] += 1;
  }

  return {
    spansById,
    orderedSpans: Object.values(spansById).sort(compareSourceSpans),
    countsByStatus,
  };
}
