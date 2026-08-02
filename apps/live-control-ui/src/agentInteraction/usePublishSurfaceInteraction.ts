import { useEffect, useRef } from "react";

import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { useAgentInteraction } from "./useAgentInteraction";

/**
 * Bind-on-identity / update-on-config publisher for complete neutral or route
 * compatibility publications. Same-identity continuity is owned by the provider
 * update API, not by repeated bind calls.
 */
export function usePublishSurfaceInteraction(publication: SurfaceInteractionPublication | null): void {
  const { publishSurfaceInteractionPublication, updateSurfaceInteractionPublication } = useAgentInteraction();
  const publicationRef = useRef(publication);
  publicationRef.current = publication;
  const surfaceId = publication?.identity.surfaceId ?? null;
  const instanceKey = publication?.identity.instanceKey ?? null;

  useEffect(() => {
    return publishSurfaceInteractionPublication(publicationRef.current);
  }, [surfaceId, instanceKey, publishSurfaceInteractionPublication]);

  useEffect(() => {
    if (!publication) return;
    updateSurfaceInteractionPublication(publication);
  }, [publication, updateSurfaceInteractionPublication]);
}
