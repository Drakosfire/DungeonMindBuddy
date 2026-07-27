import { useCallback } from "react";

import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";
import { useProjection } from "../planSurface/projection/projectionContext";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../planSurface/reference/graphAwareReferenceResolver";
import { openGraphReference } from "./openGraphReference";

export function useOpenGraphReference(): (
  planResolution: PlanReferenceResolution,
  projectionState?: PlanGraphProjectionState | null,
  ref?: RunbookReferenceAttrs,
) => void {
  const { openPlanReferenceResolution, openContentFromChip } = useProjection();

  return useCallback(
    (
      planResolution: PlanReferenceResolution,
      projectionState?: PlanGraphProjectionState | null,
      ref?: RunbookReferenceAttrs,
    ) => {
      openGraphReference(
        { openPlanReferenceResolution, openContentFromChip },
        { planResolution, projectionState, ref },
      );
    },
    [openContentFromChip, openPlanReferenceResolution],
  );
}
