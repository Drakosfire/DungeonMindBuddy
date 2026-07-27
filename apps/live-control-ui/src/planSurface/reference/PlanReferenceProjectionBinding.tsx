import { useEffect } from "react";

import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { useProjection } from "../projection/projectionContext";

/**
 * Adapts route-local Plan resolver/projection actions into a typed projection binding.
 * Must mount under PlanGraphReferenceResolverProvider and ProjectionProvider.
 */
export function PlanReferenceProjectionBinding() {
  const { registerPlanReferenceBinding, openPlanReferenceResolution, openTool } = useProjection();
  const { resolvePlanRelationship, projectionState } = usePlanGraphReferenceResolver();

  useEffect(() => {
    return registerPlanReferenceBinding({
      resolverState: projectionState,
      resolveRelationship: resolvePlanRelationship,
      openResolvedReference: openPlanReferenceResolution,
      openTool,
    });
  }, [
    openPlanReferenceResolution,
    openTool,
    projectionState,
    registerPlanReferenceBinding,
    resolvePlanRelationship,
  ]);

  return null;
}
