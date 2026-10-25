import { useContext, useEffect, useLayoutEffect } from "react";

import { SurfaceContextStoreContext } from "./SurfaceContextProvider";
import type { SurfaceContextContribution } from "./surfaceContextTypes";

export function useSurfaceContext() {
  const context = useContext(SurfaceContextStoreContext);
  if (!context) {
    throw new Error("useSurfaceContext must be used within SurfaceContextProvider");
  }
  return context;
}

export function useOptionalSurfaceContext() {
  return useContext(SurfaceContextStoreContext);
}

export function useSurfaceContextContribution(contribution: SurfaceContextContribution): void {
  const { registerContribution, updateContribution } = useSurfaceContext();
  const { id, order, surfaceIdentity, content } = contribution;

  useEffect(() => {
    return registerContribution({
      id,
      order,
      surfaceIdentity,
      content,
    });
  }, [id, surfaceIdentity.surfaceId, surfaceIdentity.instanceKey, registerContribution]);

  // Context controls are part of the current commit. Deferring their publication
  // to a passive effect adds another nested update for every synchronous input.
  useLayoutEffect(() => {
    updateContribution(id, { content, order, surfaceIdentity });
  }, [id, content, order, surfaceIdentity, updateContribution]);
}
