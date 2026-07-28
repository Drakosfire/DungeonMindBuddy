import { useLayoutEffect, type ReactNode } from "react";

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
  const { publishProjectionSurface } = useAgentInteraction();
  useLayoutEffect(() => {
    return publishProjectionSurface(buildPublicationForConfig(config));
  }, [config, publishProjectionSurface]);
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
