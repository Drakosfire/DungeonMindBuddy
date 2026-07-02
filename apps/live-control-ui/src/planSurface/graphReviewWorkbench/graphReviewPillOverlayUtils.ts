import type { GraphReviewContextualDelta } from "./graphReviewDeltaTypes";

export type GraphReviewPillDeltaStatus =
  | "matched"
  | "live_only"
  | "comparator_uncertain"
  | "unclassified";

export interface GraphReviewNodeDeltaPresentation {
  nodeId: string;
  status: GraphReviewPillDeltaStatus;
  deltas: GraphReviewContextualDelta[];
  primaryDelta?: GraphReviewContextualDelta | null;
  label?: string | null;
  sourceSpanRefIds: string[];
  evidenceRefIds: string[];
}

const PILL_STATUS_PRIORITY: GraphReviewPillDeltaStatus[] = [
  "comparator_uncertain",
  "live_only",
  "matched",
  "unclassified",
];

function pillStatusForDelta(delta: GraphReviewContextualDelta): GraphReviewPillDeltaStatus {
  if (delta.status === "matched" || delta.status === "live_only" || delta.status === "comparator_uncertain") {
    return delta.status;
  }
  return "unclassified";
}

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.trim()))).sort((a, b) => a.localeCompare(b));
}

function primaryDeltaFor(deltas: GraphReviewContextualDelta[]): GraphReviewContextualDelta | null {
  return [...deltas].sort((a, b) => {
    const statusOrder = PILL_STATUS_PRIORITY.indexOf(pillStatusForDelta(a)) - PILL_STATUS_PRIORITY.indexOf(pillStatusForDelta(b));
    if (statusOrder !== 0) return statusOrder;
    return a.deltaId.localeCompare(b.deltaId);
  })[0] ?? null;
}

export function statusLabelForPill(status: GraphReviewPillDeltaStatus): string {
  switch (status) {
    case "matched":
      return "Matched";
    case "live_only":
      return "Live-only";
    case "comparator_uncertain":
      return "Uncertain";
    case "unclassified":
      return "Unclassified";
  }
}

export function buildLiveNodeDeltaPresentationIndex(
  deltas: GraphReviewContextualDelta[],
): Record<string, GraphReviewNodeDeltaPresentation> {
  const deltasByNodeId = new Map<string, GraphReviewContextualDelta[]>();

  for (const delta of deltas) {
    for (const ref of delta.laneObjectRefs) {
      if (ref.laneRole !== "live" || ref.objectKind !== "node") continue;
      const existing = deltasByNodeId.get(ref.objectId) ?? [];
      existing.push(delta);
      deltasByNodeId.set(ref.objectId, existing);
    }
  }

  const entries = Array.from(deltasByNodeId.entries()).sort(([left], [right]) => left.localeCompare(right));
  const index: Record<string, GraphReviewNodeDeltaPresentation> = {};

  for (const [nodeId, nodeDeltas] of entries) {
    const sortedDeltas = [...nodeDeltas].sort((a, b) => a.deltaId.localeCompare(b.deltaId));
    const primaryDelta = primaryDeltaFor(sortedDeltas);
    const liveNodeRef = primaryDelta?.laneObjectRefs.find(
      (ref) => ref.laneRole === "live" && ref.objectKind === "node" && ref.objectId === nodeId,
    );
    index[nodeId] = {
      nodeId,
      status: primaryDelta ? pillStatusForDelta(primaryDelta) : "unclassified",
      deltas: sortedDeltas,
      primaryDelta,
      label: liveNodeRef?.label ?? primaryDelta?.label ?? null,
      sourceSpanRefIds: uniqueSorted(sortedDeltas.flatMap((delta) => delta.sourceSpanRefIds)),
      evidenceRefIds: uniqueSorted(sortedDeltas.flatMap((delta) => delta.evidenceRefIds)),
    };
  }

  return index;
}
