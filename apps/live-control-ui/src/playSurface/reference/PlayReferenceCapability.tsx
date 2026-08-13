import { useEffect, useMemo, type ReactNode } from "react";

import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildPlaySurfaceInteractionPublication } from "./buildPlaySurfaceInteractionPublication";
import { PlayReferenceObjectProjection } from "./PlayReferenceObjectProjection";

export interface PlayReferenceCapabilityProps {
  panelId: string;
  children?: ReactNode;
}

/**
 * Declares Play graph-reference authority and registers the ProjectionHost catalog
 * + binding so Beats chips (and other Play openGraphReference callers) can open sheets.
 */
export function PlayReferenceCapability({ panelId, children }: PlayReferenceCapabilityProps) {
  const {
    openGraphReference,
    openTool,
    registerGraphReferenceBinding,
    registerProjectionCatalog,
  } = useAgentInteraction();

  const publication = useMemo(
    () => buildPlaySurfaceInteractionPublication(panelId),
    [panelId],
  );

  usePublishSurfaceInteraction(publication);

  useEffect(() => {
    return registerProjectionCatalog({
      projectionId: GRAPH_REFERENCE_PROJECTION_ID,
      surfaceId: "play",
      kind: "content",
      preferredSize: "wide",
      requiredBindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      render: ({ bindings, active }) => (
        <PlayReferenceObjectProjection
          bindings={bindings}
          glanceOnly={active.glanceOnly === true}
        />
      ),
    });
  }, [registerProjectionCatalog]);

  useEffect(() => {
    return registerGraphReferenceBinding({
      resolverState: "ready",
      resolveRelationship: async (relationship) => {
        const locator = relationship.targetId?.trim() || relationship.label;
        const unresolved: GraphReferenceResolution = {
          kind: "unresolved",
          locator,
          reference: null,
          projectionState: "ready",
          message: "Relationship navigation is not available on Play yet.",
        };
        return unresolved;
      },
      openResolvedReference: (resolution, state) => {
        openGraphReference({
          resolution,
          projectionState: state ?? resolution.projectionState ?? "ready",
        });
      },
      openTool: (toolId) => {
        openTool(toolId);
      },
    });
  }, [openGraphReference, openTool, registerGraphReferenceBinding]);

  return children ? <>{children}</> : null;
}
