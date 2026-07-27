import type { PlanReferenceResolution } from "../planSurface/reference/graphAwareReferenceResolver";
import type { GraphReferenceResolution } from "./graphReferenceTypes";

export function mapPlanResolutionToGraphReferenceResolution(
  resolution: PlanReferenceResolution,
): GraphReferenceResolution {
  if (resolution.kind === "graph-node" && resolution.graphNodeId) {
    return {
      kind: "resolved_graph",
      nodeId: resolution.graphNodeId,
      revision: null,
    };
  }

  if (resolution.kind === "corpus-index") {
    const refId = resolution.refId?.trim() || resolution.locator.trim();
    return {
      kind: "resolved_corpus_fallback",
      refId,
    };
  }

  if (resolution.ambiguousNodeIds?.length) {
    return {
      kind: "ambiguous",
      candidates: [...resolution.ambiguousNodeIds],
      refId: resolution.refId ?? null,
    };
  }

  const refId = resolution.refId?.trim() || resolution.locator.trim() || "unknown";
  return {
    kind: "unresolved",
    refId,
  };
}
