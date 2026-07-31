import { useEffect } from "react";

import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { useProjection } from "../projection/projectionContext";

/**
 * Adapts route-local Plan resolver/projection actions into a typed projection binding.
 * Must mount under PlanGraphReferenceResolverProvider and the app projection host.
 */
export function PlanReferenceProjectionBinding() {
  const { registerGraphReferenceBinding, openGraphReference, openTool } = useProjection();
  const { resolvePlanRelationship, projectionState } = usePlanGraphReferenceResolver();

  useEffect(() => {
    return registerGraphReferenceBinding({
      resolverState: projectionState,
      resolveRelationship: resolvePlanRelationship,
      openResolvedReference: (resolution, state) => {
        openGraphReference({
          resolution,
          projectionState: state ?? projectionState,
        });
      },
      openTool,
    });
  }, [
    openGraphReference,
    openTool,
    projectionState,
    registerGraphReferenceBinding,
    resolvePlanRelationship,
  ]);

  return null;
}
