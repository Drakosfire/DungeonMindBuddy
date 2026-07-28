import { useLayoutEffect, useMemo, useRef, type ReactNode } from "react";

import {
  AgentInteractionProvider,
  useAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";
import {
  buildIngestSurfaceIdentity,
  buildPlanSurfaceIdentity,
  type ProjectionSurfacePublication,
} from "../../agentInteraction/projectionSurfacePublication";
import type { SurfaceConfig } from "../types";

function buildPublicationForConfig(config: SurfaceConfig): ProjectionSurfacePublication {
  if (config.id === "plan" && config.sessionDescriptor) {
    return {
      identity: buildPlanSurfaceIdentity({
        documentId: config.sessionDescriptor.planningDocument.documentId,
        campaignId: config.sessionDescriptor.campaignId,
        liveSession: config.context!.liveSession,
        memorySession: config.sessionDescriptor.memorySession,
      }),
      config,
    };
  }
  if (config.id === "ingest" && config.context) {
    return {
      identity: buildIngestSurfaceIdentity({
        campaignId: config.context.campaignId,
        liveSession: config.context.liveSession,
        ingestSession: config.context.ingestSession,
      }),
      config,
    };
  }
  return {
    identity: {
      surfaceId: config.id,
      instanceKey: `test\u001f${config.id}`,
    },
    config,
  };
}

export function ProjectionSurfacePublisher({
  config,
  children,
}: {
  config: SurfaceConfig;
  children: ReactNode;
}) {
  const { publishProjectionSurface, updateProjectionSurfaceConfig } = useAgentInteraction();
  // Mirrors the production publishers: identity registration is separate from
  // same-identity config updates so a config-only rerender never unbinds.
  const publication = useMemo(() => buildPublicationForConfig(config), [config]);
  const publicationInstanceKey = `${publication.identity.surfaceId}${publication.identity.instanceKey}`;
  const publicationRef = useRef(publication);
  publicationRef.current = publication;
  useLayoutEffect(() => {
    return publishProjectionSurface(publicationRef.current);
  }, [publicationInstanceKey, publishProjectionSurface]);
  useLayoutEffect(() => {
    updateProjectionSurfaceConfig(publication);
  }, [publication, updateProjectionSurfaceConfig]);
  return children;
}

/** Test host for projection hooks. Mount AdaptiveProjectionContainer in the .test.tsx file when needed. */
export function AgentInteractionProjectionTestHost({
  config,
  children,
}: {
  config: SurfaceConfig;
  children: ReactNode;
}) {
  return (
    <AgentInteractionProvider>
      <ProjectionSurfacePublisher config={config}>{children}</ProjectionSurfacePublisher>
    </AgentInteractionProvider>
  );
}
