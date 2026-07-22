import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "./graphAwareReferenceResolver";

export interface OpenGraphNodeFromChipDeps {
  resolvePlanReference: (ref: RunbookReferenceAttrs) => Promise<PlanReferenceResolution>;
  openContentFromChip: (
    ref: RunbookReferenceAttrs,
    resolution: PlanReferenceResolution,
    glanceOnly?: boolean,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  projectionState?: PlanGraphProjectionState | null;
}

/**
 * Shared chip → Plan reference drawer path used by Plan canvas and Recap/Ingest readers.
 */
export async function openGraphNodeFromChip(
  nodeId: string,
  deps: OpenGraphNodeFromChipDeps,
  label?: string,
): Promise<void> {
  const trimmedId = nodeId.trim();
  if (!trimmedId) return;
  const ref: RunbookReferenceAttrs = {
    kind: "ref",
    refType: GRAPH_NODE_REF_TYPE,
    refId: trimmedId,
    label: (label ?? trimmedId).trim() || trimmedId,
  };
  const resolution = await deps.resolvePlanReference(ref);
  deps.openContentFromChip(ref, resolution, true, deps.projectionState ?? null);
}
