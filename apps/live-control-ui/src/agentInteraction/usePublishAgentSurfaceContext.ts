import { useEffect } from "react";

import type { AgentInteractionSurfaceContext } from "./agentInteractionTypes";
import { useAgentInteraction } from "./useAgentInteraction";

type PublishableSurfaceContext = Omit<AgentInteractionSurfaceContext, "updatedAt">;

/**
 * Publish (and keep fresh) Agent Interaction ambient surface context.
 * Callers should memoize `context`. Surfaces own the payload; chrome only displays it.
 */
export function usePublishAgentSurfaceContext(context: PublishableSurfaceContext | null): void {
  const { publishSurfaceContext, rehydrateScope } = useAgentInteraction();

  useEffect(() => {
    if (!context) return;
    rehydrateScope({
      campaignId: context.campaignId ?? context.surfaceId,
      sessionNumber: context.sessionNumber ?? null,
      surfaceId: context.surfaceId,
      documentId: context.documentId ?? null,
    });
    publishSurfaceContext({
      ...context,
      updatedAt: new Date().toISOString(),
    });
  }, [context, publishSurfaceContext, rehydrateScope]);
}
