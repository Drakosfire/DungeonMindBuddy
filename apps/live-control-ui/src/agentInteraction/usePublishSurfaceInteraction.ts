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
  const identityKey = publication
    ? `${publication.identity.surfaceId}:${publication.identity.instanceKey}`
    : null;

  useEffect(() => {
    if (!publicationRef.current) return;
    return publishSurfaceInteractionPublication(publicationRef.current);
  }, [identityKey, publishSurfaceInteractionPublication]);

  useEffect(() => {
    if (!publicationRef.current) return;
    updateSurfaceInteractionPublication(publicationRef.current);
  }, [publication, updateSurfaceInteractionPublication]);
}
